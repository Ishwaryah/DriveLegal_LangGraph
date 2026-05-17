import os
import json
import logging
import geojson
from datetime import datetime
from typing import List, Dict
from shapely.geometry import shape, Point

logger = logging.getLogger(__name__)

class GeofencingEngine:
    def __init__(self, zones_dir: str = None):
        self.zones = []
        self.zones_dir = zones_dir
        if zones_dir:
            self.load_all_zones(zones_dir)

    def load_all_zones(self, zones_dir: str):
        """
        Recursively loads all .geojson files from the zones directory.
        Includes error handling for malformed GeoJSON files.
        """
        self.zones_dir = zones_dir
        self.zones = []
        if not os.path.exists(zones_dir):
            logger.warning(f"Zones directory {zones_dir} does not exist.")
            return

        geojson_files = []
        for root, _, files in os.walk(zones_dir):
            for file in files:
                if file.endswith(".geojson") and file != "template.geojson" and file != "india_states.geojson":
                    geojson_files.append(os.path.join(root, file))

        for file_path in geojson_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = geojson.load(f)
                    
                    # Validate and parse features
                    if not isinstance(data, geojson.FeatureCollection):
                        if isinstance(data, dict) and "features" in data:
                            features = data["features"]
                        else:
                            features = [data]
                    else:
                        features = data.get("features", [])

                    for feature in features:
                        if "geometry" in feature and "properties" in feature:
                            geom = shape(feature["geometry"])
                            props = feature["properties"]
                            self.zones.append({
                                "geometry": geom,
                                "properties": props
                            })
            except Exception as e:
                logger.error(f"Error loading/parsing GeoJSON file {file_path}: {e}")

    def check_location(self, lat: float, lng: float) -> List[Dict]:
        """
        Checks which zones a given lat/lng point falls inside.
        For LineString and Point, it buffers them using `buffer_meters` property value.
        """
        point = Point(lng, lat)  # Shapely geometries use (x, y) i.e. (lng, lat)
        matches = []
        
        for zone in self.zones:
            geom = zone["geometry"]
            props = zone["properties"]
            matched = False

            if geom.geom_type == "Point":
                buffer_meters = float(props.get("buffer_meters", 150))
                # 1 degree lat/lng is approx 111,320 meters
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
                matches.append({
                    "zone_type": props.get("zone_type", "UNKNOWN"),
                    "alert_message": props.get("alert_message", "No alert message"),
                    "fine_amount_inr": int(props.get("fine_amount_inr", 0)) if props.get("fine_amount_inr") is not None else 0,
                    "fine_section": props.get("fine_section", "N/A"),
                    "zone_name": props.get("zone_name") or props.get("zone_id", "Unnamed Zone")
                })
                
        return matches

    def get_active_zones(self, lat: float, lng: float, current_time: datetime) -> List[Dict]:
        """
        Checks location and filters zones by time_window and applicable_days if present.
        """
        point = Point(lng, lat)
        matched_raw_props = []

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
                matched_raw_props.append(props)

        active_zones = []
        current_t = current_time.time()
        current_day = current_time.strftime("%A")

        for props in matched_raw_props:
            # 1. Check applicable days if present
            applicable_days = props.get("applicable_days")
            if applicable_days:
                if current_day not in applicable_days:
                    continue

            # 2. Check time windows if present
            time_window = props.get("time_window")
            if time_window:
                is_active = False
                # support multiple comma-separated time ranges
                ranges = time_window.split(",")
                for time_range in ranges:
                    try:
                        start_str, end_str = time_range.strip().split("-")
                        start_time = datetime.strptime(start_str, "%H:%M").time()
                        end_time = datetime.strptime(end_str, "%H:%M").time()

                        if start_time <= end_time:
                            if start_time <= current_t <= end_time:
                                is_active = True
                                break
                        else:  # Over midnight
                            if current_t >= start_time or current_t <= end_time:
                                is_active = True
                                break
                    except Exception as e:
                        logger.error(f"Error parsing time window range '{time_range}': {e}")
                        is_active = True  # Fallback to active on malformed format
                if not is_active:
                    continue

            active_zones.append({
                "zone_type": props.get("zone_type", "UNKNOWN"),
                "alert_message": props.get("alert_message", "No alert message"),
                "fine_amount_inr": int(props.get("fine_amount_inr", 0)) if props.get("fine_amount_inr") is not None else 0,
                "fine_section": props.get("fine_section", "N/A"),
                "zone_name": props.get("zone_name") or props.get("zone_id", "Unnamed Zone")
            })

        return active_zones
