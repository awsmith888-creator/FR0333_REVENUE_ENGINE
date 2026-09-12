#!/usr/bin/env python3
import json
import pathlib
import sys

EXPECTED_ID = "FR0333.RED.SEA.DUAL.CHOKEPOINT.0001"
EXPECTED_GOLDEN = "FR.0333.GOLDEN.CHAIN.RED.SEA.DUAL.CHOKEPOINT.0001"
EXPECTED_REFS = ["A1","B2","C3","D4","E5","F6","G7","H8","I9","J10","K11","L12","M13","N14"]


def validate(doc):
    results = []

    def gate(name, ok, detail):
        results.append({"gate": name, "state": "PASS" if ok else "FAIL", "detail": detail})

    gate("G1.IDENTIFIER.LOCK",
         doc.get("identifier") == EXPECTED_ID and doc.get("golden_chain_identifier") == EXPECTED_GOLDEN,
         "canonical metric and Golden Chain identifiers")

    sources = doc.get("source_lock", {}).get("sources", [])
    gate("G2.SOURCE.AUTHORITY",
         len(sources) >= 7 and any(s.get("publisher") == "U.S. Energy Information Administration" for s in sources)
         and any(s.get("publisher") == "Reuters" for s in sources)
         and any(s.get("publisher") == "Associated Press" for s in sources)
         and any(s.get("publisher") == "Al Jazeera Arabic" for s in sources),
         "federal energy data plus independent and regional-language reporting")

    refs = doc.get("reference_points", [])
    gate("G3.REFERENCE.POINT.SEQUENCE",
         [r.get("reference_point") for r in refs] == EXPECTED_REFS and len(refs) == 14,
         "A1 through N14 present exactly once and in order")

    laws = set(doc.get("control_laws", []))
    gate("G4.HOUTHI.IRAN.DISTINCTION",
         "HOUTHI_ADVANCE_NE_DIRECT_IRANIAN_ATTACK" in laws
         and "IRANIAN_SUPPORT_NE_PROVEN_COMMAND_CONTROL" in laws,
         "Houthi operations and Iranian support are not collapsed into a direct-Iran-attack claim")

    gate("G5.FLOW.OWNERSHIP.DISTINCTION",
         "TRANSIT_FLOW_NE_RESOURCE_OWNERSHIP" in laws
         and "DUAL_CHOKEPOINT_PRESSURE_NE_UNIFIED_PHYSICAL_CONTROL" in laws,
         "transit leverage is not misreported as ownership of oil or gas")

    by_ref = {r.get("reference_point"): r for r in refs}
    c3 = by_ref.get("C3", {}).get("value")
    d4 = by_ref.get("D4", {}).get("value")
    e5 = by_ref.get("E5", {}).get("value")
    f6 = by_ref.get("F6", {}).get("value")
    g7 = by_ref.get("G7", {}).get("value")
    per1000_ok = isinstance(c3, (int, float)) and isinstance(d4, (int, float)) and d4 > 0 \
        and round(c3 / d4 * 1000) == e5 \
        and isinstance(f6, (int, float)) and round(f6 / d4 * 1000) == g7
    gate("G6.PER1000.RECONSTRUCTION", per1000_ok,
         "Bab el-Mandeb and Hormuz per-1000 references reconstruct from same-quarter oil-flow denominator")

    gate("G7.NO_DOUBLE.COUNTING",
         by_ref.get("H8", {}).get("value") == "U.21.HOLD"
         and "BAB_EL_MANDEB_PLUS_HORMUZ_MUST_NOT_BE_SUMMED_WITHOUT_OVERLAP_ADJUSTMENT" in laws,
         "dual chokepoint values are not naively summed")

    gate("G8.PLEDGE.ENACTMENT.DISTINCTION",
         by_ref.get("K11", {}).get("class") == "POLITICAL_PROPOSAL_NOT_ENACTED"
         and "CAMPAIGN_PLEDGE_NE_ENACTED_SPENDING" in laws,
         "political pledge remains distinct from enacted fiscal policy")

    gate("G9.CONGRESSIONAL.AUTHORITY",
         by_ref.get("M13", {}).get("value") == "REQUIRED_FOR_SPENDING_PROGRAM"
         and "ELECTION_CONDITION_NE_EXECUTIVE_SPENDING_AUTHORITY" in laws,
         "spending authority boundary remains explicit")

    gate("G10.TEMPORAL.CAUSATION.BOUNDARY",
         "TEMPORAL_OVERLAP_NE_CAUSATION" in laws
         and by_ref.get("N14", {}).get("value") == "F.6.NOT_ESTABLISHED",
         "timing overlap is not promoted into geopolitical-electoral causation")

    gate("G11.MORAL.FRAME.BOUNDARY",
         "RETALIATION_OR_REVENGE_FRAMING_NE_VERIFIED_MORAL_JUSTIFICATION" in laws
         and doc.get("human_cost_boundary", {}).get("state") == "ACTIVE",
         "human harm is preserved without converting moral framing into verified fact")

    regional = doc.get("regional_language_findings", {})
    gate("G12.REGIONAL.LANGUAGE.CLASSIFICATION",
         regional.get("classification") == "OFFICIAL_POLITICAL_FRAMING_NOT_COMMAND_RECEIPT"
         and regional.get("source") == "SRC.007",
         "regional-language official framing is retained but bounded")

    golden = doc.get("golden_chain", {})
    gate("G13.HUMANLOCK",
         golden.get("humanlock") is True,
         "HumanLock remains required for promotion")

    genius = doc.get("genius_bar", {})
    gate("G14.GOLDEN.CHAIN.INDEX.LOCK",
         genius.get("gate_count") == 14
         and genius.get("required_pass_count") == 14
         and len(genius.get("gates", [])) == 14
         and golden.get("public_index_target") == "0.4.FR.0333.GOLDEN.CHAIN.RED.SEA.DUAL.CHOKEPOINT.0001",
         "14-gate rail targets append-only Golden Chain index 0.4")

    passed = sum(r["state"] == "PASS" for r in results)
    return {
        "identifier": "FR0333.GENIUS.RED.SEA.DUAL.CHOKEPOINT.0001",
        "state": "PASS" if passed == 14 else "FAIL",
        "passed": passed,
        "total": 14,
        "results": results,
    }


def main():
    path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).with_name("fr0333_red_sea_dual_chokepoint_0001.json")
    doc = json.loads(path.read_text(encoding="utf-8"))
    report = validate(doc)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["state"] == "PASS" else 1)


if __name__ == "__main__":
    main()
