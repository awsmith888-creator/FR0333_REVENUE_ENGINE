#!/usr/bin/env python3
import argparse
import json
import tempfile
from pathlib import Path

from adobe_purge_runtime import DATA_CLASSES, asset_paths, hard_purge

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = "FR0333_HARD_PURGE_RUNTIME_001"
SOURCE_MARKER = "FR0333_PRIVATE_SOURCE_MARKER_001"


def seed(root: Path, asset_key: str):
    paths = asset_paths(root, asset_key)
    for data_class, path in paths.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if data_class == "payload":
            path.write_bytes((SOURCE_MARKER + "::PAYLOAD").encode("utf-8"))
        else:
            path.write_text(
                json.dumps(
                    {
                        "source_marker": SOURCE_MARKER,
                        "asset_key": asset_key,
                        "data_class": data_class,
                    }
                ),
                encoding="utf-8",
            )
    return paths


def assert_source_absent(root: Path, asset_key: str):
    for path in root.rglob("*"):
        if path.is_file():
            data = path.read_bytes()
            assert SOURCE_MARKER.encode() not in data, f"source marker retained in {path}"
            assert asset_key.encode() not in data, f"source reference retained in {path}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--receipt",
        default=str(ROOT / "artifacts" / "fr0333_adobe_purge_runtime_receipt.json"),
    )
    args = parser.parse_args()

    checks = {}

    with tempfile.TemporaryDirectory(prefix="fr0333-purge-no-consent-") as tmp:
        root = Path(tmp)
        asset_key = "fixture-asset-no-consent"
        paths = seed(root, asset_key)
        assert all(path.exists() for path in paths.values())

        result = hard_purge(
            root,
            asset_key,
            consent_granted=False,
            audit_receipt_required=True,
        )
        assert result["state"] == "HARD_PURGE_COMPLETE"
        assert result["deleted_classes"] == sorted(DATA_CLASSES)
        assert result["feedback_allowed"] is False
        assert all(not path.exists() for path in paths.values())
        checks["PG_01_NO_CONSENT_TRIGGER"] = "PASS"
        checks["PG_02_PAYLOAD_DELETION"] = "PASS"
        checks["PG_03_DERIVED_TELEMETRY_DELETION"] = "PASS"
        checks["PG_07_FEEDBACK_BLOCK_AFTER_PURGE"] = "PASS"

        receipt_path = Path(result["receipt_path"])
        assert receipt_path.exists()
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        allowed_receipt_keys = {
            "event_id",
            "operation",
            "completed_utc",
            "payload_retained",
            "derived_retained",
            "telemetry_retained",
            "source_reference_retained",
            "source_hash_retained",
            "feedback_allowed",
        }
        assert set(receipt) == allowed_receipt_keys
        assert receipt["operation"] == "HARD_PURGE"
        assert receipt["payload_retained"] is False
        assert receipt["derived_retained"] is False
        assert receipt["telemetry_retained"] is False
        assert receipt["source_reference_retained"] is False
        assert receipt["source_hash_retained"] is False
        assert receipt["feedback_allowed"] is False
        assert_source_absent(root, asset_key)
        checks["PG_04_MINIMAL_RECEIPT"] = "PASS"

    with tempfile.TemporaryDirectory(prefix="fr0333-purge-consent-present-") as tmp:
        root = Path(tmp)
        asset_key = "fixture-asset-consent-present"
        paths = seed(root, asset_key)
        result = hard_purge(
            root,
            asset_key,
            consent_granted=True,
            audit_receipt_required=True,
        )
        assert result["state"] == "NO_PURGE_CONSENT_PRESENT"
        assert result["deleted_classes"] == []
        assert result["receipt_path"] is None
        assert result["feedback_allowed"] is True
        assert all(path.exists() for path in paths.values())
        checks["PG_05_CONSENT_PRESENT_NO_PURGE"] = "PASS"

    with tempfile.TemporaryDirectory(prefix="fr0333-purge-no-receipt-") as tmp:
        root = Path(tmp)
        asset_key = "fixture-asset-no-receipt"
        paths = seed(root, asset_key)
        result = hard_purge(
            root,
            asset_key,
            consent_granted=False,
            audit_receipt_required=False,
        )
        assert result["state"] == "HARD_PURGE_COMPLETE"
        assert result["receipt_path"] is None
        assert result["feedback_allowed"] is False
        assert all(not path.exists() for path in paths.values())
        assert not (root / "audit").exists()
        checks["PG_06_NO_RECEIPT_MODE"] = "PASS"

    expected = {
        "PG_01_NO_CONSENT_TRIGGER",
        "PG_02_PAYLOAD_DELETION",
        "PG_03_DERIVED_TELEMETRY_DELETION",
        "PG_04_MINIMAL_RECEIPT",
        "PG_05_CONSENT_PRESENT_NO_PURGE",
        "PG_06_NO_RECEIPT_MODE",
        "PG_07_FEEDBACK_BLOCK_AFTER_PURGE",
    }
    assert set(checks) == expected and all(v == "PASS" for v in checks.values())

    receipt_path = Path(args.receipt)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    ci_receipt = {
        "identifier": "FR0333.ADOBE.HARD_PURGE.RUNTIME.RECEIPT.001",
        "fixture": FIXTURE,
        "evidence_class": "E_MES",
        "checks": checks,
        "boundaries": {
            "purge_runtime_fixture": "VERIFIED_IN_CI",
            "deployed_storage_backend_integration": "UNVERIFIED",
            "external_provider_deletion": "UNVERIFIED",
            "production_retention_obligations": "UNVERIFIED",
            "feedback_after_purge": "BLOCKED_BY_RUNTIME",
        },
    }
    receipt_path.write_text(json.dumps(ci_receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("FR-0333 Adobe HARD_PURGE runtime validation PASS")
    print(f"fixture={FIXTURE}")
    print("no-consent payload/derived/telemetry deletion PASS")
    print("minimal non-source-derived receipt PASS")
    print("consent-present no-purge branch PASS")
    print("no-receipt retention branch PASS")
    print("post-purge feedback blocked PASS")
    print("DEPLOYED_STORAGE_BACKEND_INTEGRATION remains UNVERIFIED")


if __name__ == "__main__":
    main()
