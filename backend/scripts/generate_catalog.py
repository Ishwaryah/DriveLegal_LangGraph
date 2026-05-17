import os
import json
from datetime import datetime

def generate_catalog():
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data"))
    catalog_path = os.path.join(data_dir, "dataset_catalog.json")
    
    catalog_entries = []
    total_files = 0
    total_size = 0
    
    # Supported file extensions and their mappings
    ext_mapping = {
        ".json": "json",
        ".csv": "csv",
        ".geojson": "geojson",
        ".pdf": "pdf",
        ".db": "db",
        ".sqlite": "db"
    }

    for root, dirs, files in os.walk(data_dir):
        # Skip pycache or vector db internal files if they are not standard dataset types
        if "__pycache__" in root or "vector_db" in root:
            continue
            
        for file in files:
            # Let's skip catalog itself or hidden files
            if file == "dataset_catalog.json" or file.startswith("."):
                continue
                
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, data_dir).replace("\\", "/")
            
            # Skip if it is not a file
            if not os.path.isfile(full_path):
                continue
                
            size = os.path.getsize(full_path)
            ext = os.path.splitext(file)[1].lower()
            
            # Determine type
            file_type = ext_mapping.get(ext, ext.lstrip("."))
            if not file_type:
                file_type = "unknown"
                
            # Determine category
            parts = rel_path.split("/")
            if len(parts) > 1:
                category = parts[0]
            else:
                category = "core"
                
            # Determine last modified time in ISO format
            mtime = os.path.getmtime(full_path)
            last_modified = datetime.fromtimestamp(mtime).isoformat()
            
            entry = {
                "path": rel_path,
                "size_bytes": size,
                "type": file_type,
                "category": category,
                "last_modified": last_modified
            }
            
            catalog_entries.append(entry)
            total_files += 1
            total_size += size

    # Write catalog entries to dataset_catalog.json
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(catalog_entries, f, indent=2)
        
    print(f"Dataset Catalog Generated Successfully!")
    print(f"Total Files Indexed: {total_files}")
    print(f"Total Size: {total_size} bytes ({total_size / (1024*1024):.2f} MB)")
    print(f"Catalog saved to: {catalog_path}")

if __name__ == "__main__":
    generate_catalog()
