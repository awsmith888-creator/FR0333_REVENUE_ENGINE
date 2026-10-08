import unittest
from fr0333_recovery import RecoveryController, State, Routing

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.c = RecoveryController()
        for lane in ("A.01", "P.01", "A.02", "P.02"):
            self.c.observe(lane, True, "observed-pass")
        self.c.observe("A.01", False, "fault-detected")

    def test_counts(self):
        self.assertEqual((len(self.c.active), len(self.c.passive)), (64, 64))
        self.assertNotIn("MR.00", self.c.active)

    def test_verified_bypass(self):
        r = self.c.recover("A.01", ["A.02"], lambda _: True)
        self.assertEqual(r.state, State.GREEN)
        self.assertEqual(self.c.active["A.01"].state, State.RED)
        self.assertEqual(self.c.active["A.01"].routing, Routing.QUARANTINED)

    def test_failed_regression(self):
        r = self.c.recover("A.01", ["A.02"], lambda _: False)
        self.assertEqual(r.state, State.YELLOW)
        self.assertTrue(any(b["state"] == "FAILED.BLOOM" for b in self.c.blooms))

    def test_partner_not_green(self):
        self.c.observe("P.02", False, "partner-fault")
        self.assertEqual(self.c.recover("A.01", ["A.02"], lambda _: True).state, State.YELLOW)

    def test_no_reentry(self):
        self.assertRaises(ValueError, self.c.recover, "A.02", ["A.01"], lambda _: True)

    def test_humanlock(self):
        self.assertRaises(PermissionError, self.c.retire, "A.01", False)
        self.c.retire("A.01", True)
        self.assertEqual(self.c.active["A.01"].routing, Routing.RETIRED)
        self.assertEqual(self.c.active["A.01"].state, State.RED)

    def test_no_false_green(self):
        self.assertEqual(self.c.recover("A.01", [], lambda _: True).state, State.YELLOW)

    def test_evidence_required(self):
        self.assertRaises(ValueError, self.c.observe, "A.03", False, "")

if __name__ == "__main__":
    unittest.main()
