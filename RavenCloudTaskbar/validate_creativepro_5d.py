#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "RavenCloudTaskbar" / "fr0333_creativepro_adobe_5d_index.json"

EXPECTED_DIMENSIONS = {
    "D1_SOURCE_AUTHORITY",
    "D2_PRODUCTION_WORKFLOW",
    "D3_FORENSICS_RIGHTS",
    "D4_ATTENTION_NETWORK",
    "D5_ECONOMIC_RUNTIME",
}
REQUIRED_GATES = {
    "100_PERCENT_MEANS_REQUIRED_LANE_COVERAGE_NOT_INFALLIBILITY",
    "FOLLOWER_COUNT_NE_TECHNICAL_AUTHORITY",
    "SOURCE_COUNT_NE_INDEPENDENT_SOURCE_COUNT",
    "REPRODUCTION_COUNT_NE_INDEPENDENT_EVIDENCE_COUNT",
    "METADATA_NE_PROVENANCE_NE_AUTHENTICITY_NE_IDENTITY_NE_TRUTH",
    "ACCESS_NE_AUTHORITY",
    "MISSING_NE_ZERO",
    "HOLD_NE_PASS",
    "DEFINED_NE_CI_VALIDATED_NE_RUNTIME_PROVEN",
    "PRICE_LISTING_VERIFIED_NE_TRANSACTION_OBSERVED",
    "OBSERVED_NE_CORRELATED_NE_CAUSAL",
    "STILLNESS_NE_INCAPACITY",
    "NARRATIVE_METAPHOR_NE_BIOLOGICAL_LAW",
    "INTERPRETATION_NE_OBSERVED_FACT",
    "DESTRUCTIVE_RHETORIC_NE_PRODUCTION_INSTRUCTION",
    "QUIET_FRAME_REQUIRES_LATENT_FORCE_SIGNALS",
}
REQUIRED_RUNTIME_STATES = {
    "PASS_RUNTIME", "PASS_SPEC", "HOLD", "FAIL", "UNKNOWN",
    "NOT_OBSERVED", "NOT_APPLICABLE", "CONFLICT"
}
EXPECTED_FIXES = {
    "DF-0001": "ROUTE_ISOLATION_FILTER",
    "DF-0002": "EXPLICIT_BOUNDS_CHECK",
    "DF-0003": "NARROW_CRYPTO_SCOPE",
    "DF-0004": "NON_HUMAN_SIGNATURE_FORCE",
    "DF-0005": "APPLICATION_AUTH_DECOUPLING",
    "DF-0006": "FAIL_CLOSED_VALIDATION",
    "DF-0007": "EXPLICIT_DENOMINATOR_INJECTION",
    "DF-0008": "ANONYMIZED_PURGE_RECEIPT",
}
REQUIRED_QUIET_SIGNALS = {
    "posture_control", "gaze_control", "lighting_hierarchy",
    "environmental_reaction", "perspective_dominance", "prop_control",
    "negative_space_control", "occlusion_tension",
}


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def main() -> None:
    data = json.loads(INDEX.read_text(encoding="utf-8"))

    if data.get("version") != "1.2.0":
        fail(f"expected index version 1.2.0; got {data.get('version')}")

    dims = data.get("five_dimensions", {})
    if set(dims) != EXPECTED_DIMENSIONS:
        fail(f"dimension mismatch: {sorted(dims)}")

    for name, block in dims.items():
        controls = block.get("required_controls", [])
        if len(controls) != 8:
            fail(f"{name} must define exactly 8 required controls; got {len(controls)}")
        if len(set(controls)) != len(controls):
            fail(f"{name} contains duplicate controls")

    gates = set(data.get("governing_gates", []))
    missing_gates = REQUIRED_GATES - gates
    if missing_gates:
        fail(f"missing governing gates: {sorted(missing_gates)}")

    coverage = data.get("coverage", {})
    if coverage.get("target") != 1.0:
        fail("coverage.target must remain 1.0")
    if coverage.get("spec_formula") != "defined_required_controls / required_controls":
        fail("unexpected spec coverage formula")
    if coverage.get("runtime_formula") != "runtime_pass_controls / applicable_runtime_controls":
        fail("unexpected runtime coverage formula")

    rule = coverage.get("rule", "")
    for token in ("HOLD", "UNKNOWN", "NOT_OBSERVED", "CONFLICT", "FAIL", "NOT_APPLICABLE"):
        if token not in rule:
            fail(f"coverage.rule must explicitly preserve {token}")

    lanes = data.get("system_lanes", [])
    if len(lanes) != 10 or len(set(lanes)) != 10:
        fail("system_lanes must contain 10 unique lanes")

    states = set(data.get("runtime_state_model", []))
    missing_states = REQUIRED_RUNTIME_STATES - states
    if missing_states:
        fail(f"runtime_state_model missing: {sorted(missing_states)}")

    stats = data.get("creativepro_statistics", [])
    if not stats:
        fail("statistics register must not be empty")
    for row in stats:
        for key in ("metric", "value", "period", "evidence_state", "source"):
            if key not in row:
                fail(f"statistics row missing {key}: {row}")
        if not str(row["source"]).startswith("https://creativepro.com/"):
            fail(f"CreativePro statistics source outside boundary: {row['source']}")

    gs = data.get("genius_statistics", {})
    if gs.get("summit_member_price_advantage_usd") != 125:
        fail("price advantage statistic mismatch")
    if gs.get("membership_cost_usd") != 78:
        fail("membership cost statistic mismatch")
    if gs.get("net_savings_if_membership_bought_only_for_one_qualifying_125_discount_usd") != 47:
        fail("net savings statistic mismatch")

    total_controls = sum(len(d["required_controls"]) for d in dims.values())
    if total_controls != 40:
        fail(f"required control count must remain 40; got {total_controls}")

    bridge = data.get("legacy_registry_bridge", {})
    if bridge.get("source_registry") != "FR-0333-ADOBE-64BIT-REG":
        fail("legacy Adobe registry bridge missing")
    if bridge.get("semantic_fix_state") != "8_OF_8_CLOSED_SPEC":
        fail("semantic fix bridge is not 8/8 CLOSED_SPEC")
    if bridge.get("local_retest_state") != "8_OF_8_PASS_LOCAL":
        fail("semantic fix bridge is not 8/8 PASS_LOCAL")
    if bridge.get("external_adobe_runtime") != "HOLD_UNTIL_CREDENTIAL_BACKED_RECEIPT":
        fail("external Adobe runtime must remain receipt-gated")

    fixes = data.get("semantic_fixes", [])
    if len(fixes) != 8:
        fail(f"expected 8 semantic fixes; got {len(fixes)}")
    fix_map = {row.get("id"): row for row in fixes}
    if set(fix_map) != set(EXPECTED_FIXES):
        fail("semantic fix IDs mismatch")
    for fix_id, expected_after in EXPECTED_FIXES.items():
        row = fix_map[fix_id]
        if row.get("after") != expected_after:
            fail(f"{fix_id} resolution mismatch")
        if row.get("state") != "CLOSED_SPEC" or row.get("retest") != "PASS_LOCAL":
            fail(f"{fix_id} not closed and locally retested")

    narrative = data.get("narrative_power_gate", {})
    if narrative.get("record_id") != "FR.0333.ADOBE.NARRATIVE.POWER.0001":
        fail("narrative power record missing")
    if narrative.get("genius_bit_candidate") != "0016":
        fail("GENIUS bit candidate must be 0016")
    if narrative.get("core_rule") != "STILLNESS_NE_INCAPACITY":
        fail("narrative core rule mismatch")

    verification = narrative.get("source_verification", [])
    verified_states = {row.get("state") for row in verification}
    if "VERIFIED_ATTRIBUTION_AND_SPEECH" not in verified_states or "VERIFIED_LION_SPEECH_CONTEXT" not in verified_states:
        fail("Lion speech attribution/context source verification incomplete")

    boundary = narrative.get("evidence_boundary", {})
    if boundary.get("david_comparison") != "INTERPRETATION":
        fail("David comparison must remain interpretation")
    if boundary.get("genetic_makeup_built_to_destroy") != "QUARANTINED_UNSUPPORTED_BIOLOGICAL_CLAIM":
        fail("unsupported biological claim must remain quarantined")
    if boundary.get("total_eradication") != "QUARANTINED_RHETORICAL_EXAGGERATION":
        fail("eradication rhetoric must remain quarantined")

    quiet = narrative.get("nine_sixteen_quiet_authority_spec", {})
    if quiet.get("target_ratio") != "9:16":
        fail("quiet-authority target ratio must remain 9:16")
    if quiet.get("required_signals") != 3:
        fail("quiet-authority minimum signal count must remain 3")
    if set(quiet.get("eligible_signals", [])) != REQUIRED_QUIET_SIGNALS:
        fail("quiet-authority signal vocabulary mismatch")
    if quiet.get("status") != "PASS_SPEC":
        fail("quiet-authority gate must be PASS_SPEC, not runtime")

    print("FR0333.CREATIVEPRO.ADOBE.5D.HARDENER.001")
    print(f"version={data.get('version')}")
    print(f"dimensions={len(dims)}/5")
    print(f"required_controls={total_controls}/40")
    print(f"system_lanes={len(lanes)}/10")
    print(f"statistics_rows={len(stats)}")
    print("semantic_fixes=8/8")
    print("semantic_retests=8/8")
    print("lion_gate=PASS_SPEC")
    print("quiet_authority_signals=8_DEFINED_MIN_3_REQUIRED")
    print("external_adobe_runtime=HOLD_CREDENTIAL_RECEIPT_REQUIRED")
    print("economic_discount_check=125")
    print("economic_net_savings_after_membership=47")
    print("coverage_semantics=EXPLICIT_DENOMINATOR_REQUIRED")
    print("state=PASS_SPEC_STRUCTURE_V1_2")


if __name__ == "__main__":
    main()
