import pytest
import os
import json
import sqlite3
from fastapi.testclient import TestClient
from backend.main import app

# We'll use the real app but we need to ensure the data for testing exists.
# For integration tests, we can override dependencies or just ensure files exist.

@pytest.fixture(scope="module")
def test_data_setup():
    # Setup temporary data directory
    test_dir = "backend/tests/test_data"
    os.makedirs(test_dir, exist_ok=True)
    os.makedirs(os.path.join(test_dir, "zones"), exist_ok=True)
    
    db_path = os.path.join(test_dir, "fines.db")
    rules_path = os.path.join(test_dir, "rules.json")
    
    # 1. Seed Fines DB
    conn = sqlite3.connect(db_path)
    conn.execute("DROP TABLE IF EXISTS fines")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fines (
            id INTEGER PRIMARY KEY,
            violation_code TEXT,
            vehicle_type TEXT,
            state_province TEXT,
            country TEXT,
            min_fine_local INTEGER,
            max_fine_local INTEGER,
            mv_act_section TEXT,
            currency TEXT,
            notes TEXT
        )
    """)
    conn.execute("DELETE FROM fines")
    conn.execute("""
        INSERT INTO fines (violation_code, vehicle_type, state_province, country, min_fine_local, max_fine_local, mv_act_section, currency, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ("no_helmet", "two_wheeler", "Tamil Nadu", "IN", 1000, 1000, "194D MVA", "INR", "Wear helmet"))
    conn.commit()
    conn.close()
    
    # 2. Seed Rules JSON
    rules_data = {
        "rules": [
            {
                "rule_id": "rule_129",
                "title": "Helmet Requirement",
                "description": "Every person driving or riding a motorcycle shall wear protective headgear.",
                "related_offence_codes": ["NO_HELMET"]
            }
        ]
    }
    with open(rules_path, "w", encoding="utf-8") as f:
        json.dump(rules_data, f)
        
    # 3. Seed Geofencing Zone
    zone_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Test Zone", "zone_type": "restricted", "rules": ["No entry for heavy vehicles"]},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[80.0, 13.0], [81.0, 13.0], [81.0, 14.0], [80.0, 14.0], [80.0, 13.0]]]
                }
            }
        ]
    }
    with open(os.path.join(test_dir, "zones", "test.geojson"), "w") as f:
        json.dump(zone_data, f)

    # Patch the main app's paths for testing
    import backend.main as main
    main.FINES_DB = db_path
    main.RULES_JSON = rules_path
    main.ZONES_DIR = os.path.join(test_dir, "zones")
    
    # Re-initialize the engines with test paths
    from backend.modules.fines.lookup import FineLookup
    from backend.modules.rules.loader import RulesLoader
    from backend.modules.geofencing.engine import GeofencingEngine
    from backend.modules.response.builder import ResponseBuilder
    
    main.fine_lookup = FineLookup(db_path)
    main.rules_loader = RulesLoader(rules_path)
    main.geofencing = GeofencingEngine(os.path.join(test_dir, "zones"))
    
    class MockHybridSearch:
        def search(self, query, top_k=3, country="IN"):
            return []
            
    main.hybrid_search = MockHybridSearch()
    main.builder = ResponseBuilder(main.fine_lookup, main.rules_loader, main.geofencing)

    from backend.modules.agent.engine import AgentEngine
    main.agent_engine = AgentEngine(main.fine_lookup, main.rules_loader, main.geofencing)
    main.agent_engine.groq_available = False
    main.agent_engine.hybrid_search = main.hybrid_search
    main.agent_engine.tool_executor.hybrid_search = main.hybrid_search

    yield test_dir
    
    # Cleanup (optional, but good practice)
    # import shutil
    # shutil.rmtree(test_dir)

@pytest.fixture
def client(test_data_setup):
    return TestClient(app)

def test_fine_lookup_end_to_end(client):
    """
    Full pipeline with seeded DB, valid query → status ok, amount returned
    """
    payload = {
        "text": "what is the fine for no helmet on a bike in Tamil Nadu",
        "gps": None,
        "session": {}
    }
    response = client.post("/query", json=payload)
    data = response.json()
    
    assert response.status_code == 200
    assert data["status"] == "ok"
    assert data["intent"] == "fine_lookup"
    assert data["fine"]["amount_inr"] == 1000
    assert "no helmet" in data["query_summary"].lower().replace("_", " ")

def test_not_found(client):
    """
    Valid query but offence not in DB → status not_found, fine null
    """
    payload = {
        "text": "what is the fine for jumping red light in Tamil Nadu",
        "gps": None,
        "session": {}
    }
    response = client.post("/query", json=payload)
    data = response.json()
    
    # NLP might recognize jumping red light, but DB doesn't have it
    assert data["status"] == "not_found"
    assert data["fine"] is None
    assert any("no data" in w.lower() or "not available" in w.lower() for w in data["warnings"])

def test_zone_check_with_gps(client):
    """
    GPS inside mock zone → zone returned
    """
    payload = {
        "text": "check zones",
        "gps": {"lat": 13.5, "lon": 80.5}, # Inside the test zone
        "session": {}
    }
    response = client.post("/query", json=payload)
    data = response.json()
    
    assert response.status_code == 200
    assert data["zone"] is not None
    assert "Test Zone" in data["zone"]["active_zones"]
    assert "No entry for heavy vehicles" in data["zone"]["applicable_rules"][0]

def test_insufficient_info(client):
    """
    Vague query "gibberish text" → status insufficient_info
    """
    payload = {
        "text": "gibberish text",
        "gps": None,
        "session": {}
    }
    response = client.post("/query", json=payload)
    data = response.json()
    
    assert data["status"] == "insufficient_info"
    assert data["intent"] == "unknown"
