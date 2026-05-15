#!/usr/bin/env python3
"""
DriveLegal Bulk Insert
-----------------------
1. Reads all *_cleaned.json files from data/processed/ and inserts into fines.db
   (INSERT OR REPLACE keyed on country + state_province + violation_code + vehicle_type).
2. Creates legal_sections and violation_translations tables.
3. Seeds multilingual violation translations (hi / ta / te / kn).
4. Builds FTS5 virtual tables for fast chatbot search.
5. Prints DB stats and a timed sample query.
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
DB_PATH = DATA_DIR / "fines.db"


# ── Helpers ────────────────────────────────────────────────────────────────────

def slugify(name: str) -> str:
    """'No Seatbelt' -> 'no_seatbelt' (max 64 chars)"""
    s = re.sub(r"[^a-z0-9]+", "_", name.lower().strip()).strip("_")
    return s[:64]


# ── Schema ─────────────────────────────────────────────────────────────────────

def ensure_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    # fines — created by migrate_db.py; recreate if absent
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fines (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            country              TEXT NOT NULL DEFAULT 'IN',
            state_province       TEXT,
            violation_code       TEXT NOT NULL,
            violation_name       TEXT NOT NULL,
            vehicle_type         TEXT NOT NULL DEFAULT 'all',
            min_fine_local       INTEGER,
            max_fine_local       INTEGER,
            currency             TEXT NOT NULL DEFAULT 'INR',
            mv_act_section       TEXT,
            compounding_eligible BOOLEAN DEFAULT 0,
            compounding_fee      INTEGER,
            imprisonment_days    INTEGER DEFAULT 0,
            notes                TEXT
        )
    """)

    # Unique expression-index so INSERT OR REPLACE works even when state_province IS NULL.
    # COALESCE maps NULL -> '' so two NULLs are treated as the same bucket.
    try:
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_fine
            ON fines(country, COALESCE(state_province,''), violation_code, vehicle_type)
        """)
    except sqlite3.OperationalError as exc:
        print(f"  WARNING: unique index not created ({exc}). "
              "Deduplication will be Python-side only.")

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_geo_lookup
        ON fines(country, state_province, violation_code, vehicle_type)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_country_violation
        ON fines(country, violation_code)
    """)

    # Legal sections (for chatbot citations)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS legal_sections (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            country       TEXT NOT NULL,
            act_name      TEXT NOT NULL,
            section_id    TEXT NOT NULL,
            section_title TEXT,
            section_text  TEXT NOT NULL,
            language      TEXT NOT NULL DEFAULT 'en',
            source_file   TEXT,
            UNIQUE(country, section_id, language)
        )
    """)

    # Multilingual violation names
    cur.execute("""
        CREATE TABLE IF NOT EXISTS violation_translations (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            violation_code TEXT NOT NULL,
            language       TEXT NOT NULL,
            violation_name TEXT NOT NULL,
            description    TEXT,
            UNIQUE(violation_code, language)
        )
    """)

    conn.commit()


# ── Fines insertion ────────────────────────────────────────────────────────────

def _to_int(val) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def insert_fines_from_json(conn: sqlite3.Connection, json_path: Path) -> int:
    try:
        with open(json_path, encoding="utf-8") as fh:
            records = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"  WARNING  {json_path.name}: {exc}")
        return 0

    if not isinstance(records, list) or not records:
        return 0

    # Only handle CSV-derived records (have 'violation_name' key).
    # MV Act section records go to legal_sections, not fines.
    if "violation_name" not in records[0]:
        return 0

    cur = conn.cursor()
    inserted = 0

    for rec in records:
        vname = (rec.get("violation_name") or "").strip()
        if not vname:
            continue

        # Prefer explicit offence_code; fall back to a slug derived from the name
        violation_code = (rec.get("offence_code") or "").strip() or slugify(vname)

        country      = (rec.get("country") or "IN").strip().upper()
        state        = (rec.get("state_province") or None)
        vehicle_type = (rec.get("vehicle_type") or "all").strip() or "all"
        min_fine     = _to_int(rec.get("min_fine") or rec.get("fine_amount"))
        max_fine     = _to_int(rec.get("max_fine") or rec.get("fine_amount"))
        currency     = (rec.get("currency") or "INR").strip()
        section      = rec.get("section_reference") or None

        cur.execute("""
            INSERT OR REPLACE INTO fines (
                country, state_province, violation_code, violation_name,
                vehicle_type, min_fine_local, max_fine_local, currency,
                mv_act_section, compounding_eligible, compounding_fee,
                imprisonment_days, notes
            ) VALUES (?,?,?,?,?,?,?,?,?,0,NULL,0,NULL)
        """, (country, state, violation_code, vname,
              vehicle_type, min_fine, max_fine, currency, section))
        inserted += 1

    conn.commit()
    return inserted


# ── Legal sections ─────────────────────────────────────────────────────────────

_SECTION_FILES = [
    ("mv_act_sections.json",       "en", "Motor Vehicles (Amendment) Act 2019"),
    ("mv_act_sections_hindi.json", "hi", "मोटर वाहन (संशोधन) अधिनियम 2019"),
]


def insert_legal_sections(conn: sqlite3.Connection) -> int:
    cur = conn.cursor()
    total = 0

    for filename, default_lang, act_name in _SECTION_FILES:
        path = PROCESSED_DIR / filename
        if not path.exists():
            print(f"  NOTE  {filename} not found "
                  "(run ingest_data.py on PDFs to generate it)")
            continue

        try:
            with open(path, encoding="utf-8") as fh:
                sections = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  WARNING  {filename}: {exc}")
            continue

        for sec in sections:
            section_id    = (sec.get("section_id") or "").strip()
            section_title = (sec.get("section_title") or "").strip() or None
            section_text  = (sec.get("section_text") or "").strip()
            language      = sec.get("language") or default_lang
            source_file   = sec.get("source_file") or filename

            if not section_id or not section_text:
                continue

            cur.execute("""
                INSERT OR REPLACE INTO legal_sections
                    (country, act_name, section_id, section_title,
                     section_text, language, source_file)
                VALUES (?,?,?,?,?,?,?)
            """, ("IN", act_name, section_id, section_title,
                  section_text, language, source_file))
            total += 1

    conn.commit()
    return total


# ── Violation translations ─────────────────────────────────────────────────────

# fmt: off
_TRANSLATIONS: list[tuple[str, str, str]] = [
    # ── Hindi (hi) ──────────────────────────────────────────────────────────────
    ("drunk_driving",     "hi", "नशे में गाड़ी चलाना"),
    ("overspeeding",      "hi", "तेज़ गति से वाहन चलाना"),
    ("no_helmet",         "hi", "हेलमेट न पहनना"),
    ("no_seatbelt",       "hi", "सीट बेल्ट न पहनना"),
    ("using_phone",       "hi", "गाड़ी चलाते समय फोन का उपयोग"),
    ("no_insurance",      "hi", "बीमा न होना"),
    ("no_rc",             "hi", "पंजीकरण प्रमाण पत्र न होना"),
    ("signal_jumping",    "hi", "सिग्नल तोड़ना"),
    ("dangerous_driving", "hi", "खतरनाक ड्राइविंग"),
    ("no_license",        "hi", "लाइसेंस न होना"),
    ("juvenile_driving",  "hi", "नाबालिग द्वारा वाहन चलाना"),
    # ── Tamil (ta) ──────────────────────────────────────────────────────────────
    ("drunk_driving",  "ta", "குடிபோதையில் வாகனம் ஓட்டுதல்"),
    ("no_helmet",      "ta", "தலைக்கவசம் அணியாமல் இருத்தல்"),
    ("overspeeding",   "ta", "அதிவேக ஓட்டுதல்"),
    ("no_seatbelt",    "ta", "சீட் பெல்ட் அணியாமல் இருத்தல்"),
    ("using_phone",    "ta", "வாகனம் ஓட்டும்போது தொலைபேசி பயன்படுத்துதல்"),
    ("signal_jumping", "ta", "சிக்னல் மீறல்"),
    ("no_license",     "ta", "உரிமம் இல்லாமல் வாகனம் ஓட்டுதல்"),
    ("no_insurance",   "ta", "காப்பீடு இல்லாமல் வாகனம் ஓட்டுதல்"),
    # ── Telugu (te) ─────────────────────────────────────────────────────────────
    ("drunk_driving",  "te", "మత్తులో వాహనం నడపడం"),
    ("no_helmet",      "te", "హెల్మెట్ ధరించకపోవడం"),
    ("overspeeding",   "te", "అతివేగంగా వాహనం నడపడం"),
    ("no_seatbelt",    "te", "సీట్ బెల్ట్ ధరించకపోవడం"),
    ("signal_jumping", "te", "సిగ్నల్ దాటడం"),
    ("no_license",     "te", "లైసెన్స్ లేకుండా వాహనం నడపడం"),
    # ── Kannada (kn) ────────────────────────────────────────────────────────────
    ("drunk_driving",  "kn", "ಮಾದಕ ಸ್ಥಿತಿಯಲ್ಲಿ ವಾಹನ ಚಲಾಯಿಸುವುದು"),
    ("no_helmet",      "kn", "ಹೆಲ್ಮೆಟ್ ಧರಿಸದಿರುವುದು"),
    ("overspeeding",   "kn", "ಅತಿ ವೇಗದಲ್ಲಿ ವಾಹನ ಚಲಾಯಿಸುವುದು"),
    ("signal_jumping", "kn", "ಸಿಗ್ನಲ್ ಉಲ್ಲಂಘನೆ"),
]
# fmt: on


def seed_translations(conn: sqlite3.Connection) -> int:
    cur = conn.cursor()
    for code, lang, name in _TRANSLATIONS:
        cur.execute("""
            INSERT OR REPLACE INTO violation_translations
                (violation_code, language, violation_name)
            VALUES (?,?,?)
        """, (code, lang, name))
    conn.commit()
    return len(_TRANSLATIONS)


# ── FTS5 indexes ───────────────────────────────────────────────────────────────

def build_fts_indexes(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    cur.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS fines_fts
        USING fts5(
            violation_code, violation_name, notes,
            mv_act_section, country, state_province,
            content='fines', content_rowid='id'
        )
    """)
    # Full rebuild so the index reflects all rows currently in fines
    cur.execute("INSERT INTO fines_fts(fines_fts) VALUES('rebuild')")

    cur.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS sections_fts
        USING fts5(
            section_id, section_title, section_text, language,
            content='legal_sections', content_rowid='id'
        )
    """)
    cur.execute("INSERT INTO sections_fts(sections_fts) VALUES('rebuild')")

    conn.commit()


# ── Stats & sample query ───────────────────────────────────────────────────────

def print_stats(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    print()
    print("=" * 60)
    print("DB STATS")
    print("=" * 60)

    for table in ("fines", "legal_sections", "violation_translations"):
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"  {table:<32} {cur.fetchone()[0]:>6} rows")

    for fts in ("fines_fts", "sections_fts"):
        try:
            cur.execute(f"SELECT COUNT(*) FROM {fts}")
            print(f"  {fts:<32} {cur.fetchone()[0]:>6} rows (FTS index)")
        except sqlite3.OperationalError:
            print(f"  {fts:<32}  — not built")

    cur.execute(
        "SELECT DISTINCT language FROM violation_translations ORDER BY language"
    )
    langs = [r[0] for r in cur.fetchall()]
    print(f"\n  Languages in violation_translations: {', '.join(langs)}")

    # Sample search — should be <10 ms
    print()
    print("  Sample: fines_fts MATCH 'helmet'")
    t0 = time.perf_counter()
    cur.execute("""
        SELECT f.violation_code, f.violation_name, f.country, f.state_province
        FROM fines_fts
        JOIN fines f ON f.id = fines_fts.rowid
        WHERE fines_fts MATCH 'helmet'
        LIMIT 5
    """)
    rows = cur.fetchall()
    ms = (time.perf_counter() - t0) * 1000
    status = "OK (<10 ms)" if ms < 10 else "SLOW (>10 ms)"
    print(f"  -> {len(rows)} results in {ms:.2f} ms  [{status}]")
    for code, name, country, state in rows:
        state_str = state or "(national)"
        print(f"     {code:<28} {name:<35} {country}/{state_str}")

    print("=" * 60)


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("DriveLegal Bulk Insert")
    print(f"  DB       : {DB_PATH}")
    print(f"  Processed: {PROCESSED_DIR}")
    print("=" * 60)

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    # ── 1. Schema ────────────────────────────────────────────────────────────────
    print("\n[1/5] Ensuring schema ...")
    ensure_schema(conn)
    print("      Schema ready.")

    # ── 2. Fines from processed JSONs ────────────────────────────────────────────
    print("\n[2/5] Inserting fines from processed JSON files ...")
    json_files = sorted(PROCESSED_DIR.glob("*_cleaned.json"))
    if not json_files:
        print(f"      WARNING: no *_cleaned.json files found in {PROCESSED_DIR}")
    total_fines = 0
    for jf in json_files:
        n = insert_fines_from_json(conn, jf)
        print(f"      {jf.name:<55} {n:>5} rows")
        total_fines += n
    print(f"      Total fines inserted/replaced: {total_fines}")

    # ── 3. Legal sections (MV Act PDFs) ──────────────────────────────────────────
    print("\n[3/5] Inserting legal sections ...")
    n_sections = insert_legal_sections(conn)
    print(f"      {n_sections} section rows inserted/replaced.")

    # ── 4. Violation translations ─────────────────────────────────────────────────
    print("\n[4/5] Seeding violation translations ...")
    n_trans = seed_translations(conn)
    print(f"      {n_trans} translation rows inserted/replaced.")

    # ── 5. FTS5 indexes ───────────────────────────────────────────────────────────
    print("\n[5/5] Building FTS5 search indexes ...")
    build_fts_indexes(conn)
    print("      fines_fts and sections_fts rebuilt.")

    print_stats(conn)
    conn.close()


if __name__ == "__main__":
    main()
