import pytest
from fastapi.testclient import TestClient
from backend.main import app
import os
import sqlite3

client = TestClient(app)

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/fines.db"))

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "country_counts" in data
    assert "IN" in data["country_counts"]

def test_calculate_challan():
    payload = {
        "violation_codes": ["no_helmet", "overspeeding"],
        "vehicle_type": "two_wheeler",
        "country": "IN",
        "state_province": "Tamil Nadu",
        "is_repeat_offense": False
    }
    
    response = client.post("/api/v1/challan/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["currency"] == "INR"
    assert len(data["violations"]) > 0
    
    # Verify compounding fields
    assert "compounding_available" in data
    assert "total_compounding_fee" in data

def test_get_country_fines():
    response = client.get("/api/v1/fines/country/IN")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["country"] == "IN"
    
def test_get_country_fines_with_filters():
    response = client.get("/api/v1/fines/country/IN?vehicle_type=two_wheeler&state_province=Tamil%20Nadu")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    # Make sure we only get applicable types
    for fine in data:
        assert fine["vehicle_type"] in ["two_wheeler", "all"]

def test_search_fines():
    response = client.get("/api/v1/fines/search?q=helmet&country=IN")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    for fine in data:
        assert "helmet" in fine["violation_name"].lower() or (fine["notes"] and "helmet" in fine["notes"].lower())

def test_get_supported_countries():
    response = client.get("/api/v1/fines/countries")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    country_codes = [c["code"] for c in data]
    assert "IN" in country_codes
    assert "AE" in country_codes

def test_get_compounding():
    response = client.get("/api/v1/fines/compounding?state=Tamil%20Nadu&violation=no_helmet&vehicle_type=two_wheeler")
    assert response.status_code == 200
    data = response.json()
    assert "compounding_eligible" in data
    assert "compounding_fee" in data

def test_get_compounding_not_found():
    response = client.get("/api/v1/fines/compounding?state=XX&violation=invalid_code&vehicle_type=two_wheeler")
    assert response.status_code == 404

def test_challan_live_lookup_no_key(monkeypatch):
    """When RAPIDAPI_KEY is absent the endpoint returns service_unavailable, not 5xx."""
    import backend.main as main_mod
    monkeypatch.setattr(main_mod, "rapid_api_provider", None)
    response = client.post("/challan/calculate", json={"vehicle_number": "TN01AB1234"})
    assert response.status_code == 200
    assert response.json()["status"] == "service_unavailable"
