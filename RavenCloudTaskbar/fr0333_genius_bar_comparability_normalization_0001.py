"""FR0333 Genius Bar comparability normalization rail.

Specification boundary:
SCHEMA.VALID != SEMANTICALLY.VALID != COMPARABLE != CONSUMER.COMPATIBLE

This module issues deterministic hash-bound receipts only. It does not create
cryptographic signatures or claim external runtime deployment.
"""
from __future__ import annotations

import copy
import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Iterable, Mapping, Tuple

PASS = "T.20.PASS"
HOLD = "U.21.HOLD"
REJECT = "F.6.REJECT"
CANONICALIZATION_VERSION = "CANONICAL.JSON.V1"

REQUIRED_TOP_LEVEL = {
    "metric_id", "source_id", "source_timestamp", "source_unit", "source_semantics",
    "source_value", "source_range", "semantic_type", "denominator_id", "reference_frame",
    "current_reference", "precision_profile", "segmentation_architecture",
    "comparability_metadata", "transform_rule", "transform_version",
    "transformation_receipt", "comparability_key", "gate_state",
}

ROUNDING_QUANTA = {
    "HALF_UP_2": Decimal("0.01"),
    "HALF_UP_4": Decimal("0.0001"),
}

TRANSFORM_RULES = {
    "RELATIVE.INCREASE": "RELATIVE.INCREASE.BASE100",
    "OF.BASELINE": "OF.BASELINE.BASE100",
    "COMPOSITION.SHARE": "COMPOSITION.SHARE.FIELD100",
}


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def canonical_decimal(value: Any, rounding_rule: str) -> Decimal | None:
    """Canonical numeric equality; deliberately not raw-byte identity."""
    if value is None:
        return None
    d = _decimal(value)
    if rounding_rule == "NONE":
        return d.normalize()
    if rounding_rule in ROUNDING_QUANTA:
        return d.quantize(ROUNDING_QUANTA[rounding_rule], rounding=ROUND_HALF_UP).normalize()
    raise ValueError("UNDECLARED.TOLERANCE.PROHIBITED")


def canonical_text(value: Any) -> str:
    """Case-insensitive, whitespace-normalized semantic label for V1 hash fields."""
    if value is None:
        return ""
    return " ".join(str(value).strip().casefold().split())


def canonical_json_v1(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def validate_structure(record: Mapping[str, Any]) -> Tuple[str, str]:
    missing = sorted(REQUIRED_TOP_LEVEL - set(record))
    if missing:
        return HOLD, "STRUCTURAL.SCHEMA.MISSING:" + ",".join(missing)
    if not isinstance(record.get("precision_profile"), Mapping):
        return HOLD, "STRUCTURAL.SCHEMA.PRECISION_PROFILE.REQUIRED"
    precision_required = {"source_qualifier", "precision_state", "uncertainty_lower", "uncertainty_upper", "rounding_rule"}
    missing_precision = sorted(precision_required - set(record["precision_profile"]))
    if missing_precision:
        return HOLD, "STRUCTURAL.SCHEMA.PRECISION_PROFILE.MISSING:" + ",".join(missing_precision)
    if not isinstance(record.get("segmentation_architecture"), Mapping):
        return HOLD, "STRUCTURAL.SCHEMA.SEGMENTATION_ARCHITECTURE.REQUIRED"
    if not isinstance(record.get("comparability_metadata"), Mapping):
        return HOLD, "STRUCTURAL.SCHEMA.COMPARABILITY_METADATA.REQUIRED"
    return PASS, "STRUCTURAL.SCHEMA.VALID"


def _expected_current(record: Mapping[str, Any]) -> Dict[str, Any]:
    semantic = record["semantic_type"]
    qualifier = record["precision_profile"]["source_qualifier"]
    if qualifier == "RANGE":
        source_range = record["source_range"]
        if not isinstance(source_range, Mapping):
            raise ValueError("RANGE.SOURCE_RANGE.REQUIRED")
        lower = _decimal(source_range["lower"])
        upper = _decimal(source_range["upper"])
        if lower > upper:
            raise ValueError("RANGE.BOUNDS.INVALID")
        if semantic == "RELATIVE.INCREASE":
            lower += Decimal("100")
            upper += Decimal("100")
        return {"value": None, "lower_bound": lower, "upper_bound": upper}

    source = _decimal(record["source_value"])
    if semantic == "RELATIVE.INCREASE":
        current = Decimal("100") + source
    elif semantic in {"OF.BASELINE", "COMPOSITION.SHARE"}:
        current = source
    else:
        raise ValueError("SEMANTIC.TYPE.UNKNOWN")
    return {"value": current, "lower_bound": None, "upper_bound": None}


def _compare_decimal(a: Any, b: Any, rounding_rule: str) -> bool:
    return canonical_decimal(a, rounding_rule) == canonical_decimal(b, rounding_rule)


def validate_invariants(record: Mapping[str, Any]) -> Tuple[str, str]:
    structural_state, structural_reason = validate_structure(record)
    if structural_state != PASS:
        return structural_state, structural_reason

    source_unit = str(record.get("source_unit", ""))
    if "%" in source_unit:
        return REJECT, "I.01:PERCENT.SYMBOL.PROHIBITED"
    if not record.get("denominator_id"):
        return HOLD, "I.04:DENOMINATOR.REQUIRED"

    semantic = record["semantic_type"]
    source_operator = record["source_semantics"].get("operator")
    if source_operator != semantic:
        return REJECT, "I.07:SEMANTIC.CONTRADICTION"

    frame = record["reference_frame"]
    if semantic == "COMPOSITION.SHARE":
        if frame.get("field_base") != 100 or frame.get("base_reference") is not None:
            return REJECT, "I.02:FIELD.BASE.MUST_EQUAL.100"
    else:
        if frame.get("base_reference") != 100 or frame.get("field_base") is not None:
            return REJECT, "I.02:REFERENCE.BASE.MUST_EQUAL.100"

    if record.get("transform_rule") != TRANSFORM_RULES[semantic]:
        return REJECT, "TRANSFORM.RULE.SEMANTIC.MISMATCH"

    qualifier = record["precision_profile"]["source_qualifier"]
    precision_state = record["precision_profile"]["precision_state"]
    if qualifier == "EXACT" and precision_state != "EXACT":
        return REJECT, "PRECISION.STATE.CONTRADICTION"
    if qualifier in {"APPROX", "RANGE", "LOWER.BOUND", "UPPER.BOUND"} and precision_state != "APPROX":
        return REJECT, "PRECISION.STATE.CONTRADICTION"

    rounding_rule = record["precision_profile"]["rounding_rule"]
    if rounding_rule not in {"NONE", "HALF_UP_2", "HALF_UP_4"}:
        return REJECT, "UNDECLARED.TOLERANCE.PROHIBITED"

    try:
        expected = _expected_current(record)
    except (ValueError, TypeError, KeyError) as exc:
        return REJECT, str(exc)

    current = record["current_reference"]
    if qualifier == "RANGE":
        if record.get("source_value") is not None:
            return REJECT, "RANGE.SOURCE_VALUE.MUST.BE.NULL"
        if current.get("value") is not None:
            return REJECT, "RANGE.CURRENT.VALUE.MUST.BE.NULL"
        if not _compare_decimal(current.get("lower_bound"), expected["lower_bound"], rounding_rule):
            return REJECT, "RANGE.LOWER.TRANSFORM.MISMATCH"
        if not _compare_decimal(current.get("upper_bound"), expected["upper_bound"], rounding_rule):
            return REJECT, "RANGE.UPPER.TRANSFORM.MISMATCH"
    else:
        if record.get("source_range") is not None:
            return REJECT, "POINT.SOURCE_RANGE.MUST.BE.NULL"
        if not _compare_decimal(current.get("value"), expected["value"], rounding_rule):
            return REJECT, "CURRENT.REFERENCE.TRANSFORM.MISMATCH"

    receipt = record.get("transformation_receipt")
    if receipt is None:
        return HOLD, "I.06:TRANSFORMATION.RECEIPT.REQUIRED"
    receipt_checks = {
        "semantic_type": semantic,
        "source_qualifier": qualifier,
        "transform_rule": record["transform_rule"],
        "transform_version": record["transform_version"],
        "canonicalization_version": CANONICALIZATION_VERSION,
    }
    for key, expected_value in receipt_checks.items():
        if receipt.get(key) != expected_value:
            return REJECT, f"TRANSFORMATION.RECEIPT.MISMATCH:{key}"

    return inverse_transform_assertion(record)


def inverse_transform_assertion(record: Mapping[str, Any]) -> Tuple[str, str]:
    receipt = record.get("transformation_receipt")
    if receipt is None:
        return HOLD, "I.06:TRANSFORMATION.RECEIPT.REQUIRED"

    semantic = record["semantic_type"]
    qualifier = record["precision_profile"]["source_qualifier"]
    rounding_rule = record["precision_profile"]["rounding_rule"]
    current = record["current_reference"]

    try:
        if qualifier == "RANGE":
            lower = _decimal(current["lower_bound"])
            upper = _decimal(current["upper_bound"])
            if semantic == "RELATIVE.INCREASE":
                lower -= Decimal("100")
                upper -= Decimal("100")
            source_range = record["source_range"]
            if not _compare_decimal(lower, source_range["lower"], rounding_rule):
                return REJECT, "IRREVERSIBLE.TRANSFORMATION:LOWER"
            if not _compare_decimal(upper, source_range["upper"], rounding_rule):
                return REJECT, "IRREVERSIBLE.TRANSFORMATION:UPPER"
            if receipt.get("source_range_snapshot") != source_range:
                return REJECT, "TRANSFORMATION.RECEIPT.RANGE.SNAPSHOT.MISMATCH"
        else:
            reconstructed = _decimal(current["value"])
            if semantic == "RELATIVE.INCREASE":
                reconstructed -= Decimal("100")
            if not _compare_decimal(reconstructed, record["source_value"], rounding_rule):
                return REJECT, "IRREVERSIBLE.TRANSFORMATION:VALUE"
            if not _compare_decimal(receipt.get("source_value_snapshot"), record["source_value"], rounding_rule):
                return REJECT, "TRANSFORMATION.RECEIPT.VALUE.SNAPSHOT.MISMATCH"
    except (ValueError, TypeError, KeyError) as exc:
        return REJECT, f"IRREVERSIBLE.TRANSFORMATION:{exc}"

    return PASS, "INVARIANTS.AND.REVERSIBILITY.VALIDATED"


def comparability_key_input(record: Mapping[str, Any]) -> Dict[str, str]:
    meta = record["comparability_metadata"]
    seg = record["segmentation_architecture"]
    precision = record["precision_profile"]
    return {
        "serialization_version": CANONICALIZATION_VERSION,
        "construct_id": canonical_text(meta["construct_id"]),
        "semantic_type": record["semantic_type"],
        "denominator_profile_id": canonical_text(record["denominator_id"]),
        "population_id": canonical_text(meta["population_id"]),
        "time_basis_id": canonical_text(meta["time_basis_id"]),
        "method_compatibility_class": canonical_text(meta["method_compatibility_class"]),
        "segment_schema_id": canonical_text(seg.get("segment_schema_id")),
        "precision_class": precision["precision_state"],
        "transform_version": record["transform_version"],
    }


def generate_comparability_key(record: Mapping[str, Any]) -> str:
    serialized = canonical_json_v1(comparability_key_input(record))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def validate_comparability_key(record: Mapping[str, Any]) -> Tuple[str, str]:
    stored = record.get("comparability_key")
    if not stored:
        return HOLD, "COMPARABILITY.KEY.MISSING"
    calculated = generate_comparability_key(record)
    if stored != calculated:
        return REJECT, "COMPARABILITY.KEY.MISMATCH"
    return PASS, "COMPARABILITY.KEY.VALID"


def evaluate_record(record: Mapping[str, Any]) -> Tuple[str, str]:
    state, reason = validate_invariants(record)
    if state != PASS:
        return state, reason
    return validate_comparability_key(record)


def compare_records(left: Mapping[str, Any], right: Mapping[str, Any]) -> Tuple[str, str]:
    left_state, left_reason = evaluate_record(left)
    if left_state != PASS:
        return left_state, "LEFT:" + left_reason
    right_state, right_reason = evaluate_record(right)
    if right_state != PASS:
        return right_state, "RIGHT:" + right_reason
    if left["comparability_key"] != right["comparability_key"]:
        return HOLD, "COMPARABILITY.KEY.DIFFERENCE"
    return PASS, "COMPARABLE"


def consumer_capability_gate(record: Mapping[str, Any], policy: Mapping[str, Any]) -> Tuple[str, str]:
    state, reason = evaluate_record(record)
    if state != PASS:
        return state, "RECORD:" + reason

    if policy.get("detach_precision_profile"):
        return REJECT, "PRECISION.LAUNDERING.DETECTION"

    precision = record["precision_profile"]["precision_state"]
    requires = policy.get("requires")
    approximation_policy = policy.get("approximation_policy")

    if requires == "EXACT" and precision != "EXACT":
        return HOLD, "PRECISION.INCOMPATIBLE"
    if precision == "APPROX":
        if requires != "APPROX.ALLOWED":
            return HOLD, "PRECISION.INCOMPATIBLE"
        if approximation_policy != "PRESERVE.QUALIFIER":
            return REJECT, "PRECISION.LAUNDERING.DETECTION"
    return PASS, "CONSUMER.COMPATIBLE"


def build_transformation_receipt(record: Mapping[str, Any]) -> Dict[str, Any]:
    frame = record["reference_frame"]
    return {
        "semantic_type": record["semantic_type"],
        "source_qualifier": record["precision_profile"]["source_qualifier"],
        "transform_rule": record["transform_rule"],
        "transform_version": record["transform_version"],
        "base_used": frame.get("base_reference"),
        "field_base_used": frame.get("field_base"),
        "source_value_snapshot": record.get("source_value"),
        "source_range_snapshot": copy.deepcopy(record.get("source_range")),
        "current_reference_snapshot": copy.deepcopy(record["current_reference"]),
        "canonicalization_version": CANONICALIZATION_VERSION,
    }


def finalize_record(record: Mapping[str, Any]) -> Dict[str, Any]:
    finalized = copy.deepcopy(dict(record))
    finalized["transformation_receipt"] = build_transformation_receipt(finalized)
    finalized["comparability_key"] = generate_comparability_key(finalized)
    state, _ = evaluate_record(finalized)
    finalized["gate_state"] = state
    return finalized


def issue_hash_bound_execution_receipt(record: Mapping[str, Any]) -> Dict[str, Any]:
    state, reason = evaluate_record(record)
    payload = {
        "receipt_type": "HASH_BOUND.DETERMINISTIC.EXECUTION.RECEIPT",
        "signature_state": "NOT.CRYPTOGRAPHICALLY.SIGNED",
        "record_metric_id": record.get("metric_id"),
        "gate_state": state,
        "reason": reason,
        "comparability_key": record.get("comparability_key"),
        "canonicalization_version": CANONICALIZATION_VERSION,
    }
    payload["receipt_sha256"] = hashlib.sha256(canonical_json_v1(payload).encode("utf-8")).hexdigest()
    return payload


def reconcile_exclusive_partition(values: Iterable[Any], rounding_rule: str = "NONE") -> Tuple[str, str]:
    total = sum((_decimal(v) for v in values), Decimal("0"))
    if canonical_decimal(total, rounding_rule) == canonical_decimal(100, rounding_rule):
        return PASS, "EXCLUSIVE.PARTITION.RECONCILED"
    return HOLD, "EXCLUSIVE.PARTITION.NOT.RECONCILED"
