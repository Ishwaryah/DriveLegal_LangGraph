import os
import json
import logging
from typing import Optional, List, Dict, Any

# Setup Logger
logger = logging.getLogger("drivelegal.analytics")

# Base directory for relative paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NCRB_PATH = os.path.join(BASE_DIR, "data", "drivelegal_dataset", "json", "ncrb_road_safety_summary.json")
WEATHER_PATH = os.path.join(BASE_DIR, "data", "drivelegal_dataset", "json", "weather_risk_multiplier.json")
ROAD_PATH = os.path.join(BASE_DIR, "data", "drivelegal_dataset", "json", "road_condition_mapping.json")
TRAUMA_CENTERS_PATH = os.path.join(BASE_DIR, "data", "zones", "ALL", "india_trauma_centers.geojson")

STATE_NAMES = {
    "TN": "Tamil Nadu",
    "MH": "Maharashtra",
    "UP": "Uttar Pradesh",
    "MP": "Madhya Pradesh",
    "KA": "Karnataka",
    "RJ": "Rajasthan",
    "GJ": "Gujarat",
    "AP": "Andhra Pradesh",
    "TS": "Telangana",
    "DL": "Delhi",
    "WB": "West Bengal",
    "KL": "Kerala"
}

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    import math
    R = 6371.0  # Earth's radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class AnalyticsService:
    def __init__(self):
        self._ncrb_data = None
        self._weather_data = None
        self._road_data = None
        self._trauma_centers = None

    def _load_ncrb_data(self) -> Dict[str, Any]:
        if not self._ncrb_data:
            if os.path.exists(NCRB_PATH):
                with open(NCRB_PATH, "r", encoding="utf-8") as f:
                    self._ncrb_data = json.load(f)
            else:
                logger.error(f"NCRB file not found at {NCRB_PATH}")
                self._ncrb_data = {}
        return self._ncrb_data

    def _load_weather_data(self) -> Dict[str, Any]:
        if not self._weather_data:
            if os.path.exists(WEATHER_PATH):
                with open(WEATHER_PATH, "r", encoding="utf-8") as f:
                    self._weather_data = json.load(f)
            else:
                logger.error(f"Weather file not found at {WEATHER_PATH}")
                self._weather_data = {}
        return self._weather_data

    def _load_road_data(self) -> Dict[str, Any]:
        if not self._road_data:
            if os.path.exists(ROAD_PATH):
                with open(ROAD_PATH, "r", encoding="utf-8") as f:
                    self._road_data = json.load(f)
            else:
                logger.error(f"Road mapping file not found at {ROAD_PATH}")
                self._road_data = {}
        return self._road_data

    def _resolve_state_from_coords(self, lat: float, lng: float) -> str:
        """
        Resolves the closest Indian state code based on trauma center locations,
        falling back to DL (Delhi) if no closer centers exist or file is missing.
        """
        if not self._trauma_centers:
            if os.path.exists(TRAUMA_CENTERS_PATH):
                try:
                    with open(TRAUMA_CENTERS_PATH, "r", encoding="utf-8") as f:
                        self._trauma_centers = json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to load trauma centers: {e}")
                    self._trauma_centers = {}
            else:
                self._trauma_centers = {}

        state_code = "DL"
        min_dist = float("inf")
        
        features = self._trauma_centers.get("features", [])
        for feature in features:
            coords = feature.get("geometry", {}).get("coordinates", [])
            if len(coords) >= 2:
                # GeoJSON coordinates order: [longitude, latitude]
                h_lng, h_lat = coords[0], coords[1]
                dist = haversine_distance(lat, lng, h_lat, h_lng)
                if dist < min_dist:
                    min_dist = dist
                    state_code = feature.get("properties", {}).get("state", "DL")
        
        return state_code.upper().strip()

    def get_state_risk_score(self, state_code: str) -> dict:
        """
        Computes composite risk score (0-100) from: accident_rate, death_rate,
        violation_density. Returns score + breakdown.
        """
        state_code = state_code.upper().strip()
        data = self._load_ncrb_data()
        
        state_info = data.get("statewise", {}).get(state_code)
        if not state_info:
            return {
                "status": "error",
                "message": f"State code '{state_code}' not found in safety statistics. Supported states: {list(STATE_NAMES.keys())}"
            }

        # Use 2023 statistics as standard for current state risk score
        stats_2023 = state_info.get("2023", {})
        accidents = stats_2023.get("accidents", 0)
        deaths = stats_2023.get("deaths", 0)
        injuries = stats_2023.get("injuries", 0)
        rank_accidents = stats_2023.get("rank_accidents", 12)
        rank_deaths = stats_2023.get("rank_deaths", 12)

        # 1. Accident Rate Score (0 - 100): Normalized by a standard high accident rate (e.g. 60,000)
        accident_score = round(min(100.0, (accidents / 60000.0) * 100.0), 1)

        # 2. Death Rate (Fatality Severity) Score (0 - 100): Calculated as deaths per accident scaled
        fatality_rate = (deaths / accidents * 100.0) if accidents > 0 else 0.0
        # Scaled so that a 50% fatality rate (extremely dangerous) is 100.0
        death_severity_score = round(min(100.0, fatality_rate * 2.0), 1)

        # 3. Violation Density Score (0 - 100): Based on rankings (lower rank numbers mean higher volume/risk)
        # Formula uses rank positions out of 12 states
        violation_density = round(max(10.0, 100.0 - ((rank_accidents * 4) + (rank_deaths * 3))), 1)

        # Composite Risk Score calculation (weighted average)
        # Accidents: 40%, Fatalities: 40%, Violation Density: 20%
        composite_score = round((0.4 * accident_score) + (0.4 * death_severity_score) + (0.2 * violation_density), 1)

        # Classify risk level
        if composite_score >= 70:
            risk_level = "Critical High"
        elif composite_score >= 50:
            risk_level = "High"
        elif composite_score >= 30:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        return {
            "state_code": state_code,
            "state_name": STATE_NAMES.get(state_code, state_code),
            "year": 2023,
            "risk_score": composite_score,
            "risk_level": risk_level,
            "breakdown": {
                "accident_severity_score": accident_score,
                "fatality_severity_score": death_severity_score,
                "violation_density_score": violation_density
            },
            "raw_data": {
                "accidents": accidents,
                "deaths": deaths,
                "injuries": injuries,
                "rank_accidents": rank_accidents,
                "rank_deaths": rank_deaths,
                "fatality_rate_pct": round(fatality_rate, 2)
            }
        }

    def get_violation_heatmap_data(self, state_code: str = None, year: str = "2023") -> list:
        """
        Returns violation type + count + section + avg_fine for dashboard bar chart.
        If state_code is provided, counts are adjusted to mimic state-specific profiles.
        """
        data = self._load_ncrb_data()
        violations = data.get("top_violations_nationally", [])
        
        if not violations:
            return []

        # Find total base accidents count
        total_accidents = 485447  # national 2023 default
        
        state_adjusted = False
        if state_code:
            state_code = state_code.upper().strip()
            state_info = data.get("statewise", {}).get(state_code, {})
            if state_info:
                # Use specified year, fall back to 2023 if missing
                year_data = state_info.get(year, state_info.get("2023", {}))
                total_accidents = year_data.get("accidents", 10000)
                state_adjusted = True

        heatmap_data = []
        for v in violations:
            pct = v["pct_of_accidents"]
            avg_fine = v["avg_fine_inr"]
            violation_name = v["violation"]
            
            # Apply simulated overrides to match local enforcement priorities
            multiplier = 1.0
            if state_adjusted:
                if state_code == "DL":  # Delhi has high camera monitoring and strict enforcement for signals/phones
                    if violation_name == "Use of Mobile Phones":
                        multiplier = 1.6
                    elif violation_name == "Red Light Jumping":
                        multiplier = 1.5
                elif state_code == "TN":  # Tamil Nadu has high speeding figures
                    if violation_name == "Over Speeding":
                        multiplier = 1.15
                elif state_code == "KL":  # Kerala has dense, high-speed regional roads
                    if violation_name == "Over Speeding":
                        multiplier = 1.2
                elif state_code == "UP":  # Uttar Pradesh has high helmet and seatbelt compliance challenges
                    if violation_name == "Non-wearing of Helmet":
                        multiplier = 1.45
                    elif violation_name == "Non-wearing of Seatbelt":
                        multiplier = 1.4
                elif state_code == "MH":  # Maharashtra urban centers have major drunk driving checks
                    if violation_name == "Drunk Driving":
                        multiplier = 1.35
            
            adjusted_pct = round(pct * multiplier, 2)
            simulated_count = int((adjusted_pct / 100.0) * total_accidents)
            
            heatmap_data.append({
                "violation": violation_name,
                "count": simulated_count,
                "percentage": adjusted_pct,
                "section": v["section"],
                "avg_fine_inr": avg_fine
            })
            
        # Re-sort list by count descending
        heatmap_data.sort(key=lambda x: x["count"], reverse=True)
        return heatmap_data

    def get_weather_risk_for_route(self, lat: float, lng: float, weather_condition: str) -> dict:
        """
        Returns: risk_multiplier, alerts, recommended_actions, relevant_sections.
        Dynamically adjusts risk factor if coordinates fall within a documented high-risk state.
        """
        weather_condition = weather_condition.strip()
        data = self._load_weather_data()
        
        matched_cond = None
        for c in data.get("conditions", []):
            if c["condition"].lower() == weather_condition.lower():
                matched_cond = c
                break
        
        if not matched_cond:
            # Fallback to Clear condition if not matched
            for c in data.get("conditions", []):
                if c["condition"] == "Clear":
                    matched_cond = c
                    break
            
            if not matched_cond:
                return {"status": "error", "message": f"Weather condition '{weather_condition}' not found and fallback unavailable."}

        # Resolve state from location coordinates
        state_code = self._resolve_state_from_coords(lat, lng)
        state_name = STATE_NAMES.get(state_code, "")
        
        risk_multiplier = matched_cond["risk_multiplier"]
        recommended_reduction = matched_cond["recommended_speed_reduction_pct"]
        alerts = [matched_cond["additional_alert"]]
        
        # Check if coordinates lie in a high risk state for this specific condition
        is_high_risk_zone = False
        high_risk_states = matched_cond.get("high_risk_states", [])
        if state_name and any(state.lower() == state_name.lower() for state in high_risk_states):
            is_high_risk_zone = True
            # Elevate risk multiplier by 20% due to local topography/history
            risk_multiplier = round(risk_multiplier * 1.2, 2)
            recommended_reduction = min(80, recommended_reduction + 10)
            alerts.append(f"⚠️ Extreme Regional Risk: {state_name} roads are highly prone to accidents under {matched_cond['condition']}.")

        actions = [
            f"Reduce speed by at least {recommended_reduction}% under speed limits.",
            "Double your standard following distance to vehicles ahead.",
            "Turn on low-beam headlights or fog lights to improve vehicle visibility."
        ]

        return {
            "condition": matched_cond["condition"],
            "resolved_state_code": state_code,
            "resolved_state_name": state_name if state_name else "Unknown State",
            "is_high_risk_zone": is_high_risk_zone,
            "risk_multiplier": risk_multiplier,
            "recommended_speed_reduction_pct": recommended_reduction,
            "alerts": alerts,
            "recommended_actions": actions,
            "relevant_sections": matched_cond["sections_triggered"]
        }

    def get_safety_trend(self, state_code: str, years: List[int] = [2019, 2020, 2021, 2022, 2023]) -> dict:
        """
        Returns year-wise accidents/deaths/injuries for trend line chart.
        If state_code is 'ALL' or not specified, returns the national trends.
        """
        data = self._load_ncrb_data()
        state_code = state_code.upper().strip() if state_code else "ALL"
        
        trends = []
        
        if state_code == "ALL":
            national = data.get("national_summary", {})
            for year in years:
                y_str = str(year)
                if y_str in national:
                    trends.append({
                        "year": year,
                        "accidents": national[y_str]["total_accidents"],
                        "deaths": national[y_str]["total_deaths"],
                        "injuries": national[y_str]["total_injuries"]
                    })
        else:
            state_data = data.get("statewise", {}).get(state_code)
            if not state_data:
                return {
                    "status": "error",
                    "message": f"State code '{state_code}' not found in safety statistics. Supported states: {list(STATE_NAMES.keys())}"
                }
                
            for year in years:
                y_str = str(year)
                if y_str in state_data:
                    trends.append({
                        "year": year,
                        "accidents": state_data[y_str]["accidents"],
                        "deaths": state_data[y_str]["deaths"],
                        "injuries": state_data[y_str]["injuries"]
                    })
                    
        return {
            "state_code": state_code,
            "state_name": STATE_NAMES.get(state_code, "India National"),
            "trends": trends
        }

    def get_national_comparison(self, state_code: str) -> dict:
        """
        Compares state metrics vs average metrics across all tracked states in 2023
        for the 'Your state vs India' comparison widget.
        """
        state_code = state_code.upper().strip()
        data = self._load_ncrb_data()
        
        statewise = data.get("statewise", {})
        if state_code not in statewise:
            return {
                "status": "error",
                "message": f"State code '{state_code}' not found in safety statistics. Supported states: {list(STATE_NAMES.keys())}"
            }
            
        # Get specified state metrics for 2023
        state_2023 = statewise[state_code].get("2023", {})
        state_accidents = state_2023.get("accidents", 0)
        state_deaths = state_2023.get("deaths", 0)
        state_injuries = state_2023.get("injuries", 0)
        
        # Calculate averages for all tracked states (12 key states)
        all_accidents = []
        all_deaths = []
        all_injuries = []
        
        for code, years_data in statewise.items():
            stats_2023 = years_data.get("2023", {})
            all_accidents.append(stats_2023.get("accidents", 0))
            all_deaths.append(stats_2023.get("deaths", 0))
            all_injuries.append(stats_2023.get("injuries", 0))
            
        avg_accidents = sum(all_accidents) / len(all_accidents) if all_accidents else 0.0
        avg_deaths = sum(all_deaths) / len(all_deaths) if all_deaths else 0.0
        avg_injuries = sum(all_injuries) / len(all_injuries) if all_injuries else 0.0
        
        # Calculate percentage differences
        pct_diff_accidents = round(((state_accidents - avg_accidents) / avg_accidents) * 100.0, 1) if avg_accidents > 0 else 0.0
        pct_diff_deaths = round(((state_deaths - avg_deaths) / avg_deaths) * 100.0, 1) if avg_deaths > 0 else 0.0
        pct_diff_injuries = round(((state_injuries - avg_injuries) / avg_injuries) * 100.0, 1) if avg_injuries > 0 else 0.0
        
        # Formulate a narrative insight
        diff_str = "higher" if pct_diff_accidents > 0 else "lower"
        abs_diff = abs(pct_diff_accidents)
        insight = (
            f"{STATE_NAMES.get(state_code, state_code)} has an accident rate that is {abs_diff}% {diff_str} "
            f"than the average of key Indian states. "
        )
        if pct_diff_deaths > 0:
            insight += "⚠️ Caution: Fatalities are also above average. Drive extra carefully."
        else:
            insight += "Fatalities remain lower than the major state average."

        return {
            "state_code": state_code,
            "state_name": STATE_NAMES.get(state_code, state_code),
            "year": 2023,
            "state_metrics": {
                "accidents": state_accidents,
                "deaths": state_deaths,
                "injuries": state_injuries
            },
            "national_averages": {
                "accidents": round(avg_accidents, 1),
                "deaths": round(avg_deaths, 1),
                "injuries": round(avg_injuries, 1)
            },
            "comparison": {
                "accidents_pct_diff": pct_diff_accidents,
                "deaths_pct_diff": pct_diff_deaths,
                "injuries_pct_diff": pct_diff_injuries
            },
            "insight": insight
        }
