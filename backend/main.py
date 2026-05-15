"""
DriveLegal API  v2.0
=====================
FastAPI application entry point.

Endpoints:
  POST /query              — main NLP + retrieval pipeline
  POST /challan/calculate  — honest vehicle-number lookup (no real API)
  POST /fine/calculate     — ChallanCalculator fine computation
  GET  /health             — system status
  GET  /sync/*             — mobile sync endpoints
"""

import asyncio
import os
import sys
import logging
import uvicorn
from datetime import datetime
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Configuration ─────────────────────────────────────────────────────────────
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger("drivelegal")

# Ensure project root is on sys.path for absolute imports
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Also expose dataset loader path (data_loader.py is not a proper package)
_DATASET_DIR = os.path.join(os.path.dirname(__file__), "data", "drivelegal_dataset")
if _DATASET_DIR not in sys.path:
    sys.path.insert(0, _DATASET_DIR)

# ── Module Imports ────────────────────────────────────────────────────────────
from backend.modules.nlp.pipeline import NLPPipeline
from backend.modules.fines.lookup import FineLookup
from backend.modules.rules.loader import RulesLoader
from backend.modules.geofencing.engine import GeofencingEngine
from backend.modules.response.builder import ResponseBuilder
from backend.modules.sync.router import router as sync_router
from backend.modules.nlp.hybrid_search import HybridSearch
from backend.modules.nlp.country_detector import detect_country
from backend.modules.ai import GroqProvider
from backend.modules.fines.router_v1 import router as fines_v1_router
from backend.modules.fines.rapid_api import RapidAPIChallanProvider

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR  = os.path.join(os.path.dirname(__file__), "data")
FINES_DB  = os.path.join(DATA_DIR, "fines.db")
RULES_JSON = os.path.join(DATA_DIR, "rules.json")
ZONES_DIR = os.path.join(DATA_DIR, "zones")
os.makedirs(DATA_DIR, exist_ok=True)

# ── Component Initialization ──────────────────────────────────────────────────
nlp = NLPPipeline()

fine_lookup: Optional[FineLookup] = None
if os.path.exists(FINES_DB):
    try:
        fine_lookup = FineLookup(FINES_DB)
        logger.info("FineLookup initialized (%d rows).", fine_lookup.get_count())
    except Exception as e:
        logger.warning("FineLookup init failed: %s", e)
else:
    logger.warning("fines.db not found — run: python -m backend.modules.fines.seed")

rules_loader = RulesLoader(RULES_JSON)
logger.info(
    "RulesLoader initialized (schema v%s, %d rules).",
    rules_loader.schema_version,
    rules_loader.count,
)

geofencing = GeofencingEngine(ZONES_DIR)

hybrid_search = HybridSearch(RULES_JSON, os.path.join(DATA_DIR, "vector_db"))

# ── ChallanCalculator (dataset-based, offline) ────────────────────────────────
challan_calculator: Optional[Any] = None
try:
    from data_loader import ChallanCalculator  # type: ignore
    challan_calculator = ChallanCalculator()
    logger.info("ChallanCalculator initialized.")
except Exception as e:
    logger.warning("ChallanCalculator unavailable: %s", e)

# ── AI Provider ────────────────────────────────────────────────────────────────
ai_engine: Optional[Any] = None
api_key = os.getenv("GROQ_API_KEY")
if api_key:
    try:
        ai_engine = GroqProvider(api_key=api_key)
        logger.info("Groq AI engine initialized.")
    except Exception as e:
        logger.warning("Groq init failed: %s", e)
else:
    logger.info("GROQ_API_KEY not set — using template-based responses.")

# ── RapidAPI Provider ──────────────────────────────────────────────────────────
rapid_api_provider: Optional[RapidAPIChallanProvider] = None
rapid_api_key = os.getenv("RAPIDAPI_KEY")
if rapid_api_key:
    rapid_api_provider = RapidAPIChallanProvider(rapid_api_key)
    logger.info("RapidAPI Challan Provider initialized.")

# ── Response Builder ──────────────────────────────────────────────────────────
builder = ResponseBuilder(
    fine_lookup        = fine_lookup,
    rules_loader       = rules_loader,
    geofencing_engine  = geofencing,
    ai_engine          = ai_engine,
    challan_calculator = challan_calculator,
)

# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title       = "DriveLegal API",
    description = "Indian traffic law assistant — NLP, fine lookup, and rule retrieval.",
    version     = "2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Request / Response Models ─────────────────────────────────────────────────
class QueryRequest(BaseModel):
    text:    str
    gps:     Optional[Dict] = None
    session: Dict           = {}
    country: Optional[str] = "IN"

class ChallanRequest(BaseModel):
    vehicle_number: str

class FineCalculateRequest(BaseModel):
    violation:     str
    state:         Optional[str] = "National"
    vehicle_type:  Optional[str] = "LMV"
    repeat:        Optional[bool] = False
    zone_type:     Optional[str] = "urban_road"
    country:       Optional[str] = "IN"

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/query", summary="NLP query — intent, fine, and rule lookup")
async def handle_query(request: QueryRequest = Body(...)):
    """
    Main pipeline:  NLP → hybrid search → fine/rule retrieval → response synthesis.
    """
    try:
        nlp_result = nlp.run(request.text, request.session, request.gps)

        # Country detection: text mention overrides the default "IN" request param;
        # an explicit non-default value in the request body always wins.
        effective_country = request.country or "IN"
        if effective_country == "IN":
            detected = detect_country(request.text, default="IN")
            effective_country = detected

        # Hybrid search (best-effort; failure does not block response)
        search_context = []
        try:
            search_context = hybrid_search.search(request.text, top_k=3)
        except Exception as e:
            logger.warning("Hybrid search failed: %s", e)

        nlp_result["search_matches"] = search_context
        nlp_result["country"] = effective_country

        structured = await builder.build(nlp_result, request.gps)

        # Persist session context for multi-turn conversations
        updated_session = {
            k: v for k, v in {
                "state":        nlp_result.get("state"),
                "vehicle_class": nlp_result.get("vehicle_class"),
                "offence_type": nlp_result.get("offence_type"),
                "section_ref":  nlp_result.get("section_ref"),
            }.items() if v is not None
        }
        structured["session"] = updated_session

        return structured

    except Exception as e:
        logger.exception("Unhandled error in /query: %s", e)
        return {
            "status": "error",
            "text":   "The legal database is temporarily unavailable.",
            "error_detail": str(e),
        }


@app.post(
    "/fine/calculate",
    summary="Offline fine calculator using Motor Vehicles Act dataset",
)
async def calculate_fine(request: FineCalculateRequest = Body(...)):
    """
    Computes a fine amount from the DriveLegal dataset (offline, no live API).
    Sourced from Motor Vehicles (Amendment) Act 2019 base rates and state overrides.
    Always verify final amounts at echallan.parivahan.gov.in.
    """
    if not challan_calculator:
        return {
            "status":  "service_unavailable",
            "message": "Offline calculator not initialised. Ensure the drivelegal_dataset is present.",
        }

    try:
        result = challan_calculator.calculate(
            violation_query = request.violation,
            state           = request.state or "National",
            vehicle_type    = request.vehicle_type or "LMV",
            offence_number  = 2 if request.repeat else 1,
            zone_type       = request.zone_type or "urban_road",
        )
        return {
            "status":    "ok" if result.get("found") else "not_found",
            "result":    result,
            "disclaimer": (
                "Amounts are based on Motor Vehicles (Amendment) Act 2019 base rates. "
                "Verify current amounts at https://echallan.parivahan.gov.in."
            ),
        }
    except Exception as e:
        logger.error("/fine/calculate error: %s", e)
        return {"status": "error", "message": str(e)}


@app.post(
    "/challan/calculate",
    summary="Vehicle-number challan lookup (via RapidAPI live lookup)",
)
async def calculate_challan(request: ChallanRequest = Body(...)):
    """
    Live challan lookup by vehicle number using RapidAPI.
    """
    if not rapid_api_provider:
        return {
            "status":               "service_unavailable",
            "vehicle_number":       request.vehicle_number,
            "message": (
                "Live challan lookup is not currently configured. "
                "Check pending challans at: https://echallan.parivahan.gov.in/index/accused-challan "
                "or provide a RAPIDAPI_KEY in .env."
            ),
            "last_updated":         datetime.now().isoformat(),
        }

    # Run network request in thread pool
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None, 
        lambda: rapid_api_provider.get_challans(request.vehicle_number)
    )

    if result["status"] == "success":
        challans = result.get("challans", [])
        total_fine = sum(int(c.get("amount", 0)) for c in challans)
        return {
            "status":         "ok",
            "vehicle_number": request.vehicle_number,
            "vehicle_info":   result.get("vehicle_details"),
            "challan_count":  len(challans),
            "total_fine":     total_fine,
            "challans":       challans,
            "source":         "RapidAPI (Live RTO Data)",
            "last_updated":   datetime.now().isoformat(),
        }

    if result["status"] == "provider_down":
        # API provider is having an outage — return demo data so the app still works
        demo_challans = [
            {"challan_no": "DEMO-2024-001", "offence": "Overspeeding", "amount": 1000, "status": "Pending", "date": "2024-11-01"},
            {"challan_no": "DEMO-2024-002", "offence": "No Helmet",    "amount": 500,  "status": "Pending", "date": "2024-11-15"},
        ]
        return {
            "status":         "demo",
            "vehicle_number": request.vehicle_number,
            "challan_count":  len(demo_challans),
            "total_fine":     1500,
            "challans":       demo_challans,
            "source":         "Demo data (live RTO API temporarily unavailable)",
            "last_updated":   datetime.now().isoformat(),
        }

    return {
        "status":         "error",
        "vehicle_number": request.vehicle_number,
        "message":        result.get("message", "Failed to fetch data from RapidAPI"),
        "last_updated":   datetime.now().isoformat(),
    }


@app.get("/health", summary="System health and database metadata")
async def get_health():
    db_age     = fine_lookup.get_db_age() if fine_lookup else "DB not found"
    fine_count = fine_lookup.get_count()  if fine_lookup else 0
    
    # Get country counts
    import sqlite3
    try:
        conn = sqlite3.connect(FINES_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT country, COUNT(*) FROM fines GROUP BY country")
        country_counts = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
    except Exception as e:
        country_counts = {"error": str(e)}

    return {
        "status":               "ok",
        "schema_version":       rules_loader.schema_version,
        "rules_count":          rules_loader.count,
        "fines_count":          fine_count,
        "country_counts":       country_counts,
        "db_age":               db_age,
        "ai_engine":            "groq" if ai_engine else "template",
        "challan_calculator":   challan_calculator is not None,
        "vector_search":        hybrid_search.bm25 is not None,
        "rapid_api_live":       rapid_api_provider is not None,
    }


# ── Router Mounts ─────────────────────────────────────────────────────────────
app.include_router(sync_router)
app.include_router(fines_v1_router)

# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()

    os.environ.setdefault(
        "PYTHONPATH",
        _PROJECT_ROOT + os.pathsep + os.environ.get("PYTHONPATH", ""),
    )

    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)
