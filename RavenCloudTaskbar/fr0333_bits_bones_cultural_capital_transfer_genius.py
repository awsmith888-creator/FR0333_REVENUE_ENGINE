#!/usr/bin/env python3
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT = HERE / "fr0333_bits_bones_cultural_capital_transfer_0002.json"

EXPECTED_PIPELINE = [
    "CREATION",
    "OWNERSHIP",
    "DISTRIBUTION",
    "MARKET.TRANSLATION",
    "VISUAL.IDENTITY",
    "REWARD",
    "RECOGNITION",
    "LEGACY",
]

REQUIRED_LAWS = {
    "CULTURAL_EXCHANGE_NE_EXPLOITATION",
    "INFLUENCE_NE_THEFT",
    "COVER_VERSION_NE_APPROPRIATION_BY_DEFAULT",
    "POPULARIZATION_NE_ORIGIN",
    "STRUCTURAL_BARRIER_NE_ABSOLUTE_BARRIER",
    "AUDIO_IDENTITY_NE_VISUAL_IDENTITY",
    "OBSERVED_NE_CORRELATED_NE_CAUSAL",
    "DIRECT_THEFT_CLAIM_REQUIRES_DIRECT_EVIDENCE",
    "HUMANLOCK_REQUIRED_FOR_CANONICAL_PROMOTION",
}


def validate(doc):
    results = []

    def check(name, condition, detail):
        results.append({"gate": name, "state": "PASS" if condition else "FAIL", "detail": detail})

    check(
        "G1.IDENTIFIER.LOCK",
        doc.get("identifier") == "FR0333.BITS.BONES.CULTURAL.CAPITAL.TRANSFER.0002"
        and doc.get("golden_chain_identifier") == "FR.0333.GOLDEN.CHAIN.BITS.BONES.CULTURAL.CAPITAL.TRANSFER.0002",
        "canonical identifiers",
    )
    check(
        "G2.PIPELINE.LOCK",
        doc.get("pipeline") == EXPECTED_PIPELINE,
        "creation through legacy pipeline including market translation and visual identity",
    )
    creation = doc.get("creation_field_map", {})
    check(
        "G3.CREATION.GRANULARITY",
        set(creation) == {"composition", "performance", "arrangement", "production"},
        "creative contribution is not collapsed into legal authorship alone",
    )
    evidence = doc.get("metric_evidence_boundaries", [])
    evidence_classes = {x.get("source_class") for x in evidence}
    check(
        "G4.EVIDENCE.CLASS.BOUNDARY",
        {"AUDITED_FINANCIAL_RECORD", "HISTORICALLY_CORROBORATED_RECOLLECTION", "PUBLIC_ANECDOTE"}.issubset(evidence_classes),
        "financial and narrative evidence classes remain distinct",
    )
    visual = doc.get("visual_identity", {})
    fields = visual.get("fields", {})
    check(
        "G5.VISUAL.IDENTITY.GATE",
        "artist_face_on_cover" in fields
        and "substitute_subject" in fields
        and "label_marketing_intent" in fields
        and "crossover_target" in fields,
        "visual packaging is measurable without automatic intent inference",
    )
    laws = set(doc.get("control_laws", []))
    check(
        "G6.CONTROL.LAWS",
        REQUIRED_LAWS.issubset(laws),
        "exchange, theft, causality, structural barrier, visual identity, and HumanLock boundaries",
    )
    cases = {c.get("case_id"): c for c in doc.get("cases", [])}
    check(
        "G7.HOUND.DOG.CASE",
        cases.get("CASE.0001.HOUND.DOG", {}).get("evidence_boundaries", {}).get("direct_composition_theft_by_presley") == "F.6.NOT_SUPPORTED"
        and cases.get("CASE.0001.HOUND.DOG", {}).get("evidence_boundaries", {}).get("structural_commercial_divergence") == "T.20.SUPPORTED",
        "case 0001 separates unsupported direct theft from supported structural divergence",
    )
    tutti = cases.get("CASE.0002.TUTTI.FRUTTI", {})
    check(
        "G8.TUTTI.FRUTTI.CASE",
        tutti.get("metrics", {}).get("little_richard_pop_peak") == 17
        and tutti.get("metrics", {}).get("pat_boone_pop_peak") == 12
        and tutti.get("evidence_boundaries", {}).get("exact_boone_vs_richard_artist_earnings_delta") == "U.21.NOT_ESTABLISHED",
        "case 0002 preserves ordinal chart data and revenue hold",
    )
    sources = doc.get("source_lock", {}).get("sources", [])
    check(
        "G9.SOURCE.REGISTRY",
        len(sources) >= 8 and all(s.get("url", "").startswith("https://") for s in sources),
        "public source registry present with HTTPS references",
    )
    golden = doc.get("golden_chain", {})
    genius = doc.get("genius_bar", {})
    check(
        "G10.GOLDEN.CHAIN.HUMANLOCK",
        golden.get("public_index_target") == "0.8.FR.0333.GOLDEN.CHAIN.BITS.BONES.CULTURAL.CAPITAL.TRANSFER.0002"
        and golden.get("prior_entries_renumbered") is False
        and golden.get("humanlock") is True
        and genius.get("gate_count") == 10
        and genius.get("required_pass_count") == 10,
        "0.8 append-only target with ten-gate invariant and HumanLock",
    )

    passed = sum(r["state"] == "PASS" for r in results)
    return {
        "identifier": "FR0333.GENIUS.BITS.BONES.CULTURAL.CAPITAL.TRANSFER.0002",
        "state": "PASS" if passed == len(results) else "FAIL",
        "passed": passed,
        "total": len(results),
        "invariant": "TEN.IN -> TEN.OUT",
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
