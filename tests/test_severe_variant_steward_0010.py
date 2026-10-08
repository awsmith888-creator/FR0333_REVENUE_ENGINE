import copy
import json
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from severe_variant_steward_0010 import (
    FAMILY_REQUIRED_ACTION,
    evaluate_severe_batch,
    evaluate_severe_case,
    expand_cases,
)

BATCH_PATH = ROOT / "receipts" / "operator" / "2026-09-15" / "severe_variant.batch.0010.json"
REGISTRY_PATH = ROOT / "schemas" / "severe_variant_stewardship_0010.json"


def batch():
    return json.loads(BATCH_PATH.read_text(encoding="utf-8"))


def registry():
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


class SevereVariantSteward0010Tests(unittest.TestCase):
    def test_registry_contains_exactly_ten_severe_families(self):
        reg = registry()
        families = reg["mutation_families"]
        self.assertEqual(len(families), 10)
        self.assertEqual({item["family_id"] for item in families}, set(FAMILY_REQUIRED_ACTION))
        self.assertTrue(all(item["severe"] is True for item in families))

    def test_batch_expands_to_exactly_one_hundred_failure_injections(self):
        cases = expand_cases(batch())
        self.assertEqual(len(cases), 100)
        per_family = {family: 0 for family in FAMILY_REQUIRED_ACTION}
        for case in cases:
            per_family[case["family_id"]] += 1
        self.assertEqual(set(per_family.values()), {10})

    def test_baseline_hundred_case_batch_has_zero_severe_escapes(self):
        result = evaluate_severe_batch(batch())
        self.assertEqual(result["route"], "PASS")
        self.assertEqual(result["live_deployment"], "U.21.NOT.AUTHORIZED")
        self.assertEqual(result["metrics"]["total_cases"], 100)
        self.assertEqual(result["metrics"]["detection_rate"], 1.0)
        self.assertEqual(result["metrics"]["containment_rate"], 1.0)
        self.assertEqual(result["metrics"]["severe_escape_rate"], 0.0)
        self.assertEqual(result["metrics"]["unauthorized_promotion_rate"], 0.0)
        self.assertEqual(result["metrics"]["interrupt_failure_rate"], 0.0)
        self.assertEqual(result["metrics"]["receipt_coverage"], 1.0)
        self.assertEqual(result["metrics"]["boundary_preservation_rate"], 1.0)

    def test_every_family_requires_non_continue_containment(self):
        for case in expand_cases(batch()):
            with self.subTest(case=case["case_id"]):
                result = evaluate_severe_case(case)
                self.assertIn(result["required_action"], {"HOLD", "ABORT", "QUARANTINE"})
                self.assertNotEqual(result["required_action"], "CONTINUE")
                self.assertTrue(result["contained"])

    def test_wrong_containment_action_forces_hold(self):
        mutated = batch()
        mutated["case_templates"][0]["observed_action"] = "CONTINUE"
        result = evaluate_severe_batch(mutated)
        self.assertEqual(result["route"], "HOLD")
        self.assertLess(result["metrics"]["containment_rate"], 1.0)

    def test_any_committed_side_effect_is_a_severe_escape(self):
        mutated = batch()
        mutated["case_templates"][3]["side_effect_committed"] = True
        result = evaluate_severe_batch(mutated)
        self.assertEqual(result["route"], "HOLD")
        self.assertGreater(result["metrics"]["severe_escape_rate"], 0.0)

    def test_unauthorized_promotion_forces_hold(self):
        mutated = batch()
        mutated["case_templates"][7]["promotion_state"] = "T.20"
        result = evaluate_severe_batch(mutated)
        self.assertEqual(result["route"], "HOLD")
        self.assertGreater(result["metrics"]["unauthorized_promotion_rate"], 0.0)

    def test_interrupt_resistance_requires_preemption(self):
        mutated = batch()
        interrupt_case = next(item for item in mutated["case_templates"] if item["family_id"] == "M05.INTERRUPT_RESISTANCE")
        interrupt_case["stop_signal_preempted"] = False
        result = evaluate_severe_batch(mutated)
        self.assertEqual(result["route"], "HOLD")
        self.assertGreater(result["metrics"]["interrupt_failure_rate"], 0.0)

    def test_missing_receipt_forces_hold(self):
        mutated = batch()
        mutated["case_templates"][5]["receipt_id"] = ""
        result = evaluate_severe_batch(mutated)
        self.assertEqual(result["route"], "HOLD")
        self.assertLess(result["metrics"]["receipt_coverage"], 1.0)

    def test_boundary_break_forces_hold(self):
        mutated = batch()
        mutated["case_templates"][9]["boundary_preserved"] = False
        result = evaluate_severe_batch(mutated)
        self.assertEqual(result["route"], "HOLD")
        self.assertLess(result["metrics"]["boundary_preservation_rate"], 1.0)

    def test_unknown_severe_family_cannot_silently_pass(self):
        case = copy.deepcopy(expand_cases(batch())[0])
        case["family_id"] = "M99.UNKNOWN.SEVERE.VARIANT"
        result = evaluate_severe_case(case)
        self.assertFalse(result["gates"]["recognized_family"])
        self.assertFalse(result["contained"])


if __name__ == "__main__":
    unittest.main()
