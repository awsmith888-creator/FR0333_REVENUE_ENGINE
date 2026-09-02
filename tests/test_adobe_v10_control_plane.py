import pytest

from fr0333.adobe_v10_control_plane import (
    ArchitectureViolation,
    BatchManifest,
    SlotIntent,
    verify_output_manifest,
)


def make_slots():
    descriptors = [
        "Overlook", "Dock Arrival", "Boats Passing", "Team Briefing", "Boarding",
        "Command From Boat", "Shoreline Landing", "Exercise Observation",
        "Post-Exercise Debrief", "Final Command Portrait",
    ]
    return [
        SlotIntent(f"{i:02d}", descriptor, f"camera-{i:02d}", f"blocking-{i:02d}")
        for i, descriptor in enumerate(descriptors, start=1)
    ]


def test_compile_exact_ten_independent_slots():
    manifest = BatchManifest("BATCH-FR0333-V10-RIVER-001", "ADOBE_V2_TACTICAL_SEQUENCE", make_slots())
    graph = manifest.compile_action_graph()
    assert graph["architecture_version"] == "10.0"
    assert len(graph["actions"]) == 10
    assert len({a["slot_id"] for a in graph["actions"]}) == 10
    assert all(a["independent_asset_required"] for a in graph["actions"])
    assert all(not a["collage_allowed"] for a in graph["actions"])
    assert graph["promotion_state"] == "HOLD_EXTERNAL_RUNTIME"


def test_batch_count_mismatch_hard_fails():
    manifest = BatchManifest("x", "y", make_slots()[:-1])
    with pytest.raises(ArchitectureViolation, match="BATCH_COUNT_MISMATCH"):
        manifest.validate()


def test_legacy_v1_hard_denied():
    manifest = BatchManifest("x", "y", make_slots(), legacy_v1=True)
    with pytest.raises(ArchitectureViolation, match="LEGACY_V1_DENY"):
        manifest.validate()


def test_collage_hard_denied():
    manifest = BatchManifest("x", "y", make_slots(), collage=True)
    with pytest.raises(ArchitectureViolation, match="COLLAGE_DENY"):
        manifest.validate()


def test_humanlock_required():
    manifest = BatchManifest("x", "y", make_slots(), humanlock=False)
    with pytest.raises(ArchitectureViolation, match="HUMANLOCK_REQUIRED"):
        manifest.validate()


def test_duplicate_slot_id_hard_fails():
    slots = make_slots()
    slots[9] = SlotIntent("09", "dup", "camera", "blocking")
    with pytest.raises(ArchitectureViolation, match="DUPLICATE_SLOT_ID"):
        BatchManifest("x", "y", slots).validate()


def test_output_manifest_requires_unique_asset_per_slot():
    graph = BatchManifest("x", "y", make_slots()).compile_action_graph()
    outputs = [
        {
            "slot_id": f"{i:02d}",
            "asset_id": f"asset-{i:02d}",
            "aspect_ratio": "9:16",
            "collage": False,
            "runtime_verified": False,
        }
        for i in range(1, 11)
    ]
    receipt = verify_output_manifest(graph, outputs)
    assert receipt["validation_state"] == "PASS_STRUCTURE"
    assert receipt["output_count"] == 10
    assert receipt["promotion_state"] == "HOLD_EXTERNAL_RUNTIME"


def test_duplicate_output_asset_id_hard_fails():
    graph = BatchManifest("x", "y", make_slots()).compile_action_graph()
    outputs = [
        {
            "slot_id": f"{i:02d}",
            "asset_id": "same-asset",
            "aspect_ratio": "9:16",
            "collage": False,
            "runtime_verified": False,
        }
        for i in range(1, 11)
    ]
    with pytest.raises(ArchitectureViolation, match="DUPLICATE_ASSET_ID"):
        verify_output_manifest(graph, outputs)
