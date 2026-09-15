from typing import Any, Dict, Iterable, Set

from four_kernel_hardener_v2 import evaluate_four_kernel_transaction_v2


ALLOWED_TRUTH_STATES = {"T.20", "U.21", "F.6"}
ALLOWED_AUTHORITY_TIERS = {
    "PRIMARY.GOVERNMENT",
    "PRIMARY.INTERGOVERNMENTAL",
    "PRIMARY.INSTITUTIONAL",
    "PEER_REVIEWED",
    "INDEPENDENT.SECONDARY",
}
ALLOWED_EVIDENCE_CLASSES = {
    "ORIGINAL",
    "INDEPENDENT.CORROBORATION",
    "PEER_REVIEWED",
}
ALLOWED_RELATIONS = {
    "OBSERVED",
    "CORRELATED",
    "CAUSAL",
    "LEGAL_STATUS",
    "DIPLOMATIC_POLICY",
    "INSTITUTIONAL_RECORD",
    "STATISTICAL_DISPARITY",
}

EVIDENCE_GATES = (
    "SOURCE.PROVENANCE.BOUND",
    "CLAIM.SOURCE.BOUND",
    "SOURCE.INDEPENDENCE.BOUND",
    "PRIMARY.AUTHORITY.REQUIRED",
    "OBSERVED.CORRELATED.CAUSAL.SEPARATED",
    "CAUSAL.SCOPE.BOUNDED",
    "ABSOLUTE.LANGUAGE.GUARD",
    "LEGAL.EFFECT.SEPARATED",
    "ENTITY.NORMALIZATION.BOUND",
    "UNRESOLVED.ATTRIBUTION.HELD",
    "HUMAN.PROMOTION.REQUIRED",
)

INTERACTION_GATES = (
    "CHOMP.FREEZE.STAY",
    "COUNT.INVARIANT",
    "SOURCE.SET.PRESERVED",
    "ORDER.PRESERVED",
    "RATIO.PRESERVED",
    "NO.REINTERPRET.ON.CHOMP",
    "NO.EXPANSION.ON.CHOMP",
    "NEW.EXPLICIT.INSTRUCTION.REQUIRED",
)


def _nonempty(value: Any) -> bool:
    return value not in (None, "", [], {})


def _unique_nonempty(values: Iterable[Any]) -> bool:
    values = list(values)
    return bool(values) and all(_nonempty(v) for v in values) and len(values) == len(set(values))


def _source_groups(source_ids: Iterable[str], source_by_id: Dict[str, Dict[str, Any]]) -> Set[str]:
    return {
        str(source_by_id[sid].get("independence_group"))
        for sid in source_ids
        if sid in source_by_id and _nonempty(source_by_id[sid].get("independence_group"))
    }


def _validate_evidence(transaction: Dict[str, Any]) -> Dict[str, Any]:
    e = transaction.get("evidence_hardening", {})
    sources = e.get("source_receipts", [])
    claims = e.get("claims", [])
    rejected = e.get("rejected_absolutes", [])
    normalization = e.get("entity_normalization", {})

    source_ids = [s.get("source_id") for s in sources]
    source_by_id = {s.get("source_id"): s for s in sources if s.get("source_id")}

    source_provenance_bound = (
        len(sources) >= 6
        and _unique_nonempty(source_ids)
        and all(
            _nonempty(s.get("publisher"))
            and s.get("authority_tier") in ALLOWED_AUTHORITY_TIERS
            and s.get("evidence_class") in ALLOWED_EVIDENCE_CLASSES
            and _nonempty(s.get("independence_group"))
            and _nonempty(s.get("jurisdiction"))
            and _nonempty(s.get("accessed_at"))
            and str(s.get("url", "")).startswith("https://")
            for s in sources
        )
    )

    claim_ids = [c.get("claim_id") for c in claims]
    claims_structured = (
        len(claims) >= 8
        and _unique_nonempty(claim_ids)
        and all(
            c.get("state") in ALLOWED_TRUTH_STATES
            and c.get("evidence_relation") in ALLOWED_RELATIONS
            and _nonempty(c.get("scope"))
            and isinstance(c.get("source_ids", []), list)
            for c in claims
        )
    )

    claim_source_bound = claims_structured and all(
        all(sid in source_by_id for sid in c.get("source_ids", []))
        and (c.get("state") != "T.20" or len(c.get("source_ids", [])) >= 1)
        for c in claims
    )

    independence_bound = claims_structured and all(
        (
            not c.get("requires_independent_corroboration", False)
            or c.get("state") != "T.20"
            or len(_source_groups(c.get("source_ids", []), source_by_id)) >= 2
        )
        for c in claims
    )

    primary_relations = {
        "LEGAL_STATUS",
        "DIPLOMATIC_POLICY",
        "INSTITUTIONAL_RECORD",
        "STATISTICAL_DISPARITY",
    }
    primary_tiers = {
        "PRIMARY.GOVERNMENT",
        "PRIMARY.INTERGOVERNMENTAL",
        "PRIMARY.INSTITUTIONAL",
        "PEER_REVIEWED",
    }
    primary_authority_required = claims_structured and all(
        (
            c.get("state") != "T.20"
            or c.get("evidence_relation") not in primary_relations
            or any(
                source_by_id[sid].get("authority_tier") in primary_tiers
                for sid in c.get("source_ids", [])
                if sid in source_by_id
            )
        )
        for c in claims
    )

    relation_separated = claims_structured and all(
        c.get("evidence_relation") in ALLOWED_RELATIONS
        and not (
            c.get("evidence_relation") == "OBSERVED"
            and c.get("causal_scope") not in (None, "NOT.APPLICABLE")
        )
        for c in claims
    )

    causal_scope_bounded = claims_structured and all(
        (
            c.get("evidence_relation") != "CAUSAL"
            or c.get("state") != "T.20"
            or (
                c.get("causal_scope") == "BOUNDED"
                and any(
                    source_by_id[sid].get("authority_tier") == "PEER_REVIEWED"
                    for sid in c.get("source_ids", [])
                    if sid in source_by_id
                )
            )
        )
        for c in claims
    )

    absolute_guard = claims_structured and all(
        not (c.get("state") == "T.20" and c.get("absolute_language") is True)
        for c in claims
    ) and all(r.get("state") == "F.6" for r in rejected)

    unga = next((c for c in claims if c.get("claim_id") == "UNGA.A.RES.80.250.VOTE"), None)
    legal_effect_separated = bool(
        unga
        and unga.get("state") == "T.20"
        and unga.get("evidence_relation") == "LEGAL_STATUS"
        and unga.get("resolution_effect") == "NON_BINDING.GENERAL.ASSEMBLY.RESOLUTION"
        and unga.get("vote_summary") == {"yes": 123, "no": 3, "abstain": 52, "non_voting": 15}
        and set(unga.get("vote_no_states", [])) == {"ARGENTINA", "ISRAEL", "UNITED.STATES"}
    )

    entity_normalization_bound = (
        normalization.get("JERUSALEM") == "ISRAEL"
        and normalization.get("UNITED STATES OF AMERICA") == "UNITED.STATES"
        and unga is not None
        and "JERUSALEM" not in set(unga.get("vote_no_states", []))
    )

    attribution = next((c for c in claims if c.get("claim_id") == "CURRENT.DISPARITY.TOTAL.ATTRIBUTION"), None)
    unresolved_attribution_held = bool(
        attribution
        and attribution.get("state") == "U.21"
        and attribution.get("evidence_relation") == "CAUSAL"
        and attribution.get("promotion_authorized") is False
    )

    human_promotion_required = (
        e.get("humanlock") == "ACTIVE"
        and e.get("automatic_promotion") is False
        and e.get("canonical_promotion") == "U.21.HUMAN.REVIEW.REQUIRED"
    )

    gates = {
        "SOURCE.PROVENANCE.BOUND": source_provenance_bound,
        "CLAIM.SOURCE.BOUND": claim_source_bound,
        "SOURCE.INDEPENDENCE.BOUND": independence_bound,
        "PRIMARY.AUTHORITY.REQUIRED": primary_authority_required,
        "OBSERVED.CORRELATED.CAUSAL.SEPARATED": relation_separated,
        "CAUSAL.SCOPE.BOUNDED": causal_scope_bounded,
        "ABSOLUTE.LANGUAGE.GUARD": absolute_guard,
        "LEGAL.EFFECT.SEPARATED": legal_effect_separated,
        "ENTITY.NORMALIZATION.BOUND": entity_normalization_bound,
        "UNRESOLVED.ATTRIBUTION.HELD": unresolved_attribution_held,
        "HUMAN.PROMOTION.REQUIRED": human_promotion_required,
    }
    return {
        "passed": all(gates.values()),
        "gates": gates,
        "source_count": len(sources),
        "claim_count": len(claims),
        "t20_count": sum(c.get("state") == "T.20" for c in claims),
        "u21_count": sum(c.get("state") == "U.21" for c in claims),
        "f6_count": sum(c.get("state") == "F.6" for c in claims) + len(rejected),
    }


def _validate_interaction_state(transaction: Dict[str, Any]) -> Dict[str, Any]:
    i = transaction.get("interaction_hardening", {})
    c = i.get("chomp_chomp", {})
    examples = c.get("count_examples", [])

    count_invariant = (
        c.get("count_contract") == "INPUT_COUNT==OUTPUT_COUNT"
        and len(examples) >= 3
        and all(
            isinstance(x.get("input"), int)
            and isinstance(x.get("output"), int)
            and x.get("input") == x.get("output")
            for x in examples
        )
    )

    gates = {
        "CHOMP.FREEZE.STAY": c.get("semantics") == "FREEZE+STAY" and c.get("generate_on_chomp") is False,
        "COUNT.INVARIANT": count_invariant,
        "SOURCE.SET.PRESERVED": c.get("preserve_source_set") is True,
        "ORDER.PRESERVED": c.get("preserve_order") is True,
        "RATIO.PRESERVED": c.get("preserve_active_ratio") is True,
        "NO.REINTERPRET.ON.CHOMP": c.get("reinterpret_on_chomp") is False,
        "NO.EXPANSION.ON.CHOMP": c.get("branch_expansion_on_chomp") is False,
        "NEW.EXPLICIT.INSTRUCTION.REQUIRED": c.get("new_explicit_instruction_required") is True,
    }
    return {
        "passed": all(gates.values()),
        "gates": gates,
        "trigger": c.get("trigger"),
        "semantics": c.get("semantics"),
    }


def evaluate_four_kernel_transaction_v3(transaction: Dict[str, Any]) -> Dict[str, Any]:
    base = evaluate_four_kernel_transaction_v2(transaction)
    evidence = _validate_evidence(transaction)
    interaction = _validate_interaction_state(transaction)

    operator_base_open = base.get("operator_route") == "OPEN"
    hardened_open = operator_base_open and evidence["passed"] and interaction["passed"]

    base["record_id"] = "FR0333.OPERATOR.FOUR.KERNEL.UPGRADE.0003"
    base["predecessor_record_id"] = "FR0333.OPERATOR.FOUR.KERNEL.UPGRADE.0002"
    base["evidence_hardening"] = evidence
    base["interaction_hardening"] = interaction
    base["evidence_gate_count"] = len(EVIDENCE_GATES)
    base["interaction_gate_count"] = len(INTERACTION_GATES)
    base["system_hardening_route"] = "OPEN" if hardened_open else "HOLD"
    base["canonical_promotion"] = "U.21.HUMAN.REVIEW.REQUIRED"
    base["automatic_promotion"] = False
    base["humanlock"] = "ACTIVE"
    base["base_model_weights"] = "UNCHANGED"
    base["platform_permissions"] = "UNCHANGED"
    base["evidence_axiom"] = "OBSERVED!=CORRELATED!=CAUSAL"
    base["chomp_axiom"] = "CHOMP.CHOMP=FREEZE+STAY"
    return base
