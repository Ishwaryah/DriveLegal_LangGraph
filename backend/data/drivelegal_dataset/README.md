# DriveLegal Dataset Package
## IIT Madras Road Safety Hackathon 2026 — Problem Statement 1

---

## 📦 Package Contents

```
drivelegal_dataset/
├── json/
│   ├── violations_db.json      # All 28 MV Act sections with fines (core dataset)
│   ├── state_wise_fines.json   # 13 states with fine overrides & local rules
│   ├── geo_fencing_zones.json  # Speed limits & multipliers by zone type
│   ├── vehicle_categories.json # Vehicle types, licence requirements, speed limits
│   └── faq_chatbot.json        # 20 Q&A pairs for chatbot RAG corpus
├── csv/
│   ├── violations_flat.csv     # Flat lookup table — all violations in one sheet
│   └── state_fines_lookup.csv  # State × Violation fine matrix
├── data_loader.py              # Python utility: calculator + RAG builder
├── rag_corpus.json             # Auto-generated: 61 RAG chunks (run data_loader.py)
└── README.md                   # This file
```

---

## 🏛️ Data Sources

| File | Source |
|------|--------|
| `violations_db.json` | Motor Vehicles (Amendment) Act, 2019 (No. 32 of 2019) — MoRTH |
| `state_wise_fines.json` | State Transport Department notifications (2019–2026) |
| `geo_fencing_zones.json` | MoRTH Speed Limit Notifications + CMVR Rules |
| `vehicle_categories.json` | Central Motor Vehicles Rules 1989 + MVA Schedule |
| `faq_chatbot.json` | Synthesized from official MoRTH, PIB, MCA circulars |

**Verify at official sources:**
- MoRTH: https://morth.nic.in
- eChallan: https://echallan.parivahan.gov.in
- PIB: https://pib.gov.in

---

## ⚡ Quick Start

### 1. Challan Calculator
```python
from data_loader import ChallanCalculator

calc = ChallanCalculator()
result = calc.calculate(
    violation_query="no helmet",
    state="Tamil Nadu",
    vehicle_type="Two-Wheeler",
    offence_number=1,
    zone_type="urban_road"
)
print(calc.format_result(result))
```

### 2. Build RAG Corpus (for ChromaDB / FAISS / BM25)
```python
from data_loader import DriveLegalKB

kb = DriveLegalKB()

# Export to JSON for manual ingestion
chunks = kb.export_for_chromadb("rag_corpus.json")

# OR directly ingest to ChromaDB (requires: pip install chromadb sentence-transformers)
collection = kb.ingest_to_chromadb("drivelegal")
```

### 3. Direct JSON Lookup
```python
import json

with open("json/violations_db.json") as f:
    db = json.load(f)

# Get fine for Section 185 (Drunk Driving)
v = next(v for v in db["violations"] if v["id"] == "MV185")
print(v["national_fine"]["first_offence"])
# Output: {"fine_min": 10000, "fine_max": 10000}
```

---

## 🗺️ Architecture: How to Feed Data into Your Chatbot

```
User Query
    │
    ▼
[Geo-detect State]  ◄── IP geolocation / user input
    │
    ▼
[Intent Detection]
  ├── "How much fine?" → ChallanCalculator.calculate()
  ├── "What is the rule?" → RAG retrieval from rag_corpus.json
  └── "Pay my challan" → Redirect to echallan.parivahan.gov.in
    │
    ▼
[ChallanCalculator]
  1. Match violation query → violations_db.json (tag-based search)
  2. Get national base fine
  3. Override with state fine (state_wise_fines.json)
  4. Apply zone multiplier (geo_fencing_zones.json)
  5. Return structured result
    │
    ▼
[LLM Response Generation]
  Context = RAG chunks + Calculator result
  → Format final response
```

---

## 📊 Dataset Statistics

- **28** MV Act violations (Sections 177–210B)
- **13** states with fine overrides
- **9** geo-fence zone types
- **9** vehicle categories with speed limits
- **20** FAQ Q&A pairs
- **61** total RAG corpus chunks

---

## 🎯 Evaluation Criteria Coverage

| Criterion | How This Dataset Covers It |
|-----------|---------------------------|
| Legal accuracy | All sections from official MV (Amendment) Act 2019 |
| Challan calculator | `ChallanCalculator` class with vehicle type + state + zone |
| Information across countries | `geo_fencing_zones.json` has global zone types; extend `state_wise_fines.json` schema for other countries |
| Offline functionality | All data is local JSON/CSV — zero external API calls needed |
| User interface | Connect `data_loader.py` to your existing chatbot backend |

---

## 🔌 API Integration (Optional - Live Challan Check)

For live challan lookup by vehicle number, use:
- **InstantPay Traffic Challan API**: https://www.instantpay.in/
  - Register → Get API key → Query by vehicle number
- **Sarathi Parivahan API** (for DL verification): https://sarathi.parivahan.gov.in/
- **Vahan API** (for RC verification): https://vahan.parivahan.gov.in/

---

## ⚠️ Important Notes

1. **State fines change**: Always verify state-specific fines from official state transport websites before production deployment.
2. **Annual hike**: Per MV Act, central fines increase 10% every April 1st.
3. **Court discretion**: Non-compoundable offences have variable court-determined penalties.
4. **Local rules**: Cities like Delhi, Mumbai have additional local rules not in central Act.

---

*Compiled for DriveLegal — IIT Madras Road Safety Hackathon 2026*
