#!/usr/bin/env python3
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
GATE_PATH = HERE / "fr0333_image_quality_gate_0004.json"
RECEIPT_PATH = HERE / "fr0333_adobe_image_runtime_receipt_0001.json"

EXPECTED_DIMENSIONS = [
    "IDENTITY.FIDELITY",
    "ANATOMY.FACE.HANDS.FEET",
    "POSE.WEIGHT.CONTACT",
    "CAMERA.GEOMETRY",
    "MOTION.BLUR.COHERENCE",
    "LIGHT.SHADOW.REFLECTION",
    "MATERIAL.TEXTURE.REALISM",
    "BACKGROUND.SCALE.DEPTH",
    "CROP.FRAME.INTEGRITY",
    "ARTIFACT.TEXT.LOGO.CONTROL",
    "AESTHETIC.COHERENCE",
    "SCENE.UNIQUENESS",
    "USER.INTENT.MATCH",
    "VISUAL.READBACK",
]


def validate(gate_doc, receipt_doc):
    results = []

    def check(name, condition, detail):
        results.append({"gate": name, "state": "PASS" if condition else "FAIL", "detail": detail})

    check(
        "G1.IDENTIFIER.LOCK",
        gate_doc.get("identifier") == "FR0333.IMAGE.QUALITY.GATE.0004"
        and gate_doc.get("supersedes") == "FR0333.IMAGE.QUALITY.GATE.0003"
        and receipt_doc.get("identifier") == "FR0333.ADOBE.IMAGE.RUNTIME.RECEIPT.0001",
        "0004 supersedes 0003 while retaining the bounded Adobe runtime witness",
    )

    ref = gate_doc.get("reference_scale", {})
    check(
        "G2.QUALITY.REFERENCE.LOCK",
        ref.get("percent_symbols_prohibited") is True
        and ref.get("minimum_promotable_reference") == 8,
        "0-9 quality reference with minimum promotable reference 8",
    )

    queue = gate_doc.get("queue_contract", {})
    check(
        "G3.QUEUE.CARDINALITY.CONTRACT",
        queue.get("requested_count_must_equal_delivered_count") is True
        and queue.get("one_slot_one_canvas_one_image") is True
        and queue.get("independent_9_16_canvas_per_slot") is True
        and queue.get("max_user_queue") == 10
        and queue.get("slot_ids_required") is True
        and queue.get("slot_receipt_required") is True
        and queue.get("collage") == "REJECT"
        and queue.get("contact_sheet") == "REJECT"
        and queue.get("multi_panel") == "REJECT"
        and queue.get("duplicate_output") == "REJECT"
        and queue.get("count_mismatch") == "REJECT"
        and queue.get("completion_claim_requires_all_slots_present") is True,
        "ten-slot queues cannot promote unless every independent 9:16 slot exists",
    )

    caps = gate_doc.get("provider_batch_caps", {})
    chunk_plan = caps.get("TEN_SLOT_CHUNK_PLAN", [])
    provider_max = caps.get("ADOBE_FIREFLY_IMAGE_GENERATE_MAX_VARIATIONS_PER_CALL")
    check(
        "G4.PROVIDER.CAP.CHUNK.PLAN",
        provider_max == 4
        and chunk_plan == [4, 4, 2]
        and sum(chunk_plan) == 10
        and all(0 < x <= provider_max for x in chunk_plan)
        and caps.get("successful_slots_must_not_be_regenerated") is True,
        "ten outputs are split into Firefly-compatible 4+4+2 execution chunks",
    )

    compile_gate = gate_doc.get("prompt_compile", {})
    globals_ = set(compile_gate.get("global_lock_fields", []))
    variations = set(compile_gate.get("per_slot_variation_required", []))
    check(
        "G5.PROMPT.COMPILE.UNIQUENESS",
        {"TARGET_RATIO_9_16", "PHOTOREAL_HUMAN", "NATURAL_ANATOMY", "NO_COLLAGE"}.issubset(globals_)
        and {"SCENERY", "WARDROBE", "POSE_OR_ACTION", "CAMERA_POSITION", "LIGHTING_SETUP", "COMPOSITION"}.issubset(variations)
        and bool(compile_gate.get("slot_uniqueness_rule")),
        "global realism locks stay constant while scenery, wardrobe, pose, camera, lighting, and composition vary per slot",
    )

    human = gate_doc.get("human_realism_gate", {})
    required_human = set(human.get("human_subject_request_requires", []))
    check(
        "G6.HUMAN.REALISM.GATE",
        {"CORRECT_LIMB_COUNT", "JOINT_CONTINUITY", "PLAUSIBLE_WEIGHT_BEARING", "NATURAL_HAND_FINGER_STRUCTURE", "NATURAL_FOOT_TOE_STRUCTURE"}.issubset(required_human)
        and human.get("clone_face_across_unrelated_people") == "REJECT"
        and human.get("rubber_limb_or_fused_body_geometry") == "REJECT"
        and human.get("floating_or_impossible_contact") == "REJECT"
        and human.get("mannequin_or_plastic_skin") == "REJECT",
        "human outputs require plausible anatomy, contact, skin, hands, and feet",
    )

    mode = gate_doc.get("mode_gate", {})
    check(
        "G7.MODE.SEPARATION",
        mode.get("edit_ne_regenerate") is True
        and mode.get("remaster_ne_reinvent") is True
        and mode.get("remake_multiple_inputs") == "ONE_OUTPUT_PER_INPUT_INDEPENDENT"
        and mode.get("concept_reference_total_remake") == "GENERATE_DISTINCT_NEW_SCENES_WITH_CONCEPT_LOCK",
        "edit, remaster, independent remake, and concept-reference total remake remain distinct",
    )

    check(
        "G8.PHOTOREALISM.DIMENSIONS",
        gate_doc.get("photorealism_dimensions") == EXPECTED_DIMENSIONS,
        "14 ordered dimensions include face/hands/feet, pose/contact, scene uniqueness, and readback",
    )

    defaults = gate_doc.get("adobe_execution_defaults", {})
    check(
        "G9.ADOBE.QUALITY.DEFAULTS",
        defaults.get("generation_prompt_reasoner") == "quality"
        and defaults.get("edit_prompt_reasoner") == "quality"
        and defaults.get("target_aspect_ratio") == "9:16"
        and defaults.get("target_resolution_level") == "4MP"
        and defaults.get("output_format") == "png"
        and defaults.get("post_generation_visual_readback") == "REQUIRED"
        and defaults.get("post_edit_visual_readback") == "REQUIRED",
        "Adobe execution defaults are quality-first, 9:16, 4MP, PNG, and readback-bound",
    )

    promo = gate_doc.get("promotion_gate", {})
    threshold_fields = [
        "anatomy_reference_min", "pose_contact_reference_min", "camera_geometry_reference_min",
        "lighting_reference_min", "material_realism_reference_min", "crop_reference_min",
        "artifact_control_reference_min", "aesthetic_reference_min", "scene_uniqueness_reference_min",
        "user_intent_reference_min",
    ]
    check(
        "G10.PROMOTION.THRESHOLDS",
        all(promo.get(field, -1) >= 8 for field in threshold_fields)
        and promo.get("visual_readback_required") is True
        and promo.get("queue_cardinality_required") is True
        and promo.get("user_reject_overrides_promotion") is True,
        "quality, uniqueness, cardinality, readback, and user acceptance all gate promotion",
    )

    recovery = gate_doc.get("failure_recovery", {})
    check(
        "G11.FAILURE.RECOVERY",
        recovery.get("SILENT_EMPTY_OUTPUT") == "FAIL_AND_RETRY_SLOT"
        and recovery.get("CARDINALITY_MISMATCH") == "FAIL_AND_RETRY_MISSING_SLOTS"
        and recovery.get("PROVIDER_ERROR") == "RETRY_ONCE_THEN_REPORT_HOLD"
        and recovery.get("MAX_RETRY_PER_SLOT") == 2
        and recovery.get("no_silent_success") is True,
        "empty/partial outputs cannot silently pass and recovery targets missing slots only",
    )

    hard = set(gate_doc.get("hard_boundaries", []))
    check(
        "G12.HARD.BOUNDARIES",
        "TEN.REQUESTED = TEN.DELIVERED" in hard
        and "ONE.SLOT = ONE.IMAGE = ONE.FULL.9.16.CANVAS" in hard
        and "PARTIAL.SUCCESS != QUEUE.SUCCESS" in hard
        and "EMPTY.RESPONSE != SUCCESS" in hard
        and "HUMAN.LOOKING != HUMAN.ANATOMY.PASS" in hard
        and "USER.REJECT = OUTPUT.HOLD" in hard,
        "cardinality, one-canvas, empty response, anatomy, and HumanLock boundaries are explicit",
    )

    provider = receipt_doc.get("provider_receipt", {})
    check(
        "G13.ADOBE.RUNTIME.WITNESS",
        provider.get("execution_state") == "PASS_RUNTIME"
        and bool(provider.get("request_id"))
        and str(provider.get("output_asset_id", "")).startswith("urn:aaid:ps:"),
        "prior authenticated Adobe runtime witness remains bounded evidence",
    )

    readback = receipt_doc.get("readback", {})
    check(
        "G14.READBACK.HOLD",
        readback.get("input_preview_observed") is True
        and readback.get("output_preview_observed") is True
        and readback.get("quality_promotion_state") == "U.21.HOLD"
        and readback.get("user_acceptance") == "NOT_OBSERVED",
        "prior runtime witness remains held without user acceptance",
    )

    result = receipt_doc.get("result", {})
    check(
        "G15.FULL.CAPACITY.BOUNDARY",
        result.get("connector_runtime") == "T.20.PASS"
        and result.get("photorealism_promotion") == "U.21.HOLD"
        and result.get("external_adobe_full_capacity") == "NOT_ESTABLISHED",
        "bounded connector runtime does not establish ten-slot production capacity",
    )

    check(
        "G16.HUMANLOCK.CAMERA.BINDING",
        gate_doc.get("humanlock") is True
        and gate_doc.get("camera_gate_binding") == "FR.0333.ADOBE.CAMERA.3.3.3.0001",
        "HumanLock and camera 3.3.3 remain bound",
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
    gate_path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else GATE_PATH
    receipt_path = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else RECEIPT_PATH
    gate_doc = json.loads(gate_path.read_text(encoding="utf-8"))
    receipt_doc = json.loads(receipt_path.read_text(encoding="utf-8"))
    report = validate(gate_doc, receipt_doc)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["state"] == "PASS" else 1)


if __name__ == "__main__":
    main()
