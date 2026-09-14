#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from validate_clotilda_anson_dna_separation import validate


HERE = Path(__file__).resolve().parent
BASE = json.loads(
    (HERE / "fr0333_clotilda_anson_dna_separation_0001.json").read_text(encoding="utf-8")
)


class ClotildaAnsonEvidenceTests(unittest.TestCase):
    def test_canonical_record_passes(self) -> None:
        self.assertEqual(validate(copy.deepcopy(BASE)), [])

    def assert_rejected(self, mutate) -> None:
        candidate = copy.deepcopy(BASE)
        mutate(candidate)
        self.assertTrue(validate(candidate))

    def test_rejects_clotilda_positive_auto_promotion(self) -> None:
        self.assert_rejected(
            lambda d: d["claims"][9].update(state="T.20")
        )

    def test_rejects_no_dna_false_promotion(self) -> None:
        self.assert_rejected(
            lambda d: d["claims"][10].update(state="F.6")
        )

    def test_rejects_facebook_provenance_promotion(self) -> None:
        self.assert_rejected(
            lambda d: d["claims"][13].update(state="T.20")
        )

    def test_rejects_presumed_status_as_direct_proof(self) -> None:
        self.assert_rejected(
            lambda d: d["claims"][5].update(state="T.20")
        )

    def test_rejects_collective_motive_promotion(self) -> None:
        self.assert_rejected(
            lambda d: d["claims"][17].update(state="T.20")
        )

    def test_rejects_missing_source_reference(self) -> None:
        self.assert_rejected(
            lambda d: d["claims"][0].update(sources=["S.99"])
        )

    def test_rejects_missing_pinpoint(self) -> None:
        self.assert_rejected(
            lambda d: d["claims"][0].pop("pinpoint")
        )

    def test_rejects_humanlock_disabled(self) -> None:
        self.assert_rejected(
            lambda d: d.update(humanlock=False)
        )

    def test_rejects_promotion_without_review(self) -> None:
        self.assert_rejected(
            lambda d: d.update(canonical_promotion="T.20.PASS")
        )

    def test_rejects_predecessor_drift(self) -> None:
        self.assert_rejected(
            lambda d: d.update(golden_chain_predecessor="GC.SB.0029")
        )

    def test_rejects_unbounded_search_claim(self) -> None:
        self.assert_rejected(
            lambda d: d["search_boundary"].update(result_scope="COMPLETE.WEB.CENSUS")
        )

    def test_rejects_silent_rewrite_policy(self) -> None:
        self.assert_rejected(
            lambda d: d["correction_policy"].update(overwrite_prior_observation=True)
        )


if __name__ == "__main__":
    unittest.main()
