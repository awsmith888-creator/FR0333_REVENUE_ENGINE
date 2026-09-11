from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Iterable


MODULE_ID = "FR0333.AI.IMAGE.TOOL.METRICS.0001"
GOLDEN_CHAIN_ID = "GC.SB.0027"
VERSION = "1.0.0"


class EvidenceState(StrEnum):
    VERIFIED_RELEASE = "VERIFIED_RELEASE"
    PREVIEW = "PREVIEW"
    VENDOR_CLAIM = "VENDOR_CLAIM"
    UNVERIFIED = "UNVERIFIED"


class Capability(StrEnum):
    IDENTITY_PRESERVATION = "IDENTITY_PRESERVATION"
    REMASTERING = "REMASTERING"
    OUTPUT_9_16 = "OUTPUT_9_16"
    BATCH_SPLIT = "BATCH_SPLIT"
    RUNTIME_RELIABILITY = "RUNTIME_RELIABILITY"


EVIDENCE_WEIGHT = {
    EvidenceState.VERIFIED_RELEASE: 3,
    EvidenceState.PREVIEW: 2,
    EvidenceState.VENDOR_CLAIM: 1,
    EvidenceState.UNVERIFIED: 0,
}


@dataclass(frozen=True, slots=True)
class ToolChange:
    record_id: str
    tool: str
    capability: Capability
    observed_at: datetime
    evidence_state: EvidenceState
    consequence: int
    source_url: str
    change: str
    workflow_effect: str
    runtime_receipt: str | None = None

    def __post_init__(self) -> None:
        if not self.record_id or not self.tool or not self.change or not self.workflow_effect:
            raise ValueError("record_id, tool, change, and workflow_effect are required")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        object.__setattr__(self, "observed_at", self.observed_at.astimezone(timezone.utc))
        if not 0 <= self.consequence <= 3:
            raise ValueError("consequence must be an integer from 0 through 3")
        if not self.source_url.startswith(("https://", "http://")):
            raise ValueError("source_url must be an HTTP(S) URL")
        if self.evidence_state is EvidenceState.VERIFIED_RELEASE and not self.runtime_receipt:
            raise ValueError("VERIFIED_RELEASE requires a runtime_receipt")

    @property
    def metric(self) -> int:
        return EVIDENCE_WEIGHT[self.evidence_state] * self.consequence


def compile_report(changes: Iterable[ToolChange]) -> dict[str, object]:
    records = sorted(changes, key=lambda item: (item.observed_at, item.record_id))
    if len({item.record_id for item in records}) != len(records):
        raise ValueError("record_id values must be unique")

    lanes = {state.value: [] for state in EvidenceState}
    capability_totals = {capability.value: 0 for capability in Capability}
    for item in records:
        serialized = asdict(item)
        serialized["capability"] = item.capability.value
        serialized["evidence_state"] = item.evidence_state.value
        serialized["observed_at"] = item.observed_at.isoformat()
        serialized["metric"] = item.metric
        lanes[item.evidence_state.value].append(serialized)
        capability_totals[item.capability.value] += item.metric

    return {
        "module": MODULE_ID,
        "golden_chain": GOLDEN_CHAIN_ID,
        "version": VERSION,
        "record_count": len(records),
        "capability_metric_totals": capability_totals,
        "evidence_lanes": lanes,
        "gate": {
            "verified_release_ne_preview": True,
            "preview_ne_vendor_claim": True,
            "vendor_claim_ne_runtime_receipt": True,
            "observed_ne_correlated_ne_causal": True,
        },
    }


def write_report(changes: Iterable[ToolChange], destination: str) -> None:
    with open(destination, "w", encoding="utf-8") as handle:
        json.dump(compile_report(changes), handle, indent=2, sort_keys=True)
        handle.write("\n")
