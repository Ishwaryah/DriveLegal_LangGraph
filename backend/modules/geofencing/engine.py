import os
import json
import logging
from datetime import datetime
from typing import List, Dict
from shapely.geometry import shape, Point

logger = logging.getLogger(__name__)

class GeofencingEngine:
    def __init__(self, zones_dir: str):
        self.zones_dir = zones_dir
        self.zones = []
        self._load_zones()

    def _load_zones(self):
        if not os.path.exists(self.zones_dir):
            logger.warning(f"Zones directory {self.zones_dir} does not exist.")
            return

        geojson_files = []
        for root, _, files in os.walk(self.zones_dir):
            for file in files:
                if file.endswith(".geojson") and file != "template.geojson" and file != "india_states.geojson":
                    geojson_files.append(os.path.join(root, file))

        if not geojson_files:
            logger.warning(f"No GeoJSON files found in {self.zones_dir}")
            return

        for file_path in geojson_files:
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    if "features" in data:
                        for feature in data["features"]:
                            geom = shape(feature["geometry"])
                            props = feature["properties"]
                            self.zones.append({
                                "geometry": geom,
                                "properties": props
                            })
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")

    def detect_zones(self, lat: float, lon: float) -> List[Dict]:
        point = Point(lon, lat)
        matches = []
        for zone in self.zones:
            if zone["geometry"].contains(point):
                matches.append(zone["properties"])
        return matches

    def is_in_zone(self, lat: float, lon: float, zone_type: str) -> bool:
        zones = self.detect_zones(lat, lon)
        return any(z["zone_type"] == zone_type for z in zones)

    def get_applicable_rules(self, lat: float, lon: float, current_time: str = None) -> List[Dict]:
        """
        current_time format: "HH:MM"
        """
        if current_time is None:
            current_time = datetime.now().strftime("%H:%M")
        
        matched_zones = self.detect_zones(lat, lon)
        applicable = []
        
        for zone in matched_zones:
            active_hours = zone.get("active_hours", "ALL")
            if self._is_time_in_range(current_time, active_hours):
                applicable.append(zone)
        
        return applicable

    def _is_time_in_range(self, current_time: str, range_str: str) -> bool:
        if range_str == "ALL":
            return True
        
        try:
            start_str, end_str = range_str.split("-")
            start_time = datetime.strptime(start_str, "%H:%M").time()
            end_time = datetime.strptime(end_str, "%H:%M").time()
            curr_time = datetime.strptime(current_time, "%H:%M").time()
            
            if start_time <= end_time:
                return start_time <= curr_time <= end_time
            else: # Over midnight
                return curr_time >= start_time or curr_time <= end_time
        except Exception as e:
            logger.error(f"Error parsing time range {range_str}: {e}")
            return True # Fallback to active if malformed? Or False? Let's say True to be safe
