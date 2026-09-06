from __future__ import annotations

import hashlib
import hmac
import json
import os
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request

BRIDGE_VERSION = "FACEBOOK_ENGINE_BRIDGE.1"
EVIDENCE_BOUNDARY = "OBSERVED != VERIFIED != CORRELATED != CAUSAL"

_VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "")
_APP_SECRET = os.getenv("META_APP_SECRET", "")
_EVENT_LOG = Path(os.getenv("FACEBOOK_EVENT_LOG", "/tmp/fr0333_facebook_events.jsonl"))
_RECEIPT_LOG = Path(os.getenv("FACEBOOK_RECEIPT_LOG", "/tmp/fr0333_facebook_receipts.jsonl"))
_MAX_MEMORY_EVENTS = int(os.getenv("FACEBOOK_MAX_MEMORY_EVENTS", "500"))
_MAX_MEMORY_RECEIPTS = int(os.getenv("FACEBOOK_MAX_MEMORY_RECEIPTS", "500"))
_RECENT_EVENTS: deque[dict[str, Any]] = deque(maxlen=_MAX_MEMORY_EVENTS)
_RECENT_RECEIPTS: deque[dict[str, Any]] = deque(maxlen=_MAX_MEMORY_RECEIPTS)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def bridge_manifest() -> dict[str, Any]:
    return {
        "bridge_version": BRIDGE_VERSION,
        "source": "FACEBOOK_META",
        "state": "STAY_1",
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "verify_token_configured": bool(_VERIFY_TOKEN),
        "app_secret_configured": bool(_APP_SECRET),
        "event_log": str(_EVENT_LOG),
        "receipt_log": str(_RECEIPT_LOG),
        "memory_capacity": _MAX_MEMORY_EVENTS,
        "receipt_memory_capacity": _MAX_MEMORY_RECEIPTS,
    }


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n")
    except OSError:
        # Webhook acknowledgement must not fail because local receipt storage is unavailable.
        pass


def _record_receipt(receipt: dict[str, Any]) -> None:
    _RECENT_RECEIPTS.append(receipt)
    _append_jsonl(_RECEIPT_LOG, receipt)


def verify_webhook_subscription(mode: str | None, token: str | None, challenge: str | None) -> str:
    received_at = _now()
    configured = bool(_VERIFY_TOKEN)
    token_match = configured and token is not None and hmac.compare_digest(token, _VERIFY_TOKEN)
    success = mode == "subscribe" and token_match and challenge is not None

    receipt = {
        "engine": BRIDGE_VERSION,
        "receipt_type": "META_GET_VERIFICATION",
        "observed_at": received_at,
        "hub_mode": mode,
        "hub_challenge_present": challenge is not None,
        "hub_verify_token_match": token_match,
        "configured": configured,
        "result": "VERIFIED" if success else "REJECTED",
        "http_status": 200 if success else (503 if not configured else 403),
        "evidence_class": "OBSERVED",
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "promotion": "NONE",
        "state": "STAY_1",
    }
    _record_receipt(receipt)

    if not configured:
        raise HTTPException(status_code=503, detail="META_VERIFY_TOKEN is not configured")
    if not success:
        raise HTTPException(status_code=403, detail="Facebook webhook verification failed")
    return challenge


def _validate_signature(raw_body: bytes, signature_header: str | None) -> bool:
    if not _APP_SECRET:
        raise HTTPException(status_code=503, detail="META_APP_SECRET is not configured")
    if not signature_header or not signature_header.startswith("sha256="):
        raise HTTPException(status_code=401, detail="Missing X-Hub-Signature-256")

    supplied = signature_header.removeprefix("sha256=")
    expected = hmac.new(_APP_SECRET.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Invalid Facebook webhook signature")
    return True


def _event_id(payload: dict[str, Any], entry_index: int, change_index: int) -> str:
    stable = json.dumps(
        {"payload": payload, "entry_index": entry_index, "change_index": change_index},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(stable).hexdigest()


def _extract_vector(entry: dict[str, Any], change: dict[str, Any]) -> dict[str, Any]:
    value = change.get("value") if isinstance(change, dict) else None
    value = value if isinstance(value, dict) else {}

    return {
        "page_id": entry.get("id"),
        "entry_time": entry.get("time"),
        "field": change.get("field") if isinstance(change, dict) else None,
        "item": value.get("item"),
        "verb": value.get("verb"),
        "post_id": value.get("post_id"),
        "comment_id": value.get("comment_id"),
        "parent_id": value.get("parent_id"),
        "sender_id": (value.get("sender") or {}).get("id") if isinstance(value.get("sender"), dict) else None,
        "message": value.get("message"),
        "created_time": value.get("created_time"),
    }


def _persist_event(event: dict[str, Any]) -> None:
    _append_jsonl(_EVENT_LOG, event)


def _normalize_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    observed_at = _now()
    object_type = payload.get("object")
    entries = payload.get("entry") if isinstance(payload.get("entry"), list) else []
    normalized: list[dict[str, Any]] = []

    for entry_index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        changes = entry.get("changes") if isinstance(entry.get("changes"), list) else []
        if not changes:
            changes = [{}]

        for change_index, change in enumerate(changes):
            change = change if isinstance(change, dict) else {}
            event = {
                "engine": BRIDGE_VERSION,
                "source": "FACEBOOK_META",
                "event_id": _event_id(payload, entry_index, change_index),
                "observed_at": observed_at,
                "object": object_type,
                "raw": {"entry": entry, "change": change},
                "vector": _extract_vector(entry, change),
                "raven_state": "INTAKE",
                "evidence_class": "OBSERVED",
                "evidence_boundary": EVIDENCE_BOUNDARY,
                "promotion": "NONE",
            }
            normalized.append(event)
    return normalized


async def ingest_webhook(request: Request) -> dict[str, Any]:
    received_at = _now()
    raw_body = await request.body()
    body_sha256 = hashlib.sha256(raw_body).hexdigest()
    signature_header = request.headers.get("X-Hub-Signature-256")

    try:
        signature_valid = _validate_signature(raw_body, signature_header)
    except HTTPException as exc:
        _record_receipt({
            "engine": BRIDGE_VERSION,
            "receipt_type": "META_POST_DELIVERY",
            "observed_at": received_at,
            "signature_header_present": signature_header is not None,
            "signature_valid": False,
            "payload_sha256": body_sha256,
            "payload_bytes": len(raw_body),
            "result": "REJECTED",
            "http_status": exc.status_code,
            "events_ingested": 0,
            "evidence_class": "OBSERVED",
            "evidence_boundary": EVIDENCE_BOUNDARY,
            "promotion": "NONE",
            "state": "STAY_1",
        })
        raise

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _record_receipt({
            "engine": BRIDGE_VERSION,
            "receipt_type": "META_POST_DELIVERY",
            "observed_at": received_at,
            "signature_header_present": signature_header is not None,
            "signature_valid": signature_valid,
            "payload_sha256": body_sha256,
            "payload_bytes": len(raw_body),
            "result": "INVALID_JSON",
            "http_status": 400,
            "events_ingested": 0,
            "evidence_class": "OBSERVED",
            "evidence_boundary": EVIDENCE_BOUNDARY,
            "promotion": "NONE",
            "state": "STAY_1",
        })
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Webhook payload must be a JSON object")

    events = _normalize_payload(payload)
    for event in events:
        _RECENT_EVENTS.append(event)
        _persist_event(event)

    page_ids = sorted({str(e.get("vector", {}).get("page_id")) for e in events if e.get("vector", {}).get("page_id")})
    fields = sorted({str(e.get("vector", {}).get("field")) for e in events if e.get("vector", {}).get("field")})

    receipt = {
        "engine": BRIDGE_VERSION,
        "receipt_type": "META_POST_DELIVERY",
        "observed_at": received_at,
        "signature_header_present": signature_header is not None,
        "signature_valid": signature_valid,
        "payload_sha256": body_sha256,
        "payload_bytes": len(raw_body),
        "object": payload.get("object"),
        "page_ids": page_ids,
        "fields": fields,
        "result": "ACCEPTED",
        "http_status": 200,
        "events_ingested": len(events),
        "event_ids": [event["event_id"] for event in events],
        "evidence_class": "OBSERVED",
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "promotion": "NONE",
        "state": "STAY_1",
    }
    _record_receipt(receipt)

    return {
        "received": True,
        "bridge_version": BRIDGE_VERSION,
        "events_ingested": len(events),
        "payload_sha256": body_sha256,
        "state": "STAY_1",
    }


def recent_events(limit: int = 25) -> dict[str, Any]:
    limit = max(1, min(limit, 100))
    events = list(_RECENT_EVENTS)[-limit:]
    return {
        "bridge_version": BRIDGE_VERSION,
        "count": len(events),
        "events": events,
        "evidence_boundary": EVIDENCE_BOUNDARY,
    }


def recent_receipts(limit: int = 25) -> dict[str, Any]:
    limit = max(1, min(limit, 100))
    receipts = list(_RECENT_RECEIPTS)[-limit:]
    return {
        "bridge_version": BRIDGE_VERSION,
        "count": len(receipts),
        "receipts": receipts,
        "evidence_boundary": EVIDENCE_BOUNDARY,
    }
