#!/usr/bin/env python3
import json
import math
import pathlib
import sys

EXPECTED_ID = "FR0333.CENSUS.BLACK.DETAILED.ORIGIN.0001"
EXPECTED_EXAMPLES = ["African American","Jamaican","Haitian","Nigerian","Ethiopian","Somali"]
EXPECTED_2020 = {
    "African American": 24569479,
    "Jamaican": 1047117,
    "Haitian": 1032737,
    "Nigerian": 604077,
    "Ethiopian": 325214,
    "Somali": 221043,
    "Trinidadian and Tobagonian": 194364,
    "Ghanaian": 172558,
    "Congolese": 110537,
    "Kenyan": 104708,
    "South African": 86528,
    "Cameroonian": 77058,
    "Liberian": 71379,
    "Eritrean": 69060,
}
EXPECTED_USVI = {
    "USVI_TOTAL_POPULATION": 87146,
    "USVI_BLACK_OR_AFRICAN_AMERICAN_ALONE": 62183,
    "USVI_BLACK_OR_AFRICAN_AMERICAN_ALONE_OR_IN_COMBINATION": 67769,
    "USVI_AFRICAN_AMERICAN_ALONE": 18867,
    "US_VIRGIN_ISLANDER_ALONE": 2565,
    "US_VIRGIN_ISLANDER_ALONE_OR_IN_ANY_COMBINATION": 2756,
}

def validate(doc):
    results = []

    def gate(name, ok, detail):
        results.append({"gate": name, "state": "PASS" if ok else "FAIL", "detail": detail})

    gate("G1.IDENTIFIER_LOCK",
         doc.get("identifier") == EXPECTED_ID and doc.get("golden_chain_identifier","").startswith("FR.0333.GOLDEN.CHAIN."),
         "canonical identifiers")

    laws = set(doc.get("control_laws", []))
    gate("G2.UMBRELLA_DETAIL_SEPARATION",
         "BLACK_OR_AFRICAN_AMERICAN_UMBRELLA_NE_AFRICAN_AMERICAN_DETAILED_IDENTITY" in laws,
         "umbrella and detailed identity are not interchangeable")

    gate("G3.QUESTIONNAIRE_EXAMPLE_LOCK",
         doc.get("questionnaire_examples_2020") == EXPECTED_EXAMPLES,
         "2020 form examples preserved in source order")

    sources = doc.get("source_lock", {}).get("sources", [])
    source_ok = len(sources) >= 8 and all(
        s.get("publisher") == "U.S. Census Bureau" and "census.gov" in s.get("url","")
        for s in sources
    )
    gate("G4.SOURCE_AUTHORITY_LOCK", source_ok, "all registered sources are Census Bureau sources")

    rows = doc.get("metrics_2020_dhc_a_alone_or_in_any_combination", [])
    observed = {r.get("identity"): r.get("value") for r in rows}
    rail_ok = observed == EXPECTED_2020 and all(
        r.get("universe") == "BLACK_OR_AFRICAN_AMERICAN_ALONE_OR_IN_ANY_COMBINATION"
        and r.get("class") == "MEASURED_DECENNIAL_COUNT"
        for r in rows
    )
    gate("G5.DHC_A_COUNT_RAIL_LOCK", rail_ok, "14-count DHC-A rail exact")

    rr = doc.get("reference_ratio_rail", {})
    denom = rr.get("denominator_value")
    ratio_rows = rr.get("metrics", [])
    ratio_ok = denom == EXPECTED_2020["African American"] and len(ratio_rows) == 13
    if ratio_ok:
        for r in ratio_rows:
            name = r["identity"]
            expected = round(EXPECTED_2020[name] * 1000 / denom, 3)
            if not math.isclose(r["value"], expected, abs_tol=0.0005):
                ratio_ok = False
                break
            if r.get("unit") != "persons_per_1000_african_american_reference":
                ratio_ok = False
                break
    gate("G6.REFERENCE_RATIO_RECONSTRUCTION", ratio_ok, "all 13 reference ratios reconstruct from measured counts")

    usvi_rows = doc.get("usvi_2020_island_area_metrics", [])
    usvi_observed = {r.get("name"): r.get("value") for r in usvi_rows}
    usvi_ok = usvi_observed == EXPECTED_USVI and all(r.get("source") == "SRC.006" for r in usvi_rows)
    gate("G7.USVI_GEOGRAPHY_LOCK", usvi_ok, "USVI kept as Island Areas geography with exact counts")

    acs_rows = doc.get("acs_2024_black_alone_selected_groups", [])
    comp = doc.get("comparability_gate", {})
    acs_ok = len(acs_rows) == 7 and all(
        r.get("universe") == "2024_ACS_1_YEAR_BLACK_ALONE" and r.get("class") == "ACS_ESTIMATE"
        for r in acs_rows
    ) and comp.get("state") == "HOLD_FOR_DIRECT_GROWTH_CALCULATION"
    gate("G8.ACS_UNIVERSE_SEPARATION", acs_ok, "ACS rail separated from decennial alone-or-combination rail")

    logic = doc.get("classification_logic", {})
    boundary_ok = (
        logic.get("detailed_identity") == "PRESERVE_AS_REPORTED"
        and logic.get("citizenship_inference") == "NOT_ALLOWED"
        and logic.get("nationality_inference") == "NOT_ALLOWED"
        and logic.get("language_inference") == "NOT_ALLOWED"
        and logic.get("economic_contribution_test") == "NOT_A_CLASSIFICATION_REQUIREMENT"
        and "ECONOMIC_CONTRIBUTION_NE_CLASSIFICATION_QUALIFIER" in laws
    )
    gate("G9.CLASSIFICATION_BOUNDARY_LOCK", boundary_ok, "classification does not infer nationality, citizenship, language, or economic qualification")

    genius = doc.get("genius_bar", {})
    golden = doc.get("golden_chain", {})
    promotion_ok = (
        genius.get("gate_count") == 10
        and genius.get("required_pass_count") == 10
        and len(genius.get("gates", [])) == 10
        and golden.get("humanlock") is True
        and "ALL_10_GENIUS_GATES_PASS" in golden.get("promotion_rule","")
    )
    gate("G10.GOLDEN_CHAIN_PROMOTION_LOCK", promotion_ok, "ten-in ten-out Genius gate with HumanLock")

    passed = sum(r["state"] == "PASS" for r in results)
    return {
        "identifier": "FR0333.GENIUS.CENSUS.BLACK.DETAILED.ORIGIN.0001",
        "state": "PASS" if passed == 10 else "FAIL",
        "passed": passed,
        "total": 10,
        "results": results,
    }

def main():
    path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).with_name("fr0333_census_black_detailed_origin_0001.json")
    doc = json.loads(path.read_text(encoding="utf-8"))
    report = validate(doc)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["state"] == "PASS" else 1)

if __name__ == "__main__":
    main()
