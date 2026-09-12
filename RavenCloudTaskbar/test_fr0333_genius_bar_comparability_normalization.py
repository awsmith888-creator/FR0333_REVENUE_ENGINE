import copy
import json
import unittest
from pathlib import Path

from fr0333_genius_bar_comparability_normalization_0001 import (
    HOLD,
    PASS,
    REJECT,
    canonical_decimal,
    compare_records,
    consumer_capability_gate,
    evaluate_record,
    finalize_record,
    generate_comparability_key,
    issue_hash_bound_execution_receipt,
    reconcile_exclusive_partition,
    validate_invariants,
    validate_structure,
)

ROOT = Path(__file__).parent
FIXTURES = json.loads((ROOT / "fr0333_genius_bar_comparability_fixtures_0001.json").read_text())
BASE = FIXTURES["base_record"]


def rec():
    return copy.deepcopy(BASE)


class GeniusBarComparabilityTests(unittest.TestCase):
    def test_00_schema_blueprint_has_atomic_profiles(self):
        schema = json.loads((ROOT / "fr0333_genius_bar_comparability_normalization_0001.schema.json").read_text())
        self.assertIn("precision_profile", schema["required"])
        self.assertIn("segmentation_architecture", schema["required"])
        self.assertIn("transformation_receipt", schema["required"])
        self.assertFalse(schema["additionalProperties"])

    def test_n01_relative_increase(self):
        r = finalize_record(rec())
        self.assertEqual(r["current_reference"]["value"], 171)
        self.assertEqual(evaluate_record(r)[0], PASS)

    def test_n02_of_baseline(self):
        r = rec()
        r.update({"source_value": 71, "semantic_type": "OF.BASELINE", "transform_rule": "OF.BASELINE.BASE100"})
        r["source_semantics"]["operator"] = "OF.BASELINE"
        r["source_semantics"]["raw_expression"] = "71 of baseline"
        r["current_reference"]["value"] = 71
        r = finalize_record(r)
        self.assertEqual(evaluate_record(r)[0], PASS)
        self.assertEqual(r["current_reference"]["value"] - 100, -29)

    def test_n03_composition_share(self):
        r = rec()
        r.update({"source_value": 74.2, "semantic_type": "COMPOSITION.SHARE", "transform_rule": "COMPOSITION.SHARE.FIELD100"})
        r["source_semantics"] = {"operator": "COMPOSITION.SHARE", "raw_expression": "74.2 of field"}
        r["reference_frame"] = {"base_reference": None, "field_base": 100}
        r["current_reference"]["value"] = 74.2
        r = finalize_record(r)
        self.assertEqual(evaluate_record(r)[0], PASS)

    def test_n04_same_number_different_semantics_different_key(self):
        a = finalize_record(rec())
        b = rec()
        b.update({"semantic_type": "OF.BASELINE", "transform_rule": "OF.BASELINE.BASE100"})
        b["source_semantics"]["operator"] = "OF.BASELINE"
        b["current_reference"]["value"] = 71
        b = finalize_record(b)
        self.assertNotEqual(a["comparability_key"], b["comparability_key"])

    def test_n05_missing_denominator_holds(self):
        r = rec()
        r["denominator_id"] = ""
        self.assertEqual(validate_invariants(r)[0], HOLD)

    def test_n06_semantic_contradiction_rejects(self):
        r = rec()
        r["source_semantics"]["operator"] = "COMPOSITION.SHARE"
        self.assertEqual(validate_invariants(r)[0], REJECT)

    def test_n07_missing_receipt_holds(self):
        r = rec()
        r["comparability_key"] = generate_comparability_key(r)
        self.assertEqual(evaluate_record(r)[0], HOLD)

    def test_n08_approx_passes_normalization_but_exact_consumer_holds(self):
        r = rec()
        r["source_value"] = 25
        r["current_reference"]["value"] = 125
        r["precision_profile"].update({"source_qualifier": "APPROX", "precision_state": "APPROX"})
        r = finalize_record(r)
        self.assertEqual(evaluate_record(r)[0], PASS)
        state, _ = consumer_capability_gate(r, {"requires": "EXACT", "approximation_policy": "NONE"})
        self.assertEqual(state, HOLD)
        state, _ = consumer_capability_gate(r, {"requires": "APPROX.ALLOWED", "approximation_policy": "PRESERVE.QUALIFIER"})
        self.assertEqual(state, PASS)

    def test_n09_range_preserved_without_midpoint(self):
        r = rec()
        r["source_value"] = None
        r["source_range"] = {"lower": 20, "upper": 30}
        r["current_reference"] = {"value": None, "lower_bound": 120, "upper_bound": 130}
        r["precision_profile"].update({"source_qualifier": "RANGE", "precision_state": "APPROX"})
        r = finalize_record(r)
        self.assertEqual(evaluate_record(r)[0], PASS)
        self.assertIsNone(r["current_reference"]["value"])

    def test_n10_time_basis_difference_holds_comparison(self):
        a = finalize_record(rec())
        b = rec()
        b["comparability_metadata"]["time_basis_id"] = "Q3.2025"
        b = finalize_record(b)
        self.assertEqual(compare_records(a, b)[0], HOLD)

    def test_n11_denominator_difference_holds_comparison(self):
        a = finalize_record(rec())
        b = rec()
        b["denominator_id"] = "US.HOUSEHOLDS.BASE"
        b = finalize_record(b)
        self.assertEqual(compare_records(a, b)[0], HOLD)

    def test_n12_inverse_corruption_rejects(self):
        r = finalize_record(rec())
        r["current_reference"]["value"] = 171.0005
        self.assertEqual(evaluate_record(r)[0], REJECT)

    def test_formatting_noise_does_not_change_key(self):
        a = finalize_record(rec())
        b = rec()
        b["comparability_metadata"]["population_id"] = "  u.s.   adults  "
        b = finalize_record(b)
        self.assertEqual(a["comparability_key"], b["comparability_key"])

    def test_canonical_decimal_equality_is_not_raw_byte_identity(self):
        self.assertEqual(canonical_decimal(71, "NONE"), canonical_decimal("71.0000", "NONE"))

    def test_precision_laundering_rejects(self):
        r = rec()
        r["source_value"] = 25
        r["current_reference"]["value"] = 125
        r["precision_profile"].update({"source_qualifier": "APPROX", "precision_state": "APPROX"})
        r = finalize_record(r)
        state, _ = consumer_capability_gate(r, {
            "requires": "APPROX.ALLOWED",
            "approximation_policy": "PRESERVE.QUALIFIER",
            "detach_precision_profile": True,
        })
        self.assertEqual(state, REJECT)

    def test_structural_missing_precision_holds(self):
        r = rec()
        del r["precision_profile"]
        self.assertEqual(validate_structure(r)[0], HOLD)

    def test_exclusive_partition_reconciler(self):
        self.assertEqual(reconcile_exclusive_partition([40, 35, 25])[0], PASS)
        self.assertEqual(reconcile_exclusive_partition([40, 35, 24])[0], HOLD)

    def test_hash_bound_receipt_is_explicitly_unsigned(self):
        r = finalize_record(rec())
        receipt = issue_hash_bound_execution_receipt(r)
        self.assertEqual(receipt["signature_state"], "NOT.CRYPTOGRAPHICALLY.SIGNED")
        self.assertEqual(len(receipt["receipt_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
