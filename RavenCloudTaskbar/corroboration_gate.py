#!/usr/bin/env python3
"""FR-0333 Zero Lion corroboration gate.

Counts independent evidentiary origins, never headline volume.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

VERSION = "FR0333.CORROBORATION.1"
REQUIRED_FIELDS = (
    "SOURCE.ORIGIN",
    "SOURCE.DERIVATION",
    "SOURCE.INDEPENDENCE",
    "SOURCE.CLASS",
    "CLAIM.CLASS",
    "CORROBORATION.STATE",
    "CONTRADICTION.STATE",
    "CAUSATION.STATE",
    "PROMOTION.STATE",
)
STATES = {f"C{i}" for i in range(7)}
INDEPENDENT_STATES = {"C3", "C4", "C5", "C6"}
FACT_PROMOTIONS = {"FACT", "PROVEN", "VERIFIED_TRUE", "HIGHER_EVIDENTIARY_CONFIDENCE"}
CAUSAL_PROMOTIONS = {"CAUSAL", "CAUSATION.PROVEN"}


class CorroborationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def distinct_origins(sources: list[dict[str, Any]]) -> set[str]:
    origins: set[str] = set()
    for source in sources:
        origin = source.get("origin")
        if not isinstance(origin, str) or not origin.strip():
            raise CorroborationError("SOURCE_ORIGIN_REQUIRED", "every source requires a stable origin")
        origins.add(origin.strip())
    return origins


def validate_claim(claim: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in REQUIRED_FIELDS if field not in claim]
    if missing:
        raise CorroborationError("LINEAGE_FIELDS_REQUIRED", ",".join(missing))

    state = claim["CORROBORATION.STATE"]
    if state not in STATES:
        raise CorroborationError("INVALID_CORROBORATION_STATE", str(state))

    sources = claim.get("SOURCES")
    if not isinstance(sources, list) or not sources:
        raise CorroborationError("SOURCES_REQUIRED", "claim requires at least one source")
    origin_count = len(distinct_origins(sources))
    report_count = len(sources)

    if state == "C0" and claim["SOURCE.ORIGIN"] not in (None, "UNKNOWN"):
        raise CorroborationError("C0_ORIGIN_CONFLICT", "C0 must not assert an authenticated origin")
    if state == "C1" and origin_count != 1:
        raise CorroborationError("C1_REQUIRES_ONE_ORIGIN", str(origin_count))
    if state == "C2" and (origin_count != 1 or report_count < 2):
        raise CorroborationError(
            "C2_SAME_ORIGIN_REQUIRED",
            f"reports={report_count};origins={origin_count}",
        )
    if state in INDEPENDENT_STATES and origin_count < 2:
        raise CorroborationError("INDEPENDENCE_NOT_DEMONSTRATED", f"state={state};origins={origin_count}")

    promotion = claim["PROMOTION.STATE"]
    contradiction = claim["CONTRADICTION.STATE"]
    causation = claim["CAUSATION.STATE"]

    if state in {"C0", "C1", "C2"} and promotion in FACT_PROMOTIONS:
        raise CorroborationError("AUTHENTICITY_NE_TRUTH", f"{state} cannot promote as {promotion}")
    if promotion == "HIGHER_EVIDENTIARY_CONFIDENCE" and not (
        state == "C6" and contradiction == "PASS"
    ):
        raise CorroborationError(
            "HIGHER_CONFIDENCE_REQUIRES_C6_CONTRADICTION_PASS",
            f"state={state};contradiction={contradiction}",
        )
    if promotion in CAUSAL_PROMOTIONS and causation != "PASS":
        raise CorroborationError("CAUSAL_GATE_REQUIRED", f"causation={causation}")

    return {
        "gate_version": VERSION,
        "claim_id": claim.get("CLAIM.ID"),
        "report_count": report_count,
        "evidentiary_origin_count": origin_count,
        "corroboration_state": state,
        "contradiction_state": contradiction,
        "causation_state": causation,
        "promotion_state": promotion,
        "gate": "PASS",
    }


def validate_document(document: dict[str, Any]) -> dict[str, Any]:
    claims = document.get("claims")
    if not isinstance(claims, list) or not claims:
        raise CorroborationError("CLAIMS_REQUIRED", "document requires a non-empty claims array")
    receipts = [validate_claim(claim) for claim in claims]
    return {
        "artifact_type": "FR0333.ZERO.LION.CORROBORATION.RECEIPT",
        "gate_version": VERSION,
        "claim_count": len(receipts),
        "pass_count": len(receipts),
        "failure_count": 0,
        "receipts": receipts,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    aggregate: list[dict[str, Any]] = []
    try:
        for path in args.paths:
            aggregate.append(validate_document(json.loads(path.read_text(encoding="utf-8"))))
    except (CorroborationError, json.JSONDecodeError, OSError) as exc:
        print(json.dumps({"gate": "REJECT", "error": str(exc)}, indent=2))
        return 1
    output = {"gate": "PASS", "documents": aggregate}
    rendered = json.dumps(output, indent=2, sort_keys=True)
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
