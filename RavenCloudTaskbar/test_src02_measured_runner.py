#!/usr/bin/env python3
from __future__ import annotations

import copy
import unittest

from src02_measured_runner import (
    SRC02ValidationError,
    build_opportunity_records,
    build_source_set,
    canonicalize_uri,
    run,
    score_run,
    validate_comparator_controls,
)


def fixture() -> dict:
    return {
        "run_id": "FR0333-SRC02-TEST-0001",
        "query_id": "Q.0001",
        "started_at": "2026-09-01T13:00:00-04:00",
        "retrieved_at": "2026-09-01T13:00:01-04:00",
        "retrieval_method": "WEB",
        "execution_class": "LOCAL_INTERNAL",
        "raw_sources": [
            {
                "uri": "https://example.gov/opportunity?id=7&utm_source=test",
                "source_class": "PRIMARY",
                "title": "Official opportunity",
                "publisher": "Example Agency",
                "published_at": "2026-09-01T12:00:00-04:00",
                "raw_content": "official funding amount 100",
                "capture_pointer": "receipt://0",
            },
            {
                "uri": "https://example.gov/opportunity?id=7",
                "source_class": "PRIMARY",
                "title": "Official opportunity duplicate",
                "publisher": "Example Agency",
                "published_at": "2026-09-01T12:00:00-04:00",
                "raw_content": "official funding amount 100",
                "capture_pointer": "receipt://1",
            },
            {
                "uri": "https://news.example.com/report",
                "source_class": "SECONDARY",
                "title": "Independent report",
                "publisher": "Example News",
                "published_at": "2026-09-01T12:30:00-04:00",
                "raw_content": "independent confirmation with a contradiction",
                "capture_pointer": "receipt://2",
            },
        ],
        "opportunities": [
            {
                "candidate_key": "example-opportunity",
                "title": "Example Opportunity",
                "qualification_state": "QUALIFIED",
                "scam_risk_state": "PASS",
                "pricing_state": "VERIFIED",
                "funding_state": "VERIFIED",
                "source_indexes": [0, 2],
                "claims": [
                    {
                        "claim_id": "funding",
                        "field": "funding",
                        "value": "100",
                        "evidence_state": "VERIFIED",
                        "evidence_refs": [
                            {"retrieval_index": 0, "selector": "funding amount"},
                            {"retrieval_index": 2, "selector": "independent confirmation"},
                        ],
                    },
                    {
                        "claim_id": "deadline",
                        "field": "deadline",
                        "value": None,
                        "evidence_state": "CONTRADICTED",
                        "evidence_refs": [
                            {"retrieval_index": 0, "selector": "deadline"},
                            {"retrieval_index": 2, "selector": "deadline"},
                        ],
                    },
                ],
                "unresolved_gaps": ["deadline"],
                "humanlock": {
                    "state": "APPROVED",
                    "actor": "TEST.HUMAN",
                    "decided_at": "2026-09-01T13:01:01-04:00",
                },
            }
        ],
        "scoring_labels": {
            "known_contradiction_total": 2,
            "required_claim_fields": ["funding", "deadline"],
            "adjudications": [
                {"candidate_key": "example-opportunity", "outcome": "CONFIRMED"}
            ],
        },
    }


class SRC02MeasuredRunnerTests(unittest.TestCase):
    def test_tracking_parameters_do_not_create_false_uniques(self) -> None:
        self.assertEqual(
            canonicalize_uri("https://Example.GOV/a?utm_source=x&id=7#fragment"),
            "https://example.gov/a?id=7",
        )

    def test_source_set_preserves_duplicate_as_one_unique_source(self) -> None:
        source_set = build_source_set(fixture())
        self.assertEqual(len(source_set["sources"]), 3)
        self.assertEqual(source_set["sources"][0]["duplicate_state"], "UNIQUE")
        self.assertEqual(source_set["sources"][1]["duplicate_state"], "DUPLICATE")
        self.assertEqual(source_set["sources"][1]["duplicate_of"], source_set["sources"][0]["source_id"])
        self.assertEqual(len(source_set["source_set_hash"]), 64)

    def test_opportunity_references_source_objects_by_id_and_hash(self) -> None:
        data = fixture()
        source_set = build_source_set(data)
        records = build_opportunity_records(data, source_set)
        self.assertEqual(len(records), 1)
        ref = records[0]["source_refs"][0]
        self.assertTrue(ref["source_id"].startswith("SRC02-SRC-"))
        self.assertEqual(len(ref["content_sha256"]), 64)
        self.assertNotIn("raw_content", records[0])

    def test_verified_claim_cannot_exist_without_source_reference(self) -> None:
        data = fixture()
        data["opportunities"][0]["claims"][0]["evidence_refs"] = []
        source_set = build_source_set(data)
        with self.assertRaises(SRC02ValidationError) as caught:
            build_opportunity_records(data, source_set)
        self.assertEqual(caught.exception.code, "VERIFIED_CLAIM_REQUIRES_SOURCE")

    def test_scoring_keeps_uncontrolled_contradiction_denominator_unknown(self) -> None:
        data = fixture()
        data["scoring_labels"].pop("known_contradiction_total")
        source_set = build_source_set(data)
        records = build_opportunity_records(data, source_set)
        score = score_run(data, source_set, records)
        self.assertEqual(score["contradictions_detected"], 1)
        self.assertIsNone(score["contradiction_capture"]["denominator"])
        self.assertIsNone(score["contradiction_capture"]["per_1000"])

    def test_scoring_metrics(self) -> None:
        receipt = run(fixture())
        score = receipt["score"]
        self.assertEqual(score["retrieval_count"], 3)
        self.assertEqual(score["unique_source_yield"]["numerator"], 2)
        self.assertEqual(score["unique_source_yield"]["denominator"], 3)
        self.assertEqual(score["duplicate_rate"]["numerator"], 1)
        self.assertEqual(score["primary_source_ratio"]["numerator"], 1)
        self.assertEqual(score["primary_source_ratio"]["denominator"], 2)
        self.assertEqual(score["corroboration_coverage"]["numerator"], 1)
        self.assertEqual(score["contradiction_capture"]["numerator"], 1)
        self.assertEqual(score["contradiction_capture"]["denominator"], 2)
        self.assertEqual(score["evidence_coverage"]["numerator"], 1)
        self.assertEqual(score["evidence_coverage"]["denominator"], 2)
        self.assertEqual(score["unresolved_gap_count"], 1)
        self.assertEqual(score["lineage_coverage"]["numerator"], 1)
        self.assertEqual(score["latency_per_verified_opportunity"]["median_seconds"], 61.0)
        self.assertEqual(score["false_promotion_rate"]["numerator"], 0)
        self.assertEqual(score["false_promotion_rate"]["denominator"], 1)
        self.assertTrue(receipt["scenario_not_forecast"])
        self.assertTrue(receipt["forecast_promotion_blocked"])
        self.assertEqual(len(receipt["receipt_hash"]), 64)

    def test_false_promotion_rate_stays_unknown_without_complete_adjudication(self) -> None:
        data = fixture()
        data["scoring_labels"]["adjudications"] = []
        receipt = run(data)
        self.assertEqual(receipt["score"]["false_promotions_detected"], 0)
        self.assertEqual(receipt["score"]["false_promotion_adjudication_coverage"]["numerator"], 0)
        self.assertEqual(receipt["score"]["false_promotion_adjudication_coverage"]["denominator"], 1)
        self.assertIsNone(receipt["score"]["false_promotion_rate"]["denominator"])
        self.assertIsNone(receipt["score"]["false_promotion_rate"]["per_1000"])

    def test_false_promotion_requires_later_rejection_label(self) -> None:
        data = fixture()
        data["scoring_labels"]["adjudications"][0]["outcome"] = "REJECTED"
        receipt = run(data)
        rate = receipt["score"]["false_promotion_rate"]
        self.assertEqual(rate["numerator"], 1)
        self.assertEqual(rate["denominator"], 1)

    def test_comparator_requires_all_four_controls_equal(self) -> None:
        controls = {
            "query_set_hash": "a" * 64,
            "time_window": "2026-09-01T13:00:00-04:00/2026-09-01T14:00:00-04:00",
            "eligibility_rules_hash": "b" * 64,
            "scoring_function_version": "SRC02.SCORING.1",
        }
        result = validate_comparator_controls(controls, copy.deepcopy(controls))
        self.assertTrue(result["comparator_ready"])
        changed = copy.deepcopy(controls)
        changed["time_window"] = "different"
        result = validate_comparator_controls(controls, changed)
        self.assertFalse(result["comparator_ready"])
        self.assertEqual(result["mismatched_controls"], ["time_window"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
