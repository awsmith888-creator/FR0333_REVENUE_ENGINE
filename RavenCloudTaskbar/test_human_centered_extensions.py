from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TRANSCRIPT = json.loads((ROOT / "fr0333_transcript_confidence_humanlock_0001.json").read_text(encoding="utf-8"))
PUBLIC = json.loads((ROOT / "fr0333_public_benefit_human_centered_0001.json").read_text(encoding="utf-8"))
CHAIN = json.loads((ROOT / "fr0333_golden_chain_gc_sb_0028.json").read_text(encoding="utf-8"))


class HumanCenteredExtensionTests(unittest.TestCase):
    def test_01_transcript_parent_and_humanlock(self) -> None:
        self.assertEqual(TRANSCRIPT["parent"], "FR0333.HUMAN.TOOL.CONTRIBUTION.EVIDENCE.0001")
        self.assertTrue(TRANSCRIPT["humanlock"])

    def test_02_raw_confidence_ne_calibrated_probability(self) -> None:
        self.assertIn(
            "RAW.ASR.CONFIDENCE != CALIBRATED.EXACTNESS.PROBABILITY",
            TRANSCRIPT["core_invariants"],
        )

    def test_03_repeat_agreement_does_not_claim_independence(self) -> None:
        self.assertIn(
            "OBSERVATION.AGREEMENT != STATISTICAL.INDEPENDENCE",
            TRANSCRIPT["core_invariants"],
        )
        self.assertIn("INDEPENDENCE MUST BE MEASURED", TRANSCRIPT["independence_rule"])

    def test_04_unfitted_c12_holds(self) -> None:
        self.assertEqual(TRANSCRIPT["joint_recalibration_model"]["coefficients"], "UNFITTED")
        self.assertEqual(TRANSCRIPT["pre_calibration_fallback"]["C12"], "UNKNOWN")
        self.assertEqual(TRANSCRIPT["pre_calibration_fallback"]["terminal_state"], "U.21.HOLD")
        self.assertTrue(TRANSCRIPT["pre_calibration_fallback"]["humanlock"])

    def test_05_critical_risk_never_confidence_only(self) -> None:
        critical = TRANSCRIPT["risk_thresholds"]["R.4.CRITICAL"]
        self.assertFalse(critical["confidence_only_auto_execute"])
        self.assertTrue(critical["human_authorization_required"])

    def test_06_public_benefit_root_and_design_maxim(self) -> None:
        self.assertEqual(PUBLIC["parent"], "SYSTEM.ROOT")
        self.assertEqual(PUBLIC["design_maxim"], "STRICT.SYSTEM -> COMPASSIONATE.INTERFACE")
        self.assertEqual(PUBLIC["primary_public_benefit_failure_metric"], "FALSE.DENIAL.RATE")

    def test_07_system_uncertainty_cannot_auto_deny(self) -> None:
        hold = PUBLIC["protective_hold"]
        self.assertFalse(hold["automatic_adverse_action_from_system_uncertainty"])
        self.assertEqual(hold["route"], "HUMAN.ADVOCACY")
        self.assertIn("NO.SILENT.DENIAL", PUBLIC["core_invariants"])

    def test_08_access_preservation_respects_authority_boundary(self) -> None:
        hold = PUBLIC["protective_hold"]
        self.assertIn("AUTHORIZED", hold["maintain_existing_access"])
        self.assertEqual(hold["authority_boundary"], "SYSTEM MUST NOT INVENT BENEFIT CONTINUATION AUTHORITY")

    def test_09_golden_chain_position_and_predecessor(self) -> None:
        self.assertEqual(CHAIN["golden_chain_id"], "GC.SB.0028")
        self.assertEqual(CHAIN["predecessor"], "GC.SB.0027")
        self.assertIn("MUST EXIST", CHAIN["predecessor_requirement"])

    def test_10_all_three_modules_registered(self) -> None:
        ids = {CHAIN["primary_module"], *(item["id"] for item in CHAIN["linked_modules"])}
        self.assertEqual(
            ids,
            {
                "FR0333.HUMAN.TOOL.CONTRIBUTION.EVIDENCE.0001",
                "FR0333.TRANSCRIPT.CONFIDENCE.HUMANLOCK.0001",
                "FR0333.PUBLIC.BENEFIT.HUMAN.CENTERED.0001",
            },
        )

    def test_11_visual_artifacts_are_hash_bound_and_non_evidentiary(self) -> None:
        self.assertEqual(len(CHAIN["visual_artifacts"]), 3)
        for artifact in CHAIN["visual_artifacts"]:
            self.assertRegex(artifact["sha256"], re.compile(r"^[0-9a-f]{64}$"))
            self.assertIn("NOT.EVIDENCE", artifact["role"])

    def test_12_chain_registration_does_not_claim_runtime(self) -> None:
        self.assertIn("CI.PASS != EXTERNAL.RUNTIME", CHAIN["hard_boundaries"])
        self.assertIn("GOLDEN.CHAIN.REGISTRATION != PRODUCTION.DEPLOYMENT", CHAIN["hard_boundaries"])
        self.assertEqual(CHAIN["state"], "REGISTERED.DRAFT.UNMERGED")


if __name__ == "__main__":
    unittest.main()
