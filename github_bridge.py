from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import math
import os
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

try:
    from fastapi import HTTPException, Request
except ModuleNotFoundError:  # Allows the dependency-light core benchmark to run.
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class Request:  # pragma: no cover - FastAPI supplies the runtime implementation.
        pass

BRIDGE_VERSION = "FR0333_GITHUB_WEBHOOK.99.1V.1"
EVIDENCE_BOUNDARY = "OBSERVED != INTERPRETATION; TEST_PASS != DEPLOYMENT; MERGEABLE != MERGED"
MAX_GITHUB_PAYLOAD_BYTES = 25_000_000
SUPPORTED_EVENTS = frozenset(
    {
        "ping",
        "push",
        "pull_request",
        "pull_request_review",
        "pull_request_review_comment",
        "pull_request_review_thread",
        "issue_comment",
        "workflow_run",
        "check_suite",
        "status",
    }
)
_EVENT_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_HEX_64_RE = re.compile(r"^[0-9a-f]{64}$")


class _RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(
            req.full_url,
            code,
            "GitHub API redirect rejected",
            headers,
            fp,
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str | None) -> str | None:
    if value is None:
        return None
    return _sha256_bytes(value.encode("utf-8"))


def _bounded_int(raw: str | None, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(raw) if raw is not None else default
    except ValueError:
        value = default
    return min(maximum, max(minimum, value))


def _bounded_float(
    raw: str | None, default: float, minimum: float, maximum: float
) -> float:
    try:
        value = float(raw) if raw is not None else default
    except ValueError:
        value = default
    return min(maximum, max(minimum, value))


def _truthy(raw: str | None) -> bool:
    return (raw or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class GitHubBridgeConfig:
    webhook_secret: str
    read_token: str
    repository: str
    pull_request_number: int
    head_branch: str
    base_branch: str
    database_path: Path
    max_payload_bytes: int
    live_resolution: bool
    github_read_token: str
    api_base: str
    api_version: str
    api_timeout_seconds: float
    max_rejection_receipts: int
    alert_stdout: bool

    @classmethod
    def from_env(cls) -> "GitHubBridgeConfig":
        return cls(
            webhook_secret=os.getenv("GITHUB_WEBHOOK_SECRET", ""),
            read_token=os.getenv("GITHUB_BRIDGE_READ_TOKEN", ""),
            repository=os.getenv(
                "GITHUB_WEBHOOK_REPOSITORY",
                "awsmith888-creator/FR0333_REVENUE_ENGINE",
            ),
            pull_request_number=_bounded_int(
                os.getenv("GITHUB_WEBHOOK_PULL_REQUEST"), 1, 1, 2_147_483_647
            ),
            head_branch=os.getenv("GITHUB_WEBHOOK_HEAD_BRANCH", "zllg-1.0.1-prototype"),
            base_branch=os.getenv("GITHUB_WEBHOOK_BASE_BRANCH", "main"),
            database_path=Path(
                os.getenv("GITHUB_WEBHOOK_DB", "/tmp/fr0333_github_webhook.sqlite3")
            ),
            max_payload_bytes=_bounded_int(
                os.getenv("GITHUB_MAX_PAYLOAD_BYTES"),
                2_000_000,
                1_024,
                MAX_GITHUB_PAYLOAD_BYTES,
            ),
            live_resolution=_truthy(os.getenv("GITHUB_LIVE_RESOLUTION")),
            github_read_token=os.getenv("GITHUB_READ_TOKEN", ""),
            api_base=os.getenv("GITHUB_API_BASE", "https://api.github.com").rstrip("/"),
            api_version=os.getenv("GITHUB_API_VERSION", "2026-03-10"),
            api_timeout_seconds=_bounded_float(
                os.getenv("GITHUB_API_TIMEOUT_SECONDS"), 5.0, 1.0, 30.0
            ),
            max_rejection_receipts=_bounded_int(
                os.getenv("GITHUB_MAX_REJECTION_RECEIPTS"), 1_000, 10, 100_000
            ),
            alert_stdout=not (os.getenv("GITHUB_ALERT_STDOUT", "true").lower() in {"0", "false", "no", "off"}),
        )


class GitHubWebhookStore:
    def __init__(self, path: Path, max_rejection_receipts: int = 1_000):
        self.path = path
        self.max_rejection_receipts = max_rejection_receipts
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    def _initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS receipts (
                    receipt_id TEXT PRIMARY KEY,
                    delivery_id TEXT,
                    observed_at TEXT NOT NULL,
                    event_name TEXT,
                    action TEXT,
                    repository TEXT,
                    pull_request_number INTEGER,
                    signature_valid INTEGER NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    payload_bytes INTEGER NOT NULL,
                    outcome TEXT NOT NULL,
                    duplicate INTEGER NOT NULL DEFAULT 0,
                    processing_ms REAL NOT NULL,
                    evidence_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS accepted_deliveries (
                    delivery_id TEXT PRIMARY KEY,
                    payload_sha256 TEXT NOT NULL,
                    receipt_id TEXT NOT NULL,
                    accepted_at TEXT NOT NULL,
                    FOREIGN KEY(receipt_id) REFERENCES receipts(receipt_id)
                );

                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    delivery_id TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    event_name TEXT NOT NULL,
                    action TEXT,
                    repository TEXT NOT NULL,
                    pull_request_number INTEGER,
                    payload_sha256 TEXT NOT NULL,
                    vector_json TEXT NOT NULL,
                    FOREIGN KEY(delivery_id) REFERENCES accepted_deliveries(delivery_id)
                );

                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id TEXT PRIMARY KEY,
                    delivery_id TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    observed_delta_json TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    interpretation TEXT NOT NULL,
                    next_review_action TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS snapshots (
                    scope TEXT PRIMARY KEY,
                    observed_at TEXT NOT NULL,
                    snapshot_sha256 TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_receipts_observed_at
                    ON receipts(observed_at DESC);
                CREATE INDEX IF NOT EXISTS idx_events_observed_at
                    ON events(observed_at DESC);
                CREATE INDEX IF NOT EXISTS idx_alerts_observed_at
                    ON alerts(observed_at DESC);
                """
            )
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def accepted_delivery(self, delivery_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT delivery_id, payload_sha256, receipt_id, accepted_at "
                "FROM accepted_deliveries WHERE delivery_id=?",
                (delivery_id,),
            ).fetchone()
        return dict(row) if row else None

    def record_rejection(
        self,
        *,
        delivery_id: str | None,
        observed_at: str,
        event_name: str | None,
        payload_sha256: str,
        payload_bytes: int,
        outcome: str,
        processing_ms: float,
        evidence: Mapping[str, Any],
    ) -> str:
        receipt_id = _sha256_text(
            f"rejection:{delivery_id}:{payload_sha256}:{observed_at}:{outcome}"
        )
        assert receipt_id is not None
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO receipts(
                    receipt_id, delivery_id, observed_at, event_name, action,
                    repository, pull_request_number, signature_valid,
                    payload_sha256, payload_bytes, outcome, duplicate,
                    processing_ms, evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    receipt_id,
                    delivery_id,
                    observed_at,
                    event_name,
                    None,
                    None,
                    None,
                    0,
                    payload_sha256,
                    payload_bytes,
                    outcome,
                    0,
                    processing_ms,
                    _canonical_json(dict(evidence)),
                ),
            )
            connection.execute(
                """
                DELETE FROM receipts
                WHERE signature_valid=0 AND rowid NOT IN (
                    SELECT rowid FROM receipts
                    WHERE signature_valid=0
                    ORDER BY rowid DESC LIMIT ?
                )
                """,
                (self.max_rejection_receipts,),
            )
        return receipt_id

    def record_duplicate(
        self,
        *,
        delivery_id: str,
        observed_at: str,
        event_name: str,
        payload_sha256: str,
        payload_bytes: int,
        outcome: str,
        processing_ms: float,
    ) -> str:
        receipt_id = _sha256_text(
            f"duplicate:{delivery_id}:{payload_sha256}:{observed_at}:{outcome}"
        )
        assert receipt_id is not None
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO receipts(
                    receipt_id, delivery_id, observed_at, event_name, action,
                    repository, pull_request_number, signature_valid,
                    payload_sha256, payload_bytes, outcome, duplicate,
                    processing_ms, evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    receipt_id,
                    delivery_id,
                    observed_at,
                    event_name,
                    None,
                    None,
                    None,
                    1,
                    payload_sha256,
                    payload_bytes,
                    outcome,
                    1,
                    processing_ms,
                    _canonical_json(
                        {
                            "delivery_id": delivery_id,
                            "payload_sha256": payload_sha256,
                            "evidence_class": "OBSERVED",
                        }
                    ),
                ),
            )
        return receipt_id

    def record_delivery(
        self,
        *,
        delivery_id: str,
        observed_at: str,
        event_name: str,
        action: str | None,
        repository: str,
        pull_request_number: int | None,
        payload_sha256: str,
        payload_bytes: int,
        vector: Mapping[str, Any],
        outcome: str,
        processing_ms: float,
        evidence: Mapping[str, Any],
        alerts: list[dict[str, Any]],
    ) -> tuple[str, str | None]:
        receipt_id = _sha256_text(
            f"accepted:{delivery_id}:{payload_sha256}:{observed_at}:{outcome}"
        )
        event_id = None
        if outcome == "ACCEPTED_TARGET":
            event_id = _sha256_text(f"event:{delivery_id}:{payload_sha256}")
        assert receipt_id is not None

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO receipts(
                    receipt_id, delivery_id, observed_at, event_name, action,
                    repository, pull_request_number, signature_valid,
                    payload_sha256, payload_bytes, outcome, duplicate,
                    processing_ms, evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    receipt_id,
                    delivery_id,
                    observed_at,
                    event_name,
                    action,
                    repository,
                    pull_request_number,
                    1,
                    payload_sha256,
                    payload_bytes,
                    outcome,
                    0,
                    processing_ms,
                    _canonical_json(dict(evidence)),
                ),
            )
            connection.execute(
                "INSERT INTO accepted_deliveries(delivery_id, payload_sha256, receipt_id, accepted_at) "
                "VALUES(?,?,?,?)",
                (delivery_id, payload_sha256, receipt_id, observed_at),
            )
            if event_id is not None:
                connection.execute(
                    """
                    INSERT INTO events(
                        event_id, delivery_id, observed_at, event_name, action,
                        repository, pull_request_number, payload_sha256, vector_json
                    ) VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        event_id,
                        delivery_id,
                        observed_at,
                        event_name,
                        action,
                        repository,
                        pull_request_number,
                        payload_sha256,
                        _canonical_json(dict(vector)),
                    ),
                )
            for alert in alerts:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO alerts(
                        alert_id, delivery_id, observed_at, kind,
                        observed_delta_json, evidence_json, interpretation,
                        next_review_action
                    ) VALUES(?,?,?,?,?,?,?,?)
                    """,
                    (
                        alert["alert_id"],
                        delivery_id,
                        observed_at,
                        alert["kind"],
                        _canonical_json(alert["observed_delta"]),
                        _canonical_json(alert["evidence"]),
                        alert["interpretation"],
                        alert["next_review_action"],
                    ),
                )
        return receipt_id, event_id

    def record_resolution(
        self,
        *,
        delivery_id: str,
        observed_at: str,
        outcome: str,
        evidence: Mapping[str, Any],
        processing_ms: float,
    ) -> str:
        receipt_id = _sha256_text(
            f"resolution:{delivery_id}:{observed_at}:{outcome}:{_canonical_json(evidence)}"
        )
        assert receipt_id is not None
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO receipts(
                    receipt_id, delivery_id, observed_at, event_name, action,
                    repository, pull_request_number, signature_valid,
                    payload_sha256, payload_bytes, outcome, duplicate,
                    processing_ms, evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    receipt_id,
                    delivery_id,
                    observed_at,
                    "state_resolution",
                    None,
                    None,
                    None,
                    1,
                    "0" * 64,
                    0,
                    outcome,
                    0,
                    processing_ms,
                    _canonical_json(dict(evidence)),
                ),
            )
        return receipt_id

    def replace_snapshot(
        self, scope: str, observed_at: str, snapshot: Mapping[str, Any]
    ) -> dict[str, Any] | None:
        snapshot_json = _canonical_json(dict(snapshot))
        snapshot_sha256 = _sha256_text(snapshot_json)
        assert snapshot_sha256 is not None
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            previous_row = connection.execute(
                "SELECT snapshot_json FROM snapshots WHERE scope=?", (scope,)
            ).fetchone()
            connection.execute(
                """
                INSERT INTO snapshots(scope, observed_at, snapshot_sha256, snapshot_json)
                VALUES(?,?,?,?)
                ON CONFLICT(scope) DO UPDATE SET
                    observed_at=excluded.observed_at,
                    snapshot_sha256=excluded.snapshot_sha256,
                    snapshot_json=excluded.snapshot_json
                """,
                (scope, observed_at, snapshot_sha256, snapshot_json),
            )
        return json.loads(previous_row["snapshot_json"]) if previous_row else None

    def get_snapshot(self, scope: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT snapshot_json FROM snapshots WHERE scope=?", (scope,)
            ).fetchone()
        return json.loads(row["snapshot_json"]) if row else None

    def add_alerts(self, delivery_id: str, observed_at: str, alerts: list[dict[str, Any]]) -> int:
        inserted = 0
        with self._connect() as connection:
            for alert in alerts:
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO alerts(
                        alert_id, delivery_id, observed_at, kind,
                        observed_delta_json, evidence_json, interpretation,
                        next_review_action
                    ) VALUES(?,?,?,?,?,?,?,?)
                    """,
                    (
                        alert["alert_id"],
                        delivery_id,
                        observed_at,
                        alert["kind"],
                        _canonical_json(alert["observed_delta"]),
                        _canonical_json(alert["evidence"]),
                        alert["interpretation"],
                        alert["next_review_action"],
                    ),
                )
                inserted += cursor.rowcount
        return inserted

    def list_receipts(self, limit: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT receipt_id, delivery_id, observed_at, event_name, action,
                       repository, pull_request_number, signature_valid,
                       payload_sha256, payload_bytes, outcome, duplicate,
                       processing_ms, evidence_json
                FROM receipts ORDER BY rowid DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["signature_valid"] = bool(item["signature_valid"])
            item["duplicate"] = bool(item["duplicate"])
            item["evidence"] = json.loads(item.pop("evidence_json"))
            result.append(item)
        return result

    def list_events(self, limit: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT event_id, delivery_id, observed_at, event_name, action,
                       repository, pull_request_number, payload_sha256, vector_json
                FROM events ORDER BY rowid DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["vector"] = json.loads(item.pop("vector_json"))
            result.append(item)
        return result

    def list_alerts(self, limit: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT alert_id, delivery_id, observed_at, kind,
                       observed_delta_json, evidence_json, interpretation,
                       next_review_action
                FROM alerts ORDER BY rowid DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["observed_delta"] = json.loads(item.pop("observed_delta_json"))
            item["evidence"] = json.loads(item.pop("evidence_json"))
            result.append(item)
        return result

    def metrics(self) -> dict[str, Any]:
        with self._connect() as connection:
            receipt_rows = connection.execute(
                "SELECT outcome, duplicate, processing_ms FROM receipts"
            ).fetchall()
            event_rows = connection.execute(
                "SELECT event_name, COUNT(*) AS count FROM events GROUP BY event_name"
            ).fetchall()
            alert_count = connection.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
            delivery_count = connection.execute(
                "SELECT COUNT(*) FROM accepted_deliveries"
            ).fetchone()[0]

        latencies = sorted(float(row["processing_ms"]) for row in receipt_rows)
        outcomes: dict[str, int] = {}
        for row in receipt_rows:
            outcomes[row["outcome"]] = outcomes.get(row["outcome"], 0) + 1
        return {
            "accepted_delivery_count": delivery_count,
            "receipt_count": len(receipt_rows),
            "alert_count": alert_count,
            "duplicate_receipt_count": sum(int(row["duplicate"]) for row in receipt_rows),
            "outcomes": outcomes,
            "events": {row["event_name"]: row["count"] for row in event_rows},
            "processing_ms": {
                "p50": _percentile(latencies, 0.50),
                "p95": _percentile(latencies, 0.95),
                "max": max(latencies) if latencies else None,
            },
        }


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    position = (len(values) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


class GitHubWebhookBridge:
    def __init__(self, config: GitHubBridgeConfig):
        self.config = config
        self.store = GitHubWebhookStore(
            config.database_path, config.max_rejection_receipts
        )

    def manifest(self) -> dict[str, Any]:
        return {
            "bridge_version": BRIDGE_VERSION,
            "source": "GITHUB",
            "state": "BUILT_LOCAL_NOT_RUNTIME_VERIFIED",
            "target_repository": self.config.repository,
            "target_pull_request": self.config.pull_request_number,
            "target_head_branch": self.config.head_branch,
            "target_base_branch": self.config.base_branch,
            "webhook_secret_configured": len(self.config.webhook_secret.encode("utf-8")) >= 32,
            "read_token_configured": len(self.config.read_token.encode("utf-8")) >= 24,
            "live_resolution_enabled": self.config.live_resolution,
            "github_read_token_configured": bool(self.config.github_read_token),
            "max_payload_bytes": self.config.max_payload_bytes,
            "max_rejection_receipts": self.config.max_rejection_receipts,
            "github_api_version": self.config.api_version,
            "supported_events": sorted(SUPPORTED_EVENTS),
            "storage": "SQLITE_RECEIPT_LEDGER",
            "raw_payload_retained": False,
            "alert_transport": (
                "PROTECTED_API_AND_STDOUT" if self.config.alert_stdout else "PROTECTED_API"
            ),
            "evidence_boundary": EVIDENCE_BOUNDARY,
            "external_actions": "NONE",
        }

    def authorize_read(self, supplied_token: str | None) -> None:
        if len(self.config.read_token.encode("utf-8")) < 24:
            raise HTTPException(status_code=503, detail="GITHUB_BRIDGE_READ_TOKEN is not configured")
        if supplied_token is None or not hmac.compare_digest(supplied_token, self.config.read_token):
            raise HTTPException(status_code=401, detail="Unauthorized")

    async def ingest_request(self, request: Request) -> dict[str, Any]:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.config.max_payload_bytes:
                    raise HTTPException(status_code=413, detail="GitHub webhook payload is too large")
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Invalid Content-Length") from exc

        raw_body = bytearray()
        async for chunk in request.stream():
            raw_body.extend(chunk)
            if len(raw_body) > self.config.max_payload_bytes:
                raise HTTPException(status_code=413, detail="GitHub webhook payload is too large")
        return self.process_delivery(bytes(raw_body), request.headers)

    def process_delivery(self, raw_body: bytes, headers: Mapping[str, str]) -> dict[str, Any]:
        started = time.perf_counter()
        observed_at = _utc_now()
        normalized_headers = {str(key).lower(): str(value) for key, value in headers.items()}
        delivery_raw = normalized_headers.get("x-github-delivery")
        event_name = normalized_headers.get("x-github-event")
        signature = normalized_headers.get("x-hub-signature-256")
        content_type = normalized_headers.get("content-type", "").split(";", 1)[0].strip().lower()
        payload_sha256 = _sha256_bytes(raw_body)

        if len(self.config.webhook_secret.encode("utf-8")) < 32:
            raise HTTPException(status_code=503, detail="GITHUB_WEBHOOK_SECRET must contain at least 32 bytes")
        if len(raw_body) > self.config.max_payload_bytes:
            raise HTTPException(status_code=413, detail="GitHub webhook payload is too large")
        if content_type != "application/json":
            raise HTTPException(status_code=415, detail="GitHub webhook content type must be application/json")

        signature_valid = self._valid_signature(raw_body, signature)
        if not signature_valid:
            self.store.record_rejection(
                delivery_id=delivery_raw[:128] if delivery_raw else None,
                observed_at=observed_at,
                event_name=event_name[:64] if event_name else None,
                payload_sha256=payload_sha256,
                payload_bytes=len(raw_body),
                outcome="REJECTED_SIGNATURE",
                processing_ms=(time.perf_counter() - started) * 1000,
                evidence={
                    "signature_header_present": signature is not None,
                    "payload_sha256": payload_sha256,
                    "payload_bytes": len(raw_body),
                    "evidence_class": "OBSERVED",
                },
            )
            raise HTTPException(status_code=401, detail="Invalid GitHub webhook signature")

        delivery_id = self._delivery_id(delivery_raw)
        if not event_name or not _EVENT_RE.fullmatch(event_name):
            raise HTTPException(status_code=400, detail="Invalid X-GitHub-Event")

        prior = self.store.accepted_delivery(delivery_id)
        if prior:
            outcome = "DUPLICATE" if prior["payload_sha256"] == payload_sha256 else "DELIVERY_ID_COLLISION"
            self.store.record_duplicate(
                delivery_id=delivery_id,
                observed_at=observed_at,
                event_name=event_name,
                payload_sha256=payload_sha256,
                payload_bytes=len(raw_body),
                outcome=outcome,
                processing_ms=(time.perf_counter() - started) * 1000,
            )
            if outcome == "DELIVERY_ID_COLLISION":
                raise HTTPException(status_code=409, detail="Delivery ID was reused with a different payload")
            return {
                "received": True,
                "duplicate": True,
                "delivery_id": delivery_id,
                "payload_sha256": payload_sha256,
                "state": "STAY",
                "alerts_created": 0,
                "resolution_eligible": False,
            }

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="GitHub webhook payload must be a JSON object")

        action = payload.get("action") if isinstance(payload.get("action"), str) else None
        repository = self._repository(payload)
        pull_request_number, route_reason = self._pull_request_route(event_name, payload)
        repository_match = hmac.compare_digest(repository, self.config.repository)
        event_supported = event_name in SUPPORTED_EVENTS
        target_match = repository_match and (
            event_name == "ping" or pull_request_number == self.config.pull_request_number
        )

        outcome = "ACCEPTED_TARGET"
        if not event_supported:
            outcome = "FILTERED_UNSUPPORTED_EVENT"
        elif not repository_match:
            outcome = "FILTERED_REPOSITORY"
        elif event_name != "ping" and not target_match:
            outcome = "FILTERED_PULL_REQUEST"

        vector = self._vector(event_name, action, payload, pull_request_number)
        evidence = {
            "delivery_id": delivery_id,
            "event": event_name,
            "action": action,
            "repository": repository,
            "pull_request_number": pull_request_number,
            "route_reason": route_reason,
            "payload_sha256": payload_sha256,
            "payload_bytes": len(raw_body),
            "signature_valid": True,
            "target_match": target_match,
            "evidence_class": "OBSERVED",
            "evidence_boundary": EVIDENCE_BOUNDARY,
        }
        alerts = self._event_alerts(
            delivery_id=delivery_id,
            observed_at=observed_at,
            event_name=event_name,
            action=action,
            payload=payload,
            vector=vector,
            evidence=evidence,
        ) if outcome == "ACCEPTED_TARGET" else []

        processing_ms = (time.perf_counter() - started) * 1000
        receipt_id, event_id = self.store.record_delivery(
            delivery_id=delivery_id,
            observed_at=observed_at,
            event_name=event_name,
            action=action,
            repository=repository,
            pull_request_number=pull_request_number,
            payload_sha256=payload_sha256,
            payload_bytes=len(raw_body),
            vector=vector,
            outcome=outcome,
            processing_ms=processing_ms,
            evidence=evidence,
            alerts=alerts,
        )
        self._emit_alerts(alerts)
        return {
            "received": True,
            "duplicate": False,
            "delivery_id": delivery_id,
            "receipt_id": receipt_id,
            "event_id": event_id,
            "payload_sha256": payload_sha256,
            "outcome": outcome,
            "alerts_created": len(alerts),
            "resolution_eligible": outcome == "ACCEPTED_TARGET",
            "state": "INTAKE" if outcome == "ACCEPTED_TARGET" else "STAY",
        }

    def _valid_signature(self, raw_body: bytes, signature: str | None) -> bool:
        if not signature or not signature.startswith("sha256="):
            return False
        supplied = signature.removeprefix("sha256=").lower()
        if not _HEX_64_RE.fullmatch(supplied):
            return False
        expected = hmac.new(
            self.config.webhook_secret.encode("utf-8"), raw_body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(supplied, expected)

    def _emit_alerts(self, alerts: list[dict[str, Any]]) -> None:
        if not self.config.alert_stdout:
            return
        for alert in alerts:
            print(
                _canonical_json(
                    {
                        "record_type": "FR0333_GITHUB_ACTIONABLE_CHANGE",
                        "bridge_version": BRIDGE_VERSION,
                        "alert_id": alert["alert_id"],
                        "kind": alert["kind"],
                        "observed_state": alert["observed_delta"],
                        "evidence": alert["evidence"],
                        "interpretation": alert["interpretation"],
                        "next_review_action": alert["next_review_action"],
                    }
                ),
                flush=True,
            )

    @staticmethod
    def _delivery_id(delivery_id: str | None) -> str:
        if not delivery_id:
            raise HTTPException(status_code=400, detail="Missing X-GitHub-Delivery")
        try:
            return str(uuid.UUID(delivery_id))
        except (ValueError, AttributeError) as exc:
            raise HTTPException(status_code=400, detail="Invalid X-GitHub-Delivery") from exc

    @staticmethod
    def _repository(payload: Mapping[str, Any]) -> str:
        repository = payload.get("repository")
        if not isinstance(repository, dict):
            return ""
        full_name = repository.get("full_name")
        return full_name if isinstance(full_name, str) else ""

    def _pull_request_route(
        self, event_name: str, payload: Mapping[str, Any]
    ) -> tuple[int | None, str]:
        number = payload.get("number")
        if isinstance(number, int):
            return number, "top_level_number"

        pull_request = payload.get("pull_request")
        if isinstance(pull_request, dict) and isinstance(pull_request.get("number"), int):
            return pull_request["number"], "pull_request.number"

        issue = payload.get("issue")
        if (
            isinstance(issue, dict)
            and isinstance(issue.get("number"), int)
            and isinstance(issue.get("pull_request"), dict)
        ):
            return issue["number"], "issue.pull_request"

        container = payload.get(event_name)
        if isinstance(container, dict):
            pull_requests = container.get("pull_requests")
            if isinstance(pull_requests, list):
                for candidate in pull_requests:
                    if (
                        isinstance(candidate, dict)
                        and candidate.get("number") == self.config.pull_request_number
                    ):
                        return self.config.pull_request_number, f"{event_name}.pull_requests"
            head_branch = container.get("head_branch")
            if isinstance(head_branch, str) and hmac.compare_digest(
                head_branch, self.config.head_branch
            ):
                return self.config.pull_request_number, f"{event_name}.head_branch"

            head_sha = container.get("head_sha")
            if isinstance(head_sha, str) and self._matches_snapshot_head(head_sha):
                return self.config.pull_request_number, f"{event_name}.head_sha_snapshot"

        if event_name == "push":
            ref = payload.get("ref")
            target_refs = {
                f"refs/heads/{self.config.head_branch}",
                f"refs/heads/{self.config.base_branch}",
            }
            if isinstance(ref, str) and ref in target_refs:
                return self.config.pull_request_number, "push.target_branch"
            return None, "push_not_bound_to_target_branch"

        if event_name == "status":
            branches = payload.get("branches")
            if isinstance(branches, list):
                for branch in branches:
                    if (
                        isinstance(branch, dict)
                        and isinstance(branch.get("name"), str)
                        and hmac.compare_digest(branch["name"], self.config.head_branch)
                    ):
                        return self.config.pull_request_number, "status.branches"
            status_sha = payload.get("sha")
            if isinstance(status_sha, str) and self._matches_snapshot_head(status_sha):
                return self.config.pull_request_number, "status.sha_snapshot"
            return None, "status_not_bound_to_target_head"
        return None, "no_pull_request_binding"

    def _matches_snapshot_head(self, head_sha: str) -> bool:
        scope = f"{self.config.repository}#{self.config.pull_request_number}"
        snapshot = self.store.get_snapshot(scope)
        observed_sha = snapshot.get("head_sha") if snapshot else None
        return isinstance(observed_sha, str) and hmac.compare_digest(head_sha, observed_sha)

    def _vector(
        self,
        event_name: str,
        action: str | None,
        payload: Mapping[str, Any],
        pull_request_number: int | None,
    ) -> dict[str, Any]:
        pull_request = payload.get("pull_request")
        pull_request = pull_request if isinstance(pull_request, dict) else {}
        sender = payload.get("sender")
        sender = sender if isinstance(sender, dict) else {}
        vector: dict[str, Any] = {
            "event": event_name,
            "action": action,
            "pull_request_number": pull_request_number,
            "sender_login": sender.get("login"),
            "sender_id": sender.get("id"),
            "observed_fields_only": True,
        }

        if event_name == "pull_request":
            vector.update(
                {
                    "state": pull_request.get("state"),
                    "draft": pull_request.get("draft"),
                    "merged": pull_request.get("merged"),
                    "mergeable": pull_request.get("mergeable"),
                    "mergeable_state": pull_request.get("mergeable_state"),
                    "head_sha": _nested(pull_request, "head", "sha"),
                    "base_sha": _nested(pull_request, "base", "sha"),
                    "body_sha256": _sha256_text(_string_or_none(pull_request.get("body"))),
                    "title_sha256": _sha256_text(_string_or_none(pull_request.get("title"))),
                    "updated_at": pull_request.get("updated_at"),
                    "closed_at": pull_request.get("closed_at"),
                    "merged_at": pull_request.get("merged_at"),
                }
            )
        elif event_name == "pull_request_review":
            review = payload.get("review")
            review = review if isinstance(review, dict) else {}
            vector.update(
                {
                    "review_id": review.get("id"),
                    "review_node_id": review.get("node_id"),
                    "review_state": review.get("state"),
                    "review_commit_id": review.get("commit_id"),
                    "review_body_sha256": _sha256_text(_string_or_none(review.get("body"))),
                    "submitted_at": review.get("submitted_at"),
                }
            )
        elif event_name == "pull_request_review_comment":
            comment = payload.get("comment")
            comment = comment if isinstance(comment, dict) else {}
            vector.update(
                {
                    "comment_id": comment.get("id"),
                    "comment_node_id": comment.get("node_id"),
                    "path": comment.get("path"),
                    "line": comment.get("line"),
                    "start_line": comment.get("start_line"),
                    "commit_id": comment.get("commit_id"),
                    "comment_body_sha256": _sha256_text(_string_or_none(comment.get("body"))),
                }
            )
        elif event_name == "pull_request_review_thread":
            thread = payload.get("thread")
            thread = thread if isinstance(thread, dict) else {}
            vector.update(
                {
                    "thread_id": thread.get("id") or thread.get("node_id"),
                    "thread_resolved": thread.get("is_resolved"),
                    "thread_updated_at": thread.get("updated_at"),
                }
            )
        elif event_name == "issue_comment":
            comment = payload.get("comment")
            comment = comment if isinstance(comment, dict) else {}
            vector.update(
                {
                    "comment_id": comment.get("id"),
                    "comment_node_id": comment.get("node_id"),
                    "comment_body_sha256": _sha256_text(_string_or_none(comment.get("body"))),
                    "comment_created_at": comment.get("created_at"),
                    "comment_updated_at": comment.get("updated_at"),
                }
            )
        elif event_name == "workflow_run":
            run = payload.get("workflow_run")
            run = run if isinstance(run, dict) else {}
            vector.update(
                {
                    "workflow_run_id": run.get("id"),
                    "workflow_name": run.get("name"),
                    "run_number": run.get("run_number"),
                    "status": run.get("status"),
                    "conclusion": run.get("conclusion"),
                    "head_sha": run.get("head_sha"),
                    "head_branch": run.get("head_branch"),
                    "updated_at": run.get("updated_at"),
                }
            )
        elif event_name == "check_suite":
            suite = payload.get("check_suite")
            suite = suite if isinstance(suite, dict) else {}
            vector.update(
                {
                    "check_suite_id": suite.get("id"),
                    "status": suite.get("status"),
                    "conclusion": suite.get("conclusion"),
                    "head_sha": suite.get("head_sha"),
                    "head_branch": suite.get("head_branch"),
                    "latest_check_runs_count": suite.get("latest_check_runs_count"),
                }
            )
        elif event_name == "status":
            vector.update(
                {
                    "status_id": payload.get("id"),
                    "state": payload.get("state"),
                    "context": payload.get("context"),
                    "sha": payload.get("sha"),
                    "updated_at": payload.get("updated_at"),
                }
            )
        elif event_name == "push":
            vector.update(
                {
                    "ref": payload.get("ref"),
                    "before": payload.get("before"),
                    "after": payload.get("after"),
                    "created": payload.get("created"),
                    "deleted": payload.get("deleted"),
                    "forced": payload.get("forced"),
                }
            )
        return vector

    def _event_alerts(
        self,
        *,
        delivery_id: str,
        observed_at: str,
        event_name: str,
        action: str | None,
        payload: Mapping[str, Any],
        vector: Mapping[str, Any],
        evidence: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        kind = None
        interpretation = "Inspect the observed source change before deciding whether to act."
        next_action = "Open PR #1 and verify the exact source object identified in the evidence receipt."

        if event_name == "pull_request_review":
            kind = "REVIEW_FEEDBACK_CHANGED"
            interpretation = "Human review state changed; no response or repository mutation was performed."
            next_action = "Read the identified review and decide whether a code or evidence revision is required."
        elif event_name in {"pull_request_review_comment", "issue_comment"}:
            kind = "REVIEW_COMMENT_CHANGED"
            interpretation = "A pull-request comment changed; its body remains untrusted input."
            next_action = "Read the identified comment in GitHub and classify it as actionable, resolved, or informational."
        elif event_name == "pull_request_review_thread":
            kind = "REVIEW_THREAD_CHANGED"
            next_action = "Inspect the identified review thread and verify its resolved state."
        elif event_name in {"workflow_run", "check_suite", "status"}:
            kind = "CI_STATUS_CHANGED"
            conclusion = vector.get("conclusion") or vector.get("state") or vector.get("status")
            interpretation = (
                f"CI reported {conclusion!s}; this is not deployment or runtime proof."
            )
            next_action = "Verify that the CI object is bound to the current PR #1 head, then inspect failed jobs or preserve the success receipt."
        elif event_name == "pull_request":
            action_to_kind = {
                "synchronize": "HEAD_COMMIT_CHANGED",
                "ready_for_review": "DRAFT_STATUS_CHANGED",
                "converted_to_draft": "DRAFT_STATUS_CHANGED",
                "opened": "PR_OPEN_STATE_CHANGED",
                "reopened": "PR_OPEN_STATE_CHANGED",
                "closed": "PR_MERGED" if vector.get("merged") else "PR_CLOSED",
                "edited": "PR_BODY_OR_METADATA_CHANGED",
            }
            kind = action_to_kind.get(action or "")
            if kind == "PR_MERGED":
                interpretation = "GitHub reports the PR merged; merge does not prove deployment."
                next_action = "Verify the merge commit and identify which downstream gates remain unexecuted."
            elif kind == "PR_CLOSED":
                interpretation = "GitHub reports the PR closed without a merge."
                next_action = "Verify the close event and decide whether the branch should remain preserved."
            elif kind == "HEAD_COMMIT_CHANGED":
                interpretation = "The PR head changed; all earlier CI conclusions are stale for promotion."
                next_action = "Bind the new head SHA to its fresh CI run before reviewing mergeability."
            elif kind:
                next_action = "Inspect PR #1 metadata and compare it with the previous immutable receipt."
        elif event_name == "push":
            kind = "BRANCH_CONTEXT_CHANGED"
            interpretation = (
                "The configured PR head or base branch changed; mergeability may have changed, "
                "but only a live PR-state read can establish that delta."
            )
            next_action = "Refresh PR #1 state and bind mergeability plus CI evidence to the current head SHA."

        if kind is None:
            return []
        subject = next(
            (
                vector.get(key)
                for key in (
                    "review_id",
                    "comment_id",
                    "thread_id",
                    "workflow_run_id",
                    "check_suite_id",
                    "status_id",
                    "head_sha",
                )
                if vector.get(key) is not None
            ),
            action or event_name,
        )
        alert_id = _sha256_text(f"alert:{delivery_id}:{kind}:{subject}")
        assert alert_id is not None
        return [
            {
                "alert_id": alert_id,
                "kind": kind,
                "observed_delta": dict(vector),
                "evidence": {
                    **dict(evidence),
                    "canonical_pr_url": (
                        f"https://github.com/{self.config.repository}/pull/"
                        f"{self.config.pull_request_number}"
                    ),
                    "observed_at": observed_at,
                },
                "interpretation": interpretation,
                "next_review_action": next_action,
            }
        ]

    async def resolve_current_state(self, delivery_id: str) -> dict[str, Any]:
        if not self.config.live_resolution:
            return {"state": "HOLD", "reason": "GITHUB_LIVE_RESOLUTION is disabled"}
        return await asyncio.to_thread(self._resolve_current_state_sync, delivery_id)

    def _resolve_current_state_sync(self, delivery_id: str) -> dict[str, Any]:
        started = time.perf_counter()
        observed_at = _utc_now()
        try:
            pull_request = self._api_get(
                f"/repos/{self.config.repository}/pulls/{self.config.pull_request_number}"
            )
            head_sha = _nested(pull_request, "head", "sha")
            workflow_runs = self._api_get(
                f"/repos/{self.config.repository}/actions/runs?"
                + urllib.parse.urlencode(
                    {"event": "pull_request", "head_sha": head_sha or "", "per_page": 20}
                )
            )
            reviews = self._api_get(
                f"/repos/{self.config.repository}/pulls/{self.config.pull_request_number}/reviews?per_page=100"
            )
            comments = self._api_get(
                f"/repos/{self.config.repository}/issues/{self.config.pull_request_number}/comments?per_page=100"
            )
            combined_status: Any = {}
            check_runs: Any = {}
            if isinstance(head_sha, str) and head_sha:
                encoded_sha = urllib.parse.quote(head_sha, safe="")
                combined_status = self._api_get(
                    f"/repos/{self.config.repository}/commits/{encoded_sha}/status?per_page=100"
                )
                check_runs = self._api_get(
                    f"/repos/{self.config.repository}/commits/{encoded_sha}/check-runs?per_page=100"
                )
            snapshot = self._snapshot(
                pull_request,
                workflow_runs,
                reviews,
                comments,
                combined_status,
                check_runs,
            )
            scope = f"{self.config.repository}#{self.config.pull_request_number}"
            previous = self.store.replace_snapshot(scope, observed_at, snapshot)
            alerts = self._snapshot_alerts(delivery_id, observed_at, previous, snapshot)
            inserted = self.store.add_alerts(delivery_id, observed_at, alerts)
            self._emit_alerts(alerts)
            evidence = {
                "scope": scope,
                "snapshot_sha256": _sha256_text(_canonical_json(snapshot)),
                "previous_snapshot_present": previous is not None,
                "alerts_created": inserted,
                "evidence_class": "LIVE_GITHUB_API_READ",
            }
            self.store.record_resolution(
                delivery_id=delivery_id,
                observed_at=observed_at,
                outcome="RESOLUTION_VERIFIED",
                evidence=evidence,
                processing_ms=(time.perf_counter() - started) * 1000,
            )
            return {"state": "VERIFIED", **evidence}
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
            evidence = {
                "error_type": type(exc).__name__,
                "error": str(exc)[:500],
                "evidence_class": "TRANSPORT_OBSERVATION",
            }
            self.store.record_resolution(
                delivery_id=delivery_id,
                observed_at=observed_at,
                outcome="RESOLUTION_FAILED",
                evidence=evidence,
                processing_ms=(time.perf_counter() - started) * 1000,
            )
            return {"state": "HOLD", **evidence}

    def _api_get(self, path: str) -> Any:
        url = f"{self.config.api_base}{path}"
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("GITHUB_API_BASE must resolve to an HTTPS host")
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.config.api_version,
            "User-Agent": "FR0333-GitHub-Webhook-Bridge",
        }
        if self.config.github_read_token:
            headers["Authorization"] = f"Bearer {self.config.github_read_token}"
        request = urllib.request.Request(url, headers=headers, method="GET")
        opener = urllib.request.build_opener(_RejectRedirects())
        with opener.open(request, timeout=self.config.api_timeout_seconds) as response:
            body = response.read(10_000_000)
        return json.loads(body.decode("utf-8"))

    @staticmethod
    def _snapshot(
        pull_request: Mapping[str, Any],
        workflow_runs: Any,
        reviews: Any,
        comments: Any,
        combined_status: Any,
        check_runs: Any,
    ) -> dict[str, Any]:
        runs = workflow_runs.get("workflow_runs", []) if isinstance(workflow_runs, dict) else []
        runs = [run for run in runs if isinstance(run, dict)]
        review_list = [review for review in reviews if isinstance(review, dict)] if isinstance(reviews, list) else []
        comment_list = [comment for comment in comments if isinstance(comment, dict)] if isinstance(comments, list) else []
        statuses = combined_status.get("statuses", []) if isinstance(combined_status, dict) else []
        statuses = [status for status in statuses if isinstance(status, dict)]
        checks = check_runs.get("check_runs", []) if isinstance(check_runs, dict) else []
        checks = [check for check in checks if isinstance(check, dict)]
        return {
            "state": pull_request.get("state"),
            "draft": pull_request.get("draft"),
            "merged": pull_request.get("merged"),
            "mergeable": pull_request.get("mergeable"),
            "mergeable_state": pull_request.get("mergeable_state"),
            "head_sha": _nested(pull_request, "head", "sha"),
            "base_sha": _nested(pull_request, "base", "sha"),
            "body_sha256": _sha256_text(_string_or_none(pull_request.get("body"))),
            "updated_at": pull_request.get("updated_at"),
            "closed_at": pull_request.get("closed_at"),
            "merged_at": pull_request.get("merged_at"),
            "ci_state": _ci_state(runs, statuses, checks),
            "workflow_runs": [
                {
                    "id": run.get("id"),
                    "name": run.get("name"),
                    "run_number": run.get("run_number"),
                    "status": run.get("status"),
                    "conclusion": run.get("conclusion"),
                    "head_sha": run.get("head_sha"),
                    "updated_at": run.get("updated_at"),
                }
                for run in runs
            ],
            "commit_statuses": sorted(
                (
                    {
                        "id": status.get("id"),
                        "context": status.get("context"),
                        "state": status.get("state"),
                        "updated_at": status.get("updated_at"),
                    }
                    for status in statuses
                ),
                key=lambda item: (str(item["context"]), str(item["id"])),
            ),
            "check_runs": sorted(
                (
                    {
                        "id": check.get("id"),
                        "name": check.get("name"),
                        "status": check.get("status"),
                        "conclusion": check.get("conclusion"),
                        "completed_at": check.get("completed_at"),
                    }
                    for check in checks
                ),
                key=lambda item: (str(item["name"]), str(item["id"])),
            ),
            "reviews": sorted(
                (
                    {
                        "id": review.get("id"),
                        "state": review.get("state"),
                        "commit_id": review.get("commit_id"),
                        "submitted_at": review.get("submitted_at"),
                        "body_sha256": _sha256_text(_string_or_none(review.get("body"))),
                    }
                    for review in review_list
                ),
                key=lambda item: str(item["id"]),
            ),
            "comments": sorted(
                (
                    {
                        "id": comment.get("id"),
                        "updated_at": comment.get("updated_at"),
                        "body_sha256": _sha256_text(_string_or_none(comment.get("body"))),
                    }
                    for comment in comment_list
                ),
                key=lambda item: str(item["id"]),
            ),
        }

    def _snapshot_alerts(
        self,
        delivery_id: str,
        observed_at: str,
        previous: Mapping[str, Any] | None,
        current: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        if previous is None:
            return []
        mapping = {
            "head_sha": ("HEAD_COMMIT_CHANGED", "Bind the new head SHA to fresh CI evidence."),
            "ci_state": ("CI_STATUS_CHANGED", "Inspect the current-head workflow runs and preserve their exact IDs."),
            "mergeable": ("MERGEABILITY_CHANGED", "Inspect conflicts, required checks, and branch protection before any merge decision."),
            "mergeable_state": ("MERGEABILITY_CHANGED", "Inspect conflicts, required checks, and branch protection before any merge decision."),
            "draft": ("DRAFT_STATUS_CHANGED", "Verify whether PR #1 should remain draft."),
            "state": ("PR_OPEN_STATE_CHANGED", "Verify the PR open or closed state in GitHub."),
            "merged": ("PR_MERGE_STATE_CHANGED", "Verify the merge commit; merge is not deployment."),
            "body_sha256": ("PR_BODY_CHANGED", "Compare the current PR body against the prior immutable body hash."),
            "reviews": ("REVIEW_FEEDBACK_CHANGED", "Inspect the changed review IDs, states, commit bindings, or body hashes."),
            "comments": ("REVIEW_COMMENT_CHANGED", "Inspect the changed conversation comment IDs, timestamps, or body hashes."),
        }
        alerts = []
        for field, (kind, next_action) in mapping.items():
            before = previous.get(field)
            after = current.get(field)
            if field in {"mergeable", "mergeable_state"} and after in {None, "unknown"}:
                continue
            if before == after:
                continue
            alert_id = _sha256_text(
                f"snapshot-alert:{delivery_id}:{kind}:{field}:{_canonical_json(after)}"
            )
            assert alert_id is not None
            alerts.append(
                {
                    "alert_id": alert_id,
                    "kind": kind,
                    "observed_delta": {"field": field, "prior": before, "current": after},
                    "evidence": {
                        "delivery_id": delivery_id,
                        "observed_at": observed_at,
                        "source": "LIVE_GITHUB_API_READ",
                        "canonical_pr_url": (
                            f"https://github.com/{self.config.repository}/pull/"
                            f"{self.config.pull_request_number}"
                        ),
                    },
                    "interpretation": "A live GitHub read returned a material state delta; no external action was taken.",
                    "next_review_action": next_action,
                }
            )
        return alerts


def _nested(value: Mapping[str, Any], *keys: str) -> Any:
    current: Any = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _ci_state(
    runs: list[Mapping[str, Any]],
    statuses: list[Mapping[str, Any]],
    checks: list[Mapping[str, Any]],
) -> str:
    if not runs and not statuses and not checks:
        return "NONE_OBSERVED"

    failing = {
        "failure",
        "cancelled",
        "timed_out",
        "action_required",
        "startup_failure",
        "error",
    }
    if (
        any(run.get("conclusion") in failing for run in runs)
        or any(status.get("state") in {"failure", "error"} for status in statuses)
        or any(check.get("conclusion") in failing for check in checks)
    ):
        return "FAILURE"

    if (
        any(run.get("status") != "completed" for run in runs)
        or any(status.get("state") == "pending" for status in statuses)
        or any(check.get("status") != "completed" for check in checks)
    ):
        return "PENDING"

    successful = {"success", "neutral", "skipped"}
    conclusions = [run.get("conclusion") for run in runs] + [
        check.get("conclusion") for check in checks
    ]
    status_states = [status.get("state") for status in statuses]
    if (
        all(conclusion in successful for conclusion in conclusions)
        and all(state == "success" for state in status_states)
    ):
        return "SUCCESS"
    return "UNKNOWN"


_BRIDGE: GitHubWebhookBridge | None = None


def get_github_bridge() -> GitHubWebhookBridge:
    global _BRIDGE
    if _BRIDGE is None:
        _BRIDGE = GitHubWebhookBridge(GitHubBridgeConfig.from_env())
    return _BRIDGE


def github_bridge_manifest() -> dict[str, Any]:
    return get_github_bridge().manifest()


async def ingest_github_webhook(request: Request) -> dict[str, Any]:
    return await get_github_bridge().ingest_request(request)


async def resolve_github_state(delivery_id: str) -> dict[str, Any]:
    return await get_github_bridge().resolve_current_state(delivery_id)


def github_recent_receipts(limit: int = 25) -> dict[str, Any]:
    limit = max(1, min(limit, 100))
    return {
        "bridge_version": BRIDGE_VERSION,
        "count": len(receipts := get_github_bridge().store.list_receipts(limit)),
        "receipts": receipts,
        "evidence_boundary": EVIDENCE_BOUNDARY,
    }


def github_recent_events(limit: int = 25) -> dict[str, Any]:
    limit = max(1, min(limit, 100))
    return {
        "bridge_version": BRIDGE_VERSION,
        "count": len(events := get_github_bridge().store.list_events(limit)),
        "events": events,
        "evidence_boundary": EVIDENCE_BOUNDARY,
    }


def github_recent_alerts(limit: int = 25) -> dict[str, Any]:
    limit = max(1, min(limit, 100))
    return {
        "bridge_version": BRIDGE_VERSION,
        "count": len(alerts := get_github_bridge().store.list_alerts(limit)),
        "alerts": alerts,
        "evidence_boundary": EVIDENCE_BOUNDARY,
    }


def github_metrics() -> dict[str, Any]:
    return {
        "bridge_version": BRIDGE_VERSION,
        "metrics": get_github_bridge().store.metrics(),
        "probability_claimed": False,
        "benchmark": {
            "id": "FR0333_GITHUB_WEBHOOK_64_V1",
            "fixture_count": 64,
            "runtime_attests_execution": False,
        },
        "benchmark_state": "DEFINED_RUNTIME_DOES_NOT_ATTEST_CI_EXECUTION",
        "evidence_boundary": EVIDENCE_BOUNDARY,
    }
