#!/usr/bin/env python3
import json
import pathlib
import unittest

from fr0333_two_lane_highway_genius import validate

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "fr0333_two_lane_highway_0001.json"


class TwoLaneHighwayGeniusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(DATA.read_text(encoding="utf-8"))
        cls.report = validate(cls.doc)

    def test_fourteen_in_fourteen_out(self):
        self.assertEqual(self.report["total"], 14)
        self.assertEqual(self.report["passed"], 14)
        self.assertEqual(self.report["state"], "PASS")

    def test_all_gates_pass(self):
        self.assertTrue(all(row["state"] == "PASS" for row in self.report["results"]))

    def test_reference_points_exact(self):
        refs = [r["reference_point"] for r in self.doc["reference_points"]]
        self.assertEqual(refs, ["A1","B2","C3","D4","E5","F6","G7","H8","I9","J10","K11","L12","M13","N14"])

    def test_passive_lane_append_only(self):
        passive = self.doc["passive_lane"]
        self.assertEqual(passive["write_mode"], "APPEND.ONLY")
        self.assertEqual(passive["mutation_policy"], "NO_OVERWRITE_NO_COMPRESSION_NO_RENUMBERING")

    def test_runtime_remains_hold(self):
        self.assertEqual(self.doc["runtime_execution"], "U.21.HOLD")
        self.assertEqual(self.doc["empirical_runtime_receipt"], "U.21.HOLD")
        self.assertEqual(self.doc["external_registry_write"], "NOT.ESTABLISHED")

    def test_no_fabricated_hardware_stop(self):
        boundary = self.doc["source_boundary"]
        self.assertEqual(boundary["hardware_stop_vector"], "NOT_CLAIMED")
        self.assertEqual(boundary["user_interrupt_control"], "STOP.CONTROL.REQUIRED")

    def test_auto_promotion_disabled(self):
        terminal = self.doc["terminal_control_matrix"]
        self.assertEqual(terminal["auto_continue"], "F.6.NONE")
        self.assertEqual(terminal["auto_promotion"], "F.6.NONE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
