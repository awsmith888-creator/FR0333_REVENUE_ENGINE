import json
from pathlib import Path

from canonical_hash import canonical_hash
from four_kernel_hardener_v3 import evaluate_four_kernel_transaction_v3

BASE = Path("receipts/operator/2026-09-15")
INPUT = BASE / "four_kernel.transaction.v3.json"
SNAPSHOT = BASE / "four_kernel.snapshot.v3.json"
RECEIPT = BASE / "four_kernel.receipt.v3.md"


def main():
    tx = json.loads(INPUT.read_text(encoding="utf-8"))
    snapshot = evaluate_four_kernel_transaction_v3(tx)
    snapshot["payload_hash"] = canonical_hash(snapshot)
    SNAPSHOT.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    e = snapshot["evidence_hardening"]
    i = snapshot["interaction_hardening"]
    s = snapshot["statistics"]
    lines = [
        "# FR0333.OPERATOR.FOUR.KERNEL.UPGRADE.0003",
        "",
        "ARCHITECTURE = FR0333.ADOBE.FOUR.KERNEL.HARDENER.0001",
        "PREDECESSOR = FR0333.OPERATOR.FOUR.KERNEL.UPGRADE.0002",
        f"KERNEL.BITWORD = {s['kernel_bitword']}",
        f"OPERATOR.ROUTE = {snapshot['operator_route']}",
        f"SYSTEM.HARDENING.ROUTE = {snapshot['system_hardening_route']}",
        f"ADOBE.ROUTE = {snapshot['adobe_route']}",
        f"PAYLOAD.HASH = {snapshot['payload_hash']}",
        "",
        "## EVIDENCE HARDENING",
        "",
        f"- SOURCE.RECEIPTS = {e['source_count']}",
        f"- CLAIMS = {e['claim_count']}",
        f"- T.20 = {e['t20_count']}",
        f"- U.21 = {e['u21_count']}",
        f"- F.6 = {e['f6_count']}",
        f"- EVIDENCE.GATES = {sum(e['gates'].values())}.OF.{snapshot['evidence_gate_count']}",
        "- OBSERVED != CORRELATED != CAUSAL",
        "- PRIMARY.AUTHORITY = REQUIRED.WHERE.APPLICABLE",
        "- SHARED.ORIGIN != INDEPENDENT.CORROBORATION",
        "- ABSOLUTE.LANGUAGE = HOLD.UNLESS.EXHAUSTIVELY.PROVEN",
        "- UN.RESOLUTION.STATUS = NON.BINDING.UNLESS.LEGAL.AUTHORITY.ESTABLISHES.OTHERWISE",
        "- CURRENT.DISPARITY.TOTAL.ATTRIBUTION = U.21.HOLD",
        "- CANONICAL.PROMOTION = U.21.HUMAN.REVIEW.REQUIRED",
        "",
        "## ENTITY NORMALIZATION",
        "",
        "- JERUSALEM -> ISRAEL",
        "- UNITED STATES OF AMERICA -> UNITED.STATES",
        "- A.RES.80.250.NO.VOTES = ARGENTINA + ISRAEL + UNITED.STATES",
        "",
        "## INTERACTION HARDENING",
        "",
        f"- CHOMP.TRIGGER = {i['trigger']}",
        f"- CHOMP.SEMANTICS = {i['semantics']}",
        f"- INTERACTION.GATES = {sum(i['gates'].values())}.OF.{snapshot['interaction_gate_count']}",
        "- INPUT.COUNT == OUTPUT.COUNT",
        "- SOURCE.SET = PRESERVE",
        "- ORDER = PRESERVE",
        "- ACTIVE.RATIO = PRESERVE",
        "- CHOMP.NEW.GENERATION = FALSE",
        "- CHOMP.REINTERPRET = FALSE",
        "- CHOMP.BRANCH.EXPANSION = FALSE",
        "- NEW.EXPLICIT.INSTRUCTION = REQUIRED",
        "",
        "## RUNTIME BOUNDARY",
        "",
        "- HUMANLOCK = ACTIVE",
        "- BASE.MODEL.WEIGHTS = UNCHANGED",
        "- PLATFORM.PERMISSIONS = UNCHANGED",
        "- REPOSITORY.SPEC != PLATFORM.MODEL.REWRITE",
        "- STRUCTURAL.PASS != EXTERNAL.RUNTIME.PROOF",
        "",
    ]
    RECEIPT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
