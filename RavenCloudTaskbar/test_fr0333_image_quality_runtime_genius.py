#!/usr/bin/env python3
import json
import pathlib
import unittest

from fr0333_image_quality_runtime_genius import validate

HERE = pathlib.Path(__file__).resolve().parent
GATE = HERE / "fr0333_image_quality_gate_0004.json"
RECEIPT = HERE / "fr0333_adobe_image_runtime_receipt_0001.json"


class ImageQualityRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = json.loads(GATE.read_text(encoding="utf-8"))
        cls.receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        cls.report = validate(cls.gate, cls.receipt)

    def test_sixteen_in_sixteen_out(self):
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

    def test_firefly_ten_slot_plan_is_4_4_2(self):
        caps = self.gate["provider_batch_caps"]
        self.assertEqual(caps["ADOBE_FIREFLY_IMAGE_GENERATE_MAX_VARIATIONS_PER_CALL"], 4)
        self.assertEqual(caps["TEN_SLOT_CHUNK_PLAN"], [4, 4, 2])
        self.assertEqual(sum(caps["TEN_SLOT_CHUNK_PLAN"]), 10)

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

    def test_fourteen_photorealism_dimensions(self):
        self.assertEqual(len(self.gate["photorealism_dimensions"]), 14)
        self.assertIn("ANATOMY.FACE.HANDS.FEET", self.gate["photorealism_dimensions"])
        self.assertIn("POSE.WEIGHT.CONTACT", self.gate["photorealism_dimensions"])
        self.assertIn("SCENE.UNIQUENESS", self.gate["photorealism_dimensions"])
        self.assertIn("VISUAL.READBACK", self.gate["photorealism_dimensions"])

    def test_adobe_defaults_are_quality_first_9_16(self):
        defaults = self.gate["adobe_execution_defaults"]
        self.assertEqual(defaults["generation_prompt_reasoner"], "quality")
        self.assertEqual(defaults["edit_prompt_reasoner"], "quality")
        self.assertEqual(defaults["target_aspect_ratio"], "9:16")
        self.assertEqual(defaults["target_resolution_level"], "4MP")
        self.assertEqual(defaults["output_format"], "png")

    def test_runtime_receipt_stays_bounded(self):
        self.assertEqual(self.receipt["provider_receipt"]["execution_state"], "PASS_RUNTIME")
        self.assertEqual(self.receipt["result"]["external_adobe_full_capacity"], "NOT_ESTABLISHED")
        self.assertEqual(self.receipt["readback"]["quality_promotion_state"], "U.21.HOLD")
        self.assertEqual(self.receipt["readback"]["user_acceptance"], "NOT_OBSERVED")

    def test_user_reject_and_humanlock_override(self):
        self.assertTrue(self.gate["humanlock"])
        self.assertTrue(self.gate["promotion_gate"]["user_reject_overrides_promotion"])
        self.assertIn("USER.REJECT = OUTPUT.HOLD", self.gate["hard_boundaries"])
        self.assertIn("EMPTY.RESPONSE != SUCCESS", self.gate["hard_boundaries"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
