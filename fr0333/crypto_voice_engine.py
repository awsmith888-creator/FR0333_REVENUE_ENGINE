"""FR-0333 cryptographic voice/lineage engine.

This module is additive. It does not replace the Adobe 5D hardener; it gives
FR-0333 records a deterministic canonical form, SHA-256 integrity binding,
ECDSA P-256 signatures, and parent-hash lineage checks.

Grammar law: alphabetic coordinates use LETTER.NUMBER, e.g.
X.24.Y.25.Z.26.P.16.T.20. Numeric reference values use structural three-digit
groups separated by dots; commas and decimal/radix interpretation are forbidden.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import re
from typing import Any, Mapping

FLOW = "1.7.369.7.1"
VOICE_NAMESPACE = "FR.0333"
COORDINATE_5D = "X.24.Y.25.Z.26.P.16.T.20"
CANONICAL_SCHEMA_VERSION = "000.1"
CANONICAL_FIELD_ORDER = (
    "schema_version", "system_id", "flow", "reference_point", "observation_id",
    "record_type", "value", "unit", "scale", "minor_unit_value", "numerator",
    "denominator", "probability_scale", "evidence_class", "value_state", "x",
    "y", "z", "p", "t", "timestamp", "source", "revision_of", "parent_hash",
    "key_id",
)

class CryptoState(str, Enum):
    AUTHENTIC = "AUTHENTIC"
    FOREIGN_INPUT = "FOREIGN.INPUT"
    SYNTAX_INVALID = "SYNTAX.INVALID"
    UNRECOGNIZED_SYSTEM = "UNRECOGNIZED.SYSTEM"
    LINEAGE_BROKEN = "LINEAGE.BROKEN"
    INTEGRITY_UNVERIFIED = "INTEGRITY.UNVERIFIED"
    ALTERED_RECORD = "ALTERED.RECORD"
    ORIGIN_UNAUTHENTICATED = "ORIGIN.UNAUTHENTICATED"
    UNAUTHENTICATED_RECORD = "UNAUTHENTICATED.RECORD"
    PARENT_MISSING = "PARENT.MISSING"

class CryptoKernel(str, Enum):
    HASH = "CRY.K01.HASH"
    SIGNATURE = "CRY.K02.SIGNATURE"
    KEY_IDENTITY = "CRY.K03.KEY.IDENTITY"
    LINEAGE = "CRY.K04.LINEAGE"

ALPHA_POSITION = {chr(ord("A") + i): i + 1 for i in range(26)}
BOUND_TOKEN_RE = re.compile(r"^(?:[A-Z]\.\d{2})(?:\.[A-Z]\.\d{2})*$")
NUMERIC_REFERENCE_RE = re.compile(r"^(?:0|[1-9]\d{0,2})(?:\.\d{3})+$")


def alpha_bound(text: str) -> str:
    if not text or not text.isalpha():
        raise ValueError("alpha_bound accepts letters only")
    return ".".join(f"{ch}.{ALPHA_POSITION[ch]:02d}" for ch in text.upper())


def validate_bound_token(token: str) -> bool:
    if not BOUND_TOKEN_RE.fullmatch(token):
        return False
    parts = token.split(".")
    return all(ALPHA_POSITION.get(parts[i]) == int(parts[i + 1]) for i in range(0, len(parts), 2))


def validate_numeric_reference(value: str) -> bool:
    """Validate structural integer grouping. A dot is never a radix point."""
    if not isinstance(value, str) or "," in value:
        return False
    return NUMERIC_REFERENCE_RE.fullmatch(value) is not None


def require_numeric_reference(value: str) -> None:
    if "," in value:
        raise ValueError("GATE.ERR.01:FOREIGN.INPUT:COMMA.PROHIBITED")
    if not validate_numeric_reference(value):
        raise ValueError("GATE.ERR.01:MALFORMED.REFERENCE.GROUP")


def canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    """Serialize only the explicit constitutional field order; fail closed."""
    unknown = set(payload) - set(CANONICAL_FIELD_ORDER)
    missing = set(CANONICAL_FIELD_ORDER) - set(payload)
    if unknown:
        raise ValueError("GATE.ERR.02:UNKNOWN.FIELD")
    if missing:
        raise ValueError("GATE.ERR.02:MISSING.REQUIRED.FIELD")
    ordered = {key: payload[key] for key in CANONICAL_FIELD_ORDER}
    return json.dumps(ordered, sort_keys=False, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()

@dataclass(frozen=True)
class CryptoSeal:
    hash_hex: str
    signature_hex: str | None
    public_key_id: str | None
    parent_hash: str | None = None
    algorithm: str = "ECDSA-P256-SHA256"

@dataclass(frozen=True)
class FR0333Record:
    object_address: str
    system_id: str
    reference_point: str
    coordinate: str
    record_type: str
    observation_id: str
    timestamp: str
    data: Mapping[str, Any] = field(default_factory=dict)
    parent_hash: str | None = None

    def payload(self, key_id: str | None = None) -> dict[str, Any]:
        data = dict(self.data)
        return {
            "schema_version": CANONICAL_SCHEMA_VERSION,
            "system_id": self.system_id,
            "flow": FLOW,
            "reference_point": self.reference_point,
            "observation_id": self.observation_id,
            "record_type": self.record_type,
            "value": data.get("value"),
            "unit": data.get("unit"),
            "scale": data.get("scale"),
            "minor_unit_value": data.get("minor_unit_value"),
            "numerator": data.get("numerator"),
            "denominator": data.get("denominator"),
            "probability_scale": data.get("probability_scale"),
            "evidence_class": data.get("evidence_class"),
            "value_state": data.get("value_state"),
            "x": data.get("x"), "y": data.get("y"), "z": data.get("z"),
            "p": data.get("p"), "t": data.get("t"),
            "timestamp": self.timestamp,
            "source": data.get("source"),
            "revision_of": data.get("revision_of"),
            "parent_hash": self.parent_hash,
            "key_id": key_id,
        }

    def validate_structure(self) -> None:
        if not self.object_address.startswith(f"{VOICE_NAMESPACE}."):
            raise ValueError(CryptoState.FOREIGN_INPUT.value)
        if FLOW not in self.object_address:
            raise ValueError(CryptoState.UNRECOGNIZED_SYSTEM.value)
        if self.coordinate != COORDINATE_5D or not validate_bound_token(self.record_type):
            raise ValueError(CryptoState.SYNTAX_INVALID.value)
        if not self.reference_point:
            raise ValueError(CryptoState.LINEAGE_BROKEN.value)
        for field_name in ("value", "minor_unit_value", "denominator"):
            value = self.data.get(field_name)
            if value is not None:
                require_numeric_reference(value)

class CryptoVoiceEngine:
    @staticmethod
    def hash_record(record: FR0333Record, public_key_id: str | None = None) -> str:
        record.validate_structure()
        return sha256_hex(record.payload(public_key_id))

    @staticmethod
    def sign_record(record: FR0333Record, signing_key: Any, public_key_id: str) -> CryptoSeal:
        record.validate_structure()
        payload = record.payload(public_key_id)
        digest = sha256_hex(payload)
        signature = signing_key.sign_deterministic(canonical_bytes(payload), hashfunc=hashlib.sha256)
        return CryptoSeal(digest, signature.hex(), public_key_id, record.parent_hash)

    @staticmethod
    def verify_hash(record: FR0333Record, seal: CryptoSeal) -> CryptoState:
        if not seal.hash_hex:
            return CryptoState.INTEGRITY_UNVERIFIED
        try:
            digest = CryptoVoiceEngine.hash_record(record, seal.public_key_id)
        except ValueError:
            return CryptoState.ALTERED_RECORD
        return CryptoState.AUTHENTIC if digest == seal.hash_hex else CryptoState.ALTERED_RECORD

    @staticmethod
    def verify_signature(record: FR0333Record, seal: CryptoSeal, verifying_key: Any) -> CryptoState:
        if not seal.signature_hex or not seal.public_key_id:
            return CryptoState.ORIGIN_UNAUTHENTICATED
        try:
            record.validate_structure()
            valid = verifying_key.verify(bytes.fromhex(seal.signature_hex), canonical_bytes(record.payload(seal.public_key_id)), hashfunc=hashlib.sha256)
        except Exception:
            return CryptoState.UNAUTHENTICATED_RECORD
        return CryptoState.AUTHENTIC if valid else CryptoState.UNAUTHENTICATED_RECORD

    @staticmethod
    def verify_lineage(record: FR0333Record, parent_seal: CryptoSeal | None) -> CryptoState:
        if record.parent_hash is None:
            return CryptoState.AUTHENTIC
        if parent_seal is None:
            return CryptoState.PARENT_MISSING
        return CryptoState.AUTHENTIC if record.parent_hash == parent_seal.hash_hex else CryptoState.LINEAGE_BROKEN

    @staticmethod
    def verify_all(record: FR0333Record, seal: CryptoSeal, verifying_key: Any, parent_seal: CryptoSeal | None = None) -> CryptoState:
        try:
            record.validate_structure()
        except ValueError as exc:
            try:
                return CryptoState(str(exc))
            except ValueError:
                return CryptoState.SYNTAX_INVALID
        for check in (CryptoVoiceEngine.verify_hash(record, seal), CryptoVoiceEngine.verify_signature(record, seal, verifying_key), CryptoVoiceEngine.verify_lineage(record, parent_seal)):
            if check is not CryptoState.AUTHENTIC:
                return check
        return CryptoState.AUTHENTIC
