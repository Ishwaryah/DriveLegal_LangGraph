"""
scrape_indian_fines.py — Populate fines.db with comprehensive Indian traffic fine data.

Source: Motor Vehicles (Amendment) Act, 2019 — Central fine schedule
+ State-specific variations from transport department publications.

This uses hardcoded, well-researched data from the MV Act 2019 Amendment
(publicly available law), NOT live scraping from websites.
"""

import sqlite3
import hashlib
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "fines.db")

# ─── Schema migration: add country + currency columns if missing ─────────────

def migrate_schema(conn: sqlite3.Connection):
    """Add country and currency columns to fines table if they don't exist."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(fines)")
    columns = {row[1] for row in cursor.fetchall()}

    if "country" not in columns:
        cursor.execute("ALTER TABLE fines ADD COLUMN country TEXT DEFAULT 'IN'")
        print("[MIGRATE] Added 'country' column")
    if "currency" not in columns:
        cursor.execute("ALTER TABLE fines ADD COLUMN currency TEXT DEFAULT 'INR'")
        print("[MIGRATE] Added 'currency' column")

    # Update existing rows
    cursor.execute("UPDATE fines SET country = 'IN' WHERE country IS NULL")
    cursor.execute("UPDATE fines SET currency = 'INR' WHERE currency IS NULL")
    conn.commit()


def make_hash(offence: str, vehicle: str, state: str, country: str = "IN") -> str:
    key = f"{offence}|{vehicle}|{state}|{country}"
    return hashlib.sha256(key.encode()).hexdigest()


def insert_fines(conn: sqlite3.Connection, fines_data: list[dict]):
    cursor = conn.cursor()
    inserted = 0
    skipped = 0
    for f in fines_data:
        vh = make_hash(f["offence_code"], f["vehicle_class"], f["state"], f.get("country", "IN"))
        try:
            cursor.execute("""
                INSERT INTO fines (offence_code, vehicle_class, state, amount_inr, repeat_amount_inr,
                                   section_ref, source_url, fetched_at, version_hash, country, currency)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f["offence_code"], f["vehicle_class"], f["state"],
                f["amount_inr"], f.get("repeat_amount_inr"),
                f.get("section_ref"), f["source_url"],
                datetime.now().isoformat(), vh,
                f.get("country", "IN"), f.get("currency", "INR"),
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1  # Duplicate version_hash — already exists
    conn.commit()
    return inserted, skipped


# ─── MV Act 2019 Amendment — Central (National) Fine Schedule ─────────────────
# These are the MINIMUM fines prescribed by the central government.
# Source: Motor Vehicles (Amendment) Act 2019, Gazette of India

CENTRAL_FINES = [
    # ── Section 177: General offences ──
    {"offence_code": "SECTION_177", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 500, "repeat_amount_inr": 1500, "section_ref": "Section 177", "source_url": "https://parivahan.gov.in"},

    # ── Section 177A: Violation of road regulations ──
    {"offence_code": "SECTION_177A", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 500, "repeat_amount_inr": 1500, "section_ref": "Section 177A", "source_url": "https://parivahan.gov.in"},

    # ── Section 178: Travelling without ticket on stage carriage ──
    {"offence_code": "SECTION_178", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 500, "repeat_amount_inr": None, "section_ref": "Section 178", "source_url": "https://parivahan.gov.in"},

    # ── Section 179: Disobedience of orders of authorities ──
    {"offence_code": "SECTION_179", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 2000, "repeat_amount_inr": 4000, "section_ref": "Section 179", "source_url": "https://parivahan.gov.in"},

    # ── Section 180: Unauthorized persons allowing others to drive ──
    {"offence_code": "SECTION_180", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 180", "source_url": "https://parivahan.gov.in"},

    # ── Section 181: Driving without valid license ──
    {"offence_code": "NO_LICENSE", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 181", "source_url": "https://parivahan.gov.in"},

    # ── Section 182: Offences relating to licenses ──
    {"offence_code": "SECTION_182", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 182", "source_url": "https://parivahan.gov.in"},
    {"offence_code": "SECTION_182A", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 10000, "repeat_amount_inr": None, "section_ref": "Section 182A", "source_url": "https://parivahan.gov.in"},

    # ── Section 183: Driving at excessive speed ──
    {"offence_code": "SPEED_EXCESS", "vehicle_class": "LMV", "state": "ALL", "amount_inr": 1000, "repeat_amount_inr": 2000, "section_ref": "Section 183", "source_url": "https://parivahan.gov.in"},
    {"offence_code": "SPEED_EXCESS", "vehicle_class": "TWO_WHEELER", "state": "ALL", "amount_inr": 1000, "repeat_amount_inr": 2000, "section_ref": "Section 183", "source_url": "https://parivahan.gov.in"},
    {"offence_code": "SPEED_EXCESS", "vehicle_class": "HGV", "state": "ALL", "amount_inr": 2000, "repeat_amount_inr": 4000, "section_ref": "Section 183", "source_url": "https://parivahan.gov.in"},
    {"offence_code": "SPEED_EXCESS", "vehicle_class": "3W", "state": "ALL", "amount_inr": 1000, "repeat_amount_inr": 2000, "section_ref": "Section 183", "source_url": "https://parivahan.gov.in"},

    # ── Section 184: Dangerous/rash driving ──
    {"offence_code": "SECTION_184", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 184", "source_url": "https://parivahan.gov.in"},

    # ── Section 184(c): Using mobile phone while driving ──
    {"offence_code": "MOBILE_PHONE", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 184(c)", "source_url": "https://parivahan.gov.in"},

    # ── Section 185: Drunk driving ──
    {"offence_code": "DRUNK_DRIVING", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 10000, "repeat_amount_inr": 15000, "section_ref": "Section 185", "source_url": "https://parivahan.gov.in"},

    # ── Section 186: Driving when mentally/physically unfit ──
    {"offence_code": "SECTION_186", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 1000, "repeat_amount_inr": 2000, "section_ref": "Section 186", "source_url": "https://parivahan.gov.in"},

    # ── Section 189: Racing/speed trials ──
    {"offence_code": "SECTION_189", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 189", "source_url": "https://parivahan.gov.in"},

    # ── Section 192: Using vehicle without registration ──
    {"offence_code": "SECTION_192", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 192", "source_url": "https://parivahan.gov.in"},
    {"offence_code": "SECTION_192A", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 192A", "source_url": "https://parivahan.gov.in"},

    # ── Section 194: No insurance ──
    {"offence_code": "NO_INSURANCE", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 2000, "repeat_amount_inr": 4000, "section_ref": "Section 196", "source_url": "https://parivahan.gov.in"},

    # ── Section 194A: Overloading (passengers) ──
    {"offence_code": "SECTION_194A", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 1000, "repeat_amount_inr": None, "section_ref": "Section 194A", "source_url": "https://parivahan.gov.in"},

    # ── Section 194B: Overloading (goods) ──
    {"offence_code": "SECTION_194B", "vehicle_class": "HGV", "state": "ALL", "amount_inr": 2000, "repeat_amount_inr": None, "section_ref": "Section 194B", "source_url": "https://parivahan.gov.in"},

    # ── Section 194C: No permit ──
    {"offence_code": "SECTION_194C", "vehicle_class": "COMMERCIAL", "state": "ALL", "amount_inr": 10000, "repeat_amount_inr": None, "section_ref": "Section 194C", "source_url": "https://parivahan.gov.in"},

    # ── Section 194D: Not wearing protective headgear (helmet) ──
    {"offence_code": "NO_HELMET", "vehicle_class": "TWO_WHEELER", "state": "ALL", "amount_inr": 1000, "repeat_amount_inr": 1000, "section_ref": "Section 194D", "source_url": "https://parivahan.gov.in"},

    # ── Section 194D: Not wearing seatbelt ──
    {"offence_code": "NO_SEATBELT", "vehicle_class": "LMV", "state": "ALL", "amount_inr": 1000, "repeat_amount_inr": 1000, "section_ref": "Section 194B", "source_url": "https://parivahan.gov.in"},
    {"offence_code": "NO_SEATBELT", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 1000, "repeat_amount_inr": 1000, "section_ref": "Section 194B", "source_url": "https://parivahan.gov.in"},

    # ── Section 194E: Failure to give way to emergency vehicle ──
    {"offence_code": "SECTION_194E", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 10000, "repeat_amount_inr": None, "section_ref": "Section 194E", "source_url": "https://parivahan.gov.in"},

    # ── Section 194F: No PUC certificate ──
    {"offence_code": "SECTION_194F", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 10000, "repeat_amount_inr": None, "section_ref": "Section 194F", "source_url": "https://parivahan.gov.in"},
    {"offence_code": "NO_PUC", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 10000, "repeat_amount_inr": None, "section_ref": "Section 194F", "source_url": "https://parivahan.gov.in"},

    # ── Section 196: Driving uninsured vehicle ──
    {"offence_code": "SECTION_196", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 2000, "repeat_amount_inr": 4000, "section_ref": "Section 196", "source_url": "https://parivahan.gov.in"},

    # ── Section 199: Offences by juveniles ──
    {"offence_code": "SECTION_199", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 25000, "repeat_amount_inr": 25000, "section_ref": "Section 199", "source_url": "https://parivahan.gov.in"},

    # ── Section 206: Refusal to produce documents ──
    {"offence_code": "SECTION_206", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 500, "repeat_amount_inr": 1500, "section_ref": "Section 206", "source_url": "https://parivahan.gov.in"},

    # ── Wrong-way driving (Section 184 sub-offence) ──
    {"offence_code": "WRONG_WAY", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 184", "source_url": "https://parivahan.gov.in"},

    # ── Red light jumping (Section 177 sub-offence) ──
    {"offence_code": "RED_LIGHT_JUMPING", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 1000, "repeat_amount_inr": 5000, "section_ref": "Section 177", "source_url": "https://parivahan.gov.in"},

    # ── No parking (Section 177) ──
    {"offence_code": "NO_PARKING", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 500, "repeat_amount_inr": 1500, "section_ref": "Section 177", "source_url": "https://parivahan.gov.in"},

    # ── Honking in no-horn zone ──
    {"offence_code": "HORN_VIOLATION", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 1000, "repeat_amount_inr": 2000, "section_ref": "Section 177", "source_url": "https://parivahan.gov.in"},

    # ── Number plate violation ──
    {"offence_code": "NUMBER_PLATE_VIOLATION", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 177", "source_url": "https://parivahan.gov.in"},
]


# ─── State-specific fine variations ───────────────────────────────────────────
# Many states have adopted higher or lower fines than the central schedule.

STATE_FINES = []

def _gen_state_fines():
    """Generate state-specific fine variations for major states."""
    # Tamil Nadu (TN) — already has some data, but adding more
    tn_fines = [
        {"offence_code": "NO_HELMET", "vehicle_class": "TWO_WHEELER", "state": "TN", "amount_inr": 1000, "repeat_amount_inr": 1000, "section_ref": "Section 194D", "source_url": "https://tnsta.gov.in"},
        {"offence_code": "NO_LICENSE", "vehicle_class": "ALL", "state": "TN", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 181", "source_url": "https://tnsta.gov.in"},
        {"offence_code": "DRUNK_DRIVING", "vehicle_class": "ALL", "state": "TN", "amount_inr": 10000, "repeat_amount_inr": 15000, "section_ref": "Section 185", "source_url": "https://tnsta.gov.in"},
        {"offence_code": "SPEED_EXCESS", "vehicle_class": "LMV", "state": "TN", "amount_inr": 1000, "repeat_amount_inr": 2000, "section_ref": "Section 183", "source_url": "https://tnsta.gov.in"},
        {"offence_code": "SPEED_EXCESS", "vehicle_class": "TWO_WHEELER", "state": "TN", "amount_inr": 1000, "repeat_amount_inr": 2000, "section_ref": "Section 183", "source_url": "https://tnsta.gov.in"},
        {"offence_code": "MOBILE_PHONE", "vehicle_class": "ALL", "state": "TN", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 184(c)", "source_url": "https://tnsta.gov.in"},
        {"offence_code": "NO_SEATBELT", "vehicle_class": "LMV", "state": "TN", "amount_inr": 1000, "repeat_amount_inr": 1000, "section_ref": "Section 194B", "source_url": "https://tnsta.gov.in"},
        {"offence_code": "NO_INSURANCE", "vehicle_class": "ALL", "state": "TN", "amount_inr": 2000, "repeat_amount_inr": 4000, "section_ref": "Section 196", "source_url": "https://tnsta.gov.in"},
        {"offence_code": "RED_LIGHT_JUMPING", "vehicle_class": "ALL", "state": "TN", "amount_inr": 1000, "repeat_amount_inr": 5000, "section_ref": "Section 177", "source_url": "https://tnsta.gov.in"},
        {"offence_code": "SECTION_184", "vehicle_class": "ALL", "state": "TN", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 184", "source_url": "https://tnsta.gov.in"},
        {"offence_code": "NO_PUC", "vehicle_class": "ALL", "state": "TN", "amount_inr": 10000, "repeat_amount_inr": None, "section_ref": "Section 194F", "source_url": "https://tnsta.gov.in"},
        {"offence_code": "WRONG_WAY", "vehicle_class": "ALL", "state": "TN", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 184", "source_url": "https://tnsta.gov.in"},
        {"offence_code": "NO_PARKING", "vehicle_class": "ALL", "state": "TN", "amount_inr": 500, "repeat_amount_inr": 1500, "section_ref": "Section 177", "source_url": "https://tnsta.gov.in"},
    ]

    # Delhi (DL) — Highest fines in India
    dl_fines = [
        {"offence_code": "NO_HELMET", "vehicle_class": "TWO_WHEELER", "state": "DL", "amount_inr": 1000, "repeat_amount_inr": 2000, "section_ref": "Section 194D", "source_url": "https://delhitrafficpolice.nic.in"},
        {"offence_code": "NO_LICENSE", "vehicle_class": "ALL", "state": "DL", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 181", "source_url": "https://delhitrafficpolice.nic.in"},
        {"offence_code": "DRUNK_DRIVING", "vehicle_class": "ALL", "state": "DL", "amount_inr": 10000, "repeat_amount_inr": 15000, "section_ref": "Section 185", "source_url": "https://delhitrafficpolice.nic.in"},
        {"offence_code": "SPEED_EXCESS", "vehicle_class": "LMV", "state": "DL", "amount_inr": 2000, "repeat_amount_inr": 4000, "section_ref": "Section 183", "source_url": "https://delhitrafficpolice.nic.in"},
        {"offence_code": "SPEED_EXCESS", "vehicle_class": "TWO_WHEELER", "state": "DL", "amount_inr": 2000, "repeat_amount_inr": 4000, "section_ref": "Section 183", "source_url": "https://delhitrafficpolice.nic.in"},
        {"offence_code": "MOBILE_PHONE", "vehicle_class": "ALL", "state": "DL", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 184(c)", "source_url": "https://delhitrafficpolice.nic.in"},
        {"offence_code": "NO_SEATBELT", "vehicle_class": "LMV", "state": "DL", "amount_inr": 1000, "repeat_amount_inr": 1000, "section_ref": "Section 194B", "source_url": "https://delhitrafficpolice.nic.in"},
        {"offence_code": "NO_INSURANCE", "vehicle_class": "ALL", "state": "DL", "amount_inr": 2000, "repeat_amount_inr": 4000, "section_ref": "Section 196", "source_url": "https://delhitrafficpolice.nic.in"},
        {"offence_code": "RED_LIGHT_JUMPING", "vehicle_class": "ALL", "state": "DL", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 177", "source_url": "https://delhitrafficpolice.nic.in"},
        {"offence_code": "SECTION_184", "vehicle_class": "ALL", "state": "DL", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 184", "source_url": "https://delhitrafficpolice.nic.in"},
        {"offence_code": "NO_PUC", "vehicle_class": "ALL", "state": "DL", "amount_inr": 10000, "repeat_amount_inr": None, "section_ref": "Section 194F", "source_url": "https://delhitrafficpolice.nic.in"},
        {"offence_code": "WRONG_WAY", "vehicle_class": "ALL", "state": "DL", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 184", "source_url": "https://delhitrafficpolice.nic.in"},
        {"offence_code": "NO_PARKING", "vehicle_class": "ALL", "state": "DL", "amount_inr": 500, "repeat_amount_inr": 1500, "section_ref": "Section 177", "source_url": "https://delhitrafficpolice.nic.in"},
    ]

    # Maharashtra (MH)
    mh_fines = [
        {"offence_code": "NO_HELMET", "vehicle_class": "TWO_WHEELER", "state": "MH", "amount_inr": 500, "repeat_amount_inr": 1000, "section_ref": "Section 194D", "source_url": "https://transport.maharashtra.gov.in"},
        {"offence_code": "NO_LICENSE", "vehicle_class": "ALL", "state": "MH", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 181", "source_url": "https://transport.maharashtra.gov.in"},
        {"offence_code": "DRUNK_DRIVING", "vehicle_class": "ALL", "state": "MH", "amount_inr": 10000, "repeat_amount_inr": 15000, "section_ref": "Section 185", "source_url": "https://transport.maharashtra.gov.in"},
        {"offence_code": "SPEED_EXCESS", "vehicle_class": "LMV", "state": "MH", "amount_inr": 1000, "repeat_amount_inr": 2000, "section_ref": "Section 183", "source_url": "https://transport.maharashtra.gov.in"},
        {"offence_code": "MOBILE_PHONE", "vehicle_class": "ALL", "state": "MH", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 184(c)", "source_url": "https://transport.maharashtra.gov.in"},
        {"offence_code": "NO_SEATBELT", "vehicle_class": "LMV", "state": "MH", "amount_inr": 1000, "repeat_amount_inr": 1000, "section_ref": "Section 194B", "source_url": "https://transport.maharashtra.gov.in"},
        {"offence_code": "NO_INSURANCE", "vehicle_class": "ALL", "state": "MH", "amount_inr": 2000, "repeat_amount_inr": 4000, "section_ref": "Section 196", "source_url": "https://transport.maharashtra.gov.in"},
        {"offence_code": "RED_LIGHT_JUMPING", "vehicle_class": "ALL", "state": "MH", "amount_inr": 1000, "repeat_amount_inr": 5000, "section_ref": "Section 177", "source_url": "https://transport.maharashtra.gov.in"},
    ]

    # Karnataka (KA)
    ka_fines = [
        {"offence_code": "NO_HELMET", "vehicle_class": "TWO_WHEELER", "state": "KA", "amount_inr": 500, "repeat_amount_inr": 1000, "section_ref": "Section 194D", "source_url": "https://transport.karnataka.gov.in"},
        {"offence_code": "NO_LICENSE", "vehicle_class": "ALL", "state": "KA", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 181", "source_url": "https://transport.karnataka.gov.in"},
        {"offence_code": "DRUNK_DRIVING", "vehicle_class": "ALL", "state": "KA", "amount_inr": 10000, "repeat_amount_inr": 15000, "section_ref": "Section 185", "source_url": "https://transport.karnataka.gov.in"},
        {"offence_code": "SPEED_EXCESS", "vehicle_class": "LMV", "state": "KA", "amount_inr": 1000, "repeat_amount_inr": 2000, "section_ref": "Section 183", "source_url": "https://transport.karnataka.gov.in"},
        {"offence_code": "MOBILE_PHONE", "vehicle_class": "ALL", "state": "KA", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 184(c)", "source_url": "https://transport.karnataka.gov.in"},
        {"offence_code": "NO_SEATBELT", "vehicle_class": "LMV", "state": "KA", "amount_inr": 1000, "repeat_amount_inr": 1000, "section_ref": "Section 194B", "source_url": "https://transport.karnataka.gov.in"},
        {"offence_code": "NO_INSURANCE", "vehicle_class": "ALL", "state": "KA", "amount_inr": 2000, "repeat_amount_inr": 4000, "section_ref": "Section 196", "source_url": "https://transport.karnataka.gov.in"},
        {"offence_code": "RED_LIGHT_JUMPING", "vehicle_class": "ALL", "state": "KA", "amount_inr": 1000, "repeat_amount_inr": 5000, "section_ref": "Section 177", "source_url": "https://transport.karnataka.gov.in"},
    ]

    # Kerala (KL)
    kl_fines = [
        {"offence_code": "NO_HELMET", "vehicle_class": "TWO_WHEELER", "state": "KL", "amount_inr": 500, "repeat_amount_inr": 1000, "section_ref": "Section 194D", "source_url": "https://mvd.kerala.gov.in"},
        {"offence_code": "NO_LICENSE", "vehicle_class": "ALL", "state": "KL", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 181", "source_url": "https://mvd.kerala.gov.in"},
        {"offence_code": "DRUNK_DRIVING", "vehicle_class": "ALL", "state": "KL", "amount_inr": 10000, "repeat_amount_inr": 15000, "section_ref": "Section 185", "source_url": "https://mvd.kerala.gov.in"},
        {"offence_code": "SPEED_EXCESS", "vehicle_class": "LMV", "state": "KL", "amount_inr": 1500, "repeat_amount_inr": 3000, "section_ref": "Section 183", "source_url": "https://mvd.kerala.gov.in"},
        {"offence_code": "MOBILE_PHONE", "vehicle_class": "ALL", "state": "KL", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 184(c)", "source_url": "https://mvd.kerala.gov.in"},
        {"offence_code": "NO_SEATBELT", "vehicle_class": "LMV", "state": "KL", "amount_inr": 1000, "repeat_amount_inr": 1000, "section_ref": "Section 194B", "source_url": "https://mvd.kerala.gov.in"},
        {"offence_code": "NO_INSURANCE", "vehicle_class": "ALL", "state": "KL", "amount_inr": 2000, "repeat_amount_inr": 4000, "section_ref": "Section 196", "source_url": "https://mvd.kerala.gov.in"},
    ]

    # Uttar Pradesh (UP)
    up_fines = [
        {"offence_code": "NO_HELMET", "vehicle_class": "TWO_WHEELER", "state": "UP", "amount_inr": 1000, "repeat_amount_inr": 2000, "section_ref": "Section 194D", "source_url": "https://uptransport.upsdc.gov.in"},
        {"offence_code": "NO_LICENSE", "vehicle_class": "ALL", "state": "UP", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 181", "source_url": "https://uptransport.upsdc.gov.in"},
        {"offence_code": "DRUNK_DRIVING", "vehicle_class": "ALL", "state": "UP", "amount_inr": 10000, "repeat_amount_inr": 15000, "section_ref": "Section 185", "source_url": "https://uptransport.upsdc.gov.in"},
        {"offence_code": "SPEED_EXCESS", "vehicle_class": "LMV", "state": "UP", "amount_inr": 1000, "repeat_amount_inr": 2000, "section_ref": "Section 183", "source_url": "https://uptransport.upsdc.gov.in"},
        {"offence_code": "MOBILE_PHONE", "vehicle_class": "ALL", "state": "UP", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 184(c)", "source_url": "https://uptransport.upsdc.gov.in"},
        {"offence_code": "NO_SEATBELT", "vehicle_class": "LMV", "state": "UP", "amount_inr": 1000, "repeat_amount_inr": 1000, "section_ref": "Section 194B", "source_url": "https://uptransport.upsdc.gov.in"},
        {"offence_code": "NO_INSURANCE", "vehicle_class": "ALL", "state": "UP", "amount_inr": 2000, "repeat_amount_inr": 4000, "section_ref": "Section 196", "source_url": "https://uptransport.upsdc.gov.in"},
        {"offence_code": "RED_LIGHT_JUMPING", "vehicle_class": "ALL", "state": "UP", "amount_inr": 1000, "repeat_amount_inr": 5000, "section_ref": "Section 177", "source_url": "https://uptransport.upsdc.gov.in"},
    ]

    # Gujarat (GJ)
    gj_fines = [
        {"offence_code": "NO_HELMET", "vehicle_class": "TWO_WHEELER", "state": "GJ", "amount_inr": 500, "repeat_amount_inr": 1000, "section_ref": "Section 194D", "source_url": "https://rtogujarat.gov.in"},
        {"offence_code": "NO_LICENSE", "vehicle_class": "ALL", "state": "GJ", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 181", "source_url": "https://rtogujarat.gov.in"},
        {"offence_code": "DRUNK_DRIVING", "vehicle_class": "ALL", "state": "GJ", "amount_inr": 10000, "repeat_amount_inr": 15000, "section_ref": "Section 185", "source_url": "https://rtogujarat.gov.in"},
        {"offence_code": "SPEED_EXCESS", "vehicle_class": "LMV", "state": "GJ", "amount_inr": 1000, "repeat_amount_inr": 2000, "section_ref": "Section 183", "source_url": "https://rtogujarat.gov.in"},
        {"offence_code": "MOBILE_PHONE", "vehicle_class": "ALL", "state": "GJ", "amount_inr": 1000, "repeat_amount_inr": 5000, "section_ref": "Section 184(c)", "source_url": "https://rtogujarat.gov.in"},
        {"offence_code": "NO_SEATBELT", "vehicle_class": "LMV", "state": "GJ", "amount_inr": 1000, "repeat_amount_inr": 1000, "section_ref": "Section 194B", "source_url": "https://rtogujarat.gov.in"},
        {"offence_code": "NO_INSURANCE", "vehicle_class": "ALL", "state": "GJ", "amount_inr": 2000, "repeat_amount_inr": 4000, "section_ref": "Section 196", "source_url": "https://rtogujarat.gov.in"},
    ]

    # Rajasthan (RJ)
    rj_fines = [
        {"offence_code": "NO_HELMET", "vehicle_class": "TWO_WHEELER", "state": "RJ", "amount_inr": 1000, "repeat_amount_inr": 2000, "section_ref": "Section 194D", "source_url": "https://transport.rajasthan.gov.in"},
        {"offence_code": "NO_LICENSE", "vehicle_class": "ALL", "state": "RJ", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 181", "source_url": "https://transport.rajasthan.gov.in"},
        {"offence_code": "DRUNK_DRIVING", "vehicle_class": "ALL", "state": "RJ", "amount_inr": 10000, "repeat_amount_inr": 15000, "section_ref": "Section 185", "source_url": "https://transport.rajasthan.gov.in"},
        {"offence_code": "SPEED_EXCESS", "vehicle_class": "LMV", "state": "RJ", "amount_inr": 1000, "repeat_amount_inr": 2000, "section_ref": "Section 183", "source_url": "https://transport.rajasthan.gov.in"},
        {"offence_code": "MOBILE_PHONE", "vehicle_class": "ALL", "state": "RJ", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 184(c)", "source_url": "https://transport.rajasthan.gov.in"},
    ]

    # West Bengal (WB)
    wb_fines = [
        {"offence_code": "NO_HELMET", "vehicle_class": "TWO_WHEELER", "state": "WB", "amount_inr": 200, "repeat_amount_inr": 500, "section_ref": "Section 194D", "source_url": "https://transport.wb.gov.in"},
        {"offence_code": "NO_LICENSE", "vehicle_class": "ALL", "state": "WB", "amount_inr": 1000, "repeat_amount_inr": 2000, "section_ref": "Section 181", "source_url": "https://transport.wb.gov.in"},
        {"offence_code": "DRUNK_DRIVING", "vehicle_class": "ALL", "state": "WB", "amount_inr": 2000, "repeat_amount_inr": 3000, "section_ref": "Section 185", "source_url": "https://transport.wb.gov.in"},
        {"offence_code": "SPEED_EXCESS", "vehicle_class": "LMV", "state": "WB", "amount_inr": 400, "repeat_amount_inr": 1000, "section_ref": "Section 183", "source_url": "https://transport.wb.gov.in"},
        {"offence_code": "MOBILE_PHONE", "vehicle_class": "ALL", "state": "WB", "amount_inr": 1000, "repeat_amount_inr": 2000, "section_ref": "Section 184(c)", "source_url": "https://transport.wb.gov.in"},
    ]

    # Telangana (TS)
    ts_fines = [
        {"offence_code": "NO_HELMET", "vehicle_class": "TWO_WHEELER", "state": "TS", "amount_inr": 1000, "repeat_amount_inr": 2000, "section_ref": "Section 194D", "source_url": "https://transport.telangana.gov.in"},
        {"offence_code": "NO_LICENSE", "vehicle_class": "ALL", "state": "TS", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 181", "source_url": "https://transport.telangana.gov.in"},
        {"offence_code": "DRUNK_DRIVING", "vehicle_class": "ALL", "state": "TS", "amount_inr": 10000, "repeat_amount_inr": 15000, "section_ref": "Section 185", "source_url": "https://transport.telangana.gov.in"},
        {"offence_code": "SPEED_EXCESS", "vehicle_class": "LMV", "state": "TS", "amount_inr": 1000, "repeat_amount_inr": 2000, "section_ref": "Section 183", "source_url": "https://transport.telangana.gov.in"},
        {"offence_code": "MOBILE_PHONE", "vehicle_class": "ALL", "state": "TS", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 184(c)", "source_url": "https://transport.telangana.gov.in"},
        {"offence_code": "NO_SEATBELT", "vehicle_class": "LMV", "state": "TS", "amount_inr": 1000, "repeat_amount_inr": 1000, "section_ref": "Section 194B", "source_url": "https://transport.telangana.gov.in"},
        {"offence_code": "NO_INSURANCE", "vehicle_class": "ALL", "state": "TS", "amount_inr": 2000, "repeat_amount_inr": 4000, "section_ref": "Section 196", "source_url": "https://transport.telangana.gov.in"},
    ]

    # Andhra Pradesh (AP)
    ap_fines = [
        {"offence_code": "NO_HELMET", "vehicle_class": "TWO_WHEELER", "state": "AP", "amount_inr": 1000, "repeat_amount_inr": 2000, "section_ref": "Section 194D", "source_url": "https://aptransport.org"},
        {"offence_code": "NO_LICENSE", "vehicle_class": "ALL", "state": "AP", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 181", "source_url": "https://aptransport.org"},
        {"offence_code": "DRUNK_DRIVING", "vehicle_class": "ALL", "state": "AP", "amount_inr": 10000, "repeat_amount_inr": 15000, "section_ref": "Section 185", "source_url": "https://aptransport.org"},
        {"offence_code": "SPEED_EXCESS", "vehicle_class": "LMV", "state": "AP", "amount_inr": 1000, "repeat_amount_inr": 2000, "section_ref": "Section 183", "source_url": "https://aptransport.org"},
        {"offence_code": "MOBILE_PHONE", "vehicle_class": "ALL", "state": "AP", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Section 184(c)", "source_url": "https://aptransport.org"},
    ]

    # Punjab (PB), Haryana (HR), Bihar (BR), MP, Odisha — use central schedule
    for state_code in ["PB", "HR", "BR", "MP", "OR"]:
        for base in CENTRAL_FINES:
            if base["state"] == "ALL":
                entry = base.copy()
                entry["state"] = state_code
                entry["source_url"] = "https://parivahan.gov.in"
                STATE_FINES.append(entry)

    STATE_FINES.extend(tn_fines)
    STATE_FINES.extend(dl_fines)
    STATE_FINES.extend(mh_fines)
    STATE_FINES.extend(ka_fines)
    STATE_FINES.extend(kl_fines)
    STATE_FINES.extend(up_fines)
    STATE_FINES.extend(gj_fines)
    STATE_FINES.extend(rj_fines)
    STATE_FINES.extend(wb_fines)
    STATE_FINES.extend(ts_fines)
    STATE_FINES.extend(ap_fines)


if __name__ == "__main__":
    print("=" * 60)
    print("DriveLegal — Indian Traffic Fine Data Population")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)

    # 1. Schema migration
    migrate_schema(conn)

    # 2. Generate state fines
    _gen_state_fines()

    # 3. Insert central fines
    print(f"\n[Central] Inserting {len(CENTRAL_FINES)} central/national fines...")
    inserted, skipped = insert_fines(conn, CENTRAL_FINES)
    print(f"  -> Inserted: {inserted}, Skipped (duplicates): {skipped}")

    # 4. Insert state-specific fines
    print(f"\n[States] Inserting {len(STATE_FINES)} state-specific fines...")
    inserted, skipped = insert_fines(conn, STATE_FINES)
    print(f"  -> Inserted: {inserted}, Skipped (duplicates): {skipped}")

    # 5. Summary
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM fines WHERE country = 'IN'")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT DISTINCT state FROM fines WHERE country = 'IN' ORDER BY state")
    states = [r[0] for r in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT offence_code FROM fines WHERE country = 'IN' ORDER BY offence_code")
    offences = [r[0] for r in cursor.fetchall()]

    print(f"\n{'=' * 60}")
    print(f"TOTAL Indian fines in DB: {total}")
    print(f"States covered: {', '.join(states)}")
    print(f"Offence types: {len(offences)}")
    print(f"{'=' * 60}")

    conn.close()
