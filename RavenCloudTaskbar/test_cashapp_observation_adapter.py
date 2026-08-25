#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path

from cashapp_observation_adapter import (
    ObservationValidationError,
    normalize_cashapp_observation,
    observation_receipt_hash,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "RavenCloudTaskbar" / "fr0333_cashapp_observation_fixtures.json"


class CashAppObservationAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(FIXTURES.read_text(encoding="utf-8"))

    def test_fixture_expectations(self) -> None:
        passes = 0
        expected_failures = 0
        for fixture in self.data["records"]:
            if fixture["expect"] == "PASS":
                receipt = normalize_cashapp_observation(fixture["record"])
                self.assertEqual(receipt["provider"], "CASH_APP")
                self.assertEqual(receipt["mode"], "READ_ONLY")
                self.assertEqual(len(receipt["observation_receipt_hash"]), 64)
                passes += 1
            else:
                with self.assertRaises(ObservationValidationError) as caught:
                    normalize_cashapp_observation(fixture["record"])
                self.assertEqual(caught.exception.code, fixture["failure_code"], fixture["name"])
                expected_failures += 1
        self.assertEqual(passes, 2)
        self.assertEqual(expected_failures, 5)

    def test_provider_completed_status_does_not_become_settled(self) -> None:
        receipt = normalize_cashapp_observation(self.data["records"][0]["record"])
        event = receipt["normalized_runtime_event"]
        self.assertEqual(receipt["source_status_observed"], "COMPLETED")
        self.assertEqual(event["settlement_status"], "UNKNOWN")
        self.assertEqual(event["reconciliation_status"], "NOT_RECONCILED")
        self.assertIsNone(event["settled_at"])
        self.assertIsNone(event["reconciled_at"])

    def test_no_automatic_protection_revenue_or_value_promotion(self) -> None:
        receipt = normalize_cashapp_observation(self.data["records"][0]["record"])
        event = receipt["normalized_runtime_event"]
        self.assertEqual(event["bond_status"], "NOT_VERIFIED")
        self.assertEqual(event["insurance_status"], "NOT_VERIFIED")
        self.assertEqual(event["fdic_status"], "NOT_VERIFIED")
        self.assertEqual(event["value_realized"], "UNKNOWN")
        self.assertEqual(event["reserve_amount"], "UNKNOWN")
        self.assertEqual(event["amount_net"], "UNKNOWN")
        self.assertEqual(event["refund_exposure"], "UNKNOWN")
        self.assertEqual(event["chargeback_exposure"], "UNKNOWN")

    def test_observation_has_no_money_authority(self) -> None:
        receipt = normalize_cashapp_observation(self.data["records"][0]["record"])
        self.assertEqual(receipt["live_money_movement"], 0)
        self.assertEqual(receipt["live_financial_execution"], 0)
        self.assertFalse(receipt["authority_to_move_funds"])
        self.assertEqual(
            receipt["normalized_runtime_event"]["authority_id"],
            "READ_ONLY_OBSERVATION_NO_MONEY_AUTHORITY",
        )

    def test_provider_evidence_pointer_binds_source_hash(self) -> None:
        receipt = normalize_cashapp_observation(self.data["records"][0]["record"])
        self.assertIn("sha256=", receipt["provider_evidence_pointer"])
        self.assertTrue(receipt["provider_evidence_pointer"].endswith("a" * 64))

    def test_observation_receipt_hash_is_deterministic(self) -> None:
        first = normalize_cashapp_observation(self.data["records"][0]["record"])
        second = normalize_cashapp_observation(self.data["records"][0]["record"])
        self.assertEqual(first["observation_receipt_hash"], second["observation_receipt_hash"])
        self.assertEqual(observation_receipt_hash(first), first["observation_receipt_hash"])

    def test_runtime_event_requires_provider_evidence(self) -> None:
        receipt = normalize_cashapp_observation(self.data["records"][0]["record"])
        evidence = receipt["normalized_runtime_event"]["source_evidence"]
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0]["evidence_class"], "PROVIDER_RECORD")


if __name__ == "__main__":
    unittest.main(verbosity=2)
