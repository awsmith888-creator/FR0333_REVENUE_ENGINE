#!/usr/bin/env python3
import copy
import json
import unittest
from pathlib import Path

from fr0333_find_hub_remembered_state_boundary_genius import evaluate_record, validate_spec

HERE = Path(__file__).resolve().parent
SPEC = json.loads((HERE / "fr0333_find_hub_remembered_state_boundary_0001.json").read_text(encoding="utf-8"))


class FindHubRememberedStateBoundaryTests(unittest.TestCase):
    def test_spec_passes_all_twelve_gates(self):
        report = validate_spec(SPEC)
        self.assertEqual(report["state"], "PASS")
        self.assertEqual(report["passed"], 12)
        self.assertEqual(report["total"], 12)

    def test_missing_control_law_fails(self):
        doc = copy.deepcopy(SPEC)
        doc["control_laws"].remove("REMEMBERED_LOCATION_NE_CURRENT_VERIFIED_LOCATION")
        self.assertEqual(validate_spec(doc)["state"], "FAIL")

    def test_continuous_tracking_mutation_fails(self):
        doc = copy.deepcopy(SPEC)
        doc["remembered_item"]["sensor_assisted_capture"]["continuous_tracking"] = True
        self.assertEqual(validate_spec(doc)["state"], "FAIL")

    def test_terminal_grammar_mutation_fails(self):
        doc = copy.deepcopy(SPEC)
        doc["terminal_logic"]["T.99"] = doc["terminal_logic"].pop("T.20")
        self.assertEqual(validate_spec(doc)["state"], "FAIL")

    def test_valid_remembered_record_holds_present_location(self):
        record = {
            "ITEM_ID": "PASSPORT.1",
            "RECORDED_VALUE": "TOP_BEDROOM_DRAWER",
            "SOURCE_CLASS": "USER_ASSERTED",
            "RECORDED_AT": "2026-09-13T11:00:00-04:00",
            "READABLE": True,
            "CURRENT_PHYSICAL_STATE": "NOT_VERIFIED"
        }
        result = evaluate_record(record)
        self.assertEqual(result["record_state"], "T.20")
        self.assertEqual(result["present_state"], "U.21")

    def test_sensor_assisted_capture_is_not_live_tracking(self):
        record = {
            "ITEM_ID": "KEYS.1",
            "RECORDED_VALUE": "HOME_ADDRESS_AT_SAVE_TIME",
            "SOURCE_CLASS": "SENSOR_ASSISTED_CAPTURE",
            "RECORDED_AT": "2026-09-13T11:01:00-04:00",
            "READABLE": True,
            "CURRENT_PHYSICAL_STATE": "UNKNOWN"
        }
        result = evaluate_record(record)
        self.assertEqual(result["record_state"], "T.20")
        self.assertEqual(result["present_state"], "U.21")

    def test_current_location_requires_separate_runtime_evidence(self):
        record = {
            "ITEM_ID": "DEVICE.1",
            "RECORDED_VALUE": "CURRENT_LOCATION_CANDIDATE",
            "SOURCE_CLASS": "SENSOR_ASSISTED_CAPTURE",
            "RECORDED_AT": "2026-09-13T11:02:00-04:00",
            "READABLE": True,
            "CURRENT_PHYSICAL_STATE": "VERIFIED",
            "SEPARATE_RUNTIME_EVIDENCE": True
        }
        result = evaluate_record(record)
        self.assertEqual(result["record_state"], "T.20")
        self.assertEqual(result["present_state"], "T.20")

    def test_verified_label_without_runtime_evidence_still_holds(self):
        record = {
            "ITEM_ID": "ITEM.2",
            "RECORDED_VALUE": "KITCHEN_DRAWER",
            "SOURCE_CLASS": "USER_ASSERTED",
            "RECORDED_AT": "2026-09-13T11:03:00-04:00",
            "READABLE": True,
            "CURRENT_PHYSICAL_STATE": "VERIFIED",
            "SEPARATE_RUNTIME_EVIDENCE": False
        }
        result = evaluate_record(record)
        self.assertEqual(result["present_state"], "U.21")

    def test_contradicted_present_state_rejects_present_claim_only(self):
        record = {
            "ITEM_ID": "ITEM.3",
            "RECORDED_VALUE": "FRONT_DOOR",
            "SOURCE_CLASS": "USER_ASSERTED",
            "RECORDED_AT": "2026-09-13T11:04:00-04:00",
            "READABLE": True,
            "CURRENT_PHYSICAL_STATE": "CONTRADICTED"
        }
        result = evaluate_record(record)
        self.assertEqual(result["record_state"], "T.20")
        self.assertEqual(result["present_state"], "F.6")

    def test_invalid_source_class_rejects(self):
        record = {
            "ITEM_ID": "ITEM.4",
            "RECORDED_VALUE": "DESK",
            "SOURCE_CLASS": "LIVE_TRACKER",
            "RECORDED_AT": "2026-09-13T11:05:00-04:00",
            "READABLE": True,
            "CURRENT_PHYSICAL_STATE": "UNKNOWN"
        }
        result = evaluate_record(record)
        self.assertEqual(result["record_state"], "F.6")
        self.assertEqual(result["present_state"], "F.6")


if __name__ == "__main__":
    unittest.main()
