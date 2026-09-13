# FR0333 Adobe Human Realism Diversity Patch 0004

`FR0333.ADOBE.HUMAN.REALISM.DIVERSITY.PATCH.0004` is a fail-closed FR0333 orchestration patch for human-image production. It does **not** modify Adobe internals and does **not** establish live Adobe runtime by itself.

## Failure class addressed

The patch targets a recurring production failure where a request for multiple distinct human images can return outputs that are technically photorealistic but still fail the user intent through clone-like faces, repeated bodies, repeated scenery, repeated wardrobe, repeated camera setups, repeated lighting, collage/contact-sheet behavior, missing images, or synthetic-looking anatomy.

## Core controls

- `ONE.SLOT = ONE.PROMPT = ONE.CANVAS = ONE.IMAGE`
- `N.REQUESTED = N.SLOTS = N.OUTPUTS`
- every slot is `9:16`
- collage/contact-sheet output is rejected
- duplicate and missing outputs are rejected
- human requests require anatomy, hands, joints, contact physics, skin microvariation, eye/gaze, hair, and fabric/body realism checks
- `PHOTOREALISTIC.STYLE != HUMAN.REALISM`
- `REMAKE != CLONE`
- style reference does not authorize identity copying
- same face across scenes is rejected unless identity continuity is explicitly requested
- when the user requests every image to be different, scene, wardrobe, pose/action, camera setup, lighting, background, and cast must all be unique per slot
- visual readback is required for every output
- a failed slot is held and regenerated independently; passing slots are preserved
- user rejection overrides provider success

## Deterministic ten-slot fixture

`fr0333_adobe_human_realism_manifest_0004.json` contains Q01 through Q10 with ten different scenes, wardrobes, actions, camera setups, lighting setups, backgrounds, and distinct-cast identity modes. It exists to prove the orchestration contract, not to claim that an external provider has generated those images.

## Validation

`fr0333_adobe_human_realism_patch_genius.py` validates the patch and manifest. The test rail intentionally mutates the good manifest to verify fail-closed behavior for repeated scene, repeated wardrobe, repeated camera setup, count mismatch, slot-sequence collision, missing fields, and unintended continuity-cast reuse.

## Evidence boundary

`LOCAL.CI.PASS != EXTERNAL.ADOBE.RUNTIME`

`PROVIDER.SUCCESS != QUALITY.PASS`

`THIS.PATCH != ADOBE.INTERNAL.MODEL.MODIFICATION`

A real external Adobe execution still requires a provider/runtime receipt plus post-output visual readback before any production-quality claim may be promoted.
