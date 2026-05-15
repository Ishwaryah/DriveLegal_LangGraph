import os
import json
import logging
from shapely.geometry import shape, Point

logger = logging.getLogger(__name__)

def reverse_geocode(lat: float, lon: float, zones_dir: str) -> dict:
    """
    Returns: {state, city, district} by checking which state polygon contains the point.
    """
    states_file = os.path.join(zones_dir, "india_states.geojson")
    if not os.path.exists(states_file):
        logger.warning(f"States boundary file not found: {states_file}")
        return {"state": "UNKNOWN"}

    try:
        point = Point(lon, lat)
        with open(states_file, "r") as f:
            data = json.load(f)
            
        for feature in data.get("features", []):
            geom = shape(feature["geometry"])
            if geom.contains(point):
                props = feature["properties"]
                return {
                    "state": props.get("state", "UNKNOWN"),
                    "city": props.get("city", "UNKNOWN"),
                    "district": props.get("district", "UNKNOWN")
                }
    except Exception as e:
        logger.error(f"Error in reverse_geocode: {e}")
    
    return {"state": "UNKNOWN"}
