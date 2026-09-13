#!/usr/bin/env python3
import json
import pathlib
import unittest

from fr0333_bits_bones_cultural_capital_transfer_genius import validate

HERE = pathlib.Path(__file__).resolve().parent
SPEC = HERE / "fr0333_bits_bones_cultural_capital_transfer_0002.json"


class CulturalCapitalTransferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(SPEC.read_text(encoding="utf-8"))

    def test_validator_passes_all_ten_gates(self):
        report = validate(self.doc)
        self.assertEqual(report["state"], "PASS")
        self.assertEqual(report["passed"], 10)
        self.assertEqual(report["total"], 10)
        self.assertEqual(report["invariant"], "TEN.IN -> TEN.OUT")

    def test_terminal_states_are_canonical(self):
        self.assertEqual(self.doc["terminal_states"], {"true": "T.20", "hold": "U.21", "false": "F.6"})

    def test_direct_theft_is_not_inferred(self):
        cases = {c["case_id"]: c for c in self.doc["cases"]}
        self.assertEqual(
            cases["CASE.0001.HOUND.DOG"]["evidence_boundaries"]["direct_composition_theft_by_presley"],
            "F.6.NOT_SUPPORTED",
        )
        self.assertEqual(
            cases["CASE.0002.TUTTI.FRUTTI"]["evidence_boundaries"]["direct_composition_theft_by_boone"],
            "F.6.NOT_SUPPORTED",
        )

    def test_visual_intent_requires_evidence(self):
        rules = self.doc["visual_identity"]["evidence_rules"]
        self.assertIn(
            "LABEL_MARKETING_INTENT_REQUIRES_EXECUTIVE_STATEMENT_LABEL_RECORD_OR_EQUIVALENT_STRONG_SOURCE_FOR_T20",
            rules,
        )


if __name__ == "__main__":
    unittest.main()
