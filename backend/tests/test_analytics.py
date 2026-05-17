import os
import sys
import json

# Ensure the workspace root is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.services.analytics_service import AnalyticsService
from fastapi.testclient import TestClient
from backend.main import app

def run_direct_tests():
    print("=" * 80)
    print("1. RUNNING DIRECT SERVICE TESTS ON AnalyticsService")
    print("=" * 80)
    
    service = AnalyticsService()
    
    # ── Test Case 1: TN Risk Score ──
    print("\n[TEST CASE 1] GET STATE RISK SCORE FOR TAMIL NADU (TN)")
    print("-" * 60)
    tn_risk = service.get_state_risk_score("TN")
    print(json.dumps(tn_risk, indent=2))
    assert tn_risk.get("state_code") == "TN"
    assert tn_risk.get("risk_score") is not None
    assert tn_risk.get("risk_level") is not None
    print("-> Test Case 1 Passed!")

    # ── Test Case 2: National Violation Heatmap ──
    print("\n[TEST CASE 2] GET NATIONAL VIOLATION HEATMAP")
    print("-" * 60)
    national_heatmap = service.get_violation_heatmap_data()
    print(f"Retrieved {len(national_heatmap)} violation categories.")
    print("Top 3 violations nationally:")
    for v in national_heatmap[:3]:
        print(f"  - {v['violation']} ({v['section']}): {v['percentage']}% of accidents, Count: {v['count']}, Avg Fine: INR {v['avg_fine_inr']}")
    assert len(national_heatmap) > 0
    assert any(v["violation"] == "Over Speeding" for v in national_heatmap)
    print("-> Test Case 2 Passed!")

    # ── Test Case 3: Weather Risk for Mumbai in Heavy Rain ──
    print("\n[TEST CASE 3] GET WEATHER RISK FOR MUMBAI IN HEAVY RAIN")
    print("-" * 60)
    # Mumbai coordinates: lat 19.0760, lng 72.8777
    mumbai_lat, mumbai_lng = 19.0760, 72.8777
    weather_risk = service.get_weather_risk_for_route(mumbai_lat, mumbai_lng, "Heavy Rain")
    print(json.dumps(weather_risk, indent=2))
    assert weather_risk.get("condition") == "Heavy Rain"
    assert weather_risk.get("risk_multiplier") > 1.0
    print("-> Test Case 3 Passed!")

    # ── Test Case 4: TN vs National Comparison ──
    print("\n[TEST CASE 4] GET TN VS NATIONAL COMPARISON")
    print("-" * 60)
    tn_comparison = service.get_national_comparison("TN")
    print(json.dumps(tn_comparison, indent=2))
    assert tn_comparison.get("state_code") == "TN"
    assert "comparison" in tn_comparison
    print("-> Test Case 4 Passed!")


def run_api_tests():
    print("\n" + "=" * 80)
    print("2. RUNNING FASTAPI ENDPOINT TESTS VIA TestClient")
    print("=" * 80)
    
    client = TestClient(app)
    
    # ── API Endpoint 1: State Risk ──
    print("\n[API GET] /api/v1/analytics/state-risk/TN")
    print("-" * 60)
    response = client.get("/api/v1/analytics/state-risk/TN")
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    assert response.status_code == 200
    
    # ── API Endpoint 2: Violations Heatmap ──
    print("\n[API GET] /api/v1/analytics/violations?state=DL&year=2023")
    print("-" * 60)
    response = client.get("/api/v1/analytics/violations?state=DL&year=2023")
    print(f"Status Code: {response.status_code}")
    # Print just first 3 to save space
    print(json.dumps(response.json()[:3], indent=2))
    assert response.status_code == 200
    
    # ── API Endpoint 3: Safety Trend ──
    print("\n[API GET] /api/v1/analytics/safety-trend/TN?years=2019,2020,2021,2022,2023")
    print("-" * 60)
    response = client.get("/api/v1/analytics/safety-trend/TN?years=2019,2020,2021,2022,2023")
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    assert response.status_code == 200
    
    # ── API Endpoint 4: National Comparison ──
    print("\n[API GET] /api/v1/analytics/national-comparison/TN")
    print("-" * 60)
    response = client.get("/api/v1/analytics/national-comparison/TN")
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    assert response.status_code == 200
    
    # ── API Endpoint 5: Weather Risk ──
    print("\n[API GET] /api/v1/analytics/weather-risk?lat=19.0760&lng=72.8777&condition=Heavy Rain")
    print("-" * 60)
    response = client.get("/api/v1/analytics/weather-risk?lat=19.0760&lng=72.8777&condition=Heavy Rain")
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    assert response.status_code == 200

    print("\n" + "=" * 80)
    print("ALL API ROUTER ENDPOINT TESTS COMPLETED SUCCESSFULLY! [SUCCESS]")
    print("=" * 80)


if __name__ == "__main__":
    run_direct_tests()
    run_api_tests()
