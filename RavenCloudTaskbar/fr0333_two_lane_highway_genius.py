#!/usr/bin/env python3
import json
import pathlib
import sys

EXPECTED_ID = "FR0333.TWO_LANE.HIGHWAY.0001"
EXPECTED_GOLDEN = "FR.0333.GOLDEN.CHAIN.TWO.LANE.HIGHWAY.0001"
EXPECTED_REFS = [
    "A1","B2","C3","D4","E5","F6","G7","H8","I9","J10","K11","L12","M13","N14"
]
EXPECTED_PATH = [
    "ACTIVE.RESEARCH","FAN.OUT","MULTI.SOURCE","SECOND.LOOK","VERIFY",
    "COMPARE.PASSIVE","GENIUS","HUMANLOCK","ACTIVE.CANONICAL.PROMOTION",
    "APPEND.WITNESS.SNAPSHOT","PASSIVE.HISTORY"
]


def validate(doc):
    results = []

    def gate(name, ok, detail):
        results.append({"gate": name, "state": "PASS" if ok else "FAIL", "detail": detail})

    gate("G1.REGISTRY.ID.LOCK",
         doc.get("registry_id") == EXPECTED_ID and doc.get("golden_chain_identifier") == EXPECTED_GOLDEN,
         "canonical registry and Golden Chain identifiers")

    refs = doc.get("reference_points", [])
    gate("G2.REFERENCE.POINT.SEQUENCE",
         [r.get("reference_point") for r in refs] == EXPECTED_REFS and len(refs) == 14,
         "A1 through N14 present exactly once and in order")

    active = doc.get("active_lane", {})
    passive = doc.get("passive_lane", {})
    invariants = set(doc.get("core_invariants", []))
    gate("G3.ACTIVE.PASSIVE.SEPARATION",
         "ACTIVE_MUST_NOT_OVERWRITE_PASSIVE" in invariants
         and "PASSIVE_MUST_NOT_BLOCK_ACTIVE" in invariants
         and active.get("non_blocking") is True,
         "active advances while passive remains a non-blocking witness")

    gate("G4.PASSIVE.APPEND.ONLY",
         passive.get("write_mode") == "APPEND.ONLY"
         and passive.get("mutation_policy") == "NO_OVERWRITE_NO_COMPRESSION_NO_RENUMBERING"
         and "PASSIVE.WRITE.MODE_APPEND_ONLY" in invariants,
         "passive lane is append-only and non-destructive")

    second = doc.get("second_look_gate", {})
    second_laws = set(second.get("laws", []))
    gate("G5.SECOND.LOOK.BOUNDARY",
         second.get("reference_point") == "D4"
         and "SOURCE.ONE_NE_CORROBORATION" in second_laws
         and "AI.SYNTHESIS_NE_VERIFIED.FACT" in second_laws,
         "synthesis is isolated from corroboration and verification")

    interlock = doc.get("four_gate_interlock", {})
    gate("G6.FOUR.GATE.INTERLOCK",
         interlock.get("gate_count") == 4
         and interlock.get("terminal_transition_count") == 1
         and interlock.get("gates") == ["E5.VERIFY","F6.COMPARE.PASSIVE","G7.GENIUS","H8.HUMANLOCK"]
         and interlock.get("terminal_transition") == "I9.ACTIVE.CANONICAL.PROMOTION",
         "four gates plus one terminal promotion transition")

    golden = doc.get("golden_chain", {})
    gate("G7.HUMANLOCK.REQUIRED",
         golden.get("humanlock") is True and "HUMANLOCK" in doc.get("promotion_path", []),
         "HumanLock is mandatory in the promotion path")

    execution = doc.get("execution_interlock", {})
    exec_laws = set(execution.get("laws", []))
    gate("G8.EXECUTION.INTERLOCK",
         execution.get("reference_point") == "L12"
         and "RESEARCH.CAPABILITY_NE_EXTERNAL.ACTION" in exec_laws
         and "AI.ORCHESTRATION_NE_PROVIDER.EXECUTION" in exec_laws
         and execution.get("runtime_state") == "U.21.HOLD",
         "research and orchestration do not imply external execution")

    governance = doc.get("data_governance", {})
    gov_laws = set(governance.get("laws", []))
    gate("G9.DATA.GOVERNANCE.SEPARATION",
         governance.get("reference_point") == "M13"
         and {"CONNECTED_NE_AUTHORIZED.FOR.ALL.ACTIONS","DISCONNECT_NE_DELETE","SOURCE.STATE_NE_SESSION.STATE","ORIGINAL.FILE_NE_EDITED.VERSION"}.issubset(gov_laws),
         "connection, authorization, retention, source, session, and version states remain separated")

    terminal = doc.get("terminal_control_matrix", {})
    gate("G10.RUNTIME.CLAIM.HOLD",
         doc.get("runtime_execution") == "U.21.HOLD"
         and doc.get("empirical_runtime_receipt") == "U.21.HOLD"
         and doc.get("external_registry_write") == "NOT.ESTABLISHED"
         and terminal.get("runtime_execution") == "U.21.HOLD",
         "runtime and external registry claims remain unpromoted")

    source_boundary = doc.get("source_boundary", {})
    gate("G11.BYTE.ISOLATION.SPEC.ONLY",
         source_boundary.get("byte_level_isolation") == "SPECIFICATION.ISOLATION.DEFINED"
         and source_boundary.get("internal_runtime_claim") == "NOT_ESTABLISHED",
         "byte-level isolation is a specification claim only")

    gate("G12.STOP.CONTROL.REQUIREMENT",
         source_boundary.get("user_interrupt_control") == "STOP.CONTROL.REQUIRED"
         and source_boundary.get("hardware_stop_vector") == "NOT_CLAIMED",
         "user interrupt is required without fabricating hardware runtime")

    gate("G13.AUTO.PROMOTION.DISABLED",
         terminal.get("auto_continue") == "F.6.NONE"
         and terminal.get("auto_promotion") == "F.6.NONE",
         "no automatic continuation or promotion")

    genius = doc.get("genius_bar", {})
    gate("G14.GOLDEN.CHAIN.INDEX.LOCK",
         genius.get("gate_count") == 14
         and genius.get("required_pass_count") == 14
         and len(genius.get("gates", [])) == 14
         and golden.get("public_index_target") == "0.3.FR.0333.GOLDEN.CHAIN.TWO.LANE.HIGHWAY.0001"
         and doc.get("promotion_path") == EXPECTED_PATH,
         "14-gate rail targets append-only Golden Chain index 0.3")

    passed = sum(row["state"] == "PASS" for row in results)
    return {
        "identifier": "FR0333.GENIUS.TWO.LANE.HIGHWAY.0001",
        "state": "PASS" if passed == 14 else "FAIL",
        "passed": passed,
        "total": 14,
        "results": results
    }


def main():
    path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).with_name("fr0333_two_lane_highway_0001.json")
    doc = json.loads(path.read_text(encoding="utf-8"))
    report = validate(doc)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["state"] == "PASS" else 1)


if __name__ == "__main__":
    main()
