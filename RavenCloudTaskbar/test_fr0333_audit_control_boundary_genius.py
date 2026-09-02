import unittest

from RavenCloudTaskbar.fr0333_audit_control_boundary_genius import (
    genius_audit_statistics,
    promotion_gate,
)


class AuditControlBoundaryTests(unittest.TestCase):
    def test_promotion_requires_all_four_fields(self) -> None:
        self.assertEqual(
            promotion_gate({
                "SOURCE": True,
                "VERIFICATION": True,
                "EVIDENCE.CLASS": True,
                "RECEIPT": True,
            }),
            "PROMOTE",
        )

    def test_missing_receipt_forces_hold(self) -> None:
        self.assertEqual(
            promotion_gate({
                "SOURCE": True,
                "VERIFICATION": True,
                "EVIDENCE.CLASS": True,
                "RECEIPT": False,
            }),
            "HOLD",
        )

    def test_zero_denominator_is_not_zero_rate(self) -> None:
        results = genius_audit_statistics({})
        self.assertTrue(all(result.state == "NOT_EVALUABLE" for result in results))
        self.assertTrue(all(result.value is None for result in results))

    def test_complete_fixture_scores_expected_rates(self) -> None:
        counts = {
            "unsupported_inference_events": 1,
            "all_audit_findings": 10,
            "externally_corroborated_findings_passing_gate": 4,
            "external_corroboration_submissions": 5,
            "successful_independent_cross_checks": 6,
            "cross_checks_attempted": 8,
            "contradictions_preserved": 3,
            "contradictions_detected": 3,
            "false_promotions": 1,
            "all_promotions": 10,
            "unresolved_holds": 2,
            "all_findings": 10,
            "findings_with_complete_receipts": 7,
            "findings_requiring_receipts": 8,
            "findings_with_complete_source_lineage": 9,
        }
        results = {result.metric_id: result for result in genius_audit_statistics(counts)}
        self.assertEqual(results["GENIUS.AUDIT.01"].value, 0.1)
        self.assertEqual(results["GENIUS.AUDIT.02"].value, 0.8)
        self.assertEqual(results["GENIUS.AUDIT.04"].value, 1.0)
        self.assertEqual(results["GENIUS.AUDIT.08"].value, 0.9)


if __name__ == "__main__":
    unittest.main()
