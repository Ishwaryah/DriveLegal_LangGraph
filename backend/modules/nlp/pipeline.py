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
from backend.modules.multilingual_intent import (
    detect_language,
    extract_intent_multilingual,
    extract_state_multilingual,
    violation_code_to_offence_type
)

logger = logging.getLogger(__name__)

# Canonical empty entity dict — used as fallback if extraction fails
_EMPTY_ENTITIES: Dict[str, Any] = {
    "offence_type":  None,
    "vehicle_class": None,
    "state":         None,
    "repeat_offence": None,
    "section_ref":   None,
    "road_type":     None,
}

# Intents that are valid without a structured offence_type/section_ref.
# General and procedure queries are answered from the knowledge base alone.
_KNOWLEDGE_INTENTS = {"general_query", "procedure_query"}


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

            # 2. Language detection
            lang = detect_language(clean_text)
            
            # 3. Classify intent (Multilingual support)
            multilingual_intent = "unknown"
            multilingual_violations = []
            multilingual_country = "IN"
            if lang != "en":
                multilingual_intent, multilingual_violations, multilingual_country = extract_intent_multilingual(clean_text, lang)

            try:
                intent = self.classifier.predict(clean_text) or "unknown"
                # Use multilingual intent if classifier failed but keyword match found
                if intent == "unknown" and multilingual_intent != "unknown":
                    intent = multilingual_intent
            except Exception as e:
                logger.error("Intent classification error: %s", e)
                intent = multilingual_intent or "unknown"

            # 4. Extract entities
            try:
                entities = self.extractor.extract(clean_text)
                # Merge multilingual violations if found
                if multilingual_violations:
                    for v_code in multilingual_violations:
                        offence = violation_code_to_offence_type(v_code)
                        if offence and not entities.get("offence_type"):
                            entities["offence_type"] = offence

                # Merge state detected from native-script keywords (e.g. Tamil Nadu in Tamil)
                if not entities.get("state") and lang != "en":
                    ml_state = extract_state_multilingual(clean_text, lang)
                    if ml_state:
                        entities["state"] = ml_state

                # Propagate country detected from multilingual extraction (e.g. Arabic UAE)
                if multilingual_country != "IN":
                    entities["country"] = multilingual_country

                # Ensure all keys present
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
            # Knowledge-base intents (general/procedure) are valid without a
            # structured offence code — they rely on semantic search instead.
            if intent == "unknown":
                status = "insufficient_info"
            elif not has_subject and intent not in _KNOWLEDGE_INTENTS:
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
                "road_type":     resolved.get("road_type"),
                "country":       resolved.get("country") or entities.get("country"),
                "confidence":    confidence,
                "status":        status,
                "raw_text":      raw_text,
                "lang":          lang,
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
