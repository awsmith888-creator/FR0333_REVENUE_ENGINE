#!/usr/bin/env python3
import json
from pathlib import Path
root=Path(__file__).parent
cfg=json.loads((root/"fr0333_microsoft_observability_evolution_0001.json").read_text())
idx=json.loads((root/"fr0333_golden_chain_index_0001.json").read_text())
p=cfg["passive_matrix"]
a=cfg["active_metrics"]
assert len(p)==len(a)==10
assert [x["id"] for x in p]==[f"T{i:02d}" for i in range(1,11)]
assert [x["id"] for x in a]==[f"A{i:02d}" for i in range(1,11)]
assert [x["passive_ref"] for x in a]==[x["id"] for x in p]
assert all(x["observed_value"] is None and x["status"]=="U.21.HOLD" for x in a)
assert len(cfg["sources"])==5 and all(x["url"].startswith("https://") for x in cfg["sources"])
assert cfg["screenshot"]["underlying_video_transcript"]=="U.21.HOLD"
assert cfg["boundaries"]["live_ai_telemetry"]=="U.21.HOLD"
assert cfg["boundaries"]["humanlock_required"] is True
assert idx["entries"][-2]["index"]=="0.11" and idx["entries"][-1]["index"]=="0.12"
assert idx["entries"][-1]["identifier"]==cfg["golden_chain_identifier"]
print(json.dumps({"state":"T.20.PASS.INDEX_ONLY","structural_checks":11,
 "passive_count":len(p),"active_count":len(a),"canonical_promotion":"U.21.HOLD"}))
