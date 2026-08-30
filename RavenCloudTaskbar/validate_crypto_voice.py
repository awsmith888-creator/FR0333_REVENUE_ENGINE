#!/usr/bin/env python3
"""Executable validation for FR-0333 cryptographic voice kernels."""
from dataclasses import replace
from ecdsa import NIST256p, SigningKey
from fr0333.crypto_voice_engine import (
    CANONICAL_FIELD_ORDER, COORDINATE_5D, CryptoState, CryptoVoiceEngine,
    FR0333Record, alpha_bound, canonical_bytes, require_numeric_reference,
    validate_bound_token, validate_numeric_reference,
)

VALID = ("1.000", "10.000", "70.000", "120.000", "1.000.000", "1.073.741.824")
INVALID = ("70000", "70.00", "70.0000", "1,000", "1.00.000", "01.000", "1..000", ".1.000", "1.000.")

def make_record(**overrides):
    values = {
        "object_address": "FR.0333.L01.1.7.369.7.1.L01.001.1",
        "system_id": "L01", "reference_point": "L01.000.1",
        "coordinate": COORDINATE_5D, "record_type": "R.18.A.01.W.23",
        "observation_id": "L01.001.1", "timestamp": "2026-08-29T23:11:00Z",
        "data": {"value": "1.000", "unit": "TEST", "evidence_class": "E_OBS", "value_state": "PRESENT"},
        "parent_hash": None,
    }
    values.update(overrides)
    return FR0333Record(**values)

def expect_gate(value, suffix):
    try:
        require_numeric_reference(value)
    except ValueError as exc:
        assert str(exc) == f"GATE.ERR.01:{suffix}", (value, str(exc))
        return
    raise AssertionError(f"{value} must fail before CRY.K01")

def main():
    assert alpha_bound("RAW") == "R.18.A.01.W.23"
    assert alpha_bound("REV") == "R.18.E.05.V.22"
    assert validate_bound_token("X.24.Y.25.Z.26.P.16.T.20")
    assert not validate_bound_token("X.25") and not validate_bound_token("RAW")

    for value in VALID:
        assert validate_numeric_reference(value), value
    for value in INVALID:
        assert not validate_numeric_reference(value), value
    expect_gate("70.00", "MALFORMED.REFERENCE.GROUP")
    expect_gate("1,000", "FOREIGN.INPUT:COMMA.PROHIBITED")

    # Schema order is constitutional, not dict/alphabetical order.
    probe = make_record().payload("PUB_FR0333_TEST_01")
    assert tuple(probe.keys()) == CANONICAL_FIELD_ORDER
    canonical = canonical_bytes(probe)
    assert canonical.startswith(b'{"schema_version":"000.1","system_id":"L01","flow":"1.7.369.7.1"')
    try:
        canonical_bytes({**probe, "unknown": "FAIL"})
    except ValueError as exc:
        assert str(exc) == "GATE.ERR.02:UNKNOWN.FIELD"
    else:
        raise AssertionError("unknown field must fail closed")
    missing = dict(probe); missing.pop("source")
    try:
        canonical_bytes(missing)
    except ValueError as exc:
        assert str(exc) == "GATE.ERR.02:MISSING.REQUIRED.FIELD"
    else:
        raise AssertionError("missing required field must fail closed")

    signing_key = SigningKey.generate(curve=NIST256p)
    verifying_key = signing_key.get_verifying_key()
    parent = make_record(data={"value": "70.000", "unit": "USD", "evidence_class": "E_OBS", "value_state": "PRESENT"})
    parent_seal = CryptoVoiceEngine.sign_record(parent, signing_key, "PUB_FR0333_TEST_01")
    assert CryptoVoiceEngine.verify_all(parent, parent_seal, verifying_key) is CryptoState.AUTHENTIC

    # Post-signature mutation is a cryptographic failure, distinct from parser-gate rejection.
    altered = replace(parent, data={"value": "70000", "unit": "USD", "evidence_class": "E_OBS", "value_state": "PRESENT"})
    assert CryptoVoiceEngine.verify_hash(altered, parent_seal) is CryptoState.ALTERED_RECORD
    assert CryptoVoiceEngine.verify_signature(altered, parent_seal, verifying_key) is CryptoState.UNAUTHENTICATED_RECORD

    child = make_record(object_address="FR.0333.L01.1.7.369.7.1.L01.002.1", observation_id="L01.002.1", parent_hash=parent_seal.hash_hex)
    child_seal = CryptoVoiceEngine.sign_record(child, signing_key, "PUB_FR0333_TEST_01")
    assert CryptoVoiceEngine.verify_all(child, child_seal, verifying_key, parent_seal) is CryptoState.AUTHENTIC
    assert CryptoVoiceEngine.verify_lineage(child, None) is CryptoState.PARENT_MISSING

    malformed = make_record(coordinate="X.24.Y.25.Z.26.P.17.T.20")
    try: CryptoVoiceEngine.hash_record(malformed)
    except ValueError as exc: assert str(exc) == CryptoState.SYNTAX_INVALID.value
    else: raise AssertionError("misbound P coordinate must be rejected")

    print("FR0333.CRYPTO.VOICE VALIDATION PASS")
    print("NUMERIC.GRAMMAR 6/6 VALID; 9/9 INVALID REJECTED")
    print("PRE.HASH.GATES PASS")
    print("SERIALIZATION.ORDER 25/25 PASS")
    print("UNKNOWN/MISSING FIELD FAIL.CLOSED PASS")
    print("ALTERATION.AFTER.SIGNATURE PASS")
    print("KERNELS 4/4: HASH SIGNATURE KEY_IDENTITY LINEAGE")
    print("COORDINATE:", COORDINATE_5D)

if __name__ == "__main__": main()
