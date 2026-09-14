#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent
TASKBARS_PATH = ROOT / "taskbars.json"
MANIFEST_PATH = ROOT / "fr0333_taskbars_stronghold_root_0001.json"
SCHEMA_PATH = ROOT / "fr0333_taskbars_stronghold_0001.schema.json"

def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def sha256_hex(value):
    return hashlib.sha256(value).hexdigest()

def git_blob_sha(data):
    header = f"blob {len(data)}\0".encode("utf-8")
    return hashlib.sha1(header + data).hexdigest()

def keyed_set_root(records):
    hashes = {record["id"]: sha256_hex(canonical_bytes(record)) for record in records}
    material = "\n".join(f"{taskbar_id}:{hashes[taskbar_id]}" for taskbar_id in sorted(hashes))
    return sha256_hex(material.encode("utf-8")), hashes

def validate(taskbars, manifest, schema):
    errors = []

    schema_errors = sorted(Draft202012Validator(schema).iter_errors(taskbars), key=lambda e: list(e.path))
    errors.extend(f"SCHEMA:{'/'.join(map(str, e.path))}:{e.message}" for e in schema_errors)

    records = taskbars.get("taskbars", [])
    ids = [record.get("id") for record in records]
    if len(ids) != 21:
        errors.append(f"COUNT:{len(ids)}!=21")
    if len(set(ids)) != len(ids):
        errors.append("DUPLICATE_ID")

    protected_metadata = manifest["protected_metadata"]
    for key, expected in protected_metadata.items():
        if taskbars.get(key) != expected:
            errors.append(f"METADATA:{key}:MISMATCH")

    required_ids = set(manifest["record_hashes_sha256"])
    if set(ids) != required_ids:
        missing = sorted(required_ids - set(ids))
        extra = sorted(set(ids) - required_ids)
        errors.append(f"ID_SET:MISSING={missing}:EXTRA={extra}")

    actual_canonical = sha256_hex(canonical_bytes(taskbars))
    expected_canonical = manifest["hash_roots"]["canonical_taskbars_sha256"]
    if actual_canonical != expected_canonical:
        errors.append(f"CANONICAL_TASKBARS_SHA256:{actual_canonical}!={expected_canonical}")

    metadata = {k: v for k, v in taskbars.items() if k != "taskbars"}
    actual_metadata = sha256_hex(canonical_bytes(metadata))
    expected_metadata = manifest["hash_roots"]["canonical_metadata_sha256"]
    if actual_metadata != expected_metadata:
        errors.append(f"CANONICAL_METADATA_SHA256:{actual_metadata}!={expected_metadata}")

    actual_set_root, actual_record_hashes = keyed_set_root(records)
    expected_set_root = manifest["hash_roots"]["keyed_taskbar_set_sha256"]
    if actual_set_root != expected_set_root:
        errors.append(f"KEYED_SET_SHA256:{actual_set_root}!={expected_set_root}")

    expected_record_hashes = manifest["record_hashes_sha256"]
    for taskbar_id, expected_hash in expected_record_hashes.items():
        actual_hash = actual_record_hashes.get(taskbar_id)
        if actual_hash != expected_hash:
            errors.append(f"RECORD_HASH:{taskbar_id}:{actual_hash}!={expected_hash}")

    if "TB.FR0333.FIND.HUB.REMEMBERED.STATE.BOUNDARY.0001" not in set(ids):
        errors.append("FIND_HUB_REQUIRED")

    source_ids = set()
    for source in manifest["source_anchors"].values():
        source_ids.update(source["imported_ids"])
    if not source_ids.issubset(set(ids)):
        errors.append("SOURCE_IMPORT_MISSING")

    if manifest.get("truth_state") != "U.21":
        errors.append("MANIFEST_TRUTH_STATE_NOT_HOLD")
    if manifest.get("truth_qualifier") != "HOLD_AT_HUMANLOCK":
        errors.append("MANIFEST_HUMANLOCK_HOLD_MISSING")

    return errors

def main():
    taskbars_bytes = TASKBARS_PATH.read_bytes()
    taskbars = json.loads(taskbars_bytes)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    actual_blob = git_blob_sha(taskbars_bytes)
    expected_blob = manifest["protected_target"]["git_blob_sha"]
    errors = validate(taskbars, manifest, schema)
    if actual_blob != expected_blob:
        errors.append(f"GIT_BLOB_SHA:{actual_blob}!={expected_blob}")

    if errors:
        print("FR0333.TASKBARS.STRONGHOLD = HOLD")
        for error in errors:
            print(error)
        raise SystemExit(1)

    print("FR0333.TASKBARS.STRONGHOLD = PASS")
    print(f"TASKBAR.COUNT = {len(taskbars['taskbars'])}")
    print(f"TASKBARS.CANONICAL.SHA256 = {manifest['hash_roots']['canonical_taskbars_sha256']}")
    print(f"TASKBARS.KEYED.SET.SHA256 = {manifest['hash_roots']['keyed_taskbar_set_sha256']}")
    print(f"TASKBARS.GIT.BLOB.SHA = {actual_blob}")
    print("HUMANLOCK = ACTIVE_IMMUTABLE")
    print("MERGE = NOT.PERFORMED")
    print("PROMOTION = U.21.HOLD")

if __name__ == "__main__":
    main()
