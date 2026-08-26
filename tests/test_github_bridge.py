import unittest
import tempfile
from dataclasses import replace
from pathlib import Path

from github_bridge import GitHubWebhookBridge
from github_webhook_benchmark import _config, _pull_request, run_benchmark


class GitHubWebhookBenchmarkTests(unittest.TestCase):
    def test_all_64_cases_pass(self):
        report = run_benchmark()
        failures = [case for case in report["cases"] if not case["pass"]]
        self.assertEqual(report["fixture_count"], 64)
        self.assertEqual(report["critical_failure_count"], 0, failures)
        self.assertEqual(report["pass_count"], 64, failures)
        self.assertEqual(report["deployment_state"], "NOT_EXECUTED")
        self.assertFalse(report["probability_claimed"])
        self.assertEqual(report["genius_vector"]["C_calibration"]["status"], "HOLD")

    def test_mocked_live_resolution_records_material_deltas(self):
        with tempfile.TemporaryDirectory(prefix="fr0333-github-resolution-") as directory:
            bridge = GitHubWebhookBridge(
                replace(_config(Path(directory) / "ledger.sqlite3"), live_resolution=True)
            )
            state = {
                "pull_request": _pull_request(),
                "workflow_runs": [
                    {
                        "id": 66,
                        "name": "CI",
                        "run_number": 66,
                        "status": "completed",
                        "conclusion": "success",
                        "head_sha": "a" * 40,
                    }
                ],
                "reviews": [],
            }

            def fake_api_get(path):
                if path.endswith("/pulls/1"):
                    return state["pull_request"]
                if "/actions/runs?" in path:
                    return {"workflow_runs": state["workflow_runs"]}
                if "/pulls/1/reviews?" in path:
                    return state["reviews"]
                if "/issues/1/comments?" in path:
                    return []
                if path.endswith("/status?per_page=100"):
                    return {"statuses": []}
                if path.endswith("/check-runs?per_page=100"):
                    return {"check_runs": []}
                raise AssertionError(f"Unexpected API path: {path}")

            bridge._api_get = fake_api_get
            baseline = bridge._resolve_current_state_sync(
                "0f6d87aa-4248-48a8-a529-cb780bb1dd54"
            )
            self.assertEqual(baseline["state"], "VERIFIED")
            self.assertEqual(baseline["alerts_created"], 0)

            state["pull_request"] = _pull_request(
                mergeable=False, mergeable_state="dirty"
            )
            state["workflow_runs"] = [
                {
                    "id": 67,
                    "name": "CI",
                    "run_number": 67,
                    "status": "completed",
                    "conclusion": "failure",
                    "head_sha": "a" * 40,
                }
            ]
            state["reviews"] = [
                {
                    "id": 99,
                    "state": "CHANGES_REQUESTED",
                    "commit_id": "a" * 40,
                    "body": "Please revise",
                }
            ]
            changed = bridge._resolve_current_state_sync(
                "a25642ba-c9f5-43ec-857d-f69aa163270e"
            )
            self.assertEqual(changed["state"], "VERIFIED")
            kinds = {alert["kind"] for alert in bridge.store.list_alerts(20)}
            self.assertIn("MERGEABILITY_CHANGED", kinds)
            self.assertIn("CI_STATUS_CHANGED", kinds)
            self.assertIn("REVIEW_FEEDBACK_CHANGED", kinds)


if __name__ == "__main__":
    unittest.main()
