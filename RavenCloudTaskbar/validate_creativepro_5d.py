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
    "METADATA_NE_PROVENANCE_NE_AUTHENTICITY_NE_IDENTITY_NE_TRUTH",
    "MISSING_NE_ZERO",
    "HOLD_NE_PASS",
    "OBSERVED_NE_CORRELATED_NE_CAUSAL",
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

    if data.get("coverage_target") != 1.0:
        fail("coverage_target must remain 1.0")

    rule = data.get("coverage_rule", "")
    for token in ("HOLD", "UNKNOWN", "NOT_OBSERVED", "CONFLICT"):
        if token not in rule:
            fail(f"coverage_rule must explicitly preserve {token} as non-PASS")

    lanes = data.get("system_lanes", [])
    if len(lanes) != 10 or len(set(lanes)) != 10:
        fail("system_lanes must contain 10 unique lanes")

    stats = data.get("creativepro_statistics", [])
    if not stats:
        fail("statistics register must not be empty")
    for row in stats:
        for key in ("metric", "value", "period", "evidence_state", "source"):
            if key not in row:
                fail(f"statistics row missing {key}: {row}")
        if not str(row["source"]).startswith("https://creativepro.com/"):
            fail(f"CreativePro statistics source outside source boundary: {row['source']}")

    total_controls = sum(len(d["required_controls"]) for d in dims.values())
    print("FR0333.CREATIVEPRO.ADOBE.5D.HARDENER.001")
    print(f"dimensions={len(dims)}/5")
    print(f"required_controls={total_controls}/40")
    print(f"system_lanes={len(lanes)}/10")
    print(f"statistics_rows={len(stats)}")
    print("coverage_semantics=100_PERCENT_REQUIRED_LANE_COVERAGE_NOT_INFALLIBILITY")
    print("state=PASS_SPEC_STRUCTURE")


if __name__ == "__main__":
    main()
