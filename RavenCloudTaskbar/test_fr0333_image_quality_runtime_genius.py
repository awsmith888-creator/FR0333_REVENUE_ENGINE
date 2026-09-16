#!/usr/bin/env python3
import json
import pathlib
import unittest

from fr0333_image_quality_runtime_genius import validate

HERE = pathlib.Path(__file__).resolve().parent
GATE = HERE / "fr0333_image_quality_gate_0004.json"
RECEIPT = HERE / "fr0333_adobe_image_runtime_receipt_0001.json"
QUEUE_FAILURE = HERE / "fr0333_adobe_image_queue_runtime_receipt_0002.json"
QUEUE_RUNTIME = HERE / "fr0333_adobe_image_queue_runtime_receipt_0003.json"


class ImageQualityRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = json.loads(GATE.read_text(encoding="utf-8"))
        cls.receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        cls.queue_failure = json.loads(QUEUE_FAILURE.read_text(encoding="utf-8"))
        cls.queue_runtime = json.loads(QUEUE_RUNTIME.read_text(encoding="utf-8"))
        cls.report = validate(cls.gate, cls.receipt, cls.queue_failure, cls.queue_runtime)

    def test_sixteen_validation_gates_pass(self):
        self.assertEqual(self.report["total"], 16)
        self.assertEqual(self.report["passed"], 16)
        self.assertEqual(self.report["state"], "PASS")
        self.assertEqual(self.report["invariant"], "SIXTEEN.IN -> SIXTEEN.OUT")

    def test_ten_requested_means_ten_delivered(self):
        queue = self.gate["queue_contract"]
        self.assertEqual(queue["max_user_queue"], 10)
        self.assertTrue(queue["requested_count_must_equal_delivered_count"])
        self.assertTrue(queue["completion_claim_requires_all_slots_present"])
        self.assertEqual(queue["collage"], "REJECT")
        self.assertEqual(queue["contact_sheet"], "REJECT")

    def test_connected_runtime_caps_are_singleton(self):
        caps = self.gate["provider_batch_caps"]
        for operation in ("IMAGE_GENERATE", "IMAGE_INSTRUCT_EDIT"):
            cap = caps[operation]
            self.assertEqual(cap["schema_n_max"], 4)
            self.assertEqual(cap["max_variations_per_call"], 1)
            self.assertEqual(cap["ten_slot_chunk_plan"], [1] * 10)
            self.assertEqual(cap["ten_slot_provider_call_count"], 10)
            self.assertEqual(cap["state"], "T.20.BOUNDED_EFFECTIVE_CONNECTOR_CAP")
        self.assertTrue(caps["schema_cap_ne_effective_runtime_cap"])

    def test_native_dimension_drift_requires_normalization(self):
        defaults = self.gate["adobe_execution_defaults"]
        self.assertEqual(defaults["requested_generation_width"], 1080)
        self.assertEqual(defaults["observed_native_generation_width"], 1072)
        self.assertEqual(defaults["observed_native_generation_height"], 1920)
        self.assertEqual(defaults["delivery_width"], 1080)
        self.assertEqual(defaults["delivery_height"], 1920)
        self.assertTrue(defaults["dimension_normalization_required_when_native_drift_observed"])
        self.assertEqual(defaults["dimension_normalization_operation"], "image_crop_and_resize")

    def test_runtime_receipt_bindings_preserve_history_and_current_pass(self):
        bindings = self.gate["runtime_receipt_bindings"]
        self.assertEqual(bindings["connector_runtime"], "RavenCloudTaskbar/fr0333_adobe_image_runtime_receipt_0001.json")
        self.assertEqual(bindings["queue_failure_historical"], "RavenCloudTaskbar/fr0333_adobe_image_queue_runtime_receipt_0002.json")
        self.assertEqual(bindings["queue_runtime_bounded"], "RavenCloudTaskbar/fr0333_adobe_image_queue_runtime_receipt_0003.json")
        self.assertEqual(self.queue_failure["result"]["queue_contract"], "F.6.FAIL")
        self.assertEqual(self.queue_runtime["result"]["ten_slot_generate_runtime"], "T.20.PASS.BOUNDED")

    def test_q09_surgical_retry_preserves_nine_successes(self):
        queue = self.queue_runtime["queue"]
        self.assertEqual(queue["failed_first_pass_slots"], ["Q09"])
        self.assertEqual(queue["retried_slots"], ["Q09"])
        self.assertEqual(len(queue["preserved_successful_slots"]), 9)
        self.assertNotIn("Q09", queue["preserved_successful_slots"])
        self.assertEqual(queue["final_delivered_count"], 10)
        self.assertEqual(queue["final_visual_readback"], "PASS")

    def test_additional_runtime_witnesses_pass_bounded(self):
        witnesses = self.queue_runtime["additional_runtime_witnesses"]
        self.assertEqual(witnesses["human_generation"]["state"], "T.20")
        self.assertEqual(witnesses["single_instruct_edit"]["state"], "T.20")
        self.assertEqual(witnesses["lightroom_preset"]["state"], "T.20")
        self.assertEqual(witnesses["generated_asset_persistence"]["state"], "T.20")

    def test_quality_and_universal_scope_remain_held(self):
        self.assertEqual(self.queue_runtime["quality_promotion"]["state"], "U.21")
        self.assertEqual(self.queue_runtime["result"]["universal_adobe_surface"], "U.21.HOLD")
        self.assertEqual(self.gate["status_output_contract"]["QUALITY.PROMOTION"], "U.21.HOLD")
        self.assertEqual(self.gate["status_output_contract"]["UNIVERSAL.ADOBE.SURFACE"], "U.21.HOLD")

    def test_humanlock_and_double_chomp_remain_bound(self):
        self.assertTrue(self.gate["humanlock"])
        self.assertEqual(self.gate["golden_chain_route"].count("CHOMP"), 2)
        self.assertIn("USER.REJECT = OUTPUT.HOLD", self.gate["hard_boundaries"])
        self.assertIn("TEN.SLOT.RUNTIME.PASS != UNIVERSAL.ADOBE.PRODUCT.CAPACITY", self.gate["hard_boundaries"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
