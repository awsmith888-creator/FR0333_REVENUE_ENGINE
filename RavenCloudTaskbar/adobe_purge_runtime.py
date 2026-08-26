#!/usr/bin/env python3
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

DATA_CLASSES = ("payload", "derived", "telemetry")


def asset_paths(root: Path, asset_key: str):
    root = Path(root)
    return {
        "payload": root / "payload" / f"{asset_key}.bin",
        "derived": root / "derived" / f"{asset_key}.json",
        "telemetry": root / "telemetry" / f"{asset_key}.json",
    }


def hard_purge(
    root: Path,
    asset_key: str,
    *,
    consent_granted: bool,
    audit_receipt_required: bool,
):
    root = Path(root)
    paths = asset_paths(root, asset_key)

    if consent_granted:
        return {
            "state": "NO_PURGE_CONSENT_PRESENT",
            "deleted_classes": [],
            "receipt_path": None,
            "feedback_allowed": True,
        }

    deleted = []
    for data_class, path in paths.items():
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            deleted.append(data_class)

    receipt_path = None
    if audit_receipt_required:
        audit_dir = root / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        receipt_path = audit_dir / f"purge-{uuid.uuid4()}.json"
        receipt = {
            "event_id": str(uuid.uuid4()),
            "operation": "HARD_PURGE",
            "completed_utc": datetime.now(timezone.utc).isoformat(),
            "payload_retained": False,
            "derived_retained": False,
            "telemetry_retained": False,
            "source_reference_retained": False,
            "source_hash_retained": False,
            "feedback_allowed": False,
        }
        receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")

    return {
        "state": "HARD_PURGE_COMPLETE",
        "deleted_classes": sorted(deleted),
        "receipt_path": str(receipt_path) if receipt_path else None,
        "feedback_allowed": False,
    }
