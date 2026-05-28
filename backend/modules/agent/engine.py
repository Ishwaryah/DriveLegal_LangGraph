"""
engine.py — DriveLegal Agent Engine (LangGraph Architecture)

LangGraph Flow:
──────────────────────────────────────────────────────────────
 START
   │
   ▼
 [intent_gate] ──── greeting / meta ──────────────────► END
   │
   │  traffic query
   ├──── no LLM available ──────────────────────────► [keyword_fallback] ── END
   │
   ▼
 [call_llm]  ◄──────────────────────────────────────────────────┐
   │                                                             │
   ├── tool_calls present AND iteration < max ──► [execute_tools]
   │                                                             │ (loop)
   │  no tool_calls  OR  max iterations reached                  │
   ▼                                                             │
  END ◄──────────────────────────────────────────────────────────┘

LLM Priority per call_llm node: Ollama (local) → Gemini (cloud) → Groq (cloud)
──────────────────────────────────────────────────────────────

State fields:
  user_text, conversation_history, gps, image_base64, image_mime  — input
  messages   (Annotated[list, operator.add])  — accumulated LLM messages
  tools_used (Annotated[list, operator.add])  — accumulated tool results
  iteration, max_iterations                   — loop control
  final_text, is_conversational, agent_powered, model_label  — output
"""

import os
import re
import json
import logging
import operator
from typing import Any, Dict, List, Optional, Annotated
from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from backend.modules.agent.tools import ToolExecutor, TOOL_DEFINITIONS

logger = logging.getLogger(__name__)

_HERE = os.path.dirname(os.path.abspath(__file__))

# ─────────────────────────────────────────────────────────────────────────────
# Default System Prompt
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
# LangGraph State
# ─────────────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    # ── Input (set once at invocation) ────────────────────────────────────────
    user_text:            str
    conversation_history: List[Dict]
    gps:                  Optional[Dict]
    image_base64:         Optional[str]
    image_mime:           str

    # ── Accumulating (operator.add appends each node's list onto current) ─────
    messages:   Annotated[List[Dict], operator.add]   # full LLM message history
    tools_used: Annotated[List[Dict], operator.add]   # all tool calls made

    # ── Loop control ───────────────────────────────────────────────────────────
    iteration:      int
    max_iterations: int

    # ── Output ─────────────────────────────────────────────────────────────────
    final_text:        str
    is_conversational: bool
    agent_powered:     bool
    model_label:       str


# ─────────────────────────────────────────────────────────────────────────────
# Agent Engine
# ─────────────────────────────────────────────────────────────────────────────

class AgentEngine:
    """
    LangGraph-powered traffic law agent.

    Graph nodes
    ───────────
    intent_gate      Fast-path for greetings/meta; builds initial LLM messages.
    call_llm         Calls the active provider (Ollama → Gemini → Groq).
    execute_tools    Executes every tool_call in the last assistant message.
    keyword_fallback Pure keyword + BM25/vector search (no LLM required).

    Providers
    ─────────
    Ollama  — OpenAI-compatible API at localhost:11434 (highest priority)
    Gemini  — google-genai SDK (gemini-2.0-flash)
    Groq    — groq SDK with pybreaker circuit breaker
    keyword — always available offline
    """

    MAX_TOOL_ITERATIONS = 5

    def __init__(self, fine_lookup, rules_loader, geofencing_engine):
        self.tool_executor = ToolExecutor(fine_lookup, rules_loader, geofencing_engine)
        self.hybrid_search = None

        # Provider availability flags
        self.ollama_available = False
        self.gemini_available = False
        self.groq_available   = False

        self.ollama_client = None
        self.ollama_model  = None
        self.gemini_client = None
        self.gemini_types  = None
        self.groq_client   = None

        # Load config / prompt / keywords
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

        # HybridSearch (offline NLP fallback)
        try:
            from backend.modules.nlp.hybrid_search import HybridSearch
            rules_path  = os.path.join(_HERE, "..", "..", "data", "rules.json")
            persist_dir = os.path.join(_HERE, "..", "..", "data", "vector_db")
            self.hybrid_search = HybridSearch(rules_path, persist_dir)
            self.tool_executor.hybrid_search = self.hybrid_search
            logger.info("[Agent] HybridSearch loaded (%d documents).", len(self.hybrid_search.documents))
        except Exception as e:
            logger.warning("[Agent] HybridSearch unavailable (%s). Keyword-only fallback.", e)

        # Initialise providers in priority order
        self._init_ollama()
        if not self.ollama_available:
            self._init_gemini()
        if not self.ollama_available and not self.gemini_available:
            self._init_groq()

        # Compile the LangGraph
        self._graph = self._build_graph()
        logger.info(
            "[Agent] LangGraph compiled. Active provider: %s",
            self._active_model_label(),
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Provider initialisation
    # ─────────────────────────────────────────────────────────────────────────

    def _init_ollama(self):
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        model    = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
        try:
            from openai import OpenAI
            client = OpenAI(base_url=base_url, api_key="ollama")
            client.models.list()
            self.ollama_client    = client
            self.ollama_model     = model
            self.ollama_available = True
            logger.info("[Agent] Ollama ready — model: %s at %s", model, base_url)
        except Exception as e:
            logger.warning("[Agent] Ollama not available (%s). Trying Gemini...", e)

    def _init_gemini(self):
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
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.info("[Agent] GROQ_API_KEY not set — keyword-fallback only.")
            return
        try:
            from groq import Groq
            self.groq_client    = Groq(api_key=api_key)
            self.groq_available = True
            logger.info("[Agent] Groq ready (model=%s).", self._groq_cfg["model"])
        except Exception as e:
            logger.error("[Agent] Groq init failed: %s", e)

    # ─────────────────────────────────────────────────────────────────────────
    # LangGraph: build & routing
    # ─────────────────────────────────────────────────────────────────────────

    def _build_graph(self):
        """Compile the StateGraph that drives the agentic loop."""
        g = StateGraph(AgentState)

        g.add_node("intent_gate",      self._node_intent_gate)
        g.add_node("call_llm",         self._node_call_llm)
        g.add_node("execute_tools",    self._node_execute_tools)
        g.add_node("keyword_fallback", self._node_keyword_fallback)

        # Entry
        g.add_edge(START, "intent_gate")

        # After intent_gate: conversational → END, no-LLM → keyword, else → call_llm
        g.add_conditional_edges(
            "intent_gate",
            self._route_from_intent,
            {"end": END, "keyword": "keyword_fallback", "llm": "call_llm"},
        )

        # After call_llm: tool calls present → execute_tools, otherwise → END
        g.add_conditional_edges(
            "call_llm",
            self._route_from_llm,
            {"tools": "execute_tools", "end": END},
        )

        # Tool results loop back to call_llm for synthesis
        g.add_edge("execute_tools",    "call_llm")
        g.add_edge("keyword_fallback", END)

        return g.compile()

    def _route_from_intent(self, state: AgentState) -> str:
        if state["is_conversational"]:
            return "end"
        if not (self.ollama_available or self.gemini_available or self.groq_available):
            return "keyword"
        return "llm"

    def _route_from_llm(self, state: AgentState) -> str:
        last_msg   = state["messages"][-1] if state["messages"] else {}
        tool_calls = last_msg.get("tool_calls", [])
        if tool_calls and state["iteration"] < state["max_iterations"]:
            return "tools"
        return "end"

    # ─────────────────────────────────────────────────────────────────────────
    # LangGraph nodes
    # ─────────────────────────────────────────────────────────────────────────

    def _node_intent_gate(self, state: AgentState) -> Dict:
        """
        Fast-path for greetings / meta questions.
        For traffic queries: build the initial message list for the LLM.
        """
        user_text = state["user_text"]

        # Conversational fast-path
        conv = (
            self._try_conversational_response(self._clean_user_text(user_text))
            or self._try_conversational_response(user_text)
        )
        if conv and not state.get("image_base64"):
            return {
                "is_conversational": True,
                "final_text":        conv["response"],
                "agent_powered":     conv["agent_powered"],
                "model_label":       conv["model"],
                "messages":          [],
                "tools_used":        [],
            }

        # Build initial message list
        system_msg = {"role": "system", "content": self._system_prompt}

        history_msgs: List[Dict] = []
        for turn in state["conversation_history"]:
            role    = "assistant" if turn.get("role") == "model" else turn.get("role", "user")
            parts   = turn.get("parts", [""])
            content = parts[0] if parts else ""
            if content:
                history_msgs.append({"role": role, "content": content})

        expanded = self._expand_follow_up_user_text(user_text, state["conversation_history"])
        enriched = self._enrich_with_gps(expanded, state["gps"])

        if state.get("image_base64"):
            enriched += (
                "\n\n[Image task: inspect the attached image. If it looks like a challan, "
                "notice, traffic sign, licence, RC, insurance, or PUC document, extract "
                "visible text, vehicle number, date, violation, location, amount, and "
                "section if present. Clearly separate 'Extracted from image' from "
                "'Verified from database'.]"
            )
            user_content: Any = [
                {"type": "text", "text": enriched},
                {"type": "image_url", "image_url": {
                    "url": f"data:{state['image_mime']};base64,{state['image_base64']}"
                }},
            ]
        else:
            user_content = enriched

        return {
            "is_conversational": False,
            "agent_powered":     True,
            "messages":          [system_msg] + history_msgs + [{"role": "user", "content": user_content}],
            "tools_used":        [],
        }

    def _node_call_llm(self, state: AgentState) -> Dict:
        """
        Call the active LLM provider with the current message history.
        Falls back through Ollama → Gemini → Groq → keyword on error.
        Returns a state-update dict with the assistant message appended.
        """
        messages = state["messages"]
        errors: List[str] = []

        if self.ollama_available:
            try:
                return self._call_ollama(messages, state)
            except Exception as e:
                errors.append(f"Ollama: {e}")
                logger.warning("[Agent/Ollama] Failed — trying next provider. %s", e)

        if self.gemini_available:
            try:
                return self._call_gemini(messages, state)
            except Exception as e:
                errors.append(f"Gemini: {e}")
                logger.warning("[Agent/Gemini] Failed — trying Groq. %s", e)

        if self.groq_available:
            try:
                return self._call_groq(messages, state)
            except Exception as e:
                errors.append(f"Groq: {e}")
                logger.error("[Agent/Groq] Failed. %s", e)

        # All providers failed → inline keyword fallback
        logger.error("[Agent] All LLM providers failed: %s", errors)
        fb_result = self._keyword_fallback(state["user_text"], state["gps"])
        return {
            "final_text":    fb_result["response"],
            "tools_used":    fb_result.get("tools_used", []),
            "messages":      [{"role": "assistant", "content": fb_result["response"]}],
            "agent_powered": False,
            "model_label":   "keyword-fallback",
        }

    def _node_execute_tools(self, state: AgentState) -> Dict:
        """
        Execute every tool_call in the last assistant message.
        Appends tool-result messages and increments the iteration counter.
        """
        last_msg   = state["messages"][-1]
        tool_calls = last_msg.get("tool_calls", [])

        new_msgs:  List[Dict] = []
        new_tools: List[Dict] = []

        for tc in tool_calls:
            func_name = tc["function"]["name"]
            try:
                params = json.loads(tc["function"]["arguments"])
            except (json.JSONDecodeError, TypeError):
                params = {}

            result = self.tool_executor.execute(func_name, params, state["gps"])
            new_tools.append({"tool": func_name, "params": params, "result": result})
            new_msgs.append({
                "role":         "tool",
                "tool_call_id": tc["id"],
                "name":         func_name,
                "content":      json.dumps({"result": result}),
            })

        logger.info(
            "[Agent/LangGraph] iter %d — executed: %s",
            state["iteration"] + 1,
            [t["tool"] for t in new_tools],
        )

        return {
            "messages":   new_msgs,
            "tools_used": new_tools,
            "iteration":  state["iteration"] + 1,
        }

    def _node_keyword_fallback(self, state: AgentState) -> Dict:
        """Keyword + BM25/vector search — no LLM required."""
        result = self._keyword_fallback(state["user_text"], state["gps"])
        return {
            "final_text":    result["response"],
            "tools_used":    result.get("tools_used", []),
            "agent_powered": False,
            "model_label":   "keyword-fallback",
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Provider call helpers  (called from _node_call_llm)
    # ─────────────────────────────────────────────────────────────────────────

    def _call_groq(self, messages: List[Dict], _state: AgentState) -> Dict:
        """Call Groq, return state-update dict with assistant message."""
        groq_tools = []
        for t in TOOL_DEFINITIONS:
            params = dict(t.get("parameters", {}))
            if "type" not in params:
                params["type"] = "object"
            if "properties" not in params:
                params["properties"] = {}
            groq_tools.append({
                "type": "function",
                "function": {"name": t["name"], "description": t["description"], "parameters": params},
            })

        try:
            from backend.modules.ai.circuit_breaker import ai_circuit_breaker
            response = ai_circuit_breaker.call(
                self.groq_client.chat.completions.create,
                model       = self._groq_cfg["model"],
                messages    = messages,
                tools       = groq_tools,
                tool_choice = "auto",
                max_tokens  = self._groq_cfg["max_tokens"],
                temperature = self._groq_cfg["temperature"],
            )
        except Exception:
            # Circuit breaker unavailable — call directly
            response = self.groq_client.chat.completions.create(
                model       = self._groq_cfg["model"],
                messages    = messages,
                tools       = groq_tools,
                tool_choice = "auto",
                max_tokens  = self._groq_cfg["max_tokens"],
                temperature = self._groq_cfg["temperature"],
            )

        msg        = response.choices[0].message
        tool_calls = msg.tool_calls or []
        content    = self._strip_thinking_tags((msg.content or "").strip())

        assistant_msg: Dict = {"role": "assistant"}
        if content:
            assistant_msg["content"] = content
        if tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id":       c.id,
                    "type":     "function",
                    "function": {"name": c.function.name, "arguments": c.function.arguments},
                }
                for c in tool_calls
            ]

        return {
            "messages":      [assistant_msg],
            "final_text":    content,
            "model_label":   self._groq_cfg.get("model_label", "groq-llama3"),
            "agent_powered": True,
        }

    def _call_ollama(self, messages: List[Dict], state: AgentState) -> Dict:
        """Call Ollama (OpenAI-compatible), return state-update dict."""
        model         = self.ollama_model or ""
        system_prompt = self._system_prompt

        # Qwen3 thinking-mode workaround
        if "qwen3" in model.lower():
            system_prompt += "\n\n/no_think"
            msgs_to_send = list(messages)
            if msgs_to_send and msgs_to_send[0]["role"] == "system":
                msgs_to_send[0] = {**msgs_to_send[0], "content": system_prompt}
            else:
                msgs_to_send = [{"role": "system", "content": system_prompt}] + msgs_to_send
        else:
            msgs_to_send = messages

        # Vision models don't support native tool calling
        native_tools = not any(m in model.lower() for m in ("vision", "llava"))
        openai_tools = self._build_openai_tools() if native_tools else None

        # Non-native: inject tools as text into system prompt
        if not native_tools and msgs_to_send and msgs_to_send[0]["role"] == "system":
            tool_json = json.dumps(TOOL_DEFINITIONS, indent=2)
            extra = (
                f"\n\n### AVAILABLE TOOLS\n{tool_json}\n\n"
                "### TOOL CALLING\nOutput a raw JSON block to call a tool:\n"
                '```json\n{"name": "lookup_fine", "arguments": {"offence_type": "NO_HELMET", "vehicle_class": "2W", "state": "ALL"}}\n```\n'
                "Wait for the tool result before answering."
            )
            msgs_to_send[0] = {**msgs_to_send[0], "content": msgs_to_send[0]["content"] + extra}

        create_kwargs: Dict = {"model": model, "messages": msgs_to_send, "temperature": 0.1}
        if openai_tools:
            create_kwargs["tools"] = openai_tools

        response          = self.ollama_client.chat.completions.create(**create_kwargs)
        msg               = response.choices[0].message
        tool_calls_native = msg.tool_calls or []
        content           = self._strip_thinking_tags((msg.content or "").strip())

        # Text-parsed tool calls (non-native path)
        text_parsed: List[Dict] = []
        if not tool_calls_native and content:
            text_parsed = self._parse_tool_calls_from_text(content)

        if tool_calls_native:
            assistant_msg: Dict = {"role": "assistant"}
            if content:
                assistant_msg["content"] = content
            assistant_msg["tool_calls"] = [
                {
                    "id":       tc.id,
                    "type":     "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in tool_calls_native
            ]
            return {
                "messages":      [assistant_msg],
                "final_text":    content,
                "model_label":   f"ollama/{model}",
                "agent_powered": True,
            }

        if text_parsed:
            # Convert text-parsed calls to standard tool_calls format
            assistant_msg = {"role": "assistant", "content": content}
            assistant_msg["tool_calls"] = [
                {
                    "id":       f"txt_{i}",
                    "type":     "function",
                    "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"])},
                }
                for i, tc in enumerate(text_parsed)
            ]
            return {
                "messages":      [assistant_msg],
                "final_text":    "",
                "model_label":   f"ollama/{model}",
                "agent_powered": True,
            }

        # No tool calls — this is the final answer
        # Guard: if the content still looks like a raw JSON tool call, force a synthesis pass
        if self._looks_like_json_tool_call(content) and state["tools_used"]:
            tool_summary = "\n".join(
                f"Tool '{t['tool']}' result: {json.dumps(t['result'])}"
                for t in state["tools_used"]
            )
            synthesis_msgs = list(msgs_to_send) + [
                {"role": "assistant", "content": content},
                {
                    "role":    "user",
                    "content": (
                        "[TOOL RESULTS — write your FINAL answer now]\n"
                        "Use the data below to give a clear, structured answer. "
                        "Do NOT output JSON. Do NOT call tools again.\n\n"
                        + tool_summary
                    ),
                },
            ]
            r2      = self.ollama_client.chat.completions.create(
                model=model, messages=synthesis_msgs, temperature=0.1
            )
            content = self._strip_thinking_tags((r2.choices[0].message.content or "").strip())

        return {
            "messages":      [{"role": "assistant", "content": content}],
            "final_text":    content,
            "model_label":   f"ollama/{model}",
            "agent_powered": True,
        }

    def _call_gemini(self, messages: List[Dict], state: AgentState) -> Dict:
        """
        Call Gemini 2.0 Flash.
        Converts OpenAI-style messages ↔ google-genai Contents at the boundary.
        """
        gtypes = self.gemini_types

        contents: List[Any] = []
        for msg in messages:
            role = msg.get("role", "user")
            if role == "system":
                continue  # system instruction passed via GenerateContentConfig

            elif role == "user":
                c = msg.get("content", "")
                text = c if isinstance(c, str) else str(c)
                contents.append(gtypes.Content(
                    role="user",
                    parts=[gtypes.Part.from_text(text=text)],
                ))

            elif role == "assistant":
                if msg.get("tool_calls"):
                    parts = []
                    for tc in msg["tool_calls"]:
                        try:
                            args = json.loads(tc["function"]["arguments"])
                        except (json.JSONDecodeError, TypeError):
                            args = {}
                        parts.append(gtypes.Part.from_function_call(
                            name=tc["function"]["name"], args=args
                        ))
                    contents.append(gtypes.Content(role="model", parts=parts))
                elif msg.get("content"):
                    contents.append(gtypes.Content(
                        role="model",
                        parts=[gtypes.Part.from_text(text=msg["content"])],
                    ))

            elif role == "tool":
                name = msg.get("name", "")
                try:
                    result_dict = json.loads(msg.get("content", "{}"))
                except (json.JSONDecodeError, TypeError):
                    result_dict = {"result": msg.get("content", "")}
                contents.append(gtypes.Content(
                    role="tool",
                    parts=[gtypes.Part.from_function_response(name=name, response=result_dict)],
                ))

        tool_decls = [
            gtypes.FunctionDeclaration(
                name=t["name"], description=t["description"], parameters=t["parameters"]
            )
            for t in TOOL_DEFINITIONS
        ]
        config = gtypes.GenerateContentConfig(
            system_instruction=self._system_prompt,
            tools=[gtypes.Tool(function_declarations=tool_decls)],
            temperature=0.1,
        )

        response    = self.gemini_client.models.generate_content(
            model="gemini-2.0-flash", contents=contents, config=config
        )
        candidate   = response.candidates[0]
        text_parts  = []
        tool_calls_std: List[Dict] = []

        for part in candidate.content.parts:
            if hasattr(part, "function_call") and part.function_call:
                fc = part.function_call
                tool_calls_std.append({
                    "id":       f"gemini_{fc.name}",
                    "type":     "function",
                    "function": {
                        "name":      fc.name,
                        "arguments": json.dumps(dict(fc.args)),
                    },
                })
            if hasattr(part, "text") and part.text:
                text_parts.append(part.text)

        content       = "".join(text_parts).strip()
        assistant_msg: Dict = {"role": "assistant"}
        if content:
            assistant_msg["content"] = content
        if tool_calls_std:
            assistant_msg["tool_calls"] = tool_calls_std

        return {
            "messages":      [assistant_msg],
            "final_text":    content,
            "model_label":   "gemini-2.0-flash",
            "agent_powered": True,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def run(
        self,
        user_text: str,
        conversation_history: Optional[List[Dict]] = None,
        gps: Optional[Dict] = None,
        image_base64: Optional[str] = None,
        image_mime: str = "image/jpeg",
    ) -> Dict[str, Any]:
        """
        Invoke the LangGraph agent and return a unified response dict.

        The graph handles:
          - Greeting fast-path (no LLM call)
          - Full agentic loop (call_llm ↔ execute_tools)
          - Automatic provider fallback
          - Keyword-only fallback when no LLM is available
        """
        # Pre-graph shortcut: return structured greeting/meta responses immediately
        # so that intent, model, and session fields are populated correctly.
        if not image_base64:
            conv = (
                self._try_conversational_response(self._clean_user_text(user_text))
                or self._try_conversational_response(user_text)
            )
            if conv:
                return conv

        initial_state: AgentState = {
            "user_text":             user_text,
            "conversation_history":  conversation_history or [],
            "gps":                   gps,
            "image_base64":          image_base64,
            "image_mime":            image_mime or "image/jpeg",
            # Accumulating lists start empty
            "messages":              [],
            "tools_used":            [],
            # Loop control
            "iteration":             0,
            "max_iterations":        self.MAX_TOOL_ITERATIONS,
            # Output defaults
            "final_text":            "",
            "is_conversational":     False,
            "agent_powered":         False,
            "model_label":           "keyword-fallback",
        }

        try:
            final_state = self._graph.invoke(initial_state)
        except Exception as e:
            logger.error("[Agent] LangGraph invoke error: %s", e)
            fallback = self._keyword_fallback(user_text, gps)
            fallback["error_detail"] = str(e)
            return fallback

        final_text = final_state.get("final_text", "").strip()
        if not final_text:
            final_text = self._fb_cfg["no_info_response"]

        # Append disclaimer on Groq responses that don't already have it
        model_lbl  = final_state.get("model_label", "")
        disclaimer = self._guard_cfg["disclaimer"]
        if model_lbl.startswith("groq") and disclaimer not in final_text:
            final_text += f"\n\n{disclaimer}"

        return self._build_unified_response(
            final_text,
            final_state.get("tools_used", []),
            final_state.get("agent_powered", False),
            model_lbl or "keyword-fallback",
        )

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
        text = re.sub(
            r'<(?:thought|think|reasoning)>.*?</(?:thought|think|reasoning)>',
            '', text, flags=re.DOTALL,
        )
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
        hints = (
            "fine", "penalty", "challan", "helmet", "speed", "offence", "offense",
            "violation", "₹", "rupee", "section", "motor vehicle", "mv act", "license",
        )
        return any(h in blob for h in hints)

    def _is_follow_up_question(self, text: str, history: List[Dict]) -> bool:
        if len(history) < 2:
            return False
        clean = self._clean_user_text(text)
        if len(clean.split()) <= 2 and not any(
            k in clean for k in ("fine", "penalty", "rule", "helmet", "licence", "license")
        ):
            return False
        follow_up_keywords = (
            "5th", "5 time", "fifth", "fourth", "4th", "third", "3rd",
            "second", "2nd", "repeat", "again", "same offence", "same offense",
            "what about", "how about", "and if", "what if", "the fine", "my fine",
            "that offence", "that offense", "previous", "earlier",
        )
        if any(k in clean for k in follow_up_keywords):
            return True
        traffic_hints = (
            "fine", "penalty", "section", "rule", "offence", "offense",
            "repeat", "vehicle", "helmet", "license", "licence",
        )
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
        return any(k in clean for k in traffic_keywords) or self._message_needs_location(text)

    def _expand_follow_up_user_text(self, user_text: str, history: List[Dict]) -> str:
        if not self._is_follow_up_question(user_text, history):
            return user_text
        return (
            f"{user_text}\n\n"
            "[System Note: This is a short follow-up. Use the conversation history to "
            "understand context. Reuse the same offence, vehicle type, and state. "
            "For repeat offences (2nd, 5th time, etc.) call lookup_fine with is_repeat=true.]"
        )

    def _try_conversational_response(self, user_text: str) -> Optional[Dict[str, Any]]:
        """Return a canned response for greetings / meta questions (no tools needed)."""
        text_lower  = self._clean_user_text(user_text)
        model_label = self._active_model_label()

        greetings = (
            "hi", "hello", "hey", "hii", "hola",
            "good morning", "good evening", "good afternoon", "namaste",
        )
        if (
            text_lower in greetings
            or text_lower.startswith(("hi ", "hello ", "hey "))
            or re.match(r"^(hi|hello|hey|hii|namaste)[\s!.]*$", text_lower)
        ):
            return {
                "status":        "ok",
                "intent":        "greeting",
                "response": (
                    "Hello! I'm DriveLegal AI — your traffic law assistant.\n\n"
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

        meta_keywords = (
            "which model", "what model", "running on", "what ai", "who are you",
            "which llm", "what llm", "are you gemini", "are you ollama", "your model",
            "are you groq",
        )
        if any(k in text_lower for k in meta_keywords):
            if self.ollama_available:
                backend = f"local Ollama ({self.ollama_model})"
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

        return None

    def _enrich_with_gps(self, user_text: str, gps: Optional[Dict]) -> str:
        if not gps or not self._message_needs_location(user_text):
            return user_text
        return (
            f"{user_text}\n\n"
            f"[System context: User GPS lat={gps.get('lat')}, lon={gps.get('lon')}. "
            "Use check_zone only if this question is about location-based restrictions.]"
        )

    def _build_openai_tools(self) -> List[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name":        t["name"],
                    "description": t["description"],
                    "parameters":  t["parameters"],
                },
            }
            for t in TOOL_DEFINITIONS
        ]

    def _parse_tool_calls_from_text(self, text: str) -> List[Dict]:
        """Extract JSON tool-call blocks from raw LLM text (non-native tool calling)."""
        valid  = {t["name"] for t in TOOL_DEFINITIONS}
        parsed: List[Dict] = []

        try:
            data = json.loads(text.strip())
            if isinstance(data, dict) and data.get("name") in valid:
                parsed.append({
                    "name":      data["name"],
                    "arguments": data.get("arguments", data.get("params", {})),
                })
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass

        blocks = re.findall(r'```(?:json)?\s*({.*?})\s*```', text, re.DOTALL)
        if not blocks:
            blocks = re.findall(r'({\s*"name"\s*:.*?})', text, re.DOTALL)
        for block in blocks:
            try:
                data = json.loads(block)
                if isinstance(data, dict) and data.get("name") in valid:
                    parsed.append({
                        "name":      data["name"],
                        "arguments": data.get("arguments", data.get("params", {})),
                    })
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
                    "greeting_response":          "Hello! I'm DriveLegal AI — your Indian traffic law assistant.\n\nHow can I help you today?",
                    "unknown_query_response":     "Sorry, I didn't understand that. Try asking about a specific traffic rule or fine.",
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
            logger.warning("[Agent] Could not load system_prompt.txt (%s) — using built-in.", exc)
        return _DEFAULT_SYSTEM_PROMPT

    @staticmethod
    def _load_offence_keywords() -> Dict[str, List[str]]:
        path = os.path.join(_HERE, "offence_keywords.json")
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            return {k: v for k, v in data.items() if not k.startswith("_")}
        except Exception as exc:
            logger.warning("[Agent] Could not load offence_keywords.json (%s) — minimal fallback.", exc)
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
    # Keyword fallback (no LLM — BM25 + rule-based)
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
    _CLOSING_TERMS  = ["thanks", "thank you", "ok thanks", "bye", "goodbye", "noted", "got it", "great", "ok"]
    _CURRENCY_SYMBOL = {"IN": "₹", "AE": "AED ", "GB": "£", "SG": "SGD ", "US": "USD ", "SA": "SAR "}

    def _keyword_fallback(self, text: str, gps: Optional[Dict]) -> Dict[str, Any]:
        text_lower     = text.lower()
        tools_used:    List[Dict] = []
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

        greeting_set = {g.lower() for g in fb["greetings"]}
        stripped = clean_text.strip()
        if stripped in greeting_set or any(stripped.startswith(g) for g in greeting_set):
            return self._build_unified_response(fb["greeting_response"], [], False, "keyword-fallback")

        is_closing  = any(k in clean_text for k in self._CLOSING_TERMS)
        has_traffic = any(k in clean_text for k in self._TRAFFIC_TERMS)
        if is_closing and not has_traffic:
            return self._build_unified_response(
                "You're welcome! Drive safe and feel free to ask any other traffic law questions.",
                [], False, "keyword-fallback",
            )

        if not has_traffic:
            oos = (
                "I'm DriveLegal AI — I can only help with traffic law queries.\n\n"
                "Try asking things like:\n"
                "• \"Fine for no helmet in Tamil Nadu\"\n"
                "• \"Drunk driving penalty in UAE\"\n"
                "• \"What is Section 194D?\"\n"
                "• \"Speed limit in a school zone\""
            )
            return self._build_unified_response(oos, [], False, "keyword-fallback")

        country, intl_state = self._detect_country(clean_text)
        currency_sym        = self._CURRENCY_SYMBOL.get(country, "₹")

        offence = self._detect_offence(clean_text) or (context_offence.upper() if context_offence else None)
        vehicle = self._detect_vehicle(clean_text)
        state   = intl_state or (context_state.title() if context_state else self._detect_state(clean_text))

        fine_triggered = (
            any(k in clean_text for k in fb["fine_keywords"])
            or (context_offence and (intl_state or self._detect_state(clean_text) != "ALL"))
        )
        if fine_triggered and offence:
            params = {
                "offence_type": offence,
                "vehicle_class": vehicle,
                "state": state or "ALL",
                "country": country,
            }
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
                    response_parts.append(
                        f"**{r['title']}** ({r.get('section', '')}):\n{r['description']}"
                    )
            if not response_parts:
                tokens = [w for w in clean_text.split() if len(w) > 2][:hs["rule_query_word_limit"]]
                result = self.tool_executor.execute("search_rules", {"keywords": tokens}, gps)
                tools_used.append({"tool": "search_rules", "result": result})
                if result.get("found") and result.get("rules"):
                    r = result["rules"][0]
                    response_parts.append(
                        f"**{r['title']}** ({r.get('section', '')}): {r['description']}"
                    )

        if gps and any(k in clean_text for k in fb["zone_keywords"]):
            zone_result = self.tool_executor.execute("check_zone", {}, gps)
            tools_used.append({"tool": "check_zone", "result": zone_result})
            if zone_result.get("found"):
                for z in zone_result.get("zones", []):
                    mult = z.get("fine_multiplier", 1.0)
                    response_parts.append(
                        f"Active zone: **{z['name']}**"
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

    # ── Detection helpers (keyword fallback) ──────────────────────────────────

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
    # Unified response builder
    # ─────────────────────────────────────────────────────────────────────────

    def _build_unified_response(
        self,
        final_text: str,
        tools_used: List[Dict],
        agent_powered: bool,
        model: str,
    ) -> Dict[str, Any]:
        fine_data:      Optional[Dict] = None
        rule_data:      Optional[Dict] = None
        zone_data:      Optional[Dict] = None
        search_matches: List          = []
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

        warnings_list: List[str] = []
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
