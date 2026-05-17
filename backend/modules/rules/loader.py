import json
import os
from typing import Dict, List, Optional


class RulesLoader:
    """
    Loads rules.json (schema v1.0 or v2.0) and provides indexed lookup.

    Schema v2.0 adds:  tags, compoundable, imprisonment, national_fine, dataset_id
    All new fields are optional so v1.0 files remain fully compatible.
    """

    def __init__(self, rules_path: str, metadata_path: str = None):
        self.rules_path     = rules_path
        self.schema_version = "1.0"

        # Primary storage
        self.rules: List[Dict] = []

        # Indices
        self.rule_id_index:     Dict[str, Dict]       = {}
        self.offence_code_index: Dict[str, Dict]      = {}
        self.section_index:     Dict[str, Dict]       = {}
        self.tag_index:         Dict[str, List[Dict]] = {}   # tag_lower → [rules]
        self.dataset_id_index:  Dict[str, Dict]       = {}   # "MV181" → rule

        # State abbreviation map from metadata.json
        self.state_abbr_map: Dict[str, str] = {}
        if metadata_path is None:
            metadata_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "data", "metadata.json"
            )
        if os.path.exists(metadata_path):
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            for canonical, variations in metadata.get("states", {}).items():
                for v in variations:
                    if len(v) <= 3:
                        self.state_abbr_map[canonical.lower()] = v.upper()

        self._load_rules()

    # ── Loading ───────────────────────────────────────────────────────────────

    def _load_rules(self):
        if not os.path.exists(self.rules_path):
            return

        with open(self.rules_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.schema_version = data.get("schema_version", "1.0")
        self.rules = data.get("rules", [])

        # Country index
        self.country_index: Dict[str, List[Dict]] = {}

        for rule in self.rules:
            rid = rule.get("rule_id")
            if not rid:
                continue

            # Set default country to IN if missing, with basic detection for US rules
            country = rule.get("country")
            if not country:
                act_text = (rule.get("act") or "").lower()
                title_text = (rule.get("title") or "").lower()
                if any(k in act_text for k in ["minnesota", "texas", "usa", "america", "us "]) or \
                   any(k in title_text for k in ["minnesota", "texas"]):
                    country = "US"
                elif any(k in act_text for k in ["singapore", "sg "]):
                    country = "SG"
                elif any(k in act_text for k in ["united kingdom", "uk ", "london"]):
                    country = "GB"
                elif any(k in act_text for k in ["emirates", "uae", "dubai"]):
                    country = "AE"
                else:
                    country = "IN"
            
            country = country.upper()
            rule["country"] = country
            self.country_index.setdefault(country, []).append(rule)

            self.rule_id_index[rid] = rule

            section = (rule.get("section") or "").strip()
            if section:
                self.section_index[section.lower()] = rule

            for code in rule.get("related_offence_codes", []):
                if code:
                    self.offence_code_index[code] = rule

            # v2.0 tag index
            for tag in rule.get("tags", []):
                self.tag_index.setdefault(tag.lower(), []).append(rule)

            # v2.0 dataset_id index ("MV181" cross-reference)
            did = rule.get("dataset_id")
            if did:
                self.dataset_id_index[did] = rule

    # ── Primary lookups ───────────────────────────────────────────────────────

    def get_by_rule_id(self, rule_id: str) -> Optional[Dict]:
        return self.rule_id_index.get(rule_id)

    def get_by_section(self, section: str) -> Optional[Dict]:
        if not section:
            return None
        return self.section_index.get(section.strip().lower())

    def get_by_offence_code(self, offence_code: str, state: str = "ALL") -> Optional[Dict]:
        """Returns rule for offence_code; applies state-specific override if available."""
        rule = self.offence_code_index.get(offence_code)
        if not rule or state == "ALL":
            return rule

        override = self.get_state_override(rule["rule_id"], state)
        if override:
            enriched = rule.copy()
            enriched["description"]     = override.get("description") or rule["description"]
            enriched["is_state_override"] = True
            enriched["state_fine_data"]   = override.get("fine_data")
            return enriched
        return rule

    def get_by_dataset_id(self, dataset_id: str) -> Optional[Dict]:
        return self.dataset_id_index.get(dataset_id)

    def get_rules_by_country(self, country: str) -> List[Dict]:
        """Returns all rules for a specific country (e.g. 'IN', 'US')."""
        return self.country_index.get(country.upper(), [])

    # ── State overrides ────────────────────────────────────────────────────────

    def get_state_override(self, rule_id: str, state: str) -> Optional[Dict]:
        """
        Returns the state_override entry for a given rule and state.
        Accepts full state name ('Tamil Nadu') or abbreviation ('TN').
        Returns None — never fabricates data.
        """
        rule = self.get_by_rule_id(rule_id)
        if not rule or not state:
            return None

        state_lower = state.lower()
        # Resolve full name → abbreviation
        state_code  = self.state_abbr_map.get(state_lower, state).upper()

        for override in rule.get("state_overrides", []):
            candidate = (override.get("state") or "").upper()
            if candidate == state_code or candidate == state.upper():
                return override
        return None

    # ── Fine extraction (v2.0) ────────────────────────────────────────────────

    def get_fine_from_rule(
        self,
        rule: Dict,
        is_repeat: bool = False,
        vehicle_class: str = "ALL",
    ) -> Optional[int]:
        """
        Extract a fine amount from rule.national_fine (schema v2.0).
        Returns None if data is missing — never invents amounts.
        """
        nf = rule.get("national_fine")
        if not nf or not isinstance(nf, dict):
            return None

        offence_key = "subsequent" if is_repeat else "first_offence"
        fine_data   = nf.get(offence_key) or nf.get("first_offence")
        if not fine_data or not isinstance(fine_data, dict):
            return None

        # Try vehicle-class-specific sub-entry (e.g. nf["LMV"]["first_offence"])
        if vehicle_class != "ALL" and vehicle_class in nf:
            vc_data   = nf[vehicle_class]
            fine_data = vc_data.get(offence_key) or vc_data.get("first_offence") or fine_data

        return fine_data.get("fine_max") or fine_data.get("fine_min")

    # ── Tag-based search ──────────────────────────────────────────────────────

    def search_by_tags(self, tags: List[str]) -> List[Dict]:
        """Return unique rules that match any of the supplied tags."""
        seen: Dict[str, Dict] = {}
        for tag in tags:
            for rule in self.tag_index.get(tag.lower(), []):
                seen[rule["rule_id"]] = rule
        return list(seen.values())

    # ── Token-based lexical search ────────────────────────────────────────────

    def search(self, query_tokens: List[str]) -> List[Dict]:
        """All-token lexical match across title + description + tags."""
        tokens = [t.lower() for t in query_tokens if t]
        results = []
        for rule in self.rules:
            searchable = " ".join([
                rule.get("title", ""),
                rule.get("description", ""),
                " ".join(rule.get("tags", [])),
            ]).lower()
            if all(t in searchable for t in tokens):
                results.append(rule)
        return results

    # ── Aggregates ────────────────────────────────────────────────────────────

    @property
    def count(self) -> int:
        return len(self.rules)

    def get_all_offence_codes(self) -> List[str]:
        return list(self.offence_code_index.keys())

    def get_compoundable_rules(self) -> List[Dict]:
        return [r for r in self.rules if r.get("compoundable", True)]

    def get_non_compoundable_rules(self) -> List[Dict]:
        return [r for r in self.rules if not r.get("compoundable", True)]
