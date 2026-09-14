import json
from pathlib import Path

from canonical_hash import canonical_hash


BASE = Path("receipts/rsi/2026-09-14")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    bundle = load_json(BASE / "observation.bundle.json")
    stored_hash = load_json(BASE / "observation.bundle.hash.json")
    computed_hash = canonical_hash(bundle)

    if stored_hash.get("payload_hash") != computed_hash:
        raise AssertionError("OBSERVATION_BUNDLE_HASH_MISMATCH")

    lines = [
        f"# {bundle['record_id']}",
        "",
        f"TIMESTAMP = {bundle['timestamp']}  ",
        f"TOPIC = {bundle['topic']}  ",
        f"PAYLOAD_HASH = {computed_hash}",
        "",
        "## CLAIMS",
        "",
    ]
    lines.extend(f"- {key} = {value}" for key, value in bundle["claims"].items())
    lines.extend(["", "## SOURCE IDS", ""])
    lines.extend(f"- {source_id}" for source_id in bundle["sources"])
    lines.extend(
        [
            "",
            "## EVIDENCE BOUNDARY",
            "",
            "OBSERVED ≠ CORRELATED ≠ CAUSAL",
            "",
            (
                "The primary-source record establishes bounded AI participation in "
                "AI research and development. It does not establish a fully autonomous "
                "system that designs and develops its own successor without human direction."
            ),
            "",
            "## RUNTIME BOUNDARY",
            "",
            bundle["notes"]["runtime_scope"],
            "",
            "## SOURCE URLS",
            "",
            "- OpenAI: https://openai.com/index/research-acceleration-view-inside-openai/",
            "- Anthropic: https://www.anthropic.com/institute/recursive-self-improvement",
            "",
        ]
    )
    (BASE / "receipt.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
