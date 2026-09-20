import hashlib
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from work_trunk_branch_fabric_v5 import (
    GateHold,
    LeaseConflict,
    WorkTrunkFabric,
    branch_adapter_receipt,
)


def h(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def envelope(job_id="FR0333.JOB.0001", lane="CHAT", expected=1):
    return {
        "record_id": job_id,
        "parent_id": "FR0333.WORK.TRUNK.BRANCH.FABRIC.0005",
        "source_hash": h("source" + job_id),
        "lane": lane,
        "intent": "TEST.CONTINUITY",
        "authorization": "BUILD",
        "evidence_class": "OBSERVED",
        "humanlock": "ACTIVE",
        "expected_outputs": expected,
        "payload": {"sequence": 1},
    }


class FabricTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "fabric.sqlite3"
        self.fabric = WorkTrunkFabric(self.db)

    def tearDown(self):
        self.temp.cleanup()

    def test_enqueue_claim_checkpoint_complete(self):
        self.fabric.enqueue(envelope())
        claim = self.fabric.claim("CHAT", "worker-1")
        self.fabric.checkpoint(claim.job_id, "worker-1", {"step": 1})
        receipt = branch_adapter_receipt(claim, [h("output")])
        self.fabric.complete(claim.job_id, "worker-1", receipt)
        self.assertEqual(self.fabric.status(claim.job_id)["status"], "COMPLETED")
        self.assertTrue(self.fabric.verify_receipt_chain())

    def test_duplicate_enqueue_is_idempotent(self):
        item = envelope()
        item["idempotency_key"] = "same-authorized-work"
        first = self.fabric.enqueue(item)
        duplicate = dict(item)
        duplicate["record_id"] = "FR0333.JOB.OTHER"
        second = self.fabric.enqueue(duplicate)
        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(second["job_id"], first["job_id"])

    def test_humanlock_cannot_be_disabled(self):
        item = envelope()
        item["humanlock"] = "DISABLED"
        with self.assertRaisesRegex(GateHold, "HUMANLOCK"):
            self.fabric.enqueue(item)

    def test_wrong_lane_rejected(self):
        item = envelope(lane="VIDEO")
        with self.assertRaisesRegex(GateHold, "WRONG.LANE"):
            self.fabric.enqueue(item)

    def test_wrong_branch_receipt_rejected(self):
        self.fabric.enqueue(envelope(lane="ENGINE"))
        claim = self.fabric.claim("ENGINE", "worker-1")
        receipt = branch_adapter_receipt(claim, [h("one")])
        receipt["branch"] = "CHAT"
        with self.assertRaisesRegex(GateHold, "BRANCH.IDENTITY"):
            self.fabric.complete(claim.job_id, "worker-1", receipt)

    def test_expected_count_enforced(self):
        self.fabric.enqueue(envelope(lane="ADOBE", expected=10))
        claim = self.fabric.claim("ADOBE", "worker-1")
        with self.assertRaisesRegex(GateHold, "EXPECTED.COUNT"):
            self.fabric.complete(claim.job_id, "worker-1", branch_adapter_receipt(claim, [h("one")]))

    def test_duplicate_outputs_rejected(self):
        self.fabric.enqueue(envelope(lane="ADOBE", expected=2))
        claim = self.fabric.claim("ADOBE", "worker-1")
        with self.assertRaisesRegex(GateHold, "DUPLICATE"):
            self.fabric.complete(claim.job_id, "worker-1", branch_adapter_receipt(claim, [h("one"), h("one")]))

    def test_shadow_mode_blocks_external_actions(self):
        self.fabric.enqueue(envelope())
        claim = self.fabric.claim("CHAT", "worker-1")
        receipt = branch_adapter_receipt(claim, [h("one")])
        receipt["external_actions"] = [{"type": "PUBLISH"}]
        with self.assertRaisesRegex(GateHold, "SHADOW.MODE"):
            self.fabric.complete(claim.job_id, "worker-1", receipt)

    def test_expired_worker_is_requeued_and_checkpoint_survives(self):
        self.fabric.enqueue(envelope())
        claim = self.fabric.claim("CHAT", "worker-1", lease_seconds=1)
        self.fabric.checkpoint(claim.job_id, "worker-1", {"step": 7}, lease_seconds=1)
        count = self.fabric.recover_expired(now=datetime.now(timezone.utc) + timedelta(seconds=2))
        self.assertEqual(count, 1)
        resumed = self.fabric.claim("CHAT", "worker-2")
        self.assertEqual(resumed.checkpoint, {"step": 7})

    def test_stale_worker_cannot_complete_after_failover(self):
        self.fabric.enqueue(envelope())
        first = self.fabric.claim("CHAT", "worker-1", lease_seconds=1)
        self.fabric.recover_expired(now=datetime.now(timezone.utc) + timedelta(seconds=2))
        self.fabric.claim("CHAT", "worker-2")
        with self.assertRaises(LeaseConflict):
            self.fabric.complete(first.job_id, "worker-1", branch_adapter_receipt(first, [h("one")]))

    def test_temporary_failure_retries(self):
        self.fabric.enqueue(envelope(), max_attempts=2)
        claim = self.fabric.claim("CHAT", "worker-1")
        self.assertEqual(self.fabric.fail(claim.job_id, "worker-1", "TEMP", retry_seconds=0), "RETRY.WAIT")
        self.assertIsNotNone(self.fabric.claim("CHAT", "worker-2"))

    def test_max_attempts_dead_letters(self):
        self.fabric.enqueue(envelope(), max_attempts=1)
        claim = self.fabric.claim("CHAT", "worker-1")
        self.assertEqual(self.fabric.fail(claim.job_id, "worker-1", "PERMANENT"), "DEAD.LETTER")
        self.assertEqual(self.fabric.status(claim.job_id)["status"], "DEAD.LETTER")

    def test_dead_letter_replay_requires_human(self):
        self.fabric.enqueue(envelope(), max_attempts=1)
        claim = self.fabric.claim("CHAT", "worker-1")
        self.fabric.fail(claim.job_id, "worker-1", "PERMANENT")
        with self.assertRaisesRegex(GateHold, "HUMANLOCK"):
            self.fabric.replay_dead_letter(claim.job_id, human_authorized=False)
        self.fabric.replay_dead_letter(claim.job_id, human_authorized=True)
        self.assertEqual(self.fabric.status(claim.job_id)["status"], "QUEUED")

    def test_circuit_breaker_is_lane_local(self):
        for i in range(3):
            item = envelope(f"FR0333.CHAT.{i}", lane="CHAT")
            item["source_hash"] = h(str(i))
            item["intent"] = f"CHAT.FAIL.{i}"
            self.fabric.enqueue(item, max_attempts=2)
            claim = self.fabric.claim("CHAT", f"worker-{i}")
            self.fabric.fail(claim.job_id, f"worker-{i}", "PROVIDER.DOWN", retry_seconds=0,
                             circuit_threshold=3, circuit_seconds=60)
        engine = envelope("FR0333.ENGINE.1", lane="ENGINE")
        engine["intent"] = "ENGINE.CONTINUES"
        self.fabric.enqueue(engine)
        self.assertIsNone(self.fabric.claim("CHAT", "chat-standby"))
        self.assertIsNotNone(self.fabric.claim("ENGINE", "engine-worker"))

    def test_receipt_chain_detects_tampering(self):
        self.fabric.enqueue(envelope())
        self.assertTrue(self.fabric.verify_receipt_chain())
        with self.fabric._connect() as con:
            con.execute("UPDATE receipts SET event_json='{}' WHERE sequence=1")
        self.assertFalse(self.fabric.verify_receipt_chain())

    def test_invalid_source_hash_rejected(self):
        item = envelope()
        item["source_hash"] = "not-a-hash"
        with self.assertRaisesRegex(GateHold, "SOURCE.HASH"):
            self.fabric.enqueue(item)

    def test_non_hex_output_hash_rejected(self):
        self.fabric.enqueue(envelope())
        claim = self.fabric.claim("CHAT", "worker-1")
        with self.assertRaisesRegex(GateHold, "OUTPUT.HASH"):
            self.fabric.complete(claim.job_id, "worker-1", branch_adapter_receipt(claim, ["z" * 64]))

    def test_failed_branch_gate_cannot_complete(self):
        self.fabric.enqueue(envelope())
        claim = self.fabric.claim("CHAT", "worker-1")
        receipt = branch_adapter_receipt(claim, [h("one")], gate_results={"SOURCE.LOCK": False})
        with self.assertRaisesRegex(GateHold, "BRANCH.GATE"):
            self.fabric.complete(claim.job_id, "worker-1", receipt)


if __name__ == "__main__":
    unittest.main()
