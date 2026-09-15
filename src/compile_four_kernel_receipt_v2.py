import json
from pathlib import Path

from canonical_hash import canonical_hash
from four_kernel_hardener_v2 import evaluate_four_kernel_transaction_v2

BASE = Path("receipts/operator/2026-09-15")
INPUT = BASE / "four_kernel.transaction.v2.json"
SNAPSHOT = BASE / "four_kernel.snapshot.v2.json"
RECEIPT = BASE / "four_kernel.receipt.v2.md"


def main():
    tx = json.loads(INPUT.read_text(encoding="utf-8"))
    snapshot = evaluate_four_kernel_transaction_v2(tx)
    snapshot["payload_hash"] = canonical_hash(snapshot)
    SNAPSHOT.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    s = snapshot["statistics"]
    n = snapshot["nelson_measurement_gate"]
    lines = [
        "# FR0333.OPERATOR.FOUR.KERNEL.UPGRADE.0002", "",
        "ARCHITECTURE = FR0333.ADOBE.FOUR.KERNEL.HARDENER.0001",
        "PREDECESSOR = FR0333.OPERATOR.FOUR.KERNEL.UPGRADE.0001",
        f"KERNEL.BITWORD = {s['kernel_bitword']}",
        f"DECIMAL.STATE = {s['decimal_state']}",
        f"ACTIVE.KERNELS = {s['active_kernel_count']}.OF.4",
        f"KERNEL.PASS.RATE = {s['kernel_pass_rate']:.4f}",
        f"CORE.GATES = {s['passed_core_gate_count']}.OF.{s['required_core_gate_count']}",
        f"CORE.GATE.PASS.RATE = {s['core_gate_pass_rate']:.4f}",
        f"OPERATOR.ROUTE = {snapshot['operator_route']}",
        f"ADOBE.ROUTE = {snapshot['adobe_route']}",
        f"PAYLOAD.HASH = {snapshot['payload_hash']}", "",
        "## KERNELS", "",
        "- K1 = NEWSFLASH = CURRENT.SIGNAL.INTAKE",
        "- K2 = ESPN.FANTASY.SPORTS = NUMERIC.STATISTICAL.BONE",
        "- K3 = NELSON = USER.DEFINED.MEASUREMENT.KERNEL",
        "- K4 = GENIUS.BAR = DIAGNOSE.CONTRADICT.REPAIR", "",
        "NELSON is preserved exactly as supplied. NIELSEN identifies an external measurement source; it is not the kernel name.", "",
        "## NELSON HARDENING", "",
        "- ROLE.STATUS = DEFINED.ACTIVE",
        f"- SOURCE.RECEIPTS = {n['source_receipt_count']}",
        f"- MEASUREMENTS = {n['measurement_count']}",
        f"- PROGRAMS = {n['program_count']}",
        f"- MEASUREMENT.PERIODS = {n['measurement_period_count']}",
        f"- COMPARABLE.PROGRAMS = {s['comparable_program_count']}",
        f"- CROSS.PERIOD.RANKING = {snapshot['cross_period_ranking']}",
        "- EVENING.NEWS.COMPARISON = ABC.WORLD.NEWS.TONIGHT + NBC.NIGHTLY.NEWS + CBS.EVENING.NEWS",
        "- 60.MINUTES = CONTEXT.ONLY.SEASON.SCOPE",
        "- SEP14.EVENING.NEWS.SPECIFIC.RATINGS = U.21.AWAITING.NIELSEN",
        "- SEP13.60.MINUTES.PREMIERE.RATING = U.21.AWAITING.NIELSEN", "",
        "## STATISTICAL BONE", "",
        "- WEEK.2026.08.31 ABC.TOTAL = 8508000",
        "- WEEK.2026.08.31 ABC.A25.54 = 1102000",
        "- WEEK.2026.08.31 NBC.TOTAL = 6988000",
        "- WEEK.2026.08.31 NBC.A25.54 = 1103000",
        "- WEEK.2026.08.31 CBS.TOTAL = 4037000",
        "- WEEK.2026.08.31 CBS.A25.54 = 544000",
        "- SEASON.2025.26 60.MINUTES.AVG.TOTAL = 9100000",
        "- SEASON.2025.26 60.MINUTES.YOY.TOTAL.PCT = 9",
        "- SEASON.2025.26 60.MINUTES.YOY.A25.54.PCT = 5",
        "- SEASON.2025.26 60.MINUTES.SOCIAL.VIDEO.VIEWS = 2500000000",
        "- SEASON.2025.26 60.MINUTES.SOCIAL.ENGAGEMENTS.MIN = 105000000",
        "- SEASON.2025.26 60.MINUTES.SOCIAL.FOLLOWERS.APPROX = 17000000", "",
        "## HARDENED BOUNDARIES", "",
        "- BARE.INTEGER.COUNTS != MEASUREMENT.PROOF",
        "- ROLE.DEFINITION.PENDING != NELSON.PASS",
        "- SOURCE + PERIOD + METRIC + UNIT + SCOPE + RECEIPT = REQUIRED",
        "- WEEKLY.EVENING.NEWS != SEASONAL.60.MINUTES.RANKING",
        "- UNPUBLISHED.SPECIFIC.TELECAST.RATING -> U.21.HOLD",
        "- HUMANLOCK = ACTIVE",
        "- BASE.MODEL.WEIGHTS = UNCHANGED",
        "- PLATFORM.PERMISSIONS = UNCHANGED",
        "- ADOBE.EMPIRICAL.ROUTE = HOLD", "",
    ]
    RECEIPT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
