#!/usr/bin/env python3
import argparse
import json
import pathlib
import re
from dataclasses import asdict, dataclass
from typing import Optional

HERE = pathlib.Path(__file__).resolve().parent
SPEC_PATH = HERE / "fr0333_chat_to_work_bridge_0001.json"

REPOSITORY_TERMS = (
    "bridge", "repo", "repository", "github", "commit", "branch",
    "pull request", "write it in", "write the", "upload it", "into the system",
)
IMAGE_TERMS = (
    "image", "images", "picture", "pictures", "photo", "photos", "render",
)
IMAGE_EDIT_TERMS = (
    "edit", "fix", "clean up", "cleanup", "remove", "replace", "change", "remake",
)
IMAGE_GENERATION_TERMS = (
    "create", "generate", "make", "draw", "render", "visualize",
)
RESEARCH_TERMS = (
    "look up", "research", "statistics", "history", "search", "verify", "source",
)
STOP_PATTERNS = (
    r"\bstop\b", r"\bcancel\b", r"\bdon't\b", r"\bdo not\b", r"\bquit\b",
)

LANE_TOOLS = {
    "REPOSITORY_WRITE": {"GITHUB_READ", "GITHUB_WRITE", "LOCAL_VALIDATION"},
    "IMAGE_EDIT": {"IMAGE_GENERATION"},
    "IMAGE_GENERATION": {"IMAGE_GENERATION"},
    "RESEARCH": {"PUBLIC_SEARCH", "CONNECTED_SOURCE_READ"},
    "TEXT": set(),
}

IMAGE_LANES = {"IMAGE_EDIT", "IMAGE_GENERATION"}


@dataclass
class IntentReceipt:
    source_locked: bool
    latest_intent_controls: bool
    explicit_stop: bool
    prior_lane: Optional[str]
    compiled_lane: str
    cancelled_lane: Optional[str]
    image_tool_allowed: bool
    github_write_allowed: bool
    cross_lane_fallthrough_allowed: bool
    state: str
    execution_claim: str


def _has_any(text: str, terms) -> bool:
    return any(term in text for term in terms)


def _has_stop(text: str) -> bool:
    return any(re.search(pattern, text) for pattern in STOP_PATTERNS)


def detect_lane(text: str, prior_lane: Optional[str] = None) -> IntentReceipt:
    normalized = " ".join(text.lower().split())
    explicit_stop = _has_stop(normalized)
    repository_signal = _has_any(normalized, REPOSITORY_TERMS)
    image_signal = _has_any(normalized, IMAGE_TERMS)
    edit_signal = _has_any(normalized, IMAGE_EDIT_TERMS)
    generation_signal = _has_any(normalized, IMAGE_GENERATION_TERMS)
    research_signal = _has_any(normalized, RESEARCH_TERMS)

    cancelled_lane = None
    if explicit_stop and prior_lane in IMAGE_LANES:
        cancelled_lane = prior_lane

    # Explicit repository/bridge work outranks stale or cancelled image intent.
    if repository_signal and (explicit_stop or "bridge" in normalized or "repository" in normalized or "github" in normalized or "into the system" in normalized):
        lane = "REPOSITORY_WRITE"
    elif image_signal and edit_signal:
        lane = "IMAGE_EDIT"
    elif image_signal and generation_signal:
        lane = "IMAGE_GENERATION"
    elif research_signal:
        lane = "RESEARCH"
    else:
        lane = "TEXT"

    allowed = LANE_TOOLS[lane]
    return IntentReceipt(
        source_locked=True,
        latest_intent_controls=True,
        explicit_stop=explicit_stop,
        prior_lane=prior_lane,
        compiled_lane=lane,
        cancelled_lane=cancelled_lane,
        image_tool_allowed="IMAGE_GENERATION" in allowed,
        github_write_allowed="GITHUB_WRITE" in allowed,
        cross_lane_fallthrough_allowed=False,
        state="T.20",
        execution_claim="LOCAL_ROUTE_CLASSIFICATION_ONLY",
    )


def tool_gate(receipt: IntentReceipt, requested_tool_class: str) -> str:
    allowed = LANE_TOOLS[receipt.compiled_lane]
    return "T.20" if requested_tool_class in allowed else "F.6"


def validate_source_bound_image_batch(readable_source_count: int, requested_output_count: int) -> dict:
    if readable_source_count < 0 or requested_output_count < 0:
        raise ValueError("counts must be non-negative")
    valid = readable_source_count == requested_output_count and requested_output_count > 0
    return {
        "readable_source_count": readable_source_count,
        "requested_output_count": requested_output_count,
        "n_in_equals_n_out": valid,
        "collage": "REJECT",
        "contact_sheet": "REJECT",
        "duplicate_output": "REJECT",
        "state": "T.20" if valid else "F.6",
    }


def load_spec() -> dict:
    doc = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    assert doc["identifier"] == "FR0333.CHAT.TO.WORK.BRIDGE.0001"
    assert doc["humanlock"] is True
    assert doc["pipeline"] == [
        "SOURCE_LOCK", "INTENT_COMPILE", "LANE_DETECT", "TOOL_GATE", "DECOMPOSE",
        "EXECUTE", "FAILURE_LOOP", "LOGIC_GATE", "OUTPUT_GATE", "CHOMP", "STAY",
    ]
    assert "LATEST_USER_INTENT_OVERRIDES_PRIOR_ACTIVE_INTENT" in doc["override_rules"]
    assert "EXPLICIT_STOP_CANCELS_PENDING_EXECUTION" in doc["override_rules"]
    assert "NO_CROSS_LANE_FALLTHROUGH" in doc["override_rules"]
    return doc


def main() -> int:
    parser = argparse.ArgumentParser(description="FR0333 Chat-to-Work lane bridge")
    parser.add_argument("--text", required=True)
    parser.add_argument("--prior-lane", default=None)
    parser.add_argument("--tool-class", default=None)
    args = parser.parse_args()

    load_spec()
    receipt = detect_lane(args.text, args.prior_lane)
    payload = {"receipt": asdict(receipt)}
    if args.tool_class:
        payload["tool_gate"] = {
            "requested_tool_class": args.tool_class,
            "state": tool_gate(receipt, args.tool_class),
        }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
