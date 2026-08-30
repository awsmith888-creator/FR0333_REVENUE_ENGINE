from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Tuple


FLOW = "1.7.369.7.1"


class KernelRoute(str, Enum):
    PASS_STREAM = "PASS_STREAM"
    ROUTE_UNVERIFIED = "ROUTE_UNVERIFIED"
    HALT_STREAM = "HALT_STREAM"
    HARD_PURGE = "HARD_PURGE"
    STAY_HOLD = "STAY_HOLD"


@dataclass(frozen=True)
class KernelPacket:
    packet_id: str
    source_ref: str
    flow: str = FLOW
    provenance_verified: bool = False
    logical_slots: int = 64
    physical_bits_derived: bool = False
    probability_variance: float = 0.0
    signature_match: float = 1.0
    bit_62_valid: bool = True
    bit_63_valid: bool = True
    termination_trigger: bool = False
    image_execution_enabled: bool = False
    route: KernelRoute = KernelRoute.STAY_HOLD
    trace: Tuple[str, ...] = field(default_factory=tuple)

    def mark(self, event: str, **changes: object) -> "KernelPacket":
        return replace(self, trace=self.trace + (event,), **changes)


class SourceKernelK01:
    address = f"K01.{FLOW}"

    def process(self, packet: KernelPacket) -> KernelPacket:
        if packet.flow != FLOW:
            return packet.mark("K01.FLOW_MISMATCH", route=KernelRoute.HALT_STREAM)
        if not packet.source_ref:
            return packet.mark("K01.SOURCE_MISSING", route=KernelRoute.ROUTE_UNVERIFIED)
        if not packet.provenance_verified:
            return packet.mark("K01.PROVENANCE_UNVERIFIED", route=KernelRoute.ROUTE_UNVERIFIED)
        return packet.mark("K01.PROVENANCE_MATCH")


class MetricKernelK02:
    address = f"K02.{FLOW}"
    logical_slot_limit = 64

    def process(self, packet: KernelPacket) -> KernelPacket:
        if packet.route in {KernelRoute.HARD_PURGE, KernelRoute.HALT_STREAM}:
            return packet.mark("K02.BYPASS_TERMINAL")
        if packet.logical_slots != self.logical_slot_limit:
            return packet.mark("K02.LOGICAL_SLOT_MISMATCH", route=KernelRoute.HALT_STREAM)
        if packet.physical_bits_derived:
            return packet.mark("K02.PHYSICAL_BIT_COERCION", route=KernelRoute.HALT_STREAM)
        return packet.mark("K02.DIMENSIONAL_GUARD_PASS")


class ProbabilityKernelK03:
    address = f"K03.{FLOW}"
    variance_limit = 0.01

    def process(self, packet: KernelPacket) -> KernelPacket:
        if packet.route in {KernelRoute.HARD_PURGE, KernelRoute.HALT_STREAM}:
            return packet.mark("K03.BYPASS_TERMINAL")
        if packet.probability_variance < 0.0 or packet.probability_variance > self.variance_limit:
            return packet.mark("K03.VARIANCE_LIMIT_FAIL", route=KernelRoute.HALT_STREAM)
        return packet.mark("K03.STATE_EVALUATION_PASS")


class LogicKernelK04:
    address = f"K04.{FLOW}"

    def process(self, packet: KernelPacket) -> KernelPacket:
        # HARD_PURGE has absolute dominance.
        if not packet.bit_62_valid or not packet.bit_63_valid:
            return packet.mark("K04.HARD_PURGE", route=KernelRoute.HARD_PURGE)
        if packet.termination_trigger:
            return packet.mark("K04.TERMINATION_TRIGGER", route=KernelRoute.HALT_STREAM)
        if packet.route is KernelRoute.HALT_STREAM:
            return packet.mark("K04.FAIL_CLOSED")
        if packet.route is KernelRoute.ROUTE_UNVERIFIED:
            return packet.mark("K04.ROUTE_UNVERIFIED")
        if packet.signature_match != 1.0:
            return packet.mark("K04.SIGNATURE_FAIL_CLOSED", route=KernelRoute.ROUTE_UNVERIFIED)
        if not packet.provenance_verified:
            return packet.mark("K04.PROVENANCE_FAIL_CLOSED", route=KernelRoute.ROUTE_UNVERIFIED)
        if not packet.image_execution_enabled:
            return packet.mark("K04.K05_STATIC_STAY_HOLD", route=KernelRoute.STAY_HOLD)
        return packet.mark("K04.PASS_STREAM", route=KernelRoute.PASS_STREAM)


class AdobeStudioKernelBus:
    """Deterministic K01 -> K02 -> K03 -> K04 coordination bus.

    This is an executable coordination layer, not evidence of a live Adobe
    credential-backed runtime. Each kernel receives the exact packet emitted by
    the previous kernel and appends an immutable trace event.
    """

    def __init__(self) -> None:
        self.kernels = (
            SourceKernelK01(),
            MetricKernelK02(),
            ProbabilityKernelK03(),
            LogicKernelK04(),
        )

    def process(self, packet: KernelPacket) -> KernelPacket:
        current = packet
        for kernel in self.kernels:
            current = kernel.process(current)
        return current


__all__ = [
    "AdobeStudioKernelBus",
    "FLOW",
    "KernelPacket",
    "KernelRoute",
    "LogicKernelK04",
    "MetricKernelK02",
    "ProbabilityKernelK03",
    "SourceKernelK01",
]
