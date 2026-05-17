#!/usr/bin/env python3
"""
DriveLegal Dataset Merger  v2.0
================================
Merges drivelegal_dataset/* into rules.json (schema v2.0) and seed_fines.csv.

Run from project root:
    python backend/scripts/merge_dataset.py

Outputs:
  backend/data/rules.json       — enriched rules, schema_version "2.0"
  backend/data/seed_fines.csv   — expanded fine table (national + state rows)

After running, reload the database:
    python -m backend.modules.fines.seed
"""

import csv
import hashlib
import json
import os
import re
import shutil
from datetime import date
from typing import Dict, List, Optional, Tuple

# ── Paths ────────────────────────────────────────────────────────────────────
BACKEND_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR     = os.path.join(BACKEND_DIR, "data")
DATASET_DIR  = os.path.join(DATA_DIR, "drivelegal_dataset")
RULES_JSON   = os.path.join(DATA_DIR, "rules.json")
SEED_CSV     = os.path.join(DATA_DIR, "seed_fines.csv")
VECTOR_DB    = os.path.join(DATA_DIR, "vector_db")

# ── Canonical offence-code mappings ──────────────────────────────────────────
# Maps keywords found in violation names / tags → canonical offence_code
TAG_TO_CODE: Dict[str, str] = {
    "no helmet":            "NO_HELMET",
    "helmet":               "NO_HELMET",
    "over speed":           "SPEED_EXCESS",
    "overspeeding":         "SPEED_EXCESS",
    "speeding":             "SPEED_EXCESS",
    "drunk driving":        "DRUNK_DRIVING",
    "drunk":                "DRUNK_DRIVING",
    "alcohol":              "DRUNK_DRIVING",
    "no insurance":         "NO_INSURANCE",
    "insurance":            "NO_INSURANCE",
    "no licence":           "NO_LICENSE",
    "no dl":                "NO_LICENSE",
    "no license":           "NO_LICENSE",
    "license":              "NO_LICENSE",
    "licence":              "NO_LICENSE",
    "signal jump":          "RED_LIGHT_JUMPING",
    "red light":            "RED_LIGHT_JUMPING",
    "mobile phone":         "MOBILE_PHONE",
    "phone":                "MOBILE_PHONE",
    "no seatbelt":          "NO_SEATBELT",
    "seat belt":            "NO_SEATBELT",
    "seatbelt":             "NO_SEATBELT",
    "wrong parking":        "WRONG_PARKING",
    "parking":              "WRONG_PARKING",
    "dangerous":            "DANGEROUS_DRIVING",
    "rash":                 "DANGEROUS_DRIVING",
    "wrong side":           "WRONG_SIDE",
    "overloading":          "OVERLOADING",
    "overload":             "OVERLOADING",
    "emission":             "EMISSION_VIOLATION",
    "pollution":            "EMISSION_VIOLATION",
    "no registration":      "INVALID_REGISTRATION",
    "registration":         "INVALID_REGISTRATION",
    "no rc":                "INVALID_REGISTRATION",
    "disqualified":         "DISQUALIFIED_LICENSE",
    "modified vehicle":     "MODIFIED_VEHICLE",
    "general":              "GENERAL_VIOLATION",
    "minor":                "GENERAL_VIOLATION",
    "disobey":              "POLICE_DISOBEDIENCE",
    "police":               "POLICE_DISOBEDIENCE",
    "unauthorized":         "UNAUTHORIZED_USE",
    "juvenile":             "JUVENILE_OFFENCE",
    "tinted":               "TINTED_GLASS",
    "dark glass":           "TINTED_GLASS",
    "noise":                "NOISE_POLLUTION",
    "horn":                 "NOISE_POLLUTION",
    "racing":               "RACING",
    "road rage":            "ROAD_RAGE",
    "hit and run":          "HIT_AND_RUN",
    "lane":                 "LANE_VIOLATION",
    "toll":                 "TOLL_EVASION",
    "fare":                 "FARE_EVASION",
    "bus":                  "FARE_EVASION",
    "ticket":               "FARE_EVASION",
}

# Maps violation name fragments in state_fines_lookup.csv → (offence_code, vehicle_class, is_repeat)
STATE_VIOLATION_MAP: Dict[str, Tuple[str, str, bool]] = {
    "no driving licence":              ("NO_LICENSE",          "ALL", False),
    "over speeding (lmv)":             ("SPEED_EXCESS",        "LMV", False),
    "over speeding (hgv)":             ("SPEED_EXCESS",        "HGV", False),
    "signal jump / dangerous driving": ("RED_LIGHT_JUMPING",   "ALL", False),
    "mobile phone while driving":      ("MOBILE_PHONE",        "ALL", False),
    "wrong side driving":              ("WRONG_SIDE",          "ALL", False),
    "drunk driving (1st)":             ("DRUNK_DRIVING",       "ALL", False),
    "drunk driving (2nd+)":            ("DRUNK_DRIVING",       "ALL", True),
    "no vehicle registration":         ("INVALID_REGISTRATION","ALL", False),
    "no seat belt":                    ("NO_SEATBELT",         "LMV", False),
    "no helmet":                       ("NO_HELMET",           "2W",  False),
    "no insurance":                    ("NO_INSURANCE",        "ALL", False),
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_csv(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def normalize_rule_id(dataset_id: str) -> str:
    """'MV181' → 'MV_181',  'MV183A' → 'MV_183A'."""
    m = re.match(r'^MV(\d+.*)$', dataset_id.strip())
    return f"MV_{m.group(1)}" if m else dataset_id

def infer_offence_codes(violation: Dict, existing_rule: Optional[Dict]) -> List[str]:
    """Return offence codes: prefer existing rule's codes, then infer from tags/name."""
    if existing_rule:
        codes = existing_rule.get("related_offence_codes", [])
        if codes:
            return codes

    tags = " ".join(violation.get("tags", [])).lower()
    name = violation.get("violation_name", "").lower()
    combined = f"{tags} {name}"

    for keyword, code in TAG_TO_CODE.items():
        if keyword in combined:
            return [code]

    return [f"{violation.get('id', 'UNKNOWN')}_OFFENCE"]

def build_section_index(rules: List[Dict]) -> Dict[str, Dict]:
    return {r.get("section", "").strip().lower(): r for r in rules if r.get("section")}

def build_rule_id_index(rules: List[Dict]) -> Dict[str, Dict]:
    return {r["rule_id"]: r for r in rules}

def merge_violation_into_rule(existing: Optional[Dict], violation: Dict) -> Dict:
    """
    Enrich an existing rule (or build a new one) with fields from violations_db.json.
    Existing authoritative fields (title, description, offence_codes) take priority.
    """
    rule_id = normalize_rule_id(violation["id"]) if existing is None else existing["rule_id"]
    offence_codes = infer_offence_codes(violation, existing)

    merged = {
        "rule_id":               rule_id,
        "section":               violation.get("section") or (existing or {}).get("section", ""),
        "act":                   (existing or {}).get("act", "Motor Vehicles (Amendment) Act, 2019"),
        "title":                 (existing or {}).get("title") or violation.get("violation_name", ""),
        "description":           (existing or {}).get("description") or violation.get("description", ""),
        "applies_to":            (existing or {}).get("applies_to", ["ALL"]),
        "vehicle_classes":       (existing or {}).get("vehicle_classes", ["ALL"]),
        "vehicle_types":         violation.get("vehicle_types", ["All"]),
        "state_overrides":       (existing or {}).get("state_overrides", []),
        "related_offence_codes": offence_codes,
        "penalty_ref":           (existing or {}).get("penalty_ref", f"{rule_id}_FINE"),
        # ── Enrichment from dataset ──────────────────────────────────────────
        "tags":                  violation.get("tags", []),
        "compoundable":          violation.get("compoundable", True),
        "imprisonment":          violation.get("imprisonment", False),
        "national_fine":         violation.get("national_fine", {}),
        "dataset_id":            violation.get("id"),
    }
    return merged


def apply_state_overrides(rules: List[Dict], state_fines_json: Dict) -> List[Dict]:
    """
    Enrich rules with per-state fine overrides from state_wise_fines.json.
    Adds structured state_override entries; never duplicates an existing state entry.
    """
    rule_id_idx = build_rule_id_index(rules)

    for state_name, state_data in state_fines_json.get("states", {}).items():
        state_code = state_data.get("state_code", state_name[:2].upper())

        for violation_id, fine_obj in state_data.get("overrides", {}).items():
            rid = normalize_rule_id(violation_id)
            rule = rule_id_idx.get(rid)
            if not rule:
                continue

            existing_states = {o.get("state") for o in rule.get("state_overrides", [])}
            if state_code in existing_states:
                continue

            rule.setdefault("state_overrides", []).append({
                "state":       state_code,
                "state_name":  state_name,
                "fine_data":   fine_obj,
                "notes":       state_data.get("notes", ""),
                "source":      "state_wise_fines.json",
            })

    return rules


# ── Seed-fines expansion ──────────────────────────────────────────────────────

VEHICLE_TYPE_MAP: Dict[str, str] = {
    "two-wheeler": "2W", "two wheeler": "2W", "2w": "2W",
    "lmv": "LMV", "car": "LMV", "four-wheeler": "LMV", "four wheeler": "LMV",
    "hgv": "HGV", "hgv/mgv": "HGV", "mgv": "HGV", "truck": "HGV",
    "bus": "HGV", "public transport": "HGV",
    "all": "ALL", "": "ALL",
}

def _vc(raw: str) -> str:
    return VEHICLE_TYPE_MAP.get(raw.strip().lower(), "ALL")

def expand_seed_fines(
    violations_csv: List[Dict],
    state_csv: List[Dict],
    rules: List[Dict],
) -> List[Dict]:
    """
    Build comprehensive fine records from:
      1. violations_flat.csv  → national defaults (first & subsequent offences)
      2. state_fines_lookup.csv → state-specific amounts
    Returns deduplicated list of dicts matching seed_fines.csv schema.
    """
    section_idx = {r.get("section", "").strip().lower(): r for r in rules}

    # keyed by (offence_code, vehicle_class, state, is_repeat) → row dict
    fine_map: Dict[Tuple, Dict] = {}

    def upsert(offence_code, vehicle_class, state, amount, repeat_amount, section_ref, source):
        """Insert or update a fine record (non-None amount wins over None)."""
        key = (offence_code, vehicle_class, state)
        existing = fine_map.get(key)
        if existing is None:
            fine_map[key] = {
                "offence_code":       offence_code,
                "vehicle_class":      vehicle_class,
                "state":              state,
                "amount_inr":         amount,
                "repeat_amount_inr":  repeat_amount,
                "section_ref":        section_ref,
                "source_url":         source,
            }
        else:
            # Prefer the richer / non-null amount
            if amount and not existing["amount_inr"]:
                existing["amount_inr"] = amount
            if repeat_amount and not existing["repeat_amount_inr"]:
                existing["repeat_amount_inr"] = repeat_amount

    # 1. violations_flat.csv — national defaults
    # Group by (section, vehicle_class): collect first-offence and subsequent amounts
    # CSV has separate rows for 1st and 2nd+ offences for the same section/vehicle.
    national: Dict[Tuple, Dict] = {}  # (section_lower, vc) → {first, repeat, section_ref}
    for row in violations_csv:
        section_lower = (row.get("section") or "").strip().lower()
        vc = _vc(row.get("vehicle_type") or "All")
        is_repeat = "2nd" in (row.get("offence_number") or "")

        try:
            amount = int(float(row["fine_amount_inr"])) if row.get("fine_amount_inr") else None
        except (ValueError, TypeError):
            amount = None

        key = (section_lower, vc)
        entry = national.setdefault(key, {"first": None, "repeat": None, "section_ref": row.get("section", "")})
        if is_repeat:
            entry["repeat"] = amount
        else:
            entry["first"] = amount

    for (section_lower, vc), entry in national.items():
        rule = section_idx.get(section_lower)
        if not rule:
            continue
        codes = rule.get("related_offence_codes", [])
        if not codes:
            continue
        offence_code = codes[0]
        repeat = entry["repeat"] or entry["first"]
        upsert(offence_code, vc, "ALL", entry["first"], repeat, rule.get("section", ""), "https://parivahan.gov.in")

    # 2. state_fines_lookup.csv — state-specific amounts
    for row in state_csv:
        state_code = (row.get("state_code") or "").strip()
        if not state_code:
            continue
        vname = (row.get("violation") or "").strip().lower()
        try:
            amount = int(float(row["fine_inr"])) if row.get("fine_inr") else None
        except (ValueError, TypeError):
            amount = None

        match = STATE_VIOLATION_MAP.get(vname)
        if not match:
            # fuzzy: try substring
            for key, val in STATE_VIOLATION_MAP.items():
                if key in vname or vname in key:
                    match = val
                    break
        if not match or not amount:
            continue

        offence_code, vehicle_class, is_repeat = match
        if is_repeat:
            key3 = (offence_code, vehicle_class, state_code)
            existing = fine_map.get(key3)
            if existing:
                existing["repeat_amount_inr"] = amount
            else:
                upsert(offence_code, vehicle_class, state_code, None, amount,
                       offence_code.replace("_", " ").title(), "https://parivahan.gov.in")
        else:
            repeat_amount = amount  # keep same as first for now; repeat row may follow
            upsert(offence_code, vehicle_class, state_code, amount, repeat_amount,
                   offence_code.replace("_", " ").title(), "https://parivahan.gov.in")

    return list(fine_map.values())


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("DriveLegal Dataset Merger  v2.0")
    print("=" * 60)

    # ── Load sources ──────────────────────────────────────────────────────────
    violations_db  = load_json(os.path.join(DATASET_DIR, "json", "violations_db.json"))
    state_fines_js = load_json(os.path.join(DATASET_DIR, "json", "state_wise_fines.json"))
    current_rules  = load_json(RULES_JSON)

    violations_csv_rows  = load_csv(os.path.join(DATASET_DIR, "csv", "violations_flat.csv"))
    state_csv_rows       = load_csv(os.path.join(DATASET_DIR, "csv", "state_fines_lookup.csv"))

    print(f"  violations_db.json : {len(violations_db['violations'])} violations")
    print(f"  rules.json (current): {len(current_rules['rules'])} rules")
    print(f"  violations_flat.csv : {len(violations_csv_rows)} rows")
    print(f"  state_fines_lookup.csv: {len(state_csv_rows)} rows")

    existing_rules  = current_rules["rules"]
    section_idx     = build_section_index(existing_rules)
    rule_id_idx     = build_rule_id_index(existing_rules)

    # ── Merge violations into rules ───────────────────────────────────────────
    merged_by_rid: Dict[str, Dict] = {}
    enriched = 0
    added = 0

    for violation in violations_db["violations"]:
        section_key  = violation.get("section", "").strip().lower()
        existing_rule = section_idx.get(section_key)
        merged        = merge_violation_into_rule(existing_rule, violation)

        if existing_rule:
            enriched += 1
        else:
            added += 1

        merged_by_rid[merged["rule_id"]] = merged

    # Preserve existing rules not covered by violations_db
    for rule in existing_rules:
        if rule["rule_id"] not in merged_by_rid:
            merged_by_rid[rule["rule_id"]] = rule

    rules_list = sorted(merged_by_rid.values(), key=lambda r: r["rule_id"])

    # ── Apply state overrides ─────────────────────────────────────────────────
    rules_list = apply_state_overrides(rules_list, state_fines_js)

    print(f"\n  Enriched : {enriched} existing rules")
    print(f"  Added    : {added} new rules from dataset")
    print(f"  Total    : {len(rules_list)} rules in merged output")

    # ── Write rules.json ──────────────────────────────────────────────────────
    output = {
        "schema_version": "2.0",
        "last_updated":   date.today().isoformat(),
        "metadata":       violations_db.get("metadata", {}),
        "rules":          rules_list,
    }

    with open(RULES_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n[OK]  rules.json  written  ({len(rules_list)} rules)")

    # ── Expand seed_fines.csv ─────────────────────────────────────────────────
    fine_records = expand_seed_fines(violations_csv_rows, state_csv_rows, rules_list)
    fieldnames   = [
        "offence_code", "vehicle_class", "state",
        "amount_inr", "repeat_amount_inr", "section_ref", "source_url",
    ]
    with open(SEED_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(fine_records)
    print(f"[OK]  seed_fines.csv written ({len(fine_records)} rows)")

    # ── Reset vector DB so HybridSearch re-indexes on next start ─────────────
    if os.path.exists(VECTOR_DB):
        shutil.rmtree(VECTOR_DB)
        print("[OK]  vector_db cleared — will be re-indexed on server start")

    print("\nNext step: python -m backend.modules.fines.seed")
    print("=" * 60)


if __name__ == "__main__":
    main()
