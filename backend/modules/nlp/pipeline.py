"""
NLP Pipeline  v2.0
===================
Orchestrates: normalize → classify intent → extract entities → resolve context.

NoneType safeguards applied throughout:
  - All entity fields default to None (not absent keys)
  - Classifier and extractor failures are caught and logged
  - resolve() receives a complete entity dict — never a partial one
  - Confidence is 0.0 when intent is unknown
"""

import logging
from typing import Dict, Any, Optional

from .normalizer import normalize
from .intent_classifier import IntentClassifier
from .entity_extractor import EntityExtractor
from .context_resolver import resolve

logger = logging.getLogger(__name__)

# Canonical empty entity dict — used as fallback if extraction fails
_EMPTY_ENTITIES: Dict[str, Any] = {
    "offence_type":  None,
    "vehicle_class": None,
    "state":         None,
    "repeat_offence": None,
    "section_ref":   None,
}


class NLPPipeline:
    def __init__(self):
        self.classifier = IntentClassifier()
        self.extractor  = EntityExtractor()

    def run(
        self,
        raw_text: str,
        session: Dict = None,
        gps: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Run the full NLP pipeline.

        Returns a dict with keys:
          intent, offence_type, vehicle_class, state, repeat_offence,
          section_ref, confidence, status, raw_text
        """
        session = session or {}

        if not raw_text or not raw_text.strip():
            return {
                **_EMPTY_ENTITIES,
                "intent":     "unknown",
                "confidence": 0.0,
                "status":     "insufficient_info",
                "raw_text":   raw_text or "",
            }

        try:
            # 1. Normalise
            clean_text = normalize(raw_text)

            # 2. Classify intent
            try:
                intent = self.classifier.predict(clean_text) or "unknown"
            except Exception as e:
                logger.error("Intent classification error: %s", e)
                intent = "unknown"

            # 3. Extract entities (returns complete dict with None defaults)
            try:
                entities = self.extractor.extract(clean_text)
                # Ensure all keys present — guard against partial returns
                for key in _EMPTY_ENTITIES:
                    entities.setdefault(key, None)
            except Exception as e:
                logger.error("Entity extraction error: %s", e)
                entities = dict(_EMPTY_ENTITIES)

            # 4. Resolve context (session + GPS fill-in)
            try:
                resolved = resolve(entities, session, gps, intent, raw_text)
                for key in _EMPTY_ENTITIES:
                    resolved.setdefault(key, None)
            except Exception as e:
                logger.error("Context resolution error: %s", e)
                resolved = entities

            # 5. Confidence & status
            confidence = 0.8 if intent != "unknown" else 0.0

            has_subject = (
                resolved.get("offence_type") is not None
                or resolved.get("section_ref") is not None
            )
            if intent == "unknown" or not has_subject:
                status = "insufficient_info"
            else:
                status = "success"

            return {
                "intent":        intent,
                "offence_type":  resolved.get("offence_type"),
                "vehicle_class": resolved.get("vehicle_class"),
                "state":         resolved.get("state"),
                "repeat_offence": resolved.get("repeat_offence"),
                "section_ref":   resolved.get("section_ref"),
                "confidence":    confidence,
                "status":        status,
                "raw_text":      raw_text,
            }

        except Exception as e:
            logger.exception("NLP Pipeline unhandled error: %s", e)
            return {
                **_EMPTY_ENTITIES,
                "intent":     "unknown",
                "confidence": 0.0,
                "status":     "error",
                "message":    str(e),
                "raw_text":   raw_text,
            }
