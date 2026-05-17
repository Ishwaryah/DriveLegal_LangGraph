import os
import sqlite3
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException
from backend.services.parivahan_service import ParivahanService

router = APIRouter(prefix="/api/v1", tags=["Vehicle Lookup"])

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/fines.db"))

def get_db_connection():
    if not os.path.exists(DB_PATH):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@router.get("/vehicle/rc/{reg_no}", summary="Get vehicle Registration Certificate (RC) details")
def get_rc(reg_no: str):
    """
    Fetch Registration Certificate (RC) details for a given vehicle registration number.
    
    This endpoint:
    1. Checks the SQLite `vehicle_cache` table to see if matching details are already stored.
    2. If found in cache, returns the cached JSON data.
    3. If cache miss, requests the RC details using the `ParivahanService` (which uses
       either offline snapshot fuzzy matching or a live government RTO lookup, depending on configuration).
    4. Caches the successful RC details in `vehicle_cache` for subsequent lookups.
    """
    reg_no_clean = reg_no.replace(" ", "").replace("-", "").upper()
    
    # 1. Try to fetch from cache first
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vehicle_cache WHERE reg_no = ?", (reg_no_clean,))
        row = cursor.fetchone()
        if row:
            rc_data = json.loads(row["rc_data"])
            return {
                "success": True,
                "data": rc_data,
                "source": row["source"],
                "cached": True,
                "last_fetched": row["last_fetched"]
            }
    except sqlite3.OperationalError:
        # Cache table might not exist yet if migration hasn't run; ignore and fall through
        pass
    finally:
        conn.close()

    # 2. Cache miss -> Call ParivahanService
    service = ParivahanService()
    result = service.get_rc_details(reg_no_clean)
    
    if result.get("success") and result.get("data"):
        # Save to cache table
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            # Ensure the table is created
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vehicle_cache (
                    reg_no TEXT PRIMARY KEY,
                    rc_data TEXT,
                    last_fetched TEXT,
                    source TEXT
                )
            """)
            cursor.execute(
                """
                INSERT OR REPLACE INTO vehicle_cache (reg_no, rc_data, last_fetched, source)
                VALUES (?, ?, ?, ?)
                """,
                (
                    reg_no_clean,
                    json.dumps(result["data"]),
                    result["timestamp"],
                    result["source"]
                )
            )
            conn.commit()
        except Exception:
            # Keep execution going if caching write fails
            pass
        finally:
            conn.close()
            
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Vehicle details not found"))
        
    return result

@router.get("/vehicle/dl/{dl_no}", summary="Get driving license (DL) details")
def get_dl(dl_no: str):
    """
    Fetch Driving License (DL) details for a given driving license number.
    
    Returns the driving license validity status, valid classes (e.g. LMV, MCWG),
    holder name, and state code using ParivahanService (offline or live depending on config).
    """
    dl_no_clean = dl_no.replace(" ", "").replace("-", "").upper()
    service = ParivahanService()
    result = service.get_dl_details(dl_no_clean)
    
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Driving license details not found"))
        
    return result

@router.get("/vehicle/challans/{reg_no}", summary="Get pending e-challans for a vehicle")
def get_challans(reg_no: str):
    """
    Fetch pending traffic challans for a given vehicle registration number.
    
    Returns details of active and pending traffic challans, including violation description,
    fine amounts, law section, and a mock/live payment URL.
    """
    reg_no_clean = reg_no.replace(" ", "").replace("-", "").upper()
    service = ParivahanService()
    result = service.get_pending_challans(reg_no_clean)
    
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Failed to retrieve pending challans"))
        
    return result
