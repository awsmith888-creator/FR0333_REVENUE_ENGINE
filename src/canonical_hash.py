import hashlib
import json
from typing import Any


def canonical_hash(payload: Any) -> str:
    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return "sha256_" + hashlib.sha256(serialized.encode("utf-8")).hexdigest()
