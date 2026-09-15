#!/usr/bin/env python3
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_C = ROOT / "specs" / "FR-0333-ADOBE-64BIT-INDEX.C.v1.0.5-RC.json"

FIXTURE_MARKER = "FR0333_C2PA_RUNTIME_001"
SOURCE_SENTINEL = 'fill="#111111"'
TAMPER_SENTINEL = 'fill="#222222"'


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd, *, check=True):
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if check and proc.returncode != 0:
        raise AssertionError(
            f"command failed ({proc.returncode}): {' '.join(map(str, cmd))}\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return proc


def parse_json_output(text: str):
    text = text.strip()
    if not text:
        raise AssertionError("expected JSON output, received empty output")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def walk_strings(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield str(k)
            yield from walk_strings(v)
    elif isinstance(value, list):
        for item in value:
            yield from walk_strings(item)
    elif isinstance(value, (str, int, float, bool)):
        yield str(value)


def contains_string(value, needle: str) -> bool:
    needle = needle.lower()
    return any(needle in s.lower() for s in walk_strings(value))


def mismatch_strings(value):
    return sorted({s for s in walk_strings(value) if "mismatch" in s.lower()})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--c2patool", required=True)
    parser.add_argument(
        "--receipt",
        default=str(ROOT / "artifacts" / "fr0333_adobe_c2pa_runtime_receipt.json"),
    )
    args = parser.parse_args()

    index_c = json.loads(INDEX_C.read_text(encoding="utf-8"))
    expected_version = index_c["tool_pin"]["version"]
    expected_fixture = index_c["runtime_fixture"]
    assert expected_fixture == FIXTURE_MARKER

    tool = str(Path(args.c2patool).resolve())
    version = run([tool, "--version"]).stdout.strip()
    assert expected_version in version, (
        f"c2patool version mismatch: expected {expected_version}, got {version}"
    )

    with tempfile.TemporaryDirectory(prefix="fr0333-c2pa-runtime-") as tmp:
        work = Path(tmp)
        source = work / "source.svg"
        manifest = work / "manifest.json"
        signed = work / "signed.svg"
        tampered = work / "tampered.svg"

        source.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">'
            f'<rect id="{FIXTURE_MARKER}" width="64" height="64" {SOURCE_SENTINEL}/>'
            "</svg>\n",
            encoding="utf-8",
        )

        manifest.write_text(
            json.dumps(
                {
                    "claim_generator_info": [
                        {
                            "name": "FR-0333 C2PA Runtime Fixture",
                            "version": "1.0.5-RC",
                        }
                    ],
                    "assertions": [
                        {
                            "label": "org.fr0333.runtime",
                            "data": {
                                "fixture": FIXTURE_MARKER,
                                "purpose": "CI_RUNTIME_VALIDATION",
                                "production_credential_claim": "PROHIBITED",
                            },
                        }
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        source_hash = sha256(source)

        sign_proc = run(
            [
                tool,
                str(source),
                "--manifest",
                str(manifest),
                "--create",
                "digitalCapture",
                "--output",
                str(signed),
            ]
        )
        assert signed.exists() and signed.stat().st_size > source.stat().st_size
        signed_hash = sha256(signed)
        assert signed_hash != source_hash

        sign_json = parse_json_output(sign_proc.stdout)
        read_proc = run([tool, str(signed)])
        read_json = parse_json_output(read_proc.stdout)

        assert contains_string(sign_json, FIXTURE_MARKER)
        assert contains_string(read_json, FIXTURE_MARKER)
        assert contains_string(read_json, "org.fr0333.runtime")
        assert contains_string(read_json, "c2pa.created")

        signed_mismatches = mismatch_strings(read_json)
        assert not signed_mismatches, (
            f"freshly signed fixture must not report mismatch statuses: {signed_mismatches}"
        )

        cert_proc = run([tool, str(signed), "--certs"])
        assert "BEGIN CERTIFICATE" in cert_proc.stdout
        assert "END CERTIFICATE" in cert_proc.stdout

        signed_bytes = signed.read_bytes()
        source_token = SOURCE_SENTINEL.encode("utf-8")
        tamper_token = TAMPER_SENTINEL.encode("utf-8")
        assert len(source_token) == len(tamper_token)
        assert source_token in signed_bytes, "source sentinel not found in signed SVG"
        tampered_bytes = signed_bytes.replace(source_token, tamper_token, 1)
        assert tampered_bytes != signed_bytes
        tampered.write_bytes(tampered_bytes)
        tampered_hash = sha256(tampered)
        assert tampered_hash != signed_hash

        tamper_proc = run([tool, str(tampered)], check=False)
        combined_tamper_output = (tamper_proc.stdout + "\n" + tamper_proc.stderr).strip()
        try:
            tamper_json = parse_json_output(tamper_proc.stdout)
            tamper_mismatches = mismatch_strings(tamper_json)
        except Exception:
            tamper_json = None
            tamper_mismatches = sorted(
                {
                    token
                    for token in combined_tamper_output.replace("\n", " ").split()
                    if "mismatch" in token.lower()
                }
            )

        assert tamper_mismatches or "mismatch" in combined_tamper_output.lower(), (
            "post-signing byte mutation was not detected as a mismatch"
        )

        receipt_path = Path(args.receipt)
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt = {
            "identifier": "FR0333.ADOBE.C2PA.RUNTIME.RECEIPT.001",
            "fixture": FIXTURE_MARKER,
            "evidence_class": "E_MES",
            "tool": {
                "name": index_c["tool_pin"]["name"],
                "version_observed": version,
                "version_expected": expected_version,
                "release_tag": index_c["tool_pin"]["release_tag"],
                "release_archive_sha256": index_c["tool_pin"]["linux_x86_64_sha256"],
                "signer_mode": "C2PATOOL_BUILT_IN_TEST_SIGNER",
            },
            "hashes": {
                "source_sha256": source_hash,
                "signed_sha256": signed_hash,
                "tampered_sha256": tampered_hash,
            },
            "checks": {
                "RT_01_TOOL_PIN": "PASS",
                "RT_02_SIGN_ROUNDTRIP": "PASS",
                "RT_03_ASSERTION_ROUNDTRIP": "PASS",
                "RT_04_CERT_EXTRACTION": "PASS",
                "RT_05_HASH_RECEIPT": "PASS",
                "RT_06_TAMPER_NEGATIVE": "PASS",
                "RT_07_RECEIPT_BOUNDARY": "PASS",
            },
            "tamper_mismatch_signals": tamper_mismatches,
            "boundaries": {
                "c2pa_test_signer_runtime": "VERIFIED_IN_CI",
                "adobe_production_signer_runtime": "UNVERIFIED",
                "production_trust_chain": "UNVERIFIED",
                "human_identity": "NOT_CLAIMED",
                "deployment": "NOT_CLAIMED",
                "purge_lifecycle": "UNVERIFIED",
            },
        }
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    print("FR-0333 Adobe/C2PA runtime validation PASS")
    print(f"fixture={FIXTURE_MARKER}")
    print(f"c2patool={version}")
    print("sign/read/assertion/certificate/hash/tamper gates PASS")
    print("ADOBE_PRODUCTION_SIGNER_RUNTIME remains UNVERIFIED")
    print("PURGE_LIFECYCLE remains UNVERIFIED")


if __name__ == "__main__":
    main()
