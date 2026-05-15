import logging
import os
import json

logger = logging.getLogger(__name__)

# Priority order: earlier = higher priority.
# procedure_query must beat rule_query/fine_lookup for "how to" phrases.
# general_query must beat rule_query for open-ended "what is/are" questions.
# zone_check is last because its keywords are very broad.
_INTENT_PRIORITY = [
    "procedure_query",
    "general_query",
    "fine_lookup",
    "rule_query",
    "zone_check",
]


class IntentClassifier:
    def __init__(self, metadata_path: str = None):
        """
        Keyword-based intent classifier using metadata.json rules.
        Intents (in priority order):
          procedure_query — how to, steps to, apply for, renew, contest, pay
          general_query   — open-ended road rule questions (speed limits, signs, etc.)
          fine_lookup     — fine/penalty/challan amounts for a specific offence
          rule_query      — is it legal, section, act references
          zone_check      — location/zone-specific questions
          unknown         — fallback
        """
        if metadata_path is None:
            metadata_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "metadata.json")

        self.rules: dict = {}
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                self.rules = metadata.get("intent_rules", {})
            except Exception as e:
                logger.warning("IntentClassifier: failed to load metadata: %s", e)

    def predict(self, text: str) -> str:
        """
        Predict intent using priority-ordered keyword matching.
        Returns one of: procedure_query, general_query, fine_lookup,
                        rule_query, zone_check, unknown.
        """
        text_lower = text.lower()

        # Walk intents in priority order so the first match wins
        for intent in _INTENT_PRIORITY:
            keywords = self.rules.get(intent, [])
            if any(kw in text_lower for kw in keywords):
                return intent

        # Any intent defined in metadata but not in our priority list (future-proof)
        for intent, keywords in self.rules.items():
            if intent not in _INTENT_PRIORITY:
                if any(kw in text_lower for kw in keywords):
                    return intent

        return "unknown"
