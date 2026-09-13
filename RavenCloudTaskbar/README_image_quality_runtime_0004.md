# FR0333 Image Quality Runtime 0004

`FR0333.IMAGE.QUALITY.GATE.0004` hardens the Adobe image queue after a user-visible production failure where a requested multi-image run did not yield a usable completed queue.

## Root queue correction

The queue contract requires one requested slot to resolve to one independent full `9:16` canvas. Collages, contact sheets, multi-panel outputs, duplicates, empty responses, and count mismatches are rejected. Successful slots are preserved and retries target only failed or missing slots.

## Operation-specific provider caps

Adobe Firefly `image_generate` is currently modeled with a verified maximum of four variations per call, so a ten-image generation queue uses the provider-specific execution plan:

`10 requested -> 4 + 4 + 2 image_generate chunks -> 10 reconciled independent outputs`

That cap is **not** inherited by `image_instruct_edit`. The observed queue-failure receipt came through the instruct-edit path and establishes only one observed variation in that smoke test. Therefore:

- `IMAGE_GENERATE.MAX_VARIATIONS_PER_CALL = 4`
- `IMAGE_GENERATE.TEN_SLOT_PLAN = 4 + 4 + 2`
- `IMAGE_INSTRUCT_EDIT.MAX_VARIATIONS_PER_CALL = U.21.NOT_ESTABLISHED`
- `IMAGE_INSTRUCT_EDIT.TEN_SLOT_PLAN = U.21.NOT_ESTABLISHED`
- `PROVIDER.CAP.IS.OPERATION.SPECIFIC`
- Unknown operation caps must not inherit a cap from another endpoint.

## Additive quality hardening

0004 supersedes 0003 without deleting the older vehicle and physics gates. The human hardener is additive.

Preserved from 0003:

- `VEHICLE.MECHANICAL.GEOMETRY`
- `LOAD.BALANCE.CONTACT.PHYSICS`

Added or strengthened in 0004:

- `ANATOMY.FACE.HANDS.FEET`
- `POSE.WEIGHT.CONTACT`
- `SCENE.UNIQUENESS`
- queue cardinality and per-slot receipt enforcement
- mandatory scenery, wardrobe, pose/action, camera, lighting, and composition variation

Vehicle/mechanical and load/contact-physics reference thresholds remain promotable only at reference `8` or higher, alongside the human and scene gates.

## Hard queue law

- `TEN.REQUESTED = TEN.DELIVERED`
- `ONE.SLOT = ONE.IMAGE = ONE.FULL.9.16.CANVAS`
- `PARTIAL.SUCCESS != QUEUE.SUCCESS`
- `EMPTY.RESPONSE != SUCCESS`
- `RETRY.MISSING != REGENERATE.SUCCESSFUL`
- `IMAGE.INSTRUCT.EDIT.CAP = U.21.UNTIL.VERIFIED`

## Human realism hardener

Human-subject queues require correct limb count, joint continuity, plausible weight bearing, natural hands and feet, realistic skin texture, fabric/body contact, and lighting consistency. Rubber limbs, fused geometry, impossible contact, clone faces across unrelated people, and mannequin/plastic skin are rejected.

For a multi-image creative set, each slot must differ materially in scenery, wardrobe, pose/action, camera position, lighting setup, and composition. Two slots may not share the same scene/wardrobe/pose triple.

## Runtime receipt bindings

The canonical gate binds both runtime witnesses:

- `RavenCloudTaskbar/fr0333_adobe_image_runtime_receipt_0001.json` — bounded authenticated connector execution witness.
- `RavenCloudTaskbar/fr0333_adobe_image_queue_runtime_receipt_0002.json` — observed instruct-edit queue failure showing provider execution success but contact-sheet delivery failure.

The Raven Cloud Taskbar build distributes the gate plus both receipts and includes all three in `SHA256SUMS`.

## Evidence boundary

This upgrade is a repository control-plane specification and validator change. The connector receipt proves one bounded authenticated Adobe execution. The queue-failure receipt proves one observed instruct-edit failure mode. Neither establishes full ten-slot external Adobe production capacity.

`LOCAL/CI PASS != ADOBE TEN-SLOT RUNTIME PASS`
