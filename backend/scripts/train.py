import os
import sys
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from modules.nlp.hybrid_search import HybridSearch

def train():
    print("--- Starting Data Training/Indexing ---")
    
    data_path = "backend/data/rules.json"
    persist_dir = "backend/data/vector_db"
    
    # 1. Initialize HybridSearch
    # The __init__ calls _load_and_index automatically
    search = HybridSearch(data_path, persist_dir)
    
    # 2. Force Re-indexing in Chroma
    print(f"Current document count in vector DB: {search.collection.count()}")
    
    if search.embedding_function:
        print("Re-indexing vector database...")
        # Clear existing
        ids_to_delete = search.collection.get()["ids"]
        if ids_to_delete:
            search.collection.delete(ids=ids_to_delete)
        
        # Re-add
        ids = [doc["rule_id"] for doc in search.documents]
        metadatas = [{"section": doc["section"], "title": doc["title"]} for doc in search.documents]
        documents = [doc["description"] for doc in search.documents]
        
        search.collection.add(
            ids=ids,
            metadatas=metadatas,
            documents=documents
        )
        print(f"Successfully indexed {len(ids)} rules into vector DB.")
    else:
        print("Skipping vector re-index: Embedding function not available.")
    
    print("--- Training Complete ---")

if __name__ == "__main__":
    train()
