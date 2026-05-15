#!/usr/bin/env python3
"""
DriveLegal Data Ingestion Pipeline
------------------------------------
Inputs:  backend/data/raw/pdfs/  (text-based and scanned PDFs)
         backend/data/raw/csv/   (Kaggle / any traffic-fine CSVs)
Outputs: backend/data/processed/mv_act_sections.json
         backend/data/processed/mv_act_sections_hindi.json
         backend/data/processed/{stem}_cleaned.json     (one per CSV)
         backend/data/processed/validation_errors.log
Updates: backend/data/rules.json

Dependencies:
  pip install pdfplumber pytesseract pdf2image
  (tesseract-ocr binary must be installed separately for OCR)
"""

from __future__ import annotations

import csv
import datetime
import json
import logging
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

# ─── Tesseract / Poppler paths (Windows) ──────────────────────────────────────
# Adjust if your installations differ.
_TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
_POPPLER_PATH = (
    r"C:\Users\USER\AppData\Local\Microsoft\WinGet\Packages"
    r"\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\poppler-25.07.0\Library\bin"
)

# ─── Paths ────────────────────────────────────────────────────────────────────

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
RAW_PDFS_DIR = DATA_DIR / "raw" / "pdfs"
RAW_CSV_DIR = DATA_DIR / "raw" / "csv"
PROCESSED_DIR = DATA_DIR / "processed"
RULES_JSON_PATH = DATA_DIR / "rules.json"
VALIDATION_LOG_PATH = PROCESSED_DIR / "validation_errors.log"

for _d in (RAW_PDFS_DIR, RAW_CSV_DIR, PROCESSED_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ─── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("ingest")

# Validation error lines collected throughout; written to file at the end.
_val_errors: list[str] = []

# ─── Known MV Act offence sections (2019 Amendment) ──────────────────────────

KNOWN_MV_SECTIONS: frozenset[str] = frozenset({
    "177", "177A",
    "179", "180", "181", "182", "182A",
    "183", "184", "185", "186", "187", "188", "189",
    "190", "191", "192", "192A", "193",
    "194", "194A", "194B", "194C", "194D", "194E",
    "196", "197", "199", "199A", "201",
    "206", "207", "208", "210B",
})

# ─── Compiled regexes ─────────────────────────────────────────────────────────

# Section / Rule / Chapter boundary markers inside extracted text
_BOUNDARY_RE = re.compile(
    r"(?:^|\n)[ \t]*"
    r"(?:"
    r"(?:Section|SECTION|Sec\.)[ \t]+(\d+[A-Z]?(?:[ \t]*\(\d+\))?)"  # Section 183
    r"|धारा[ \t]+(\d+[A-Z]?)"                                          # Hindi धारा 183
    r"|(?:Rule|RULE)[ \t]+(\d+[A-Z]?)"                                 # Rule 12
    r"|Chapter[ \t]+([IVX]+(?:\b|$))"                                  # Chapter XIV
    r")",
    re.MULTILINE,
)

# Fine amounts: ₹1,000 / Rs. 5000 / INR 2000 / fine of 1500
_FINE_RE = re.compile(
    r"(?:"
    r"(?:₹|Rs\.?\s*|INR\s*)(\d{1,3}(?:,\d{3})*(?:\.\d+)?)"
    r"|fine\s+of\s+(?:₹|Rs\.?\s*|INR\s*)?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)"
    r"|(\d{1,3}(?:,\d{3})+)\s*(?:rupees|INR)\b"
    r")",
    re.IGNORECASE,
)

# Page number lines: standalone digits, optionally dashed
_PAGE_NUM_RE = re.compile(r"^\s*[-–]?\s*\d+\s*[-–]?\s*$")

# Hyphenated line-wrap: "driv-\ning" -> "driving"
_HYPHEN_WRAP_RE = re.compile(r"(\w)-\n(\w)")

# Devanagari code block (Hindi / Sanskrit)
_DEVANAGARI_RE = re.compile(r"[ऀ-ॿ]")

# ─── Vehicle-type normalisation ───────────────────────────────────────────────

_LMV_ALIASES: frozenset[str] = frozenset({
    "car", "cars", "lmv", "4-wheeler", "4 wheeler", "four-wheeler",
    "four wheeler", "private car", "sedan", "suv", "hatchback",
    "automobile", "motor car", "light motor vehicle", "light vehicle",
    "jeep", "van", "mpv",
})
_HGV_ALIASES: frozenset[str] = frozenset({
    "truck", "lorry", "hgv", "mgv", "hmv", "heavy vehicle", "heavy goods vehicle",
    "medium goods vehicle", "medium vehicle", "goods vehicle", "bus",
    "mini bus", "minibus", "transport vehicle", "commercial vehicle",
})
_TWO_WHEELER_ALIASES: frozenset[str] = frozenset({
    "motorcycle", "motorbike", "bike", "scooter", "moped",
    "two-wheeler", "two wheeler", "2-wheeler", "2wheeler", "2w",
    "motor cycle", "moto",
})
_THREE_WHEELER_ALIASES: frozenset[str] = frozenset({
    "auto", "auto-rickshaw", "autorickshaw", "three-wheeler", "three wheeler",
    "3-wheeler", "3wheeler", "3w", "rickshaw", "e-rickshaw",
})


def normalise_vehicle(raw: str) -> str:
    v = raw.strip().lower()
    if v in _LMV_ALIASES:
        return "lmv"
    if v in _HGV_ALIASES:
        return "hgv"
    if v in _TWO_WHEELER_ALIASES:
        return "two_wheeler"
    if v in _THREE_WHEELER_ALIASES:
        return "three_wheeler"
    if v in ("all", "any", ""):
        return "all"
    # Partial matching for compound strings like "LMV/Car" or "HGV/MGV"
    if any(a in v for a in ("lmv", "car", "sedan")):
        return "lmv"
    if any(a in v for a in ("hgv", "mgv", "hmv", "truck", "bus")):
        return "hgv"
    if any(a in v for a in ("two", "bike", "scooter", "moto", "2w")):
        return "two_wheeler"
    return v


# ─── Currency / fine parsing ──────────────────────────────────────────────────

_CURRENCY_MAP: dict[str, str] = {
    "₹": "INR", "rs": "INR", "rs.": "INR", "inr": "INR",
    "aed": "AED", "sgd": "SGD", "$": "USD", "usd": "USD",
    "£": "GBP", "gbp": "GBP", "€": "EUR", "eur": "EUR",
}
_CURRENCY_RE = re.compile(
    r"([₹$£€]|(?:rs\.?|INR|AED|SGD|USD|GBP|EUR)\b)?\s*([\d,]+(?:\.\d+)?)\s*"
    r"([₹$£€]|(?:rs\.?|INR|AED|SGD|USD|GBP|EUR)\b)?",
    re.IGNORECASE,
)


def parse_currency_str(raw: str) -> tuple[Optional[float], str]:
    """Return (amount, currency_code), or (None, '') if the string is unparseable."""
    m = _CURRENCY_RE.search(raw.strip())
    if not m:
        return None, ""
    prefix = (m.group(1) or "").strip().lower()
    suffix = (m.group(3) or "").strip().lower()
    numeric = m.group(2).replace(",", "")
    try:
        amount = float(numeric)
    except ValueError:
        return None, ""
    currency = _CURRENCY_MAP.get(prefix) or _CURRENCY_MAP.get(suffix) or "INR"
    return amount, currency


def parse_fine_range(raw: str) -> tuple[Optional[int], Optional[int]]:
    """'1000-2000' -> (1000, 2000).  '5000' -> (5000, 5000).  Else (None, None)."""
    clean = raw.strip().replace(",", "")
    m = re.match(r"^(\d+)\s*[-–]\s*(\d+)$", clean)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.match(r"^(\d+)$", clean)
    if m:
        v = int(m.group(1))
        return v, v
    return None, None


# ─── Section ID normalisation ─────────────────────────────────────────────────

def normalise_section_id(raw: str) -> str:
    """'182 A' -> '182A'   '183(1)' -> '183'   ' 177 ' -> '177'"""
    sid = re.sub(r"\(.*?\)", "", raw)               # drop sub-section notation
    sid = re.sub(r"(\d+)\s+([A-Za-z])", r"\1\2", sid)  # "182 A" -> "182A"
    return re.sub(r"\s+", "", sid).upper()


# ──────────────────────────────────────────────────────────────────────────────
# PDF PROCESSING
# ──────────────────────────────────────────────────────────────────────────────

def _load_pdfplumber():
    try:
        import pdfplumber
        return pdfplumber
    except ImportError:
        log.error("pdfplumber not installed — run: pip install pdfplumber")
        return None


def _load_ocr():
    try:
        import pytesseract
        from pdf2image import convert_from_path as _cfp

        # Configure tesseract binary path if it exists on Windows
        if os.path.exists(_TESSERACT_PATH):
            pytesseract.pytesseract.tesseract_cmd = _TESSERACT_PATH

        return pytesseract, _cfp
    except ImportError as exc:
        log.warning(
            f"OCR dependencies missing ({exc}); scanned PDFs will be skipped.\n"
            "  Run: pip install pytesseract pdf2image\n"
            "  (also install the tesseract-ocr binary)"
        )
        return None, None


def is_text_based(pdf_path: Path, pdfplumber) -> bool:
    """True if pdfplumber extracts >100 chars/page on average (samples first 3 pages)."""
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            sample = pdf.pages[:3]
            if not sample:
                return False
            total = sum(len(p.extract_text() or "") for p in sample)
            return (total / len(sample)) > 100
    except Exception as exc:
        log.warning(f"pdfplumber could not probe {pdf_path.name}: {exc}")
        return False


def extract_text_pages(pdf_path: Path, pdfplumber) -> list[dict]:
    pages: list[dict] = []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                pages.append({"page": i, "text": page.extract_text() or ""})
    except Exception as exc:
        log.error(f"pdfplumber extraction failed for {pdf_path.name}: {exc}")
    return pages


def extract_scanned_pages(
    pdf_path: Path,
    pytesseract,
    convert_from_path,
    lang: str = "eng+hin",
) -> list[dict]:
    pages: list[dict] = []
    try:
        poppler_path = _POPPLER_PATH if os.path.isdir(_POPPLER_PATH) else None
        images = convert_from_path(str(pdf_path), dpi=300, poppler_path=poppler_path)
    except Exception as exc:
        log.error(f"pdf2image failed for {pdf_path.name}: {exc}")
        return pages
    for i, img in enumerate(images, 1):
        try:
            text = pytesseract.image_to_string(img, lang=lang)
        except Exception as exc:
            log.warning(f"OCR failed on page {i} of {pdf_path.name}: {exc}")
            text = ""
        pages.append({"page": i, "text": text})
    return pages


# --- Cleaning helpers ---------------------------------------------------------

def _repeated_lines(pages: list[dict], threshold: int = 3) -> set[str]:
    """Return lines that appear on ≥ threshold pages (headers / footers)."""
    counter: Counter = Counter()
    for p in pages:
        seen = {ln.strip() for ln in p["text"].splitlines() if ln.strip()}
        counter.update(seen)
    return {ln for ln, cnt in counter.items() if cnt >= threshold}


def clean_pages(pages: list[dict]) -> list[dict]:
    """Remove boilerplate & page numbers; fix hyphenation; normalise whitespace."""
    boilerplate = _repeated_lines(pages)
    cleaned: list[dict] = []
    for p in pages:
        kept: list[str] = []
        for ln in p["text"].splitlines():
            stripped = ln.strip()
            if not stripped:
                kept.append("")
                continue
            if stripped in boilerplate:
                continue
            if _PAGE_NUM_RE.match(stripped):
                continue
            kept.append(ln)
        text = "\n".join(kept)
        text = _HYPHEN_WRAP_RE.sub(r"\1\2", text)          # fix word-wrap hyphens
        text = re.sub(r"[ \t]{2,}", " ", text)              # collapse inline spaces
        text = re.sub(r"\n{3,}", "\n\n", text)              # collapse blank lines
        cleaned.append({"page": p["page"], "text": text.strip()})
    return cleaned


# --- Section parsing helpers --------------------------------------------------

def _build_full_text(pages: list[dict]) -> tuple[str, list[tuple[int, int, int]]]:
    """Return (full_text, page_map) where page_map = [(page_num, start, end), ...]."""
    parts: list[str] = []
    page_map: list[tuple[int, int, int]] = []
    pos = 0
    for p in pages:
        t = p["text"]
        page_map.append((p["page"], pos, pos + len(t)))
        parts.append(t)
        pos += len(t) + 2  # two-char '\n\n' separator
    return "\n\n".join(parts), page_map


def _pages_for_span(
    start: int, end: int, page_map: list[tuple[int, int, int]]
) -> list[int]:
    return [pnum for pnum, pstart, pend in page_map
            if pstart < end and pend > start]


def _parse_header(line: str) -> tuple[str, str]:
    """'Section 183 – Driving at excessive speed' -> ('183', 'Driving…')"""
    m = re.match(
        r"Section[ \t]+(\d+[A-Z]?(?:[ \t]*\(\d+\))?)\s*[.–\-—:]\s*(.*)",
        line, re.IGNORECASE,
    )
    if m:
        return normalise_section_id(m.group(1)), m.group(2).strip()
    m = re.match(r"Section[ \t]+(\d+[A-Z]?)", line, re.IGNORECASE)
    if m:
        return normalise_section_id(m.group(1)), ""
    return "", line.strip()


def _extract_fines_from_text(text: str, vehicle_hint: str = "all") -> list[dict]:
    records: list[dict] = []
    seen: set[float] = set()
    for m in _FINE_RE.finditer(text):
        raw = (m.group(1) or m.group(2) or m.group(3) or "").replace(",", "")
        try:
            amount = float(raw)
        except ValueError:
            continue
        if amount <= 0 or amount in seen:
            continue
        seen.add(amount)
        records.append({"type": vehicle_hint, "amount": int(amount), "currency": "INR"})
    return records


def _infer_penalties(text: str) -> list[str]:
    tl = text.lower()
    penalties: list[str] = []
    if re.search(r"\bfine\b|\bpenalty\b|\bchallan\b|जुर्माना", tl):
        penalties.append("fine")
    if re.search(r"\bimprisonment\b|\bjail\b|\bcustody\b|कारावास", tl):
        penalties.append("imprisonment")
    if re.search(r"\bsuspend|\bcancell?ation\b|\bdisqualif", tl):
        penalties.append("licence_action")
    if re.search(r"\bimpound\b|\bseize\b", tl):
        penalties.append("vehicle_seizure")
    return penalties or ["fine"]


def parse_mv_act_sections(pages: list[dict], source_file: str) -> list[dict]:
    """Segment the cleaned, full text into per-section dicts."""
    full_text, page_map = _build_full_text(pages)

    # Collect all boundary positions
    boundaries: list[tuple[int, str]] = []
    for m in _BOUNDARY_RE.finditer(full_text):
        raw_id = (m.group(1) or m.group(2) or m.group(3) or "").strip()
        chapter = (m.group(4) or "").strip()
        if raw_id:
            label = normalise_section_id(raw_id)
        else:
            label = f"CHAPTER_{chapter}"
        boundaries.append((m.start(), label))

    if not boundaries:
        return []

    sections: list[dict] = []
    for idx, (start, label) in enumerate(boundaries):
        end = boundaries[idx + 1][0] if idx + 1 < len(boundaries) else len(full_text)
        body = full_text[start:end].strip()

        lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
        sec_id, title = _parse_header(lines[0]) if lines else ("", "")
        if not sec_id:
            sec_id = label
        if not title and len(lines) > 1:
            title = lines[1][:200]

        span_pages = _pages_for_span(start, end, page_map)
        fines = _extract_fines_from_text(body)
        penalties = _infer_penalties(body)
        language = "hi" if _DEVANAGARI_RE.search(body) else "en"

        sections.append({
            "section_id": sec_id,
            "section_title": title or f"Section {sec_id}",
            "section_text": body,
            "penalties": penalties,
            "extracted_fines": fines,
            "language": language,
            "source_file": source_file,
            "page_numbers": sorted(set(span_pages)),
        })

    return sections


# --- Main PDF driver ----------------------------------------------------------

def process_pdfs() -> tuple[list[dict], list[dict], int]:
    """Process all PDFs in RAW_PDFS_DIR.

    Returns: (english_sections, hindi_sections, pdf_count)
    """
    pdfplumber = _load_pdfplumber()
    pytesseract, convert_from_path = _load_ocr()

    en_sections: list[dict] = []
    hi_sections: list[dict] = []
    pdf_count = 0

    pdf_files = sorted(RAW_PDFS_DIR.glob("*.pdf"))
    if not pdf_files:
        log.warning(
            f"No PDFs found in {RAW_PDFS_DIR}\n"
            f"  Copy PDF files there, e.g.:\n"
            f"  xcopy backend\\data\\drivelegal_dataset\\*.pdf {RAW_PDFS_DIR}\\"
        )
        return en_sections, hi_sections, 0

    for pdf_path in pdf_files:
        log.info(f"Processing PDF: {pdf_path.name}")
        pdf_count += 1
        pages: list[dict] = []

        if pdfplumber and is_text_based(pdf_path, pdfplumber):
            log.info("  -> text-based PDF, using pdfplumber")
            pages = extract_text_pages(pdf_path, pdfplumber)
        elif pytesseract and convert_from_path:
            log.info("  -> scanned PDF, using pytesseract (eng+hin)")
            pages = extract_scanned_pages(
                pdf_path, pytesseract, convert_from_path, lang="eng+hin"
            )
        else:
            log.warning(
                f"  -> skipping {pdf_path.name}: "
                "no suitable extractor available (install pdfplumber / pytesseract)"
            )
            continue

        if not pages:
            log.warning(f"  -> no text extracted from {pdf_path.name}")
            continue

        cleaned = clean_pages(pages)
        sections = parse_mv_act_sections(cleaned, pdf_path.name)
        log.info(f"  -> {len(sections)} sections extracted")

        for sec in sections:
            if sec["language"] == "hi":
                hi_sections.append({
                    "section_id": sec["section_id"],
                    "section_title": sec["section_title"],
                    "section_text": sec["section_text"],
                    "language": "hi",
                    "english_equivalent_id": sec["section_id"],
                })
            else:
                en_sections.append(sec)

        # Extra Hindi-only OCR pass when Devanagari was found in the bilingual pass
        has_devanagari = any(_DEVANAGARI_RE.search(p["text"]) for p in cleaned)
        if has_devanagari and pytesseract and convert_from_path:
            log.info("  -> Devanagari detected, running hin-only OCR pass")
            hin_pages = extract_scanned_pages(
                pdf_path, pytesseract, convert_from_path, lang="hin"
            )
            if hin_pages:
                hin_cleaned = clean_pages(hin_pages)
                for hs in parse_mv_act_sections(hin_cleaned, pdf_path.name):
                    hi_sections.append({
                        "section_id": hs["section_id"],
                        "section_title": hs["section_title"],
                        "section_text": hs["section_text"],
                        "language": "hi",
                        "english_equivalent_id": hs["section_id"],
                    })
                log.info(f"  -> {len(hin_pages)} pages processed in Hindi pass")

    return en_sections, hi_sections, pdf_count


# ──────────────────────────────────────────────────────────────────────────────
# CSV PROCESSING
# ──────────────────────────────────────────────────────────────────────────────

# Maps raw CSV header names -> canonical field names
_COL_ALIASES: dict[str, str] = {
    # violation name
    "violation_name": "violation_name",
    "violation_type": "violation_name",
    "violation": "violation_name",
    "offence": "violation_name",
    "offence_name": "violation_name",
    "offense_name": "violation_name",
    "offense": "violation_name",
    "offense_type": "violation_name",
    "description": "violation_name",
    "challantype": "violation_name",
    "challan_type": "violation_name",
    "traffic_violation_type": "violation_name",
    "type_of_violation": "violation_name",
    # vehicle type
    "vehicle_type": "vehicle_type",
    "vehicletype": "vehicle_type",
    "vehicle": "vehicle_type",
    "vehicle_class": "vehicle_type",
    "vehicleclass": "vehicle_type",
    "vehicle_category": "vehicle_type",
    # fine amount
    "fine_amount": "fine_amount",
    "fine_amount_inr": "fine_amount",
    "amount": "fine_amount",
    "amount_inr": "fine_amount",
    "penalty_amount": "fine_amount",
    "fine": "fine_amount",
    "challan_amount": "fine_amount",
    "totalamount": "fine_amount",
    "total_amount": "fine_amount",
    "penalty": "fine_amount",
    "fine_inr": "fine_amount",
    # state / province
    "state": "state_province",
    "state_province": "state_province",
    "province": "state_province",
    "state_code": "state_province",
    "region": "state_province",
    "registration_state": "state_province",
    "issuing_state": "state_province",
    "location_state": "state_province",
    # country
    "country": "country",
    # section reference
    "section": "section_reference",
    "section_reference": "section_reference",
    "section_ref": "section_reference",
    "law_section": "section_reference",
    "act_section": "section_reference",
    "legal_section": "section_reference",
    # offence code
    "offence_code": "offence_code",
    "offense_code": "offence_code",
    "violation_code": "offence_code",
    "violation_id": "offence_code",
    # source URL (authority scoring only)
    "source_url": "source_url",
}

_SOURCE_PRIORITY: dict[str, int] = {
    "parivahan.gov.in": 3,
    "morth": 2,
    "tnsta": 2,
    "official": 2,
    "kaggle": 1,
}


def _map_columns(raw_headers: list[str]) -> dict[str, str]:
    """Return {raw_header: canonical_name} for recognised headers."""
    return {
        h: _COL_ALIASES[h.strip().lower().replace(" ", "_")]
        for h in raw_headers
        if h.strip().lower().replace(" ", "_") in _COL_ALIASES
    }


def _source_score(url: str) -> int:
    lower = url.lower()
    for keyword, score in _SOURCE_PRIORITY.items():
        if keyword in lower:
            return score
    return 0


def _parse_csv_row(
    row: dict,
    col_map: dict[str, str],
    row_num: int,
    source_name: str,
) -> dict:
    rec: dict = {
        "violation_name": None,
        "vehicle_type": None,
        "fine_amount": None,
        "min_fine": None,
        "max_fine": None,
        "currency": "INR",
        "state_province": None,
        "country": "IN",
        "section_reference": None,
        "offence_code": None,
        "source_file": source_name,
        "source_priority": 1,
    }

    for raw_col, canon in col_map.items():
        raw_val = (row.get(raw_col) or "").strip()

        if canon == "source_url":
            rec["source_priority"] = _source_score(raw_val)
            continue

        if not raw_val:
            if canon == "violation_name":
                msg = f"WARNING CSV {source_name}:row{row_num} missing violation_name"
                log.warning(f"  {msg}")
                _val_errors.append(msg)
            continue

        if canon == "violation_name":
            rec["violation_name"] = raw_val

        elif canon == "vehicle_type":
            rec["vehicle_type"] = normalise_vehicle(raw_val)

        elif canon == "fine_amount":
            # Strip currency symbols before range detection
            plain = re.sub(
                r"[₹$£€]|(?:rs\.?|INR|AED|SGD|USD|GBP|EUR)\b",
                "", raw_val, flags=re.IGNORECASE,
            ).strip()
            lo, hi = parse_fine_range(plain)
            if lo is not None:
                rec["min_fine"] = lo
                rec["max_fine"] = hi
                rec["fine_amount"] = lo
            else:
                amount, currency = parse_currency_str(raw_val)
                if amount is not None:
                    rec["fine_amount"] = int(amount)
                    rec["min_fine"] = int(amount)
                    rec["max_fine"] = int(amount)
                    rec["currency"] = currency
                else:
                    msg = (
                        f"WARNING CSV {source_name}:row{row_num} "
                        f"unparseable fine '{raw_val}'"
                    )
                    log.warning(f"  {msg}")
                    _val_errors.append(msg)

        elif canon == "state_province":
            rec["state_province"] = raw_val
        elif canon == "country":
            rec["country"] = raw_val
        elif canon == "section_reference":
            rec["section_reference"] = raw_val
        elif canon == "offence_code":
            rec["offence_code"] = raw_val

    return rec


def process_csv_file(csv_path: Path) -> list[dict]:
    records: list[dict] = []

    try:
        with open(csv_path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            if not reader.fieldnames:
                log.warning(f"  {csv_path.name}: no headers, skipping")
                return []

            col_map = _map_columns(list(reader.fieldnames))
            if not col_map:
                log.warning(
                    f"  {csv_path.name}: no recognised columns "
                    f"(headers: {list(reader.fieldnames)[:8]})"
                )

            for row_num, row in enumerate(reader, 2):
                rec = _parse_csv_row(row, col_map, row_num, csv_path.name)
                records.append(rec)

    except Exception as exc:
        log.error(f"  Failed to read {csv_path.name}: {exc}")
        return []

    # Deduplication: same (violation_name, vehicle_type, state_province) ->
    # keep the record from the highest-authority source.
    dedup: dict[tuple, dict] = {}
    for rec in records:
        key = (
            (rec["violation_name"] or "").lower(),
            rec["vehicle_type"] or "",
            (rec["state_province"] or "").lower(),
        )
        existing = dedup.get(key)
        if existing is None or rec["source_priority"] > existing["source_priority"]:
            dedup[key] = rec

    result = list(dedup.values())
    log.info(f"  {csv_path.name}: {len(records)} rows -> {len(result)} after dedup")
    return result


def process_csvs() -> tuple[dict[str, list[dict]], int]:
    """Process all CSVs in RAW_CSV_DIR.

    Returns: ({stem: records}, csv_count)
    """
    all_records: dict[str, list[dict]] = {}
    csv_count = 0

    csv_files = sorted(RAW_CSV_DIR.glob("*.csv"))
    if not csv_files:
        log.warning(
            f"No CSVs found in {RAW_CSV_DIR}\n"
            f"  Copy CSV files there, e.g.:\n"
            f"  copy backend\\data\\*.csv {RAW_CSV_DIR}\\"
        )
        return all_records, 0

    for csv_path in csv_files:
        log.info(f"Processing CSV: {csv_path.name}")
        csv_count += 1
        records = process_csv_file(csv_path)
        all_records[csv_path.stem] = records

        out_path = PROCESSED_DIR / f"{csv_path.stem}_cleaned.json"
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(records, fh, indent=2, ensure_ascii=False)
        log.info(f"  Saved -> {out_path.name}")

    return all_records, csv_count


# ──────────────────────────────────────────────────────────────────────────────
# VALIDATION
# ──────────────────────────────────────────────────────────────────────────────

def validate_all(
    en_sections: list[dict],
    hi_sections: list[dict],
    csv_map: dict[str, list[dict]],
) -> int:
    """Run all validation checks; append errors to _val_errors; write log file."""

    # English sections
    for sec in en_sections:
        sid = sec.get("section_id", "")
        if sid and sid not in KNOWN_MV_SECTIONS:
            _val_errors.append(
                f"UNKNOWN_SECTION id='{sid}' source='{sec.get('source_file')}'"
            )
        for fine in sec.get("extracted_fines", []):
            amt = fine.get("amount")
            if not isinstance(amt, (int, float)) or amt <= 0:
                _val_errors.append(
                    f"INVALID_FINE section='{sid}' fine={fine} "
                    f"source='{sec.get('source_file')}'"
                )

    # Hindi sections (IDs only)
    for hs in hi_sections:
        sid = hs.get("section_id", "")
        if sid and sid not in KNOWN_MV_SECTIONS:
            _val_errors.append(f"UNKNOWN_SECTION(HI) id='{sid}'")

    # CSV records
    for stem, records in csv_map.items():
        for i, rec in enumerate(records):
            fa = rec.get("fine_amount")
            if fa is not None and (not isinstance(fa, (int, float)) or fa <= 0):
                _val_errors.append(
                    f"INVALID_FINE CSV='{stem}' row={i} fine_amount={fa}"
                )

    with open(VALIDATION_LOG_PATH, "w", encoding="utf-8") as fh:
        if _val_errors:
            fh.write("\n".join(_val_errors) + "\n")
        else:
            fh.write("No validation errors.\n")

    return len(_val_errors)


# ──────────────────────────────────────────────────────────────────────────────
# RULES.JSON UPDATE
# ──────────────────────────────────────────────────────────────────────────────

def _section_to_rule(sec: dict) -> dict:
    """Convert an extracted MV Act section into a rules.json entry."""
    sid = sec["section_id"]
    amounts = sorted(
        f["amount"] for f in sec.get("extracted_fines", [])
        if isinstance(f.get("amount"), (int, float)) and f["amount"] > 0
    )

    national_fine: dict = {}
    if amounts:
        national_fine["first_offence"] = {
            "fine_min": amounts[0],
            "fine_max": amounts[-1],
        }
        if len(amounts) >= 2:
            national_fine["subsequent"] = {
                "fine_min": amounts[1],
                "fine_max": amounts[-1],
            }

    description = (sec.get("section_text") or "")[:500].replace("\n", " ").strip()

    return {
        "rule_id": f"MV_{sid}",
        "section": f"Section {sid}",
        "act": "Motor Vehicles (Amendment) Act 2019",
        "title": sec.get("section_title", f"Section {sid}"),
        "description": description,
        "applies_to": ["ALL"],
        "vehicle_classes": ["ALL"],
        "compoundable": "imprisonment" not in sec.get("penalties", []),
        "compounding_fee": None,
        "imprisonment": "imprisonment" in sec.get("penalties", []),
        "national_fine": national_fine,
        "state_overrides": [],
        "related_offence_codes": [],
        "penalty_ref": f"MV_{sid}_FINE",
        "source_file": sec.get("source_file", ""),
        "page_numbers": sec.get("page_numbers", []),
    }


def _csv_row_to_rule(stem: str, idx: int, rec: dict) -> dict:
    vname = rec.get("violation_name") or "Unknown Violation"
    return {
        "rule_id": f"CSV_{stem}_{idx}",
        "section": rec.get("section_reference") or "",
        "act": "Motor Vehicles (Amendment) Act 2019",
        "title": vname,
        "description": vname,
        "applies_to": [rec.get("vehicle_type") or "ALL"],
        "vehicle_classes": [rec.get("vehicle_type") or "ALL"],
        "compoundable": True,
        "compounding_fee": None,
        "imprisonment": False,
        "national_fine": {
            "first_offence": {
                "fine_min": rec.get("min_fine") or rec.get("fine_amount") or 0,
                "fine_max": rec.get("max_fine") or rec.get("fine_amount") or 0,
            }
        },
        "state_overrides": (
            [{
                "state": rec["state_province"],
                "description": f"State fine: {rec['fine_amount']} {rec['currency']}",
                "effective_date": None,
            }]
            if rec.get("state_province") else []
        ),
        "related_offence_codes": (
            [rec["offence_code"]] if rec.get("offence_code") else []
        ),
        "penalty_ref": f"CSV_{stem}_{idx}",
        "source_file": rec.get("source_file", ""),
    }


def update_rules_json(
    en_sections: list[dict],
    csv_map: dict[str, list[dict]],
) -> None:
    try:
        with open(RULES_JSON_PATH, "r", encoding="utf-8") as fh:
            rules_data = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        rules_data = {"schema_version": "1.0", "last_updated": "", "rules": []}

    existing_ids: set[str] = {r["rule_id"] for r in rules_data.get("rules", [])}
    added = 0

    for sec in en_sections:
        rule = _section_to_rule(sec)
        if rule["rule_id"] not in existing_ids:
            rules_data["rules"].append(rule)
            existing_ids.add(rule["rule_id"])
            added += 1

    for stem, records in csv_map.items():
        for idx, rec in enumerate(records):
            rule = _csv_row_to_rule(stem, idx, rec)
            if rule["rule_id"] not in existing_ids:
                rules_data["rules"].append(rule)
                existing_ids.add(rule["rule_id"])
                added += 1

    rules_data["last_updated"] = datetime.date.today().isoformat()

    with open(RULES_JSON_PATH, "w", encoding="utf-8") as fh:
        json.dump(rules_data, fh, indent=2, ensure_ascii=False)

    log.info(
        f"rules.json updated: +{added} new rules "
        f"(total {len(rules_data['rules'])})"
    )


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("DriveLegal Data Ingestion Pipeline")
    print("=" * 60)

    # ── PDFs ──────────────────────────────────────────────────────────────────
    en_sections, hi_sections, pdf_count = process_pdfs()

    mv_out = PROCESSED_DIR / "mv_act_sections.json"
    with open(mv_out, "w", encoding="utf-8") as fh:
        json.dump(en_sections, fh, indent=2, ensure_ascii=False)
    log.info(f"Saved {len(en_sections)} English sections -> {mv_out.name}")

    hi_out = PROCESSED_DIR / "mv_act_sections_hindi.json"
    with open(hi_out, "w", encoding="utf-8") as fh:
        json.dump(hi_sections, fh, indent=2, ensure_ascii=False)
    log.info(f"Saved {len(hi_sections)} Hindi sections -> {hi_out.name}")

    # ── CSVs ──────────────────────────────────────────────────────────────────
    csv_map, csv_count = process_csvs()
    total_csv_records = sum(len(v) for v in csv_map.values())

    # ── Validation ────────────────────────────────────────────────────────────
    error_count = validate_all(en_sections, hi_sections, csv_map)

    # ── Update rules.json ─────────────────────────────────────────────────────
    update_rules_json(en_sections, csv_map)

    # ── Stats ─────────────────────────────────────────────────────────────────
    total_fines = (
        sum(len(s.get("extracted_fines", [])) for s in en_sections)
        + total_csv_records
    )
    langs: set[str] = set()
    for s in en_sections:
        langs.add(s.get("language", "en"))
    if hi_sections:
        langs.add("hi")

    print()
    print("=" * 60)
    print(f"Processed:          {pdf_count} PDFs, {csv_count} CSVs")
    print(
        f"Extracted:          "
        f"{len(en_sections) + len(hi_sections)} sections, "
        f"{total_fines} fine records"
    )
    print(f"Languages detected: {', '.join(sorted(langs)) if langs else 'none'}")
    print(f"Validation errors:  {error_count} (see {VALIDATION_LOG_PATH})")
    print("=" * 60)


if __name__ == "__main__":
    main()
