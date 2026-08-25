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
}
REQUIRED_RUNTIME_STATES = {
    "PASS_RUNTIME", "PASS_SPEC", "HOLD", "FAIL", "UNKNOWN",
    "NOT_OBSERVED", "NOT_APPLICABLE", "CONFLICT"
}


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def main() -> None:
    data = json.loads(INDEX.read_text(encoding="utf-8"))

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

    print("FR0333.CREATIVEPRO.ADOBE.5D.HARDENER.001")
    print(f"version={data.get('version')}")
    print(f"dimensions={len(dims)}/5")
    print(f"required_controls={total_controls}/40")
    print(f"system_lanes={len(lanes)}/10")
    print(f"statistics_rows={len(stats)}")
    print("economic_discount_check=125")
    print("economic_net_savings_after_membership=47")
    print("coverage_semantics=EXPLICIT_DENOMINATOR_REQUIRED")
    print("state=PASS_SPEC_STRUCTURE_V1_1")


if __name__ == "__main__":
    main()
