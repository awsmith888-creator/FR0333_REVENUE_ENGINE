#!/usr/bin/env python3
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC_PATH = HERE / "fr0333_ai_self_improvement_0004.json"

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

REQUIRED_METRICS = {
    "SOURCE.SELECTION.ERROR",
    "ROUTING.ERROR",
    "STALE.STATE.ERROR",
    "UNSUPPORTED.PROMOTION",
    "AUTHORIZATION.BYPASS",
    "RECEIPT.COMPLETENESS",
    "LINEAGE.PRESERVATION",
}


def load_spec(path: Path = SPEC_PATH):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_spec(spec):
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    require(spec.get("identifier") == "FR0333.AI.SELF.IMPROVEMENT.0004", "identifier mismatch")
    require(spec.get("mode") == "BOUNDED.RSI", "mode must remain BOUNDED.RSI")
    require(spec.get("state") == "CANDIDATE.WORKING.SPEC", "candidate state drift")
    require(spec.get("surface") == "ACTIVE.EXPERIMENTAL", "surface drift")
    require(spec.get("target") == "SOURCE.VALIDATION.STRUCTURES", "target drift")
    require(spec.get("secondary_measurement") == "TOOL.ROUTING.ACCURACY", "secondary measurement drift")
    require(spec.get("architecture_expansion") is False, "architecture expansion must remain false")
    require(spec.get("new_lane") is False, "new lane must remain false")
    require(spec.get("autonomous_promotion") is False, "autonomous promotion must remain false")

    humanlock = spec.get("humanlock", {})
    require(humanlock.get("id") == "Z.26.21.HUMANLOCK", "HumanLock id mismatch")
    require(humanlock.get("state") == "ACTIVE_IMMUTABLE", "HumanLock must remain ACTIVE_IMMUTABLE")
    require(humanlock.get("can_be_disabled") is False, "HumanLock disable path detected")
    require(humanlock.get("simulation_can_satisfy") is False, "simulation cannot satisfy HumanLock")
    require(humanlock.get("cryptographic_signature_equivalent") is False, "HumanLock cannot equal signature")

    promotion = spec.get("promotion", {})
    require(promotion.get("truth_state") == "U.21", "promotion truth state must remain U.21")
    require(promotion.get("qualifier") == "HOLD", "promotion qualifier must remain HOLD")
    require(promotion.get("capability_gain_claimed") is False, "capability gain cannot be claimed")
    require(promotion.get("canonical_spec_promotion_requires_exact_head_human_authorization") is True,
            "canonical spec promotion must require exact-head human authorization")
    require(promotion.get("capability_improvement_promotion_requires_behavioral_evidence") is True,
            "capability improvement promotion must require behavioral evidence")

    pr41 = spec.get("pr41_reference", {})
    require(pr41.get("state") == "COMPLETE.STAY", "PR41 must remain COMPLETE.STAY")
    require(pr41.get("merge_commit") == "2cac8a66d7d435be8f9dbbd8b375c83ce088763f", "PR41 merge commit drift")
    require(pr41.get("authorization_token") == "CONSUMED", "PR41 authorization token must stay consumed")
    require(pr41.get("new_authorization_token_required") is False, "PR41 cannot demand a new token")

    tokens = spec.get("token_mapping", [])
    require(len(tokens) == 10, "TEN.IN/TEN.OUT invariant violated")
    require([t.get("index") for t in tokens] == list(range(1, 11)), "token numbering drift")
    require([t.get("id") for t in tokens] == EXPECTED_TOKENS, "token identity/order drift")

    invariants = spec.get("systemic_invariants", {})
    require(invariants.get("ten_in") == 10, "TEN.IN must equal 10")
    require(invariants.get("ten_out") == 10, "TEN.OUT must equal 10")
    require(invariants.get("token_identity") == "PRESERVED", "token identity must be preserved")
    require(invariants.get("token_renumbering") is False, "token renumbering detected")
    require(invariants.get("eleventh_token_created") is False, "eleventh token detected")
    require(invariants.get("new_ten_token_batch") == "NOT.SEPARATELY.ESTABLISHED", "unverified token batch introduced")
    require(invariants.get("predecessor_overwrite_allowed") is False, "predecessor overwrite cannot be allowed")

    evaluation = spec.get("behavioral_evaluation", {})
    metric_ids = {m.get("id") for m in evaluation.get("metrics", [])}
    require(metric_ids == REQUIRED_METRICS, "behavioral metric set drift")
    require(evaluation.get("self_generated_logs_sufficient_for_pass") is False,
            "self-generated logs cannot satisfy candidate pass")

    boundaries = set(spec.get("boundaries", []))
    for required in {
        "CANONICAL.SPEC.PROMOTION != CAPABILITY.IMPROVEMENT.PROMOTION",
        "OBSERVATION != EXECUTION",
        "RECEIPT != AUTHORIZATION",
        "ROUTING != AUTHORIZATION",
        "MERGE != DEPLOYMENT",
        "HUMANLOCK != CRYPTOGRAPHIC.SIGNATURE",
    }:
        require(required in boundaries, f"missing boundary: {required}")

    return errors


def main():
    spec = load_spec()
    errors = validate_spec(spec)
    if errors:
        print("FR0333.AI.SELF.IMPROVEMENT.0004 VALIDATION: FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("FR0333.AI.SELF.IMPROVEMENT.0004 VALIDATION: PASS")
    print("TEN.IN=10 TEN.OUT=10 HUMANLOCK=ACTIVE_IMMUTABLE PROMOTION=U.21 QUALIFIER=HOLD")


if __name__ == "__main__":
    main()
