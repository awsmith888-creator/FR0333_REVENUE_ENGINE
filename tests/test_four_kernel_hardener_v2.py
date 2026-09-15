import copy
import json
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from four_kernel_hardener_v2 import evaluate_four_kernel_transaction_v2

TX_PATH = ROOT / "receipts" / "operator" / "2026-09-15" / "four_kernel.transaction.v2.json"


def transaction():
    return json.loads(TX_PATH.read_text(encoding="utf-8"))


class FourKernelHardenerV2Tests(unittest.TestCase):
    def test_hardened_transaction_opens_operator_route(self):
        result = evaluate_four_kernel_transaction_v2(transaction())
        self.assertEqual(result["operator_route"], "OPEN")
        self.assertEqual(result["statistics"]["kernel_bitword"], "1111")
        self.assertEqual(result["statistics"]["passed_core_gate_count"], 11)

    def test_pending_role_cannot_pass_nelson(self):
        tx = transaction()
        tx["kernels"]["NELSON"]["receipt"]["status"] = "ROLE.DEFINITION.PENDING"
        result = evaluate_four_kernel_transaction_v2(tx)
        self.assertEqual(result["operator_route"], "HOLD")
        self.assertFalse(result["nelson_measurement_gate"]["role_defined"])

    def test_unbound_source_id_holds_route(self):
        tx = transaction()
        tx["nelson_measurement"]["measurements"][0]["source_id"] = "MISSING.SOURCE"
        result = evaluate_four_kernel_transaction_v2(tx)
        self.assertEqual(result["operator_route"], "HOLD")
        self.assertFalse(result["nelson_measurement_gate"]["metrics_bound"])

    def test_declared_metric_count_must_match_records(self):
        tx = transaction()
        tx["statistics"]["metric_count"] = 25
        result = evaluate_four_kernel_transaction_v2(tx)
        self.assertEqual(result["operator_route"], "HOLD")
        self.assertFalse(result["nelson_measurement_gate"]["declared_counts_match"])

    def test_evening_news_comparison_requires_same_scope(self):
        tx = transaction()
        tx["nelson_measurement"]["comparison_groups"][0]["measurement_period"] = "SEASON.2025.26"
        result = evaluate_four_kernel_transaction_v2(tx)
        self.assertEqual(result["operator_route"], "HOLD")
        self.assertFalse(result["nelson_measurement_gate"]["comparison_scope_bound"])

    def test_60_minutes_remains_context_only(self):
        tx = transaction()
        tx["nelson_measurement"]["comparison_groups"][1]["comparable"] = True
        result = evaluate_four_kernel_transaction_v2(tx)
        self.assertEqual(result["operator_route"], "HOLD")
        self.assertFalse(result["nelson_measurement_gate"]["cross_period_context_isolated"])

    def test_cross_period_ranking_is_rejected(self):
        tx = transaction()
        tx["nelson_measurement"]["cross_period_ranking_allowed"] = True
        result = evaluate_four_kernel_transaction_v2(tx)
        self.assertEqual(result["operator_route"], "HOLD")
        self.assertEqual(result["cross_period_ranking"], "F.6")

    def test_unpublished_specific_telecast_ratings_remain_u21(self):
        result = evaluate_four_kernel_transaction_v2(transaction())
        self.assertTrue(result["nelson_measurement_gate"]["pending_claims_held"])

    def test_adobe_boundary_remains_held(self):
        result = evaluate_four_kernel_transaction_v2(transaction())
        self.assertEqual(result["adobe_route"], "HOLD")
        self.assertEqual(result["adobe_live_traversal_receipt"], "U.21")

    def test_runtime_boundary_preserved(self):
        result = evaluate_four_kernel_transaction_v2(transaction())
        self.assertEqual(result["humanlock"], "ACTIVE")
        self.assertEqual(result["base_model_weights"], "UNCHANGED")
        self.assertEqual(result["platform_permissions"], "UNCHANGED")


if __name__ == "__main__":
    unittest.main()
