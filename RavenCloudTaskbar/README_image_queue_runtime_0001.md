# FR0333 Image Queue Runtime 0001

`FR0333.IMAGE.QUEUE.RUNTIME.0001` is the provider-neutral queue dispatcher and reconciler for multi-image requests.

It exists because a queue contract in configuration does not prove queue execution. The runtime rail therefore separates specification, local dispatcher behavior, bounded single-image provider evidence, and external multi-slot provider execution.

## Pipeline

`USER.REQUEST -> INTENT.COMPILE -> SLOT.SPLIT -> SLOT.ISOLATION -> ONE.PROVIDER.REQUEST.PER.SLOT -> PER.SLOT.RECEIPT -> VISUAL.READBACK -> DUPLICATE.DETECTION -> COUNT.RECONCILIATION -> HUMANLOCK -> OUTPUT`

For ten requested images, the dispatcher compiles ten independent slots: `Q01` through `Q10`. Each slot receives its own intent hash, scene contract, reference policy, provider request, output asset, visual fingerprint, readback state, and user state.

## Queue pass law

The queue passes only when all of the following are true:

- requested count equals output count
- requested count equals receipt count
- unique output asset IDs equal requested count
- unique provider request IDs equal requested count
- unique visual fingerprints equal requested count for distinct-scene jobs
- failed slots equal zero
- duplicate slots equal zero
- collage/contact-sheet/multi-panel slots equal zero
- all slots complete readback

`ONE.REQUEST.TEN.VARIANTS != TEN.ISOLATED.REQUESTS`

## Surgical retry

A failure in one slot does not authorize re-generation of successful slots.

`FAILED.Q04 -> RETRY.Q04`

not

`FAILED.Q04 -> REGENERATE.Q01.THROUGH.Q10`

The reconciler emits `retry_slots` and `preserve_slots` separately so successful outputs remain outside the failed slot's visual ancestry loop.

## Deterministic test rail

`test_fr0333_image_queue_runtime.py` runs a provider-neutral ten-slot simulation that actually calls the adapter once per slot and requires ten distinct runtime receipt objects. It also rejects count mismatch, duplicate output assets, duplicate visual fingerprints, contact-sheet output, slot/receipt mismatch, and broad retry behavior.

This is materially different from counting validation gates. A passing ten-slot simulation establishes dispatcher and reconciliation behavior only.

## Evidence boundary

- `QUEUE.SPEC.PASS != QUEUE.RUNTIME.PASS`
- `COUNT.CONTRACT.PRESENT != COUNT.EXECUTED`
- `SLOT.DEFINED != SLOT.ISOLATED`
- `PROVIDER.SUCCESS != QUEUE.INTEGRITY`
- `PROMPT.DIVERSITY != VISUAL.DIVERSITY`
- `LOCAL.SIMULATION.PASS != EXTERNAL.PROVIDER.RUNTIME.PASS`
- `GITHUB.SPECIFICATION != CHATGPT.INTERNAL.IMAGE.RUNTIME.CONTROL`

Current external state remains `U.21.HOLD` for multi-slot provider runtime and ten-slot isolation until ten real per-slot provider receipts are captured and reconciled.
