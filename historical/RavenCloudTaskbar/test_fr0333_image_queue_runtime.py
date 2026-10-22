#!/usr/bin/env python3
import dataclasses
import unittest

from fr0333_image_queue_runtime import (
    QueueIntegrityError,
    SlotReceipt,
    compile_slots,
    dispatch_slots,
    reconcile,
)


class ImageQueueRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.scenes = [
            {"scene_contract": f"distinct human dance scene {i}", "input_reference_ids": [f"ref-{i}"]}
            for i in range(1, 11)
        ]
        self.slots = compile_slots(self.scenes)

    @staticmethod
    def provider_ok(slot):
        n = int(slot.slot_id[1:])
        return SlotReceipt(
            slot_id=slot.slot_id,
            intent_hash=slot.intent_hash,
            scene_contract=slot.scene_contract,
            reference_policy=slot.reference_policy,
            input_reference_ids=slot.input_reference_ids,
            output_asset_id=f"asset-{n:02d}",
            width=1080,
            height=1920,
            aspect_ratio="9:16",
            provider_request_id=f"request-{n:02d}",
            visual_fingerprint=f"fingerprint-{n:02d}",
            readback_state="PASS",
            user_state="NOT_OBSERVED",
        )

    def test_ten_slot_dispatch_produces_ten_independent_receipts(self):
        receipts = dispatch_slots(self.slots, self.provider_ok)
        report = reconcile(self.slots, receipts)
        self.assertEqual(len(self.slots), 10)
        self.assertEqual(len(receipts), 10)
        self.assertEqual(report["requested_count"], 10)
        self.assertEqual(report["output_count"], 10)
        self.assertEqual(report["receipt_count"], 10)
        self.assertEqual(report["unique_output_asset_ids"], 10)
        self.assertEqual(report["unique_provider_request_ids"], 10)
        self.assertEqual(report["unique_visual_fingerprints"], 10)
        self.assertEqual(report["failed_slots"], [])
        self.assertEqual(report["collage_slots"], [])
        self.assertEqual(report["state"], "T.20.PASS")

    def test_count_mismatch_fails_closed(self):
        receipts = dispatch_slots(self.slots, self.provider_ok)[:-1]
        report = reconcile(self.slots, receipts)
        self.assertEqual(report["state"], "F.6.REJECT")
        self.assertEqual(report["missing_slots"], ["Q10"])
        self.assertEqual(report["retry_slots"], ["Q10"])

    def test_duplicate_output_asset_is_rejected(self):
        receipts = dispatch_slots(self.slots, self.provider_ok)
        receipts[9] = dataclasses.replace(receipts[9], output_asset_id=receipts[0].output_asset_id)
        report = reconcile(self.slots, receipts)
        self.assertEqual(report["state"], "F.6.REJECT")
        self.assertTrue(report["duplicate_output_assets"])

    def test_duplicate_visual_fingerprint_is_rejected(self):
        receipts = dispatch_slots(self.slots, self.provider_ok)
        receipts[8] = dataclasses.replace(receipts[8], visual_fingerprint=receipts[0].visual_fingerprint)
        report = reconcile(self.slots, receipts)
        self.assertEqual(report["state"], "F.6.REJECT")
        self.assertTrue(report["duplicate_visual_fingerprints"])

    def test_contact_sheet_slot_is_rejected(self):
        receipts = dispatch_slots(self.slots, self.provider_ok)
        receipts[3] = dataclasses.replace(receipts[3], collage_detected=True, readback_state="FAIL")
        report = reconcile(self.slots, receipts)
        self.assertEqual(report["state"], "F.6.REJECT")
        self.assertEqual(report["collage_slots"], ["Q04"])
        self.assertEqual(report["retry_slots"], ["Q04"])

    def test_failed_q04_retries_q04_only(self):
        receipts = dispatch_slots(self.slots, self.provider_ok)
        receipts[3] = dataclasses.replace(receipts[3], execution_state="FAIL_RUNTIME", readback_state="FAIL")
        report = reconcile(self.slots, receipts)
        self.assertEqual(report["state"], "F.6.REJECT")
        self.assertEqual(report["retry_slots"], ["Q04"])
        self.assertEqual(len(report["preserve_slots"]), 9)
        self.assertNotIn("Q04", report["preserve_slots"])
        self.assertIn("Q01", report["preserve_slots"])
        self.assertIn("Q10", report["preserve_slots"])

    def test_receipt_slot_mismatch_is_rejected_before_reconciliation(self):
        def bad_provider(slot):
            receipt = self.provider_ok(slot)
            if slot.slot_id == "Q04":
                return dataclasses.replace(receipt, slot_id="Q05")
            return receipt

        with self.assertRaises(QueueIntegrityError):
            dispatch_slots(self.slots, bad_provider)

    def test_queue_is_one_request_per_slot_not_one_request_ten_variants(self):
        seen = []

        def counting_provider(slot):
            seen.append(slot.slot_id)
            return self.provider_ok(slot)

        receipts = dispatch_slots(self.slots, counting_provider)
        self.assertEqual(seen, [f"Q{i:02d}" for i in range(1, 11)])
        self.assertEqual(len(receipts), 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
