#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC_PATH = ROOT / "fr0333_sports_bits_bones_0001.json"


def load_spec():
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def validate():
    spec = load_spec()

    assert spec["id"] == "FR0333.SPORTS.BITS.BONES.0001"
    assert spec["state"] == "PROMOTED.WORKING.SPEC.REFERENCE_POINT_VALIDATED"
    assert spec["source_fixture"]["independent_verification"] == "NOT_ESTABLISHED"

    refs = {row["reference_id"]: row for row in spec["reference_points"]}
    assert set(refs) == {
        "RP.01.CURRENT.GAME",
        "RP.02.COMPLETED.ROWS",
        "RP.03.NEXT.GAME",
        "RP.04.MEDIA.VIDEO",
    }

    current = refs["RP.01.CURRENT.GAME"]
    assert current["game_state"] == "ONGOING"
    assert current["final_result"] == "UNKNOWN"
    assert current["terminal_state"] == "U.21.HOLD"
    assert current["score_observed"] == {"mets": 3, "yankees": 0}
    assert current["inning"] == "UNKNOWN"

    completed = refs["RP.02.COMPLETED.ROWS"]
    rows = completed["completed_games"]
    mets_wins = sum(1 for row in rows if row["winner"] == "METS")
    yankees_wins = sum(1 for row in rows if row["winner"] == "YANKEES")
    assert len(rows) == 4
    assert mets_wins == 2
    assert yankees_wins == 2
    assert completed["derived_completed_record"] == {
        "mets_wins": mets_wins,
        "yankees_wins": yankees_wins,
    }
    assert completed["derivation_class"] == "DERIVED_FROM_PROVIDED_ROWS_ONLY"

    future = refs["RP.03.NEXT.GAME"]
    assert future["result"] == "NOT_YET_OBSERVED"
    assert future["terminal_state"] == "U.21.HOLD"

    media = refs["RP.04.MEDIA.VIDEO"]
    assert media["views_observed"] == 165000
    assert media["metric_class"] == "MEDIA.VIEWS"
    assert media["tv_ratings"] == "UNKNOWN"
    assert media["total_game_reach"] == "UNKNOWN"

    boundaries = set(spec["evidence_boundaries"])
    required = {
        "SCREENSHOT.OBSERVED != INDEPENDENT.VERIFICATION",
        "ONGOING.SCORE != FINAL.RESULT",
        "VIDEO.VIEWS != TV.RATINGS",
        "VIDEO.VIEWS != TOTAL.GAME.REACH",
        "SCHEDULED.EVENT != COMPLETED.EVENT",
        "UNKNOWN != ZERO != PASS",
        "DERIVED.RECORD != SOURCE.REPORTED.RECORD",
    }
    assert required.issubset(boundaries)

    control = spec["terminal_control"]
    assert control["specification"] == "T.20.PASS"
    assert control["current_game_final"] == "U.21.HOLD"
    assert control["next_game_result"] == "U.21.HOLD"
    assert control["tv_audience"] == "U.21.HOLD"
    assert control["external_runtime"] == "NOT_CLAIMED"

    return {
        "result": "T.20.PASS",
        "rail": spec["id"],
        "reference_points": len(refs),
        "completed_rows": len(rows),
        "derived_record": "METS.2.YANKEES.2",
        "current_game_final": "U.21.HOLD",
        "tv_audience": "U.21.HOLD",
        "runtime_claim": "NONE",
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
