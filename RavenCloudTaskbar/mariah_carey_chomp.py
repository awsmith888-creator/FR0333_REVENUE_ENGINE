from __future__ import annotations

import json
from pathlib import Path
from typing import Any


MODULE_ID = "FR0333.ADOBE.MARIAH.CAREY.CHOMP.0001"
PARENT_ID = "FR0333.AI.IMAGE.TOOL.METRICS.0001"
VERSION = "1.0.0"
ALLOWED_STATES = {
    "OBSERVED",
    "REPORTED",
    "ESTIMATE",
    "DYNAMIC",
    "TABLE_COUNT",
    "TABLE_SUM",
    "HOLD",
}


def load_register(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def _route_source(bit: str, routes: dict[str, list[str]]) -> list[str]:
    matches = [(prefix, refs) for prefix, refs in routes.items() if bit.startswith(prefix)]
    if not matches:
        raise ValueError(f"no source route for bit: {bit}")
    return max(matches, key=lambda item: len(item[0]))[1]


def _state(bit: str) -> str:
    state = bit.rsplit(".", 1)[-1]
    if state not in ALLOWED_STATES:
        raise ValueError(f"unsupported evidence state in bit: {bit}")
    return state


def validate_register(data: dict[str, Any]) -> dict[str, Any]:
    if data.get("module_id") != MODULE_ID:
        raise ValueError("module_id mismatch")
    if data.get("parent_id") != PARENT_ID:
        raise ValueError("parent_id mismatch")
    if data.get("version") != VERSION:
        raise ValueError("version mismatch")
    if data.get("golden_chain_binding") != "CHILD.REFERENCE.PACK.NO_NEW_GLOBAL_POSITION":
        raise ValueError("reference pack must not claim a new global bit")

    sources = data.get("sources", {})
    routes = data.get("source_routes", {})
    statistical = data.get("statistical_bits", [])
    money = data.get("money_bits", [])
    bits = statistical + money

    if len(statistical) != 51 or len(money) != 9 or len(bits) != 60:
        raise ValueError("register requires 51 statistical bits and 9 money bits")
    if len(bits) != len(set(bits)):
        raise ValueError("bit identifiers must be unique")
    if not sources or not routes:
        raise ValueError("sources and source_routes are required")

    unresolved_sources: set[str] = set()
    states: dict[str, int] = {state: 0 for state in ALLOWED_STATES}
    for bit in bits:
        if not bit.startswith("MC."):
            raise ValueError(f"invalid bit namespace: {bit}")
        states[_state(bit)] += 1
        unresolved_sources.update(ref for ref in _route_source(bit, routes) if ref not in sources)
    if unresolved_sources:
        raise ValueError(f"unresolved source references: {sorted(unresolved_sources)}")

    holds = data.get("holds", [])
    if len(holds) != 7:
        raise ValueError("seven documented data holds are required")
    if len({item["id"] for item in holds}) != len(holds):
        raise ValueError("hold identifiers must be unique")
    if any(item.get("promotion") != "HOLD" for item in holds):
        raise ValueError("every unresolved conflict must remain HOLD")

    human_line = data.get("human_line", [])
    if len(human_line) != 9:
        raise ValueError("human_line requires nine dated periods")
    if any(item.get("causal_claim") is not False for item in human_line):
        raise ValueError("human_line may not convert sequence into causation")

    policy = data.get("adobe_binding", {})
    expected_policy = {
        "aspect_ratio": "9:16",
        "one_canvas_per_output": True,
        "collage_allowed": False,
        "duplicate_output_allowed": False,
        "reference_pack_confers_identity_authorization": False,
        "attached_image_required_for_identity_lock": True,
        "render_statistical_text_by_default": False,
        "money_aggregation_allowed": False,
        "external_adobe_runtime_claimed": False,
        "humanlock": True,
    }
    for key, expected in expected_policy.items():
        if policy.get(key) != expected:
            raise ValueError(f"adobe_binding.{key} must be {expected!r}")

    return {
        "module_id": MODULE_ID,
        "version": VERSION,
        "statistical_bit_count": len(statistical),
        "money_bit_count": len(money),
        "total_bit_count": len(bits),
        "hold_count": len(holds),
        "human_line_period_count": len(human_line),
        "evidence_states": {key: value for key, value in states.items() if value},
        "local_schema_valid": True,
        "external_adobe_runtime_claimed": False,
    }


def compile_adobe_reference_context(
    data: dict[str, Any], requested_count: int, input_count: int
) -> dict[str, Any]:
    receipt = validate_register(data)
    if isinstance(requested_count, bool) or not isinstance(requested_count, int):
        raise TypeError("requested_count must be an integer")
    if isinstance(input_count, bool) or not isinstance(input_count, int):
        raise TypeError("input_count must be an integer")
    if not 1 <= requested_count <= 10:
        raise ValueError("requested_count must be from 1 through 10")
    if requested_count != input_count:
        raise ValueError("TEN_IN_TEN_OUT and N_IN_N_OUT require matching input and output counts")

    bits = data["statistical_bits"] + data["money_bits"]
    source_routes = data["source_routes"]
    safe_facts = []
    excluded_holds = []
    for bit in bits:
        record = {"id": bit, "source_refs": _route_source(bit, source_routes)}
        if _state(bit) == "HOLD":
            excluded_holds.append(record)
        else:
            safe_facts.append(record)

    return {
        "module_id": MODULE_ID,
        "parent_id": PARENT_ID,
        "usage_scope": "REFERENCE_CONTEXT_ONLY",
        "queue": [
            {
                "slot": f"Q{slot:02d}",
                "canvas": "9:16",
                "output_count": 1,
                "collage": False,
            }
            for slot in range(1, requested_count + 1)
        ],
        "safe_facts": safe_facts,
        "excluded_holds": excluded_holds,
        "visual_prompt_rules": {
            "attached_image_controls_identity": True,
            "preserve_source_wardrobe_and_pose_unless_user_requests_change": True,
            "ordinary_clothed_stage_performance_fashion_context": "ALLOWED_STANDARD_CONTEXT",
            "render_statistical_text": False,
            "reference_pack_is_not_identity_authorization": True,
        },
        "evidence_gate": "OBSERVED != CORRELATED != CAUSAL",
        "runtime_gate": "LOCAL_SCHEMA_VALIDATED != ADOBE_EXECUTED",
        "validation_receipt": receipt,
    }


def validate_file(path: str | Path) -> dict[str, Any]:
    return validate_register(load_register(path))
