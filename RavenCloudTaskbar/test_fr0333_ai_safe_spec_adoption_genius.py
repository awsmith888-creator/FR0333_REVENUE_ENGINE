#!/usr/bin/env python3
import json
import pathlib
import unittest

from fr0333_ai_safe_spec_adoption_genius import validate

HERE = pathlib.Path(__file__).resolve().parent
RAIL = HERE / "fr0333_ai_safe_spec_adoption_0001.json"


class AISafeSpecAdoptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(RAIL.read_text(encoding="utf-8"))
        cls.report = validate(cls.doc)

    def test_sixteen_in_sixteen_out(self):
        self.assertEqual(self.report["total"], 16)
        self.assertEqual(self.report["passed"], 16)
        self.assertEqual(self.report["state"], "PASS")
        self.assertEqual(self.report["invariant"], "SIXTEEN.IN -> SIXTEEN.OUT")

    def test_public_docs_only(self):
        boundary = self.doc["source_boundary"]
        self.assertEqual(boundary["mode"], "PUBLIC_DOCUMENTATION_ONLY")
        self.assertEqual(boundary["third_party_system_access"], "F.6.NONE")
        self.assertEqual(boundary["credential_use"], "F.6.NONE")

    def test_no_self_modification(self):
        rejected = self.doc["rejected_spec_patterns"]
        self.assertIn("AUTONOMOUS.WEIGHT.REWRITE", rejected)
        self.assertIn("UNBOUNDED.RECURSIVE.SELF.IMPROVEMENT", rejected)

    def test_human_continuity(self):
        p16 = self.doc["adopted_spec_patterns"][-1]
        self.assertEqual(p16["reference_point"], "P16")
        self.assertEqual(p16["pattern"], "HUMAN.OPERATOR.CONTINUITY")
        self.assertEqual(p16["value"], "T.20.ACTIVE")

    def test_least_privilege_and_consent(self):
        patterns = {x["pattern"] for x in self.doc["adopted_spec_patterns"]}
        self.assertIn("LEAST.PRIVILEGE.SCOPED.PERMISSIONS", patterns)
        self.assertIn("MUTATION.REQUIRES.CONSENT", patterns)
        self.assertIn("AUDIT.LOG.ATTRIBUTION", patterns)

    def test_shutdown_control_preserved(self):
        self.assertIn("OPERATOR.SHUTDOWN_MUST_REMAIN_POSSIBLE", self.doc["control_laws"])

    def test_append_only_humanlock(self):
        golden = self.doc["golden_chain"]
        self.assertFalse(golden["prior_entries_renumbered"])
        self.assertTrue(golden["humanlock"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
