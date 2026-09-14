#!/usr/bin/env python3
"""Fail-closed validator for FR0333.CLOTILDA.ANSON.DNA.SEPARATION.0001."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

EXPECTED_ID = "FR0333.CLOTILDA.ANSON.DNA.SEPARATION.0001"
ALLOWED_STATES = {"T.20", "U.21", "F.6"}
REQUIRED_INVARIANTS = {
    "ANSON_STREET_DNA != CLOTILDA_DNA",
    "SAMPLE_COLLECTION != DNA_RECOVERY",
    "NO_PUBLIC_RESULT_LOCATED != NEGATIVE_LAB_RESULT",
    "INDEXED_TEXT_MATCH != EDITORIAL_PROVENANCE",
    "CONVICT_LEASING != DEBT_PEONAGE",
    "REPOSITORY_REGISTRATION != CANONICAL_PROMOTION",
}


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if data.get("id") != EXPECTED_ID:
        errors.append("record id mismatch")
    if data.get("golden_chain_position") != "GC.SB.0031":
        errors.append("golden chain position mismatch")
    if data.get("golden_chain_predecessor") != "GC.SB.0030":
        errors.append("predecessor mismatch")
    if data.get("humanlock") is not True:
        errors.append("HumanLock must remain active")
    if data.get("canonical_promotion") != "U.21.HOLD":
        errors.append("canonical promotion must remain HOLD")

    claims = data.get("claims")
    sources = data.get("sources")
    if not isinstance(claims, list) or len(claims) != 18:
        errors.append("exactly 18 claim records are required")
        claims = []
    if not isinstance(sources, list) or len(sources) < 9:
        errors.append("at least nine source records are required")
        sources = []

    source_ids = {item.get("id") for item in sources if isinstance(item, dict)}
    if None in source_ids or len(source_ids) != len(sources):
        errors.append("source ids must be present and unique")

    claim_ids: set[str] = set()
    claim_by_id: dict[str, dict[str, Any]] = {}
    for claim in claims:
        if not isinstance(claim, dict):
            errors.append("every claim must be an object")
            continue
        claim_id = claim.get("id")
        if not isinstance(claim_id, str) or claim_id in claim_ids:
            errors.append("claim ids must be present and unique")
            continue
        claim_ids.add(claim_id)
        claim_by_id[claim_id] = claim
        if claim.get("state") not in ALLOWED_STATES:
            errors.append(f"{claim_id}: invalid state")
        if not claim.get("proposition") or not claim.get("evidence_class"):
            errors.append(f"{claim_id}: proposition and evidence class required")
        if not claim.get("pinpoint"):
            errors.append(f"{claim_id}: pinpoint required")
        refs = claim.get("sources")
        if not isinstance(refs, list) or not refs:
            errors.append(f"{claim_id}: at least one source required")
        elif any(ref not in source_ids for ref in refs):
            errors.append(f"{claim_id}: unresolved source reference")

    for required in {f"C.{index:02d}" for index in range(1, 19)} - claim_ids:
        errors.append(f"missing claim {required}")

    expected_states = {
        "C.01": "T.20",
        "C.02": "T.20",
        "C.03": "T.20",
        "C.04": "T.20",
        "C.06": "U.21",
        "C.08": "T.20",
        "C.10": "U.21",
        "C.11": "U.21",
        "C.13": "U.21",
        "C.14": "U.21",
        "C.17": "F.6",
        "C.18": "U.21",
    }
    for claim_id, state in expected_states.items():
        if claim_by_id.get(claim_id, {}).get("state") != state:
            errors.append(f"{claim_id}: state must remain {state}")

    grammar = data.get("state_grammar", {})
    if grammar.get("prohibition") != "ABSENCE_OF_PUBLICATION_MUST_NOT_BE_PROMOTED_TO_F.6":
        errors.append("absence/publication prohibition missing")

    boundary = data.get("search_boundary", {})
    if boundary.get("result_scope") != "BOUNDED_PUBLIC_SEARCH.NOT_COMPLETE_WEB_OR_PRIVATE_LAB_CENSUS":
        errors.append("bounded-search scope missing")
    required_promotion = boundary.get("promotion_requirement_for_C10", [])
    if len(required_promotion) != 5:
        errors.append("C.10 promotion requires five evidence elements")

    invariants = set(data.get("hard_invariants", []))
    missing = REQUIRED_INVARIANTS - invariants
    if missing:
        errors.append("missing invariants: " + ", ".join(sorted(missing)))

    policy = data.get("correction_policy", {})
    if policy.get("mode") != "APPEND_ONLY" or policy.get("overwrite_prior_observation") is not False:
        errors.append("append-only correction policy violated")

    return errors


def main() -> int:
    target = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path(__file__).with_name("fr0333_clotilda_anson_dna_separation_0001.json")
    )
    data = json.loads(target.read_text(encoding="utf-8"))
    errors = validate(data)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: 13/13 evidence gates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
