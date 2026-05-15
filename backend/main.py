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
from backend.modules.agent.engine import AgentEngine
from backend.modules.multilingual_intent import (
    detect_language,
    extract_intent_multilingual,
    translate_to_english,
    violation_code_to_offence_type,
)
from backend.modules.legal_formatter import format_legal_response, build_violation_row

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

# ── Gemini Agent (optional — requires GEMINI_API_KEY in .env) ─────────────────
agent_engine = AgentEngine(
    fine_lookup        = fine_lookup,
    rules_loader       = rules_loader,
    geofencing_engine  = geofencing,
)

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

class AgentQueryRequest(BaseModel):
    text:    str
    gps:     Optional[Dict] = None
    # Multi-turn history: [{"role": "user"|"model", "parts": ["message"]}]
    history: list = []

class MultilingualChatRequest(BaseModel):
    message: str
    country: Optional[str] = "IN"
    gps:     Optional[Dict] = None
    session: Dict           = {}

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/query", summary="NLP query — intent, fine, and rule lookup")
async def handle_query(request: QueryRequest = Body(...)):
    """
    Main pipeline:  NLP → hybrid search → fine/rule retrieval → response synthesis.
    """
    try:
        nlp_result = nlp.run(request.text, request.session, request.gps)

        # Country detection: priority order —
        #   1. NLP pipeline country (from Arabic/multilingual extraction)
        #   2. Text keyword detection (detect_country)
        #   3. Explicit request.country
        #   4. Default "IN"
        effective_country = request.country or "IN"
        nlp_country = nlp_result.get("country")
        if nlp_country and nlp_country != "IN":
            effective_country = nlp_country
        elif effective_country == "IN":
            detected = detect_country(request.text, default="IN")
            effective_country = detected

        # Hybrid search — retrieve more candidates when AI engine is available
        # so the AI has a wider knowledge base to answer open-ended questions.
        # For general/procedure queries fetch more results (up to 8) since there
        # is no structured fine data and the answer comes entirely from search.
        search_context = []
        try:
            general_intents = {"general_query", "procedure_query"}
            search_top_k = (
                8 if nlp_result.get("intent") in general_intents
                else (5 if ai_engine else 3)
            )
            # Enrich the search query with road_type context when extracted
            search_query = request.text
            road_type = nlp_result.get("road_type")
            if road_type:
                search_query = f"{request.text} {road_type.replace('_', ' ')}"
            search_context = hybrid_search.search(
                search_query,
                top_k=search_top_k,
                country=effective_country
            )
        except Exception as e:
            logger.warning("Hybrid search failed: %s", e)

        nlp_result["search_matches"] = search_context
        nlp_result["country"] = effective_country

        structured = await builder.build(nlp_result, request.gps)

        # If the builder already wrote a richer session (clarification gate),
        # keep it as-is.  Otherwise build the standard session update.
        if "session" not in structured:
            updated_session = {
                k: v for k, v in {
                    "state":        nlp_result.get("state"),
                    "vehicle_class": nlp_result.get("vehicle_class"),
                    "offence_type": nlp_result.get("offence_type"),
                    "section_ref":  nlp_result.get("section_ref"),
                    # Clear the clarification flag once a full answer is given
                    "in_clarification": False,
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


@app.post("/api/v1/chat/multilingual", summary="Multilingual chatbot — auto-detects language, returns bilingual response")
async def handle_multilingual_chat(request: MultilingualChatRequest = Body(...)):
    """
    Accepts a message in any supported language (EN, HI, TA, …).
    Pipeline:
      1. Detect language via langdetect.
      2. Extract intent + violation codes from Hindi/Tamil keywords.
      3. Map to canonical offence_type; fall back to English NLP pipeline.
      4. If multilingual extraction yields nothing, translate query to English
         and run the standard NLP pipeline on the translated text.
      5. Build structured response, format in detected language AND English.
      6. Return bilingual payload.
    """
    msg = request.message.strip()
    if not msg:
        return {"status": "error", "text": "Empty message."}

    try:
        # ── 1. Language detection ──────────────────────────────────────────────
        detected_lang = detect_language(msg)

        # ── 2. Multilingual intent extraction ─────────────────────────────────
        ml_intent, violation_codes, country = extract_intent_multilingual(msg, detected_lang)
        effective_country = request.country or country or "IN"

        # ── 3. Build NLP result from multilingual extraction ───────────────────
        # Try to map the first detected violation code to an offence_type.
        offence_type: Optional[str] = None
        if violation_codes:
            offence_type = violation_code_to_offence_type(violation_codes[0])

        # ── 4. Fallback: translate to English and run standard NLP pipeline ────
        if not offence_type and detected_lang in ("hi", "ta"):
            translated = translate_to_english(msg, detected_lang)
            logger.info("Multilingual fallback: translated '%s' → '%s'", msg[:60], translated[:60])
            nlp_result = nlp.run(translated, request.session, request.gps)
            nlp_result["_translated_from"] = detected_lang
        else:
            # Run standard pipeline on the original text (entities like state still useful)
            nlp_result = nlp.run(msg, request.session, request.gps)
            # Override intent/offence_type with multilingual extraction when better
            if offence_type:
                nlp_result["offence_type"] = offence_type
            if ml_intent != "unknown" and nlp_result.get("intent") == "unknown":
                nlp_result["intent"] = ml_intent
                nlp_result["status"] = "success"

        # Hybrid search — enrich query context
        search_context = []
        try:
            search_top_k = 5 if ai_engine else 3
            search_query = msg
            if offence_type:
                search_query = f"{msg} {offence_type.replace('_', ' ').lower()}"
            search_context = hybrid_search.search(
                search_query, top_k=search_top_k, country=effective_country
            )
        except Exception as e:
            logger.warning("Multilingual hybrid search failed: %s", e)

        nlp_result["search_matches"] = search_context
        nlp_result["country"] = effective_country

        # ── 5. Build structured response ───────────────────────────────────────
        structured = await builder.build(nlp_result, request.gps)

        # ── 6. Format localised response text ─────────────────────────────────
        response_text = structured.get("text", "")
        response_en   = response_text  # default: same as detected-lang response

        _SUPPORTED_NATIVE_LANGS = ("hi", "ta", "ar")
        if detected_lang in _SUPPORTED_NATIVE_LANGS:
            rule  = structured.get("rule")
            fine  = structured.get("fine")
            if rule or fine:
                try:
                    vrow = build_violation_row(rule, fine)
                    response_text = format_legal_response(vrow, country=effective_country, lang=detected_lang)
                    response_en   = format_legal_response(vrow, country=effective_country, lang="en")
                except Exception as e:
                    logger.warning("Multilingual formatter error: %s", e)
                    # response_text stays as the AI/template text; add a note
                    _fallback_note = {
                        "hi": "हिंदी में जवाब उपलब्ध नहीं है। / Answer in English:\n\n",
                        "ta": "தமிழில் பதில் கிடைக்கவில்லை. / Answer in English:\n\n",
                        "ar": "الإجابة باللغة الإنجليزية:\n\n",
                    }
                    response_text = _fallback_note.get(detected_lang, "") + response_text
            else:
                _fallback_note = {
                    "hi": "हिंदी में जवाब उपलब्ध नहीं है। / Answer in English:\n\n",
                    "ta": "தமிழில் பதில் கிடைக்கவில்லை. / Answer in English:\n\n",
                    "ar": "الإجابة باللغة الإنجليزية:\n\n",
                }
                response_text = _fallback_note.get(detected_lang, "") + response_text

        # ── 7. Build legal_citations list ──────────────────────────────────────
        legal_citations: list = []
        fine_data = structured.get("fine")
        rule_data = structured.get("rule")
        if fine_data and fine_data.get("section_ref"):
            legal_citations.append(f"{fine_data['section_ref']}, MV Act 2019")
        if rule_data and rule_data.get("section") and rule_data["section"] not in legal_citations:
            legal_citations.append(f"{rule_data['section']}, MV Act 2019")

        return {
            "status":            structured.get("status", "ok"),
            "response":          response_text,
            "response_en":       response_en,
            "detected_language": detected_lang,
            "violation_codes":   violation_codes or ([nlp_result.get("offence_type")] if nlp_result.get("offence_type") else []),
            "legal_citations":   legal_citations,
            "fine":              structured.get("fine"),
            "rule":              structured.get("rule"),
            "warnings":          structured.get("warnings", []),
        }

    except Exception as e:
        logger.exception("Unhandled error in /api/v1/chat/multilingual: %s", e)
        return {
            "status":            "error",
            "response":          "The multilingual assistant is temporarily unavailable.",
            "response_en":       "The multilingual assistant is temporarily unavailable.",
            "detected_language": "en",
            "violation_codes":   [],
            "legal_citations":   [],
            "error_detail":      str(e),
        }


@app.post("/agent/query", summary="Gemini agentic query — tool calling + multi-turn")
async def handle_agent_query(request: AgentQueryRequest = Body(...)):
    """
    Agentic endpoint powered by Gemini 2.0 Flash with function calling.
    The model autonomously decides which tools to call (lookup_fine,
    lookup_rule, check_zone, search_rules) and synthesises a grounded
    natural-language response.

    Falls back to HybridSearch + keyword matching when GEMINI_API_KEY is
    not set or the API is rate-limited.
    """
    try:
        result = agent_engine.run(
            user_text             = request.text,
            conversation_history  = request.history,
            gps                   = request.gps,
        )
        return result
    except Exception as e:
        logger.exception("Unhandled error in /agent/query: %s", e)
        return {
            "status":       "error",
            "response":     "The agent is temporarily unavailable.",
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
        "agent_engine":         "gemini-2.0-flash" if agent_engine.gemini_available else "keyword-fallback",
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
