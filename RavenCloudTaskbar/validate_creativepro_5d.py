#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "RavenCloudTaskbar" / "fr0333_creativepro_adobe_5d_index.json"

EXPECTED_DIMENSIONS = {
    "D1_SOURCE_AUTHORITY",
    "D2_PRODUCTION_WORKFLOW",
    "D3_FORENSICS_RIGHTS",
    "D4_ATTENTION_NETWORK",
    "D5_ECONOMIC_RUNTIME",
}
REQUIRED_GATES = {
    "100_PERCENT_MEANS_REQUIRED_LANE_COVERAGE_NOT_INFALLIBILITY",
    "FOLLOWER_COUNT_NE_TECHNICAL_AUTHORITY",
    "SOURCE_COUNT_NE_INDEPENDENT_SOURCE_COUNT",
    "REPRODUCTION_COUNT_NE_INDEPENDENT_EVIDENCE_COUNT",
    "METADATA_NE_PROVENANCE_NE_AUTHENTICITY_NE_IDENTITY_NE_TRUTH",
    "ACCESS_NE_AUTHORITY",
    "MISSING_NE_ZERO",
    "HOLD_NE_PASS",
    "DEFINED_NE_CI_VALIDATED_NE_RUNTIME_PROVEN",
    "PRICE_LISTING_VERIFIED_NE_TRANSACTION_OBSERVED",
    "OBSERVED_NE_CORRELATED_NE_CAUSAL",
    "STILLNESS_NE_INCAPACITY",
    "NARRATIVE_METAPHOR_NE_BIOLOGICAL_LAW",
    "INTERPRETATION_NE_OBSERVED_FACT",
    "DESTRUCTIVE_RHETORIC_NE_PRODUCTION_INSTRUCTION",
    "QUIET_FRAME_REQUIRES_LATENT_FORCE_SIGNALS",
    "CAPTURE_NE_INTERPRETATION",
    "VISIBLE_OBJECT_NE_IDENTIFIED_OBJECT",
    "TRACKED_OBJECT_NE_IDENTIFIED_PERSON",
    "THERMAL_SIGNATURE_NE_HUMAN_IDENTITY",
    "MEDIA_REPOST_NE_ORIGINAL_CAPTURE",
    "TEXT_OVERLAY_NE_SOURCE_EVIDENCE",
    "VISUAL_CORRELATION_NE_CAUSAL_PROOF",
}
REQUIRED_RUNTIME_STATES = {
    "PASS_RUNTIME", "PASS_SPEC", "HOLD", "FAIL", "UNKNOWN",
    "NOT_OBSERVED", "NOT_APPLICABLE", "CONFLICT"
}
EXPECTED_FIXES = {
    "DF-0001": "ROUTE_ISOLATION_FILTER",
    "DF-0002": "EXPLICIT_BOUNDS_CHECK",
    "DF-0003": "NARROW_CRYPTO_SCOPE",
    "DF-0004": "NON_HUMAN_SIGNATURE_FORCE",
    "DF-0005": "APPLICATION_AUTH_DECOUPLING",
    "DF-0006": "FAIL_CLOSED_VALIDATION",
    "DF-0007": "EXPLICIT_DENOMINATOR_INJECTION",
    "DF-0008": "ANONYMIZED_PURGE_RECEIPT",
}
REQUIRED_QUIET_SIGNALS = {
    "posture_control", "gaze_control", "lighting_hierarchy",
    "environmental_reaction", "perspective_dominance", "prop_control",
    "negative_space_control", "occlusion_tension",
}
EXPECTED_DRONE_BITS = {f"BIT.ADOBE.DRONE.{n:03d}" for n in range(1, 17)}
EXPECTED_VISION_BONE = {
    "CAPTURE_NE_INTERPRETATION",
    "VISIBLE_OBJECT_NE_IDENTIFIED_OBJECT",
    "TRACKED_OBJECT_NE_IDENTIFIED_PERSON",
    "THERMAL_SIGNATURE_NE_HUMAN_IDENTITY",
    "MEDIA_REPOST_NE_ORIGINAL_CAPTURE",
    "TEXT_OVERLAY_NE_SOURCE_EVIDENCE",
    "VISUAL_CORRELATION_NE_CAUSAL_PROOF",
}
EXPECTED_CROSSWALK = {
    "CLUSTER.01.ORIGIN": {1, 3, 4, 5, 8},
    "CLUSTER.02.INTEGRITY": {9, 11, 13},
    "CLUSTER.03.EDIT_HISTORY": {17, 18, 19, 20},
    "CLUSTER.05.RELATIONSHIP": {33, 34, 37},
    "CLUSTER.06.AUTHENTICITY": {41, 42, 43, 44},
    "CLUSTER.08.ENGINE": {57, 59, 60, 61},
}


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def main() -> None:
    data = json.loads(INDEX.read_text(encoding="utf-8"))

    if data.get("version") != "1.3.0":
        fail(f"expected index version 1.3.0; got {data.get('version')}")

    dims = data.get("five_dimensions", {})
    if set(dims) != EXPECTED_DIMENSIONS:
        fail(f"dimension mismatch: {sorted(dims)}")

    for name, block in dims.items():
        controls = block.get("required_controls", [])
        if len(controls) != 8:
            fail(f"{name} must define exactly 8 required controls; got {len(controls)}")
        if len(set(controls)) != len(controls):
            fail(f"{name} contains duplicate controls")

    gates = set(data.get("governing_gates", []))
    missing_gates = REQUIRED_GATES - gates
    if missing_gates:
        fail(f"missing governing gates: {sorted(missing_gates)}")

    coverage = data.get("coverage", {})
    if coverage.get("target") != 1.0:
        fail("coverage.target must remain 1.0")
    if coverage.get("spec_formula") != "defined_required_controls / required_controls":
        fail("unexpected spec coverage formula")
    if coverage.get("runtime_formula") != "runtime_pass_controls / applicable_runtime_controls":
        fail("unexpected runtime coverage formula")

    rule = coverage.get("rule", "")
    for token in ("HOLD", "UNKNOWN", "NOT_OBSERVED", "CONFLICT", "FAIL", "NOT_APPLICABLE"):
        if token not in rule:
            fail(f"coverage.rule must explicitly preserve {token}")

    lanes = data.get("system_lanes", [])
    if len(lanes) != 10 or len(set(lanes)) != 10:
        fail("system_lanes must contain 10 unique lanes")

    states = set(data.get("runtime_state_model", []))
    missing_states = REQUIRED_RUNTIME_STATES - states
    if missing_states:
        fail(f"runtime_state_model missing: {sorted(missing_states)}")

    stats = data.get("creativepro_statistics", [])
    if not stats:
        fail("statistics register must not be empty")
    for row in stats:
        for key in ("metric", "value", "period", "evidence_state", "source"):
            if key not in row:
                fail(f"statistics row missing {key}: {row}")
        if not str(row["source"]).startswith("https://creativepro.com/"):
            fail(f"CreativePro statistics source outside boundary: {row['source']}")

    gs = data.get("genius_statistics", {})
    if gs.get("summit_member_price_advantage_usd") != 125:
        fail("price advantage statistic mismatch")
    if gs.get("membership_cost_usd") != 78:
        fail("membership cost statistic mismatch")
    if gs.get("net_savings_if_membership_bought_only_for_one_qualifying_125_discount_usd") != 47:
        fail("net savings statistic mismatch")

    total_controls = sum(len(d["required_controls"]) for d in dims.values())
    if total_controls != 40:
        fail(f"required control count must remain 40; got {total_controls}")

    bridge = data.get("legacy_registry_bridge", {})
    if bridge.get("source_registry") != "FR-0333-ADOBE-64BIT-REG":
        fail("legacy Adobe registry bridge missing")
    if bridge.get("semantic_fix_state") != "8_OF_8_CLOSED_SPEC":
        fail("semantic fix bridge is not 8/8 CLOSED_SPEC")
    if bridge.get("local_retest_state") != "8_OF_8_PASS_LOCAL":
        fail("semantic fix bridge is not 8/8 PASS_LOCAL")
    if bridge.get("external_adobe_runtime") != "HOLD_UNTIL_CREDENTIAL_BACKED_RECEIPT":
        fail("external Adobe runtime must remain receipt-gated")

    fixes = data.get("semantic_fixes", [])
    if len(fixes) != 8:
        fail(f"expected 8 semantic fixes; got {len(fixes)}")
    fix_map = {row.get("id"): row for row in fixes}
    if set(fix_map) != set(EXPECTED_FIXES):
        fail("semantic fix IDs mismatch")
    for fix_id, expected_after in EXPECTED_FIXES.items():
        row = fix_map[fix_id]
        if row.get("after") != expected_after:
            fail(f"{fix_id} resolution mismatch")
        if row.get("state") != "CLOSED_SPEC" or row.get("retest") != "PASS_LOCAL":
            fail(f"{fix_id} not closed and locally retested")

    narrative = data.get("narrative_power_gate", {})
    if narrative.get("record_id") != "FR.0333.ADOBE.NARRATIVE.POWER.0001":
        fail("narrative power record missing")
    if narrative.get("genius_bit_candidate") != "0016":
        fail("GENIUS bit candidate must remain 0016 until canonical promotion")
    if narrative.get("core_rule") != "STILLNESS_NE_INCAPACITY":
        fail("narrative core rule mismatch")

    verification = narrative.get("source_verification", [])
    verified_states = {row.get("state") for row in verification}
    if "VERIFIED_ATTRIBUTION_AND_SPEECH" not in verified_states or "VERIFIED_LION_SPEECH_CONTEXT" not in verified_states:
        fail("Lion speech attribution/context source verification incomplete")

    boundary = narrative.get("evidence_boundary", {})
    if boundary.get("david_comparison") != "INTERPRETATION":
        fail("David comparison must remain interpretation")
    if boundary.get("genetic_makeup_built_to_destroy") != "QUARANTINED_UNSUPPORTED_BIOLOGICAL_CLAIM":
        fail("unsupported biological claim must remain quarantined")
    if boundary.get("total_eradication") != "QUARANTINED_RHETORICAL_EXAGGERATION":
        fail("eradication rhetoric must remain quarantined")

    quiet = narrative.get("nine_sixteen_quiet_authority_spec", {})
    if quiet.get("target_ratio") != "9:16":
        fail("quiet-authority target ratio must remain 9:16")
    if quiet.get("required_signals") != 3:
        fail("quiet-authority minimum signal count must remain 3")
    if set(quiet.get("eligible_signals", [])) != REQUIRED_QUIET_SIGNALS:
        fail("quiet-authority signal vocabulary mismatch")
    if quiet.get("status") != "PASS_SPEC":
        fail("quiet-authority gate must be PASS_SPEC, not runtime")

    vision_bindings = data.get("vision_family_bindings", {})
    vision = vision_bindings.get("FR.0333.ADOBE.DRONE.VISION.0001")
    if not vision:
        fail("Adobe drone vision binding missing")
    if vision.get("chomp_record") != "FR.0333.CHOMP.ADOBE.DRONE.0001":
        fail("drone vision CHOMP binding mismatch")
    if vision.get("bone_record") != "FR.0333.ADOBE.BONE.VISION.0001":
        fail("drone vision bone binding mismatch")
    if vision.get("upgrade_record") != "FR.0333.ADOBE.5D.UPGRADE.0003":
        fail("drone vision upgrade record mismatch")
    if vision.get("state") != "BOUND_SPEC_EVIDENCE_BOUNDED":
        fail("drone vision family must remain evidence-bounded")

    source_set = {row.get("id"): row for row in vision.get("source_set", [])}
    for required in ("SOURCE.01", "SOURCE.02", "SOURCE.03A", "SOURCE.03B"):
        if required not in source_set:
            fail(f"drone source missing: {required}")
    if source_set["SOURCE.03A"].get("state") != "VERIFIED_CORROBORATION_2026_08_27":
        fail("KOCO corroboration not bound as verified")
    if source_set["SOURCE.03B"].get("state") != "VERIFIED_CORROBORATION_2026_08_27":
        fail("Officer.com corroboration not bound as verified")
    if source_set["SOURCE.02"].get("state") != "USER_SUPPLIED_REFERENCE_DIRECT_FETCH_UNVERIFIED":
        fail("YouTube reference must not be silently promoted")

    incident = vision.get("incident_core", {})
    for key in ("rtic_drone_used", "spotlight_intervention", "post_event_dog_tracking_to_residence"):
        if incident.get(key) != "CORROBORATED":
            fail(f"incident corroboration missing for {key}")
    if incident.get("identity_from_thermal_frame") != "NOT_ESTABLISHED":
        fail("thermal frame identity must remain unestablished")

    drone_bits = vision.get("adobe_bits", [])
    if len(drone_bits) != 16:
        fail(f"expected 16 Adobe drone bits; got {len(drone_bits)}")
    ids = {row.get("id") for row in drone_bits}
    if ids != EXPECTED_DRONE_BITS:
        fail("Adobe drone bit IDs mismatch")
    if len(ids) != len(drone_bits):
        fail("duplicate Adobe drone bit IDs")

    five_d = vision.get("five_d_mapping", {})
    if set(five_d) != {"X", "Y", "Z", "P", "T"}:
        fail("drone vision 5D mapping must populate X/Y/Z/P/T")
    for dim, values in five_d.items():
        if not values:
            fail(f"drone vision dimension {dim} is empty")

    crosswalk = vision.get("register_crosswalk", {})
    if set(crosswalk) != set(EXPECTED_CROSSWALK):
        fail("64-bit crosswalk cluster set mismatch")
    for cluster, expected in EXPECTED_CROSSWALK.items():
        if set(crosswalk.get(cluster, [])) != expected:
            fail(f"64-bit crosswalk mismatch for {cluster}")
        for bit in expected:
            if bit < 1 or bit > 64:
                fail(f"64-bit register index out of range: {bit}")

    bone = set(vision.get("bone_rules", []))
    if bone != EXPECTED_VISION_BONE:
        fail("Adobe vision bone rule set mismatch")

    provenance = vision.get("provenance_gate", {})
    if provenance.get("source_provenance") != "PARTIAL":
        fail("source provenance must remain PARTIAL")
    if provenance.get("original_okcpd_file") != "NOT_INGESTED":
        fail("original OKCPD file must remain NOT_INGESTED")
    if provenance.get("c2pa_manifest") != "UNVERIFIED":
        fail("C2PA manifest must remain UNVERIFIED")
    if provenance.get("adobe_runtime") != "NOT_PROMOTED":
        fail("Adobe runtime must remain NOT_PROMOTED")

    chain = vision.get("bind_chain", [])
    required_chain = ["SOURCE_LOCK","333.CATCH","VISUAL.ATOMIZE","SOURCE.CLASSIFY","5D.ADDRESS","64BIT.CROSSWALK","PROVENANCE.GATE","VISION.MEASUREMENT","CORROBORATION","ADOBE.BONE","CHOMP","STAY"]
    if chain != required_chain:
        fail("drone vision bind chain mismatch")

    print("FR0333.CREATIVEPRO.ADOBE.5D.HARDENER.001")
    print(f"version={data.get('version')}")
    print(f"dimensions={len(dims)}/5")
    print(f"required_controls={total_controls}/40")
    print(f"system_lanes={len(lanes)}/10")
    print(f"statistics_rows={len(stats)}")
    print("semantic_fixes=8/8")
    print("semantic_retests=8/8")
    print("lion_gate=PASS_SPEC")
    print("quiet_authority_signals=8_DEFINED_MIN_3_REQUIRED")
    print("drone_vision_family=BOUND_SPEC_EVIDENCE_BOUNDED")
    print("drone_vision_bits=16/16")
    print("drone_vision_5d=5/5")
    print("drone_vision_64bit_crosswalk_clusters=6/6")
    print("drone_vision_external_corroboration=2/2")
    print("original_okcpd_file=NOT_INGESTED")
    print("c2pa_manifest=UNVERIFIED")
    print("external_adobe_runtime=HOLD_CREDENTIAL_RECEIPT_REQUIRED")
    print("economic_discount_check=125")
    print("economic_net_savings_after_membership=47")
    print("coverage_semantics=EXPLICIT_DENOMINATOR_REQUIRED")
    print("state=PASS_SPEC_STRUCTURE_V1_3")


if __name__ == "__main__":
    main()
