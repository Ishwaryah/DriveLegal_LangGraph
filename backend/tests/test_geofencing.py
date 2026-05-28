import os
import sys
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.services.geofencing_engine import GeofencingEngine

_zones_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "zones"))
_engine = GeofencingEngine(_zones_dir)
_test_time = datetime(2026, 5, 18, 12, 0, 0)


def test_connaught_place_odd_even_zone():
    active = _engine.get_active_zones(28.6315, 77.2167, _test_time)
    zone_types = [z["zone_type"] for z in active]
    assert "ODD_EVEN_RESTRICTION" in zone_types


def test_aiims_silent_zone():
    active = _engine.get_active_zones(28.5672, 77.2100, _test_time)
    zone_types = [z["zone_type"] for z in active]
    assert "SILENT_ZONE" in zone_types


def test_nh48_highway_corridor():
    active = _engine.get_active_zones(18.8897, 73.7501, _test_time)
    zone_types = [z["zone_type"] for z in active]
    assert "HIGHWAY_SPEED_CORRIDOR" in zone_types


def test_marina_beach_no_active_zones():
    active = _engine.get_active_zones(13.0500, 80.2824, _test_time)
    assert len(active) == 0
