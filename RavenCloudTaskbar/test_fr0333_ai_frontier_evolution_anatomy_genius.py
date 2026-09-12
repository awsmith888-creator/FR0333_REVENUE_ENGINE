#!/usr/bin/env python3
import json
import pathlib
import unittest

from fr0333_ai_frontier_evolution_anatomy_genius import validate

HERE = pathlib.Path(__file__).resolve().parent
RAIL = HERE / "fr0333_ai_frontier_evolution_anatomy_0001.json"


class AIFrontierEvolutionAnatomyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(RAIL.read_text(encoding="utf-8"))
        cls.report = validate(cls.doc)

    def test_sixteen_in_sixteen_out(self):
        self.assertEqual(self.report["total"], 16)
        self.assertEqual(self.report["passed"], 16)
        self.assertEqual(self.report["state"], "PASS")
        self.assertEqual(self.report["invariant"], "SIXTEEN.IN -> SIXTEEN.OUT")

    def test_reference_points_are_a1_through_p16(self):
        expected = ["A1","B2","C3","D4","E5","F6","G7","H8","I9","J10","K11","L12","M13","N14","O15","P16"]
        actual = [x["reference_point"] for x in self.doc["reference_points"]]
        self.assertEqual(actual, expected)

    def test_evolution_overlay_is_append_only(self):
        golden = self.doc["golden_chain"]
        self.assertEqual(golden["mode"], "EVOLUTION_OVERLAY_APPEND_ONLY")
        self.assertFalse(golden["prior_entries_renumbered"])
        self.assertTrue(golden["humanlock"])

    def test_race_is_not_single_winner_claim(self):
        self.assertEqual(self.doc["race_anatomy"]["state"], "MULTI.FRONT.RACE.NO.PERMANENT.WINNER.ESTABLISHED")
        self.assertIn("BENCHMARK_LEADER_NE_GENERAL_DOMINANCE", self.doc["control_laws"])

    def test_intelligence_not_benevolence(self):
        laws = self.doc["control_laws"]
        self.assertIn("INTELLIGENCE_NE_BENEVOLENCE", laws)
        self.assertIn("SMARTER_NE_HARMLESS", laws)
        self.assertIn("SAFETY_FRAMEWORK_NE_ZERO_RISK", laws)

    def test_consciousness_hold(self):
        p16 = self.doc["reference_points"][-1]
        self.assertEqual(p16["reference_point"], "P16")
        self.assertEqual(p16["value"], "U.21.HOLD")

    def test_digital_physical_separation(self):
        self.assertIn("DIGITAL_TASK_SUCCESS_NE_PHYSICAL_WORLD_MASTERY", self.doc["control_laws"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
