from fr0333.adobe_studio_kernel_bus import AdobeStudioKernelBus, KernelPacket, KernelRoute


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
    assert result.trace[-1] == "K04.K05_STATIC_STAY_HOLD"


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
        "K01.PROVENANCE_MATCH",
        "K02.DIMENSIONAL_GUARD_PASS",
        "K03.STATE_EVALUATION_PASS",
        "K04.PASS_STREAM",
    )
