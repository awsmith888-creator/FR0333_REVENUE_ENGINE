#!/usr/bin/env python3
"""Stand-alone public-spec and repo-chain structural gate. HumanLock remains HOLD."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
doc=json.loads((HERE/"fr0333_media_capability_evolution_0001.json").read_text())
idx=json.loads((HERE/"fr0333_golden_chain_index_0001.json").read_text())
p=doc["passive_matrix"]
a=doc["active_metrics"]
s=doc["source_catalog"]
checks={
 "SOURCE.3":len(s)==3 and all(x["url"].startswith("https://") for x in s),
 "PASSIVE.10":len(p)==10 and [x["id"] for x in p]==[f"M{i:02d}" for i in range(1,11)],
 "ACTIVE.10":len(a)==10 and [x["id"] for x in a]==[f"A{i:02d}" for i in range(1,11)],
 "ALIGN.10":[x["ref"] for x in a]==[x["id"] for x in p],
 "NO.FAKE.METRICS":all(x["value"] is None and x["state"]=="U.21.HOLD" for x in a),
 "PILOT.NOT.GA":doc["external_feature"]["phase"]=="LIMITED_PILOT" and doc["external_feature"]["universal_availability"]=="U.21.HOLD",
 "NO.EXTERNAL.ACTION":doc["control"]["external_upload"]=="F.6.NONE" and doc["control"]["auto_publish"]=="F.6.NONE",
 "NO.PROMOTION":doc["control"]["canonical_promotion"]=="U.21.HOLD" and doc["control"]["humanlock"]=="REQUIRED_FOR_PROMOTION",
 "GOLDEN.APPEND":len(idx["entries"])>=11 and idx["entries"][-1]["index"]=="0.11" and idx["entries"][-2]["index"]=="0.10" and idx["entries"][-1]["identifier"]==doc["golden_chain_identifier"]
}
assert all(checks.values()), checks
print(json.dumps({"state":"T.20.PASS.STRUCTURE_ONLY","checks_passed":len(checks),
                  "humanlock":"U.21.HOLD","provider_actions":0},sort_keys=True))
