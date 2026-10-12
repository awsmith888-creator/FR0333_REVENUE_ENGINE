#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs" / "FR-0333-ADOBE-64BIT-REG.v1.0.5-RC.json"
INDEX_E = ROOT / "specs" / "FR-0333-ADOBE-64BIT-INDEX.E.v1.0.5-RC.json"

REQUIRED = {
    "AP_01_RAW_ASSET_HASH",
    "AP_02_C2PA_MANIFEST_PRESENT",
    "AP_03_SIGNATURE_AND_BINDING_VALID",
    "AP_04_ADOBE_ISSUER",
    "AP_05_FIREFLY_AGENT_BINDING",
    "AP_06_CERT_CHAIN_EXTRACTABLE",
    "AP_07_NO_TEST_SIGNER_FALSE_POSITIVE",
    "AP_08_BOUNDARY_RECEIPT",
}


def main():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    index = json.loads(INDEX_E.read_text(encoding="utf-8"))
    bits = {
        bit_id: bit
        for cluster in spec["register_schema"].values()
        for bit_id, bit in cluster.items()
    }
    assert len(bits) == 64
    assert index["identifier"] == "FR-0333-ADOBE-64BIT-INDEX.E"
    assert index["role"] == "ADOBE_PRODUCTION_EVIDENCE_GATE"
    assert index["source_spec"] == spec["specification_metadata"]["identifier"]
    assert index["version"] == spec["specification_metadata"]["architecture_version"]
    assert index["required_external_input"] == "RAW_ADOBE_EXPORTED_ASSET_WITH_EMBEDDED_C2PA"
    assert "DO_NOT_COMMIT" in index["public_repo_secret_policy"]

    allowed = set(spec["schema_definitions"]["evidence_class"])
    ids = []
    observed = set()
    for check in index["checks"]:
        ids.append(check["check_id"])
        assert check["description"].strip()
        assert check["evidence_class"] in allowed
        assert check["observes_bits"]
        for bit_id in check["observes_bits"]:
            assert bit_id in bits, f"unknown bit {bit_id}"
            observed.add(bit_id)

    assert len(ids) == len(set(ids))
    assert set(ids) == REQUIRED
    assert {"BIT_11", "BIT_12", "BIT_13", "BIT_14", "BIT_25", "BIT_26", "BIT_27", "BIT_28", "BIT_37", "BIT_41", "BIT_42"}.issubset(observed)

    required_boundaries = {
        "ADOBE_SOFTWARE_AGENT_DECLARATION != ADOBE_SIGNER_VERIFICATION",
        "ISSUER_ADOBE_INC_PLUS_VALID_C2PA != HUMAN_IDENTITY",
        "PRODUCTION_SIGNER_EVIDENCE != AUTHORIZATION",
        "SELF_TEST_PASS != PRODUCTION_ASSET_PASS",
    }
    assert required_boundaries.issubset(set(index["evidence_boundaries"]))

    print("FR-0333 Adobe 64-bit INDEX.E production-evidence audit PASS")
    print(f"production_gate_checks={len(ids)}")
    print("test signer cannot satisfy Adobe issuer gate by declaration alone")
    print("production asset remains an external evidence input")


if __name__ == "__main__":
    main()
