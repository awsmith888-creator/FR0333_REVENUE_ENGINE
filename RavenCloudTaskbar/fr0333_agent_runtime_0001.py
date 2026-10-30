#!/usr/bin/env python3
"""Bounded FR-0333 agent adapter. Offline by default; no shell or self-install."""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

MODEL_NAME = "meta-models/Muse-Glimmer-30B"
MAX_RESPONSE_BYTES = 1_000_000
ALLOWED_ACTIONS = {"read_asset", "read_board", "generate_image", "add_board_item"}
SENSITIVE_ACTIONS = {"generate_image", "add_board_item"}


class GateError(ValueError):
    pass


def probability_from_receipts(successes: int, trials: int, *, min_trials: int = 10) -> dict[str, Any]:
    """Wilson interval over independently verified binary outcomes.

    No probability is emitted below min_trials. Model self-confidence is not an input.
    """
    if type(successes) is not int or type(trials) is not int or trials < 0 or not 0 <= successes <= trials:
        raise GateError("invalid receipt counts")
    if type(min_trials) is not int or min_trials < 1:
        raise GateError("min_trials must be a positive integer")
    if trials < min_trials:
        return {"state": "U.21.HOLD.INSUFFICIENT_VERIFIED_TRIALS", "probability": None,
                "interval_95": None, "verified_successes": successes,
                "verified_trials": trials, "minimum_trials": min_trials}
    z = 1.959963984540054
    p = successes / trials
    denom = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / denom
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * trials)) / trials) / denom
    return {"state": "T.20.PASS.EMPIRICAL_RECEIPT_ESTIMATE", "probability": round(p, 6),
            "interval_95": [round(max(0.0, center - margin), 6), round(min(1.0, center + margin), 6)],
            "verified_successes": successes, "verified_trials": trials,
            "method": "WILSON_SCORE_95_PERCENT", "evidence_basis": "INDEPENDENTLY_VERIFIED_RECEIPTS_ONLY"}


def validate_local_model_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise GateError("model endpoint must be local HTTP loopback; remote model calls are disabled")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise GateError("model endpoint must not contain credentials, query, or fragment")
    return value.rstrip("/")


def validate_adobe_mcp_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    host = (parsed.hostname or "").lower().rstrip(".")
    adobe_host = host == "adobe.com" or host.endswith(".adobe.com") or host == "adobe.io" or host.endswith(".adobe.io")
    if parsed.scheme != "https" or not adobe_host or not parsed.path.startswith("/"):
        raise GateError("Adobe bridge must use HTTPS on an Adobe-owned adobe.com/adobe.io host")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise GateError("Adobe bridge URL must not embed credentials, query, or fragment")
    return value.rstrip("/")


def authorize_action(action: str, *, operator_approved: bool = False) -> dict[str, Any]:
    if action not in ALLOWED_ACTIONS:
        raise GateError("action is not allowlisted")
    if action in SENSITIVE_ACTIONS and operator_approved is not True:
        return {"state": "U.21.HOLD.OPERATOR_APPROVAL_REQUIRED", "action": action}
    return {"state": "T.20.PASS.ACTION_AUTHORIZED_FOR_ADAPTER", "action": action}


def local_model_completion(prompt: str, *, endpoint: str | None = None) -> dict[str, Any]:
    """Send one text-only request to a local OpenAI-compatible Glimmer server."""
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 8000:
        raise GateError("prompt must be non-empty text no longer than 8000 characters")
    base = validate_local_model_url(endpoint or os.environ.get("FR0333_LOCAL_MODEL_URL", "http://127.0.0.1:8000/v1"))
    url = base + "/chat/completions"
    body = {
        "model": MODEL_NAME,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": "You are the FR-0333 local planning model. Return a proposed plan or answer only. You have no tools, shell, network, credentials, or authority to claim an external action occurred. Mark unknown evidence HOLD."},
            {"role": "user", "content": prompt},
        ],
    }
    request = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json", "Accept": "application/json"},
                                     method="POST")
    opener = urllib.request.build_opener(_NoRedirectHandler())
    try:
        with opener.open(request, timeout=60) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise GateError("local model response exceeds size limit")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise GateError("local model call failed; response details withheld") from exc
    try:
        data = json.loads(raw.decode("utf-8", errors="strict"))
        content = data["choices"][0]["message"]["content"]
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        raise GateError("local model returned an invalid completion payload") from exc
    if not isinstance(content, str):
        raise GateError("local model completion content must be plain text")
    return {"state": "T.20.PASS.LOCAL_MODEL_RESPONSE_UNVERIFIED", "model": MODEL_NAME,
            "response": content[:12000], "tool_calls": 0, "writes": 0,
            "model_quality": "U.21.HOLD.PENDING_VERIFIED_TASK_RECEIPTS"}


@dataclass
class MCPResponse:
    payload: dict[str, Any]
    session_id: str | None


class AdobeMCPDiscovery:
    """Read-only MCP initialize/tools-list probe; no Adobe tool is invoked."""
    def __init__(self, url: str, bearer_token: str):
        self.url = validate_adobe_mcp_url(url)
        if not bearer_token or "\n" in bearer_token or "\r" in bearer_token:
            raise GateError("Adobe bearer token is missing or malformed")
        self._token = bearer_token
        self._session: str | None = None
        self._next_id = 1

    def _post(self, method: str, params: dict[str, Any] | None = None) -> MCPResponse:
        body = {"jsonrpc": "2.0", "id": self._next_id, "method": method}
        self._next_id += 1
        if params is not None:
            body["params"] = params
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
                   "Authorization": "Bearer " + self._token}
        if self._session:
            headers["Mcp-Session-Id"] = self._session
        request = urllib.request.Request(self.url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
        context = ssl.create_default_context()
        opener = urllib.request.build_opener(_NoRedirectHandler(), urllib.request.HTTPSHandler(context=context))
        try:
            with opener.open(request, timeout=8) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise GateError("Adobe MCP response exceeds size limit")
                self._session = response.headers.get("Mcp-Session-Id", self._session)
                content_type = response.headers.get("Content-Type", "")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise GateError("Adobe MCP request failed; response details withheld") from exc
        text = raw.decode("utf-8", errors="strict")
        if "text/event-stream" in content_type:
            data_lines = [line[6:].strip() for line in text.splitlines() if line.startswith("data:")]
            if not data_lines:
                raise GateError("Adobe MCP stream had no JSON data event")
            text = data_lines[-1]
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise GateError("Adobe MCP returned invalid JSON") from exc
        if not isinstance(payload, dict) or "error" in payload:
            raise GateError("Adobe MCP returned an error response")
        return MCPResponse(payload, self._session)

    def discover(self) -> dict[str, Any]:
        init = self._post("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                                           "clientInfo": {"name": "FR0333-bounded-agent", "version": "0.1.0"}})
        if not isinstance(init.payload.get("result"), dict):
            raise GateError("Adobe MCP initialize response lacked result")
        initialized = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        self._notification(initialized)
        listing = self._post("tools/list", {})
        result = listing.payload.get("result", {})
        tools = result.get("tools", []) if isinstance(result, dict) else []
        safe_tools = []
        if isinstance(tools, list):
            for item in tools:
                if isinstance(item, dict) and isinstance(item.get("name"), str):
                    safe_tools.append({"name": item["name"], "description": str(item.get("description", ""))[:240]})
        return {"state": "T.20.PASS.ADOBE_MCP_DISCOVERED_READ_ONLY", "tool_count": len(safe_tools),
                "tools": safe_tools, "tools_invoked": 0, "writes": 0, "session_created": bool(self._session)}

    def _notification(self, payload: dict[str, Any]) -> None:
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
                   "Authorization": "Bearer " + self._token}
        if self._session:
            headers["Mcp-Session-Id"] = self._session
        req = urllib.request.Request(self.url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        opener = urllib.request.build_opener(_NoRedirectHandler(), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
        try:
            with opener.open(req, timeout=8) as response:
                response.read(1024)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise GateError("Adobe MCP initialization notification failed") from exc


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise GateError("Adobe MCP redirects are blocked")


def config_status(env: dict[str, str] | None = None) -> dict[str, Any]:
    env = os.environ if env is None else env
    model_url = env.get("FR0333_LOCAL_MODEL_URL", "http://127.0.0.1:8000/v1")
    try:
        validate_local_model_url(model_url)
        model_state = "CONFIGURED_LOCAL_ENDPOINT_NOT_PROBED"
    except GateError as exc:
        model_state = "HOLD:" + str(exc)
    adobe_url = env.get("FR0333_ADOBE_MCP_URL", "")
    try:
        validate_adobe_mcp_url(adobe_url) if adobe_url else None
        adobe_state = "CONFIGURED_ENDPOINT_NOT_AUTHENTICATED" if adobe_url and env.get("FR0333_ADOBE_BEARER_TOKEN") else "HOLD.DISCONNECTED"
    except GateError as exc:
        adobe_state = "HOLD:" + str(exc)
    return {"model": MODEL_NAME, "model_adapter": model_state, "adobe_adapter": adobe_state,
            "network_calls": 0, "tool_calls": 0, "writes": 0,
            "probability": probability_from_receipts(0, 0)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true", help="offline configuration and safety check")
    parser.add_argument("--discover-adobe", action="store_true", help="read-only MCP initialize and tool listing")
    parser.add_argument("--ask", type=str, help="send one text-only prompt to an already-running local Glimmer endpoint")
    args = parser.parse_args()
    if args.ask is not None:
        try:
            result = local_model_completion(args.ask)
        except GateError as exc:
            print(json.dumps({"state": "U.21.HOLD.LOCAL_MODEL_UNAVAILABLE", "reason": str(exc), "tool_calls": 0}, indent=2))
            return 2
        print(json.dumps(result, indent=2))
        return 0
    if args.discover_adobe:
        url = os.environ.get("FR0333_ADOBE_MCP_URL", "")
        token = os.environ.get("FR0333_ADOBE_BEARER_TOKEN", "")
        if not url or not token:
            print(json.dumps({"state": "U.21.HOLD.DISCONNECTED", "network_calls": 0, "writes": 0}, indent=2))
            return 2
        try:
            result = AdobeMCPDiscovery(url, token).discover()
        except GateError as exc:
            result = {"state": "F.6.REJECT_OR_CONNECTION_HOLD", "reason": str(exc), "writes": 0}
            print(json.dumps(result, indent=2))
            return 1
        print(json.dumps(result, indent=2))
        return 0
    result = config_status()
    print(json.dumps(result, indent=2))
    return 0 if args.self_check else 2


if __name__ == "__main__":
    sys.exit(main())
