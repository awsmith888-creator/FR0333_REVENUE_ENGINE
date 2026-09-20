import copy
import json
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from statistical_anti_hallucination_v4 import evaluate_statistical_hardener_v4

FIXTURE = ROOT / "receipts/operator/2026-09-20/statistical_anti_hallucination.fixture.v4.json"


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class StatisticalAntiHallucinationV4Tests(unittest.TestCase):
    def test_control_fixture_opens(self):
        result = evaluate_statistical_hardener_v4(load_fixture())
        self.assertEqual(result["decision"], "OPEN")
        self.assertEqual(result["kernel_bitword"], "1111")
        self.assertTrue(all(result["gates"].values()))

    def test_one_kernel_zero_holds(self):
        fixture = load_fixture()
        fixture["kernels"]["ESPN.FANTASY.SPORTS"] = "HOLD"
        self.assertEqual(evaluate_statistical_hardener_v4(fixture)["decision"], "HOLD")

    def test_future_final_score_holds(self):
        fixture = load_fixture()
        fixture["scoreboards"][0]["games"][0]["event_date"] = "2026-09-21"
        result = evaluate_statistical_hardener_v4(fixture)
        self.assertFalse(result["gates"]["SPORTS.SCOREBOARD.RECOMPUTATION"])

    def test_score_total_is_recomputed(self):
        fixture = load_fixture()
        fixture["scoreboards"][0]["declared"]["total_points"] = 142
        result = evaluate_statistical_hardener_v4(fixture)
        self.assertEqual(result["scoreboards"][0]["total_points"], 141)
        self.assertEqual(result["decision"], "HOLD")

    def test_duplicate_game_is_not_independent_evidence(self):
        fixture = load_fixture()
        fixture["scoreboards"][0]["games"][1]["game_id"] = "DET.CWS"
        result = evaluate_statistical_hardener_v4(fixture)
        self.assertFalse(result["scoreboards"][0]["checks"]["GAME.IDS.UNIQUE"])

    def test_bad_derivation_holds(self):
        fixture = load_fixture()
        fixture["derivations"][0]["declared_result"] = 591
        result = evaluate_statistical_hardener_v4(fixture)
        self.assertFalse(result["gates"]["DERIVATION.RECOMPUTATION"])

    def test_blocked_espn_page_cannot_promote_t20_claim(self):
        fixture = load_fixture()
        fixture["claims"][0]["source_ids"] = ["ESPN.NFL.WEEK2.ROUTE"]
        result = evaluate_statistical_hardener_v4(fixture)
        self.assertTrue(result["claims"][0]["blocked_source_promoted"])
        self.assertEqual(result["decision"], "HOLD")

    def test_sports_cannot_promote_art_lane(self):
        fixture = load_fixture()
        fixture["claims"][-1]["promotes_lane"] = "ART"
        result = evaluate_statistical_hardener_v4(fixture)
        self.assertFalse(result["gates"]["LANE.CAUSALITY.FIREWALL"])

    def test_causal_t20_without_design_holds(self):
        fixture = load_fixture()
        fixture["claims"][0]["relation"] = "CAUSAL"
        result = evaluate_statistical_hardener_v4(fixture)
        self.assertFalse(result["claims"][0]["causal_bounded"])

    def test_negative_control_must_detect_mismatch(self):
        fixture = load_fixture()
        control = fixture["negative_controls"][0]
        control["displayed_start"] = "2026-09-19"
        control["displayed_week"] = 3
        control["access_state"] = "ACCESSIBLE"
        result = evaluate_statistical_hardener_v4(fixture)
        self.assertFalse(result["gates"]["NEGATIVE.CONTROL.DETECTED"])
        self.assertEqual(result["decision"], "HOLD")

    def test_humanlock_cannot_be_disabled(self):
        fixture = load_fixture()
        fixture["humanlock"] = "DISABLED"
        self.assertEqual(evaluate_statistical_hardener_v4(fixture)["decision"], "HOLD")


if __name__ == "__main__":
    unittest.main()
