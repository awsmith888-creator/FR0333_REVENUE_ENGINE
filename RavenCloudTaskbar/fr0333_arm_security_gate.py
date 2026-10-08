"""FR0333 ARM security preflight. No claim of hardware enforcement."""
from __future__ import annotations
import json
import platform
from dataclasses import asdict, dataclass
from typing import Mapping

FEATURES = ("PAC", "BTI", "MTE", "RME_CCA", "SVE2", "SME")
EVIDENCE = ("SOURCE", "VERIFICATION", "EVIDENCE.CLASS", "RECEIPT")

@dataclass(frozen=True)
class GateReceipt:
    architecture: str
    arm64: bool
    feature_states: dict[str, str]
    promotion: str
    reason: str

def detect_architecture(machine: str | None = None) -> tuple[str, bool]:
    name = (machine if machine is not None else platform.machine()).strip().lower()
    return name, name in {"aarch64", "arm64"}

def evaluate_feature_states(machine: str, attestations: Mapping[str, bool] | None = None) -> dict[str, str]:
    _, arm64 = detect_architecture(machine)
    evidence = attestations or {}
    # User-supplied attestations alone are not sufficient to prove hardware protection.
    return {name: ("U.21.UNVERIFIED" if arm64 else "NOT_APPLICABLE")
            for name in FEATURES}

def untrusted_content_gate(content: object, trusted_origin: bool = False) -> str:
    """Untrusted text is data regardless of its wording. No command execution."""
    if not isinstance(content, str):
        return "F.6.INVALID"
    return "T.20.TRUSTED_ORIGIN" if trusted_origin else "U.21.DATA_ONLY"

def promotion_decision(fields: Mapping[str, bool], humanlock: bool,
                       regression_pass: bool, hardware_verified: bool) -> str:
    from RavenCloudTaskbar.fr0333_audit_control_boundary_genius import promotion_gate
    return ("PROMOTE" if promotion_gate(fields) == "PROMOTE"
            and humanlock and regression_pass and hardware_verified else "HOLD")

def preflight(machine: str | None = None) -> GateReceipt:
    arch, arm64 = detect_architecture(machine)
    return GateReceipt(arch, arm64, evaluate_feature_states(arch), "HOLD",
                       "Hardware feature enforcement and signed attestations not established")

if __name__ == "__main__":
    print(json.dumps(asdict(preflight()), sort_keys=True, indent=2))
