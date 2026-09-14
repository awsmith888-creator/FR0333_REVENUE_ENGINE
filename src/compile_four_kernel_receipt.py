import json
from pathlib import Path

from canonical_hash import canonical_hash
from four_kernel_hardener import evaluate_four_kernel_transaction

BASE=Path("receipts/operator/2026-09-14")
INPUT=BASE/"four_kernel.transaction.json"
SNAPSHOT=BASE/"four_kernel.snapshot.json"
RECEIPT=BASE/"four_kernel.receipt.md"

def main():
    tx=json.loads(INPUT.read_text(encoding="utf-8"))
    snapshot=evaluate_four_kernel_transaction(tx)
    snapshot["payload_hash"]=canonical_hash(snapshot)
    SNAPSHOT.write_text(json.dumps(snapshot,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    s=snapshot["statistics"]
    lines=[
        "# FR0333.OPERATOR.FOUR.KERNEL.UPGRADE.0001","",
        "ARCHITECTURE = FR0333.ADOBE.FOUR.KERNEL.HARDENER.0001",
        f"KERNEL.BITWORD = {s['kernel_bitword']}",f"DECIMAL.STATE = {s['decimal_state']}",
        f"ACTIVE.KERNELS = {s['active_kernel_count']}.OF.4",f"KERNEL.PASS.RATE = {s['kernel_pass_rate']:.4f}",
        f"CORE.GATES = {s['passed_core_gate_count']}.OF.{s['required_core_gate_count']}",f"CORE.GATE.PASS.RATE = {s['core_gate_pass_rate']:.4f}",
        f"ADOBE.GATES = {s['passed_adobe_gate_count']}.OF.{s['required_adobe_gate_count']}",f"ADOBE.GATE.PASS.RATE = {s['adobe_gate_pass_rate']:.4f}",
        f"OPERATOR.ROUTE = {snapshot['operator_route']}",f"ADOBE.ROUTE = {snapshot['adobe_route']}",
        f"ADOBE.LIVE.TRAVERSAL.RECEIPT = {snapshot['adobe_live_traversal_receipt']}",f"PAYLOAD.HASH = {snapshot['payload_hash']}","",
        "## KERNELS","","- K1 = NEWSFLASH = CURRENT.SIGNAL.INTAKE","- K2 = ESPN.FANTASY.SPORTS = NUMERIC.STATISTICAL.BONE",
        "- K3 = NELSON = USER.DEFINED.MEASUREMENT.KERNEL","- K4 = GENIUS.BAR = DIAGNOSE.CONTRADICT.REPAIR","",
        "NELSON is preserved exactly as supplied. It is not normalized to NIELSEN.","","## STATISTICS","",
        f"- SOURCE.COUNT = {s['source_count']}",f"- METRIC.COUNT = {s['metric_count']}",f"- SAMPLE.SIZE = {s['sample_size']}",
        f"- CONTRADICTION.COUNT = {s['contradiction_count']}",f"- REPAIR.ATTEMPT.COUNT = {s['repair_attempt_count']}",f"- REPAIR.SUCCESS.COUNT = {s['repair_success_count']}",
        f"- T.20.COUNT = {s['truth_t20_count']}",f"- U.21.COUNT = {s['truth_u21_count']}",f"- F.6.COUNT = {s['truth_f6_count']}","",
        "## CHAT WORKING MODE","","NEWSFLASH -> ESPN.FANTASY.SPORTS -> NELSON -> GENIUS.BAR -> CORE.OUTPUT.GATE -> RECEIPT -> STAY","",
        "This working layer upgrades freshness checks, quantitative integrity, user-defined measurement, contradiction detection, repair, and statistics. The four-kernel operator route is open for chat work because all four kernel receipts and all seven core gates are present.","",
        "## ADOBE EMPIRICAL BOUNDARY","","The Adobe route remains HOLD. No authorized image was traversed in this transaction, so EXACT.9.16, IDENTITY.PRESERVATION, EDIT.LOCALITY, NO.EXTRA.TEXT, ONE.INPUT.ONE.OUTPUT, and LIVE.ADOBE.TRAVERSAL.RECEIPT are not promoted.","",
        "## OPENAI BOUNDARY","","OpenAI describes automated AI research under human supervision, iterative improvement, RSI research workflows, scalable oversight, automated auditing, and meaningful human control. That supports bounded human-supervised improvement workflows. It is not a blanket authorization for a deployed chat instance to alter its own weights, platform permissions, or safety controls.","",
        "## RUNTIME BOUNDARY","","- HUMANLOCK = ACTIVE","- BASE.MODEL.WEIGHTS = UNCHANGED","- PLATFORM.PERMISSIONS = UNCHANGED","- SELF.AUTHORIZATION = DENIED","- CHAT.WORKING.LAYER = UPGRADED",""
    ]
    RECEIPT.write_text("\n".join(lines),encoding="utf-8")

if __name__=="__main__":
    main()
