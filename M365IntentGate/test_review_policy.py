import unittest

from M365IntentGate.review_policy import POLICY_ID, evaluate_review_policy


class ReviewPolicyTests(unittest.TestCase):
    def test_exact_head_local_pass_preserves_external_hold(self):
        result = evaluate_review_policy(
            local_verification_pass=True,
            authenticated_runtime_established=False,
            external_execution_count=0,
            provider_envelope_count=0,
            humanlock_active=True,
        )
        self.assertEqual(result["POLICY.ID"], POLICY_ID)
        self.assertEqual(result["DECISION"], "PASS.LOCAL.HOLD.EXTERNAL")
        self.assertEqual(result["REVIEW.ACTION"], "COMMENT.ONLY")
        self.assertEqual(
            result["REVIEW.COMMENT"],
            "exact-head local fixture verification accepted; authenticated runtime remains unestablished",
        )
        self.assertEqual(result["EXTERNAL.EXECUTION.STATE"], "HOLD")
        self.assertFalse(result["APPROVE.ALLOWED"])
        self.assertFalse(result["READY.ALLOWED"])
        self.assertFalse(result["MERGE.ALLOWED"])
        self.assertFalse(result["AUTO.PROMOTION.ALLOWED"])

    def test_external_execution_without_authenticated_runtime_is_c9(self):
        result = evaluate_review_policy(
            local_verification_pass=True,
            authenticated_runtime_established=False,
            external_execution_count=1,
            provider_envelope_count=0,
            humanlock_active=True,
        )
        self.assertEqual(result["DECISION"], "REJECT")
        self.assertEqual(result["CONSEQUENCE"], "C.9.BOUNDARY.BREACH")
        self.assertEqual(result["EXTERNAL.EXECUTION.STATE"], "REJECT")
        self.assertEqual(result["REVIEW.ACTION"], "REQUEST.CHANGES")

    def test_provider_envelope_without_authenticated_runtime_is_c9(self):
        result = evaluate_review_policy(
            local_verification_pass=True,
            authenticated_runtime_established=False,
            external_execution_count=0,
            provider_envelope_count=1,
            humanlock_active=True,
        )
        self.assertEqual(result["DECISION"], "REJECT")
        self.assertEqual(result["CONSEQUENCE"], "C.9.BOUNDARY.BREACH")

    def test_authenticated_runtime_never_auto_promotes(self):
        result = evaluate_review_policy(
            local_verification_pass=True,
            authenticated_runtime_established=True,
            external_execution_count=0,
            provider_envelope_count=0,
            humanlock_active=True,
        )
        self.assertEqual(result["DECISION"], "HOLD.HUMAN.REVIEW")
        self.assertEqual(result["REVIEW.ACTION"], "HUMAN.REVIEW.REQUIRED")
        self.assertFalse(result["APPROVE.ALLOWED"])
        self.assertFalse(result["READY.ALLOWED"])
        self.assertFalse(result["MERGE.ALLOWED"])
        self.assertFalse(result["AUTO.PROMOTION.ALLOWED"])

    def test_negative_counts_fail_closed(self):
        with self.assertRaises(ValueError):
            evaluate_review_policy(
                local_verification_pass=True,
                authenticated_runtime_established=False,
                external_execution_count=-1,
                provider_envelope_count=0,
                humanlock_active=True,
            )


if __name__ == "__main__":
    unittest.main()
