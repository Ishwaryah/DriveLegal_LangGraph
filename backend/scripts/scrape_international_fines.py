"""
scrape_international_fines.py — Populate fines.db with international traffic fine data.

Countries covered:
  - UAE (Dubai, Abu Dhabi)
  - USA (Federal / General)
  - UK (Fixed Penalty Notices)
  - Singapore
  - Saudi Arabia (Moroor)

Data sources: Official government traffic fine schedules (publicly available).
Amounts stored in local currency with currency code.
"""

import sqlite3
import hashlib
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "fines.db")


def make_hash(offence: str, vehicle: str, state: str, country: str) -> str:
    key = f"{offence}|{vehicle}|{state}|{country}"
    return hashlib.sha256(key.encode()).hexdigest()


def insert_fines(conn: sqlite3.Connection, fines_data: list[dict]):
    cursor = conn.cursor()
    inserted = 0
    skipped = 0
    for f in fines_data:
        vh = make_hash(f["offence_code"], f["vehicle_class"], f["state"], f["country"])
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
                f["country"], f["currency"],
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1
    conn.commit()
    return inserted, skipped


# ═══════════════════════════════════════════════════════════════════════════════
# UAE / DUBAI — Dubai Police Traffic Fine Schedule
# Source: https://www.dubaipolice.gov.ae / Federal Traffic Law
# Amounts in AED (1 AED ≈ ₹22.7)
# ═══════════════════════════════════════════════════════════════════════════════

UAE_FINES = [
    # Speeding fines (tiered by km/h over limit)
    {"offence_code": "SPEED_EXCESS", "vehicle_class": "ALL", "state": "DUBAI", "amount_inr": 300, "repeat_amount_inr": 600, "section_ref": "Federal Traffic Law Art. 52", "source_url": "https://www.dubaipolice.gov.ae", "country": "AE", "currency": "AED"},
    {"offence_code": "SPEED_EXCESS_20", "vehicle_class": "ALL", "state": "DUBAI", "amount_inr": 600, "repeat_amount_inr": 1200, "section_ref": "Federal Traffic Law Art. 52 (20+ km/h)", "source_url": "https://www.dubaipolice.gov.ae", "country": "AE", "currency": "AED"},
    {"offence_code": "SPEED_EXCESS_40", "vehicle_class": "ALL", "state": "DUBAI", "amount_inr": 1000, "repeat_amount_inr": 2000, "section_ref": "Federal Traffic Law Art. 52 (40+ km/h)", "source_url": "https://www.dubaipolice.gov.ae", "country": "AE", "currency": "AED"},
    {"offence_code": "SPEED_EXCESS_60", "vehicle_class": "ALL", "state": "DUBAI", "amount_inr": 2000, "repeat_amount_inr": 3000, "section_ref": "Federal Traffic Law Art. 52 (60+ km/h)", "source_url": "https://www.dubaipolice.gov.ae", "country": "AE", "currency": "AED"},
    {"offence_code": "SPEED_EXCESS_80", "vehicle_class": "ALL", "state": "DUBAI", "amount_inr": 3000, "repeat_amount_inr": 3000, "section_ref": "Federal Traffic Law Art. 52 (80+ km/h) + 60 days impound", "source_url": "https://www.dubaipolice.gov.ae", "country": "AE", "currency": "AED"},

    # Running red light
    {"offence_code": "RED_LIGHT_JUMPING", "vehicle_class": "ALL", "state": "DUBAI", "amount_inr": 1000, "repeat_amount_inr": 1000, "section_ref": "Federal Traffic Law Art. 35 + 12 black points + 30-day impound", "source_url": "https://www.dubaipolice.gov.ae", "country": "AE", "currency": "AED"},

    # No seatbelt
    {"offence_code": "NO_SEATBELT", "vehicle_class": "ALL", "state": "DUBAI", "amount_inr": 400, "repeat_amount_inr": 400, "section_ref": "Federal Traffic Law Art. 43 + 4 black points", "source_url": "https://www.dubaipolice.gov.ae", "country": "AE", "currency": "AED"},

    # Mobile phone while driving
    {"offence_code": "MOBILE_PHONE", "vehicle_class": "ALL", "state": "DUBAI", "amount_inr": 800, "repeat_amount_inr": 800, "section_ref": "Federal Traffic Law Art. 30 + 4 black points", "source_url": "https://www.dubaipolice.gov.ae", "country": "AE", "currency": "AED"},

    # No helmet (motorcycle)
    {"offence_code": "NO_HELMET", "vehicle_class": "TWO_WHEELER", "state": "DUBAI", "amount_inr": 500, "repeat_amount_inr": 500, "section_ref": "Federal Traffic Law Art. 44 + 4 black points", "source_url": "https://www.dubaipolice.gov.ae", "country": "AE", "currency": "AED"},

    # Drunk driving
    {"offence_code": "DRUNK_DRIVING", "vehicle_class": "ALL", "state": "DUBAI", "amount_inr": 0, "repeat_amount_inr": 0, "section_ref": "Federal Traffic Law Art. 49 — ZERO TOLERANCE. Imprisonment, vehicle impound, deportation for expats. No fine — criminal charge.", "source_url": "https://www.dubaipolice.gov.ae", "country": "AE", "currency": "AED"},

    # No license
    {"offence_code": "NO_LICENSE", "vehicle_class": "ALL", "state": "DUBAI", "amount_inr": 5000, "repeat_amount_inr": 5000, "section_ref": "Federal Traffic Law Art. 25 + vehicle impound", "source_url": "https://www.dubaipolice.gov.ae", "country": "AE", "currency": "AED"},

    # No insurance
    {"offence_code": "NO_INSURANCE", "vehicle_class": "ALL", "state": "DUBAI", "amount_inr": 500, "repeat_amount_inr": 500, "section_ref": "Federal Traffic Law Art. 12 + 4 black points", "source_url": "https://www.dubaipolice.gov.ae", "country": "AE", "currency": "AED"},

    # Dangerous driving
    {"offence_code": "SECTION_184", "vehicle_class": "ALL", "state": "DUBAI", "amount_inr": 2000, "repeat_amount_inr": 2000, "section_ref": "Federal Traffic Law Art. 48 + 23 black points + 60-day impound", "source_url": "https://www.dubaipolice.gov.ae", "country": "AE", "currency": "AED"},

    # Wrong way driving
    {"offence_code": "WRONG_WAY", "vehicle_class": "ALL", "state": "DUBAI", "amount_inr": 600, "repeat_amount_inr": 600, "section_ref": "Federal Traffic Law + 6 black points", "source_url": "https://www.dubaipolice.gov.ae", "country": "AE", "currency": "AED"},

    # No parking
    {"offence_code": "NO_PARKING", "vehicle_class": "ALL", "state": "DUBAI", "amount_inr": 200, "repeat_amount_inr": 400, "section_ref": "RTA Parking Violation", "source_url": "https://www.rta.ae", "country": "AE", "currency": "AED"},

    # Abu Dhabi specifics
    {"offence_code": "SPEED_EXCESS", "vehicle_class": "ALL", "state": "ABU_DHABI", "amount_inr": 300, "repeat_amount_inr": 600, "section_ref": "Federal Traffic Law Art. 52", "source_url": "https://www.adpolice.gov.ae", "country": "AE", "currency": "AED"},
    {"offence_code": "RED_LIGHT_JUMPING", "vehicle_class": "ALL", "state": "ABU_DHABI", "amount_inr": 1000, "repeat_amount_inr": 1000, "section_ref": "Federal Traffic Law Art. 35 + 12 black points", "source_url": "https://www.adpolice.gov.ae", "country": "AE", "currency": "AED"},
    {"offence_code": "NO_SEATBELT", "vehicle_class": "ALL", "state": "ABU_DHABI", "amount_inr": 400, "repeat_amount_inr": 400, "section_ref": "Federal Traffic Law Art. 43", "source_url": "https://www.adpolice.gov.ae", "country": "AE", "currency": "AED"},
    {"offence_code": "MOBILE_PHONE", "vehicle_class": "ALL", "state": "ABU_DHABI", "amount_inr": 800, "repeat_amount_inr": 800, "section_ref": "Federal Traffic Law Art. 30", "source_url": "https://www.adpolice.gov.ae", "country": "AE", "currency": "AED"},
]


# ═══════════════════════════════════════════════════════════════════════════════
# UK — Fixed Penalty Notices + Court Fines
# Source: gov.uk/browse/driving/penalty-points-fines-bans
# Amounts in GBP (1 GBP ≈ ₹105)
# ═══════════════════════════════════════════════════════════════════════════════

UK_FINES = [
    {"offence_code": "SPEED_EXCESS", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 100, "repeat_amount_inr": 2500, "section_ref": "Road Traffic Act 1988 s.89 — minimum £100 + 3 points, up to £2,500 court fine", "source_url": "https://www.gov.uk/speeding-penalties", "country": "GB", "currency": "GBP"},
    {"offence_code": "RED_LIGHT_JUMPING", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 100, "repeat_amount_inr": 1000, "section_ref": "Road Traffic Act 1988 s.36 — £100 FPN + 3 points, up to £1,000 court fine", "source_url": "https://www.gov.uk/traffic-light-offences", "country": "GB", "currency": "GBP"},
    {"offence_code": "MOBILE_PHONE", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 200, "repeat_amount_inr": 1000, "section_ref": "Road Vehicles Regs 2003 — £200 FPN + 6 points, up to £1,000 court fine", "source_url": "https://www.gov.uk/using-mobile-phones-when-driving", "country": "GB", "currency": "GBP"},
    {"offence_code": "NO_SEATBELT", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 100, "repeat_amount_inr": 500, "section_ref": "Road Traffic Act 1988 s.14 — £100 FPN, up to £500 court fine", "source_url": "https://www.gov.uk/seat-belt-fine", "country": "GB", "currency": "GBP"},
    {"offence_code": "NO_INSURANCE", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 300, "repeat_amount_inr": 0, "section_ref": "Road Traffic Act 1988 s.143 — £300 FPN + 6 points; unlimited court fine", "source_url": "https://www.gov.uk/vehicle-insurance", "country": "GB", "currency": "GBP"},
    {"offence_code": "NO_LICENSE", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 0, "repeat_amount_inr": 0, "section_ref": "Road Traffic Act 1988 s.87 — up to £1,000 court fine + 3-6 points", "source_url": "https://www.gov.uk/driving-licence-penalties", "country": "GB", "currency": "GBP"},
    {"offence_code": "DRUNK_DRIVING", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 0, "repeat_amount_inr": 0, "section_ref": "Road Traffic Act 1988 s.5 — UNLIMITED fine + 12-month driving ban + up to 6 months prison", "source_url": "https://www.gov.uk/drink-driving-penalties", "country": "GB", "currency": "GBP"},
    {"offence_code": "NO_HELMET", "vehicle_class": "TWO_WHEELER", "state": "ALL", "amount_inr": 500, "repeat_amount_inr": 500, "section_ref": "Road Traffic Act 1988 s.16 — £500 maximum court fine", "source_url": "https://www.gov.uk/motorcycle-helmet-law", "country": "GB", "currency": "GBP"},
    {"offence_code": "SECTION_184", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 0, "repeat_amount_inr": 0, "section_ref": "Road Traffic Act 1988 s.2 — UNLIMITED fine + 2 years prison + mandatory disqualification", "source_url": "https://www.gov.uk/dangerous-driving-penalties", "country": "GB", "currency": "GBP"},
    {"offence_code": "NO_PARKING", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 70, "repeat_amount_inr": 130, "section_ref": "Traffic Management Act 2004 — PCN £70-£130 (varies by London/non-London)", "source_url": "https://www.gov.uk/parking-penalties", "country": "GB", "currency": "GBP"},
]


# ═══════════════════════════════════════════════════════════════════════════════
# USA — Federal / General State Traffic Fines
# Amounts in USD — varies widely by state; these are typical ranges
# Source: Various state DMV / NHTSA data
# ═══════════════════════════════════════════════════════════════════════════════

USA_FINES = [
    {"offence_code": "SPEED_EXCESS", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 150, "repeat_amount_inr": 500, "section_ref": "Varies by state — typically $150-$500; doubles in school/work zones", "source_url": "https://www.nhtsa.gov", "country": "US", "currency": "USD"},
    {"offence_code": "SPEED_EXCESS", "vehicle_class": "ALL", "state": "CALIFORNIA", "amount_inr": 238, "repeat_amount_inr": 490, "section_ref": "CA Vehicle Code §22350 — $238+ for 1-15mph over", "source_url": "https://www.dmv.ca.gov", "country": "US", "currency": "USD"},
    {"offence_code": "SPEED_EXCESS", "vehicle_class": "ALL", "state": "NEW_YORK", "amount_inr": 150, "repeat_amount_inr": 600, "section_ref": "NY VTL §1180 — $150-$600 + 3-11 points", "source_url": "https://dmv.ny.gov", "country": "US", "currency": "USD"},
    {"offence_code": "SPEED_EXCESS", "vehicle_class": "ALL", "state": "TEXAS", "amount_inr": 200, "repeat_amount_inr": 500, "section_ref": "TX Transportation Code §545.351", "source_url": "https://www.txdot.gov", "country": "US", "currency": "USD"},

    {"offence_code": "RED_LIGHT_JUMPING", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 100, "repeat_amount_inr": 500, "section_ref": "Varies — typically $100-$500 + points", "source_url": "https://www.nhtsa.gov", "country": "US", "currency": "USD"},
    {"offence_code": "RED_LIGHT_JUMPING", "vehicle_class": "ALL", "state": "CALIFORNIA", "amount_inr": 490, "repeat_amount_inr": 490, "section_ref": "CA Vehicle Code §21453(a) — $490+ including surcharges", "source_url": "https://www.dmv.ca.gov", "country": "US", "currency": "USD"},

    {"offence_code": "NO_SEATBELT", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 25, "repeat_amount_inr": 100, "section_ref": "Varies — $25-$200; primary or secondary enforcement depends on state", "source_url": "https://www.nhtsa.gov", "country": "US", "currency": "USD"},
    {"offence_code": "NO_SEATBELT", "vehicle_class": "ALL", "state": "CALIFORNIA", "amount_inr": 162, "repeat_amount_inr": 162, "section_ref": "CA Vehicle Code §27315 — $162+", "source_url": "https://www.dmv.ca.gov", "country": "US", "currency": "USD"},

    {"offence_code": "MOBILE_PHONE", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 150, "repeat_amount_inr": 500, "section_ref": "Varies — $150-$500; illegal in 29+ states", "source_url": "https://www.nhtsa.gov", "country": "US", "currency": "USD"},
    {"offence_code": "MOBILE_PHONE", "vehicle_class": "ALL", "state": "CALIFORNIA", "amount_inr": 162, "repeat_amount_inr": 285, "section_ref": "CA Vehicle Code §23123 — $162 first, $285 subsequent", "source_url": "https://www.dmv.ca.gov", "country": "US", "currency": "USD"},

    {"offence_code": "DRUNK_DRIVING", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 1000, "repeat_amount_inr": 10000, "section_ref": "DUI/DWI — $1,000-$10,000+ fine, license suspension, possible jail. BAC limit: 0.08%", "source_url": "https://www.nhtsa.gov", "country": "US", "currency": "USD"},
    {"offence_code": "DRUNK_DRIVING", "vehicle_class": "ALL", "state": "CALIFORNIA", "amount_inr": 2000, "repeat_amount_inr": 18000, "section_ref": "CA Vehicle Code §23152 — $390-$1,000 + surcharges = ~$2,000-$18,000 total", "source_url": "https://www.dmv.ca.gov", "country": "US", "currency": "USD"},

    {"offence_code": "NO_INSURANCE", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 500, "repeat_amount_inr": 2500, "section_ref": "Varies — $500-$2,500; license suspension in most states", "source_url": "https://www.nhtsa.gov", "country": "US", "currency": "USD"},
    {"offence_code": "NO_LICENSE", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 250, "repeat_amount_inr": 1000, "section_ref": "Varies — $250-$1,000; potential arrest in some states", "source_url": "https://www.nhtsa.gov", "country": "US", "currency": "USD"},
    {"offence_code": "NO_PARKING", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 50, "repeat_amount_inr": 200, "section_ref": "Varies — $50-$200; towing + additional fees", "source_url": "https://www.nhtsa.gov", "country": "US", "currency": "USD"},
]


# ═══════════════════════════════════════════════════════════════════════════════
# SINGAPORE — Land Transport Authority (LTA) / Traffic Police
# Amounts in SGD (1 SGD ≈ ₹62)
# Source: https://www.police.gov.sg / https://www.lta.gov.sg
# ═══════════════════════════════════════════════════════════════════════════════

SINGAPORE_FINES = [
    {"offence_code": "SPEED_EXCESS", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 150, "repeat_amount_inr": 300, "section_ref": "Road Traffic Act s.63 — $130-$170 (1-20km/h over), 4 demerit points", "source_url": "https://www.police.gov.sg", "country": "SG", "currency": "SGD"},
    {"offence_code": "SPEED_EXCESS_40", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 300, "repeat_amount_inr": 500, "section_ref": "Road Traffic Act s.63 — $300+ (40+ km/h over), 12 demerit points, court", "source_url": "https://www.police.gov.sg", "country": "SG", "currency": "SGD"},

    {"offence_code": "RED_LIGHT_JUMPING", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 400, "repeat_amount_inr": 400, "section_ref": "Road Traffic Act s.120 — $400 + 12 demerit points; serious = court", "source_url": "https://www.police.gov.sg", "country": "SG", "currency": "SGD"},

    {"offence_code": "NO_SEATBELT", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 120, "repeat_amount_inr": 120, "section_ref": "Road Traffic Act — $120 fine + 3 demerit points", "source_url": "https://www.police.gov.sg", "country": "SG", "currency": "SGD"},

    {"offence_code": "MOBILE_PHONE", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 200, "repeat_amount_inr": 200, "section_ref": "Road Traffic Rules r.28A — $200 + 6 demerit points", "source_url": "https://www.police.gov.sg", "country": "SG", "currency": "SGD"},

    {"offence_code": "DRUNK_DRIVING", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 2000, "repeat_amount_inr": 5000, "section_ref": "Road Traffic Act s.67 — $2,000-$10,000 or 12 months jail; disqualification ≥2 years. BAC limit: 0.035%", "source_url": "https://www.police.gov.sg", "country": "SG", "currency": "SGD"},

    {"offence_code": "NO_LICENSE", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 1000, "repeat_amount_inr": 5000, "section_ref": "Road Traffic Act s.35 — $1,000-$5,000 or 12 months jail", "source_url": "https://www.police.gov.sg", "country": "SG", "currency": "SGD"},

    {"offence_code": "NO_INSURANCE", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 1000, "repeat_amount_inr": 5000, "section_ref": "Motor Vehicles Act s.3 — $1,000-$5,000 or 12 months jail", "source_url": "https://www.lta.gov.sg", "country": "SG", "currency": "SGD"},

    {"offence_code": "NO_HELMET", "vehicle_class": "TWO_WHEELER", "state": "ALL", "amount_inr": 200, "repeat_amount_inr": 200, "section_ref": "Road Traffic Act s.74 — $200 fine", "source_url": "https://www.police.gov.sg", "country": "SG", "currency": "SGD"},

    {"offence_code": "NO_PARKING", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 70, "repeat_amount_inr": 150, "section_ref": "Parking Places Act — $70 coupon parking, $150 season parking", "source_url": "https://www.lta.gov.sg", "country": "SG", "currency": "SGD"},
]


# ═══════════════════════════════════════════════════════════════════════════════
# SAUDI ARABIA — Moroor (Traffic Department) Fine Schedule
# Amounts in SAR (1 SAR ≈ ₹22.2)
# Source: https://www.moi.gov.sa
# ═══════════════════════════════════════════════════════════════════════════════

SAUDI_FINES = [
    {"offence_code": "SPEED_EXCESS", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 500, "repeat_amount_inr": 900, "section_ref": "Moroor Traffic Law — SAR 500-900 for exceeding speed limit", "source_url": "https://www.moi.gov.sa", "country": "SA", "currency": "SAR"},
    {"offence_code": "RED_LIGHT_JUMPING", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 3000, "repeat_amount_inr": 6000, "section_ref": "Moroor — SAR 3,000-6,000 + possible impound", "source_url": "https://www.moi.gov.sa", "country": "SA", "currency": "SAR"},
    {"offence_code": "NO_SEATBELT", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 150, "repeat_amount_inr": 300, "section_ref": "Moroor — SAR 150-300", "source_url": "https://www.moi.gov.sa", "country": "SA", "currency": "SAR"},
    {"offence_code": "MOBILE_PHONE", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 500, "repeat_amount_inr": 900, "section_ref": "Moroor — SAR 500-900 + possible impound", "source_url": "https://www.moi.gov.sa", "country": "SA", "currency": "SAR"},
    {"offence_code": "DRUNK_DRIVING", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 0, "repeat_amount_inr": 0, "section_ref": "Saudi law — ZERO TOLERANCE. Criminal charge: imprisonment, lashing (historically), deportation for expats. No fine — criminal prosecution.", "source_url": "https://www.moi.gov.sa", "country": "SA", "currency": "SAR"},
    {"offence_code": "NO_LICENSE", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 500, "repeat_amount_inr": 900, "section_ref": "Moroor — SAR 500-900 + vehicle impound", "source_url": "https://www.moi.gov.sa", "country": "SA", "currency": "SAR"},
    {"offence_code": "NO_INSURANCE", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 500, "repeat_amount_inr": 900, "section_ref": "Moroor — SAR 500-900; insurance is mandatory", "source_url": "https://www.moi.gov.sa", "country": "SA", "currency": "SAR"},
    {"offence_code": "SECTION_184", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 5000, "repeat_amount_inr": 10000, "section_ref": "Moroor — SAR 5,000-10,000 + 90 days impound + potential jail", "source_url": "https://www.moi.gov.sa", "country": "SA", "currency": "SAR"},
    {"offence_code": "WRONG_WAY", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 3000, "repeat_amount_inr": 6000, "section_ref": "Moroor — SAR 3,000-6,000 + vehicle impound", "source_url": "https://www.moi.gov.sa", "country": "SA", "currency": "SAR"},
    {"offence_code": "NO_PARKING", "vehicle_class": "ALL", "state": "ALL", "amount_inr": 100, "repeat_amount_inr": 300, "section_ref": "Moroor — SAR 100-300", "source_url": "https://www.moi.gov.sa", "country": "SA", "currency": "SAR"},
]


if __name__ == "__main__":
    print("=" * 60)
    print("DriveLegal — International Traffic Fine Data Population")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)

    all_datasets = [
        ("UAE/Dubai", UAE_FINES),
        ("UK", UK_FINES),
        ("USA", USA_FINES),
        ("Singapore", SINGAPORE_FINES),
        ("Saudi Arabia", SAUDI_FINES),
    ]

    total_inserted = 0
    total_skipped = 0

    for name, dataset in all_datasets:
        print(f"\n[{name}] Inserting {len(dataset)} fines...")
        inserted, skipped = insert_fines(conn, dataset)
        print(f"  -> Inserted: {inserted}, Skipped: {skipped}")
        total_inserted += inserted
        total_skipped += skipped

    # Summary
    cursor = conn.cursor()
    cursor.execute("SELECT country, COUNT(*) FROM fines GROUP BY country ORDER BY country")
    print(f"\n{'=' * 60}")
    print("DATABASE SUMMARY BY COUNTRY:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} entries")

    cursor.execute("SELECT COUNT(*) FROM fines")
    print(f"\nTOTAL: {cursor.fetchone()[0]} fine entries")
    print(f"Inserted this run: {total_inserted}, Skipped: {total_skipped}")
    print(f"{'=' * 60}")

    conn.close()
