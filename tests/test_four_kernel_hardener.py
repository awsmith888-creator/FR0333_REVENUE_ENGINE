import sys
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from four_kernel_hardener import evaluate_four_kernel_transaction, CORE_GATES, ADOBE_GATES

def transaction():
    return {
        "kernels": {
            "NEWSFLASH": {"passed": True, "receipt": {"id":"r1"}},
            "ESPN.FANTASY.SPORTS": {"passed": True, "receipt": {"id":"r2"}},
            "NELSON": {"passed": True, "receipt": {"id":"r3"}},
            "GENIUS.BAR": {"passed": True, "receipt": {"id":"r4"}},
        },
        "core_gates": {gate: True for gate in CORE_GATES},
        "adobe_gates": {gate: False for gate in ADOBE_GATES},
        "adobe_execution_receipt": {},
        "statistics": {"source_count":3,"metric_count":18,"sample_size":4,"truth_t20_count":4,"truth_u21_count":3,"truth_f6_count":0},
    }

class FourKernelHardenerTests(unittest.TestCase):
    def test_1111_opens_operator_route(self):
        result=evaluate_four_kernel_transaction(transaction())
        self.assertEqual(result["operator_route"],"OPEN")
        self.assertEqual(result["statistics"]["kernel_bitword"],"1111")
        self.assertEqual(result["statistics"]["decimal_state"],15)

    def test_adobe_stays_held_without_empirical_receipt(self):
        result=evaluate_four_kernel_transaction(transaction())
        self.assertEqual(result["adobe_route"],"HOLD")
        self.assertEqual(result["adobe_live_traversal_receipt"],"U.21")

    def test_any_kernel_zero_holds_operator(self):
        tx=transaction(); tx["kernels"]["NELSON"]["passed"]=False
        result=evaluate_four_kernel_transaction(tx)
        self.assertEqual(result["operator_route"],"HOLD")
        self.assertEqual(result["statistics"]["kernel_bitword"],"1101")

    def test_missing_receipt_holds_operator(self):
        tx=transaction(); tx["kernels"]["GENIUS.BAR"]["receipt"]={}
        result=evaluate_four_kernel_transaction(tx)
        self.assertEqual(result["operator_route"],"HOLD")
        self.assertEqual(result["statistics"]["kernel_bitword"],"1110")

    def test_core_gate_zero_holds_operator(self):
        tx=transaction(); tx["core_gates"]["SOURCE.TIMESTAMP"]=False
        result=evaluate_four_kernel_transaction(tx)
        self.assertEqual(result["operator_route"],"HOLD")

    def test_empirical_adobe_receipt_plus_gates_opens_adobe(self):
        tx=transaction(); tx["adobe_gates"]={gate:True for gate in ADOBE_GATES}; tx["adobe_execution_receipt"]={"id":"adobe-live-1"}
        result=evaluate_four_kernel_transaction(tx)
        self.assertEqual(result["adobe_route"],"OPEN")
        self.assertEqual(result["adobe_live_traversal_receipt"],"T.20")

    def test_nelson_name_is_exact(self):
        result=evaluate_four_kernel_transaction(transaction())
        self.assertIn("NELSON",result["kernels"])
        self.assertNotIn("NIELSEN",result["kernels"])

    def test_runtime_boundary_preserved(self):
        result=evaluate_four_kernel_transaction(transaction())
        self.assertEqual(result["humanlock"],"ACTIVE")
        self.assertEqual(result["base_model_weights"],"UNCHANGED")
        self.assertEqual(result["platform_permissions"],"UNCHANGED")

if __name__=="__main__":
    unittest.main()
