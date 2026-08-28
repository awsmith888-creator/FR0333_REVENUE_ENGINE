#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from revenue_auditance_runtime import RuntimeValidationError, build_receipt

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "RavenCloudTaskbar" / "fr0333_revenue_auditance_runtime_fixtures.json"
OUT = ROOT / "RavenCloudTaskbar" / "generated_revenue_auditance_receipts.json"


def main() -> None:
    data = json.loads(FIXTURES.read_text(encoding="utf-8"))
    receipts = []
    failures = []

    for fixture in data["events"]:
        event = fixture["event"]
        if fixture["expect"] == "PASS":
            receipts.append(build_receipt(event))
            continue
        try:
            build_receipt(event)
        except RuntimeValidationError as exc:
            failures.append({
                "fixture": fixture["name"],
                "event_id": event["event_id"],
                "expected_failure_code": fixture["failure_code"],
                "observed_failure_code": exc.code,
                "matched": exc.code == fixture["failure_code"],
            })
        else:
            failures.append({
                "fixture": fixture["name"],
                "event_id": event["event_id"],
                "expected_failure_code": fixture["failure_code"],
                "observed_failure_code": "NO_FAILURE",
                "matched": False,
            })

    if not all(row["matched"] for row in failures):
        raise SystemExit("FAIL: one or more negative fixtures did not fail as expected")

    output = {
        "identifier": "FR0333.REVENUE.AUDITANCE.RUNTIME.001.SYNTHETIC.RECEIPTS",
        "state": "SIMULATION_VERIFIED_CANDIDATE",
        "live_money_movement": 0,
        "live_financial_execution": 0,
        "receipts": receipts,
        "negative_gate_receipts": failures,
    }
    OUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"receipts={len(receipts)}")
    print(f"negative_gate_receipts={len(failures)}")
    print("live_money_movement=0")
    print(f"output={OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
