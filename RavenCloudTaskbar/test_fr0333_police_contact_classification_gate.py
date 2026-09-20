#!/usr/bin/env python3
import unittest

from fr0333_police_contact_classification_gate import (
    ClassificationError,
    reviewed_national_gap_status,
    validate_record,
)


def base_record():
    return {
        "record_id": "FR.0333.GENIUS.POLICE.CONTACT.TEST.0001",
        "pointer": "https://example.invalid/source",
        "source_dataset": "BJS_PPCS",
        "observation_class": "PERCEIVED_EXCESSIVE_FORCE",
        "legal_classification": "NOT_ASSESSED",
        "evidence": [
            {
                "evidence_class": "AGENCY_STATISTICAL_REPORT",
                "pointer": "https://example.invalid/report",
            }
        ],
    }


class PoliceContactClassificationGateTests(unittest.TestCase):
    def test_bjs_perception_does_not_promote_legality(self):
        result = validate_record(base_record())
        self.assertEqual(result["gate_status"], "PASS")
        self.assertEqual(result["legal_promotion"], "HOLD")

    def test_fbi_resistance_is_descriptive_only(self):
        row = base_record()
        row["source_dataset"] = "FBI_NUOF"
        row["observation_class"] = "SUBJECT_RESISTANCE_REPORTED"
        result = validate_record(row)
        self.assertEqual(result["legal_promotion"], "HOLD")

    def test_leoka_assault_is_not_legal_conclusion(self):
        row = base_record()
        row["source_dataset"] = "FBI_LEOKA"
        row["observation_class"] = "OFFICER_ASSAULT_REPORTED"
        result = validate_record(row)
        self.assertEqual(result["legal_classification"], "NOT_ASSESSED")

    def test_claimed_self_defense_can_be_recorded_without_adjudication(self):
        row = base_record()
        row["source_dataset"] = "OTHER"
        row["observation_class"] = "CIVILIAN_FORCE_REPORTED"
        row["legal_classification"] = "SELF_DEFENSE_CLAIMED"
        row["evidence"] = [{"evidence_class": "SELF_REPORT", "pointer": "record://claim"}]
        result = validate_record(row)
        self.assertEqual(result["legal_promotion"], "HOLD")

    def test_established_self_defense_requires_adjudicative_evidence(self):
        row = base_record()
        row["legal_classification"] = "SELF_DEFENSE_ESTABLISHED"
        with self.assertRaises(ClassificationError) as ctx:
            validate_record(row)
        self.assertEqual(ctx.exception.code, "LEGAL_CONCLUSION_REQUIRES_ADJUDICATIVE_EVIDENCE")

    def test_established_self_defense_with_court_decision_passes(self):
        row = base_record()
        row["source_dataset"] = "COURT_RECORD"
        row["observation_class"] = "CIVILIAN_FORCE_REPORTED"
        row["legal_classification"] = "SELF_DEFENSE_ESTABLISHED"
        row["evidence"] = [{"evidence_class": "COURT_DECISION", "pointer": "court://decision"}]
        result = validate_record(row)
        self.assertEqual(result["legal_promotion"], "EVIDENCE_BACKED")

    def test_rejected_self_defense_with_official_disposition_passes(self):
        row = base_record()
        row["source_dataset"] = "OFFICIAL_DISPOSITION"
        row["legal_classification"] = "SELF_DEFENSE_REJECTED"
        row["evidence"] = [{"evidence_class": "OFFICIAL_DISPOSITION", "pointer": "case://disposition"}]
        result = validate_record(row)
        self.assertEqual(result["legal_promotion"], "EVIDENCE_BACKED")

    def test_research_pointer_cannot_be_legal_conclusion(self):
        row = base_record()
        row["source_dataset"] = "OTHER"
        row["observation_class"] = "RESEARCH_POINTER_ONLY"
        row["legal_classification"] = "SELF_DEFENSE_CLAIMED"
        with self.assertRaises(ClassificationError) as ctx:
            validate_record(row)
        self.assertEqual(ctx.exception.code, "RESEARCH_POINTER_CANNOT_CARRY_LEGAL_CONCLUSION")

    def test_research_pointer_cannot_impersonate_national_dataset(self):
        row = base_record()
        row["observation_class"] = "RESEARCH_POINTER_ONLY"
        with self.assertRaises(ClassificationError) as ctx:
            validate_record(row)
        self.assertEqual(ctx.exception.code, "RESEARCH_POINTER_SOURCE_MUST_BE_OTHER")

    def test_missing_evidence_fails_closed(self):
        row = base_record()
        row["evidence"] = []
        with self.assertRaises(ClassificationError) as ctx:
            validate_record(row)
        self.assertEqual(ctx.exception.code, "EVIDENCE_REQUIRED")

    def test_gap_status_requires_all_three_national_sources(self):
        self.assertEqual(
            reviewed_national_gap_status({"BJS_PPCS", "FBI_NUOF"}),
            "INSUFFICIENT_REVIEW",
        )
        self.assertEqual(
            reviewed_national_gap_status({"BJS_PPCS", "FBI_NUOF", "FBI_LEOKA"}),
            "NO_DIRECT_LEGALLY_ESTABLISHED_CIVILIAN_SELF_DEFENSE_VARIABLE_IDENTIFIED_IN_REVIEWED_DATASETS",
        )


if __name__ == "__main__":
    unittest.main()
