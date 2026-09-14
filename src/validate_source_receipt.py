from typing import Any, Dict

from canonical_hash import canonical_hash


REQUIRED = {
    "source_id",
    "source_type",
    "publisher",
    "title",
    "published_at",
    "retrieved_at",
    "url",
    "evidence_class",
    "payload_hash",
}


def receipt_payload(receipt: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source_id": receipt["source_id"],
        "source_type": receipt["source_type"],
        "publisher": receipt["publisher"],
        "title": receipt["title"],
        "published_at": receipt["published_at"],
        "retrieved_at": receipt["retrieved_at"],
        "url": receipt["url"],
        "evidence_class": receipt["evidence_class"],
        "summary": receipt.get("summary"),
        "claims_observed": receipt.get("claims_observed", []),
    }


def validate_source_receipt(receipt: Dict[str, Any]) -> bool:
    if not isinstance(receipt, dict) or not REQUIRED.issubset(receipt):
        return False
    if not all(receipt.get(k) for k in REQUIRED - {"payload_hash"}):
        return False
    if not str(receipt["url"]).startswith("https://"):
        return False
    return receipt["payload_hash"] == canonical_hash(receipt_payload(receipt))
