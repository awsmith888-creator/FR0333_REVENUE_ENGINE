# FR0333 Adobe Runtime Examples 0001

This record binds the selected Adobe visual examples to the bounded external runtime witness already carried by `FR0333.ADOBE.IMAGE.QUEUE.RUNTIME.RECEIPT.0003`.

It does not create a new lane, taskbar slot, or universal Adobe-capacity claim. HumanLock remains active.

## What made the ten-slot queue work

The live connected Adobe runtime did not behave like the earlier repository assumption that the schema maximum of four variations implied four connected-runtime outputs per call. A four-variation probe returned one output. The safe operating rule was therefore reduced to one provider output per call.

The observed path was:

`PROMPT_COMPILE -> SINGLETON_DISPATCH -> PROVIDER_RECEIPT -> NATIVE_DIMENSION_OBSERVE -> NORMALIZE_1080x1920 -> PER_SLOT_VISUAL_READBACK -> COUNT_RECONCILE -> RETRY_FAILED_SLOT_ONLY -> HUMANLOCK -> RECEIPT -> CHOMP -> CHOMP -> STAY`

For ten requested images this means ten independent provider calls. Successful slots are preserved and are not regenerated merely because another slot fails.

## Dimension correction

A generation requested at 1080x1920 was observed at 1072x1920 from the connected generation runtime. Native output therefore did not satisfy the exact delivery contract.

Each affected image was normalized with `image_crop_and_resize` to exact 1080x1920 and then visually read back again before the slot could pass.

`REQUESTED.1080x1920 != OBSERVED.NATIVE.1080x1920`

`NATIVE.1072x1920 -> NORMALIZE -> 1080x1920`

## Failure recovery that was actually observed

The first pass of Q09 failed intent alignment because a human reflection appeared where the scene contract required no person. Q01-Q08 and Q10 were preserved. Only Q09 was regenerated, normalized, and read back again. Its retry passed.

`FAILED.Q09 -> RETRY.Q09`

`RETRY.FAILED.SLOT != REGENERATE.SUCCESSFUL.SLOTS`

The final bounded diagnostic queue therefore ended with ten requested, ten delivered, ten independent slots, no final collage/contact sheet, and exact 1080x1920 delivery after normalization.

## Visual example family

The selected example set contains 19 Adobe assets. The six strongest black-onyx/platinum visual anchors are:

- A01.SPHERE — polished platinum sphere
- A04.STEPPED.MONOLITH — platinum stepped monolith
- A06.SPIRAL — platinum spiral sculpture
- A08.PYRAMID — faceted platinum pyramid
- A10.RING — platinum ring sculpture
- A11.FLOATING.CUBE — floating platinum cube

These are reference artifacts for visual language and quality comparison. They do not become mandatory copies or templates for future generations.

## Additional bounded runtime examples

The selected set also retains examples of human generation, instructed editing, a dark-background edit, diagnostic images, prior documentary/editorial generations, and a full-frame 9:16 example.

The complete stable Adobe asset URNs and roles are stored in `fr0333_adobe_runtime_examples_inventory_0001.json`.

## User acceptance observation

The user positively accepted the selected 19-asset set as visually strong. That observation is bound only to the selected set.

`SELECTED.SET.USER.ACCEPTANCE = T.20`

`SELECTED.SET.USER.ACCEPTANCE != UNIVERSAL.ADOBE.QUALITY.PROMOTION`

## Evidence boundary

What is established within the observed domain:

- connected Adobe generation execution
- ten-slot singleton dispatch
- ten final independent outputs
- exact 1080x1920 delivery after normalization
- visual readback
- failed-slot-only retry behavior
- bounded human generation
- bounded instructed editing
- bounded Lightroom preset execution
- generated-asset persistence in Adobe storage
- positive user acceptance for the selected 19-asset visual set

What is not established:

- every Adobe product surface
- every future prompt or input
- universal uptime or throughput
- universal aesthetic acceptance
- autonomous canonical promotion

`TEN.SLOT.RUNTIME.PASS != UNIVERSAL.ADOBE.PRODUCT.CAPACITY`

`HUMANLOCK = ACTIVE`
