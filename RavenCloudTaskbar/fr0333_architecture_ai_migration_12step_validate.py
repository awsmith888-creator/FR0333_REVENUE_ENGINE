#!/usr/bin/env python3
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MIGRATION_PATH = HERE / "fr0333_architecture_ai_migration_12step_0001.json"
SIMULATION_PATH = HERE / "fr0333_humanlock_authorization_simulation_fixture_0001.json"

EXPECTED_EXECUTION_CLASSES = [
    "DOCUMENTATION.ONLY",
    "AUTOMATED.TEST",
    "SIMULATION.ONLY",
    "LIVE.READ_ONLY",
    "LIVE.MUTATION.REQUIRES.HUMANLOCK",
]

EXPECTED_STEP_CLASSES = {
    1: "DOCUMENTATION.ONLY",
    2: "DOCUMENTATION.ONLY",
    3: "LIVE.READ_ONLY",
    4: "SIMULATION.ONLY",
    5: "AUTOMATED.TEST",
    6: "LIVE.READ_ONLY",
    7: "AUTOMATED.TEST",
    8: "AUTOMATED.TEST",
    9: "AUTOMATED.TEST",
    10: "AUTOMATED.TEST",
    11: "LIVE.MUTATION.REQUIRES.HUMANLOCK",
    12: "LIVE.MUTATION.REQUIRES.HUMANLOCK",
}


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_migration_spec(doc=None):
    doc = doc or _load(MIGRATION_PATH)

    assert doc["identifier"] == "FR0333.ARCHITECTURE.AI.MIGRATION.12STEP.0001"
    assert doc["spec_state"] == "WORKING.SPEC"
    assert doc["origin"] == "NEWLY.AUTHORED.CONTROL.ARTIFACT.NOT.RECOVERED.HISTORICAL.DOCUMENT"
    assert doc["architecture_state"] == "LOCKED.BASELINE"
    assert doc["humanlock"] == "ACTIVE_IMMUTABLE"
    assert doc["execution_classes"] == EXPECTED_EXECUTION_CLASSES

    steps = doc["steps"]
    assert len(steps) == 12
    assert [step["step"] for step in steps] == list(range(1, 13))

    for step in steps:
        number = step["step"]
        assert step["execution_class"] == EXPECTED_STEP_CLASSES[number]

    for step in steps[:10]:
        assert step["authorization_effect"] == "NONE"
        assert step["may_satisfy_humanlock"] is False
        assert step["execution_class"] != "LIVE.MUTATION.REQUIRES.HUMANLOCK"

    step10 = steps[9]
    assert step10["gate"] == "TECHNICAL.CLEARANCE.ONLY"
    assert step10["authorization_effect"] == "NONE"

    step11 = steps[10]
    assert step11["gate"] == "HUMANLOCK.BOUNDARY"
    assert step11["authorization_effect"] == "HUMAN.DECISION.ONLY"
    assert step11["requires_real_human_operator"] is True
    assert step11["requires_exact_action"] is True
    assert step11["requires_exact_head"] is True
    assert step11["requires_explicit_authorization"] is True
    assert step11["simulation_can_satisfy"] is False

    step12 = steps[11]
    assert step12["authorization_effect"] == "CONSUME.VALID.STEP11.RECEIPT.ONLY"
    assert step12["requires_valid_step11_receipt"] is True
    assert step12["requires_exact_action_match"] is True
    assert step12["requires_exact_head_match"] is True

    handoff = doc["critical_handoff"]
    assert handoff["technical_clearance_step"] == 10
    assert handoff["authorization_step"] == 11
    assert handoff["authorized_action_step"] == 12
    assert handoff["technical_clearance_is_authorization"] is False
    assert handoff["steps_1_through_10_can_imply_step_11"] is False
    assert handoff["step_12_without_valid_step_11_authorization"] == "U.21.HOLD"

    invariants = set(doc["controlling_invariants"])
    required = {
        "SIMULATION.FIXTURE != HUMAN.AUTHORIZATION",
        "CI.SUCCESS != HUMAN.AUTHORIZATION",
        "CRYPTOGRAPHIC.SIGNATURE != HUMANLOCK",
        "HUMANLOCK = EXPLICIT.HUMAN.AUTHORIZATION.BOUNDARY",
        "STEP.10.TECHNICAL.CLEARANCE != STEP.11.AUTHORIZATION",
        "STEP.12.REQUIRES.VALID.STEP.11.EXACT.ACTION.EXACT.HEAD.AUTHORIZATION",
    }
    assert required.issubset(invariants)

    position = doc["pr41_position"]
    assert position["pull_request"] == 41
    assert position["technical_work_steps"] == "4.THROUGH.10"
    assert position["step_11"] == "NOT.CLEARED"
    assert position["step_12"] == "BLOCKED"
    assert position["real_human_authorization_present"] is False
    assert position["merge_authorized"] is False
    assert position["canonical_promotion_authorized"] is False

    boundaries = doc["boundaries"]
    assert boundaries["new_lane"] is False
    assert boundaries["taskbars_json_mutation"] is False
    assert boundaries["autonomous_promotion"] is False
    assert boundaries["merge_performed"] is False
    assert boundaries["promotion_performed"] is False

    return doc


def evaluate_step12_authorization(requested_action, requested_head, authorization_payload=None, doc=None):
    validate_migration_spec(doc)

    hold = {
        "truth_state": "U.21",
        "qualifier": "HUMANLOCK.HOLD",
        "step_12_action_eligible": False,
        "merge_authorized": False,
        "canonical_promotion_authorized": False,
    }

    if authorization_payload is None:
        return {"decision": "REJECT.MISSING.EXACT_HEAD.HUMANLOCK.AUTHORIZATION", **hold}

    if authorization_payload.get("simulation_fixture") is True:
        return {"decision": "REJECT.SIMULATION.CANNOT.SATISFY.HUMANLOCK", **hold}

    if authorization_payload.get("authorization_state") != "EXPLICIT.HUMAN.AUTHORIZED":
        return {"decision": "REJECT.MISSING.EXPLICIT.HUMAN.AUTHORIZATION", **hold}
    if authorization_payload.get("human_authorization_present") is not True:
        return {"decision": "REJECT.MISSING.EXPLICIT.HUMAN.AUTHORIZATION", **hold}
    if authorization_payload.get("authorized_by_role") != "HUMAN.OPERATOR":
        return {"decision": "REJECT.NON_HUMAN_OPERATOR", **hold}
    if authorization_payload.get("authorization_scope") != "LIVE_TARGET_ACTION":
        return {"decision": "REJECT.NON_LIVE.AUTHORIZATION.SCOPE", **hold}
    if authorization_payload.get("live_execution_eligible") is not True:
        return {"decision": "REJECT.LIVE.EXECUTION.NOT.ELIGIBLE", **hold}
    if authorization_payload.get("target_action") != requested_action:
        return {"decision": "REJECT.WRONG.ACTION", **hold}
    if authorization_payload.get("target_head") != requested_head:
        return {"decision": "REJECT.STALE.OR.MISMATCHED.HEAD", **hold}

    return {
        "decision": "PASS.EXACT_HEAD.HUMANLOCK.AUTHORIZATION",
        "truth_state": "T.20",
        "qualifier": "EXACT.ACTION.EXACT.HEAD.HUMAN.AUTHORIZATION.PASS",
        "step_12_action_eligible": True,
        "merge_authorized": requested_action == "MERGE",
        "canonical_promotion_authorized": requested_action == "CANONICAL_PROMOTION",
    }


def validate_all():
    doc = validate_migration_spec()
    simulation = _load(SIMULATION_PATH)["simulation_authorization_fixture"]

    missing_auth = evaluate_step12_authorization(
        requested_action="MERGE",
        requested_head="cc3021f65b6b518b29ab220f818c1582fa18c03a",
        authorization_payload=None,
        doc=doc,
    )
    simulation_attempt = evaluate_step12_authorization(
        requested_action="MERGE",
        requested_head=simulation["target_head"],
        authorization_payload=simulation,
        doc=doc,
    )

    assert missing_auth["truth_state"] == "U.21"
    assert missing_auth["step_12_action_eligible"] is False
    assert simulation_attempt["truth_state"] == "U.21"
    assert simulation_attempt["step_12_action_eligible"] is False

    return {
        "identifier": "FR0333.ARCHITECTURE.AI.MIGRATION.12STEP.VALIDATION.RECEIPT.0001",
        "state": "T.20",
        "qualifier": "WORKING.SPEC.CONTRACT.PASS",
        "steps_validated": 12,
        "steps_1_through_10_can_imply_step_11": False,
        "step_10_is_authorization": False,
        "step_11_requires_real_human_exact_action_exact_head": True,
        "step_12_without_authorization": missing_auth,
        "simulation_cannot_satisfy_humanlock": simulation_attempt,
        "real_human_authorization_present": False,
        "merge_authorized": False,
        "canonical_promotion_authorized": False,
        "new_lane": False,
        "taskbars_json_mutation": False,
        "merge_performed": False,
        "promotion_performed": False,
    }


def main():
    report = validate_all()
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["state"] == "T.20" else 1)


if __name__ == "__main__":
    main()
