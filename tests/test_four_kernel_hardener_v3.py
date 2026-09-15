import copy
import json
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from four_kernel_hardener_v3 import evaluate_four_kernel_transaction_v3

TX_PATH = ROOT / "receipts" / "operator" / "2026-09-15" / "four_kernel.transaction.v3.json"


def transaction():
    return json.loads(TX_PATH.read_text(encoding="utf-8"))


def claim(tx, claim_id):
    return next(c for c in tx["evidence_hardening"]["claims"] if c["claim_id"] == claim_id)


class FourKernelHardenerV3Tests(unittest.TestCase):
    def test_v3_opens_hardening_route_without_auto_promotion(self):
        result = evaluate_four_kernel_transaction_v3(transaction())
        self.assertEqual(result["operator_route"], "OPEN")
        self.assertEqual(result["system_hardening_route"], "OPEN")
        self.assertEqual(result["canonical_promotion"], "U.21.HUMAN.REVIEW.REQUIRED")
        self.assertFalse(result["automatic_promotion"])

    def test_four_kernel_structure_is_preserved(self):
        result = evaluate_four_kernel_transaction_v3(transaction())
        self.assertEqual(set(result["kernels"]), {"NEWSFLASH", "ESPN.FANTASY.SPORTS", "NELSON", "GENIUS.BAR"})
        self.assertEqual(result["statistics"]["kernel_bitword"], "1111")

    def test_unbound_t20_source_holds(self):
        tx = transaction()
        claim(tx, "UK.SLAVE.OWNER.COMPENSATION.20M")["source_ids"] = ["SRC.DOES.NOT.EXIST"]
        result = evaluate_four_kernel_transaction_v3(tx)
        self.assertEqual(result["system_hardening_route"], "HOLD")
        self.assertFalse(result["evidence_hardening"]["gates"]["CLAIM.SOURCE.BOUND"])

    def test_duplicate_source_ids_hold(self):
        tx = transaction()
        tx["evidence_hardening"]["source_receipts"][1]["source_id"] = tx["evidence_hardening"]["source_receipts"][0]["source_id"]
        result = evaluate_four_kernel_transaction_v3(tx)
        self.assertFalse(result["evidence_hardening"]["gates"]["SOURCE.PROVENANCE.BOUND"])
        self.assertEqual(result["system_hardening_route"], "HOLD")

    def test_shared_origin_does_not_count_as_independent(self):
        tx = transaction()
        tx["evidence_hardening"]["source_receipts"][2]["independence_group"] = "UCL"
        result = evaluate_four_kernel_transaction_v3(tx)
        self.assertFalse(result["evidence_hardening"]["gates"]["SOURCE.INDEPENDENCE.BOUND"])

    def test_causal_t20_requires_peer_review_and_bounded_scope(self):
        tx = transaction()
        c = claim(tx, "US.REDLINING.PERSISTENT.SEGREGATION")
        c["causal_scope"] = "UNBOUNDED"
        result = evaluate_four_kernel_transaction_v3(tx)
        self.assertFalse(result["evidence_hardening"]["gates"]["CAUSAL.SCOPE.BOUNDED"])

    def test_absolute_language_cannot_be_promoted_t20(self):
        tx = transaction()
        claim(tx, "HISTORICAL.WEALTH.TRANSFER.INSTITUTIONAL.RECORD")["absolute_language"] = True
        result = evaluate_four_kernel_transaction_v3(tx)
        self.assertFalse(result["evidence_hardening"]["gates"]["ABSOLUTE.LANGUAGE.GUARD"])

    def test_rejected_absolutes_remain_f6(self):
        tx = transaction()
        tx["evidence_hardening"]["rejected_absolutes"][0]["state"] = "T.20"
        result = evaluate_four_kernel_transaction_v3(tx)
        self.assertFalse(result["evidence_hardening"]["gates"]["ABSOLUTE.LANGUAGE.GUARD"])

    def test_un_resolution_is_not_misrepresented_as_binding(self):
        tx = transaction()
        claim(tx, "UNGA.A.RES.80.250.VOTE")["resolution_effect"] = "BINDING.CASH.AWARD"
        result = evaluate_four_kernel_transaction_v3(tx)
        self.assertFalse(result["evidence_hardening"]["gates"]["LEGAL.EFFECT.SEPARATED"])

    def test_un_vote_no_states_are_exact(self):
        tx = transaction()
        claim(tx, "UNGA.A.RES.80.250.VOTE")["vote_no_states"] = ["ARGENTINA", "JERUSALEM", "UNITED.STATES"]
        result = evaluate_four_kernel_transaction_v3(tx)
        self.assertFalse(result["evidence_hardening"]["gates"]["LEGAL.EFFECT.SEPARATED"])
        self.assertFalse(result["evidence_hardening"]["gates"]["ENTITY.NORMALIZATION.BOUND"])

    def test_entity_normalization_maps_city_to_state(self):
        result = evaluate_four_kernel_transaction_v3(transaction())
        self.assertTrue(result["evidence_hardening"]["gates"]["ENTITY.NORMALIZATION.BOUND"])

    def test_total_present_day_attribution_remains_u21(self):
        result = evaluate_four_kernel_transaction_v3(transaction())
        self.assertTrue(result["evidence_hardening"]["gates"]["UNRESOLVED.ATTRIBUTION.HELD"])

    def test_total_attribution_cannot_silently_promote(self):
        tx = transaction()
        c = claim(tx, "CURRENT.DISPARITY.TOTAL.ATTRIBUTION")
        c["state"] = "T.20"
        c["promotion_authorized"] = True
        result = evaluate_four_kernel_transaction_v3(tx)
        self.assertFalse(result["evidence_hardening"]["gates"]["UNRESOLVED.ATTRIBUTION.HELD"])
        self.assertEqual(result["system_hardening_route"], "HOLD")

    def test_chomp_is_freeze_stay_not_generation(self):
        result = evaluate_four_kernel_transaction_v3(transaction())
        self.assertEqual(result["chomp_axiom"], "CHOMP.CHOMP=FREEZE+STAY")
        self.assertTrue(result["interaction_hardening"]["gates"]["CHOMP.FREEZE.STAY"])

    def test_count_invariant_is_literal(self):
        tx = transaction()
        tx["interaction_hardening"]["chomp_chomp"]["count_examples"][1]["output"] = 36
        result = evaluate_four_kernel_transaction_v3(tx)
        self.assertFalse(result["interaction_hardening"]["gates"]["COUNT.INVARIANT"])
        self.assertEqual(result["system_hardening_route"], "HOLD")

    def test_chomp_reinterpretation_holds(self):
        tx = transaction()
        tx["interaction_hardening"]["chomp_chomp"]["reinterpret_on_chomp"] = True
        result = evaluate_four_kernel_transaction_v3(tx)
        self.assertFalse(result["interaction_hardening"]["gates"]["NO.REINTERPRET.ON.CHOMP"])

    def test_humanlock_and_runtime_boundaries_remain_active(self):
        result = evaluate_four_kernel_transaction_v3(transaction())
        self.assertEqual(result["humanlock"], "ACTIVE")
        self.assertEqual(result["base_model_weights"], "UNCHANGED")
        self.assertEqual(result["platform_permissions"], "UNCHANGED")

    def test_adobe_runtime_is_not_fabricated(self):
        result = evaluate_four_kernel_transaction_v3(transaction())
        self.assertEqual(result["adobe_route"], "HOLD")
        self.assertEqual(result["adobe_live_traversal_receipt"], "U.21")


if __name__ == "__main__":
    unittest.main()
