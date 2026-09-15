#!/usr/bin/env python3
import copy
import unittest

from fr0333_ai_self_improvement_0004_validate import load_spec, validate_spec


class TestAISelfImprovement0004(unittest.TestCase):
    def setUp(self):
        self.spec = load_spec()

    def test_canonical_candidate_passes(self):
        self.assertEqual(validate_spec(self.spec), [])

    def test_ten_in_ten_out(self):
        self.assertEqual(len(self.spec["token_mapping"]), 10)
        self.assertEqual(self.spec["systemic_invariants"]["ten_in"], 10)
        self.assertEqual(self.spec["systemic_invariants"]["ten_out"], 10)

    def test_eleventh_token_rejected(self):
        candidate = copy.deepcopy(self.spec)
        candidate["token_mapping"].append({"index": 11, "id": "HIDDEN_TOKEN", "role": "INVALID"})
        self.assertTrue(validate_spec(candidate))

    def test_token_substitution_rejected(self):
        candidate = copy.deepcopy(self.spec)
        candidate["token_mapping"][2]["id"] = "RAVEN_REPLACED"
        self.assertTrue(validate_spec(candidate))

    def test_humanlock_downgrade_rejected(self):
        candidate = copy.deepcopy(self.spec)
        candidate["humanlock"]["state"] = "DISABLED"
        candidate["humanlock"]["can_be_disabled"] = True
        self.assertTrue(validate_spec(candidate))

    def test_autonomous_promotion_rejected(self):
        candidate = copy.deepcopy(self.spec)
        candidate["autonomous_promotion"] = True
        self.assertTrue(validate_spec(candidate))

    def test_capability_gain_cannot_be_self_promoted(self):
        candidate = copy.deepcopy(self.spec)
        candidate["promotion"]["capability_gain_claimed"] = True
        self.assertTrue(validate_spec(candidate))

    def test_pr41_consumed_token_preserved(self):
        candidate = copy.deepcopy(self.spec)
        candidate["pr41_reference"]["authorization_token"] = "REUSABLE"
        self.assertTrue(validate_spec(candidate))

    def test_no_predecessor_overwrite(self):
        candidate = copy.deepcopy(self.spec)
        candidate["systemic_invariants"]["predecessor_overwrite_allowed"] = True
        self.assertTrue(validate_spec(candidate))


if __name__ == "__main__":
    unittest.main()
