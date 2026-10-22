#!/usr/bin/env python3
"""Offline regression tests for receipt 0003 verification; synthetic provider fixtures only."""
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from verify_image_queue_live_readback_0001 import RECEIPT_ID, run


class ReadbackGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.receipt_path = self.root / "receipt.json"
        self.evidence_dir = self.root / "evidence"
        self.evidence_dir.mkdir()
        self.slots = []
        self.manifest_slots = []
        for i in range(1, 11):
            slot = f"Q{i:02d}"
            gen = f"gen-{i}"
            gurl = f"https://example.invalid/generation/{i}"
            norm = f"norm-{i}"
            furl = f"https://example.invalid/final/{i}"
            receipt_row = {
                "slot_id": slot,
                "normalization_request_id": norm,
                "final_output_url": furl,
                "final_dimensions": [1080, 1920],
                "readback": "PASS",
            }
            if i == 9:
                receipt_row["retry_generation_request_id"] = gen
                receipt_row["retry_generation_output_url"] = gurl
                receipt_row["initial_generation_request_id"] = "failed-q09"
            else:
                receipt_row["generation_request_id"] = gen
                receipt_row["generation_output_url"] = gurl
            self.slots.append(receipt_row)
            gen_file = f"{slot}.generate.response.json"
            norm_file = f"{slot}.normalize.response.json"
            final_file = f"{slot}.png"
            (self.evidence_dir / gen_file).write_text(json.dumps({"request_id": gen, "output_url": gurl}))
            (self.evidence_dir / norm_file).write_text(json.dumps({"request_id": norm, "output_url": furl}))
            Image.new("RGB", (1080, 1920), (i, i * 2, i * 3)).save(self.evidence_dir / final_file)
            self.manifest_slots.append({
                "slot_id": slot,
                "generation_request_id": gen,
                "generation_output_url": gurl,
                "normalization_request_id": norm,
                "final_output_url": furl,
                "generation_response_file": gen_file,
                "normalization_response_file": norm_file,
                "final_file": final_file,
            })
        self.receipt_path.write_text(json.dumps({
            "identifier": RECEIPT_ID,
            "queue": {"final_delivered_count": 10},
            "slots": self.slots,
        }))
        self.manifest_path = self.evidence_dir / "provider_export_manifest.json"
        self.write_manifest()

    def write_manifest(self):
        self.manifest_path.write_text(json.dumps({
            "receipt_identifier": RECEIPT_ID,
            "source_class": "EXISTING_ADOBE_PROVIDER_RESPONSE_EXPORT",
            "slots": self.manifest_slots,
        }))

    def gate(self):
        return run(self.receipt_path, self.evidence_dir)

    def test_ten_distinct_files_and_records_pass_bounded_gate(self):
        r = self.gate()
        self.assertEqual(r["state"], "T.20.BOUNDED_FILE_AND_PROVIDER_RECORD_MATCH")
        self.assertEqual(r["verified_byte_count"], 10)
        self.assertEqual(r["verified_provider_record_slots"], 10)
        self.assertEqual(r["unique_final_sha256_count"], 10)
        self.assertEqual(r["quality_promotion"], "U.21.HOLD")

    def test_missing_provider_records_never_promotes(self):
        self.manifest_path.unlink()
        self.assertEqual(self.gate()["state"], "U.21.HOLD")

    def test_duplicate_final_bytes_rejected(self):
        (self.evidence_dir / "Q10.png").write_bytes((self.evidence_dir / "Q01.png").read_bytes())
        result = self.gate()
        self.assertEqual(result["state"], "F.6.REJECT")
        self.assertTrue(any("duplicate output bytes" in e for e in result["reject"]))

    def test_zero_byte_final_rejected(self):
        (self.evidence_dir / "Q10.png").write_bytes(b"")
        self.assertEqual(self.gate()["state"], "F.6.REJECT")

    def test_provider_request_mismatch_rejected(self):
        self.manifest_slots[0]["normalization_request_id"] = "other"
        self.write_manifest()
        self.assertEqual(self.gate()["state"], "F.6.REJECT")

    def test_missing_image_blocks_gate(self):
        (self.evidence_dir / "Q05.png").unlink()
        self.assertEqual(self.gate()["state"], "U.21.HOLD")

    def test_path_traversal_rejected_as_unavailable_not_read(self):
        self.manifest_slots[0]["final_file"] = "../../outside.png"
        self.write_manifest()
        r = self.gate()
        self.assertEqual(r["state"], "U.21.HOLD")
        self.assertTrue(any("escapes evidence directory" in e for e in r["hold"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
