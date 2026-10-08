import json
import unittest
from copy import deepcopy
from pathlib import Path

from RavenCloudTaskbar.mariah_carey_chomp import (
    MODULE_ID,
    PARENT_ID,
    compile_adobe_reference_context,
    validate_register,
)


FIXTURE = Path(__file__).with_name("mariah_carey_chomp_register.json")


class MariahCareyChompTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_module_and_parent_binding(self):
        self.assertEqual(self.data["module_id"], MODULE_ID)
        self.assertEqual(self.data["parent_id"], PARENT_ID)

    def test_register_validates_sixty_bits(self):
        receipt = validate_register(self.data)
        self.assertEqual(receipt["statistical_bit_count"], 51)
        self.assertEqual(receipt["money_bit_count"], 9)
        self.assertEqual(receipt["total_bit_count"], 60)

    def test_seven_holds_remain_unpromoted(self):
        receipt = validate_register(self.data)
        self.assertEqual(receipt["hold_count"], 7)
        self.assertTrue(all(item["promotion"] == "HOLD" for item in self.data["holds"]))

    def test_human_line_has_nine_noncausal_periods(self):
        receipt = validate_register(self.data)
        self.assertEqual(receipt["human_line_period_count"], 9)
        self.assertTrue(all(item["causal_claim"] is False for item in self.data["human_line"]))

    def test_duplicate_bit_rejected(self):
        changed = deepcopy(self.data)
        changed["statistical_bits"][-1] = changed["statistical_bits"][0]
        with self.assertRaises(ValueError):
            validate_register(changed)

    def test_unknown_source_rejected(self):
        changed = deepcopy(self.data)
        changed["source_routes"]["MC.BIRTH"] = ["SOURCE.DOES.NOT.EXIST"]
        with self.assertRaises(ValueError):
            validate_register(changed)

    def test_unsupported_evidence_state_rejected(self):
        changed = deepcopy(self.data)
        changed["statistical_bits"][0] = "MC.BIRTH.DATE.1969_03_27.PROVEN"
        with self.assertRaises(ValueError):
            validate_register(changed)

    def test_reference_pack_does_not_claim_global_position(self):
        changed = deepcopy(self.data)
        changed["golden_chain_binding"] = "GC.SB.0028"
        with self.assertRaises(ValueError):
            validate_register(changed)

    def test_four_inputs_compile_to_four_individual_slots(self):
        compiled = compile_adobe_reference_context(self.data, requested_count=4, input_count=4)
        self.assertEqual([item["slot"] for item in compiled["queue"]], ["Q01", "Q02", "Q03", "Q04"])
        self.assertTrue(all(item["output_count"] == 1 for item in compiled["queue"]))
        self.assertTrue(all(item["canvas"] == "9:16" for item in compiled["queue"]))
        self.assertTrue(all(item["collage"] is False for item in compiled["queue"]))

    def test_input_output_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            compile_adobe_reference_context(self.data, requested_count=4, input_count=3)

    def test_queue_bounds_rejected(self):
        with self.assertRaises(ValueError):
            compile_adobe_reference_context(self.data, requested_count=0, input_count=0)
        with self.assertRaises(ValueError):
            compile_adobe_reference_context(self.data, requested_count=11, input_count=11)

    def test_boolean_count_rejected(self):
        with self.assertRaises(TypeError):
            compile_adobe_reference_context(self.data, requested_count=True, input_count=1)

    def test_hold_bits_excluded_from_safe_facts(self):
        compiled = compile_adobe_reference_context(self.data, requested_count=1, input_count=1)
        self.assertEqual(len(compiled["excluded_holds"]), 3)
        self.assertTrue(all(not item["id"].endswith(".HOLD") for item in compiled["safe_facts"]))

    def test_reference_pack_ne_identity_authorization(self):
        compiled = compile_adobe_reference_context(self.data, requested_count=1, input_count=1)
        rules = compiled["visual_prompt_rules"]
        self.assertTrue(rules["reference_pack_is_not_identity_authorization"])
        self.assertTrue(rules["attached_image_controls_identity"])

    def test_runtime_and_money_boundaries(self):
        receipt = validate_register(self.data)
        self.assertFalse(receipt["external_adobe_runtime_claimed"])
        self.assertFalse(self.data["adobe_binding"]["money_aggregation_allowed"])


if __name__ == "__main__":
    unittest.main()
