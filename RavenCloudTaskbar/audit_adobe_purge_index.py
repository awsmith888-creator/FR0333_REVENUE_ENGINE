#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs" / "FR-0333-ADOBE-64BIT-REG.v1.0.5-RC.json"
INDEX_A = ROOT / "specs" / "FR-0333-ADOBE-64BIT-INDEX.A.v1.0.5-RC.json"
INDEX_B = ROOT / "specs" / "FR-0333-ADOBE-64BIT-INDEX.B.v1.0.5-RC.json"
INDEX_C = ROOT / "specs" / "FR-0333-ADOBE-64BIT-INDEX.C.v1.0.5-RC.json"
INDEX_D = ROOT / "specs" / "FR-0333-ADOBE-64BIT-INDEX.D.v1.0.5-RC.json"

REQUIRED = {
    "PG_01_NO_CONSENT_TRIGGER",
    "PG_02_PAYLOAD_DELETION",
    "PG_03_DERIVED_TELEMETRY_DELETION",
    "PG_04_MINIMAL_RECEIPT",
    "PG_05_CONSENT_PRESENT_NO_PURGE",
    "PG_06_NO_RECEIPT_MODE",
    "PG_07_FEEDBACK_BLOCK_AFTER_PURGE",
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    spec = load(SPEC)
    indexes = [load(INDEX_A), load(INDEX_B), load(INDEX_C)]
    d = load(INDEX_D)

    assert d["identifier"] == "FR-0333-ADOBE-64BIT-INDEX.D"
    assert d["role"] == "PURGE_LIFECYCLE_EVIDENCE_INDEX"
    assert d["source_spec"] == spec["specification_metadata"]["identifier"]
    assert d["version"] == spec["specification_metadata"]["architecture_version"]
    assert d["cross_audits"] == [x["identifier"] for x in indexes]

    bits = {
        bit_id: bit
        for cluster in spec["register_schema"].values()
        for bit_id, bit in cluster.items()
    }
    assert len(bits) == 64
    allowed_evidence = set(spec["schema_definitions"]["evidence_class"])

    ids = []
    for check in d["checks"]:
        ids.append(check["check_id"])
        assert check["description"].strip()
        assert check["evidence_class"] in allowed_evidence
        assert check["observes_bits"]
        for bit_id in check["observes_bits"]:
            assert bit_id in bits, f"unknown bit {bit_id}"

    assert len(ids) == len(set(ids))
    assert set(ids) == REQUIRED

    purge_bits = {"BIT_62", "BIT_63", "BIT_64"}
    observed = {bit_id for check in d["checks"] for bit_id in check["observes_bits"]}
    assert purge_bits.issubset(observed)
    assert bits["BIT_62"]["zero_lion_gate"] == "HARD_PURGE"
    assert bits["BIT_63"]["zero_lion_gate"] == "HARD_PURGE"
    assert bits["BIT_64"]["applicability"] == "BIT_62 == 1 && BIT_63 == 1"

    required_boundaries = {
        "PURGE_RUNTIME_CI_PASS != DEPLOYED_STORAGE_BACKEND_INTEGRATION",
        "MINIMAL_AUDIT_RECEIPT != SOURCE_RETENTION",
        "CONSENT_ABSENT != AUTHORIZATION_GRANTED",
        "BIT_62_HARD_PURGE != BIT_64_FEEDBACK_PERMISSION",
    }
    assert required_boundaries.issubset(set(d["evidence_boundaries"]))

    print("FR-0333 Adobe 64-bit INDEX.D purge cross-audit PASS")
    print(f"purge_checks={len(ids)}")
    print("INDEX.D -> INDEX.C -> INDEX.A/B -> REGISTER agreement PASS")
    print("BIT_62/BIT_63 HARD_PURGE semantics PASS")
    print("BIT_64 post-purge feedback boundary PASS")


if __name__ == "__main__":
    main()
