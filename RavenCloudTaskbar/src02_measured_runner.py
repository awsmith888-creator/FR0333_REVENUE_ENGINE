#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

NORMALIZATION_VERSION = "SRC02.NORMALIZE.1"
SOURCE_OBJECT_VERSION = "SRC02.SourceObject.1"
OPPORTUNITY_RECORD_VERSION = "SRC02.OpportunityRecord.1"
SCORING_VERSION = "SRC02.SCORING.1"

TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


class SRC02ValidationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _parse_time(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise SRC02ValidationError("INVALID_TIMESTAMP", f"{field} must be a non-empty ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SRC02ValidationError("INVALID_TIMESTAMP", f"{field} is not valid ISO-8601") from exc
    if parsed.tzinfo is None:
        raise SRC02ValidationError("TIMESTAMP_REQUIRES_OFFSET", f"{field} must include a timezone offset")
    return parsed


def canonicalize_uri(uri: str) -> str:
    if not isinstance(uri, str) or not uri.strip():
        raise SRC02ValidationError("INVALID_URI", "uri must be non-empty")
    parts = urlsplit(uri.strip())
    if not parts.scheme or not parts.netloc:
        return uri.strip()
    host = parts.hostname.lower() if parts.hostname else ""
    port = f":{parts.port}" if parts.port else ""
    userinfo = ""
    if parts.username:
        userinfo = parts.username
        if parts.password:
            userinfo += f":{parts.password}"
        userinfo += "@"
    netloc = f"{userinfo}{host}{port}"
    kept = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered in TRACKING_QUERY_KEYS or any(lowered.startswith(p) for p in TRACKING_QUERY_PREFIXES):
            continue
        kept.append((key, value))
    query = urlencode(sorted(kept))
    path = parts.path or "/"
    return urlunsplit((parts.scheme.lower(), netloc, path, query, ""))


def _source_id(run_id: str, query_id: str, retrieval_index: int, canonical_uri: str, content_sha256: str) -> str:
    material = f"{run_id}|{query_id}|{retrieval_index}|{canonical_uri}|{content_sha256}"
    return f"SRC02-SRC-{_sha256_text(material)[:16].upper()}"


def _opportunity_id(run_id: str, candidate_key: str) -> str:
    return f"SRC02-OPP-{_sha256_text(run_id + '|' + candidate_key)[:16].upper()}"


def normalize_source(raw: dict[str, Any], *, run_id: str, query_id: str, retrieval_index: int,
                     retrieval_method: str, default_retrieved_at: str) -> dict[str, Any]:
    allowed_source_classes = {"PRIMARY", "SECONDARY", "AGGREGATOR", "SOCIAL", "UNKNOWN"}
    if raw.get("source_class", "UNKNOWN") not in allowed_source_classes:
        raise SRC02ValidationError("INVALID_SOURCE_CLASS", str(raw.get("source_class")))
    uri = raw.get("uri")
    canonical_uri = canonicalize_uri(uri)
    raw_content = raw.get("raw_content")
    if not isinstance(raw_content, str):
        raise SRC02ValidationError("RAW_CONTENT_REQUIRED", f"retrieval_index={retrieval_index}")
    capture_payload = raw.get("capture_payload", raw_content)
    if isinstance(capture_payload, str):
        capture_bytes = capture_payload.encode("utf-8")
    else:
        capture_bytes = _canonical_json(capture_payload)
    content_sha256 = _sha256_text(raw_content)
    capture_sha256 = _sha256_bytes(capture_bytes)
    retrieved_at = raw.get("retrieved_at", default_retrieved_at)
    _parse_time(retrieved_at, "retrieved_at")
    published_at = raw.get("published_at")
    if published_at is not None:
        _parse_time(published_at, "published_at")
    source_id = _source_id(run_id, query_id, retrieval_index, canonical_uri, content_sha256)
    return {
        "source_object_version": SOURCE_OBJECT_VERSION,
        "source_id": source_id,
        "run_id": run_id,
        "query_id": query_id,
        "retrieved_at": retrieved_at,
        "retrieval_method": retrieval_method,
        "source_class": raw.get("source_class", "UNKNOWN"),
        "uri": uri,
        "canonical_uri": canonical_uri,
        "title": raw.get("title"),
        "publisher": raw.get("publisher"),
        "published_at": published_at,
        "raw_receipt": {
            "capture_pointer": raw.get("capture_pointer") or f"INLINE.RETRIEVAL.{retrieval_index}",
            "content_sha256": content_sha256,
            "capture_sha256": capture_sha256,
        },
        "duplicate_state": "UNIQUE",
        "duplicate_of": None,
        "lineage": {
            "retrieval_index": retrieval_index,
            "normalization_version": NORMALIZATION_VERSION,
        },
    }


def collapse_duplicates(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_by_content: dict[str, str] = {}
    output = deepcopy(sources)
    for source in output:
        content_hash = source["raw_receipt"]["content_sha256"]
        duplicate_of = seen_by_content.get(content_hash)
        if duplicate_of:
            source["duplicate_state"] = "DUPLICATE"
            source["duplicate_of"] = duplicate_of
        else:
            seen_by_content[content_hash] = source["source_id"]
    return output


def build_source_set(payload: dict[str, Any]) -> dict[str, Any]:
    for field in ("run_id", "query_id", "retrieved_at", "retrieval_method", "raw_sources"):
        if field not in payload:
            raise SRC02ValidationError("MISSING_FIELD", field)
    if payload["retrieval_method"] not in {"WEB", "API", "CONNECTOR", "USER_SUPPLIED", "OTHER"}:
        raise SRC02ValidationError("INVALID_RETRIEVAL_METHOD", str(payload["retrieval_method"]))
    _parse_time(payload["retrieved_at"], "retrieved_at")
    if not isinstance(payload["raw_sources"], list):
        raise SRC02ValidationError("RAW_SOURCES_REQUIRED", "raw_sources must be an array")
    sources = [
        normalize_source(
            raw,
            run_id=payload["run_id"],
            query_id=payload["query_id"],
            retrieval_index=index,
            retrieval_method=payload["retrieval_method"],
            default_retrieved_at=payload["retrieved_at"],
        )
        for index, raw in enumerate(payload["raw_sources"])
    ]
    sources = collapse_duplicates(sources)
    artifact = {
        "artifact_type": "FR0333.DEEP.SEARCH.SRC02.SOURCESET.001",
        "run_id": payload["run_id"],
        "query_id": payload["query_id"],
        "normalization_version": NORMALIZATION_VERSION,
        "sources": sources,
        "source_set_hash": None,
    }
    canonical = deepcopy(artifact)
    canonical["source_set_hash"] = None
    artifact["source_set_hash"] = _sha256_bytes(_canonical_json(canonical))
    return artifact


def _source_by_index(source_set: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {s["lineage"]["retrieval_index"]: s for s in source_set["sources"]}


def build_opportunity_records(payload: dict[str, Any], source_set: dict[str, Any]) -> list[dict[str, Any]]:
    source_by_index = _source_by_index(source_set)
    records: list[dict[str, Any]] = []
    for raw in payload.get("opportunities", []):
        candidate_key = raw.get("candidate_key")
        title = raw.get("title")
        if not isinstance(candidate_key, str) or not candidate_key:
            raise SRC02ValidationError("CANDIDATE_KEY_REQUIRED", "opportunity candidate_key is required")
        if not isinstance(title, str) or not title:
            raise SRC02ValidationError("OPPORTUNITY_TITLE_REQUIRED", candidate_key)
        source_indexes = raw.get("source_indexes", [])
        if not source_indexes:
            raise SRC02ValidationError("OPPORTUNITY_SOURCE_REQUIRED", candidate_key)
        refs = []
        for idx in source_indexes:
            if idx not in source_by_index:
                raise SRC02ValidationError("UNKNOWN_SOURCE_INDEX", f"{candidate_key}:{idx}")
            src = source_by_index[idx]
            refs.append({
                "source_id": src["source_id"],
                "content_sha256": src["raw_receipt"]["content_sha256"],
            })
        claims = []
        for claim in raw.get("claims", []):
            evidence_refs = []
            for evidence in claim.get("evidence_refs", []):
                idx = evidence.get("retrieval_index")
                if idx not in source_by_index:
                    raise SRC02ValidationError("UNKNOWN_CLAIM_SOURCE_INDEX", f"{candidate_key}:{idx}")
                evidence_refs.append({
                    "source_id": source_by_index[idx]["source_id"],
                    "selector": evidence.get("selector") or "UNSPECIFIED",
                })
            evidence_state = claim.get("evidence_state", "UNSOURCED")
            if evidence_state == "VERIFIED" and not evidence_refs:
                raise SRC02ValidationError("VERIFIED_CLAIM_REQUIRES_SOURCE", f"{candidate_key}:{claim.get('claim_id')}")
            claims.append({
                "claim_id": claim.get("claim_id") or f"{candidate_key}.CLAIM.{len(claims)+1}",
                "field": claim.get("field") or "UNSPECIFIED",
                "value": claim.get("value"),
                "evidence_state": evidence_state,
                "evidence_refs": evidence_refs,
            })
        humanlock = raw.get("humanlock") or {"state": "PENDING", "actor": None, "decided_at": None}
        if humanlock.get("state") in {"APPROVED", "REJECTED"}:
            if not humanlock.get("actor") or not humanlock.get("decided_at"):
                raise SRC02ValidationError("HUMANLOCK_DECISION_REQUIRES_RECEIPT", candidate_key)
            _parse_time(humanlock["decided_at"], "humanlock.decided_at")
        records.append({
            "opportunity_record_version": OPPORTUNITY_RECORD_VERSION,
            "opportunity_id": _opportunity_id(payload["run_id"], candidate_key),
            "run_id": payload["run_id"],
            "candidate_key": candidate_key,
            "title": title,
            "qualification_state": raw.get("qualification_state", "UNSCREENED"),
            "scam_risk_state": raw.get("scam_risk_state", "NOT_SCREENED"),
            "pricing_state": raw.get("pricing_state", "NOT_OBSERVED"),
            "funding_state": raw.get("funding_state", "NOT_OBSERVED"),
            "source_refs": refs,
            "claims": claims,
            "unresolved_gaps": list(raw.get("unresolved_gaps", [])),
            "humanlock": {
                "state": humanlock.get("state", "PENDING"),
                "actor": humanlock.get("actor"),
                "decided_at": humanlock.get("decided_at"),
            },
        })
    return records


def _ratio(numerator: int, denominator: int | None) -> dict[str, Any]:
    if denominator in (None, 0):
        return {"numerator": numerator, "denominator": denominator, "per_1000": None}
    return {
        "numerator": numerator,
        "denominator": denominator,
        "per_1000": round((numerator * 1000) / denominator),
    }


def _unique_source_ids(refs: list[dict[str, Any]]) -> set[str]:
    return {row["source_id"] for row in refs}


def score_run(payload: dict[str, Any], source_set: dict[str, Any],
              opportunities: list[dict[str, Any]]) -> dict[str, Any]:
    sources = source_set["sources"]
    unique_sources = [s for s in sources if s["duplicate_state"] == "UNIQUE"]
    duplicates = len(sources) - len(unique_sources)
    primary_unique = sum(1 for s in unique_sources if s["source_class"] == "PRIMARY")

    verified_claims = [
        claim for opp in opportunities for claim in opp["claims"] if claim["evidence_state"] == "VERIFIED"
    ]
    corroborated = sum(1 for claim in verified_claims if len(_unique_source_ids(claim["evidence_refs"])) >= 2)
    contradicted = sum(
        1 for opp in opportunities for claim in opp["claims"] if claim["evidence_state"] == "CONTRADICTED"
    )

    labels = payload.get("scoring_labels") or {}
    contradiction_total = labels.get("known_contradiction_total")
    if contradiction_total is not None:
        if not isinstance(contradiction_total, int) or contradiction_total < contradicted:
            raise SRC02ValidationError("INVALID_CONTRADICTION_DENOMINATOR", str(contradiction_total))

    required_fields = labels.get("required_claim_fields")
    evidence_satisfied = 0
    evidence_denominator: int | None = None
    if required_fields is not None:
        if not isinstance(required_fields, list):
            raise SRC02ValidationError("INVALID_REQUIRED_CLAIM_FIELDS", "must be an array")
        evidence_denominator = len(required_fields) * len(opportunities)
        for opp in opportunities:
            by_field = {c["field"]: c for c in opp["claims"]}
            for field in required_fields:
                claim = by_field.get(field)
                if claim and claim["evidence_state"] == "VERIFIED" and claim["evidence_refs"]:
                    evidence_satisfied += 1

    lineage_denominator = len(verified_claims)
    lineage_numerator = sum(1 for claim in verified_claims if claim["evidence_refs"])
    unresolved_gaps = sum(len(opp["unresolved_gaps"]) for opp in opportunities)

    started_at = _parse_time(payload.get("started_at", payload["retrieved_at"]), "started_at")
    latencies = []
    for opp in opportunities:
        if opp["humanlock"]["state"] == "APPROVED" and opp["humanlock"]["decided_at"]:
            decided = _parse_time(opp["humanlock"]["decided_at"], "humanlock.decided_at")
            seconds = (decided - started_at).total_seconds()
            if seconds < 0:
                raise SRC02ValidationError("NEGATIVE_LATENCY", opp["candidate_key"])
            latencies.append(seconds)

    latency_summary = {
        "count": len(latencies),
        "median_seconds": None,
        "max_seconds": None,
    }
    if latencies:
        latencies_sorted = sorted(latencies)
        midpoint = len(latencies_sorted) // 2
        if len(latencies_sorted) % 2:
            median = latencies_sorted[midpoint]
        else:
            median = (latencies_sorted[midpoint - 1] + latencies_sorted[midpoint]) / 2
        latency_summary["median_seconds"] = median
        latency_summary["max_seconds"] = max(latencies_sorted)

    adjudications = {
        row["candidate_key"]: row["outcome"]
        for row in labels.get("adjudications", [])
        if isinstance(row, dict) and row.get("candidate_key")
    }
    promoted = [
        opp for opp in opportunities
        if opp["qualification_state"] == "QUALIFIED" and opp["humanlock"]["state"] == "APPROVED"
    ]
    adjudicated_promoted = [opp for opp in promoted if opp["candidate_key"] in adjudications]
    false_promotions = sum(
        1 for opp in adjudicated_promoted if adjudications.get(opp["candidate_key"]) == "REJECTED"
    )
    false_promotion_denominator = len(promoted) if len(adjudicated_promoted) == len(promoted) else None

    return {
        "scoring_version": SCORING_VERSION,
        "retrieval_count": len(sources),
        "unique_source_yield": _ratio(len(unique_sources), len(sources)),
        "duplicate_rate": _ratio(duplicates, len(sources)),
        "primary_source_ratio": _ratio(primary_unique, len(unique_sources)),
        "corroboration_coverage": _ratio(corroborated, len(verified_claims)),
        "contradictions_detected": contradicted,
        "contradiction_capture": _ratio(contradicted, contradiction_total),
        "evidence_coverage": _ratio(evidence_satisfied, evidence_denominator),
        "unresolved_gap_count": unresolved_gaps,
        "lineage_coverage": _ratio(lineage_numerator, lineage_denominator),
        "latency_per_verified_opportunity": latency_summary,
        "false_promotions_detected": false_promotions,
        "false_promotion_adjudication_coverage": _ratio(len(adjudicated_promoted), len(promoted)),
        "false_promotion_rate": _ratio(false_promotions, false_promotion_denominator),
    }


def validate_comparator_controls(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    fields = ("query_set_hash", "time_window", "eligibility_rules_hash", "scoring_function_version")
    mismatches = [field for field in fields if left.get(field) != right.get(field)]
    missing = [field for field in fields if left.get(field) is None or right.get(field) is None]
    return {
        "comparator_ready": not mismatches and not missing,
        "required_controls": list(fields),
        "missing_controls": sorted(set(missing)),
        "mismatched_controls": mismatches,
    }


def run(payload: dict[str, Any]) -> dict[str, Any]:
    source_set = build_source_set(payload)
    opportunities = build_opportunity_records(payload, source_set)
    score = score_run(payload, source_set, opportunities)
    result = {
        "receipt_type": "FR0333.DEEP.SEARCH.SRC02.MEASURED.RETRIEVAL.RECEIPT.001",
        "run_id": payload["run_id"],
        "execution_class": payload.get("execution_class", "LOCAL_INTERNAL"),
        "scenario_not_forecast": True,
        "forecast_promotion_blocked": True,
        "source_set": source_set,
        "opportunity_records": opportunities,
        "score": score,
        "receipt_hash": None,
    }
    canonical = deepcopy(result)
    canonical["receipt_hash"] = None
    result["receipt_hash"] = _sha256_bytes(_canonical_json(canonical))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="FR0333 SRC02 measured retrieval runner")
    parser.add_argument("input", type=Path, help="JSON input containing raw_sources and opportunity candidates")
    parser.add_argument("-o", "--output", type=Path, required=True, help="receipt output path")
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    receipt = run(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(receipt["receipt_type"])
    print(f"run_id={receipt['run_id']}")
    print(f"retrieval_count={receipt['score']['retrieval_count']}")
    print(f"receipt_hash={receipt['receipt_hash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
