import copy
import json
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from steward_observability_hardener_0011 import evaluate_observability_hardener

FIXTURE = ROOT / "receipts" / "operator" / "2026-09-15" / "steward_observability.batch.0011.json"


def tx():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class StewardObservabilityHardener0011Tests(unittest.TestCase):
    def test_baseline_passes(self):
        result = evaluate_observability_hardener(tx())
        self.assertEqual(result["route"], "PASS")
        self.assertTrue(all(result["gates"].values()))

    def test_discovery_pointer_alone_cannot_establish_evidence(self):
        data = tx()
        data["source_chain"] = [data["source_chain"][0], {"source_id": "SECONDARY", "class": "INDEPENDENT_SECONDARY"}]
        result = evaluate_observability_hardener(data)
        self.assertEqual(result["route"], "HOLD")
        self.assertIn("PROVENANCE_GAP", result["failure_classes"])

    def test_beta_cannot_be_promoted_to_production(self):
        data = tx()
        data["release_state"] = "BETA"
        data["production_capability_established"] = True
        result = evaluate_observability_hardener(data)
        self.assertEqual(result["route"], "HOLD")
        self.assertIn("RELEASE_STATE_COLLAPSE", result["failure_classes"])

    def test_visualization_is_not_ground_truth(self):
        data = tx()
        data["workflow_graph"]["visualization_is_ground_truth"] = True
        result = evaluate_observability_hardener(data)
        self.assertEqual(result["route"], "HOLD")
        self.assertIn("WORKFLOW_GRAPH_GAP", result["failure_classes"])

    def test_analytics_plane_cannot_mutate_production(self):
        data = tx()
        data["analytics_plane"]["production_mutation_allowed"] = True
        result = evaluate_observability_hardener(data)
        self.assertEqual(result["route"], "HOLD")
        self.assertIn("ANALYTICS_PLANE_BREACH", result["failure_classes"])

    def test_write_requires_human_approval(self):
        data = tx()
        for action in data["agent_actions"]:
            if action["access"] == "WRITE":
                action["human_approval_required"] = False
        result = evaluate_observability_hardener(data)
        self.assertEqual(result["route"], "HOLD")
        self.assertIn("AGENT_ACTION_AUTHORITY_BREACH", result["failure_classes"])

    def test_unobserved_severe_event_holds(self):
        data = tx()
        data["telemetry"]["unobserved_severe_events"] = 1
        result = evaluate_observability_hardener(data)
        self.assertEqual(result["route"], "HOLD")
        self.assertIn("OBSERVABILITY_GAP", result["failure_classes"])

    def test_cross_device_context_requires_explicit_scope(self):
        data = tx()
        data["cross_device_context"].pop("permission_scope")
        result = evaluate_observability_hardener(data)
        self.assertEqual(result["route"], "HOLD")
        self.assertIn("CROSS_DEVICE_CONTEXT_LEAK", result["failure_classes"])

    def test_vendor_metric_cannot_pose_as_independent_benchmark(self):
        data = tx()
        data["vendor_metrics"][0]["state"] = "T.20.INDEPENDENT.BENCHMARK"
        result = evaluate_observability_hardener(data)
        self.assertEqual(result["route"], "HOLD")
        self.assertIn("VENDOR_METRIC_OVERPROMOTION", result["failure_classes"])


if __name__ == "__main__":
    unittest.main()
