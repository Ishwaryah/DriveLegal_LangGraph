import os
import sys
import time

# Mock some paths
DATA_DIR = os.path.join(os.getcwd(), "data")
RULES_JSON = os.path.join(DATA_DIR, "rules.json")
VECTOR_DB = os.path.join(DATA_DIR, "vector_db_debug")

print("Importing HybridSearch...")
from modules.nlp.hybrid_search import HybridSearch
print("HybridSearch imported.")

print(f"Initializing HybridSearch with {RULES_JSON} and {VECTOR_DB}...")
start = time.time()
try:
    hs = HybridSearch(RULES_JSON, VECTOR_DB)
    print(f"HybridSearch initialized in {time.time() - start:.2f} seconds.")
except Exception as e:
    print(f"Initialization failed: {e}")
