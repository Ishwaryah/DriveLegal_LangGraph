"""Normalize AI tool inputs to match fines.db / rules.json conventions.

This module is the single source of truth for all lookup tables shared across
the agent, router, and rules modules. Import from here rather than re-defining
the same dicts elsewhere.
"""

from __future__ import annotations

# Plain-language offence phrases → offence_code in SQLite
OFFENCE_ALIASES: dict[str, str] = {
    "no helmet": "NO_HELMET",
    "helmet": "NO_HELMET",
    "without helmet": "NO_HELMET",
    "no license": "NO_LICENSE",
    "no licence": "NO_LICENSE",
    "driving without license": "NO_LICENSE",
    "speeding": "SPEED_EXCESS",
    "over speeding": "SPEED_EXCESS",
    "speed excess": "SPEED_EXCESS",
    "drunk driving": "DRUNK_DRIVING",
    "drink driving": "DRUNK_DRIVING",
    "dui": "DRUNK_DRIVING",
    "no insurance": "NO_INSURANCE",
    "mobile phone": "MOBILE_PHONE",
    "phone while driving": "MOBILE_PHONE",
    "red light": "RED_LIGHT_JUMPING",
    "jumping red light": "RED_LIGHT_JUMPING",
    "seatbelt": "NO_SEATBELT",
    "no seatbelt": "NO_SEATBELT",
}

VEHICLE_CLASS_MAP: dict[str, str] = {
    "2W": "TWO_WHEELER",
    "TWO WHEELER": "TWO_WHEELER",
    "TWO-WHEELER": "TWO_WHEELER",
    "BIKE": "TWO_WHEELER",
    "MOTORCYCLE": "TWO_WHEELER",
    "SCOOTER": "TWO_WHEELER",
    "LMV": "LMV",
    "CAR": "LMV",
    "HGV": "HGV",
    "TRUCK": "HGV",
    "BUS": "HGV",
    "3W": "3W",
    "AUTO": "3W",
    "GENERAL": "GENERAL",
    "ALL": "ALL",
}

STATE_MAP: dict[str, str] = {
    "TAMIL NADU": "TN",
    "TAMILNADU": "TN",
    "DELHI": "DL",
    "NCT OF DELHI": "DL",
    "MAHARASHTRA": "MH",
    "KARNATAKA": "KA",
    "KERALA": "KL",
    "ANDHRA PRADESH": "AP",
    "TELANGANA": "TS",
    "WEST BENGAL": "WB",
    "GUJARAT": "GJ",
    "RAJASTHAN": "RJ",
    "UTTAR PRADESH": "UP",
    "PUNJAB": "PB",
    "HARYANA": "HR",
    "ODISHA": "OR",
    "BIHAR": "BR",
    "MADHYA PRADESH": "MP",
    # International regions/states
    "CALIFORNIA": "CALIFORNIA",
    "NEW YORK": "NEW_YORK",
    "TEXAS": "TEXAS",
    "ABU DHABI": "ABU_DHABI",
    "ABUDHABI": "ABU_DHABI",
}


# ─── Country detection ────────────────────────────────────────────────────────

COUNTRY_ALIASES: dict[str, str] = {
    "india": "IN",
    "indian": "IN",
    "bharat": "IN",
    "dubai": "AE",
    "uae": "AE",
    "abu dhabi": "AE",
    "abudhabi": "AE",
    "united arab emirates": "AE",
    "emirates": "AE",
    "sharjah": "AE",
    "ajman": "AE",
    "uk": "GB",
    "united kingdom": "GB",
    "england": "GB",
    "britain": "GB",
    "great britain": "GB",
    "london": "GB",
    "scotland": "GB",
    "wales": "GB",
    "usa": "US",
    "us": "US",
    "united states": "US",
    "america": "US",
    "california": "US",
    "new york": "US",
    "texas": "US",
    "florida": "US",
    "los angeles": "US",
    "san francisco": "US",
    "nyc": "US",
    "houston": "US",
    "dallas": "US",
    "minnesota": "US",
    "singapore": "SG",
    "spore": "SG",
    "saudi": "SA",
    "saudi arabia": "SA",
    "ksa": "SA",
    "riyadh": "SA",
    "jeddah": "SA",
}

# Map country codes to state defaults (when user says 'dubai' we know state=DUBAI, country=AE)
COUNTRY_STATE_MAP: dict[str, str] = {
    "dubai": "DUBAI",
    "abu dhabi": "ABU_DHABI",
    "abudhabi": "ABU_DHABI",
    "sharjah": "ALL",
    "california": "CALIFORNIA",
    "los angeles": "CALIFORNIA",
    "san francisco": "CALIFORNIA",
    "new york": "NEW_YORK",
    "nyc": "NEW_YORK",
    "texas": "TEXAS",
    "houston": "TEXAS",
    "dallas": "TEXAS",
    "london": "ALL",
}

CURRENCY_MAP: dict[str, str] = {
    "IN": "INR",
    "AE": "AED",
    "GB": "GBP",
    "US": "USD",
    "SG": "SGD",
    "SA": "SAR",
}

CURRENCY_SYMBOL: dict[str, str] = {
    "INR": "₹",
    "AED": "AED ",
    "GBP": "£",
    "USD": "$",
    "SGD": "S$",
    "SAR": "SAR ",
}

# Convenience map used when building /fines/countries responses
COUNTRY_NAMES: dict[str, str] = {
    "IN": "India",
    "AE": "UAE",
    "GB": "United Kingdom",
    "SG": "Singapore",
    "SA": "Saudi Arabia",
    "US": "United States",
}

# City / shorthand (lowercase) → canonical full state name used in fines.db
CITY_TO_STATE: dict[str, str] = {
    "tn": "Tamil Nadu",        "tamilnadu": "Tamil Nadu",    "chennai": "Tamil Nadu",
    "coimbatore": "Tamil Nadu", "madurai": "Tamil Nadu",
    "dl": "Delhi",             "delhi": "Delhi",             "new delhi": "Delhi",
    "mh": "Maharashtra",       "maharashtra": "Maharashtra", "mumbai": "Maharashtra",
    "pune": "Maharashtra",     "nagpur": "Maharashtra",
    "ka": "Karnataka",         "karnataka": "Karnataka",     "bangalore": "Karnataka",
    "bengaluru": "Karnataka",  "mysuru": "Karnataka",
    "kl": "Kerala",            "kerala": "Kerala",           "kochi": "Kerala",
    "thiruvananthapuram": "Kerala",
    "up": "Uttar Pradesh",     "lucknow": "Uttar Pradesh",   "noida": "Uttar Pradesh",
    "agra": "Uttar Pradesh",
    "gj": "Gujarat",           "gujarat": "Gujarat",         "ahmedabad": "Gujarat",
    "surat": "Gujarat",
    "rj": "Rajasthan",         "rajasthan": "Rajasthan",     "jaipur": "Rajasthan",
    "wb": "West Bengal",       "kolkata": "West Bengal",     "west bengal": "West Bengal",
    "tg": "Telangana",         "ts": "Telangana",            "telangana": "Telangana",
    "hyderabad": "Telangana",
    "ap": "Andhra Pradesh",    "andhra pradesh": "Andhra Pradesh",
    "br": "Bihar",             "bihar": "Bihar",             "patna": "Bihar",
    "hr": "Haryana",           "haryana": "Haryana",         "gurugram": "Haryana",
    "mp": "Madhya Pradesh",    "madhya pradesh": "Madhya Pradesh",
    "or": "Odisha",            "od": "Odisha",               "odisha": "Odisha",
    "pb": "Punjab",            "punjab": "Punjab",           "chandigarh": "Punjab",
    "as": "Assam",             "assam": "Assam",             "guwahati": "Assam",
    "cg": "Chhattisgarh",      "chhattisgarh": "Chhattisgarh",
    "jh": "Jharkhand",         "jharkhand": "Jharkhand",
    "uk": "Uttarakhand",       "uttarakhand": "Uttarakhand",
    "hp": "Himachal Pradesh",  "himachal pradesh": "Himachal Pradesh",
    "goa": "Goa",              "ga": "Goa",
}


def normalize_offence_code(offence_type: str) -> str:
    raw = (offence_type or "").strip()
    if not raw:
        return ""
    key = raw.lower().replace("-", " ").replace("_", " ")
    if key in OFFENCE_ALIASES:
        return OFFENCE_ALIASES[key]
    return raw.upper().replace(" ", "_").replace("-", "_")


def normalize_vehicle_class(vehicle_class: str) -> str:
    vc = (vehicle_class or "GENERAL").strip().upper().replace("-", " ")
    return VEHICLE_CLASS_MAP.get(vc, vc.replace(" ", "_"))


def normalize_state(state: str) -> str:
    s = (state or "ALL").strip().upper()
    if s in ("ALL", "ANY", "INDIA", "NATIONAL"):
        return "ALL"
    if len(s) <= 3 and s.isalpha():
        return s
    compact = s.replace(" ", "")
    if compact in STATE_MAP:
        return STATE_MAP[compact]
    return STATE_MAP.get(s, s)


def detect_country(text: str) -> str:
    """Detect country code from user text. Returns ISO 2-letter code or 'IN' default."""
    lower = (text or "").lower()
    for alias in sorted(COUNTRY_ALIASES.keys(), key=len, reverse=True):
        if alias in lower:
            return COUNTRY_ALIASES[alias]
    return "IN"


def detect_country_and_state(text: str) -> tuple[str, str]:
    """Detect both country code and state/region from user text."""
    lower = (text or "").lower()
    country = "IN"
    state = "ALL"

    for region in sorted(COUNTRY_STATE_MAP.keys(), key=len, reverse=True):
        if region in lower:
            state = COUNTRY_STATE_MAP[region]
            country = detect_country(region)
            return country, state

    for alias in sorted(COUNTRY_ALIASES.keys(), key=len, reverse=True):
        if alias in lower:
            country = COUNTRY_ALIASES[alias]
            return country, "ALL"

    return country, state


def get_currency_symbol(country: str) -> str:
    """Get currency symbol for display in responses."""
    currency = CURRENCY_MAP.get(country, "INR")
    return CURRENCY_SYMBOL.get(currency, currency + " ")


def get_currency_code(country: str) -> str:
    """Get ISO currency code for a country."""
    return CURRENCY_MAP.get(country, "INR")
