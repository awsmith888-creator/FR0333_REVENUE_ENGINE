#!/usr/bin/env python3
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
SPEC_PATH = HERE / "fr0333_adobe_human_realism_patch_0004.json"
MANIFEST_PATH = HERE / "fr0333_adobe_human_realism_manifest_0004.json"

REQUIRED_SLOT_FIELDS = [
    "slot_id",
    "scene",
    "wardrobe",
    "pose_action",
    "camera_setup",
    "lighting",
    "background",
    "subject_count",
    "identity_mode",
]

DIVERSITY_FIELDS = [
    "scene",
    "wardrobe",
    "pose_action",
    "camera_setup",
    "lighting",
    "background",
]


def _check(results, name, condition, detail):
    results.append({"gate": name, "state": "PASS" if condition else "FAIL", "detail": detail})


def validate_spec(spec):
    results = []

    _check(
        results,
        "G1.IDENTIFIER.BINDING",
        spec.get("identifier") == "FR0333.ADOBE.HUMAN.REALISM.DIVERSITY.PATCH.0004"
        and spec.get("binds", {}).get("image_quality_gate") == "FR0333.IMAGE.QUALITY.GATE.0003"
        and spec.get("binds", {}).get("camera_gate") == "FR.0333.ADOBE.CAMERA.3.3.3.0001",
        "patch identifier and upstream Adobe/quality bindings are locked",
    )

    queue = spec.get("queue_contract", {})
    _check(
        results,
        "G2.QUEUE.COUNT.CANVAS",
        queue.get("supported_requested_count_min") == 1
        and queue.get("supported_requested_count_max") == 10
        and queue.get("requested_count_equals_slot_count") is True
        and queue.get("slot_count_equals_output_count") is True
        and queue.get("one_slot_one_prompt") is True
        and queue.get("one_slot_one_canvas") is True
        and queue.get("one_canvas_one_image") is True
        and queue.get("aspect_ratio") == "9:16"
        and queue.get("collage") == "REJECT"
        and queue.get("contact_sheet") == "REJECT"
        and queue.get("duplicate_output") == "REJECT"
        and queue.get("missing_output") == "REJECT",
        "one requested slot maps to one independent 9:16 image with no collage, duplication, or missing output",
    )

    human = spec.get("human_realism_gate", {})
    _check(
        results,
        "G3.HUMAN.REALISM",
        human.get("human_request_requires_human_anatomy_pass") is True
        and human.get("face_proportion_check") == "REQUIRED"
        and human.get("hand_digit_joint_check") == "REQUIRED"
        and human.get("limb_joint_range_check") == "REQUIRED"
        and human.get("weight_balance_contact_check") == "REQUIRED"
        and human.get("skin_texture_microvariation") == "REQUIRED"
        and human.get("fabric_body_interaction_check") == "REQUIRED"
        and human.get("synthetic_plastic_skin") == "REJECT",
        "human outputs require anatomy, contact physics, skin, and fabric realism",
    )

    diversity = spec.get("diversity_contract", {})
    _check(
        results,
        "G4.DIVERSITY.CONTRACT",
        diversity.get("activation") == "USER_REQUESTS_DIFFERENT_UNIQUE_OR_EVERYTHING_DIFFERENT"
        and all(diversity.get(key) is True for key in (
            "scene_unique_per_slot",
            "wardrobe_unique_per_slot",
            "pose_or_action_unique_per_slot",
            "camera_setup_unique_per_slot",
            "background_unique_per_slot",
            "lighting_setup_unique_per_slot",
            "subject_cast_unique_per_slot",
        ))
        and diversity.get("repeat_allowed_only_when_explicitly_requested") is True,
        "explicit diversity requests make scene, wardrobe, action, camera, background, light, and cast independently unique",
    )

    identity = spec.get("identity_policy", {})
    _check(
        results,
        "G5.IDENTITY.ANTI.CLONE",
        identity.get("default_for_multi_scene_human_generation") == "DISTINCT_CAST"
        and identity.get("same_face_across_slots") == "REJECT_UNLESS_PRESERVE_SOURCE_IDENTITY_OR_CONTINUITY_CAST"
        and identity.get("same_face_multiple_times_in_one_scene") == "REJECT_UNLESS_EXPLICIT_CLONE_CONCEPT"
        and identity.get("style_reference_does_not_imply_identity_copy") is True
        and identity.get("remake_ne_clone") is True,
        "style continuity cannot silently become repeated identity or clone output",
    )

    manifest = spec.get("slot_manifest", {})
    _check(
        results,
        "G6.SLOT.MANIFEST",
        manifest.get("required") is True
        and manifest.get("required_fields") == REQUIRED_SLOT_FIELDS
        and manifest.get("slot_id_format") == "Q01_TO_Q10"
        and manifest.get("semantic_collision_check") == "REQUIRED_BEFORE_PROVIDER_EXECUTION",
        "each slot carries explicit scene, wardrobe, action, camera, lighting, background, cast count, and identity mode",
    )

    readback = spec.get("readback_gate", {})
    _check(
        results,
        "G7.READBACK.FAIL.CLOSED",
        readback.get("required_per_output") is True
        and readback.get("compare_against_slot_manifest") is True
        and readback.get("check_human_realism") is True
        and readback.get("check_scene_uniqueness") is True
        and readback.get("check_wardrobe_uniqueness") is True
        and readback.get("check_cast_uniqueness") is True
        and readback.get("check_count_integrity") is True
        and readback.get("on_failure") == "HOLD_OUTPUT_REGENERATE_ONLY_FAILED_SLOT",
        "every output must be visually read back and only failed slots are regenerated",
    )

    promotion = spec.get("promotion_gate", {})
    _check(
        results,
        "G8.PROMOTION.HUMANLOCK",
        spec.get("humanlock") is True
        and promotion.get("all_slots_must_pass") is True
        and promotion.get("user_reject_overrides_promotion") is True
        and promotion.get("visual_readback_required") is True
        and promotion.get("runtime_receipt_required_for_external_execution_claim") is True
        and promotion.get("provider_success_ne_quality_pass") is True
        and promotion.get("failed_slot_must_not_force_regeneration_of_passing_slots") is True,
        "HumanLock, readback, and user rejection remain authoritative; provider success alone cannot promote",
    )

    hard = set(spec.get("hard_boundaries", []))
    required_hard = {
        "PHOTOREALISTIC.STYLE != HUMAN.REALISM",
        "STYLE.COHERENCE != SLOT.DUPLICATION",
        "SAME.FACE != CAST.CONTINUITY.UNLESS.REQUESTED",
        "PROVIDER.SUCCESS != QUALITY.PASS",
        "BATCH.SUCCESS != N_IN_N_OUT.PASS",
        "READBACK.FAIL = SLOT.HOLD",
        "USER.REJECT = OUTPUT.HOLD",
        "LOCAL.CI.PASS != EXTERNAL.ADOBE.RUNTIME",
        "THIS.PATCH != ADOBE.INTERNAL.MODEL.MODIFICATION",
    }
    _check(
        results,
        "G9.HARD.BOUNDARIES",
        required_hard.issubset(hard),
        "quality, provider, runtime, duplication, and ownership boundaries are explicit",
    )

    runtime = spec.get("runtime_boundary", {})
    _check(
        results,
        "G10.RUNTIME.BOUNDARY",
        runtime.get("local_validator") == "ESTABLISHES_SPEC_CONFORMANCE_ONLY"
        and runtime.get("external_adobe_runtime") == "NOT_ESTABLISHED_BY_THIS_PATCH"
        and runtime.get("external_provider_quality") == "MUST_BE_PROVEN_BY_RUNTIME_RECEIPT_AND_READBACK"
        and runtime.get("ownership_boundary") == "PATCH_MODIFIES_FR0333_ORCHESTRATION_AND_VALIDATION_NOT_ADOBE_INTERNAL_SYSTEMS",
        "the patch changes FR0333 orchestration and cannot claim modification of Adobe internals or live runtime",
    )

    return results


def validate_manifest(spec, manifest):
    results = []
    queue = spec["queue_contract"]
    diversity = spec["diversity_contract"]
    identity = spec["identity_policy"]
    slots = manifest.get("slots", [])
    requested = manifest.get("requested_count")

    _check(
        results,
        "M1.COUNT.INVARIANT",
        isinstance(requested, int)
        and queue["supported_requested_count_min"] <= requested <= queue["supported_requested_count_max"]
        and len(slots) == requested,
        "requested count equals manifest slot count within supported range",
    )

    expected_ids = [f"Q{i:02d}" for i in range(1, requested + 1)] if isinstance(requested, int) and requested > 0 else []
    actual_ids = [slot.get("slot_id") for slot in slots]
    _check(
        results,
        "M2.SLOT.SEQUENCE",
        actual_ids == expected_ids and len(set(actual_ids)) == len(actual_ids),
        "slot IDs are deterministic Q01 through requested count with no duplicates",
    )

    _check(
        results,
        "M3.REQUIRED.FIELDS",
        all(all(field in slot and slot[field] not in (None, "") for field in REQUIRED_SLOT_FIELDS) for slot in slots),
        "every slot contains all required semantic controls",
    )

    diversity_required = "DIFFERENT" in str(manifest.get("user_intent", "")).upper() or "UNIQUE" in str(manifest.get("user_intent", "")).upper()
    unique_ok = True
    if diversity_required:
        for field in DIVERSITY_FIELDS:
            values = [str(slot.get(field, "")).strip().lower() for slot in slots]
            unique_ok = unique_ok and len(values) == len(set(values))
    _check(
        results,
        "M4.SEMANTIC.DIVERSITY",
        unique_ok,
        "explicit diversity intent produces unique scene, wardrobe, action, camera, lighting, and background per slot",
    )

    modes = set(identity.get("identity_mode_values", []))
    identity_modes = [slot.get("identity_mode") for slot in slots]
    _check(
        results,
        "M5.IDENTITY.MODE",
        all(mode in modes for mode in identity_modes)
        and (not diversity_required or all(mode == "DISTINCT_CAST" for mode in identity_modes)),
        "diversity manifest uses supported identity modes and distinct cast by default",
    )

    _check(
        results,
        "M6.SUBJECT.COUNT",
        all(isinstance(slot.get("subject_count"), int) and slot["subject_count"] >= 1 for slot in slots),
        "every scene declares one or more human subjects",
    )

    return results


def validate(spec, manifest):
    results = validate_spec(spec) + validate_manifest(spec, manifest)
    passed = sum(item["state"] == "PASS" for item in results)
    return {
        "identifier": "FR0333.GENIUS.ADOBE.HUMAN.REALISM.DIVERSITY.PATCH.0004",
        "state": "PASS" if passed == len(results) else "FAIL",
        "passed": passed,
        "total": len(results),
        "invariant": "TEN.IN -> TEN.OUT WHEN REQUESTED; ONE.SLOT -> ONE.IMAGE ALWAYS",
        "results": results,
    }


def main():
    spec_path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else SPEC_PATH
    manifest_path = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else MANIFEST_PATH
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = validate(spec, manifest)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["state"] == "PASS" else 1)


if __name__ == "__main__":
    main()
