"""
Country Detector
================
Detects country context from free-form user query text.
Returns a 2-letter ISO 3166-1 alpha-2 code, defaulting to "IN".

No external dependencies — uses plain substring matching.
"""

from typing import Dict, List

# keyword → ISO country code (longer phrases before short ones to avoid false
# positives — e.g. "UK" appearing inside "ukukule" should not match)
_COUNTRY_KEYWORDS: Dict[str, List[str]] = {
    "AE": [
        "united arab emirates",
        "uae",
        "dubai",
        "abu dhabi",
        "sharjah",
        "ajman",
        "emirates",
        "emirati",
        "ras al khaimah",
    ],
    "SG": [
        "singapore",
        " sg ",         # space-padded to avoid matching e.g. "msg"
        "singaporean",
    ],
    "GB": [
        "united kingdom",
        "great britain",
        "britain",
        "british",
        "london",
        "england",
        "scotland",
        "wales",
        " uk ",         # space-padded
    ],
    "US": [
        "united states of america",
        "united states",
        "usa",
        "america",
        "american",
    ],
    "AU": [
        "australia",
        "australian",
        "sydney",
        "melbourne",
        "brisbane",
    ],
    "CA": [
        "canada",
        "canadian",
        "toronto",
        "vancouver",
    ],
}


def detect_country(text: str, default: str = "IN") -> str:
    """
    Scan *text* for country-specific keywords and return the ISO country code.

    Evaluation order is fixed (AE, SG, GB, US, AU, CA) so that longer /
    more-specific phrases are checked before ambiguous two-letter codes.

    Returns *default* ("IN") if no match is found, preserving backward
    compatibility with callers that always want India unless explicitly stated.
    """
    if not text:
        return default

    text_lower = " " + text.lower() + " "   # pad so " uk " boundary check works

    for country_code, keywords in _COUNTRY_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return country_code

    return default
