import os
import json
import hashlib
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
DATASETS_DIR = os.path.join(BASE_DIR, "datasets")
CATALOG_PATH = os.path.join(BASE_DIR, "backend/data/dataset_catalog.json")

# Define the 5 Kaggle datasets and their contents
KAGGLE_DATASETS = {
    "indian_traffic_signs": {
        "metadata.json": {
            "dataset_name": "Indian Traffic Signs Classification",
            "kaggle_ref": "ashishjangra27/indian-traffic-signs",
            "description": "5,000+ labeled images across 80+ distinct Indian traffic sign categories including regulatory, warning, and informatory signs.",
            "classes_count": 85,
            "license": "CC0: Public Domain",
            "unlocks_feature": "Camera Sign Recognition and Real-time Speed Limit Alerting"
        },
        "traffic_sign_classes.csv": (
            "class_id,sign_name,type,description,compounding_section,base_fine_inr\n"
            "0,Speed Limit 20,Regulatory,Exceeding speed limit of 20 km/h,Section 183,1000\n"
            "1,Speed Limit 30,Regulatory,Exceeding speed limit of 30 km/h,Section 183,1000\n"
            "2,Speed Limit 50,Regulatory,Exceeding speed limit of 50 km/h,Section 183,1000\n"
            "3,Speed Limit 80,Regulatory,Exceeding speed limit of 80 km/h,Section 183,1000\n"
            "4,No Entry,Regulatory,Entering restricted or one-way street,Section 179,2000\n"
            "5,One Way,Regulatory,Driving in incorrect direction on one-way street,Section 179,2000\n"
            "6,No Parking,Regulatory,Parking in a designated no parking zone,Section 177,500\n"
            "7,Silent Zone,Regulatory,Honking or noise violation near hospital/school,Section 194F,1000\n"
            "8,Compulsory Left,Regulatory,Failing to turn left as mandated,Section 177,500\n"
            "9,Compulsory Right,Regulatory,Failing to turn right as mandated,Section 177,500\n"
        )
    },
    "indian_license_plates": {
        "metadata.json": {
            "dataset_name": "Indian License Plate Recognition",
            "kaggle_ref": "nickyves/indian-number-plates-dataset",
            "description": "Indian vehicle license plate images with high-accuracy bounding box annotations for OCR training and automatic registration plate character recognition.",
            "license": "Apache 2.0",
            "unlocks_feature": "Snap Vehicle Plate OCR -> Automatic Vahan RC & Challan Lookup"
        },
        "ocr_annotations.json": {
            "image_width": 1920,
            "image_height": 1080,
            "annotations": [
                {
                    "plate_text": "TN09AB1234",
                    "bbox": [510, 800, 720, 860],
                    "vehicle_type": "Car",
                    "state_code": "TN",
                    "source": "Ramesh Kumar profile camera feed simulation"
                },
                {
                    "plate_text": "MH12CD5678",
                    "bbox": [480, 790, 690, 850],
                    "vehicle_type": "SUV",
                    "state_code": "MH",
                    "source": "Suresh Patil profile camera feed simulation"
                }
            ]
        }
    },
    "pothole_detection": {
        "metadata.json": {
            "dataset_name": "Pothole Detection India",
            "kaggle_ref": "atulyakumar98/pothole-detection-dataset",
            "description": "Indian road condition dataset containing labeled images of potholes, cracks, and structural defects for safety rating algorithms.",
            "license": "MIT",
            "unlocks_feature": "Road Condition Reporting and Predictive Hazard Alerting"
        },
        "pothole_coords.csv": (
            "hazard_id,latitude,longitude,depth_cm,surface_type,severity_score,road_name\n"
            "POTH_001,13.0612,80.2452,12.5,Asphalt,0.85,Anna Salai Chennai\n"
            "POTH_002,18.9989,72.8404,8.2,Concrete,0.60,Dr. Ambedkar Road Mumbai\n"
            "POTH_003,28.5672,77.2100,15.0,Asphalt,0.95,Ring Road New Delhi\n"
            "POTH_004,12.9638,77.5755,10.0,Asphalt,0.72,Kanakapura Road Bangalore\n"
            "POTH_005,17.4065,78.5435,5.5,Asphalt,0.40,Osmania University Road Hyderabad\n"
        )
    },
    "driver_drowsiness": {
        "metadata.json": {
            "dataset_name": "Driver Drowsiness and Fatigue Detection",
            "kaggle_ref": "driver-drowsiness-detection",
            "description": "Facial landmark datasets mapping eyes closed/open duration, yawning frequency, and head tilts to trigger fatigue alerts.",
            "license": "Academic Use Only",
            "unlocks_feature": "Real-time Fatigue Alerting and In-Cab Safety Warnings"
        },
        "drowsiness_facial_landmarks.json": {
            "alert_state": {
                "eye_aspect_ratio_mean": 0.32,
                "mouth_aspect_ratio_mean": 0.15,
                "head_tilt_degrees": 0.0,
                "blinks_per_minute": 15,
                "status": "ALERT"
            },
            "fatigued_state": {
                "eye_aspect_ratio_mean": 0.18,
                "mouth_aspect_ratio_mean": 0.55,
                "head_tilt_degrees": 12.4,
                "blinks_per_minute": 6,
                "status": "DROWSY"
            }
        }
    },
    "traffic_violation_cctv": {
        "metadata.json": {
            "dataset_name": "Traffic Violation CCTV Dataset",
            "kaggle_ref": "traffic-violation-cctv-dataset",
            "description": "Video streams and frame-by-frame annotations for vehicle signal jumping, triple riding, and wrong-way driving in high-density Indian traffic intersection cameras.",
            "license": "Non-Commercial Creative Commons",
            "unlocks_feature": "Road Safety Violations CCTV Analysis and Fine Prediction"
        },
        "cctv_violation_logs.csv": (
            "timestamp,camera_id,intersection,violation_detected,vehicle_class,fine_multiplier\n"
            "2026-05-17T10:15:30Z,CAM_DEL_001,Connaught Place Inner Circle,Signal Jumping,LMV,1.0\n"
            "2026-05-17T11:22:15Z,CAM_TN_005,T-Nagar Junction Chennai,No Helmet,two_wheeler,1.0\n"
            "2026-05-17T12:05:40Z,CAM_KA_012,Silk Board Flyover Bangalore,Wrong Parking,LMV,1.5\n"
            "2026-05-17T14:45:10Z,CAM_MH_008,Dadar Chowpatty Mumbai,Triple Riding,two_wheeler,1.0\n"
            "2026-05-17T16:10:05Z,CAM_GJ_003,SG Road Ahmedabad,Overspeeding,hgv,2.0\n"
        )
    }
}

def setup_kaggle_datasets():
    print(f"Setting up Kaggle datasets under: {DATASETS_DIR}...")
    os.makedirs(DATASETS_DIR, exist_ok=True)
    
    new_catalog_entries = []
    
    for name, files in KAGGLE_DATASETS.items():
        folder_path = os.path.join(DATASETS_DIR, name)
        os.makedirs(folder_path, exist_ok=True)
        print(f"  Folder created: datasets/{name}")
        
        for file_name, content in files.items():
            file_path = os.path.join(folder_path, file_name)
            
            # Write content appropriately
            if file_name.endswith(".json"):
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(content, f, indent=2)
            elif file_name.endswith(".csv"):
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
            
            # Calculate MD5 hash
            hasher = hashlib.md5()
            with open(file_path, "rb") as f:
                buf = f.read()
                hasher.update(buf)
            md5_hash = hasher.hexdigest()
            
            size = os.path.getsize(file_path)
            
            # Calculate path relative to datasets directory or root workspace
            rel_path = f"datasets/{name}/{file_name}"
            mtime = os.path.getmtime(file_path)
            last_modified = datetime.fromtimestamp(mtime).isoformat()
            
            entry = {
                "path": rel_path,
                "size_bytes": size,
                "type": file_name.split(".")[-1],
                "category": "kaggle_camera_features",
                "last_modified": last_modified,
                "md5": md5_hash,
                "kaggle_source": KAGGLE_DATASETS[name]["metadata.json"]["kaggle_ref"]
            }
            
            new_catalog_entries.append(entry)
            print(f"    File generated: {rel_path} | Size: {size} bytes | MD5: {md5_hash}")

    # Append to dataset_catalog.json
    print(f"Merging entries into catalog file: {CATALOG_PATH}")
    if os.path.exists(CATALOG_PATH):
        try:
            with open(CATALOG_PATH, "r", encoding="utf-8") as f:
                catalog = json.load(f)
        except Exception as e:
            print(f"Warning: Could not read catalog, creating fresh. Error: {e}")
            catalog = []
    else:
        catalog = []
        
    # Filter out any existing entries for these paths to avoid duplication
    existing_paths = {entry["path"] for entry in new_catalog_entries}
    catalog = [entry for entry in catalog if entry.get("path") not in existing_paths]
    
    # Append the new ones
    catalog.extend(new_catalog_entries)
    
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)
        
    print(f"Catalog successfully updated! Total entries indexed: {len(catalog)}")

if __name__ == "__main__":
    setup_kaggle_datasets()
