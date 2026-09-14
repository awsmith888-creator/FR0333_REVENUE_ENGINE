import copy
import json
import unittest
from pathlib import Path

from fr0333_taskbars_stronghold_validate import validate

ROOT = Path(__file__).resolve().parent

class TaskbarsStrongholdTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.taskbars = json.loads((ROOT / "taskbars.json").read_text(encoding="utf-8"))
        cls.manifest = json.loads((ROOT / "fr0333_taskbars_stronghold_root_0001.json").read_text(encoding="utf-8"))
        cls.schema = json.loads((ROOT / "fr0333_taskbars_stronghold_0001.schema.json").read_text(encoding="utf-8"))

    def test_01_canonical_stronghold_passes(self):
        self.assertEqual(validate(copy.deepcopy(self.taskbars), self.manifest, self.schema), [])

    def test_02_duplicate_id_rejected(self):
        candidate = copy.deepcopy(self.taskbars)
        candidate["taskbars"][-1]["id"] = candidate["taskbars"][0]["id"]
        self.assertTrue(any("DUPLICATE_ID" in e or "ID_SET" in e for e in validate(candidate, self.manifest, self.schema)))

    def test_03_humanlock_downgrade_rejected(self):
        candidate = copy.deepcopy(self.taskbars)
        candidate["humanlock_can_be_disabled"] = True
        self.assertTrue(validate(candidate, self.manifest, self.schema))

    def test_04_find_hub_removal_rejected(self):
        candidate = copy.deepcopy(self.taskbars)
        candidate["taskbars"] = [r for r in candidate["taskbars"] if r["id"] != "TB.FR0333.FIND.HUB.REMEMBERED.STATE.BOUNDARY.0001"]
        self.assertTrue(validate(candidate, self.manifest, self.schema))

    def test_05_pr17_import_mutation_rejected(self):
        candidate = copy.deepcopy(self.taskbars)
        for record in candidate["taskbars"]:
            if record["id"] == "TB.FR0333.AI.IMAGE.TOOL.METRICS.0001":
                record["state"] = "MUTATED"
        self.assertTrue(any("RECORD_HASH:TB.FR0333.AI.IMAGE.TOOL.METRICS.0001" in e for e in validate(candidate, self.manifest, self.schema)))

    def test_06_pr19_import_mutation_rejected(self):
        candidate = copy.deepcopy(self.taskbars)
        for record in candidate["taskbars"]:
            if record["id"] == "TB.FR0333.GC.SB.0028.HUMAN.CENTERED.EVIDENCE":
                record["next_action"] = "BYPASS"
        self.assertTrue(any("RECORD_HASH:TB.FR0333.GC.SB.0028.HUMAN.CENTERED.EVIDENCE" in e for e in validate(candidate, self.manifest, self.schema)))

    def test_07_main_record_mutation_rejected(self):
        candidate = copy.deepcopy(self.taskbars)
        candidate["taskbars"][0]["state"] = "MUTATED"
        self.assertTrue(any("RECORD_HASH:TB.REPARATION.UPDATE" in e for e in validate(candidate, self.manifest, self.schema)))

    def test_08_unexpected_record_count_rejected(self):
        candidate = copy.deepcopy(self.taskbars)
        candidate["taskbars"].append(copy.deepcopy(candidate["taskbars"][0]))
        self.assertTrue(validate(candidate, self.manifest, self.schema))

    def test_09_metadata_change_rejected(self):
        candidate = copy.deepcopy(self.taskbars)
        candidate["version"] = "1.0.10"
        self.assertTrue(any("METADATA:version:MISMATCH" in e for e in validate(candidate, self.manifest, self.schema)))

    def test_10_manifest_stays_at_humanlock_hold(self):
        self.assertEqual(self.manifest["truth_state"], "U.21")
        self.assertEqual(self.manifest["truth_qualifier"], "HOLD_AT_HUMANLOCK")

if __name__ == "__main__":
    unittest.main()
