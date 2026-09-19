#!/usr/bin/env python3
"""Fail-closed validator for the FR-0333 Adobe/package certificate audit."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

DEFAULT_MANIFEST = Path("RavenCloudTaskbar/fr0333_adobe_package_certificate_audit_0001.json")


class AuditError(RuntimeError):
    pass


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"invalid or unavailable JSON: {path}: {exc}") from exc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def validate(root: Path, manifest_path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    root = root.resolve()
    manifest_file = manifest_path if manifest_path.is_absolute() else root / manifest_path
    manifest = load_json(manifest_file)

    require(manifest.get("mode") == "APPEND_ONLY_BRANCH_REVIEW", "audit mode must remain append-only")
    require(manifest.get("humanlock", {}).get("required") is True, "HumanLock must remain required")
    for field in ("automatic_merge", "automatic_deployment", "automatic_promotion"):
        require(manifest["humanlock"].get(field) is False, f"{field} must remain false")

    checked: list[str] = []
    for artifact in manifest.get("artifacts", []):
        rel = artifact.get("path")
        expected = artifact.get("git_blob_sha")
        require(isinstance(rel, str) and rel, "artifact path missing")
        require(isinstance(expected, str) and len(expected) == 40, f"invalid blob SHA for {rel}")
        path = root / rel
        require(path.is_file(), f"required artifact missing: {rel}")
        data = path.read_bytes()
        actual = git_blob_sha(data)
        require(actual == expected, f"artifact drift: {rel}: expected {expected}, got {actual}")
        if path.suffix == ".json":
            load_json(path)
        checked.append(rel)

    portable = manifest.get("portable_receipt", {})
    payload_rel = portable.get("payload_path")
    require(portable.get("source_class") == "USER.CONFIRMED.RECEIPT", "portable receipt attribution changed")
    require(portable.get("reported_integrity") == "PASS", "reported portable integrity changed")
    require(portable.get("reported_handoff_readiness") == "T.20", "handoff readiness changed")
    require(portable.get("work_mode_required") is False, "work mode requirement changed")
    reported_sha = portable.get("reported_sha256")
    require(isinstance(reported_sha, str) and len(reported_sha) == 64, "invalid reported package SHA-256")
    payload = root / payload_rel

    if payload.is_file():
        actual_sha = hashlib.sha256(payload.read_bytes()).hexdigest()
        require(actual_sha == reported_sha, f"portable payload SHA-256 mismatch: {actual_sha}")
        require(portable.get("repository_payload_present") is True, "payload exists but manifest says absent")
        require(portable.get("independent_hash_recomputation") == "T.20", "verified payload must be T.20")
        portable_state = "T.20.INDEPENDENTLY.RECOMPUTED"
    else:
        require(portable.get("repository_payload_present") is False, "manifest claims a missing payload is present")
        require(portable.get("independent_hash_recomputation") == "U.21.HOLD", "missing payload must remain U.21.HOLD")
        portable_state = "U.21.HOLD.USER.CONFIRMED.ONLY"

    boundaries = set(manifest.get("promotion_boundaries", []))
    required_boundaries = {
        "USER.CONFIRMED.RECEIPT != INDEPENDENT.HASH.RECOMPUTATION",
        "PORTABLE.READINESS != LIVE.MODEL.EXECUTION",
        "LOCAL.RUNTIME != PUBLIC.DEPLOYMENT",
        "TEST.PASS != CANONICAL.PROMOTION",
        "QUEUE.SPECIFICATION != VERIFIED.PRODUCTION.ENFORCEMENT",
    }
    require(required_boundaries <= boundaries, "one or more evidence boundaries were removed")

    return {
        "audit": manifest["id"],
        "artifacts_checked": len(checked),
        "portable_state": portable_state,
        "humanlock": "ACTIVE",
        "result": "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    try:
        result = validate(args.root, args.manifest)
    except AuditError as exc:
        print(json.dumps({"result": "FAIL", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
