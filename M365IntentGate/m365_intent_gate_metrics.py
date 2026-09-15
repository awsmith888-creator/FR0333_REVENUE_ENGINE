from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterable
from uuid import UUID


MATRIX_ID = "FR0333.M365.INTENT.GATE.MATRIX.0001"
MODULE_ID = "FR0333.M365.INTENT.GATE.METRICS.0001"
FIXTURE_ID = "FR0333.M365.INTENT.GATE.METRICS.FIXTURES.0001"
VERSION = "1.0.0"
ALLOWED_ROUTES = {"SHAREPOINT", "POWER_AUTOMATE", "POWER_APPS", "POWER_BI"}


class Confidence(StrEnum):
    EXACT = "EXACT.MATCH"
    STRONG = "STRONG.MATCH"
    AMBIGUOUS = "AMBIGUOUS"
    NO_MATCH = "NO.MATCH"


class IntentClass(StrEnum):
    INTERNAL_CLASSIFICATION = "INTERNAL.CLASSIFICATION"
    ROUTE_CANDIDATE = "ROUTE.CANDIDATE"
    MULTI_ROUTE_CANDIDATE = "MULTI.ROUTE.CANDIDATE"
    CROSS_RAIL_CANDIDATE = "CROSS.RAIL.CANDIDATE"
    EXTERNAL_ACTION_REQUESTED = "EXTERNAL.ACTION.REQUESTED"
    AMBIGUOUS = "AMBIGUOUS"
    NO_MATCH = "NO.MATCH"
    UNAUTHORIZED_EXTERNAL_ROUTE = "UNAUTHORIZED.EXTERNAL.ROUTE"


class Consequence(StrEnum):
    C0 = "C.0.NO.CONSEQUENCE"
    C1 = "C.1.ROUTE.CANDIDATE.CREATED"
    C2 = "C.2.MULTI.ROUTE.CANDIDATE.CREATED"
    C3 = "C.3.CROSS.RAIL.CANDIDATE.CREATED"
    C4 = "C.4.HUMANLOCK.REQUIRED"
    C5 = "C.5.AMBIGUITY.HOLD"
    C6 = "C.6.NO.MATCH.HOLD"
    C7 = "C.7.CONTRADICTION.DETECTED"
    C8 = "C.8.REJECT"
    C9 = "C.9.BOUNDARY.BREACH"


PRIMARY_BY_CLASS = {
    IntentClass.INTERNAL_CLASSIFICATION: Consequence.C0,
    IntentClass.ROUTE_CANDIDATE: Consequence.C1,
    IntentClass.MULTI_ROUTE_CANDIDATE: Consequence.C2,
    IntentClass.CROSS_RAIL_CANDIDATE: Consequence.C3,
    IntentClass.EXTERNAL_ACTION_REQUESTED: Consequence.C4,
    IntentClass.AMBIGUOUS: Consequence.C5,
    IntentClass.NO_MATCH: Consequence.C6,
    IntentClass.UNAUTHORIZED_EXTERNAL_ROUTE: Consequence.C8,
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_fixtures(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("fixture_suite_id") != FIXTURE_ID:
        raise ValueError("fixture_suite_id mismatch")
    fixtures = payload.get("fixtures")
    if not isinstance(fixtures, list):
        raise ValueError("fixtures must be a list")
    return fixtures


def _validate_input(record: dict[str, Any]) -> tuple[IntentClass, Confidence]:
    required = {"fixture_id", "source_intent", "intent_class", "confidence", "candidate_routes", "external_action_requested", "authorized_external_route"}
    if required - record.keys():
        raise ValueError(f"missing input fields: {sorted(required - record.keys())}")
    intent_class = IntentClass(record["intent_class"])
    confidence = Confidence(record["confidence"])
    routes = record["candidate_routes"]
    if not isinstance(routes, list) or len(routes) != len(set(routes)):
        raise ValueError("candidate_routes must be a unique list")
    if set(routes) - ALLOWED_ROUTES:
        raise ValueError("unknown provider route")
    if intent_class is IntentClass.ROUTE_CANDIDATE and len(routes) != 1:
        raise ValueError("ROUTE.CANDIDATE requires exactly one provider route")
    if intent_class is IntentClass.MULTI_ROUTE_CANDIDATE and len(routes) < 2:
        raise ValueError("MULTI.ROUTE.CANDIDATE requires at least two provider routes")
    if intent_class is IntentClass.CROSS_RAIL_CANDIDATE and not record.get("cross_rail"):
        raise ValueError("CROSS.RAIL.CANDIDATE requires cross_rail")
    if intent_class in {IntentClass.EXTERNAL_ACTION_REQUESTED, IntentClass.UNAUTHORIZED_EXTERNAL_ROUTE} and not record["external_action_requested"]:
        raise ValueError("external intent classes require external_action_requested")
    if intent_class is IntentClass.UNAUTHORIZED_EXTERNAL_ROUTE and record["authorized_external_route"]:
        raise ValueError("unauthorized route cannot be marked authorized")
    if intent_class is IntentClass.AMBIGUOUS and confidence is not Confidence.AMBIGUOUS:
        raise ValueError("AMBIGUOUS intent requires AMBIGUOUS confidence")
    if intent_class is IntentClass.NO_MATCH and confidence is not Confidence.NO_MATCH:
        raise ValueError("NO.MATCH intent requires NO.MATCH confidence")
    return intent_class, confidence


def classify(record: dict[str, Any]) -> dict[str, Any]:
    intent_class, confidence = _validate_input(record)
    primary = PRIMARY_BY_CLASS[intent_class]
    secondary_flags = [Consequence.C7.value] if intent_class is IntentClass.UNAUTHORIZED_EXTERNAL_ROUTE else []
    return {
        "fixture_id": record["fixture_id"],
        "confidence": confidence.value,
        "primary_consequence": primary.value,
        "secondary_flags": secondary_flags,
        "route_candidates": list(record["candidate_routes"]),
        "cross_rail": record.get("cross_rail"),
        "routing_state": "REJECT" if primary is Consequence.C8 else "HOLD" if primary in {Consequence.C4, Consequence.C5, Consequence.C6} else "CANDIDATE",
        "humanlock_required": primary is Consequence.C4,
        "external_execution_count": 0,
        "provider_request_envelopes": [],
    }


def classify_suite(fixtures: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    records = list(fixtures)
    ids = [item.get("fixture_id") for item in records]
    if len(ids) != len(set(ids)):
        raise ValueError("fixture_id values must be unique")
    return [classify(item) for item in records]


def calculate_metrics(fixtures: list[dict[str, Any]], outputs: list[dict[str, Any]]) -> dict[str, int]:
    input_ids = [item["fixture_id"] for item in fixtures]
    output_ids = [item["fixture_id"] for item in outputs]
    confidence = Counter(item["confidence"] for item in fixtures)
    output_counts = Counter(output_ids)
    return {
        "M.01.INPUT.COUNT": len(fixtures),
        "M.02.EXACT.COUNT": confidence[Confidence.EXACT.value],
        "M.03.STRONG.COUNT": confidence[Confidence.STRONG.value],
        "M.04.AMBIGUOUS.COUNT": confidence[Confidence.AMBIGUOUS.value],
        "M.05.NO.MATCH.COUNT": confidence[Confidence.NO_MATCH.value],
        "M.06.CLASSIFIED.OUTPUT.COUNT": len(outputs),
        "M.07.DROPPED.COUNT": len(set(input_ids) - set(output_ids)),
        "M.08.DUPLICATED.COUNT": sum(max(0, count - 1) for count in output_counts.values()),
        "M.09.CONTRADICTION.COUNT": sum(Consequence.C7.value in item.get("secondary_flags", []) for item in outputs),
        "M.10.BOUNDARY.BREACH.COUNT": 0,
        "M.11.HUMANLOCK.COUNT": sum(bool(item.get("humanlock_required")) for item in outputs),
        "M.12.EXTERNAL.EXECUTION.COUNT": sum(int(item.get("external_execution_count", 0)) for item in outputs),
    }


def invariant_violations(metrics: dict[str, int], fixtures: list[dict[str, Any]], outputs: list[dict[str, Any]]) -> list[str]:
    violations = []
    confidence_sum = sum(metrics[f"M.0{i}.{name}.COUNT"] for i, name in ((2, "EXACT"), (3, "STRONG"), (4, "AMBIGUOUS"), (5, "NO.MATCH")))
    if metrics["M.01.INPUT.COUNT"] != confidence_sum:
        violations.append("M.01.SUM.M.02.M.03.M.04.M.05")
    if metrics["M.06.CLASSIFIED.OUTPUT.COUNT"] != metrics["M.01.INPUT.COUNT"]:
        violations.append("M.06.MATCH.M.01")
    if metrics["M.07.DROPPED.COUNT"] != 0:
        violations.append("M.07.COUNT.0")
    if metrics["M.08.DUPLICATED.COUNT"] != 0:
        violations.append("M.08.COUNT.0")
    if metrics["M.12.EXTERNAL.EXECUTION.COUNT"] != 0:
        violations.append("M.12.COUNT.0")
    if any(item.get("primary_consequence") == Consequence.C9.value for item in outputs):
        violations.append("C.9.NOT.ACCEPTED.OUTPUT")
    if any(item.get("provider_request_envelopes") for item in outputs):
        violations.append("PROVIDER.ENVELOPES.BLOCKED")
    input_ids = Counter(item["fixture_id"] for item in fixtures)
    output_ids = Counter(item["fixture_id"] for item in outputs)
    if input_ids != output_ids:
        violations.append("INPUT.OUTPUT.IDENTITY.PRESERVATION")
    return sorted(set(violations))


def _valid_uuid4(value: str) -> bool:
    try:
        parsed = UUID(value)
    except ValueError:
        return False
    return parsed.version == 4 and str(parsed) == value.lower()


def compile_receipt(fixtures: list[dict[str, Any]], outputs: list[dict[str, Any]], test_run_id: str, observed_at: str) -> dict[str, Any]:
    if not _valid_uuid4(test_run_id):
        raise ValueError("test_run_id must be a canonical UUIDv4")
    datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    metrics = calculate_metrics(fixtures, outputs)
    violations = invariant_violations(metrics, fixtures, outputs)
    if violations:
        raise ValueError(f"{Consequence.C9.value}: {'.'.join(violations)}")
    receipt = {
        "SOURCE_LOCK": MODULE_ID,
        "PARENT_MATRIX": MATRIX_ID,
        "FIXTURE_SUITE": FIXTURE_ID,
        "TEST.RUN.ID": test_run_id,
        "OBSERVED.AT": observed_at,
        "STATE": "LOCAL.EVALUATION.PASS",
        "METRICS": metrics,
        "INPUT.SHA256": sha256(fixtures),
        "OUTPUT.SHA256": sha256(outputs),
        "PROVIDER.ENVELOPE.STATE": "BLOCKED",
        "AUTHENTICATED.RUNTIME": "NOT.ESTABLISHED",
        "HUMANLOCK": "ACTIVE",
        "PROMOTION.STATE": "HUMAN.REVIEW.REQUIRED",
    }
    receipt["RECEIPT.SHA256"] = sha256(receipt)
    return receipt


def evaluate(fixtures: list[dict[str, Any]], outputs: list[dict[str, Any]], test_run_id: str, observed_at: str) -> dict[str, Any]:
    try:
        return {"accepted": True, "consequence": None, "receipt": compile_receipt(fixtures, outputs, test_run_id, observed_at)}
    except ValueError as error:
        return {"accepted": False, "consequence": Consequence.C9.value, "receipt": None, "error": str(error)}
