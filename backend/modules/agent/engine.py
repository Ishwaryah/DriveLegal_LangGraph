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

import os
import logging
from typing import Any, Dict, List, Optional

from backend.modules.agent.tools import ToolExecutor, TOOL_DEFINITIONS

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
        self.types = None
        self.gemini_available = False
        self.hybrid_search = None

        # Local NLP fallback (HybridSearch)
        try:
            from backend.modules.nlp.hybrid_search import HybridSearch
            _base = os.path.dirname(os.path.abspath(__file__))
            rules_path   = os.path.join(_base, "..", "..", "data", "rules.json")
            persist_dir  = os.path.join(_base, "..", "..", "data", "vector_db")
            self.hybrid_search = HybridSearch(rules_path, persist_dir)
            logger.info(
                "[AgentEngine] HybridSearch loaded (%d documents).",
                len(self.hybrid_search.documents),
            )
        except Exception as e:
            logger.warning("[AgentEngine] HybridSearch unavailable: %s", e)

        # Gemini SDK
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.info("[AgentEngine] GEMINI_API_KEY not set — keyword fallback mode.")
            return

        try:
            from google import genai
            from google.genai import types
            self.client = genai.Client(api_key=api_key)
            self.types = types
            self.gemini_available = True
            logger.info("[AgentEngine] Gemini 2.0 Flash ready with tool calling.")
        except Exception as e:
            logger.error("[AgentEngine] Gemini init failed: %s", e)

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def run(
        self,
        user_text: str,
        conversation_history: Optional[List[Dict]] = None,
        gps: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        if self.gemini_available:
            return self._run_gemini(user_text, conversation_history or [], gps)
        return self._keyword_fallback(user_text, gps)

    # ─────────────────────────────────────────────────────────────────────────
    # Gemini Agentic Loop
    # ─────────────────────────────────────────────────────────────────────────

    def _run_gemini(
        self,
        user_text: str,
        history: List[Dict],
        gps: Optional[Dict],
    ) -> Dict[str, Any]:
        tools_used: List[Dict] = []

        enriched_text = user_text
        if gps:
            enriched_text += (
                f"\n\n[System context: User GPS lat={gps.get('lat')}, "
                f"lon={gps.get('lon')}. Check zone restrictions if relevant.]"
            )

        # Build conversation contents
        contents = []
        for turn in history:
            role = turn.get("role", "user")
            parts_text = turn.get("parts", [""])
            contents.append(
                self.types.Content(
                    role=role,
                    parts=[self.types.Part.from_text(text=p) for p in parts_text],
                )
            )
        contents.append(
            self.types.Content(
                role="user",
                parts=[self.types.Part.from_text(text=enriched_text)],
            )
        )

        tool_declarations = [
            self.types.FunctionDeclaration(
                name=t["name"],
                description=t["description"],
                parameters=t["parameters"],
            )
            for t in TOOL_DEFINITIONS
        ]

        config = self.types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[self.types.Tool(function_declarations=tool_declarations)],
            temperature=0.1,
        )

        try:
            response = None
            for iteration in range(self.MAX_TOOL_ITERATIONS):
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=contents,
                    config=config,
                )

                tool_calls = [
                    part.function_call
                    for part in response.candidates[0].content.parts
                    if hasattr(part, "function_call") and part.function_call
                ]

                if not tool_calls:
                    break

                logger.info(
                    "[AgentEngine] iter %d tools: %s",
                    iteration + 1,
                    [c.name for c in tool_calls],
                )

                contents.append(response.candidates[0].content)

                tool_result_parts = []
                for call in tool_calls:
                    params = dict(call.args)
                    result = self.tool_executor.execute(call.name, params, gps)
                    tools_used.append({"tool": call.name, "params": params, "result": result})
                    tool_result_parts.append(
                        self.types.Part.from_function_response(
                            name=call.name,
                            response={"result": result},
                        )
                    )

                contents.append(
                    self.types.Content(role="tool", parts=tool_result_parts)
                )

            final_text = ""
            if response:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text:
                        final_text += part.text

            final_text = final_text.strip() or (
                "I couldn't find specific information. "
                "Please rephrase or consult echallan.parivahan.gov.in."
            )

            return {
                "status":        "ok",
                "response":      final_text,
                "tools_used":    tools_used,
                "agent_powered": True,
                "model":         "gemini-2.0-flash",
            }

        except Exception as e:
            error_msg = str(e)
            logger.error("[AgentEngine] Gemini error: %s", error_msg)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
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
                tools_used.append({"tool": "lookup_fine", "result": result})

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
                "I couldn't find specific information for that query. "
                "Try asking about a specific traffic rule or fine — e.g. "
                "'fine for no helmet in Tamil Nadu'."
            ]

        response_parts.append(
            "\n⚠️ Informational only. Verify at echallan.parivahan.gov.in."
        )

        return {
            "status":        "fallback",
            "response":      "\n".join(response_parts),
            "tools_used":    tools_used,
            "agent_powered": False,
        }

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