from typing import Any, Dict

KERNELS = (("K1", "NEWSFLASH"), ("K2", "ESPN.FANTASY.SPORTS"), ("K3", "NELSON"), ("K4", "GENIUS.BAR"))
CORE_GATES = (
    "SOURCE.TIMESTAMP", "FORMULA.LABEL.MATCH", "NUMERATOR.DENOMINATOR.MATCH", "SAMPLE.SIZE",
    "NELSON.KERNEL.RECEIPT", "FAILURE.REPAIR.RECEIPT", "ROLLBACK.PATH",
    "NELSON.ROLE.DEFINED", "MEASUREMENT.SOURCE.BOUND", "MEASUREMENT.PERIOD.BOUND", "COMPARISON.SCOPE.BOUND",
)
ADOBE_GATES = ("EXACT.9.16", "IDENTITY.PRESERVATION", "EDIT.LOCALITY", "NO.EXTRA.TEXT", "ONE.INPUT.ONE.OUTPUT")


def _nonempty(value: Any) -> bool:
    return value not in (None, "", [], {})


def _validate_nelson(transaction: Dict[str, Any]) -> Dict[str, Any]:
    receipt = transaction.get("kernels", {}).get("NELSON", {}).get("receipt", {})
    measurement = transaction.get("nelson_measurement", {})
    sources = measurement.get("source_receipts", [])
    metrics = measurement.get("measurements", [])
    groups = measurement.get("comparison_groups", [])
    stats = transaction.get("statistics", {})

    source_ids = {s.get("source_id") for s in sources if s.get("source_id")}
    periods = {m.get("measurement_period") for m in metrics if m.get("measurement_period")}
    programs = {m.get("program") for m in metrics if m.get("program")}

    role_defined = (
        receipt.get("role") == "USER.DEFINED.MEASUREMENT.KERNEL"
        and receipt.get("status") == "DEFINED.ACTIVE"
        and receipt.get("measurement_contract") == "SOURCE+PERIOD+METRIC+UNIT+SCOPE+RECEIPT"
    )
    sources_bound = len(sources) >= 2 and all(
        _nonempty(s.get("source_id"))
        and _nonempty(s.get("publisher"))
        and _nonempty(s.get("underlying_measurement"))
        and _nonempty(s.get("evidence_class"))
        and _nonempty(s.get("measurement_period"))
        and str(s.get("url", "")).startswith("https://")
        for s in sources
    )
    metrics_bound = len(metrics) >= 4 and all(
        _nonempty(m.get("program"))
        and _nonempty(m.get("measurement_period"))
        and _nonempty(m.get("metric"))
        and isinstance(m.get("value"), (int, float))
        and _nonempty(m.get("unit"))
        and m.get("source_id") in source_ids
        for m in metrics
    )
    declared_counts_match = (
        int(stats.get("source_count", -1)) == len(sources)
        and int(stats.get("metric_count", -1)) == len(metrics)
        and int(stats.get("program_count", -1)) == len(programs)
        and int(stats.get("measurement_period_count", -1)) == len(periods)
    )

    expected_evening = {"ABC.WORLD.NEWS.TONIGHT", "NBC.NIGHTLY.NEWS", "CBS.EVENING.NEWS"}
    evening_groups = [
        g for g in groups
        if g.get("group_id") == "EVENING.NEWS.WEEKLY.2026.08.31" and g.get("comparable") is True
    ]
    comparable_scope = False
    if len(evening_groups) == 1:
        group = evening_groups[0]
        programs_in_group = set(group.get("programs", []))
        period = group.get("measurement_period")
        comparable_scope = programs_in_group == expected_evening and period == "WEEK.OF.2026.08.31"
        if comparable_scope:
            for program in expected_evening:
                keys = {
                    (m.get("metric"), m.get("unit"))
                    for m in metrics
                    if m.get("program") == program and m.get("measurement_period") == period
                }
                if ("TOTAL.VIEWERS", "VIEWERS") not in keys or ("A25.54.VIEWERS", "VIEWERS") not in keys:
                    comparable_scope = False
                    break

    context_groups = [g for g in groups if g.get("group_id") == "CONTEXT.60.MINUTES.SEASON.2025.26"]
    context_isolated = (
        len(context_groups) == 1
        and context_groups[0].get("comparable") is False
        and context_groups[0].get("context_only") is True
        and measurement.get("cross_period_ranking_allowed") is False
    )
    pending_held = all(str(c.get("state", "")).startswith("U.21") for c in measurement.get("pending_claims", []))

    passed = all((
        role_defined, sources_bound, metrics_bound, declared_counts_match,
        comparable_scope, context_isolated, pending_held,
    ))
    return {
        "passed": passed,
        "role_defined": role_defined,
        "sources_bound": sources_bound,
        "metrics_bound": metrics_bound,
        "declared_counts_match": declared_counts_match,
        "comparison_scope_bound": comparable_scope,
        "cross_period_context_isolated": context_isolated,
        "pending_claims_held": pending_held,
        "source_receipt_count": len(sources),
        "measurement_count": len(metrics),
        "program_count": len(programs),
        "measurement_period_count": len(periods),
    }


def evaluate_four_kernel_transaction_v2(transaction: Dict[str, Any]) -> Dict[str, Any]:
    nelson = _validate_nelson(transaction)
    results = {}
    bits = []
    for _, name in KERNELS:
        record = transaction.get("kernels", {}).get(name, {})
        passed = bool(record.get("passed")) and _nonempty(record.get("receipt"))
        if name == "NELSON":
            passed = passed and nelson["passed"]
        results[name] = {"passed": passed, "receipt_present": bool(record.get("receipt"))}
        bits.append("1" if passed else "0")
    bitword = "".join(bits)

    core = {gate: bool(transaction.get("core_gates", {}).get(gate)) for gate in CORE_GATES}
    core["NELSON.ROLE.DEFINED"] = core["NELSON.ROLE.DEFINED"] and nelson["role_defined"]
    core["MEASUREMENT.SOURCE.BOUND"] = core["MEASUREMENT.SOURCE.BOUND"] and nelson["sources_bound"] and nelson["metrics_bound"]
    core["MEASUREMENT.PERIOD.BOUND"] = core["MEASUREMENT.PERIOD.BOUND"] and nelson["declared_counts_match"]
    core["COMPARISON.SCOPE.BOUND"] = core["COMPARISON.SCOPE.BOUND"] and nelson["comparison_scope_bound"] and nelson["cross_period_context_isolated"]

    adobe = {gate: bool(transaction.get("adobe_gates", {}).get(gate)) for gate in ADOBE_GATES}
    adobe_receipt = _nonempty(transaction.get("adobe_execution_receipt"))
    s = transaction.get("statistics", {})
    stats = {
        "kernel_count": 4,
        "active_kernel_count": sum(v["passed"] for v in results.values()),
        "kernel_pass_rate": sum(v["passed"] for v in results.values()) / 4.0,
        "kernel_bitword": bitword,
        "decimal_state": int(bitword, 2),
        "required_core_gate_count": len(CORE_GATES),
        "passed_core_gate_count": sum(core.values()),
        "core_gate_pass_rate": sum(core.values()) / len(CORE_GATES),
        "required_adobe_gate_count": len(ADOBE_GATES),
        "passed_adobe_gate_count": sum(adobe.values()),
        "adobe_gate_pass_rate": sum(adobe.values()) / len(ADOBE_GATES),
        "source_count": int(s.get("source_count", 0)),
        "metric_count": int(s.get("metric_count", 0)),
        "sample_size": int(s.get("sample_size", 0)),
        "program_count": int(s.get("program_count", 0)),
        "measurement_period_count": int(s.get("measurement_period_count", 0)),
        "comparable_program_count": int(s.get("comparable_program_count", 0)),
        "contradiction_count": int(s.get("contradiction_count", 0)),
        "repair_attempt_count": int(s.get("repair_attempt_count", 0)),
        "repair_success_count": int(s.get("repair_success_count", 0)),
        "truth_t20_count": int(s.get("truth_t20_count", 0)),
        "truth_u21_count": int(s.get("truth_u21_count", 0)),
        "truth_f6_count": int(s.get("truth_f6_count", 0)),
    }

    operator_open = bitword == "1111" and all(core.values())
    adobe_open = operator_open and all(adobe.values()) and adobe_receipt
    return {
        "record_id": "FR0333.OPERATOR.FOUR.KERNEL.UPGRADE.0002",
        "predecessor_record_id": "FR0333.OPERATOR.FOUR.KERNEL.UPGRADE.0001",
        "architecture_id": "FR0333.ADOBE.FOUR.KERNEL.HARDENER.0001",
        "kernels": results,
        "nelson_measurement_gate": nelson,
        "core_gates": core,
        "adobe_gates": adobe,
        "statistics": stats,
        "operator_route": "OPEN" if operator_open else "HOLD",
        "adobe_route": "OPEN" if adobe_open else "HOLD",
        "adobe_live_traversal_receipt": "T.20" if adobe_receipt else "U.21",
        "humanlock": "ACTIVE",
        "base_model_weights": "UNCHANGED",
        "platform_permissions": "UNCHANGED",
        "cross_period_ranking": "F.6",
    }
