import re
import spacy
from spacy.matcher import Matcher
import os
import json
from typing import Dict

# Road/zone type keywords → normalised label used in search context
_ROAD_TYPE_MAP = {
    "expressway": "expressway",
    "national highway": "national_highway",
    "nh": "national_highway",
    "state highway": "state_highway",
    "highway": "highway",
    "flyover": "flyover",
    "bridge": "bridge",
    "tunnel": "tunnel",
    "school zone": "school_zone",
    "school area": "school_zone",
    "near school": "school_zone",
    "hospital zone": "hospital_zone",
    "silent zone": "silent_zone",
    "residential area": "residential",
    "residential road": "residential",
    "city road": "urban",
    "urban road": "urban",
    "village road": "rural",
    "rural road": "rural",
    "one way": "one_way",
    "one-way": "one_way",
    "roundabout": "roundabout",
    "intersection": "intersection",
    "junction": "intersection",
    "parking lot": "parking",
    "no parking": "no_parking_zone",
}


class EntityExtractor:
    def __init__(self, metadata_path: str = None):
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            self.nlp = spacy.blank("en")

        self.matcher = Matcher(self.nlp.vocab)
        # "Section 185", "Section 183(1)", etc.
        self.matcher.add("SECTION_REF", [
            [{"LOWER": "section"}, {"IS_DIGIT": True}],
            [{"LOWER": "section"}, {"IS_DIGIT": True}, {"TEXT": "("}, {"IS_ALPHA": True}, {"TEXT": ")"}],
        ])

        if metadata_path is None:
            metadata_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "metadata.json")

        self.metadata: Dict = {}
        if os.path.exists(metadata_path):
            with open(metadata_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)

        self.vehicle_classes = self.metadata.get("vehicle_classes", {})
        self.offence_map     = self.metadata.get("offence_map", {})
        self.state_map       = self.metadata.get("states", {})
        self.repeat_keywords = self.metadata.get("repeat_keywords", [])

    def extract(self, text: str) -> Dict:
        """
        Extract structured entities from a traffic law query.

        Returns:
          offence_type  — normalised offence code or None
          vehicle_class — 2W / LMV / HGV / 3W or None
          state         — canonical state name or None
          repeat_offence— "true" or None
          section_ref   — "Section NNN" or None
          road_type     — normalised road/zone label or None
        """
        doc = self.nlp(text)
        entities: Dict = {
            "offence_type":  None,
            "vehicle_class": None,
            "state":         None,
            "repeat_offence": None,
            "section_ref":   None,
            "road_type":     None,
        }

        text_lower = text.lower()

        # 1. Vehicle class — longest-match first to avoid "bike" matching "e-bike" partially
        for key in sorted(self.vehicle_classes, key=len, reverse=True):
            if key in text_lower:
                entities["vehicle_class"] = self.vehicle_classes[key]
                break

        # 2. Section reference via spaCy Matcher
        matches = self.matcher(doc)
        if matches:
            _, start, end = matches[0]
            entities["section_ref"] = doc[start:end].text

        # 3. State — Priority 1: spaCy GPE entities
        for ent in doc.ents:
            if ent.label_ == "GPE":
                # Verify the GPE is actually a known Indian state/city
                ent_lower = ent.text.lower()
                for canonical, variations in self.state_map.items():
                    if any(ent_lower == v.lower() for v in variations):
                        entities["state"] = canonical
                        break
                if entities["state"]:
                    break

        # Priority 2: metadata keyword mapping
        # Short variations (<=3 chars) use word-boundary matching to avoid false
        # matches on common substrings ("as" in "class", "up" in "upon", etc.)
        if entities["state"] is None:
            for canonical_state, variations in self.state_map.items():
                matched = False
                for v in variations:
                    if len(v) <= 3:
                        if re.search(r"\b" + re.escape(v) + r"\b", text_lower):
                            matched = True
                            break
                    else:
                        if v in text_lower:
                            matched = True
                            break
                if matched:
                    entities["state"] = canonical_state
                    break

        # 4. Repeat offence
        if any(kw in text_lower for kw in self.repeat_keywords):
            entities["repeat_offence"] = "true"

        # 5. Offence type — longest-match first to prefer specific phrases
        for phrase in sorted(self.offence_map, key=len, reverse=True):
            if phrase in text_lower:
                entities["offence_type"] = self.offence_map[phrase]
                break

        # 6. Road / zone type — appended to query context for search enrichment
        for phrase in sorted(_ROAD_TYPE_MAP, key=len, reverse=True):
            if phrase in text_lower:
                entities["road_type"] = _ROAD_TYPE_MAP[phrase]
                break

        return entities
