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

# Minimum search score threshold for accepting a search-result fallback
_MIN_SEARCH_SCORE = 0.45

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

        # ── 2. Early-exit for pipeline errors / insufficient info ─────────────
        pipeline_status = nlp_result.get("status")
        if pipeline_status == "insufficient_info":
            # Only exit early when hybrid search also has nothing useful.
            # If search_matches were added by main.py, fall through to step 5.
            search_matches = nlp_result.get("search_matches") or []
            has_useful_search = any(
                (m.get("score") or 0) >= _MIN_SEARCH_SCORE for m in search_matches
            )
            if not has_useful_search:
                response["status"] = "insufficient_info"
                response["text"]   = self._generate_text_response(response, nlp_result)
                return response
            # Has useful search results — fall through so step 5 can use them.

        if pipeline_status == "error":
            response["status"] = "error"
            response["text"]   = "I encountered an error while processing your request."
            return response

        # ── Extract NLP fields (with None-safe defaults) ──────────────────────
        offence_code  = nlp_result.get("offence_type")
        state         = nlp_result.get("state") or "ALL"
        vehicle_class = nlp_result.get("vehicle_class") or "LMV"
        is_repeat     = bool(nlp_result.get("repeat_offence"))
        section_ref   = nlp_result.get("section_ref")

        # ── 3. Rule lookup ────────────────────────────────────────────────────
        rule_data: Optional[Dict] = None
        if self.rules_loader:
            try:
                if section_ref:
                    rule_data = self.rules_loader.get_by_section(section_ref)
                if not rule_data and offence_code:
                    rule_data = self.rules_loader.get_by_offence_code(offence_code, state)
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
                        fine_data = self.fine_lookup.query(offence_code, vehicle_class, state, is_repeat)

                    # Section-based fallback when offence_code lookup misses
                    if not fine_data and section_ref:
                        rows = self.fine_lookup.query_by_section(section_ref)
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
        relevant = [m for m in search_matches if (m.get("score") or 0) >= _MIN_SEARCH_SCORE]
        if relevant and not response["rule"]:
            top = relevant[0]
            meta = top.get("metadata") or {}
            response["rule"] = {
                "rule_id":     top.get("rule_id"),
                "title":       meta.get("title") or top.get("rule_id"),
                "description": top.get("content", ""),
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

        # ── 7. Text synthesis ─────────────────────────────────────────────────
        try:
            if self.ai_engine:
                response["text"] = await self._generate_ai_response(response, nlp_result)
            else:
                response["text"] = self._generate_text_response(response, nlp_result)
        except Exception as e:
            logger.error("Text generation error: %s", e)
            response["text"] = self._generate_text_response(response, nlp_result)

        return response

    # ── AI response (guardrailed) ─────────────────────────────────────────────

    async def _generate_ai_response(
        self,
        response_data: Dict[str, Any],
        nlp_result: Dict[str, Any],
    ) -> str:
        system_instruction = (
            "You are DriveLegal AI, a factual assistant for traffic laws. "
            "RULES:\n"
            "1. ONLY use the CONTEXT DATA below — never invent fine amounts or section numbers.\n"
            "2. If context says 'Not found', tell the user to check official local sources.\n"
            "3. Clearly state the data source (fines_db / national_act / challan_calculator).\n"
            "4. Use appropriate currency symbols (e.g. ₹ for India, AED for UAE, £ for UK).\n"
            "5. For EVERY traffic violation response you MUST include:\n"
            "   a) The applicable law section (e.g. 'Motor Vehicles (Amendment) Act 2019, Section 183')\n"
            "   b) The fine range for the detected vehicle type\n"
            "   c) Whether the offence is compoundable (can be settled) or requires court appearance\n"
            "   d) A one-line plain-English explanation of what the offence means\n"
            "6. Mention imprisonment risk when present in context.\n"
            "7. Always respect the specified country context."
        )

        fine_ctx = response_data.get("fine")
        rule_ctx = response_data.get("rule")
        zone_ctx = response_data.get("zone")

        context_lines = [f"Intent: {response_data['intent']}"]
        if fine_ctx:
            context_lines.append(
                f"Fine: ₹{fine_ctx.get('amount_inr')} "
                f"(source: {fine_ctx.get('data_source')}, "
                f"section: {fine_ctx.get('section_ref')})"
            )
        else:
            context_lines.append("Fine: Not found in database")

        if rule_ctx:
            context_lines.append(
                f"Rule: {rule_ctx.get('title')} — {rule_ctx.get('description', '')[:300]}"
            )
            if rule_ctx.get("compoundable") is False:
                context_lines.append("Non-compoundable: court appearance mandatory")
            if rule_ctx.get("imprisonment"):
                context_lines.append(f"Imprisonment risk: {rule_ctx['imprisonment']}")
        else:
            context_lines.append("Rule: Not found in database")

        if zone_ctx and zone_ctx.get("active_zones"):
            context_lines.append(f"Zone: {', '.join(zone_ctx['active_zones'])}")

        if response_data.get("warnings"):
            context_lines.append("Warnings: " + "; ".join(response_data["warnings"]))

        prompt = (
            f"CONTEXT DATA:\n" + "\n".join(context_lines) + "\n\n"
            f"USER QUERY: {nlp_result.get('raw_text', 'traffic law query')}\n"
            f"Offence={nlp_result.get('offence_type')}, "
            f"State={nlp_result.get('state')}, "
            f"Country={nlp_result.get('country')}, "
            f"Vehicle={nlp_result.get('vehicle_class')}"
        )

        return await self.ai_engine.generate_response(prompt, system_instruction)

    # ── Template-based fallback ────────────────────────────────────────────────

    def _generate_text_response(
        self,
        response: Dict[str, Any],
        nlp_result: Dict[str, Any],
    ) -> str:
        status = response.get("status")

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
                    ]
                    suggestions = suggest_violations(str(query_desc), all_titles, n=3)
                    if suggestions:
                        listed = "\n".join(f"  • {s}" for s in suggestions)
                        msg += f"\n\nDid you mean one of these?\n{listed}"
                except Exception as e:
                    logger.warning("did_you_mean error: %s", e)
            return msg

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
                    parts.append(desc[:500])
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

        return "\n".join(parts) if parts else "Information retrieved. See the details above."

    # ── Summary ────────────────────────────────────────────────────────────────

    def _generate_summary(self, nlp_result: Dict[str, Any]) -> str:
        intent  = nlp_result.get("intent") or "unknown"
        offence = nlp_result.get("offence_type") or "general traffic rules"
        state   = nlp_result.get("state") or "India"

        if intent == "fine_lookup":
            return f"Fine lookup: {offence} in {state}."
        if intent == "rule_query":
            return f"Rule query: {offence} in {state}."
        if intent == "zone_check":
            return f"Zone check for {state}."
        return "Traffic law information search."
