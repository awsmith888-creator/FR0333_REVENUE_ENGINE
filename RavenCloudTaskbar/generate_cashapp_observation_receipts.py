#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from cashapp_observation_adapter import ObservationValidationError, normalize_cashapp_observation

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "RavenCloudTaskbar" / "fr0333_cashapp_observation_fixtures.json"
OUT = ROOT / "RavenCloudTaskbar" / "generated_cashapp_observation_receipts.json"


def main() -> None:
    data = json.loads(FIXTURES.read_text(encoding="utf-8"))
    receipts = []
    failures = []

    for fixture in data["records"]:
        if fixture["expect"] == "PASS":
            receipts.append(normalize_cashapp_observation(fixture["record"]))
            continue
        try:
            normalize_cashapp_observation(fixture["record"])
        except ObservationValidationError as exc:
            failures.append({
                "fixture": fixture["name"],
                "expected_failure_code": fixture["failure_code"],
                "observed_failure_code": exc.code,
                "matched": exc.code == fixture["failure_code"],
            })
        else:
            failures.append({
                "fixture": fixture["name"],
                "expected_failure_code": fixture["failure_code"],
                "observed_failure_code": "NO_FAILURE",
                "matched": False,
            })

    if not all(row["matched"] for row in failures):
        raise SystemExit("FAIL: one or more observation fixtures did not fail as expected")

    output = {
        "identifier": "FR0333.REVENUE.AUDITANCE.CASHAPP.OBSERVATION.001.CI.RECEIPTS",
        "state": "READ_ONLY_CI_CANDIDATE",
        "provider": "CASH_APP",
        "mode": "READ_ONLY",
        "provider_record_receipts": receipts,
        "negative_gate_receipts": failures,
        "provider_records_normalized": len(receipts),
        "expected_failures_matched": len(failures),
        "live_money_movement": 0,
        "live_financial_execution": 0,
        "authority_to_move_funds": False,
        "real_cash_app_credentials_used": 0,
        "real_cash_app_api_calls": 0,
    }
    OUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"provider_record_receipts={len(receipts)}")
    print(f"negative_gate_receipts={len(failures)}")
    print("live_money_movement=0")
    print("real_cash_app_api_calls=0")
    print(f"output={OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
