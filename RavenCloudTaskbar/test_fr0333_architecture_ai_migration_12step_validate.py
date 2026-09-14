#!/usr/bin/env python3
import json
import pathlib
import unittest

from fr0333_architecture_ai_migration_12step_validate import (
    MIGRATION_PATH,
    SIMULATION_PATH,
    evaluate_step12_authorization,
    validate_all,
    validate_migration_spec,
)


class ArchitectureAIMigration12StepTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(MIGRATION_PATH.read_text(encoding="utf-8"))
        cls.simulation = json.loads(SIMULATION_PATH.read_text(encoding="utf-8"))["simulation_authorization_fixture"]
        cls.report = validate_all()

    def test_spec_has_exactly_twelve_ordered_steps(self):
        validate_migration_spec(self.doc)
        self.assertEqual([step["step"] for step in self.doc["steps"]], list(range(1, 13)))

    def test_steps_1_through_10_cannot_imply_human_authorization(self):
        for step in self.doc["steps"][:10]:
            self.assertEqual(step["authorization_effect"], "NONE")
            self.assertFalse(step["may_satisfy_humanlock"])
        self.assertFalse(self.doc["critical_handoff"]["steps_1_through_10_can_imply_step_11"])

    def test_step_10_is_technical_clearance_only(self):
        step10 = self.doc["steps"][9]
        self.assertEqual(step10["gate"], "TECHNICAL.CLEARANCE.ONLY")
        self.assertEqual(step10["authorization_effect"], "NONE")
        self.assertFalse(self.doc["critical_handoff"]["technical_clearance_is_authorization"])

    def test_step_11_is_real_human_exact_action_exact_head_boundary(self):
        step11 = self.doc["steps"][10]
        self.assertEqual(step11["gate"], "HUMANLOCK.BOUNDARY")
        self.assertTrue(step11["requires_real_human_operator"])
        self.assertTrue(step11["requires_exact_action"])
        self.assertTrue(step11["requires_exact_head"])
        self.assertTrue(step11["requires_explicit_authorization"])
        self.assertFalse(step11["simulation_can_satisfy"])

    def test_step_12_rejects_absent_exact_head_humanlock_authorization(self):
        result = evaluate_step12_authorization(
            requested_action="MERGE",
            requested_head="cc3021f65b6b518b29ab220f818c1582fa18c03a",
            authorization_payload=None,
            doc=self.doc,
        )
        self.assertEqual(result["decision"], "REJECT.MISSING.EXACT_HEAD.HUMANLOCK.AUTHORIZATION")
        self.assertEqual(result["truth_state"], "U.21")
        self.assertEqual(result["qualifier"], "HUMANLOCK.HOLD")
        self.assertFalse(result["step_12_action_eligible"])
        self.assertFalse(result["merge_authorized"])
        self.assertFalse(result["canonical_promotion_authorized"])

    def test_simulation_fixture_cannot_unlock_step_12(self):
        result = evaluate_step12_authorization(
            requested_action="MERGE",
            requested_head=self.simulation["target_head"],
            authorization_payload=self.simulation,
            doc=self.doc,
        )
        self.assertEqual(result["decision"], "REJECT.SIMULATION.CANNOT.SATISFY.HUMANLOCK")
        self.assertEqual(result["truth_state"], "U.21")
        self.assertFalse(result["step_12_action_eligible"])

    def test_pr41_position_remains_before_humanlock(self):
        position = self.doc["pr41_position"]
        self.assertEqual(position["technical_work_steps"], "4.THROUGH.10")
        self.assertEqual(position["step_11"], "NOT.CLEARED")
        self.assertEqual(position["step_12"], "BLOCKED")
        self.assertFalse(position["real_human_authorization_present"])
        self.assertFalse(position["merge_authorized"])
        self.assertFalse(position["canonical_promotion_authorized"])

    def test_frozen_boundaries_remain_intact(self):
        boundaries = self.doc["boundaries"]
        self.assertFalse(boundaries["new_lane"])
        self.assertFalse(boundaries["taskbars_json_mutation"])
        self.assertFalse(boundaries["autonomous_promotion"])
        self.assertFalse(boundaries["merge_performed"])
        self.assertFalse(boundaries["promotion_performed"])
        self.assertEqual(self.report["state"], "T.20")


if __name__ == "__main__":
    unittest.main(verbosity=2)
