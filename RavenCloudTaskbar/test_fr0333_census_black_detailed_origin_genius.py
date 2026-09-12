#!/usr/bin/env python3
import json
import pathlib
import unittest
from fr0333_census_black_detailed_origin_genius import validate

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "fr0333_census_black_detailed_origin_0001.json"

class CensusBlackDetailedOriginGeniusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(DATA.read_text(encoding="utf-8"))
        cls.report = validate(cls.doc)

    def test_ten_in_ten_out(self):
        self.assertEqual(self.report["total"], 10)
        self.assertEqual(self.report["passed"], 10)
        self.assertEqual(self.report["state"], "PASS")

    def test_all_gates_pass(self):
        self.assertTrue(all(row["state"] == "PASS" for row in self.report["results"]))

    def test_no_percent_metric_units(self):
        serialized = json.dumps(self.doc).lower()
        self.assertNotIn('"unit": "percent"', serialized)
        self.assertEqual(self.doc["reference_ratio_rail"]["rule"], "REFERENCE_RATIO_ONLY_NOT_SHARE_NOT_PERCENT")

    def test_cross_series_growth_hold(self):
        self.assertEqual(self.doc["comparability_gate"]["state"], "HOLD_FOR_DIRECT_GROWTH_CALCULATION")
        self.assertIn("UNQUALIFIED_2020_TO_2024_GROWTH_DELTA", self.doc["comparability_gate"]["forbidden"])

    def test_humanlock(self):
        self.assertIs(self.doc["golden_chain"]["humanlock"], True)

if __name__ == "__main__":
    unittest.main(verbosity=2)
