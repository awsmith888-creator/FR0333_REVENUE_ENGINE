#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "RavenCloudTaskbar" / "fr0333_creativepro_adobe_5d_index.json"
VECTOR = ROOT / "RavenCloudTaskbar" / "fr0333_creativepro_adobe_5d_runtime_vector.json"
DIST = ROOT / "RavenCloudTaskbar" / "dist"
RECEIPT = DIST / "fr0333_creativepro_adobe_5d_runtime_receipt.json"

VALID = {"PASS_RUNTIME","PASS_SPEC","HOLD","FAIL","UNKNOWN","NOT_OBSERVED","NOT_APPLICABLE","CONFLICT"}


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def main() -> None:
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    vector = json.loads(VECTOR.read_text(encoding="utf-8"))
    dims = index["five_dimensions"]
    v_dims = vector["dimensions"]

    if set(dims) != set(v_dims):
        fail("runtime vector dimensions do not match index")

    total = 0
    runtime_pass = 0
    spec_pass = 0
    applicable = 0
    all_counts: Counter[str] = Counter()
    dimension_receipts = {}

    for dname, dblock in dims.items():
        expected = dblock["required_controls"]
        actual = v_dims[dname]
        if set(expected) != set(actual):
            fail(f"{dname} control mismatch")
        if len(expected) != 8:
            fail(f"{dname} must retain eight controls")

        counts = Counter(actual.values())
        invalid = set(counts) - VALID
        if invalid:
            fail(f"{dname} invalid states: {sorted(invalid)}")

        d_total = len(expected)
        d_applicable = d_total - counts["NOT_APPLICABLE"]
        d_runtime = counts["PASS_RUNTIME"]
        d_spec = counts["PASS_SPEC"]
        d_coverage = d_runtime / d_applicable if d_applicable else None

        total += d_total
        applicable += d_applicable
        runtime_pass += d_runtime
        spec_pass += d_spec
        all_counts.update(counts)
        dimension_receipts[dname] = {
            "controls": d_total,
            "applicable_runtime_controls": d_applicable,
            "runtime_pass": d_runtime,
            "spec_only_pass": d_spec,
            "runtime_coverage": d_coverage,
            "states": dict(sorted(counts.items())),
        }

    if total != 40:
        fail(f"expected 40 controls, got {total}")

    stats = {row["metric"]: row["value"] for row in index["creativepro_statistics"]}
    member = stats["design_ai_summit_part2_member_price_usd"]
    nonmember = stats["design_ai_summit_part2_nonmember_price_usd"]
    membership = stats["membership_price_usd"]
    discount = stats["multi_day_member_discount_usd"]

    if nonmember - member != discount:
        fail("summit price difference must equal recorded member discount")
    if discount - membership != 47:
        fail("net one-pass membership savings must remain $47 for current source snapshot")

    overall_runtime_coverage = runtime_pass / applicable if applicable else None
    spec_definition_coverage = total / 40

    receipt = {
        "system": "FR0333_CREATIVEPRO_ADOBE_5D_RUNTIME",
        "parent": index["identifier"],
        "index_version": index["version"],
        "vector_version": vector["version"],
        "total_required_controls": total,
        "spec_definition_coverage": spec_definition_coverage,
        "applicable_runtime_controls": applicable,
        "runtime_pass_controls": runtime_pass,
        "spec_only_pass_controls": spec_pass,
        "runtime_coverage": overall_runtime_coverage,
        "state_counts": dict(sorted(all_counts.items())),
        "dimensions": dimension_receipts,
        "economic_checks": {
            "nonmember_minus_member_usd": nonmember - member,
            "recorded_discount_usd": discount,
            "membership_cost_usd": membership,
            "net_savings_after_membership_usd": discount - membership,
        },
        "evidence_gate": "DEFINED != CI_VALIDATED != RUNTIME_PROVEN",
        "independence_gate": "REPRODUCTION_COUNT != INDEPENDENT_EVIDENCE_COUNT",
        "promotion": "STAY" if overall_runtime_coverage != 1.0 else "RUNTIME_COVERAGE_COMPLETE_REVIEW_REQUIRED",
    }

    DIST.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(index["identifier"])
    print(f"spec_definition_coverage={total}/40")
    print(f"runtime_pass={runtime_pass}/{applicable}")
    print(f"runtime_coverage={overall_runtime_coverage:.6f}")
    print(f"spec_only_pass={spec_pass}")
    print(f"states={dict(sorted(all_counts.items()))}")
    print(f"economic_discount_check={nonmember-member}")
    print(f"economic_net_savings_after_membership={discount-membership}")
    print(f"promotion={receipt['promotion']}")
    print(RECEIPT)


if __name__ == "__main__":
    main()
