#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from revenue_auditance_runtime import RuntimeValidationError, validate_event

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "RavenCloudTaskbar" / "fr0333_cashapp_observation_schema.json"

REQUIRED_FIELDS = {
    "provider", "mode", "source_event_id", "source_record_type", "source_timestamp",
    "source_amount", "source_status", "source_parties", "source_fee", "source_reference",
    "source_document_hash", "source_evidence_class",
}
FORBIDDEN_PROMOTION_FIELDS = {
    "settlement_status", "reconciliation_status", "fdic_status", "bond_status",
    "insurance_status", "revenue", "revenue_true", "value_realized", "reserve_amount",
    "refund_exposure", "chargeback_exposure", "authority_to_move_funds", "money_movement",
}
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class ObservationValidationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _money(value: Any, field: str) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ObservationValidationError("INVALID_MONEY", f"{field} is not a decimal")
    if amount < 0:
        raise ObservationValidationError("NEGATIVE_MONEY", f"{field} must be non-negative")
    if amount.as_tuple().exponent < -2:
        raise ObservationValidationError("MONEY_PRECISION", f"{field} may have at most two decimals")
    return amount


def _money_text(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):.2f}"


def _timestamp(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise ObservationValidationError("INVALID_TIMESTAMP", "source_timestamp must be a non-empty ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ObservationValidationError("INVALID_TIMESTAMP", "source_timestamp is not valid ISO-8601")
    if parsed.tzinfo is None:
        raise ObservationValidationError("TIMESTAMP_REQUIRES_OFFSET", "source_timestamp must include a timezone offset")
    return value


def observation_receipt_hash(receipt: dict[str, Any]) -> str:
    canonical = deepcopy(receipt)
    canonical["observation_receipt_hash"] = None
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_provider_record(record: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ObservationValidationError("INVALID_RECORD", "observation input must be an object")

    missing = sorted(REQUIRED_FIELDS - set(record))
    if missing:
        raise ObservationValidationError("MISSING_FIELDS", ",".join(missing))

    extra = sorted(set(record) - REQUIRED_FIELDS)
    promoted = sorted(set(extra) & FORBIDDEN_PROMOTION_FIELDS)
    if promoted:
        raise ObservationValidationError(
            "UNAUTHORIZED_PROMOTION_FIELD",
            ",".join(promoted),
        )
    if extra:
        raise ObservationValidationError("EXTRA_FIELDS", ",".join(extra))

    if record["provider"] != "CASH_APP":
        raise ObservationValidationError("PROVIDER_MISMATCH", "provider must be CASH_APP")
    if record["mode"] != "READ_ONLY":
        raise ObservationValidationError("MODE_MUST_BE_READ_ONLY", "mode must remain READ_ONLY")

    for field in ("source_event_id", "source_record_type", "source_status", "source_reference"):
        if not isinstance(record[field], str) or not record[field].strip():
            raise ObservationValidationError("EMPTY_REQUIRED_TEXT", field)

    source_timestamp = _timestamp(record["source_timestamp"])
    source_amount = _money(record["source_amount"], "source_amount")
    source_fee = _money(record["source_fee"], "source_fee")
    if source_fee > source_amount:
        raise ObservationValidationError("FEE_EXCEEDS_SOURCE_AMOUNT", "source_fee exceeds source_amount")

    parties = record["source_parties"]
    if not isinstance(parties, list) or not parties or not all(isinstance(x, str) and x.strip() for x in parties):
        raise ObservationValidationError("INVALID_PARTIES", "source_parties must contain non-empty strings")

    document_hash = record["source_document_hash"]
    if not isinstance(document_hash, str) or not SHA256_RE.fullmatch(document_hash):
        raise ObservationValidationError("INVALID_DOCUMENT_HASH", "source_document_hash must be a 64-character SHA-256 hex digest")

    evidence_class = record["source_evidence_class"]
    if evidence_class == "SCREENSHOT":
        raise ObservationValidationError(
            "SCREENSHOT_NOT_PROVIDER_VERIFIED",
            "screenshot-only evidence cannot promote to provider-record observation",
        )
    if evidence_class != "PROVIDER_RECORD":
        raise ObservationValidationError(
            "PROVIDER_RECORD_REQUIRED",
            "read-only observed-live normalization requires provider-record evidence",
        )

    normalized = deepcopy(record)
    normalized["source_timestamp"] = source_timestamp
    normalized["source_amount"] = _money_text(source_amount)
    normalized["source_fee"] = _money_text(source_fee)
    normalized["source_document_hash"] = document_hash.lower()
    return normalized


def normalize_cashapp_observation(record: dict[str, Any]) -> dict[str, Any]:
    source = validate_provider_record(record)

    provider_pointer = (
        f"{source['source_reference']}#sha256={source['source_document_hash']}"
    )
    runtime_event = {
        "event_id": f"OBS.CASHAPP.{source['source_event_id']}",
        "event_class": "OBSERVED_LIVE",
        "source_event_id": source["source_event_id"],
        "contract_id": "UNVERIFIED_CONTRACT",
        "contract_version": "UNKNOWN",
        "authority_id": "READ_ONLY_OBSERVATION_NO_MONEY_AUTHORITY",
        "source_rail": "CASH_APP",
        "source_account_class": "CASH_APP_UNCLASSIFIED",
        "amount_gross": source["source_amount"],
        "fee_amount": source["source_fee"],
        "refund_exposure": "UNKNOWN",
        "chargeback_exposure": "UNKNOWN",
        "reserve_amount": "UNKNOWN",
        "amount_net": "UNKNOWN",
        "legal_owner_before": "NOT_VERIFIED",
        "legal_owner_after": "NOT_VERIFIED",
        "custodian": "NOT_VERIFIED",
        "destination": "NOT_VERIFIED",
        "settlement_status": "UNKNOWN",
        "reconciliation_status": "NOT_RECONCILED",
        "bond_status": "NOT_VERIFIED",
        "insurance_status": "NOT_VERIFIED",
        "fdic_status": "NOT_VERIFIED",
        "encumbrance_status": "NOT_VERIFIED",
        "value_realized": "UNKNOWN",
        "requested_at": source["source_timestamp"],
        "observed_at": source["source_timestamp"],
        "settled_at": None,
        "reconciled_at": None,
        "source_evidence": [
            {
                "evidence_id": f"CASHAPP.PROVIDER.{source['source_event_id']}",
                "evidence_class": "PROVIDER_RECORD",
                "pointer": provider_pointer,
            }
        ],
        "receipt_hash": None,
    }

    try:
        runtime_event = validate_event(runtime_event, allow_live=True)
    except RuntimeValidationError as exc:
        raise ObservationValidationError(
            "RUNTIME_NORMALIZATION_REJECTED",
            f"{exc.code}: {exc.message}",
        ) from exc

    receipt = {
        "identifier": "FR0333.REVENUE.AUDITANCE.CASHAPP.OBSERVATION.001.RECEIPT",
        "provider": "CASH_APP",
        "mode": "READ_ONLY",
        "source_record": source,
        "source_status_observed": source["source_status"],
        "normalized_runtime_event": runtime_event,
        "provider_evidence_pointer": provider_pointer,
        "live_money_movement": 0,
        "live_financial_execution": 0,
        "authority_to_move_funds": False,
        "promotion_ceiling": "PROVIDER_RECORD_OBSERVED_NOT_SETTLED_RECONCILED_PROTECTED_INSURED_REVENUE_OR_VALUE",
        "gates": {
            "provider_record_is_settled": False,
            "settled_is_reconciled": False,
            "observed_live_is_authorized_money_movement": False,
            "provider_record_is_fdic_insured": False,
            "provider_record_is_bond_protected": False,
            "provider_record_is_revenue": False,
            "provider_record_proves_value_realized": False,
            "absent_exposure_is_zero_exposure": False,
            "absent_reserve_is_zero_reserve": False,
        },
        "observation_receipt_hash": None,
    }
    receipt["observation_receipt_hash"] = observation_receipt_hash(receipt)
    return receipt


if __name__ == "__main__":
    print("FR0333.REVENUE.AUDITANCE.CASHAPP.OBSERVATION.001")
    print("mode=READ_ONLY")
    print("live_money_movement=0")
    print("authority_to_move_funds=false")
