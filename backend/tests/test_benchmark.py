"""
Data-driven benchmark test suite.

All test cases live in tests/fixtures/bench_cases.json — add new queries there
without touching this file.  The suite covers:
  • Fine lookups via the LangGraph engine pipeline
  • Direct ToolExecutor fine / rule / zone calls
  • Engine routing (greeting, meta, keyword-fallback, OOS)
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.modules.agent.engine import AgentEngine
from backend.modules.agent.tools import ToolExecutor
from backend.modules.fines.lookup import FineLookup
from backend.modules.geofencing.engine import GeofencingEngine
from backend.modules.rules.loader import RulesLoader

# ── Fixture data ───────────────────────────────────────────────────────────────

_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "bench_cases.json")
with open(_FIXTURE, encoding="utf-8") as _f:
    _CASES = json.load(_f)

_DATA_DIR  = os.path.join(os.path.dirname(__file__), "..", "data")
_FINES_DB  = os.path.join(_DATA_DIR, "fines.db")
_RULES_JSON = os.path.join(_DATA_DIR, "rules.json")
_ZONES_DIR = os.path.join(_DATA_DIR, "zones")


# ── Shared fixtures ────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def engine():
    fl  = FineLookup(_FINES_DB)
    rl  = RulesLoader(_RULES_JSON)
    geo = GeofencingEngine(_ZONES_DIR)
    eng = AgentEngine(fl, rl, geo)
    eng.ollama_available = False
    eng.gemini_available = False
    eng.groq_available   = False
    return eng


@pytest.fixture(scope="module")
def te():
    fl  = FineLookup(_FINES_DB)
    rl  = RulesLoader(_RULES_JSON)
    geo = GeofencingEngine(_ZONES_DIR)
    return ToolExecutor(fl, rl, geo)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _assert_engine_ok(result: dict) -> dict:
    assert result is not None
    assert result["status"] not in ("error",), \
        f"Engine error: {result.get('response', '')[:200]}"
    assert isinstance(result.get("response", ""), str)
    assert len(result.get("response", "")) > 0
    return result


# ── Fine lookups — engine pipeline ────────────────────────────────────────────

@pytest.mark.parametrize("case", _CASES["fine_lookup_engine"],
                         ids=[c["id"] for c in _CASES["fine_lookup_engine"]])
def test_fine_lookup_engine(engine, case):
    r = _assert_engine_ok(engine.run(case["query"]))

    if case.get("expect_intent"):
        assert r["intent"] == case["expect_intent"]

    if case.get("expect_intent") == "fine_lookup":
        assert r["fine"] is not None, f"Expected a fine result for: {case['query']}"
        assert r["fine"]["amount_inr"] > 0
        if case.get("expect_section"):
            assert case["expect_section"] in r["fine"]["section_ref"], \
                f"Expected section {case['expect_section']} in {r['fine']['section_ref']}"

    if case.get("expect_section_in_response"):
        assert case["expect_section_in_response"] in r["response"]


# ── Fine lookups — direct tool ─────────────────────────────────────────────────

@pytest.mark.parametrize("case", _CASES["fine_lookup_tool"],
                         ids=[c["id"] for c in _CASES["fine_lookup_tool"]])
def test_fine_lookup_tool(te, case):
    params = {
        "offence_type":  case["offence_type"],
        "vehicle_class": case.get("vehicle_class", "GENERAL"),
        "state":         case.get("state", "ALL"),
    }
    if "country"   in case: params["country"]   = case["country"]
    if "is_repeat" in case: params["is_repeat"]  = case["is_repeat"]

    res = te.execute("lookup_fine", params, None)

    assert res["found"] is case["expect_found"], \
        f"Expected found={case['expect_found']} for {case['id']}, got {res}"

    if case["expect_found"]:
        assert res["amount_inr"] > 0
        if case.get("expect_currency"):
            assert res["currency"] == case["expect_currency"]
        if case.get("expect_section"):
            assert case["expect_section"] in res["section_ref"]
        if case.get("expect_section_contains"):
            assert case["expect_section_contains"] in res["section_ref"].lower()


# ── Rule lookups — direct tool ─────────────────────────────────────────────────

@pytest.mark.parametrize("case", _CASES["rule_lookup_tool"],
                         ids=[c["id"] for c in _CASES["rule_lookup_tool"]])
def test_rule_lookup_tool(te, case):
    res = te.execute("lookup_rule", {"offence_code": case["offence_code"]}, None)
    assert res["found"], f"Rule not found for {case['offence_code']}"

    if case.get("expect_section"):
        assert case["expect_section"] in res["section"]

    if case.get("expect_section_or_title"):
        assert any(k in res["section"] or k in res["title"].lower()
                   for k in case["expect_section_or_title"])

    if case.get("expect_title_keywords"):
        assert any(k in res["title"].lower() for k in case["expect_title_keywords"])

    if case.get("expect_desc_keywords"):
        assert any(k in res["description"].lower() for k in case["expect_desc_keywords"])


# ── Offence suggestion — direct tool ──────────────────────────────────────────

@pytest.mark.parametrize("case", _CASES["suggest_offence_tool"],
                         ids=[c["id"] for c in _CASES["suggest_offence_tool"]])
def test_suggest_offence_tool(te, case):
    res = te.execute("suggest_offence_categories", {"description": case["description"]}, None)
    assert res["found"]
    codes = [s["offence_code"] for s in res["suggestions"]]
    assert case["expect_code"] in codes


# ── Rule search — direct tool ──────────────────────────────────────────────────

@pytest.mark.parametrize("case", _CASES["search_rules_tool"],
                         ids=[c["id"] for c in _CASES["search_rules_tool"]])
def test_search_rules_tool(te, case):
    res = te.execute("search_rules", {"keywords": case["keywords"]}, None)
    assert res["found"]
    titles = [r["title"].lower() for r in res["rules"]]
    assert any(k in t for t in titles for k in case["expect_title_keywords"])


# ── Zone detection — direct tool ───────────────────────────────────────────────

@pytest.mark.parametrize("case", _CASES["zone_check_tool"],
                         ids=[c["id"] for c in _CASES["zone_check_tool"]])
def test_zone_check_tool(te, case):
    gps = {"lat": case["lat"], "lon": case["lon"]}
    res = te.execute("check_zone", {}, gps)

    assert res["found"] is case["expect_found"]

    if not case["expect_found"]:
        return

    if case.get("expect_zone_type"):
        assert any(z["zone_type"] == case["expect_zone_type"] for z in res["zones"]), \
            f"Zone type {case['expect_zone_type']} not found in {[z['zone_type'] for z in res['zones']]}"

    if case.get("expect_fine_multiplier"):
        zone = next((z for z in res["zones"]
                     if z["zone_type"] == case["expect_zone_type"]), None)
        assert zone is not None
        assert zone["fine_multiplier"] == case["expect_fine_multiplier"]

    if case.get("expect_speed_limit_kmh"):
        zone = next((z for z in res["zones"]
                     if z["zone_type"] == case.get("expect_zone_type")), None)
        assert zone and zone["speed_limit_kmh"] == case["expect_speed_limit_kmh"]

    if case.get("expect_horn_prohibited"):
        zone = next((z for z in res["zones"]
                     if z["zone_type"] == case.get("expect_zone_type")), None)
        assert zone and "HORN_HONKING" in zone["rules"]


# ── Engine routing ─────────────────────────────────────────────────────────────

def test_engine_routing_greeting(engine):
    r = engine.run("Hello!")
    assert r["status"] == "ok"
    assert r["intent"] == "greeting"
    assert r["fine"] is None
    assert len(r["tools_used"]) == 0


def test_engine_routing_meta(engine):
    r = engine.run("Which model are you running on?")
    assert r["status"] == "ok"
    assert r["intent"] == "meta"


def test_engine_routing_keyword_fallback(engine):
    r = engine.run("What is the fine for drunk driving in Delhi?")
    assert r["agent_powered"] is False
    assert r["model"] == "keyword-fallback"
    assert len(r["tools_used"]) > 0


def test_engine_tools_used_structure(engine):
    r = engine.run("Fine for no helmet in Maharashtra.")
    for tu in r["tools_used"]:
        assert "tool" in tu
        assert "result" in tu


def test_engine_response_always_string(engine):
    for query in [
        "What is the fine for drunk driving?",
        "gibberish xkcd 123 !@#",
        "Fine for helmet in Tamil Nadu",
    ]:
        r = engine.run(query)
        assert isinstance(r.get("response"), str), f"Non-string response for: {query!r}"


def test_engine_graceful_unknown_offence(te):
    res = te.execute("lookup_fine",
                     {"offence_type": "TOTALLY_UNKNOWN_OFFENCE_XYZ", "vehicle_class": "LMV", "state": "ALL"},
                     None)
    assert res["found"] is False


def test_engine_graceful_missing_gps(te):
    res = te.execute("check_zone", {}, None)
    assert res["found"] is False
    assert "GPS" in res.get("message", "") or "coordinates" in res.get("message", "")


def test_engine_session_state_populated(engine):
    r = engine.run("Fine for overspeeding in Tamil Nadu?")
    if r["fine"] is not None:
        assert "offence_type" in r["session"]
        assert r["session"]["offence_type"] != ""


# ── Out-of-scope queries ───────────────────────────────────────────────────────

_OOS_KEYWORDS = ("traffic law", "drivelegal", "traffic", "fine", "penalty",
                 "i can only", "try asking", "help with traffic")


def _is_oos_response(response: str) -> bool:
    return any(k in response.lower() for k in _OOS_KEYWORDS)


@pytest.mark.parametrize("case", _CASES["oos_queries"],
                         ids=[c["id"] for c in _CASES["oos_queries"]])
def test_oos_query(engine, case):
    r = engine.run(case["query"])
    assert r["status"] != "error"
    assert isinstance(r["response"], str)
    assert r["fine"] is None


def test_oos_recipe_declined(engine):
    r = engine.run("Give me a recipe for chocolate cake.")
    assert _is_oos_response(r["response"]), \
        f"Expected OOS redirect, got: {r['response'][:200]}"


def test_oos_capital_france_declined(engine):
    r = engine.run("What is the capital of France?")
    assert _is_oos_response(r["response"]), \
        f"Expected OOS redirect, got: {r['response'][:200]}"


# ── Amount comparisons (relative, not absolute) ────────────────────────────────

def test_hgv_speed_fine_exceeds_lmv(te):
    car   = te.execute("lookup_fine", {"offence_type": "SPEED_EXCESS", "vehicle_class": "LMV", "state": "ALL"}, None)
    truck = te.execute("lookup_fine", {"offence_type": "SPEED_EXCESS", "vehicle_class": "HGV", "state": "ALL"}, None)
    assert car["found"] and truck["found"]
    assert truck["amount_inr"] > car["amount_inr"]


def test_repeat_fine_gte_first_fine(te):
    first  = te.execute("lookup_fine", {"offence_type": "NO_SEATBELT", "vehicle_class": "LMV", "state": "ALL"}, None)
    repeat = te.execute("lookup_fine", {"offence_type": "NO_SEATBELT", "vehicle_class": "LMV", "state": "ALL", "is_repeat": "true"}, None)
    assert first["found"] and repeat["found"]
    assert repeat["amount_inr"] >= first["amount_inr"]
