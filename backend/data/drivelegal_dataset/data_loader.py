"""
DriveLegal Data Loader & Challan Calculator
============================================
Feed this data into your existing chatbot/RAG pipeline.
Works offline - no API needed.

Usage:
    from data_loader import ChallanaCalculator, DriveLegalKB
    
    calc = ChallanaCalculator()
    result = calc.calculate("no helmet", "Tamil Nadu", "Two-Wheeler")
    print(result)
"""

import json
import csv
import os
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─────────────────────────────────────────────
# 1. LOAD ALL DATASETS
# ─────────────────────────────────────────────

def load_json(filename):
    path = os.path.join(BASE_DIR, "json", filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_csv(filename):
    path = os.path.join(BASE_DIR, "csv", filename)
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows

# Singleton data store
_violations_db = None
_state_fines = None
_geo_zones = None
_vehicle_cats = None
_faq_data = None
_violations_csv = None

def get_violations_db():
    global _violations_db
    if not _violations_db:
        _violations_db = load_json("violations_db.json")
    return _violations_db

def get_state_fines():
    global _state_fines
    if not _state_fines:
        _state_fines = load_json("state_wise_fines.json")
    return _state_fines

def get_geo_zones():
    global _geo_zones
    if not _geo_zones:
        _geo_zones = load_json("geo_fencing_zones.json")
    return _geo_zones

def get_vehicle_categories():
    global _vehicle_cats
    if not _vehicle_cats:
        _vehicle_cats = load_json("vehicle_categories.json")
    return _vehicle_cats

def get_faq():
    global _faq_data
    if not _faq_data:
        _faq_data = load_json("faq_chatbot.json")
    return _faq_data

def get_violations_csv():
    global _violations_csv
    if not _violations_csv:
        _violations_csv = load_csv("violations_flat.csv")
    return _violations_csv


# ─────────────────────────────────────────────
# 2. CHALLAN CALCULATOR
# ─────────────────────────────────────────────

class ChallanCalculator:
    """
    Core calculator for DriveLegal chatbot.
    Given a violation + state + vehicle type, returns exact fine.
    """

    def __init__(self):
        self.violations = get_violations_db()["violations"]
        self.state_fines = get_state_fines()["states"]
        self.geo_zones = get_geo_zones()

    def find_violation(self, query: str) -> list:
        """Fuzzy-match a user query to violations using tags."""
        query_lower = query.lower()
        matches = []
        for v in self.violations:
            tags = v.get("tags", [])
            name = v.get("violation_name", "").lower()
            desc = v.get("description", "").lower()
            score = 0
            for tag in tags:
                if tag in query_lower:
                    score += 2
            if any(word in name for word in query_lower.split()):
                score += 1
            if any(word in desc for word in query_lower.split()):
                score += 0.5
            if score > 0:
                matches.append((score, v))
        matches.sort(reverse=True, key=lambda x: x[0])
        return [m[1] for m in matches[:3]]  # top 3

    def get_state_override(self, violation_id: str, state: str, fine_key: str) -> Optional[int]:
        """Check if state has a specific override for this violation."""
        state_data = self.state_fines.get(state)
        if not state_data:
            return None
        overrides = state_data.get("overrides", {})
        if violation_id in overrides:
            return overrides[violation_id].get(fine_key)
        return None

    def calculate(
        self,
        violation_query: str,
        state: str = "National",
        vehicle_type: str = "LMV",
        offence_number: int = 1,
        zone_type: str = "urban_road"
    ) -> dict:
        """
        Main challan calculation function.
        
        Args:
            violation_query: Natural language description e.g. "no helmet", "drunk driving"
            state: State name e.g. "Tamil Nadu", "Delhi"
            vehicle_type: "LMV", "Two-Wheeler", "HGV", etc.
            offence_number: 1 for first offence, 2 for subsequent
            zone_type: "urban_road", "school_zone", "national_highway", etc.
        
        Returns:
            dict with fine amount, legal info, and advice
        """
        matches = self.find_violation(violation_query)
        if not matches:
            return {
                "found": False,
                "message": "Violation not found. Please describe it differently.",
                "examples": ["no helmet", "drunk driving", "overspeeding", "no insurance"]
            }

        violation = matches[0]
        vid = violation["id"]
        result = {
            "found": True,
            "violation_id": vid,
            "section": violation["section"],
            "violation_name": violation["violation_name"],
            "description": violation["description"],
            "state": state,
            "vehicle_type": vehicle_type,
            "offence_number": offence_number,
            "compoundable": violation.get("compoundable", True),
            "national_fine": None,
            "state_fine": None,
            "applicable_fine": None,
            "imprisonment": violation.get("imprisonment", False),
            "dl_action": None,
            "zone_multiplier": 1.0,
            "zone_type": zone_type,
            "advice": []
        }

        # Get base national fine
        nf = violation.get("national_fine", {})
        offence_key = "first_offence" if offence_number == 1 else "subsequent"

        if isinstance(nf, dict):
            if offence_key in nf:
                fine_data = nf[offence_key]
                base_fine = fine_data.get("fine_max") or fine_data.get("fine_min", 0)
                result["national_fine"] = base_fine
                result["dl_action"] = fine_data.get("dl_disqualification_months") or fine_data.get("dl_impound")
            elif "LMV" in nf and vehicle_type in ["LMV", "Car", "Four-Wheeler"]:
                fine_data = nf["LMV"].get(offence_key, {})
                base_fine = fine_data.get("fine_max", fine_data.get("fine_min", 0))
                result["national_fine"] = base_fine
            elif "HGV_MGV" in nf and vehicle_type in ["HGV", "MGV", "Truck"]:
                fine_data = nf["HGV_MGV"].get(offence_key, {})
                base_fine = fine_data.get("fine_max", fine_data.get("fine_min", 0))
                result["national_fine"] = base_fine
            elif "guardian_owner" in nf:
                base_fine = nf["guardian_owner"].get("fine_min", 0)
                result["national_fine"] = base_fine
            else:
                base_fine = 500  # fallback
                result["national_fine"] = base_fine
        else:
            base_fine = 500
            result["national_fine"] = base_fine

        # Check state override
        state_fine = self.get_state_override(vid, state, "no_helmet" if "helmet" in violation_query.lower() else "first")
        result["state_fine"] = state_fine

        # Determine applicable fine
        applicable = state_fine if state_fine else base_fine
        result["applicable_fine"] = applicable

        # Apply zone multiplier
        zone_data = self.geo_zones.get("zone_types", {}).get(zone_type, {})
        multiplier = zone_data.get("fine_multiplier", 1.0)
        if multiplier > 1.0:
            result["zone_multiplier"] = multiplier
            result["final_fine"] = int(applicable * multiplier)
            result["advice"].append(f"⚠️ You are in a {zone_type.replace('_', ' ')} — fine multiplied by {multiplier}x")
        else:
            result["final_fine"] = applicable

        # Add contextual advice
        if not result["compoundable"]:
            result["advice"].append("🔴 This is a NON-COMPOUNDABLE offence — court appearance mandatory.")
        else:
            result["advice"].append("🟢 This is a COMPOUNDABLE offence — can be paid online or on-spot.")

        imp = violation.get("imprisonment")
        if imp and imp is not False:
            if isinstance(imp, dict):
                months = imp.get("first_offence_months") or imp.get("max_months", 0)
                if months:
                    result["advice"].append(f"⚖️ May include imprisonment up to {months} months.")

        return result

    def format_result(self, result: dict) -> str:
        """Format calculator result as readable text for chatbot response."""
        if not result["found"]:
            return result["message"]

        lines = [
            f"📋 **{result['violation_name']}** ({result['section']})",
            f"📍 State: {result['state']} | Vehicle: {result['vehicle_type']}",
            f"",
            f"💰 **Fine:**",
            f"   • National base fine: ₹{result['national_fine']:,}",
        ]
        if result["state_fine"] and result["state_fine"] != result["national_fine"]:
            lines.append(f"   • {result['state']} specific fine: ₹{result['state_fine']:,}")
        if result["zone_multiplier"] > 1.0:
            lines.append(f"   • Zone multiplier ({result['zone_type']}): {result['zone_multiplier']}x")
        lines.append(f"   • **Total applicable fine: ₹{result['final_fine']:,}**")

        if result["imprisonment"]:
            lines.append(f"")
            lines.append(f"⚖️ **Possible imprisonment:** See section details")

        if result["dl_action"]:
            lines.append(f"🪪 **DL Action:** {result['dl_action']}")

        lines.append(f"")
        for advice in result["advice"]:
            lines.append(advice)

        return "\n".join(lines)


# ─────────────────────────────────────────────
# 3. RAG KNOWLEDGE BASE BUILDER
# ─────────────────────────────────────────────

class DriveLegalKB:
    """
    Build a flat text corpus for RAG ingestion (ChromaDB / FAISS / BM25).
    Each document chunk = one violation or one FAQ.
    """

    def __init__(self):
        self.violations = get_violations_db()["violations"]
        self.faqs = get_faq()
        self.state_fines = get_state_fines()["states"]

    def build_violation_chunks(self) -> list[dict]:
        """Convert violations to RAG-ready text chunks."""
        chunks = []
        for v in self.violations:
            text = f"""
TRAFFIC VIOLATION: {v['violation_name']}
Section: {v['section']}
Act: Motor Vehicles (Amendment) Act, 2019
Description: {v['description']}
Compoundable: {'Yes - can be paid on spot' if v.get('compoundable') else 'No - requires court appearance'}
Tags: {', '.join(v.get('tags', []))}

FINES:
"""
            nf = v.get("national_fine", {})
            if "first_offence" in nf:
                fo = nf["first_offence"]
                text += f"  First Offence: ₹{fo.get('fine_min', 0):,}"
                if fo.get("fine_max") and fo["fine_max"] != fo.get("fine_min"):
                    text += f" to ₹{fo['fine_max']:,}"
                text += "\n"
            if "subsequent" in nf:
                so = nf["subsequent"]
                text += f"  Subsequent Offence: ₹{so.get('fine_min', 0):,}"
                if so.get("fine_max") and so["fine_max"] != so.get("fine_min"):
                    text += f" to ₹{so['fine_max']:,}"
                text += "\n"

            imp = v.get("imprisonment")
            if imp and imp is not False:
                text += f"IMPRISONMENT: Possible - see section for details\n"

            extra = v.get("extra_info")
            if extra:
                text += f"ADDITIONAL INFO: {extra}\n"

            chunks.append({
                "id": v["id"],
                "type": "violation",
                "text": text.strip(),
                "metadata": {
                    "section": v["section"],
                    "violation_name": v["violation_name"],
                    "tags": v.get("tags", []),
                    "compoundable": v.get("compoundable", True)
                }
            })
        return chunks

    def build_faq_chunks(self) -> list[dict]:
        """Convert FAQs to RAG-ready text chunks."""
        chunks = []
        for faq in self.faqs:
            text = f"""
QUESTION: {faq['question']}

ANSWER: {faq['answer']}

Category: {faq['category']}
Section: {faq.get('section', 'General')}
"""
            chunks.append({
                "id": faq["id"],
                "type": "faq",
                "text": text.strip(),
                "metadata": {
                    "question": faq["question"],
                    "category": faq["category"],
                    "tags": faq.get("tags", [])
                }
            })
        return chunks

    def build_state_chunks(self) -> list[dict]:
        """Convert state-specific rules to RAG-ready text chunks."""
        chunks = []
        for state, data in self.state_fines.items():
            overrides = data.get("overrides", {})
            rules = data.get("additional_rules", [])
            text = f"""
STATE: {state} (Code: {data['state_code']})
Enforcement Level: {data.get('enforcement_level', 'Medium')}
Notes: {data.get('notes', '')}

SPECIFIC FINE OVERRIDES IN {state.upper()}:
"""
            for section_id, fine_data in overrides.items():
                text += f"  {section_id}: {json.dumps(fine_data)}\n"

            if rules:
                text += f"\nADDITIONAL RULES IN {state.upper()}:\n"
                for rule in rules:
                    text += f"  - {rule}\n"

            chunks.append({
                "id": f"STATE_{data['state_code']}",
                "type": "state_rules",
                "text": text.strip(),
                "metadata": {
                    "state": state,
                    "state_code": data["state_code"]
                }
            })
        return chunks

    def get_all_chunks(self) -> list[dict]:
        """Get all chunks for RAG ingestion."""
        return (
            self.build_violation_chunks() +
            self.build_faq_chunks() +
            self.build_state_chunks()
        )

    def export_for_chromadb(self, output_path: str = "rag_corpus.json"):
        """Export all chunks as JSON for ChromaDB ingestion."""
        chunks = self.get_all_chunks()
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)
        print(f"✅ Exported {len(chunks)} chunks to {output_path}")
        return chunks

    def ingest_to_chromadb(self, collection_name: str = "drivelegal"):
        """
        Directly ingest into ChromaDB.
        Requires: pip install chromadb sentence-transformers
        """
        try:
            import chromadb
            from chromadb.utils import embedding_functions
        except ImportError:
            print("Install with: pip install chromadb sentence-transformers")
            return

        client = chromadb.PersistentClient(path="./drivelegal_chroma_db")
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="law-ai/InLegalBERT"
        )
        collection = client.get_or_create_collection(
            name=collection_name,
            embedding_function=ef
        )

        chunks = self.get_all_chunks()
        docs = [c["text"] for c in chunks]
        ids = [c["id"] for c in chunks]
        metas = [c["metadata"] for c in chunks]

        # ChromaDB metadata values must be str/int/float/bool
        clean_metas = []
        for m in metas:
            clean = {}
            for k, v in m.items():
                if isinstance(v, list):
                    clean[k] = ", ".join(str(i) for i in v)
                elif isinstance(v, bool):
                    clean[k] = str(v)
                else:
                    clean[k] = v
            clean_metas.append(clean)

        collection.add(documents=docs, ids=ids, metadatas=clean_metas)
        print(f"✅ Ingested {len(docs)} documents into ChromaDB collection '{collection_name}'")
        return collection


# ─────────────────────────────────────────────
# 4. QUICK TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("DriveLegal Challan Calculator - Test Run")
    print("=" * 60)

    calc = ChallanCalculator()

    test_cases = [
        ("no helmet", "Tamil Nadu", "Two-Wheeler", 1, "urban_road"),
        ("drunk driving", "Delhi", "LMV", 1, "urban_road"),
        ("signal jump", "Maharashtra", "LMV", 1, "urban_road"),
        ("overspeeding", "Karnataka", "LMV", 1, "school_zone"),
        ("no insurance", "Kerala", "Two-Wheeler", 2, "national_highway"),
    ]

    for violation, state, vehicle, offence, zone in test_cases:
        print(f"\n{'─' * 50}")
        result = calc.calculate(violation, state, vehicle, offence, zone)
        print(calc.format_result(result))

    print("\n" + "=" * 60)
    print("Building RAG corpus...")
    kb = DriveLegalKB()
    chunks = kb.export_for_chromadb("rag_corpus.json")
    print(f"Total RAG chunks: {len(chunks)}")
    print("  - Violations:", len(kb.build_violation_chunks()))
    print("  - FAQs:", len(kb.build_faq_chunks()))
    print("  - State Rules:", len(kb.build_state_chunks()))
