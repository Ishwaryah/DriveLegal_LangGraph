import sqlite3
from datetime import datetime
import os
from typing import Optional, List, Dict

# Maps NLP offence codes (from metadata.json offence_map / rules.json) → DB violation_code.
# Needed because rules.json uses uppercase codes while fines.db uses lowercase snake_case.
_NLP_TO_DB: dict = {
    "DRUNK_DRIVING":           "drunk_driving",
    "SPEED_EXCESS":            "overspeeding",
    "RED_LIGHT_JUMPING":       "signal_jumping",
    "NO_HELMET":               "no_helmet",
    "NO_SEATBELT":             "no_seatbelt",
    "NO_INSURANCE":            "no_insurance",
    "NO_LICENSE":              "no_license",
    "NO_RC":                   "no_rc",
    "MOBILE_PHONE":            "using_phone",
    "DANGEROUS_DRIVING":       "dangerous_driving",
    "WRONG_SIDE":              "wrong_side",
    "OVERLOADING":             "overloading",
    "JUVENILE_DRIVING":        "juvenile_driving",
    "PUC_VIOLATION":           "puc_violation",
    "STUNT_DRIVING":           "stunt_driving",
    "EMERGENCY_OBSTRUCTION":   "not_giving_way_to_emergency",
    "DISOBEY_POLICE":          "disobeying_police",
    "TINTED_GLASS":            "tinted_glass",
    "TRIPLE_RIDING":           "triple_riding",
    "VEHICLE_MODIFICATION":    "vehicle_modification",
    "PARKING_VIOLATION":       "parking_violation",
    "WRONG_OVERTAKING":        "wrong_overtaking",
    "ROAD_RAGE":               "road_rage",
    "SUSPENDED_LICENCE":       "suspended_licence",
}

# Maps NLP vehicle class codes → DB vehicle_type values.
# NLP produces 'LMV'/'2W'/'HGV'; DB stores 'lmv'/'two_wheeler'/'hmv'.
_VEHICLE_CLASS_TO_DB: dict = {
    "LMV":  "lmv",
    "2W":   "two_wheeler",
    "3W":   "three_wheeler",
    "HGV":  "hmv",
    "HMV":  "hmv",
}

class FineLookup:
    def __init__(self, db_path: str):
        self.db_path = db_path
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at {self.db_path}")

    def query(self, offence_code: str, vehicle_class: str, state: str, country: str = "IN", repeat: bool = False) -> Optional[dict]:
        """
        Query the fine database for a specific offence and vehicle class in a state.
        Returns: {amount_inr, section_ref} or None
        """
        # Translate NLP codes → DB codes
        db_code    = _NLP_TO_DB.get(offence_code, offence_code.lower())
        db_vehicle = _VEHICLE_CLASS_TO_DB.get(vehicle_class, vehicle_class.lower() if vehicle_class else "all")

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Try state-specific first, then national (NULL state)
        query = """
            SELECT min_fine_local, max_fine_local, mv_act_section, currency, notes
            FROM fines
            WHERE violation_code = ?
              AND vehicle_type IN (?, 'all')
              AND country = ?
              AND (state_province = ? OR state_province IS NULL)
            ORDER BY CASE WHEN state_province = ? THEN 0 ELSE 1 END
            LIMIT 1
        """
        cursor.execute(query, (db_code, db_vehicle, country, state, state))
        row = cursor.fetchone()
        conn.close()

        if row:
            data = dict(row)
            amount = data['max_fine_local'] if repeat else data['min_fine_local']
            return {
                "amount_inr":        amount,
                "repeat_amount_inr": data['max_fine_local'],
                "section_ref":       data['mv_act_section'] or "",
                "source_url":        "",
                "fetched_at":        datetime.now().isoformat(),
                "currency":          data['currency'],
                "notes":             data['notes'],
            }
        return None

    def query_by_section(self, section_ref: str, country: str = "IN") -> List[Dict]:
        """Query fines by MV Act section reference."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM fines WHERE mv_act_section LIKE ? AND country = ?",
            (f"%{section_ref}%", country)
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def get_db_age(self) -> str:
        """Returns a human-readable string describing the database's last-known update."""
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
        """Returns all fines (new schema has no timestamp; returns empty for compatibility)."""
        return []

    def get_all(self) -> List[Dict]:
        """Returns all fines in the database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM fines")
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def get_count(self) -> int:
        """Returns total number of fines."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM fines")
        count = cursor.fetchone()[0]
        conn.close()
        return count
