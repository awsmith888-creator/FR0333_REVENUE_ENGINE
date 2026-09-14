from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TASKBAR = ROOT / "RavenCloudTaskbar"
MANIFEST = TASKBAR / "fr0333_extraction_manifest_pr17_successor_0001.json"
STRONGHOLD_BLOB = "056d63083395b5d092a23c4764cc81520acad8cb"

MUTATION_1_7_REQUIRED: dict[str, Any] = {
    "NUMERIC_ROLE_MUTATION": "1.7",
    "SEVEN_REGULATOR_STATE": "CONDITIONAL",
    "SEVEN_REGULATOR_ACTIVATION": "EIGHT.CONDITION.REACHED.AND.INCOMING.POWER.REQUIRES.REGULATION",
    "DIGIT_VALUE_NE_FUNCTIONAL_ROLE": True,
    "SUFFIX_7_INHERITS_REGULATOR_ROLE": False,
    "GC_SB_0027_AUTO_REGULATOR": False,
    "POSITION_27_ROLE": "UNASSIGNED.UNLESS.SEPARATELY.ESTABLISHED",
}

AI_PUBLIC_CLASSES = {"EvidenceState", "Capability", "ToolChange"}
AI_PUBLIC_FUNCTIONS = {"compile_report", "write_report"}
MARIAH_PUBLIC_FUNCTIONS = {
    "load_register",
    "validate_register",
    "compile_adobe_reference_context",
    "validate_file",
}


def git_blob(path: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", path], cwd=ROOT, text=True
    ).strip()


def literal_assignments(tree: ast.AST) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in MUTATION_1_7_REQUIRED:
                try:
                    values[name] = ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    values[name] = "<NON_LITERAL>"
    return values


def loaded_names(node: ast.AST) -> set[str]:
    return {
        child.id
        for child in ast.walk(node)
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load)
    }


def top_level_contract(tree: ast.Module) -> tuple[set[str], set[str]]:
    classes = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
    functions = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    return classes, functions


def validate_manifest() -> dict[str, Any]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = data["entries"]
    if len(entries) != 12:
        raise AssertionError(f"E2 requires 12 source-delta entries, got {len(entries)}")

    counts = {"COPY": 0, "TRANSFORM": 0, "OMIT": 0}
    seen: set[str] = set()
    for entry in entries:
        source = entry["source_path"]
        if source in seen:
            raise AssertionError(f"duplicate E2 source path: {source}")
        seen.add(source)
        classification = entry["classification"]
        if classification not in counts:
            raise AssertionError(f"unclassified E2 state: {classification}")
        counts[classification] += 1

        if classification in {"COPY", "TRANSFORM"}:
            destination = entry["destination_path"]
            observed = git_blob(destination)
            expected = entry["target_blob_sha"]
            if observed != expected:
                raise AssertionError(
                    f"target blob mismatch for {destination}: {observed} != {expected}"
                )
            if classification == "COPY" and entry["source_blob_sha"] != expected:
                raise AssertionError(f"COPY is not byte-identical: {source}")

    if counts != {"COPY": 9, "TRANSFORM": 2, "OMIT": 1}:
        raise AssertionError(f"E2 classification balance mismatch: {counts}")

    balance = data["classification_balance"]
    if balance != {
        "source_delta": 12,
        "copy": 9,
        "transform": 2,
        "omit": 1,
        "unclassified": 0,
    }:
        raise AssertionError(f"manifest balance record mismatch: {balance}")

    taskbars_blob = git_blob("RavenCloudTaskbar/taskbars.json")
    if taskbars_blob != STRONGHOLD_BLOB:
        raise AssertionError(
            f"Stronghold taskbars drift: {taskbars_blob} != {STRONGHOLD_BLOB}"
        )

    return data


def validate_e3_e4() -> dict[str, Any]:
    ai_path = TASKBAR / "ai_image_tool_metrics.py"
    ai_tree = ast.parse(ai_path.read_text(encoding="utf-8"), filename=str(ai_path))
    assignments = literal_assignments(ai_tree)

    for name, expected in MUTATION_1_7_REQUIRED.items():
        observed = assignments.get(name, "<MISSING>")
        if observed != expected:
            raise AssertionError(f"E3 mutation bound failed: {name}={observed!r}, expected {expected!r}")

    compile_node = next(
        (
            node
            for node in ai_tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "compile_report"
        ),
        None,
    )
    if compile_node is None:
        raise AssertionError("E4 missing public function compile_report")

    consumed = loaded_names(compile_node)
    missing_consumption = sorted(set(MUTATION_1_7_REQUIRED) - consumed)
    if missing_consumption:
        raise AssertionError(
            "E3 controls declared but not consumed by compile_report: "
            + ", ".join(missing_consumption)
        )

    ai_classes, ai_functions = top_level_contract(ai_tree)
    if not AI_PUBLIC_CLASSES.issubset(ai_classes):
        raise AssertionError(f"E4 AI public classes missing: {sorted(AI_PUBLIC_CLASSES - ai_classes)}")
    if not AI_PUBLIC_FUNCTIONS.issubset(ai_functions):
        raise AssertionError(f"E4 AI public functions missing: {sorted(AI_PUBLIC_FUNCTIONS - ai_functions)}")

    mariah_path = TASKBAR / "mariah_carey_chomp.py"
    mariah_tree = ast.parse(mariah_path.read_text(encoding="utf-8"), filename=str(mariah_path))
    _, mariah_functions = top_level_contract(mariah_tree)
    if not MARIAH_PUBLIC_FUNCTIONS.issubset(mariah_functions):
        raise AssertionError(
            f"E4 Mariah public functions missing: {sorted(MARIAH_PUBLIC_FUNCTIONS - mariah_functions)}"
        )

    return {
        "E3": "T.20",
        "E4": "T.20",
        "qualifier": "BOUNDED.STRUCTURAL.AND.CONTRACT.EQUIVALENCE",
        "mutation": "1.7",
        "controls_declared_consumed_exposed": True,
    }


def main() -> None:
    manifest = validate_manifest()
    gates = validate_e3_e4()
    receipt = {
        "receipt_id": "FR0333.E3.E4.RECEIPT.PR17.SUCCESSOR.0001",
        "source_head": manifest["source"]["head_sha"],
        "payload_head_sha": manifest["target"]["payload_head_sha"],
        "e2_state": "T.20",
        "e3_state": gates["E3"],
        "e4_state": gates["E4"],
        "stronghold_state": "T.20",
        "truth_state": "T.20",
        "qualifier": gates["qualifier"],
        "promotion": "HUMANLOCK_REQUIRED",
        "external_runtime": "NOT_ESTABLISHED",
    }
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
