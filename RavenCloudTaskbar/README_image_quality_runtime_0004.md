# FR0333 Image Quality Runtime 0004

`FR0333.IMAGE.QUALITY.GATE.0004` hardens the Adobe image queue after an observed user-visible production failure while preserving the evidence boundary between repository validation and external provider runtime.

## Root queue correction

The queue contract requires one requested slot to resolve to one independent full `9:16` canvas. Collages, contact sheets, multi-panel outputs, duplicates, empty responses, and count mismatches are rejected. Successful slots are preserved and retries target only failed or missing slots.

## Operation-specific provider caps

Adobe Firefly `image_generate` is modeled with a verified maximum of four variations per call. The control-plane dispatcher therefore implements the native ten-slot plan:

`10 requested -> 4 + 4 + 2 image_generate batches -> 10 reconciled independent slot receipts`

This plan is implemented in the dispatcher; it is not evidence that a ten-output Adobe runtime has actually completed.

The cap is not inherited by `image_instruct_edit`:

- `IMAGE_GENERATE.MAX_VARIATIONS_PER_CALL = 4`
- `IMAGE_GENERATE.TEN_SLOT_PLAN = 4 + 4 + 2`
- `IMAGE_GENERATE.TEN_SLOT.PROVIDER.CALLS = 3`
- `IMAGE_INSTRUCT_EDIT.MAX_VARIATIONS_PER_CALL = U.21.NOT_ESTABLISHED`
- `IMAGE_INSTRUCT_EDIT.TEN_SLOT_PLAN = U.21.NOT_ESTABLISHED`
- `PROVIDER.CAP.IS.OPERATION.SPECIFIC`

## Exact output dimensions

Provider render level and user delivery dimensions are separate fields.

- provider render target: `4MP`
- delivery width: `1080`
- delivery height: `1920`
- delivery aspect ratio: `9:16`
- exact dimensions required: `true`

`9.16.RATIO != EXACT.1080x1920.DELIVERY`

A slot that is proportional to 9:16 but is not exactly `1080x1920` fails the delivery gate.

## Additive quality hardening

0004 supersedes 0003 without deleting the older vehicle and physics gates.

Preserved from 0003:

- `VEHICLE.MECHANICAL.GEOMETRY`
- `LOAD.BALANCE.CONTACT.PHYSICS`

Human-subject output also requires correct limb count, joint continuity, plausible weight bearing, natural hands and feet, realistic skin texture, fabric/body contact, and lighting consistency.

For a multi-image creative set, scenery, wardrobe, pose/action, camera position, lighting setup, and composition must vary materially by slot.

## Per-slot quality readback

One generic readback flag is insufficient. Each slot now requires separate:

- anatomy readback
- realism readback
- clothing-variance readback
- intent-alignment readback
- general readback state

All must equal `PASS` before slot promotion.

## Runtime receipt bindings

The gate continues to bind:

- `fr0333_adobe_image_runtime_receipt_0001.json` — one bounded authenticated connector execution witness.
- `fr0333_adobe_image_queue_runtime_receipt_0002.json` — one observed instruct-edit contact-sheet queue failure.

Neither receipt establishes upload-path proof, human-generation proof, exact `1080x1920` production proof, or ten-output Adobe runtime.

## Required system status

```text
BUILD.VALIDATION=T.20.PASS
CONNECTOR.RUNTIME=T.20.PASS.BOUNDED
QUALITY.PROMOTION=U.21.HOLD
QUEUE.RUNTIME=U.21.NOT.PROVEN
OVERALL.SYSTEM.STATUS=U.21.HOLD
```

`LOCAL/CI PASS != ADOBE TEN-SLOT RUNTIME PASS`

This baseline remains an active repair target; it is not frozen.
