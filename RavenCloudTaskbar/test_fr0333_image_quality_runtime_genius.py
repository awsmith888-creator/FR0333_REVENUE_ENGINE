#!/usr/bin/env python3
import json
import pathlib
import unittest

from fr0333_image_quality_runtime_genius import validate

HERE = pathlib.Path(__file__).resolve().parent
GATE = HERE / "fr0333_image_quality_gate_0003.json"
RECEIPT = HERE / "fr0333_adobe_image_runtime_receipt_0001.json"


class ImageQualityRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = json.loads(GATE.read_text(encoding="utf-8"))
        cls.receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        cls.report = validate(cls.gate, cls.receipt)

    def test_twelve_in_twelve_out(self):
        self.assertEqual(self.report["total"], 12)
        self.assertEqual(self.report["passed"], 12)
        self.assertEqual(self.report["state"], "PASS")

    def test_fourteen_photorealism_dimensions(self):
        self.assertEqual(len(self.gate["photorealism_dimensions"]), 14)
        self.assertIn("VEHICLE.MECHANICAL.GEOMETRY", self.gate["photorealism_dimensions"])
        self.assertIn("LOAD.BALANCE.CONTACT.PHYSICS", self.gate["photorealism_dimensions"])
        self.assertIn("VISUAL.READBACK", self.gate["photorealism_dimensions"])

    def test_adobe_defaults_are_quality_first(self):
        defaults = self.gate["adobe_execution_defaults"]
        self.assertEqual(defaults["edit_prompt_reasoner"], "quality")
        self.assertEqual(defaults["target_resolution_level"], "4MP")
        self.assertEqual(defaults["output_format"], "png")

    def test_runtime_receipt_is_bounded(self):
        self.assertEqual(self.receipt["provider_receipt"]["execution_state"], "PASS_RUNTIME")
        self.assertEqual(self.receipt["result"]["external_adobe_full_capacity"], "NOT_ESTABLISHED")

    def test_quality_stays_hold_without_acceptance(self):
        self.assertEqual(self.receipt["readback"]["quality_promotion_state"], "U.21.HOLD")
        self.assertEqual(self.receipt["readback"]["user_acceptance"], "NOT_OBSERVED")

    def test_user_reject_overrides(self):
        self.assertTrue(self.gate["promotion_gate"]["user_reject_overrides_promotion"])
        self.assertIn("USER.REJECT = OUTPUT.HOLD", self.gate["hard_boundaries"])

    def test_humanlock_active(self):
        self.assertTrue(self.gate["humanlock"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
