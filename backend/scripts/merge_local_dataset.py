import json
import os
import sqlite3
import csv
from datetime import datetime

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "data")
NEW_DATASET_DIR = os.path.join(DATA_DIR, "drivelegal_dataset")
RULES_JSON_PATH = os.path.join(DATA_DIR, "rules.json")
FINES_DB_PATH = os.path.join(DATA_DIR, "fines.db")

def merge_rules():
    print("Merging rules...")
    violations_path = os.path.join(NEW_DATASET_DIR, "json", "violations_db.json")
    faq_path = os.path.join(NEW_DATASET_DIR, "json", "faq_chatbot.json")
    
    if not os.path.exists(violations_path):
        print(f"Error: {violations_path} not found.")
        return

    with open(violations_path, 'r', encoding='utf-8') as f:
        new_data = json.load(f)
    
    try:
        with open(RULES_JSON_PATH, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
    except Exception:
        existing_data = {"rules": []}

    existing_ids = {r['rule_id'] for r in existing_data['rules']}
    added_count = 0

    # Process violations
    for v in new_data.get('violations', []):
        rule_id = v['id']
        if rule_id not in existing_ids:
            new_rule = {
                "rule_id": rule_id,
                "section": v.get('section', 'N/A'),
                "act": "Motor Vehicles (Amendment) Act 2019",
                "title": v.get('violation_name', 'N/A'),
                "description": v.get('description', 'N/A'),
                "applies_to": ["ALL"],
                "vehicle_classes": v.get('vehicle_types', ["ALL"]),
                "state_overrides": [],
                "related_offence_codes": [tag.upper().replace(" ", "_") for tag in v.get('tags', [])],
                "penalty_ref": f"{rule_id}_FINE"
            }
            existing_data['rules'].append(new_rule)
            existing_ids.add(rule_id)
            added_count += 1

    # Process FAQs
    if os.path.exists(faq_path):
        with open(faq_path, 'r', encoding='utf-8') as f:
            faq_list = json.load(f)
        for faq in faq_list:
            faq_id = f"FAQ_{faq['id']}"
            if faq_id not in existing_ids:
                new_rule = {
                    "rule_id": faq_id,
                    "section": "FAQ",
                    "act": "FAQ Database",
                    "title": faq['question'],
                    "description": faq['answer'],
                    "applies_to": ["ALL"],
                    "vehicle_classes": ["ALL"],
                    "state_overrides": [],
                    "related_offence_codes": [],
                    "penalty_ref": "DATASET_INFO"
                }
                existing_data['rules'].append(new_rule)
                existing_ids.add(faq_id)
                added_count += 1

    with open(RULES_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, indent=2)
    
    print(f"Successfully added {added_count} rules/FAQs to rules.json")

def merge_fines():
    print("Merging fines into SQLite...")
    flat_csv = os.path.join(NEW_DATASET_DIR, "csv", "violations_flat.csv")
    if not os.path.exists(flat_csv):
        print(f"Error: {flat_csv} not found.")
        return

    conn = sqlite3.connect(FINES_DB_PATH)
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fines'")
    if not cursor.fetchone():
        print("Fines table doesn't exist. Creating...")
        schema_path = os.path.join(BASE_DIR, "modules", "fines", "schema.sql")
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                conn.executescript(f.read())
        else:
            # Fallback schema
            conn.execute("""
                CREATE TABLE fines (
                    offence_code TEXT,
                    vehicle_class TEXT,
                    state TEXT,
                    amount_inr INTEGER,
                    repeat_amount_inr INTEGER,
                    section_ref TEXT,
                    source_url TEXT,
                    fetched_at TEXT,
                    version_hash TEXT PRIMARY KEY
                )
            """)

    with open(flat_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        fetched_at = datetime.now().isoformat()
        
        for row in reader:
            # Map violations_flat.csv to fines table
            section = row['section']
            # Create a simple offence code if not present
            offence_code = section.replace(" ", "_").replace("(", "").replace(")", "").upper()
            vehicle_class = row['vehicle_type'].upper()
            if vehicle_class == "ALL": vehicle_class = "ALL"
            
            amount = row['fine_amount_inr']
            if amount.lower() in ['base', 'per_tonne', 'per_person', 'guardian']:
                # Handle special cases if needed, for now just skip or set to 0
                amount = 0
            else:
                try:
                    amount = int(amount)
                except ValueError:
                    amount = 0

            # Generate version hash
            import hashlib
            payload = f"{offence_code}{vehicle_class}ALL{amount}"
            v_hash = hashlib.sha256(payload.encode()).hexdigest()

            try:
                conn.execute("""
                    INSERT INTO fines (
                        offence_code, vehicle_class, state, amount_inr, 
                        section_ref, source_url, fetched_at, version_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(version_hash) DO NOTHING
                """, (offence_code, vehicle_class, 'ALL', amount, section, 'https://morth.nic.in', fetched_at, v_hash))
                count += 1
            except sqlite3.Error as e:
                print(f"Error inserting row: {e}")

    conn.commit()
    conn.close()
    print(f"Successfully merged {count} fine records into fines.db")

if __name__ == "__main__":
    merge_rules()
    merge_fines()
    # Clear vector db
    vector_db_path = os.path.join(DATA_DIR, "vector_db")
    if os.path.exists(vector_db_path):
        import shutil
        try:
            shutil.rmtree(vector_db_path)
            print("Vector DB cleared for re-indexing.")
        except Exception as e:
            print(f"Could not clear vector DB: {e}")
