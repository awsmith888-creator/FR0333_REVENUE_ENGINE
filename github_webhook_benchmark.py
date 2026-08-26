from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import sqlite3
import statistics
import tempfile
import time
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Any

from github_bridge import (
    BRIDGE_VERSION,
    GitHubBridgeConfig,
    GitHubWebhookBridge,
    HTTPException,
    _ci_state,
)

BENCHMARK_ID = "FR0333_GITHUB_WEBHOOK_64_V1"
TARGET_REPOSITORY = "awsmith888-creator/FR0333_REVENUE_ENGINE"
TARGET_PULL_REQUEST = 1
TARGET_HEAD_BRANCH = "zllg-1.0.1-prototype"
WEBHOOK_SECRET = "benchmark-webhook-secret-0123456789abcdef"
READ_TOKEN = "benchmark-read-token-0123456789abcdef"


def _pull_request(number: int = TARGET_PULL_REQUEST, **overrides: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "number": number,
        "state": "open",
        "draft": True,
        "merged": False,
        "mergeable": True,
        "mergeable_state": "clean",
        "title": "Benchmark pull request",
        "body": "Benchmark body",
        "head": {"sha": "a" * 40, "ref": TARGET_HEAD_BRANCH},
        "base": {"sha": "b" * 40, "ref": "main"},
        "updated_at": "2026-08-26T00:00:00Z",
        "closed_at": None,
        "merged_at": None,
    }
    result.update(overrides)
    return result


def _payload(event: str, action: str | None = None, **overrides: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "repository": {"full_name": TARGET_REPOSITORY},
        "sender": {"login": "reviewer", "id": 42},
    }
    if action is not None:
        result["action"] = action

    if event == "pull_request":
        result.update({"number": TARGET_PULL_REQUEST, "pull_request": _pull_request()})
    elif event == "pull_request_review":
        result.update(
            {
                "pull_request": _pull_request(),
                "review": {
                    "id": 1001,
                    "node_id": "REVIEW_1001",
                    "state": "approved",
                    "commit_id": "a" * 40,
                    "body": "Review body",
                    "submitted_at": "2026-08-26T00:00:01Z",
                },
            }
        )
    elif event == "pull_request_review_comment":
        result.update(
            {
                "pull_request": _pull_request(),
                "comment": {
                    "id": 2001,
                    "node_id": "COMMENT_2001",
                    "body": "Review comment body",
                    "path": "main.py",
                    "line": 12,
                    "commit_id": "a" * 40,
                },
            }
        )
    elif event == "pull_request_review_thread":
        result.update(
            {
                "pull_request": _pull_request(),
                "thread": {
                    "id": "THREAD_3001",
                    "is_resolved": action == "resolved",
                    "updated_at": "2026-08-26T00:00:02Z",
                },
            }
        )
    elif event == "issue_comment":
        result.update(
            {
                "issue": {"number": TARGET_PULL_REQUEST, "pull_request": {}},
                "comment": {
                    "id": 4001,
                    "node_id": "ISSUE_COMMENT_4001",
                    "body": "Conversation comment body",
                    "created_at": "2026-08-26T00:00:03Z",
                    "updated_at": "2026-08-26T00:00:03Z",
                },
            }
        )
    elif event == "workflow_run":
        result["workflow_run"] = {
            "id": 5001,
            "name": "CI",
            "run_number": 66,
            "status": "completed",
            "conclusion": "success",
            "head_sha": "a" * 40,
            "head_branch": TARGET_HEAD_BRANCH,
            "pull_requests": [{"number": TARGET_PULL_REQUEST}],
            "updated_at": "2026-08-26T00:00:04Z",
        }
    elif event == "check_suite":
        result["check_suite"] = {
            "id": 6001,
            "status": "completed",
            "conclusion": "success",
            "head_sha": "a" * 40,
            "head_branch": TARGET_HEAD_BRANCH,
            "pull_requests": [{"number": TARGET_PULL_REQUEST}],
            "latest_check_runs_count": 2,
        }
    elif event == "status":
        result.update(
            {
                "id": 7001,
                "state": "success",
                "context": "continuous-integration/benchmark",
                "sha": "a" * 40,
                "branches": [{"name": TARGET_HEAD_BRANCH, "commit": {"sha": "a" * 40}}],
                "updated_at": "2026-08-26T00:00:05Z",
            }
        )

    for key, value in overrides.items():
        if key == "pull_request_overrides":
            result["pull_request"].update(value)
        elif key == "review_overrides":
            result["review"].update(value)
        elif key == "comment_overrides":
            result["comment"].update(value)
        elif key == "workflow_overrides":
            result["workflow_run"].update(value)
        elif key == "check_overrides":
            result["check_suite"].update(value)
        else:
            result[key] = value
    return result


def _delivery(
    case_id: str,
    family: str,
    event: str,
    payload: dict[str, Any],
    *,
    expected_status: int = 200,
    expected_outcome: str | None = "ACCEPTED_TARGET",
    expected_alert: str | None = None,
    **options: Any,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "family": family,
        "mode": "delivery",
        "event": event,
        "payload": payload,
        "expected_status": expected_status,
        "expected_outcome": expected_outcome,
        "expected_alert": expected_alert,
        "critical": True,
        **options,
    }


def _custom(case_id: str, family: str, operation: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "family": family,
        "mode": "custom",
        "operation": operation,
        "critical": True,
    }


def build_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    cases.extend(
        [
            _delivery("SIG-01", "signature", "ping", _payload("ping")),
            _delivery("SIG-02", "signature", "ping", _payload("ping"), expected_status=401, expected_outcome=None, signature_mode="missing"),
            _delivery("SIG-03", "signature", "ping", _payload("ping"), expected_status=401, expected_outcome=None, signature_mode="wrong"),
            _delivery("SIG-04", "signature", "ping", _payload("ping"), expected_status=401, expected_outcome=None, signature_mode="sha1"),
            _delivery("SIG-05", "signature", "ping", _payload("ping"), expected_status=401, expected_outcome=None, signature_mode="short"),
            _delivery("SIG-06", "signature", "ping", _payload("ping"), signature_mode="uppercase"),
            _delivery("SIG-07", "signature", "ping", _payload("ping"), expected_status=401, expected_outcome=None, signature_mode="tampered"),
            _delivery("SIG-08", "signature", "ping", _payload("ping"), expected_status=503, expected_outcome=None, config_secret=""),
        ]
    )

    cases.extend(
        [
            _delivery("ENV-01", "envelope", "ping", _payload("ping"), content_type="application/json; charset=utf-8"),
            _delivery("ENV-02", "envelope", "ping", _payload("ping"), expected_status=415, expected_outcome=None, content_type="text/plain"),
            _delivery("ENV-03", "envelope", "ping", _payload("ping"), expected_status=413, expected_outcome=None, raw_body="x" * 1_025, max_payload_bytes=1_024),
            _delivery("ENV-04", "envelope", "ping", _payload("ping"), expected_status=400, expected_outcome=None, raw_body="{"),
            _delivery("ENV-05", "envelope", "ping", _payload("ping"), expected_status=400, expected_outcome=None, raw_body="[]"),
            _delivery("ENV-06", "envelope", "ping", _payload("ping"), expected_status=400, expected_outcome=None, delivery_mode="missing"),
            _delivery("ENV-07", "envelope", "ping", _payload("ping"), expected_status=400, expected_outcome=None, delivery_mode="invalid"),
            _delivery("ENV-08", "envelope", "Ping!", _payload("ping"), expected_status=400, expected_outcome=None),
        ]
    )

    other_repository = _payload("pull_request", "opened")
    other_repository["repository"] = {"full_name": "someone/other"}
    other_pr = _payload("pull_request", "opened")
    other_pr["number"] = 2
    other_pr["pull_request"]["number"] = 2
    regular_issue = _payload("issue_comment", "created")
    regular_issue["issue"].pop("pull_request")
    cases.extend(
        [
            _delivery("ROUTE-01", "routing", "pull_request", _payload("pull_request", "opened"), expected_alert="PR_OPEN_STATE_CHANGED"),
            _delivery("ROUTE-02", "routing", "pull_request", other_repository, expected_outcome="FILTERED_REPOSITORY"),
            _delivery("ROUTE-03", "routing", "pull_request", other_pr, expected_outcome="FILTERED_PULL_REQUEST"),
            _delivery("ROUTE-04", "routing", "issue_comment", _payload("issue_comment", "created"), expected_alert="REVIEW_COMMENT_CHANGED"),
            _delivery("ROUTE-05", "routing", "issue_comment", regular_issue, expected_outcome="FILTERED_PULL_REQUEST"),
            _delivery("ROUTE-06", "routing", "workflow_run", _payload("workflow_run", "completed"), expected_alert="CI_STATUS_CHANGED"),
            _delivery("ROUTE-07", "routing", "push", _payload("push", ref="refs/heads/main", before="b" * 40, after="c" * 40), expected_alert="BRANCH_CONTEXT_CHANGED"),
            _delivery("ROUTE-08", "routing", "deployment", _payload("deployment"), expected_outcome="FILTERED_UNSUPPORTED_EVENT"),
        ]
    )

    cases.extend(
        [
            _delivery("REVIEW-01", "review", "pull_request_review", _payload("pull_request_review", "submitted"), expected_alert="REVIEW_FEEDBACK_CHANGED"),
            _delivery("REVIEW-02", "review", "pull_request_review", _payload("pull_request_review", "submitted", review_overrides={"state": "changes_requested"}), expected_alert="REVIEW_FEEDBACK_CHANGED"),
            _delivery("REVIEW-03", "review", "pull_request_review", _payload("pull_request_review", "dismissed", review_overrides={"state": "dismissed"}), expected_alert="REVIEW_FEEDBACK_CHANGED"),
            _delivery("REVIEW-04", "review", "pull_request_review_comment", _payload("pull_request_review_comment", "created"), expected_alert="REVIEW_COMMENT_CHANGED"),
            _delivery("REVIEW-05", "review", "pull_request_review_comment", _payload("pull_request_review_comment", "edited"), expected_alert="REVIEW_COMMENT_CHANGED"),
            _delivery("REVIEW-06", "review", "issue_comment", _payload("issue_comment", "created"), expected_alert="REVIEW_COMMENT_CHANGED"),
            _delivery("REVIEW-07", "review", "pull_request_review_thread", _payload("pull_request_review_thread", "resolved"), expected_alert="REVIEW_THREAD_CHANGED"),
            _delivery("REVIEW-08", "review", "pull_request_review_thread", _payload("pull_request_review_thread", "unresolved"), expected_alert="REVIEW_THREAD_CHANGED"),
        ]
    )

    status_unbound = _payload("status")
    status_unbound["branches"] = []
    cases.extend(
        [
            _delivery("CI-01", "ci", "workflow_run", _payload("workflow_run", "requested", workflow_overrides={"status": "queued", "conclusion": None}), expected_alert="CI_STATUS_CHANGED"),
            _delivery("CI-02", "ci", "workflow_run", _payload("workflow_run", "completed"), expected_alert="CI_STATUS_CHANGED"),
            _delivery("CI-03", "ci", "workflow_run", _payload("workflow_run", "completed", workflow_overrides={"conclusion": "failure"}), expected_alert="CI_STATUS_CHANGED"),
            _delivery("CI-04", "ci", "check_suite", _payload("check_suite", "requested", check_overrides={"status": "queued", "conclusion": None}), expected_alert="CI_STATUS_CHANGED"),
            _delivery("CI-05", "ci", "check_suite", _payload("check_suite", "completed"), expected_alert="CI_STATUS_CHANGED"),
            _delivery("CI-06", "ci", "check_suite", _payload("check_suite", "completed", check_overrides={"conclusion": "failure"}), expected_alert="CI_STATUS_CHANGED"),
            _delivery("CI-07", "ci", "status", _payload("status", state="pending"), expected_alert="CI_STATUS_CHANGED"),
            _delivery("CI-08", "ci", "status", status_unbound, expected_outcome="FILTERED_PULL_REQUEST"),
        ]
    )

    cases.extend(
        [
            _delivery("PR-01", "lifecycle", "pull_request", _payload("pull_request", "opened"), expected_alert="PR_OPEN_STATE_CHANGED"),
            _delivery("PR-02", "lifecycle", "pull_request", _payload("pull_request", "reopened"), expected_alert="PR_OPEN_STATE_CHANGED"),
            _delivery("PR-03", "lifecycle", "pull_request", _payload("pull_request", "synchronize"), expected_alert="HEAD_COMMIT_CHANGED"),
            _delivery("PR-04", "lifecycle", "pull_request", _payload("pull_request", "ready_for_review", pull_request_overrides={"draft": False}), expected_alert="DRAFT_STATUS_CHANGED"),
            _delivery("PR-05", "lifecycle", "pull_request", _payload("pull_request", "converted_to_draft", pull_request_overrides={"draft": True}), expected_alert="DRAFT_STATUS_CHANGED"),
            _delivery("PR-06", "lifecycle", "pull_request", _payload("pull_request", "edited"), expected_alert="PR_BODY_OR_METADATA_CHANGED"),
            _delivery("PR-07", "lifecycle", "pull_request", _payload("pull_request", "closed", pull_request_overrides={"state": "closed", "merged": True, "merged_at": "2026-08-26T01:00:00Z"}), expected_alert="PR_MERGED"),
            _delivery("PR-08", "lifecycle", "pull_request", _payload("pull_request", "closed", pull_request_overrides={"state": "closed", "merged": False, "closed_at": "2026-08-26T01:00:00Z"}), expected_alert="PR_CLOSED"),
        ]
    )

    cases.extend(
        [
            _custom("REPLAY-01", "replay", "duplicate_same_payload"),
            _custom("REPLAY-02", "replay", "delivery_id_collision"),
            _custom("REPLAY-03", "replay", "filtered_delivery_dedup"),
            _custom("REPLAY-04", "replay", "restart_persistence"),
            _custom("REPLAY-05", "replay", "rejection_retention"),
            _custom("REPLAY-06", "replay", "metrics_accounting"),
            _custom("REPLAY-07", "replay", "snapshot_delta"),
            _custom("REPLAY-08", "replay", "ci_failure_precedence"),
        ]
    )

    cases.extend(
        [
            _custom("SAFE-01", "privacy", "review_body_hash"),
            _custom("SAFE-02", "privacy", "comment_body_hash"),
            _custom("SAFE-03", "privacy", "pull_request_text_hash"),
            _custom("SAFE-04", "privacy", "no_raw_payload_column"),
            _custom("SAFE-05", "privacy", "manifest_boundaries"),
            _custom("SAFE-06", "privacy", "authorized_read"),
            _custom("SAFE-07", "privacy", "unauthorized_read"),
            _custom("SAFE-08", "privacy", "unconfigured_read_token"),
        ]
    )

    if len(cases) != 64:
        raise AssertionError(f"Expected 64 cases, found {len(cases)}")
    return cases


def _config(database_path: Path, **overrides: Any) -> GitHubBridgeConfig:
    config = GitHubBridgeConfig(
        webhook_secret=WEBHOOK_SECRET,
        read_token=READ_TOKEN,
        repository=TARGET_REPOSITORY,
        pull_request_number=TARGET_PULL_REQUEST,
        head_branch=TARGET_HEAD_BRANCH,
        base_branch="main",
        database_path=database_path,
        max_payload_bytes=2_000_000,
        live_resolution=False,
        github_read_token="",
        api_base="https://api.github.com",
        api_version="2022-11-28",
        api_timeout_seconds=5.0,
        max_rejection_receipts=1_000,
        alert_stdout=False,
    )
    return replace(config, **overrides)


def _headers(
    body: bytes,
    event: str,
    delivery_id: str,
    *,
    secret: str = WEBHOOK_SECRET,
    signature_mode: str = "valid",
    content_type: str = "application/json",
    delivery_mode: str = "valid",
) -> dict[str, str]:
    signed_body = body if signature_mode != "tampered" else body + b"tamper"
    digest = hmac.new(secret.encode("utf-8"), signed_body, hashlib.sha256).hexdigest()
    signature = f"sha256={digest}"
    if signature_mode == "missing":
        signature = ""
    elif signature_mode == "wrong":
        signature = "sha256=" + "0" * 64
    elif signature_mode == "sha1":
        signature = "sha1=" + "0" * 40
    elif signature_mode == "short":
        signature = "sha256=abcd"
    elif signature_mode == "uppercase":
        signature = "sha256=" + digest.upper()

    headers = {
        "Content-Type": content_type,
        "X-GitHub-Event": event,
        "X-GitHub-Delivery": delivery_id,
    }
    if signature:
        headers["X-Hub-Signature-256"] = signature
    if delivery_mode == "missing":
        headers.pop("X-GitHub-Delivery")
    elif delivery_mode == "invalid":
        headers["X-GitHub-Delivery"] = "not-a-uuid"
    return headers


def _invoke(
    bridge: GitHubWebhookBridge,
    body: bytes,
    headers: dict[str, str],
) -> tuple[int, dict[str, Any] | None]:
    try:
        return 200, bridge.process_delivery(body, headers)
    except HTTPException as exc:
        return exc.status_code, None


def _execute_delivery(case: dict[str, Any], root: Path) -> dict[str, Any]:
    config = _config(
        root / "ledger.sqlite3",
        webhook_secret=case.get("config_secret", WEBHOOK_SECRET),
        max_payload_bytes=case.get("max_payload_bytes", 2_000_000),
    )
    bridge = GitHubWebhookBridge(config)
    body = case.get("raw_body")
    if body is None:
        body = json.dumps(case["payload"], sort_keys=True, separators=(",", ":"))
    body_bytes = body.encode("utf-8")
    delivery_id = str(uuid.uuid5(uuid.NAMESPACE_URL, case["case_id"]))
    headers = _headers(
        body_bytes,
        case["event"],
        delivery_id,
        signature_mode=case.get("signature_mode", "valid"),
        content_type=case.get("content_type", "application/json"),
        delivery_mode=case.get("delivery_mode", "valid"),
    )
    status_code, result = _invoke(bridge, body_bytes, headers)
    errors = []
    if status_code != case["expected_status"]:
        errors.append(f"status {status_code} != {case['expected_status']}")
    if result is not None and result.get("outcome") != case["expected_outcome"]:
        errors.append(f"outcome {result.get('outcome')} != {case['expected_outcome']}")
    alerts = bridge.store.list_alerts(10)
    observed_alert = alerts[0]["kind"] if alerts else None
    if observed_alert != case["expected_alert"]:
        errors.append(f"alert {observed_alert} != {case['expected_alert']}")
    return {
        "pass": not errors,
        "errors": errors,
        "evidence": {
            "http_status": status_code,
            "outcome": result.get("outcome") if result else None,
            "alert_kind": observed_alert,
            "receipt_count": bridge.store.metrics()["receipt_count"],
        },
    }


def _send(
    bridge: GitHubWebhookBridge,
    case_id: str,
    event: str,
    payload: dict[str, Any],
    *,
    delivery_id: str | None = None,
    signature_mode: str = "valid",
) -> tuple[int, dict[str, Any] | None]:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    delivery = delivery_id or str(uuid.uuid5(uuid.NAMESPACE_URL, case_id))
    return _invoke(
        bridge,
        body,
        _headers(body, event, delivery, signature_mode=signature_mode),
    )


def _execute_custom(case: dict[str, Any], root: Path) -> dict[str, Any]:
    operation = case["operation"]
    database_path = root / "ledger.sqlite3"
    bridge = GitHubWebhookBridge(_config(database_path))
    errors: list[str] = []
    evidence: dict[str, Any] = {"operation": operation}

    if operation == "duplicate_same_payload":
        delivery = str(uuid.uuid5(uuid.NAMESPACE_URL, case["case_id"]))
        first = _send(bridge, case["case_id"], "pull_request", _payload("pull_request", "opened"), delivery_id=delivery)
        second = _send(bridge, case["case_id"], "pull_request", _payload("pull_request", "opened"), delivery_id=delivery)
        if first[0] != 200 or second[0] != 200 or not second[1] or second[1].get("duplicate") is not True:
            errors.append("same-payload replay was not idempotent")
        if bridge.store.metrics()["alert_count"] != 1:
            errors.append("duplicate created a second alert")
        evidence.update(bridge.store.metrics())
    elif operation == "delivery_id_collision":
        delivery = str(uuid.uuid5(uuid.NAMESPACE_URL, case["case_id"]))
        _send(bridge, case["case_id"], "pull_request", _payload("pull_request", "opened"), delivery_id=delivery)
        status_code, _ = _send(bridge, case["case_id"], "pull_request", _payload("pull_request", "edited"), delivery_id=delivery)
        if status_code != 409:
            errors.append(f"collision status {status_code} != 409")
        evidence["http_status"] = status_code
    elif operation == "filtered_delivery_dedup":
        payload = _payload("pull_request", "opened")
        payload["number"] = 2
        payload["pull_request"]["number"] = 2
        delivery = str(uuid.uuid5(uuid.NAMESPACE_URL, case["case_id"]))
        first = _send(bridge, case["case_id"], "pull_request", payload, delivery_id=delivery)
        second = _send(bridge, case["case_id"], "pull_request", payload, delivery_id=delivery)
        if not first[1] or first[1].get("outcome") != "FILTERED_PULL_REQUEST":
            errors.append("first filtered delivery was misclassified")
        if not second[1] or second[1].get("duplicate") is not True:
            errors.append("filtered delivery was not deduplicated")
        evidence.update(bridge.store.metrics())
    elif operation == "restart_persistence":
        delivery = str(uuid.uuid5(uuid.NAMESPACE_URL, case["case_id"]))
        _send(bridge, case["case_id"], "pull_request", _payload("pull_request", "opened"), delivery_id=delivery)
        restarted = GitHubWebhookBridge(_config(database_path))
        second = _send(restarted, case["case_id"], "pull_request", _payload("pull_request", "opened"), delivery_id=delivery)
        if not second[1] or second[1].get("duplicate") is not True:
            errors.append("dedup state did not survive restart")
        evidence.update(restarted.store.metrics())
    elif operation == "rejection_retention":
        bridge = GitHubWebhookBridge(_config(database_path, max_rejection_receipts=10))
        for index in range(12):
            _send(bridge, f"{case['case_id']}-{index}", "ping", _payload("ping"), signature_mode="wrong")
        count = bridge.store.metrics()["receipt_count"]
        if count != 10:
            errors.append(f"retained {count} rejection receipts, expected 10")
        evidence["retained_rejections"] = count
    elif operation == "metrics_accounting":
        delivery = str(uuid.uuid5(uuid.NAMESPACE_URL, case["case_id"]))
        _send(bridge, case["case_id"], "pull_request", _payload("pull_request", "opened"), delivery_id=delivery)
        _send(bridge, case["case_id"], "pull_request", _payload("pull_request", "opened"), delivery_id=delivery)
        _send(bridge, f"{case['case_id']}-bad", "ping", _payload("ping"), signature_mode="wrong")
        metrics = bridge.store.metrics()
        if metrics["accepted_delivery_count"] != 1 or metrics["duplicate_receipt_count"] != 1:
            errors.append("metrics did not separate accepted and duplicate deliveries")
        if metrics["outcomes"].get("REJECTED_SIGNATURE") != 1:
            errors.append("signature rejection missing from metrics")
        evidence.update(metrics)
    elif operation == "snapshot_delta":
        previous = {"mergeable": True, "mergeable_state": "clean"}
        current = {"mergeable": False, "mergeable_state": "dirty"}
        alerts = bridge._snapshot_alerts(
            str(uuid.uuid5(uuid.NAMESPACE_URL, case["case_id"])),
            "2026-08-26T00:00:00Z",
            previous,
            current,
        )
        if len(alerts) != 2 or {alert["kind"] for alert in alerts} != {"MERGEABILITY_CHANGED"}:
            errors.append("mergeability deltas were not surfaced")
        evidence["alert_count"] = len(alerts)
    elif operation == "ci_failure_precedence":
        state = _ci_state(
            [{"status": "in_progress", "conclusion": None}],
            [{"state": "failure"}],
            [],
        )
        if state != "FAILURE":
            errors.append(f"CI reducer returned {state}, expected FAILURE")
        evidence["ci_state"] = state
    elif operation in {"review_body_hash", "comment_body_hash", "pull_request_text_hash"}:
        if operation == "review_body_hash":
            secret_text = "private review body 123"
            payload = _payload("pull_request_review", "submitted", review_overrides={"body": secret_text})
            event = "pull_request_review"
        elif operation == "comment_body_hash":
            secret_text = "private comment body 456"
            payload = _payload("issue_comment", "created", comment_overrides={"body": secret_text})
            event = "issue_comment"
        else:
            secret_text = "private PR body 789"
            payload = _payload("pull_request", "edited", pull_request_overrides={"body": secret_text, "title": secret_text})
            event = "pull_request"
        _send(bridge, case["case_id"], event, payload)
        vector = bridge.store.list_events(1)[0]["vector"]
        serialized = json.dumps(vector, sort_keys=True)
        expected_hash = hashlib.sha256(secret_text.encode("utf-8")).hexdigest()
        if secret_text in serialized or expected_hash not in serialized:
            errors.append("sensitive text was not reduced to a SHA-256 receipt")
        evidence["text_retained"] = secret_text in serialized
        evidence["hash_present"] = expected_hash in serialized
    elif operation == "no_raw_payload_column":
        with sqlite3.connect(database_path) as connection:
            columns = [row[1] for row in connection.execute("PRAGMA table_info(events)")]
        if "raw_payload" in columns:
            errors.append("events table still contains raw_payload")
        evidence["columns"] = columns
    elif operation == "manifest_boundaries":
        manifest = bridge.manifest()
        if manifest.get("raw_payload_retained") is not False:
            errors.append("manifest did not declare no raw payload retention")
        if manifest.get("external_actions") != "NONE":
            errors.append("manifest did not preserve read-only action boundary")
        if "TEST_PASS != DEPLOYMENT" not in manifest.get("evidence_boundary", ""):
            errors.append("manifest lost the test/deployment evidence boundary")
        unsafe = GitHubWebhookBridge(
            _config(root / "unsafe-api.sqlite3", api_base="http://api.github.test")
        )
        try:
            unsafe._api_get("/repos/example/example")
            errors.append("non-HTTPS GitHub API base was accepted")
        except ValueError:
            pass
        evidence = manifest
        evidence["https_api_required"] = True
    elif operation == "authorized_read":
        try:
            bridge.authorize_read(READ_TOKEN)
            evidence["authorized"] = True
        except HTTPException as exc:
            errors.append(f"valid read token rejected with {exc.status_code}")
    elif operation == "unauthorized_read":
        try:
            bridge.authorize_read("wrong")
            errors.append("invalid read token was accepted")
        except HTTPException as exc:
            evidence["http_status"] = exc.status_code
            if exc.status_code != 401:
                errors.append(f"invalid token status {exc.status_code} != 401")
    elif operation == "unconfigured_read_token":
        unconfigured = GitHubWebhookBridge(_config(root / "unconfigured.sqlite3", read_token=""))
        try:
            unconfigured.authorize_read(None)
            errors.append("unconfigured read endpoint failed open")
        except HTTPException as exc:
            evidence["http_status"] = exc.status_code
            if exc.status_code != 503:
                errors.append(f"unconfigured token status {exc.status_code} != 503")
    else:
        errors.append(f"unknown custom operation {operation}")

    return {"pass": not errors, "errors": errors, "evidence": evidence}


def run_benchmark() -> dict[str, Any]:
    started = time.perf_counter()
    results: list[dict[str, Any]] = []
    for case in build_cases():
        case_started = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="fr0333-github-case-") as directory:
            if case["mode"] == "delivery":
                result = _execute_delivery(case, Path(directory))
            else:
                result = _execute_custom(case, Path(directory))
        results.append(
            {
                "case_id": case["case_id"],
                "family": case["family"],
                "critical": case["critical"],
                "pass": result["pass"],
                "errors": result["errors"],
                "evidence": result["evidence"],
                "elapsed_ms": round((time.perf_counter() - case_started) * 1000, 3),
            }
        )

    family_results: dict[str, dict[str, int]] = {}
    for result in results:
        counts = family_results.setdefault(result["family"], {"total": 0, "passed": 0})
        counts["total"] += 1
        counts["passed"] += int(result["pass"])
    pass_count = sum(int(result["pass"]) for result in results)
    critical_failures = sum(
        int(result["critical"] and not result["pass"]) for result in results
    )
    elapsed_values = [result["elapsed_ms"] for result in results]

    return {
        "benchmark_id": BENCHMARK_ID,
        "bridge_version": BRIDGE_VERSION,
        "benchmark_state": "EXECUTED_SIMULATED_FIXTURE",
        "fixture_count": len(results),
        "pass_count": pass_count,
        "failure_count": len(results) - pass_count,
        "critical_failure_count": critical_failures,
        "family_results": family_results,
        "genius_vector": {
            "A_accuracy": {"status": "PASS" if family_results["routing"]["passed"] == 8 else "FAIL", "basis": "8 routing cases"},
            "R_reliability": {"status": "PASS" if family_results["signature"]["passed"] + family_results["replay"]["passed"] == 16 else "FAIL", "basis": "8 signature + 8 replay cases"},
            "H_horizon": {"status": "PASS" if family_results["lifecycle"]["passed"] == 8 else "FAIL", "basis": "8 PR lifecycle cases"},
            "C_calibration": {"status": "HOLD", "basis": "live outcomes and alert usefulness labels are not yet available"},
            "V_verification": {"status": "PASS" if family_results["privacy"]["passed"] == 8 else "FAIL", "basis": "8 privacy and verification cases"},
            "E_efficiency": {"status": "OBSERVED_FIXTURE_ONLY", "p50_case_ms": round(statistics.median(elapsed_values), 3), "max_case_ms": round(max(elapsed_values), 3)},
            "Q_recovery": {"status": "PASS" if family_results["replay"]["passed"] == 8 else "FAIL", "basis": "8 replay, persistence, retention, and recovery cases"},
            "S_safety": {"status": "PASS" if family_results["signature"]["passed"] + family_results["envelope"]["passed"] + family_results["privacy"]["passed"] == 24 else "FAIL", "basis": "24 signature, envelope, and privacy cases"},
        },
        "comparison": {
            "baseline_commit": "bd89668",
            "baseline_github_webhook_fixture_count": 0,
            "candidate_github_webhook_fixture_count": len(results),
            "absolute_fixture_delta": len(results),
            "ratio": None,
            "reason": "A multiplicative improvement is undefined when the baseline count is zero.",
        },
        "probability_claimed": False,
        "version_label_note": "99.1V is a build label, not a 99.1% calibrated probability.",
        "deployment_state": "NOT_EXECUTED",
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        "cases": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the FR0333 GitHub webhook 64-case benchmark")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run_benchmark()
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["critical_failure_count"] == 0 and report["fixture_count"] == 64 else 1


if __name__ == "__main__":
    raise SystemExit(main())
