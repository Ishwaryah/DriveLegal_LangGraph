import spacy
from spacy.matcher import Matcher
import os
import json
from typing import Dict

class EntityExtractor:
    def __init__(self, metadata_path: str = None):
        # Load spaCy model
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            self.nlp = spacy.blank("en")
            
        self.matcher = Matcher(self.nlp.vocab)
        section_pattern = [{"LOWER": "section"}, {"IS_DIGIT": True}]
        self.matcher.add("SECTION_REF", [section_pattern])

        # Load Metadata
        if metadata_path is None:
            metadata_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "metadata.json")
        
        self.metadata = {}
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                self.metadata = json.load(f)
        
        self.vehicle_classes = self.metadata.get("vehicle_classes", {})
        self.offence_map = self.metadata.get("offence_map", {})
        self.state_map = self.metadata.get("states", {})
        self.repeat_keywords = self.metadata.get("repeat_keywords", [])

    def extract(self, text: str) -> Dict:
        """
        Extract entities using data-driven mappings.
        """
        doc = self.nlp(text)
        entities = {
            "offence_type": None,
            "vehicle_class": None,
            "state": None,
            "repeat_offence": None,
            "section_ref": None
        }

        text_lower = text.lower()

        # 1. Extract Vehicle Class
        for key, val in self.vehicle_classes.items():
            if key in text_lower:
                entities["vehicle_class"] = val
                break

        # 2. Extract Section Ref via Matcher
        matches = self.matcher(doc)
        if matches:
            _, start, end = matches[0]
            entities["section_ref"] = doc[start:end].text

        # 3. Extract State
        # Priority 1: spaCy GPE
        for ent in doc.ents:
            if ent.label_ == "GPE":
                entities["state"] = ent.text
                break
        
        # Priority 2: metadata.json mapping
        if entities["state"] is None:
            for canonical_state, variations in self.state_map.items():
                if any(v in text_lower for v in variations):
                    entities["state"] = canonical_state
                    break

        # 4. Repeat Offence detection
        if any(keyword in text_lower for keyword in self.repeat_keywords):
            entities["repeat_offence"] = "true"

        # 5. Offence Type Mapping
        for phrase, code in self.offence_map.items():
            if phrase in text_lower:
                entities["offence_type"] = code
                break

        return entities
