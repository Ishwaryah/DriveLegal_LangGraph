from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional, Dict
from datetime import datetime
import os
import json

from backend.modules.fines.lookup import FineLookup
from backend.modules.rules.loader import RulesLoader
from backend.modules.geofencing.engine import GeofencingEngine

router = APIRouter(prefix="/sync", tags=["Sync"])

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

FINES_DB_PATH = os.path.join(DATA_DIR, "fines.db")
RULES_JSON_PATH = os.path.join(DATA_DIR, "rules.json")
ZONES_DIR = os.path.join(DATA_DIR, "zones")

@router.get("/fines")
async def get_sync_fines(since: Optional[str] = Query(None)):
    """Returns changed fines rows as JSON array"""
    try:
        lookup = FineLookup(FINES_DB_PATH)
        if since:
            return lookup.get_changes(since)
        return lookup.get_all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rules")
async def get_sync_rules(since: Optional[str] = Query(None)):
    """
    Returns rules. 
    Since our rules are in a single JSON, we return all rules if mod time > since
    or if since is missing.
    """
    try:
        if since:
            try:
                since_dt = datetime.fromisoformat(since)
                file_mod_time = datetime.fromtimestamp(os.path.getmtime(RULES_JSON_PATH))
                if file_mod_time <= since_dt:
                    return [] # No changes
            except (ValueError, OSError):
                pass

        loader = RulesLoader(RULES_JSON_PATH)
        return loader.rules
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/zones")
async def get_sync_zones(states: str = Query(...)):
    """Returns zone GeoJSON for requested states"""
    try:
        state_list = [s.strip().upper() for s in states.split(",")]
        result = {"type": "FeatureCollection", "features": []}
        
        # We look for {state}.geojson in ZONES_DIR
        for state in state_list:
            state_file = os.path.join(ZONES_DIR, f"{state.lower()}.geojson")
            if os.path.exists(state_file):
                with open(state_file, "r") as f:
                    data = json.load(f)
                    if "features" in data:
                        result["features"].extend(data["features"])
            else:
                # If individual file doesn't exist, check index or fallback
                pass
                
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_sync_status():
    """Returns {fines_count, rules_count, zones_count, last_scraped_at}"""
    try:
        lookup = FineLookup(FINES_DB_PATH)
        loader = RulesLoader(RULES_JSON_PATH)
        # For zones, we just count features across all files
        engine = GeofencingEngine(ZONES_DIR)
        
        # Get last_scraped_at from fines DB age
        last_updated = "never"
        try:
            import sqlite3
            conn = sqlite3.connect(FINES_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(fetched_at) FROM fines")
            row = cursor.fetchone()
            if row and row[0]:
                last_updated = row[0]
            conn.close()
        except:
            pass

        return {
            "fines_count": lookup.get_count(),
            "rules_count": len(loader.rules),
            "zones_count": len(engine.zones),
            "last_scraped_at": last_updated
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
