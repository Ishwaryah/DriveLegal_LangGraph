import os
from typing import Optional, Dict
from backend.modules.geofencing.offline_geocoder import reverse_geocode

def _reverse_geocode_state(gps: Dict) -> Optional[str]:
    """
    Attempts to resolve a state from GPS coordinates using local GeoJSON zone data.
    Returns None if no match is found — does NOT fall back to a hardcoded value.
    """
    lat = gps.get("lat")
    lon = gps.get("lon")
    if lat is None or lon is None:
        return None
        
    # Find zones directory relative to this file
    # backend/modules/nlp/context_resolver.py -> backend/data/zones
    zones_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "zones"))
    
    result = reverse_geocode(lat, lon, zones_dir)
    state = result.get("state")
    if state and state != "UNKNOWN":
        return state
        
    return None


def resolve(entities: Dict, session: Dict, gps: Optional[Dict], intent: str = "unknown", raw_text: str = "") -> Dict:
    """
    Resolve missing fields using GPS or session context.
    Never infer offence_type — leave as None if missing.
    Never fabricate state from GPS — only use it if real reverse-geocoding is available.
    """
    # 1. State Resolution from Session or GPS (no hardcoded fallback)
    if entities.get("state") is None:
        if session.get("state"):
            entities["state"] = session["state"]
        elif gps:
            resolved_state = _reverse_geocode_state(gps)
            if resolved_state:
                entities["state"] = resolved_state

    # 2. Vehicle Class Resolution from Session
    if entities.get("vehicle_class") is None and session.get("vehicle_class"):
        entities["vehicle_class"] = session["vehicle_class"]

    # 3. Offence Type & Section Resolution from Session
    #
    # Always inherit when the previous turn asked a clarification question
    # (session["in_clarification"] = True).  This covers any reply length or
    # intent — the user is just answering our question, not starting a new topic.
    #
    # Also inherit for short/ambiguous follow-ups (≤ 4 words, or unknown intent)
    # so that "Chennai" / "I'm in Delhi" / "bike" all flow naturally.
    in_clarification = session.get("in_clarification", False)
    is_followup = in_clarification or len(raw_text.split()) <= 4 or intent == "unknown"

    if is_followup:
        if entities.get("offence_type") is None and session.get("offence_type"):
            entities["offence_type"] = session["offence_type"]

        if entities.get("section_ref") is None and session.get("section_ref"):
            entities["section_ref"] = session["section_ref"]

    # 4. Repeat Offence Resolution from Session
    if entities.get("repeat_offence") is None and session.get("previous_offences"):
        entities["repeat_offence"] = "true"

    return entities
