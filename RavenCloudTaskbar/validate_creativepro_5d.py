#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "RavenCloudTaskbar" / "fr0333_creativepro_adobe_5d_index.json"
GOOGLE_INDEX = ROOT / "RavenCloudTaskbar" / "FR0333_GOOGLE_CLOUD_FREE_INDEX_0002.txt"
GOOGLE_POINTERS = ROOT / "RavenCloudTaskbar" / "FR0333_GOOGLE_CLOUD_FREE_POINTERS_0002.json"

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
    "CRYPTOGRAPHIC_VALIDITY_NE_HUMAN_IDENTITY_NE_AUTHORIZATION",
    "ABSENT_NE_INVALID_NE_CONFLICTING_NE_SUSPICIOUS_NE_PROVEN_FALSE",
    "MISSING_NE_ZERO",
    "HOLD_NE_PASS",
    "DEFINED_NE_CI_VALIDATED_NE_RUNTIME_PROVEN",
    "DETECTOR_FAILURE_NE_SYNTHETIC_EVIDENCE",
    "BYTE_MISMATCH_NE_TAMPER",
    "RATING_NE_AVERAGE_AUDIENCE_NE_REACH",
    "TV_AUDIENCE_NE_APP_USERS_NE_WEBSITE_USERS",
    "WEATHER_IMPORTANCE_NE_FORECAST_ACCURACY",
    "FORECAST_COMPREHENSION_NE_FORECAST_ACCURACY",
    "PRICE_LISTING_VERIFIED_NE_TRANSACTION_OBSERVED",
    "OBSERVED_NE_MEASURED_NE_DERIVED_NE_INFERRED_NE_CLAIMED",
    "OBSERVED_NE_CORRELATED_NE_CAUSAL",
    "NO_CROSS_RAIL_PROMOTION_WITHOUT_EVIDENCE",
    "REQUESTED_OUTPUT_COUNT_EQ_UNIQUE_OUTPUT_ASSET_COUNT",
    "UNREQUESTED_COLLAGE_NE_VALID_MULTI_OUTPUT_BATCH",
    "IDENTITY_LOCK_REQUIRES_SOURCE_ANCHOR",
    "OUTPUT_ID_REUSE_NE_SEPARATE_ASSET",
}
REQUIRED_RUNTIME_STATES = {
    "PASS_RUNTIME", "PASS_SPEC", "HOLD", "FAIL", "UNKNOWN",
    "NOT_OBSERVED", "NOT_APPLICABLE", "CONFLICT", "ABSENT",
    "INVALID", "SUSPICIOUS", "PROVEN_FALSE"
}
REQUIRED_EVIDENCE_CLASSES = {"E_OBS", "E_MES", "E_DER", "E_INF", "E_CLM"}
REQUIRED_VALUE_STATES = {
    "PRESENT", "ABSENT", "UNKNOWN", "NOT_APPLICABLE", "INVALID",
    "CONFLICTING", "SUSPICIOUS", "PROVEN_FALSE"
}
REQUIRED_5D_KEYS = {"X", "Y", "Z", "P", "T", "rule"}
REQUIRED_IMAGE_HARDENING = {
    "requested_output_count_must_equal_unique_isolated_output_count",
    "identity_locked_generation_requires_explicit_source_anchor",
}
EXPECTED_GOOGLE_VALUES = [
    "300", "90", "20", "30", "28", "9", "1", "180000",
    "50", "360000", "100", "400", "20", "2", "512", "1",
    "10", "2500", "1", "100", "10000", "50", "1000000", "5000",
    "2000000", "360000", "180000", "1", "2000000", "400000", "200000", "5",
    "5", "5", "50", "50", "5", "5000", "50000", "100",
    "1000", "1", "30", "1", "3", "100", "1", "50000",
    "20000", "20000", "10", "1", "10", "10000", "6", "10000",
    "3", "60", "1000", "100000", "5000", "2000", "5000", "350000",
]


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def validate_google_register() -> None:
    if not GOOGLE_INDEX.exists():
        fail("Google Cloud numeric index missing")
    if not GOOGLE_POINTERS.exists():
        fail("Google Cloud pointer map missing")

    lines = [line.strip() for line in GOOGLE_INDEX.read_text(encoding="utf-8").splitlines()]
    if not lines or lines[0] != "FR.0333.GOOGLE.CLOUD.FREE.INDEX.0002":
        fail("unexpected Google Cloud index header")

    numeric_lines: list[str] = []
    for line in lines[1:]:
        if line == "64.64":
            break
        if line:
            numeric_lines.append(line)

    if len(numeric_lines) != 64:
        fail(f"Google Cloud register must contain 64 numeric positions; got {len(numeric_lines)}")

    for position, (line, expected_value) in enumerate(zip(numeric_lines, EXPECTED_GOOGLE_VALUES), start=1):
        prefix = f"{position:02d}."
        if not line.startswith(prefix):
            fail(f"Google Cloud position {position:02d} malformed: {line}")
        raw_value = line[len(prefix):]
        if not raw_value or any(part == "" or not part.isdigit() for part in raw_value.split(".")):
            fail(f"Google Cloud position {position:02d} is not dotted numeric data: {line}")
        compact = raw_value.replace(".", "")
        if compact != expected_value:
            fail(f"Google Cloud position {position:02d} value mismatch: {compact} != {expected_value}")

    if "STATE.LOCKED" not in lines or "DECIMAL.COLLISION.RETIRED" not in lines:
        fail("Google Cloud index lock markers missing")

    pointer_data = json.loads(GOOGLE_POINTERS.read_text(encoding="utf-8"))
    if pointer_data.get("index") != "FR.0333.GOOGLE.CLOUD.FREE.INDEX.0002":
        fail("Google pointer map index binding mismatch")
    pointers = pointer_data.get("pointers", {})
    if len(pointers) != 64:
        fail(f"Google pointer map must bind 64 positions; got {len(pointers)}")

    for position, expected_value in enumerate(EXPECTED_GOOGLE_VALUES, start=1):
        key = f"{position:02d}"
        row = pointers.get(key)
        if not row:
            fail(f"Google pointer missing position {key}")
        if str(row.get("value")) != expected_value:
            fail(f"Google pointer value mismatch at {key}")
        if not row.get("metric") or not row.get("unit") or not row.get("source"):
            fail(f"Google pointer incomplete at {key}")

    artifact = pointers["15"]
    if artifact.get("source_value") != "0.5_GiB":
        fail("Artifact Registry source decimal must remain explicit")
    if artifact.get("derivation") != "0.5_x_1024_MiB_per_GiB":
        fail("Artifact Registry 512 MiB derivation missing")


def main() -> None:
    data = json.loads(INDEX.read_text(encoding="utf-8"))

    if data.get("version") != "1.2.1-RC":
        fail(f"unexpected version: {data.get('version')}")

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

    evidence_classes = set(data.get("evidence_classes", {}))
    if evidence_classes != REQUIRED_EVIDENCE_CLASSES:
        fail(f"evidence class mismatch: {sorted(evidence_classes)}")

    value_states = set(data.get("value_states", []))
    if value_states != REQUIRED_VALUE_STATES:
        fail(f"value-state mismatch: {sorted(value_states)}")

    coord = data.get("coordinate_5d", {})
    if set(coord) != REQUIRED_5D_KEYS:
        fail(f"5D coordinate mismatch: {sorted(coord)}")

    calibration = data.get("calibration_5d", {})
    for key in (
        "immutable_receipt_fields", "metric_identity_fields", "applicability_rule",
        "zero_state_rule", "revision_rule", "detector_rule", "tamper_rule"
    ):
        if key not in calibration:
            fail(f"calibration_5d missing {key}")

    if calibration.get("metric_identity_fields") != ["metric_name", "numerator", "denominator"]:
        fail("metric identity must preserve numerator and denominator")

    weather = data.get("weather_transfer_learning", {})
    if weather.get("promotion_effect") != "NONE_ON_ADOBE_RUNTIME_PROOF":
        fail("weather evidence must not promote Adobe runtime proof")
    if weather.get("human_importance_bones") != 8:
        fail("weather human-importance bones must remain 8")
    if weather.get("human_statistical_bits") != 16:
        fail("weather statistical bits must remain 16")
    if weather.get("five_d_weather_bits") != 20:
        fail("weather 5D bit count must remain 20")

    alignment = data.get("adobe_64bit_alignment", {})
    if alignment.get("register") != "FR-0333-ADOBE-64BIT-REG":
        fail("Adobe 64-bit register binding missing")
    if alignment.get("clusters") != 8 or alignment.get("bits") != 64:
        fail("Adobe register must remain 8 clusters / 64 bits")
    if alignment.get("semantic_fixes") != 8:
        fail("Adobe semantic fix count must be exactly 8")
    hardening = alignment.get("critical_hardening", [])
    if len(hardening) != 8 or len(set(hardening)) != 8:
        fail("Adobe critical hardening must contain 8 unique fixes")
    if not REQUIRED_IMAGE_HARDENING.issubset(set(hardening)):
        fail("Adobe image-output hardening invariants missing")

    image_contract = data.get("image_production_contract", {})
    if image_contract.get("promotion_effect") != "NONE_ON_CREDENTIAL_BACKED_ADOBE_RUNTIME_PROOF":
        fail("image contract cannot promote Adobe runtime proof")
    for key in (
        "single_asset_rule", "batch_rule", "collage_rule", "identity_rule",
        "output_reuse_rule", "default_master"
    ):
        if not image_contract.get(key):
            fail(f"image production contract missing {key}")

    google = data.get("google_cloud_free_pointer", {})
    if google.get("index") != "FR.0333.GOOGLE.CLOUD.FREE.INDEX.0002":
        fail("Google Cloud pointer index mismatch")
    if google.get("pointer_only") is not True:
        fail("Google Cloud crosswalk must remain pointer-only")
    if google.get("promotion_effect") != "NONE_ON_ADOBE_RUNTIME_PROOF":
        fail("Google Cloud pointer cannot promote Adobe runtime proof")
    if google.get("artifact_registry_decimal_resolution") != "0.5_GiB_EQUALS_512_MiB":
        fail("Artifact Registry decimal collision resolution missing")

    coverage = data.get("coverage", {})
    if coverage.get("target") != 1.0:
        fail("coverage.target must remain 1.0")
    if coverage.get("spec_formula") != "defined_required_controls / required_controls":
        fail("unexpected spec coverage formula")
    if coverage.get("runtime_formula") != "runtime_pass_controls / applicable_runtime_controls":
        fail("unexpected runtime coverage formula")

    rule = coverage.get("rule", "")
    for token in (
        "HOLD", "UNKNOWN", "NOT_OBSERVED", "CONFLICT", "FAIL",
        "NOT_APPLICABLE", "ABSENT", "INVALID", "SUSPICIOUS", "PROVEN_FALSE"
    ):
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
    required_genius = {
        "summit_member_price_advantage_usd": 125,
        "membership_cost_usd": 78,
        "net_savings_if_membership_bought_only_for_one_qualifying_125_discount_usd": 47,
        "google_trial_credit_usd": 300,
        "google_trial_days": 90,
        "google_agent_runtime_vcpu_seconds_per_month": 180000,
        "google_agent_runtime_hours_per_month": 50,
        "google_cloud_run_requests_per_month": 2000000,
        "google_kms_active_key_versions_per_month": 100,
        "google_kms_crypto_operations_per_month": 10000,
        "google_artifact_registry_free_mib_per_month": 512,
    }
    for key, expected in required_genius.items():
        if gs.get(key) != expected:
            fail(f"Genius statistic mismatch for {key}: {gs.get(key)} != {expected}")
    if gs.get("google_pointer_promotion_effect") != "NONE_ON_ADOBE_RUNTIME_PROOF":
        fail("Genius Google pointer cannot promote Adobe runtime proof")

    zero = data.get("runtime_zero_state", {})
    for key in (
        "adobe_credential_runtime", "external_image_generation_runtime",
        "artifact_provenance_runtime"
    ):
        if zero.get(key) != "HOLD":
            fail(f"runtime zero-state must remain HOLD for {key}")

    total_controls = sum(len(d["required_controls"]) for d in dims.values())
    if total_controls != 40:
        fail(f"required control count must remain 40; got {total_controls}")

    validate_google_register()

    print("FR0333.CREATIVEPRO.ADOBE.5D.HARDENER.001")
    print(f"version={data.get('version')}")
    print(f"dimensions={len(dims)}/5")
    print(f"required_controls={total_controls}/40")
    print(f"system_lanes={len(lanes)}/10")
    print(f"statistics_rows={len(stats)}")
    print("evidence_classes=5/5")
    print("value_states=8/8")
    print("coordinate_5d=X.Y.Z.P.T")
    print("adobe_64bit=64/64")
    print("adobe_semantic_fixes=8/8")
    print("image_isolation_contract=BOUND")
    print("google_cloud_free_index=64/64")
    print("google_cloud_pointers=64/64")
    print("artifact_registry_decimal_collision=RESOLVED_TO_512_MiB")
    print("runtime_proof=HOLD")
    print("coverage_semantics=EXPLICIT_DENOMINATOR_AND_APPLICABILITY_REQUIRED")
    print("state=PASS_SPEC_STRUCTURE_V1_2_1_RC")


if __name__ == "__main__":
    main()
