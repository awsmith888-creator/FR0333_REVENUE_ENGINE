#!/usr/bin/env python3
import dataclasses
import unittest

from fr0333_image_queue_runtime import (
    IMAGE_GENERATE,
    IMAGE_INSTRUCT_EDIT,
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
    def make_receipt(slot, *, operation, request_id, variation_index, batch_index, batch_size):
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
            provider_request_id=request_id,
            provider_variation_index=variation_index,
            batch_index=batch_index,
            batch_size=batch_size,
            visual_fingerprint=f"fingerprint-{n:02d}",
            readback_state="PASS",
            anatomy_readback="PASS",
            realism_readback="PASS",
            clothing_variance_readback="PASS",
            intent_alignment_readback="PASS",
            user_state="NOT_OBSERVED",
            operation=operation,
        )

    def generate_provider(self):
        calls = []

        def provider(batch, batch_index):
            calls.append([slot.slot_id for slot in batch])
            request_id = f"request-batch-{batch_index:02d}"
            return [
                self.make_receipt(
                    slot,
                    operation=IMAGE_GENERATE,
                    request_id=request_id,
                    variation_index=variation_index,
                    batch_index=batch_index,
                    batch_size=len(batch),
                )
                for variation_index, slot in enumerate(batch, start=1)
            ]

        return provider, calls

    def singleton_edit_provider(self):
        calls = []

        def provider(slot):
            batch_index = len(calls) + 1
            calls.append(slot.slot_id)
            return self.make_receipt(
                slot,
                operation=IMAGE_INSTRUCT_EDIT,
                request_id=f"edit-request-{batch_index:02d}",
                variation_index=1,
                batch_index=batch_index,
                batch_size=1,
            )

        return provider, calls

    def test_ten_slot_generate_dispatch_uses_native_4_4_2(self):
        provider, calls = self.generate_provider()
        receipts = dispatch_slots(self.slots, provider, operation=IMAGE_GENERATE)
        report = reconcile(self.slots, receipts, operation=IMAGE_GENERATE)
        self.assertEqual([len(batch) for batch in calls], [4, 4, 2])
        self.assertEqual(report["expected_batch_plan"], [4, 4, 2])
        self.assertEqual(report["provider_call_count"], 3)
        self.assertEqual(report["expected_provider_call_count"], 3)
        self.assertEqual(report["requested_count"], 10)
        self.assertEqual(report["output_count"], 10)
        self.assertEqual(report["unique_output_asset_ids"], 10)
        self.assertEqual(report["unique_provider_output_coordinates"], 10)
        self.assertEqual(report["unique_visual_fingerprints"], 10)
        self.assertEqual(report["state"], "T.20.PASS")

    def test_exact_1080_1920_is_required_not_ratio_only(self):
        provider, _ = self.generate_provider()
        receipts = dispatch_slots(self.slots, provider, operation=IMAGE_GENERATE)
        receipts[4] = dataclasses.replace(receipts[4], width=900, height=1600)
        report = reconcile(self.slots, receipts, operation=IMAGE_GENERATE)
        self.assertEqual(report["state"], "F.6.REJECT")
        self.assertEqual(report["exact_dimension_failures"], ["Q05"])
        self.assertIn("Q05", report["failed_slots"])

    def test_per_slot_readback_fields_are_independent_gates(self):
        for field in (
            "anatomy_readback",
            "realism_readback",
            "clothing_variance_readback",
            "intent_alignment_readback",
        ):
            provider, _ = self.generate_provider()
            receipts = dispatch_slots(self.slots, provider, operation=IMAGE_GENERATE)
            receipts[2] = dataclasses.replace(receipts[2], **{field: "FAIL"})
            report = reconcile(self.slots, receipts, operation=IMAGE_GENERATE)
            self.assertEqual(report["state"], "F.6.REJECT", field)
            self.assertIn("Q03", report["failed_slots"], field)
            self.assertIn(field, report["readback_failures"]["Q03"], field)

    def test_count_mismatch_fails_closed(self):
        provider, _ = self.generate_provider()
        receipts = dispatch_slots(self.slots, provider, operation=IMAGE_GENERATE)[:-1]
        report = reconcile(self.slots, receipts, operation=IMAGE_GENERATE)
        self.assertEqual(report["state"], "F.6.REJECT")
        self.assertEqual(report["missing_slots"], ["Q10"])
        self.assertEqual(report["retry_slots"], ["Q10"])

    def test_duplicate_output_asset_is_rejected(self):
        provider, _ = self.generate_provider()
        receipts = dispatch_slots(self.slots, provider, operation=IMAGE_GENERATE)
        receipts[9] = dataclasses.replace(receipts[9], output_asset_id=receipts[0].output_asset_id)
        report = reconcile(self.slots, receipts, operation=IMAGE_GENERATE)
        self.assertEqual(report["state"], "F.6.REJECT")
        self.assertTrue(report["duplicate_output_assets"])

    def test_duplicate_visual_fingerprint_is_rejected(self):
        provider, _ = self.generate_provider()
        receipts = dispatch_slots(self.slots, provider, operation=IMAGE_GENERATE)
        receipts[8] = dataclasses.replace(receipts[8], visual_fingerprint=receipts[0].visual_fingerprint)
        report = reconcile(self.slots, receipts, operation=IMAGE_GENERATE)
        self.assertEqual(report["state"], "F.6.REJECT")
        self.assertTrue(report["duplicate_visual_fingerprints"])

    def test_contact_sheet_slot_is_rejected(self):
        provider, _ = self.generate_provider()
        receipts = dispatch_slots(self.slots, provider, operation=IMAGE_GENERATE)
        receipts[3] = dataclasses.replace(receipts[3], collage_detected=True, readback_state="FAIL")
        report = reconcile(self.slots, receipts, operation=IMAGE_GENERATE)
        self.assertEqual(report["state"], "F.6.REJECT")
        self.assertEqual(report["collage_slots"], ["Q04"])
        self.assertEqual(report["retry_slots"], ["Q04"])

    def test_failed_q04_retries_q04_only(self):
        provider, _ = self.generate_provider()
        receipts = dispatch_slots(self.slots, provider, operation=IMAGE_GENERATE)
        receipts[3] = dataclasses.replace(receipts[3], execution_state="FAIL_RUNTIME", readback_state="FAIL")
        report = reconcile(self.slots, receipts, operation=IMAGE_GENERATE)
        self.assertEqual(report["state"], "F.6.REJECT")
        self.assertEqual(report["retry_slots"], ["Q04"])
        self.assertEqual(len(report["preserve_slots"]), 9)
        self.assertNotIn("Q04", report["preserve_slots"])

    def test_receipt_slot_mismatch_is_rejected_before_reconciliation(self):
        provider, _ = self.generate_provider()

        def bad_provider(batch, batch_index):
            receipts = provider(batch, batch_index)
            if batch_index == 1:
                receipts[3] = dataclasses.replace(receipts[3], slot_id="Q05")
            return receipts

        with self.assertRaises(QueueIntegrityError):
            dispatch_slots(self.slots, bad_provider, operation=IMAGE_GENERATE)

    def test_instruct_edit_stays_singleton_until_cap_is_verified(self):
        provider, calls = self.singleton_edit_provider()
        receipts = dispatch_slots(self.slots, provider, operation=IMAGE_INSTRUCT_EDIT)
        report = reconcile(self.slots, receipts, operation=IMAGE_INSTRUCT_EDIT)
        self.assertEqual(calls, [f"Q{i:02d}" for i in range(1, 11)])
        self.assertEqual(report["expected_batch_plan"], [1] * 10)
        self.assertEqual(report["provider_call_count"], 10)
        self.assertEqual(report["state"], "T.20.PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
