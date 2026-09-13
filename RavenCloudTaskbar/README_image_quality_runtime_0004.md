# FR0333 Image Quality Runtime 0004

`FR0333.IMAGE.QUALITY.GATE.0004` hardens the Adobe image queue after a user-visible production failure where a requested multi-image run did not yield a usable completed queue.

## Root queue correction

The previous contract stated that input and output counts must match, but it did not encode the provider execution ceiling or a slot-level recovery plan. Adobe Firefly `image_generate` supports at most four variations in one call. A ten-image request therefore must not be submitted as one ten-output provider call.

The canonical ten-slot execution plan is:

`10 requested -> 4 + 4 + 2 provider chunks -> 10 reconciled independent outputs`

A queue is not complete until every requested slot has exactly one independent full-canvas output.

## Hard queue law

- `TEN.REQUESTED = TEN.DELIVERED`
- `ONE.SLOT = ONE.IMAGE = ONE.FULL.9.16.CANVAS`
- Collages, contact sheets, multi-panel outputs, duplicates, empty responses, and count mismatches are rejected.
- Successful slots are preserved. Retries target only failed or missing slots.
- A partial provider response is not a completed user queue.
- A silent or empty provider response is a failure, not success.

## Human realism hardener

Human-subject queues require correct limb count, joint continuity, plausible weight bearing, natural hands and feet, realistic skin texture, fabric/body contact, and lighting consistency. Rubber limbs, fused geometry, impossible contact, clone faces across unrelated people, and mannequin/plastic skin are rejected.

For a multi-image creative set, each slot must differ materially in scenery, wardrobe, pose/action, camera position, lighting setup, and composition. Two slots may not share the same scene/wardrobe/pose triple.

## Execution defaults

Adobe generation/editing remains quality-first, PNG, `9:16`, target `4MP`, with post-generation or post-edit visual readback required before promotion.

## Evidence boundary

This upgrade is a repository control-plane specification and validator change. The existing Adobe runtime receipt proves one bounded authenticated Adobe execution only. It does **not** establish full ten-slot external Adobe production capacity. A real ten-slot runtime requires its own per-slot provider receipts and cardinality reconciliation before any production-capacity claim can be promoted.

`LOCAL/CI PASS != ADOBE TEN-SLOT RUNTIME PASS`
