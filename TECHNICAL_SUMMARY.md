# DriveLegal — Technical Summary
**IIT Madras Road Safety Hackathon 2026**

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     MOBILE APP  (Expo / React Native)           │
│                                                                 │
│  ┌──────────┐  ┌──────────────┐  ┌────────────┐  ┌──────────┐ │
│  │  Ask     │  │  Fine Calc   │  │  Zones Map │  │ Settings │ │
│  │ Chatbot  │  │  (Offline ✓) │  │  (GPS)     │  │ Lang/A11y│ │
│  └────┬─────┘  └──────┬───────┘  └─────┬──────┘  └──────────┘ │
│       │               │                │                        │
│  useQuery.ts    useLocalDB.ts    useGeoFineAlert.ts             │
│  (REST/offline) (SQLite WAL)    (AsyncStorage cache)           │
└───────┼───────────────┼────────────────┼────────────────────────┘
        │ HTTPS         │ SQLite         │ GPS / Reverse Geocode
        ▼               ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     BACKEND  (FastAPI, port 8001)               │
│                                                                 │
│  POST /query ──────────► NLP Pipeline v2                        │
│                          ├─ normalize → detect_language         │
│                          ├─ multilingual intent (HI/TA/AR/EN)   │
│                          ├─ entity extraction (spaCy + rules)   │
│                          ├─ context resolver (session + GPS)    │
│                          └─ HybridSearch (BM25 + ChromaDB)      │
│                                      │                          │
│  POST /api/v1/challan/calculate ──► SQLite fines.db             │
│  GET  /api/v1/fines/countries ─────► SQLite fines.db            │
│  POST /api/v1/chat/multilingual ──► NLP + legal_formatter       │
│  POST /agent/query ───────────────► Gemini 2.0 Flash (optional) │
│  GET  /health ──────────────────── Component status             │
│  GET  /sync/* ──────────────────── Mobile data sync             │
│                                                                 │
│  Response Builder ──► FineLookup (SQLite Tier 1)               │
│                    ──► RulesLoader  (rules.json Tier 2)         │
│                    ──► ChallanCalc  (dataset Tier 3)            │
│                    ──► Groq LLM / template fallback             │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
  fines.db (SQLite)     rules.json (2 MB, 300+ rules)
  216 rows / 4 countries  ChromaDB vectors (offline)
```

---

## Data Sources

| Source | Format | Records | Used For |
|--------|--------|---------|----------|
| Motor Vehicles (Amendment) Act 2019 — official gazette | PDF → JSON | 24 violation types | National fine base rates, section numbers |
| State Transport Dept. notifications (TN, MH, DL, KA, KL, GJ, TS, PB, UP, WB, RJ, MP, OD, HR, BR, AS, UK, JH, CG) | Web → JSON | 63 state overrides | State-specific fine amounts |
| UAE Federal Traffic Law No. 21 of 1995 | Web → JSON | 13 violations | AED fines, black points system |
| Singapore Road Traffic Act Cap 276 | Web → JSON | 10 violations | SGD fines, demerit points |
| UK Road Traffic Act 1988 + Road Traffic Offenders Act 1988 | Web → JSON | 10 violations | GBP fines, offence codes (IN10, SP30, DD40) |
| MoRTH Parivahan state-wise challan data (`indian_traffic_e_challan.csv`) | Kaggle CSV | ~5,000 rows | ChallanCalculator training |
| DriveLegal dataset (`violations_db.json`, `state_fines_lookup.csv`) | Curated JSON/CSV | 200+ entries | HybridSearch knowledge base |
| TN GeoJSON zones (school zones, NH corridors, no-horn) | GeoJSON | 3 zone files | Geofencing fine multipliers |

---

## Language Support Matrix

| Language | Detection | Intent Extraction | State Detection | Response |
|----------|-----------|-------------------|-----------------|----------|
| English | ✓ | Full NLP (spaCy + rules) | All 22 states | Full |
| Hindi | ✓ (langdetect) | Keyword map (14 terms) | Via translation | Template + AI |
| Tamil | ✓ (langdetect) | Keyword map (12 terms) | Tamil-script (`தமிழ்நாடு`) | format_legal_response (ta) |
| Arabic | ✓ (langdetect) | Keyword map (14 terms) | Country: UAE/IN/SG/GB | format_legal_response (ar) |

---

## API Endpoint Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/query` | None | Main NLP chatbot — intent + fine + rule retrieval |
| POST | `/api/v1/chat/multilingual` | None | Language-auto-detected bilingual chatbot |
| POST | `/api/v1/challan/calculate` | None | Offline fine calculator (SQLite, no live API) |
| GET | `/api/v1/fines/countries` | None | List supported countries with row counts |
| GET | `/api/v1/fines/country/{code}` | None | All violations for a country (+ optional state/vehicle filter) |
| GET | `/api/v1/fines/search` | None | Text search across violation names and notes |
| GET | `/api/v1/fines/compounding` | None | Compounding eligibility for a specific offence |
| POST | `/fine/calculate` | None | Dataset-based fine computation (ChallanCalculator) |
| POST | `/challan/calculate` | None | Live RTO challan lookup (requires RAPIDAPI_KEY) |
| POST | `/agent/query` | None | Gemini 2.0 Flash agentic tool-calling endpoint |
| GET | `/health` | None | Component status, DB counts, AI engine availability |
| GET | `/sync/rules` | None | Mobile sync — full rules.json payload |
| GET | `/sync/fines` | None | Mobile sync — fines since timestamp |

---

## Offline Capability

```
Network available?
        │
        ├── YES → Full pipeline: NLP + vector search + SQLite + AI/Groq
        │
        └── NO  → Three-layer offline degradation:
                  │
                  ├─ Layer 1 — Challan Calculator: always works
                  │            SQLite fines.db is bundled on-device (WebSQL/expo-sqlite)
                  │            Returns fine amounts, section refs, compounding status
                  │
                  ├─ Layer 2 — Chatbot limited mode:
                  │            Keyword search against mobile/assets/seed/rules.json
                  │            Shows: "⚠️ Limited mode — Using last known: Tamil Nadu"
                  │            (Location cached in AsyncStorage with cache key
                  │             @drivelegal_last_location_v1)
                  │
                  └─ Layer 3 — GPS / Location:
                               Last known coords from AsyncStorage shown in status bar
                               Status: "Last known: Tamil Nadu, India" (amber dot)
                               GeoJSON zones queried from local expo-sqlite WAL DB
```

### Key Accuracy Test Answers

| Query | Expected Answer |
|-------|----------------|
| Drunk driving fine, Tamil Nadu | ₹10,000 (first) / ₹15,000 (repeat) · Sec 185 MV Act 2019 · up to 6 months imprisonment · **Non-compoundable** |
| Juvenile driving India | ₹25,000 · Sec 199A · guardian liable · RC cancelled · up to 3 years imprisonment |
| Arabic UAE speed fine | AED 300–1,000 + 4–8 black points; >60 km/h: AED 1,000 + 60-day licence confiscation |
| Helmet fine TN (Tamil) | ₹1,000 · Sec 194D (129) · compoundable at designated RTO counters |
| No insurance UK | £300 fixed penalty · offence code **IN10** · 6–8 licence points |
| No insurance India (repeat) | ₹4,000 (Sec 196) — repeat offence toggle applies max_fine |

---

*Built with FastAPI · spaCy · ChromaDB · Expo/React Native · SQLite · Motor Vehicles (Amendment) Act 2019*