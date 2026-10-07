#!/usr/bin/env python3
import json
import tempfile
import unittest
from pathlib import Path

from provider_change_monitor import CONFIG, SOURCES, diff_candidate, extract_text, run_monitor


BENCHMARK_MAP = {
    "identifier": "FR0333.FRONTIER.MODEL.MASTER.BENCHMARK.0001",
    "providers": [
        {"provider_id": "P01.OPENAI.CHATGPT", "company": "OpenAI", "assistant": "ChatGPT", "documented_frontier_options": ["GPT-x"], "documented_plan_signal": "plan row", "strength_tags": ["CODING", "FILES"], "runtime_in_this_master": "CURRENT.CHATGPT.ENVIRONMENT.ONLY"},
        {"provider_id": "P02.ANTHROPIC.CLAUDE", "company": "Anthropic", "assistant": "Claude", "documented_frontier_options": ["Claude-x"], "documented_plan_signal": "plan row", "strength_tags": ["CODING", "RESEARCH"], "runtime_in_this_master": "U.21.NOT.CONNECTED"},
        {"provider_id": "P03.GOOGLE.GEMINI", "company": "Google", "assistant": "Gemini", "documented_frontier_options": ["Gemini-x"], "documented_plan_signal": "plan row", "strength_tags": ["LONG.CONTEXT", "FILES"], "runtime_in_this_master": "U.21.NOT.CONNECTED"},
        {"provider_id": "P04.XAI.GROK", "company": "xAI", "assistant": "Grok", "documented_frontier_options": ["Grok-x"], "documented_plan_signal": "plan row", "strength_tags": ["REAL.TIME.WEB", "BUILD"], "runtime_in_this_master": "U.21.NOT.CONNECTED"},
    ],
    "fr0333_workload_benchmark": {
        "same_workload_required": True,
        "same_acceptance_criteria_required": True,
        "workloads": ["DIFFICULT.REPOSITORY.AUDIT", "MULTI.SOURCE.EVIDENCE.SYNTHESIS", "LARGE.FILE.ANALYSIS", "ARCHITECTURE.VALIDATION", "FAILURE.RECOVERY.TOOL.WORKFLOW"],
        "measures": ["CORRECTNESS", "COST"],
        "measured_cross_provider_performance_delta": "U.21.UNMEASURED",
    },
    "diamond_comparator": {
        "required_normalized_fields": ["cost_or_plan_context"],
        "route": ["PROVIDER_ELIGIBILITY_GATE"],
    },
}


class ProviderChangeMonitorTests(unittest.TestCase):
    def test_extract_text_ignores_script_content(self):
        self.assertEqual(extract_text("<p>New model launched</p><script>fake price $99</script>"), "New model launched")

    def test_news_diff_is_a_review_candidate_not_a_verified_claim(self):
        source = next(item for item in SOURCES if item["id"] == "OPENAI.NEWS")
        candidate = diff_candidate(source, "Old release.", "Old release. Introducing a new model now available.", BENCHMARK_MAP)
        self.assertEqual(candidate["status"], "SOURCE_CHANGE_CANDIDATE_REVIEW_REQUIRED")
        self.assertEqual(candidate["benchmark_lane_candidate"], "MODEL_CAPABILITY")
        mapping = candidate["benchmark_map_comparison"]
        self.assertEqual(candidate["workbench_map_state"], "PROVIDER_ROW_MATCHED_SURFACE_REVIEW_REQUIRED")
        self.assertEqual(mapping["provider_id"], "P01.OPENAI.CHATGPT")
        self.assertIn("DIFFICULT.REPOSITORY.AUDIT", mapping["workload_candidates"])
        self.assertEqual(mapping["performance_delta"], "U.21.UNMEASURED")
        self.assertIn("does not establish", candidate["interpretation"])

    def test_pricing_pages_map_to_cost_review(self):
        source = next(item for item in SOURCES if item["id"] == "OPENAI.API.PRICING")
        candidate = diff_candidate(source, "model input price 1.00", "model input price 2.00", BENCHMARK_MAP)
        self.assertEqual(candidate["benchmark_lane_candidate"], "COST")
        self.assertIn("cost_or_plan_context", candidate["benchmark_map_comparison"]["assumption_candidates"][1])

    def test_plan_changes_map_to_access_and_packaging_assumptions(self):
        source = next(item for item in SOURCES if item["id"] == "ANTHROPIC.CLAUDE.PLANS")
        candidate = diff_candidate(source, "Old plan limit.", "Old plan limit. New subscription plan adds higher usage and priority access.", BENCHMARK_MAP)
        self.assertEqual(candidate["benchmark_lane_candidate"], "PACKAGING")
        self.assertEqual(candidate["benchmark_map_comparison"]["provider_id"], "P02.ANTHROPIC.CLAUDE")
        self.assertIn("PROVIDER_ELIGIBILITY_GATE", candidate["benchmark_map_comparison"]["assumption_candidates"][0])

    def test_openai_status_incident_maps_to_desktop_workflow_lane(self):
        source = next(item for item in SOURCES if item["id"] == "OPENAI.CHATGPT.STATUS")
        incident = "We're currently experiencing issues. Unable to create new ChatGPT Work threads in the latest desktop app. Identified, partial outage. Updated Linux and macOS apps are available; fix rolling out for Windows."
        candidate = diff_candidate(source, "", incident, BENCHMARK_MAP)
        self.assertEqual(candidate["benchmark_lane_candidate"], "ACCESS")
        self.assertEqual(candidate["surface_identity"]["affected_surface_candidate"], "CHATGPT_WORK_THREAD_CREATION")
        mapping = candidate["benchmark_map_comparison"]
        self.assertEqual(mapping["provider_id"], "P01.OPENAI.CHATGPT")
        self.assertIn("FAILURE.RECOVERY.TOOL.WORKFLOW", mapping["workload_candidates"])
        self.assertIn("PROVIDER_ELIGIBILITY_GATE", mapping["assumption_candidates"][0])

    def test_openai_library_doc_maps_to_packaging_and_file_workflows(self):
        source = next(item for item in SOURCES if item["id"] == "OPENAI.CHATGPT.LIBRARY")
        passage = "Library is available to Free, Go, Plus, Pro, and Business users. Pro has up to 100 GB of Library storage. Google Drive files and folders can be browsed in Library."
        candidate = diff_candidate(source, "", passage, BENCHMARK_MAP)
        self.assertEqual(candidate["benchmark_lane_candidate"], "PACKAGING")
        self.assertEqual(candidate["surface_identity"]["affected_surface_candidate"], "CHATGPT_LIBRARY_FILE_WORKFLOW")
        mapping = candidate["benchmark_map_comparison"]
        self.assertEqual(mapping["provider_id"], "P01.OPENAI.CHATGPT")
        self.assertIn("LARGE.FILE.ANALYSIS", mapping["workload_candidates"])
        self.assertIn("PROVIDER_ELIGIBILITY_GATE", mapping["assumption_candidates"][0])

    def test_all_watched_providers_resolve_to_existing_map_rows(self):
        expected = {"openai": "P01.OPENAI.CHATGPT", "anthropic": "P02.ANTHROPIC.CLAUDE", "google": "P03.GOOGLE.GEMINI", "xai": "P04.XAI.GROK"}
        for source in SOURCES:
            if source["lane_hint"] == "COST":
                continue
            provider_row = next(row for row in BENCHMARK_MAP["providers"] if row["company"].casefold() == source["provider"].casefold())
            self.assertEqual(provider_row["provider_id"], expected[source["provider"].casefold()])

    def test_first_run_initializes_baseline_without_alert(self):
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "state.json"
            receipt = Path(temp) / "receipt.json"
            benchmark_map = Path(temp) / "benchmark.json"
            benchmark_map.write_text(json.dumps(BENCHMARK_MAP))
            fake_fetch = lambda _url: "<p>Stable provider page.</p>"
            first = run_monitor(fake_fetch, state, receipt, benchmark_map)
            second = run_monitor(fake_fetch, state, receipt, benchmark_map)
            self.assertEqual(first["run_state"], "BASELINE_INITIALIZED")
            self.assertEqual(second["run_state"], "STAY")
            self.assertEqual(json.loads(receipt.read_text())["source_count"], len(SOURCES))

    def test_manifest_binds_existing_sonar_without_new_taskbar_slot(self):
        self.assertEqual(CONFIG["taskbar_binding"], "TB.SONAR")
        self.assertEqual(len(SOURCES), 14)
        self.assertFalse(CONFIG["historical_baseline_mutation"])

    def test_active_status_page_on_first_observation_creates_review_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "state.json"
            receipt = Path(temp) / "receipt.json"
            benchmark_map = Path(temp) / "benchmark.json"
            benchmark_map.write_text(json.dumps(BENCHMARK_MAP))
            status_url = next(item["url"] for item in SOURCES if item["id"] == "OPENAI.CHATGPT.STATUS")

            def fake_fetch(url):
                if url == status_url:
                    return "<p>We're currently experiencing issues. Unable to create new ChatGPT Work threads. Partial outage.</p>"
                return "<p>Stable provider page.</p>"

            first = run_monitor(fake_fetch, state, receipt, benchmark_map)
            second = run_monitor(fake_fetch, state, receipt, benchmark_map)
            status_candidate = next(item for item in first["candidates"] if item["source_id"] == "OPENAI.CHATGPT.STATUS")
            self.assertEqual(first["run_state"], "SOURCE_CHANGE_CANDIDATES")
            self.assertEqual(status_candidate["source_state"], "ACTIVE_INCIDENT_ON_FIRST_OBSERVATION")
            self.assertEqual(second["run_state"], "STAY")


if __name__ == "__main__":
    unittest.main(verbosity=2)
