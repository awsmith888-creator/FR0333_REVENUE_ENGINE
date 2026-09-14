import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import unittest

from run_regression_guard import assert_append_only


class RegressionContractTests(unittest.TestCase):
    def test_cooccurrence_cannot_be_promoted_to_causation(self):
        with self.assertRaisesRegex(AssertionError, "CAUSALITY_LEAK"):
            assert_append_only({}, {"COOCCURRENCE_IS_CAUSATION": True})

    def test_truth_state_metadata_pollution_rejected(self):
        with self.assertRaisesRegex(AssertionError, "TRUTH_STATE_METADATA_POLLUTION"):
            assert_append_only({}, {"CLAIM": "T.20.GENERAL.ECONOMIC.EFFECT"})

    def test_stable_unknown_remains_stable(self):
        assert_append_only({"A": "U.21"}, {"A": "U.21"})


if __name__ == "__main__":
    unittest.main()
