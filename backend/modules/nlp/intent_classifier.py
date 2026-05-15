import logging
import os
import json

class IntentClassifier:
    def __init__(self, metadata_path: str = None):
        """
        Keyword-based intent classifier using metadata.json rules.
        """
        # Load Metadata
        if metadata_path is None:
            metadata_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "metadata.json")
        
        self.rules = {}
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                self.rules = metadata.get("intent_rules", {})

    def predict(self, text: str) -> str:
        """
        Predict intent: "fine_lookup", "rule_query", "zone_check", "unknown"
        """
        predicted_intent = "unknown"
        confidence = 0.0

        for intent, keywords in self.rules.items():
            if any(keyword in text.lower() for keyword in keywords):
                predicted_intent = intent
                confidence = 0.8
                break

        return predicted_intent
