import os
import sys
from datetime import datetime

# Ensure the workspace root is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.services.geofencing_engine import GeofencingEngine

def run_tests():
    # Locate zones directory
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    zones_dir = os.path.join(base_dir, "data", "zones")
    
    print("=" * 80)
    print(f"Initializing GeofencingEngine with zones from: {zones_dir}")
    print("=" * 80)
    
    engine = GeofencingEngine(zones_dir)
    print(f"Loaded {len(engine.zones)} geofencing zone features.")
    
    # Coordinates to test
    test_cases = [
        {
            "name": "Connaught Place Delhi",
            "lat": 28.6315,
            "lng": 77.2167,
            "expected": "ODD_EVEN_RESTRICTION",
            "test_time": datetime(2026, 5, 18, 12, 0, 0)  # Monday 12:00 PM
        },
        {
            "name": "AIIMS Delhi",
            "lat": 28.5672,
            "lng": 77.2100,
            "expected": "SILENT_ZONE",
            "test_time": datetime(2026, 5, 18, 12, 0, 0)
        },
        {
            "name": "NH-48 Expressway",
            "lat": 18.8897,
            "lng": 73.7501,
            "expected": "HIGHWAY_SPEED_CORRIDOR",
            "test_time": datetime(2026, 5, 18, 12, 0, 0)
        },
        {
            "name": "Marina Beach Chennai",
            "lat": 13.0500,
            "lng": 80.2824,
            "expected": "None",
            "test_time": datetime(2026, 5, 18, 12, 0, 0)
        }
    ]
    
    success = True
    for case in test_cases:
        name = case["name"]
        lat = case["lat"]
        lng = case["lng"]
        expected = case["expected"]
        test_time = case["test_time"]
        
        print("\n" + "-" * 60)
        print(f"TEST CASE: {name} ({lat}, {lng})")
        print(f"Testing at: {test_time.strftime('%A, %Y-%m-%d %H:%M:%S')}")
        print("-" * 60)
        
        # 1. Test check_location (Geometrical check only)
        matched_geom = engine.check_location(lat, lng)
        print(f"1. check_location() matched {len(matched_geom)} zone(s):")
        for z in matched_geom:
            print(f"   - Name    : {z['zone_name']}")
            print(f"     Type    : {z['zone_type']}")
            print(f"     Alert   : {z['alert_message']}")
            print(f"     Section : {z['fine_section']}")
            print(f"     Fine    : INR {z['fine_amount_inr']}")
            
        # 2. Test get_active_zones (Geometrical + Time range check)
        active_zones = engine.get_active_zones(lat, lng, test_time)
        print(f"\n2. get_active_zones() matched {len(active_zones)} active zone(s):")
        for z in active_zones:
            print(f"   - Name    : {z['zone_name']}")
            print(f"     Type    : {z['zone_type']}")
            print(f"     Alert   : {z['alert_message']}")
            print(f"     Section : {z['fine_section']}")
            print(f"     Fine    : INR {z['fine_amount_inr']}")
            
        # Verify expectations
        matched_types = [z['zone_type'] for z in active_zones]
        if expected == "None":
            passed = len(active_zones) == 0
            status_str = "PASSED (No active zones as expected)" if passed else "FAILED (Expected no active zones)"
        else:
            passed = expected in matched_types
            status_str = f"PASSED (Found active zone type '{expected}')" if passed else f"FAILED (Expected active zone type '{expected}')"
            
        if not passed:
            success = False
            
        print(f"\nSTATUS: {status_str}")
        
    print("\n" + "=" * 80)
    if success:
        print("ALL GEOFENCING TEST CASES COMPLETED SUCCESSFULLY! [SUCCESS]")
    else:
        print("SOME GEOFENCING TEST CASES FAILED! [FAILURE]")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
