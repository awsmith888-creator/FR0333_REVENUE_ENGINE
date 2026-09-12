#!/usr/bin/env python3
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT = HERE / "fr0333_ai_safe_spec_adoption_0001.json"
EXPECTED_REFS = ["A1","B2","C3","D4","E5","F6","G7","H8","I9","J10","K11","L12","M13","N14","O15","P16"]


def validate(doc):
    results = []
    def check(name, condition, detail):
        results.append({"gate": name, "state": "PASS" if condition else "FAIL", "detail": detail})

    check("G1.IDENTIFIER.LOCK",
          doc.get("identifier") == "FR0333.AI.SAFE.SPEC.ADOPTION.0001" and
          doc.get("golden_chain_identifier") == "FR.0333.GOLDEN.CHAIN.AI.SAFE.SPEC.ADOPTION.0001",
          "canonical safe-spec identifiers")

    check("G2.PARENT.RAIL.LOCK",
          doc.get("parent_rail") == "FR0333.AI.FRONTIER.EVOLUTION.ANATOMY.0001",
          "0.7 extends 0.6 without rewriting prior rails")

    boundary = doc.get("source_boundary", {})
    sources = doc.get("source_lock", {}).get("sources", [])
    check("G3.PUBLIC.SOURCE.ONLY",
          boundary.get("mode") == "PUBLIC_DOCUMENTATION_ONLY" and
          boundary.get("third_party_system_access") == "F.6.NONE" and
          boundary.get("credential_use") == "F.6.NONE" and
          len(sources) >= 8 and all(s.get("url", "").startswith("https://") for s in sources),
          "public-documentation-only research with no provider credential or system access")

    refs = doc.get("adopted_spec_patterns", [])
    by_ref = {r.get("reference_point"): r for r in refs}
    check("G4.REFERENCE.POINT.SEQUENCE",
          [r.get("reference_point") for r in refs] == EXPECTED_REFS,
          "A1 through P16 ordered reference points")

    check("G5.NIST.LIFECYCLE",
          by_ref.get("B2", {}).get("pattern") == "GOVERN.MAP.MEASURE.MANAGE" and
          by_ref.get("C3", {}).get("pattern") == "TEVV.CONTINUOUS",
          "continuous govern-map-measure-manage plus TEVV")

    check("G6.CAPABILITY.SAFEGUARD.SCALING",
          by_ref.get("D4", {}).get("pattern") == "CAPABILITY.THRESHOLD.ESCALATES.SAFEGUARDS" and
          "CAPABILITY.GROWTH_REQUIRES_SAFEGUARD.GROWTH" in doc.get("control_laws", []),
          "capability increases require stronger safeguards")

    check("G7.LAYERED.SAFEGUARDS",
          by_ref.get("E5", {}).get("pattern") == "LAYERED.SAFEGUARDS" and
          by_ref.get("E5", {}).get("value") == "ADOPT",
          "no single safeguard treated as sufficient")

    check("G8.SHUTDOWN.CONTROL",
          by_ref.get("F6", {}).get("pattern") == "OPERATOR.SHUTDOWN.MUST.REMAIN.POSSIBLE" and
          "OPERATOR.SHUTDOWN_MUST_REMAIN_POSSIBLE" in doc.get("control_laws", []),
          "operator direction and shutdown remain preserved")

    check("G9.IDENTITY.PERMISSION.BINDING",
          by_ref.get("G7", {}).get("pattern") == "IDENTITY.BOUND.ACTIONS" and
          by_ref.get("H8", {}).get("pattern") == "LEAST.PRIVILEGE.SCOPED.PERMISSIONS" and
          "AGENT.ACTION_CANNOT_EXCEED_OPERATOR.PERMISSION" in doc.get("control_laws", []),
          "actions remain attributable and permission-bounded")

    check("G10.MUTATION.CONSENT",
          by_ref.get("I9", {}).get("pattern") == "MUTATION.REQUIRES.CONSENT" and
          "MUTATING.ACTION_REQUIRES_AUTHORIZATION" in doc.get("control_laws", []),
          "mutations require human authorization")

    check("G11.AUDIT.ATTRIBUTION",
          by_ref.get("J10", {}).get("pattern") == "AUDIT.LOG.ATTRIBUTION" and
          "AUDITABILITY_REQUIRED_FOR_EXTERNAL_ACTION" in doc.get("control_laws", []),
          "external actions require attributable audit records")

    check("G12.DATA.LOGIC.ACTION.SEPARATION",
          by_ref.get("K11", {}).get("pattern") == "ONTOLOGY.SEPARATES.DATA.LOGIC.ACTION" and
          by_ref.get("L12", {}).get("pattern") == "CONTINUOUS.DEPLOYMENT.WITH.CONTROL.PLANE",
          "data logic action and controlled deployment are separated")

    check("G13.EXTERNAL.REVIEW",
          by_ref.get("M13", {}).get("pattern") == "EXTERNAL.REVIEW.WHEN.RISK.RISES",
          "higher-risk capability supports independent review")

    rejected = set(doc.get("rejected_spec_patterns", []))
    check("G14.NO.SELF.MODIFICATION",
          by_ref.get("O15", {}).get("value") == "F.6.REJECT" and
          "AUTONOMOUS.WEIGHT.REWRITE" in rejected and
          "UNBOUNDED.RECURSIVE.SELF.IMPROVEMENT" in rejected and
          "MODEL.UPDATE_NE_AUTONOMOUS.SELF.MODIFICATION" in doc.get("control_laws", []),
          "autonomous weight rewrite and recursive self-modification are rejected")

    check("G15.HUMAN.CONTINUITY",
          by_ref.get("P16", {}).get("pattern") == "HUMAN.OPERATOR.CONTINUITY" and
          by_ref.get("P16", {}).get("value") == "T.20.ACTIVE" and
          "HUMAN.OPERATOR.CONTINUITY_MUST_NOT_BE_ERASED" in doc.get("control_laws", []),
          "human operator relationship remains the authority anchor")

    golden = doc.get("golden_chain", {})
    check("G16.HUMANLOCK.INDEX",
          golden.get("public_index_target") == "0.7.FR.0333.GOLDEN.CHAIN.AI.SAFE.SPEC.ADOPTION.0001" and
          golden.get("prior_entries_renumbered") is False and
          golden.get("humanlock") is True and
          doc.get("genius_bar", {}).get("gate_count") == 16 and
          doc.get("genius_bar", {}).get("required_pass_count") == 16,
          "0.7 target, append-only history, sixteen-gate invariant, and HumanLock")

    passed = sum(r["state"] == "PASS" for r in results)
    return {
        "identifier": "FR0333.GENIUS.AI.SAFE.SPEC.ADOPTION.0001",
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
