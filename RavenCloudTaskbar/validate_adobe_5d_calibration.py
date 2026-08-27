#!/usr/bin/env python3
from __future__ import annotations

from fr0333.adobe_5d_engine import (
    Adobe5DCalibrationEngine,
    Coordinate5D,
    EvidenceBit,
    EvidenceClass,
    GateAction,
    MetricIdentity,
    ValueState,
)


def make_bit(bit_id: str, value, state: ValueState = ValueState.PRESENT) -> EvidenceBit:
    return EvidenceBit(
        bit_id=bit_id,
        coordinate=Coordinate5D("US", "TEST", "ADOBE", "P", "T"),
        evidence_class=EvidenceClass.MEASURED,
        value=value,
        state=state,
    )


def main() -> None:
    engine = Adobe5DCalibrationEngine()

    assert engine.gate(make_bit("BIT_11", None, ValueState.ABSENT)) is GateAction.ROUTE_UNVERIFIED
    assert engine.gate(make_bit("BIT_13", None, ValueState.ABSENT)) is GateAction.ROUTE_UNVERIFIED
    assert engine.gate(make_bit("BIT_25", None, ValueState.UNKNOWN)) is GateAction.ROUTE_UNVERIFIED
    assert engine.gate(make_bit("BIT_62", False)) is GateAction.HARD_PURGE
    assert engine.gate(make_bit("BIT_63", False)) is GateAction.HARD_PURGE
    assert engine.gate(make_bit("BIT_28", None, ValueState.INVALID)) is GateAction.HALT_STREAM

    score, state = engine.detector_result(None, status="ERROR")
    assert score is None and state is ValueState.UNKNOWN

    score, state = engine.detector_result(0.72, status="SUCCESS")
    assert score == 0.72 and state is ValueState.PRESENT

    score, state = engine.detector_result(1.2, status="SUCCESS")
    assert score is None and state is ValueState.INVALID

    assert engine.byte_identity("a", "b") is False
    assert engine.tamper_suspected(
        signed_binding_expected=False,
        signed_binding_valid=None,
        manifest_present=False,
        manifest_valid=None,
    ) is False
    assert engine.tamper_suspected(
        signed_binding_expected=True,
        signed_binding_valid=False,
        manifest_present=True,
        manifest_valid=True,
    ) is True

    assert engine.applicable_ratio(3, 4) == 0.75
    assert engine.applicable_ratio(0, 0) is None

    MetricIdentity("FALSE_ALARM_RATIO", "FALSE_ALARMS", "HITS_PLUS_FALSE_ALARMS").validate()

    try:
        MetricIdentity("BAD_RATE", "FALSE_ALARMS", None).validate()
    except ValueError:
        pass
    else:
        raise AssertionError("ratio without denominator must fail")

    try:
        make_bit("BIT_46", 0.0, ValueState.UNKNOWN).validate()
    except ValueError:
        pass
    else:
        raise AssertionError("UNKNOWN must never be encoded as numeric zero")

    assert engine.no_cross_rail_promotion("AUDIENCE", "FORECAST_QUALITY") is False
    assert engine.no_cross_rail_promotion("PROVENANCE", "TRUTH") is False
    assert engine.no_cross_rail_promotion("PROVENANCE", "PROVENANCE_COMPLETENESS") is True

    print("FR0333.ADOBE.5D.CALIBRATION")
    print("checks=17/17")
    print("absent_invalid_separation=PASS")
    print("route_unverified=PASS")
    print("hard_purge_gate=PASS")
    print("detector_failure_semantics=PASS")
    print("byte_mismatch_ne_tamper=PASS")
    print("applicable_denominator=PASS")
    print("metric_identity_denominator=PASS")
    print("cross_rail_promotion=PASS")
    print("state=PASS_LOCAL_LOGIC")


if __name__ == "__main__":
    main()
