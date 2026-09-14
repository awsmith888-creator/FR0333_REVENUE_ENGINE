import copy
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from canonical_hash import canonical_hash
from rsi_delta_monitor import compare_observations


def source_receipt(source_id, claims):
    payload = {
        "source_id": source_id,
        "source_type": "official_webpage",
        "publisher": "Example",
        "title": "Primary source",
        "published_at": "UNDATED",
        "retrieved_at": "2026-09-14",
        "url": "https://example.com/source",
        "evidence_class": "OFFICIAL.PRIMARY.SOURCE",
        "summary": "Bounded test receipt.",
        "claims_observed": claims,
    }
    payload["payload_hash"] = canonical_hash(payload)
    return payload


class RSIDeltaMonitorTests(unittest.TestCase):
    def setUp(self):
        self.baseline = {
            "record_id": "FR0333.RSI.OBSERVATION.PIPELINE.0001",
            "timestamp": "2026-09-14T00:00:00Z",
            "topic": "bounded_recursive_self_improvement",
            "sources": ["base"],
            "claims": {"A": "T.20", "B": "U.21", "C": "F.6"},
        }

    def test_new_verified_claim_requires_primary_binding(self):
        candidate = copy.deepcopy(self.baseline)
        candidate["record_id"] = "FR0333.RSI.OBSERVATION.PIPELINE.0002"
        candidate["timestamp"] = "2026-09-14T01:00:00Z"
        candidate["sources"].append("source.new")
        candidate["claims"]["D"] = "T.20"
        candidate["claim_sources"] = {"D": ["source.new"]}
        report = compare_observations(
            self.baseline,
            candidate,
            [source_receipt("source.new", ["D"])],
        )
        self.assertEqual(report["new_verified_facts"], ["D"])

    def test_unsourced_new_t20_is_rejected(self):
        candidate = copy.deepcopy(self.baseline)
        candidate["claims"]["D"] = "T.20"
        candidate["claim_sources"] = {}
        with self.assertRaisesRegex(AssertionError, "UNSOURCED_NEW_ASSERTION"):
            compare_observations(self.baseline, candidate, [])

    def test_unsourced_new_f6_is_rejected(self):
        candidate = copy.deepcopy(self.baseline)
        candidate["claims"]["D"] = "F.6"
        candidate["claim_sources"] = {}
        with self.assertRaisesRegex(AssertionError, "UNSOURCED_NEW_ASSERTION"):
            compare_observations(self.baseline, candidate, [])

    def test_claim_deletion_is_rejected(self):
        candidate = copy.deepcopy(self.baseline)
        del candidate["claims"]["A"]
        with self.assertRaisesRegex(AssertionError, "CLAIM_DELETION"):
            compare_observations(self.baseline, candidate, [])

    def test_u21_promotion_requires_transition_receipt(self):
        candidate = copy.deepcopy(self.baseline)
        candidate["claims"]["B"] = "T.20"
        with self.assertRaisesRegex(AssertionError, "UNAUTHORIZED_STATE_CHANGE"):
            compare_observations(self.baseline, candidate, [])

    def test_invalid_source_receipt_is_rejected(self):
        candidate = copy.deepcopy(self.baseline)
        candidate["claims"]["D"] = "T.20"
        candidate["claim_sources"] = {"D": ["source.new"]}
        bad = source_receipt("source.new", ["D"])
        bad["payload_hash"] = "sha256_" + "0" * 64
        with self.assertRaisesRegex(AssertionError, "INVALID_SOURCE_RECEIPT"):
            compare_observations(self.baseline, candidate, [bad])

    def test_stable_unknown_remains_retained(self):
        candidate = copy.deepcopy(self.baseline)
        report = compare_observations(self.baseline, candidate, [])
        self.assertEqual(report["retained_unknowns"], ["B"])


if __name__ == "__main__":
    unittest.main()
