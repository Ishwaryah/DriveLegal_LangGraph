"""
DriveLegal Agent Tools
======================
Defines Gemini-compatible tool declarations and the ToolExecutor that bridges
function calls from the Gemini model to the backend modules (FineLookup,
RulesLoader, GeofencingEngine).
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Tool Declarations (Gemini FunctionDeclaration schema)
# ─────────────────────────────────────────────────────────────────────────────

TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "lookup_fine",
        "description": (
            "Retrieve the exact penalty/fine amount for a traffic violation "
            "in India. Queries the official Motor Vehicles Act database. "
            "Use this whenever the user asks about challan amounts, penalties, "
            "or fines for a specific offence."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "offence_type": {
                    "type": "string",
                    "description": (
                        "Standardised offence code in UPPER_SNAKE_CASE. "
                        "Examples: NO_HELMET, DRUNK_DRIVING, SPEED_EXCESS, "
                        "RED_LIGHT_JUMPING, NO_LICENSE, NO_INSURANCE, "
                        "MOBILE_PHONE, NO_SEATBELT, WRONG_WAY, DANGEROUS_DRIVING."
                    ),
                },
                "vehicle_class": {
                    "type": "string",
                    "description": (
                        "Vehicle class. One of: TWO_WHEELER, LMV, HGV, 3W, GENERAL. "
                        "Infer from user context: bike/scooter → TWO_WHEELER, "
                        "car/SUV → LMV, truck/bus → HGV."
                    ),
                    "enum": ["TWO_WHEELER", "LMV", "HGV", "3W", "GENERAL"],
                },
                "state": {
                    "type": "string",
                    "description": (
                        "Indian state name (e.g. 'Tamil Nadu', 'Delhi', 'Maharashtra'). "
                        "Use 'ALL' when the user has not mentioned a state."
                    ),
                },
                "is_repeat": {
                    "type": "boolean",
                    "description": "True if this is a repeat/subsequent offence.",
                },
            },
            "required": ["offence_type"],
        },
    },
    {
        "name": "lookup_rule",
        "description": (
            "Retrieve the legal rule and Motor Vehicles Act section for a "
            "traffic violation. Returns the rule title, section number, full "
            "description, and imprisonment details if applicable. Use when "
            "the user asks what the law says about a specific offence."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "offence_code": {
                    "type": "string",
                    "description": (
                        "Offence code in UPPER_SNAKE_CASE, e.g. NO_HELMET, "
                        "DRUNK_DRIVING. Also accepts a Section reference like "
                        "'Section 185' or a rule ID like 'MV185'."
                    ),
                },
                "state": {
                    "type": "string",
                    "description": "State for state-specific rule overrides (optional).",
                },
            },
            "required": ["offence_code"],
        },
    },
    {
        "name": "check_zone",
        "description": (
            "Check what traffic zone restrictions are active at the user's "
            "current GPS location. Returns active zones (school zone, "
            "no-horn zone, speed camera zone) and their applicable rules. "
            "Use when GPS coordinates are available or the user asks about "
            "local restrictions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "lat": {
                    "type": "number",
                    "description": "GPS latitude of the user's location.",
                },
                "lon": {
                    "type": "number",
                    "description": "GPS longitude of the user's location.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "search_rules",
        "description": (
            "Search the traffic rules database by keywords when you don't "
            "know the exact offence code. Returns the most relevant rules "
            "with their sections and descriptions. Use as a fallback when "
            "the specific offence code is uncertain."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of search keywords, e.g. ['helmet', 'pillion', 'fine'].",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default 3).",
                },
            },
            "required": ["keywords"],
        },
    },
    {
        "name": "suggest_offence_categories",
        "description": (
            "Suggest the closest standard traffic offence categories/codes based on a natural language "
            "description of a violation. Use this when the user describes a violation in terms that do not "
            "directly match standard codes (e.g., 'driving too fast', 'forgot my papers', 'riding three people on a bike'). "
            "Returns a list of recommended standardised offence codes to be used with lookup_fine."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Natural language description of the traffic violation or scenario.",
                },
            },
            "required": ["description"],
        },
    },
    {
        "name": "get_location_info",
        "description": (
            "Retrieves the readable address based on the user's GPS coordinates. "
            "Use this when the user asks 'where am I located' or 'what is my location'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "lat": {
                    "type": "number",
                    "description": "GPS latitude of the user's location.",
                },
                "lon": {
                    "type": "number",
                    "description": "GPS longitude of the user's location.",
                },
            },
            "required": ["lat", "lon"],
        },
    },
    {
        "name": "get_emergency_info",
        "description": (
            "Retrieves emergency contacts, nearest police stations, hospitals/trauma centers, and highway helplines. "
            "Use this when the user asks for emergency numbers, highway helplines, or nearest police/hospitals."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "lat": {
                    "type": "number",
                    "description": "GPS latitude of the user's location.",
                },
                "lon": {
                    "type": "number",
                    "description": "GPS longitude of the user's location.",
                },
            },
            "required": [],
        },
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# NLP → DB code mapping
# Maps NLP agent offence codes to the actual offence_code values stored in
# fines.db (case-insensitive UPPER() matching is used in FineLookup.query,
# so exact case doesn't matter — but the *name* must match what the DB has).
# ─────────────────────────────────────────────────────────────────────────────

_OFFENCE_TO_DB = {
    # Direct matches (DB stores same code as NLP)
    "NO_HELMET":             "NO_HELMET",
    "DRUNK_DRIVING":         "DRUNK_DRIVING",
    "SPEED_EXCESS":          "SPEED_EXCESS",          # DB: SPEED_EXCESS (not 'overspeeding')
    "RED_LIGHT_JUMPING":     "RED_LIGHT_JUMPING",     # DB: RED_LIGHT_JUMPING (not 'signal_jumping')
    "NO_LICENSE":            "NO_LICENSE",
    "NO_INSURANCE":          "NO_INSURANCE",
    "MOBILE_PHONE":          "MOBILE_PHONE",           # DB: MOBILE_PHONE (not 'using_phone')
    "NO_SEATBELT":           "NO_SEATBELT",
    "WRONG_WAY":             "WRONG_WAY",
    "WRONG_SIDE":            "WRONG_WAY",              # DB uses WRONG_WAY for wrong-side driving
    # Newly added offence codes
    "NO_PUC":                "NO_PUC",                 # Direct DB code
    "TRIPLE_RIDING":         "SECTION_194C",           # DB: SECTION_194C
    "NO_NUMBER_PLATE":       "SECTION_192",            # Sec 192: no registration/plate
    "JUVENILE_DRIVING":      "JUVENILE_DRIVING",       # Direct DB code (added by patch)
    "TINTED_GLASS":          "TINTED_GLASS",           # Direct DB code
    "VEHICLE_MODIFICATION":  "VEHICLE_MODIFICATION",   # Direct DB code
    "HIGH_BEAM":             "SECTION_177",            # General rule violation under Sec 177
    "HORN_HONKING":          "SECTION_177",            # Noise/horn rule violation
    # Section-based codes that exist in DB
    "DANGEROUS_DRIVING":     "SECTION_184",
    "STUNT_DRIVING":         "SECTION_189",
    "EMERGENCY_OBSTRUCTION": "SECTION_194E",
    "DISOBEY_POLICE":        "SECTION_179",
    "OVERLOADING":           "SECTION_194",
    "PUC_VIOLATION":         "NO_PUC",                 # Alias → NO_PUC
    "PARKING_VIOLATION":     "NO_PARKING",             # DB: NO_PARKING
    "WRONG_OVERTAKING":      "SECTION_184",
    "ROAD_RAGE":             "SECTION_184",
    # Section code passthrough aliases
    "SECTION_177":           "SECTION_177",
    "SECTION_177A":          "SECTION_177A",
    "SECTION_178":           "SECTION_178",
    "SECTION_179":           "SECTION_179",
    "SECTION_180":           "SECTION_180",
    "SECTION_181":           "SECTION_181",
    "SECTION_182":           "SECTION_182",
    "SECTION_182A":          "SECTION_182A",
    "SECTION_183":           "SECTION_183",
    "SECTION_184":           "SECTION_184",
    "SECTION_185":           "SECTION_185",
    "SECTION_186":           "SECTION_186",
    "SECTION_189":           "SECTION_189",
    "SECTION_192":           "SECTION_192",
    "SECTION_192A":          "SECTION_192A",
    "SECTION_194":           "SECTION_194",
    "SECTION_194A":          "SECTION_194A",
    "SECTION_194B":          "SECTION_194B",
    "SECTION_194C":          "SECTION_194C",
    "SECTION_194D":          "SECTION_194D",
    "SECTION_194E":          "SECTION_194E",
    "SECTION_194F":          "SECTION_194F",
    "SECTION_196":           "SECTION_196",
    "SECTION_199":           "SECTION_199",
    "SECTION_206":           "SECTION_206",
}

_VEHICLE_TO_DB = {
    # The DB stores: 'ALL', 'LMV', '2W', 'TWO_WHEELER', 'HGV', 'HGV/MGV', '3W', 'COMMERCIAL'
    # FineLookup.query handles multi-variant matching via _VEHICLE_ALIASES, so
    # just pass a recognised form and let lookup.py expand it.
    "TWO_WHEELER": "TWO_WHEELER",
    "2W":          "2W",
    "LMV":         "LMV",
    "HGV":         "HGV",
    "HMV":         "HGV",
    "3W":          "3W",
    "GENERAL":     "ALL",
}


# ─────────────────────────────────────────────────────────────────────────────
# ToolExecutor
# ─────────────────────────────────────────────────────────────────────────────

class ToolExecutor:
    """
    Bridges Gemini function-call names → backend module method calls.
    All handlers return plain dicts (JSON-serialisable).
    """

    def __init__(self, fine_lookup, rules_loader, geofencing_engine, hybrid_search=None):
        self.fine_lookup = fine_lookup
        self.rules_loader = rules_loader
        self.geofencing = geofencing_engine
        self.hybrid_search = hybrid_search

    def execute(
        self,
        tool_name: str,
        params: Dict[str, Any],
        gps: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        handlers = {
            "lookup_fine":   self._lookup_fine,
            "lookup_rule":   self._lookup_rule,
            "check_zone":    self._check_zone,
            "search_rules":  self._search_rules,
            "suggest_offence_categories": self._suggest_offence_categories,
            "get_location_info": self._get_location_info,
            "get_emergency_info": self._get_emergency_info,
        }
        handler = handlers.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}
        try:
            return handler(params, gps)
        except Exception as e:
            logger.error("[ToolExecutor] %s error: %s", tool_name, e)
            return {"error": str(e), "tool": tool_name}

    # ── lookup_fine ───────────────────────────────────────────────────────────

    # City/shorthand → canonical state name used in the DB
    _STATE_ALIASES: Dict[str, str] = {
        "tn": "Tamil Nadu",        "tamilnadu": "Tamil Nadu",   "chennai": "Tamil Nadu",
        "coimbatore": "Tamil Nadu", "madurai": "Tamil Nadu",
        "dl": "Delhi",             "delhi": "Delhi",            "new delhi": "Delhi",
        "mh": "Maharashtra",       "maharashtra": "Maharashtra","mumbai": "Maharashtra",
        "pune": "Maharashtra",     "nagpur": "Maharashtra",
        "ka": "Karnataka",         "karnataka": "Karnataka",    "bangalore": "Karnataka",
        "bengaluru": "Karnataka",  "mysuru": "Karnataka",
        "kl": "Kerala",            "kerala": "Kerala",          "kochi": "Kerala",
        "thiruvananthapuram": "Kerala",
        "up": "Uttar Pradesh",     "lucknow": "Uttar Pradesh",  "noida": "Uttar Pradesh",
        "agra": "Uttar Pradesh",
        "gj": "Gujarat",           "gujarat": "Gujarat",        "ahmedabad": "Gujarat",
        "surat": "Gujarat",
        "rj": "Rajasthan",         "rajasthan": "Rajasthan",    "jaipur": "Rajasthan",
        "wb": "West Bengal",       "kolkata": "West Bengal",    "west bengal": "West Bengal",
        "tg": "Telangana",         "ts": "Telangana",           "telangana": "Telangana",
        "hyderabad": "Telangana",
        "ap": "Andhra Pradesh",    "andhra pradesh": "Andhra Pradesh",
        "br": "Bihar",             "bihar": "Bihar",            "patna": "Bihar",
        "hr": "Haryana",           "haryana": "Haryana",        "gurugram": "Haryana",
        "mp": "Madhya Pradesh",    "madhya pradesh": "Madhya Pradesh",
        "or": "Odisha",            "od": "Odisha",              "odisha": "Odisha",
        "pb": "Punjab",            "punjab": "Punjab",          "chandigarh": "Punjab",
        "as": "Assam",             "assam": "Assam",            "guwahati": "Assam",
        "cg": "Chhattisgarh",      "chhattisgarh": "Chhattisgarh",
        "jh": "Jharkhand",         "jharkhand": "Jharkhand",
        "uk": "Uttarakhand",       "uttarakhand": "Uttarakhand",
        "hp": "Himachal Pradesh",  "himachal pradesh": "Himachal Pradesh",
        "goa": "Goa",              "ga": "Goa",
    }

    def _lookup_fine(self, params: Dict, _gps: Optional[Dict]) -> Dict:
        if not self.fine_lookup:
            return {"found": False, "error": "Fine database not available."}

        offence_raw = (params.get("offence_type") or "").strip()
        vehicle_raw = (params.get("vehicle_class") or "GENERAL").strip()
        state_raw   = (params.get("state") or "ALL").strip()
        is_repeat   = bool(params.get("is_repeat", False))

        if not offence_raw:
            return {"found": False, "error": "offence_type is required"}

        # Map offence to DB code (identity if already a DB code; use raw value as
        # fallback so novel but valid codes are still attempted against the DB).
        offence_db = _OFFENCE_TO_DB.get(offence_raw.upper(), offence_raw.upper())
        if offence_raw.upper() not in _OFFENCE_TO_DB:
            logger.warning("[ToolExecutor] Unrecognised offence_type '%s' — trying DB lookup anyway.", offence_raw)

        # Map vehicle class
        vehicle_db = _VEHICLE_TO_DB.get(vehicle_raw.upper(), vehicle_raw.upper())

        # Normalise state: city/shorthand → full state name
        state_clean = state_raw.strip().lower()
        if state_clean in self._STATE_ALIASES:
            state_norm = self._STATE_ALIASES[state_clean]
        elif state_raw.upper() in ("ALL", "ANY", "NATIONAL", ""):
            state_norm = "ALL"
        else:
            # Title-case for full names like "Tamil Nadu" that Groq sends correctly
            state_norm = state_raw.strip().title()

        state_for_lookup = "" if state_norm in ("ALL", "ANY", "NATIONAL") else state_norm

        # Accept country + intl_state directly from params (set by _keyword_fallback country detection)
        country_param   = (params.get("country") or "IN").strip().upper()
        intl_state_raw  = (params.get("intl_state") or "").strip()

        # For international queries, intl_state overrides the normal state resolution
        if country_param != "IN" and intl_state_raw:
            state_for_lookup = intl_state_raw if intl_state_raw not in ("ALL", "") else ""

        result = self.fine_lookup.query(
            offence_code  = offence_db,
            vehicle_class = vehicle_db,
            state         = state_for_lookup,
            country       = country_param,
            repeat        = is_repeat,
        )

        if result:
            return {
                "found":             True,
                "amount_inr":        result["amount_inr"],
                "repeat_amount_inr": result.get("repeat_amount_inr"),
                "section_ref":       result.get("section_ref"),
                "currency":          result.get("currency", "INR"),
                "notes":             result.get("notes"),
                "state":             state_norm if state_for_lookup else "National",
                "vehicle_class":     vehicle_raw,
            }

        return {
            "found":   False,
            "message": f"No fine data found for offence '{offence_raw}' in the database.",
        }

    # ── lookup_rule ───────────────────────────────────────────────────────────

    def _lookup_rule(self, params: Dict, gps: Optional[Dict]) -> Dict:
        if not self.rules_loader:
            return {"found": False, "error": "Rules database not available."}

        code  = params.get("offence_code", "").strip()
        state = params.get("state")

        # Try exact offence code first
        rule = self.rules_loader.get_by_offence_code(code.upper(), state=state)

        # Try section reference (e.g. "Section 185")
        if not rule and "section" in code.lower():
            rule = self.rules_loader.get_by_section(code)

        # Try rule ID (e.g. "MV185")
        if not rule:
            rule = self.rules_loader.get_by_rule_id(code.upper())

        # Keyword fallback via tags/lexical search
        if not rule:
            tokens = code.lower().replace("_", " ").split()
            matches = self.rules_loader.search(tokens)
            rule = matches[0] if matches else None

        if not rule:
            return {"found": False, "message": f"No rule found for '{code}'."}

        return {
            "found":       True,
            "rule_id":     rule.get("rule_id"),
            "title":       rule.get("title"),
            "section":     rule.get("section"),
            "description": rule.get("description"),
            "compoundable": rule.get("compoundable", False),
            "imprisonment": rule.get("imprisonment"),
            "tags":        rule.get("tags", []),
        }

    # ── check_zone ────────────────────────────────────────────────────────────

    def _check_zone(self, params: Dict, gps: Optional[Dict]) -> Dict:
        lat = params.get("lat") or (gps.get("lat") if gps else None)
        lon = params.get("lon") or (gps.get("lon") if gps else None)

        if lat is None or lon is None:
            return {"found": False, "message": "GPS coordinates not available."}

        if not self.geofencing:
            return {"found": False, "error": "Geofencing engine not available."}

        try:
            zones = self.geofencing.detect_zones(float(lat), float(lon))
        except Exception as e:
            return {"found": False, "error": str(e)}

        if not zones:
            return {"found": False, "message": "No special traffic zones detected at this location."}

        return {
            "found": True,
            "zones": [
                {
                    "name":            (z.get("name") or z.get("zone_id") or "Unknown Zone"),
                    "zone_type":       z.get("zone_type"),
                    "fine_multiplier": z.get("fine_multiplier", 1.0),
                    "active_hours":    z.get("active_hours", "ALL"),
                    # Accept either "rules" (old schema) or "offences" (new hospital schema)
                    "rules":           z.get("rules") or z.get("offences") or [],
                    "description":     z.get("description", ""),
                    "speed_limit_kmh": z.get("speed_limit_kmh"),
                }
                for z in zones
            ],
        }

    # ── search_rules ──────────────────────────────────────────────────────────

    def _search_rules(self, params: Dict, gps: Optional[Dict]) -> Dict:
        if not self.rules_loader:
            return {"found": False, "error": "Rules database not available."}

        keywords = params.get("keywords", [])
        top_k    = int(params.get("top_k", 3))

        if not keywords:
            return {"found": False, "message": "No keywords provided."}

        matches = self.rules_loader.search(keywords)[:top_k]

        if not matches:
            return {"found": False, "message": f"No rules found for keywords: {keywords}"}

        return {
            "found": True,
            "rules": [
                {
                    "rule_id":     r.get("rule_id"),
                    "title":       r.get("title"),
                    "section":     r.get("section"),
                    "description": (r.get("description") or "")[:300],
                    "tags":        r.get("tags", []),
                }
                for r in matches
            ],
        }

    # ── suggest_offence_categories ────────────────────────────────────────────

    def _suggest_offence_categories(self, params: Dict, gps: Optional[Dict]) -> Dict:
        description = params.get("description", "").strip()
        if not description:
            return {"found": False, "message": "No description provided."}

        suggestions = []
        seen_codes = set()

        # 1. Direct keyword checking for quick high-confidence matching
        keyword_mappings = {
            "helmet": ("NO_HELMET", "Riding without a helmet"),
            "pillion": ("NO_HELMET", "Riding without a helmet"),
            "drunk": ("DRUNK_DRIVING", "Drunk driving / driving under the influence"),
            "drink": ("DRUNK_DRIVING", "Drunk driving / driving under the influence"),
            "alcohol": ("DRUNK_DRIVING", "Drunk driving / driving under the influence"),
            "speed": ("SPEED_EXCESS", "Overspeeding / exceeding speed limits"),
            "fast": ("SPEED_EXCESS", "Overspeeding / exceeding speed limits"),
            "license": ("NO_LICENSE", "Driving without a valid license"),
            "licence": ("NO_LICENSE", "Driving without a valid license"),
            "insurance": ("NO_INSURANCE", "Driving a vehicle without insurance"),
            "seatbelt": ("NO_SEATBELT", "Driving or riding without a seatbelt"),
            "seat belt": ("NO_SEATBELT", "Driving or riding without a seatbelt"),
            "phone": ("MOBILE_PHONE", "Using a mobile phone while driving"),
            "mobile": ("MOBILE_PHONE", "Using a mobile phone while driving"),
            "call": ("MOBILE_PHONE", "Using a mobile phone while driving"),
            "red light": ("RED_LIGHT_JUMPING", "Jumping a red light / traffic signal"),
            "signal": ("RED_LIGHT_JUMPING", "Jumping a red light / traffic signal"),
            "wrong way": ("WRONG_WAY", "Driving against the designated flow of traffic (wrong way)"),
            "wrong side": ("WRONG_SIDE", "Driving on the wrong side of the road"),
            "triple": ("TRIPLE_RIDING", "Triple riding on a two-wheeler"),
            "three people": ("TRIPLE_RIDING", "Triple riding on a two-wheeler"),
            "3 people": ("TRIPLE_RIDING", "Triple riding on a two-wheeler"),
            "glass": ("TINTED_GLASS", "Using tinted glass / dark film on windows"),
            "tinted": ("TINTED_GLASS", "Using tinted glass / dark film on windows"),
            "modification": ("VEHICLE_MODIFICATION", "Illegal vehicle modification"),
            "modified": ("VEHICLE_MODIFICATION", "Illegal vehicle modification"),
            "park": ("PARKING_VIOLATION", "Parking in a no-parking zone / illegal parking"),
            "puc": ("PUC_VIOLATION", "Driving without a valid PUC (Pollution Under Control) certificate"),
            "pollution": ("PUC_VIOLATION", "Driving without a valid PUC certificate"),
            "rc": ("NO_RC", "Driving without a valid Registration Certificate (RC)"),
            "registration": ("NO_RC", "Driving without a valid Registration Certificate (RC)"),
            "juvenile": ("JUVENILE_DRIVING", "Driving by a minor / juvenile driving"),
            "minor": ("JUVENILE_DRIVING", "Driving by a minor / juvenile driving"),
            "underage": ("JUVENILE_DRIVING", "Driving by a minor / juvenile driving"),
            "stunt": ("STUNT_DRIVING", "Dangerous stunt driving or racing"),
            "racing": ("STUNT_DRIVING", "Dangerous stunt driving or racing"),
            "ambulance": ("EMERGENCY_OBSTRUCTION", "Obstruction of emergency vehicles (ambulance, fire engine)"),
            "emergency": ("EMERGENCY_OBSTRUCTION", "Obstruction of emergency vehicles"),
            "police": ("DISOBEY_POLICE", "Disobeying lawful directions of a police officer"),
            "disobey": ("DISOBEY_POLICE", "Disobeying lawful directions of a police officer"),
            "overload": ("OVERLOADING", "Overloading of passenger or goods vehicle"),
            "excess weight": ("OVERLOADING", "Overloading of passenger or goods vehicle"),
            "rash": ("DANGEROUS_DRIVING", "Dangerous / rash driving"),
            "reckless": ("DANGEROUS_DRIVING", "Dangerous / rash driving"),
            "rage": ("ROAD_RAGE", "Road rage or violent behaviour on roads"),
            "suspended": ("SUSPENDED_LICENCE", "Driving with a suspended or cancelled license"),
        }

        desc_lower = description.lower()
        for kw, (code, title) in keyword_mappings.items():
            if kw in desc_lower:
                if code not in seen_codes:
                    suggestions.append({
                        "offence_code": code,
                        "title": title,
                        "confidence": "HIGH"
                    })
                    seen_codes.add(code)

        # 2. Use HybridSearch to retrieve semantic/lexical matches
        if hasattr(self, "hybrid_search") and self.hybrid_search:
            try:
                search_results = self.hybrid_search.search(description, top_k=5)
                for r in search_results:
                    rule_id = r.get("rule_id", "")
                    if rule_id and self.rules_loader:
                        rule = self.rules_loader.get_by_rule_id(rule_id)
                        if rule:
                            related_codes = rule.get("related_offence_codes", [])
                            for c in related_codes:
                                if c and c.upper() not in seen_codes:
                                    title = rule.get("title", f"Related to {c}")
                                    suggestions.append({
                                        "offence_code": c.upper(),
                                        "title": title,
                                        "confidence": "MEDIUM"
                                    })
                                    seen_codes.add(c.upper())
            except Exception as e:
                logger.error("Hybrid search in suggest_offence_categories failed: %s", e)

        # 3. Fallback popular ones
        if not suggestions:
            popular = [
                ("NO_HELMET", "Riding without a helmet"),
                ("SPEED_EXCESS", "Overspeeding"),
                ("DRUNK_DRIVING", "Drunk driving"),
                ("NO_LICENSE", "Driving without license"),
                ("RED_LIGHT_JUMPING", "Jumping red light"),
            ]
            for code, title in popular:
                suggestions.append({
                    "offence_code": code,
                    "title": title,
                    "confidence": "LOW"
                })

        return {
            "found": True,
            "suggestions": suggestions[:5]
        }

    # ── get_location_info ────────────────────────────────────────────────────────
    
    def _get_location_info(self, params: Dict, gps: Optional[Dict]) -> Dict:
        lat = params.get("lat") or (gps.get("lat") if gps else None)
        lon = params.get("lon") or (gps.get("lon") if gps else None)

        if lat is None or lon is None:
            return {"found": False, "message": "GPS coordinates not available to determine location."}

        try:
            import urllib.request
            import json
            url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
            req = urllib.request.Request(url, headers={'User-Agent': 'DriveLegal/2.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                address = data.get("display_name", "Unknown address")
                return {"found": True, "address": address, "details": data.get("address", {})}
        except Exception as e:
            logger.error("[ToolExecutor] Reverse geocoding error: %s", e)
            return {"found": False, "error": f"Failed to fetch address: {str(e)}"}

    # ── get_emergency_info ───────────────────────────────────────────────────────
    
    def _get_emergency_info(self, params: Dict, gps: Optional[Dict]) -> Dict:
        lat = params.get("lat") or (gps.get("lat") if gps else 0.0)
        lon = params.get("lon") or (gps.get("lon") if gps else 0.0)
        
        try:
            from backend.services.emergency_service import EmergencyService
            svc = EmergencyService()
            report = svc.handle_accident_report(float(lat), float(lon))
            return {"found": True, "emergency_data": report}
        except Exception as e:
            logger.error("[ToolExecutor] Emergency info error: %s", e)
            return {"found": False, "error": str(e)}