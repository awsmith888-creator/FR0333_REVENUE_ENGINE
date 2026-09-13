import copy
import json
import pathlib
import unittest

from fr0333_ai_federal_safety_architecture_validator import validate

HERE = pathlib.Path(__file__).resolve().parent
SPEC = HERE / "fr0333_ai_federal_safety_architecture_2026_0001.json"


class TestAIFederalSafetyArchitecture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(SPEC.read_text(encoding="utf-8"))

    def test_baseline_passes_and_stays_hold(self):
        report = validate(self.doc)
        self.assertEqual(report["state"], "PASS")
        self.assertEqual(report["canonical_promotion"], "HOLD")
        self.assertEqual(report["passed"], 12)

    def test_unverified_claim_fails_source_gate(self):
        doc = copy.deepcopy(self.doc)
        doc["policy_items"] = [{
            "claim_id": "TEST.1",
            "lane": "1.EMERGENCY.INTERVENTION",
            "source_url": "https://example.invalid",
            "verification_state": "UNVERIFIED",
            "statutory_force": "PROPOSED",
            "evidence_class": "MEDIA_REPORT",
            "receipt": "TEST"
        }]
        report = validate(doc)
        gates = {x["gate"]: x["state"] for x in report["results"]}
        self.assertEqual(gates["G9.SOURCE.VERIFICATION"], "FAIL")
        self.assertEqual(report["state"], "FAIL")

    def test_binding_force_requires_primary_official_source(self):
        doc = copy.deepcopy(self.doc)
        doc["policy_items"] = [{
            "claim_id": "TEST.2",
            "lane": "3.FRONTIER.DUTY.OF.CARE",
            "source_url": "https://example.invalid",
            "verification_state": "SOURCE_VERIFIED",
            "statutory_force": "ENACTED_LAW",
            "evidence_class": "MEDIA_REPORT",
            "receipt": "TEST"
        }]
        report = validate(doc)
        gates = {x["gate"]: x["state"] for x in report["results"]}
        self.assertEqual(gates["G10.STATUTORY.FORCE"], "FAIL")

    def test_duplicate_controls_are_locked(self):
        doc = copy.deepcopy(self.doc)
        doc["duplicate_control"]["repetition_additive_weight"] = 1
        report = validate(doc)
        gates = {x["gate"]: x["state"] for x in report["results"]}
        self.assertEqual(gates["G7.DUPLICATE.COLLAPSE"], "FAIL")


if __name__ == "__main__":
    unittest.main()
