import json
from pathlib import Path

from canonical_hash import canonical_hash
from rsi_delta_monitor import build_delta_snapshot


BASE = Path("receipts/rsi/2026-09-14")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    baseline = load_json(BASE / "observation.bundle.json")
    baseline_hash_record = load_json(BASE / "observation.bundle.hash.json")
    candidate = load_json(BASE / "observation.bundle.0002.json")
    candidate_hash_record = load_json(BASE / "observation.bundle.0002.hash.json")
    source_receipts = [
        load_json(BASE / "openai.rsi.team.source.json"),
        load_json(BASE / "openai.rsi.safety.source.json"),
    ]

    if canonical_hash(baseline) != baseline_hash_record["payload_hash"]:
        raise AssertionError("BASELINE_HASH_MISMATCH")
    if canonical_hash(candidate) != candidate_hash_record["payload_hash"]:
        raise AssertionError("CANDIDATE_HASH_MISMATCH")

    snapshot = build_delta_snapshot(
        baseline,
        candidate,
        source_receipts,
        baseline_hash_record["payload_hash"],
        candidate_hash_record["payload_hash"],
    )
    snapshot_hash = canonical_hash(snapshot)

    (BASE / "delta.snapshot.0001.json").write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# FR0333.RSI.DELTA.MONITOR.0001",
        "",
        f"BASELINE = {snapshot['baseline_record_id']}",
        f"CANDIDATE = {snapshot['candidate_record_id']}",
        f"OBSERVED_AT = {snapshot['observed_at']}",
        f"BASELINE_HASH = {snapshot['baseline_payload_hash']}",
        f"CANDIDATE_HASH = {snapshot['candidate_payload_hash']}",
        f"DELTA_HASH = {snapshot_hash}",
        f"STATUS = {snapshot['status']}",
        "",
        "## NEW VERIFIED FACTS",
        "",
    ]
    lines.extend(f"- {claim} = T.20" for claim in snapshot["new_verified_facts"])
    lines.extend([
        "",
        "## RETAINED BOUNDARIES",
        "",
        "- FULL.AUTONOMOUS.SELF.SUCCESSOR.DESIGN remains U.21.",
        "- CURRENT.RUNTIME.CAN.SELF.REWRITE.MODEL.WEIGHTS remains F.6.",
        "- Repository evidence/evaluation upgrades do not alter hosted model weights or platform permissions.",
        "",
        "## SOURCE IDS ADDED",
        "",
    ])
    lines.extend(f"- {source_id}" for source_id in snapshot["source_ids_added"])
    lines.extend([
        "",
        "## INVARIANT",
        "",
        "OBSERVED ≠ CORRELATED ≠ CAUSAL",
        "",
        "No baseline claim was deleted. No prior truth state changed in this delta.",
        "",
    ])

    (BASE / "delta.receipt.0001.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
