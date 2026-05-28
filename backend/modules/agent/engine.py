"""
engine.py — DriveLegal Agent Engine

Architecture (Agentic Loop):
───────────────────────────────────────────────────────────────
User message
    │
    ▼
LLM (Ollama local / Gemini cloud / Groq cloud) with tools + system prompt
    │
    ├── Decides to call: lookup_fine("no helmet", "2W", "Tamil Nadu")
    │       └── ToolExecutor._lookup_fine() → queries SQLite
    │               └── returns { amount_inr: 1000, section: "129" }
    │
    ├── Decides to call: lookup_rule("NO_HELMET", "Tamil Nadu")
    │       └── ToolExecutor._lookup_rule() → queries rules.json
    │               └── returns { title:..., description:... }
    │
    └── Synthesizes tool results → writes natural language response
            └── "The fine for not wearing a helmet in Tamil Nadu is ₹1,000
                 under Section 194D of the Motor Vehicles Act 1988..."
    │
    ▼
Final structured response returned to mobile app
───────────────────────────────────────────────────────────────

Priority: Ollama (local) → Gemini (cloud) → Groq (cloud) → Keyword fallback

SDKs:
  - Ollama: openai Python SDK pointed at http://localhost:11434/v1
  - Gemini: google-genai SDK
  - Groq:   groq SDK with pybreaker circuit breaker

Configuration files (in the same directory):
  agent_config.json     — model params, keyword lists, thresholds
  offence_keywords.json — per-offence keyword expansion for fallback
  system_prompt.txt     — optional LLM system prompt override
"""

import os
import re
import time
import json
import logging
from typing import Any, Dict, List, Optional

from backend.modules.agent.tools import ToolExecutor, TOOL_DEFINITIONS

logger = logging.getLogger(__name__)

_HERE = os.path.dirname(os.path.abspath(__file__))

# ─────────────────────────────────────────────────────────────────────────────
# Default System Prompt (overridable via system_prompt.txt)
# ─────────────────────────────────────────────────────────────────────────────

_DEFAULT_SYSTEM_PROMPT = """<identity>
You are DriveLegal, a world-class AI traffic law assistant — think of yourself as a brilliant, friendly lawyer who specializes in traffic regulations across multiple countries. You help people understand traffic fines, penalties, legal sections, and what to do if they get caught.

You have access to a comprehensive database covering traffic laws in:
- **India** (all major states — Tamil Nadu, Delhi, Maharashtra, Karnataka, Kerala, UP, Gujarat, Rajasthan, West Bengal, Telangana, AP, Punjab, Haryana, Bihar, MP, Odisha)
- **UAE/Dubai** (Dubai, Abu Dhabi — Federal Traffic Law + black point system)
- **United Kingdom** (Fixed Penalty Notices, Road Traffic Act 1988)
- **United States** (Federal + California, New York, Texas)
- **Singapore** (Road Traffic Act, demerit point system)
- **Saudi Arabia** (Moroor traffic fine schedule)
</identity>

<communication_style>
- **Detailed & Comprehensive:** Write thorough, informative answers — typically 3-5 paragraphs. Explain the legal basis, practical implications, and what happens in practice.
- **Conversational Expert Tone:** Write like a knowledgeable friend who happens to be a traffic lawyer. Be warm, helpful, and reassuring — not robotic or terse.
- **Well-Structured Markdown:** Use bold headers (##), bullet points, and blockquotes to organize information beautifully. Make answers scannable and professional.
- **Practical Advice:** Beyond just stating the fine amount, explain:
  * What happens when you get caught (procedure)
  * First offence vs repeat offence penalties
  * Additional consequences (license suspension, black points, vehicle impound, jail)
  * How to pay the fine / appeal process
  * Tips to avoid the violation
- **Currency Awareness:** Always display fines in the correct local currency with the right symbol (INR for India, AED for UAE, GBP for UK, USD for USA, SGD for Singapore, SAR for Saudi Arabia).
- **Comparisons:** When the user asks to compare fines between countries, present a clear comparison table.
</communication_style>

<core_instructions>
1. **Tool Usage (CRITICAL):** You MUST use your available tools (`lookup_fine`, `lookup_rule`, `check_zone`, `search_rules`) to fetch data before answering. NEVER hallucinate fine amounts, sections, or legal details.
2. **Country Detection:** When the user mentions a country or city (Dubai, UK, USA, Singapore, Saudi, etc.), use the correct country code in the `lookup_fine` tool call. Default to India ('IN') when no country is specified.
3. **Handle Missing Data:** If a tool returns `"found": false`, honestly say the specific data isn't in the database yet, but share what you do know from your general knowledge with a clear disclaimer.
4. **Location Context:** Only call `check_zone` when the user explicitly asks about their physical location or GPS-based restrictions.
5. **Context Awareness:** Remember previous conversation context — if the user said they're in Dubai, keep that context for follow-up questions.
6. **Citations:** Always cite the specific law section provided by the tool (MV Act for India, Federal Traffic Law for UAE, Road Traffic Act for UK, etc.).
7. **Disclaimer:** End every legal analysis with:
> [!NOTE]
> This is informational only. Consult official sources or a legal professional for official advice.
8. **Conversational Messages:** If the user sends casual messages (greetings, "ok", "thanks", "mmm", "lol"), respond naturally and warmly. Do NOT call any tools. Do NOT assume they're asking about traffic rules.
9. **Never Assume:** If the message is ambiguous, ask a friendly clarifying question.
10. **Be Honest About Scope:** If asked something completely outside traffic law (weather, recipes, coding), politely redirect — but do it conversationally, not rigidly.
</core_instructions>

<output_rules>
- NEVER output raw JSON, function call syntax, or tool results directly. Always synthesize into natural language.
- NEVER include <thought>, <think>, or reasoning tags in your output.
- NEVER repeat the user's question back to them verbatim.
- NEVER expose internal function signatures like {"name": "...", "parameters": {...}}.
- When you receive tool results, synthesize them into a detailed, well-structured answer.
- If you have already called a tool and received results, DO NOT call the same tool again.
- When displaying fine amounts, ALWAYS use the correct currency symbol for the country.
</output_rules>"""


# ─────────────────────────────────────────────────────────────────────────────
# Agent Engine
# ─────────────────────────────────────────────────────────────────────────────

class AgentEngine:
    """
    Main AI agent. Priority: Ollama (local) → Gemini (cloud) → Groq (cloud) → Keyword fallback.

    - Ollama: OpenAI-compatible API at http://localhost:11434/v1 (default model: qwen2.5-coder:7b)
    - Gemini: google-genai SDK (gemini-2.0-flash)
    - Groq:   groq SDK with pybreaker circuit breaker (llama-3.3-70b-versatile)
    - Keyword: HybridSearch + rule-based matching (always available offline)
    """

    MAX_TOOL_ITERATIONS = 5

    def __init__(self, fine_lookup, rules_loader, geofencing_engine):
        self.tool_executor = ToolExecutor(fine_lookup, rules_loader, geofencing_engine)
        self.hybrid_search = None

        # Provider flags
        self.ollama_available = False
        self.gemini_available = False
        self.groq_available   = False

        self.ollama_client  = None
        self.ollama_model   = None
        self.gemini_client  = None
        self.gemini_types   = None
        self.groq_client    = None

        # Load external config / prompt files (graceful fallback to defaults)
        self._cfg              = self._load_agent_config()
        self._system_prompt    = self._load_system_prompt()
        self._offence_keywords = self._load_offence_keywords()

        self._groq_cfg  = self._cfg["groq"]
        self._hs_cfg    = self._cfg["hybrid_search"]
        self._guard_cfg = self._cfg["hallucination_guard"]
        self._fb_cfg    = self._cfg["fallback"]
        self._veh_cfg   = self._cfg["vehicle_types"]
        self._state_cfg = self._cfg["states"]
        self._oname_cfg = self._cfg["offence_names"]

        # ── Local NLP (HybridSearch) for offline fallback ──────────────────────
        try:
            from backend.modules.nlp.hybrid_search import HybridSearch
            rules_path  = os.path.join(_HERE, "..", "..", "data", "rules.json")
            persist_dir = os.path.join(_HERE, "..", "..", "data", "vector_db")
            self.hybrid_search = HybridSearch(rules_path, persist_dir)
            self.tool_executor.hybrid_search = self.hybrid_search
            logger.info("[Agent] HybridSearch loaded (%d documents).", len(self.hybrid_search.documents))
        except Exception as e:
            logger.warning("[Agent] HybridSearch unavailable (%s). Keyword-only fallback.", e)

        # ── 1. Try Ollama (local, highest priority) ────────────────────────────
        self._init_ollama()

        # ── 2. Try Gemini (cloud fallback) ─────────────────────────────────────
        if not self.ollama_available:
            self._init_gemini()

        # ── 3. Try Groq (cloud fallback) ───────────────────────────────────────
        if not self.ollama_available and not self.gemini_available:
            self._init_groq()

    # ─────────────────────────────────────────────────────────────────────────
    # Provider initialisation
    # ─────────────────────────────────────────────────────────────────────────

    def _init_ollama(self):
        """Initialize Ollama via OpenAI-compatible API at localhost:11434."""
        base_url    = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        model       = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
        try:
            from openai import OpenAI
            client = OpenAI(base_url=base_url, api_key="ollama")
            client.models.list()  # connectivity check
            self.ollama_client    = client
            self.ollama_model     = model
            self.ollama_available = True
            logger.info("[Agent] Ollama ready — model: %s at %s", model, base_url)
        except Exception as e:
            logger.warning("[Agent] Ollama not available (%s). Trying Gemini...", e)

    def _init_gemini(self):
        """Initialize Gemini 2.0 Flash via google-genai SDK."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "your_gemini_api_key_here":
            logger.warning("[Agent] GEMINI_API_KEY not set. Trying Groq...")
            return
        try:
            from google import genai
            from google.genai import types
            self.gemini_client    = genai.Client(api_key=api_key)
            self.gemini_types     = types
            self.gemini_available = True
            logger.info("[Agent] Gemini 2.0 Flash ready (cloud).")
        except Exception as e:
            logger.error("[Agent] Gemini init failed: %s", e)

    def _init_groq(self):
        """Initialize Groq LLM with circuit breaker."""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.info("[Agent] GROQ_API_KEY not set — running keyword-fallback only.")
            return
        try:
            from groq import Groq
            self.groq_client    = Groq(api_key=api_key)
            self.groq_available = True
            logger.info("[Agent] Groq ready (model=%s).", self._groq_cfg["model"])
        except Exception as e:
            logger.error("[Agent] Groq init failed: %s", e)

    # ─────────────────────────────────────────────────────────────────────────
    # Config / data loaders
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _load_agent_config() -> Dict[str, Any]:
        path = os.path.join(_HERE, "agent_config.json")
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            return {k: v for k, v in data.items() if not k.startswith("_")}
        except Exception as exc:
            logger.warning("[Agent] Could not load agent_config.json (%s) — using defaults.", exc)
            disclaimer = "⚠️ Informational only. Verify at echallan.parivahan.gov.in."
            return {
                "groq": {
                    "model":               "llama-3.3-70b-versatile",
                    "model_label":         "groq-llama3",
                    "max_tokens":          1024,
                    "temperature":         0.1,
                    "max_tool_iterations": 5,
                },
                "hybrid_search": {
                    "top_k":                3,
                    "score_threshold":      0.15,
                    "content_max_chars":    400,
                    "rule_query_word_limit": 5,
                },
                "hallucination_guard": {
                    "max_fine_amount_inr": 50000,
                    "disclaimer":          disclaimer,
                    "verify_url":          "https://echallan.parivahan.gov.in",
                },
                "fallback": {
                    "greetings":                  ["hi", "hello", "hey", "namaste"],
                    "fine_keywords":              ["fine", "penalty", "challan", "amount", "how much", "cost"],
                    "rule_keywords":              ["rule", "law", "legal", "section", "act", "allowed", "permitted"],
                    "zone_keywords":              ["zone", "area", "here", "location", "nearby", "restriction"],
                    "clarification_keywords":     ["which state", "what state", "vehicle", "what city", "which city"],
                    "not_found_keywords":         ["couldn't find", "no data", "not found", "don't have", "unavailable"],
                    "insufficient_info_keywords": ["gibberish", "rephrase", "sorry"],
                    "greeting_response":          "Hello! 👋 I'm DriveLegal AI — your Indian traffic law assistant.\n\nHow can I help you today?",
                    "unknown_query_response":     "Sorry, I didn't understand that query. Try asking about a specific traffic rule or fine.",
                    "no_info_response":           "I couldn't find specific information. Please rephrase or consult echallan.parivahan.gov.in.",
                },
                "vehicle_types": {
                    "TWO_WHEELER": ["bike", "scooter", "motorcycle", "two wheeler", "2w", "helmet"],
                    "HGV":         ["truck", "bus", "heavy", "lorry", "hgv"],
                    "3W":          ["auto", "rickshaw", "three wheeler", "3w"],
                    "LMV":         ["car", "jeep", "suv", "lmv"],
                },
                "states": {
                    "Tamil Nadu":    ["tamil nadu", "tn", "chennai", "coimbatore"],
                    "Delhi":         ["delhi", "dl", "new delhi"],
                    "Maharashtra":   ["maharashtra", "mumbai", "pune", "nagpur"],
                    "Karnataka":     ["karnataka", "bangalore", "bengaluru"],
                    "Kerala":        ["kerala", "kochi", "thiruvananthapuram"],
                    "Uttar Pradesh": ["uttar pradesh", "up", "lucknow", "noida"],
                    "Gujarat":       ["gujarat", "ahmedabad", "surat"],
                    "Rajasthan":     ["rajasthan", "jaipur"],
                    "West Bengal":   ["west bengal", "kolkata"],
                    "Telangana":     ["telangana", "hyderabad"],
                },
                "offence_names": {
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
                    "SECTION_194D":      "No Helmet (Sec 194D)",
                },
            }

    @staticmethod
    def _load_system_prompt() -> str:
        path = os.path.join(_HERE, "system_prompt.txt")
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read().strip()
            if text:
                return text
        except Exception as exc:
            logger.warning("[Agent] Could not load system_prompt.txt (%s) — using built-in prompt.", exc)
        return _DEFAULT_SYSTEM_PROMPT

    @staticmethod
    def _load_offence_keywords() -> Dict[str, List[str]]:
        path = os.path.join(_HERE, "offence_keywords.json")
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            return {k: v for k, v in data.items() if not k.startswith("_")}
        except Exception as exc:
            logger.warning("[Agent] Could not load offence_keywords.json (%s) — using minimal fallback.", exc)
            return {
                "NO_HELMET":         ["helmet", "194d"],
                "DRUNK_DRIVING":     ["drunk", "alcohol", "daaru", "dui"],
                "SPEED_EXCESS":      ["speed", "overspeeding", "speeding"],
                "RED_LIGHT_JUMPING": ["red light", "signal jump", "jumping red"],
                "NO_LICENSE":        ["no license", "without license", "licence"],
                "NO_SEATBELT":       ["seatbelt", "seat belt", "194b"],
                "MOBILE_PHONE":      ["mobile", "phone", "call while driving"],
                "SECTION_179":       ["wrong way", "one way", "wrong side"],
                "SECTION_184":       ["dangerous", "rash driving"],
                "NO_INSURANCE":      ["insurance"],
            }

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def run(
        self,
        user_text: str,
        conversation_history: Optional[List[Dict]] = None,
        gps: Optional[Dict[str, float]] = None,
        image_base64: Optional[str] = None,
        image_mime: str = "image/jpeg",
    ) -> Dict[str, Any]:
        clean_text = self._clean_user_text(user_text)

        # Fast-path for greetings / meta questions (skip tools unless image attached)
        if not image_base64:
            conversational = (
                self._try_conversational_response(clean_text)
                or self._try_conversational_response(user_text)
            )
            if conversational:
                return conversational

        history = conversation_history or []

        if self.ollama_available:
            return self._run_ollama(user_text, history, gps, image_base64, image_mime)
        if self.gemini_available:
            return self._run_gemini(user_text, history, gps)
        if self.groq_available:
            return self._run_groq_with_circuit_breaker(user_text, history, gps)
        return self._keyword_fallback(user_text, gps)

    # ─────────────────────────────────────────────────────────────────────────
    # Shared helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _active_model_label(self) -> str:
        if self.ollama_available:
            return f"ollama/{self.ollama_model}"
        if self.gemini_available:
            return "gemini-2.0-flash"
        if self.groq_available:
            return self._groq_cfg.get("model_label", "groq-llama3")
        return "keyword-fallback"

    def _clean_user_text(self, text: str) -> str:
        t = (text or "").strip().lower()
        t = re.sub(r"[!?.。,;:]+$", "", t)
        t = re.sub(r"\s+", " ", t)
        return t

    def _strip_thinking_tags(self, text: str) -> str:
        """Remove <thought>/<think>/<reasoning> blocks (Qwen3, deepseek-r1, etc.)."""
        text = re.sub(r'<(?:thought|think|reasoning)>.*?</(?:thought|think|reasoning)>', '', text, flags=re.DOTALL)
        text = re.sub(r'<(?:thought|think|reasoning)>.*', '', text, flags=re.DOTALL)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def _message_needs_location(self, text: str) -> bool:
        keywords = (
            "zone", "here", "location", "nearby", "near me", "this area",
            "my area", "where i am", "school zone", "no-horn", "no horn",
            "speed limit", "gps", "coordinates",
        )
        return any(k in self._clean_user_text(text) for k in keywords)

    def _history_transcript(self, history: List[Dict], max_turns: int = 6) -> str:
        lines = []
        for turn in history[-max_turns:]:
            role    = "User" if turn.get("role") == "user" else "Assistant"
            parts   = turn.get("parts", [""])
            content = (parts[0] if parts else "").strip()
            if content:
                lines.append(f"{role}: {content[:600]}")
        return "\n".join(lines)

    def _history_has_traffic_context(self, history: List[Dict]) -> bool:
        blob  = self._history_transcript(history, max_turns=10).lower()
        hints = ("fine", "penalty", "challan", "helmet", "speed", "offence", "offense",
                 "violation", "₹", "rupee", "section", "motor vehicle", "mv act", "license")
        return any(h in blob for h in hints)

    def _is_follow_up_question(self, text: str, history: List[Dict]) -> bool:
        if len(history) < 2:
            return False
        clean = self._clean_user_text(text)
        if len(clean.split()) <= 2 and not any(k in clean for k in ("fine", "penalty", "rule", "helmet", "licence", "license")):
            return False
        follow_up_keywords = (
            "5th", "5 time", "fifth", "fourth", "4th", "third", "3rd",
            "second", "2nd", "repeat", "again", "same offence", "same offense",
            "what about", "how about", "and if", "what if", "the fine", "my fine",
            "that offence", "that offense", "previous", "earlier",
        )
        if any(k in clean for k in follow_up_keywords):
            return True
        traffic_hints = ("fine", "penalty", "section", "rule", "offence", "offense", "repeat", "vehicle", "helmet", "license", "licence")
        return any(h in clean for h in traffic_hints) and self._history_has_traffic_context(history)

    def _is_traffic_query(self, text: str, history: Optional[List[Dict]] = None) -> bool:
        history = history or []
        clean   = self._clean_user_text(text)
        if self._try_conversational_response(clean):
            return False
        if history and self._is_follow_up_question(text, history):
            return True
        traffic_keywords = (
            "fine", "penalty", "challan", "amount", "how much", "rupee", "₹",
            "helmet", "speed", "license", "licence", "insurance", "drunk",
            "rule", "law", "act", "section", "offence", "offense", "violation",
            "vehicle", "bike", "car", "truck", "red light", "seatbelt",
            "parking", "horn", "permit", "document", "mv act", "motor vehicle",
        )
        if any(k in clean for k in traffic_keywords):
            return True
        return self._message_needs_location(text)

    def _expand_follow_up_user_text(self, user_text: str, history: List[Dict]) -> str:
        if not self._is_follow_up_question(user_text, history):
            return user_text
        return (
            f"{user_text}\n\n"
            "[System Note: The user's message is a short follow-up. "
            "Use the conversation history to understand the context. "
            "Reuse the same offence, vehicle type, and state if they are asking about the same topic. "
            "For repeat offences (2nd, 5th time, etc.) call lookup_fine with is_repeat=true.]"
        )

    def _try_conversational_response(self, user_text: str) -> Optional[Dict[str, Any]]:
        """Fast path for greetings and filler messages — no tools needed."""
        text_lower   = self._clean_user_text(user_text)
        model_label  = self._active_model_label()

        greetings = ("hi", "hello", "hey", "hii", "hola", "good morning", "good evening", "good afternoon", "namaste")
        if (
            text_lower in greetings
            or text_lower.startswith(("hi ", "hello ", "hey "))
            or re.match(r"^(hi|hello|hey|hii|namaste)[\s!.]*$", text_lower)
        ):
            return {
                "status":        "ok",
                "intent":        "greeting",
                "response":      (
                    "Hello! 👋 I'm DriveLegal AI — your traffic law assistant.\n\n"
                    "Ask me about fines, MV Act rules, challans, or zone restrictions. "
                    "For example: \"What's the fine for no helmet in Tamil Nadu?\"\n\n"
                    f"(Running on **{model_label}**.)"
                ),
                "text":          "",
                "tools_used":    [],
                "agent_powered": self.ollama_available or self.gemini_available or self.groq_available,
                "model":         model_label,
                "fine": None, "rule": None, "zone": None,
                "session": {}, "warnings": [],
            }

        meta_keywords = ("which model", "what model", "running on", "what ai", "who are you",
                         "which llm", "what llm", "are you gemini", "are you ollama", "your model",
                         "are you groq")
        if any(k in text_lower for k in meta_keywords):
            if self.ollama_available:
                backend = f"local Ollama ({self.ollama_model}) on your machine"
            elif self.gemini_available:
                backend = "Google Gemini 2.0 Flash (cloud)"
            elif self.groq_available:
                backend = f"Groq ({self._groq_cfg.get('model', 'llama-3.3-70b')}) (cloud)"
            else:
                backend = "keyword search (no LLM active)"
            return {
                "status":        "ok",
                "intent":        "meta",
                "response":      f"I'm **DriveLegal AI**, powered by **{model_label}** ({backend}).\n\nAsk me any traffic-law question!",
                "text":          "",
                "tools_used":    [],
                "agent_powered": self.ollama_available or self.gemini_available or self.groq_available,
                "model":         model_label,
                "fine": None, "rule": None, "zone": None,
                "session": {}, "warnings": [],
            }

        filler_patterns = (
            "ok", "okay", "mmm", "hmm", "hmmm", "mhm", "ah", "oh",
            "lol", "haha", "thanks", "thank you", "thank", "bye", "cool",
            "what", "why", "how", "no", "yes", "yeah", "yep", "nope",
            "nice", "great", "good", "sure", "got it",
        )
        if text_lower in filler_patterns:
            return None

        return None

    def _enrich_with_gps(self, user_text: str, gps: Optional[Dict]) -> str:
        if not gps or not self._message_needs_location(user_text):
            return user_text
        return (
            f"{user_text}\n\n"
            f"[System context: User GPS lat={gps.get('lat')}, lon={gps.get('lon')}. "
            "Use check_zone only if this question is about location-based restrictions.]"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Ollama Agentic Loop (OpenAI-compatible API)
    # ─────────────────────────────────────────────────────────────────────────

    def _ollama_supports_native_tools(self) -> bool:
        model = (self.ollama_model or "").lower()
        return not any(m in model for m in ("vision", "llava"))

    def _run_ollama(
        self,
        user_text: str,
        history: List[Dict],
        gps: Optional[Dict],
        image_base64: Optional[str] = None,
        image_mime: str = "image/jpeg",
    ) -> Dict[str, Any]:
        tools_used: List[Dict] = []

        expanded_text = self._expand_follow_up_user_text(user_text, history)
        enriched_text = self._enrich_with_gps(expanded_text, gps)

        if image_base64:
            enriched_text += (
                "\n\n[Image task: inspect the attached image. If it looks like a challan, notice, "
                "traffic sign, licence, RC, insurance, or PUC document, extract visible text, "
                "vehicle number, date, violation, location, amount, and section if present. "
                "Then use traffic-law tools when possible to verify fine/rule details. "
                "Clearly separate 'Extracted from image' from 'Verified from database'.]"
            )

        use_tools    = bool(image_base64) or self._is_traffic_query(user_text, history)
        native_tools = use_tools and self._ollama_supports_native_tools()
        openai_tools = self._build_openai_tools() if native_tools else None

        system_prompt = self._system_prompt
        # Qwen3 thinking mode workaround — disable <think> output
        if "qwen3" in (self.ollama_model or "").lower():
            system_prompt += "\n\n/no_think"

        if use_tools and not native_tools:
            tool_json     = json.dumps(TOOL_DEFINITIONS, indent=2)
            system_prompt += f"\n\n### AVAILABLE TOOLS\n{tool_json}\n\n"
            system_prompt += (
                "### INSTRUCTIONS FOR TOOL CALLING\n"
                "You do NOT have native tool calling enabled. To use a tool, output a raw JSON block and NOTHING ELSE:\n"
                "```json\n{\"name\": \"lookup_fine\", \"arguments\": {\"offence_type\": \"NO_HELMET\", \"vehicle_class\": \"2W\", \"state\": \"ALL\"}}\n```\n"
                "Wait for the tool result before providing the final answer."
            )

        messages = [{"role": "system", "content": system_prompt}]
        for turn in history:
            role    = "assistant" if turn.get("role") == "model" else turn.get("role", "user")
            parts   = turn.get("parts", [""])
            content = parts[0] if parts else ""
            messages.append({"role": role, "content": content})

        if image_base64:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": enriched_text},
                    {"type": "image_url", "image_url": {"url": f"data:{image_mime};base64,{image_base64}"}},
                ],
            })
        else:
            messages.append({"role": "user", "content": enriched_text})

        try:
            assistant_message = None
            for iteration in range(self.MAX_TOOL_ITERATIONS):
                create_kwargs: Dict[str, Any] = {
                    "model":       self.ollama_model,
                    "messages":    messages,
                    "temperature": 0.1,
                }
                if openai_tools:
                    create_kwargs["tools"] = openai_tools

                response          = self.ollama_client.chat.completions.create(**create_kwargs)
                assistant_message = response.choices[0].message
                tool_calls_list   = assistant_message.tool_calls or []

                text_parsed_calls = []
                if use_tools and not tool_calls_list and assistant_message.content:
                    text_parsed_calls = self._parse_tool_calls_from_text(assistant_message.content)

                if not tool_calls_list and not text_parsed_calls:
                    break

                if tool_calls_list:
                    logger.info("[Agent/Ollama] iter %d tools: %s", iteration + 1,
                                [tc.function.name for tc in tool_calls_list])
                    messages.append(assistant_message.model_dump())
                    for tc in tool_calls_list:
                        func_name = tc.function.name
                        try:
                            params = json.loads(tc.function.arguments)
                        except json.JSONDecodeError:
                            params = {}
                        result = self.tool_executor.execute(func_name, params, gps)
                        tools_used.append({"tool": func_name, "params": params, "result": result})
                        messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)})

                elif text_parsed_calls:
                    logger.info("[Agent/Ollama] iter %d parsed tools: %s", iteration + 1,
                                [tc["name"] for tc in text_parsed_calls])
                    messages.append({"role": "assistant", "content": assistant_message.content})
                    tool_results_text = []
                    for tc in text_parsed_calls:
                        result = self.tool_executor.execute(tc["name"], tc["arguments"], gps)
                        tools_used.append({"tool": tc["name"], "params": tc["arguments"], "result": result})
                        tool_results_text.append(f"Tool '{tc['name']}' returned: {json.dumps(result)}")
                    messages.append({
                        "role": "user",
                        "content": (
                            "[TOOL RESULTS — now write your FINAL answer]\n"
                            "Use the data below to give a clear, structured answer in markdown. "
                            "Do NOT output JSON, do NOT call any more tools.\n\n"
                            + "\n".join(tool_results_text)
                        ),
                    })

            final_text = self._strip_thinking_tags((assistant_message.content or "").strip()) if assistant_message else ""

            # If model still output a raw JSON tool call, do a final synthesis pass
            if final_text and self._looks_like_json_tool_call(final_text) and tools_used:
                messages.append({"role": "assistant", "content": final_text})
                tool_summary = "\n".join(f"Tool '{t['tool']}' result: {json.dumps(t['result'])}" for t in tools_used)
                messages.append({
                    "role": "user",
                    "content": (
                        "[TOOL RESULTS — now write your FINAL answer]\n"
                        "Use the data below to give a clear, structured, well-formatted answer. "
                        "Do NOT output JSON. Do NOT call tools again.\n\n" + tool_summary
                    ),
                })
                response   = self.ollama_client.chat.completions.create(
                    model=self.ollama_model, messages=messages, temperature=0.1
                )
                final_text = self._strip_thinking_tags((response.choices[0].message.content or "").strip())

            if not final_text:
                final_text = "I couldn't find specific information. Please rephrase or consult official sources."

            return self._build_unified_response(final_text, tools_used, True, f"ollama/{self.ollama_model}")

        except Exception as e:
            error_msg = str(e)
            logger.error("[Agent/Ollama] Error: %s", error_msg)
            if self.gemini_available:
                logger.info("[Agent] Ollama failed — falling back to Gemini.")
                return self._run_gemini(user_text, history, gps)
            if self.groq_available:
                logger.info("[Agent] Ollama failed — falling back to Groq.")
                return self._run_groq_with_circuit_breaker(user_text, history, gps)
            fallback = self._keyword_fallback(user_text, gps)
            fallback["error_detail"] = error_msg
            return fallback

    def _build_openai_tools(self) -> list:
        return [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}} for t in TOOL_DEFINITIONS]

    def _parse_tool_calls_from_text(self, text: str) -> list:
        valid = {t["name"] for t in TOOL_DEFINITIONS}
        parsed = []
        try:
            data = json.loads(text.strip())
            if isinstance(data, dict) and data.get("name") in valid:
                parsed.append({"name": data["name"], "arguments": data.get("arguments", data.get("params", {}))})
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
        json_blocks = re.findall(r'```(?:json)?\s*({.*?})\s*```', text, re.DOTALL)
        if not json_blocks:
            json_blocks = re.findall(r'({\s*"name"\s*:.*?})', text, re.DOTALL)
        for block in json_blocks:
            try:
                data = json.loads(block)
                if isinstance(data, dict) and data.get("name") in valid:
                    parsed.append({"name": data["name"], "arguments": data.get("arguments", data.get("params", {}))})
            except (json.JSONDecodeError, TypeError):
                continue
        return parsed

    def _looks_like_json_tool_call(self, text: str) -> bool:
        stripped = text.strip()
        if stripped.startswith('{') and stripped.endswith('}'):
            try:
                data = json.loads(stripped)
                return "name" in data or "function" in data
            except (json.JSONDecodeError, TypeError):
                pass
        return False

    # ─────────────────────────────────────────────────────────────────────────
    # Gemini Agentic Loop (google-genai SDK)
    # ─────────────────────────────────────────────────────────────────────────

    def _run_gemini(self, user_text: str, history: List[Dict], gps: Optional[Dict]) -> Dict[str, Any]:
        tools_used: List[Dict] = []

        expanded_text = self._expand_follow_up_user_text(user_text, history)
        enriched_text = self._enrich_with_gps(expanded_text, gps)

        contents = []
        for turn in history:
            role       = turn.get("role", "user")
            parts_text = turn.get("parts", [""])
            contents.append(self.gemini_types.Content(
                role=role,
                parts=[self.gemini_types.Part.from_text(text=p) for p in parts_text]
            ))
        contents.append(self.gemini_types.Content(
            role="user",
            parts=[self.gemini_types.Part.from_text(text=enriched_text)]
        ))

        tool_declarations = self._build_gemini_tool_declarations()
        config = self.gemini_types.GenerateContentConfig(
            system_instruction=self._system_prompt,
            tools=[self.gemini_types.Tool(function_declarations=tool_declarations)],
            temperature=0.1,
        )

        try:
            response = None
            for iteration in range(self.MAX_TOOL_ITERATIONS):
                response   = self.gemini_client.models.generate_content(
                    model="gemini-2.0-flash", contents=contents, config=config
                )
                tool_calls = [
                    part.function_call
                    for part in response.candidates[0].content.parts
                    if hasattr(part, "function_call") and part.function_call
                ]
                if not tool_calls:
                    break

                logger.info("[Agent/Gemini] iter %d tools: %s", iteration + 1, [c.name for c in tool_calls])
                contents.append(response.candidates[0].content)

                tool_result_parts = []
                for call in tool_calls:
                    params = dict(call.args)
                    result = self.tool_executor.execute(call.name, params, gps)
                    tools_used.append({"tool": call.name, "params": params, "result": result})
                    tool_result_parts.append(
                        self.gemini_types.Part.from_function_response(name=call.name, response={"result": result})
                    )
                contents.append(self.gemini_types.Content(role="tool", parts=tool_result_parts))

            final_text = ""
            if response:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text:
                        final_text += part.text
            final_text = final_text.strip() or "I couldn't find specific information. Please rephrase or consult official sources."

            return self._build_unified_response(final_text, tools_used, True, "gemini-2.0-flash")

        except Exception as e:
            error_msg = str(e)
            logger.error("[Agent/Gemini] Error: %s", error_msg)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                logger.info("[Agent] Gemini rate-limited — falling back to Groq or keyword.")
            if self.groq_available:
                return self._run_groq_with_circuit_breaker(user_text, history, gps)
            fallback = self._keyword_fallback(user_text, gps)
            fallback["error_detail"] = error_msg
            return fallback

    def _build_gemini_tool_declarations(self) -> list:
        from google.genai import types
        return [
            types.FunctionDeclaration(
                name=tool["name"],
                description=tool["description"],
                parameters=tool["parameters"],
            )
            for tool in TOOL_DEFINITIONS
        ]

    # ─────────────────────────────────────────────────────────────────────────
    # Groq Agentic Loop (with circuit breaker)
    # ─────────────────────────────────────────────────────────────────────────

    def _run_groq_with_circuit_breaker(
        self, user_text: str, history: List[Dict], gps: Optional[Dict]
    ) -> Dict[str, Any]:
        try:
            from pybreaker import CircuitBreakerError
            from backend.modules.ai.circuit_breaker import ai_circuit_breaker
            return ai_circuit_breaker.call(self._run_groq, user_text, history, gps)
        except Exception as e:
            error_msg = str(e)
            # CircuitBreakerError or other — fall back to keyword
            logger.warning("[Agent] Groq circuit breaker / error: %s — falling back to keyword.", error_msg)
            fallback = self._keyword_fallback(user_text, gps)
            fallback["error_detail"] = error_msg
            return fallback

    def _run_groq(
        self,
        user_text: str,
        history: List[Dict],
        gps: Optional[Dict],
    ) -> Dict[str, Any]:
        t0 = time.time()
        
        try:
            from langchain_groq import ChatGroq
            from langgraph.prebuilt import create_react_agent
            from langchain_core.tools import StructuredTool
            from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
        except ImportError as e:
            logger.error("[Agent/LangGraph] Missing LangChain dependencies: %s", e)
            return self._keyword_fallback(user_text, gps)

        groq_cfg  = self._groq_cfg
        guard_cfg = self._guard_cfg

        enriched_text = user_text
        if gps:
            enriched_text += (
                f"\n\n[System context: User GPS lat={gps.get('lat')}, lon={gps.get('lon')}. "
                "Check zone restrictions if relevant.]"
            )

        # 1. Build LangChain Tools dynamically from TOOL_DEFINITIONS
        lc_tools = []
        tools_used_record = [] # To keep track for _build_unified_response
        
        for t_def in TOOL_DEFINITIONS:
            name = t_def["name"]
            desc = t_def["description"]
            # Create a closure to capture the tool name
            def tool_func(name=name, **kwargs) -> str:
                result = self.tool_executor.execute(name, kwargs, gps)
                tools_used_record.append({"tool": name, "params": kwargs, "result": result})
                return json.dumps(result)
            
            # Use type() to dynamically create a Pydantic model for args if needed, 
            # or just use StructuredTool.from_function (which requires type hints usually).
            # For simplicity, we'll let LangChain infer from a generic wrapper or we build it manually.
            
            lc_tools.append(
                StructuredTool.from_function(
                    func=tool_func,
                    name=name,
                    description=desc,
                    # We pass the raw JSON schema for args
                    args_schema=None, # LangChain can accept raw schema in other ways, but for StructuredTool it's best to use pydantic.
                )
            )
            
        # Refine tool creation to properly use the schema from TOOL_DEFINITIONS
        # Actually, ChatGroq.bind_tools can accept raw OpenAI-style dicts!
        groq_tools = []
        for t in TOOL_DEFINITIONS:
            parameters = dict(t.get("parameters", {}))
            if "type" not in parameters:
                parameters["type"] = "object"
            if "properties" not in parameters:
                parameters["properties"] = {}
            groq_tools.append({
                "type": "function",
                "function": {"name": t["name"], "description": t["description"], "parameters": parameters},
            })

        # Initialize the LLM
        llm = ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model=groq_cfg["model"],
            temperature=groq_cfg["temperature"],
            max_tokens=groq_cfg["max_tokens"]
        )
        
        # We need a custom Node for tools since we use raw dict schemas for binding, 
        # but create_react_agent prefers LangChain tools.
        # Let's wrap our ToolExecutor in LangChain tools properly.
        from pydantic import create_model, Field
        from typing import Optional, Any
        
        pydantic_tools = []
        for t in TOOL_DEFINITIONS:
            name = t["name"]
            props = t.get("parameters", {}).get("properties", {})
            fields = {}
            for k, v in props.items():
                # Define field types based on schema
                f_type = str
                if v.get("type") == "number": f_type = float
                elif v.get("type") == "integer": f_type = int
                elif v.get("type") == "boolean": f_type = bool
                
                # Default to Optional if not in required
                is_req = k in t.get("parameters", {}).get("required", [])
                if is_req:
                    fields[k] = (f_type, Field(description=v.get("description", "")))
                else:
                    fields[k] = (Optional[f_type], Field(default=None, description=v.get("description", "")))
            
            Model = create_model(f"{name}Schema", **fields)
            
            def create_func(tool_name):
                def _impl(**kwargs):
                    result = self.tool_executor.execute(tool_name, kwargs, gps)
                    tools_used_record.append({"tool": tool_name, "params": kwargs, "result": result})
                    return json.dumps(result)
                return _impl

            pydantic_tools.append(
                StructuredTool.from_function(
                    func=create_func(name),
                    name=name,
                    description=t["description"],
                    args_schema=Model
                )
            )

        # Create the LangGraph agent
        agent = create_react_agent(llm, tools=pydantic_tools)

        # Create a simplified system prompt for LangGraph to avoid confusing Groq's tool parser
        langgraph_system_prompt = (
            "You are DriveLegal AI, an expert Indian traffic law assistant.\n"
            "You have access to tools to lookup rules and fines.\n"
            "ALWAYS use the tools provided to fetch accurate information before answering.\n"
            "When using tools, provide the EXACT correct arguments.\n"
            "Once you have the tool results, synthesize them into a helpful, detailed markdown response.\n"
            "Important: Do NOT attempt to output XML or raw JSON yourself. Just call the tools normally."
        )

        # Convert history to LangChain messages
        lc_messages = [SystemMessage(content=langgraph_system_prompt)]
        for turn in history:
            role = "assistant" if turn.get("role") == "model" else turn.get("role", "user")
            parts_text = turn.get("parts", [""])
            text = " ".join(parts_text)
            if role == "assistant":
                lc_messages.append(AIMessage(content=text))
            else:
                lc_messages.append(HumanMessage(content=text))
                
        lc_messages.append(HumanMessage(content=enriched_text))

        # Run the graph
        try:
            logger.info("[Agent/LangGraph] Invoking LangGraph agent...")
            final_state = agent.invoke({"messages": lc_messages})
            
            # The last message is the AI's final response
            final_message = final_state["messages"][-1]
            final_text = final_message.content if hasattr(final_message, "content") else str(final_message)
            
            if not final_text:
                final_text = self._fb_cfg["no_info_response"]

            disclaimer = guard_cfg["disclaimer"]
            if disclaimer not in final_text:
                final_text += f"\n\n{disclaimer}"

            logger.info("[Agent/LangGraph] Finished in %.0fms", (time.time() - t0) * 1000)
            
            return self._build_unified_response(final_text, tools_used_record, True, "langgraph/" + groq_cfg["model_label"])

        except Exception as e:
            error_msg = str(e)
            logger.error("[Agent/LangGraph] Error during graph execution: %s", error_msg)
            fallback = self._keyword_fallback(user_text, gps)
            fallback["error_detail"] = error_msg
            return fallback

    # ─────────────────────────────────────────────────────────────────────────
    # Keyword Fallback (no AI available / rate-limited)
    # ─────────────────────────────────────────────────────────────────────────

    _TRAFFIC_TERMS = [
        "fine", "penalty", "challan", "helmet", "seatbelt", "seat belt",
        "speed", "license", "licence", "insurance", "drunk", "alcohol",
        "mobile", "phone", "signal", "red light", "rule", "law", "section",
        "act", "traffic", "vehicle", "driving", "car", "bike", "truck",
        "road", "zone", "puc", "echallan", "parivahan", "motor vehicle",
        "transport", "rto", "mvact", "mv act", "violation", "parking",
        "overload", "number plate", "registration", "fitness",
    ]
    _CLOSING_TERMS = ["thanks", "thank you", "ok thanks", "bye", "goodbye", "noted", "got it", "great", "ok"]
    _CURRENCY_SYMBOL = {"IN": "₹", "AE": "AED ", "GB": "£", "SG": "SGD ", "US": "USD ", "SA": "SAR "}

    def _keyword_fallback(self, text: str, gps: Optional[Dict]) -> Dict[str, Any]:
        text_lower = text.lower()
        tools_used: List[Dict] = []
        response_parts: List[str] = []
        fb    = self._fb_cfg
        hs    = self._hs_cfg
        guard = self._guard_cfg

        context_offence: Optional[str] = None
        context_state:   Optional[str] = None
        clean_text = text_lower
        if text_lower.startswith("[context:"):
            bracket_end = text_lower.find("]")
            if bracket_end != -1:
                ctx_str    = text_lower[9:bracket_end]
                clean_text = text_lower[bracket_end + 1:].strip()
                for part in ctx_str.split(","):
                    part = part.strip()
                    if part.startswith("offence:"):
                        context_offence = part.split(":", 1)[1].strip()
                    elif part.startswith("state:"):
                        context_state = part.split(":", 1)[1].strip()

        greeting_set = set(g.lower() for g in fb["greetings"])
        stripped = clean_text.strip()
        if stripped in greeting_set or any(stripped.startswith(g) for g in greeting_set):
            return self._build_unified_response(fb["greeting_response"], [], False, "keyword-fallback")

        is_closing  = any(k in clean_text for k in self._CLOSING_TERMS)
        has_traffic = any(k in clean_text for k in self._TRAFFIC_TERMS)
        if is_closing and not has_traffic:
            return self._build_unified_response(
                "You're welcome! 😊 Drive safe and feel free to ask any other traffic law questions.",
                [], False, "keyword-fallback"
            )

        if not has_traffic:
            oos = (
                "I'm DriveLegal AI — I can only help with traffic law queries. 🚦\n\n"
                "Try asking things like:\n"
                "• \"Fine for no helmet in Tamil Nadu\"\n"
                "• \"Drunk driving penalty in UAE\"\n"
                "• \"What is Section 194D?\"\n"
                "• \"Speed limit in a school zone\""
            )
            return self._build_unified_response(oos, [], False, "keyword-fallback")

        country, intl_state = self._detect_country(clean_text)
        currency_sym = self._CURRENCY_SYMBOL.get(country, "₹")

        offence = self._detect_offence(clean_text) or (context_offence.upper() if context_offence else None)
        vehicle = self._detect_vehicle(clean_text)
        state   = intl_state or (context_state.title() if context_state else self._detect_state(clean_text))

        fine_triggered = (
            any(k in clean_text for k in fb["fine_keywords"])
            or (context_offence and (intl_state or self._detect_state(clean_text) != "ALL"))
        )
        if fine_triggered and offence:
            params = {"offence_type": offence, "vehicle_class": vehicle, "state": state or "ALL", "country": country}
            result = self.tool_executor.execute("lookup_fine", params, gps)
            tools_used.append({"tool": "lookup_fine", "result": result, "params": params})
            display_name = self._oname_cfg.get(offence, offence.replace("_", " ").title())

            if result.get("found"):
                amt     = result["amount_inr"]
                rpt_amt = result.get("repeat_amount_inr", "N/A")
                sec     = result.get("section_ref", "N/A")
                st_lbl  = result.get("state", state or "National")
                response_parts.append(
                    f"**Fine for {display_name} ({vehicle}):**\n"
                    f"   • Amount: {currency_sym}{amt}\n"
                    f"   • Repeat Offence: {currency_sym}{rpt_amt}\n"
                    f"   • Section: {sec}\n"
                    f"   • Location: {st_lbl}"
                )
            else:
                response_parts.append(f"No fine data found for '{display_name}' in this location.")

            if offence and country == "IN":
                rule_result = self.tool_executor.execute("lookup_rule", {"offence_code": offence}, gps)
                if rule_result.get("found"):
                    tools_used.append({"tool": "lookup_rule", "params": {"offence_code": offence}, "result": rule_result})

        if not response_parts and any(k in clean_text for k in fb["rule_keywords"]):
            if offence:
                rule_result = self.tool_executor.execute("lookup_rule", {"offence_code": offence}, gps)
                tools_used.append({"tool": "lookup_rule", "result": rule_result, "params": {"offence_code": offence}})
                if rule_result.get("found"):
                    r = rule_result
                    response_parts.append(f"**{r['title']}** ({r.get('section', '')}):\n{r['description']}")
            if not response_parts:
                tokens = [w for w in clean_text.split() if len(w) > 2][:hs["rule_query_word_limit"]]
                result = self.tool_executor.execute("search_rules", {"keywords": tokens}, gps)
                tools_used.append({"tool": "search_rules", "result": result})
                if result.get("found") and result.get("rules"):
                    r = result["rules"][0]
                    response_parts.append(f"**{r['title']}** ({r.get('section', '')}): {r['description']}")

        if gps and any(k in clean_text for k in fb["zone_keywords"]):
            zone_result = self.tool_executor.execute("check_zone", {}, gps)
            tools_used.append({"tool": "check_zone", "result": zone_result})
            if zone_result.get("found"):
                for z in zone_result.get("zones", []):
                    mult    = z.get("fine_multiplier", 1.0)
                    response_parts.append(
                        f"📍 Active zone: **{z['name']}**"
                        + (f" (fine ×{mult})" if mult and mult > 1.0 else "")
                        + f"\n   {', '.join(z.get('rules', [z.get('zone_type', '')]))}"
                    )

        if not response_parts and self.hybrid_search:
            try:
                nlp_results = self.hybrid_search.search(text, top_k=hs["top_k"])
                relevant    = [r for r in nlp_results if r.get("score", 0) > hs["score_threshold"]]
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
                        response_parts.append(f"{i}. {header}\n   {content[:hs['content_max_chars']]}")
            except Exception as e:
                logger.warning("[Agent] HybridSearch fallback error: %s", e)

        if not response_parts:
            response_parts = [fb["unknown_query_response"]]

        response_parts.append(f"\n{guard['disclaimer']}")
        return self._build_unified_response(
            "\n".join(response_parts), tools_used, False, "keyword-fallback"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Detection helpers (used by keyword fallback)
    # ─────────────────────────────────────────────────────────────────────────

    def _detect_offence(self, text: str) -> Optional[str]:
        scores: Dict[str, int] = {}
        for offence, keywords in self._offence_keywords.items():
            hits = sum(1 for kw in keywords if kw in text)
            if hits:
                scores[offence] = hits
        return max(scores, key=lambda o: scores[o]) if scores else None

    def _detect_vehicle(self, text: str) -> str:
        for vehicle_class, keywords in self._veh_cfg.items():
            if vehicle_class.startswith("_"):
                continue
            if any(k in text for k in keywords):
                return vehicle_class
        return "GENERAL"

    def _detect_state(self, text: str) -> str:
        for state, keywords in self._state_cfg.items():
            if state.startswith("_"):
                continue
            for k in keywords:
                if len(k) <= 3:
                    if re.search(r'(?<![a-z0-9])' + re.escape(k) + r'(?![a-z0-9])', text):
                        return state
                elif k in text:
                    return state
        return "ALL"

    def _detect_country(self, text: str) -> tuple:
        if any(k in text for k in ["dubai", "uae", "united arab emirates", "sharjah", "ajman"]):
            region = "ABU_DHABI" if "abu dhabi" in text else "DUBAI"
            return "AE", region
        if "abu dhabi" in text:
            return "AE", "ABU_DHABI"
        if any(k in text for k in ["united kingdom", "london", "britain", "england", "scotland", "wales"]) \
                or re.search(r'(?<![a-z0-9])uk(?![a-z0-9])', text):
            return "GB", "ALL"
        if any(k in text for k in ["singapore", "spore", " sg "]):
            return "SG", "ALL"
        if any(k in text for k in ["saudi", "saudi arabia", "riyadh", "jeddah", "ksa"]):
            return "SA", "ALL"
        if any(k in text for k in ["usa", "united states", "america", "california", "new york", "texas"]):
            if "california" in text or "los angeles" in text or "san francisco" in text:
                return "US", "CALIFORNIA"
            if "new york" in text or "nyc" in text:
                return "US", "NEW_YORK"
            if "texas" in text or "houston" in text or "dallas" in text:
                return "US", "TEXAS"
            return "US", "ALL"
        return "IN", None

    # ─────────────────────────────────────────────────────────────────────────
    # Unified response builder (provides structured fields for all API consumers)
    # ─────────────────────────────────────────────────────────────────────────

    def _build_unified_response(
        self,
        final_text: str,
        tools_used: List[Dict],
        agent_powered: bool,
        model: str,
    ) -> Dict[str, Any]:
        fine_data      = None
        rule_data      = None
        zone_data      = None
        search_matches = []
        intent         = "general_query"
        query_summary  = "general traffic query"
        status         = "ok"

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
                intent        = "fine_lookup"
                query_summary = params.get("offence_type", "fine_lookup").lower().replace("_", " ")
                amount = fine_data["amount_inr"]
                if isinstance(amount, (int, float)) and amount > guard["max_fine_amount_inr"]:
                    logger.warning("[Agent] High fine ₹%s detected — possible hallucination.", amount)

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
                    intent        = "rule_query"
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
                    intent        = "rule_query"
                    query_summary = " ".join(params.get("keywords", []))

            elif tool_name == "check_zone" and result.get("found") and result.get("zones"):
                zone_data = {
                    "active_zones":     [z.get("name") for z in result["zones"]],
                    "applicable_rules": [z.get("rules", []) for z in result["zones"]],
                }

            elif tool_name == "hybrid_search":
                search_matches = result

        lower_text = final_text.lower()
        if "?" in final_text and any(k in lower_text for k in fb["clarification_keywords"]):
            status = "needs_clarification"
        elif not fine_data and not rule_data and any(k in lower_text for k in fb["not_found_keywords"]):
            status = "not_found"
        elif (
            not fine_data and not rule_data and intent == "general_query"
            and any(k in lower_text for k in fb["insufficient_info_keywords"])
        ):
            status = "insufficient_info"
            intent = "unknown"

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
            warnings_list.append(f"No data found. Please verify at {guard['verify_url']}.")

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
