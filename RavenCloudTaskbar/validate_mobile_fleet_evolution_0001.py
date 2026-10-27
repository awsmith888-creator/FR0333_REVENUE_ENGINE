#!/usr/bin/env python3
"""Research-layer 10+10 structural test, no promotion or hardware claim."""
import json
from pathlib import Path
base=Path(__file__).resolve().parent
d=json.loads((base/"fr0333_mobile_fleet_evolution_0001.json").read_text())
i=json.loads((base/"fr0333_golden_chain_index_0001.json").read_text())
p=d["passive_matrix"]
a=d["active_metrics"]
checks={
  "SOURCE_LOCK":len(d["sources"])==6 and all(s["url"].startswith("https://") for s in d["sources"]),
  "PASSIVE_TEN":[x["id"] for x in p]==[f"M{x:02d}" for x in range(1,11)],
  "ACTIVE_TEN":[x["id"] for x in a]==[f"A{x:02d}" for x in range(1,11)],
  "EXACT_PAIRING":[x["passive_reference_id"] for x in a]==[x["id"] for x in p],
  "NO_FAKE_SENSOR_READINGS":all(x["actual_fr0333_measurement"] is None for x in p),
  "NO_FAKE_METRICS":all(x["live_value"] is None and x["status"]=="U.21.HOLD" for x in a),
  "VENDOR_SCOPE":p[0]["published_reference_value"]==20 and d["source_input"]["model_number"]=="NOT_OBSERVED",
  "PHYSICAL_SAFETY_HOLD":d["safety"]["physical_safety_thresholds"]=="U.21.HOLD",
  "NO_NETWORK_OR_ACTION":d["safety"]["adb_commands_executed"]==0 and d["safety"]["net_requests"]==0,
  "NO_ENGAGEMENT_FARM":d["safety"]["fake_engagement"]=="F.6.REJECT",
  "HUMANLOCK":d["safety"]["canonical_promotion"]=="U.21.HOLD" and d["safety"]["operator_humanlock"]=="REQUIRED",
  "CHAIN_APPEND":i["entries"][-2]["index"]=="0.12" and i["entries"][-1]["index"]=="0.13" and i["entries"][-1]["identifier"]==d["golden_chain_identifier"],
}
assert all(checks.values()),checks
print(json.dumps({"state":"T.20.PASS.INDEX_ONLY","checks_passed":len(checks),"passive_nodes":len(p),"active_definitions":len(a),"runtime_hardware":"U.21.HOLD","canonical_promotion":"U.21.HOLD"},sort_keys=True))
