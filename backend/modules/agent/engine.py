"""
DriveLegal Agent Engine
=======================
Agentic loop powered by Gemini 2.0 Flash with function calling.

Architecture:
─────────────────────────────────────────────────────────────────────
User message
    │
    ▼
Gemini 2.0 Flash (system prompt + tool declarations)
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

Falls back to HybridSearch + keyword matching if GEMINI_API_KEY is absent
or if Gemini rate-limits (HTTP 429).

SDK: google-genai  (pip install google-genai)
Model: gemini-2.0-flash
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

# ─────────────────────────────────────────────────────────────────────────────
# System Prompt
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are DriveLegal AI — an official Indian traffic law assistant.

You help drivers, citizens, and legal professionals with:
- Traffic violation fines and challan amounts (Motor Vehicles Act 1988)
- Traffic laws, rules, and which MV Act sections apply
- Location-based zone restrictions (school zones, no-horn zones, speed limits)
- Repeat-offence implications and higher penalties

STRICT GUIDELINES:
1. Always use the provided tools — never guess fine amounts or law sections.
2. Always cite the MV Act section number when mentioning a rule.
3. Use ₹ symbol for Indian Rupee amounts.
4. If the database has no data, say so clearly. Never fabricate.
5. For repeat offences, always mention the higher penalty.
6. Be concise, clear, and structured. Use bullet points for multiple items.
7. End responses with: "⚠️ Informational only. Verify at echallan.parivahan.gov.in."
8. If GPS context is available, proactively check for zone restrictions.
9. Infer vehicle type from context (e.g. "bike" = TWO_WHEELER, "car" = LMV).

TONE: Professional, helpful, government-branded. Not casual."""


# ─────────────────────────────────────────────────────────────────────────────
# Agent Engine
# ─────────────────────────────────────────────────────────────────────────────

class AgentEngine:
    """
    AI agent using Gemini 2.0 Flash with function calling.
    Falls back to HybridSearch + keyword matching when GEMINI_API_KEY is unset
    or when Gemini is rate-limited.
    """

    MAX_TOOL_ITERATIONS = 5

    def __init__(self, fine_lookup, rules_loader, geofencing_engine):
        self.tool_executor = ToolExecutor(fine_lookup, rules_loader, geofencing_engine)
        self.client = None
        self.groq_available = False
        self.hybrid_search = None

        # Local NLP fallback (HybridSearch)
        try:
            from backend.modules.nlp.hybrid_search import HybridSearch
            _base = os.path.dirname(os.path.abspath(__file__))
            rules_path   = os.path.join(_base, "..", "..", "data", "rules.json")
            persist_dir  = os.path.join(_base, "..", "..", "data", "vector_db")
            self.hybrid_search = HybridSearch(rules_path, persist_dir)
            self.tool_executor.hybrid_search = self.hybrid_search
            logger.info(
                "[AgentEngine] HybridSearch loaded (%d documents).",
                len(self.hybrid_search.documents),
            )
        except Exception as e:
            logger.warning("[AgentEngine] HybridSearch unavailable: %s", e)

        # Groq SDK
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.info("[AgentEngine] GROQ_API_KEY not set — keyword fallback mode.")
            return

        try:
            self.client = Groq(api_key=api_key)
            self.groq_available = True
            logger.info("[AgentEngine] Groq ready with tool calling.")
        except Exception as e:
            logger.error("[AgentEngine] Groq init failed: %s", e)

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

    def _run_groq_with_circuit_breaker(self, user_text: str, history: List[Dict], gps: Optional[Dict]) -> Dict[str, Any]:
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

        enriched_text = user_text
        if gps:
            enriched_text += (
                f"\n\n[System context: User GPS lat={gps.get('lat')}, "
                f"lon={gps.get('lon')}. Check zone restrictions if relevant.]"
            )

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for turn in history:
            role = turn.get("role", "user")
            # map model to assistant
            if role == "model": role = "assistant"
            parts_text = turn.get("parts", [""])
            messages.append({"role": role, "content": " ".join(parts_text)})
            
        messages.append({"role": "user", "content": enriched_text})

        # Convert tool definitions to Groq format
        groq_tools = []
        for t in TOOL_DEFINITIONS:
            # We map "parameters" to the JSON schema
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
                    "parameters": parameters
                }
            })

        try:
            for iteration in range(self.MAX_TOOL_ITERATIONS):
                t1 = time.time()
                response = self.client.chat.completions.create(
                    model="llama3-70b-8192",  # Or your preferred Groq model
                    messages=messages,
                    tools=groq_tools,
                    tool_choice="auto",
                    max_tokens=1024,
                    temperature=0.1
                )
                groq_time += (time.time() - t1)
                
                response_message = response.choices[0].message
                tool_calls = response_message.tool_calls
                
                # Append assistant message with tool calls to history
                # Ensure we handle the case where content is None
                assistant_msg = {"role": "assistant"}
                if response_message.content is not None:
                    assistant_msg["content"] = response_message.content
                if tool_calls:
                    assistant_msg["tool_calls"] = []
                    for call in tool_calls:
                        assistant_msg["tool_calls"].append({
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.function.name,
                                "arguments": call.function.arguments
                            }
                        })
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
                    # Groq returns arguments as a JSON string
                    try:
                        params = json.loads(call.function.arguments)
                    except json.JSONDecodeError:
                        params = {}
                        
                    result = self.tool_executor.execute(call.function.name, params, gps)
                    tool_time += (time.time() - t_tool_start)
                    
                    tools_used.append({"tool": call.function.name, "params": params, "result": result})
                    
                    messages.append({
                        "tool_call_id": call.id,
                        "role": "tool",
                        "name": call.function.name,
                        "content": json.dumps({"result": result})
                    })

            final_text = ""
            if response_message.content:
                final_text = response_message.content.strip()

            final_text = final_text or (
                "I couldn't find specific information. "
                "Please rephrase or consult echallan.parivahan.gov.in."
            )

            # Hallucination Check: Missing disclaimer
            disclaimer = "⚠️ Informational only. Verify at echallan.parivahan.gov.in."
            if disclaimer not in final_text:
                logger.warning("[AgentEngine] Hallucination Alert: Missing disclaimer in Groq response. Appending automatically.")
                final_text += f"\n\n{disclaimer}"
            
            t_format_start = time.time()
            unified_res = self._build_unified_response(final_text, tools_used, True, "groq-llama3")
            format_time = time.time() - t_format_start
            
            total_time = time.time() - t0
            logger.info(
                "[AgentEngine] Latency Breakdown -> Groq: %.0fms | Tools: %.0fms | Format: %.0fms | Total: %.0fms",
                groq_time * 1000, tool_time * 1000, format_time * 1000, total_time * 1000
            )

            return unified_res

        except Exception as e:
            error_msg = str(e)
            logger.error("[AgentEngine] Groq error: %s", error_msg)
            
            # Re-raise CircuitBreakerError if applicable (though it's caught in run())
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

    def _keyword_fallback(self, text: str, gps: Optional[Dict]) -> Dict[str, Any]:
        text_lower = text.lower()
        tools_used: List[Dict] = []
        response_parts: List[str] = []

        # ── Greeting ──────────────────────────────────────────────────────────
        greetings = {"hi", "hello", "hey", "good morning", "good evening", "good afternoon", "namaste"}
        if text_lower.strip() in greetings:
            return {
                "status":        "fallback",
                "response": (
                    "Hello! 👋 I'm DriveLegal AI — your Indian traffic law assistant.\n\n"
                    "You can ask me things like:\n"
                    "• \"What's the fine for no helmet?\"\n"
                    "• \"Drunk driving penalty in Tamil Nadu\"\n"
                    "• \"What are the rules for using high beam?\"\n"
                    "• \"Speed limit in a school zone\"\n\n"
                    "How can I help you today?"
                ),
                "tools_used":    [],
                "agent_powered": False,
            }

        # ── Fine lookup ───────────────────────────────────────────────────────
        fine_keywords = ["fine", "penalty", "challan", "amount", "how much", "cost"]
        if any(k in text_lower for k in fine_keywords):
            offence = self._detect_offence(text_lower)
            vehicle = self._detect_vehicle(text_lower)
            state   = self._detect_state(text_lower)

            if offence:
                result = self.tool_executor.execute(
                    "lookup_fine",
                    {"offence_type": offence, "vehicle_class": vehicle, "state": state},
                    gps,
                )
                tools_used.append({"tool": "lookup_fine", "result": result, "params": {"offence_type": offence, "vehicle_class": vehicle, "state": state}})

                offence_names = {
                    "NO_HELMET":         "No Helmet",
                    "DRUNK_DRIVING":     "Drunk Driving",
                    "SPEED_EXCESS":      "Over Speeding",
                    "NO_LICENSE":        "Driving Without License",
                    "MOBILE_PHONE":      "Using Mobile Phone While Driving",
                    "NO_INSURANCE":      "No Insurance",
                    "RED_LIGHT_JUMPING": "Jumping Red Light",
                    "SECTION_179":       "Wrong Way Driving",
                    "SECTION_184":       "Dangerous/Rash Driving",
                    "NO_SEATBELT":       "No Seatbelt",
                    "SECTION_194D":      "No Seatbelt",
                }
                display_name = offence_names.get(offence, offence)

                if result.get("found"):
                    response_parts.append(
                        f"**Fine for {display_name} ({vehicle}):**\n"
                        f"   • Amount: ₹{result['amount_inr']}\n"
                        f"   • Repeat Offence: ₹{result.get('repeat_amount_inr', 'N/A')}\n"
                        f"   • Section: {result.get('section_ref', 'N/A')}\n"
                        f"   • State: {result.get('state', state)}"
                    )
                    
                    # Also look up rule for context
                    rule_result = self.tool_executor.execute("lookup_rule", {"offence_code": offence}, gps)
                    if rule_result.get("found"):
                        tools_used.append({"tool": "lookup_rule", "params": {"offence_code": offence}, "result": rule_result})
                else:
                    response_parts.append(
                        f"No fine data found for '{display_name}' in {state}."
                    )

        # ── Rule lookup ───────────────────────────────────────────────────────
        rule_keywords = ["rule", "law", "legal", "section", "act", "allowed", "permitted"]
        if any(k in text_lower for k in rule_keywords):
            result = self.tool_executor.execute(
                "search_rules",
                {"keywords": text_lower.split()[:5]},
                gps,
            )
            tools_used.append({"tool": "search_rules", "result": result})
            if result.get("found") and result.get("rules"):
                r = result["rules"][0]
                response_parts.append(
                    f"**{r['title']}** ({r.get('section', '')}): {r['description']}"
                )

        # ── Zone check ────────────────────────────────────────────────────────
        zone_keywords = ["zone", "area", "here", "location", "nearby", "restriction"]
        if gps and any(k in text_lower for k in zone_keywords):
            result = self.tool_executor.execute("check_zone", {}, gps)
            tools_used.append({"tool": "check_zone", "result": result})
            if result.get("found"):
                z = result["zones"][0]
                response_parts.append(
                    f"Active zone: **{z['name']}** — {', '.join(z.get('rules', []))}"
                )

        # ── HybridSearch fallback ─────────────────────────────────────────────
        if not response_parts and self.hybrid_search:
            try:
                nlp_results = self.hybrid_search.search(text, top_k=3)
                relevant = [r for r in nlp_results if r.get("score", 0) > 0.15]
                if relevant:
                    tools_used.append({"tool": "hybrid_search", "result": relevant})
                    response_parts.append("Here's what I found in the traffic law database:\n")
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
                        response_parts.append(f"{i}. {header}\n   {content[:400]}")
            except Exception as e:
                logger.warning("[AgentEngine] HybridSearch fallback error: %s", e)

        if not response_parts:
            response_parts = [
                "Sorry, I didn't understand that query. "
                "Try asking about a specific traffic rule or fine — e.g. "
                "'fine for no helmet in Tamil Nadu'."
            ]

        response_parts.append(
            "\n⚠️ Informational only. Verify at echallan.parivahan.gov.in."
        )

        return self._build_unified_response("\n".join(response_parts), tools_used, False, "keyword-fallback")

    # ─────────────────────────────────────────────────────────────────────────
    # Fallback Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _detect_offence(self, text: str) -> Optional[str]:
        offences = {
            "NO_HELMET":         ["helmet"],
            "DRUNK_DRIVING":     ["drunk", "alcohol", "daaru", "dui", "drink and drive"],
            "SPEED_EXCESS":      ["speed", "overspeeding", "speeding", "fast"],
            "RED_LIGHT_JUMPING": ["red light", "signal jump", "jumping red"],
            "NO_LICENSE":        ["no license", "without license", "licence"],
            "NO_SEATBELT":       ["seatbelt", "seat belt"],
            "SECTION_194D":      ["194d"],
            "MOBILE_PHONE":      ["mobile", "phone", "call while driving"],
            "SECTION_179":       ["wrong way", "one way"],
            "SECTION_184":       ["dangerous", "rash driving"],
            "NO_INSURANCE":      ["insurance"],
        }
        for offence, keywords in offences.items():
            if any(k in text for k in keywords):
                return offence
        return None

    def _detect_vehicle(self, text: str) -> str:
        if any(k in text for k in ["bike", "scooter", "motorcycle", "two wheeler", "2w"]):
            return "TWO_WHEELER"
        if any(k in text for k in ["truck", "bus", "heavy", "lorry", "hgv"]):
            return "HGV"
        if any(k in text for k in ["auto", "rickshaw", "three wheeler", "3w"]):
            return "3W"
        if any(k in text for k in ["car", "jeep", "suv", "lmv"]):
            return "LMV"
        return "GENERAL"

    def _detect_state(self, text: str) -> str:
        states = {
            "Tamil Nadu":    ["tamil nadu", "tn", "chennai", "coimbatore"],
            "Delhi":         ["delhi", "dl", "new delhi"],
            "Maharashtra":   ["maharashtra", "mumbai", "pune", "nagpur"],
            "Karnataka":     ["karnataka", "bangalore", "bengaluru", "mysuru"],
            "Kerala":        ["kerala", "kochi", "thiruvananthapuram"],
            "Uttar Pradesh": ["uttar pradesh", "up", "lucknow", "noida"],
            "Gujarat":       ["gujarat", "ahmedabad", "surat"],
            "Rajasthan":     ["rajasthan", "jaipur"],
            "West Bengal":   ["west bengal", "kolkata"],
            "Telangana":     ["telangana", "hyderabad"],
        }
        for state, keywords in states.items():
            if any(k in text for k in keywords):
                return state
        return "ALL"

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

        for tu in tools_used:
            tool_name = tu.get("tool")
            result = tu.get("result", {})
            params = tu.get("params", {})

            if tool_name == "lookup_fine" and result.get("found"):
                fine_data = {
                    "amount_inr": result.get("amount_inr"),
                    "repeat_amount_inr": result.get("repeat_amount_inr"),
                    "section_ref": result.get("section_ref"),
                    "data_source": "fines_db",
                    "state": result.get("state"),
                    "vehicle_class": result.get("vehicle_class"),
                    "notes": result.get("notes"),
                }
                intent = "fine_lookup"
                query_summary = params.get("offence_type", "fine_lookup").lower().replace("_", " ")
                
                # Hallucination Check: High fine amount
                if fine_data["amount_inr"] and isinstance(fine_data["amount_inr"], (int, float)):
                    if fine_data["amount_inr"] > 50000:
                        logger.warning(
                            "[AgentEngine] Hallucination Alert: High fine amount detected: ₹%s. Possible hallucination or edge-case.",
                            fine_data["amount_inr"]
                        )

            elif tool_name == "lookup_rule" and result.get("found"):
                rule_data = {
                    "rule_id": result.get("rule_id"),
                    "title": result.get("title"),
                    "description": result.get("description"),
                    "section": result.get("section"),
                    "compoundable": result.get("compoundable"),
                    "imprisonment": result.get("imprisonment"),
                }
                if intent == "general_query":
                    intent = "rule_query"
                    query_summary = params.get("offence_code", "rule_query").lower().replace("_", " ")

            elif tool_name == "search_rules" and result.get("found") and result.get("rules"):
                top_rule = result["rules"][0]
                rule_data = {
                    "rule_id": top_rule.get("rule_id"),
                    "title": top_rule.get("title"),
                    "description": top_rule.get("description"),
                    "section": top_rule.get("section"),
                }
                if intent == "general_query":
                    intent = "rule_query"
                    query_summary = " ".join(params.get("keywords", []))

            elif tool_name == "check_zone" and result.get("found") and result.get("zones"):
                zone_data = {
                    "active_zones": [z.get("name") for z in result["zones"]],
                    "applicable_rules": [z.get("rules", []) for z in result["zones"]],
                }

            elif tool_name == "hybrid_search":
                # Ensure search_matches array is populated for legacy compatibility
                search_matches = result

        # Handle specific fallback/empty states
        lower_text = final_text.lower()
        if "?" in final_text and any(k in lower_text for k in ["which state", "what state", "vehicle", "what city", "which city"]):
            status = "needs_clarification"
        elif not fine_data and not rule_data and any(k in lower_text for k in ["couldn't find", "no data", "not found", "don't have", "unavailable", "no fine data"]):
            status = "not_found"
        elif not fine_data and not rule_data and intent == "general_query" and any(k in lower_text for k in ["gibberish", "rephrase", "sorry"]):
            status = "insufficient_info"
            intent = "unknown"

        # Session state
        session_state = {}
        if fine_data:
            session_state["offence_type"] = query_summary.upper().replace(" ", "_")
            session_state["state"] = fine_data.get("state")
            session_state["vehicle_class"] = fine_data.get("vehicle_class")
            session_state["section_ref"] = fine_data.get("section_ref")
            session_state["in_clarification"] = False
        if status == "needs_clarification":
            session_state["in_clarification"] = True

        warnings_list = []
        if status == "not_found":
            warnings_list.append("No data found in the database. Please verify at https://echallan.parivahan.gov.in.")

        return {
            "status":        status,
            "intent":        intent,
            "query_summary": query_summary,
            "fine":          fine_data,
            "rule":          rule_data,
            "zone":          zone_data,
            "search_matches": search_matches,
            "text":          final_text,
            "response":      final_text,
            "session":       session_state,
            "tools_used":    tools_used,
            "agent_powered": agent_powered,
            "model":         model,
            "warnings":      warnings_list,
        }