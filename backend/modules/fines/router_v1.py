"""
Fines API v1
============
Endpoints for challan calculation, country fine listing, and compoundability lookup.

DB schema (fines.db):
  offence_code, vehicle_class, state, amount_inr, repeat_amount_inr,
  section_ref, source_url, fetched_at, version_hash, country, currency
"""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import os

from backend.modules.agent.normalize import CURRENCY_MAP, COUNTRY_NAMES

router = APIRouter(prefix="/api/v1", tags=["v1"])

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/fines.db"))

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ── Pydantic models ───────────────────────────────────────────────────────────

class ChallanCalculationRequest(BaseModel):
    violation_codes: List[str]
    vehicle_type: str                       # accepts 'two_wheeler', 'LMV', '2W', etc.
    country: str = "IN"
    state_province: Optional[str] = None   # full name or code, e.g. 'Tamil Nadu' / 'TN'
    is_repeat_offense: bool = False
    vehicle_registration: Optional[str] = None

class ViolationResponse(BaseModel):
    violation_code: str
    violation_name: str
    fine_amount: int        # applied fine (min, or max if repeat)
    fine_min: int
    fine_max: int
    mv_act_section: str
    is_compoundable: bool   # matches mobile CalculateResponse
    compounding_eligible: bool
    compounding_fee: Optional[int]
    imprisonment: str
    notes: Optional[str]

class ChallanCalculationResponse(BaseModel):
    total_fine: int         # matches mobile CalculateResponse
    total_min_fine: int
    total_max_fine: int
    currency: str
    violations: List[ViolationResponse]
    compounding_available: bool
    total_compounding_fee: int
    legal_disclaimer: str

# ── Static helpers ────────────────────────────────────────────────────────────

# Violations known to be NON-compoundable under MV Act 2019.
_NON_COMPOUNDABLE = {
    "DRUNK_DRIVING", "DANGEROUS_DRIVING", "RED_LIGHT_JUMPING",
    "SIGNAL_JUMPING", "JUVENILE_DRIVING", "SUSPENDED_LICENCE",
    "STUNT_DRIVING", "ROAD_RAGE",
}

# Rough imprisonment strings per section (for display only).
_IMPRISONMENT_MAP = {
    "Section 185":  "Up to 6 months (first); up to 2 years (repeat)",
    "Section 184":  "Up to 6 months",
    "Section 194E": "Up to 6 months",
    "Section 199A": "Up to 3 years",
    "Section 190":  "Up to 6 months",
    "Section 196":  "Up to 3 months",
    "Section 192":  "Up to 6 months",
    "Section 189":  "Up to 1 year (repeat)",
}

# Compoundable violations and their typical fee (≈ min fine).
_COMPOUNDABLE = {
    "NO_HELMET", "NO_SEATBELT", "SPEED_EXCESS",
    "MOBILE_PHONE", "PARKING_VIOLATION", "TRIPLE_RIDING",
    "TINTED_GLASS", "WRONG_OVERTAKING",
}

# Normalize vehicle_class input to a set of DB values to match.
_VC_NORMALIZE = {
    "two_wheeler":  ["2W", "TWO_WHEELER", "TWO-WHEELER"],
    "lmv":          ["LMV", "LMV/CAR"],
    "hmv":          ["HGV", "HGV/MGV", "COMMERCIAL"],
    "hgv":          ["HGV", "HGV/MGV", "COMMERCIAL"],
    "3w":           ["3W"],
    "commercial":   ["COMMERCIAL", "HGV", "HGV/MGV"],
}

# Map state full names → DB codes (same as lookup.py).
_STATE_TO_CODE = {
    "Tamil Nadu": "TN",  "Maharashtra": "MH",  "Delhi": "DL",
    "Karnataka": "KA",   "Kerala": "KL",        "Gujarat": "GJ",
    "Andhra Pradesh": "AP", "Bihar": "BR",       "Haryana": "HR",
    "Rajasthan": "RJ",   "Uttar Pradesh": "UP",  "West Bengal": "WB",
    "Madhya Pradesh": "MP", "Telangana": "TS",   "Odisha": "OR",
    "Punjab": "PB",
}

def _resolve_vehicle(raw: str) -> List[str]:
    """Return list of DB vehicle_class values to try for a given input."""
    key = raw.strip().lower().replace("-", "_").replace(" ", "_")
    if key in _VC_NORMALIZE:
        return _VC_NORMALIZE[key] + ["ALL"]
    upper = raw.upper()
    return [upper, "ALL"]

def _resolve_state(raw: Optional[str]) -> List[str]:
    """Return list of DB state values to try (full name + code)."""
    if not raw or raw.upper() in ("ALL", "ANY", "NATIONAL", "OTHER", ""):
        return []
    candidates = [raw]
    code = _STATE_TO_CODE.get(raw.strip().title()) or _STATE_TO_CODE.get(raw.strip())
    if code and code not in candidates:
        candidates.append(code)
    return candidates


# ── POST /api/v1/challan/calculate ───────────────────────────────────────────

@router.post("/challan/calculate", response_model=ChallanCalculationResponse)
def calculate_challan(req: ChallanCalculationRequest = Body(...)):
    if not req.violation_codes:
        raise HTTPException(status_code=400, detail="violation_codes list cannot be empty")

    conn = get_db_connection()
    cursor = conn.cursor()

    currency = CURRENCY_MAP.get(req.country, "USD")

    vc_candidates = _resolve_vehicle(req.vehicle_type)
    vc_ph = ",".join("?" * len(vc_candidates))

    state_candidates = _resolve_state(req.state_province)

    violations_resp = []
    total_min = 0
    total_max = 0
    total_comp = 0
    compounding_available = False

    for code in req.violation_codes:
        row = None

        if state_candidates:
            sc_ph = ",".join("?" * len(state_candidates))
            sql = f"""
                SELECT offence_code, amount_inr, repeat_amount_inr, section_ref, currency
                FROM fines
                WHERE country = ?
                  AND UPPER(offence_code) = UPPER(?)
                  AND UPPER(vehicle_class) IN ({vc_ph})
                  AND (state IN ({sc_ph}) OR state = 'ALL')
                ORDER BY CASE WHEN state = 'ALL' THEN 1 ELSE 0 END
                LIMIT 1
            """
            params = [req.country, code] + vc_candidates + state_candidates
        else:
            sql = f"""
                SELECT offence_code, amount_inr, repeat_amount_inr, section_ref, currency
                FROM fines
                WHERE country = ?
                  AND UPPER(offence_code) = UPPER(?)
                  AND UPPER(vehicle_class) IN ({vc_ph})
                  AND state = 'ALL'
                LIMIT 1
            """
            params = [req.country, code] + vc_candidates

        cursor.execute(sql, params)
        row = cursor.fetchone()

        if row:
            data = dict(row)
            currency = data.get("currency", currency)
            offence_upper = (data["offence_code"] or code).upper()

            fine_min_val = data["amount_inr"] or 0
            fine_max_val = data["repeat_amount_inr"] or fine_min_val
            applied_fine = fine_max_val if req.is_repeat_offense and fine_max_val else fine_min_val

            total_min += applied_fine
            total_max += fine_max_val

            is_comp = offence_upper in _COMPOUNDABLE
            comp_fee = fine_min_val if is_comp else None
            if is_comp and comp_fee:
                compounding_available = True
                total_comp += comp_fee

            section = data.get("section_ref") or ""
            imprisonment_str = _IMPRISONMENT_MAP.get(section.split()[0:2][0] if section else "", "None")

            violations_resp.append(ViolationResponse(
                violation_code=offence_upper,
                violation_name=offence_upper.replace("_", " ").title(),
                fine_amount=applied_fine,
                fine_min=fine_min_val,
                fine_max=fine_max_val,
                mv_act_section=section,
                is_compoundable=is_comp,
                compounding_eligible=is_comp,
                compounding_fee=comp_fee,
                imprisonment=imprisonment_str,
                notes=None,
            ))

    conn.close()

    return ChallanCalculationResponse(
        total_fine=total_min,
        total_min_fine=total_min,
        total_max_fine=total_max,
        currency=currency,
        violations=violations_resp,
        compounding_available=compounding_available,
        total_compounding_fee=total_comp,
        legal_disclaimer=(
            "Amounts as per Motor Vehicles (Amendment) Act 2019 base rates. "
            "Verify at echallan.parivahan.gov.in."
            if req.country == "IN" else "Amounts as per local laws."
        ),
    )


# ── GET /api/v1/fines/country/{country_code} ──────────────────────────────────

@router.get("/fines/country/{country_code}")
def get_country_fines(
    country_code: str,
    vehicle_type: Optional[str] = None,
    state_province: Optional[str] = None,
):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM fines WHERE country = ?"
    params: List = [country_code.upper()]

    if vehicle_type:
        vc_candidates = _resolve_vehicle(vehicle_type)
        vc_ph = ",".join("?" * len(vc_candidates))
        query += f" AND UPPER(vehicle_class) IN ({vc_ph})"
        params.extend(vc_candidates)

    # Return state-specific rows when a named state is given;
    # fall back to national ('ALL') rows for 'Other' or no state.
    if state_province and state_province != "Other":
        sc = _resolve_state(state_province)
        if sc:
            sc_ph = ",".join("?" * len(sc))
            query += f" AND state IN ({sc_ph})"
            params.extend(sc)
        else:
            query += " AND state = 'ALL'"
    else:
        query += " AND state = 'ALL'"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


# ── GET /api/v1/fines/search ──────────────────────────────────────────────────

@router.get("/fines/search")
def search_fines(q: str, country: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT * FROM fines
        WHERE country = ? AND offence_code LIKE ?
    """
    params = [country.upper(), f"%{q}%"]

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


# ── GET /api/v1/fines/countries ───────────────────────────────────────────────

@router.get("/fines/countries")
def get_supported_countries():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT country, MAX(currency) as currency, COUNT(*) as total_violations FROM fines GROUP BY country"
    )
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "code": row["country"],
            "name": COUNTRY_NAMES.get(row["country"], row["country"]),
            "currency": row["currency"],
            "total_violations": row["total_violations"],
        }
        for row in rows
    ]


# ── GET /api/v1/fines/compounding ─────────────────────────────────────────────

@router.get("/fines/compounding")
def get_compounding(state: str, violation: str, vehicle_type: str):
    """
    Check if a violation is compoundable (can be paid without a court appearance).
    Since the current DB doesn't store compounding_eligible per row, we use a
    static rule map based on MV Act 2019 provisions.
    """
    is_comp = violation.upper() in _COMPOUNDABLE

    if not is_comp:
        raise HTTPException(status_code=404, detail="Compounding not available for this violation")

    # Look up the base fine to set as compounding fee
    conn = get_db_connection()
    cursor = conn.cursor()
    vc_candidates = _resolve_vehicle(vehicle_type)
    vc_ph = ",".join("?" * len(vc_candidates))
    sc = _resolve_state(state)

    if sc:
        sc_ph = ",".join("?" * len(sc))
        sql = f"""
            SELECT amount_inr FROM fines
            WHERE country = 'IN'
              AND UPPER(offence_code) = UPPER(?)
              AND UPPER(vehicle_class) IN ({vc_ph})
              AND (state IN ({sc_ph}) OR state = 'ALL')
            ORDER BY CASE WHEN state = 'ALL' THEN 1 ELSE 0 END
            LIMIT 1
        """
        params = [violation] + vc_candidates + sc
    else:
        sql = f"""
            SELECT amount_inr FROM fines
            WHERE country = 'IN'
              AND UPPER(offence_code) = UPPER(?)
              AND UPPER(vehicle_class) IN ({vc_ph})
              AND state = 'ALL'
            LIMIT 1
        """
        params = [violation] + vc_candidates

    cursor.execute(sql, params)
    row = cursor.fetchone()
    conn.close()

    comp_fee = row["amount_inr"] if row else None
    return {
        "compounding_eligible": True,
        "compounding_fee": comp_fee,
    }
