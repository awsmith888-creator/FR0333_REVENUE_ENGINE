#!/usr/bin/env python3
import json
import pathlib
import unittest

from fr0333_image_quality_runtime_genius import validate

HERE = pathlib.Path(__file__).resolve().parent
GATE = HERE / "fr0333_image_quality_gate_0004.json"
RECEIPT = HERE / "fr0333_adobe_image_runtime_receipt_0001.json"
QUEUE_RECEIPT = HERE / "fr0333_adobe_image_queue_runtime_receipt_0002.json"


class ImageQualityRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = json.loads(GATE.read_text(encoding="utf-8"))
        cls.receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        cls.queue_receipt = json.loads(QUEUE_RECEIPT.read_text(encoding="utf-8"))
        cls.report = validate(cls.gate, cls.receipt, cls.queue_receipt)

    def test_sixteen_validation_gates_pass_not_queue_throughput(self):
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
        self.assertEqual(queue["multi_panel"], "REJECT")

    def test_provider_caps_are_operation_specific(self):
        caps = self.gate["provider_batch_caps"]
        generate = caps["IMAGE_GENERATE"]
        edit = caps["IMAGE_INSTRUCT_EDIT"]
        self.assertEqual(generate["state"], "T.20.VERIFIED_PROVIDER_CAP")
        self.assertEqual(generate["max_variations_per_call"], 4)
        self.assertEqual(generate["ten_slot_chunk_plan"], [4, 4, 2])
        self.assertEqual(sum(generate["ten_slot_chunk_plan"]), 10)
        self.assertEqual(edit["state"], "U.21.NOT_ESTABLISHED")
        self.assertEqual(edit["max_variations_per_call"], "U.21.NOT_ESTABLISHED")
        self.assertEqual(edit["ten_slot_chunk_plan"], "U.21.NOT_ESTABLISHED")
        self.assertEqual(caps["cap_scope_rule"], "PROVIDER_CAP_IS_OPERATION_SPECIFIC")

    def test_missing_slots_retry_without_replacing_successes(self):
        queue = self.gate["queue_contract"]
        caps = self.gate["provider_batch_caps"]
        recovery = self.gate["failure_recovery"]
        self.assertEqual(queue["empty_provider_response"], "RETRY_MISSING_SLOT_ONLY")
        self.assertEqual(queue["partial_provider_response"], "RETRY_MISSING_SLOTS_ONLY")
        self.assertTrue(caps["successful_slots_must_not_be_regenerated"])
        self.assertTrue(recovery["no_silent_success"])

    def test_human_realism_rejects_artificial_geometry(self):
        human = self.gate["human_realism_gate"]
        required = set(human["human_subject_request_requires"])
        self.assertIn("CORRECT_LIMB_COUNT", required)
        self.assertIn("JOINT_CONTINUITY", required)
        self.assertIn("NATURAL_HAND_FINGER_STRUCTURE", required)
        self.assertIn("NATURAL_FOOT_TOE_STRUCTURE", required)
        self.assertEqual(human["rubber_limb_or_fused_body_geometry"], "REJECT")
        self.assertEqual(human["mannequin_or_plastic_skin"], "REJECT")

    def test_slot_variation_is_mandatory(self):
        required = set(self.gate["prompt_compile"]["per_slot_variation_required"])
        self.assertEqual(
            required,
            {"SCENERY", "WARDROBE", "POSE_OR_ACTION", "CAMERA_POSITION", "LIGHTING_SETUP", "COMPOSITION"},
        )

    def test_sixteen_photorealism_dimensions_preserve_0003(self):
        dimensions = self.gate["photorealism_dimensions"]
        self.assertEqual(len(dimensions), 16)
        self.assertIn("ANATOMY.FACE.HANDS.FEET", dimensions)
        self.assertIn("VEHICLE.MECHANICAL.GEOMETRY", dimensions)
        self.assertIn("LOAD.BALANCE.CONTACT.PHYSICS", dimensions)
        self.assertIn("POSE.WEIGHT.CONTACT", dimensions)
        self.assertIn("SCENE.UNIQUENESS", dimensions)
        self.assertIn("VISUAL.READBACK", dimensions)
        self.assertEqual(
            set(self.gate["preserved_from_0003"]),
            {"VEHICLE.MECHANICAL.GEOMETRY", "LOAD.BALANCE.CONTACT.PHYSICS"},
        )

    def test_promotion_gate_preserves_vehicle_and_physics_thresholds(self):
        promo = self.gate["promotion_gate"]
        self.assertGreaterEqual(promo["identity_reference_min"], 8)
        self.assertGreaterEqual(promo["vehicle_geometry_reference_min"], 8)
        self.assertGreaterEqual(promo["physics_reference_min"], 8)
        self.assertGreaterEqual(promo["anatomy_reference_min"], 8)
        self.assertGreaterEqual(promo["scene_uniqueness_reference_min"], 8)

    def test_adobe_defaults_are_quality_first_9_16(self):
        defaults = self.gate["adobe_execution_defaults"]
        self.assertEqual(defaults["generation_prompt_reasoner"], "quality")
        self.assertEqual(defaults["edit_prompt_reasoner"], "quality")
        self.assertEqual(defaults["target_aspect_ratio"], "9:16")
        self.assertEqual(defaults["target_resolution_level"], "4MP")
        self.assertEqual(defaults["output_format"], "png")

    def test_runtime_receipt_bindings_include_both_witnesses(self):
        bindings = self.gate["runtime_receipt_bindings"]
        self.assertEqual(bindings["connector_runtime"], "RavenCloudTaskbar/fr0333_adobe_image_runtime_receipt_0001.json")
        self.assertEqual(bindings["queue_failure"], "RavenCloudTaskbar/fr0333_adobe_image_queue_runtime_receipt_0002.json")

    def test_runtime_receipt_stays_bounded(self):
        self.assertEqual(self.receipt["provider_receipt"]["execution_state"], "PASS_RUNTIME")
        self.assertEqual(self.receipt["result"]["external_adobe_full_capacity"], "NOT_ESTABLISHED")
        self.assertEqual(self.receipt["readback"]["quality_promotion_state"], "U.21.HOLD")
        self.assertEqual(self.receipt["readback"]["user_acceptance"], "NOT_OBSERVED")

    def test_observed_contact_sheet_failure_is_preserved(self):
        q = self.queue_receipt
        self.assertEqual(q["provider"], "ADOBE_FIREFLY_IMAGE_INSTRUCT_EDIT")
        self.assertEqual(q["provider_receipt"]["execution_state"], "T.20.PASS")
        self.assertEqual(q["provider_receipt"]["api_variation_count"], 1)
        self.assertTrue(q["visual_readback"]["single_output_contains_multiple_panels"])
        self.assertTrue(q["visual_readback"]["contact_sheet_or_collage_detected"])
        self.assertFalse(q["visual_readback"]["independent_full_canvas_delivery"])
        self.assertEqual(q["result"]["queue_contract"], "F.6.FAIL")
        self.assertEqual(q["result"]["user_delivery"], "F.6.FAIL")
        self.assertEqual(q["result"]["external_ten_slot_capacity"], "U.21.NOT_ESTABLISHED")

    def test_user_reject_and_humanlock_override(self):
        self.assertTrue(self.gate["humanlock"])
        self.assertTrue(self.gate["promotion_gate"]["user_reject_overrides_promotion"])
        self.assertIn("USER.REJECT = OUTPUT.HOLD", self.gate["hard_boundaries"])
        self.assertIn("PROVIDER.CAP.IS.OPERATION.SPECIFIC", self.gate["hard_boundaries"])
        self.assertIn("IMAGE.INSTRUCT.EDIT.CAP = U.21.UNTIL.VERIFIED", self.gate["hard_boundaries"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
