from src.provider_change_gate import evaluate_provider_change


def candidate(**overrides):
    value = {
        "provider": "google",
        "product": "Gemini API",
        "surface": "grounded_generation",
        "transport": "api",
        "model_reported": "Gemini example",
        "account_context": "developer account",
        "personalization_state": "not reported",
        "session_context": "single request",
        "change_type": "PRICE",
        "source_class": "PRIMARY_OFFICIAL",
        "source_url": "https://ai.google.dev/pricing",
        "publication_date": "2026-10-07",
        "effective_date": "2026-10-07",
        "availability_state": "GENERALLY_AVAILABLE",
        "documented_facts": ["The official page lists a new price."],
        "benchmark_lane": "COST",
        "benchmark_assumption_affected": "API cost per million tokens",
        "interpretation": "The cost comparison may need a new observation.",
    }
    value.update(overrides)
    return value


def test_complete_candidate_keeps_facts_and_interpretation_separate():
    result = evaluate_provider_change(candidate())
    assert result["status"] == "MATERIAL_CANDIDATE_REVIEW"
    assert result["verified_facts"] == ["The official page lists a new price."]
    assert result["interpretation"].startswith("The cost comparison")
    assert result["source_verification"] == "NOT_INDEPENDENTLY_VERIFIED_BY_ENGINE"
    assert result["promotion"] == "NOT_AUTHORIZED_BY_INTAKE_GATE"
    assert result["historical_baseline_mutated"] is False


def test_api_surface_cannot_omit_surface_identity():
    result = evaluate_provider_change(candidate(transport=""))
    assert result["status"] == "HOLD"
    assert any(reason.startswith("SURFACE_IDENTITY_INCOMPLETE:") for reason in result["hold_reasons"])


def test_secondary_source_is_held():
    result = evaluate_provider_change(candidate(source_class="SECONDARY_REPORT"))
    assert result["status"] == "HOLD"
    assert "PRIMARY_OFFICIAL_SOURCE_CLASS_REQUIRED" in result["hold_reasons"]


def test_facts_and_interpretation_must_be_distinct():
    result = evaluate_provider_change(candidate(documented_facts=[], interpretation=""))
    assert result["status"] == "HOLD"
    assert "DOCUMENTED_FACTS_REQUIRED_AS_NONEMPTY_LIST" in result["hold_reasons"]
    assert "INTERPRETATION_FIELD_REQUIRED_SEPARATELY" in result["hold_reasons"]
