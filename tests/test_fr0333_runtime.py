import os
import tempfile
import unittest
from fr0333_runtime import Runtime, serve
from fr0333_recovery import RecoveryController

class RuntimeTests(unittest.TestCase):
    def test_clock_receipt_persists_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "runtime.sqlite")
            a = Runtime(db, clock=lambda: 3600.0)
            a.tick()
            self.assertEqual(a.count("CLOCK.OBSERVATION"), 1)
            row = a.conn.execute("SELECT payload FROM events WHERE kind='CLOCK.OBSERVATION'").fetchone()[0]
            self.assertIn('"ONE_HOUR"', row)
            a.close()
            b = Runtime(db, clock=lambda: 3601.0)
            self.assertEqual(b.count("CLOCK.OBSERVATION"), 1)
            b.close()

    def test_recovery_bloom_held(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "runtime.sqlite")
            r = RecoveryController()
            for lane in ("A.01", "A.02", "P.02"):
                r.observe(lane, True, "verified")
            r.observe("A.01", False, "fault")
            receipt = r.recover("A.01", ["A.02"], lambda _: True)
            worker = Runtime(db)
            worker.ingest_recovery(receipt)
            self.assertEqual(worker.conn.execute("SELECT state FROM blooms").fetchone()[0], "HOLD.BLOOM")
            self.assertEqual(r.active["A.01"].state.value, "F.6")
            worker.close()

    def test_bounded_run_records_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "runtime.sqlite")
            serve(db, interval=0.001, max_ticks=2)
            worker = Runtime(db)
            self.assertEqual(worker.count("CLOCK.OBSERVATION"), 2)
            self.assertEqual(worker.count("RUNTIME.START"), 1)
            self.assertEqual(worker.count("RUNTIME.STOP"), 1)
            worker.close()

    def test_reject_nonpositive_interval(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                serve(os.path.join(tmp, "bad.sqlite"), interval=0)

if __name__ == "__main__":
    unittest.main()
