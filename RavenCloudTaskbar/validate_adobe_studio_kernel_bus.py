from fr0333.adobe_studio_kernel_bus import AdobeStudioKernelBus, KernelPacket, KernelRoute


def main() -> None:
    bus = AdobeStudioKernelBus()

    hold = bus.process(
        KernelPacket(
            packet_id="OBS.001",
            source_ref="SOURCE.TEST",
            provenance_verified=True,
            logical_slots=64,
            probability_variance=0.01,
            signature_match=1.0,
            bit_62_valid=True,
            bit_63_valid=True,
            image_execution_enabled=False,
        )
    )
    assert hold.route is KernelRoute.STAY_HOLD
    assert hold.trace == (
        "K01.PROVENANCE_MATCH",
        "K02.DIMENSIONAL_GUARD_PASS",
        "K03.STATE_EVALUATION_PASS",
        "K04.K05_STATIC_STAY_HOLD",
    )

    purge = bus.process(
        KernelPacket(
            packet_id="OBS.002",
            source_ref="SOURCE.TEST",
            provenance_verified=True,
            bit_62_valid=False,
            bit_63_valid=True,
        )
    )
    assert purge.route is KernelRoute.HARD_PURGE
    assert purge.trace[-1] == "K04.HARD_PURGE"

    unverified = bus.process(
        KernelPacket(
            packet_id="OBS.003",
            source_ref="SOURCE.TEST",
            provenance_verified=False,
        )
    )
    assert unverified.route is KernelRoute.ROUTE_UNVERIFIED
    assert "K01.PROVENANCE_UNVERIFIED" in unverified.trace

    dimensional_fail = bus.process(
        KernelPacket(
            packet_id="OBS.004",
            source_ref="SOURCE.TEST",
            provenance_verified=True,
            physical_bits_derived=True,
        )
    )
    assert dimensional_fail.route is KernelRoute.HALT_STREAM
    assert "K02.PHYSICAL_BIT_COERCION" in dimensional_fail.trace

    variance_fail = bus.process(
        KernelPacket(
            packet_id="OBS.005",
            source_ref="SOURCE.TEST",
            provenance_verified=True,
            probability_variance=0.011,
        )
    )
    assert variance_fail.route is KernelRoute.HALT_STREAM
    assert "K03.VARIANCE_LIMIT_FAIL" in variance_fail.trace

    pass_stream = bus.process(
        KernelPacket(
            packet_id="OBS.006",
            source_ref="SOURCE.TEST",
            provenance_verified=True,
            probability_variance=0.0,
            signature_match=1.0,
            image_execution_enabled=True,
        )
    )
    assert pass_stream.route is KernelRoute.PASS_STREAM
    assert pass_stream.trace[-1] == "K04.PASS_STREAM"

    print("ADOBE.STUDIO.KERNEL.BUS 6/6 PASS")
    print("FLOW 1.7.369.7.1")
    print("K01->K02->K03->K04 SYNCHRONIZED")
    print("K05 STATIC_STAY_HOLD RESPECTED")


if __name__ == "__main__":
    main()
