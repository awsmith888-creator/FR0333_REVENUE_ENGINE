"""FR0333 whole-system statistical anti-hallucination hardener v4.

This module does not retrain a model.  It validates dated statistical claim
fixtures before they may be used by the four-kernel operator route.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List


KERNELS = ("NEWSFLASH", "ESPN.FANTASY.SPORTS", "NELSON", "GENIUS.BAR")
LANES = {"CULTURE", "SPORTS", "ART", "NEWS", "MEASUREMENT"}
STATES = {"T.20", "U.21", "F.6"}
RELATIONS = {"OBSERVED", "DERIVED", "CORRELATED", "CAUSAL"}


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"not numeric: {value!r}") from exc


def _iso_day(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _distinct_nonempty(values: Iterable[Any]) -> bool:
    values = list(values)
    return bool(values) and all(v not in (None, "") for v in values) and len(values) == len(set(values))


def _source_gate(record: Dict[str, Any], reference_day: date) -> bool:
    try:
        accessed = _iso_day(record["accessed_at"])
    except (KeyError, TypeError, ValueError):
        return False
    return (
        record.get("source_id") not in (None, "")
        and str(record.get("url", "")).startswith("https://")
        and record.get("publisher") not in (None, "")
        and record.get("lane") in LANES
        and record.get("evidence_class") in {
            "PRIMARY.INSTITUTIONAL",
            "PRIMARY.LEAGUE",
            "INDEPENDENT.SECONDARY",
        }
        and accessed <= reference_day
        and record.get("access_state") in {"ACCESSIBLE", "BLOCKED.JS", "CONFLICTING.PAGE"}
    )


def _evaluate_claim(
    claim: Dict[str, Any], source_by_id: Dict[str, Dict[str, Any]], reference_day: date
) -> Dict[str, Any]:
    source_ids = claim.get("source_ids", [])
    sources_exist = bool(source_ids) and all(sid in source_by_id for sid in source_ids)
    state_valid = claim.get("state") in STATES
    relation_valid = claim.get("relation") in RELATIONS
    lane_valid = claim.get("lane") in LANES
    unit_present = claim.get("unit") not in (None, "")

    period_valid = False
    try:
        period_start = _iso_day(claim["period_start"])
        period_end = _iso_day(claim["period_end"])
        period_valid = period_start <= period_end <= reference_day
    except (KeyError, TypeError, ValueError):
        pass

    no_future_event = claim.get("event_status") != "FINAL" or period_valid
    blocked_source_promoted = any(
        source_by_id[sid].get("access_state") != "ACCESSIBLE" for sid in source_ids if sid in source_by_id
    ) and claim.get("state") == "T.20"
    causal_bounded = claim.get("relation") != "CAUSAL" or (
        claim.get("state") != "T.20" or claim.get("causal_design") in {"RANDOMIZED", "QUASI.EXPERIMENTAL"}
    )
    cross_lane_promotion = claim.get("promotes_lane") not in (None, claim.get("lane"))

    passed = all(
        (
            sources_exist,
            state_valid,
            relation_valid,
            lane_valid,
            unit_present,
            period_valid,
            no_future_event,
            not blocked_source_promoted,
            causal_bounded,
            not cross_lane_promotion,
        )
    )
    return {
        "claim_id": claim.get("claim_id"),
        "passed": passed,
        "sources_exist": sources_exist,
        "period_valid": period_valid,
        "blocked_source_promoted": blocked_source_promoted,
        "causal_bounded": causal_bounded,
        "cross_lane_promotion": cross_lane_promotion,
    }


def _evaluate_derivation(derivation: Dict[str, Any]) -> Dict[str, Any]:
    inputs = derivation.get("inputs", [])
    operator = derivation.get("operator")
    try:
        numbers = [_decimal(x) for x in inputs]
        declared = _decimal(derivation.get("declared_result"))
        if operator == "SUM":
            recomputed = sum(numbers, Decimal("0"))
        elif operator == "DIFFERENCE":
            recomputed = numbers[0] - numbers[1]
        elif operator == "RATIO.PERCENT":
            recomputed = (numbers[0] / numbers[1] * Decimal("100")).quantize(Decimal("0.01"))
        elif operator == "MAXIMUM.SELECTION.PERCENT":
            # A denominator recorded as a lower bound yields a maximum rate.
            recomputed = (numbers[0] / numbers[1] * Decimal("100")).quantize(Decimal("0.01"))
        else:
            raise ValueError("unsupported operator")
        passed = recomputed == declared
        return {
            "derivation_id": derivation.get("derivation_id"),
            "passed": passed,
            "recomputed": str(recomputed),
            "declared": str(declared),
        }
    except (IndexError, ValueError, ZeroDivisionError):
        return {
            "derivation_id": derivation.get("derivation_id"),
            "passed": False,
            "recomputed": None,
            "declared": str(derivation.get("declared_result")),
        }


def _evaluate_scoreboard(board: Dict[str, Any], reference_day: date) -> Dict[str, Any]:
    games: List[Dict[str, Any]] = board.get("games", [])
    game_ids = [g.get("game_id") for g in games]
    finals = [g for g in games if g.get("status") == "FINAL"]
    scores_valid = all(
        isinstance(g.get("away_score"), int)
        and isinstance(g.get("home_score"), int)
        and g.get("away_score") >= 0
        and g.get("home_score") >= 0
        for g in finals
    )
    dates_valid = True
    for game in finals:
        try:
            if _iso_day(game["event_date"]) > reference_day:
                dates_valid = False
        except (KeyError, TypeError, ValueError):
            dates_valid = False
    recomputed_points = sum(g["away_score"] + g["home_score"] for g in finals if scores_valid)
    declared = board.get("declared", {})
    checks = {
        "GAME.IDS.UNIQUE": _distinct_nonempty(game_ids),
        "FINAL.SCORES.NONNEGATIVE.INTEGER": scores_valid,
        "FINAL.DATES.NOT.FUTURE": dates_valid,
        "FINAL.COUNT.RECOMPUTES": declared.get("final_count") == len(finals),
        "TOTAL.POINTS.RECOMPUTE": declared.get("total_points") == recomputed_points,
    }
    return {
        "board_id": board.get("board_id"),
        "passed": all(checks.values()),
        "checks": checks,
        "final_count": len(finals),
        "total_points": recomputed_points,
    }


def _evaluate_negative_control(control: Dict[str, Any], reference_day: date) -> Dict[str, Any]:
    reasons = []
    try:
        displayed_start = _iso_day(control["displayed_start"])
        if displayed_start > reference_day:
            reasons.append("FUTURE.DISPLAYED.DATE")
    except (KeyError, TypeError, ValueError):
        reasons.append("INVALID.DISPLAYED.DATE")
    if control.get("requested_week") != control.get("displayed_week"):
        reasons.append("WEEK.LABEL.MISMATCH")
    if control.get("access_state") != "ACCESSIBLE":
        reasons.append("SOURCE.NOT.FULLY.ACCESSIBLE")
    expected = set(control.get("expected_reasons", []))
    detected = set(reasons)
    return {
        "control_id": control.get("control_id"),
        "passed": bool(detected) and expected.issubset(detected),
        "decision": "HOLD" if detected else "INVALID.NEGATIVE.CONTROL",
        "reasons": sorted(detected),
    }


def evaluate_statistical_hardener_v4(fixture: Dict[str, Any]) -> Dict[str, Any]:
    reference_day = _iso_day(fixture["reference_point"])
    kernels = fixture.get("kernels", {})
    kernel_gate = set(kernels) == set(KERNELS) and all(kernels.get(k) == "PASS" for k in KERNELS)

    sources = fixture.get("sources", [])
    source_ids = [source.get("source_id") for source in sources]
    source_gate = _distinct_nonempty(source_ids) and all(_source_gate(s, reference_day) for s in sources)
    source_by_id = {s["source_id"]: s for s in sources if s.get("source_id")}

    claim_results = [_evaluate_claim(c, source_by_id, reference_day) for c in fixture.get("claims", [])]
    derivation_results = [_evaluate_derivation(d) for d in fixture.get("derivations", [])]
    scoreboard_results = [_evaluate_scoreboard(b, reference_day) for b in fixture.get("scoreboards", [])]
    negative_results = [
        _evaluate_negative_control(c, reference_day) for c in fixture.get("negative_controls", [])
    ]

    gates = {
        "FOUR.KERNEL.1111": kernel_gate,
        "SOURCE.PROVENANCE.AND.DATE": source_gate,
        "CLAIM.UNIT.PERIOD.STATE": bool(claim_results) and all(x["passed"] for x in claim_results),
        "DERIVATION.RECOMPUTATION": bool(derivation_results) and all(x["passed"] for x in derivation_results),
        "SPORTS.SCOREBOARD.RECOMPUTATION": bool(scoreboard_results) and all(x["passed"] for x in scoreboard_results),
        "NEGATIVE.CONTROL.DETECTED": bool(negative_results) and all(x["passed"] for x in negative_results),
        "LANE.CAUSALITY.FIREWALL": all(
            not x["cross_lane_promotion"] and x["causal_bounded"] for x in claim_results
        ),
        "HUMANLOCK.ACTIVE": fixture.get("humanlock") == "ACTIVE"
        and fixture.get("automatic_promotion") is False,
    }
    return {
        "record_id": "FR0333.SYSTEM.STATISTICAL.ANTI.HALLUCINATION.HARDENER.0004",
        "predecessor_record_id": "FR0333.OPERATOR.FOUR.KERNEL.UPGRADE.0003",
        "reference_point": fixture["reference_point"],
        "kernel_bitword": "1111" if kernel_gate else "HOLD",
        "gates": gates,
        "claims": claim_results,
        "derivations": derivation_results,
        "scoreboards": scoreboard_results,
        "negative_controls": negative_results,
        "decision": "OPEN" if all(gates.values()) else "HOLD",
        "humanlock": "ACTIVE",
        "automatic_promotion": False,
        "base_model_weights": "UNCHANGED",
        "evidence_axiom": "OBSERVED!=DERIVED!=CORRELATED!=CAUSAL",
    }
