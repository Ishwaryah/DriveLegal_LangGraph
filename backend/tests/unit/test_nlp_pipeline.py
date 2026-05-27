"""
Unit tests for NLPPipeline — intent, entity, and state extraction.
"""

import pytest
from backend.modules.nlp.pipeline import NLPPipeline


@pytest.fixture(scope="module")
def pipeline():
    return NLPPipeline()


def test_fine_lookup_basic(pipeline):
    result = pipeline.run("what is the fine for jumping red light on a bike in Tamil Nadu")
    assert result["intent"] == "fine_lookup"
    assert result["vehicle_class"] == "2W"
    assert result["state"] == "Tamil Nadu"
    assert result["offence_type"] == "RED_LIGHT_JUMPING"
    assert result["status"] == "success"


def test_unknown_intent(pipeline):
    result = pipeline.run("hello how are you")
    assert result["intent"] == "unknown"
    assert result["status"] == "insufficient_info"


def test_gps_resolves_missing_state(pipeline):
    result = pipeline.run(
        "what is the fine for speeding on a bike",
        gps={"lat": 13.0827, "lon": 80.2707},  # Chennai, TN
    )
    assert result["state"] in ("Tamil Nadu", "TN")
    assert result["intent"] == "fine_lookup"
    assert result["status"] == "success"


def test_session_resolves_vehicle_class(pipeline):
    result = pipeline.run(
        "what is the fine for no helmet",
        session={"vehicle_class": "2W"},
    )
    assert result["vehicle_class"] == "2W"
    assert result["status"] == "success"


def test_section_ref_query(pipeline):
    result = pipeline.run("What does Section 185 govern?")
    assert result["section_ref"] == "section 185"
    assert result["intent"] == "rule_query"
    assert result["status"] == "success"


def test_multi_turn_state_resolution(pipeline):
    result = pipeline.run(
        "DL",
        session={"section_ref": "Section 185", "offence_type": "DRUNK_DRIVING"},
    )
    assert result["state"] == "Delhi"
    assert result["section_ref"] == "Section 185"
    assert result["status"] == "success"
