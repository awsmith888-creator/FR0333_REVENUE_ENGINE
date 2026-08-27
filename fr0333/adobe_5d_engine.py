from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any, Iterable, Mapping, Optional


class EvidenceClass(str, Enum):
    OBSERVED = "E_OBS"
    MEASURED = "E_MES"
    DERIVED = "E_DER"
    INFERRED = "E_INF"
    CLAIMED = "E_CLM"


class ValueState(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INVALID = "INVALID"
    CONFLICTING = "CONFLICTING"
    SUSPICIOUS = "SUSPICIOUS"
    PROVEN_FALSE = "PROVEN_FALSE"


class GateAction(str, Enum):
    PASS = "PASS"
    ROUTE_UNVERIFIED = "ROUTE_UNVERIFIED"
    HALT_STREAM = "HALT_STREAM"
    HARD_PURGE = "HARD_PURGE"


@dataclass(frozen=True)
class Coordinate5D:
    """FR-0333 X.Y.Z.P.T address.

    X: spatial / population scope
    Y: measured variable
    Z: source / product / evidence layer
    P: probability / proportion / population statistic
    T: time / horizon / revision coordinate
    """

    x: str
    y: str
    z: str
    p: str
    t: str

    def canonical(self) -> str:
        return ".".join((self.x, self.y, self.z, self.p, self.t))


@dataclass(frozen=True)
class MetricIdentity:
    name: str
    numerator: Optional[str] = None
    denominator: Optional[str] = None

    def validate(self) -> None:
        if (self.numerator is None) ^ (self.denominator is None):
            raise ValueError("ratio metrics require both numerator and denominator")


@dataclass(frozen=True)
class EvidenceBit:
    bit_id: str
    coordinate: Coordinate5D
    evidence_class: EvidenceClass
    value: Any
    state: ValueState = ValueState.PRESENT
    metric: Optional[MetricIdentity] = None
    source_ref: Optional[str] = None

    def validate(self) -> None:
        if self.metric:
            self.metric.validate()
        if self.state is ValueState.PRESENT and self.value is None:
            raise ValueError(f"{self.bit_id}: PRESENT value cannot be None")
        if self.state is not ValueState.PRESENT and self.value is not None:
            raise ValueError(
                f"{self.bit_id}: non-present state must not carry a value; "
                "absence/unknown/N-A are not numeric zero"
            )


@dataclass(frozen=True)
class ImmutableReceipt:
    observation_id: str
    capture_timestamp: str
    target_timestamp: Optional[str]
    source: str
    payload_hash: str
    revision_of: Optional[str] = None

    @staticmethod
    def from_payload(
        observation_id: str,
        capture_timestamp: str,
        source: str,
        payload: bytes,
        *,
        target_timestamp: Optional[str] = None,
        revision_of: Optional[str] = None,
    ) -> "ImmutableReceipt":
        return ImmutableReceipt(
            observation_id=observation_id,
            capture_timestamp=capture_timestamp,
            target_timestamp=target_timestamp,
            source=source,
            payload_hash=sha256(payload).hexdigest(),
            revision_of=revision_of,
        )


@dataclass
class CalibrationResult:
    accepted: list[EvidenceBit] = field(default_factory=list)
    routed_unverified: list[EvidenceBit] = field(default_factory=list)
    halted: list[EvidenceBit] = field(default_factory=list)
    purged: list[EvidenceBit] = field(default_factory=list)

    @property
    def stream_halted(self) -> bool:
        return bool(self.halted or self.purged)


class Adobe5DCalibrationEngine:
    """Fail-closed calibration layer for image/provenance measurements.

    Governing boundaries:
      metadata != provenance != authenticity != identity != truth
      cryptographic validity != human identity != authorization
      absent != invalid != conflicting != suspicious != proven false
      detector failure != synthetic evidence
      ratings != average audience != reach
      app users != website users != TV audience
    """

    HARD_PURGE_BITS = {"BIT_62", "BIT_63"}
    UNVERIFIED_ROUTE_BITS = {"BIT_11", "BIT_13", "BIT_25"}

    def gate(self, bit: EvidenceBit) -> GateAction:
        bit.validate()

        if bit.bit_id in self.HARD_PURGE_BITS and bit.state is not ValueState.PRESENT:
            return GateAction.HARD_PURGE
        if bit.bit_id in self.HARD_PURGE_BITS and bit.value is False:
            return GateAction.HARD_PURGE

        if bit.bit_id in self.UNVERIFIED_ROUTE_BITS and (
            bit.state in {ValueState.ABSENT, ValueState.UNKNOWN, ValueState.NOT_APPLICABLE}
            or bit.value is False
        ):
            return GateAction.ROUTE_UNVERIFIED

        if bit.state in {
            ValueState.INVALID,
            ValueState.CONFLICTING,
            ValueState.PROVEN_FALSE,
        }:
            return GateAction.HALT_STREAM

        return GateAction.PASS

    def calibrate(self, bits: Iterable[EvidenceBit]) -> CalibrationResult:
        result = CalibrationResult()
        for bit in bits:
            action = self.gate(bit)
            if action is GateAction.PASS:
                result.accepted.append(bit)
            elif action is GateAction.ROUTE_UNVERIFIED:
                result.routed_unverified.append(bit)
            elif action is GateAction.HALT_STREAM:
                result.halted.append(bit)
            elif action is GateAction.HARD_PURGE:
                result.purged.append(bit)
        return result

    @staticmethod
    def applicable_ratio(valid: int, applicable: int) -> Optional[float]:
        """Coverage/continuity denominator excludes non-applicable fields."""
        if applicable < 0 or valid < 0 or valid > applicable:
            raise ValueError("invalid applicable ratio bounds")
        if applicable == 0:
            return None
        return valid / applicable

    @staticmethod
    def detector_result(score: Optional[float], *, status: str) -> tuple[Optional[float], ValueState]:
        """A detector error is UNKNOWN, never synthetic=1.0."""
        if status != "SUCCESS":
            return None, ValueState.UNKNOWN
        if score is None or not 0.0 <= score <= 1.0:
            return None, ValueState.INVALID
        return score, ValueState.PRESENT

    @staticmethod
    def byte_identity(original_hash: str, current_hash: str) -> bool:
        """Descriptive only: mismatch does not establish tampering."""
        return original_hash == current_hash

    @staticmethod
    def tamper_suspected(
        *,
        signed_binding_expected: bool,
        signed_binding_valid: Optional[bool],
        manifest_present: bool,
        manifest_valid: Optional[bool],
    ) -> bool:
        if signed_binding_expected and signed_binding_valid is False:
            return True
        if manifest_present and manifest_valid is False:
            return True
        return False

    @staticmethod
    def no_cross_rail_promotion(source_rail: str, target_claim: str) -> bool:
        forbidden: Mapping[str, set[str]] = {
            "HUMAN_DEMAND": {"FORECAST_ACCURACY", "IMAGE_AUTHENTICITY"},
            "AUDIENCE": {"FORECAST_QUALITY", "IMAGE_AUTHENTICITY"},
            "PROVENANCE": {"HUMAN_IDENTITY", "TRUTH"},
            "DETECTOR": {"HUMAN_IDENTITY", "TRUTH"},
        }
        return target_claim not in forbidden.get(source_rail, set())


__all__ = [
    "Adobe5DCalibrationEngine",
    "CalibrationResult",
    "Coordinate5D",
    "EvidenceBit",
    "EvidenceClass",
    "GateAction",
    "ImmutableReceipt",
    "MetricIdentity",
    "ValueState",
]
