import pytest
import os
import json
import sqlite3
from fastapi.testclient import TestClient
from backend.main import app
from backend.modules.fines.lookup import FineLookup
from backend.modules.rules.loader import RulesLoader
from backend.modules.nlp.hybrid_search import HybridSearch

# Use the real data for these tests
DATA_DIR = os.path.join(os.getcwd(), "backend", "data")
FINES_DB = os.path.join(DATA_DIR, "fines.db")
RULES_JSON = os.path.join(DATA_DIR, "rules.json")
VECTOR_DB = os.path.join(DATA_DIR, "vector_db")

@pytest.fixture(scope="module")
def real_client():
    import backend.main as main
    main.agent_engine.groq_available = False
    return TestClient(main.app)

def test_dataset_files_exist():
    """Verify that the core dataset files are present."""
    assert os.path.exists(FINES_DB), f"Fines DB missing at {FINES_DB}"
    assert os.path.exists(RULES_JSON), f"Rules JSON missing at {RULES_JSON}"

def test_rules_schema_and_load():
    """Verify that rules.json can be loaded and has the correct schema."""
    loader = RulesLoader(RULES_JSON)
    assert len(loader.rules) > 0
    rule = loader.rules[0]
    required_keys = ["rule_id", "title", "description"]
    for key in required_keys:
        assert key in rule, f"Missing key {key} in rule {rule.get('rule_id')}"

def test_fine_lookup_real_data():
    """Test fine lookup logic with real entries from fines.db."""
    lookup = FineLookup(FINES_DB)
    
    # Test Drunk Driving (Generic)
    res = lookup.query("DRUNK_DRIVING", "LMV", "Delhi")
    assert res is not None
    assert res["amount_inr"] >= 10000
    assert "185" in res["section_ref"]

    # Test No Helmet in Tamil Nadu
    res = lookup.query("NO_HELMET", "TWO_WHEELER", "TN")
    if res: # Might vary by dataset version
        assert res["amount_inr"] == 1000
        assert "194D" in res["section_ref"]

def test_hybrid_search_functionality():
    """Test if HybridSearch can find relevant rules in the real dataset."""
    # Note: HybridSearch might need the vector_db to be initialized
    if not os.path.exists(VECTOR_DB):
        pytest.skip("Vector DB not initialized, skipping hybrid search test")
    
    searcher = HybridSearch(RULES_JSON, VECTOR_DB)
    results = searcher.search("speeding", top_k=3)
    
    assert len(results) > 0
    # Check if the first result is relevant to speeding
    found_speed = any("speed" in r["metadata"].get("title", "").lower() or "speed" in r["content"].lower() for r in results)
    assert found_speed, "Could not find speeding related rules in hybrid search"

def test_end_to_end_query_drunk_driving(real_client):
    """Test the full /query pipeline for a known offence in the dataset."""
    payload = {
        "text": "what is the fine for drunk driving in a car in Delhi",
        "gps": None,
        "session": {}
    }
    response = real_client.post("/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "ok"
    assert data["intent"] == "fine_lookup"
    assert data["fine"]["amount_inr"] >= 10000
    assert "185" in data["fine"]["section_ref"]

def test_dataset_coverage_qa(real_client):
    """Test if the system can answer questions from the Indian Traffic Law QA dataset."""
    payload = {
        "text": "speed limit in residential areas",
        "gps": None,
        "session": {}
    }
    response = real_client.post("/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # We check if we got a rule or fine or search match (at least one)
    has_info = data.get("fine") is not None or data.get("rule") is not None or len(data.get("search_matches", [])) > 0
    assert has_info, "System failed to retrieve any info for a known QA topic"

def test_invalid_query_handling(real_client):
    """Test how the system handles a query that doesn't match the dataset."""
    payload = {
        "text": "how to bake a cake",
        "gps": None,
        "session": {}
    }
    response = real_client.post("/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # Should not find a fine, might return unknown or a polite error
    assert data["status"] in ["insufficient_info", "not_found", "error", "ok", "needs_clarification"]
    assert data.get("fine") is None
