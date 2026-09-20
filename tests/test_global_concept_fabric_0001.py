import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs" / "FR0333.GLOBAL.CONCEPT.FABRIC.0001.json"

class GlobalConceptFabricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads(SPEC.read_text(encoding="utf-8"))

    def test_identity(self):
        self.assertEqual(self.spec["spec_id"], "FR0333.GLOBAL.CONCEPT.FABRIC.0001")

    def test_shadow_candidate(self):
        self.assertEqual(self.spec["state"], "SHADOW.CANDIDATE")

    def test_golden_chain_remains_canonical(self):
        self.assertEqual(self.spec["authority"]["canonical"], "GOLDEN.CHAIN")

    def test_no_override_authority(self):
        self.assertFalse(self.spec["authority"]["override_authority"])

    def test_no_promotion_authority(self):
        self.assertFalse(self.spec["authority"]["promotion_authority"])

    def test_no_deployment_authority(self):
        self.assertFalse(self.spec["authority"]["deployment_authority"])

    def test_humanlock(self):
        self.assertEqual(self.spec["authority"]["humanlock"], "ACTIVE_IMMUTABLE")

    def test_exact_module_count(self):
        self.assertEqual(len(self.spec["modules"]), 10)
        self.assertEqual(set(self.spec["modules"]), {f"GF.{i:02d}" for i in range(1, 11)})

    def test_module_contract(self):
        required = {"INPUT","OUTPUT","SOURCE","VERSION","METRICS","DEPENDENCIES","FAILURE.MODE","ROLLBACK","RECEIPT","STATE"}
        self.assertEqual(set(self.spec["module_contract"]), required)

    def test_exact_metric_count(self):
        self.assertEqual(len(self.spec["metrics"]), 15)

    def test_hard_gates_not_soft_metrics(self):
        self.assertTrue(set(self.spec["hard_gates"]).isdisjoint(self.spec["soft_metrics"]))

    def test_fail_closed_invariant(self):
        self.assertIn("HARD_GATE.FAILURE => HOLD", self.spec["invariants"])

    def test_simulation_boundary(self):
        self.assertIn("SIMULATED != OBSERVED", self.spec["invariants"])

    def test_promotion_hold(self):
        self.assertTrue(self.spec["promotion"].startswith("HOLD"))

    def test_pipeline_terminates_humanlock(self):
        self.assertEqual(self.spec["pipeline"][-1], "HUMANLOCK")

if __name__ == "__main__":
    unittest.main()
