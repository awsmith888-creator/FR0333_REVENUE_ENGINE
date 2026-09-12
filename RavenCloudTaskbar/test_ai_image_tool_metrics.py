import unittest
from datetime import datetime, timezone

from RavenCloudTaskbar.ai_image_tool_metrics import (
    Capability,
    EvidenceState,
    GOLDEN_CHAIN_ID,
    ToolChange,
    compile_report,
)


class AIImageToolMetricsTests(unittest.TestCase):
    def change(
        self,
        state=EvidenceState.VERIFIED_RELEASE,
        availability_receipt="AVAILABLE.001",
        runtime_receipt=None,
        capability=Capability.OUTPUT_9_16,
        consequence=3,
    ):
        return ToolChange(
            record_id="AIT.0001",
            tool="TEST.TOOL",
            capability=capability,
            observed_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
            evidence_state=state,
            consequence=consequence,
            source_url="https://example.test/release",
            change="Native portrait output added",
            workflow_effect="Removes manual crop step",
            availability_receipt=availability_receipt,
            runtime_receipt=runtime_receipt,
        )

    def test_golden_chain_binding(self):
        self.assertEqual(GOLDEN_CHAIN_ID, "GC.SB.0027")

    def test_verified_release_requires_availability_receipt(self):
        with self.assertRaises(ValueError):
            self.change(availability_receipt=None)

    def test_release_availability_does_not_imply_runtime_verification(self):
        record = self.change()
        self.assertFalse(record.runtime_verified)

    def test_verified_runtime_reliability_requires_runtime_receipt(self):
        with self.assertRaises(ValueError):
            self.change(capability=Capability.RUNTIME_RELIABILITY)
        record = self.change(
            capability=Capability.RUNTIME_RELIABILITY,
            runtime_receipt="RUN.001",
        )
        self.assertTrue(record.runtime_verified)

    def test_evidence_lanes_remain_separate(self):
        preview = ToolChange(
            record_id="AIT.0002",
            tool="TEST.TOOL",
            capability=Capability.IDENTITY_PRESERVATION,
            observed_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
            evidence_state=EvidenceState.PREVIEW,
            consequence=2,
            source_url="https://example.test/preview",
            change="Identity preview shown",
            workflow_effect="Potential future reduction in face drift",
        )
        report = compile_report([self.change(), preview])
        self.assertEqual(len(report["evidence_lanes"]["VERIFIED_RELEASE"]), 1)
        self.assertEqual(len(report["evidence_lanes"]["PREVIEW"]), 1)
        self.assertEqual(report["record_count"], 2)

    def test_metric_is_deterministic_and_not_percentage(self):
        record = self.change()
        self.assertEqual(record.metric, 9)
        report = compile_report([record])
        self.assertEqual(
            report["capability_metrics_by_evidence"]["VERIFIED_RELEASE"]["OUTPUT_9_16"],
            9,
        )

    def test_cross_lane_totals_are_not_emitted(self):
        report = compile_report([self.change()])
        self.assertNotIn("capability_metric_totals", report)
        self.assertTrue(report["gate"]["cross_lane_aggregation_forbidden"])

    def test_non_integer_consequence_rejected(self):
        with self.assertRaises(TypeError):
            self.change(consequence=2.5)
        with self.assertRaises(TypeError):
            self.change(consequence=True)

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            compile_report([self.change(), self.change()])


if __name__ == "__main__":
    unittest.main()
