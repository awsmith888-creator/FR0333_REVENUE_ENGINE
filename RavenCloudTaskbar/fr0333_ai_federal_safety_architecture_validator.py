#!/usr/bin/env python3
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT = HERE / "fr0333_ai_federal_safety_architecture_2026_0001.json"

EXPECTED_LANES = [
    "1.EMERGENCY.INTERVENTION",
    "2.DEVELOPMENT.PROHIBITION",
    "3.FRONTIER.DUTY.OF.CARE",
    "4.AGENT.DISCOVERY.AND.CONTAINMENT",
    "5.MANDATORY.SAFETY.AUDIT.REGIME",
]

REQUIRED_LAWS = {
    "INCIDENT != LEGISLATIVE.PROOF",
    "PROPOSAL != LAW",
    "NEGOTIATION != FINAL.TEXT",
    "MODEL.MISALIGNMENT.EVENT != GENERAL.MODEL.BEHAVIOR",
    "CYBER.INCIDENT != EXISTENTIAL.CATASTROPHE",
    "AI.SOFTWARE.SAFETY != AI.INFRASTRUCTURE.ECONOMICS",
    "MULTIPLE.ARTICLES.REPORTING.SAME.EVENT != MULTIPLE.INDEPENDENT.EVENTS",
}


def validate(doc):
    results = []

    def gate(name, condition, detail):
        results.append({"gate": name, "state": "PASS" if condition else "FAIL", "detail": detail})

    gate("G1.IDENTIFIER", doc.get("identifier") == "FR0333.AI.FEDERAL.SAFETY.ARCHITECTURE.2026.0001", "canonical identifier")
    gate("G2.UNPROMOTED.HOLD", doc.get("state") == "WORKING.SPECIFICATION.UNPROMOTED" and doc.get("canonical_promotion") == "HOLD", "working specification remains unpromoted")
    gate("G3.HUMANLOCK", doc.get("humanlock") == "ACTIVE", "HumanLock is active")
    gate("G4.LANES", [x.get("id") for x in doc.get("policy_lanes", [])] == EXPECTED_LANES, "five policy lanes preserved in order")
    gate("G5.SEPARATE.RAIL", doc.get("separate_rail") == "AI.INFRASTRUCTURE.ECONOMICS", "infrastructure economics remains separate")
    gate("G6.EVIDENCE.LAWS", REQUIRED_LAWS.issubset(set(doc.get("evidence_gate", []))), "all evidence boundaries present")

    dup = doc.get("duplicate_control", {})
    gate("G7.DUPLICATE.COLLAPSE", dup.get("same_event_multiple_articles_collapse") is True and dup.get("duplicate_burst_weight") == 1 and dup.get("repetition_additive_weight") == 0, "duplicate media burst carries one logical event weight")

    contract = doc.get("claim_contract", {})
    required_fields = set(contract.get("required_fields", []))
    gate("G8.CLAIM.CONTRACT", {"claim_id", "lane", "source_url", "verification_state", "statutory_force", "evidence_class", "receipt"}.issubset(required_fields), "claim intake requires source and evidence fields")

    items = doc.get("policy_items", [])
    verified = all(item.get("verification_state") == "SOURCE_VERIFIED" for item in items)
    force_safe = all(
        item.get("statutory_force") not in {"ENACTED_LAW", "FINAL_RULE", "EFFECTIVE_GUIDANCE"}
        or item.get("evidence_class") == "PRIMARY_OFFICIAL"
        for item in items
    )
    gate("G9.SOURCE.VERIFICATION", verified if items else True, "every present policy item is source verified; empty intake is safe")
    gate("G10.STATUTORY.FORCE", force_safe, "binding legal force requires primary official evidence")

    promo = doc.get("promotion_gate", {})
    hold_required = (not verified) if items else True
    gate("G11.PROMOTION.GATE", promo.get("source_verification_required_per_claim") is True and promo.get("official_primary_source_required_for_statutory_force") is True and promo.get("current_result") == "HOLD" and hold_required, "promotion remains HOLD until source verification is complete")
    gate("G12.APPEND.ONLY", doc.get("record_mode") == "APPEND_ONLY_POLICY_TRACKING" and "PRIOR_VERIFIED_RECORDS_MUST_NOT_BE_REWRITTEN" in doc.get("append_only_rules", []), "record is append-only")

    passed = sum(x["state"] == "PASS" for x in results)
    return {
        "identifier": "FR0333.AI.FEDERAL.SAFETY.ARCHITECTURE.2026.0001.VALIDATION",
        "state": "PASS" if passed == len(results) else "FAIL",
        "passed": passed,
        "total": len(results),
        "canonical_promotion": "HOLD",
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
