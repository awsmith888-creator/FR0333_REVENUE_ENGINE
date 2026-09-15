#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "fr0333_migration_receipt_0001.json"

EXPECTED_ADDITIONS = {
    "DRAFT.PUBLICLY.RELEASED",
    "FINAL.STATUTORY.LANGUAGE",
    "FR0333.INDEPENDENT.GOOGLE.INDEX.HIT",
    "GOOGLE.DERIVED.FR0333.FROM.PUBLIC.WEB",
    "INCUMBENT.GATE.ACTUALLY.CREATED",
    "SAFETY.COORDINATION.ANTICOMPETITIVE.USE",
    "SOURCE.RECEIPT.DRAFT.PUBLICLY.RELEASED",
    "TERAFAB.REGULATORY.CAUSAL.CONNECTION",
}

REQUIRED_U21_HOLDS = {
    "FINAL.STATUTORY.LANGUAGE",
    "FR0333.INDEPENDENT.GOOGLE.INDEX.HIT",
    "GOOGLE.DERIVED.FR0333.FROM.PUBLIC.WEB",
    "INCUMBENT.GATE.ACTUALLY.CREATED",
    "SAFETY.COORDINATION.ANTICOMPETITIVE.USE",
    "TERAFAB.REGULATORY.CAUSAL.CONNECTION",
}


def canonical_sha256(payload):
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256_" + hashlib.sha256(encoded).hexdigest()


def main():
    data = json.loads(RECEIPT.read_text(encoding="utf-8"))
    e6 = data["e6_baseline"]
    e12 = data["e12_candidate"]
    compiler = data["compiler_payload"]
    status = data["status"]

    source_receipt = dict(e12["SOURCE.RECEIPT.DRAFT.PUBLICLY.RELEASED"])
    stored_source_hash = source_receipt.pop("payload_hash")

    assert canonical_sha256(e6) == compiler["e6_state_hash"]
    assert canonical_sha256(e12) == compiler["e12_state_hash"]
    assert canonical_sha256(source_receipt) == stored_source_hash
    assert stored_source_hash == compiler["source_receipt_hash"]
    assert canonical_sha256(compiler) == data["compiler_payload_hash"]

    shared = set(e6) & set(e12)
    additions = set(e12) - set(e6)
    removals = set(e6) - set(e12)
    modifications = {key for key in shared if e6[key] != e12[key]}

    assert len(e6) == 8
    assert additions == EXPECTED_ADDITIONS
    assert len(additions) == 8
    assert not removals
    assert not modifications

    assert compiler["regression_status"] == "VERIFIED_ZERO_LEAKAGE"
    assert compiler["humanlock"] == "ACTIVE"
    assert compiler["canonical_promotion"] == "HOLD.PENDING.HUMAN.MERGE"
    assert compiler["causality_boundary"] == "OBSERVED != CORRELATED != CAUSAL"

    for key in REQUIRED_U21_HOLDS:
        assert e12[key] == "U.21", f"{key} must remain U.21"

    assert status["verified_structural_delta"] == "T.20"
    assert status["e6_e12_zero_leakage"] == "T.20"
    assert status["delta_count"] == 8
    assert status["delta_additions"] == 8
    assert status["delta_removals"] == 0
    assert status["shared_field_modifications"] == 0
    assert status["external_claim_promotion"] == "HOLD"
    assert status["canonical_promotion"] == "HOLD.PENDING.HUMAN.MERGE"
    assert status["humanlock"] == "ACTIVE"

    print(
        "PASS "
        "structural_delta=T.20 "
        "zero_leakage=T.20 "
        f"additions={len(additions)} "
        f"removals={len(removals)} "
        f"shared_modifications={len(modifications)} "
        "external_claim_promotion=HOLD "
        "humanlock=ACTIVE"
    )


if __name__ == "__main__":
    main()
