"""Deterministic intake gate for FR0333 provider product and pricing changes.

This module validates and classifies source observations supplied to the engine.
It does not crawl provider websites or independently verify source claims.
"""

from __future__ import annotations

from typing import Any, Dict, List
from urllib.parse import urlparse


PROVIDERS = {"openai", "anthropic", "google", "google_deepmind", "xai"}
CHANGE_TYPES = {"PRODUCT_LAUNCH", "PRICE", "PLAN", "ACCESS", "PACKAGING"}
BENCHMARK_LANES = {"MODEL_CAPABILITY", "ACCESS", "COST", "SURFACE", "PACKAGING"}
SURFACE_FIELDS = (
    "provider",
    "product",
    "surface",
    "transport",
    "model_reported",
    "account_context",
    "personalization_state",
    "session_context",
)


def evaluate_provider_change(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Return a reviewable candidate or HOLD without promoting source claims."""
    reasons: List[str] = []
    provider = str(candidate.get("provider", "")).strip().lower()
    change_type = str(candidate.get("change_type", "")).strip().upper()
    if provider not in PROVIDERS:
        reasons.append("UNSUPPORTED_OR_MISSING_PROVIDER")
    if change_type not in CHANGE_TYPES:
        reasons.append("UNSUPPORTED_OR_MISSING_CHANGE_TYPE")

    source_url = str(candidate.get("source_url", "")).strip()
    parsed_url = urlparse(source_url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        reasons.append("OFFICIAL_SOURCE_URL_REQUIRED")
    if str(candidate.get("source_class", "")).upper() != "PRIMARY_OFFICIAL":
        reasons.append("PRIMARY_OFFICIAL_SOURCE_CLASS_REQUIRED")

    documented_facts = candidate.get("documented_facts")
    if not isinstance(documented_facts, list) or not documented_facts or any(
        not isinstance(item, str) or not item.strip() for item in documented_facts
    ):
        reasons.append("DOCUMENTED_FACTS_REQUIRED_AS_NONEMPTY_LIST")

    lane = str(candidate.get("benchmark_lane", "")).upper()
    if lane not in BENCHMARK_LANES:
        reasons.append("VALID_BENCHMARK_LANE_REQUIRED")
    if not str(candidate.get("benchmark_assumption_affected", "")).strip():
        reasons.append("AFFECTED_BENCHMARK_ASSUMPTION_REQUIRED")
    if not str(candidate.get("interpretation", "")).strip():
        reasons.append("INTERPRETATION_FIELD_REQUIRED_SEPARATELY")

    missing_surface_fields = [
        field for field in SURFACE_FIELDS if not str(candidate.get(field, "")).strip()
    ]
    if missing_surface_fields:
        reasons.append("SURFACE_IDENTITY_INCOMPLETE:" + ",".join(missing_surface_fields))

    status = "MATERIAL_CANDIDATE_REVIEW" if not reasons else "HOLD"
    return {
        "record_type": "FR0333.PROVIDER.CHANGE.CANDIDATE",
        "status": status,
        "promotion": "NOT_AUTHORIZED_BY_INTAKE_GATE",
        "source_verification": "NOT_INDEPENDENTLY_VERIFIED_BY_ENGINE",
        "source_class_asserted": str(candidate.get("source_class", "UNSPECIFIED")).upper(),
        "source_url": source_url or None,
        "publication_date": candidate.get("publication_date"),
        "effective_date": candidate.get("effective_date"),
        "availability_state": candidate.get("availability_state", "UNKNOWN"),
        "provider": provider or None,
        "product": candidate.get("product"),
        "change_type": change_type or None,
        "benchmark_lane": lane or None,
        "benchmark_assumption_affected": candidate.get("benchmark_assumption_affected"),
        "surface_identity": {field: candidate.get(field) for field in SURFACE_FIELDS},
        "verified_facts": documented_facts if isinstance(documented_facts, list) else [],
        "interpretation": candidate.get("interpretation"),
        "historical_baseline_mutated": False,
        "hold_reasons": reasons,
        "next_action": "INDEPENDENT_SOURCE_REVIEW" if not reasons else "COMPLETE_MISSING_FIELDS",
    }
