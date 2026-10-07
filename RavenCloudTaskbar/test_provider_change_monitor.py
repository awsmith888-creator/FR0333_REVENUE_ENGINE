#!/usr/bin/env python3
import json
import tempfile
import unittest
from pathlib import Path

from provider_change_monitor import CONFIG, SOURCES, diff_candidate, extract_text, run_monitor


class ProviderChangeMonitorTests(unittest.TestCase):
    def test_extract_text_ignores_script_content(self):
        self.assertEqual(extract_text("<p>New model launched</p><script>fake price $99</script>"), "New model launched")

    def test_news_diff_is_a_review_candidate_not_a_verified_claim(self):
        source = next(item for item in SOURCES if item["id"] == "OPENAI.NEWS")
        candidate = diff_candidate(source, "Old release.", "Old release. Introducing a new model now available.")
        self.assertEqual(candidate["status"], "SOURCE_CHANGE_CANDIDATE_REVIEW_REQUIRED")
        self.assertEqual(candidate["benchmark_lane_candidate"], "MODEL_CAPABILITY")
        self.assertEqual(candidate["workbench_map_state"], "UNRESOLVED_DISTINCT_WORKBENCH_MAP_NOT_LOCATED")
        self.assertIn("does not establish", candidate["interpretation"])

    def test_pricing_pages_map_to_cost_review(self):
        source = next(item for item in SOURCES if item["id"] == "OPENAI.API.PRICING")
        candidate = diff_candidate(source, "model input price 1.00", "model input price 2.00")
        self.assertEqual(candidate["benchmark_lane_candidate"], "COST")

    def test_first_run_initializes_baseline_without_alert(self):
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "state.json"
            receipt = Path(temp) / "receipt.json"
            fake_fetch = lambda _url: "<p>Stable provider page.</p>"
            first = run_monitor(fake_fetch, state, receipt)
            second = run_monitor(fake_fetch, state, receipt)
            self.assertEqual(first["run_state"], "BASELINE_INITIALIZED")
            self.assertEqual(second["run_state"], "STAY")
            self.assertEqual(json.loads(receipt.read_text())["source_count"], len(SOURCES))

    def test_manifest_binds_existing_sonar_without_new_taskbar_slot(self):
        self.assertEqual(CONFIG["taskbar_binding"], "TB.SONAR")
        self.assertEqual(len(SOURCES), 8)
        self.assertFalse(CONFIG["historical_baseline_mutation"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
