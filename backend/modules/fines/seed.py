import csv
import sqlite3
import hashlib
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/fines.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")
SEED_CSV = os.path.join(os.path.dirname(__file__), "../../data/seed_fines.csv")

def generate_version_hash(offence_code, vehicle_class, state, amount_inr):
    payload = f"{offence_code}{vehicle_class}{state}{amount_inr}"
    return hashlib.sha256(payload.encode()).hexdigest()

def seed():
    if not os.path.exists(SEED_CSV):
        print(f"Seed file not found: {SEED_CSV}")
        return

    # Ensure DB and table exist
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH, 'r') as f:
        conn.executescript(f.read())

    with open(SEED_CSV, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        fetched_at = datetime.now().isoformat()
        
        for row in reader:
            v_hash = generate_version_hash(
                row['offence_code'], 
                row['vehicle_class'], 
                row['state'], 
                row['amount_inr']
            )
            
            try:
                conn.execute("""
                    INSERT INTO fines (
                        offence_code, vehicle_class, state, amount_inr, 
                        repeat_amount_inr, section_ref, source_url, 
                        fetched_at, version_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(version_hash) DO UPDATE SET
                        repeat_amount_inr=excluded.repeat_amount_inr,
                        section_ref=excluded.section_ref,
                        source_url=excluded.source_url,
                        fetched_at=excluded.fetched_at
                """, (
                    row['offence_code'], row['vehicle_class'], row['state'], 
                    row['amount_inr'], row['repeat_amount_inr'], row['section_ref'], 
                    row['source_url'], fetched_at, v_hash
                ))
                count += 1
            except sqlite3.Error as e:
                print(f"Error seeding row {row['offence_code']}: {e}")

    conn.commit()
    conn.close()
    print(f"Seeded {count} rows from seed_fines.csv")

if __name__ == "__main__":
    seed()
