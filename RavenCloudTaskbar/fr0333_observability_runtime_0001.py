#!/usr/bin/env python3
"""FR-0333 vendor-neutral offline agent telemetry estimator.

No network operations or Microsoft service dependencies.
Receipts/source hashes are DECLARED strings, not independently reverified bytes.
No raw inputs, outputs, system prompts, PII, or credentials are accepted.
"""
import argparse
import json
import re
from pathlib import Path
from datetime import datetime

ALLOWED={"trace_id","event_id","timestamp_utc","latency_ms","input_tokens",
         "output_tokens","estimated_cost_microusd","tool_calls","tool_errors",
         "test_outcome","evaluation_receipt_sha256","source_sha256"}
HEX64=re.compile(r"^[0-9a-f]{64}$")
SAFE_ID=re.compile(r"^[A-Za-z0-9_.:-]{1,90}$")
MAX_EVENTS=10000

def normalize_event(e):
    if not isinstance(e,dict) or set(e)!=ALLOWED:
        raise ValueError("fields not allowlisted; prompts, responses and personal data forbidden")
    for key in ("trace_id","event_id"):
        if not isinstance(e[key],str) or SAFE_ID.fullmatch(e[key]) is None:
            raise ValueError("invalid trace or event identifier")
    if not isinstance(e["source_sha256"],str) or not HEX64.fullmatch(e["source_sha256"]):
        raise ValueError("invalid declared source SHA-256")
    receipt=e["evaluation_receipt_sha256"]
    if receipt is not None and (not isinstance(receipt,str) or not HEX64.fullmatch(receipt)):
        raise ValueError("invalid declared evaluation receipt")
    for key in ("latency_ms","input_tokens","output_tokens","estimated_cost_microusd","tool_calls","tool_errors"):
        if type(e[key]) is not int or e[key]<0:
            raise ValueError("invalid nonnegative integer: "+key)
    if e["tool_errors"]>e["tool_calls"]:
        raise ValueError("tool error count exceeds calls")
    if e["test_outcome"] not in ("pass","fail","unverified"):
        raise ValueError("invalid test outcome")
    if e["test_outcome"]!="unverified" and receipt is None:
        raise ValueError("evaluated outcome requires a declared evidence receipt")
    if type(e["timestamp_utc"]) is not str:
        raise ValueError("invalid timestamp type")
    try:
        timestamp=datetime.fromisoformat(e["timestamp_utc"].replace("Z","+00:00"))
    except ValueError as exc:
        raise ValueError("invalid ISO8601 timestamp") from exc
    if timestamp.utcoffset() is None or not e["timestamp_utc"].endswith("Z"):
        raise ValueError("timestamp must be explicit UTC Z")
    return e

def aggregate(payload):
    if not isinstance(payload,dict) or set(payload)!={"schema_version","events"} or payload["schema_version"]!="1.0":
        raise ValueError("invalid telemetry document schema")
    events=payload["events"]
    if not isinstance(events,list) or not 1<=len(events)<=MAX_EVENTS:
        raise ValueError("invalid event count")
    seen=set()
    clean=[]
    for record in events:
        e=normalize_event(record)
        if e["event_id"] in seen:
            raise ValueError("duplicate event identifier")
        seen.add(e["event_id"])
        clean.append(e)
    n=len(clean)
    attested_pass=sum(e["test_outcome"]=="pass" for e in clean)
    evaluated=sum(e["test_outcome"]!="unverified" for e in clean)
    cost=sum(e["estimated_cost_microusd"] for e in clean)
    tokens_in=sum(e["input_tokens"] for e in clean)
    tokens_out=sum(e["output_tokens"] for e in clean)
    tool_errors=sum(e["tool_errors"] for e in clean)
    return {
      "identifier":"FR0333.MICROSOFT.OBSERVABILITY.OFFLINE.RECEIPT.0001",
      "status":"T.20.PASS.SCHEMA_AGGREGATION_ONLY",
      "events":n,
      "unique_trace_count":len({e["trace_id"] for e in clean}),
      "attested_pass_count":attested_pass,
      "mean_latency_ms":round(sum(e["latency_ms"] for e in clean)/n,3),
      "input_tokens":tokens_in,"output_tokens":tokens_out,
      "total_tool_errors":tool_errors,
      "evaluated_receipt_coverage_ratio":round(evaluated/n,6),
      "source_sha_string_coverage_ratio":1,
      "estimated_cost_total_microusd":cost,
      "estimated_microusd_per_attested_pass":round(cost/attested_pass,3) if attested_pass else None,
      "privacy_allowlist_applied":True,
      "independent_source_fixity":"U.21.HOLD",
      "provider_billing_verification":"U.21.HOLD",
      "actual_ai_provider_execution":"U.21.HOLD",
      "external_requests":0,
      "safety_notice":"Declared receipts and success flags are not independently verified execution or quality"
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True,type=Path)
    ap.add_argument("--receipt",type=Path)
    args=ap.parse_args()
    try:
        doc=json.loads(args.input.read_text(encoding="utf-8"))
        result=aggregate(doc)
        code=0
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:
        result={"status":"F.6.REJECT","error":type(exc).__name__,"external_requests":0}
        code=1
    out=json.dumps(result,indent=2,sort_keys=True)+"\n"
    if args.receipt:
        args.receipt.write_text(out,encoding="utf-8")
    print(out,end="")
    raise SystemExit(code)

if __name__=="__main__":
    main()
