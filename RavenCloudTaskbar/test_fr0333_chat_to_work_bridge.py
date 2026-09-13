#!/usr/bin/env python3
import unittest

from fr0333_chat_to_work_bridge import detect_lane, tool_gate, validate_source_bound_image_batch


class ChatToWorkBridgeTests(unittest.TestCase):
    def test_stop_image_and_write_bridge_routes_repository(self):
        receipt = detect_lane(
            "Stop trying to make pictures. Write the bridge into the system.",
            prior_lane="IMAGE_GENERATION",
        )
        self.assertEqual(receipt.compiled_lane, "REPOSITORY_WRITE")
        self.assertEqual(receipt.cancelled_lane, "IMAGE_GENERATION")
        self.assertFalse(receipt.image_tool_allowed)
        self.assertTrue(receipt.github_write_allowed)
        self.assertEqual(tool_gate(receipt, "IMAGE_GENERATION"), "F.6")
        self.assertEqual(tool_gate(receipt, "GITHUB_WRITE"), "T.20")

    def test_current_image_generation_intent_routes_image_lane(self):
        receipt = detect_lane("Create ten different images from these pictures.")
        self.assertEqual(receipt.compiled_lane, "IMAGE_GENERATION")
        self.assertTrue(receipt.image_tool_allowed)
        self.assertFalse(receipt.github_write_allowed)

    def test_image_edit_routes_edit_lane(self):
        receipt = detect_lane("Fix this image and remove the background.")
        self.assertEqual(receipt.compiled_lane, "IMAGE_EDIT")
        self.assertTrue(receipt.image_tool_allowed)

    def test_research_routes_research_lane(self):
        receipt = detect_lane("Look up the statistics and verify the history.")
        self.assertEqual(receipt.compiled_lane, "RESEARCH")
        self.assertFalse(receipt.image_tool_allowed)
        self.assertFalse(receipt.github_write_allowed)

    def test_source_bound_queue_requires_equal_counts(self):
        self.assertEqual(validate_source_bound_image_batch(10, 10)["state"], "T.20")
        self.assertEqual(validate_source_bound_image_batch(9, 10)["state"], "F.6")
        self.assertEqual(validate_source_bound_image_batch(10, 9)["state"], "F.6")

    def test_no_cross_lane_fallthrough(self):
        receipt = detect_lane("Write this bridge into the GitHub repository.")
        self.assertFalse(receipt.cross_lane_fallthrough_allowed)
        self.assertEqual(tool_gate(receipt, "IMAGE_GENERATION"), "F.6")


if __name__ == "__main__":
    unittest.main()
