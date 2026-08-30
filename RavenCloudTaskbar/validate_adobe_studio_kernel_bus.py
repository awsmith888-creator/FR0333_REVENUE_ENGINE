from fr0333.adobe_studio_kernel_bus import (
    AdobeStudioKernelBus,
    KERNEL_INDEX,
    KernelPacket,
    KernelRoute,
)


def main() -> None:
    expected_index = tuple(
        (f"K.11.0.{slot}", f"K.11.0.{slot}.000.1", f"K.11.0.{slot}.1.7.369.7.1")
        for slot in range(1, 6)
    )
    actual_index = tuple(
        (entry.system_id, entry.reference_point, entry.flow_address)
        for entry in KERNEL_INDEX
    )
    assert actual_index == expected_index

    bus = AdobeStudioKernelBus()

    hold = bus.process(KernelPacket(
        packet_id="OBS.001", source_ref="SOURCE.TEST", provenance_verified=True,
        logical_slots=64, probability_variance=0.01, signature_match=1.0,
        bit_62_valid=True, bit_63_valid=True, image_execution_enabled=False,
    ))
    assert hold.route is KernelRoute.STAY_HOLD
    assert hold.trace == (
        "K.11.0.1.PROVENANCE_MATCH",
        "K.11.0.2.DIMENSIONAL_GUARD_PASS",
        "K.11.0.3.STATE_EVALUATION_PASS",
        "K.11.0.4.LOGIC_GATE_PASS",
        "K.11.0.5.STATIC_STAY_HOLD",
    )

    purge = bus.process(KernelPacket(
        packet_id="OBS.002", source_ref="SOURCE.TEST", provenance_verified=True,
        bit_62_valid=False, bit_63_valid=True,
    ))
    assert purge.route is KernelRoute.HARD_PURGE
    assert "K.11.0.4.HARD_PURGE" in purge.trace
    assert purge.trace[-1] == "K.11.0.5.BYPASS_HARD_PURGE"

    unverified = bus.process(KernelPacket(
        packet_id="OBS.003", source_ref="SOURCE.TEST", provenance_verified=False,
    ))
    assert unverified.route is KernelRoute.ROUTE_UNVERIFIED
    assert "K.11.0.1.PROVENANCE_UNVERIFIED" in unverified.trace
    assert unverified.trace[-1] == "K.11.0.5.ISOLATE_UNVERIFIED"

    dimensional_fail = bus.process(KernelPacket(
        packet_id="OBS.004", source_ref="SOURCE.TEST", provenance_verified=True,
        physical_bits_derived=True,
    ))
    assert dimensional_fail.route is KernelRoute.HALT_STREAM
    assert "K.11.0.2.PHYSICAL_BIT_COERCION" in dimensional_fail.trace

    variance_fail = bus.process(KernelPacket(
        packet_id="OBS.005", source_ref="SOURCE.TEST", provenance_verified=True,
        probability_variance=0.011,
    ))
    assert variance_fail.route is KernelRoute.HALT_STREAM
    assert "K.11.0.3.VARIANCE_LIMIT_FAIL" in variance_fail.trace

    pass_stream = bus.process(KernelPacket(
        packet_id="OBS.006", source_ref="SOURCE.TEST", provenance_verified=True,
        probability_variance=0.0, signature_match=1.0, image_execution_enabled=True,
    ))
    assert pass_stream.route is KernelRoute.PASS_STREAM
    assert pass_stream.trace[-2:] == (
        "K.11.0.4.LOGIC_GATE_PASS",
        "K.11.0.5.PASS_STREAM",
    )

    print("ADOBE.STUDIO.KERNEL.BUS PASS")
    print("FLOW 1.7.369.7.1")
    print("K.11.0.1 -> K.11.0.2 -> K.11.0.3 -> K.11.0.4 -> K.11.0.5 INDEXED")
    print("REFERENCE.POINTS .000.1 BOUND")
    print("K.11.0.5 STATIC_STAY_HOLD RESPECTED")


if __name__ == "__main__":
    main()
