#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HUB = ROOT / "RavenCloudTaskbar" / "fr0333_revenue_auditance_hub_64bit.json"

ALLOWED_GROUPS = set("ABCDEFGH")
REQUIRED_BOUNDARIES = {
    "FR0333_IS_NOT_A_BANK_UNLESS_SEPARATELY_CHARTERED_AND_VERIFIED",
    "CASH_APP_IS_REFERENCE_ARCHITECTURE_NOT_FR0333_PAYMENT_INFRASTRUCTURE",
    "BOND_NE_100_PERCENT_GUARANTEE",
    "INFLOW_NE_REVENUE_NE_GROSS_PROFIT_NE_CASH_AVAILABLE",
    "OWNERSHIP_NE_POSSESSION_NE_CUSTODY_NE_LICENSE_NE_TRANSFER_AUTHORITY",
    "OBSERVED_NE_DERIVED_NE_CORRELATED_NE_CAUSAL",
}
DISALLOWED_UNSCOPED_GEOGRAPHIES = {"japan"}


def fail(msg: str) -> None:
    raise SystemExit(f"FAIL: {msg}")


def main() -> None:
    data = json.loads(HUB.read_text(encoding="utf-8"))

    if data.get("identifier") != "FR0333.REVENUE.AUDITANCE.HUB.64BIT.001":
        fail("identifier mismatch")
    if data.get("geographic_scope") != "UNITED_STATES":
        fail("geographic_scope must remain UNITED_STATES")
    if data.get("runtime_status", {}).get("bank_status") != "NOT_A_BANK":
        fail("spec must not claim bank status")
    if data.get("runtime_status", {}).get("cash_app_dependency") != "REFERENCE_ONLY":
        fail("Cash App must remain reference-only")

    boundaries = set(data.get("hard_boundaries", []))
    missing = REQUIRED_BOUNDARIES - boundaries
    if missing:
        fail(f"missing hard boundaries: {sorted(missing)}")

    bits = data.get("bits", [])
    if len(bits) != 64:
        fail(f"expected exactly 64 bits; got {len(bits)}")

    ids = [b.get("bit") for b in bits]
    expected = [f"BIT.{i:02d}" for i in range(1, 65)]
    if ids != expected:
        fail("bit sequence must be BIT.01 through BIT.64 in order")

    groups = Counter(b.get("group") for b in bits)
    if set(groups) != ALLOWED_GROUPS:
        fail(f"group mismatch: {sorted(groups)}")
    for group in sorted(ALLOWED_GROUPS):
        if groups[group] != 8:
            fail(f"group {group} must contain exactly 8 bits; got {groups[group]}")

    sources = {s["id"]: s for s in data.get("sources", [])}
    if len(sources) < 15:
        fail("source register too small")

    # Geography contamination is checked only where geography can enter the
    # evidence register. Policy text may name a forbidden geography while
    # describing the guard itself; that must not self-trigger the validator.
    for source in sources.values():
        searchable = " ".join(
            str(source.get(key, ""))
            for key in ("id", "publisher", "url", "scope")
        ).lower()
        hits = sorted(
            token for token in DISALLOWED_UNSCOPED_GEOGRAPHIES
            if token in searchable
        )
        if hits:
            fail(
                f"unscoped foreign geography in source {source['id']}: {hits}"
            )

    stats = data.get("statistics_register", [])
    if len(stats) < 40:
        fail("statistics register must contain at least 40 external statistics")
    for row in stats:
        if row.get("source") not in sources:
            fail(f"unknown source for {row.get('id')}: {row.get('source')}")
        for key in ("id", "metric", "value", "unit", "period", "source", "evidence"):
            if key not in row:
                fail(f"statistics row missing {key}: {row}")

    genius = data.get("genius_statistics", [])
    if len(genius) < 16:
        fail("genius statistics register must contain at least 16 derived statistics")
    stat_ids = {s["id"] for s in stats}
    for row in genius:
        if "formula" not in row or "inputs" not in row:
            fail(f"derived statistic lacks formula/inputs: {row.get('id')}")
        for input_id in row["inputs"]:
            if input_id not in stat_ids:
                fail(f"derived statistic {row.get('id')} references missing input {input_id}")

    chain = data.get("money_order_chain", [])
    for token in (
        "CONTRACT", "AUTHORITY", "MONEY_IN", "GROSS_RECEIPT",
        "NET_AVAILABLE", "RECONCILIATION", "REALIZED_VALUE", "AUDIT_RECEIPT"
    ):
        if token not in chain:
            fail(f"money_order_chain missing {token}")

    print("FR0333.REVENUE.AUDITANCE.HUB.64BIT.001")
    print("bits=64/64")
    print(f"groups={len(groups)}/8")
    print(f"sources={len(sources)}")
    print(f"external_statistics={len(stats)}")
    print(f"genius_statistics={len(genius)}")
    print("geographic_scope=UNITED_STATES")
    print("foreign_source_contamination=0")
    print("bank_status=NOT_A_BANK")
    print("cash_app_dependency=REFERENCE_ONLY")
    print("state=PASS_SPEC_STRUCTURE")


if __name__ == "__main__":
    main()
