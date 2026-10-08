#!/usr/bin/env python3

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "RavenCloudTaskbar" / "fr0333_adobe_package_certificate_validate.py"
SPEC = importlib.util.spec_from_file_location("certificate_validator", MODULE_PATH)
VALIDATOR = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(VALIDATOR)

BOUNDARIES = [
    "USER.CONFIRMED.RECEIPT != INDEPENDENT.HASH.RECOMPUTATION",
    "PORTABLE.READINESS != LIVE.MODEL.EXECUTION",
    "LOCAL.RUNTIME != PUBLIC.DEPLOYMENT",
    "TEST.PASS != CANONICAL.PROMOTION",
    "QUEUE.SPECIFICATION != VERIFIED.PRODUCTION.ENFORCEMENT",
]


class CertificateAuditTests(unittest.TestCase):
    def fixture(self, base: Path):
        artifact = base / "receipt.json"
        artifact.write_text('{"count":10}\n', encoding="utf-8")
        manifest = {
            "id": "TEST.AUDIT",
            "mode": "APPEND_ONLY_BRANCH_REVIEW",
            "artifacts": [{
                "path": "receipt.json",
                "git_blob_sha": VALIDATOR.git_blob_sha(artifact.read_bytes()),
                "class": "TEST",
            }],
            "portable_receipt": {
                "source_class": "USER.CONFIRMED.RECEIPT",
                "reported_integrity": "PASS",
                "reported_handoff_readiness": "T.20",
                "work_mode_required": False,
                "reported_sha256": hashlib.sha256(b"portable").hexdigest(),
                "payload_path": "portable.zip",
                "repository_payload_present": False,
                "independent_hash_recomputation": "U.21.HOLD",
            },
            "promotion_boundaries": BOUNDARIES,
            "humanlock": {
                "required": True,
                "automatic_merge": False,
                "automatic_deployment": False,
                "automatic_promotion": False,
            },
        }
        manifest_path = base / "audit.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return manifest_path, artifact, manifest

    def test_repository_audit_passes(self):
        result = VALIDATOR.validate(ROOT)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["portable_state"], "U.21.HOLD.USER.CONFIRMED.ONLY")

    def test_artifact_mutation_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            manifest_path, artifact, _ = self.fixture(base)
            artifact.write_text('{"count":9}\n', encoding="utf-8")
            with self.assertRaisesRegex(VALIDATOR.AuditError, "artifact drift"):
                VALIDATOR.validate(base, manifest_path)

    def test_missing_payload_cannot_be_promoted(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            manifest_path, _, manifest = self.fixture(base)
            promoted = copy.deepcopy(manifest)
            promoted["portable_receipt"]["independent_hash_recomputation"] = "T.20"
            manifest_path.write_text(json.dumps(promoted), encoding="utf-8")
            with self.assertRaisesRegex(VALIDATOR.AuditError, "missing payload"):
                VALIDATOR.validate(base, manifest_path)

    def test_present_payload_is_recomputed(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            manifest_path, _, manifest = self.fixture(base)
            (base / "portable.zip").write_bytes(b"portable")
            manifest["portable_receipt"]["repository_payload_present"] = True
            manifest["portable_receipt"]["independent_hash_recomputation"] = "T.20"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = VALIDATOR.validate(base, manifest_path)
            self.assertEqual(result["portable_state"], "T.20.INDEPENDENTLY.RECOMPUTED")


if __name__ == "__main__":
    unittest.main()
