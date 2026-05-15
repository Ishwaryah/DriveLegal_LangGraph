import os
import json
import shutil
import requests
import csv

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "data")
RULES_JSON_PATH = os.path.join(DATA_DIR, "rules.json")
VECTOR_DB_PATH = os.path.join(DATA_DIR, "vector_db")
KAGGLE_CSV_PATH = os.path.join(DATA_DIR, "indian_traffic_e_challan.csv")

def fetch_hf_rows_api(dataset, config="default", split="train", limit=100):
    url = f"https://datasets-server.huggingface.co/rows?dataset={dataset}&config={config}&split={split}&offset=0&length={limit}"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return r.json().get('rows', [])
    except Exception as e:
        print(f"  Error fetching {dataset} via API: {e}")
        return []

def fetch_hf_raw_jsonl(repo_id, filename, limit=100):
    url = f"https://huggingface.co/datasets/{repo_id}/resolve/main/{filename}"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        lines = r.text.strip().split('\n')
        rows = []
        for line in lines[:limit]:
            if not line.strip(): continue
            data = json.loads(line)
            rows.append({"row": data})
        return rows
    except Exception as e:
        print(f"  Error fetching {repo_id} raw file: {e}")
        return []

def train_datasets():
    print("Starting dataset training...")
    new_rules = []
    
    # 1. Pravincoder/Indian_traffic_law_QA
    print("Fetching rows from Pravincoder/Indian_traffic_law_QA...")
    rows_1 = fetch_hf_rows_api("Pravincoder/Indian_traffic_law_QA", limit=100)
    print(f"  Received {len(rows_1)} rows.")
    for i, row_wrapper in enumerate(rows_1):
        item = row_wrapper.get('row', {})
        question = item.get('question') or item.get('query') or item.get('text', '')
        answer = item.get('answer') or item.get('response') or item.get('label', '')
        if question and answer:
            new_rules.append({
                "rule_id": f"DS_Indian_traffic_law_QA_{i}",
                "section": "QA Dataset",
                "act": "Pravincoder/Indian_traffic_law_QA",
                "title": str(question)[:100],
                "description": str(answer),
                "applies_to": ["ALL"],
                "vehicle_classes": ["ALL"],
                "state_overrides": [],
                "related_offence_codes": [],
                "penalty_ref": "DATASET_INFO"
            })

    # 2. DriveQA/DriveQA_Dataset
    print("Fetching rows from DriveQA/DriveQA_Dataset...")
    rows_2 = fetch_hf_raw_jsonl("DriveQA/DriveQA_Dataset", "DriveQA_T.jsonl", limit=100)
    print(f"  Received {len(rows_2)} rows.")
    for i, row_wrapper in enumerate(rows_2):
        item = row_wrapper.get('row', {})
        question = item.get('question', '')
        answer = item.get('answer', '')
        if question and answer:
            new_rules.append({
                "rule_id": f"DS_DriveQA_{i}",
                "section": "QA Dataset",
                "act": "DriveQA/DriveQA_Dataset",
                "title": str(question)[:100],
                "description": str(answer),
                "applies_to": ["ALL"],
                "vehicle_classes": ["ALL"],
                "state_overrides": [],
                "related_offence_codes": [],
                "penalty_ref": "DATASET_INFO"
            })

    # 3. Kaggle Dataset: bhanageviraj/indian-traffic-e-challan-daily-dataset-20152026
    print("Fetching rows from Kaggle Dataset (bhanageviraj/indian-traffic-e-challan-daily-dataset-20152026)...")
    if os.path.exists(KAGGLE_CSV_PATH):
        try:
            with open(KAGGLE_CSV_PATH, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    if count >= 100: break
                    date_val = row.get('date', '')
                    total = row.get('totalChallan', '')
                    if date_val and total:
                        new_rules.append({
                            "rule_id": f"DS_Kaggle_Challan_{count}",
                            "section": "Challan Dataset",
                            "act": "bhanageviraj/indian-traffic-e-challan",
                            "title": f"Challan Summary for {date_val}",
                            "description": f"Total Challans: {total}, Disposed: {row.get('disposedChallan', '0')}, Total Amount: {row.get('totalAmount', '0')}",
                            "applies_to": ["ALL"],
                            "vehicle_classes": ["ALL"],
                            "state_overrides": [],
                            "related_offence_codes": [],
                            "penalty_ref": "DATASET_INFO"
                        })
                        count += 1
            print(f"  Processed {count} rows from Kaggle CSV.")
        except Exception as e:
            print(f"  Error reading Kaggle CSV: {e}")
    else:
        print(f"  Warning: Kaggle CSV not found at {KAGGLE_CSV_PATH}.")
        print("  Please download 'bhanageviraj/indian-traffic-e-challan-daily-dataset-20152026' from Kaggle and save as indian_traffic_e_challan.csv in backend/data/")
        # Adding a dummy rule to show it's integrated
        new_rules.append({
            "rule_id": "DS_Kaggle_Challan_DUMMY",
            "section": "Challan Dataset",
            "act": "bhanageviraj/indian-traffic-e-challan",
            "title": "Kaggle Dataset Placeholder",
            "description": "Please download the actual CSV from Kaggle.",
            "applies_to": ["ALL"],
            "vehicle_classes": ["ALL"],
            "state_overrides": [],
            "related_offence_codes": [],
            "penalty_ref": "DATASET_INFO"
        })
        print("  Added dummy Kaggle row for verification.")

    if new_rules:
        # Load existing
        try:
            with open(RULES_JSON_PATH, 'r') as f:
                data = json.load(f)
        except Exception:
            data = {"rules": []}
        
        # Add new
        existing_ids = {r['rule_id'] for r in data['rules']}
        added_count = 0
        for nr in new_rules:
            if nr['rule_id'] not in existing_ids:
                data['rules'].append(nr)
                added_count += 1
        
        # Save
        with open(RULES_JSON_PATH, 'w') as f:
            json.dump(data, f, indent=2)
            
        print(f"Success! Added {added_count} new entries to rules database.")
        
        # Clear Vector DB for re-indexing
        if os.path.exists(VECTOR_DB_PATH):
            try:
                shutil.rmtree(VECTOR_DB_PATH)
                print("Vector DB cleared. It will be rebuilt on the next query.")
            except Exception as e:
                print(f"Note: Vector DB could not be cleared ({e}). Please restart the backend.")
    else:
        print("No new data found to add.")

if __name__ == "__main__":
    train_datasets()

