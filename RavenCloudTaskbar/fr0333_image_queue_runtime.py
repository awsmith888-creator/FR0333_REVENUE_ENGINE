#!/usr/bin/env python3
import hashlib
import json
from dataclasses import dataclass, asdict
from typing import Callable, Dict, Iterable, List, Optional


TARGET_ASPECT = "9:16"


class QueueIntegrityError(RuntimeError):
    pass


@dataclass(frozen=True)
class SlotIntent:
    slot_id: str
    intent_hash: str
    scene_contract: str
    reference_policy: str
    input_reference_ids: List[str]


@dataclass(frozen=True)
class SlotReceipt:
    slot_id: str
    intent_hash: str
    scene_contract: str
    reference_policy: str
    input_reference_ids: List[str]
    output_asset_id: str
    width: int
    height: int
    aspect_ratio: str
    provider_request_id: str
    visual_fingerprint: str
    readback_state: str
    user_state: str
    execution_state: str = "PASS_RUNTIME"
    collage_detected: bool = False
    multi_panel_detected: bool = False


def _stable_hash(payload: Dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def compile_slots(scene_contracts: List[Dict], reference_policy: str = "INDEPENDENT_SLOT") -> List[SlotIntent]:
    if not 1 <= len(scene_contracts) <= 10:
        raise QueueIntegrityError("queue size must be between 1 and 10")

    slots: List[SlotIntent] = []
    for index, scene in enumerate(scene_contracts, start=1):
        slot_id = f"Q{index:02d}"
        scene_text = str(scene.get("scene_contract", "")).strip()
        if not scene_text:
            raise QueueIntegrityError(f"{slot_id} missing scene_contract")
        refs = list(scene.get("input_reference_ids", []))
        payload = {
            "slot_id": slot_id,
            "scene_contract": scene_text,
            "reference_policy": reference_policy,
            "input_reference_ids": refs,
        }
        slots.append(
            SlotIntent(
                slot_id=slot_id,
                intent_hash=_stable_hash(payload),
                scene_contract=scene_text,
                reference_policy=reference_policy,
                input_reference_ids=refs,
            )
        )
    return slots


def dispatch_slots(slots: Iterable[SlotIntent], provider_call: Callable[[SlotIntent], SlotReceipt]) -> List[SlotReceipt]:
    receipts: List[SlotReceipt] = []
    for slot in slots:
        receipt = provider_call(slot)
        if receipt.slot_id != slot.slot_id:
            raise QueueIntegrityError(f"receipt slot mismatch: expected {slot.slot_id}, got {receipt.slot_id}")
        if receipt.intent_hash != slot.intent_hash:
            raise QueueIntegrityError(f"intent hash mismatch for {slot.slot_id}")
        receipts.append(receipt)
    return receipts


def reconcile(slots: List[SlotIntent], receipts: List[SlotReceipt]) -> Dict:
    requested = len(slots)
    slot_ids = [slot.slot_id for slot in slots]
    receipt_by_slot = {receipt.slot_id: receipt for receipt in receipts}
    duplicate_slot_ids = len(receipt_by_slot) != len(receipts)

    missing_slots = [slot_id for slot_id in slot_ids if slot_id not in receipt_by_slot]
    unexpected_slots = sorted(set(receipt_by_slot) - set(slot_ids))

    output_assets = [r.output_asset_id for r in receipts if r.output_asset_id]
    request_ids = [r.provider_request_id for r in receipts if r.provider_request_id]
    fingerprints = [r.visual_fingerprint for r in receipts if r.visual_fingerprint]

    duplicate_output_assets = len(output_assets) != len(set(output_assets))
    duplicate_provider_requests = len(request_ids) != len(set(request_ids))
    duplicate_visual_fingerprints = len(fingerprints) != len(set(fingerprints))

    failed_slots = [
        r.slot_id
        for r in receipts
        if r.execution_state != "PASS_RUNTIME"
        or r.readback_state != "PASS"
        or r.aspect_ratio != TARGET_ASPECT
        or r.collage_detected
        or r.multi_panel_detected
        or not r.output_asset_id
        or not r.provider_request_id
        or not r.visual_fingerprint
    ]

    collage_slots = [r.slot_id for r in receipts if r.collage_detected or r.multi_panel_detected]

    count_ok = requested == len(receipts)
    unique_assets_ok = len(output_assets) == requested and len(set(output_assets)) == requested
    unique_requests_ok = len(request_ids) == requested and len(set(request_ids)) == requested
    unique_fingerprints_ok = len(fingerprints) == requested and len(set(fingerprints)) == requested

    queue_pass = all(
        [
            count_ok,
            not duplicate_slot_ids,
            not missing_slots,
            not unexpected_slots,
            not duplicate_output_assets,
            not duplicate_provider_requests,
            not duplicate_visual_fingerprints,
            not failed_slots,
            not collage_slots,
            unique_assets_ok,
            unique_requests_ok,
            unique_fingerprints_ok,
        ]
    )

    return {
        "identifier": "FR0333.IMAGE.QUEUE.RUNTIME.RECEIPT.CHECK.0001",
        "state": "T.20.PASS" if queue_pass else "F.6.REJECT",
        "requested_count": requested,
        "output_count": len(receipts),
        "receipt_count": len(receipts),
        "unique_output_asset_ids": len(set(output_assets)),
        "unique_provider_request_ids": len(set(request_ids)),
        "unique_visual_fingerprints": len(set(fingerprints)),
        "missing_slots": missing_slots,
        "unexpected_slots": unexpected_slots,
        "failed_slots": sorted(set(failed_slots)),
        "collage_slots": sorted(set(collage_slots)),
        "duplicate_output_assets": duplicate_output_assets,
        "duplicate_provider_requests": duplicate_provider_requests,
        "duplicate_visual_fingerprints": duplicate_visual_fingerprints,
        "retry_slots": sorted(set(missing_slots + failed_slots)),
        "preserve_slots": sorted(
            slot_id
            for slot_id in slot_ids
            if slot_id not in set(missing_slots + failed_slots)
        ),
        "external_runtime_state": "U.21.HOLD_UNLESS_RECEIPTS_ARE_REAL_PROVIDER_RECEIPTS",
    }


def receipt_to_dict(receipt: SlotReceipt) -> Dict:
    return asdict(receipt)


def main() -> None:
    print("FR0333.IMAGE.QUEUE.RUNTIME.0001 provider-neutral dispatcher loaded")


if __name__ == "__main__":
    main()
