#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path

from revenue_auditance_runtime import RuntimeValidationError, build_receipt, receipt_hash, validate_event

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "RavenCloudTaskbar" / "fr0333_revenue_auditance_runtime_fixtures.json"


class RevenueAuditanceRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(FIXTURES.read_text(encoding="utf-8"))

    def test_fixture_expectations(self) -> None:
        passes = 0
        expected_failures = 0
        for fixture in self.data["events"]:
            event = fixture["event"]
            if fixture["expect"] == "PASS":
                validated = validate_event(event)
                self.assertEqual(validated["event_id"], event["event_id"])
                self.assertEqual(len(validated["receipt_hash"]), 64)
                passes += 1
            else:
                with self.assertRaises(RuntimeValidationError) as caught:
                    validate_event(event)
                self.assertEqual(caught.exception.code, fixture["failure_code"], fixture["name"])
                expected_failures += 1
        self.assertGreaterEqual(passes, 2)
        self.assertGreaterEqual(expected_failures, 3)

    def test_receipt_hash_is_deterministic(self) -> None:
        event = self.data["events"][0]["event"]
        first = receipt_hash(event)
        second = receipt_hash(event)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_receipt_preserves_non_equivalence_gates(self) -> None:
        receipt = build_receipt(self.data["events"][0]["event"])
        gates = receipt["gates"]
        self.assertFalse(gates["money_in_is_revenue"])
        self.assertFalse(gates["available_is_settled"])
        self.assertFalse(gates["settled_is_reconciled"])
        self.assertFalse(gates["reconciled_is_protected"])
        self.assertFalse(gates["protected_is_insured"])
        self.assertFalse(gates["unknown_protection_is_safe"])

    def test_live_event_blocked_in_simulation_mode(self) -> None:
        event = dict(self.data["events"][0]["event"])
        event["event_class"] = "OBSERVED_LIVE"
        with self.assertRaises(RuntimeValidationError) as caught:
            validate_event(event)
        self.assertEqual(caught.exception.code, "LIVE_EVENT_REQUIRES_OBSERVATION_ADAPTER")

    def test_unknown_protection_does_not_promote(self) -> None:
        validated = validate_event(self.data["events"][1]["event"])
        self.assertEqual(validated["bond_status"], "UNKNOWN")
        self.assertEqual(validated["insurance_status"], "UNKNOWN")
        self.assertEqual(validated["fdic_status"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main(verbosity=2)
