#!/usr/bin/env python3
import dataclasses
import unittest

from fr0333_image_queue_runtime import (
    IMAGE_GENERATE,
    IMAGE_INSTRUCT_EDIT,
    OBSERVED_NATIVE_GENERATE_HEIGHT,
    OBSERVED_NATIVE_GENERATE_WIDTH,
    QueueIntegrityError,
    SlotReceipt,
    compile_slots,
    dispatch_slots,
    reconcile,
)


class ImageQueueRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.scenes = [
            {"scene_contract": f"distinct scene {i}", "input_reference_ids": [f"ref-{i}"]}
            for i in range(1, 11)
        ]
        self.slots = compile_slots(self.scenes)

    @staticmethod
    def make_receipt(slot, *, operation, request_id, batch_index, width=1080, height=1920):
        n = int(slot.slot_id[1:])
        return SlotReceipt(
            slot_id=slot.slot_id,
            intent_hash=slot.intent_hash,
            scene_contract=slot.scene_contract,
            reference_policy=slot.reference_policy,
            input_reference_ids=slot.input_reference_ids,
            output_asset_id=f"asset-{n:02d}",
            width=width,
            height=height,
            aspect_ratio="9:16",
            provider_request_id=request_id,
            provider_variation_index=1,
            batch_index=batch_index,
            batch_size=1,
            visual_fingerprint=f"fingerprint-{n:02d}",
            readback_state="PASS",
            anatomy_readback="PASS",
            realism_readback="PASS",
            clothing_variance_readback="PASS",
            intent_alignment_readback="PASS",
            user_state="NOT_OBSERVED",
            operation=operation,
        )

    def singleton_provider(self, operation=IMAGE_GENERATE, *, native_dimensions=False):
        calls = []

        def provider(slot):
            batch_index = len(calls) + 1
            calls.append(slot.slot_id)
            width = OBSERVED_NATIVE_GENERATE_WIDTH if native_dimensions else 1080
            height = OBSERVED_NATIVE_GENERATE_HEIGHT if native_dimensions else 1920
            return self.make_receipt(
                slot,
                operation=operation,
                request_id=f"request-{operation.lower()}-{batch_index:02d}",
                batch_index=batch_index,
                width=width,
                height=height,
            )

        return provider, calls

    def test_ten_slot_generate_dispatch_uses_effective_singleton_cap(self):
        provider, calls = self.singleton_provider(IMAGE_GENERATE)
        receipts = dispatch_slots(self.slots, provider, operation=IMAGE_GENERATE)
        report = reconcile(self.slots, receipts, operation=IMAGE_GENERATE)
        self.assertEqual(calls, [f"Q{i:02d}" for i in range(1, 11)])
        self.assertEqual(report["expected_batch_plan"], [1] * 10)
        self.assertEqual(report["provider_call_count"], 10)
        self.assertEqual(report["expected_provider_call_count"], 10)
        self.assertEqual(report["requested_count"], 10)
        self.assertEqual(report["output_count"], 10)
        self.assertEqual(report["unique_output_asset_ids"], 10)
        self.assertEqual(report["unique_provider_output_coordinates"], 10)
        self.assertEqual(report["unique_visual_fingerprints"], 10)
        self.assertEqual(report["state"], "T.20.PASS")

    def test_native_1072_1920_requires_dimension_normalization(self):
        provider, _ = self.singleton_provider(IMAGE_GENERATE, native_dimensions=True)
        native_receipts = dispatch_slots(self.slots, provider, operation=IMAGE_GENERATE)
        native_report = reconcile(self.slots, native_receipts, operation=IMAGE_GENERATE)
        self.assertEqual(native_report["state"], "F.6.REJECT")
        self.assertEqual(native_report["exact_dimension_failures"], [f"Q{i:02d}" for i in range(1, 11)])

        normalized = [dataclasses.replace(r, width=1080, height=1920) for r in native_receipts]
        normalized_report = reconcile(self.slots, normalized, operation=IMAGE_GENERATE)
        self.assertEqual(normalized_report["state"], "T.20.PASS")
        self.assertEqual(normalized_report["exact_dimension_failures"], [])

    def test_per_slot_readback_fields_are_independent_gates(self):
        for field in (
            "anatomy_readback", "realism_readback",
            "clothing_variance_readback", "intent_alignment_readback",
        ):
            provider, _ = self.singleton_provider(IMAGE_GENERATE)
            receipts = dispatch_slots(self.slots, provider, operation=IMAGE_GENERATE)
            receipts[2] = dataclasses.replace(receipts[2], **{field: "FAIL"})
            report = reconcile(self.slots, receipts, operation=IMAGE_GENERATE)
            self.assertEqual(report["state"], "F.6.REJECT", field)
            self.assertIn("Q03", report["failed_slots"], field)
            self.assertIn(field, report["readback_failures"]["Q03"], field)

    def test_count_mismatch_fails_closed(self):
        provider, _ = self.singleton_provider(IMAGE_GENERATE)
        receipts = dispatch_slots(self.slots, provider, operation=IMAGE_GENERATE)[:-1]
        report = reconcile(self.slots, receipts, operation=IMAGE_GENERATE)
        self.assertEqual(report["state"], "F.6.REJECT")
        self.assertEqual(report["missing_slots"], ["Q10"])
        self.assertEqual(report["retry_slots"], ["Q10"])

    def test_duplicate_output_asset_is_rejected(self):
        provider, _ = self.singleton_provider(IMAGE_GENERATE)
        receipts = dispatch_slots(self.slots, provider, operation=IMAGE_GENERATE)
        receipts[9] = dataclasses.replace(receipts[9], output_asset_id=receipts[0].output_asset_id)
        report = reconcile(self.slots, receipts, operation=IMAGE_GENERATE)
        self.assertEqual(report["state"], "F.6.REJECT")
        self.assertTrue(report["duplicate_output_assets"])

    def test_duplicate_visual_fingerprint_is_rejected(self):
        provider, _ = self.singleton_provider(IMAGE_GENERATE)
        receipts = dispatch_slots(self.slots, provider, operation=IMAGE_GENERATE)
        receipts[8] = dataclasses.replace(receipts[8], visual_fingerprint=receipts[0].visual_fingerprint)
        report = reconcile(self.slots, receipts, operation=IMAGE_GENERATE)
        self.assertEqual(report["state"], "F.6.REJECT")
        self.assertTrue(report["duplicate_visual_fingerprints"])

    def test_contact_sheet_slot_is_rejected(self):
        provider, _ = self.singleton_provider(IMAGE_GENERATE)
        receipts = dispatch_slots(self.slots, provider, operation=IMAGE_GENERATE)
        receipts[3] = dataclasses.replace(receipts[3], collage_detected=True, readback_state="FAIL")
        report = reconcile(self.slots, receipts, operation=IMAGE_GENERATE)
        self.assertEqual(report["state"], "F.6.REJECT")
        self.assertEqual(report["collage_slots"], ["Q04"])
        self.assertEqual(report["retry_slots"], ["Q04"])

    def test_failed_q09_retries_q09_only(self):
        provider, _ = self.singleton_provider(IMAGE_GENERATE)
        receipts = dispatch_slots(self.slots, provider, operation=IMAGE_GENERATE)
        receipts[8] = dataclasses.replace(
            receipts[8], execution_state="FAIL_RUNTIME", intent_alignment_readback="FAIL"
        )
        report = reconcile(self.slots, receipts, operation=IMAGE_GENERATE)
        self.assertEqual(report["state"], "F.6.REJECT")
        self.assertEqual(report["retry_slots"], ["Q09"])
        self.assertEqual(len(report["preserve_slots"]), 9)
        self.assertNotIn("Q09", report["preserve_slots"])

    def test_receipt_slot_mismatch_is_rejected_before_reconciliation(self):
        provider, _ = self.singleton_provider(IMAGE_GENERATE)

        def bad_provider(slot):
            receipt = provider(slot)
            if slot.slot_id == "Q04":
                return dataclasses.replace(receipt, slot_id="Q05")
            return receipt

        with self.assertRaises(QueueIntegrityError):
            dispatch_slots(self.slots, bad_provider, operation=IMAGE_GENERATE)

    def test_instruct_edit_uses_observed_singleton_cap(self):
        provider, calls = self.singleton_provider(IMAGE_INSTRUCT_EDIT)
        receipts = dispatch_slots(self.slots, provider, operation=IMAGE_INSTRUCT_EDIT)
        report = reconcile(self.slots, receipts, operation=IMAGE_INSTRUCT_EDIT)
        self.assertEqual(calls, [f"Q{i:02d}" for i in range(1, 11)])
        self.assertEqual(report["expected_batch_plan"], [1] * 10)
        self.assertEqual(report["provider_call_count"], 10)
        self.assertEqual(report["state"], "T.20.PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
