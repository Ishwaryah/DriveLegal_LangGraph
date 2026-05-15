import json
import os
from typing import Optional, Dict


def _reverse_geocode_state(gps: Dict) -> Optional[str]:
    """
    Attempts to resolve a state from GPS coordinates using local GeoJSON zone data.
    Returns None if no match is found — does NOT fall back to a hardcoded value.
    """
    # NOTE: A real implementation would use the GeoJSON zone files in data/zones/
    # to do a point-in-polygon lookup. Until that data is integrated, we return None
    # honestly rather than guessing. This prevents hallucinated state data.
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
            # Attempt real reverse geocoding — returns None if unavailable
            resolved_state = _reverse_geocode_state(gps)
            if resolved_state:
                entities["state"] = resolved_state
            # If None, we leave state as None — prompting the user to clarify

    # 2. Vehicle Class Resolution from Session
    if entities.get("vehicle_class") is None and session.get("vehicle_class"):
        entities["vehicle_class"] = session["vehicle_class"]

    # 3. Offence Type & Section Resolution from Session
    # Only inherit offence/section if this looks like a follow-up query
    # e.g., very short text (like 'DL', 'car') or unknown intent.
    is_followup = len(raw_text.split()) <= 3 or intent == "unknown"

    if is_followup:
        if entities.get("offence_type") is None and session.get("offence_type"):
            entities["offence_type"] = session["offence_type"]

        if entities.get("section_ref") is None and session.get("section_ref"):
            entities["section_ref"] = session["section_ref"]

    # 4. Repeat Offence Resolution from Session
    if entities.get("repeat_offence") is None and session.get("previous_offences"):
        entities["repeat_offence"] = "true"

    return entities
