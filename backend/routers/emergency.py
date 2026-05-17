from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from typing import Optional
from backend.services.emergency_service import EmergencyService

router = APIRouter(prefix="/api/v1/emergency", tags=["Emergency Services"])
service = EmergencyService()


class AccidentReportRequest(BaseModel):
    lat: float
    lng: float
    description: Optional[str] = None


@router.get("/contacts/{state_code}", summary="Get emergency contacts by state code")
def get_contacts(state_code: str):
    """
    Retrieve statewise emergency helplines, trauma centers, RTO locations,
    and specific state-level implementation details of the Good Samaritan law (Section 134A).
    Supported states: TN, MH, DL, KA, GJ, RJ, UP, WB, TS, AP.
    """
    contacts = service.get_state_emergency_contacts(state_code)
    if not contacts:
        raise HTTPException(
            status_code=404,
            detail=f"Emergency contacts for state code '{state_code}' not found. Supported codes: TN, MH, DL, KA, GJ, RJ, UP, WB, TS, AP."
        )
    return contacts


@router.get("/nearest-hospital", summary="Find the nearest government trauma centers")
def get_nearest_hospital(
    lat: float = Query(..., description="Latitude of current location"),
    lng: float = Query(..., description="Longitude of current location"),
    max_results: int = Query(3, description="Maximum number of trauma centers to return")
):
    """
    Calculate and return the nearest trauma centers using the Haversine formula
    on the pre-validated government trauma center database.
    """
    try:
        centers = service.get_nearest_trauma_center(lat, lng, max_results=max_results)
        return centers
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate nearest trauma centers: {str(e)}"
        )


@router.get("/good-samaritan-rights", summary="Retrieve rights and scene-response guidelines")
def get_good_samaritan_rights(
    lang: str = Query("en", description="Preferred language for the rights and steps ('en' or 'hi')")
):
    """
    Get legal rights under Section 134A and detailed first-aid guidelines.
    Includes translations for English ('en') and Hindi ('hi') to support native helpers.
    """
    rights = service.get_good_samaritan_rights(lang)
    if not rights:
        raise HTTPException(
            status_code=404,
            detail="Good Samaritan guide content is unavailable."
        )
    return rights


@router.post("/accident-report", summary="Submit accident coordinates and get rapid response data")
def create_accident_report(request: AccidentReportRequest = Body(...)):
    """
    Report an accident by coordinates to retrieve a highly curated, consolidated emergency packet.
    Returns:
    - Nearest trauma hospitals with calculated distances
    - State-specific emergency helplines
    - Nearest RTO coordinates and contact details
    - Complete Good Samaritan scene-handling guide
    """
    try:
        report = service.handle_accident_report(request.lat, request.lng)
        if request.description:
            report["description"] = request.description
        return report
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process accident report flow: {str(e)}"
        )
