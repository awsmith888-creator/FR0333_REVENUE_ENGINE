from fr0333.adobe_5d_engine import (
    Adobe5DCalibrationEngine,
    Coordinate5D,
    EvidenceBit,
    EvidenceClass,
    GateAction,
    MetricIdentity,
    ValueState,
)


def bit(bit_id, value, state=ValueState.PRESENT):
    return EvidenceBit(
        bit_id=bit_id,
        coordinate=Coordinate5D("US", "TEST", "SOURCE", "P", "T"),
        evidence_class=EvidenceClass.MEASURED,
        value=value,
        state=state,
    )


def test_absent_signature_routes_unverified_not_halt():
    engine = Adobe5DCalibrationEngine()
    b = bit("BIT_11", None, ValueState.ABSENT)
    assert engine.gate(b) is GateAction.ROUTE_UNVERIFIED


def test_absent_manifest_routes_unverified_not_halt():
    engine = Adobe5DCalibrationEngine()
    b = bit("BIT_13", None, ValueState.ABSENT)
    assert engine.gate(b) is GateAction.ROUTE_UNVERIFIED


def test_no_consent_hard_purges():
    engine = Adobe5DCalibrationEngine()
    b = bit("BIT_62", False)
    assert engine.gate(b) is GateAction.HARD_PURGE


def test_privacy_failure_hard_purges():
    engine = Adobe5DCalibrationEngine()
    b = bit("BIT_63", False)
    assert engine.gate(b) is GateAction.HARD_PURGE


def test_invalid_state_halts():
    engine = Adobe5DCalibrationEngine()
    b = bit("BIT_28", None, ValueState.INVALID)
    assert engine.gate(b) is GateAction.HALT_STREAM


def test_detector_failure_is_unknown_not_one():
    score, state = Adobe5DCalibrationEngine.detector_result(None, status="ERROR")
    assert score is None
    assert state is ValueState.UNKNOWN


def test_detector_success_range_validated():
    score, state = Adobe5DCalibrationEngine.detector_result(0.72, status="SUCCESS")
    assert score == 0.72
    assert state is ValueState.PRESENT


def test_detector_out_of_range_is_invalid():
    score, state = Adobe5DCalibrationEngine.detector_result(1.2, status="SUCCESS")
    assert score is None
    assert state is ValueState.INVALID


def test_byte_mismatch_does_not_itself_assert_tamper():
    assert Adobe5DCalibrationEngine.byte_identity("a", "b") is False
    assert Adobe5DCalibrationEngine.tamper_suspected(
        signed_binding_expected=False,
        signed_binding_valid=None,
        manifest_present=False,
        manifest_valid=None,
    ) is False


def test_invalid_signed_binding_can_raise_tamper_suspicion():
    assert Adobe5DCalibrationEngine.tamper_suspected(
        signed_binding_expected=True,
        signed_binding_valid=False,
        manifest_present=True,
        manifest_valid=True,
    ) is True


def test_applicable_ratio_excludes_not_applicable_fields():
    assert Adobe5DCalibrationEngine.applicable_ratio(3, 4) == 0.75
    assert Adobe5DCalibrationEngine.applicable_ratio(0, 0) is None


def test_metric_identity_requires_both_ratio_terms():
    metric = MetricIdentity("FALSE_ALARM_RATIO", "FALSE_ALARMS", "HITS_PLUS_FALSE_ALARMS")
    metric.validate()


def test_metric_identity_rejects_ambiguous_denominator():
    metric = MetricIdentity("BAD_RATE", "FALSE_ALARMS", None)
    try:
        metric.validate()
    except ValueError:
        pass
    else:
        raise AssertionError("ratio metric without denominator should fail")


def test_non_present_state_cannot_carry_numeric_zero():
    b = bit("BIT_46", 0.0, ValueState.UNKNOWN)
    try:
        b.validate()
    except ValueError:
        pass
    else:
        raise AssertionError("UNKNOWN must not be encoded as numeric zero")


def test_no_cross_rail_promotion():
    assert Adobe5DCalibrationEngine.no_cross_rail_promotion("AUDIENCE", "FORECAST_QUALITY") is False
    assert Adobe5DCalibrationEngine.no_cross_rail_promotion("PROVENANCE", "TRUTH") is False
    assert Adobe5DCalibrationEngine.no_cross_rail_promotion("PROVENANCE", "PROVENANCE_COMPLETENESS") is True
