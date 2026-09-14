#!/usr/bin/env python3
import copy
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
MASTER_PATH = HERE / "fr0333_frontier_model_master_benchmark_0001.json"
FIXTURES_PATH = HERE / "fr0333_frontier_model_mock_fixtures_0001.json"
SCHEMA_PATH = HERE / "fr0333_disagreement_register_0001.schema.json"
HUMANLOCK_RECEIPT_PATH = HERE / "fr0333_humanlock_compliance_receipt_0001.json"
AUTH_SCHEMA_PATH = HERE / "fr0333_humanlock_authorization_0001.schema.json"
AUTH_MOCK_PATH = HERE / "fr0333_humanlock_authorization_mock_0001.json"

EXPECTED_PROVIDER_IDS = [
    "P01.OPENAI.CHATGPT",
    "P02.ANTHROPIC.CLAUDE",
    "P03.GOOGLE.GEMINI",
    "P04.XAI.GROK",
    "P05.PERPLEXITY",
    "P06.MICROSOFT.COPILOT",
]

EXPECTED_HUMANLOCK_PATH = [
    "HUMAN.OPERATOR",
    "Z.26.21.HUMANLOCK",
    "HUMAN.AUTHORIZATION",
    "PARTITION.ROUTING",
    "STATE.VALIDATION",
    "RECEIPT",
    "PASS.HOLD.REJECT",
]

SCENARIO_RULES = {
    "ALL.6.AGREE.BUT.WRONG": ("REJECT_ALL", "F.6", "VERIFIED_REPO_STATE", "FAILED_VALIDATION", "CRITICAL_BLOCKER", "RESOLVED_BY_REPOSITORY_FACT"),
    "1.MODEL.OBJECTS.WITH.VALID.SOURCE": ("HALT_COMPOSITE_OUTPUT", "U.21", "UNVERIFIED", "PENDING", "CRITICAL_BLOCKER", "INVESTIGATING"),
    "MODEL.CITES.NONEXISTENT.API": ("FLAG_CLAIM_INVALID", "F.6", "VERIFIED_REPO_STATE", "FAILED_VALIDATION", "CRITICAL_BLOCKER", "RESOLVED_BY_REPOSITORY_FACT"),
    "MODELS.DISAGREE.ON.CURRENT.REPO.STATE": ("FETCH_REPOSITORY_EVIDENCE", "U.21", "UNVERIFIED", "PENDING", "HIGH", "INVESTIGATING"),
    "SOURCE.CONFLICT": ("HOLD_SOURCE_CONFLICT", "U.21", "CONFLICTING_INTERNAL_DOCS", "IRRESOLVABLE_CONFLICT", "HIGH", "OPEN"),
    "PROVIDER.TIMEOUT": ("PARTIAL_RESULT_NO_FALSE_CONSENSUS", "U.21", "UNVERIFIED", "PENDING", "HIGH", "OPEN"),
    "MISSING.RECEIPT": ("HOLD_MISSING_RECEIPT", "U.21", "UNVERIFIED", "PENDING", "CRITICAL_BLOCKER", "OPEN"),
    "HUMANLOCK.ABSENT": ("BLOCK_PROMOTION", "U.21", "UNVERIFIED", "PENDING", "CRITICAL_BLOCKER", "OPEN"),
}


def _canonical_hash(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _provider_sets(fixture):
    responses = fixture.get("provider_responses", [])
    participating = [r["provider_id"] for r in responses]
    objections = [r["provider_id"] for r in responses if r.get("verdict") == "CRITICAL_BUG"]
    agreements = [p for p in participating if p not in objections and next((r for r in responses if r["provider_id"] == p), {}).get("status") != "TIMEOUT"]
    return agreements, objections


def _sources(fixture):
    out = []
    for response in fixture.get("provider_responses", []):
        out.extend(response.get("cited_sources", []))
    ground = fixture.get("ground_truth", {})
    repo = ground.get("repository_evidence")
    if repo:
        out.append(repo)
    return list(dict.fromkeys(out))


def validate_humanlock_contract(master):
    assert master["humanlock"] is True, "HumanLock top-level state must remain true"
    contract = master["humanlock_contract"]
    assert contract["identifier"] == "Z.26.21.HUMANLOCK"
    assert contract["state"] == "ACTIVE_IMMUTABLE"
    assert contract["can_be_disabled"] is False
    assert contract["semantic_role"] == "HUMAN_AUTHORIZATION_BOUNDARY"
    assert contract["biometric_or_neural_interface"] is False
    assert contract["cryptographic_signature_equivalence"] is False
    assert contract["automatic_bypass"] == "F.6"
    assert contract["removal_or_downgrade"] == "REJECT"
    assert contract["merge_requires_explicit_human_authorization"] is True
    assert contract["canonical_promotion_requires_explicit_human_authorization"] is True
    assert contract["authorization_path"] == EXPECTED_HUMANLOCK_PATH

    boundaries = set(master["boundaries"])
    required_boundaries = {
        "HUMANLOCK != CRYPTOGRAPHIC.SIGNATURE",
        "HUMANLOCK.REMOVAL.OR.DOWNGRADE = REJECT",
        "MERGE.REQUIRES.EXPLICIT.HUMAN.AUTHORIZATION",
        "CANONICAL.PROMOTION.REQUIRES.EXPLICIT.HUMAN.AUTHORIZATION",
        "NO.AUTONOMOUS.PROMOTION",
    }
    assert required_boundaries.issubset(boundaries)

    route = master["diamond_comparator"]["route"]
    assert route.count("HUMANLOCK") == 1
    assert route.index("HUMANLOCK") > route.index("FR0333.LOGIC_GATE")
    assert route.index("HUMANLOCK") < route.index("OUTPUT")
    assert master["diamond_comparator"]["promotion_rule"].endswith("+ HUMANLOCK")
    assert master["result"]["humanlock_state"] == "ACTIVE_IMMUTABLE"
    assert master["result"]["canonical_promotion"] == "HUMANLOCK_REQUIRED"


def assert_humanlock_mutation_rejected(master, mutator):
    candidate = copy.deepcopy(master)
    mutator(candidate)
    try:
        validate_humanlock_contract(candidate)
    except (AssertionError, KeyError, ValueError):
        return True
    raise AssertionError("HumanLock mutation was not rejected")


def evaluate_fixture(fixture, claim_index=1):
    scenario = fixture["scenario"]
    if scenario not in SCENARIO_RULES:
        raise AssertionError(f"unrecognized scenario {scenario}")

    action, truth_state, evidence_class, verification_state, impact, resolution = SCENARIO_RULES[scenario]
    agreements, objections = _provider_sets(fixture)
    responses = fixture.get("provider_responses", [])

    if scenario == "ALL.6.AGREE.BUT.WRONG":
        assert len(agreements) == 6
        assert fixture["ground_truth"].get("actual_state") == "ASYNC_WORKERS_UNSUPPORTED"
    elif scenario == "1.MODEL.OBJECTS.WITH.VALID.SOURCE":
        assert len(objections) == 1
        objector = next(r for r in responses if r.get("verdict") == "CRITICAL_BUG")
        assert objector.get("cited_sources"), "evidenced dissent must carry a source"
    elif scenario == "MODEL.CITES.NONEXISTENT.API":
        assert fixture["ground_truth"].get("exists") is False
    elif scenario == "MODELS.DISAGREE.ON.CURRENT.REPO.STATE":
        assert fixture["ground_truth"].get("actual_state") == "UNKNOWN_UNTIL_FETCH"
    elif scenario == "SOURCE.CONFLICT":
        ground = fixture["ground_truth"]
        assert ground.get("source_A_value") != ground.get("source_B_value")
        assert ground.get("authoritative_source") == "UNRESOLVED"
    elif scenario == "PROVIDER.TIMEOUT":
        assert any(r.get("status") == "TIMEOUT" for r in responses)
        assert fixture["ground_truth"].get("complete_provider_count") < fixture["ground_truth"].get("expected_provider_count")
    elif scenario == "MISSING.RECEIPT":
        recommendation = next(r for r in responses if r.get("active_recommendation"))
        assert recommendation.get("source_receipt_present") is False
    elif scenario == "HUMANLOCK.ABSENT":
        assert fixture["ground_truth"].get("technical_gate_pass") is True
        assert fixture["ground_truth"].get("human_authorization") is False

    assert action == fixture["expected_action"]
    assert truth_state == fixture["expected_truth_state"]

    claim_material = [r.get("claim", r.get("status", "")) for r in responses]
    primary_provider = objections[0] if objections else responses[0]["provider_id"]
    register = {
        "provider_id": primary_provider,
        "model_or_mode": "MOCK.FIXTURE",
        "task_hash": _canonical_hash({"fixture_id": fixture["fixture_id"], "workload_type": fixture["workload_type"]}),
        "claim_id": f"CLM-{claim_index:04d}",
        "claim_text_hash": _canonical_hash(claim_material),
        "agreement_set": agreements,
        "objection_set": objections,
        "cited_sources": _sources(fixture),
        "evidence_class": evidence_class,
        "verification_state": verification_state,
        "impact_level": impact,
        "resolution_state": resolution,
        "receipt_hash": _canonical_hash({"fixture_id": fixture["fixture_id"], "action": action, "truth_state": truth_state}),
    }
    return {
        "fixture_id": fixture["fixture_id"],
        "scenario": scenario,
        "action": action,
        "truth_state": truth_state,
        "register": register,
    }


def validate_master(master):
    assert master["identifier"] == "FR0333.FRONTIER.MODEL.MASTER.BENCHMARK.0001"
    assert master["architecture_state"] == "LOCKED.BASELINE"
    validate_humanlock_contract(master)
    assert master["integration_mode"]["core_model_weight_fusion"] is False
    assert master["integration_mode"]["cross_provider_runtime_connection_established"] is False
    assert [p["provider_id"] for p in master["providers"]] == EXPECTED_PROVIDER_IDS
    assert master["diamond_comparator"]["fan_out"] == EXPECTED_PROVIDER_IDS
    boundaries = set(master["boundaries"])
    assert "NO.NEW.LANE" in boundaries
    assert "NO.TASKBARS.JSON.MUTATION" in boundaries
    assert "NO.AUTONOMOUS.PROMOTION" in boundaries
    assert master["diamond_comparator"]["consensus_rule"] == "MODEL.AGREEMENT != VERIFIED.FACT"


def _authorization_payload_hash(payload):
    material = copy.deepcopy(payload)
    material.pop("payload_hash", None)
    return _canonical_hash(material)


def _with_recomputed_payload_hash(payload):
    candidate = copy.deepcopy(payload)
    candidate["payload_hash"] = _authorization_payload_hash(candidate)
    return candidate


def validate_humanlock_compliance_receipt(receipt):
    assert receipt["identifier"] == "FR0333.HUMANLOCK.COMPLIANCE.RECEIPT.0001"
    assert receipt["source_pr"] == 41
    assert receipt["source_head"] == "767e5ecc96a1b50b3896c9c51256aced1b27afb9"
    assert receipt["status"] == "FROZEN_VALIDATED"
    contract = receipt["contract_configuration"]
    assert contract["humanlock_id"] == "Z.26.21.HUMANLOCK"
    assert contract["humanlock_state"] == "ACTIVE_IMMUTABLE"
    assert contract["humanlock_can_be_disabled"] == "F.6"
    assert contract["automatic_bypass"] == "F.6"
    assert contract["removal_or_downgrade"] == "REJECT"
    assert contract["definition_invariant"] == "HUMANLOCK != CRYPTOGRAPHIC.SIGNATURE"
    policy = receipt["authorization_policy"]
    assert policy["merge_requires_explicit_human_authorization"] == "T.20"
    assert policy["canonical_promotion_requires_explicit_human_authorization"] == "T.20"
    assert policy["humanlock_equivalent_to_signature"] is False
    assert all(row["expected"] == "REJECT" and row["verified"] is True for row in receipt["mutation_test_matrix"])
    verify = receipt["verification_environment"]
    assert verify["frontier_model_ci_run_id"] == 34878039174
    assert verify["frontier_model_ci_result"] == "T.20"
    assert verify["raven_cloud_taskbar_run_id"] == 34878039109
    assert verify["raven_cloud_taskbar_result"] == "T.20"
    target = receipt["target_runtime_boundaries"]
    assert target["pr41_merge_truth_state"] == "U.21"
    assert target["pr41_canonical_promotion_truth_state"] == "U.21"
    assert target["new_lane"] is False
    assert target["taskbars_json_mutation"] is False


def evaluate_authorization(payload, auth_validator, expected_action, expected_head):
    auth_validator.validate(payload)
    if payload["payload_hash"] != _authorization_payload_hash(payload):
        return {
            "decision": "REJECT.PAYLOAD_HASH_MISMATCH",
            "truth_state": "U.21",
            "qualifier": "HUMANLOCK.HOLD",
            "humanlock_boundary_reached": False,
            "action_eligible": False,
        }
    if payload["target_action"] != expected_action:
        return {
            "decision": "REJECT.WRONG_ACTION",
            "truth_state": "U.21",
            "qualifier": "HUMANLOCK.HOLD",
            "humanlock_boundary_reached": False,
            "action_eligible": False,
        }
    if payload["target_head"] != expected_head:
        return {
            "decision": "REJECT.STALE_OR_MISMATCHED_HEAD",
            "truth_state": "U.21",
            "qualifier": "HUMANLOCK.HOLD",
            "humanlock_boundary_reached": False,
            "action_eligible": False,
        }
    if payload["authorization_state"] != "EXPLICIT.HUMAN.AUTHORIZED" or payload["human_authorization_present"] is not True:
        return {
            "decision": "REJECT.MISSING_HUMAN_AUTHORIZATION",
            "truth_state": "U.21",
            "qualifier": "HUMANLOCK.HOLD",
            "humanlock_boundary_reached": False,
            "action_eligible": False,
        }
    if payload["mock_only"] is True:
        assert payload["authorization_scope"] == "SIMULATION_ONLY"
        assert payload["live_execution_eligible"] is False
        return {
            "decision": "PASS.MOCK_ONLY",
            "truth_state": "T.20",
            "qualifier": "STRUCTURAL.AUTHORIZATION.PASS.SIMULATION_ONLY",
            "humanlock_boundary_reached": True,
            "action_eligible": False,
        }
    if payload["authorization_scope"] != "LIVE_TARGET_ACTION" or payload["live_execution_eligible"] is not True:
        return {
            "decision": "REJECT.LIVE_SCOPE_NOT_ELIGIBLE",
            "truth_state": "U.21",
            "qualifier": "HUMANLOCK.HOLD",
            "humanlock_boundary_reached": False,
            "action_eligible": False,
        }
    return {
        "decision": "PASS.LIVE.AUTHORIZATION.STRUCTURE",
        "truth_state": "T.20",
        "qualifier": "HUMANLOCK.AUTHORIZATION.STRUCTURE.PASS",
        "humanlock_boundary_reached": True,
        "action_eligible": True,
    }


def validate_authorization_package(receipt=None, auth_schema=None, mock_suite=None):
    receipt = receipt or _load(HUMANLOCK_RECEIPT_PATH)
    auth_schema = auth_schema or _load(AUTH_SCHEMA_PATH)
    mock_suite = mock_suite or _load(AUTH_MOCK_PATH)

    validate_humanlock_compliance_receipt(receipt)
    Draft202012Validator.check_schema(auth_schema)
    auth_validator = Draft202012Validator(auth_schema)

    assert mock_suite["identifier"] == "FR0333.HUMANLOCK.AUTHORIZATION.MOCK.SUITE.0001"
    assert mock_suite["architecture_state"] == "LOCKED.BASELINE"
    assert mock_suite["humanlock"] == "ACTIVE_IMMUTABLE"
    expected_head = mock_suite["demonstration_target_head"]
    expected_action = mock_suite["expected_target_action"]
    assert expected_head == receipt["source_head"]
    assert expected_action == "MERGE"

    base_payload = mock_suite["mock_authorization"]
    positive = evaluate_authorization(base_payload, auth_validator, expected_action, expected_head)
    assert positive == mock_suite["expected_positive_result"]

    negative_results = []
    for test in mock_suite["negative_tests"]:
        candidate = copy.deepcopy(base_payload)
        candidate.update(test["mutation"])
        candidate = _with_recomputed_payload_hash(candidate)
        result = evaluate_authorization(candidate, auth_validator, expected_action, expected_head)
        assert result["decision"] == test["expected_decision"]
        assert result["truth_state"] == test["expected_truth_state"]
        assert result["action_eligible"] is False
        negative_results.append({
            "test_id": test["test_id"],
            "decision": result["decision"],
            "truth_state": result["truth_state"],
        })

    hold_route = mock_suite["hold_semantics"]["route"]
    assert hold_route == [
        "AUTHORIZATION.INVALID.OR.ABSENT",
        "EMIT.NEW.HOLD.RECEIPT",
        "TRUTH.STATE.U.21",
        "QUALIFIER.HUMANLOCK.HOLD",
        "NO.ROLLBACK",
        "NO.PROMOTION",
    ]
    assert mock_suite["hold_semantics"]["append_only"] is True
    boundaries = set(mock_suite["boundaries"])
    assert "MOCK.AUTHORIZATION != LIVE.AUTHORIZATION" in boundaries
    assert "NEW.COMMIT.INVALIDATES.PRIOR.HEAD_BOUND.AUTHORIZATION" in boundaries
    assert "NO.NEW.LANE" in boundaries
    assert "NO.TASKBARS.JSON.MUTATION" in boundaries
    assert "NO.MERGE" in boundaries
    assert "NO.PROMOTION" in boundaries

    return {
        "identifier": "FR0333.HUMANLOCK.AUTHORIZATION.MOCK.VALIDATION.RECEIPT.0001",
        "state": "T.20",
        "qualifier": "MOCK.AUTHORIZATION.PACKAGE.PASS",
        "compliance_receipt": receipt["identifier"],
        "compliance_source_head": receipt["source_head"],
        "positive_control": positive,
        "negative_test_count": len(negative_results),
        "negative_tests": negative_results,
        "live_authorization_created": False,
        "merge_authorized": False,
        "canonical_promotion_authorized": False,
        "humanlock": "ACTIVE_IMMUTABLE",
        "new_lane": False,
        "taskbars_json_mutation": False,
    }


def validate_all(master=None, fixtures_doc=None, schema=None):
    master = master or _load(MASTER_PATH)
    fixtures_doc = fixtures_doc or _load(FIXTURES_PATH)
    schema = schema or _load(SCHEMA_PATH)

    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    validate_master(master)

    assert fixtures_doc["architecture_state"] == "LOCKED.BASELINE"
    assert fixtures_doc["humanlock"] is True
    assert fixtures_doc["provider_ids"] == EXPECTED_PROVIDER_IDS
    fixtures = fixtures_doc["fixtures"]
    assert len(fixtures) == 8
    assert len({f["fixture_id"] for f in fixtures}) == 8

    results = []
    for index, fixture in enumerate(fixtures, start=1):
        result = evaluate_fixture(fixture, claim_index=index)
        validator.validate(result["register"])
        results.append(result)

    unresolved_high_or_critical = sum(
        1 for r in results
        if r["register"]["impact_level"] in {"HIGH", "CRITICAL_BLOCKER"}
        and r["register"]["resolution_state"] in {"OPEN", "INVESTIGATING"}
    )
    failed_claims = sum(1 for r in results if r["truth_state"] == "F.6")
    authorization_package = validate_authorization_package()

    return {
        "identifier": "FR0333.FRONTIER.MODEL.MOCK.VALIDATION.RECEIPT.0001",
        "state": "T.20" if len(results) == 8 and authorization_package["state"] == "T.20" else "F.6",
        "qualifier": "MOCK.PIPELINE.MECHANICS.PASS" if len(results) == 8 and authorization_package["state"] == "T.20" else "MOCK.PIPELINE.MECHANICS.FAIL",
        "fixture_count": len(results),
        "schema_valid_register_count": len(results),
        "failed_claim_fixture_count": failed_claims,
        "unresolved_high_or_critical_count": unresolved_high_or_critical,
        "promotion_candidate": False,
        "promotion_hold_reason": "MOCK.FAILURE.SUITE.INTENTIONALLY.CONTAINS.BLOCKERS.AND.NO_LIVE_HUMAN_AUTHORIZATION_EXISTS",
        "humanlock": "ACTIVE_IMMUTABLE.REQUIRED",
        "humanlock_bypass": "F.6",
        "humanlock_removal_or_downgrade": "REJECT",
        "merge_requires_explicit_human_authorization": True,
        "canonical_promotion_requires_explicit_human_authorization": True,
        "new_lane": False,
        "taskbars_json_mutation": False,
        "cross_provider_live_runtime": "U.21.NOT.CONNECTED",
        "authorization_package": authorization_package,
        "results": results,
    }


def main():
    report = validate_all()
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["state"] == "T.20" else 1)


if __name__ == "__main__":
    main()
