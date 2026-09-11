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
    def change(self, state=EvidenceState.VERIFIED_RELEASE, receipt="RUN.001"):
        return ToolChange(
            record_id="AIT.0001",
            tool="TEST.TOOL",
            capability=Capability.OUTPUT_9_16,
            observed_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
            evidence_state=state,
            consequence=3,
            source_url="https://example.test/release",
            change="Native portrait output added",
            workflow_effect="Removes manual crop step",
            runtime_receipt=receipt,
        )

    def test_golden_chain_binding(self):
        self.assertEqual(GOLDEN_CHAIN_ID, "GC.SB.0027")

    def test_verified_release_requires_runtime_receipt(self):
        with self.assertRaises(ValueError):
            self.change(receipt=None)

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
        self.assertEqual(report["capability_metric_totals"]["OUTPUT_9_16"], 9)

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            compile_report([self.change(), self.change()])


if __name__ == "__main__":
    unittest.main()
