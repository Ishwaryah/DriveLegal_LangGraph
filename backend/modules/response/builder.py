"""
Response Builder  v2.0
=======================
Assembles structured responses from NLP results.

Data-source priority (fine amount):
  1. FineLookup  — fines.db (authoritative, seeded from official data)
  2. RulesLoader — rule.national_fine (schema v2.0, Motor Vehicles Act)
  3. ChallanCalculator — computed from violations_db (tagged dataset)

Anti-hallucination contract
  ─ If no authoritative data is found, status = "not_found" and we direct
    the user to parivahan.gov.in. We never invent amounts or section numbers.
  ─ The source of every fine amount is labelled in the response.
  ─ AI text generation is constrained to the structured context — never allowed
    to generate amounts or legal provisions independently.
"""

import logging
from typing import Any, Dict, List, Optional

from backend.modules.legal_formatter import (
    format_legal_response,
    suggest_violations,
    build_violation_row,
)

logger = logging.getLogger(__name__)

# Minimum search score threshold for template-path fallback (no AI engine)
# AI path uses a lower threshold — it can reason over lower-confidence passages
_MIN_SEARCH_SCORE     = 0.45   # template path
_MIN_SEARCH_SCORE_AI  = 0.10   # AI path — cast a wider net

# Source labels shown in fine object
_SRC_DB          = "fines_db"
_SRC_RULE        = "national_act"
_SRC_CALCULATOR  = "challan_calculator"
_SRC_VECTOR      = "vector_search"


class ResponseBuilder:
    """
    Coordinates fine lookup, rule retrieval, geofencing, and AI text generation.

    Parameters
    ----------
    fine_lookup         : FineLookup instance (SQLite) — may be None (offline)
    rules_loader        : RulesLoader instance
    geofencing_engine   : GeofencingEngine instance — may be None
    ai_engine           : AIProvider instance — may be None
    challan_calculator  : ChallanCalculator instance — may be None
    """

    def __init__(
        self,
        fine_lookup:        Any,
        rules_loader:       Any,
        geofencing_engine:  Any,
        ai_engine:          Optional[Any] = None,
        challan_calculator: Optional[Any] = None,
    ):
        self.fine_lookup        = fine_lookup
        self.rules_loader       = rules_loader
        self.geofencing_engine  = geofencing_engine
        self.ai_engine          = ai_engine
        self.challan_calculator = challan_calculator

    # ── Public entry point ────────────────────────────────────────────────────

    async def build(
        self,
        nlp_result: Dict[str, Any],
        gps: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Build and return the final structured response.

        Never raises — all internal errors are caught and logged; the response
        degrades gracefully rather than propagating exceptions to the caller.
        """
        intent   = (nlp_result.get("intent") or "unknown").lower()
        warnings: List[str] = []

        response: Dict[str, Any] = {
            "status":       "ok",
            "intent":       intent,
            "query_summary": self._generate_summary(nlp_result),
            "fine":         None,
            "rule":         None,
            "zone":         None,
            "offline_mode": self.ai_engine is None,
            "warnings":     warnings,
        }

        # ── 1. Geofencing ─────────────────────────────────────────────────────
        if gps and self.geofencing_engine:
            lat = gps.get("lat")
            lon = gps.get("lon")
            if lat is not None and lon is not None:
                try:
                    zones = self.geofencing_engine.get_applicable_rules(lat, lon) or []
                    response["zone"] = {
                        "active_zones":     [z.get("name") or z.get("zone_id", "unknown") for z in zones],
                        "applicable_rules": [z.get("rules", []) for z in zones],
                    }
                except Exception as e:
                    logger.warning("Geofencing error: %s", e)

        # ── 2. Early-exit for pipeline errors only ───────────────────────────────
        # "insufficient_info" is NO longer a hard exit — the AI can answer any
        # question from semantic search context even without structured entities.
        # We only bail out on a true pipeline error or when there is no AI and
        # no search results at all (nothing to work with).
        pipeline_status = nlp_result.get("status")

        if pipeline_status == "error":
            response["status"] = "error"
            response["text"]   = "I encountered an error while processing your request."
            return response

        if pipeline_status == "insufficient_info" and not self.ai_engine:
            # No AI engine — check if search at least found something usable
            search_matches = nlp_result.get("search_matches") or []
            has_useful_search = any(
                (m.get("score") or 0) >= _MIN_SEARCH_SCORE for m in search_matches
            )
            if not has_useful_search:
                response["status"] = "insufficient_info"
                response["text"]   = self._generate_text_response(response, nlp_result)
                return response
            # Search found something — fall through to template synthesis

        # ── Extract NLP fields (with None-safe defaults) ──────────────────────
        offence_code  = nlp_result.get("offence_type")
        state         = nlp_result.get("state") or "ALL"
        vehicle_class = nlp_result.get("vehicle_class") or "LMV"
        is_repeat     = bool(nlp_result.get("repeat_offence"))
        section_ref   = nlp_result.get("section_ref")
        search_matches = nlp_result.get("search_matches") or []

        effective_country = nlp_result.get("country") or "IN"

        # ── 2b. Clarification gate ────────────────────────────────────────────
        # When the system understands a violation (or the query looks like one)
        # but the user has not provided their state/location, ask FIRST — don't
        # dump national rates and hope the user notices the location prompt.
        #
        # SKIPPED for general_query / procedure_query intents: questions like
        # "what are the speed limits?" or "how do I renew my license?" don't
        # need a state to give a useful answer from the knowledge base.
        #
        # Condition: we have a signal about what the violation is BUT state=None
        # and no GPS.  We skip this gate if state was already captured in session
        # (context_resolver fills it in before we reach here).
        state_missing = nlp_result.get("state") is None
        state_independent_intent = intent in ("general_query", "procedure_query")
        has_violation_signal = bool(offence_code or section_ref) or any(
            (m.get("score") or 0) >= 0.35 for m in search_matches
        )

        if state_missing and has_violation_signal and not state_independent_intent:
            response["status"] = "needs_clarification"
            response["understood_violation"] = offence_code
            try:
                if self.ai_engine:
                    response["text"] = await self._generate_clarification_response(nlp_result)
                else:
                    response["text"] = self._template_clarification(nlp_result)
            except Exception as e:
                logger.error("Clarification generation error: %s", e)
                response["text"] = self._template_clarification(nlp_result)
            # Persist what we understood so the next turn can inherit it via session.
            # in_clarification=True tells the context resolver to always carry
            # offence_type forward regardless of follow-up text length or intent.
            # Only set in_clarification when there is actually an offence to carry —
            # general queries (no offence_code) should not lock the session into a
            # clarification loop that produces raw state-data responses on follow-up.
            session_payload = {
                "offence_type":  offence_code,
                "vehicle_class": vehicle_class if nlp_result.get("vehicle_class") else None,
                "section_ref":   section_ref,
            }
            if offence_code or section_ref:
                session_payload["in_clarification"] = True
            response["session"] = {k: v for k, v in session_payload.items() if v is not None}
            return response

        response["needs_location"] = False

        # ── 3. Rule lookup ────────────────────────────────────────────────────
        rule_data: Optional[Dict] = None
        if self.rules_loader:
            try:
                if section_ref:
                    rule_data = self.rules_loader.get_by_section(section_ref)
                if not rule_data and offence_code:
                    rule_data = self.rules_loader.get_by_offence_code(offence_code, state)
                
                # Ensure country match
                if rule_data and rule_data.get("country") != effective_country:
                    rule_data = None
            except Exception as e:
                logger.warning("Rule lookup error: %s", e)

        if rule_data:
            response["rule"] = {
                "rule_id":       rule_data.get("rule_id"),
                "title":         rule_data.get("title"),
                "description":   rule_data.get("description"),
                "section":       rule_data.get("section"),
                "compoundable":  rule_data.get("compoundable"),
                "imprisonment":  rule_data.get("imprisonment"),
                "state_override": state if rule_data.get("is_state_override") else None,
                "tags":          rule_data.get("tags", []),
            }

        # ── 4. Fine lookup — three-tier with source labelling ─────────────────
        if offence_code or section_ref:
            fine_amount = None

            # Apply Zone Multiplier if available
            zone_multiplier = 1.0
            if response.get("zone") and response["zone"].get("applicable_rules"):
                # Use the highest multiplier from active zones
                for zone_props_list in response["zone"]["applicable_rules"]:
                    for zone_props in (zone_props_list if isinstance(zone_props_list, list) else [zone_props_list]):
                        m = zone_props.get("fine_multiplier", 1.0)
                        if m > zone_multiplier:
                            zone_multiplier = m

            # Tier 1: fines.db
            if self.fine_lookup:
                try:
                    fine_data = None
                    if offence_code:
                        fine_data = self.fine_lookup.query(
                            offence_code, 
                            vehicle_class, 
                            state, 
                            country=effective_country,
                            repeat=is_repeat
                        )

                    # Section-based fallback when offence_code lookup misses
                    if not fine_data and section_ref:
                        rows = self.fine_lookup.query_by_section(
                            section_ref, 
                            country=effective_country
                        )
                        if rows:
                            row = rows[0]
                            amount = row.get("max_fine_local") if is_repeat else row.get("min_fine_local")
                            if amount is not None:
                                fine_data = {
                                    "amount_inr":        amount,
                                    "repeat_amount_inr": row.get("max_fine_local"),
                                    "section_ref":       row.get("mv_act_section") or section_ref,
                                    "source_url":        "",
                                    "fetched_at":        None,
                                    "currency":          row.get("currency"),
                                    "notes":             row.get("notes"),
                                }

                    if fine_data and fine_data.get("amount_inr") is not None:
                        base_amt = fine_data.get("amount_inr")
                        final_amt = int(base_amt * zone_multiplier)
                        response["fine"] = {
                            "amount_inr":        final_amt,
                            "base_amount":       base_amt,
                            "repeat_amount_inr": fine_data.get("repeat_amount_inr"),
                            "section_ref":       fine_data.get("section_ref"),
                            "source_url":        fine_data.get("source_url"),
                            "data_as_of":        fine_data.get("fetched_at"),
                            "data_source":       _SRC_DB,
                            "zone_multiplier":   zone_multiplier if zone_multiplier > 1.0 else None
                        }
                        fine_amount = final_amt
                        if zone_multiplier > 1.0:
                            warnings.append(f"Zone-specific compounding fee applied ({zone_multiplier}x multiplier).")
                except Exception as e:
                    logger.warning("FineLookup error: %s", e)

            # Tier 2: rule.national_fine (schema v2.0)
            if fine_amount is None and rule_data and self.rules_loader:
                try:
                    amt = self.rules_loader.get_fine_from_rule(rule_data, is_repeat, vehicle_class)
                    if amt is not None:
                        final_amt = int(amt * zone_multiplier)
                        section = rule_data.get("section", "")
                        response["fine"] = {
                            "amount_inr":        final_amt,
                            "base_amount":       amt,
                            "repeat_amount_inr": self.rules_loader.get_fine_from_rule(rule_data, True, vehicle_class),
                            "section_ref":       section,
                            "source_url":        "https://parivahan.gov.in",
                            "data_as_of":        None,
                            "data_source":       _SRC_RULE,
                            "zone_multiplier":   zone_multiplier if zone_multiplier > 1.0 else None
                        }
                        fine_amount = final_amt
                        warnings.append(
                            "Fine derived from Motor Vehicles Act national base rate. "
                            "State-specific amounts may differ."
                        )
                        if zone_multiplier > 1.0:
                            warnings.append(f"Zone-specific compounding fee applied ({zone_multiplier}x multiplier).")
                except Exception as e:
                    logger.warning("Rule fine extraction error: %s", e)

            # Tier 3: ChallanCalculator (dataset-based computation)
            if fine_amount is None and self.challan_calculator and offence_code:
                try:
                    query_str = (rule_data.get("title") or offence_code.replace("_", " ")).lower()
                    calc      = self.challan_calculator.calculate(
                        violation_query=query_str,
                        state=state if state != "ALL" else "National",
                        vehicle_type=vehicle_class,
                        offence_number=2 if is_repeat else 1,
                    )
                    if calc.get("found") and calc.get("applicable_fine"):
                        response["fine"] = {
                            "amount_inr":        calc["applicable_fine"],
                            "repeat_amount_inr": None,
                            "section_ref":       calc.get("section", ""),
                            "source_url":        "https://parivahan.gov.in",
                            "data_as_of":        None,
                            "data_source":       _SRC_CALCULATOR,
                            "zone_multiplier":   calc.get("zone_multiplier", 1.0),
                            "final_fine":        calc.get("final_fine"),
                            "compoundable":      calc.get("compoundable"),
                            "dl_action":         calc.get("dl_action"),
                        }
                        warnings.append(
                            "Fine computed from Motor Vehicles (Amendment) Act base data. "
                            "Verify current amount at echallan.parivahan.gov.in."
                        )
                except Exception as e:
                    logger.warning("ChallanCalculator error: %s", e)

        # ── 5. Search fallback ────────────────────────────────────────────────
        search_matches = nlp_result.get("search_matches") or []
        # Strip raw administrative chunks (STATE_*, CSV_*, DS_*) — these are
        # internal data dumps, not user-readable knowledge-base passages.
        _ADMIN_PREFIXES = ("STATE_", "CSV_", "DS_")
        search_matches = [
            m for m in search_matches
            if not any((m.get("rule_id") or "").startswith(p) for p in _ADMIN_PREFIXES)
        ]
        # For general/procedure queries use a lower threshold — answer from
        # knowledge base even if confidence is moderate.
        _effective_threshold = (
            _MIN_SEARCH_SCORE_AI if intent in ("general_query", "procedure_query")
            else _MIN_SEARCH_SCORE
        )
        # MV177/MV177A are catch-all rules ("General Violation of Traffic Rules")
        # that match every broad query via BM25 keyword overlap; exclude them so
        # specific rules surface first.
        _CATCHALL_IDS = {"MV177", "MV177A"}
        relevant = [m for m in search_matches if (m.get("score") or 0) >= _effective_threshold]
        if relevant and not response["rule"]:
            # Prefer a specific result over the generic catch-all when available.
            specific = [m for m in relevant if m.get("rule_id") not in _CATCHALL_IDS]
            candidates = specific if specific else relevant
            top = candidates[0]
            meta = top.get("metadata") or {}
            # For general/procedure intents, aggregate up to 3 results into the
            # description so the AI has richer context to synthesise an answer.
            if intent in ("general_query", "procedure_query") and len(candidates) > 1:
                combined = "\n\n".join(
                    f"[{(m.get('metadata') or {}).get('title') or m.get('rule_id', '')}] "
                    f"{(m.get('content') or '')[:1200]}"
                    for m in candidates[:3]
                )
                description = combined
            else:
                description = top.get("content", "")
            response["rule"] = {
                "rule_id":     top.get("rule_id"),
                "title":       meta.get("title") or top.get("rule_id"),
                "description": description,
                "section":     meta.get("section"),
                "source":      _SRC_VECTOR,
            }

        # ── 6. Status consolidation ───────────────────────────────────────────
        if response["fine"] or response["rule"]:
            response["status"] = "ok"
        elif intent in ("fine_lookup", "rule_query"):
            response["status"] = "not_found"
            warnings.append(
                "No data found in the database. "
                "Please verify at https://echallan.parivahan.gov.in."
            )
        elif intent in ("general_query", "procedure_query"):
            response["status"] = "not_found"
            warnings.append(
                "I don't have specific information on that in my knowledge base. "
                "Please check https://parivahan.gov.in for official guidance."
            )

        # ── 7. Text synthesis ─────────────────────────────────────────────────
        try:
            if self.ai_engine:
                response["text"] = await self._generate_ai_response(response, nlp_result)
            else:
                response["text"] = self._generate_text_response(response, nlp_result)
            
            # 8. Translation (Regional Language Support)
            lang = nlp_result.get("lang", "en")
            if lang != "en" and response.get("text"):
                response["text"] = self._apply_regional_translation(response["text"], lang)
        except Exception as e:
            logger.error("Text generation error: %s", e)
            response["text"] = self._generate_text_response(response, nlp_result)

        return response

    def _apply_regional_translation(self, text: str, lang: str) -> str:
        """Simple translation layer for key terms in the response."""
        translations = {
            "hi": {
                "The fine is": "जुर्माना है",
                "Repeat offence": "बार-बार अपराध",
                "non-compoundable": "गैर-समाधेय (अदालत जाना होगा)",
                "compoundable": "समाधेय (ऑनलाइन भुगतान संभव)",
                "Possible imprisonment": "संभावित कारावास",
                "Which city or state": "कौन सा शहर या राज्य",
                "I need a bit more information": "मुझे थोड़ी और जानकारी चाहिए",
                "The legal database is temporarily unavailable": "कानूनी डेटाबेस अस्थायी रूप से अनुपलब्ध है",
            },
            "ta": {
                "The fine is": "அபராதம்",
                "Repeat offence": "மீண்டும் மீண்டும் குற்றம்",
                "non-compoundable": "நீதிமன்றத்தில் ஆஜராக வேண்டும்",
                "compoundable": "இடத்திலேயே அல்லது ஆன்லைனில் தீர்க்கலாம்",
                "Possible imprisonment": "சிறைத்தண்டனை வாய்ப்பு",
                "Which city or state": "எந்த நகரம் அல்லது மாநிலம்",
                "I need a bit more information": "எனக்கு இன்னும் கொஞ்சம் தகவல் தேவை",
                "Section": "பிரிவு",
            },
            "ar": {
                "The fine is": "الغرامة هي",
                "Repeat offence": "مخالفة متكررة",
                "non-compoundable": "غير قابل للتسوية — إلزامي المثول أمام المحكمة",
                "compoundable": "قابل للتسوية — يمكن الدفع إلكترونياً",
                "Possible imprisonment": "عقوبة السجن المحتملة",
                "Which city or state": "أي مدينة أو ولاية",
                "I need a bit more information": "أحتاج إلى مزيد من المعلومات",
                "Section": "المادة",
                "Verify at": "تحقق من",
                "black points": "نقاط سوداء",
                "licence confiscation": "مصادرة الرخصة",
            },
        }

        lang_map = translations.get(lang, {})
        translated_text = text
        for en, native in lang_map.items():
            translated_text = translated_text.replace(en, native)
        return translated_text

    # ── AI response (guardrailed) ─────────────────────────────────────────────

    # ── Clarification helpers ─────────────────────────────────────────────────

    # Human-readable labels for offence codes shown in clarification messages
    _OFFENCE_LABELS: Dict[str, str] = {
        "RED_LIGHT_JUMPING":      "jumped a red signal",
        "SPEED_EXCESS":           "exceeded the speed limit",
        "DRUNK_DRIVING":          "drove under the influence of alcohol",
        "NO_HELMET":              "rode without a helmet",
        "NO_SEATBELT":            "drove without a seatbelt",
        "NO_LICENSE":             "drove without a valid license",
        "NO_INSURANCE":           "drove without valid insurance",
        "NO_RC":                  "drove without a registration certificate",
        "MOBILE_PHONE":           "used a mobile phone while driving",
        "WRONG_SIDE":             "drove on the wrong side",
        "DANGEROUS_DRIVING":      "drove dangerously/rashly",
        "OVERLOADING":            "overloaded the vehicle",
        "JUVENILE_DRIVING":       "an underage person was driving",
        "PUC_VIOLATION":          "drove without a valid PUC certificate",
        "PARKING_VIOLATION":      "committed a parking violation",
        "STUNT_DRIVING":          "performed stunts or street racing",
        "EMERGENCY_OBSTRUCTION":  "obstructed an emergency vehicle",
        "TINTED_GLASS":           "used illegal tinted glass",
        "TRIPLE_RIDING":          "carried three people on a two-wheeler",
        "WRONG_OVERTAKING":       "made an unsafe/illegal overtake",
        "VEHICLE_MODIFICATION":   "made illegal vehicle modifications",
        "DISOBEY_POLICE":         "disobeyed a traffic police signal",
    }

    async def _generate_clarification_response(self, nlp_result: Dict[str, Any]) -> str:
        """
        Ask the AI to echo what it understood and ask ONE focused clarifying
        question.  The AI has full context of the original query.
        """
        offence_code = nlp_result.get("offence_type")
        understood   = self._OFFENCE_LABELS.get(offence_code, "") if offence_code else ""
        vehicle      = nlp_result.get("vehicle_class")

        missing_items = ["city/state where this happened"]
        if not vehicle:
            missing_items.append("type of vehicle you were driving")

        system_instruction = (
            "You are DriveLegal AI, a conversational Indian traffic law assistant.\n"
            "Your task RIGHT NOW is to:\n"
            "1. In one short sentence, confirm what you understood from the user's message "
            "(e.g. 'Got it — you ran a red signal.').\n"
            "2. Ask exactly ONE focused follow-up question to get the most important "
            "missing piece of information. Prioritise location (city/state) first.\n"
            "Keep the entire response under 3 sentences. Be friendly and direct.\n"
            "Do NOT provide any fines, rules, or legal advice yet — that comes after "
            "the user answers your question."
        )

        context = f"User query: {nlp_result.get('raw_text', '')}\n"
        if understood:
            context += f"Understood violation: {understood}\n"
        context += f"Missing information needed: {', '.join(missing_items)}"

        return await self.ai_engine.generate_response(context, system_instruction)

    def _template_clarification(self, nlp_result: Dict[str, Any]) -> str:
        """Template fallback when AI engine is not available."""
        offence_code = nlp_result.get("offence_type")
        understood   = self._OFFENCE_LABELS.get(offence_code, "") if offence_code else ""

        if understood:
            return (
                f"Got it — you {understood}. "
                "Which city or state did this happen in? "
                "(For example: 'in Chennai' or 'in Delhi')"
            )
        # No structured offence detected — ask what they need help with
        return (
            "I want to make sure I give you accurate information. "
            "Could you tell me which city or state this happened in, "
            "and briefly what the violation was?"
        )

    # ── AI response (full answer) ─────────────────────────────────────────────

    async def _generate_ai_response(
        self,
        response_data: Dict[str, Any],
        nlp_result: Dict[str, Any],
    ) -> str:
        system_instruction = (
            "You are DriveLegal AI, a helpful assistant for Indian traffic laws, "
            "road rules, and driving regulations. "
            "You must answer ANY question a user asks about traffic rules, fines, "
            "licenses, challans, road safety, road signs, or driving in India.\n\n"
            "GROUNDING RULES (never break these):\n"
            "1. For specific fine AMOUNTS: only quote figures present in STRUCTURED DATA. "
            "   Never invent rupee amounts. If not in STRUCTURED DATA, say "
            "   'verify the exact amount at echallan.parivahan.gov.in'.\n"
            "2. For section numbers: only cite sections present in STRUCTURED DATA or KNOWLEDGE BASE. "
            "   Do not fabricate section numbers.\n"
            "3. For imprisonment / DL suspension: only state what STRUCTURED DATA contains.\n\n"
            "ANSWERING RULES:\n"
            "4. Answer every question — never refuse a traffic law or road rule question.\n"
            "5. Use KNOWLEDGE BASE passages as your primary source of information. "
            "   Quote or paraphrase them accurately.\n"
            "6. You may supplement with general Indian traffic law knowledge when the "
            "   KNOWLEDGE BASE has no relevant passage, but clearly prefix such statements "
            "   with 'Generally under Indian traffic law...'.\n"
            "7. Always use ₹ for Indian amounts.\n"
            "8. When a specific violation or fine is mentioned: state the law section, fine amount, "
            "   whether it is compoundable, and a plain-English explanation — all from STRUCTURED DATA / "
            "   KNOWLEDGE BASE where available.\n"
            "9. For GENERAL ROAD RULE questions (speed limits, lane rules, overtaking, night driving, "
            "   road signs, documents required, etc.): answer directly from KNOWLEDGE BASE. "
            "   These questions do NOT need a state — provide the national rule and note if states vary.\n"
            "10. For PROCEDURAL questions (how to renew DL, how to contest a challan, how to apply, etc.): "
            "    answer from KNOWLEDGE BASE passages. If no passage covers it, say: "
            "    'I don't have the specific procedure in my database — please check "
            "    https://parivahan.gov.in for the official steps.'\n"
            "11. For FINE LOOKUP questions where state is unknown: give the national base rate "
            "    and then ask: 'Which state are you in? Fines may vary by state.'\n"
            "12. Format responses clearly: use numbered lists for multi-step rules, "
            "    bold for key terms, and keep answers concise but complete."
        )

        fine_ctx = response_data.get("fine")
        rule_ctx = response_data.get("rule")
        zone_ctx = response_data.get("zone")

        # ── STRUCTURED DATA block (DB-verified facts) ─────────────────────────
        structured_lines: List[str] = []
        if fine_ctx:
            structured_lines.append(
                f"Fine: ₹{fine_ctx.get('amount_inr')} "
                f"(source: {fine_ctx.get('data_source')}, "
                f"section: {fine_ctx.get('section_ref')})"
            )
            if fine_ctx.get("repeat_amount_inr"):
                structured_lines.append(f"Repeat offence fine: ₹{fine_ctx['repeat_amount_inr']}")
        if rule_ctx:
            structured_lines.append(
                f"Rule: {rule_ctx.get('title')} — {rule_ctx.get('description', '')[:1200]}"
            )
            if rule_ctx.get("compoundable") is False:
                structured_lines.append("Non-compoundable: court appearance mandatory.")
            elif rule_ctx.get("compoundable") is True:
                structured_lines.append("Compoundable: can be settled on-spot or online.")
            if rule_ctx.get("imprisonment"):
                structured_lines.append(f"Imprisonment risk: {rule_ctx['imprisonment']}")
        if zone_ctx and zone_ctx.get("active_zones"):
            structured_lines.append(f"Active zones: {', '.join(zone_ctx['active_zones'])}")
        if response_data.get("warnings"):
            structured_lines.append("Notes: " + "; ".join(response_data["warnings"]))
        if response_data.get("needs_location"):
            structured_lines.append(
                "State not provided — showing national base rates. Ask user for their state."
            )

        structured_block = (
            "STRUCTURED DATA (DB-verified):\n" + "\n".join(structured_lines)
            if structured_lines else "STRUCTURED DATA: none found for this query"
        )

        # ── KNOWLEDGE BASE block (semantic search results) ────────────────────
        search_matches = nlp_result.get("search_matches") or []
        kb_lines: List[str] = []
        for m in search_matches[:5]:
            content = (m.get("content") or "").strip()
            title   = (m.get("metadata") or {}).get("title") or m.get("rule_id", "")
            if content:
                kb_lines.append(f"[{title}] {content[:1200]}")
        kb_block = (
            "KNOWLEDGE BASE (retrieved passages):\n" + "\n\n".join(kb_lines)
            if kb_lines else "KNOWLEDGE BASE: no relevant passages retrieved"
        )

        prompt = (
            f"{structured_block}\n\n"
            f"{kb_block}\n\n"
            f"USER QUERY: {nlp_result.get('raw_text', 'traffic law query')}\n"
            f"Detected — Offence: {nlp_result.get('offence_type') or 'not detected'}, "
            f"State: {nlp_result.get('state') or 'not provided'}, "
            f"Vehicle: {nlp_result.get('vehicle_class') or 'not specified'}"
        )

        return await self.ai_engine.generate_response(prompt, system_instruction)

    # ── Template-based fallback ────────────────────────────────────────────────

    def _generate_text_response(
        self,
        response: Dict[str, Any],
        nlp_result: Dict[str, Any],
    ) -> str:
        status = response.get("status")
        intent = (nlp_result.get("intent") or "unknown").lower()

        if status == "insufficient_info":
            return (
                "I need a bit more information. "
                "Please mention the violation type and your state "
                "(e.g., 'Helmet fine in Chennai' or 'drunk driving penalty Delhi')."
            )

        if status == "not_found":
            query_desc = (
                nlp_result.get("offence_type")
                or nlp_result.get("section_ref")
                or nlp_result.get("raw_text")
                or "that query"
            )
            if intent in ("general_query", "procedure_query"):
                return (
                    f"I don't have specific information on '{query_desc}' in my knowledge base. "
                    "For official guidance, please visit https://parivahan.gov.in "
                    "or your state transport department website."
                )
            msg = (
                f"I couldn't find verified data for '{query_desc}'. "
                "Please check the official portal: https://echallan.parivahan.gov.in "
                "or your state transport department."
            )
            # Fuzzy "did you mean" suggestions
            if self.rules_loader:
                try:
                    all_titles = [
                        r["title"] for r in self.rules_loader.rules
                        if r.get("title") and not r["rule_id"].startswith("DS_")
                        and not r["rule_id"].startswith("CSV_")
                    ]
                    suggestions = suggest_violations(str(query_desc), all_titles, n=3)
                    if suggestions:
                        listed = "\n".join(f"  • {s}" for s in suggestions)
                        msg += f"\n\nDid you mean one of these?\n{listed}"
                except Exception as e:
                    logger.warning("did_you_mean error: %s", e)
            return msg

        # When neither fine nor rule was found, do not generate from thin air
        if not response.get("fine") and not response.get("rule"):
            query_desc = (
                nlp_result.get("offence_type")
                or nlp_result.get("raw_text")
                or "that query"
            )
            if intent in ("general_query", "procedure_query"):
                return (
                    f"I don't have specific information on '{query_desc}' in my knowledge base. "
                    "Please check https://parivahan.gov.in for official guidance."
                )
            return (
                f"I don't have verified data for '{query_desc}' in my database. "
                "Please check the official portal: https://echallan.parivahan.gov.in "
                "or your state transport department."
            )

        parts: List[str] = []
        country = nlp_result.get("country") or "IN"

        # Use the legal formatter when we have rule data for a richer output
        if response.get("rule") and response["rule"].get("rule_id", "").startswith("MV"):
            try:
                violation_row = build_violation_row(response.get("rule"), response.get("fine"))
                parts.append(format_legal_response(violation_row, country=country))
            except Exception as e:
                logger.warning("legal_formatter error: %s", e)
                # Fall through to legacy formatting below
                parts.clear()

        # Legacy formatting — used when formatter was not applicable / errored
        if not parts:
            if response.get("fine"):
                f = response["fine"]
                amount = f.get("amount_inr")
                section = f.get("section_ref") or ""
                source  = f.get("data_source", "")
                repeat  = f.get("repeat_amount_inr")

                if amount is not None:
                    line = f"The fine is ₹{amount:,}"
                    if section:
                        line += f" ({section})"
                    parts.append(line + ".")
                    if repeat and repeat != amount:
                        parts.append(f"Repeat offence: ₹{repeat:,}.")
                    if f.get("final_fine") and f.get("zone_multiplier", 1.0) > 1.0:
                        parts.append(
                            f"Zone multiplier {f['zone_multiplier']}x applied — "
                            f"total: ₹{f['final_fine']:,}."
                        )
                    if source == _SRC_CALCULATOR:
                        parts.append(
                            "_Amount based on Motor Vehicles Act national rate. "
                            "Verify at echallan.parivahan.gov.in._"
                        )
                    elif source == _SRC_RULE:
                        parts.append(
                            "_Amount based on central Act rate; state-specific fines may differ._"
                        )

            if response.get("rule"):
                r = response["rule"]
                if parts:
                    parts.append("")
                title = r.get("title") or ""
                desc  = r.get("description") or ""
                if title:
                    parts.append(f"**{title}**")
                if desc:
                    parts.append(desc[:2000])
                if r.get("compoundable") is False:
                    parts.append("🔴 **Non-compoundable** — court appearance is mandatory.")
                elif r.get("compoundable") is True:
                    parts.append("🟢 Compoundable — can be settled online or on-spot.")
                imp = r.get("imprisonment")
                if imp and imp is not False:
                    if isinstance(imp, dict):
                        months = imp.get("first_offence_months") or imp.get("max_months")
                        if months:
                            parts.append(f"⚖️ Possible imprisonment: up to {months} months.")

        if response.get("zone") and response["zone"].get("active_zones"):
            zones = response["zone"]["active_zones"]
            parts.append(f"📍 Active zone(s): {', '.join(zones)}.")

        if response.get("warnings"):
            for w in response["warnings"]:
                parts.append(f"_ℹ️ {w}_")

        # Prompt for location when violation known but state missing
        if response.get("needs_location") and (response.get("fine") or response.get("rule")):
            parts.append(
                "\n📍 **Share your location for state-specific fines.**\n"
                "The amounts above are national base rates. "
                "Reply with your state (e.g. 'in Tamil Nadu' or 'in Delhi') "
                "for the exact fine applicable in your area."
            )

        return "\n".join(parts) if parts else "Information retrieved. See the details above."

    # ── Summary ────────────────────────────────────────────────────────────────

    def _generate_summary(self, nlp_result: Dict[str, Any]) -> str:
        intent  = nlp_result.get("intent") or "unknown"
        offence = nlp_result.get("offence_type") or "general traffic rules"
        state   = nlp_result.get("state") or "India"
        raw     = (nlp_result.get("raw_text") or "")[:60]

        if intent == "fine_lookup":
            return f"Fine lookup: {offence} in {state}."
        if intent == "rule_query":
            return f"Rule query: {offence} in {state}."
        if intent == "zone_check":
            return f"Zone check for {state}."
        if intent == "general_query":
            return f"Road rule query: {raw}."
        if intent == "procedure_query":
            return f"Procedure query: {raw}."
        return "Traffic law information search."
