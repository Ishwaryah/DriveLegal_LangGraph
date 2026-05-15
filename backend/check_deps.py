import importlib.util
import sys

dependencies = [
    "fastapi", "uvicorn", "spacy", "transformers", "playwright", 
    "shapely", "aiosqlite", "chromadb", "rank_bm25", "dotenv", 
    "sentence_transformers", "groq"
]

missing = []
for dep in dependencies:
    name = dep if dep != "dotenv" else "python-dotenv"
    # Mapping package names to import names if they differ
    import_name = {
        "python-dotenv": "dotenv",
        "rank-bm25": "rank_bm25",
        "sentence-transformers": "sentence_transformers"
    }.get(dep, dep)
    
    if importlib.util.find_spec(import_name) is None:
        missing.append(dep)

if not missing:
    print("All dependencies are already installed.")
else:
    print(f"Missing dependencies: {', '.join(missing)}")
