"""
Hybrid search engine: vector (ChromaDB/SentenceTransformers) + lexical (BM25).

Indexes three corpora:
  1. rules.json      — Motor Vehicles Act rules (schema v1 or v2)
  2. violations_db   — DriveLegalKB violation chunks  (schema v2 / dataset)
  3. faq_chatbot     — DriveLegalKB FAQ chunks

NoneType safeguards are applied at every point where document fields may be absent.
"""

import os
import sys
import json
import logging
from typing import Any, Dict, List, Optional

import chromadb
from rank_bm25 import BM25Okapi
from dotenv import load_dotenv

from backend.modules.nlp.country_detector import detect_country
load_dotenv()
logger = logging.getLogger(__name__)

# ── Optional DriveLegalKB import (path-safe) ──────────────────────────────────
_DATASET_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "drivelegal_dataset")
)
if _DATASET_DIR not in sys.path:
    sys.path.insert(0, _DATASET_DIR)

try:
    from data_loader import DriveLegalKB  # type: ignore
    _HAS_KB = True
except Exception as _kb_err:
    logger.warning("DriveLegalKB unavailable (%s). RAG will use rules.json only.", _kb_err)
    _HAS_KB = False


def _safe_text(value: Any) -> str:
    """Return a non-None string — central guard against AttributeError on None."""
    if value is None:
        return ""
    return str(value)


def _tokenize(text: Any) -> List[str]:
    """Tokenize text for BM25; always returns a list (never raises)."""
    return _safe_text(text).lower().split() or ["<empty>"]


class HybridSearch:
    """
    Hybrid (vector + BM25) search over DriveLegal knowledge corpus.

    The ChromaDB collection is lazily populated on first use; subsequent restarts
    skip re-indexing unless the collection is empty.  Deleting the vector_db
    directory forces a full re-index (done automatically by merge_dataset.py).
    """

    def __init__(self, rules_path: str, persist_directory: str):
        self.rules_path        = rules_path
        self.persist_directory = persist_directory

        # ── Embedding function ────────────────────────────────────────────────
        self.embedding_function: Optional[Any] = None
        try:
            from chromadb.utils import embedding_functions  # type: ignore
            self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="law-ai/InLegalBERT"
            )
            logger.info("SentenceTransformer embeddings loaded (InLegalBERT).")
        except Exception as e:
            logger.warning("Local embeddings unavailable (%s). Using BM25-only fallback.", e)

        # ── ChromaDB ──────────────────────────────────────────────────────────
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        embedding_tag    = "st_inlegalbert" if self.embedding_function else "none"
        collection_name  = f"drivelegal_{embedding_tag}_v1"

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
        )

        # ── BM25 ──────────────────────────────────────────────────────────────
        self.bm25: Optional[BM25Okapi] = None
        self.documents: List[Dict]     = []   # flat list of indexable chunks

        # ── Multilingual Translation Fallback ────────────────────────────────
        self._init_multilingual_dicts()
        self.translator_pipeline = None
        try:
            from transformers import pipeline
            self.translator_pipeline = pipeline("translation", model="Helsinki-NLP/opus-mt-mul-en")
            logger.info("Translation pipeline loaded (opus-mt-mul-en).")
        except Exception as e:
            logger.warning("Translation pipeline unavailable (%s). Using dictionary-only fallback.", e)

        self._build_corpus()

    def _init_multilingual_dicts(self):
        """Load all translation dictionaries for Hindi, Tamil, Telugu, Kannada, Marathi."""
        self.phrase_map = {}
        self.word_map = {}
        
        multilingual_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "data", "drivelegal_dataset", "multilingual")
        )
        
        # 1. Load common violations translations
        common_path = os.path.join(multilingual_dir, "common_violations_translations.json")
        if os.path.exists(common_path):
            try:
                with open(common_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for key, langs in data.items():
                        english_val = langs.get("en", "")
                        if not english_val:
                            continue
                        for lang_code, regional_phrase in langs.items():
                            if lang_code != "en" and regional_phrase:
                                # Map full phrase to English equivalent
                                self.phrase_map[regional_phrase.strip().lower()] = english_val
            except Exception as e:
                logger.warning("Failed to load common violations translations: %s", e)

        # 2. Load language-specific term dictionaries
        for lang in ["hindi", "tamil", "telugu", "kannada", "marathi"]:
            term_path = os.path.join(multilingual_dir, f"traffic_terms_{lang}.json")
            if os.path.exists(term_path):
                try:
                    with open(term_path, "r", encoding="utf-8") as f:
                        terms = json.load(f)
                        for eng_key, val in terms.items():
                            val_str = str(val).strip()
                            # e.g., "போக்குவரத்து (Pokkuvarathu)"
                            # Extract native script and transliterated word
                            parts = val_str.split("(")
                            native_word = parts[0].strip().lower()
                            self.word_map[native_word] = eng_key
                            
                            if len(parts) > 1:
                                translit_word = parts[1].replace(")", "").strip().lower()
                                self.word_map[translit_word] = eng_key
                except Exception as e:
                    logger.warning("Failed to load terms dictionary traffic_terms_%s.json: %s", lang, e)

    def translate_query_to_english(self, query: str) -> str:
        """
        Translates regional/multilingual query (Hindi, Tamil, etc.) to English.
        Utilizes high-fidelity local dictionaries first, with fallback to an
        offline-safe HuggingFace translation pipeline if available.
        """
        if not query:
            return ""
            
        cleaned_query = query.strip().lower()
        
        # Step 1: Check if query contains non-ASCII characters or regional terms
        is_english = True
        try:
            query.encode('ascii')
            # Check if any words match our transliterated word_map (e.g. "abaratham" or "yatayat")
            words = cleaned_query.split()
            if not any(w in self.word_map for w in words):
                is_english = True
            else:
                is_english = False
        except UnicodeEncodeError:
            is_english = False
            
        if is_english:
            return query

        logger.info("Detecting regional query: '%s'. Applying translation pipeline...", query)

        # Step 2: Try to translate using local dictionary first (high precision for common traffic phrases)
        translated_query = cleaned_query
        
        # A. Phrase-level replacements (longest first)
        sorted_phrases = sorted(self.phrase_map.keys(), key=len, reverse=True)
        for regional_phrase in sorted_phrases:
            if regional_phrase in translated_query:
                translated_query = translated_query.replace(regional_phrase, self.phrase_map[regional_phrase])

        # B. Word-level replacements
        words = translated_query.split()
        translated_words = []
        for w in words:
            clean_w = w.strip(".,?!;:()[]\"'")
            if clean_w in self.word_map:
                translated_words.append(self.word_map[clean_w])
            else:
                translated_words.append(w)
        
        dict_translated = " ".join(translated_words)

        # Step 3: Optional HuggingFace pipeline translation
        if hasattr(self, "translator_pipeline") and self.translator_pipeline is not None:
            try:
                res = self.translator_pipeline(query)
                if res and isinstance(res, list) and len(res) > 0:
                    hf_translation = res[0].get("translation_text", "")
                    if hf_translation:
                        logger.info("HF Pipeline translation: '%s'", hf_translation)
                        return hf_translation
            except Exception as e:
                logger.warning("HF Pipeline translation failed: %s. Using local dictionary translation.", e)

        logger.info("Local dictionary translation: '%s'", dict_translated)
        return dict_translated

    # ── Corpus construction ───────────────────────────────────────────────────

    def _build_corpus(self):
        """Load all documents, build BM25 index, and populate ChromaDB if empty."""
        chunks: List[Dict] = []

        # 1. rules.json
        chunks.extend(self._chunks_from_rules())

        # 2. DriveLegalKB (violations + FAQs + state rules) — schema v2 dataset
        if _HAS_KB:
            chunks.extend(self._chunks_from_kb())

        if not chunks:
            logger.warning("No documents available for indexing.")
            return

        self.documents = chunks

        # BM25 — always rebuilt in-memory
        tokenized = [_tokenize(c["text"]) for c in chunks]
        self.bm25  = BM25Okapi(tokenized)

        # ChromaDB — repopulate when empty OR when rules.json is newer than the
        # stored collection (catches rule edits without manual cache deletion).
        needs_rebuild = self.collection.count() == 0
        if not needs_rebuild:
            try:
                rules_mtime = os.path.getmtime(self.rules_path)
                stamp_path  = os.path.join(self.persist_directory, ".rules_mtime")
                stored_mtime = float(open(stamp_path).read()) if os.path.exists(stamp_path) else 0
                if rules_mtime > stored_mtime:
                    logger.info("rules.json changed — rebuilding ChromaDB index.")
                    self.client.delete_collection(self.collection.name)
                    self.collection = self.client.get_or_create_collection(
                        name=self.collection.name,
                        embedding_function=self.embedding_function,
                    )
                    needs_rebuild = True
            except Exception as e:
                logger.warning("Staleness check failed: %s", e)

        if needs_rebuild:
            self._chroma_add(chunks)
            try:
                os.makedirs(self.persist_directory, exist_ok=True)
                with open(os.path.join(self.persist_directory, ".rules_mtime"), "w") as f:
                    f.write(str(os.path.getmtime(self.rules_path)))
            except Exception as e:
                logger.warning("Could not write mtime stamp: %s", e)

    def _chunks_from_rules(self) -> List[Dict]:
        """Convert rules.json entries to indexable chunks."""
        if not os.path.exists(self.rules_path):
            return []

        try:
            with open(self.rules_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error("Failed to read rules.json: %s", e)
            return []

        chunks = []
        for rule in data.get("rules", []):
            rid   = _safe_text(rule.get("rule_id"))
            if not rid:
                continue

            tags_str = ", ".join(rule.get("tags", []))
            text = " ".join([
                _safe_text(rule.get("title")),
                _safe_text(rule.get("description")),
                tags_str,
                _safe_text(rule.get("section")),
            ]).strip()

            # Detect country from rule context
            country = "IN"
            if rid.startswith("MV_"):
                country = "IN"
            else:
                act_text = _safe_text(rule.get("act", "")).lower()
                if any(k in act_text for k in ["minnesota", "texas", "usa", "america", "us "]):
                    country = "US"
                elif any(k in act_text for k in ["singapore", "sg "]):
                    country = "SG"
                elif any(k in act_text for k in ["united kingdom", "uk ", "london"]):
                    country = "GB"
                elif any(k in act_text for k in ["emirates", "uae", "dubai"]):
                    country = "AE"
                
                # Fallback to title-based detection if act is generic
                if country == "IN":
                    detected = detect_country(text, default="IN")
                    country = detected

            chunks.append({
                "id":       rid,
                "text":     text or rid,
                "metadata": {
                    "section":  _safe_text(rule.get("section")),
                    "title":    _safe_text(rule.get("title")),
                    "source":   "rules_json",
                    "country":  country,
                },
            })
        return chunks

    def _chunks_from_kb(self) -> List[Dict]:
        """Build chunks from DriveLegalKB (violations + FAQs + state rules)."""
        try:
            kb     = DriveLegalKB()
            raw    = kb.get_all_chunks()
        except Exception as e:
            logger.error("DriveLegalKB failed: %s", e)
            return []

        chunks = []
        seen_ids: set = set()
        for item in raw:
            cid = _safe_text(item.get("id"))
            if not cid or cid in seen_ids:
                continue
            seen_ids.add(cid)

            text = _safe_text(item.get("text"))
            meta = item.get("metadata", {}) or {}
            # Flatten list values so ChromaDB accepts them (str/int/float/bool only)
            clean_meta: Dict[str, Any] = {}
            for k, v in meta.items():
                if isinstance(v, list):
                    clean_meta[k] = ", ".join(str(i) for i in v)
                elif isinstance(v, bool):
                    clean_meta[k] = str(v)
                else:
                    clean_meta[k] = v
            # Detect country for KB chunks (mostly IN, but good to be safe)
            country = detect_country(text, default="IN")
            clean_meta["country"] = country
            clean_meta.setdefault("source", "drivelegal_kb")

            chunks.append({"id": cid, "text": text or cid, "metadata": clean_meta})
        return chunks

    def _chroma_add(self, chunks: List[Dict]):
        """Batch-add chunks to ChromaDB, skipping any with duplicate IDs."""
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            try:
                self.collection.add(
                    ids=       [c["id"]       for c in batch],
                    documents= [c["text"]     for c in batch],
                    metadatas= [c["metadata"] for c in batch],
                )
            except Exception as e:
                logger.warning("ChromaDB batch add failed (batch %d): %s", i // batch_size, e)

    # ── Search ────────────────────────────────────────────────────────────────

    def search(self, query: str, top_k: int = 3, country: str = "IN") -> List[Dict]:
        """
        Hybrid search: vector results (ranked by position) merged with BM25 results.
        Returns at most top_k unique results sorted by combined score (descending).
        Filters by country to ensure relevant legal context.
        """
        # Multilingual Translation Fallback
        original_query = query
        query = self.translate_query_to_english(query)
        if query != original_query:
            logger.info("Translated search query: '%s' -> '%s'", original_query, query)

        results: Dict[str, Dict] = {}   # chunk_id → result entry

        # 1. Vector search
        if self.embedding_function and self.collection.count() > 0:
            try:
                vr = self.collection.query(
                    query_texts=[query], 
                    n_results=min(top_k * 2, self.collection.count()),
                    where={"country": country}
                )
                ids   = (vr.get("ids")       or [[]])[0]
                metas = (vr.get("metadatas") or [[]])[0]
                docs  = (vr.get("documents") or [[]])[0]
                for rank, (cid, meta, doc) in enumerate(zip(ids, metas, docs)):
                    score = 1.0 / (rank + 1)
                    # Boost structured MV Act rules (MV_NNN format only).
                    # Old-format IDs like MV177 are catch-all dataset entries and
                    # should not be over-ranked on generic queries.
                    if cid.startswith("MV_"):
                        score *= 5.0

                    results[cid] = {
                        "rule_id":  cid,
                        "score":    score,
                        "metadata": meta or {},
                        "content":  _safe_text(doc),
                        "source":   "vector",
                    }
            except Exception as e:
                logger.warning("Vector search failed: %s", e)

        # 2. BM25 search
        if self.bm25 and self.documents:
            try:
                tokenized_query = _tokenize(query)
                scores          = self.bm25.get_scores(tokenized_query)
                top_indices     = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
                for idx in top_indices:
                    doc   = self.documents[idx]
                    cid   = doc["id"]
                    meta  = doc.get("metadata", {})
                    
                    # Filter by country for BM25 results
                    if meta.get("country") != country:
                        continue

                    bscore = float(scores[idx]) / max(10.0, float(scores[idx]) + 1e-9)
                    # Same rule: only boost structured MV_NNN IDs.
                    if cid.startswith("MV_"):
                        bscore *= 5.0

                    if cid in results:
                        # Boost combined score
                        results[cid]["score"] += bscore * 0.5
                    else:
                        results[cid] = {
                            "rule_id":  cid,
                            "score":    bscore,
                            "metadata": meta,
                            "content":  doc.get("text", ""),
                            "source":   "lexical",
                        }
            except Exception as e:
                logger.warning("BM25 search failed: %s", e)

        return sorted(results.values(), key=lambda x: x["score"], reverse=True)[:top_k]
