#!/usr/bin/env python3
"""Executable validation for FR-0333 cryptographic voice kernels."""

from dataclasses import replace

from ecdsa import NIST256p, SigningKey

from fr0333.crypto_voice_engine import (
    COORDINATE_5D,
    CryptoState,
    CryptoVoiceEngine,
    FR0333Record,
    alpha_bound,
    validate_bound_token,
)


def make_record(**overrides):
    values = {
        "object_address": "FR.0333.L01.1.7.369.7.1.L01.001.1",
        "system_id": "L01",
        "reference_point": "L01.000.1",
        "coordinate": COORDINATE_5D,
        "record_type": "R.18.A.01.W.23",
        "observation_id": "L01.001.1",
        "timestamp": "2026-08-29T23:11:00Z",
        "data": {"metric": "test", "value": 1},
        "parent_hash": None,
    }
    values.update(overrides)
    return FR0333Record(**values)


def main() -> None:
    assert alpha_bound("RAW") == "R.18.A.01.W.23"
    assert alpha_bound("REV") == "R.18.E.05.V.22"
    assert validate_bound_token("X.24.Y.25.Z.26.P.16.T.20")
    assert not validate_bound_token("X.25")
    assert not validate_bound_token("RAW")

    signing_key = SigningKey.generate(curve=NIST256p)
    verifying_key = signing_key.get_verifying_key()

    parent = make_record(observation_id="L01.001.1")
    parent_seal = CryptoVoiceEngine.sign_record(parent, signing_key, "PUB_FR0333_TEST_01")
    assert CryptoVoiceEngine.verify_all(parent, parent_seal, verifying_key) is CryptoState.AUTHENTIC

    altered = replace(parent, data={"metric": "test", "value": 2})
    assert CryptoVoiceEngine.verify_hash(altered, parent_seal) is CryptoState.ALTERED_RECORD

    child = make_record(
        object_address="FR.0333.L01.1.7.369.7.1.L01.002.1",
        observation_id="L01.002.1",
        parent_hash=parent_seal.hash_hex,
    )
    child_seal = CryptoVoiceEngine.sign_record(child, signing_key, "PUB_FR0333_TEST_01")
    assert CryptoVoiceEngine.verify_all(child, child_seal, verifying_key, parent_seal) is CryptoState.AUTHENTIC
    assert CryptoVoiceEngine.verify_lineage(child, None) is CryptoState.PARENT_MISSING

    malformed = make_record(coordinate="X.24.Y.25.Z.26.P.17.T.20")
    try:
        CryptoVoiceEngine.hash_record(malformed)
    except ValueError as exc:
        assert str(exc) == CryptoState.SYNTAX_INVALID.value
    else:
        raise AssertionError("misbound P coordinate must be rejected")

    print("FR0333.CRYPTO.VOICE VALIDATION PASS")
    print("KERNELS 4/4: HASH SIGNATURE KEY_IDENTITY LINEAGE")
    print("COORDINATE:", COORDINATE_5D)


if __name__ == "__main__":
    main()
