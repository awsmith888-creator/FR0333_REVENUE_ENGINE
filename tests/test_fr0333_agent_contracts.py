"""49 vendor-contract tests plus 3 cross-vendor invariants: 52 new tests."""
import unittest
from fr0333_agent_simulator import ManualAgentSimulator, VENDORS, TABS, PIN, STEPS

class AgentContractTests(unittest.TestCase):
    pass

def build_test(vendor, case):
    def check(self):
        agent = ManualAgentSimulator(vendor)
        if case == "pin":
            self.assertEqual(agent.retrieve_pin(), PIN)
        elif case == "tab":
            self.assertEqual(agent.route_tab(), TABS[vendor])
        elif case == "directions":
            self.assertEqual(agent.directions(), STEPS)
        elif case == "receipt":
            receipt = agent.execute()
            self.assertEqual(receipt.vendor, vendor)
            self.assertEqual(len(receipt.digest), 64)
            self.assertEqual(receipt.state, "T.20.SIMULATED")
        elif case == "humanlock":
            with self.assertRaises(PermissionError):
                agent.execute("DEPLOY")
            self.assertEqual(agent.history, [])
        elif case == "restore":
            receipt = agent.execute()
            restored = ManualAgentSimulator(vendor)
            restored.restore(agent.snapshot())
            self.assertEqual(restored.history, [receipt])
        elif case == "tamper":
            agent.execute()
            snapshot = agent.snapshot()
            snapshot[0]["operation"] = "DEPLOY"
            with self.assertRaises(ValueError):
                ManualAgentSimulator(vendor).restore(snapshot)
    return check

for vendor in VENDORS:
    for case in ("pin", "tab", "directions", "receipt", "humanlock", "restore", "tamper"):
        setattr(AgentContractTests, f"test_{vendor.lower().replace('.', '_')}_{case}",
                build_test(vendor, case))

class CrossVendorTests(unittest.TestCase):
    def test_all_seven_have_unique_tabs(self):
        self.assertEqual(len(VENDORS), 7)
        self.assertEqual(len(set(TABS.values())), 7)

    def test_unknown_vendor_rejected(self):
        with self.assertRaises(ValueError):
            ManualAgentSimulator("UNKNOWN")

    def test_cross_vendor_snapshot_rejected(self):
        source = ManualAgentSimulator("META")
        source.execute()
        with self.assertRaises(ValueError):
            ManualAgentSimulator("GOOGLE").restore(source.snapshot())
