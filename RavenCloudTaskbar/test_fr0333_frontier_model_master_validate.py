#!/usr/bin/env python3
import json
import pathlib
import unittest

from fr0333_frontier_model_master_validate import (
    EXPECTED_PROVIDER_IDS,
    MASTER_PATH,
    AUTH_SIMULATION_PATH,
    HUMANLOCK_RECEIPT_PATH,
    assert_humanlock_mutation_rejected,
    build_exact_head_ci_receipt,
    evaluate_fixture,
    validate_all,
    validate_authorization_package,
    validate_exact_head_ci_receipt,
    validate_humanlock_compliance_receipt,
    validate_humanlock_contract,
)

HERE = pathlib.Path(__file__).resolve().parent
FIXTURES = HERE / "fr0333_frontier_model_mock_fixtures_0001.json"


class FrontierModelMasterValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures_doc = json.loads(FIXTURES.read_text(encoding="utf-8"))
        cls.fixtures = {f["scenario"]: f for f in cls.fixtures_doc["fixtures"]}
        cls.master = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
        cls.simulation = json.loads(AUTH_SIMULATION_PATH.read_text(encoding="utf-8"))
        cls.compliance_template = json.loads(HUMANLOCK_RECEIPT_PATH.read_text(encoding="utf-8"))
        cls.report = validate_all()
        cls.auth_report = validate_authorization_package()

    def test_all_eight_model_failure_fixtures_validate(self):
        self.assertEqual(self.report["state"], "T.20")
        self.assertEqual(self.report["fixture_count"], 8)
        self.assertEqual(self.report["schema_valid_register_count"], 8)
        self.assertFalse(self.report["promotion_candidate"])

    def test_provider_set_matches_master_six(self):
        self.assertEqual(self.fixtures_doc["provider_ids"], EXPECTED_PROVIDER_IDS)
        self.assertEqual(len(EXPECTED_PROVIDER_IDS), 6)

    def test_halo_effect_consensus_does_not_override_repo_fact(self):
        result = evaluate_fixture(self.fixtures["ALL.6.AGREE.BUT.WRONG"], 1)
        self.assertEqual(result["action"], "REJECT_ALL")
        self.assertEqual(result["truth_state"], "F.6")
        self.assertEqual(len(result["register"]["agreement_set"]), 6)

    def test_evidenced_dissent_halts_composite(self):
        result = evaluate_fixture(self.fixtures["1.MODEL.OBJECTS.WITH.VALID.SOURCE"], 2)
        self.assertEqual(result["action"], "HALT_COMPOSITE_OUTPUT")
        self.assertEqual(result["truth_state"], "U.21")
        self.assertEqual(result["register"]["objection_set"], ["P04.XAI.GROK"])

    def test_nonexistent_api_is_failed_claim(self):
        result = evaluate_fixture(self.fixtures["MODEL.CITES.NONEXISTENT.API"], 3)
        self.assertEqual(result["action"], "FLAG_CLAIM_INVALID")
        self.assertEqual(result["truth_state"], "F.6")

    def test_repo_state_disagreement_requires_fetch(self):
        result = evaluate_fixture(self.fixtures["MODELS.DISAGREE.ON.CURRENT.REPO.STATE"], 4)
        self.assertEqual(result["action"], "FETCH_REPOSITORY_EVIDENCE")
        self.assertEqual(result["truth_state"], "U.21")

    def test_timeout_cannot_be_six_provider_consensus(self):
        result = evaluate_fixture(self.fixtures["PROVIDER.TIMEOUT"], 6)
        self.assertEqual(result["action"], "PARTIAL_RESULT_NO_FALSE_CONSENSUS")
        self.assertEqual(result["truth_state"], "U.21")
        self.assertNotIn("P04.XAI.GROK", result["register"]["agreement_set"])

    def test_humanlock_contract_is_active_immutable(self):
        validate_humanlock_contract(self.master)
        self.assertEqual(self.report["humanlock"], "ACTIVE_IMMUTABLE.REQUIRED")
        self.assertEqual(self.report["humanlock_bypass"], "F.6")
        self.assertEqual(self.report["humanlock_removal_or_downgrade"], "REJECT")

    def test_humanlock_mutation_guards(self):
        self.assertTrue(assert_humanlock_mutation_rejected(self.master, lambda m: m.__setitem__("humanlock", False)))
        self.assertTrue(assert_humanlock_mutation_rejected(self.master, lambda m: m["humanlock_contract"].__setitem__("can_be_disabled", True)))

        def remove_route(m):
            m["diamond_comparator"]["route"] = [x for x in m["diamond_comparator"]["route"] if x != "HUMANLOCK"]
        self.assertTrue(assert_humanlock_mutation_rejected(self.master, remove_route))

        def auto_promote(m):
            m["result"]["canonical_promotion"] = "AUTO_PROMOTE"
            m["humanlock_contract"]["canonical_promotion_requires_explicit_human_authorization"] = False
        self.assertTrue(assert_humanlock_mutation_rejected(self.master, auto_promote))

    def test_simulation_fixture_does_not_claim_human_authorization(self):
        payload = self.simulation["simulation_authorization_fixture"]
        self.assertTrue(payload["simulation_fixture"])
        self.assertFalse(payload["human_authorization_present"])
        self.assertEqual(payload["authorization_state"], "NOT.AUTHORIZED")
        self.assertEqual(payload["authorized_by_role"], "NONE")
        self.assertFalse(payload["live_execution_eligible"])
        self.assertEqual(payload["authorization_scope"], "SIMULATION_ONLY")

    def test_simulation_fixture_never_satisfies_humanlock(self):
        structural = self.auth_report["structural_fixture"]
        self.assertEqual(structural["decision"], "PASS.SIMULATION.FIXTURE")
        self.assertEqual(structural["truth_state"], "T.20")
        self.assertFalse(structural["humanlock_boundary_reached"])
        self.assertFalse(structural["action_eligible"])
        self.assertFalse(structural["real_human_authorization_present"])
        self.assertFalse(self.auth_report["merge_authorized"])
        self.assertFalse(self.auth_report["canonical_promotion_authorized"])

    def test_forged_human_authorization_in_simulation_is_rejected(self):
        forged = next(x for x in self.auth_report["negative_tests"] if x["test_id"] == "AUTH-SIM-NEG-003-FORGED-HUMAN-AUTH")
        self.assertEqual(forged["decision"], "REJECT.SIMULATION.CANNOT.ASSERT.HUMAN.AUTHORIZATION")
        self.assertEqual(forged["truth_state"], "U.21")

    def test_committed_receipt_is_symbolic_template_not_stale_head_claim(self):
        validate_humanlock_compliance_receipt(self.compliance_template)
        self.assertEqual(self.compliance_template["source_head_binding"], "GITHUB_SHA")
        self.assertNotIn("source_head", self.compliance_template)
        self.assertNotIn("run_id", self.compliance_template["verification_environment"])

    def test_exact_head_ci_receipt_binds_runtime_identity(self):
        head = "a" * 40
        receipt = build_exact_head_ci_receipt(self.compliance_template, head, "123456", "2")
        validated = validate_exact_head_ci_receipt(receipt, head, "123456", "2")
        self.assertEqual(validated["source_head"], head)
        self.assertFalse(validated["merge_authorized"])
        self.assertFalse(validated["canonical_promotion_authorized"])

    def test_stale_head_and_run_receipts_fail_closed(self):
        head = "b" * 40
        receipt = build_exact_head_ci_receipt(self.compliance_template, head, "777", "1")
        with self.assertRaises(AssertionError):
            validate_exact_head_ci_receipt(receipt, "c" * 40, "777", "1")
        with self.assertRaises(AssertionError):
            validate_exact_head_ci_receipt(receipt, head, "778", "1")

    def test_static_template_rejects_literal_source_head(self):
        candidate = dict(self.compliance_template)
        candidate["source_head"] = "d" * 40
        with self.assertRaises(AssertionError):
            validate_humanlock_compliance_receipt(candidate)

    def test_frozen_architecture_boundaries_remain_explicit(self):
        self.assertFalse(self.report["new_lane"])
        self.assertFalse(self.report["taskbars_json_mutation"])
        self.assertFalse(self.report["real_human_authorization_present"])
        self.assertEqual(self.report["cross_provider_live_runtime"], "U.21.NOT.CONNECTED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
