#!/usr/bin/env python3
import hashlib
import json
from dataclasses import dataclass, asdict
from typing import Callable, Dict, Iterable, List, Sequence


TARGET_ASPECT = "9:16"
TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920
IMAGE_GENERATE = "IMAGE_GENERATE"
IMAGE_INSTRUCT_EDIT = "IMAGE_INSTRUCT_EDIT"
IMAGE_GENERATE_MAX_VARIATIONS = 4
READBACK_PASS = "PASS"


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
    provider_variation_index: int
    batch_index: int
    batch_size: int
    visual_fingerprint: str
    readback_state: str
    anatomy_readback: str
    realism_readback: str
    clothing_variance_readback: str
    intent_alignment_readback: str
    user_state: str
    operation: str = IMAGE_GENERATE
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


def image_generate_chunk_plan(slot_count: int) -> List[int]:
    if not 1 <= slot_count <= 10:
        raise QueueIntegrityError("queue size must be between 1 and 10")
    remaining = slot_count
    plan = []
    while remaining:
        size = min(IMAGE_GENERATE_MAX_VARIATIONS, remaining)
        plan.append(size)
        remaining -= size
    return plan


def _chunks(slots: Sequence[SlotIntent], plan: Sequence[int]) -> Iterable[List[SlotIntent]]:
    cursor = 0
    for size in plan:
        batch = list(slots[cursor:cursor + size])
        if len(batch) != size:
            raise QueueIntegrityError("chunk plan exceeds available slots")
        yield batch
        cursor += size
    if cursor != len(slots):
        raise QueueIntegrityError("chunk plan did not consume all slots")


def _validate_receipt_binding(slot: SlotIntent, receipt: SlotReceipt) -> None:
    if receipt.slot_id != slot.slot_id:
        raise QueueIntegrityError(f"receipt slot mismatch: expected {slot.slot_id}, got {receipt.slot_id}")
    if receipt.intent_hash != slot.intent_hash:
        raise QueueIntegrityError(f"intent hash mismatch for {slot.slot_id}")


def dispatch_slots(
    slots: Iterable[SlotIntent],
    provider_call: Callable,
    operation: str = IMAGE_GENERATE,
) -> List[SlotReceipt]:
    slots = list(slots)
    receipts: List[SlotReceipt] = []

    if operation == IMAGE_GENERATE:
        plan = image_generate_chunk_plan(len(slots))
        for batch_index, batch in enumerate(_chunks(slots, plan), start=1):
            batch_receipts = provider_call(batch, batch_index)
            if not isinstance(batch_receipts, list):
                raise QueueIntegrityError(f"batch {batch_index} provider response must be a list")
            if len(batch_receipts) != len(batch):
                raise QueueIntegrityError(
                    f"batch {batch_index} cardinality mismatch: requested {len(batch)}, got {len(batch_receipts)}"
                )
            for variation_index, (slot, receipt) in enumerate(zip(batch, batch_receipts), start=1):
                _validate_receipt_binding(slot, receipt)
                if receipt.operation != IMAGE_GENERATE:
                    raise QueueIntegrityError(f"{slot.slot_id} operation mismatch")
                if receipt.batch_index != batch_index:
                    raise QueueIntegrityError(f"{slot.slot_id} batch index mismatch")
                if receipt.batch_size != len(batch):
                    raise QueueIntegrityError(f"{slot.slot_id} batch size mismatch")
                if receipt.provider_variation_index != variation_index:
                    raise QueueIntegrityError(f"{slot.slot_id} variation index mismatch")
                receipts.append(receipt)
        return receipts

    if operation == IMAGE_INSTRUCT_EDIT:
        # Capacity is not independently verified for this operation.
        # Fail safe by dispatching singletons until a provider-specific cap is proven.
        for batch_index, slot in enumerate(slots, start=1):
            receipt = provider_call(slot)
            _validate_receipt_binding(slot, receipt)
            if receipt.operation != IMAGE_INSTRUCT_EDIT:
                raise QueueIntegrityError(f"{slot.slot_id} operation mismatch")
            if receipt.batch_index != batch_index or receipt.batch_size != 1:
                raise QueueIntegrityError(f"{slot.slot_id} singleton batch metadata mismatch")
            if receipt.provider_variation_index != 1:
                raise QueueIntegrityError(f"{slot.slot_id} singleton variation index mismatch")
            receipts.append(receipt)
        return receipts

    raise QueueIntegrityError(f"unsupported operation: {operation}")


def reconcile(slots: List[SlotIntent], receipts: List[SlotReceipt], operation: str = IMAGE_GENERATE) -> Dict:
    requested = len(slots)
    slot_ids = [slot.slot_id for slot in slots]
    receipt_by_slot = {receipt.slot_id: receipt for receipt in receipts}
    duplicate_slot_ids = len(receipt_by_slot) != len(receipts)

    missing_slots = [slot_id for slot_id in slot_ids if slot_id not in receipt_by_slot]
    unexpected_slots = sorted(set(receipt_by_slot) - set(slot_ids))

    output_assets = [r.output_asset_id for r in receipts if r.output_asset_id]
    provider_output_coordinates = [
        (r.provider_request_id, r.provider_variation_index)
        for r in receipts
        if r.provider_request_id and r.provider_variation_index > 0
    ]
    fingerprints = [r.visual_fingerprint for r in receipts if r.visual_fingerprint]
    request_ids = [r.provider_request_id for r in receipts if r.provider_request_id]

    duplicate_output_assets = len(output_assets) != len(set(output_assets))
    duplicate_provider_outputs = len(provider_output_coordinates) != len(set(provider_output_coordinates))
    duplicate_visual_fingerprints = len(fingerprints) != len(set(fingerprints))

    readback_fields = (
        "readback_state",
        "anatomy_readback",
        "realism_readback",
        "clothing_variance_readback",
        "intent_alignment_readback",
    )
    readback_failures = {
        r.slot_id: [field for field in readback_fields if getattr(r, field) != READBACK_PASS]
        for r in receipts
    }
    readback_failures = {k: v for k, v in readback_failures.items() if v}

    exact_dimension_failures = [
        r.slot_id for r in receipts
        if r.width != TARGET_WIDTH or r.height != TARGET_HEIGHT
    ]

    expected_plan = image_generate_chunk_plan(requested) if operation == IMAGE_GENERATE else [1] * requested
    expected_batch_by_slot = {}
    slot_cursor = 0
    for batch_index, batch_size in enumerate(expected_plan, start=1):
        for variation_index in range(1, batch_size + 1):
            if slot_cursor >= requested:
                break
            expected_batch_by_slot[slot_ids[slot_cursor]] = (batch_index, batch_size, variation_index)
            slot_cursor += 1

    batch_metadata_failures = [
        r.slot_id
        for r in receipts
        if expected_batch_by_slot.get(r.slot_id) != (r.batch_index, r.batch_size, r.provider_variation_index)
        or r.operation != operation
    ]

    failed_slots = [
        r.slot_id
        for r in receipts
        if r.execution_state != "PASS_RUNTIME"
        or r.readback_state != READBACK_PASS
        or r.anatomy_readback != READBACK_PASS
        or r.realism_readback != READBACK_PASS
        or r.clothing_variance_readback != READBACK_PASS
        or r.intent_alignment_readback != READBACK_PASS
        or r.aspect_ratio != TARGET_ASPECT
        or r.width != TARGET_WIDTH
        or r.height != TARGET_HEIGHT
        or r.collage_detected
        or r.multi_panel_detected
        or not r.output_asset_id
        or not r.provider_request_id
        or not r.visual_fingerprint
        or r.slot_id in batch_metadata_failures
    ]

    collage_slots = [r.slot_id for r in receipts if r.collage_detected or r.multi_panel_detected]

    count_ok = requested == len(receipts)
    unique_assets_ok = len(output_assets) == requested and len(set(output_assets)) == requested
    unique_provider_outputs_ok = (
        len(provider_output_coordinates) == requested
        and len(set(provider_output_coordinates)) == requested
    )
    unique_fingerprints_ok = len(fingerprints) == requested and len(set(fingerprints)) == requested

    if operation == IMAGE_GENERATE:
        expected_provider_call_count = len(expected_plan)
        provider_call_count_ok = len(set(request_ids)) == expected_provider_call_count
    else:
        expected_provider_call_count = requested
        provider_call_count_ok = len(set(request_ids)) == requested

    queue_pass = all(
        [
            count_ok,
            not duplicate_slot_ids,
            not missing_slots,
            not unexpected_slots,
            not duplicate_output_assets,
            not duplicate_provider_outputs,
            not duplicate_visual_fingerprints,
            not failed_slots,
            not collage_slots,
            not readback_failures,
            not exact_dimension_failures,
            not batch_metadata_failures,
            unique_assets_ok,
            unique_provider_outputs_ok,
            unique_fingerprints_ok,
            provider_call_count_ok,
        ]
    )

    return {
        "identifier": "FR0333.IMAGE.QUEUE.RUNTIME.RECEIPT.CHECK.0002",
        "state": "T.20.PASS" if queue_pass else "F.6.REJECT",
        "operation": operation,
        "requested_count": requested,
        "output_count": len(receipts),
        "receipt_count": len(receipts),
        "expected_batch_plan": expected_plan,
        "provider_call_count": len(set(request_ids)),
        "expected_provider_call_count": expected_provider_call_count,
        "unique_output_asset_ids": len(set(output_assets)),
        "unique_provider_output_coordinates": len(set(provider_output_coordinates)),
        "unique_visual_fingerprints": len(set(fingerprints)),
        "missing_slots": missing_slots,
        "unexpected_slots": unexpected_slots,
        "failed_slots": sorted(set(failed_slots)),
        "readback_failures": readback_failures,
        "exact_dimension_failures": sorted(set(exact_dimension_failures)),
        "batch_metadata_failures": sorted(set(batch_metadata_failures)),
        "collage_slots": sorted(set(collage_slots)),
        "duplicate_output_assets": duplicate_output_assets,
        "duplicate_provider_outputs": duplicate_provider_outputs,
        "duplicate_visual_fingerprints": duplicate_visual_fingerprints,
        "retry_slots": sorted(set(missing_slots + failed_slots)),
        "preserve_slots": sorted(
            slot_id
            for slot_id in slot_ids
            if slot_id not in set(missing_slots + failed_slots)
        ),
        "external_runtime_state": "U.21.NOT.PROVEN_UNLESS_RECEIPTS_ARE_REAL_PROVIDER_RECEIPTS",
    }


def receipt_to_dict(receipt: SlotReceipt) -> Dict:
    return asdict(receipt)


def main() -> None:
    print("FR0333.IMAGE.QUEUE.RUNTIME.0001 provider-neutral dispatcher loaded")
    print("IMAGE_GENERATE.TEN_SLOT_PLAN=4+4+2")
    print("QUEUE.RUNTIME=U.21.NOT.PROVEN")


if __name__ == "__main__":
    main()
