#!/usr/bin/env python3
import json
import pathlib
import sys

EXPECTED_ID = "FR0333.AI.CAPABILITY.EVOLUTION.0001"
EXPECTED_GOLDEN = "FR.0333.GOLDEN.CHAIN.AI.CAPABILITY.EVOLUTION.0001"
EXPECTED_REFS = ["A1","B2","C3","D4","E5","F6","G7","H8","I9","J10","K11","L12","M13","N14"]


def validate(doc):
    results = []

    def gate(name, ok, detail):
        results.append({"gate": name, "state": "PASS" if ok else "FAIL", "detail": detail})

    gate("G1.IDENTIFIER.LOCK",
         doc.get("identifier") == EXPECTED_ID and doc.get("golden_chain_identifier") == EXPECTED_GOLDEN,
         "canonical identifiers")

    sources = doc.get("source_lock", {}).get("sources", [])
    pubs = {s.get("publisher") for s in sources}
    gate("G2.SOURCE.AUTHORITY",
         len(sources) >= 8 and {"Nature","IBM","NeurIPS","Google Research","Epoch AI","Stanford HAI"}.issubset(pubs),
         "historical primary research plus independent and academic trend sources")

    refs = doc.get("reference_points", [])
    gate("G3.REFERENCE.POINT.SEQUENCE",
         [r.get("reference_point") for r in refs] == EXPECTED_REFS and len(refs) == 14,
         "A1 through N14 exact")

    gate("G4.NO.PERCENT.UNITS",
         all("percent" not in str(r.get("unit", "")).lower() and "%" not in str(r.get("unit", "")) for r in refs),
         "reference points use ratios, per-1000, counts, currency, or state values")

    by_ref = {r.get("reference_point"): r for r in refs}
    e5 = by_ref.get("E5", {}).get("value")
    f6 = by_ref.get("F6", {}).get("value")
    g7 = by_ref.get("G7", {}).get("value")
    ratio_ok = isinstance(e5, (int, float)) and isinstance(f6, (int, float)) and f6 > 0 and round(e5 / f6) == g7
    gate("G5.COST.RATIO.RECONSTRUCTION", ratio_ok,
         "20 / 0.07 reconstructs rounded 286x cheaper reference")

    laws = set(doc.get("control_laws", []))
    gate("G6.COMPUTE.RELIABILITY.SEPARATION",
         "CAPABILITY_GROWTH_NE_TRUTH_GROWTH" in laws and "COMPUTE_GROWTH_NE_RELIABILITY_GROWTH" in laws,
         "scaling metrics are not treated as truth or reliability receipts")

    gate("G7.CONSCIOUSNESS.BOUNDARY",
         "MODEL_INTELLIGENCE_NE_MODEL_CONSCIOUSNESS" in laws and by_ref.get("N14", {}).get("value") == "U.21.HOLD",
         "subjective consciousness is not promoted from capability observations")

    gate("G8.NO.SELF.MODIFICATION.CLAIM",
         "MODEL_UPDATE_NE_AUTONOMOUS_SELF_MODIFICATION" in laws
         and "CURRENT_SESSION_ADAPTATION_NE_MODEL_WEIGHT_UPDATE" in laws
         and "HUMAN_INPUT_NE_TRAINING_RECEIPT" in laws,
         "collaboration and context use remain distinct from base-model self-modification")

    failure = doc.get("failure_memory", {})
    gate("G9.FAILURE.MEMORY.APPEND_ONLY",
         failure.get("passive_lane") == "APPEND_ONLY"
         and failure.get("law") == "NEW_CAPABILITY_MUST_NOT_ERASE_PRIOR_FAILURE_EVIDENCE",
         "prior failure evidence remains passive append-only witness material")

    lane = doc.get("collaboration_lane", {})
    path = lane.get("path", [])
    gate("G10.TWO.LANE.ROUTING",
         "ACTIVE.CANDIDATE" in path and "COMPARE.PASSIVE" in path,
         "new capability proposals route through active candidate and passive comparison")

    gate("G11.SECOND.LOOK.REQUIRED",
         "SECOND.LOOK" in path and path.index("SECOND.LOOK") < path.index("VERIFY"),
         "second-look gate precedes formal verification")

    gate("G12.COLLABORATION.BOUNDARY",
         lane.get("boundary") == "COLLABORATIVE_SYSTEM_DESIGN_NE_BASE_MODEL_SELF_MODIFICATION"
         and "HUMAN.PROPOSAL" in path and "MODEL.ANALYSIS" in path and "SOURCE.CHECK" in path,
         "human-model collaboration is explicit but evidence-bounded")

    golden = doc.get("golden_chain", {})
    gate("G13.HUMANLOCK", golden.get("humanlock") is True,
         "HumanLock remains required")

    genius = doc.get("genius_bar", {})
    gate("G14.GOLDEN.CHAIN.INDEX.LOCK",
         genius.get("gate_count") == 14
         and genius.get("required_pass_count") == 14
         and len(genius.get("gates", [])) == 14
         and golden.get("public_index_target") == "0.5.FR.0333.GOLDEN.CHAIN.AI.CAPABILITY.EVOLUTION.0001",
         "14-gate rail targets append-only Golden Chain position 0.5")

    passed = sum(r["state"] == "PASS" for r in results)
    return {
        "identifier": "FR0333.GENIUS.AI.CAPABILITY.EVOLUTION.0001",
        "state": "PASS" if passed == 14 else "FAIL",
        "passed": passed,
        "total": 14,
        "results": results,
    }


def main():
    path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).with_name("fr0333_ai_capability_evolution_0001.json")
    doc = json.loads(path.read_text(encoding="utf-8"))
    report = validate(doc)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["state"] == "PASS" else 1)


if __name__ == "__main__":
    main()
