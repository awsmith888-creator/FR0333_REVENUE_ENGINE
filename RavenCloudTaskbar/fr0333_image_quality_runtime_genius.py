#!/usr/bin/env python3
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
GATE_PATH = HERE / "fr0333_image_quality_gate_0003.json"
RECEIPT_PATH = HERE / "fr0333_adobe_image_runtime_receipt_0001.json"

EXPECTED_DIMENSIONS = [
    "IDENTITY.FIDELITY",
    "ANATOMY.FACE.HANDS",
    "VEHICLE.MECHANICAL.GEOMETRY",
    "LOAD.BALANCE.CONTACT.PHYSICS",
    "CAMERA.GEOMETRY",
    "MOTION.BLUR.COHERENCE",
    "LIGHT.SHADOW.REFLECTION",
    "MATERIAL.TEXTURE.REALISM",
    "BACKGROUND.SCALE.DEPTH",
    "CROP.FRAME.INTEGRITY",
    "ARTIFACT.TEXT.LOGO.CONTROL",
    "AESTHETIC.COHERENCE",
    "USER.INTENT.MATCH",
    "VISUAL.READBACK",
]


def validate(gate_doc, receipt_doc):
    results = []

    def check(name, condition, detail):
        results.append({"gate": name, "state": "PASS" if condition else "FAIL", "detail": detail})

    check(
        "G1.IDENTIFIER.LOCK",
        gate_doc.get("identifier") == "FR0333.IMAGE.QUALITY.GATE.0003"
        and receipt_doc.get("identifier") == "FR0333.ADOBE.IMAGE.RUNTIME.RECEIPT.0001",
        "quality gate and bounded runtime receipt identifiers",
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
        "G3.QUEUE.CONTRACT",
        queue.get("n_in_equals_n_out") is True
        and queue.get("one_run_one_canvas_one_image") is True
        and queue.get("independent_9_16_canvas_per_slot") is True
        and queue.get("collage") == "REJECT"
        and queue.get("duplicate_output") == "REJECT"
        and queue.get("count_mismatch") == "REJECT",
        "N_IN equals N_OUT with independent one-image 9:16 canvases",
    )

    mode = gate_doc.get("mode_gate", {})
    check(
        "G4.MODE.SEPARATION",
        mode.get("edit_ne_regenerate") is True
        and mode.get("remaster_ne_reinvent") is True
        and mode.get("remake_multiple_inputs") == "ONE_OUTPUT_PER_INPUT_INDEPENDENT",
        "edit, remaster, remake, and generation modes remain distinct",
    )

    check(
        "G5.PHOTOREALISM.DIMENSIONS",
        gate_doc.get("photorealism_dimensions") == EXPECTED_DIMENSIONS,
        "14 ordered photorealism dimensions including anatomy, mechanics, physics, and readback",
    )

    defaults = gate_doc.get("adobe_execution_defaults", {})
    check(
        "G6.ADOBE.QUALITY.DEFAULTS",
        defaults.get("generation_prompt_reasoner") == "quality"
        and defaults.get("edit_prompt_reasoner") == "quality"
        and defaults.get("target_resolution_level") == "4MP"
        and defaults.get("output_format") == "png"
        and defaults.get("post_edit_visual_readback") == "REQUIRED",
        "Adobe image path uses quality reasoner, 4MP target, PNG, and readback",
    )

    promo = gate_doc.get("promotion_gate", {})
    threshold_fields = [
        "identity_reference_min",
        "anatomy_reference_min",
        "vehicle_geometry_reference_min",
        "physics_reference_min",
        "camera_geometry_reference_min",
        "lighting_reference_min",
        "material_realism_reference_min",
        "crop_reference_min",
        "artifact_control_reference_min",
        "aesthetic_reference_min",
        "user_intent_reference_min",
    ]
    check(
        "G7.PROMOTION.THRESHOLDS",
        all(promo.get(field, -1) >= 8 for field in threshold_fields)
        and promo.get("visual_readback_required") is True
        and promo.get("user_reject_overrides_promotion") is True,
        "all promotable quality references meet or exceed 8 and user rejection holds output",
    )

    hard = set(gate_doc.get("hard_boundaries", []))
    check(
        "G8.REALISM.BOUNDARIES",
        "PHOTOREALISTIC.STYLE != PHYSICALLY.COHERENT" in hard
        and "TONE.IMPROVEMENT != STRUCTURAL.REALISM.REPAIR" in hard
        and "ADOBE.CONNECTOR.SUCCESS != USER.ACCEPTANCE" in hard
        and "USER.REJECT = OUTPUT.HOLD" in hard,
        "provider success and photorealistic appearance cannot substitute for physical coherence or user acceptance",
    )

    provider = receipt_doc.get("provider_receipt", {})
    check(
        "G9.ADOBE.RUNTIME.WITNESS",
        provider.get("execution_state") == "PASS_RUNTIME"
        and bool(provider.get("request_id"))
        and str(provider.get("output_asset_id", "")).startswith("urn:aaid:ps:"),
        "authenticated Adobe edit invocation returned a provider request and output asset receipt",
    )

    readback = receipt_doc.get("readback", {})
    check(
        "G10.READBACK.HOLD",
        readback.get("input_preview_observed") is True
        and readback.get("output_preview_observed") is True
        and readback.get("quality_promotion_state") == "U.21.HOLD"
        and readback.get("user_acceptance") == "NOT_OBSERVED",
        "single runtime edit was read back but not promoted without quality evidence and user acceptance",
    )

    result = receipt_doc.get("result", {})
    check(
        "G11.FULL.CAPACITY.BOUNDARY",
        result.get("connector_runtime") == "T.20.PASS"
        and result.get("photorealism_promotion") == "U.21.HOLD"
        and result.get("external_adobe_full_capacity") == "NOT_ESTABLISHED",
        "single Adobe execution proves bounded connector runtime only, not full production capacity",
    )

    check(
        "G12.HUMANLOCK.CAMERA.BINDING",
        gate_doc.get("humanlock") is True
        and gate_doc.get("camera_gate_binding") == "FR.0333.ADOBE.CAMERA.3.3.3.0001",
        "HumanLock and camera 3.3.3 remain bound",
    )

    passed = sum(item["state"] == "PASS" for item in results)
    return {
        "identifier": "FR0333.GENIUS.IMAGE.QUALITY.RUNTIME.0003",
        "state": "PASS" if passed == len(results) else "FAIL",
        "passed": passed,
        "total": len(results),
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
