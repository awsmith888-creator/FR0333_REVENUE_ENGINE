from __future__ import annotations

import hashlib
import unittest
from dataclasses import dataclass


@dataclass(frozen=True)
class Slot:
    batch_id: str
    slot_id: str
    attempted: bool = True
    successful: bool = True
    returned: bool = True
    asset_id: str = ""
    asset_sha256: str = ""
    aspect_ratio: str = "9:16"
    subject_match: bool = True
    composition_class: str = "SINGLE_PANEL"
    readback_pass: bool = True
    receipt_chain_complete: bool = True
    output_hash_matches: bool = True
    contradictions: tuple[str, ...] = ()


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def make_clean_batch() -> list[Slot]:
    batch: list[Slot] = []
    for i in range(1, 11):
        asset_id = f"ASSET-{i:02d}"
        batch.append(
            Slot(
                batch_id="BATCH-10.5-001",
                slot_id=f"{i:02d}",
                asset_id=asset_id,
                asset_sha256=_sha(asset_id),
            )
        )
    return batch


def evaluate(batch: list[Slot]) -> str:
    if len(batch) != 10:
        return "HOLD"
    keys = [(s.batch_id, s.slot_id) for s in batch]
    if len(set(keys)) != 10:
        return "HOLD"
    asset_ids = [s.asset_id for s in batch if s.returned]
    asset_hashes = [s.asset_sha256 for s in batch if s.returned]
    if len(set(asset_ids)) != len(asset_ids) or len(set(asset_hashes)) != len(asset_hashes):
        return "HOLD"
    for slot in batch:
        if not slot.attempted or not slot.successful or not slot.returned:
            return "HOLD"
        if slot.composition_class != "SINGLE_PANEL":
            return "HOLD"
        if slot.aspect_ratio != "9:16":
            return "HOLD"
        if not slot.subject_match:
            return "HOLD"
        if not slot.readback_pass:
            return "HOLD"
        if not slot.receipt_chain_complete or not slot.output_hash_matches:
            return "HOLD"
        if slot.contradictions:
            return "HOLD"
    return "PASS_CANDIDATE"


class Adobe105RuntimeMatrixTests(unittest.TestCase):
    def test_success_10_of_10(self) -> None:
        self.assertEqual(evaluate(make_clean_batch()), "PASS_CANDIDATE")

    def test_partial_failure_9_of_10(self) -> None:
        batch = make_clean_batch()
        batch[9] = Slot(**{**batch[9].__dict__, "successful": False, "returned": False})
        self.assertEqual(evaluate(batch), "HOLD")
        self.assertTrue(all(s.successful for s in batch[:9]))

    def test_duplicate_output(self) -> None:
        batch = make_clean_batch()
        batch[9] = Slot(**{**batch[9].__dict__, "asset_id": batch[0].asset_id, "asset_sha256": batch[0].asset_sha256})
        self.assertEqual(evaluate(batch), "HOLD")

    def test_collage(self) -> None:
        batch = make_clean_batch()
        batch[4] = Slot(**{**batch[4].__dict__, "composition_class": "COLLAGE"})
        self.assertEqual(evaluate(batch), "HOLD")

    def test_wrong_aspect(self) -> None:
        batch = make_clean_batch()
        batch[2] = Slot(**{**batch[2].__dict__, "aspect_ratio": "1:1"})
        self.assertEqual(evaluate(batch), "HOLD")

    def test_wrong_subject(self) -> None:
        batch = make_clean_batch()
        batch[6] = Slot(**{**batch[6].__dict__, "subject_match": False})
        self.assertEqual(evaluate(batch), "HOLD")

    def test_contradiction(self) -> None:
        batch = make_clean_batch()
        batch[1] = Slot(**{**batch[1].__dict__, "contradictions": ("SUBJECT_CONFLICT",)})
        self.assertEqual(evaluate(batch), "HOLD")

    def test_receipt_mismatch(self) -> None:
        batch = make_clean_batch()
        batch[7] = Slot(**{**batch[7].__dict__, "output_hash_matches": False})
        self.assertEqual(evaluate(batch), "HOLD")


if __name__ == "__main__":
    unittest.main()
