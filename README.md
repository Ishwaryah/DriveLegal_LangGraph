# DriveLegal 🚦

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Expo](https://img.shields.io/badge/Expo-000020?style=for-the-badge&logo=expo&logoColor=white)](https://expo.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)

> **Indian Traffic Law Assistant** — NLP-powered fine lookup, rule retrieval, geofencing alerts, and multilingual chat for drivers and legal professionals.

---

## Overview

DriveLegal helps Indian citizens understand traffic violations, challan amounts, and driving laws in real time.

| Layer | Stack |
|---|---|
| Backend API | FastAPI · Python 3.10 |
| AI Agent | LangGraph · Groq (Llama 3.3) |
| NLP | spaCy · InLegalBERT · BM25 Hybrid Search |
| Database | SQLite (fines) · ChromaDB (vector search) |
| Geofencing | Shapely · GeoJSON |
| Mobile | React Native · Expo (TypeScript) |
| Sessions | Redis |
| OCR | Tesseract · EasyOCR |

---

## Project Structure

```
DriveLegal/
├── backend/                        # FastAPI Python backend
│   ├── main.py                     # Application entry point & all route definitions
│   ├── requirements.txt            # Python dependencies
│   ├── .env                        # Environment variables (not committed — see below)
│   │
│   ├── modules/                    # Core business logic
│   │   ├── agent/                  # Groq agentic loop (engine.py + tools.py)
│   │   ├── ai/                     # AI provider abstraction (Groq, circuit breaker)
│   │   ├── fines/                  # Fine lookup, seeding, RapidAPI challan, v1 router
│   │   ├── geofencing/             # Zone-based restriction engine
│   │   ├── nlp/                    # NLP pipeline, hybrid search, entity extraction
│   │   ├── response/               # Structured response builder
│   │   ├── rules/                  # rules.json loader with state overrides
│   │   ├── sync/                   # Mobile offline-sync router
│   │   ├── legal_formatter.py      # Legal citation formatter
│   │   └── multilingual_intent.py  # Language detection & multilingual NLP
│   │
│   ├── routers/                    # FastAPI router modules
│   │   ├── analytics.py            # Usage analytics endpoints
│   │   ├── cv.py                   # Computer vision / plate OCR
│   │   ├── emergency.py            # Emergency contacts & SOS
│   │   └── vehicle_lookup.py       # RC / DL document lookup
│   │
│   ├── services/                   # External service clients
│   │   ├── analytics_service.py
│   │   ├── document_validator.py
│   │   ├── drowsiness_service.py
│   │   ├── emergency_service.py
│   │   ├── geofencing_engine.py
│   │   ├── parivahan_service.py    # Vahan / Sarathi offline snapshots
│   │   ├── plate_ocr_service.py
│   │   └── session_manager.py      # Redis session manager
│   │
│   ├── data/                       # Runtime data
│   │   ├── fines.db                # SQLite fine amounts (seeded from seed_fines.csv)
│   │   ├── rules.json              # Traffic rules with state overrides (schema v2)
│   │   ├── metadata.json           # NLP entity maps: vehicle classes, states, offences
│   │   ├── seed_fines.csv          # Fine seeding table for fines.db
│   │   ├── dataset_catalog.json    # Dataset registry
│   │   ├── zones/                  # GeoJSON geofencing zones (DL, MH, TN, ALL)
│   │   └── drivelegal_dataset/     # Reference JSON/CSV datasets
│   │       ├── json/               # Fine rules, emergency contacts, FAQ, EV regs, etc.
│   │       ├── csv/                # State-wise fine lookup tables & RTO questions
│   │       ├── multilingual/       # Multilingual string maps
│   │       └── data_loader.py      # ChallanCalculator (offline fine computation)
│   │
│   ├── tests/                      # Full test suite
│   │   ├── unit/                   # Unit tests (isolated, no external DB required)
│   │   │   ├── test_fine_lookup.py
│   │   │   ├── test_geofencing_engine.py
│   │   │   ├── test_nlp_pipeline.py
│   │   │   └── test_rules_loader.py
│   │   ├── test_analytics.py
│   │   ├── test_challan.py
│   │   ├── test_conversation_loop.py
│   │   ├── test_dataset_functionality.py
│   │   ├── test_document_validator.py
│   │   ├── test_geofencing.py      # Integration: live zone data
│   │   ├── test_integration.py
│   │   └── test_query_flow.py
│   │
│   ├── scripts/                    # Admin / one-off scripts
│   │   ├── ingest.py               # Ingest Kaggle e-challan CSV → fines.db
│   │   ├── ingest_data.py          # Extended ingestion pipeline
│   │   ├── merge_dataset.py        # Merge drivelegal_dataset → rules.json + seed_fines.csv
│   │   ├── merge_local_dataset.py  # Merge from local dataset copy
│   │   ├── add_state_rules.py      # Append state-specific rule overrides
│   │   ├── bulk_insert.py          # Bulk fine records insert
│   │   ├── generate_catalog.py     # Regenerate dataset_catalog.json
│   │   ├── setup_kaggle_datasets.py # Download & scaffold Kaggle datasets
│   │   ├── migrate_db.py           # Run schema migrations
│   │   ├── load_test.py            # API load / latency test
│   │   └── train.py                # Re-index vector DB / fine-tune embeddings
│   │
│   └── migrations/
│       └── add_vehicle_cache.py    # Schema migration: vehicle cache table
│
├── mobile/                         # React Native (Expo) mobile app
│   ├── app/                        # Expo Router screens
│   │   ├── _layout.tsx             # Root layout & navigation
│   │   ├── index.tsx               # Entry / redirect
│   │   ├── vehicle.tsx             # RC & DL document lookup
│   │   ├── location.tsx            # GPS / geofencing alerts
│   │   ├── sos.tsx                 # Emergency SOS
│   │   └── (tabs)/                 # Tab-based navigation group
│   │       ├── _layout.tsx         # Tab bar definition
│   │       ├── index.tsx           # Home tab
│   │       ├── ask.tsx             # NLP query tab
│   │       ├── fines.tsx           # Fine lookup tab
│   │       ├── settings/           # Settings screens
│   │       │   ├── _layout.tsx
│   │       │   ├── index.tsx       # Settings home
│   │       │   └── documents.tsx   # RC/DL document store
│   │       └── zones/              # Zone map screens
│   │           ├── _layout.tsx
│   │           ├── index.tsx       # Zone map overview
│   │           ├── live.tsx        # Live GPS zone detection
│   │           └── speed-limits.tsx
│   ├── components/                 # Reusable UI components
│   │   ├── ChallanCalculator.tsx
│   │   ├── FineCard.tsx
│   │   ├── Hamburger.tsx
│   │   ├── OfflineBadge.tsx
│   │   ├── RuleCard.tsx
│   │   ├── Sidebar.tsx
│   │   └── SidebarRail.tsx
│   ├── hooks/                      # Custom React hooks
│   │   ├── useDocuments.ts         # RC/DL document fetching
│   │   ├── useGeoFineAlert.ts      # GPS-based zone alerts
│   │   ├── useHistory.tsx          # Query history
│   │   ├── useLocalDB.ts           # Device SQLite
│   │   ├── useQuery.ts             # Backend query hook
│   │   ├── useSettings.tsx         # App settings
│   │   ├── useSync.ts              # Offline sync
│   │   └── useUI.tsx               # UI state (modals, sidebar)
│   ├── assets/
│   │   ├── seed/                   # Bundled offline data seed
│   │   │   ├── fines.db            # Offline fine database
│   │   │   └── rules.json          # Offline rules
│   │   └── tiles/                  # Map tile assets
│   ├── context/
│   │   └── LanguageContext.tsx     # Language preference
│   ├── i18n/
│   │   └── strings.ts              # Localisation strings
│   ├── local_db/
│   │   └── schema.sql              # Device-side SQLite schema
│   ├── types/
│   │   └── challan.ts              # TypeScript types
│   ├── config/
│   │   └── api.ts                  # Backend base URL config
│   ├── stubs/                      # Expo Go compatibility shims
│   ├── package.json
│   └── tsconfig.json
│
├── .gitignore
└── README.md
```

---

## Key API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/query` | Main NLP + agentic query (fine + rule + zone) |
| `POST` | `/agent/query` | Groq multi-turn agentic loop |
| `POST` | `/api/v1/chat/multilingual` | Auto-detect language, bilingual response |
| `POST` | `/fine/calculate` | Offline fine calculator (MV Act dataset) |
| `POST` | `/challan/calculate` | Live challan lookup by vehicle number |
| `GET`  | `/api/v1/vehicle/info/{reg_no}` | RC details (RapidAPI or offline fallback) |
| `GET`  | `/api/v1/vehicle/challans/{reg_no}` | Pending challans for a vehicle |
| `GET`  | `/api/v1/dl/info/{dl_no}` | DL validation (Sarathi or offline fallback) |
| `GET`  | `/health` | System health + DB metadata |
| `GET`  | `/api/v1/health/datasets` | Dataset readiness score |

Full interactive docs: `http://localhost:8001/docs`

---

## Quick Start

### Backend

```bash
# 1. Create & activate virtual environment
python -m venv backend/venv
# Linux/macOS:
source backend/venv/bin/activate
# Windows:
backend\venv\Scripts\activate

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Configure environment
# Create backend/.env with the variables shown in "Environment Variables" below

# 4. Seed the fine database
python -m backend.modules.fines.seed

# 5. Start the API server
uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload
```

### Mobile

```bash
cd mobile
npm install
npx expo start
```

---

## Environment Variables

Create `backend/.env` (gitignored):

```env
# Required — Groq LLM API key for the agentic query engine
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx

# Optional — live challan & vehicle lookup via RapidAPI
RAPIDAPI_KEY=your_rapidapi_key

# Optional — Redis session persistence (defaults to localhost)
REDIS_URL=redis://localhost:6379/0
```

Without `GROQ_API_KEY` the engine falls back to keyword matching + BM25 hybrid search.  
Without `RAPIDAPI_KEY` vehicle / challan lookups use the bundled offline snapshots.

---

## Running Tests

```bash
# From project root

# Unit tests only (fast, no external services)
pytest backend/tests/unit/ -v

# Full test suite
pytest backend/tests/ -v

# With coverage report
pytest backend/tests/ --cov=backend --cov-report=term-missing
```

---

## Data Architecture

```
User query (text + optional GPS)
        │
        ▼
  NLP Pipeline ──► Intent classification + Entity extraction
        │                    (metadata.json maps)
        ▼
  AgentEngine ──► LangGraph Orchestration (Llama 3.3 70B)
        │         └── lookup_fine()   → fines.db  (SQLite)
        │         └── lookup_rule()   → rules.json
        │         └── search_rules()  → BM25 + ChromaDB hybrid
        │         └── check_zone()    → GeoJSON zones (Shapely)
        ▼
  ResponseBuilder ──► Structured JSON with legal citations
        │
        ▼
  Mobile app / REST clients
```

---

## Legal Disclaimer

All fine amounts are based on the **Motor Vehicles (Amendment) Act, 2019** and published state-level notifications. Always verify current challan amounts at [echallan.parivahan.gov.in](https://echallan.parivahan.gov.in).

---

*DriveLegal — making Indian traffic law accessible to every citizen.*
