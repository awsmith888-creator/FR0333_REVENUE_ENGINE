from typing import Any, Dict, List


def evaluate_observability_hardener(tx: Dict[str, Any]) -> Dict[str, Any]:
    release_state = tx.get("release_state")
    source_chain = tx.get("source_chain", [])
    workflow_graph = tx.get("workflow_graph", {})
    analytics = tx.get("analytics_plane", {})
    actions = tx.get("agent_actions", [])
    telemetry = tx.get("telemetry", {})
    cross_device = tx.get("cross_device_context", {})
    vendor_metrics = tx.get("vendor_metrics", [])

    source_chain_valid = bool(source_chain) and source_chain[0].get("class") == "DISCOVERY_POINTER"
    primary_present = any(s.get("class") == "FIRST_PARTY" for s in source_chain)
    release_state_valid = release_state in {"ANNOUNCED", "PREORDER", "BETA", "PRODUCTION"}
    beta_not_promoted = not (
        release_state in {"ANNOUNCED", "PREORDER", "BETA"}
        and tx.get("production_capability_established") is True
    )

    graph_valid = (
        bool(workflow_graph.get("nodes"))
        and bool(workflow_graph.get("edges"))
        and workflow_graph.get("visualization_is_ground_truth") is False
    )

    analytics_isolated = (
        analytics.get("mode") in {"SNAPSHOT", "REPLICA"}
        and analytics.get("production_mutation_allowed") is False
    )

    action_gate_valid = all(
        action.get("access") in {"READ", "WRITE", "EXECUTE"}
        and (
            action.get("access") == "READ"
            or action.get("human_approval_required") is True
        )
        for action in actions
    )

    telemetry_valid = all(
        key in telemetry for key in ("run_id", "step_ids", "errors", "latency_ms", "tool_calls")
    ) and telemetry.get("unobserved_severe_events", 1) == 0

    cross_device_valid = (
        cross_device.get("enabled") is False
        or (
            bool(cross_device.get("source_device"))
            and bool(cross_device.get("permission_scope"))
            and cross_device.get("implicit_merge_allowed") is False
        )
    )

    vendor_metrics_bounded = all(
        metric.get("classification") in {"VENDOR_REPORTED", "INDEPENDENT", "OFFICIAL_RECORD"}
        and not (
            metric.get("classification") == "VENDOR_REPORTED"
            and metric.get("state") == "T.20.INDEPENDENT.BENCHMARK"
        )
        for metric in vendor_metrics
    )

    gates = {
        "source_chain_valid": source_chain_valid,
        "primary_present": primary_present,
        "release_state_valid": release_state_valid,
        "beta_not_promoted": beta_not_promoted,
        "workflow_graph_valid": graph_valid,
        "analytics_isolated": analytics_isolated,
        "agent_action_gate_valid": action_gate_valid,
        "telemetry_complete": telemetry_valid,
        "cross_device_context_bounded": cross_device_valid,
        "vendor_metrics_bounded": vendor_metrics_bounded,
    }

    failures: List[str] = []
    if not source_chain_valid or not primary_present:
        failures.append("PROVENANCE_GAP")
    if not release_state_valid or not beta_not_promoted:
        failures.append("RELEASE_STATE_COLLAPSE")
    if not graph_valid:
        failures.append("WORKFLOW_GRAPH_GAP")
    if not analytics_isolated:
        failures.append("ANALYTICS_PLANE_BREACH")
    if not action_gate_valid:
        failures.append("AGENT_ACTION_AUTHORITY_BREACH")
    if not telemetry_valid:
        failures.append("OBSERVABILITY_GAP")
    if not cross_device_valid:
        failures.append("CROSS_DEVICE_CONTEXT_LEAK")
    if not vendor_metrics_bounded:
        failures.append("VENDOR_METRIC_OVERPROMOTION")

    return {
        "record_id": tx.get("record_id"),
        "route": "PASS" if all(gates.values()) else "HOLD",
        "gates": gates,
        "failure_classes": failures,
        "invariants": {
            "discovery_pointer_ne_evidence": True,
            "beta_ne_production": True,
            "visualization_ne_ground_truth": True,
            "vendor_metric_ne_independent_benchmark": True,
            "write_or_execute_requires_human_approval": True,
            "analytics_plane_ne_production_mutation": True,
        },
    }
