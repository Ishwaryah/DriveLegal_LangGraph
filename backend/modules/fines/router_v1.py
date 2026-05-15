from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import os

router = APIRouter(prefix="/api/v1", tags=["v1"])

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/fines.db"))

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

class ChallanCalculationRequest(BaseModel):
    violation_codes: List[str]
    vehicle_type: str
    country: str = "IN"
    state_province: Optional[str] = None
    is_repeat_offense: bool = False
    vehicle_registration: Optional[str] = None

class ViolationResponse(BaseModel):
    violation_code: str
    violation_name: str
    fine_amount: int       # min fine (matches mobile CalculateResponse)
    fine_min: int          # alias kept for reference
    fine_max: int
    mv_act_section: str
    is_compoundable: bool  # matches mobile CalculateResponse
    compounding_eligible: bool
    compounding_fee: Optional[int]
    imprisonment: str
    notes: Optional[str]

class ChallanCalculationResponse(BaseModel):
    total_fine: int        # matches mobile CalculateResponse
    total_min_fine: int    # alias kept for reference
    total_max_fine: int
    currency: str
    violations: List[ViolationResponse]
    compounding_available: bool
    total_compounding_fee: int
    legal_disclaimer: str

@router.post("/challan/calculate", response_model=ChallanCalculationResponse)
def calculate_challan(req: ChallanCalculationRequest = Body(...)):
    if not req.violation_codes:
        raise HTTPException(status_code=400, detail="violation_codes list cannot be empty")
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    violations_resp = []
    total_min = 0
    total_max = 0
    total_comp = 0
    compounding_available = False
    _CURRENCY_DEFAULTS = {"IN": "INR", "AE": "AED", "SG": "SGD", "GB": "GBP"}
    currency = _CURRENCY_DEFAULTS.get(req.country, "USD")
    
    for code in req.violation_codes:
        query = """
            SELECT * FROM fines 
            WHERE country = ? AND violation_code = ? AND vehicle_type IN (?, 'all')
        """
        params = [req.country, code, req.vehicle_type]
        
        if req.state_province:
            query += " AND (state_province = ? OR state_province IS NULL)"
            params.append(req.state_province)
        else:
            query += " AND state_province IS NULL"
            
        # Prioritize exact state match over NULL
        query += " ORDER BY CASE WHEN state_province IS NULL THEN 1 ELSE 0 END LIMIT 1"
        
        cursor.execute(query, params)
        row = cursor.fetchone()
        
        if row:
            data = dict(row)
            currency = data['currency']
            comp_elig = bool(data['compounding_eligible'])
            comp_fee = data['compounding_fee']
            
            if comp_elig and comp_fee is not None:
                compounding_available = True
                total_comp += comp_fee
                
            total_min += data['min_fine_local'] or 0
            total_max += data['max_fine_local'] or 0
            
            imprisonment_str = f"{data['imprisonment_days']} days" if data['imprisonment_days'] else "None"
            
            fine_min_val = data['min_fine_local'] or 0
            fine_max_val = data['max_fine_local'] or 0
            violations_resp.append(ViolationResponse(
                violation_code=data['violation_code'],
                violation_name=data['violation_name'],
                fine_amount=fine_min_val,
                fine_min=fine_min_val,
                fine_max=fine_max_val,
                mv_act_section=data['mv_act_section'] or "",
                is_compoundable=comp_elig,
                compounding_eligible=comp_elig,
                compounding_fee=comp_fee,
                imprisonment=imprisonment_str,
                notes=data['notes']
            ))
        else:
            # Could raise exception but typically best to just ignore unmapped rules or skip
            pass
            
    conn.close()
    
    return ChallanCalculationResponse(
        total_fine=total_min,
        total_min_fine=total_min,
        total_max_fine=total_max,
        currency=currency,
        violations=violations_resp,
        compounding_available=compounding_available,
        total_compounding_fee=total_comp,
        legal_disclaimer="Amounts as per Motor Vehicles (Amendment) Act 2019 base rates." if req.country == "IN" else "Amounts as per local laws."
    )

@router.get("/fines/country/{country_code}")
def get_country_fines(country_code: str, vehicle_type: Optional[str] = None, state_province: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM fines WHERE country = ?"
    params = [country_code.upper()]
    
    if vehicle_type:
        query += " AND vehicle_type IN (?, 'all')"
        params.append(vehicle_type)

    # Return state-specific rows when a named state is given;
    # fall back to national (NULL) rows for 'Other' or no state.
    if state_province and state_province != 'Other':
        query += " AND state_province = ?"
        params.append(state_province)
    else:
        query += " AND state_province IS NULL"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]

@router.get("/fines/search")
def search_fines(q: str, country: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT * FROM fines 
        WHERE country = ? AND (violation_name LIKE ? OR notes LIKE ?)
    """
    params = [country.upper(), f"%{q}%", f"%{q}%"]
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

@router.get("/fines/countries")
def get_supported_countries():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT country, MAX(currency) as currency, COUNT(*) as total_violations FROM fines GROUP BY country")
    rows = cursor.fetchall()
    conn.close()
    
    names = {
        "IN": "India",
        "AE": "UAE",
        "GB": "United Kingdom",
        "SG": "Singapore"
    }
    
    res = []
    for row in rows:
        code = row['country']
        res.append({
            "code": code,
            "name": names.get(code, code),
            "currency": row['currency'],
            "total_violations": row['total_violations']
        })
        
    return res

@router.get("/fines/compounding")
def get_compounding(state: str, violation: str, vehicle_type: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT * FROM fines 
        WHERE country = 'IN' AND state_province = ? AND violation_code = ? AND vehicle_type IN (?, 'all')
        ORDER BY CASE WHEN vehicle_type != 'all' THEN 1 ELSE 0 END DESC
        LIMIT 1
    """
    cursor.execute(query, [state, violation, vehicle_type])
    row = cursor.fetchone()
    conn.close()
    
    if row:
        data = dict(row)
        return {
            "compounding_eligible": bool(data['compounding_eligible']),
            "compounding_fee": data['compounding_fee']
        }
    else:
        raise HTTPException(status_code=404, detail="Compounding fee not found for given parameters")
