import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import unittest

from canonical_hash import canonical_hash
from validate_source_receipt import receipt_payload, validate_source_receipt


class SourceReceiptTests(unittest.TestCase):
    def setUp(self):
        self.receipt = {
            "source_id": "source.1",
            "source_type": "official_webpage",
            "publisher": "Publisher",
            "title": "Title",
            "published_at": "2026-09-14",
            "retrieved_at": "2026-09-14",
            "url": "https://example.com/source",
            "evidence_class": "OFFICIAL.PRIMARY.SOURCE",
            "summary": "Summary",
            "claims_observed": ["CLAIM.ONE"],
        }
        self.receipt["payload_hash"] = canonical_hash(receipt_payload(self.receipt))

    def test_valid_receipt_passes(self):
        self.assertTrue(validate_source_receipt(self.receipt))

    def test_tampered_receipt_fails(self):
        tampered = dict(self.receipt)
        tampered["title"] = "Changed"
        self.assertFalse(validate_source_receipt(tampered))


if __name__ == "__main__":
    unittest.main()
