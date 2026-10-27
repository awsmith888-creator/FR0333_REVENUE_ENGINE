#!/usr/bin/env python3
"""Synthetic-only standalone schema/metric checks and fail-closed mutation tests."""
import copy
import hashlib
import json
from fr0333_observability_runtime_0001 import aggregate

def h(s):
    return hashlib.sha256(s.encode()).hexdigest()

def event(i,outcome):
    return {"trace_id":"R1" if i<3 else "R2","event_id":f"E{i:02d}",
       "timestamp_utc":f"2026-10-27T01:00:0{i}Z","latency_ms":100*i,
       "input_tokens":10*i,"output_tokens":5*i,"estimated_cost_microusd":100*i,
       "tool_calls":2,"tool_errors":1 if outcome=="fail" else 0,
       "test_outcome":outcome,"evaluation_receipt_sha256":h(f"evidence{i}") if outcome!="unverified" else None,
       "source_sha256":h(f"synthetic input fixture {i}")}
original={"schema_version":"1.0","events":[event(1,"pass"),event(2,"pass"),event(3,"fail"),event(4,"unverified")]}
positive=aggregate(original)
assert positive["events"]==4 and positive["unique_trace_count"]==2
assert positive["attested_pass_count"]==2
assert positive["mean_latency_ms"]==250
assert positive["input_tokens"]==100 and positive["output_tokens"]==50
assert positive["total_tool_errors"]==1
assert positive["evaluated_receipt_coverage_ratio"]==0.75
assert positive["estimated_cost_total_microusd"]==1000
assert positive["estimated_microusd_per_attested_pass"]==500
assert positive["actual_ai_provider_execution"]=="U.21.HOLD"
mutations=[
    ("private prompt leak",lambda d:d["events"][0].update(prompt="secret")),
    ("private output leak",lambda d:d["events"][0].update(response_text="user data")),
    ("duplicate event",lambda d:d["events"][1].update(event_id="E01")),
    ("negative latency",lambda d:d["events"][1].update(latency_ms=-20)),
    ("missing receipt",lambda d:d["events"][0].update(evaluation_receipt_sha256=None)),
    ("invalid source hash",lambda d:d["events"][0].update(source_sha256="fake")),
    ("inflated errors",lambda d:d["events"][2].update(tool_errors=3)),
    ("non-UTC timestamp",lambda d:d["events"][0].update(timestamp_utc="2026-10-27T05:00:01")),
    ("false schema version",lambda d:d.update(schema_version="2.0")),
    ("boolean count",lambda d:d["events"][0].update(input_tokens=True)),
]
for name,change in mutations:
    broken=copy.deepcopy(original)
    change(broken)
    try:
        aggregate(broken)
    except (ValueError,TypeError,KeyError):
        continue
    raise AssertionError("negative mutation accepted: "+name)
print(json.dumps({"state":"T.20.PASS.SYNTHETIC_ONLY","positive_events":4,
 "negative_mutations_rejected":len(mutations),
 "measured_fields":10,"live_provider_actions":0}))
