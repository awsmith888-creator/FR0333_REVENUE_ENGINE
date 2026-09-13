#!/usr/bin/env python3
"""FR0333 Find Hub Remembered State Boundary validator.

Zero Lion rule: a saved remembered-item record may validate as a record while the
present physical-state claim remains HOLD unless separate runtime evidence exists.
HumanLock is permanent: authorized actions may pass through it, but never remove it.
"""
from __future__ import annotations

import json
import pathlib
import sys
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT = HERE / "fr0333_find_hub_remembered_state_boundary_0001.json"

REQUIRED_LAWS = {
    "RECORD_OF_WHERE_IT_WAS_SAVED_NE_LIVE_EVIDENCE_OF_WHERE_IT_IS",
    "REMEMBERED_LOCATION_NE_CURRENT_VERIFIED_LOCATION",
    "USER_ASSERTED_STATE_NE_SENSOR_OBSERVATION",
    "SENSOR_ASSISTED_CAPTURE_NE_CONTINUOUS_TRACKING",
    "LAST_KNOWN_RECORDED_STATE_NE_PRESENT_PHYSICAL_STATE",
    "GEMINI_INTERFACE_NE_SYSTEM_OF_RECORD",
    "FIND_HUB_REMEMBERED_ITEM_NE_FIND_HUB_REAL_TIME_LOCATION_SHARE",
    "SAME_PRODUCT_NAME_NE_SAME_EVIDENCE_CLASS",
    "RECORD_EXISTS_NE_CURRENT_PHYSICAL_STATE_VERIFIED",
    "LOCATION_PERMISSION_NE_CONTINUOUS_OBJECT_TRACKING",
    "OBSERVED_NE_CORRELATED_NE_CAUSAL",
    "AUTHORIZED_ACTION_COMPLETE_NE_HUMANLOCK_REMOVED",
}

REQUIRED_SOURCES = {"S1", "S2", "S3"}
REQUIRED_TERMINALS = {"T.20", "U.21", "F.6"}
ALLOWED_SOURCE_CLASSES = {"USER_ASSERTED", "SENSOR_ASSISTED_CAPTURE"}
ALLOWED_PRESENT_STATES = {"VERIFIED", "NOT_VERIFIED", "CONTRADICTED", "UNKNOWN"}


def validate_spec(doc: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, str]] = []

    def check(gate: str, condition: bool, detail: str) -> None:
        checks.append({"gate": gate, "state": "PASS" if condition else "FAIL", "detail": detail})

    check(
        "G1.IDENTIFIER",
        doc.get("identifier") == "FR0333.FIND.HUB.REMEMBERED.STATE.BOUNDARY.0001"
        and doc.get("state") == "ACTIVE_CANONICAL_SPECIFICATION",
        "canonical identifier and active canonical repository state",
    )
    check(
        "G2.SYSTEM.OF.RECORD",
        doc.get("system_of_record") == "FIND_HUB"
        and doc.get("interfaces", {}).get("gemini") == "READ_WRITE_INTERFACE",
        "Find Hub remains system of record; Gemini is an interface",
    )
    remembered = doc.get("remembered_item", {})
    sensor = remembered.get("sensor_assisted_capture", {})
    check(
        "G3.STATE.INPUT.CLASS",
        set(remembered.get("state_input_classes", [])) == ALLOWED_SOURCE_CLASSES,
        "user-asserted and sensor-assisted capture remain distinct",
    )
    check(
        "G4.SENSOR.CAPTURE.BOUNDARY",
        sensor.get("definition") == "DEVICE_LOCATION_CAPTURED_AT_RECORD_CREATE_OR_UPDATE"
        and sensor.get("continuous_tracking") is False,
        "sensor-assisted capture is bounded to create/update and is not continuous tracking",
    )
    runtime = doc.get("runtime_lane_separation", {})
    check(
        "G5.RUNTIME.LANE.SEPARATION",
        runtime.get("remembered_items") == "PERSISTENCE_ORIENTED_RECORD_LANE"
        and runtime.get("live_tracking_equivalence") is False,
        "remembered records remain separate from runtime location lanes",
    )
    sources = doc.get("source_lock", {}).get("sources", [])
    source_ids = {s.get("id") for s in sources}
    check(
        "G6.SOURCE.LOCK",
        REQUIRED_SOURCES.issubset(source_ids)
        and all(str(s.get("url", "")).startswith("https://") for s in sources),
        "official-source registry present with HTTPS references",
    )
    laws = set(doc.get("control_laws", []))
    check(
        "G7.CONTROL.LAWS",
        REQUIRED_LAWS.issubset(laws),
        "all non-equivalence and HumanLock permanence laws are present",
    )
    terminals = set(doc.get("terminal_logic", {}))
    check(
        "G8.TERMINAL.GRAMMAR",
        terminals == REQUIRED_TERMINALS,
        "terminal grammar is exactly T.20/U.21/F.6",
    )
    promotion = doc.get("promotion_gate", {})
    check(
        "G9.NO.LIVE.PROMOTION",
        promotion.get("remembered_record_can_prove_current_location") is False
        and promotion.get("current_location_claim_requires_separate_runtime_evidence") is True
        and promotion.get("gemini_readback_is_not_independent_location_verification") is True
        and promotion.get("humanlock_required_for_canonical_promotion") is True,
        "saved record cannot self-promote into a live-location claim",
    )
    zl = doc.get("zero_lion_logic_gate", {})
    auth = doc.get("authorization_receipt", {})
    check(
        "G10.ZERO.LION.HUMANLOCK",
        zl.get("humanlock") is True
        and zl.get("humanlock_state") == "ACTIVE_IMMUTABLE"
        and zl.get("humanlock_can_be_disabled") is False
        and zl.get("operator_authorization_required_per_controlled_mutation") is True
        and zl.get("authorized_action_complete_does_not_remove_humanlock") is True
        and zl.get("fail_closed") is True
        and zl.get("evidence_gate") == "OBSERVED != CORRELATED != CAUSAL"
        and auth.get("state") == "OPERATOR_AUTHORIZED_CANONICAL_REPOSITORY_PROMOTION"
        and auth.get("scope") == "CANONICAL_REPOSITORY_PROMOTION_ONLY"
        and auth.get("external_runtime_authorized") is False
        and auth.get("humanlock_removed") is False,
        "HumanLock is active/immutable; operator authorization changes action state, never the gate",
    )
    repo_bounds = set(doc.get("repository_boundaries", []))
    check(
        "G11.RUNTIME.REPOSITORY.BOUNDARY",
        "REPOSITORY_WRITE_NE_FIND_HUB_WRITE" in repo_bounds
        and "GITHUB_ACTIONS_PASS_NE_LIVE_LOCATION_VERIFICATION" in repo_bounds
        and "CANONICAL_ACTIVE_NE_EXTERNAL_RUNTIME" in repo_bounds,
        "repository, CI, and canonical activation cannot masquerade as provider runtime",
    )
    schema = doc.get("record_schema", {})
    check(
        "G12.RECORD.SCHEMA",
        set(schema.get("source_class_allowed", [])) == ALLOWED_SOURCE_CLASSES
        and set(schema.get("current_physical_state_allowed", [])) == ALLOWED_PRESENT_STATES,
        "record source and present-state enums are closed",
    )

    passed = sum(c["state"] == "PASS" for c in checks)
    return {
        "identifier": "FR0333.GENIUS.FIND.HUB.REMEMBERED.STATE.BOUNDARY.0001",
        "state": "PASS" if passed == len(checks) else "FAIL",
        "passed": passed,
        "total": len(checks),
        "invariant": "TWELVE.IN -> TWELVE.OUT",
        "checks": checks,
    }


def evaluate_record(record: dict[str, Any]) -> dict[str, str]:
    """Return separate validity and present-state consequences.

    This separation prevents a valid saved record from becoming evidence that the
    physical item is still at the saved location now.
    """
    required = {"ITEM_ID", "RECORDED_VALUE", "SOURCE_CLASS", "RECORDED_AT", "READABLE"}
    if not required.issubset(record):
        return {"record_state": "F.6", "present_state": "F.6", "reason": "RECORD_MISSING_REQUIRED_FIELD"}
    if record.get("SOURCE_CLASS") not in ALLOWED_SOURCE_CLASSES:
        return {"record_state": "F.6", "present_state": "F.6", "reason": "SOURCE_CLASS_INVALID"}
    if not record.get("RECORDED_AT") or record.get("READABLE") is not True:
        return {"record_state": "F.6", "present_state": "F.6", "reason": "RECORDED_STATE_INVALID"}

    present = record.get("CURRENT_PHYSICAL_STATE", "UNKNOWN")
    if present not in ALLOWED_PRESENT_STATES:
        return {"record_state": "F.6", "present_state": "F.6", "reason": "PRESENT_STATE_INVALID"}

    record_state = "T.20"
    if present == "CONTRADICTED":
        return {"record_state": record_state, "present_state": "F.6", "reason": "CURRENT_STATE_CONTRADICTED"}
    if present == "VERIFIED" and record.get("SEPARATE_RUNTIME_EVIDENCE") is True:
        return {"record_state": record_state, "present_state": "T.20", "reason": "SEPARATE_RUNTIME_EVIDENCE_PRESENT"}
    return {"record_state": record_state, "present_state": "U.21", "reason": "CURRENT_PHYSICAL_STATE_NOT_VERIFIED"}


def main() -> int:
    path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    doc = json.loads(path.read_text(encoding="utf-8"))
    report = validate_spec(doc)
    print(json.dumps(report, indent=2))
    return 0 if report["state"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
