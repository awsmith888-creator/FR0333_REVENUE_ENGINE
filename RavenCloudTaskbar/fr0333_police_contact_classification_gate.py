#!/usr/bin/env python3
from __future__ import annotations

from copy import deepcopy
from typing import Any

GATE_ID = "FR.0333.GENIUS.POLICE.CONTACT.GATE.0001"

SOURCE_DATASETS = {
    "BJS_PPCS",
    "FBI_NUOF",
    "FBI_LEOKA",
    "COURT_RECORD",
    "OFFICIAL_DISPOSITION",
    "OTHER",
}

OBSERVATION_CLASSES = {
    "POLICE_CONTACT",
    "POLICE_FORCE_REPORTED",
    "CIVILIAN_FORCE_REPORTED",
    "SUBJECT_RESISTANCE_REPORTED",
    "SUBJECT_THREAT_REPORTED",
    "SUBJECT_WEAPON_INVOLVEMENT_REPORTED",
    "OFFICER_ASSAULT_REPORTED",
    "PERCEIVED_EXCESSIVE_FORCE",
    "RESEARCH_POINTER_ONLY",
    "OTHER",
}

LEGAL_CLASSIFICATIONS = {
    "NOT_ASSESSED",
    "SELF_DEFENSE_CLAIMED",
    "SELF_DEFENSE_ESTABLISHED",
    "SELF_DEFENSE_REJECTED",
    "DISPUTED",
    "UNKNOWN",
}

EVIDENCE_CLASSES = {
    "SELF_REPORT",
    "LAW_ENFORCEMENT_REPORT",
    "AGENCY_STATISTICAL_REPORT",
    "COURT_DECISION",
    "OFFICIAL_DISPOSITION",
    "OTHER",
}

ADJUDICATIVE_EVIDENCE = {"COURT_DECISION", "OFFICIAL_DISPOSITION"}

NOT_EQUAL_GATES = (
    ("OFFICER_ASSAULT_REPORTED", "UNLAWFUL_CIVILIAN_ATTACK"),
    ("SUBJECT_RESISTANCE_REPORTED", "OFFICER_ASSAULT_REPORTED"),
    ("SUBJECT_RESISTANCE_REPORTED", "SELF_DEFENSE_ESTABLISHED"),
    ("PERCEIVED_EXCESSIVE_FORCE", "ILLEGAL_POLICE_FORCE_ESTABLISHED"),
    ("CRIMINAL_CHARGE", "CONVICTION"),
    ("RESEARCH_POINTER_ONLY", "NATIONAL_PREVALENCE_EVIDENCE"),
)


class ClassificationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _require_text(record: dict[str, Any], field: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ClassificationError("MISSING_TEXT", field)
    return value.strip()


def validate_record(record: dict[str, Any]) -> dict[str, Any]:
    """Validate one police-contact statistical/legal classification record.

    Descriptive variables from national statistical systems may be preserved as
    observations, but they may not be promoted into a legal self-defense
    conclusion without adjudicative evidence.
    """
    out = deepcopy(record)
    _require_text(out, "record_id")
    _require_text(out, "pointer")

    source_dataset = out.get("source_dataset")
    observation_class = out.get("observation_class")
    legal_classification = out.get("legal_classification")

    if source_dataset not in SOURCE_DATASETS:
        raise ClassificationError("INVALID_SOURCE_DATASET", str(source_dataset))
    if observation_class not in OBSERVATION_CLASSES:
        raise ClassificationError("INVALID_OBSERVATION_CLASS", str(observation_class))
    if legal_classification not in LEGAL_CLASSIFICATIONS:
        raise ClassificationError("INVALID_LEGAL_CLASSIFICATION", str(legal_classification))

    evidence = out.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise ClassificationError("EVIDENCE_REQUIRED", "evidence must be a non-empty list")

    evidence_classes: set[str] = set()
    for index, row in enumerate(evidence):
        if not isinstance(row, dict):
            raise ClassificationError("INVALID_EVIDENCE", f"evidence[{index}] must be an object")
        evidence_class = row.get("evidence_class")
        if evidence_class not in EVIDENCE_CLASSES:
            raise ClassificationError("INVALID_EVIDENCE_CLASS", str(evidence_class))
        if not isinstance(row.get("pointer"), str) or not row["pointer"].strip():
            raise ClassificationError("INVALID_EVIDENCE_POINTER", f"evidence[{index}]")
        evidence_classes.add(evidence_class)

    if legal_classification in {"SELF_DEFENSE_ESTABLISHED", "SELF_DEFENSE_REJECTED"}:
        if not (evidence_classes & ADJUDICATIVE_EVIDENCE):
            raise ClassificationError(
                "LEGAL_CONCLUSION_REQUIRES_ADJUDICATIVE_EVIDENCE",
                "established/rejected self-defense requires court decision or official disposition evidence",
            )

    if observation_class == "RESEARCH_POINTER_ONLY":
        if legal_classification != "NOT_ASSESSED":
            raise ClassificationError(
                "RESEARCH_POINTER_CANNOT_CARRY_LEGAL_CONCLUSION",
                "research pointers are discovery triggers, not legal determinations",
            )
        if source_dataset != "OTHER":
            raise ClassificationError(
                "RESEARCH_POINTER_SOURCE_MUST_BE_OTHER",
                "research pointer records must not impersonate a national statistical dataset",
            )

    out["gate_id"] = GATE_ID
    out["gate_status"] = "PASS"
    out["legal_promotion"] = (
        "EVIDENCE_BACKED"
        if legal_classification in {"SELF_DEFENSE_ESTABLISHED", "SELF_DEFENSE_REJECTED"}
        else "HOLD"
    )
    out["not_equal_gates"] = [list(pair) for pair in NOT_EQUAL_GATES]
    return out


def reviewed_national_gap_status(reviewed_sources: set[str]) -> str:
    """Return a bounded gap finding for the three reviewed national systems.

    This deliberately does not claim that no U.S. data source anywhere measures
    lawful civilian self-defense. It only reports what was not identified in the
    reviewed BJS PPCS, FBI NUOF, and FBI LEOKA source families.
    """
    required = {"BJS_PPCS", "FBI_NUOF", "FBI_LEOKA"}
    if not required.issubset(reviewed_sources):
        return "INSUFFICIENT_REVIEW"
    return "NO_DIRECT_LEGALLY_ESTABLISHED_CIVILIAN_SELF_DEFENSE_VARIABLE_IDENTIFIED_IN_REVIEWED_DATASETS"
