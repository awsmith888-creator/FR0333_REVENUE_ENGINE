#!/usr/bin/env python3
"""Structure-only gate for the FR-0333 candidate agent spec."""
import json
from pathlib import Path

spec = json.loads(Path(__file__).with_name("fr0333_agent_capability_evolution_0001.json").read_text(encoding="utf-8"))
passive = spec.get("passive_matrix")
active = spec.get("active_metrics")
if not isinstance(passive, list) or not isinstance(active, list) or len(passive) != 10 or len(active) != 10:
    raise SystemExit("F.6.REJECT: expected ten passive nodes and ten active metrics")
mid = [item.get("id") for item in passive]
aid = [item.get("id") for item in active]
refs = [item.get("ref") for item in active]
if mid != [f"M{i:02d}" for i in range(1, 11)] or aid != [f"A{i:02d}" for i in range(1, 11)] or set(refs) != set(mid):
    raise SystemExit("F.6.REJECT: duplicate, missing or unpaired IDs")
if spec.get("implementation_evidence", {}).get("adobe_runtime_connection", "").startswith("T.20"):
    raise SystemExit("F.6.REJECT: cannot promote Adobe connection from structure-only evidence")
print("T.20.PASS.STRUCTURE_ONLY: 10 passive nodes paired 1:1 with 10 active metrics; live runtime remains HOLD")
