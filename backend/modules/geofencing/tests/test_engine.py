import os
import json
import tempfile
import shutil
import unittest
from backend.modules.geofencing.engine import GeofencingEngine

class TestGeofencingEngine(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        
        # Create a mock zone
        self.mock_zone = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "zone_id": "TEST_ZONE_1",
                        "zone_type": "school_zone",
                        "active_hours": "08:00-17:00",
                        "rule_set_id": "RULE_1"
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
                    }
                }
            ]
        }
        
        with open(os.path.join(self.test_dir, "test_zone.geojson"), "w") as f:
            json.dump(self.mock_zone, f)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_point_inside_zone(self):
        engine = GeofencingEngine(self.test_dir)
        results = engine.detect_zones(0.5, 0.5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["zone_id"], "TEST_ZONE_1")

    def test_point_outside_zone(self):
        engine = GeofencingEngine(self.test_dir)
        results = engine.detect_zones(2.0, 2.0)
        self.assertEqual(len(results), 0)

    def test_active_hours_filter(self):
        engine = GeofencingEngine(self.test_dir)
        # Inside hours
        results = engine.get_applicable_rules(0.5, 0.5, current_time="10:00")
        self.assertEqual(len(results), 1)
        
        # Outside hours
        results = engine.get_applicable_rules(0.5, 0.5, current_time="20:00")
        self.assertEqual(len(results), 0)

    def test_empty_zones_dir(self):
        empty_dir = tempfile.mkdtemp()
        try:
            engine = GeofencingEngine(empty_dir)
            results = engine.detect_zones(0.5, 0.5)
            self.assertEqual(results, [])
        finally:
            shutil.rmtree(empty_dir)

if __name__ == "__main__":
    unittest.main()
