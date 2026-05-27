"""
DriveLegal Agent Engine
=======================
Agentic loop powered by Groq (llama-3.3-70b-versatile) with function calling.

Architecture:
─────────────────────────────────────────────────────────────────────
User message
    │
    ▼
Groq LLM (system prompt + tool declarations)
    │
    ├── Calls: lookup_fine("no_helmet", "TWO_WHEELER", "Tamil Nadu")
    │       └── ToolExecutor._lookup_fine() → SQLite query
    │               └── { amount_inr: 1000, section: "Section 194D" }
    │
    ├── Calls: lookup_rule("NO_HELMET", "Tamil Nadu")
    │       └── ToolExecutor._lookup_rule() → rules.json
    │               └── { title: "Helmet Rule", description: "..." }
    │
    └── Synthesises tool results → natural language response
            └── "The fine for riding without a helmet in Tamil Nadu is ₹1,000
                 under Section 194D of the Motor Vehicles Act 1988..."
    │
    ▼
Structured response returned to caller
─────────────────────────────────────────────────────────────────────

Falls back to HybridSearch + keyword matching if GROQ_API_KEY is absent
or if Groq rate-limits (HTTP 429).

Configuration files (all in the same directory as this module):
  agent_config.json     — model params, keyword lists, thresholds, state/vehicle maps
  offence_keywords.json — per-offence keyword expansion for fallback detector
  system_prompt.txt     — LLM system prompt (edit without touching Python)
"""

import time
import os
import logging
import json
from typing import Any, Dict, List, Optional

from groq import Groq
from pybreaker import CircuitBreakerError

from backend.modules.agent.tools import ToolExecutor, TOOL_DEFINITIONS
from backend.modules.ai.circuit_breaker import ai_circuit_breaker

logger = logging.getLogger(__name__)

# Resolve config directory once at import time
_HERE = os.path.dirname(os.path.abspath(__file__))


# ─────────────────────────────────────────────────────────────────────────────
# Agent Engine
# ─────────────────────────────────────────────────────────────────────────────

class AgentEngine:
    """
    AI agent using Groq with function calling.
    Falls back to HybridSearch + keyword matching when GROQ_API_KEY is unset
    or when Groq is rate-limited.

    All tuneable values live in agent_config.json and offence_keywords.json
    alongside this file — no Python edit required to adjust them.
    """

    def __init__(self, fine_lookup, rules_loader, geofencing_engine):
        self.tool_executor = ToolExecutor(fine_lookup, rules_loader, geofencing_engine)
        self.client = None
        self.groq_available = False
        self.hybrid_search = None

        # ── Load configuration ────────────────────────────────────────────────
        self._cfg = self._load_agent_config()
        self._system_prompt = self._load_system_prompt()
        self._offence_keywords = self._load_offence_keywords()

        # Convenience shortcuts into config sections
        self._groq_cfg    = self._cfg["groq"]
        self._hs_cfg      = self._cfg["hybrid_search"]
        self._guard_cfg   = self._cfg["hallucination_guard"]
        self._fb_cfg      = self._cfg["fallback"]
        self._veh_cfg     = self._cfg["vehicle_types"]
        self._state_cfg   = self._cfg["states"]
        self._oname_cfg   = self._cfg["offence_names"]

        # ── Local NLP fallback (HybridSearch) ────────────────────────────────
        try:
            from backend.modules.nlp.hybrid_search import HybridSearch
            rules_path  = os.path.join(_HERE, "..", "..", "data", "rules.json")
            persist_dir = os.path.join(_HERE, "..", "..", "data", "vector_db")
            self.hybrid_search = HybridSearch(rules_path, persist_dir)
            self.tool_executor.hybrid_search = self.hybrid_search
            logger.info(
                "[AgentEngine] HybridSearch loaded (%d documents).",
                len(self.hybrid_search.documents),
            )
        except Exception as e:
            logger.warning("[AgentEngine] HybridSearch unavailable: %s", e)

        # ── Groq SDK ──────────────────────────────────────────────────────────
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.info("[AgentEngine] GROQ_API_KEY not set — keyword fallback mode.")
            return

        try:
            self.client = Groq(api_key=api_key)
            self.groq_available = True
            logger.info("[AgentEngine] Groq ready (model=%s).", self._groq_cfg["model"])
        except Exception as e:
            logger.error("[AgentEngine] Groq init failed: %s", e)

    # ─────────────────────────────────────────────────────────────────────────
    # Config / data loaders  (all @staticmethod — usable before __init__ ends)
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _load_agent_config() -> Dict[str, Any]:
        """Load agent_config.json; fall back to a safe minimal dict on error."""
        path = os.path.join(_HERE, "agent_config.json")
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            # Strip _comment keys at top level
            return {k: v for k, v in data.items() if not k.startswith("_")}
        except Exception as exc:
            logger.warning("[AgentEngine] Could not load agent_config.json (%s) — using defaults.", exc)
            disclaimer = "⚠️ Informational only. Verify at echallan.parivahan.gov.in."
            return {
                "groq": {
                    "model": "llama-3.3-70b-versatile",
                    "model_label": "groq-llama3",
                    "max_tokens": 1024,
                    "temperature": 0.1,
                    "max_tool_iterations": 5,
                },
                "hybrid_search": {
                    "top_k": 3,
                    "score_threshold": 0.15,
                    "content_max_chars": 400,
                    "rule_query_word_limit": 5,
                },
                "hallucination_guard": {
                    "max_fine_amount_inr": 50000,
                    "disclaimer": disclaimer,
                    "verify_url": "https://echallan.parivahan.gov.in",
                },
                "fallback": {
                    "greetings": ["hi", "hello", "hey", "namaste"],
                    "fine_keywords": ["fine", "penalty", "challan", "amount", "how much", "cost"],
                    "rule_keywords": ["rule", "law", "legal", "section", "act", "allowed", "permitted"],
                    "zone_keywords": ["zone", "area", "here", "location", "nearby", "restriction"],
                    "clarification_keywords": ["which state", "what state", "vehicle", "what city", "which city"],
                    "not_found_keywords": ["couldn't find", "no data", "not found", "don't have", "unavailable"],
                    "insufficient_info_keywords": ["gibberish", "rephrase", "sorry"],
                    "greeting_response": (
                        "Hello! 👋 I'm DriveLegal AI — your Indian traffic law assistant.\n\n"
                        "How can I help you today?"
                    ),
                    "unknown_query_response": (
                        "Sorry, I didn't understand that query. "
                        "Try asking about a specific traffic rule or fine."
                    ),
                    "no_info_response": (
                        "I couldn't find specific information. "
                        "Please rephrase or consult echallan.parivahan.gov.in."
                    ),
                },
                "vehicle_types": {
                    "TWO_WHEELER": ["bike", "scooter", "motorcycle", "two wheeler", "2w"],
                    "HGV":         ["truck", "bus", "heavy", "lorry", "hgv"],
                    "3W":          ["auto", "rickshaw", "three wheeler", "3w"],
                    "LMV":         ["car", "jeep", "suv", "lmv"],
                },
                "states": {
                    "Tamil Nadu":    ["tamil nadu", "tn", "chennai"],
                    "Delhi":         ["delhi", "dl", "new delhi"],
                    "Maharashtra":   ["maharashtra", "mumbai", "pune"],
                    "Karnataka":     ["karnataka", "bangalore", "bengaluru"],
                },
                "offence_names": {
                    "NO_HELMET":         "No Helmet",
                    "DRUNK_DRIVING":     "Drunk Driving",
                    "SPEED_EXCESS":      "Over Speeding",
                    "NO_LICENSE":        "Driving Without License",
                    "MOBILE_PHONE":      "Using Mobile Phone While Driving",
                    "NO_INSURANCE":      "No Insurance",
                    "RED_LIGHT_JUMPING": "Jumping Red Light",
                    "SECTION_179":       "Wrong Way Driving (Sec 179)",
                    "SECTION_184":       "Dangerous/Rash Driving (Sec 184)",
                    "NO_SEATBELT":       "No Seatbelt (Sec 194B)",
                    "SECTION_194D":      "No Helmet (Sec 194D)",
                },
            }

    @staticmethod
    def _load_system_prompt() -> str:
        """Read system_prompt.txt; fall back to a minimal embedded string."""
        path = os.path.join(_HERE, "system_prompt.txt")
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read().strip()
            if text:
                return text
        except Exception as exc:
            logger.warning("[AgentEngine] Could not load system_prompt.txt (%s) — using embedded fallback.", exc)
        return (
            "You are DriveLegal AI — an official Indian traffic law assistant. "
            "Always use provided tools. Cite MV Act sections. Use ₹ for amounts. "
            "End with: ⚠️ Informational only. Verify at echallan.parivahan.gov.in."
        )

    @staticmethod
    def _load_offence_keywords() -> Dict[str, List[str]]:
        """Load keyword map from offence_keywords.json; fall back to minimal dict."""
        path = os.path.join(_HERE, "offence_keywords.json")
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            return {k: v for k, v in data.items() if not k.startswith("_")}
        except Exception as exc:
            logger.warning("[AgentEngine] Could not load offence_keywords.json (%s) — using minimal fallback.", exc)
            return {
                "NO_HELMET":         ["helmet", "194d", "section 194d"],
                "DRUNK_DRIVING":     ["drunk", "alcohol", "daaru", "dui", "drink and drive", "section 185"],
                "SPEED_EXCESS":      ["speed", "overspeeding", "speeding", "fast", "section 183"],
                "RED_LIGHT_JUMPING": ["red light", "signal jump", "jumping red", "lal batti"],
                "NO_LICENSE":        ["no license", "without license", "licence", "section 3"],
                "NO_SEATBELT":       ["seatbelt", "seat belt", "194b", "section 194b"],
                "MOBILE_PHONE":      ["mobile", "phone", "call while driving"],
                "SECTION_179":       ["wrong way", "one way", "wrong side", "section 179"],
                "SECTION_184":       ["dangerous", "rash driving", "section 184"],
                "NO_INSURANCE":      ["insurance", "section 196"],
            }

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def run(
        self,
        user_text: str,
        conversation_history: Optional[List[Dict]] = None,
        gps: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        if self.groq_available:
            return self._run_groq_with_circuit_breaker(user_text, conversation_history or [], gps)
        return self._keyword_fallback(user_text, gps)

    def _run_groq_with_circuit_breaker(
        self, user_text: str, history: List[Dict], gps: Optional[Dict]
    ) -> Dict[str, Any]:
        try:
            return ai_circuit_breaker.call(self._run_groq, user_text, history, gps)
        except CircuitBreakerError:
            logger.warning("[AgentEngine] Circuit Breaker OPEN — falling back to local NLP.")
            fallback = self._keyword_fallback(user_text, gps)
            fallback["error_detail"] = "Groq API temporarily unavailable (Circuit Breaker OPEN)"
            return fallback

    # ─────────────────────────────────────────────────────────────────────────
    # Groq Agentic Loop
    # ─────────────────────────────────────────────────────────────────────────

    def _run_groq(
        self,
        user_text: str,
        history: List[Dict],
        gps: Optional[Dict],
    ) -> Dict[str, Any]:
        t0 = time.time()
        groq_time = 0.0
        tool_time = 0.0
        tools_used: List[Dict] = []

        groq_cfg  = self._groq_cfg
        guard_cfg = self._guard_cfg

        enriched_text = user_text
        if gps:
            enriched_text += (
                f"\n\n[System context: User GPS lat={gps.get('lat')}, "
                f"lon={gps.get('lon')}. Check zone restrictions if relevant.]"
            )

        messages = [{"role": "system", "content": self._system_prompt}]
        for turn in history:
            role = turn.get("role", "user")
            if role == "model":
                role = "assistant"
            parts_text = turn.get("parts", [""])
            messages.append({"role": role, "content": " ".join(parts_text)})
        messages.append({"role": "user", "content": enriched_text})

        # Build Groq-format tool list
        groq_tools = []
        for t in TOOL_DEFINITIONS:
            parameters = t.get("parameters", {})
            if "type" not in parameters:
                parameters["type"] = "object"
            if "properties" not in parameters:
                parameters["properties"] = {}
            groq_tools.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": parameters,
                },
            })

        try:
            response_message = None
            for iteration in range(groq_cfg["max_tool_iterations"]):
                t1 = time.time()
                response = self.client.chat.completions.create(
                    model=groq_cfg["model"],
                    messages=messages,
                    tools=groq_tools,
                    tool_choice="auto",
                    max_tokens=groq_cfg["max_tokens"],
                    temperature=groq_cfg["temperature"],
                )
                groq_time += time.time() - t1

                response_message = response.choices[0].message
                tool_calls = response_message.tool_calls

                assistant_msg: Dict[str, Any] = {"role": "assistant"}
                if response_message.content is not None:
                    assistant_msg["content"] = response_message.content
                if tool_calls:
                    assistant_msg["tool_calls"] = [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.function.name,
                                "arguments": call.function.arguments,
                            },
                        }
                        for call in tool_calls
                    ]
                messages.append(assistant_msg)

                if not tool_calls:
                    break

                logger.info(
                    "[AgentEngine] iter %d tools: %s",
                    iteration + 1,
                    [c.function.name for c in tool_calls],
                )

                for call in tool_calls:
                    t_tool_start = time.time()
                    try:
                        params = json.loads(call.function.arguments)
                    except json.JSONDecodeError:
                        params = {}
                    result = self.tool_executor.execute(call.function.name, params, gps)
                    tool_time += time.time() - t_tool_start
                    tools_used.append({"tool": call.function.name, "params": params, "result": result})
                    messages.append({
                        "tool_call_id": call.id,
                        "role": "tool",
                        "name": call.function.name,
                        "content": json.dumps({"result": result}),
                    })

            final_text = (response_message.content or "").strip() if response_message else ""
            if not final_text:
                final_text = self._fb_cfg["no_info_response"]

            # Hallucination guard: ensure disclaimer is always present
            disclaimer = guard_cfg["disclaimer"]
            if disclaimer not in final_text:
                logger.warning("[AgentEngine] Hallucination Alert: Missing disclaimer — appending.")
                final_text += f"\n\n{disclaimer}"

            t_fmt = time.time()
            unified_res = self._build_unified_response(
                final_text, tools_used, True, groq_cfg["model_label"]
            )
            total_time = time.time() - t0
            logger.info(
                "[AgentEngine] Latency → Groq: %.0fms | Tools: %.0fms | Format: %.0fms | Total: %.0fms",
                groq_time * 1000, tool_time * 1000, (time.time() - t_fmt) * 1000, total_time * 1000,
            )
            return unified_res

        except Exception as e:
            error_msg = str(e)
            logger.error("[AgentEngine] Groq error: %s", error_msg)
            if isinstance(e, CircuitBreakerError):
                raise
            if "429" in error_msg:
                logger.info("[AgentEngine] Rate-limited — falling back to local NLP.")
            fallback = self._keyword_fallback(user_text, gps)
            fallback["error_detail"] = error_msg
            return fallback

    # ─────────────────────────────────────────────────────────────────────────
    # Keyword Fallback (no API key / rate-limited)
    # ─────────────────────────────────────────────────────────────────────────

    # Traffic domain terms — if NONE of these appear, query is off-topic
    _TRAFFIC_TERMS = [
        "fine", "penalty", "challan", "helmet", "seatbelt", "seat belt",
        "speed", "license", "licence", "insurance", "drunk", "alcohol",
        "mobile", "phone", "signal", "red light", "rule", "law", "section",
        "act", "traffic", "vehicle", "driving", "car", "bike", "truck",
        "road", "zone", "puc", "echallan", "parivahan", "motor vehicle",
        "transport", "rto", "mvact", "mv act", "challan", "violation",
        "overspe", "wrong way", "wrong side", "triple", "pillion",
        "digilocker", "rc", "dl ", "blood alcohol", "bac", "tinted",
        "exhaust", "headlight", "honk", "horn", "ambulance", "emergency",
        "parking", "overload", "juvenile", "minor driving", "number plate",
        "registration", "fitness", "registration certificate",
    ]
    _CLOSING_TERMS = [
        "thanks", "thank you", "ok thanks", "bye", "goodbye",
        "noted", "got it", "great", "awesome", "cool", "ok",
    ]
    # Currency symbol map
    _CURRENCY_SYMBOL = {"IN": "₹", "AE": "AED ", "GB": "£", "SG": "SGD ", "US": "USD ", "SA": "SAR "}

    def _keyword_fallback(self, text: str, gps: Optional[Dict]) -> Dict[str, Any]:
        text_lower = text.lower()
        tools_used: List[Dict] = []
        response_parts: List[str] = []
        fb        = self._fb_cfg
        hs        = self._hs_cfg
        guard     = self._guard_cfg

        # ── Extract injected [Context: ...] prefix from multi-turn sessions ──
        context_offence: Optional[str] = None
        context_state:   Optional[str] = None
        clean_text = text_lower
        if text_lower.startswith("[context:"):
            bracket_end = text_lower.find("]")
            if bracket_end != -1:
                ctx_str    = text_lower[9:bracket_end]   # after "[context:"
                clean_text = text_lower[bracket_end + 1:].strip()
                for part in ctx_str.split(","):
                    part = part.strip()
                    if part.startswith("offence:"):
                        context_offence = part.split(":", 1)[1].strip()
                    elif part.startswith("state:"):
                        context_state = part.split(":", 1)[1].strip()

        # ── Fuzzy greeting detection ──────────────────────────────────────────
        greeting_set = set(g.lower() for g in fb["greetings"])
        stripped = clean_text.strip()
        if stripped in greeting_set or any(stripped.startswith(g) for g in greeting_set):
            return {
                "status":        "ok",
                "intent":        "greeting",
                "response":      fb["greeting_response"],
                "text":          fb["greeting_response"],
                "tools_used":    [],
                "agent_powered": False,
                "model":         "keyword-fallback",
                "fine":          None, "rule": None, "zone": None,
                "session":       {}, "warnings": [],
            }

        # ── Closing / thank-you messages ──────────────────────────────────────
        is_closing = any(k in clean_text for k in self._CLOSING_TERMS)
        has_traffic = any(k in clean_text for k in self._TRAFFIC_TERMS)
        if is_closing and not has_traffic:
            closing_resp = "You're welcome! 😊 Drive safe and feel free to ask any other traffic law questions."
            return {
                "status":        "ok",
                "intent":        "closing",
                "response":      closing_resp,
                "text":          closing_resp,
                "tools_used":    [],
                "agent_powered": False,
                "model":         "keyword-fallback",
                "fine":          None, "rule": None, "zone": None,
                "session":       {}, "warnings": [],
            }

        # ── Off-topic / out-of-scope guard ────────────────────────────────────
        if not has_traffic:
            oos_resp = (
                "I'm DriveLegal AI — I can only help with traffic law queries. 🚦\n\n"
                "Try asking things like:\n"
                "• \"Fine for no helmet in Tamil Nadu\"\n"
                "• \"Drunk driving penalty in UAE\"\n"
                "• \"What is Section 194D?\"\n"
                "• \"Speed limit in a school zone\""
            )
            return {
                "status":        "out_of_scope",
                "intent":        "unknown",
                "response":      oos_resp,
                "text":          oos_resp,
                "tools_used":    [],
                "agent_powered": False,
                "model":         "keyword-fallback",
                "fine":          None, "rule": None, "zone": None,
                "session":       {}, "warnings": [],
            }

        # ── Country / region detection ────────────────────────────────────────
        country, intl_state = self._detect_country(clean_text)
        currency_sym = self._CURRENCY_SYMBOL.get(country, "₹")

        # ── Detect comparison query (X vs Y) ─────────────────────────────────
        is_comparison = any(k in clean_text for k in [" vs ", " versus ", "compared to", "difference between"])

        # ── Offence / vehicle / state detection ──────────────────────────────
        offence = self._detect_offence(clean_text)
        # Fall back to session context if no offence detected in current text
        if not offence and context_offence:
            offence = context_offence.upper()
        vehicle = self._detect_vehicle(clean_text)
        state   = intl_state or (context_state.title() if context_state else self._detect_state(clean_text))

        # ── Fine lookup ───────────────────────────────────────────────────────
        fine_triggered = (
            any(k in clean_text for k in fb["fine_keywords"])
            or (context_offence and (intl_state or self._detect_state(clean_text) != "ALL"))
        )
        if fine_triggered and offence:
            if is_comparison:
                # Run two lookups: detected vehicle vs "other" type
                lookup_pairs = [
                    (offence, vehicle, state,   country),
                    (offence, "LMV" if vehicle == "HGV" else "HGV", state, country),
                ]
                labels = [vehicle, "LMV" if vehicle == "HGV" else "HGV (truck)"]
            else:
                lookup_pairs = [(offence, vehicle, state, country)]
                labels = [vehicle]

            for (off, veh, st, cty), label in zip(lookup_pairs, labels):
                params = {
                    "offence_type":  off,
                    "vehicle_class": veh,
                    "state":         st if st else "ALL",
                    "country":       cty,
                }
                result = self.tool_executor.execute("lookup_fine", params, gps)
                tools_used.append({"tool": "lookup_fine", "result": result, "params": params})
                display_name = self._oname_cfg.get(off, off.replace("_", " ").title())

                if result.get("found"):
                    amt       = result["amount_inr"]
                    rpt_amt   = result.get("repeat_amount_inr", "N/A")
                    sec       = result.get("section_ref", "N/A")
                    st_label  = result.get("state", st or "National")
                    response_parts.append(
                        f"**Fine for {display_name} ({label}):**\n"
                        f"   • Amount: {currency_sym}{amt}\n"
                        f"   • Repeat Offence: {currency_sym}{rpt_amt}\n"
                        f"   • Section: {sec}\n"
                        f"   • Location: {st_label}"
                    )
                else:
                    response_parts.append(
                        f"No fine data found for '{display_name}' ({label}) in this location."
                    )

            # Attach rule for first detected offence
            if offence:
                rule_result = self.tool_executor.execute(
                    "lookup_rule", {"offence_code": offence}, gps
                )
                if rule_result.get("found"):
                    tools_used.append({
                        "tool":   "lookup_rule",
                        "params": {"offence_code": offence},
                        "result": rule_result,
                    })

        # ── Rule lookup ───────────────────────────────────────────────────────
        if not response_parts and any(k in clean_text for k in fb["rule_keywords"]):
            # If an offence is detected, look it up directly before falling back to keyword search
            if offence:
                rule_result = self.tool_executor.execute(
                    "lookup_rule", {"offence_code": offence}, gps
                )
                tools_used.append({"tool": "lookup_rule", "result": rule_result, "params": {"offence_code": offence}})
                if rule_result.get("found"):
                    r = rule_result
                    response_parts.append(
                        f"**{r['title']}** ({r.get('section', '')}):\n{r['description']}"
                    )
            if not response_parts:
                # Strip context prefix tokens for cleaner search
                search_tokens = [w for w in clean_text.split() if len(w) > 2][:hs["rule_query_word_limit"]]
                result = self.tool_executor.execute(
                    "search_rules", {"keywords": search_tokens}, gps
                )
                tools_used.append({"tool": "search_rules", "result": result})
                if result.get("found") and result.get("rules"):
                    r = result["rules"][0]
                    response_parts.append(
                        f"**{r['title']}** ({r.get('section', '')}): {r['description']}"
                    )

        # ── Zone check ────────────────────────────────────────────────────────
        if gps and any(k in clean_text for k in fb["zone_keywords"]):
            zone_result = self.tool_executor.execute("check_zone", {}, gps)
            tools_used.append({"tool": "check_zone", "result": zone_result})
            if zone_result.get("found"):
                for z in zone_result.get("zones", []):
                    multiplier = z.get("fine_multiplier", 1.0)
                    mult_note  = f" (fine multiplier: {multiplier}×)" if multiplier > 1.0 else ""
                    response_parts.append(
                        f"📍 Active zone: **{z['name']}**{mult_note} — {', '.join(z.get('rules', []))}"
                    )
            else:
                # GPS was provided but no zone matched — give useful confirmation
                lat = gps.get("lat", "?")
                lon = gps.get("lon", "?")
                response_parts.append(
                    f"📍 No special traffic zones (school zone, silent zone, etc.) detected at your "
                    f"location (lat={lat}, lon={lon}). Standard traffic rules apply."
                )

        # ── HybridSearch fallback ─────────────────────────────────────────────
        if not response_parts and self.hybrid_search:
            try:
                nlp_results = self.hybrid_search.search(text, top_k=hs["top_k"])
                relevant = [r for r in nlp_results if r.get("score", 0) > hs["score_threshold"]]
                if relevant:
                    tools_used.append({"tool": "hybrid_search", "result": relevant})
                    response_parts.append("Here's what I found in the traffic law database:\n")
                    max_chars = hs["content_max_chars"]
                    for i, r in enumerate(relevant, 1):
                        meta    = r.get("metadata", {})
                        title   = meta.get("title", "")
                        section = meta.get("section", "")
                        content = r.get("content", "")

                        if "###Assistant:" in content:
                            content = content.split("###Assistant:")[-1].strip()
                        if "###Human:" in content:
                            content = content.split("###Human:")[0].strip()
                        content = content.strip().rstrip("0123456789").strip()
                        if not content:
                            continue

                        header = f"**{title}**" if title else f"Result {i}"
                        if section and section != "QA Dataset":
                            header += f" (Section {section})"
                        response_parts.append(f"{i}. {header}\n   {content[:max_chars]}")
            except Exception as e:
                logger.warning("[AgentEngine] HybridSearch fallback error: %s", e)

        if not response_parts:
            response_parts = [fb["unknown_query_response"]]

        response_parts.append(f"\n{guard['disclaimer']}")
        return self._build_unified_response(
            "\n".join(response_parts), tools_used, False, "keyword-fallback"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Fallback Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _detect_offence(self, text: str) -> Optional[str]:
        """Return the offence code whose keywords score highest in *text*.

        Scoring: each keyword phrase found as a substring adds 1 point.
        The offence with the most hits wins — ties keep insertion order.
        Returns None when no keyword matches at all.
        """
        scores: Dict[str, int] = {}
        for offence, keywords in self._offence_keywords.items():
            hits = sum(1 for kw in keywords if kw in text)
            if hits:
                scores[offence] = hits
        if not scores:
            return None
        return max(scores, key=lambda o: scores[o])

    def _detect_vehicle(self, text: str) -> str:
        """Detect vehicle class from text using config keyword map."""
        for vehicle_class, keywords in self._veh_cfg.items():
            if vehicle_class.startswith("_"):
                continue
            if any(k in text for k in keywords):
                return vehicle_class
        return "GENERAL"

    def _detect_state(self, text: str) -> str:
        """Detect Indian state from text using config keyword map."""
        for state, keywords in self._state_cfg.items():
            if state.startswith("_"):
                continue
            if any(k in text for k in keywords):
                return state
        return "ALL"

    def _detect_country(self, text: str) -> tuple:
        """
        Detect country and region/state from query text for international lookups.
        Returns (country_code, region_state) where region_state is the DB state value
        (e.g. "DUBAI", "ABU_DHABI", "CALIFORNIA", "ALL") or None for IN default.
        """
        # UAE — Dubai / Abu Dhabi / Sharjah
        if any(k in text for k in ["dubai", "uae", "united arab emirates", "sharjah", "ajman", "fujairah", "ras al", "أبوظبي", "دبي"]):
            region = "ABU_DHABI" if "abu dhabi" in text else "DUBAI"
            return "AE", region
        # Abu Dhabi explicit (checked after UAE block)
        if "abu dhabi" in text:
            return "AE", "ABU_DHABI"
        # United Kingdom
        if any(k in text for k in ["united kingdom", "london", "britain", "england", "scotland", "wales", "british", " uk ", " uk\n", "uk traffic", "uk law"]):
            return "GB", "ALL"
        # Singapore
        if any(k in text for k in ["singapore", "spore", " sg "]):
            return "SG", "ALL"
        # Saudi Arabia
        if any(k in text for k in ["saudi", "saudi arabia", "riyadh", "jeddah", "mecca", "medina", "ksa", "kingdom of saudi"]):
            return "SA", "ALL"
        # USA
        if any(k in text for k in ["usa", "united states", "america", "u.s.", "california", "new york", "texas", "florida", "chicago", "los angeles", "san francisco", "nyc", "new jersey"]):
            if "california" in text or "los angeles" in text or "san francisco" in text:
                return "US", "CALIFORNIA"
            if "new york" in text or "nyc" in text or "new jersey" in text:
                return "US", "NEW_YORK"
            if "texas" in text or "houston" in text or "dallas" in text:
                return "US", "TEXAS"
            return "US", "ALL"
        # Default: India
        return "IN", None

    # ── Unified Response Builder ──────────────────────────────────────────────

    def _build_unified_response(
        self,
        final_text: str,
        tools_used: List[Dict],
        agent_powered: bool,
        model: str,
    ) -> Dict[str, Any]:
        fine_data = None
        rule_data = None
        zone_data = None
        search_matches = []
        intent = "general_query"
        query_summary = "general traffic query"
        status = "ok"

        guard = self._guard_cfg
        fb    = self._fb_cfg

        for tu in tools_used:
            tool_name = tu.get("tool")
            result    = tu.get("result", {})
            params    = tu.get("params", {})

            if tool_name == "lookup_fine" and result.get("found"):
                fine_data = {
                    "amount_inr":        result.get("amount_inr"),
                    "repeat_amount_inr": result.get("repeat_amount_inr"),
                    "section_ref":       result.get("section_ref"),
                    "data_source":       "fines_db",
                    "state":             result.get("state"),
                    "vehicle_class":     result.get("vehicle_class"),
                    "notes":             result.get("notes"),
                }
                intent = "fine_lookup"
                query_summary = params.get("offence_type", "fine_lookup").lower().replace("_", " ")

                # Hallucination guard: flag suspiciously large fine amounts
                amount = fine_data["amount_inr"]
                if isinstance(amount, (int, float)) and amount > guard["max_fine_amount_inr"]:
                    logger.warning(
                        "[AgentEngine] Hallucination Alert: High fine ₹%s detected — possible error.",
                        amount,
                    )

            elif tool_name == "lookup_rule" and result.get("found"):
                rule_data = {
                    "rule_id":      result.get("rule_id"),
                    "title":        result.get("title"),
                    "description":  result.get("description"),
                    "section":      result.get("section"),
                    "compoundable": result.get("compoundable"),
                    "imprisonment": result.get("imprisonment"),
                }
                if intent == "general_query":
                    intent = "rule_query"
                    query_summary = params.get("offence_code", "rule_query").lower().replace("_", " ")

            elif tool_name == "search_rules" and result.get("found") and result.get("rules"):
                top_rule = result["rules"][0]
                rule_data = {
                    "rule_id":     top_rule.get("rule_id"),
                    "title":       top_rule.get("title"),
                    "description": top_rule.get("description"),
                    "section":     top_rule.get("section"),
                }
                if intent == "general_query":
                    intent = "rule_query"
                    query_summary = " ".join(params.get("keywords", []))

            elif tool_name == "check_zone" and result.get("found") and result.get("zones"):
                zone_data = {
                    "active_zones":      [z.get("name") for z in result["zones"]],
                    "applicable_rules":  [z.get("rules", []) for z in result["zones"]],
                }

            elif tool_name == "hybrid_search":
                search_matches = result

        # Status classification — keywords are configurable
        lower_text = final_text.lower()
        if "?" in final_text and any(k in lower_text for k in fb["clarification_keywords"]):
            status = "needs_clarification"
        elif not fine_data and not rule_data and any(k in lower_text for k in fb["not_found_keywords"]):
            status = "not_found"
        elif (
            not fine_data and not rule_data
            and intent == "general_query"
            and any(k in lower_text for k in fb["insufficient_info_keywords"])
        ):
            status = "insufficient_info"
            intent = "unknown"

        # Session state
        session_state: Dict[str, Any] = {}
        if fine_data:
            session_state["offence_type"]    = query_summary.upper().replace(" ", "_")
            session_state["state"]           = fine_data.get("state")
            session_state["vehicle_class"]   = fine_data.get("vehicle_class")
            session_state["section_ref"]     = fine_data.get("section_ref")
            session_state["in_clarification"] = False
        if status == "needs_clarification":
            session_state["in_clarification"] = True

        warnings_list = []
        if status == "not_found":
            warnings_list.append(
                f"No data found in the database. Please verify at {guard['verify_url']}."
            )

        return {
            "status":         status,
            "intent":         intent,
            "query_summary":  query_summary,
            "fine":           fine_data,
            "rule":           rule_data,
            "zone":           zone_data,
            "search_matches": search_matches,
            "text":           final_text,
            "response":       final_text,
            "session":        session_state,
            "tools_used":     tools_used,
            "agent_powered":  agent_powered,
            "model":          model,
            "warnings":       warnings_list,
        }
