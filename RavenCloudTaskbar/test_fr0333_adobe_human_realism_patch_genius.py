#!/usr/bin/env python3
import copy
import json
import pathlib
import unittest

from fr0333_adobe_human_realism_patch_genius import validate

HERE = pathlib.Path(__file__).resolve().parent
SPEC = HERE / "fr0333_adobe_human_realism_patch_0004.json"
MANIFEST = HERE / "fr0333_adobe_human_realism_manifest_0004.json"


class AdobeHumanRealismPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads(SPEC.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_reference_manifest_passes(self):
        report = validate(self.spec, self.manifest)
        self.assertEqual(report["state"], "PASS")
        self.assertEqual(report["passed"], report["total"])
        self.assertEqual(report["total"], 16)

    def test_ten_in_ten_out(self):
        self.assertEqual(self.manifest["requested_count"], 10)
        self.assertEqual(len(self.manifest["slots"]), 10)
        self.assertEqual([s["slot_id"] for s in self.manifest["slots"]], [f"Q{i:02d}" for i in range(1, 11)])

    def test_repeated_scene_fails_diversity(self):
        broken = copy.deepcopy(self.manifest)
        broken["slots"][1]["scene"] = broken["slots"][0]["scene"]
        report = validate(self.spec, broken)
        gate = next(r for r in report["results"] if r["gate"] == "M4.SEMANTIC.DIVERSITY")
        self.assertEqual(gate["state"], "FAIL")
        self.assertEqual(report["state"], "FAIL")

    def test_repeated_wardrobe_fails_diversity(self):
        broken = copy.deepcopy(self.manifest)
        broken["slots"][4]["wardrobe"] = broken["slots"][3]["wardrobe"]
        report = validate(self.spec, broken)
        gate = next(r for r in report["results"] if r["gate"] == "M4.SEMANTIC.DIVERSITY")
        self.assertEqual(gate["state"], "FAIL")

    def test_repeated_camera_setup_fails_diversity(self):
        broken = copy.deepcopy(self.manifest)
        broken["slots"][8]["camera_setup"] = broken["slots"][7]["camera_setup"]
        report = validate(self.spec, broken)
        gate = next(r for r in report["results"] if r["gate"] == "M4.SEMANTIC.DIVERSITY")
        self.assertEqual(gate["state"], "FAIL")

    def test_count_mismatch_fails(self):
        broken = copy.deepcopy(self.manifest)
        broken["slots"].pop()
        report = validate(self.spec, broken)
        gate = next(r for r in report["results"] if r["gate"] == "M1.COUNT.INVARIANT")
        self.assertEqual(gate["state"], "FAIL")

    def test_slot_sequence_gap_fails(self):
        broken = copy.deepcopy(self.manifest)
        broken["slots"][5]["slot_id"] = "Q09"
        report = validate(self.spec, broken)
        gate = next(r for r in report["results"] if r["gate"] == "M2.SLOT.SEQUENCE")
        self.assertEqual(gate["state"], "FAIL")

    def test_missing_required_field_fails(self):
        broken = copy.deepcopy(self.manifest)
        del broken["slots"][2]["lighting"]
        report = validate(self.spec, broken)
        gate = next(r for r in report["results"] if r["gate"] == "M3.REQUIRED.FIELDS")
        self.assertEqual(gate["state"], "FAIL")

    def test_diversity_defaults_to_distinct_cast(self):
        broken = copy.deepcopy(self.manifest)
        broken["slots"][0]["identity_mode"] = "CONTINUITY_CAST"
        report = validate(self.spec, broken)
        gate = next(r for r in report["results"] if r["gate"] == "M5.IDENTITY.MODE")
        self.assertEqual(gate["state"], "FAIL")

    def test_humanlock_and_runtime_boundary(self):
        self.assertTrue(self.spec["humanlock"])
        self.assertEqual(self.spec["runtime_boundary"]["external_adobe_runtime"], "NOT_ESTABLISHED_BY_THIS_PATCH")
        self.assertIn("THIS.PATCH != ADOBE.INTERNAL.MODEL.MODIFICATION", self.spec["hard_boundaries"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
