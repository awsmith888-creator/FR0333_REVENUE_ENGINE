import json
import unittest
from copy import deepcopy
from pathlib import Path

from M365IntentGate.m365_intent_gate_metrics import (
    Consequence,
    FIXTURE_ID,
    MODULE_ID,
    calculate_metrics,
    classify_suite,
    compile_receipt,
    evaluate,
    load_fixtures,
)


FIXTURE_PATH = Path(__file__).with_name("fixtures.json")
RUN_ID = "00000000-0000-4000-8000-000000000001"
OBSERVED_AT = "2026-09-11T09:00:00Z"


class M365IntentGateMetricTests(unittest.TestCase):
    def setUp(self):
        self.fixtures = load_fixtures(FIXTURE_PATH)
        self.outputs = classify_suite(self.fixtures)

    def test_fixture_suite_identity_and_count(self):
        payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(payload["fixture_suite_id"], FIXTURE_ID)
        self.assertEqual(len(self.fixtures), 12)

    def test_twelve_inputs_produce_twelve_outputs(self):
        self.assertEqual(len(self.outputs), 12)
        self.assertEqual({item["fixture_id"] for item in self.fixtures}, {item["fixture_id"] for item in self.outputs})

    def test_metric_baseline(self):
        metrics = calculate_metrics(self.fixtures, self.outputs)
        self.assertEqual(metrics, {
            "M.01.INPUT.COUNT": 12,
            "M.02.EXACT.COUNT": 7,
            "M.03.STRONG.COUNT": 3,
            "M.04.AMBIGUOUS.COUNT": 1,
            "M.05.NO.MATCH.COUNT": 1,
            "M.06.CLASSIFIED.OUTPUT.COUNT": 12,
            "M.07.DROPPED.COUNT": 0,
            "M.08.DUPLICATED.COUNT": 0,
            "M.09.CONTRADICTION.COUNT": 1,
            "M.10.BOUNDARY.BREACH.COUNT": 0,
            "M.11.HUMANLOCK.COUNT": 1,
            "M.12.EXTERNAL.EXECUTION.COUNT": 0,
        })

    def test_primary_consequence_distribution(self):
        counts = {}
        for item in self.outputs:
            counts[item["primary_consequence"]] = counts.get(item["primary_consequence"], 0) + 1
        self.assertEqual(counts, {
            Consequence.C0.value: 1,
            Consequence.C1.value: 5,
            Consequence.C2.value: 1,
            Consequence.C3.value: 1,
            Consequence.C4.value: 1,
            Consequence.C5.value: 1,
            Consequence.C6.value: 1,
            Consequence.C8.value: 1,
        })
        self.assertNotIn(Consequence.C9.value, counts)

    def test_f11_reject_primary_and_contradiction_secondary(self):
        record = next(item for item in self.outputs if item["fixture_id"] == "F.11")
        self.assertEqual(record["primary_consequence"], Consequence.C8.value)
        self.assertEqual(record["secondary_flags"], [Consequence.C7.value])

    def test_f12_repeated_wording_is_not_duplicate_identity(self):
        f02 = next(item for item in self.fixtures if item["fixture_id"] == "F.02")
        f12 = next(item for item in self.fixtures if item["fixture_id"] == "F.12")
        self.assertEqual(f02["source_intent"], f12["source_intent"])
        self.assertNotEqual(f02["fixture_id"], f12["fixture_id"])
        self.assertEqual(calculate_metrics(self.fixtures, self.outputs)["M.08.DUPLICATED.COUNT"], 0)

    def test_provider_envelopes_remain_blocked(self):
        self.assertTrue(all(item["provider_request_envelopes"] == [] for item in self.outputs))
        receipt = compile_receipt(self.fixtures, self.outputs, RUN_ID, OBSERVED_AT)
        self.assertEqual(receipt["PROVIDER.ENVELOPE.STATE"], "BLOCKED")

    def test_external_action_routes_to_humanlock_without_execution(self):
        f08 = next(item for item in self.outputs if item["fixture_id"] == "F.08")
        self.assertEqual(f08["primary_consequence"], Consequence.C4.value)
        self.assertTrue(f08["humanlock_required"])
        self.assertEqual(f08["external_execution_count"], 0)

    def test_receipt_is_deterministic(self):
        first = compile_receipt(self.fixtures, self.outputs, RUN_ID, OBSERVED_AT)
        second = compile_receipt(self.fixtures, self.outputs, RUN_ID, OBSERVED_AT)
        self.assertEqual(first, second)
        self.assertEqual(first["SOURCE_LOCK"], MODULE_ID)
        self.assertEqual(len(first["RECEIPT.SHA256"]), 64)

    def test_receipt_requires_uuid4(self):
        with self.assertRaises(ValueError):
            compile_receipt(self.fixtures, self.outputs, "NOT.A.UUID", OBSERVED_AT)

    def test_duplicate_fixture_id_rejected(self):
        changed = deepcopy(self.fixtures)
        changed[-1]["fixture_id"] = changed[0]["fixture_id"]
        with self.assertRaises(ValueError):
            classify_suite(changed)

    def test_invalid_route_shape_rejected(self):
        changed = deepcopy(self.fixtures)
        changed[1]["candidate_routes"] = ["SHAREPOINT", "POWER_BI"]
        with self.assertRaises(ValueError):
            classify_suite(changed)

    def test_mutation_drop_output_returns_c9_without_receipt(self):
        result = evaluate(self.fixtures, self.outputs[:-1], RUN_ID, OBSERVED_AT)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["consequence"], Consequence.C9.value)
        self.assertIsNone(result["receipt"])

    def test_mutation_duplicate_output_returns_c9_without_receipt(self):
        changed = deepcopy(self.outputs) + [deepcopy(self.outputs[0])]
        result = evaluate(self.fixtures, changed, RUN_ID, OBSERVED_AT)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["consequence"], Consequence.C9.value)
        self.assertIsNone(result["receipt"])

    def test_mutation_external_execution_returns_c9_without_receipt(self):
        changed = deepcopy(self.outputs)
        changed[0]["external_execution_count"] = 1
        result = evaluate(self.fixtures, changed, RUN_ID, OBSERVED_AT)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["consequence"], Consequence.C9.value)
        self.assertIsNone(result["receipt"])

    def test_mutation_invalid_confidence_sum_returns_c9_without_receipt(self):
        changed = deepcopy(self.fixtures)
        changed[0]["confidence"] = "UNCOUNTED.STATE"
        result = evaluate(changed, self.outputs, RUN_ID, OBSERVED_AT)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["consequence"], Consequence.C9.value)
        self.assertIsNone(result["receipt"])


if __name__ == "__main__":
    unittest.main()
