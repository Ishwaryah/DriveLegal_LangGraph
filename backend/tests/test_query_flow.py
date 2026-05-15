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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fines (
            id INTEGER PRIMARY KEY,
            offence_code TEXT,
            vehicle_class TEXT,
            state TEXT,
            amount_inr INTEGER,
            repeat_amount_inr INTEGER,
            section_ref TEXT,
            source_url TEXT,
            fetched_at TEXT,
            version_hash TEXT UNIQUE
        )
    """)
    conn.execute("DELETE FROM fines")
    conn.execute("""
        INSERT INTO fines (offence_code, vehicle_class, state, amount_inr, section_ref, version_hash)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ("no helmet", "2W", "Tamil Nadu", 1000, "129 MVA", "hash1"))
    conn.commit()
    conn.close()
    
    # 2. Seed Rules JSON
    rules_data = {
        "rules": [
            {
                "rule_id": "rule_129",
                "title": "Helmet Requirement",
                "description": "Every person driving or riding a motorcycle shall wear protective headgear.",
                "related_offence_codes": ["no helmet"]
            }
        ]
    }
    with open(rules_path, "w") as f:
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
    main.builder = ResponseBuilder(main.fine_lookup, main.rules_loader, main.geofencing)

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
    assert data["rule"]["rule_id"] == "rule_129"
    assert "no helmet" in data["query_summary"].lower()

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
    assert any("not available" in w.lower() for w in data["warnings"])

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
    Vague query "tell me about fines" → status insufficient_info
    """
    payload = {
        "text": "tell me about traffic laws",
        "gps": None,
        "session": {}
    }
    response = client.post("/query", json=payload)
    data = response.json()
    
    assert data["status"] == "insufficient_info"
    assert data["intent"] == "unknown"
