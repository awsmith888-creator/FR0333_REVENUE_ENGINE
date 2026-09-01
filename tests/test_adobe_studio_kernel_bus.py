from fr0333.adobe_studio_kernel_bus import (
    AdobeStudioKernelBus,
    KERNEL_INDEX,
    KernelPacket,
    KernelRoute,
)


def test_kernel_index_is_canonical_symmetric_and_reference_bound():
    assert tuple(entry.system_id for entry in KERNEL_INDEX) == tuple(
        f"K.11.0.{slot}" for slot in range(1, 6)
    )
    assert tuple(entry.reference_point for entry in KERNEL_INDEX) == tuple(
        f"K.11.0.{slot}.000.1" for slot in range(1, 6)
    )
    assert tuple(entry.flow_address for entry in KERNEL_INDEX) == tuple(
        f"K.11.0.{slot}.1.7.369.7.1" for slot in range(1, 6)
    )


def test_static_hold_is_owned_by_containment_kernel():
    result = AdobeStudioKernelBus().process(KernelPacket(
        packet_id="T.001", source_ref="SOURCE.TEST", provenance_verified=True,
        image_execution_enabled=False,
    ))
    assert result.route is KernelRoute.STAY_HOLD
    assert result.trace[-2:] == (
        "K.11.0.4.LOGIC_GATE_PASS",
        "K.11.0.5.STATIC_STAY_HOLD",
    )


def test_hard_purge_dominates_privacy_failure():
    result = AdobeStudioKernelBus().process(KernelPacket(
        packet_id="T.002", source_ref="SOURCE.TEST", provenance_verified=True,
        bit_63_valid=False, image_execution_enabled=True,
    ))
    assert result.route is KernelRoute.HARD_PURGE
    assert "K.11.0.4.HARD_PURGE" in result.trace
    assert result.trace[-1] == "K.11.0.5.BYPASS_HARD_PURGE"


def test_unverified_provenance_isolated():
    result = AdobeStudioKernelBus().process(KernelPacket(
        packet_id="T.003", source_ref="SOURCE.TEST", provenance_verified=False,
    ))
    assert result.route is KernelRoute.ROUTE_UNVERIFIED
    assert result.trace[-1] == "K.11.0.5.ISOLATE_UNVERIFIED"


def test_logical_slot_physical_bit_coercion_halts():
    result = AdobeStudioKernelBus().process(KernelPacket(
        packet_id="T.004", source_ref="SOURCE.TEST", provenance_verified=True,
        physical_bits_derived=True,
    ))
    assert result.route is KernelRoute.HALT_STREAM


def test_variance_over_limit_halts():
    result = AdobeStudioKernelBus().process(KernelPacket(
        packet_id="T.005", source_ref="SOURCE.TEST", provenance_verified=True,
        probability_variance=0.0101,
    ))
    assert result.route is KernelRoute.HALT_STREAM


def test_verified_packet_can_pass_through_logic_into_containment():
    result = AdobeStudioKernelBus().process(KernelPacket(
        packet_id="T.006", source_ref="SOURCE.TEST", provenance_verified=True,
        signature_match=1.0, image_execution_enabled=True,
    ))
    assert result.route is KernelRoute.PASS_STREAM
    assert result.trace == (
        "K.11.0.1.PROVENANCE_MATCH",
        "K.11.0.2.DIMENSIONAL_GUARD_PASS",
        "K.11.0.3.STATE_EVALUATION_PASS",
        "K.11.0.4.LOGIC_GATE_PASS",
        "K.11.0.5.ISOLATION_PASS",
    )


def test_ten_output_batch_requires_ten_unique_assets():
    ids = tuple(f"OUT.{i:03d}" for i in range(1, 11))
    result = AdobeStudioKernelBus().process(KernelPacket(
        packet_id="T.007", source_ref="SOURCE.TEST", provenance_verified=True,
        image_execution_enabled=True, requested_outputs=10,
        isolated_output_ids=ids,
    ))
    assert result.route is KernelRoute.PASS_STREAM
    assert result.trace[-1] == "K.11.0.5.ISOLATION_PASS"


def test_output_count_mismatch_halts():
    result = AdobeStudioKernelBus().process(KernelPacket(
        packet_id="T.008", source_ref="SOURCE.TEST", provenance_verified=True,
        image_execution_enabled=True, requested_outputs=10,
        isolated_output_ids=("OUT.001",),
    ))
    assert result.route is KernelRoute.HALT_STREAM
    assert result.trace[-1] == "K.11.0.5.OUTPUT_COUNT_MISMATCH"


def test_output_id_reuse_halts():
    result = AdobeStudioKernelBus().process(KernelPacket(
        packet_id="T.009", source_ref="SOURCE.TEST", provenance_verified=True,
        image_execution_enabled=True, requested_outputs=2,
        isolated_output_ids=("OUT.001", "OUT.001"),
    ))
    assert result.route is KernelRoute.HALT_STREAM
    assert result.trace[-1] == "K.11.0.5.OUTPUT_ID_REUSE"


def test_unrequested_collage_halts():
    result = AdobeStudioKernelBus().process(KernelPacket(
        packet_id="T.010", source_ref="SOURCE.TEST", provenance_verified=True,
        image_execution_enabled=True, collage_detected=True,
    ))
    assert result.route is KernelRoute.HALT_STREAM
    assert result.trace[-1] == "K.11.0.5.UNREQUESTED_COLLAGE"


def test_identity_lock_requires_anchor():
    result = AdobeStudioKernelBus().process(KernelPacket(
        packet_id="T.011", source_ref="SOURCE.TEST", provenance_verified=True,
        image_execution_enabled=True, identity_lock_required=True,
        identity_anchor_present=False,
    ))
    assert result.route is KernelRoute.ROUTE_UNVERIFIED
    assert result.trace[-1] == "K.11.0.5.IDENTITY_ANCHOR_MISSING"
