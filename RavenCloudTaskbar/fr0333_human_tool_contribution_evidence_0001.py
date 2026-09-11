from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

MODULE_ID = "FR0333.HUMAN.TOOL.CONTRIBUTION.EVIDENCE.0001"
SCHEMA_PATH = Path(__file__).with_name("fr0333_human_tool_contribution_evidence_0001.schema.json")


class ValidationError(ValueError):
    pass


def load_schema(path: Path | str = SCHEMA_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _is_nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value) is not None


def _matches_condition(record: dict[str, Any], condition: dict[str, Any]) -> bool:
    for key, expected in condition.items():
        actual = record.get(key)
        if expected == "NONEMPTY":
            if not _is_nonempty(actual):
                return False
        elif expected == "SHA256":
            if not _is_sha256(actual):
                return False
        elif actual != expected:
            return False
    return True


def _check_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def _validate_structural(instance: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []
    expected_type = schema.get("type")
    if expected_type is not None:
        allowed = expected_type if isinstance(expected_type, list) else [expected_type]
        if not any(_check_type(instance, item) for item in allowed):
            return [f"{path}: expected type {allowed}"]

    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: must be one of {schema['enum']!r}")

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: string shorter than minLength")

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: fewer than minItems")
        if schema.get("uniqueItems") and len({json.dumps(v, sort_keys=True) for v in instance}) != len(instance):
            errors.append(f"{path}: items must be unique")
        if isinstance(schema.get("items"), dict):
            for index, value in enumerate(instance):
                errors.extend(_validate_structural(value, schema["items"], f"{path}[{index}]"))

    if isinstance(instance, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in instance:
                errors.append(f"{path}.{key}: required")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extras = sorted(set(instance) - set(properties))
            for key in extras:
                errors.append(f"{path}.{key}: additional property forbidden")
        for key, child_schema in properties.items():
            if key in instance:
                errors.extend(_validate_structural(instance[key], child_schema, f"{path}.{key}"))
    return errors


def evaluate_rail(rail_id: str, rail: dict[str, Any], schema: dict[str, Any]) -> str:
    terminals = schema["x-fr0333-terminal-states"]
    if not rail.get("applicable", False):
        return "T.20.PASS"

    contract = schema["x-fr0333-rail-contracts"][rail_id]

    for condition in contract.get("reject_when", []):
        if _matches_condition(rail, condition):
            return "F.6.REJECT"

    for condition in contract.get("hold_when", []):
        if _matches_condition(rail, condition):
            return "U.21.HOLD"

    if "pass_when" in contract and _matches_condition(rail, contract["pass_when"]):
        return "T.20.PASS"

    if any(_matches_condition(rail, condition) for condition in contract.get("pass_any", [])):
        return "T.20.PASS"

    terminal = contract.get("otherwise", "U.21.HOLD")
    if terminal not in terminals:
        raise ValidationError(f"{rail_id}: schema contains invalid terminal {terminal}")
    return terminal


def validate_record(instance: dict[str, Any], schema: dict[str, Any] | None = None) -> dict[str, Any]:
    schema = schema or load_schema()
    structural_errors = _validate_structural(instance, schema)
    if structural_errors:
        return {
            "module": MODULE_ID,
            "state": "F.6.REJECT",
            "structural_errors": structural_errors,
            "rail_results": {},
            "runtime_established": False,
            "promotion_allowed": False,
        }

    if instance["source_classification"]["source_name_used_to_auto_promote"]:
        return {
            "module": MODULE_ID,
            "state": "F.6.REJECT",
            "structural_errors": [],
            "rail_results": {},
            "runtime_established": False,
            "promotion_allowed": False,
            "reason": "EVIDENCE.CLASS MUST.NOT AUTO.PROMOTE BASED.ON SOURCE.NAME",
        }

    runtime = instance["runtime"]
    if runtime["state"] == "ESTABLISHED.BY.AUTHENTICATED.RECEIPT" and not _is_nonempty(runtime["receipt"]):
        return {
            "module": MODULE_ID,
            "state": "F.6.REJECT",
            "structural_errors": [],
            "rail_results": {},
            "runtime_established": False,
            "promotion_allowed": False,
            "reason": "runtime establishment requires authenticated receipt",
        }
    if runtime["state"] == "NOT.ESTABLISHED.UNTIL.RECEIPT" and _is_nonempty(runtime["receipt"]):
        return {
            "module": MODULE_ID,
            "state": "F.6.REJECT",
            "structural_errors": [],
            "rail_results": {},
            "runtime_established": False,
            "promotion_allowed": False,
            "reason": "runtime receipt contradicts NOT.ESTABLISHED state",
        }

    rail_results: dict[str, str] = {}
    declared_mismatches: list[str] = []
    for rail_id, rail in instance["rails"].items():
        derived = evaluate_rail(rail_id, rail, schema)
        rail_results[rail_id] = derived
        if rail.get("applicable", False) and rail["terminal_state"] != derived:
            declared_mismatches.append(
                f"{rail_id}: declared {rail['terminal_state']} but derived {derived}"
            )

    if declared_mismatches:
        state = "F.6.REJECT"
    elif any(state == "F.6.REJECT" for state in rail_results.values()):
        state = "F.6.REJECT"
    elif any(
        instance["rails"][rail_id].get("applicable", False) and state == "U.21.HOLD"
        for rail_id, state in rail_results.items()
    ):
        state = "U.21.HOLD"
    else:
        state = "T.20.PASS"

    runtime_established = (
        runtime["state"] == "ESTABLISHED.BY.AUTHENTICATED.RECEIPT"
        and _is_nonempty(runtime["receipt"])
    )
    promotion_allowed = state == "T.20.PASS"

    serialized = json.dumps(instance, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "module": MODULE_ID,
        "state": state,
        "structural_errors": [],
        "declared_mismatches": declared_mismatches,
        "rail_results": rail_results,
        "runtime_established": runtime_established,
        "promotion_allowed": promotion_allowed,
        "record_sha256": hashlib.sha256(serialized).hexdigest(),
        "hard_invariants": schema["x-fr0333-hard-invariants"],
    }


def validate_file(path: str | Path) -> dict[str, Any]:
    instance = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_record(instance)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("record")
    args = parser.parse_args()
    print(json.dumps(validate_file(args.record), indent=2, sort_keys=True))
