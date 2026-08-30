from fr0333.adobe_studio_kernel_bus import (
    AdobeStudioKernelBus,
    KERNEL_INDEX,
    KernelPacket,
    KernelRoute,
)


def test_kernel_index_is_canonical_and_reference_bound():
    assert tuple(entry.system_id for entry in KERNEL_INDEX) == (
        "K.11.01",
        "K.11.02",
        "K.11.03",
        "K.11.04",
    )
    assert tuple(entry.reference_point for entry in KERNEL_INDEX) == (
        "K.11.01.000.1",
        "K.11.02.000.1",
        "K.11.03.000.1",
        "K.11.04.000.1",
    )
    assert tuple(entry.flow_address for entry in KERNEL_INDEX) == (
        "K.11.01.1.7.369.7.1",
        "K.11.02.1.7.369.7.1",
        "K.11.03.1.7.369.7.1",
        "K.11.04.1.7.369.7.1",
    )


def test_static_hold_when_image_execution_disabled():
    result = AdobeStudioKernelBus().process(
        KernelPacket(
            packet_id="T.001",
            source_ref="SOURCE.TEST",
            provenance_verified=True,
            image_execution_enabled=False,
        )
    )
    assert result.route is KernelRoute.STAY_HOLD
    assert result.trace[-1] == "K.11.04.K05_STATIC_STAY_HOLD"


def test_hard_purge_dominates_privacy_failure():
    result = AdobeStudioKernelBus().process(
        KernelPacket(
            packet_id="T.002",
            source_ref="SOURCE.TEST",
            provenance_verified=True,
            bit_63_valid=False,
            image_execution_enabled=True,
        )
    )
    assert result.route is KernelRoute.HARD_PURGE


def test_unverified_provenance_isolated():
    result = AdobeStudioKernelBus().process(
        KernelPacket(packet_id="T.003", source_ref="SOURCE.TEST", provenance_verified=False)
    )
    assert result.route is KernelRoute.ROUTE_UNVERIFIED


def test_logical_slot_physical_bit_coercion_halts():
    result = AdobeStudioKernelBus().process(
        KernelPacket(
            packet_id="T.004",
            source_ref="SOURCE.TEST",
            provenance_verified=True,
            physical_bits_derived=True,
        )
    )
    assert result.route is KernelRoute.HALT_STREAM


def test_variance_over_limit_halts():
    result = AdobeStudioKernelBus().process(
        KernelPacket(
            packet_id="T.005",
            source_ref="SOURCE.TEST",
            provenance_verified=True,
            probability_variance=0.0101,
        )
    )
    assert result.route is KernelRoute.HALT_STREAM


def test_verified_packet_can_pass_when_execution_explicitly_enabled():
    result = AdobeStudioKernelBus().process(
        KernelPacket(
            packet_id="T.006",
            source_ref="SOURCE.TEST",
            provenance_verified=True,
            signature_match=1.0,
            image_execution_enabled=True,
        )
    )
    assert result.route is KernelRoute.PASS_STREAM
    assert result.trace == (
        "K.11.01.PROVENANCE_MATCH",
        "K.11.02.DIMENSIONAL_GUARD_PASS",
        "K.11.03.STATE_EVALUATION_PASS",
        "K.11.04.PASS_STREAM",
    )
