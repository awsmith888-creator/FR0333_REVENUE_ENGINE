from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from fr0333_human_tool_contribution_evidence_0001 import load_schema, validate_record

ROOT = Path(__file__).resolve().parent
FIXTURES = json.loads(
    (ROOT / "fr0333_human_tool_contribution_evidence_fixtures.json").read_text(encoding="utf-8")
)
SCHEMA = load_schema()


class HumanToolContributionEvidenceTests(unittest.TestCase):
    def test_01_attribution_pass(self) -> None:
        self.assertEqual(validate_record(FIXTURES["C01_PASS"], SCHEMA)["state"], "T.20.PASS")

    def test_02_accessibility_pass(self) -> None:
        self.assertEqual(validate_record(FIXTURES["C02_PASS"], SCHEMA)["state"], "T.20.PASS")

    def test_03_execution_hold_without_runtime_receipt(self) -> None:
        result = validate_record(FIXTURES["C03_HOLD"], SCHEMA)
        self.assertEqual(result["state"], "U.21.HOLD")
        self.assertFalse(result["runtime_established"])

    def test_04_sparse_source_holds_promotion(self) -> None:
        result = validate_record(FIXTURES["C04_HOLD"], SCHEMA)
        self.assertEqual(result["state"], "U.21.HOLD")
        self.assertFalse(result["promotion_allowed"])

    def test_05_vendor_survey_passes_only_as_vendor_data(self) -> None:
        self.assertEqual(validate_record(FIXTURES["C05_PASS"], SCHEMA)["state"], "T.20.PASS")

    def test_06_source_name_auto_promotion_is_rejected(self) -> None:
        case = copy.deepcopy(FIXTURES["C01_PASS"])
        case["source_classification"]["source_name_used_to_auto_promote"] = True
        self.assertEqual(validate_record(case, SCHEMA)["state"], "F.6.REJECT")

    def test_07_configured_is_not_executed(self) -> None:
        case = copy.deepcopy(FIXTURES["C03_HOLD"])
        case["rails"]["C.03.EXECUTION"]["terminal_state"] = "T.20.PASS"
        self.assertEqual(validate_record(case, SCHEMA)["state"], "F.6.REJECT")

    def test_08_unextracted_source_cannot_be_promoted(self) -> None:
        case = copy.deepcopy(FIXTURES["C04_HOLD"])
        rail = case["rails"]["C.04.SOURCE.EXTRACTION"]
        rail["claim_promotion"] = "CLAIM.SPECIFIC"
        rail["terminal_state"] = "F.6.REJECT"
        self.assertEqual(validate_record(case, SCHEMA)["state"], "F.6.REJECT")

    def test_09_vendor_cannot_be_labeled_independent(self) -> None:
        case = copy.deepcopy(FIXTURES["C05_PASS"])
        rail = case["rails"]["C.05.VERIFICATION"]
        rail["verification_class"] = "INDEPENDENT.OUTCOME.STUDY"
        rail["terminal_state"] = "F.6.REJECT"
        self.assertEqual(validate_record(case, SCHEMA)["state"], "F.6.REJECT")

    def test_10_runtime_state_requires_receipt(self) -> None:
        case = copy.deepcopy(FIXTURES["C01_PASS"])
        case["runtime"]["state"] = "ESTABLISHED.BY.AUTHENTICATED.RECEIPT"
        self.assertEqual(validate_record(case, SCHEMA)["state"], "F.6.REJECT")


if __name__ == "__main__":
    unittest.main()
