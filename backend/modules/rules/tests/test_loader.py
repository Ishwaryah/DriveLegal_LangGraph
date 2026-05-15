import unittest
import json
import os
import tempfile
from backend.modules.rules.loader import RulesLoader

class TestRulesLoader(unittest.TestCase):
    def setUp(self):
        # Create a temporary rules file for testing
        self.rules_data = {
            "schema_version": "1.0",
            "rules": [
                {
                    "rule_id": "TEST_001",
                    "title": "Speeding Rule",
                    "description": "Do not speed on the highway",
                    "related_offence_codes": ["SPEEDING"],
                    "state_overrides": [
                        {
                            "state": "KA",
                            "description": "Karnataka specific speed limit rule"
                        }
                    ]
                },
                {
                    "rule_id": "TEST_002",
                    "title": "Helmet Rule",
                    "description": "Always wear a helmet",
                    "related_offence_codes": ["NO_HELMET"],
                    "state_overrides": []
                }
            ]
        }
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(self.rules_data, self.temp_file)
        self.temp_file.close()
        self.loader = RulesLoader(self.temp_file.name)

    def tearDown(self):
        if hasattr(self, 'temp_file'):
            os.unlink(self.temp_file.name)

    def test_get_by_rule_id(self):
        rule = self.loader.get_by_rule_id("TEST_001")
        self.assertIsNotNone(rule)
        self.assertEqual(rule["title"], "Speeding Rule")

    def test_state_override_priority(self):
        # Without state override
        rule = self.loader.get_by_offence_code("SPEEDING", state="ALL")
        self.assertEqual(rule["description"], "Do not speed on the highway")
        
        # With state override
        rule_ka = self.loader.get_by_offence_code("SPEEDING", state="KA")
        self.assertEqual(rule_ka["description"], "Karnataka specific speed limit rule")
        self.assertTrue(rule_ka.get("is_state_override"))

    def test_search_token_match(self):
        # Match by title token
        results = self.loader.search(["Speeding"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["rule_id"], "TEST_001")

        # Match by description token
        results = self.loader.search(["helmet"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["rule_id"], "TEST_002")
        
        # Multi token match
        results = self.loader.search(["wear", "helmet"])
        self.assertEqual(len(results), 1)
        
        # No match
        results = self.loader.search(["parking"])
        self.assertEqual(len(results), 0)

    def test_missing_returns_none(self):
        self.assertIsNone(self.loader.get_by_rule_id("NON_EXISTENT"))
        self.assertIsNone(self.loader.get_by_offence_code("UNKNOWN_OFFENCE"))

if __name__ == "__main__":
    unittest.main()
