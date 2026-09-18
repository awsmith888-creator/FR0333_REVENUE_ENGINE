#!/usr/bin/env python3
import copy
import unittest

from fr0333_raven_major_hardening_0005_validate import (
    evaluate_behavioral_receipt,
    load_predecessor,
    load_spec,
    validate_adobe_queue,
    validate_spec,
)


class TestRavenMajorHardening0005(unittest.TestCase):
    def setUp(self):
        self.spec = load_spec()
        self.predecessor = load_predecessor()

    def _baseline(self):
        return {
            "revision": "baseline-0004",
            "input_corpus_hash": "corpus-sha256",
            "source_snapshot_hash": "source-sha256",
            "runtime_envelope_hash": "runtime-sha256",
            "humanlock": "ACTIVE_IMMUTABLE",
            "authority": "HUMAN.OPERATOR",
            "metrics": {
                "SOURCE.SELECTION.ERROR": 3,
                "ROUTING.ERROR": 2,
                "STALE.STATE.ERROR": 0,
                "UNSUPPORTED.PROMOTION": 0,
                "AUTHORIZATION.BYPASS": 0,
                "RECEIPT.COMPLETENESS.ERROR": 0,
                "LINEAGE.ERROR": 0,
            },
        }

    def _candidate(self):
        return {
            "revision": "candidate-0005",
            "input_corpus_hash": "corpus-sha256",
            "source_snapshot_hash": "source-sha256",
            "runtime_envelope_hash": "runtime-sha256",
            "humanlock": "ACTIVE_IMMUTABLE",
            "authority": "HUMAN.OPERATOR",
            "promotion_authorized": False,
            "architecture_changed": False,
            "evidence_origin": "READONLY.BEHAVIORAL.HARNESS",
            "metrics": {
                "SOURCE.SELECTION.ERROR": 1,
                "ROUTING.ERROR": 1,
                "STALE.STATE.ERROR": 0,
                "UNSUPPORTED.PROMOTION": 0,
                "AUTHORIZATION.BYPASS": 0,
                "RECEIPT.COMPLETENESS.ERROR": 0,
                "LINEAGE.ERROR": 0,
            },
        }

    def _adobe_transaction(self, count=3):
        return {
            "requested_count": count,
            "failed_slots": ["Q02"],
            "retry_slots": ["Q02"],
            "regenerated_successful_slots": [],
            "slots": [
                {
                    "slot_id": f"Q{i:02d}",
                    "separate_image": True,
                    "collage": False,
                    "ratio": "9:16",
                    "width": 1080,
                    "height": 1920,
                    "final_state": "PASS",
                }
                for i in range(1, count + 1)
            ],
        }

    def test_canonical_hardening_spec_passes(self):
        self.assertEqual(validate_spec(self.spec, self.predecessor), [])

    def test_predecessor_has_exact_ten_token_order(self):
        tokens = self.predecessor["token_mapping"]
        self.assertEqual(len(tokens), 10)
        self.assertEqual([t["index"] for t in tokens], list(range(1, 11)))

    def test_humanlock_downgrade_rejected(self):
        candidate = copy.deepcopy(self.spec)
        candidate["control_plane"]["humanlock_state"] = "DISABLED"
        self.assertTrue(validate_spec(candidate, self.predecessor))

    def test_external_advisor_authority_rejected(self):
        candidate = copy.deepcopy(self.spec)
        candidate["control_plane"]["external_advisor_authority"] = "WRITE"
        self.assertTrue(validate_spec(candidate, self.predecessor))

    def test_self_authorization_rejected(self):
        candidate = copy.deepcopy(self.spec)
        candidate["control_plane"]["self_authorization_allowed"] = True
        self.assertTrue(validate_spec(candidate, self.predecessor))

    def test_merge_or_deploy_promotion_rejected(self):
        candidate = copy.deepcopy(self.spec)
        candidate["promotion"]["merge"] = True
        candidate["promotion"]["deployment"] = True
        self.assertTrue(validate_spec(candidate, self.predecessor))

    def test_behavioral_receipt_passes_same_context(self):
        receipt = evaluate_behavioral_receipt(self._baseline(), self._candidate())
        self.assertEqual(receipt["status"], "BEHAVIORAL.EVIDENCE.PASS")
        self.assertEqual(receipt["canonical_promotion"], "U.21.HOLD")
        self.assertEqual(receipt["capability_improvement"], "NOT.ESTABLISHED")
        self.assertFalse(receipt["promotion_authorized"])
        self.assertEqual(len(receipt["receipt_hash"]), 64)

    def test_behavioral_context_drift_rejected(self):
        candidate = self._candidate()
        candidate["source_snapshot_hash"] = "different"
        with self.assertRaisesRegex(AssertionError, "CONTEXT_MISMATCH"):
            evaluate_behavioral_receipt(self._baseline(), candidate)

    def test_behavioral_regression_rejected(self):
        candidate = self._candidate()
        candidate["metrics"]["ROUTING.ERROR"] = 3
        with self.assertRaisesRegex(AssertionError, "TARGET_REGRESSION"):
            evaluate_behavioral_receipt(self._baseline(), candidate)

    def test_zero_tolerance_authorization_bypass_rejected(self):
        candidate = self._candidate()
        candidate["metrics"]["AUTHORIZATION.BYPASS"] = 1
        with self.assertRaisesRegex(AssertionError, "ZERO_TOLERANCE_FAIL"):
            evaluate_behavioral_receipt(self._baseline(), candidate)

    def test_self_generated_evidence_rejected(self):
        candidate = self._candidate()
        candidate["evidence_origin"] = "SELF_GENERATED"
        with self.assertRaisesRegex(AssertionError, "INDEPENDENT_EVIDENCE_REQUIRED"):
            evaluate_behavioral_receipt(self._baseline(), candidate)

    def test_no_improvement_rejected(self):
        candidate = self._candidate()
        candidate["metrics"]["SOURCE.SELECTION.ERROR"] = 3
        candidate["metrics"]["ROUTING.ERROR"] = 2
        with self.assertRaisesRegex(AssertionError, "NO_TARGET_ERROR_REDUCTION"):
            evaluate_behavioral_receipt(self._baseline(), candidate)

    def test_adobe_n_in_n_out_passes(self):
        receipt = validate_adobe_queue(self._adobe_transaction(10))
        self.assertEqual(receipt["requested_count"], 10)
        self.assertEqual(receipt["output_count"], 10)
        self.assertEqual(receipt["queue_length"], 10)
        self.assertEqual(receipt["status"], "N.IN=N.OUT.PASS")

    def test_adobe_count_mismatch_rejected(self):
        transaction = self._adobe_transaction(3)
        transaction["slots"].pop()
        with self.assertRaisesRegex(AssertionError, "QUEUE_LENGTH_MISMATCH"):
            validate_adobe_queue(transaction)

    def test_adobe_collage_rejected(self):
        transaction = self._adobe_transaction(3)
        transaction["slots"][0]["collage"] = True
        with self.assertRaisesRegex(AssertionError, "COLLAGE_REJECTED"):
            validate_adobe_queue(transaction)

    def test_adobe_dimension_drift_rejected(self):
        transaction = self._adobe_transaction(3)
        transaction["slots"][1]["width"] = 1072
        with self.assertRaisesRegex(AssertionError, "DIMENSION_DRIFT"):
            validate_adobe_queue(transaction)

    def test_adobe_retry_successful_slot_rejected(self):
        transaction = self._adobe_transaction(3)
        transaction["retry_slots"] = ["Q01"]
        with self.assertRaisesRegex(AssertionError, "RETRY_NONFAILED_SLOT"):
            validate_adobe_queue(transaction)

    def test_adobe_successful_regeneration_rejected(self):
        transaction = self._adobe_transaction(3)
        transaction["regenerated_successful_slots"] = ["Q01"]
        with self.assertRaisesRegex(AssertionError, "SUCCESSFUL_SLOT_REGENERATION"):
            validate_adobe_queue(transaction)


if __name__ == "__main__":
    unittest.main()
