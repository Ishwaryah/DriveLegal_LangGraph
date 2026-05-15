"""
Multilingual Intent Extractor
==============================
Language detection and intent/entity extraction for Hindi, Tamil, Arabic, and
other languages.  Falls back to the English NLP pipeline when confidence is low.
"""

import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Language detection ─────────────────────────────────────────────────────────

def detect_language(text: str) -> str:
    """
    Detect language of *text*.  Returns an ISO 639-1 code ('en', 'hi', 'ta', …).
    Falls back to 'en' on any error or when text is too short to be reliable.
    """
    if not text or len(text.strip()) < 3:
        return "en"
    try:
        from langdetect import detect, DetectorFactory, LangDetectException
        # Make detection deterministic
        DetectorFactory.seed = 0
        return detect(text)
    except Exception:
        return "en"


# ── Keyword → violation-code mappings ─────────────────────────────────────────

HINDI_KEYWORDS: Dict[str, str] = {
    "हेलमेट":      "no_helmet",
    "नशे":         "drunk_driving",
    "शराब":        "drunk_driving",
    "तेज़ गति":    "overspeeding",
    "ओवरस्पीडिंग": "overspeeding",
    "सीट बेल्ट":  "no_seatbelt",
    "फोन":         "using_phone",
    "मोबाइल":      "using_phone",
    "बीमा":        "no_insurance",
    "लाइसेंस":     "no_license",
    "सिग्नल":      "signal_jumping",
    "जुर्माना":    "fine",
    "चालान":       "challan",
    "धारा":        "section",
}

TAMIL_KEYWORDS: Dict[str, str] = {
    "தலைக்கவசம்": "no_helmet",
    "குடிபோதை":   "drunk_driving",
    "மது":         "drunk_driving",
    "வேகம்":       "overspeeding",
    "அதிவேகம்":   "overspeeding",
    "சிக்னல்":    "signal_jumping",
    "சீட் பெல்ட்": "no_seatbelt",
    "பாதுகாப்பு பட்டை": "no_seatbelt",
    "தொலைபேசி":   "using_phone",
    "காப்பீடு":   "no_insurance",
    "உரிமம்":     "license",
    "அபராதம்":    "fine",
    "தண்டம்":     "fine",
}

# Tamil state keyword map: native-script state name → canonical English state name
TAMIL_STATE_KEYWORDS: Dict[str, str] = {
    "தமிழ்நாடு":      "Tamil Nadu",
    "தமிழ்நாட்டில்":  "Tamil Nadu",
    "தமிழ்நாட்டில":   "Tamil Nadu",
    "தமிழ்நாட்டின்":  "Tamil Nadu",
    "சென்னை":         "Tamil Nadu",
    "கோயம்புத்தூர்":  "Tamil Nadu",
    "மதுரை":          "Tamil Nadu",
    "கேரளா":          "Kerala",
    "கர்நாடகா":       "Karnataka",
    "மகாராஷ்டிரா":    "Maharashtra",
    "டெல்லி":         "Delhi",
}

# ── Arabic keywords ────────────────────────────────────────────────────────────

ARABIC_KEYWORDS: Dict[str, str] = {
    "تجاوز السرعة": "overspeeding",
    "سرعة زائدة":   "overspeeding",
    "السرعة":       "overspeeding",
    "سرعة":         "overspeeding",
    "قيادة متهورة": "reckless_driving",
    "قيادة تحت تأثير الكحول": "drunk_driving",
    "الكحول":       "drunk_driving",
    "تحت تأثير":    "drunk_driving",
    "حزام الأمان":  "no_seatbelt",
    "الهاتف":       "using_phone",
    "موبايل":       "using_phone",
    "التأمين":      "no_insurance",
    "بدون تأمين":   "no_insurance",
    "رخصة القيادة": "no_license",
    "بدون رخصة":    "no_license",
    "إشارة المرور": "signal_jumping",
    "الإشارة الحمراء": "signal_jumping",
    "غرامة":        "fine",
    "مخالفة":       "fine",
    "عقوبة":        "fine",
}

# Arabic country names → ISO country code
ARABIC_COUNTRY_KEYWORDS: Dict[str, str] = {
    "الإمارات":             "AE",
    "إمارات":               "AE",
    "دبي":                  "AE",
    "أبوظبي":               "AE",
    "الشارقة":              "AE",
    "الهند":                "IN",
    "سنغافورة":             "SG",
    "المملكة المتحدة":      "GB",
    "بريطانيا":             "GB",
}

# violation code → canonical offence_type used by the NLP pipeline
_VIOLATION_TO_OFFENCE: Dict[str, str] = {
    "no_helmet":     "NO_HELMET",
    "drunk_driving": "DRUNK_DRIVING",
    "overspeeding":  "SPEED_EXCESS",
    "no_seatbelt":   "NO_SEATBELT",
    "using_phone":   "MOBILE_PHONE",
    "no_insurance":  "NO_INSURANCE",
    "no_license":    "NO_LICENSE",
    "signal_jumping": "RED_LIGHT_JUMPING",
    "license":       "NO_LICENSE",
}

# ── Simple word-substitution translation tables (no API calls) ─────────────────

_HINDI_TO_ENGLISH: Dict[str, str] = {
    "हेलमेट":      "helmet",
    "नशे":         "drunk",
    "शराब":        "drunk driving alcohol",
    "तेज़ गति":    "over speeding",
    "ओवरस्पीडिंग": "overspeeding",
    "सीट बेल्ट":  "seat belt",
    "फोन":         "phone",
    "मोबाइल":      "mobile phone",
    "बीमा":        "insurance",
    "लाइसेंस":     "license",
    "सिग्नल":      "signal jumping",
    "जुर्माना":    "fine penalty",
    "चालान":       "challan",
    "धारा":        "section",
    "क्या":        "what",
    "है":          "is",
    "पर":          "on",
    "न":           "not",
    "पहनने":       "wearing",
    "न पहनने":     "not wearing",
    "गाड़ी":       "vehicle",
    "कार":         "car",
    "बाइक":        "bike",
    "ट्रक":        "truck",
    "कितना":       "how much",
    "के लिए":      "for",
    "होता है":     "is",
}

_TAMIL_TO_ENGLISH: Dict[str, str] = {
    "தலைக்கவசம்":  "helmet",
    "குடிபோதை":    "drunk driving",
    "மது":          "drunk driving",
    "வேகம்":        "speeding",
    "அதிவேகம்":    "overspeeding",
    "சிக்னல்":     "signal jumping",
    "அபராதம்":     "fine penalty",
    "தண்டம்":      "fine",
    "உரிமம்":      "license",
    "காப்பீடு":    "insurance",
    "தொலைபேசி":    "mobile phone",
    "சீட் பெல்ட்": "seat belt",
    "என்ன":        "what",
    "எவ்வளவு":     "how much",
    "தமிழ்நாடு":   "Tamil Nadu",
    "தமிழ்நாட்டில்": "Tamil Nadu",
    "சென்னை":      "Chennai Tamil Nadu",
}

_ARABIC_TO_ENGLISH: Dict[str, str] = {
    "تجاوز السرعة":    "overspeeding",
    "سرعة زائدة":      "overspeeding",
    "السرعة":          "speed limit",
    "سرعة":            "speeding",
    "قيادة متهورة":    "reckless driving",
    "قيادة تحت تأثير الكحول": "drunk driving",
    "الكحول":          "alcohol drunk driving",
    "تحت تأثير":       "under influence",
    "حزام الأمان":     "seatbelt",
    "الهاتف":          "mobile phone",
    "موبايل":          "mobile phone",
    "التأمين":         "insurance",
    "بدون تأمين":      "no insurance",
    "رخصة القيادة":    "driving license",
    "بدون رخصة":       "no license",
    "إشارة المرور":    "signal jumping",
    "الإشارة الحمراء": "red light",
    "الإمارات":        "UAE",
    "إمارات":          "UAE",
    "دبي":             "Dubai",
    "أبوظبي":          "Abu Dhabi",
    "الهند":           "India",
    "ما هي":           "what is",
    "كم":              "how much",
    "غرامة":           "fine penalty",
    "مخالفة":          "violation",
    "عقوبة":           "punishment fine",
    "في":              "in",
}

# ── Fine-intent indicators per language ───────────────────────────────────────

_FINE_INDICATORS: Dict[str, List[str]] = {
    "hi": ["जुर्माना", "चालान", "कितना", "fine", "penalty"],
    "ta": ["அபராதம்", "தண்டம்", "எவ்வளவு", "fine", "penalty"],
    "ar": ["غرامة", "مخالفة", "عقوبة", "fine", "penalty"],
}


# ── Public API ─────────────────────────────────────────────────────────────────

def extract_intent_multilingual(
    text: str,
    lang: str,
) -> Tuple[str, List[str], str]:
    """
    Extract intent, violation codes, and country from a multilingual query.

    Returns:
      intent          — 'fine_lookup', 'rule_query', 'general_query', 'unknown'
      violation_codes — raw violation codes matched (e.g. ['no_helmet'])
      country         — ISO country code ('IN', 'AE', 'SG', 'GB')
    """
    violation_codes: List[str] = []
    intent = "unknown"
    country = "IN"

    if lang == "hi":
        keyword_map = HINDI_KEYWORDS
    elif lang == "ta":
        keyword_map = TAMIL_KEYWORDS
    elif lang == "ar":
        keyword_map = ARABIC_KEYWORDS
    else:
        return intent, violation_codes, country

    # Detect country from language-specific country keywords
    if lang == "ar":
        # Arabic: detect UAE/SG/GB from Arabic country names
        for phrase, cc in sorted(ARABIC_COUNTRY_KEYWORDS.items(), key=lambda x: len(x[0]), reverse=True):
            if phrase in text:
                country = cc
                break
    elif lang == "ta":
        # Tamil: no country override needed (default IN)
        pass

    # Longest-match first so "تجاوز السرعة" beats "السرعة"
    for phrase in sorted(keyword_map, key=len, reverse=True):
        if phrase in text:
            code = keyword_map[phrase]
            if code not in ("fine", "challan", "section", "license") and code not in violation_codes:
                violation_codes.append(code)

    # Determine intent
    fine_indicators = _FINE_INDICATORS.get(lang, [])
    if violation_codes:
        if any(ind in text for ind in fine_indicators) or "fine" in text.lower():
            intent = "fine_lookup"
        else:
            intent = "rule_query"
    elif any(ind in text for ind in fine_indicators):
        intent = "fine_lookup"

    return intent, violation_codes, country


def extract_state_multilingual(text: str, lang: str) -> Optional[str]:
    """
    Extract a canonical English state name from a multilingual query.
    Returns None if no state is detected.
    """
    if lang == "ta":
        for phrase, state in sorted(TAMIL_STATE_KEYWORDS.items(), key=lambda x: len(x[0]), reverse=True):
            if phrase in text:
                return state
    return None


def translate_to_english(text: str, lang: str) -> str:
    """
    Approximate word-substitution translation for Hindi/Tamil/Arabic → English.
    Used as a fallback when multilingual intent extraction fails to yield
    any violation codes.
    """
    if lang == "hi":
        table = _HINDI_TO_ENGLISH
    elif lang == "ta":
        table = _TAMIL_TO_ENGLISH
    elif lang == "ar":
        table = _ARABIC_TO_ENGLISH
    else:
        return text

    result = text
    # Replace longest phrases first to avoid partial clobbering
    for native, english in sorted(table.items(), key=lambda kv: len(kv[0]), reverse=True):
        result = result.replace(native, english)
    return result


def violation_code_to_offence_type(violation_code: str) -> Optional[str]:
    """Map a raw violation code (e.g. 'no_helmet') to the canonical offence_type."""
    return _VIOLATION_TO_OFFENCE.get(violation_code)
