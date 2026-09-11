from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECORD = json.loads((ROOT / "fr0333_trump_bbc_litigation_evidence_0001.json").read_text(encoding="utf-8"))
CHAIN = json.loads((ROOT / "fr0333_golden_chain_gc_sb_0029.json").read_text(encoding="utf-8"))


def claim(claim_id: str) -> dict:
    return next(item for item in RECORD["claims"] if item["id"] == claim_id)


class TrumpBBCLitigationEvidenceTests(unittest.TestCase):
    def test_01_record_identity_and_chain_position(self) -> None:
        self.assertEqual(RECORD["id"], "FR0333.TRUMP.BBC.DEFAMATION.LITIGATION.EVIDENCE.0001")
        self.assertEqual(RECORD["golden_chain_position"], "GC.SB.0029")

    def test_02_chain_predecessor_is_0028(self) -> None:
        self.assertEqual(RECORD["golden_chain_predecessor"], "GC.SB.0028")
        self.assertEqual(CHAIN["predecessor"], "GC.SB.0028")

    def test_03_active_case_remains_hold(self) -> None:
        self.assertEqual(RECORD["case"]["status"], "ACTIVE")
        self.assertEqual(RECORD["terminal_state"], "U.21.HOLD")

    def test_04_trial_date_is_tentative_not_merits_proof(self) -> None:
        self.assertEqual(RECORD["case"]["trial"]["state"], "TENTATIVE.SCHEDULED")
        self.assertIn("TRIAL.SCHEDULED != LIABILITY.ESTABLISHED", RECORD["hard_invariants"])

    def test_05_edit_acknowledgment_does_not_promote_liability(self) -> None:
        self.assertEqual(claim("C.01")["state"], "ACKNOWLEDGED.BY.BBC")
        self.assertEqual(claim("C.02")["state"], "UNRESOLVED")

    def test_06_damages_are_pleaded_not_awarded(self) -> None:
        self.assertEqual(claim("C.03")["state"], "VERIFIED.PLEADING")
        self.assertNotEqual(claim("C.03")["state"], "FINAL.JUDGMENT")

    def test_07_discovery_resistance_does_not_prove_fear(self) -> None:
        self.assertIn("DISCOVERY.RESISTANCE != FEAR.PROVEN", RECORD["hard_invariants"])

    def test_08_amendment_motive_is_not_established(self) -> None:
        self.assertEqual(claim("C.06")["state"], "NOT.ESTABLISHED")

    def test_09_final_winner_is_not_established(self) -> None:
        self.assertEqual(claim("C.07")["state"], "NOT.ESTABLISHED")

    def test_10_party_assertion_is_not_court_finding(self) -> None:
        self.assertEqual(claim("C.08")["state"], "FILED.PARTY.POSITION")
        self.assertIn("PARTY.ASSERTION != COURT.FINDING", RECORD["hard_invariants"])

    def test_11_chain_registration_is_draft_unmerged(self) -> None:
        self.assertEqual(CHAIN["state"], "REGISTERED.DRAFT.UNMERGED")
        self.assertEqual(CHAIN["promotion"], "HOLD.UNTIL.PREDECESSOR.MERGE.ORDER.REVIEW.AND.CURRENT.CI.SATISFIED")

    def test_12_sources_are_https_and_nonempty(self) -> None:
        self.assertGreaterEqual(len(RECORD["source_register"]), 5)
        self.assertTrue(all(item["url"].startswith("https://") for item in RECORD["source_register"]))


if __name__ == "__main__":
    unittest.main()
