import json
from pathlib import Path

from canonical_hash import canonical_hash
from validate_source_receipt import validate_source_receipt


BASE = Path("receipts/rsi/2026-09-14")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def build_observation(openai_receipt, anthropic_receipt):
    return {
        "record_id": "FR0333.RSI.OBSERVATION.PIPELINE.0001",
        "timestamp": "2026-09-14T00:00:00Z",
        "topic": "bounded_recursive_self_improvement",
        "sources": [
            openai_receipt["source_id"],
            anthropic_receipt["source_id"],
        ],
        "claims": {
            "AI.ASSISTS.AI.RESEARCH": "T.20",
            "AI.WRITES.AI.DEVELOPMENT.CODE": "T.20",
            "AI.RUNS.RESEARCH.EXPERIMENTS": "T.20",
            "AI.PROPOSES.HYPOTHESES": "T.20",
            "AI.EVALUATES.AI.RELATED.WORK": "T.20",
            "FULL.AUTONOMOUS.SELF.SUCCESSOR.DESIGN": "U.21",
            "CURRENT.RUNTIME.CAN.SELF.REWRITE.MODEL.WEIGHTS": "F.6",
        },
        "notes": {
            "boundary": (
                "bounded improvement around model operations is established; "
                "self-directed runtime model-weight rewriting is not established"
            ),
            "runtime_scope": (
                "This repository pipeline upgrades evidence handling, evaluation, "
                "and regression controls. It does not modify hosted model weights "
                "or platform permissions."
            ),
        },
    }


def main():
    openai_receipt = load_json(BASE / "openai.research_acceleration.source.json")
    anthropic_receipt = load_json(BASE / "anthropic.when_ai_builds_itself.source.json")

    if not validate_source_receipt(openai_receipt):
        raise AssertionError("INVALID_OPENAI_RECEIPT")
    if not validate_source_receipt(anthropic_receipt):
        raise AssertionError("INVALID_ANTHROPIC_RECEIPT")

    observation = build_observation(openai_receipt, anthropic_receipt)
    bundle_hash = canonical_hash(observation)

    BASE.mkdir(parents=True, exist_ok=True)
    (BASE / "observation.bundle.json").write_text(
        json.dumps(observation, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (BASE / "observation.bundle.hash.json").write_text(
        json.dumps(
            {"record_id": observation["record_id"], "payload_hash": bundle_hash},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
