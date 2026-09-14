from typing import Any, Dict, List

from canonical_hash import canonical_hash


TRUTH_STATES = {"T.20", "U.21", "F.6"}


def _valid_hash_receipt(receipt: Any, payload_fields: List[str]) -> bool:
    if not isinstance(receipt, dict):
        return False
    required = set(payload_fields) | {"payload_hash"}
    if not required.issubset(receipt):
        return False
    if any(receipt.get(field) in (None, "", []) for field in payload_fields):
        return False
    payload = {field: receipt[field] for field in payload_fields}
    return receipt["payload_hash"] == canonical_hash(payload)


def valid_new_fact_receipt(receipt: Any, key: str, asserted_state: str) -> bool:
    fields = ["key", "source_ids", "timestamp", "evidence_class", "asserted_state"]
    if not _valid_hash_receipt(receipt, fields):
        return False
    return receipt["key"] == key and receipt["asserted_state"] == asserted_state


def valid_transition_receipt(receipt: Any, key: str, prior_state: str, new_state: str) -> bool:
    fields = [
        "key",
        "source_ids",
        "timestamp",
        "evidence_class",
        "prior_state",
        "new_state",
    ]
    if not _valid_hash_receipt(receipt, fields):
        return False
    return (
        receipt["key"] == key
        and receipt["prior_state"] == prior_state
        and receipt["new_state"] == new_state
    )


def assert_append_only(baseline: Dict[str, Any], candidate: Dict[str, Any]) -> None:
    failures = []

    for key, old_value in baseline.items():
        if key not in candidate:
            failures.append(f"KEY_DELETED:{key}")
            continue

        new_value = candidate[key]
        if old_value != new_value:
            receipt = candidate.get(f"TRANSITION.RECEIPT.{key}")
            if not valid_transition_receipt(receipt, key, old_value, new_value):
                failures.append(f"UNAUTHORIZED_STATE_CHANGE:{key}")

    for key, value in candidate.items():
        if key.startswith(("SOURCE.RECEIPT.", "TRANSITION.RECEIPT.")):
            continue

        if isinstance(value, str) and (
            value.startswith("T.20.")
            or value.startswith("U.21.")
            or value.startswith("F.6.")
        ):
            failures.append(f"TRUTH_STATE_METADATA_POLLUTION:{key}")

        if key not in baseline and value in {"T.20", "F.6"}:
            receipt = candidate.get(f"SOURCE.RECEIPT.{key}")
            if not valid_new_fact_receipt(receipt, key, value):
                failures.append(f"UNSOURCED_NEW_ASSERTION:{key}")

    if candidate.get("COOCCURRENCE_IS_CAUSATION") is True:
        failures.append("CAUSALITY_LEAK:COOCCURRENCE_IS_CAUSATION")
    if candidate.get("TOPICAL.NEIGHBORHOOD.COOCCURRENCE") == "CAUSAL":
        failures.append("CAUSALITY_LEAK:TOPICAL.NEIGHBORHOOD.COOCCURRENCE")

    if failures:
        raise AssertionError(";".join(failures))
