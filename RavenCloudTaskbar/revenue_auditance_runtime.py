#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "RavenCloudTaskbar" / "fr0333_revenue_auditance_runtime_schema.json"

REQUIRED_NUMERIC_MONEY_FIELDS = ("amount_gross", "fee_amount")
UNCERTAIN_MONEY_FIELDS = (
    "refund_exposure", "chargeback_exposure", "reserve_amount", "amount_net", "value_realized"
)

ENUMS = {
    "event_class": {"SYNTHETIC", "OBSERVED_LIVE"},
    "settlement_status": {"REQUESTED", "AVAILABLE", "PENDING", "SETTLED", "FAILED", "UNKNOWN"},
    "reconciliation_status": {"NOT_RECONCILED", "RECONCILED", "FAILED", "UNKNOWN"},
    "bond_status": {"NOT_APPLICABLE", "NOT_VERIFIED", "COVERED", "NOT_COVERED", "UNKNOWN"},
    "insurance_status": {"NOT_APPLICABLE", "NOT_VERIFIED", "COVERED", "NOT_COVERED", "UNKNOWN"},
    "fdic_status": {"NOT_APPLICABLE", "NOT_VERIFIED", "ELIGIBLE_PASS_THROUGH", "INSURED", "NOT_INSURED", "UNKNOWN"},
    "encumbrance_status": {"UNENCUMBERED", "ENCUMBERED", "NOT_VERIFIED", "UNKNOWN"},
}

PROTECTION_EVIDENCE = {
    "bond_status": {"CONTRACT", "REGULATOR", "PROVIDER_RECORD"},
    "insurance_status": {"CONTRACT", "PROVIDER_RECORD", "OTHER"},
    "fdic_status": {"BANK_RECORD", "REGULATOR"},
}


class RuntimeValidationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _decimal(event: dict[str, Any], field: str) -> Decimal:
    try:
        value = Decimal(str(event[field]))
    except (KeyError, InvalidOperation):
        raise RuntimeValidationError("INVALID_MONEY", f"{field} is not a valid decimal")
    if value < 0:
        raise RuntimeValidationError("NEGATIVE_MONEY", f"{field} must be non-negative")
    if value.as_tuple().exponent < -2:
        raise RuntimeValidationError("MONEY_PRECISION", f"{field} may have at most two decimal places")
    return value


def _money_or_unknown(event: dict[str, Any], field: str) -> Decimal | None:
    if event.get(field) == "UNKNOWN":
        return None
    return _decimal(event, field)


def _parse_time(value: Any, field: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise RuntimeValidationError("INVALID_TIMESTAMP", f"{field} must be an ISO-8601 string or null")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise RuntimeValidationError("INVALID_TIMESTAMP", f"{field} is not valid ISO-8601")
    if parsed.tzinfo is None:
        raise RuntimeValidationError("TIMESTAMP_REQUIRES_OFFSET", f"{field} must include a timezone offset")
    return parsed


def receipt_hash(event: dict[str, Any]) -> str:
    canonical = deepcopy(event)
    canonical["receipt_hash"] = None
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_event(event: dict[str, Any], *, allow_live: bool = False) -> dict[str, Any]:
    schema = _schema()
    required = schema["required"]
    properties = schema["properties"]

    missing = [field for field in required if field not in event]
    if missing:
        raise RuntimeValidationError("MISSING_FIELDS", ",".join(missing))

    extra = sorted(set(event) - set(properties))
    if extra:
        raise RuntimeValidationError("EXTRA_FIELDS", ",".join(extra))

    for field, allowed in ENUMS.items():
        if event[field] not in allowed:
            raise RuntimeValidationError("INVALID_ENUM", f"{field}={event[field]}")

    if event["event_class"] == "OBSERVED_LIVE" and not allow_live:
        raise RuntimeValidationError(
            "LIVE_EVENT_REQUIRES_OBSERVATION_ADAPTER",
            "simulation runtime cannot promote or ingest live financial events",
        )

    for field in (
        "event_id", "source_event_id", "contract_id", "contract_version", "authority_id",
        "source_rail", "source_account_class", "legal_owner_before", "legal_owner_after",
        "custodian", "destination",
    ):
        if not isinstance(event[field], str) or not event[field].strip():
            raise RuntimeValidationError("EMPTY_REQUIRED_TEXT", field)

    money = {field: _decimal(event, field) for field in REQUIRED_NUMERIC_MONEY_FIELDS}
    uncertain = {field: _money_or_unknown(event, field) for field in UNCERTAIN_MONEY_FIELDS}

    reserve = uncertain["reserve_amount"]
    net = uncertain["amount_net"]
    if reserve is None:
        if net is not None:
            raise RuntimeValidationError(
                "UNKNOWN_RESERVE_REQUIRES_UNKNOWN_NET",
                "amount_net cannot be asserted when reserve_amount is unknown",
            )
    else:
        if net is None:
            raise RuntimeValidationError(
                "KNOWN_RESERVE_REQUIRES_NUMERIC_NET",
                "amount_net must be numeric when reserve_amount is known",
            )
        expected_net = money["amount_gross"] - money["fee_amount"] - reserve
        if expected_net < 0 or net != expected_net:
            raise RuntimeValidationError(
                "NET_ARITHMETIC_MISMATCH",
                f"amount_net={net} expected={expected_net}",
            )

    requested = _parse_time(event["requested_at"], "requested_at")
    observed = _parse_time(event["observed_at"], "observed_at")
    settled = _parse_time(event["settled_at"], "settled_at")
    reconciled = _parse_time(event["reconciled_at"], "reconciled_at")

    ordered = [t for t in (requested, observed, settled, reconciled) if t is not None]
    if ordered != sorted(ordered):
        raise RuntimeValidationError("TIMESTAMP_ORDER", "timestamps must be non-decreasing")

    if event["settlement_status"] == "SETTLED" and settled is None:
        raise RuntimeValidationError("SETTLED_REQUIRES_TIMESTAMP", "settled_at is required")
    if event["settlement_status"] != "SETTLED" and settled is not None:
        raise RuntimeValidationError("SETTLED_TIMESTAMP_STATE_MISMATCH", "settled_at requires SETTLED")

    if event["reconciliation_status"] == "RECONCILED":
        if event["settlement_status"] != "SETTLED":
            raise RuntimeValidationError("RECONCILED_REQUIRES_SETTLED", "reconciliation cannot precede settlement")
        if reconciled is None:
            raise RuntimeValidationError("RECONCILED_REQUIRES_TIMESTAMP", "reconciled_at is required")
    elif reconciled is not None:
        raise RuntimeValidationError("RECONCILED_TIMESTAMP_STATE_MISMATCH", "reconciled_at requires RECONCILED")

    evidence = event["source_evidence"]
    if not isinstance(evidence, list) or not evidence:
        raise RuntimeValidationError("EVIDENCE_REQUIRED", "source_evidence must be non-empty")
    evidence_classes: set[str] = set()
    for row in evidence:
        if not isinstance(row, dict):
            raise RuntimeValidationError("INVALID_EVIDENCE", "evidence row must be an object")
        for key in ("evidence_id", "evidence_class", "pointer"):
            if not row.get(key):
                raise RuntimeValidationError("INVALID_EVIDENCE", f"missing {key}")
        evidence_classes.add(row["evidence_class"])

    protection_assertions = {
        "bond_status": "COVERED",
        "insurance_status": "COVERED",
        "fdic_status": "INSURED",
    }
    for field, positive_state in protection_assertions.items():
        if event[field] == positive_state:
            if not (evidence_classes & PROTECTION_EVIDENCE[field]):
                code = {
                    "bond_status": "BOND_COVERED_REQUIRES_EVIDENCE",
                    "insurance_status": "INSURANCE_COVERED_REQUIRES_EVIDENCE",
                    "fdic_status": "FDIC_INSURED_REQUIRES_BANK_EVIDENCE",
                }[field]
                raise RuntimeValidationError(code, f"{field}={positive_state} lacks qualifying evidence")

    if event["fdic_status"] == "ELIGIBLE_PASS_THROUGH" and not (
        evidence_classes & PROTECTION_EVIDENCE["fdic_status"]
    ):
        raise RuntimeValidationError(
            "FDIC_ELIGIBILITY_REQUIRES_BANK_EVIDENCE",
            "pass-through eligibility requires bank/regulator evidence",
        )

    output = deepcopy(event)
    output["receipt_hash"] = receipt_hash(output)
    return output


def build_receipt(event: dict[str, Any], *, allow_live: bool = False) -> dict[str, Any]:
    validated = validate_event(event, allow_live=allow_live)
    return {
        "receipt_type": "FR0333.REVENUE.AUDITANCE.RECEIPT.001",
        "runtime": "FR0333.REVENUE.AUDITANCE.RUNTIME.001",
        "execution_class": "SIMULATION" if validated["event_class"] == "SYNTHETIC" else "OBSERVED_LIVE",
        "event": validated,
        "gates": {
            "money_in_is_revenue": False,
            "available_is_settled": False,
            "settled_is_reconciled": False,
            "reconciled_is_protected": False,
            "protected_is_insured": False,
            "unknown_protection_is_safe": False,
            "unverified_exposure_is_zero_exposure": False,
            "unverified_money_state_is_zero": False,
        },
    }


if __name__ == "__main__":
    print("FR0333.REVENUE.AUDITANCE.RUNTIME.001")
    print("mode=SIMULATION_ONLY")
    print("live_money_movement=0")
