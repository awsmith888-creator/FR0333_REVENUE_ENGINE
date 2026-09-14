import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import unittest

from canonical_hash import canonical_hash


class CanonicalHashTests(unittest.TestCase):
    def test_key_order_does_not_change_hash(self):
        left = {"b": 2, "a": 1}
        right = {"a": 1, "b": 2}
        self.assertEqual(canonical_hash(left), canonical_hash(right))

    def test_expected_digest(self):
        self.assertEqual(
            canonical_hash({"a": 1}),
            "sha256_015abd7f5cc57a2dd94b7590f04ad8084273905ee33ec5cebeae62276a97f862",
        )


if __name__ == "__main__":
    unittest.main()
