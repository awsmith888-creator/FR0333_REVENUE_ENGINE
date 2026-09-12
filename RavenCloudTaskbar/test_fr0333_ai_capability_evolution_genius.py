#!/usr/bin/env python3
import json
import pathlib
import unittest

from fr0333_ai_capability_evolution_genius import validate

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "fr0333_ai_capability_evolution_0001.json"


class AICapabilityEvolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(DATA.read_text(encoding="utf-8"))
        cls.report = validate(cls.doc)
        cls.by_ref = {r["reference_point"]: r for r in cls.doc["reference_points"]}

    def test_fourteen_in_fourteen_out(self):
        self.assertEqual(self.report["total"], 14)
        self.assertEqual(self.report["passed"], 14)
        self.assertEqual(self.report["state"], "PASS")

    def test_reference_points_exact(self):
        self.assertEqual([r["reference_point"] for r in self.doc["reference_points"]],
                         ["A1","B2","C3","D4","E5","F6","G7","H8","I9","J10","K11","L12","M13","N14"])

    def test_reference_points_do_not_use_percent_units(self):
        for ref in self.doc["reference_points"]:
            self.assertNotIn("percent", str(ref.get("unit", "")).lower())
            self.assertNotIn("%", str(ref.get("unit", "")))

    def test_cost_ratio_reconstructs(self):
        self.assertEqual(round(self.by_ref["E5"]["value"] / self.by_ref["F6"]["value"]), self.by_ref["G7"]["value"])

    def test_consciousness_remains_hold(self):
        self.assertEqual(self.by_ref["N14"]["value"], "U.21.HOLD")

    def test_failure_memory_append_only(self):
        self.assertEqual(self.doc["failure_memory"]["passive_lane"], "APPEND_ONLY")

    def test_humanlock_active(self):
        self.assertTrue(self.doc["golden_chain"]["humanlock"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
