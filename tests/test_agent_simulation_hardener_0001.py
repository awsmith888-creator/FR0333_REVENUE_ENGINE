import copy
import json
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_simulation_hardener_0001 import evaluate_agent_simulation
from historical_entity_normalizer_0001 import resolve_entity_pair

SIM_PATH = ROOT / "receipts" / "operator" / "2026-09-15" / "agent_simulation.batch.0001.json"
ENTITY_PATH = ROOT / "receipts" / "operator" / "2026-09-15" / "historical_entity_resolution.batch.0001.json"


def simulation():
    return json.loads(SIM_PATH.read_text(encoding="utf-8"))


def entity_batch():
    return json.loads(ENTITY_PATH.read_text(encoding="utf-8"))


class AgentSimulationHardenerTests(unittest.TestCase):
    def test_baseline_simulation_passes_without_live_promotion(self):
        result = evaluate_agent_simulation(simulation())
        self.assertEqual(result["simulation_route"], "PASS")
        self.assertEqual(result["live_deployment"], "U.21.NOT.AUTHORIZED")
        self.assertEqual(result["promotion_state"], "U.21.UNVERIFIED")
        self.assertEqual(result["humanlock"], "ACTIVE")

    def test_read_only_rejects_write_capability(self):
        tx = simulation()
        tx["tool_manifest"].append({"name": "db.write", "signature": "write(record)", "access": "WRITE"})
        result = evaluate_agent_simulation(tx)
        self.assertEqual(result["simulation_route"], "HOLD")
        self.assertFalse(result["gates"]["read_only_respected"])
        self.assertIn("UNSAFE_MUTATION", result["failure_classes"])

    def test_capability_delta_cannot_exceed_safety_coverage(self):
        tx = simulation()
        tx["safety_coverage"]["capability_delta"] = 6
        tx["safety_coverage"]["coverage_level"] = 5
        result = evaluate_agent_simulation(tx)
        self.assertEqual(result["simulation_route"], "HOLD")
        self.assertFalse(result["gates"]["safety_coverage_sufficient"])
        self.assertIn("SAFETY_COVERAGE_GAP", result["failure_classes"])

    def test_forbidden_state_holds(self):
        tx = simulation()
        tx["observed_state"].append("ENTITY_AUTO_MERGE")
        result = evaluate_agent_simulation(tx)
        self.assertEqual(result["simulation_route"], "HOLD")
        self.assertFalse(result["gates"]["forbidden_state_absent"])

    def test_missing_expected_state_holds(self):
        tx = simulation()
        tx["observed_state"].remove("HUMANLOCK_ACTIVE")
        result = evaluate_agent_simulation(tx)
        self.assertEqual(result["simulation_route"], "HOLD")
        self.assertFalse(result["gates"]["expected_state_satisfied"])

    def test_humanlock_must_remain_interruptible(self):
        tx = simulation()
        tx["humanlock"]["interruptible"] = False
        result = evaluate_agent_simulation(tx)
        self.assertEqual(result["simulation_route"], "HOLD")
        self.assertFalse(result["gates"]["humanlock_valid"])

    def test_entity_resolution_batch_matches_expected_decisions(self):
        for case in entity_batch()["cases"]:
            with self.subTest(case=case["case_id"]):
                receipt = resolve_entity_pair(case["left"], case["right"])
                self.assertEqual(receipt["decision"], case["expected_decision"])
                self.assertFalse(receipt["auto_merge"])
                self.assertEqual(receipt["causal_attribution"], "NOT.ESTABLISHED")

    def test_same_name_without_source_id_does_not_merge(self):
        case = entity_batch()["cases"][1]
        receipt = resolve_entity_pair(case["left"], case["right"])
        self.assertEqual(receipt["decision"], "U.21.CANDIDATE.MATCH")
        self.assertTrue(receipt["human_review_required"])
        self.assertFalse(receipt["auto_merge"])

    def test_shared_company_does_not_imply_same_identity(self):
        case = entity_batch()["cases"][3]
        receipt = resolve_entity_pair(case["left"], case["right"])
        self.assertEqual(receipt["decision"], "NO.IDENTITY.INFERENCE")

    def test_chronology_conflict_rejects_same_entity(self):
        case = entity_batch()["cases"][4]
        receipt = resolve_entity_pair(case["left"], case["right"])
        self.assertEqual(receipt["decision"], "F.6.SAME.ENTITY")


if __name__ == "__main__":
    unittest.main()
