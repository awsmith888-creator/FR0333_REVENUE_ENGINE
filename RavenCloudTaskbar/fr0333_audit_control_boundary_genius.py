from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


REQUIRED_PROMOTION_FIELDS = (
    "SOURCE",
    "VERIFICATION",
    "EVIDENCE.CLASS",
    "RECEIPT",
)


@dataclass(frozen=True, slots=True)
class MetricResult:
    metric_id: str
    name: str
    numerator: int
    denominator: int
    value: float | None
    state: str


def _rate(metric_id: str, name: str, numerator: int, denominator: int) -> MetricResult:
    if numerator < 0 or denominator < 0:
        raise ValueError("metric counts cannot be negative")
    if denominator == 0:
        return MetricResult(metric_id, name, numerator, denominator, None, "NOT_EVALUABLE")
    if numerator > denominator:
        raise ValueError(f"{name}: numerator cannot exceed denominator")
    return MetricResult(metric_id, name, numerator, denominator, numerator / denominator, "EVALUATED")


def promotion_gate(fields: Mapping[str, bool]) -> str:
    return "PROMOTE" if all(bool(fields.get(key)) for key in REQUIRED_PROMOTION_FIELDS) else "HOLD"


def genius_audit_statistics(counts: Mapping[str, int]) -> tuple[MetricResult, ...]:
    """Compute GENIUS audit-quality statistics without converting UNKNOWN into zero."""
    return (
        _rate("GENIUS.AUDIT.01", "UNSUPPORTED_INFERENCE_EVENTS", counts.get("unsupported_inference_events", 0), counts.get("all_audit_findings", 0)),
        _rate("GENIUS.AUDIT.02", "EXTERNAL_CORROBORATION_ADMISSIBILITY_RATE", counts.get("externally_corroborated_findings_passing_gate", 0), counts.get("external_corroboration_submissions", 0)),
        _rate("GENIUS.AUDIT.03", "INDEPENDENT_CROSS_CHECK_SUCCESS_RATE", counts.get("successful_independent_cross_checks", 0), counts.get("cross_checks_attempted", 0)),
        _rate("GENIUS.AUDIT.04", "CONTRADICTION_CAPTURE_RATE", counts.get("contradictions_preserved", 0), counts.get("contradictions_detected", 0)),
        _rate("GENIUS.AUDIT.05", "FALSE_PROMOTION_RATE", counts.get("false_promotions", 0), counts.get("all_promotions", 0)),
        _rate("GENIUS.AUDIT.06", "UNRESOLVED_HOLD_RATE", counts.get("unresolved_holds", 0), counts.get("all_findings", 0)),
        _rate("GENIUS.AUDIT.07", "RECEIPT_COMPLETENESS_RATE", counts.get("findings_with_complete_receipts", 0), counts.get("findings_requiring_receipts", 0)),
        _rate("GENIUS.AUDIT.08", "SOURCE_LINEAGE_COMPLETENESS_RATE", counts.get("findings_with_complete_source_lineage", 0), counts.get("all_audit_findings", 0)),
    )
