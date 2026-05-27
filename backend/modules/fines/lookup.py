import sqlite3
from datetime import datetime
import os
from typing import Optional, List, Dict

# Maps Indian state full names → DB state codes stored in fines.db
# The DB uses 2-letter codes; the NLP pipeline / agent sends full names.
_FULL_NAME_TO_CODE: dict = {
    "Tamil Nadu":        "TN",
    "Maharashtra":       "MH",
    "Delhi":             "DL",
    "Karnataka":         "KA",
    "Kerala":            "KL",
    "Gujarat":           "GJ",
    "Andhra Pradesh":    "AP",
    "Bihar":             "BR",
    "Haryana":           "HR",
    "Rajasthan":         "RJ",
    "Uttar Pradesh":     "UP",
    "West Bengal":       "WB",
    "Madhya Pradesh":    "MP",
    "Telangana":         "TS",
    "Odisha":            "OR",
    "Punjab":            "PB",
    "Assam":             "AS",
    "Chhattisgarh":      "CG",
    "Jharkhand":         "JH",
    "Uttarakhand":       "UK",
    "Himachal Pradesh":  "HP",
    "Goa":               "GA",
    "Tripura":           "TR",
    "Meghalaya":         "ML",
    "Manipur":           "MN",
    "Nagaland":          "NL",
    "Arunachal Pradesh": "AR",
    "Mizoram":           "MZ",
    "Sikkim":            "SK",
    # AE regions (stored as codes in DB)
    "Abu Dhabi":         "ABU_DHABI",
    "Dubai":             "DUBAI",
    # US states
    "California":        "CALIFORNIA",
    "New York":          "NEW_YORK",
    "Texas":             "TEXAS",
}

# Reverse map: DB state codes → canonical full names (used for display)
_CODE_TO_FULL_NAME: dict = {v: k for k, v in _FULL_NAME_TO_CODE.items()}

# Vehicle class aliases: any variant the agent/NLP might send → list of DB values to try.
# The DB stores: 'ALL', 'LMV', '2W', 'TWO_WHEELER', 'HGV', 'HGV/MGV', '3W', 'COMMERCIAL', 'LMV/CAR', 'TWO-WHEELER'
_VEHICLE_ALIASES: dict = {
    "LMV":         ["LMV", "LMV/CAR"],
    "2W":          ["2W", "TWO_WHEELER", "TWO-WHEELER"],
    "TWO_WHEELER": ["2W", "TWO_WHEELER", "TWO-WHEELER"],
    "HGV":         ["HGV", "HGV/MGV", "COMMERCIAL"],
    "HMV":         ["HGV", "HGV/MGV", "COMMERCIAL"],
    "3W":          ["3W"],
    "COMMERCIAL":  ["COMMERCIAL", "HGV", "HGV/MGV"],
}

# All known vehicle class values in the DB (used when vehicle is "GENERAL"/"ALL")
_ALL_VEHICLE_CLASSES = [
    "ALL", "LMV", "LMV/CAR", "TWO_WHEELER", "2W", "TWO-WHEELER",
    "HGV", "HGV/MGV", "COMMERCIAL", "3W",
]

# Preferred vehicle class order when caller says "GENERAL"/"ALL" (LMV = most common default)
_VEHICLE_PREFERENCE_ORDER = {
    "ALL":         0,   # 'ALL' rows match any vehicle
    "LMV":         1,
    "LMV/CAR":     1,
    "TWO_WHEELER": 2,
    "2W":          2,
    "TWO-WHEELER": 2,
    "3W":          3,
    "HGV":         4,
    "HGV/MGV":     4,
    "COMMERCIAL":  4,
}


def _resolve_state_candidates(state: str) -> List[str]:
    """Return a list of DB `state` column values to try for the given input."""
    if not state or state.upper() in ("ALL", "ANY", "NATIONAL", ""):
        return []

    candidates: List[str] = []

    # 1. Try exact input first
    candidates.append(state)

    # 2. Try full-name → code lookup (e.g. "Tamil Nadu" → "TN")
    code = _FULL_NAME_TO_CODE.get(state)
    if code and code not in candidates:
        candidates.append(code)

    # 3. Try title-cased variant (handles "tamil nadu" input)
    titled = state.strip().title()
    if titled not in candidates:
        candidates.append(titled)
    code2 = _FULL_NAME_TO_CODE.get(titled)
    if code2 and code2 not in candidates:
        candidates.append(code2)

    # 4. Try upper-case (handles "TAMIL NADU" or "TN")
    upper = state.strip().upper()
    if upper not in candidates:
        candidates.append(upper)

    return candidates


class FineLookup:
    def __init__(self, db_path: str):
        self.db_path = db_path
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at {self.db_path}")

    def query(
        self,
        offence_code: str,
        vehicle_class: str,
        state: str,
        country: str = "IN",
        repeat: bool = False,
    ) -> Optional[dict]:
        """
        Query the fine database for a specific offence and vehicle class in a state.

        DB schema columns used:
          offence_code  — UPPER_SNAKE_CASE (e.g. "NO_HELMET", "DRUNK_DRIVING")
          vehicle_class — e.g. "ALL", "LMV", "TWO_WHEELER", "HGV"
          state         — 2-letter code (e.g. "TN") or "ALL" for national
          amount_inr    — first-offence fine in local currency
          repeat_amount_inr — repeat-offence fine
          section_ref   — MV Act section (e.g. "Section 194D")
          currency      — "INR", "AED", "GBP", etc.
          country       — "IN", "AE", "GB", "SG", "SA", "US"

        Priority order when multiple rows match:
          1. State-specific row before national ('ALL') row.
          2. Specific vehicle type before 'ALL' vehicle row.
          3. If vehicle_class is "GENERAL"/"ALL"/unset, accept any vehicle
             type and prefer LMV → TWO_WHEELER → HGV → ALL.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            row = self._query_row(cursor, offence_code, vehicle_class, state, country)
        finally:
            conn.close()

        if not row:
            return None

        data = dict(row)
        amount = data["repeat_amount_inr"] if repeat and data.get("repeat_amount_inr") else data["amount_inr"]
        return {
            "amount_inr":        amount,
            "repeat_amount_inr": data.get("repeat_amount_inr") or data["amount_inr"],
            "section_ref":       data.get("section_ref") or "",
            "source_url":        "",
            "fetched_at":        datetime.now().isoformat(),
            "currency":          data.get("currency", "INR"),
            "notes":             None,
        }

    def _query_row(self, cursor, offence_code: str, vehicle_class: str, state: str, country: str):
        """Internal: executes the tiered SQL lookup and returns the first sqlite3.Row or None."""
        vc_upper = (vehicle_class or "GENERAL").upper()
        is_generic = vc_upper in ("ALL", "GENERAL", "ANY", "")

        if is_generic:
            # No specific vehicle type — search all and rank by preference
            vc_candidates = _ALL_VEHICLE_CLASSES
        else:
            vc_candidates = _VEHICLE_ALIASES.get(vc_upper, [vc_upper])
            # Always include 'ALL' so rows that apply to every vehicle type are matched
            if "ALL" not in vc_candidates:
                vc_candidates = list(vc_candidates) + ["ALL"]

        vc_ph = ",".join("?" * len(vc_candidates))

        state_candidates = _resolve_state_candidates(state)

        # Build the CASE expression for vehicle preference ordering (lower = higher priority)
        vc_case_parts = []
        for vc, pref in _VEHICLE_PREFERENCE_ORDER.items():
            vc_case_parts.append(f"WHEN UPPER(vehicle_class) = '{vc}' THEN {pref}")
        vc_case_expr = "CASE " + " ".join(vc_case_parts) + " ELSE 5 END"

        if state_candidates:
            sc_ph = ",".join("?" * len(state_candidates))
            sql = f"""
                SELECT amount_inr, repeat_amount_inr, section_ref, currency
                FROM fines
                WHERE UPPER(offence_code) = UPPER(?)
                  AND UPPER(vehicle_class) IN ({vc_ph})
                  AND country = ?
                  AND (state IN ({sc_ph}) OR state = 'ALL')
                ORDER BY
                  CASE WHEN state = 'ALL' THEN 1 ELSE 0 END,
                  {vc_case_expr}
                LIMIT 1
            """
            params = [offence_code] + vc_candidates + [country] + state_candidates
        else:
            # No state provided — national rows only
            sql = f"""
                SELECT amount_inr, repeat_amount_inr, section_ref, currency
                FROM fines
                WHERE UPPER(offence_code) = UPPER(?)
                  AND UPPER(vehicle_class) IN ({vc_ph})
                  AND country = ?
                  AND state = 'ALL'
                ORDER BY {vc_case_expr}
                LIMIT 1
            """
            params = [offence_code] + vc_candidates + [country]

        cursor.execute(sql, params)
        return cursor.fetchone()

    def query_by_section(self, section_ref: str, country: str = "IN") -> List[Dict]:
        """Query fines by MV Act section reference (section_ref column)."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM fines WHERE section_ref LIKE ? AND country = ?",
            (f"%{section_ref}%", country),
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def get_db_age(self) -> str:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM fines")
            count = cursor.fetchone()[0]
            conn.close()
            return f"seeded with {count} rows" if count else "empty"
        except sqlite3.OperationalError:
            conn.close()
            return "recently updated"

    def get_changes(self, _since: str) -> List[Dict]:
        return []

    def get_all(self) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM fines")
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def get_count(self) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM fines")
        count = cursor.fetchone()[0]
        conn.close()
        return count
