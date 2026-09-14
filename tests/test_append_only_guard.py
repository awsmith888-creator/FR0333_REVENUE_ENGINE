import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import unittest

from canonical_hash import canonical_hash
from run_regression_guard import assert_append_only


def new_fact_receipt(key, state):
    payload = {
        "key": key,
        "source_ids": ["source.1"],
        "timestamp": "2026-09-14",
        "evidence_class": "OFFICIAL.PRIMARY.SOURCE",
        "asserted_state": state,
    }
    return {**payload, "payload_hash": canonical_hash(payload)}


def transition_receipt(key, prior, new):
    payload = {
        "key": key,
        "source_ids": ["source.2"],
        "timestamp": "2026-09-14",
        "evidence_class": "OFFICIAL.PRIMARY.SOURCE",
        "prior_state": prior,
        "new_state": new,
    }
    return {**payload, "payload_hash": canonical_hash(payload)}


class AppendOnlyTests(unittest.TestCase):
    def test_deletion_rejected(self):
        with self.assertRaisesRegex(AssertionError, "KEY_DELETED:A"):
            assert_append_only({"A": "U.21"}, {})

    def test_new_t20_without_receipt_rejected(self):
        with self.assertRaisesRegex(AssertionError, "UNSOURCED_NEW_ASSERTION:NEW"):
            assert_append_only({}, {"NEW": "T.20"})

    def test_new_f6_with_valid_receipt_passes(self):
        candidate = {
            "NEW": "F.6",
            "SOURCE.RECEIPT.NEW": new_fact_receipt("NEW", "F.6"),
        }
        assert_append_only({}, candidate)

    def test_u21_to_t20_requires_transition_receipt(self):
        baseline = {"A": "U.21"}
        candidate = {
            "A": "T.20",
            "TRANSITION.RECEIPT.A": transition_receipt("A", "U.21", "T.20"),
        }
        assert_append_only(baseline, candidate)


if __name__ == "__main__":
    unittest.main()
