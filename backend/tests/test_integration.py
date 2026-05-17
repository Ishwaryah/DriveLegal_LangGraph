import os
import sys
import json
import logging
from datetime import datetime

# Ensure project root/backend directories are on the path for absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.services.parivahan_service import ParivahanService
from backend.services.document_validator import DocumentValidator
from backend.services.geofencing_engine import GeofencingEngine
from backend.services.emergency_service import EmergencyService
from backend.services.analytics_service import AnalyticsService

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("drivelegal.test_integration")

def test_integration_flow():
    """
    E2E integration test simulating the entire DriveLegal data pipeline.
    """
    logger.info("Initializing Integration Test Flow...")
    
    # ── Path Resolution ────────────────────────────────────────────────────────
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    zones_dir = os.path.join(base_dir, "data", "zones")
    
    # ── 1. Component Initialization ───────────────────────────────────────────
    parivahan = ParivahanService()
    validator = DocumentValidator()
    geofencing = GeofencingEngine(zones_dir)
    emergency = EmergencyService()
    analytics = AnalyticsService()
    
    # ── 2. Run Pipeline Steps ──────────────────────────────────────────────────
    
    # Step 1: User enters vehicle number "TN09AB1234"
    vehicle_number = "TN09AB1234"
    logger.info("Step 1: User requested lookup for vehicle number: %s", vehicle_number)
    
    # Step 2: Call ParivahanService.get_rc_details()
    rc_result = parivahan.get_rc_details(vehicle_number)
    assert rc_result.get("success") is True, f"Parivahan lookup failed for {vehicle_number}"
    rc_data = rc_result["data"]
    logger.info("Step 2: Retrieved RC details successfully.")
    
    # Transform RC data for validator format
    registration_date_str = rc_data.get("registration_date")
    if registration_date_str:
        reg_date = datetime.strptime(registration_date_str, "%Y-%m-%d")
        vehicle_age_years = (datetime.now() - reg_date).days / 365.25
    else:
        vehicle_age_years = 1.0

    validator_input = {
        "vehicle_type": rc_data.get("vehicle_class", "LMV"),
        "fuel_type": rc_data.get("fuel_type", "Petrol"),
        "vehicle_age_years": vehicle_age_years,
        "state": "TN",
        "last_puc_date": rc_data.get("puc_valid_upto"),
        "policy_expiry_date": rc_data.get("insurance_valid_upto"),
        "fitness_expiry_date": rc_data.get("fitness_valid_upto"),
        "vehicle_category": rc_data.get("vehicle_class", "LMV"),
        "dl_categories": ["LMV", "MCWG"],
        "vehicle_being_driven": "LMV"
    }
    
    # Step 3: Call DocumentValidator.validate_all_documents() on RC data
    validation_result = validator.validate_all_documents(validator_input)
    logger.info("Step 3: Executed document validation.")
    
    # Step 4 & 5: Geofencing GPS check
    gps_lat, gps_lng = 13.0827, 80.2707  # Chennai coordinates
    logger.info("Step 4: User location GPS: (%s, %s)", gps_lat, gps_lng)
    
    active_zones = geofencing.get_active_zones(gps_lat, gps_lng, datetime.now())
    logger.info("Step 5: Retrieved %d active geofencing zones.", len(active_zones))
    
    # Step 6: Emergency Contacts for "TN"
    state_code = "TN"
    emergency_contacts = emergency.get_state_emergency_contacts(state_code)
    logger.info("Step 6: Loaded emergency contacts for state: %s", state_code)
    
    # Step 7: Analytics Risk Score for "TN"
    risk_score = analytics.get_state_risk_score(state_code)
    logger.info("Step 7: Generated analytics risk score for state: %s", state_code)
    
    # Step 8: Combine all results into final_response dict
    final_response = {
        "metadata": {
            "tested_at": datetime.now().isoformat(),
            "target_vehicle": vehicle_number,
            "target_gps": [gps_lat, gps_lng],
            "resolved_state": state_code
        },
        "rc_verification": {
            "source": rc_result.get("source"),
            "owner": rc_data.get("owner_name"),
            "vehicle_class": rc_data.get("vehicle_class"),
            "fuel_type": rc_data.get("fuel_type"),
            "status": rc_data.get("status"),
            "raw_details": rc_data
        },
        "document_compliance": {
            "all_clear": validation_result.get("all_clear"),
            "total_pending_fines_inr": validation_result.get("total_fine_inr"),
            "violations_detected": validation_result.get("violations_detected"),
            "compliance_ledger": validation_result.get("detailed_checks")
        },
        "active_geofences": active_zones,
        "state_emergency": {
            "state_name": emergency_contacts.get("state_name", "Tamil Nadu"),
            "police": emergency_contacts.get("police", "100"),
            "ambulance": emergency_contacts.get("ambulance", "108"),
            "helplines": emergency_contacts.get("helplines", {}),
            "protection_provisions": emergency_contacts.get("protection_provisions", [])
        },
        "state_analytics": risk_score
    }
    
    # Pretty-print
    print("\n" + "=" * 80)
    print("                DRIVELEGAL INTEGRATION PIPELINE TEST RESULTS")
    print("=" * 80)
    print(json.dumps(final_response, indent=2))
    print("=" * 80)
    print("INTEGRATION PIPELINE RUN COMPLETED SUCCESSFULLY! [SUCCESS]")
    print("=" * 80)

if __name__ == "__main__":
    test_integration_flow()
