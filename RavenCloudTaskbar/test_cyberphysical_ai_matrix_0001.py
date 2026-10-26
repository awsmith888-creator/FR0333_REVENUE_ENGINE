#!/usr/bin/env python3
"""Local-only mutation controls; no device or remote workflow is called."""
import copy
import json
from pathlib import Path
from validate_cyberphysical_ai_matrix_0001 import evaluate

path = Path(__file__).with_name("fr0333_cyberphysical_ai_matrix_0001.json")
original = json.loads(path.read_text(encoding="utf-8"))
positive = evaluate(original)
assert positive["index_state"] == "T.20.PASS.INDEX_ONLY"
assert positive["index_checks_passed"] == 13
assert positive["hold_count"] == 1
mutations = [
    ("lost passive row", lambda d: d["passive_matrix"].pop()),
    ("broken paired metric", lambda d: d["active_metrics"][2].update(passive_reference_id="M10")),
    ("invented live value", lambda d: d["active_metrics"][0].update(measurement_value=24.1)),
    ("invented safety threshold", lambda d: d["passive_matrix"][4].update(qualification_threshold=1)),
    ("forged HumanLock", lambda d: d["promotion"].update(canonical_promotion_authorized=True)),
    ("runtime falsely promoted", lambda d: d["promotion"].update(runtime_claim="T.20.PASS")),
    ("changed passive mode", lambda d: d["passive_lane"].update(mode="EDIT_IN_PLACE")),
]
for label, change in mutations:
    case = copy.deepcopy(original)
    change(case)
    assert evaluate(case)["index_state"] == "F.6.REJECT", label
print(json.dumps({"state":"T.20.PASS.LOCAL_SYNTHETIC_ONLY","baseline_index_checks":13,"humanlock_hold":1,"mutation_rejections":len(mutations),"device_executions":0,"external_workflows":0}))
