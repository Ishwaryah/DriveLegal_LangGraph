import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.services.analytics_service import AnalyticsService
from fastapi.testclient import TestClient
from backend.main import app


def test_state_risk_score():
    service = AnalyticsService()
    result = service.get_state_risk_score("TN")
    assert result.get("state_code") == "TN"
    assert result.get("risk_score") is not None
    assert result.get("risk_level") is not None


def test_national_violation_heatmap():
    service = AnalyticsService()
    result = service.get_violation_heatmap_data()
    assert len(result) > 0
    assert any(v["violation"] == "Over Speeding" for v in result)


def test_weather_risk_heavy_rain():
    service = AnalyticsService()
    result = service.get_weather_risk_for_route(19.0760, 72.8777, "Heavy Rain")
    assert result.get("condition") == "Heavy Rain"
    assert result.get("risk_multiplier") > 1.0


def test_national_comparison():
    service = AnalyticsService()
    result = service.get_national_comparison("TN")
    assert result.get("state_code") == "TN"
    assert "comparison" in result


def test_api_state_risk():
    client = TestClient(app)
    response = client.get("/api/v1/analytics/state-risk/TN")
    assert response.status_code == 200


def test_api_violations_heatmap():
    client = TestClient(app)
    response = client.get("/api/v1/analytics/violations?state=DL&year=2023")
    assert response.status_code == 200


def test_api_safety_trend():
    client = TestClient(app)
    response = client.get("/api/v1/analytics/safety-trend/TN?years=2019,2020,2021,2022,2023")
    assert response.status_code == 200


def test_api_national_comparison():
    client = TestClient(app)
    response = client.get("/api/v1/analytics/national-comparison/TN")
    assert response.status_code == 200


def test_api_weather_risk():
    client = TestClient(app)
    response = client.get("/api/v1/analytics/weather-risk?lat=19.0760&lng=72.8777&condition=Heavy Rain")
    assert response.status_code == 200
