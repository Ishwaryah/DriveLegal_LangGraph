"""
Comprehensive 32-query benchmark test suite.

Tests the LangGraph AgentEngine (keyword-fallback mode) and
ToolExecutor directly against the real fines.db + rules.json.

Categories
----------
1. Basic Fine Lookups — India (Q1-Q10)
2. Repeat Offences & Edge Cases (Q11-Q16)
3. International Traffic Fines (Q17-Q24)
4. Rule Explanations & Legal Sections (Q25-Q32)
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.modules.agent.engine import AgentEngine
from backend.modules.agent.tools import ToolExecutor
from backend.modules.fines.lookup import FineLookup
from backend.modules.rules.loader import RulesLoader
from backend.modules.geofencing.engine import GeofencingEngine

# ── Paths ──────────────────────────────────────────────────────────────────────
_DATA      = os.path.join(os.path.dirname(__file__), "..", "data")
_FINES_DB  = os.path.join(_DATA, "fines.db")
_RULES_JSON = os.path.join(_DATA, "rules.json")
_ZONES_DIR = os.path.join(_DATA, "zones")


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def engine():
    """
    AgentEngine forced into keyword-fallback mode (no LLM providers).
    This exercises the full LangGraph graph routing:
      START → intent_gate → keyword_fallback → END
    """
    fl  = FineLookup(_FINES_DB)
    rl  = RulesLoader(_RULES_JSON)
    geo = GeofencingEngine(_ZONES_DIR)
    eng = AgentEngine(fl, rl, geo)
    # Override after init so graph routing uses the live flags
    eng.ollama_available = False
    eng.gemini_available = False
    eng.groq_available   = False
    return eng


@pytest.fixture(scope="module")
def te():
    """Direct ToolExecutor for targeted assertions."""
    fl  = FineLookup(_FINES_DB)
    rl  = RulesLoader(_RULES_JSON)
    geo = GeofencingEngine(_ZONES_DIR)
    return ToolExecutor(fl, rl, geo)


# ── Shared helpers ────────────────────────────────────────────────────────────

def _ok(result: dict) -> dict:
    """Assert structural integrity of an AgentEngine response."""
    assert result is not None
    assert result["status"] not in ("error",), \
        f"Engine returned error status: {result.get('response', '')}"
    assert isinstance(result.get("response", ""), str)
    assert len(result.get("response", "")) > 0
    return result


# ═════════════════════════════════════════════════════════════════════════════
# CATEGORY 1 — Basic Fine Lookups (India)
# ═════════════════════════════════════════════════════════════════════════════

class TestCat1BasicIndia:
    """Q1–Q10: standard state-level fine queries through the LangGraph pipeline."""

    def test_q1_no_helmet_tamil_nadu(self, engine):
        """Q1 — Fine for driving without a helmet in Tamil Nadu."""
        r = _ok(engine.run("What is the fine for driving without a helmet in Tamil Nadu?"))
        assert r["intent"] == "fine_lookup"
        assert r["fine"] is not None
        assert r["fine"]["amount_inr"] == 1000
        assert "194" in r["fine"]["section_ref"]

    def test_q2_no_seatbelt_delhi_car(self, engine):
        """Q2 — Fine for not wearing a seatbelt in Delhi for a car."""
        r = _ok(engine.run("Fine for not wearing a seatbelt in Delhi for a car."))
        assert r["intent"] == "fine_lookup"
        assert r["fine"] is not None
        assert r["fine"]["amount_inr"] == 1000
        assert "194B" in r["fine"]["section_ref"]

    def test_q3_overspeeding_maharashtra_car(self, engine):
        """Q3 — Overspeeding a car in Maharashtra."""
        r = _ok(engine.run("How much do I pay for overspeeding a car in Maharashtra?"))
        assert r["intent"] == "fine_lookup"
        assert r["fine"] is not None
        assert r["fine"]["amount_inr"] == 1000
        assert "183" in r["fine"]["section_ref"]

    def test_q4_red_light_karnataka(self, engine):
        """Q4 — Penalty for jumping a red light in Karnataka."""
        r = _ok(engine.run("What is the penalty for jumping a red light in Karnataka?"))
        assert r["intent"] == "fine_lookup"
        assert r["fine"] is not None
        assert r["fine"]["amount_inr"] == 1000
        assert "177" in r["fine"]["section_ref"]

    def test_q5_no_insurance_uttar_pradesh(self, engine):
        """Q5 — Fine for driving without insurance in Uttar Pradesh."""
        r = _ok(engine.run("Fine for driving without insurance in Uttar Pradesh."))
        assert r["intent"] == "fine_lookup"
        assert r["fine"] is not None
        assert r["fine"]["amount_inr"] == 2000
        assert "196" in r["fine"]["section_ref"]

    def test_q6_no_puc_kerala(self, engine):
        """Q6 — Challan for no PUC certificate in Kerala."""
        r = _ok(engine.run("What is the challan for no PUC (pollution certificate) in Kerala?"))
        assert r["intent"] == "fine_lookup"
        assert r["fine"] is not None
        assert r["fine"]["amount_inr"] == 10000
        assert "194F" in r["fine"]["section_ref"]

    def test_q7_triple_riding_andhra_pradesh(self, engine):
        """Q7 — Fine for triple riding on a bike in Andhra Pradesh."""
        r = _ok(engine.run("Fine for triple riding on a bike in Andhra Pradesh."))
        assert r["intent"] == "fine_lookup"
        assert r["fine"] is not None
        assert r["fine"]["amount_inr"] >= 1000
        assert "194C" in r["fine"]["section_ref"]

    def test_q8_mobile_phone_telangana(self, engine):
        """Q8 — Penalty for using a mobile phone while driving in Telangana."""
        r = _ok(engine.run("Penalty for using a mobile phone while driving in Telangana."))
        assert r["intent"] == "fine_lookup"
        assert r["fine"] is not None
        assert r["fine"]["amount_inr"] == 5000
        assert "184" in r["fine"]["section_ref"]

    def test_q9_drunk_driving_west_bengal(self, engine):
        """Q9 — Fine for drunk driving in West Bengal."""
        r = _ok(engine.run("How much is the fine for drunk driving in West Bengal?"))
        assert r["intent"] == "fine_lookup"
        assert r["fine"] is not None
        assert r["fine"]["amount_inr"] == 10000
        assert "185" in r["fine"]["section_ref"]

    def test_q10_wrong_way_gujarat_truck(self, engine):
        """Q10 — Fine for wrong-way driving in Gujarat for a truck."""
        r = _ok(engine.run("Fine for wrong-way driving in Gujarat for a truck."))
        assert r["intent"] == "fine_lookup"
        assert r["fine"] is not None
        assert r["fine"]["amount_inr"] >= 2000
        assert "179" in r["fine"]["section_ref"]


# ═════════════════════════════════════════════════════════════════════════════
# CATEGORY 2 — Repeat Offences & Edge Cases
# ═════════════════════════════════════════════════════════════════════════════

class TestCat2RepeatEdge:
    """Q11–Q16: repeat-offence logic, vehicle comparisons, and special scenarios."""

    def test_q11_repeat_drunk_driving_tn_response_shows_repeat_amount(self, engine):
        """Q11 — Second offense drunk driving TN: response must show repeat amount ₹15000."""
        r = _ok(engine.run("What is the fine for a second offense of drunk driving in TN?"))
        assert r["fine"] is not None
        # Keyword fallback always shows both first and repeat amounts in the response text
        assert "15000" in r["response"]

    def test_q12_followup_helmet_third_time(self, engine):
        """Q12 — Helmet fine first ask, then follow-up for 3rd offence (multi-turn)."""
        first = engine.run("Fine for not wearing a helmet.")
        assert first["fine"] is not None
        assert first["fine"]["amount_inr"] == 1000

        followup = engine.run(
            "What if it is my 3rd time?",
            conversation_history=[
                {"role": "user",      "parts": ["Fine for not wearing a helmet."]},
                {"role": "assistant", "parts": [first["response"]]},
            ],
        )
        assert followup["status"] != "error"
        assert isinstance(followup["response"], str)

    def test_q13_seatbelt_repeat_tool(self, te):
        """Q13 — No-seatbelt fine is available for both first and repeat via tool."""
        first  = te.execute("lookup_fine", {"offence_type": "NO_SEATBELT", "vehicle_class": "LMV", "state": "ALL"}, None)
        repeat = te.execute("lookup_fine", {"offence_type": "NO_SEATBELT", "vehicle_class": "LMV", "state": "ALL", "is_repeat": "true"}, None)
        assert first["found"] and repeat["found"]
        assert first["amount_inr"] > 0
        assert repeat["amount_inr"] > 0

    def test_q14_truck_higher_than_car_overspeeding(self, te):
        """Q14 — Overspeeding: commercial truck fine (HGV ₹2000) > private car (LMV ₹1000)."""
        car   = te.execute("lookup_fine", {"offence_type": "SPEED_EXCESS", "vehicle_class": "LMV", "state": "ALL"}, None)
        truck = te.execute("lookup_fine", {"offence_type": "SPEED_EXCESS", "vehicle_class": "HGV", "state": "ALL"}, None)
        assert car["found"] and truck["found"]
        assert truck["amount_inr"] > car["amount_inr"]

    def test_q15_juvenile_driving_direct_tool(self, te):
        """Q15 — Juvenile driving fine is ₹25000 (Section 199A) via tool lookup."""
        res = te.execute("lookup_fine", {"offence_type": "JUVENILE_DRIVING", "vehicle_class": "GENERAL", "state": "ALL"}, None)
        assert res["found"]
        assert res["amount_inr"] == 25000
        assert "199A" in res["section_ref"]

    def test_q15_minor_driving_engine(self, engine):
        """Q15b — Engine handles 'minor caught driving without license' query."""
        r = _ok(engine.run("What if a minor is caught driving without a license?"))
        assert r["fine"] is not None
        assert r["fine"]["amount_inr"] >= 5000

    def test_q16_no_license_plate(self, engine):
        """Q16 — Fine for driving without a license plate (Section 192)."""
        r = _ok(engine.run("Fine for driving without a license plate."))
        assert r["intent"] == "fine_lookup"
        assert r["fine"] is not None
        assert r["fine"]["amount_inr"] >= 5000
        assert "192" in r["fine"]["section_ref"]


# ═════════════════════════════════════════════════════════════════════════════
# CATEGORY 3 — International Traffic Fines
# ═════════════════════════════════════════════════════════════════════════════

class TestCat3International:
    """Q17–Q24: multi-country fine lookups (AE, GB, US, SG, SA)."""

    def test_q17_red_light_dubai_engine(self, engine):
        """Q17 — Running a red light in Dubai: AED 1000, Federal Traffic Law."""
        r = _ok(engine.run("What is the fine for running a red light in Dubai (UAE)?"))
        assert r["fine"] is not None
        assert r["fine"]["amount_inr"] == 1000
        assert "AED" in r["response"] or "1000" in r["response"]

    def test_q17_red_light_dubai_tool(self, te):
        """Q17b — Dubai red-light fine via direct tool call."""
        res = te.execute("lookup_fine", {"offence_type": "RED_LIGHT_JUMPING", "vehicle_class": "ALL", "state": "DUBAI", "country": "AE"}, None)
        assert res["found"]
        assert res["amount_inr"] == 1000
        assert res["currency"] == "AED"

    def test_q18_speeding_abu_dhabi(self, te):
        """Q18 — Speeding fine in Abu Dhabi: AED 300."""
        res = te.execute("lookup_fine", {"offence_type": "SPEED_EXCESS", "vehicle_class": "ALL", "state": "ABU_DHABI", "country": "AE"}, None)
        assert res["found"]
        assert res["amount_inr"] == 300
        assert res["currency"] == "AED"

    def test_q19_texting_driving_uk(self, te):
        """Q19 — Texting and driving fine in UK: £200."""
        res = te.execute("lookup_fine", {"offence_type": "MOBILE_PHONE", "vehicle_class": "ALL", "state": "ALL", "country": "GB"}, None)
        assert res["found"]
        assert res["amount_inr"] == 200
        assert res["currency"] == "GBP"

    def test_q19_mobile_phone_uk_engine(self, engine):
        """Q19b — Engine correctly routes UK mobile phone query."""
        r = _ok(engine.run("How much is the penalty for texting and driving in the UK?"))
        assert r["fine"] is not None
        assert r["fine"]["amount_inr"] == 200

    def test_q20_no_insurance_california(self, te):
        """Q20 — No insurance in California, USA: USD 500."""
        res = te.execute("lookup_fine", {"offence_type": "NO_INSURANCE", "vehicle_class": "ALL", "state": "CALIFORNIA", "country": "US"}, None)
        assert res["found"]
        assert res["amount_inr"] == 500
        assert res["currency"] == "USD"

    def test_q21_speeding_singapore_demerit(self, te):
        """Q21 — Speeding in Singapore: SGD 150 + demerit points."""
        res = te.execute("lookup_fine", {"offence_type": "SPEED_EXCESS", "vehicle_class": "ALL", "state": "ALL", "country": "SG"}, None)
        assert res["found"]
        assert res["amount_inr"] == 150
        assert res["currency"] == "SGD"
        assert "demerit" in res["section_ref"].lower()

    def test_q22_disabled_parking_saudi(self, te):
        """Q22 — Parking in a disabled spot in Saudi Arabia: SAR 100+."""
        res = te.execute("lookup_fine", {"offence_type": "NO_PARKING", "vehicle_class": "ALL", "state": "ALL", "country": "SA"}, None)
        assert res["found"]
        assert res["amount_inr"] >= 100
        assert res["currency"] == "SAR"

    def test_q23_dui_new_york(self, te):
        """Q23 — DUI fine in New York, USA: USD 1000+."""
        res = te.execute("lookup_fine", {"offence_type": "DRUNK_DRIVING", "vehicle_class": "ALL", "state": "NEW_YORK", "country": "US"}, None)
        assert res["found"]
        assert res["amount_inr"] >= 1000
        assert res["currency"] == "USD"

    def test_q24_seatbelt_london_engine(self, engine):
        """Q24 — No seatbelt in London, UK: £100 via engine pipeline."""
        r = _ok(engine.run("Fine for not wearing a seatbelt in London, UK."))
        assert r["fine"] is not None
        assert r["fine"]["amount_inr"] == 100

    def test_q24_seatbelt_uk_tool(self, te):
        """Q24b — No seatbelt UK fine via tool."""
        res = te.execute("lookup_fine", {"offence_type": "NO_SEATBELT", "vehicle_class": "ALL", "state": "ALL", "country": "GB"}, None)
        assert res["found"]
        assert res["amount_inr"] == 100
        assert res["currency"] == "GBP"


# ═════════════════════════════════════════════════════════════════════════════
# CATEGORY 4 — Rule Explanations & Legal Sections
# ═════════════════════════════════════════════════════════════════════════════

class TestCat4Rules:
    """Q25–Q32: rule/section lookups and legal explanations."""

    def test_q25_section_drunk_driving(self, te):
        """Q25 — Drunk driving is penalized under Section 185 MV Act."""
        res = te.execute("lookup_rule", {"offence_code": "DRUNK_DRIVING"}, None)
        assert res["found"]
        assert "185" in res["section"]
        title_lower = res["title"].lower()
        assert "drunk" in title_lower or "driving under" in title_lower or "drunken" in title_lower

    def test_q25_drunk_driving_section_engine(self, engine):
        """Q25b — Engine can answer 'what section covers drunk driving'."""
        r = _ok(engine.run("Under what section of the Motor Vehicles Act is drunk driving penalized?"))
        assert r["status"] != "error"
        assert "185" in r["response"]

    def test_q26_section_194d_rule(self, te):
        """Q26 — Section 194D covers not wearing protective headgear."""
        res = te.execute("lookup_rule", {"offence_code": "NO_HELMET"}, None)
        assert res["found"]
        assert "194D" in res["section"]
        desc = res["description"].lower()
        assert "helmet" in desc or "headgear" in desc

    def test_q26_section_194d_engine(self, engine):
        """Q26b — Engine responds to 'Explain Section 194D' query."""
        r = _ok(engine.run("Explain Section 194D of the Motor Vehicles Act."))
        assert r["status"] != "error"
        assert "194" in r["response"]

    def test_q27_tinted_windows_rule(self, te):
        """Q27 — Tinted windows rule is present in the rules database."""
        res = te.execute("lookup_rule", {"offence_code": "TINTED_GLASS"}, None)
        assert res["found"]
        title = res["title"].lower()
        assert "tinted" in title or "glass" in title or "window" in title

    def test_q27_tinted_windows_engine(self, engine):
        """Q27b — Engine handles tinted window query without error."""
        r = _ok(engine.run("What are the rules for tinted windows on cars?"))
        assert r["status"] != "error"
        assert len(r["response"]) > 0

    def test_q28_exhaust_modification_rule(self, te):
        """Q28 — Illegal vehicle modification (exhaust) covered under Section 52."""
        res = te.execute("lookup_rule", {"offence_code": "VEHICLE_MODIFICATION"}, None)
        assert res["found"]
        assert "52" in res["section"] or "modification" in res["title"].lower()

    def test_q28_suggest_offence_exhaust(self, te):
        """Q28b — suggest_offence_categories maps 'exhaust modification' to VEHICLE_MODIFICATION."""
        res = te.execute("suggest_offence_categories", {"description": "exhaust modification on my motorcycle"}, None)
        assert res["found"]
        codes = [s["offence_code"] for s in res["suggestions"]]
        assert "VEHICLE_MODIFICATION" in codes

    def test_q29_high_beam_rule(self, te):
        """Q29 — High-beam headlights rule is in the database (Section 177)."""
        res = te.execute("lookup_rule", {"offence_code": "HIGH_BEAM"}, None)
        assert res["found"]
        assert "177" in res["section"] or "beam" in res["title"].lower()

    def test_q29_high_beam_engine(self, engine):
        """Q29b — Engine handles high-beam query."""
        r = _ok(engine.run("What are the rules regarding high-beam headlights in city limits?"))
        assert r["status"] != "error"
        assert len(r["response"]) > 0

    def test_q30_pillion_helmet_law(self, te):
        """Q30 — Pillion rider must wear helmet under Section 194D."""
        res = te.execute("lookup_rule", {"offence_code": "NO_HELMET"}, None)
        assert res["found"]
        desc = res["description"].lower()
        assert "pillion" in desc or "helmet" in desc

    def test_q30_pillion_helmet_engine(self, engine):
        """Q30b — Engine answers pillion rider helmet query."""
        r = _ok(engine.run("Does a pillion rider need to wear a helmet by law?"))
        assert r["status"] != "error"
        assert "194" in r["response"] or "helmet" in r["response"].lower()

    def test_q31_blood_alcohol_limit_rule(self, te):
        """Q31 — Drunk driving rule mentions BAC limit (30mg/100ml)."""
        res = te.execute("lookup_rule", {"offence_code": "DRUNK_DRIVING"}, None)
        assert res["found"]
        desc = res["description"].lower()
        assert "bac" in desc or "0.03" in desc or "30mg" in desc or "alcohol" in desc

    def test_q31_bac_engine(self, engine):
        """Q31b — Engine answers blood alcohol limit query."""
        r = _ok(engine.run("What is the legal blood alcohol limit for driving in India?"))
        assert r["status"] != "error"
        assert len(r["response"]) > 0

    def test_q32_digilocker_validity_search(self, te):
        """Q32 — DigiLocker is covered by a searchable rule in the database."""
        res = te.execute("search_rules", {"keywords": ["digilocker", "digital", "documents"]}, None)
        assert res["found"]
        titles = [rule["title"].lower() for rule in res["rules"]]
        assert any("digilocker" in t or "document" in t for t in titles)

    def test_q32_digilocker_engine(self, engine):
        """Q32b — Engine handles DigiLocker validity query without crashing."""
        r = engine.run("Are physical documents required, or is DigiLocker valid?")
        assert r["status"] != "error"
        assert isinstance(r["response"], str)


# ═════════════════════════════════════════════════════════════════════════════
# LangGraph Graph Wiring Checks
# ═════════════════════════════════════════════════════════════════════════════

class TestLangGraphWiring:
    """Verify LangGraph state routing: greeting fast-path, traffic routing, etc."""

    def test_greeting_fast_path(self, engine):
        """Greeting bypasses graph and returns intent='greeting'."""
        r = engine.run("Hello!")
        assert r["status"] == "ok"
        assert r["intent"] == "greeting"
        assert r["fine"] is None

    def test_meta_query(self, engine):
        """Model identity query returns intent='meta'."""
        r = engine.run("Which model are you running on?")
        assert r["status"] == "ok"
        assert r["intent"] == "meta"

    def test_traffic_query_routes_to_keyword_fallback(self, engine):
        """A fine query in keyword mode uses tools_used and returns agent_powered=False."""
        r = engine.run("What is the fine for drunk driving in Delhi?")
        assert r["agent_powered"] is False
        assert r["model"] == "keyword-fallback"
        assert len(r["tools_used"]) > 0

    def test_tools_used_structure(self, engine):
        """tools_used list entries have 'tool', 'params', and 'result' keys."""
        r = engine.run("Fine for no helmet in Maharashtra.")
        for tu in r["tools_used"]:
            assert "tool" in tu
            assert "result" in tu

    def test_session_state_populated(self, engine):
        """A successful fine lookup populates session state for context carry-over."""
        r = engine.run("Fine for overspeeding in Tamil Nadu?")
        if r["fine"] is not None:
            assert "offence_type" in r["session"]
            assert r["session"]["offence_type"] != ""

    def test_response_always_string(self, engine):
        """Engine never returns None or non-string for the 'response' key."""
        queries = [
            "What is the fine for drunk driving?",
            "gibberish xkcd 123 !@#",
            "Fine for helmet in Tamil Nadu",
        ]
        for q in queries:
            r = engine.run(q)
            assert isinstance(r.get("response"), str), \
                f"Non-string response for query: {q!r}"

    def test_no_crash_on_empty_db_fields(self, te):
        """ToolExecutor handles unknown offence gracefully (returns found=False)."""
        res = te.execute("lookup_fine", {"offence_type": "TOTALLY_UNKNOWN_OFFENCE_XYZ", "vehicle_class": "LMV", "state": "ALL"}, None)
        assert res["found"] is False

    def test_no_crash_on_missing_gps(self, te):
        """check_zone with missing GPS returns found=False gracefully."""
        res = te.execute("check_zone", {}, None)
        assert res["found"] is False
        assert "GPS" in res.get("message", "") or "coordinates" in res.get("message", "")
