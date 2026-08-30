from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Tuple


FLOW = "1.7.369.7.1"
K_ALPHA = "K.11"


@dataclass(frozen=True)
class KernelIndex:
    slot: int
    label: str

    @property
    def system_id(self) -> str:
        return f"{K_ALPHA}.{self.slot:02d}"

    @property
    def reference_point(self) -> str:
        return f"{self.system_id}.000.1"

    @property
    def flow_address(self) -> str:
        return f"{self.system_id}.{FLOW}"


K01_INDEX = KernelIndex(1, "SOURCE.KERNEL")
K02_INDEX = KernelIndex(2, "METRIC.KERNEL")
K03_INDEX = KernelIndex(3, "PROBABILITY.KERNEL")
K04_INDEX = KernelIndex(4, "LOGIC.KERNEL")
KERNEL_INDEX = (K01_INDEX, K02_INDEX, K03_INDEX, K04_INDEX)


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
    index = K01_INDEX
    address = index.flow_address
    reference_point = index.reference_point

    def process(self, packet: KernelPacket) -> KernelPacket:
        prefix = self.index.system_id
        if packet.flow != FLOW:
            return packet.mark(f"{prefix}.FLOW_MISMATCH", route=KernelRoute.HALT_STREAM)
        if not packet.source_ref:
            return packet.mark(f"{prefix}.SOURCE_MISSING", route=KernelRoute.ROUTE_UNVERIFIED)
        if not packet.provenance_verified:
            return packet.mark(f"{prefix}.PROVENANCE_UNVERIFIED", route=KernelRoute.ROUTE_UNVERIFIED)
        return packet.mark(f"{prefix}.PROVENANCE_MATCH")


class MetricKernelK02:
    index = K02_INDEX
    address = index.flow_address
    reference_point = index.reference_point
    logical_slot_limit = 64

    def process(self, packet: KernelPacket) -> KernelPacket:
        prefix = self.index.system_id
        if packet.route in {KernelRoute.HARD_PURGE, KernelRoute.HALT_STREAM}:
            return packet.mark(f"{prefix}.BYPASS_TERMINAL")
        if packet.logical_slots != self.logical_slot_limit:
            return packet.mark(f"{prefix}.LOGICAL_SLOT_MISMATCH", route=KernelRoute.HALT_STREAM)
        if packet.physical_bits_derived:
            return packet.mark(f"{prefix}.PHYSICAL_BIT_COERCION", route=KernelRoute.HALT_STREAM)
        return packet.mark(f"{prefix}.DIMENSIONAL_GUARD_PASS")


class ProbabilityKernelK03:
    index = K03_INDEX
    address = index.flow_address
    reference_point = index.reference_point
    variance_limit = 0.01

    def process(self, packet: KernelPacket) -> KernelPacket:
        prefix = self.index.system_id
        if packet.route in {KernelRoute.HARD_PURGE, KernelRoute.HALT_STREAM}:
            return packet.mark(f"{prefix}.BYPASS_TERMINAL")
        if packet.probability_variance < 0.0 or packet.probability_variance > self.variance_limit:
            return packet.mark(f"{prefix}.VARIANCE_LIMIT_FAIL", route=KernelRoute.HALT_STREAM)
        return packet.mark(f"{prefix}.STATE_EVALUATION_PASS")


class LogicKernelK04:
    index = K04_INDEX
    address = index.flow_address
    reference_point = index.reference_point

    def process(self, packet: KernelPacket) -> KernelPacket:
        prefix = self.index.system_id
        if not packet.bit_62_valid or not packet.bit_63_valid:
            return packet.mark(f"{prefix}.HARD_PURGE", route=KernelRoute.HARD_PURGE)
        if packet.termination_trigger:
            return packet.mark(f"{prefix}.TERMINATION_TRIGGER", route=KernelRoute.HALT_STREAM)
        if packet.route is KernelRoute.HALT_STREAM:
            return packet.mark(f"{prefix}.FAIL_CLOSED")
        if packet.route is KernelRoute.ROUTE_UNVERIFIED:
            return packet.mark(f"{prefix}.ROUTE_UNVERIFIED")
        if packet.signature_match != 1.0:
            return packet.mark(f"{prefix}.SIGNATURE_FAIL_CLOSED", route=KernelRoute.ROUTE_UNVERIFIED)
        if not packet.provenance_verified:
            return packet.mark(f"{prefix}.PROVENANCE_FAIL_CLOSED", route=KernelRoute.ROUTE_UNVERIFIED)
        if not packet.image_execution_enabled:
            return packet.mark(f"{prefix}.K05_STATIC_STAY_HOLD", route=KernelRoute.STAY_HOLD)
        return packet.mark(f"{prefix}.PASS_STREAM", route=KernelRoute.PASS_STREAM)


class AdobeStudioKernelBus:
    """Deterministic K01 -> K02 -> K03 -> K04 coordination bus.

    Canonical kernel index:
      K01 = K.11.01 / K.11.01.000.1 / K.11.01.1.7.369.7.1
      K02 = K.11.02 / K.11.02.000.1 / K.11.02.1.7.369.7.1
      K03 = K.11.03 / K.11.03.000.1 / K.11.03.1.7.369.7.1
      K04 = K.11.04 / K.11.04.000.1 / K.11.04.1.7.369.7.1
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
    "K01_INDEX",
    "K02_INDEX",
    "K03_INDEX",
    "K04_INDEX",
    "KERNEL_INDEX",
    "KernelIndex",
    "KernelPacket",
    "KernelRoute",
    "LogicKernelK04",
    "MetricKernelK02",
    "ProbabilityKernelK03",
    "SourceKernelK01",
]
