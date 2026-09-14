from dataclasses import dataclass
from typing import Dict, Any

KERNELS=(("K1","NEWSFLASH"),("K2","ESPN.FANTASY.SPORTS"),("K3","NELSON"),("K4","GENIUS.BAR"))
CORE_GATES=("SOURCE.TIMESTAMP","FORMULA.LABEL.MATCH","NUMERATOR.DENOMINATOR.MATCH","SAMPLE.SIZE","NELSON.KERNEL.RECEIPT","FAILURE.REPAIR.RECEIPT","ROLLBACK.PATH")
ADOBE_GATES=("EXACT.9.16","IDENTITY.PRESERVATION","EDIT.LOCALITY","NO.EXTRA.TEXT","ONE.INPUT.ONE.OUTPUT")

@dataclass(frozen=True)
class KernelResult:
    name:str
    passed:bool
    receipt:Dict[str,Any]

def _nonempty(value:Any)->bool:
    return value not in (None,"",[],{})

def evaluate_four_kernel_transaction(transaction:Dict[str,Any])->Dict[str,Any]:
    results=[]; bits=[]
    for _,kernel_name in KERNELS:
        record=transaction.get("kernels",{}).get(kernel_name,{})
        passed=bool(record.get("passed")) and _nonempty(record.get("receipt"))
        results.append(KernelResult(kernel_name,passed,record.get("receipt",{})))
        bits.append("1" if passed else "0")
    bitword="".join(bits)
    core={gate:bool(transaction.get("core_gates",{}).get(gate)) for gate in CORE_GATES}
    adobe={gate:bool(transaction.get("adobe_gates",{}).get(gate)) for gate in ADOBE_GATES}
    adobe_receipt=_nonempty(transaction.get("adobe_execution_receipt"))
    stats_in=transaction.get("statistics",{})
    stats={
        "kernel_count":4,"active_kernel_count":sum(r.passed for r in results),"kernel_pass_rate":sum(r.passed for r in results)/4.0,
        "kernel_bitword":bitword,"decimal_state":int(bitword,2),
        "required_core_gate_count":len(CORE_GATES),"passed_core_gate_count":sum(core.values()),"core_gate_pass_rate":sum(core.values())/len(CORE_GATES),
        "required_adobe_gate_count":len(ADOBE_GATES),"passed_adobe_gate_count":sum(adobe.values()),"adobe_gate_pass_rate":sum(adobe.values())/len(ADOBE_GATES),
        "source_count":int(stats_in.get("source_count",0)),"metric_count":int(stats_in.get("metric_count",0)),"sample_size":int(stats_in.get("sample_size",0)),
        "contradiction_count":int(stats_in.get("contradiction_count",0)),"repair_attempt_count":int(stats_in.get("repair_attempt_count",0)),"repair_success_count":int(stats_in.get("repair_success_count",0)),
        "truth_t20_count":int(stats_in.get("truth_t20_count",0)),"truth_u21_count":int(stats_in.get("truth_u21_count",0)),"truth_f6_count":int(stats_in.get("truth_f6_count",0)),
    }
    operator_open=bitword=="1111" and all(core.values())
    adobe_open=operator_open and all(adobe.values()) and adobe_receipt
    return {
        "record_id":"FR0333.OPERATOR.FOUR.KERNEL.UPGRADE.0001",
        "architecture_id":"FR0333.ADOBE.FOUR.KERNEL.HARDENER.0001",
        "kernels":{r.name:{"passed":r.passed,"receipt_present":bool(r.receipt)} for r in results},
        "core_gates":core,"adobe_gates":adobe,"statistics":stats,
        "operator_route":"OPEN" if operator_open else "HOLD",
        "adobe_route":"OPEN" if adobe_open else "HOLD",
        "adobe_live_traversal_receipt":"T.20" if adobe_receipt else "U.21",
        "humanlock":"ACTIVE","base_model_weights":"UNCHANGED","platform_permissions":"UNCHANGED",
    }
