#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs" / "FR-0333-ADOBE-64BIT-REG.v1.0.5-RC.json"
INDEX_A = ROOT / "specs" / "FR-0333-ADOBE-64BIT-INDEX.A.v1.0.5-RC.json"
INDEX_B = ROOT / "specs" / "FR-0333-ADOBE-64BIT-INDEX.B.v1.0.5-RC.json"
INDEX_C = ROOT / "specs" / "FR-0333-ADOBE-64BIT-INDEX.C.v1.0.5-RC.json"

REQUIRED_RUNTIME_CHECKS = {
    "RT_01_TOOL_PIN",
    "RT_02_SIGN_ROUNDTRIP",
    "RT_03_ASSERTION_ROUNDTRIP",
    "RT_04_CERT_EXTRACTION",
    "RT_05_HASH_RECEIPT",
    "RT_06_TAMPER_NEGATIVE",
    "RT_07_RECEIPT_BOUNDARY",
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def iter_bits(spec):
    for cluster_name, cluster in spec["register_schema"].items():
        for bit_name, bit in cluster.items():
            yield cluster_name, bit_name, bit


def main():
    spec = load(SPEC)
    a = load(INDEX_A)
    b = load(INDEX_B)
    c = load(INDEX_C)

    assert c["identifier"] == "FR-0333-ADOBE-64BIT-INDEX.C"
    assert c["role"] == "RUNTIME_EVIDENCE_INDEX"
    assert c["source_spec"] == spec["specification_metadata"]["identifier"]
    assert c["version"] == spec["specification_metadata"]["architecture_version"]
    assert c["cross_audits"] == [a["identifier"], b["identifier"]]

    bit_map = {}
    cluster_by_bit = {}
    for cluster_name, bit_name, bit in iter_bits(spec):
        assert bit_name not in bit_map
        bit_map[bit_name] = bit
        cluster_by_bit[bit_name] = cluster_name
    assert len(bit_map) == 64

    a_cluster_for_bit = {}
    for cluster_name, row in a["clusters"].items():
        for number in range(row["start"], row["end"] + 1):
            bit_name = f"BIT_{number:02d}"
            assert bit_name not in a_cluster_for_bit
            a_cluster_for_bit[bit_name] = cluster_name

    b_cluster_for_bit = {}
    for row in b["ranges"]:
        for number in range(row["start"], row["end"] + 1):
            bit_name = f"BIT_{number:02d}"
            assert bit_name not in b_cluster_for_bit
            b_cluster_for_bit[bit_name] = row["cluster"]

    assert set(a_cluster_for_bit) == set(bit_map)
    assert set(b_cluster_for_bit) == set(bit_map)
    assert a_cluster_for_bit == b_cluster_for_bit

    allowed_evidence = set(spec["schema_definitions"]["evidence_class"])
    check_ids = []
    observed_union = set()
    for check in c["checks"]:
        check_id = check["check_id"]
        check_ids.append(check_id)
        assert check["description"].strip()
        assert check["evidence_class"] in allowed_evidence
        assert check["observes_bits"], f"{check_id} must observe at least one bit"
        for bit_name in check["observes_bits"]:
            assert bit_name in bit_map, f"{check_id}: unknown bit {bit_name}"
            assert cluster_by_bit[bit_name] == a_cluster_for_bit[bit_name]
            assert cluster_by_bit[bit_name] == b_cluster_for_bit[bit_name]
            observed_union.add(bit_name)

    assert len(check_ids) == len(set(check_ids)), "runtime check IDs must be unique"
    assert set(check_ids) == REQUIRED_RUNTIME_CHECKS, (
        f"runtime check set mismatch: expected={sorted(REQUIRED_RUNTIME_CHECKS)} "
        f"actual={sorted(check_ids)}"
    )

    required_negative_bits = {"BIT_10", "BIT_16", "BIT_37", "BIT_44", "BIT_58"}
    tamper = next(x for x in c["checks"] if x["check_id"] == "RT_06_TAMPER_NEGATIVE")
    assert required_negative_bits.issubset(set(tamper["observes_bits"]))

    required_boundary_phrases = {
        "C2PA_TEST_SIGNER_RUNTIME != ADOBE_PRODUCTION_SIGNER_RUNTIME",
        "STRUCTURAL_SIGNATURE_VALIDATION != HUMAN_IDENTITY",
        "TEST_CERTIFICATE != PRODUCTION_TRUST",
        "C2PA_RUNTIME_CI_PASS != DEPLOYMENT",
    }
    assert required_boundary_phrases.issubset(set(c["evidence_boundaries"]))

    pin = c["tool_pin"]
    assert pin["name"] == "c2patool"
    assert pin["version"]
    assert pin["release_tag"] == f"c2patool-v{pin['version']}"
    assert pin["linux_x86_64_url"].endswith(
        f"/{pin['release_tag']}/{pin['release_tag']}-x86_64-unknown-linux-gnu.tar.gz"
    )
    digest = pin["linux_x86_64_sha256"]
    assert len(digest) == 64 and all(ch in "0123456789abcdef" for ch in digest)

    print("FR-0333 Adobe 64-bit INDEX.C cross-audit PASS")
    print(f"runtime_checks={len(check_ids)}")
    print(f"runtime_observed_bits={len(observed_union)}")
    print("INDEX.C -> INDEX.A -> INDEX.B -> REGISTER agreement PASS")
    print("test-signer / production-signer boundary PASS")


if __name__ == "__main__":
    main()
