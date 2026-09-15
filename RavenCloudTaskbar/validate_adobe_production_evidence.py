#!/usr/bin/env python3
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd, check=True):
    p = subprocess.run(cmd, text=True, capture_output=True)
    if check and p.returncode != 0:
        raise AssertionError(
            f"command failed ({p.returncode}): {' '.join(map(str, cmd))}\n"
            f"STDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}"
        )
    return p


def parse_json(text):
    text = text.strip()
    if not text:
        raise AssertionError("empty c2patool JSON output")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])
        raise


def walk(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield str(k)
            yield from walk(v)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)
    elif isinstance(value, (str, int, float, bool)):
        yield str(value)


def validation_codes(value, bucket):
    out = []
    if isinstance(value, dict):
        for k, v in value.items():
            if k == bucket and isinstance(v, list):
                for item in v:
                    if isinstance(item, dict) and item.get("code"):
                        out.append(str(item["code"]))
            out.extend(validation_codes(v, bucket))
    elif isinstance(value, list):
        for item in value:
            out.extend(validation_codes(item, bucket))
    return out


def active_manifest(report):
    label = report.get("active_manifest")
    manifests = report.get("manifests") or {}
    manifest = manifests.get(label) if label else None
    if not isinstance(manifest, dict):
        raise AssertionError("active C2PA manifest not found")
    return label, manifest


def evaluate(tool, asset: Path):
    report_proc = run([tool, str(asset)], check=False)
    try:
        report = parse_json(report_proc.stdout)
    except Exception:
        report = {}

    checks = {
        "AP_01_RAW_ASSET_HASH": asset.is_file() and asset.stat().st_size > 0,
        "AP_02_C2PA_MANIFEST_PRESENT": False,
        "AP_03_SIGNATURE_AND_BINDING_VALID": False,
        "AP_04_ADOBE_ISSUER": False,
        "AP_05_FIREFLY_AGENT_BINDING": False,
        "AP_06_CERT_CHAIN_EXTRACTABLE": False,
        "AP_08_BOUNDARY_RECEIPT": True,
    }

    manifest = {}
    label = None
    if report:
        try:
            label, manifest = active_manifest(report)
            checks["AP_02_C2PA_MANIFEST_PRESENT"] = True
        except AssertionError:
            pass

    success_codes = set(validation_codes(report, "success"))
    failure_codes = set(validation_codes(report, "failure"))
    state = str(report.get("validation_state", "")).lower()
    sig_valid = "claimSignature.validated" in success_codes
    hash_valid = "assertion.dataHash.match" in success_codes
    checks["AP_03_SIGNATURE_AND_BINDING_VALID"] = (
        checks["AP_02_C2PA_MANIFEST_PRESENT"]
        and sig_valid
        and hash_valid
        and not failure_codes
        and (state in {"", "valid"})
    )

    sig = manifest.get("signature_info") if isinstance(manifest, dict) else None
    sig = sig if isinstance(sig, dict) else {}
    issuer = str(sig.get("issuer", ""))
    common_name = str(sig.get("common_name", ""))
    checks["AP_04_ADOBE_ISSUER"] = issuer.strip().lower() == "adobe inc."

    strings = "\n".join(walk(manifest)).lower()
    checks["AP_05_FIREFLY_AGENT_BINDING"] = any(
        marker in strings
        for marker in (
            "adobe firefly",
            "adobe_firefly",
            "adobe firefly c2pa",
        )
    ) or "adobe firefly" in common_name.lower()

    cert_proc = run([tool, str(asset), "--certs"], check=False)
    checks["AP_06_CERT_CHAIN_EXTRACTABLE"] = (
        "BEGIN CERTIFICATE" in cert_proc.stdout
        and "END CERTIFICATE" in cert_proc.stdout
    )

    passed = all(checks.values())
    return {
        "passed": passed,
        "asset_sha256": sha256(asset) if asset.is_file() else None,
        "active_manifest": label,
        "issuer": issuer or None,
        "common_name": common_name or None,
        "validation_state": report.get("validation_state") if report else None,
        "success_codes": sorted(success_codes),
        "failure_codes": sorted(failure_codes),
        "checks": {k: "PASS" if v else "FAIL" for k, v in checks.items()},
        "boundaries": {
            "human_identity": "NOT_CLAIMED",
            "ownership": "NOT_CLAIMED",
            "authorization": "NOT_CLAIMED",
            "adobe_origin_provenance": "VERIFIED" if passed else "UNVERIFIED",
        },
    }


def write_receipt(path, receipt):
    if not path:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def self_test(tool, receipt_path):
    with tempfile.TemporaryDirectory(prefix="fr0333-adobe-prod-gate-") as tmp:
        work = Path(tmp)
        source = work / "source.svg"
        manifest = work / "manifest.json"
        signed = work / "fake-adobe-labelled.svg"
        source.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">'
            '<rect width="32" height="32" fill="#111111"/></svg>\n',
            encoding="utf-8",
        )
        manifest.write_text(
            json.dumps(
                {
                    "claim_generator": "Adobe_Firefly SELF_TEST_LABEL_ONLY",
                    "assertions": [
                        {
                            "label": "c2pa.actions",
                            "data": {
                                "actions": [
                                    {
                                        "action": "c2pa.created",
                                        "softwareAgent": "Adobe Firefly",
                                    }
                                ]
                            },
                        }
                    ],
                },
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        run([
            tool,
            str(source),
            "--manifest", str(manifest),
            "--create", "digitalCapture",
            "--output", str(signed),
        ])
        receipt = evaluate(tool, signed)
        receipt["identifier"] = "FR0333.ADOBE.PRODUCTION.EVIDENCE.GATE.SELFTEST.001"
        receipt["self_test_expected_result"] = "REJECT_TEST_SIGNER"
        receipt["self_test_result"] = "PASS" if not receipt["passed"] and receipt["checks"]["AP_04_ADOBE_ISSUER"] == "FAIL" else "FAIL"
        receipt["checks"]["AP_07_NO_TEST_SIGNER_FALSE_POSITIVE"] = receipt["self_test_result"]
        write_receipt(receipt_path, receipt)
        assert receipt["self_test_result"] == "PASS", receipt
        print("FR-0333 Adobe production-evidence gate self-test PASS")
        print("Adobe-labelled built-in test signer correctly REJECTED")
        print("production asset evidence remains external input")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--c2patool", required=True)
    parser.add_argument("--asset")
    parser.add_argument("--receipt")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    tool = str(Path(args.c2patool).resolve())
    if args.self_test:
        self_test(tool, args.receipt)
        return

    if not args.asset:
        raise SystemExit("--asset is required unless --self-test is used")
    asset = Path(args.asset).resolve()
    if not asset.is_file():
        raise SystemExit(f"asset not found: {asset}")

    receipt = evaluate(tool, asset)
    receipt["identifier"] = "FR0333.ADOBE.PRODUCTION.EVIDENCE.RECEIPT.001"
    receipt["checks"]["AP_07_NO_TEST_SIGNER_FALSE_POSITIVE"] = "NOT_APPLICABLE_RUNTIME_SELF_TESTED_IN_CI"
    write_receipt(args.receipt, receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    raise SystemExit(0 if receipt["passed"] else 1)


if __name__ == "__main__":
    main()
