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
]


# ─────────────────────────────────────────────────────────────────────────────
# NLP → DB code mapping (mirrors lookup.py)
# ─────────────────────────────────────────────────────────────────────────────

_OFFENCE_TO_DB = {
    "NO_HELMET":               "no_helmet",
    "DRUNK_DRIVING":           "drunk_driving",
    "SPEED_EXCESS":            "overspeeding",
    "RED_LIGHT_JUMPING":       "signal_jumping",
    "NO_LICENSE":              "no_license",
    "NO_INSURANCE":            "no_insurance",
    "MOBILE_PHONE":            "using_phone",
    "NO_SEATBELT":             "no_seatbelt",
    "SECTION_194D":            "no_seatbelt",
    "SECTION_177":             "signal_jumping",
    "SECTION_179":             "wrong_way",
    "SECTION_184":             "dangerous_driving",
    "WRONG_WAY":               "wrong_way",
    "DANGEROUS_DRIVING":       "dangerous_driving",
    "OVERLOADING":             "overloading",
    "NO_RC":                   "no_rc",
    "WRONG_SIDE":              "wrong_side",
    "JUVENILE_DRIVING":        "juvenile_driving",
    "PUC_VIOLATION":           "puc_violation",
    "STUNT_DRIVING":           "stunt_driving",
    "EMERGENCY_OBSTRUCTION":   "not_giving_way_to_emergency",
    "DISOBEY_POLICE":          "disobeying_police",
    "TINTED_GLASS":            "tinted_glass",
    "TRIPLE_RIDING":           "triple_riding",
    "VEHICLE_MODIFICATION":    "vehicle_modification",
    "PARKING_VIOLATION":       "parking_violation",
    "WRONG_OVERTAKING":        "wrong_overtaking",
    "ROAD_RAGE":               "road_rage",
    "SUSPENDED_LICENCE":       "suspended_licence",
}

_VEHICLE_TO_DB = {
    "TWO_WHEELER": "two_wheeler",
    "2W":          "two_wheeler",
    "LMV":         "lmv",
    "HGV":         "hmv",
    "HMV":         "hmv",
    "3W":          "three_wheeler",
    "GENERAL":     "all",
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

    def _lookup_fine(self, params: Dict, gps: Optional[Dict]) -> Dict:
        if not self.fine_lookup:
            return {"found": False, "error": "Fine database not available."}

        offence_raw = params.get("offence_type", "")
        vehicle_raw = params.get("vehicle_class", "GENERAL")
        state       = params.get("state", "ALL")
        is_repeat   = params.get("is_repeat", False)

        # Hallucination Check: Enum validation
        if offence_raw.upper() not in _OFFENCE_TO_DB:
            logger.error("[ToolExecutor] Hallucination Alert: Invalid offence_type enum passed by agent: %s", offence_raw)
            return {"found": False, "error": f"Invalid offence_type enum: {offence_raw}"}

        # Normalize state
        state_mapping = {
            "tn": "Tamil Nadu",
            "tamilnadu": "Tamil Nadu",
            "delhi": "Delhi",
            "dl": "Delhi",
            "new delhi": "Delhi",
            "mh": "Maharashtra",
            "mumbai": "Maharashtra",
            "ka": "Karnataka",
            "bangalore": "Karnataka",
            "bengaluru": "Karnataka",
            "kl": "Kerala",
            "up": "Uttar Pradesh",
            "gj": "Gujarat",
            "rj": "Rajasthan",
            "wb": "West Bengal",
            "tg": "Telangana",
            "ts": "Telangana",
            "ap": "Andhra Pradesh",
            "as": "Assam",
            "br": "Bihar",
            "cg": "Chhattisgarh",
            "hr": "Haryana",
            "jh": "Jharkhand",
            "mp": "Madhya Pradesh",
            "od": "Odisha",
            "pb": "Punjab",
            "uk": "Uttarakhand",
        }
        
        state_clean = state.strip().lower()
        if state_clean in state_mapping:
            state = state_mapping[state_clean]
        elif state not in ("ALL", "ANY", ""):
            state = state.title()

        offence_db = _OFFENCE_TO_DB.get(offence_raw.upper(), offence_raw.lower().replace(" ", "_"))
        vehicle_db = _VEHICLE_TO_DB.get(vehicle_raw.upper(), "all")

        state_arg = None if state in ("ALL", "ANY", "") else state

        result = self.fine_lookup.query(
            offence_code=offence_db,
            vehicle_class=vehicle_db,
            state=state_arg,
        )

        if result:
            amount = result.get("repeat_amount_inr") if is_repeat else result.get("amount_inr")
            return {
                "found":             True,
                "amount_inr":        amount or result.get("amount_inr"),
                "repeat_amount_inr": result.get("repeat_amount_inr"),
                "section_ref":       result.get("section_ref"),
                "currency":          result.get("currency", "INR"),
                "notes":             result.get("notes"),
                "state":             state_arg or "National",
                "vehicle_class":     vehicle_raw,
            }

        # Soft fallback: try national (no state)
        if state_arg:
            result_national = self.fine_lookup.query(
                offence_code=offence_db,
                vehicle_class=vehicle_db,
                state=None,
            )
            if result_national:
                amount = result_national.get("repeat_amount_inr") if is_repeat else result_national.get("amount_inr")
                return {
                    "found":             True,
                    "amount_inr":        amount or result_national.get("amount_inr"),
                    "repeat_amount_inr": result_national.get("repeat_amount_inr"),
                    "section_ref":       result_national.get("section_ref"),
                    "currency":          result_national.get("currency", "INR"),
                    "notes":             result_national.get("notes"),
                    "state":             "National (no state-specific data found)",
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
                    "name":            z.get("name", "Unknown Zone"),
                    "zone_type":       z.get("zone_type"),
                    "fine_multiplier": z.get("fine_multiplier", 1.0),
                    "active_hours":    z.get("active_hours", "ALL"),
                    "rules":           z.get("rules", []),
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