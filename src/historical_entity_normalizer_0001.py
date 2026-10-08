import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any, Dict


def normalize_candidate_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "")
    normalized = " ".join(normalized.strip().split())
    return normalized.casefold()


def _comparison_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", normalize_candidate_name(value))


def resolve_entity_pair(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    left_raw = left.get("raw_name", "")
    right_raw = right.get("raw_name", "")
    left_id = left.get("archive_entity_id")
    right_id = right.get("archive_entity_id")

    if left_id and right_id and left_id == right_id:
        return _receipt(left, right, "T.20.SAME.ENTITY", ["R01.SOURCE.PERSISTENT.ID"], False)

    if right_raw in left.get("explicit_aliases", []) or left_raw in right.get("explicit_aliases", []):
        return _receipt(left, right, "T.20.ALIAS.LINK", ["R03.EXPLICIT.ALIAS"], False)

    if left.get("chronology_conflict") is True or right.get("chronology_conflict") is True:
        return _receipt(left, right, "F.6.SAME.ENTITY", ["R08.CONFLICTING.CHRONOLOGY"], False)

    left_norm = normalize_candidate_name(left_raw)
    right_norm = normalize_candidate_name(right_raw)
    if left_norm and left_norm == right_norm:
        return _receipt(left, right, "U.21.CANDIDATE.MATCH", ["R02.EXACT.NORMALIZED.NAME"], True)

    left_key = _comparison_key(left_raw)
    right_key = _comparison_key(right_raw)
    similarity = SequenceMatcher(None, left_key, right_key).ratio() if left_key and right_key else 0.0
    if similarity >= 0.84:
        return _receipt(left, right, "U.21.CANDIDATE.MATCH", ["R04.ORTHOGRAPHIC.VARIANT"], True)

    if _shared_context_only(left, right):
        return _receipt(left, right, "NO.IDENTITY.INFERENCE", ["R05.TITLE.IS.NOT.IDENTITY", "R06.COLOCATION.IS.NOT.IDENTITY"], False)

    return _receipt(left, right, "U.21.AMBIGUOUS", ["R09.AMBIGUOUS.COLLISION"], True)


def _shared_context_only(left: Dict[str, Any], right: Dict[str, Any]) -> bool:
    context_fields = ("title", "address", "company", "voyage")
    return any(left.get(field) and left.get(field) == right.get(field) for field in context_fields)


def _receipt(left: Dict[str, Any], right: Dict[str, Any], decision: str, rule_ids, review_required: bool) -> Dict[str, Any]:
    return {
        "left_record_id": left.get("record_id"),
        "right_record_id": right.get("record_id"),
        "raw_values": [left.get("raw_name", ""), right.get("raw_name", "")],
        "normalized_values": [normalize_candidate_name(left.get("raw_name", "")), normalize_candidate_name(right.get("raw_name", ""))],
        "decision": decision,
        "rule_ids": rule_ids,
        "human_review_required": review_required,
        "auto_merge": False,
        "causal_attribution": "NOT.ESTABLISHED",
    }
