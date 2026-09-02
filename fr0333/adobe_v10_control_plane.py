from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Dict, Iterable, List


class ArchitectureViolation(ValueError):
    pass


@dataclass(frozen=True)
class SlotIntent:
    slot_id: str
    descriptor: str
    camera: str
    blocking: str
    aspect_ratio: str = "9:16"
    resolution: str = "1080x1920"

    def canonical(self) -> bytes:
        return json.dumps(
            {
                "slot_id": self.slot_id,
                "descriptor": self.descriptor,
                "camera": self.camera,
                "blocking": self.blocking,
                "aspect_ratio": self.aspect_ratio,
                "resolution": self.resolution,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    def digest(self) -> str:
        return hashlib.sha256(self.canonical()).hexdigest()


@dataclass
class BatchManifest:
    batch_id: str
    workflow_id: str
    slots: List[SlotIntent] = field(default_factory=list)
    humanlock: bool = True
    legacy_v1: bool = False
    collage: bool = False

    def validate(self, expected_count: int = 10) -> None:
        if self.legacy_v1:
            raise ArchitectureViolation("LEGACY_V1_DENY")
        if self.collage:
            raise ArchitectureViolation("COLLAGE_DENY")
        if not self.humanlock:
            raise ArchitectureViolation("HUMANLOCK_REQUIRED")
        if len(self.slots) != expected_count:
            raise ArchitectureViolation("BATCH_COUNT_MISMATCH")

        ids = [slot.slot_id for slot in self.slots]
        if len(ids) != len(set(ids)):
            raise ArchitectureViolation("DUPLICATE_SLOT_ID")

        expected_ids = [f"{i:02d}" for i in range(1, expected_count + 1)]
        if ids != expected_ids:
            raise ArchitectureViolation("NONDETERMINISTIC_SLOT_ORDER")

        for slot in self.slots:
            if slot.aspect_ratio != "9:16":
                raise ArchitectureViolation("ASPECT_RATIO_VIOLATION")
            if slot.resolution not in {"1080x1920", "2160x3840"}:
                raise ArchitectureViolation("RESOLUTION_VIOLATION")
            if not slot.descriptor or not slot.camera or not slot.blocking:
                raise ArchitectureViolation("INTENT_ATOM_MISSING")

    def compile_action_graph(self) -> Dict[str, Any]:
        self.validate()
        actions = []
        for slot in self.slots:
            actions.append(
                {
                    "slot_id": slot.slot_id,
                    "operation": "GENERATIVE_OPERATION",
                    "intent_digest": slot.digest(),
                    "independent_asset_required": True,
                    "collage_allowed": False,
                    "duplicate_asset_id_allowed": False,
                    "parameters": {
                        "descriptor": slot.descriptor,
                        "camera": slot.camera,
                        "blocking": slot.blocking,
                        "aspect_ratio": slot.aspect_ratio,
                        "resolution": slot.resolution,
                    },
                }
            )
        graph = {
            "architecture_version": "10.0",
            "batch_id": self.batch_id,
            "workflow_id": self.workflow_id,
            "execution_adapter": "ADOBE_EXECUTION_ADAPTER",
            "humanlock": self.humanlock,
            "actions": actions,
            "promotion_state": "HOLD_EXTERNAL_RUNTIME",
        }
        graph["action_graph_digest"] = hashlib.sha256(
            json.dumps(graph, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return graph


def verify_output_manifest(action_graph: Dict[str, Any], outputs: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    actions = action_graph.get("actions", [])
    outputs = list(outputs)
    if len(outputs) != len(actions):
        raise ArchitectureViolation("OUTPUT_COUNT_MISMATCH")

    expected_slots = [a["slot_id"] for a in actions]
    output_slots = [o.get("slot_id") for o in outputs]
    if output_slots != expected_slots:
        raise ArchitectureViolation("OUTPUT_SLOT_ORDER_MISMATCH")

    asset_ids = [o.get("asset_id") for o in outputs]
    if None in asset_ids or "" in asset_ids:
        raise ArchitectureViolation("ASSET_ID_MISSING")
    if len(asset_ids) != len(set(asset_ids)):
        raise ArchitectureViolation("DUPLICATE_ASSET_ID")

    for output in outputs:
        if output.get("collage") is True:
            raise ArchitectureViolation("COLLAGE_OUTPUT_DENY")
        if output.get("aspect_ratio") != "9:16":
            raise ArchitectureViolation("OUTPUT_ASPECT_RATIO_VIOLATION")
        if output.get("runtime_verified") is not True:
            # Runtime absence does not invalidate the structural compilation;
            # it blocks promotion instead.
            output["promotion_state"] = "HOLD_EXTERNAL_RUNTIME"

    canonical = json.dumps(outputs, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "validation_state": "PASS_STRUCTURE",
        "output_count": len(outputs),
        "output_manifest_digest": hashlib.sha256(canonical).hexdigest(),
        "promotion_state": "HOLD_EXTERNAL_RUNTIME",
        "evidence_boundary": "CI_STRUCTURE_PASS != EXTERNAL_ADOBE_RUNTIME_PROVEN",
    }
