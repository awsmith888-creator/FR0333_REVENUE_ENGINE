"""FR-0333 cryptographic voice/lineage engine.

This module is additive. It does not replace the Adobe 5D hardener; it gives
FR-0333 records a deterministic canonical form, SHA-256 integrity binding,
ECDSA P-256 signatures, and parent-hash lineage checks.

Grammar law: alphabetic coordinates use LETTER.NUMBER, e.g.
X.24.Y.25.Z.26.P.16.T.20.
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


def alpha_bound(text: str) -> str:
    """Convert letters to FR-0333 LETTER.NUMBER grammar.

    Example: RAW -> R.18.A.01.W.23.
    """
    if not text or not text.isalpha():
        raise ValueError("alpha_bound accepts letters only")
    return ".".join(f"{ch}.{ALPHA_POSITION[ch]}" if ALPHA_POSITION[ch] >= 10 else f"{ch}.0{ALPHA_POSITION[ch]}" for ch in text.upper())


def validate_bound_token(token: str) -> bool:
    """Validate both syntax and the actual A=01..Z=26 binding."""
    if not BOUND_TOKEN_RE.fullmatch(token):
        return False
    parts = token.split(".")
    for i in range(0, len(parts), 2):
        letter = parts[i]
        number = int(parts[i + 1])
        if ALPHA_POSITION.get(letter) != number:
            return False
    return True


def canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    """Deterministic UTF-8 JSON serialization used for hashing/signing.

    Keys are sorted and whitespace is removed. Crypto seal fields are not
    implicitly stripped; callers must pass the exact payload they intend to
    bind. This avoids hidden transformations.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


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

    def payload(self) -> dict[str, Any]:
        return {
            "namespace": VOICE_NAMESPACE,
            "flow": FLOW,
            "object_address": self.object_address,
            "system_id": self.system_id,
            "reference_point": self.reference_point,
            "coordinate": self.coordinate,
            "record_type": self.record_type,
            "observation_id": self.observation_id,
            "timestamp": self.timestamp,
            "data": dict(self.data),
            "parent_hash": self.parent_hash,
        }

    def validate_structure(self) -> None:
        if not self.object_address.startswith(f"{VOICE_NAMESPACE}."):
            raise ValueError(CryptoState.FOREIGN_INPUT.value)
        if FLOW not in self.object_address:
            raise ValueError(CryptoState.UNRECOGNIZED_SYSTEM.value)
        if self.coordinate != COORDINATE_5D:
            raise ValueError(CryptoState.SYNTAX_INVALID.value)
        if not validate_bound_token(self.record_type):
            raise ValueError(CryptoState.SYNTAX_INVALID.value)
        if not self.reference_point:
            raise ValueError(CryptoState.LINEAGE_BROKEN.value)


class CryptoVoiceEngine:
    """Four-kernel cryptographic lane for FR-0333 records."""

    @staticmethod
    def hash_record(record: FR0333Record) -> str:
        record.validate_structure()
        return sha256_hex(record.payload())

    @staticmethod
    def sign_record(record: FR0333Record, signing_key: Any, public_key_id: str) -> CryptoSeal:
        """Sign canonical record bytes using python-ecdsa SigningKey.

        The repository already pins ecdsa==0.19.0. The method accepts an
        ecdsa.SigningKey object without importing the dependency at module load.
        """
        record.validate_structure()
        digest = CryptoVoiceEngine.hash_record(record)
        signature = signing_key.sign_deterministic(
            canonical_bytes(record.payload()),
            hashfunc=hashlib.sha256,
        )
        return CryptoSeal(
            hash_hex=digest,
            signature_hex=signature.hex(),
            public_key_id=public_key_id,
            parent_hash=record.parent_hash,
        )

    @staticmethod
    def verify_hash(record: FR0333Record, seal: CryptoSeal) -> CryptoState:
        if not seal.hash_hex:
            return CryptoState.INTEGRITY_UNVERIFIED
        return CryptoState.AUTHENTIC if CryptoVoiceEngine.hash_record(record) == seal.hash_hex else CryptoState.ALTERED_RECORD

    @staticmethod
    def verify_signature(record: FR0333Record, seal: CryptoSeal, verifying_key: Any) -> CryptoState:
        if not seal.signature_hex or not seal.public_key_id:
            return CryptoState.ORIGIN_UNAUTHENTICATED
        try:
            valid = verifying_key.verify(
                bytes.fromhex(seal.signature_hex),
                canonical_bytes(record.payload()),
                hashfunc=hashlib.sha256,
            )
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

        for check in (
            CryptoVoiceEngine.verify_hash(record, seal),
            CryptoVoiceEngine.verify_signature(record, seal, verifying_key),
            CryptoVoiceEngine.verify_lineage(record, parent_seal),
        ):
            if check is not CryptoState.AUTHENTIC:
                return check
        return CryptoState.AUTHENTIC
