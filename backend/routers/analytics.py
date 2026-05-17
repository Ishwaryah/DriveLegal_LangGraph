from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from backend.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics & Dashboard Dashboard"])
service = AnalyticsService()

@router.get("/state-risk/{state_code}", summary="Get composite state risk score and breakdown")
def get_state_risk(state_code: str):
    """
    Computes and returns a composite safety risk score (0-100) for a given state
    along with breakdown variables (accident severity, fatality severity, and violation density rankings).
    Supported states: TN, MH, UP, MP, KA, RJ, GJ, AP, TS, DL, WB, KL.
    """
    result = service.get_state_risk_score(state_code)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message"))
    return result

@router.get("/violations", summary="Get violation heatmap and frequency distribution")
def get_violations(
    state: Optional[str] = Query(None, description="Optional state code to get state-adjusted violation statistics (e.g. TN, DL)"),
    year: str = Query("2023", description="Statistical year to query (e.g. 2019-2023)")
):
    """
    Returns the distribution of traffic violations nationally or for a specific state.
    Calculates simulated counts and percentages along with legal section references
    and average fine amounts for direct Recharts/Chart.js integration.
    """
    result = service.get_violation_heatmap_data(state_code=state, year=year)
    return result

@router.get("/safety-trend/{state_code}", summary="Get safety statistics trends across years")
def get_safety_trend(
    state_code: str,
    years: str = Query("2019,2020,2021,2022,2023", description="Comma-separated list of years to retrieve trends for")
):
    """
    Returns year-over-year statistics (accidents, deaths, injuries) for trend lines.
    Use state_code 'ALL' or empty state to query India national trends.
    """
    try:
        year_list = [int(y.strip()) for y in years.split(",") if y.strip().isdigit()]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid years format. Please provide a comma-separated list of integers.")

    result = service.get_safety_trend(state_code=state_code, years=year_list)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message"))
    return result

@router.get("/national-comparison/{state_code}", summary="Compare state metrics to peers")
def get_national_comparison(state_code: str):
    """
    Compares the given state's accidents, deaths, and injuries against the average
    of all key Indian states to yield percentage differences and a qualitative insight card.
    """
    result = service.get_national_comparison(state_code)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message"))
    return result

@router.get("/weather-risk", summary="Evaluate route-level weather risk multiplier")
def get_weather_risk(
    lat: float = Query(..., description="Latitude of the route/checkpoint location"),
    lng: float = Query(..., description="Longitude of the route/checkpoint location"),
    condition: str = Query(..., description="Current weather condition (Clear, Light Rain, Heavy Rain, Dense Fog, Strong Winds, Hailstorm, Night Driving, Extreme Heat (>45°C))")
):
    """
    Returns the hazard multiplier, advisory alerts, recommended speed reductions,
    and relevant Motor Vehicle Act sections triggered by adverse weather on the route.
    """
    result = service.get_weather_risk_for_route(lat, lng, condition)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result
