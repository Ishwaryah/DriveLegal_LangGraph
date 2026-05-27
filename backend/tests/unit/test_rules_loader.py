"""
Unit tests for RulesLoader — rule retrieval and state-override priority.
"""

import json
import os
import tempfile
import unittest

from backend.modules.rules.loader import RulesLoader


class TestRulesLoader(unittest.TestCase):

    def setUp(self):
        self.rules_data = {
            "schema_version": "1.0",
            "rules": [
                {
                    "rule_id":              "TEST_001",
                    "title":                "Speeding Rule",
                    "description":          "Do not speed on the highway",
                    "related_offence_codes": ["SPEEDING"],
                    "state_overrides": [
                        {
                            "state":       "KA",
                            "description": "Karnataka specific speed limit rule",
                        }
                    ],
                },
                {
                    "rule_id":              "TEST_002",
                    "title":                "Helmet Rule",
                    "description":          "Always wear a helmet",
                    "related_offence_codes": ["NO_HELMET"],
                    "state_overrides": [],
                },
            ],
        }
        self.temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        json.dump(self.rules_data, self.temp_file)
        self.temp_file.close()
        self.loader = RulesLoader(self.temp_file.name)

    def tearDown(self):
        if hasattr(self, "temp_file"):
            os.unlink(self.temp_file.name)

    def test_get_by_rule_id(self):
        rule = self.loader.get_by_rule_id("TEST_001")
        self.assertIsNotNone(rule)
        self.assertEqual(rule["title"], "Speeding Rule")

    def test_national_description(self):
        rule = self.loader.get_by_offence_code("SPEEDING", state="ALL")
        self.assertEqual(rule["description"], "Do not speed on the highway")

    def test_state_override_priority(self):
        rule = self.loader.get_by_offence_code("SPEEDING", state="KA")
        self.assertEqual(rule["description"], "Karnataka specific speed limit rule")
        self.assertTrue(rule.get("is_state_override"))

    def test_search_by_title_token(self):
        results = self.loader.search(["Speeding"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["rule_id"], "TEST_001")

    def test_search_by_description_token(self):
        results = self.loader.search(["helmet"])
        self.assertEqual(len(results), 1)

    def test_no_match_returns_none(self):
        self.assertIsNone(self.loader.get_by_rule_id("NON_EXISTENT"))
        self.assertIsNone(self.loader.get_by_offence_code("UNKNOWN_OFFENCE"))


if __name__ == "__main__":
    unittest.main()
