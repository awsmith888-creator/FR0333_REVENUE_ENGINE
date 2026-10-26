#!/usr/bin/env python3
"""Read-only Zero Lion cyberphysical matrix indexing gate.
Results attest to structure only, never to real sensor performance or external deployment.
"""
import copy
import json
from pathlib import Path
import sys

DEFAULT = Path(__file__).with_name("fr0333_cyberphysical_ai_matrix_0001.json")
EXPECTED_MATRIX = [f"M{i:02d}" for i in range(1, 11)]
EXPECTED_METRICS = [f"A{i:02d}" for i in range(1, 11)]
EXPECTED_SOURCES = {f"S{i:02d}" for i in range(1, 6)}

def evaluate(doc):
    p = doc.get("passive_matrix", [])
    a = doc.get("active_metrics", [])
    s = doc.get("source_catalog", [])
    b = doc.get("boundaries", [])
    promotion = doc.get("promotion", {})
    checks = [
        ("G01.IDENTITY", doc.get("identifier") == "FR0333.ZERO.LION.CYBERPHYSICAL.AI.MATRIX.0001"),
        ("G02.SOURCE.LOCK", {x.get("id") for x in s} == EXPECTED_SOURCES and all(x.get("url", "").startswith("https://") for x in s)),
        ("G03.PASSIVE.TEN", len(p) == 10 and [x.get("id") for x in p] == EXPECTED_MATRIX and [x.get("index") for x in p] == list(range(1, 11))),
        ("G04.ACTIVE.TEN", len(a) == 10 and [x.get("id") for x in a] == EXPECTED_METRICS and [x.get("index") for x in a] == list(range(1, 11))),
        ("G05.ONE_TO_ONE", len(a) == 10 and [x.get("passive_reference_id") for x in a] == EXPECTED_MATRIX),
        ("G06.NUMERIC.UNITS", all(x.get("unit") and x.get("source_id") in EXPECTED_SOURCES for x in p) and all(x.get("unit") and x.get("formula") and x.get("required_runtime_fields") for x in a)),
        ("G07.PASSIVE.ISOLATION", doc.get("passive_lane", {}).get("mode") == "APPEND_ONLY_NUMERIC_MATRIX" and doc.get("passive_lane", {}).get("can_control_equipment") is False),
        ("G08.ACTIVE.ISOLATION", doc.get("active_lane", {}).get("mode") == "METRIC_DEFINITIONS_NOT_EXECUTED" and doc.get("active_lane", {}).get("can_control_equipment") is False),
        ("G09.NO_FAKE.OBSERVATIONS", all(x.get("actual_fr0333_observation") is None and x.get("qualification_threshold") is None for x in p) and all(x.get("measurement_value") is None and x.get("test_status") == "U.21.HOLD" and x.get("safety_threshold") is None for x in a)),
        ("G10.LG.EXAMPLE.IS.EXAMPLE", len(p) == 10 and p[0].get("reference_example_value") == 24.1 and p[0].get("example_scope") == "MANUAL_EXAMPLE_ONLY"),
        ("G11.EVIDENCE.DIFFERENTIATION", all(x in b for x in ("DOCUMENTED_NE_EXECUTED", "VERIFIED_NE_PROMOTED", "STANDARD_SCHEMA_NE_VENDOR_IMPLEMENTATION", "NO_COPYRIGHTED_SCHEMATICS_REPRODUCED"))),
        ("G12.RUNTIME.INTERLOCK", promotion.get("runtime_claim") == "U.21.HOLD" and promotion.get("external_provider_run") == "F.6.NONE" and promotion.get("equipment_control") == "F.6.NONE"),
        ("G13.CHAIN.APPEND.ONLY", doc.get("proposed_public_index", "").startswith("0.10.") and doc.get("lineage") == "FR0333.TWO_LANE.HIGHWAY.0001" and promotion.get("mainline_merge") == "F.6.NONE"),
    ]
    result = [{"gate": label, "state": "T.20.PASS" if ok else "F.6.REJECT"} for label, ok in checks]
    if promotion.get("canonical_promotion_authorized") is False and promotion.get("operator_promotion_receipt") is None and promotion.get("humanlock") == "REQUIRED":
        humanlock = "U.21.HOLD"
    else:
        humanlock = "F.6.REJECT"  # A self-asserted promotion flag is never an authorization receipt.
    result.append({"gate": "G14.HUMANLOCK.CANONICAL.PROMOTION", "state": humanlock})
    failed = any(r["state"] == "F.6.REJECT" for r in result)
    return {
        "identifier": "FR0333.ZLLG.CYBERPHYSICAL.MATRIX.GATE.0001",
        "index_state": "F.6.REJECT" if failed else "T.20.PASS.INDEX_ONLY",
        "canonical_promotion_state": "U.21.HOLD" if not failed else "F.6.REJECT",
        "gate_count": 14,
        "index_checks_passed": sum(r["state"] == "T.20.PASS" for r in result),
        "hold_count": sum(r["state"] == "U.21.HOLD" for r in result),
        "results": result,
    }

if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    report = evaluate(json.loads(path.read_text(encoding="utf-8")))
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["index_state"] == "T.20.PASS.INDEX_ONLY" else 1)
