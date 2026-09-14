from typing import Any, Dict, Iterable, List

from run_regression_guard import TRUTH_STATES, valid_transition_receipt
from validate_source_receipt import validate_source_receipt


def _source_index(source_receipts: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for receipt in source_receipts:
        if not validate_source_receipt(receipt):
            raise AssertionError(f"INVALID_SOURCE_RECEIPT:{receipt.get('source_id', '<missing>')}")
        source_id = receipt["source_id"]
        if source_id in index:
            raise AssertionError(f"DUPLICATE_SOURCE_ID:{source_id}")
        index[source_id] = receipt
    return index


def _claim_has_primary_binding(
    claim: str,
    candidate: Dict[str, Any],
    sources: Dict[str, Dict[str, Any]],
) -> bool:
    source_ids = candidate.get("claim_sources", {}).get(claim, [])
    if not source_ids:
        return False
    for source_id in source_ids:
        receipt = sources.get(source_id)
        if receipt and claim in receipt.get("claims_observed", []):
            return True
    return False


def compare_observations(
    baseline: Dict[str, Any],
    candidate: Dict[str, Any],
    source_receipts: Iterable[Dict[str, Any]],
) -> Dict[str, List[str]]:
    if baseline.get("topic") != candidate.get("topic"):
        raise AssertionError("TOPIC_DRIFT")
    if candidate.get("timestamp", "") < baseline.get("timestamp", ""):
        raise AssertionError("TIMESTAMP_REGRESSION")

    baseline_claims = baseline.get("claims", {})
    candidate_claims = candidate.get("claims", {})
    sources = _source_index(source_receipts)

    removed = sorted(set(baseline_claims) - set(candidate_claims))
    if removed:
        raise AssertionError("CLAIM_DELETION:" + ",".join(removed))

    for claim, state in candidate_claims.items():
        if state not in TRUTH_STATES:
            raise AssertionError(f"INVALID_TRUTH_STATE:{claim}:{state}")

    new_verified: List[str] = []
    promotions: List[str] = []
    demotions: List[str] = []
    state_changes: List[str] = []
    retained_unknowns: List[str] = []
    unchanged_verified: List[str] = []
    unchanged_false: List[str] = []

    for claim, state in sorted(candidate_claims.items()):
        if claim not in baseline_claims:
            if state in {"T.20", "F.6"}:
                if not _claim_has_primary_binding(claim, candidate, sources):
                    raise AssertionError(f"UNSOURCED_NEW_ASSERTION:{claim}")
                if state == "T.20":
                    new_verified.append(claim)
            continue

        prior = baseline_claims[claim]
        if prior == state:
            if state == "T.20":
                unchanged_verified.append(claim)
            elif state == "U.21":
                retained_unknowns.append(claim)
            elif state == "F.6":
                unchanged_false.append(claim)
            continue

        receipt = candidate.get("transition_receipts", {}).get(claim)
        if not valid_transition_receipt(receipt, claim, prior, state):
            raise AssertionError(f"UNAUTHORIZED_STATE_CHANGE:{claim}")

        source_ids = receipt.get("source_ids", [])
        if not source_ids or any(source_id not in sources for source_id in source_ids):
            raise AssertionError(f"UNBOUND_TRANSITION_SOURCE:{claim}")

        state_changes.append(claim)
        if prior == "U.21" and state == "T.20":
            promotions.append(claim)
        elif prior == "T.20" and state == "U.21":
            demotions.append(claim)

    return {
        "new_verified_facts": sorted(new_verified),
        "promotions": sorted(promotions),
        "demotions": sorted(demotions),
        "state_changes": sorted(state_changes),
        "removed_claims": [],
        "retained_unknowns": sorted(retained_unknowns),
        "unchanged_verified_facts": sorted(unchanged_verified),
        "unchanged_false_claims": sorted(unchanged_false),
    }


def build_delta_snapshot(
    baseline: Dict[str, Any],
    candidate: Dict[str, Any],
    source_receipts: Iterable[Dict[str, Any]],
    baseline_payload_hash: str,
    candidate_payload_hash: str,
) -> Dict[str, Any]:
    diff = compare_observations(baseline, candidate, source_receipts)
    added_sources = sorted(set(candidate.get("sources", [])) - set(baseline.get("sources", [])))
    meaningful = bool(diff["new_verified_facts"] or diff["promotions"] or diff["demotions"] or diff["state_changes"])

    return {
        "record_id": "FR0333.RSI.DELTA.MONITOR.0001",
        "baseline_record_id": baseline["record_id"],
        "candidate_record_id": candidate["record_id"],
        "baseline_payload_hash": baseline_payload_hash,
        "candidate_payload_hash": candidate_payload_hash,
        "observed_at": candidate["timestamp"],
        **diff,
        "source_ids_added": added_sources,
        "status": "VERIFIED.DELTA" if meaningful else "NO.VERIFIED.DELTA",
    }
