#!/usr/bin/env python3
"""Bounded offline audit of evidence binding and append-only index integration."""
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent
record = json.loads((ROOT / "fr0333_image_queue_failure_closure_0001.json").read_text())
index = json.loads((ROOT / "fr0333_golden_chain_index_0001.json").read_text())
assert record["closure"]["live_provider_delivery"] == "HOLD_NOT_REEXECUTED"
assert record["verification"]["current_tests"]["evidence_class"] == "SIMULATED_FIXTURE"
assert record["verification"]["historical_reproduction"]["exit_code"] == 1
assert record["verification"]["current_tests"]["exit_code"] == 0
assert record["anti_loop"]["automatic_provider_calls"] is False
assert record["anti_loop"]["automatic_workflow_reruns"] is False
assert record["certificate_type"] == "SELF_ISSUED_VERIFICATION_RECORD_NOT_EXTERNAL_ATTESTATION"
for item in record["source_files"]:
    data = (ROOT.parent / item["path"]).read_bytes()
    assert hashlib.sha256(data).hexdigest() == item["sha256"], item["path"]
    git_blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    assert git_blob == item["git_blob_sha"], item["path"]
entries = index["entries"]
assert len({e["index"] for e in entries}) == len(entries)
assert len({e["identifier"] for e in entries}) == len(entries)
matches = [e for e in entries if e["identifier"] == record["identifier"]]
assert len(matches) == 1 and matches[0]["index"] == "0.8"
assert matches[0]["state"] == "DIAGNOSIS_VERIFIED_LOCAL_TEST_PASS_LIVE_REVERIFICATION_HOLD"
print("PASS: source hashes / evidence boundaries / bounded rechecks / unique index")

