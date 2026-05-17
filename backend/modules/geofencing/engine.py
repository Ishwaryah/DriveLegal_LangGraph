import os
import json
import logging
from datetime import datetime
from typing import List, Dict
from shapely.geometry import shape, Point

# Import the base class from services
from backend.services.geofencing_engine import GeofencingEngine as BaseGeofencingEngine

logger = logging.getLogger(__name__)

class GeofencingEngine(BaseGeofencingEngine):
    def __init__(self, zones_dir: str):
        super().__init__(zones_dir)

    def _load_zones(self):
        # Fallback/Backward compatibility for internal legacy call
        self.load_all_zones(self.zones_dir)

    def detect_zones(self, lat: float, lon: float) -> List[Dict]:
        """
        Backward compatibility method. Returns raw properties of matching zones.
        Enhanced with support for buffering LineString and Point geometries.
        """
        point = Point(lon, lat)  # shapely uses (lon, lat) i.e. (x, y)
        matches = []
        for zone in self.zones:
            geom = zone["geometry"]
            props = zone["properties"]
            matched = False

            if geom.geom_type == "Point":
                buffer_meters = float(props.get("buffer_meters", 150))
                buffer_degrees = buffer_meters / 111320.0
                if geom.buffer(buffer_degrees).contains(point):
                    matched = True
            elif geom.geom_type == "LineString":
                buffer_meters = float(props.get("buffer_meters", 100))
                buffer_degrees = buffer_meters / 111320.0
                if geom.buffer(buffer_degrees).contains(point):
                    matched = True
            else:  # Polygon or MultiPolygon
                if geom.contains(point):
                    matched = True

            if matched:
                matches.append(props)
        return matches

    def is_in_zone(self, lat: float, lon: float, zone_type: str) -> bool:
        zones = self.detect_zones(lat, lon)
        return any(z.get("zone_type") == zone_type for z in zones)

    def get_applicable_rules(self, lat: float, lon: float, current_time: str = None) -> List[Dict]:
        """
        current_time format: "HH:MM"
        """
        if current_time is None:
            current_time = datetime.now().strftime("%H:%M")
        
        matched_zones = self.detect_zones(lat, lon)
        applicable = []
        
        for zone in matched_zones:
            # Check either "active_hours" (old) or "time_window" (new)
            active_hours = zone.get("active_hours") or zone.get("time_window") or "ALL"
            # Support both comma-separated time windows
            ranges = active_hours.split(",")
            is_active = False
            for time_range in ranges:
                if time_range == "ALL":
                    is_active = True
                    break
                if self._is_time_in_range(current_time, time_range.strip()):
                    is_active = True
                    break
            if is_active:
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
            else:  # Over midnight
                return curr_time >= start_time or curr_time <= end_time
        except Exception as e:
            logger.error(f"Error parsing time range {range_str}: {e}")
            return True
