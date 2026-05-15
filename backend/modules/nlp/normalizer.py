import string
import json
import os

def normalize(text: str) -> str:
    """
    Lowercase, strip punctuation, expand common traffic abbreviations.
    Handle Hindi-English and Tamil-English code-mix using a hardcoded dict.
    """
    if not text:
        return ""

    # Lowercase and strip
    text = text.lower().strip()
    
    # Remove punctuation
    text = text.translate(str.maketrans('', '', string.punctuation))

    # Abbreviation map
    abbrev_map = {
        "hl": "headlight",
        "ow": "one way",
        "mv": "motor vehicles",
        "rto": "regional transport office"
    }
    
    # <<DATASET: expand abbreviation map from data/abbrev_map.json when available>>
    # Try to load external abbrev map if exists
    # Using relative path or absolute path based on project structure
    # Standardizing to project root relative path
    try:
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
        abbrev_file = os.path.join(data_dir, "abbrev_map.json")
        if os.path.exists(abbrev_file):
            with open(abbrev_file, 'r') as f:
                extra_abbrevs = json.load(f)
                abbrev_map.update(extra_abbrevs)
    except Exception:
        pass

    # Basic Transliteration Map (Hindi/Tamil to English)
    translit_map = {
        "challan": "fine",
        "jurmana": "fine",
        "gaadi": "vehicle",
        "vandi": "vehicle",
        "daaru": "alcohol",
        "sarayam": "alcohol",
        "pulis": "police"
    }

    words = text.split()
    normalized_words = []
    
    for word in words:
        # Transliterate first
        word = translit_map.get(word, word)
        # Expand abbreviation
        word = abbrev_map.get(word, word)
        normalized_words.append(word)
        
    return " ".join(normalized_words)
