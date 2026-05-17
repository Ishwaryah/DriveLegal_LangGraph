import pytest
from backend.modules.nlp.pipeline import NLPPipeline

@pytest.fixture
def pipeline():
    return NLPPipeline()

def test_fine_lookup_basic(pipeline):
    """
    Test a complete query for fine lookup.
    "what is the fine for jumping red light on a bike in Tamil Nadu"
    """
    raw_text = "what is the fine for jumping red light on a bike in Tamil Nadu"
    result = pipeline.run(raw_text)
    
    assert result["intent"] == "fine_lookup"
    assert result["vehicle_class"] == "2W"
    assert result["state"] == "Tamil Nadu"
    assert result["offence_type"] == "RED_LIGHT_JUMPING"
    assert result["status"] == "success"

def test_unknown_intent(pipeline):
    """
    Test a query that does not match any keyword rules.
    "hello how are you"
    """
    raw_text = "hello how are you"
    result = pipeline.run(raw_text)
    
    assert result["intent"] == "unknown"
    assert result["status"] == "insufficient_info"

def test_missing_state_resolved_by_gps(pipeline):
    """
    Test if state is correctly resolved when missing from text but GPS is provided.
    """
    raw_text = "what is the fine for speeding on a bike"
    gps = {"lat": 13.0827, "lon": 80.2707} # Chennai, TN
    result = pipeline.run(raw_text, gps=gps)
    
    assert result["state"] in ["Tamil Nadu", "TN"]
    assert result["intent"] == "fine_lookup"
    assert result["status"] == "success"

def test_vehicle_class_resolution_from_session(pipeline):
    """
    Test if vehicle_class is resolved from session if missing from text.
    """
    raw_text = "what is the fine for no helmet"
    session = {"vehicle_class": "2W"}
    result = pipeline.run(raw_text, session=session)
    
    assert result["vehicle_class"] == "2W"
    assert result["status"] == "success"

def test_section_ref_sufficiency(pipeline):
    """
    Test that a section reference is sufficient to mark status as success.
    """
    raw_text = "What does Section 185 govern?"
    result = pipeline.run(raw_text)
    
    assert result["section_ref"] == "section 185"
    assert result["intent"] == "rule_query"
    assert result["status"] == "success"

def test_multi_turn_state_resolution(pipeline):
    """
    Test that providing just a state abbreviation resolves correctly using session context.
    """
    # First turn sets context
    session = {"section_ref": "Section 185", "offence_type": "DRUNK_DRIVING"}
    raw_text = "DL"
    result = pipeline.run(raw_text, session=session)
    
    assert result["state"] == "Delhi"
    assert result["section_ref"] == "Section 185"
    assert result["status"] == "success"
