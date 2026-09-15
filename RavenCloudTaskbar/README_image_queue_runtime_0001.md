# FR0333 Image Queue Runtime 0001

`FR0333.IMAGE.QUEUE.RUNTIME.0001` is the provider-neutral queue dispatcher and reconciler for multi-image requests.

It exists because a queue contract in configuration does not prove queue execution. The runtime rail separates repository validation, bounded single-image provider evidence, operation-specific provider batching, and external multi-slot execution.

## Dispatch modes

For `IMAGE_GENERATE`, the verified provider cap is four variations per call. A ten-slot generation queue therefore uses native provider batching:

`10 requested -> 4 + 4 + 2 IMAGE_GENERATE calls -> 10 isolated slot receipts`

The same provider request ID may appear on several outputs from one verified batch. Slot identity is therefore bound to the provider output coordinate:

`provider_request_id + provider_variation_index`

For `IMAGE_INSTRUCT_EDIT`, the provider cap remains `U.21.NOT_ESTABLISHED`. The safe dispatcher stays singleton until that endpoint is independently verified.

`PROVIDER.CAP.IS.OPERATION.SPECIFIC`

## Exact delivery contract

A `9:16` ratio by itself is not enough.

Every promotable output slot must be:

- width `1080`
- height `1920`
- aspect ratio `9:16`
- one independent image
- no collage, contact sheet, or multi-panel composition

`9.16.RATIO != EXACT.1080x1920.DELIVERY`

## Per-slot readback

Each slot carries separate readback fields rather than one generic quality flag:

- `readback_state`
- `anatomy_readback`
- `realism_readback`
- `clothing_variance_readback`
- `intent_alignment_readback`

Every field must be `PASS` before that slot can pass reconciliation.

## Queue pass law

The queue passes only when requested count, output count, and receipt count match; output asset IDs, provider output coordinates, and visual fingerprints are unique; all slots are exactly `1080x1920`; all per-slot readbacks pass; and no collage/contact-sheet/multi-panel output is present.

For a ten-slot `IMAGE_GENERATE` run, the reconciler additionally requires the `4 + 4 + 2` batch plan and three provider requests.

## Surgical retry

A failure in one slot does not authorize regeneration of successful slots.

`FAILED.Q04 -> RETRY.Q04`

not

`FAILED.Q04 -> REGENERATE.Q01.THROUGH.Q10`

## Deterministic validation

`test_fr0333_image_queue_runtime.py` verifies the provider-neutral control plane. It tests native `4 + 4 + 2` generation batching, conservative singleton instruct-edit dispatch, exact `1080x1920` enforcement, separate anatomy/realism/clothing/intent readbacks, count mismatch, duplicates, contact sheets, slot/receipt mismatch, and surgical retry.

A passing test establishes repository dispatcher and reconciliation behavior only.

## Evidence boundary

- `BUILD.VALIDATION.PASS != ADOBE.RUNTIME.PASS`
- `NATIVE.4.4.2.PLAN.DEFINED != TEN.OUTPUT.ADOBE.RUNTIME.PROVEN`
- `9.16.RATIO != EXACT.1080x1920.DELIVERY`
- `GENERIC.READBACK != ANATOMY.REALISM.CLOTHING.INTENT.READBACK`
- `LOCAL.SIMULATION.PASS != EXTERNAL.PROVIDER.RUNTIME.PASS`
- `GITHUB.SPECIFICATION != CHATGPT.INTERNAL.IMAGE.RUNTIME.CONTROL`

Required status remains:

```text
BUILD.VALIDATION=T.20.PASS
CONNECTOR.RUNTIME=T.20.PASS.BOUNDED
QUALITY.PROMOTION=U.21.HOLD
QUEUE.RUNTIME=U.21.NOT.PROVEN
OVERALL.SYSTEM.STATUS=U.21.HOLD
```

The baseline is patched, not frozen. External ten-slot Adobe runtime remains unproven until real provider receipts establish it.
