import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CORRECTION = ROOT / "fr0333_reference_monitoring_correction_0003.json"
CENSUS = ROOT / "fr0333_census_black_detailed_origin_0001.json"

VALID_ALPHA_REF = re.compile(r"^[A-Z](?:[.]?)(?:[1-9]|1[0-9]|2[0-6])$")
FORBIDDEN_27 = {"AA27", "AA.27", "A27", "A.27"}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    correction = load(CORRECTION)
    census = load(CENSUS)

    p27 = correction["reference_frame"]["POSITION.27"]
    assert p27["role"] == "HUMANLOCK.CONTINUATION"
    assert p27["binding_type"] == "NUMERIC.POSITION.ONLY"
    assert p27["alphabetic_symbol"] is None
    assert p27["requires_human_authorization"] is True
    assert p27["automatic_role_inheritance"] is False

    assert correction["census_correction"]["invalid_positional_token"] == "AA27"
    assert correction["census_correction"]["observation_preserved"]["source_row"] == "ACS.ROW.07"

    refs = []
    for group in (
        "metrics_2020_dhc_a_alone_or_in_any_combination",
        "usvi_2020_island_area_metrics",
        "acs_2024_black_alone_selected_groups",
    ):
        for row in census.get(group, []):
            ref = row.get("reference_point")
            if ref:
                refs.append(ref)

    # Existing AA27 remains historical evidence in 0001, but cannot be promoted
    # as a valid reference-frame identity under correction 0003.
    for ref in refs:
        if ref in FORBIDDEN_27:
            continue
        assert VALID_ALPHA_REF.fullmatch(ref), f"invalid active alphabetic reference: {ref}"

    assert "AA27" in refs, "expected historical contradiction is missing"
    assert "AA27_REJECT" in correction["hard_invariants"]
    assert "POST_Z_LETTER_BINDING_REJECT" in correction["hard_invariants"]
    assert correction["promotion"]["merge"] == "USER_REVIEW_REQUIRED"
    assert correction["promotion"]["deployment"] == "NOT_AUTHORIZED"

    print("REFERENCE_FRAME_0003_PASS")
    print("Z26=HUMANLOCK.BOUNDARY")
    print("POSITION27=HUMANLOCK.CONTINUATION.NUMERIC_ONLY")
    print("AA27=QUARANTINED_HISTORICAL_TOKEN")
    print("ACS.ROW.07=JAMAICAN_OBSERVATION_PRESERVED")


if __name__ == "__main__":
    main()
