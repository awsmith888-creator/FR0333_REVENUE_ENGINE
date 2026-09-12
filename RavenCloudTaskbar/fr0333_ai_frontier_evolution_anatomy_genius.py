#!/usr/bin/env python3
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT = HERE / "fr0333_ai_frontier_evolution_anatomy_0001.json"

EXPECTED_REFS = [
    "A1","B2","C3","D4","E5","F6","G7","H8",
    "I9","J10","K11","L12","M13","N14","O15","P16"
]


def validate(doc):
    results = []

    def check(name, condition, detail):
        results.append({"gate": name, "state": "PASS" if condition else "FAIL", "detail": detail})

    check(
        "G1.IDENTIFIER.LOCK",
        doc.get("identifier") == "FR0333.AI.FRONTIER.EVOLUTION.ANATOMY.0001"
        and doc.get("golden_chain_identifier") == "FR.0333.GOLDEN.CHAIN.AI.FRONTIER.EVOLUTION.ANATOMY.0001",
        "canonical identifiers",
    )
    check(
        "G2.PARENT.RAIL.LOCK",
        doc.get("parent_rail") == "FR0333.AI.CAPABILITY.EVOLUTION.0001",
        "0.6 extends 0.5 rather than rewriting it",
    )

    sources = doc.get("source_lock", {}).get("sources", [])
    source_ids = {s.get("id") for s in sources}
    refs = doc.get("reference_points", [])
    used_sources = {r.get("source") for r in refs if r.get("source")}
    check(
        "G3.SOURCE.AUTHORITY",
        len(sources) >= 12 and used_sources.issubset(source_ids)
        and all(s.get("url", "").startswith("https://") for s in sources),
        "source registry is populated and every referenced source is registered",
    )

    ref_names = [r.get("reference_point") for r in refs]
    check(
        "G4.REFERENCE.POINT.SEQUENCE",
        ref_names == EXPECTED_REFS,
        "A1 through P16 ordered reference points",
    )

    units = [str(r.get("unit", "")) for r in refs]
    check(
        "G5.NO.PERCENT.UNITS",
        all("%" not in unit for unit in units),
        "reference-point units contain no percent symbols",
    )

    by_ref = {r["reference_point"]: r for r in refs}
    check(
        "G6.RACE.SPREAD.RECONSTRUCTION",
        by_ref.get("B2", {}).get("value") == 22
        and by_ref.get("C3", {}).get("value") == 5
        and by_ref.get("B2", {}).get("derivation") == "1503 minus 1481"
        and by_ref.get("C3", {}).get("derivation") == "66 minus 61",
        "race spread references reconstruct from cited leaderboard endpoints",
    )

    check(
        "G7.COMPUTE.SCALE.BOUNDARY",
        by_ref.get("D4", {}).get("value") == 5.0
        and by_ref.get("E5", {}).get("value") == 7
        and "CAPABILITY_GROWTH_NE_TRUTH_GROWTH" in doc.get("control_laws", []),
        "compute scaling is tracked without converting it into truth or reliability",
    )

    laws = set(doc.get("control_laws", []))
    check(
        "G8.AGENT.AUTONOMY.BOUNDARY",
        "AGENT_BENCHMARK_SUCCESS_NE_UNRESTRICTED_AUTONOMY" in laws
        and by_ref.get("J10", {}).get("value") == 660,
        "agent benchmark success is not promoted to unrestricted autonomy",
    )
    check(
        "G9.DIGITAL.PHYSICAL.BOUNDARY",
        "DIGITAL_TASK_SUCCESS_NE_PHYSICAL_WORLD_MASTERY" in laws
        and by_ref.get("K11", {}).get("value") == 120,
        "digital agent progress remains separated from embodied robotics",
    )
    check(
        "G10.SAFETY.ZERO.RISK.BOUNDARY",
        "SAFETY_FRAMEWORK_NE_ZERO_RISK" in laws
        and doc.get("safety_state", {}).get("openai_gpt5_6", {}).get("ai_self_improvement") == "BELOW_HIGH_VENDOR_CLASSIFICATION",
        "safety frameworks and model capability classifications do not establish zero risk",
    )
    check(
        "G11.CONSCIOUSNESS.BOUNDARY",
        "MODEL_INTELLIGENCE_NE_MODEL_CONSCIOUSNESS" in laws
        and by_ref.get("P16", {}).get("value") == "U.21.HOLD",
        "consciousness remains unestablished",
    )
    check(
        "G12.NO.BENEVOLENCE.GUARANTEE",
        "INTELLIGENCE_NE_BENEVOLENCE" in laws
        and "SMARTER_NE_HARMLESS" in laws,
        "intelligence is not treated as a guarantee of benevolence or harmlessness",
    )
    check(
        "G13.FAILURE.MEMORY.APPEND_ONLY",
        "NEW_CAPABILITY_MUST_NOT_DELETE_OLD_FAILURE_EVIDENCE" in laws
        and doc.get("golden_chain", {}).get("prior_entries_renumbered") is False,
        "new capability does not erase prior failure evidence or renumber history",
    )
    check(
        "G14.TWO.LANE.COMPATIBILITY",
        doc.get("golden_chain", {}).get("mode") == "EVOLUTION_OVERLAY_APPEND_ONLY"
        and "BENCHMARK_LEADER_NE_GENERAL_DOMINANCE" in laws,
        "active evolution overlay preserves passive historical evidence",
    )
    check(
        "G15.HUMANLOCK",
        doc.get("golden_chain", {}).get("humanlock") is True
        and "HUMANLOCK_REQUIRED_FOR_CANONICAL_PROMOTION" in laws,
        "HumanLock remains mandatory",
    )
    check(
        "G16.GOLDEN.CHAIN.INDEX.LOCK",
        doc.get("golden_chain", {}).get("public_index_target") == "0.6.FR.0333.GOLDEN.CHAIN.AI.FRONTIER.EVOLUTION.ANATOMY.0001"
        and doc.get("genius_bar", {}).get("gate_count") == 16
        and doc.get("genius_bar", {}).get("required_pass_count") == 16,
        "0.6 target and sixteen-gate invariant",
    )

    passed = sum(r["state"] == "PASS" for r in results)
    return {
        "identifier": "FR0333.GENIUS.AI.FRONTIER.EVOLUTION.ANATOMY.0001",
        "state": "PASS" if passed == len(results) else "FAIL",
        "passed": passed,
        "total": len(results),
        "invariant": "SIXTEEN.IN -> SIXTEEN.OUT",
        "results": results,
    }


def main():
    path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    doc = json.loads(path.read_text(encoding="utf-8"))
    report = validate(doc)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["state"] == "PASS" else 1)


if __name__ == "__main__":
    main()
