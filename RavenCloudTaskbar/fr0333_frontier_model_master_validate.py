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

    return {
        "identifier": "FR0333.FRONTIER.MODEL.MOCK.VALIDATION.RECEIPT.0001",
        "state": "T.20" if len(results) == 8 else "F.6",
        "qualifier": "MOCK.PIPELINE.MECHANICS.PASS" if len(results) == 8 else "MOCK.PIPELINE.MECHANICS.FAIL",
        "fixture_count": len(results),
        "schema_valid_register_count": len(results),
        "failed_claim_fixture_count": failed_claims,
        "unresolved_high_or_critical_count": unresolved_high_or_critical,
        "promotion_candidate": False,
        "promotion_hold_reason": "MOCK.FAILURE.SUITE.INTENTIONALLY.CONTAINS.BLOCKERS",
        "humanlock": "ACTIVE_IMMUTABLE.REQUIRED",
        "humanlock_bypass": "F.6",
        "humanlock_removal_or_downgrade": "REJECT",
        "merge_requires_explicit_human_authorization": True,
        "canonical_promotion_requires_explicit_human_authorization": True,
        "new_lane": False,
        "taskbars_json_mutation": False,
        "cross_provider_live_runtime": "U.21.NOT.CONNECTED",
        "results": results,
    }


def main():
    report = validate_all()
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["state"] == "T.20" else 1)


if __name__ == "__main__":
    main()
