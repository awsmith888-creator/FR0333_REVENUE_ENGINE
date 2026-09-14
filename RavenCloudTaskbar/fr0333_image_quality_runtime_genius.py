#!/usr/bin/env python3
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
GATE_PATH = HERE / "fr0333_image_quality_gate_0004.json"
RECEIPT_PATH = HERE / "fr0333_adobe_image_runtime_receipt_0001.json"
QUEUE_FAILURE_PATH = HERE / "fr0333_adobe_image_queue_runtime_receipt_0002.json"
QUEUE_RUNTIME_PATH = HERE / "fr0333_adobe_image_queue_runtime_receipt_0003.json"

EXPECTED_DIMENSIONS = [
    "IDENTITY.FIDELITY", "ANATOMY.FACE.HANDS.FEET", "VEHICLE.MECHANICAL.GEOMETRY",
    "LOAD.BALANCE.CONTACT.PHYSICS", "POSE.WEIGHT.CONTACT", "CAMERA.GEOMETRY",
    "MOTION.BLUR.COHERENCE", "LIGHT.SHADOW.REFLECTION", "MATERIAL.TEXTURE.REALISM",
    "BACKGROUND.SCALE.DEPTH", "CROP.FRAME.INTEGRITY", "ARTIFACT.TEXT.LOGO.CONTROL",
    "AESTHETIC.COHERENCE", "SCENE.UNIQUENESS", "USER.INTENT.MATCH", "VISUAL.READBACK",
]


def validate(gate_doc, connector_receipt, queue_failure_receipt, queue_runtime_receipt):
    results = []

    def check(name, condition, detail):
        results.append({"gate": name, "state": "PASS" if condition else "FAIL", "detail": detail})

    bindings = gate_doc.get("runtime_receipt_bindings", {})
    check(
        "G1.IDENTIFIER.AND.RECEIPT.BINDING.LOCK",
        gate_doc.get("identifier") == "FR0333.IMAGE.QUALITY.GATE.0004"
        and connector_receipt.get("identifier") == "FR0333.ADOBE.IMAGE.RUNTIME.RECEIPT.0001"
        and queue_failure_receipt.get("identifier") == "FR0333.ADOBE.IMAGE.QUEUE.RUNTIME.RECEIPT.0002"
        and queue_runtime_receipt.get("identifier") == "FR0333.ADOBE.IMAGE.QUEUE.RUNTIME.RECEIPT.0003"
        and bindings.get("connector_runtime") == "RavenCloudTaskbar/fr0333_adobe_image_runtime_receipt_0001.json"
        and bindings.get("queue_failure_historical") == "RavenCloudTaskbar/fr0333_adobe_image_queue_runtime_receipt_0002.json"
        and bindings.get("queue_runtime_bounded") == "RavenCloudTaskbar/fr0333_adobe_image_queue_runtime_receipt_0003.json",
        "0004 binds connector, historical failure, and current bounded runtime witnesses",
    )

    ref = gate_doc.get("reference_scale", {})
    check(
        "G2.QUALITY.REFERENCE.LOCK",
        ref.get("percent_symbols_prohibited") is True and ref.get("minimum_promotable_reference") == 8,
        "0-9 quality reference with minimum promotable reference 8",
    )

    queue = gate_doc.get("queue_contract", {})
    check(
        "G3.QUEUE.CARDINALITY.CONTRACT",
        queue.get("requested_count_must_equal_delivered_count") is True
        and queue.get("one_slot_one_canvas_one_image") is True
        and queue.get("independent_9_16_canvas_per_slot") is True
        and queue.get("max_user_queue") == 10
        and queue.get("collage") == "REJECT"
        and queue.get("contact_sheet") == "REJECT"
        and queue.get("multi_panel") == "REJECT"
        and queue.get("completion_claim_requires_all_slots_present") is True,
        "ten-slot completion requires ten independent full-canvas outputs",
    )

    caps = gate_doc.get("provider_batch_caps", {})
    generate = caps.get("IMAGE_GENERATE", {})
    edit = caps.get("IMAGE_INSTRUCT_EDIT", {})
    check(
        "G4.OBSERVED.EFFECTIVE.CONNECTOR.CAPS",
        generate.get("state") == "T.20.BOUNDED_EFFECTIVE_CONNECTOR_CAP"
        and generate.get("schema_n_max") == 4
        and generate.get("max_variations_per_call") == 1
        and generate.get("ten_slot_chunk_plan") == [1] * 10
        and generate.get("ten_slot_provider_call_count") == 10
        and edit.get("state") == "T.20.BOUNDED_EFFECTIVE_CONNECTOR_CAP"
        and edit.get("schema_n_max") == 4
        and edit.get("max_variations_per_call") == 1
        and edit.get("ten_slot_chunk_plan") == [1] * 10
        and edit.get("ten_slot_provider_call_count") == 10
        and caps.get("schema_cap_ne_effective_runtime_cap") is True,
        "public n schema permits four while connected runtime is observed singleton for both operations",
    )

    compile_gate = gate_doc.get("prompt_compile", {})
    globals_ = set(compile_gate.get("global_lock_fields", []))
    variations = set(compile_gate.get("per_slot_variation_required", []))
    check(
        "G5.PROMPT.COMPILE.UNIQUENESS",
        {"TARGET_RATIO_9_16", "PHOTOREAL_HUMAN", "NATURAL_ANATOMY", "NO_COLLAGE"}.issubset(globals_)
        and {"SCENERY", "WARDROBE", "POSE_OR_ACTION", "CAMERA_POSITION", "LIGHTING_SETUP", "COMPOSITION"}.issubset(variations),
        "global realism locks remain separate from required per-slot variation",
    )

    human = gate_doc.get("human_realism_gate", {})
    required_human = set(human.get("human_subject_request_requires", []))
    check(
        "G6.HUMAN.REALISM.GATE",
        {"CORRECT_LIMB_COUNT", "JOINT_CONTINUITY", "PLAUSIBLE_WEIGHT_BEARING", "NATURAL_HAND_FINGER_STRUCTURE", "NATURAL_FOOT_TOE_STRUCTURE"}.issubset(required_human)
        and human.get("rubber_limb_or_fused_body_geometry") == "REJECT"
        and human.get("floating_or_impossible_contact") == "REJECT"
        and human.get("mannequin_or_plastic_skin") == "REJECT",
        "human outputs retain anatomy/contact/skin gates",
    )

    mode = gate_doc.get("mode_gate", {})
    check(
        "G7.MODE.SEPARATION",
        mode.get("edit_ne_regenerate") is True
        and mode.get("remaster_ne_reinvent") is True
        and mode.get("remake_multiple_inputs") == "ONE_OUTPUT_PER_INPUT_INDEPENDENT",
        "edit, remaster, and independent remake remain distinct",
    )

    check(
        "G8.ADDITIVE.PHOTOREALISM.DIMENSIONS",
        gate_doc.get("photorealism_dimensions") == EXPECTED_DIMENSIONS
        and set(gate_doc.get("preserved_from_0003", [])) == {"VEHICLE.MECHANICAL.GEOMETRY", "LOAD.BALANCE.CONTACT.PHYSICS"},
        "sixteen dimensions preserve inherited vehicle and contact physics controls",
    )

    defaults = gate_doc.get("adobe_execution_defaults", {})
    check(
        "G9.ADOBE.DIMENSION.NORMALIZATION.DEFAULTS",
        defaults.get("generation_prompt_reasoner") == "quality"
        and defaults.get("target_aspect_ratio") == "9:16"
        and defaults.get("requested_generation_width") == 1080
        and defaults.get("observed_native_generation_width") == 1072
        and defaults.get("observed_native_generation_height") == 1920
        and defaults.get("delivery_width") == 1080
        and defaults.get("delivery_height") == 1920
        and defaults.get("dimension_normalization_operation") == "image_crop_and_resize"
        and defaults.get("post_normalization_visual_readback") == "REQUIRED",
        "native 1072x1920 observation is normalized and visually re-read before exact 1080x1920 delivery",
    )

    promo = gate_doc.get("promotion_gate", {})
    threshold_fields = [
        "identity_reference_min", "anatomy_reference_min", "vehicle_geometry_reference_min",
        "physics_reference_min", "pose_contact_reference_min", "camera_geometry_reference_min",
        "lighting_reference_min", "material_realism_reference_min", "crop_reference_min",
        "artifact_control_reference_min", "aesthetic_reference_min", "scene_uniqueness_reference_min",
        "user_intent_reference_min",
    ]
    check(
        "G10.PROMOTION.THRESHOLDS",
        all(promo.get(field, -1) >= 8 for field in threshold_fields)
        and promo.get("visual_readback_required") is True
        and promo.get("user_reject_overrides_promotion") is True,
        "technical runtime pass does not bypass quality or user acceptance",
    )

    recovery = gate_doc.get("failure_recovery", {})
    check(
        "G11.FAILURE.RECOVERY",
        recovery.get("SILENT_EMPTY_OUTPUT") == "FAIL_AND_RETRY_SLOT"
        and recovery.get("CARDINALITY_MISMATCH") == "FAIL_AND_RETRY_MISSING_SLOTS"
        and recovery.get("EXACT_DIMENSION_DRIFT") == "NORMALIZE_THEN_READBACK_OR_FAIL_AFFECTED_SLOT_ONLY"
        and recovery.get("INTENT_ALIGNMENT_DRIFT") == "FAIL_AFFECTED_SLOT_ONLY"
        and recovery.get("MAX_RETRY_PER_SLOT") == 2
        and recovery.get("no_silent_success") is True,
        "dimension drift is normalized; semantic failures retry only affected slots",
    )

    hard = set(gate_doc.get("hard_boundaries", []))
    check(
        "G12.HARD.BOUNDARIES",
        "TEN.REQUESTED = TEN.DELIVERED" in hard
        and "CURRENT.EFFECTIVE.CONNECTOR.OUTPUTS.PER.CALL = 1" in hard
        and "NATIVE.1072x1920 -> NORMALIZE -> 1080x1920" in hard
        and "RETRY.FAILED.SLOT != REGENERATE.SUCCESSFUL.SLOTS" in hard
        and "TEN.SLOT.RUNTIME.PASS != UNIVERSAL.ADOBE.PRODUCT.CAPACITY" in hard
        and "USER.REJECT = OUTPUT.HOLD" in hard,
        "cardinality, singleton cap, normalization, retry isolation, scope, and HumanLock boundaries are explicit",
    )

    provider = connector_receipt.get("provider_receipt", {})
    connector_result = connector_receipt.get("result", {})
    check(
        "G13.CONNECTOR.RUNTIME.WITNESS",
        provider.get("execution_state") == "PASS_RUNTIME"
        and bool(provider.get("request_id"))
        and connector_result.get("connector_runtime") == "T.20.PASS",
        "authenticated Adobe connector execution remains independently witnessed",
    )

    historical_readback = queue_failure_receipt.get("visual_readback", {})
    historical_result = queue_failure_receipt.get("result", {})
    check(
        "G14.HISTORICAL.FAILURE.PRESERVED",
        historical_readback.get("contact_sheet_or_collage_detected") is True
        and historical_result.get("queue_contract") == "F.6.FAIL",
        "historical contact-sheet failure remains preserved and is not rewritten by later success",
    )

    runtime_result = queue_runtime_receipt.get("result", {})
    queue_doc = queue_runtime_receipt.get("queue", {})
    cap_doc = queue_runtime_receipt.get("effective_connector_caps", {})
    dim_doc = queue_runtime_receipt.get("dimension_observation", {})
    check(
        "G15.BOUNDED.TEN.SLOT.EXTERNAL.RUNTIME",
        queue_doc.get("requested_count") == 10
        and queue_doc.get("final_delivered_count") == 10
        and queue_doc.get("final_unique_slots") == 10
        and queue_doc.get("final_visual_readback") == "PASS"
        and queue_doc.get("retried_slots") == ["Q09"]
        and cap_doc.get("ten_slot_dispatch_plan") == [1] * 10
        and dim_doc.get("observed_native_generation_size") == [1072, 1920]
        and dim_doc.get("normalized_delivery_size") == [1080, 1920]
        and runtime_result.get("ten_slot_generate_runtime") == "T.20.PASS.BOUNDED"
        and runtime_result.get("exact_1080_1920_after_normalization") == "T.20.PASS.BOUNDED",
        "real provider queue completed ten final exact slots after singleton dispatch, normalization, readback, and Q09-only retry",
    )

    route = gate_doc.get("golden_chain_route", [])
    check(
        "G16.HUMANLOCK.AND.SCOPE.BOUNDARY",
        gate_doc.get("humanlock") is True
        and "CHOMP" in route
        and route.count("CHOMP") == 2
        and runtime_result.get("fr0333_adobe_image_tested_surface") == "T.20.PASS.BOUNDED"
        and runtime_result.get("universal_adobe_surface") == "U.21.HOLD",
        "tested FR0333 Adobe image surface passes bounded while universal Adobe capacity and promotion remain held",
    )

    passed = sum(item["state"] == "PASS" for item in results)
    return {
        "identifier": "FR0333.GENIUS.IMAGE.QUALITY.RUNTIME.0004",
        "state": "PASS" if passed == len(results) else "FAIL",
        "passed": passed,
        "total": len(results),
        "invariant": "SIXTEEN.IN -> SIXTEEN.OUT",
        "results": results,
    }


def main():
    paths = [GATE_PATH, RECEIPT_PATH, QUEUE_FAILURE_PATH, QUEUE_RUNTIME_PATH]
    for i, arg in enumerate(sys.argv[1:5]):
        paths[i] = pathlib.Path(arg)
    docs = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    report = validate(*docs)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["state"] == "PASS" else 1)


if __name__ == "__main__":
    main()
