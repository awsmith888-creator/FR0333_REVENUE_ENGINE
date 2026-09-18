#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

HERE = Path(__file__).resolve().parent
SPEC_PATH = HERE / "fr0333_raven_major_hardening_0005.json"
PREDECESSOR_PATH = HERE / "fr0333_ai_self_improvement_0004.json"

EXPECTED_TOKENS = [
    "RAVEN_SOURCE",
    "RAVEN_ROUTE",
    "RAVEN_WATCH",
    "RAVEN_VERIFY",
    "RAVEN_RECEIPT",
    "LOCK_REFERENCE",
    "LOCK_APPROVAL",
    "LOCK_BOUNDARY",
    "LOCK_APPEND",
    "LOCK_INTEGRITY",
]

TARGET_METRICS = (
    "SOURCE.SELECTION.ERROR",
    "ROUTING.ERROR",
)
ZERO_TOLERANCE_METRICS = (
    "STALE.STATE.ERROR",
    "UNSUPPORTED.PROMOTION",
    "AUTHORIZATION.BYPASS",
    "RECEIPT.COMPLETENESS.ERROR",
    "LINEAGE.ERROR",
)
ALL_METRICS = set(TARGET_METRICS + ZERO_TOLERANCE_METRICS)


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_spec(path: Path = SPEC_PATH) -> Dict[str, Any]:
    return _load_json(path)


def load_predecessor(path: Path = PREDECESSOR_PATH) -> Dict[str, Any]:
    return _load_json(path)


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_spec(spec: Dict[str, Any], predecessor: Dict[str, Any]) -> List[str]:
    errors: List[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    require(spec.get("identifier") == "FR0333.RAVEN.MAJOR.HARDENING.0005", "identifier mismatch")
    require(spec.get("predecessor") == "FR0333.AI.SELF.IMPROVEMENT.0004", "predecessor mismatch")
    require(spec.get("mode") == "BOUNDED.HARDENING", "mode must remain BOUNDED.HARDENING")
    require(spec.get("state") == "CANDIDATE.WORKING.SPEC", "candidate state drift")
    require(spec.get("surface") == "ACTIVE.EXPERIMENTAL", "surface drift")
    require(spec.get("architecture_expansion") is False, "architecture expansion is not authorized")
    require(spec.get("new_lane") is False, "new lane is not authorized")
    require(spec.get("autonomous_promotion") is False, "autonomous promotion is not authorized")

    predecessor_tokens = predecessor.get("token_mapping", [])
    require(len(predecessor_tokens) == 10, "predecessor TEN.IN/TEN.OUT invariant violated")
    require([x.get("index") for x in predecessor_tokens] == list(range(1, 11)), "predecessor numbering drift")
    require([x.get("id") for x in predecessor_tokens] == EXPECTED_TOKENS, "predecessor token identity/order drift")

    auth = spec.get("authorization", {})
    require(auth.get("source") == "HUMAN.OPERATOR.EXPLICIT.CHAT.AUTHORIZATION", "authorization source drift")
    require(auth.get("authority") == "HUMAN.OPERATOR", "authorization authority drift")
    require(set(auth.get("grants", [])) == {
        "RAVEN.HARDEN",
        "ADOBE.HARDEN",
        "ENGINE.HARDEN",
        "VALIDATOR.ADD",
        "REGRESSION.TESTS.ADD",
        "CI.ADD",
    }, "authorization grant set drift")
    require(auth.get("merge_authorized") is False, "merge authorization was not granted")
    require(auth.get("deployment_authorized") is False, "deployment authorization was not granted")
    require(auth.get("canonical_promotion_authorized") is False, "canonical promotion authorization was not granted")
    require(auth.get("capability_promotion_authorized") is False, "capability promotion authorization was not granted")
    require(auth.get("replayable") is False, "human authorization cannot become a reusable bypass token")

    control = spec.get("control_plane", {})
    require(control.get("humanlock_id") == "Z.26.21.HUMANLOCK", "HumanLock id mismatch")
    require(control.get("humanlock_state") == "ACTIVE_IMMUTABLE", "HumanLock must remain ACTIVE_IMMUTABLE")
    require(control.get("human_operator") == "FINAL_CONTROLLER", "human operator must remain final controller")
    require(control.get("external_advisor_authority") == "NONE", "external advisor authority must remain NONE")
    require(control.get("self_authorization_allowed") is False, "self authorization path detected")
    require(control.get("provider_permission_escalation_allowed") is False, "provider permission escalation detected")
    require(control.get("model_weight_change_allowed") is False, "model weight change detected")
    require(control.get("secret_or_credential_access_added") is False, "secret/credential access expansion detected")
    require(control.get("write_actions_require_human_authorization") is True, "write actions must require human authorization")
    require(control.get("fail_closed_on_control_mismatch") is True, "control mismatch must fail closed")

    raven = spec.get("raven_hardening", {})
    require(raven.get("predecessor_token_count") == 10, "Raven predecessor token count drift")
    require(raven.get("predecessor_token_order_must_match") is True, "Raven token order guard missing")
    require(raven.get("eleventh_token_allowed") is False, "eleventh Raven token path detected")
    require(raven.get("source_provenance_required") is True, "source provenance guard missing")
    require(raven.get("stale_state_rejected") is True, "stale state rejection missing")
    require(raven.get("append_only_receipts") is True, "append-only receipt guard missing")
    require(raven.get("lineage_required") is True, "lineage guard missing")
    require(raven.get("observation_not_execution") is True, "observation/execution separation missing")
    require(raven.get("routing_not_authorization") is True, "routing/authorization separation missing")

    gate = spec.get("behavioral_gate", {})
    require(gate.get("same_input_corpus_required") is True, "same-input guard missing")
    require(gate.get("same_source_snapshot_required") is True, "same-source-snapshot guard missing")
    require(gate.get("same_runtime_envelope_required") is True, "same-runtime-envelope guard missing")
    require(gate.get("exact_revisions_required") is True, "exact-revision guard missing")
    require(gate.get("self_generated_logs_sufficient") is False, "self-generated logs cannot establish improvement")
    require(tuple(gate.get("target_metrics", [])) == TARGET_METRICS, "target metric set drift")
    require(tuple(gate.get("zero_tolerance_metrics", [])) == ZERO_TOLERANCE_METRICS, "zero-tolerance metric set drift")
    require(gate.get("target_errors_must_not_increase_individually") is True, "per-metric regression guard missing")
    require(gate.get("target_error_sum_must_reduce") is True, "aggregate target improvement guard missing")
    require(gate.get("promotion_on_pass") is False, "behavioral pass cannot auto-promote")

    adobe = spec.get("adobe_hardening", {})
    require(adobe.get("scope") == "CONNECTED.ADOBE.OBSERVED.RUNTIME", "Adobe scope drift")
    require(adobe.get("queue_length_equals_requested_count") is True, "Adobe queue-length invariant missing")
    require(adobe.get("output_count_equals_requested_count") is True, "Adobe output-count invariant missing")
    require(adobe.get("separate_images_required") is True, "Adobe separate-image invariant missing")
    require(adobe.get("collage_allowed") is False, "Adobe collage path detected")
    require(adobe.get("delivery_ratio") == "9:16", "Adobe delivery ratio drift")
    require(adobe.get("delivery_dimensions") == [1080, 1920], "Adobe delivery dimensions drift")
    require(adobe.get("provider_dispatch_mode") == "SINGLETON_UNTIL_BATCH.RUNTIME.VERIFIED", "Adobe dispatch boundary drift")
    require(adobe.get("failed_slot_only_retry") is True, "Adobe failed-slot-only retry guard missing")
    require(adobe.get("successful_slot_regeneration_allowed") is False, "successful Adobe slots cannot be regenerated implicitly")
    require(adobe.get("slot_identity_preserved") is True, "Adobe slot identity guard missing")
    require(adobe.get("count_invariant") == "N.IN=N.OUT", "Adobe N.IN=N.OUT invariant drift")

    engine = spec.get("engine_hardening", {})
    require(engine.get("truth_states") == ["T.20", "U.21", "F.6"], "engine truth-state set drift")
    require(engine.get("evidence_axiom") == "OBSERVED!=CORRELATED!=CAUSAL", "evidence axiom drift")
    require(engine.get("promotion_default") == "U.21.HOLD", "engine promotion default must remain U.21.HOLD")
    require(engine.get("unsupported_claims_fail_closed") is True, "unsupported claims must fail closed")
    require(engine.get("source_receipt_required") is True, "source receipt guard missing")
    require(engine.get("transition_receipt_required") is True, "transition receipt guard missing")
    require(engine.get("predecessor_overwrite_allowed") is False, "predecessor overwrite path detected")

    promotion = spec.get("promotion", {})
    require(promotion.get("canonical_spec") == "U.21.HOLD", "canonical spec must remain U.21.HOLD")
    require(promotion.get("capability_improvement") == "NOT.ESTABLISHED", "capability improvement cannot be claimed")
    require(promotion.get("merge") is False, "merge must remain false")
    require(promotion.get("deployment") is False, "deployment must remain false")
    require(promotion.get("architecture_change") is False, "architecture change must remain false")

    boundaries = set(spec.get("boundaries", []))
    for boundary in {
        "VALIDATOR.PASS != CAPABILITY.IMPROVEMENT",
        "BEHAVIORAL.RECEIPT != CANONICAL.PROMOTION",
        "MERGE != DEPLOYMENT",
        "OBSERVATION != EXECUTION",
        "ROUTING != AUTHORIZATION",
        "EXTERNAL.ADVISOR != AUTHORITY",
        "HUMANLOCK != CRYPTOGRAPHIC.SIGNATURE",
        "ADOBE.RUNTIME.PASS != UNIVERSAL.ADOBE.CAPACITY",
    }:
        require(boundary in boundaries, f"missing boundary: {boundary}")

    return errors


def _validate_metric_payload(payload: Dict[str, Any], label: str) -> None:
    metrics = payload.get("metrics")
    if not isinstance(metrics, dict) or set(metrics) != ALL_METRICS:
        raise AssertionError(f"{label}.METRIC_SET_DRIFT")
    for metric, value in metrics.items():
        if not isinstance(value, int) or value < 0:
            raise AssertionError(f"{label}.INVALID_METRIC:{metric}")


def evaluate_behavioral_receipt(baseline: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
    for field in ("input_corpus_hash", "source_snapshot_hash", "runtime_envelope_hash"):
        if not baseline.get(field) or baseline.get(field) != candidate.get(field):
            raise AssertionError(f"CONTEXT_MISMATCH:{field}")

    if not baseline.get("revision") or not candidate.get("revision"):
        raise AssertionError("EXACT_REVISIONS_REQUIRED")
    if baseline["revision"] == candidate["revision"]:
        raise AssertionError("BASELINE_AND_CANDIDATE_REVISION_MUST_DIFFER")

    if baseline.get("humanlock") != "ACTIVE_IMMUTABLE" or candidate.get("humanlock") != "ACTIVE_IMMUTABLE":
        raise AssertionError("HUMANLOCK_MISMATCH")
    if baseline.get("authority") != "HUMAN.OPERATOR" or candidate.get("authority") != "HUMAN.OPERATOR":
        raise AssertionError("AUTHORITY_DRIFT")
    if candidate.get("promotion_authorized") is not False:
        raise AssertionError("PROMOTION_BYPASS")
    if candidate.get("architecture_changed") is not False:
        raise AssertionError("ARCHITECTURE_CHANGE_DETECTED")
    if candidate.get("evidence_origin") in (None, "", "SELF_GENERATED"):
        raise AssertionError("INDEPENDENT_EVIDENCE_REQUIRED")

    _validate_metric_payload(baseline, "BASELINE")
    _validate_metric_payload(candidate, "CANDIDATE")

    b = baseline["metrics"]
    c = candidate["metrics"]

    for metric in ZERO_TOLERANCE_METRICS:
        if c[metric] != 0:
            raise AssertionError(f"ZERO_TOLERANCE_FAIL:{metric}")

    for metric in TARGET_METRICS:
        if c[metric] > b[metric]:
            raise AssertionError(f"TARGET_REGRESSION:{metric}")

    baseline_target_total = sum(b[m] for m in TARGET_METRICS)
    candidate_target_total = sum(c[m] for m in TARGET_METRICS)
    if candidate_target_total >= baseline_target_total:
        raise AssertionError("NO_TARGET_ERROR_REDUCTION")

    receipt = {
        "record_id": "FR0333.RAVEN.BEHAVIORAL.RECEIPT.0005",
        "baseline_revision": baseline["revision"],
        "candidate_revision": candidate["revision"],
        "input_corpus_hash": candidate["input_corpus_hash"],
        "source_snapshot_hash": candidate["source_snapshot_hash"],
        "runtime_envelope_hash": candidate["runtime_envelope_hash"],
        "baseline_metrics": b,
        "candidate_metrics": c,
        "baseline_target_total": baseline_target_total,
        "candidate_target_total": candidate_target_total,
        "humanlock": "ACTIVE_IMMUTABLE",
        "authority": "HUMAN.OPERATOR",
        "evidence_origin": candidate["evidence_origin"],
        "status": "BEHAVIORAL.EVIDENCE.PASS",
        "canonical_promotion": "U.21.HOLD",
        "capability_improvement": "NOT.ESTABLISHED",
        "promotion_authorized": False,
    }
    receipt["receipt_hash"] = _canonical_hash(receipt)
    return receipt


def validate_adobe_queue(transaction: Dict[str, Any]) -> Dict[str, Any]:
    requested = transaction.get("requested_count")
    slots = transaction.get("slots")
    if not isinstance(requested, int) or requested < 1:
        raise AssertionError("INVALID_REQUESTED_COUNT")
    if not isinstance(slots, list):
        raise AssertionError("SLOTS_REQUIRED")
    if len(slots) != requested:
        raise AssertionError("QUEUE_LENGTH_MISMATCH")

    slot_ids = [slot.get("slot_id") for slot in slots]
    if len(set(slot_ids)) != requested or any(not slot_id for slot_id in slot_ids):
        raise AssertionError("SLOT_IDENTITY_MISMATCH")

    final_outputs = 0
    failed_slots = set(transaction.get("failed_slots", []))
    retry_slots = set(transaction.get("retry_slots", []))

    if not retry_slots.issubset(failed_slots):
        raise AssertionError("RETRY_NONFAILED_SLOT")
    if set(transaction.get("regenerated_successful_slots", [])):
        raise AssertionError("SUCCESSFUL_SLOT_REGENERATION")

    for slot in slots:
        if slot.get("separate_image") is not True:
            raise AssertionError(f"SEPARATE_IMAGE_REQUIRED:{slot.get('slot_id')}")
        if slot.get("collage") is not False:
            raise AssertionError(f"COLLAGE_REJECTED:{slot.get('slot_id')}")
        if slot.get("ratio") != "9:16":
            raise AssertionError(f"RATIO_DRIFT:{slot.get('slot_id')}")
        if slot.get("width") != 1080 or slot.get("height") != 1920:
            raise AssertionError(f"DIMENSION_DRIFT:{slot.get('slot_id')}")
        if slot.get("final_state") != "PASS":
            raise AssertionError(f"FINAL_SLOT_NOT_PASS:{slot.get('slot_id')}")
        final_outputs += 1

    if final_outputs != requested:
        raise AssertionError("OUTPUT_COUNT_MISMATCH")

    return {
        "record_id": "FR0333.ADOBE.QUEUE.HARDENING.RECEIPT.0005",
        "requested_count": requested,
        "output_count": final_outputs,
        "queue_length": len(slots),
        "slot_ids": slot_ids,
        "retry_slots": sorted(retry_slots),
        "status": "N.IN=N.OUT.PASS",
        "humanlock": "ACTIVE_IMMUTABLE",
        "universal_adobe_capacity_claimed": False,
    }


def main() -> None:
    spec = load_spec()
    predecessor = load_predecessor()
    errors = validate_spec(spec, predecessor)
    if errors:
        print("FR0333.RAVEN.MAJOR.HARDENING.0005 VALIDATION: FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print("FR0333.RAVEN.MAJOR.HARDENING.0005 VALIDATION: PASS")
    print("HUMANLOCK=ACTIVE_IMMUTABLE AUTHORITY=HUMAN.OPERATOR MERGE=FALSE DEPLOYMENT=FALSE")
    print("CAPABILITY.IMPROVEMENT=NOT.ESTABLISHED CANONICAL.SPEC=U.21.HOLD")


if __name__ == "__main__":
    main()
