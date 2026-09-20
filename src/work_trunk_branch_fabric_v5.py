"""Durable FR0333 Work-trunk branch fabric v5.

This module upgrades workflow continuity; it does not modify model weights or
grant platform capabilities. SQLite is the canonical local ledger. Workers are
disposable: leases expire, checkpoints persist, and another worker may resume.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Optional


RECORD_ID = "FR0333.WORK.TRUNK.BRANCH.FABRIC.0005"
LANES = {"CHAT", "ENGINE", "ADOBE"}
AUTHORIZATIONS = {"READ", "BUILD", "EXTERNAL_ACTION"}
EVIDENCE_CLASSES = {"OBSERVED", "DERIVED", "CORRELATED", "CAUSAL"}
TERMINAL_STATES = {"COMPLETED", "DEAD.LETTER"}
ACTIVE_STATES = {"QUEUED", "CLAIMED", "EXECUTING", "RETRY.WAIT"}
HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Claim:
    job_id: str
    lane: str
    worker_id: str
    lease_expires_at: str
    checkpoint: Dict[str, Any]
    payload: Dict[str, Any]


class FabricError(RuntimeError):
    """Base fabric rejection."""


class GateHold(FabricError):
    """A hard gate held the requested transition."""


class LeaseConflict(FabricError):
    """The worker does not own a current lease."""


class WorkTrunkFabric:
    """Transactional queue, checkpoint ledger, failover, and receipt chain."""

    def __init__(self, db_path: str | Path, *, shadow_mode: bool = True) -> None:
        self.db_path = str(db_path)
        self.shadow_mode = shadow_mode
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path, timeout=10, isolation_level=None)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA busy_timeout=10000")
        return con

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        con = self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            yield con
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        finally:
            con.close()

    def _initialize(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        con = self._connect()
        try:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    parent_id TEXT NOT NULL,
                    source_hash TEXT NOT NULL,
                    lane TEXT NOT NULL CHECK(lane IN ('CHAT','ENGINE','ADOBE')),
                    intent TEXT NOT NULL,
                    authorization TEXT NOT NULL,
                    evidence_class TEXT NOT NULL,
                    humanlock TEXT NOT NULL CHECK(humanlock='ACTIVE'),
                    expected_outputs INTEGER NOT NULL CHECK(expected_outputs > 0),
                    idempotency_key TEXT NOT NULL UNIQUE,
                    payload_json TEXT NOT NULL,
                    checkpoint_json TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL CHECK(max_attempts > 0),
                    lease_owner TEXT,
                    lease_expires_at TEXT,
                    next_attempt_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS receipts (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL REFERENCES jobs(job_id),
                    event_type TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    receipt_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS dead_letters (
                    job_id TEXT PRIMARY KEY REFERENCES jobs(job_id),
                    reason TEXT NOT NULL,
                    checkpoint_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS branch_health (
                    lane TEXT PRIMARY KEY,
                    consecutive_failures INTEGER NOT NULL DEFAULT 0,
                    circuit_state TEXT NOT NULL DEFAULT 'CLOSED',
                    retry_after TEXT
                );
                """
            )
            con.execute("BEGIN IMMEDIATE")
            for lane in sorted(LANES):
                con.execute("INSERT OR IGNORE INTO branch_health(lane) VALUES (?)", (lane,))
            con.execute("COMMIT")
        except Exception:
            if con.in_transaction:
                con.execute("ROLLBACK")
            raise
        finally:
            con.close()

    @staticmethod
    def _validate_envelope(envelope: Dict[str, Any]) -> None:
        required = {
            "record_id", "parent_id", "source_hash", "lane", "intent",
            "authorization", "evidence_class", "humanlock", "expected_outputs",
        }
        missing = sorted(required - set(envelope))
        if missing:
            raise GateHold(f"MISSING.FIELDS:{','.join(missing)}")
        if envelope["lane"] not in LANES:
            raise GateHold("WRONG.LANE")
        if envelope["authorization"] not in AUTHORIZATIONS:
            raise GateHold("INVALID.AUTHORIZATION")
        if envelope["evidence_class"] not in EVIDENCE_CLASSES:
            raise GateHold("INVALID.EVIDENCE.CLASS")
        if envelope["humanlock"] != "ACTIVE":
            raise GateHold("HUMANLOCK.NOT.ACTIVE")
        if not isinstance(envelope["expected_outputs"], int) or envelope["expected_outputs"] < 1:
            raise GateHold("INVALID.EXPECTED.OUTPUTS")
        if not HASH_PATTERN.fullmatch(str(envelope["source_hash"])):
            raise GateHold("INVALID.SOURCE.HASH")

    def _append_receipt(self, con: sqlite3.Connection, job_id: str, event_type: str, event: Dict[str, Any], now: datetime) -> str:
        row = con.execute("SELECT receipt_hash FROM receipts ORDER BY sequence DESC LIMIT 1").fetchone()
        previous = row["receipt_hash"] if row else "0" * 64
        body = {"record_id": RECORD_ID, "job_id": job_id, "event_type": event_type,
                "event": event, "previous_hash": previous, "created_at": _iso(now)}
        receipt_hash = _sha256(_canonical(body))
        con.execute(
            "INSERT INTO receipts(job_id,event_type,event_json,previous_hash,receipt_hash,created_at) VALUES(?,?,?,?,?,?)",
            (job_id, event_type, _canonical(event), previous, receipt_hash, _iso(now)),
        )
        return receipt_hash

    def enqueue(self, envelope: Dict[str, Any], *, max_attempts: int = 3) -> Dict[str, Any]:
        self._validate_envelope(envelope)
        if max_attempts < 1:
            raise GateHold("INVALID.MAX.ATTEMPTS")
        now = _utcnow()
        job_id = str(envelope["record_id"])
        idempotency_key = str(envelope.get("idempotency_key") or _sha256(_canonical({
            "parent_id": envelope["parent_id"], "source_hash": envelope["source_hash"],
            "lane": envelope["lane"], "intent": envelope["intent"],
        })))
        if not idempotency_key.strip():
            raise GateHold("INVALID.IDEMPOTENCY.KEY")
        with self._transaction() as con:
            existing = con.execute("SELECT * FROM jobs WHERE idempotency_key=?", (idempotency_key,)).fetchone()
            if existing:
                return {"job_id": existing["job_id"], "status": existing["status"], "duplicate": True}
            if con.execute("SELECT 1 FROM jobs WHERE job_id=?", (job_id,)).fetchone():
                raise GateHold("JOB.ID.COLLISION")
            con.execute(
                """INSERT INTO jobs(job_id,parent_id,source_hash,lane,intent,authorization,evidence_class,
                humanlock,expected_outputs,idempotency_key,payload_json,status,max_attempts,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (job_id, envelope["parent_id"], envelope["source_hash"], envelope["lane"],
                 envelope["intent"], envelope["authorization"], envelope["evidence_class"],
                 "ACTIVE", envelope["expected_outputs"], idempotency_key,
                 _canonical(envelope.get("payload", {})), "QUEUED", max_attempts, _iso(now), _iso(now)),
            )
            receipt = self._append_receipt(con, job_id, "ENQUEUED", {"lane": envelope["lane"]}, now)
        return {"job_id": job_id, "status": "QUEUED", "duplicate": False, "receipt_hash": receipt}

    def _circuit_open(self, con: sqlite3.Connection, lane: str, now: datetime) -> bool:
        row = con.execute("SELECT * FROM branch_health WHERE lane=?", (lane,)).fetchone()
        if row["circuit_state"] != "OPEN":
            return False
        if row["retry_after"] and _parse(row["retry_after"]) <= now:
            con.execute("UPDATE branch_health SET circuit_state='HALF.OPEN' WHERE lane=?", (lane,))
            return False
        return True

    def claim(self, lane: str, worker_id: str, *, lease_seconds: int = 60) -> Optional[Claim]:
        if lane not in LANES or not worker_id or lease_seconds < 1:
            raise GateHold("INVALID.CLAIM")
        now = _utcnow()
        with self._transaction() as con:
            if self._circuit_open(con, lane, now):
                return None
            row = con.execute(
                """SELECT * FROM jobs WHERE lane=? AND status IN ('QUEUED','RETRY.WAIT')
                AND (next_attempt_at IS NULL OR next_attempt_at<=?) ORDER BY created_at,job_id LIMIT 1""",
                (lane, _iso(now)),
            ).fetchone()
            if not row:
                return None
            expires = now + timedelta(seconds=lease_seconds)
            con.execute(
                "UPDATE jobs SET status='CLAIMED',lease_owner=?,lease_expires_at=?,attempts=attempts+1,updated_at=? WHERE job_id=?",
                (worker_id, _iso(expires), _iso(now), row["job_id"]),
            )
            self._append_receipt(con, row["job_id"], "CLAIMED", {"worker_id": worker_id, "lease_expires_at": _iso(expires)}, now)
            return Claim(row["job_id"], lane, worker_id, _iso(expires), json.loads(row["checkpoint_json"]), json.loads(row["payload_json"]))

    def _require_lease(self, con: sqlite3.Connection, job_id: str, worker_id: str, now: datetime) -> sqlite3.Row:
        row = con.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        if not row:
            raise LeaseConflict("UNKNOWN.JOB")
        if row["lease_owner"] != worker_id or not row["lease_expires_at"] or _parse(row["lease_expires_at"]) <= now:
            raise LeaseConflict("LEASE.NOT.OWNED.OR.EXPIRED")
        if row["status"] not in {"CLAIMED", "EXECUTING"}:
            raise LeaseConflict("JOB.NOT.ACTIVE")
        return row

    def checkpoint(self, job_id: str, worker_id: str, checkpoint: Dict[str, Any], *, lease_seconds: int = 60) -> str:
        now = _utcnow()
        with self._transaction() as con:
            self._require_lease(con, job_id, worker_id, now)
            expires = now + timedelta(seconds=lease_seconds)
            con.execute("UPDATE jobs SET status='EXECUTING',checkpoint_json=?,lease_expires_at=?,updated_at=? WHERE job_id=?",
                        (_canonical(checkpoint), _iso(expires), _iso(now), job_id))
            return self._append_receipt(con, job_id, "CHECKPOINTED", {"checkpoint": checkpoint}, now)

    def complete(self, job_id: str, worker_id: str, receipt: Dict[str, Any]) -> str:
        now = _utcnow()
        with self._transaction() as con:
            row = self._require_lease(con, job_id, worker_id, now)
            if receipt.get("record_id") != job_id or receipt.get("status") != "PASS":
                raise GateHold("RECEIPT.IDENTITY.OR.STATUS.FAIL")
            if receipt.get("branch") != row["lane"]:
                raise GateHold("BRANCH.IDENTITY.MISMATCH")
            outputs = receipt.get("output_hashes", [])
            if len(outputs) != row["expected_outputs"] or len(outputs) != len(set(outputs)):
                raise GateHold("EXPECTED.COUNT.OR.DUPLICATE.FAIL")
            if any(not isinstance(x, str) or not HASH_PATTERN.fullmatch(x) for x in outputs):
                raise GateHold("INVALID.OUTPUT.HASH")
            gate_results = receipt.get("gate_results", {})
            if not isinstance(gate_results, dict) or any(value is not True for value in gate_results.values()):
                raise GateHold("BRANCH.GATE.FAIL")
            external_actions = receipt.get("external_actions", [])
            if self.shadow_mode and external_actions:
                raise GateHold("SHADOW.MODE.EXTERNAL.ACTION.BLOCKED")
            if row["authorization"] != "EXTERNAL_ACTION" and external_actions:
                raise GateHold("EXTERNAL.ACTION.NOT.AUTHORIZED")
            if receipt.get("humanlock") != "ACTIVE":
                raise GateHold("HUMANLOCK.NOT.ACTIVE")
            con.execute("UPDATE jobs SET status='COMPLETED',lease_owner=NULL,lease_expires_at=NULL,updated_at=? WHERE job_id=?",
                        (_iso(now), job_id))
            con.execute("UPDATE branch_health SET consecutive_failures=0,circuit_state='CLOSED',retry_after=NULL WHERE lane=?", (row["lane"],))
            return self._append_receipt(con, job_id, "COMPLETED", receipt, now)

    def fail(self, job_id: str, worker_id: str, reason: str, *, retry_seconds: int = 1,
             circuit_threshold: int = 3, circuit_seconds: int = 60) -> str:
        now = _utcnow()
        with self._transaction() as con:
            row = self._require_lease(con, job_id, worker_id, now)
            health = con.execute("SELECT consecutive_failures FROM branch_health WHERE lane=?", (row["lane"],)).fetchone()
            failures = health["consecutive_failures"] + 1
            circuit_open = failures >= circuit_threshold
            con.execute("UPDATE branch_health SET consecutive_failures=?,circuit_state=?,retry_after=? WHERE lane=?",
                        (failures, "OPEN" if circuit_open else "CLOSED",
                         _iso(now + timedelta(seconds=circuit_seconds)) if circuit_open else None, row["lane"]))
            if row["attempts"] >= row["max_attempts"]:
                status = "DEAD.LETTER"
                con.execute("INSERT OR REPLACE INTO dead_letters(job_id,reason,checkpoint_json,created_at) VALUES(?,?,?,?)",
                            (job_id, reason, row["checkpoint_json"], _iso(now)))
                con.execute("UPDATE jobs SET status=?,lease_owner=NULL,lease_expires_at=NULL,updated_at=? WHERE job_id=?",
                            (status, _iso(now), job_id))
            else:
                status = "RETRY.WAIT"
                con.execute("UPDATE jobs SET status=?,lease_owner=NULL,lease_expires_at=NULL,next_attempt_at=?,updated_at=? WHERE job_id=?",
                            (status, _iso(now + timedelta(seconds=retry_seconds)), _iso(now), job_id))
            self._append_receipt(con, job_id, "FAILED", {"reason": reason, "next_status": status}, now)
            return status

    def recover_expired(self, *, now: Optional[datetime] = None) -> int:
        now = now or _utcnow()
        with self._transaction() as con:
            rows = con.execute("SELECT job_id FROM jobs WHERE status IN ('CLAIMED','EXECUTING') AND lease_expires_at<=?", (_iso(now),)).fetchall()
            for row in rows:
                con.execute("UPDATE jobs SET status='QUEUED',lease_owner=NULL,lease_expires_at=NULL,updated_at=? WHERE job_id=?", (_iso(now), row["job_id"]))
                self._append_receipt(con, row["job_id"], "LEASE.EXPIRED.REQUEUED", {}, now)
            return len(rows)

    def replay_dead_letter(self, job_id: str, *, human_authorized: bool) -> None:
        if not human_authorized:
            raise GateHold("HUMANLOCK.REPLAY.AUTHORIZATION.REQUIRED")
        now = _utcnow()
        with self._transaction() as con:
            if not con.execute("SELECT 1 FROM dead_letters WHERE job_id=?", (job_id,)).fetchone():
                raise GateHold("DEAD.LETTER.NOT.FOUND")
            con.execute("DELETE FROM dead_letters WHERE job_id=?", (job_id,))
            con.execute("UPDATE jobs SET status='QUEUED',attempts=0,next_attempt_at=NULL,updated_at=? WHERE job_id=?", (_iso(now), job_id))
            self._append_receipt(con, job_id, "DEAD.LETTER.REPLAYED", {"human_authorized": True}, now)

    def verify_receipt_chain(self) -> bool:
        with self._connect() as con:
            rows = con.execute("SELECT * FROM receipts ORDER BY sequence").fetchall()
        previous = "0" * 64
        for row in rows:
            body = {"record_id": RECORD_ID, "job_id": row["job_id"], "event_type": row["event_type"],
                    "event": json.loads(row["event_json"]), "previous_hash": previous, "created_at": row["created_at"]}
            if row["previous_hash"] != previous or row["receipt_hash"] != _sha256(_canonical(body)):
                return False
            previous = row["receipt_hash"]
        return True

    def status(self, job_id: str) -> Dict[str, Any]:
        with self._connect() as con:
            row = con.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        if not row:
            raise GateHold("UNKNOWN.JOB")
        return {k: row[k] for k in ("job_id", "lane", "status", "attempts", "expected_outputs", "checkpoint_json")}


def branch_adapter_receipt(claim: Claim, output_hashes: Iterable[str], *, gate_results: Optional[Dict[str, bool]] = None) -> Dict[str, Any]:
    """Create a side-effect-free receipt for CHAT, ENGINE, or ADOBE."""
    return {"record_id": claim.job_id, "branch": claim.lane, "status": "PASS",
            "output_hashes": list(output_hashes), "gate_results": gate_results or {},
            "external_actions": [], "rollback_pointer": claim.checkpoint or None,
            "humanlock": "ACTIVE"}
