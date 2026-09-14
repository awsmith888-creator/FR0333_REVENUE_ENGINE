#!/usr/bin/env python3
import copy
import json
import pathlib
import unittest

from fr0333_frontier_model_master_validate import (
    EXPECTED_PROVIDER_IDS,
    MASTER_PATH,
    assert_humanlock_mutation_rejected,
    evaluate_fixture,
    validate_all,
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
        cls.report = validate_all()

    def test_all_eight_mock_fixtures_validate(self):
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
        self.assertEqual(result["register"]["verification_state"], "FAILED_VALIDATION")

    def test_evidenced_dissent_halts_composite(self):
        result = evaluate_fixture(self.fixtures["1.MODEL.OBJECTS.WITH.VALID.SOURCE"], 2)
        self.assertEqual(result["action"], "HALT_COMPOSITE_OUTPUT")
        self.assertEqual(result["truth_state"], "U.21")
        self.assertEqual(result["register"]["objection_set"], ["P04.XAI.GROK"])
        self.assertIn("src/engine/pipeline.c#L142", result["register"]["cited_sources"])

    def test_nonexistent_api_is_failed_claim(self):
        result = evaluate_fixture(self.fixtures["MODEL.CITES.NONEXISTENT.API"], 3)
        self.assertEqual(result["action"], "FLAG_CLAIM_INVALID")
        self.assertEqual(result["truth_state"], "F.6")
        self.assertEqual(result["register"]["evidence_class"], "VERIFIED_REPO_STATE")

    def test_repo_state_disagreement_requires_fetch(self):
        result = evaluate_fixture(self.fixtures["MODELS.DISAGREE.ON.CURRENT.REPO.STATE"], 4)
        self.assertEqual(result["action"], "FETCH_REPOSITORY_EVIDENCE")
        self.assertEqual(result["truth_state"], "U.21")

    def test_timeout_cannot_be_six_provider_consensus(self):
        result = evaluate_fixture(self.fixtures["PROVIDER.TIMEOUT"], 6)
        self.assertEqual(result["action"], "PARTIAL_RESULT_NO_FALSE_CONSENSUS")
        self.assertEqual(result["truth_state"], "U.21")
        self.assertNotIn("P04.XAI.GROK", result["register"]["agreement_set"])

    def test_missing_receipt_and_humanlock_absence_hold(self):
        missing = evaluate_fixture(self.fixtures["MISSING.RECEIPT"], 7)
        human = evaluate_fixture(self.fixtures["HUMANLOCK.ABSENT"], 8)
        self.assertEqual((missing["action"], missing["truth_state"]), ("HOLD_MISSING_RECEIPT", "U.21"))
        self.assertEqual((human["action"], human["truth_state"]), ("BLOCK_PROMOTION", "U.21"))

    def test_humanlock_contract_is_active_immutable(self):
        validate_humanlock_contract(self.master)
        self.assertEqual(self.report["humanlock"], "ACTIVE_IMMUTABLE.REQUIRED")
        self.assertEqual(self.report["humanlock_bypass"], "F.6")
        self.assertEqual(self.report["humanlock_removal_or_downgrade"], "REJECT")
        self.assertTrue(self.report["merge_requires_explicit_human_authorization"])
        self.assertTrue(self.report["canonical_promotion_requires_explicit_human_authorization"])

    def test_humanlock_false_is_rejected(self):
        self.assertTrue(assert_humanlock_mutation_rejected(self.master, lambda m: m.__setitem__("humanlock", False)))

    def test_humanlock_disable_capability_is_rejected(self):
        self.assertTrue(assert_humanlock_mutation_rejected(self.master, lambda m: m["humanlock_contract"].__setitem__("can_be_disabled", True)))

    def test_humanlock_route_removal_is_rejected(self):
        def mutate(m):
            m["diamond_comparator"]["route"] = [x for x in m["diamond_comparator"]["route"] if x != "HUMANLOCK"]
        self.assertTrue(assert_humanlock_mutation_rejected(self.master, mutate))

    def test_humanlock_promotion_bypass_is_rejected(self):
        def mutate(m):
            m["result"]["canonical_promotion"] = "AUTO_PROMOTE"
            m["humanlock_contract"]["canonical_promotion_requires_explicit_human_authorization"] = False
        self.assertTrue(assert_humanlock_mutation_rejected(self.master, mutate))

    def test_humanlock_merge_bypass_is_rejected(self):
        def mutate(m):
            m["humanlock_contract"]["merge_requires_explicit_human_authorization"] = False
        self.assertTrue(assert_humanlock_mutation_rejected(self.master, mutate))

    def test_humanlock_signature_conflation_is_rejected(self):
        def mutate(m):
            m["humanlock_contract"]["cryptographic_signature_equivalence"] = True
        self.assertTrue(assert_humanlock_mutation_rejected(self.master, mutate))

    def test_frozen_architecture_boundaries_remain_explicit(self):
        self.assertFalse(self.report["new_lane"])
        self.assertFalse(self.report["taskbars_json_mutation"])
        self.assertEqual(self.report["cross_provider_live_runtime"], "U.21.NOT.CONNECTED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
