#!/usr/bin/env python3
import json
import pathlib
import unittest

from fr0333_red_sea_dual_chokepoint_genius import validate

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "fr0333_red_sea_dual_chokepoint_0001.json"


class RedSeaDualChokepointTests(unittest.TestCase):
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

    def test_per_1000_not_percentage(self):
        self.assertEqual(self.by_ref["E5"]["unit"], "barrels_per_1000_world_supply_reference")
        self.assertEqual(self.by_ref["G7"]["unit"], "barrels_per_1000_world_supply_reference")
        self.assertEqual(self.by_ref["E5"]["value"], 81)
        self.assertEqual(self.by_ref["G7"]["value"], 49)

    def test_no_naive_dual_chokepoint_sum(self):
        self.assertEqual(self.by_ref["H8"]["value"], "U.21.HOLD")

    def test_political_pledge_not_enacted(self):
        self.assertEqual(self.by_ref["K11"]["class"], "POLITICAL_PROPOSAL_NOT_ENACTED")
        self.assertEqual(self.by_ref["M13"]["value"], "REQUIRED_FOR_SPENDING_PROGRAM")

    def test_geopolitical_election_causation_not_established(self):
        self.assertEqual(self.by_ref["N14"]["value"], "F.6.NOT_ESTABLISHED")

    def test_humanlock_active(self):
        self.assertTrue(self.doc["golden_chain"]["humanlock"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
