# FR0333 Image Quality Runtime 0003

`FR0333.IMAGE.QUALITY.GATE.0003` extends the existing image-quality control plane with explicit photorealism, physical-coherence, Adobe execution, and readback requirements.

## Why this exists

A provider can successfully return an image that is still visually weak. The controlling boundary is:

```text
PROVIDER.SUCCESS != QUALITY.PASS
PHOTOREALISTIC.STYLE != PHYSICALLY.COHERENT
TONE.IMPROVEMENT != STRUCTURAL.REALISM.REPAIR
ADOBE.CONNECTOR.SUCCESS != USER.ACCEPTANCE
```

The user explicitly rejected the preceding ten-image motorcycle set as insufficiently realistic. That rejection is evidence for `OUTPUT.HOLD`; it is not silently converted into a pass.

## Photorealism gate

Fourteen dimensions are required:

1. identity fidelity
2. anatomy / face / hands
3. vehicle mechanical geometry
4. load / balance / contact physics
5. camera geometry
6. motion-blur coherence
7. light / shadow / reflection
8. material / texture realism
9. background scale / depth
10. crop / frame integrity
11. artifact / text / logo control
12. aesthetic coherence
13. user-intent match
14. visual readback

A quality reference below `8` on a required promotion dimension holds the output.

## Adobe defaults

For the Adobe image path, the specification requires quality-first execution where available:

```text
PROMPT.REASONER = quality
TARGET.RESOLUTION = 4MP
OUTPUT = PNG
POST.EDIT.READBACK = REQUIRED
```

These are execution defaults, not proof that an image is good.

## Bounded runtime witness

`fr0333_adobe_image_runtime_receipt_0001.json` records a real Adobe connector invocation against one motorcycle image. The edit operation returned a provider request ID and an Adobe output asset, so bounded connector runtime is established for that one operation.

The output was then visually read back. Quality promotion remains `U.21.HOLD` because one generic realism edit does not establish all fourteen quality dimensions at the promotable threshold, and the edited output has not been accepted by the user.

Therefore:

```text
ADOBE.SINGLE.EDIT.RUNTIME = T.20.PASS
PHOTOREALISM.PROMOTION = U.21.HOLD
ADOBE.FULL.PRODUCTION.CAPACITY = NOT.ESTABLISHED
```

This preserves the distinction between a functioning connector and a production system that consistently produces acceptable images.

## Queue law

```text
N.IN = N.OUT
ONE.RUN = ONE.CANVAS = ONE.IMAGE
COLLAGE = REJECT
DUPLICATE = REJECT
COUNT.MISMATCH = REJECT
```

For multiple remakes, each input gets an independent 9:16 output.

## Validation

```bash
cd RavenCloudTaskbar
python3 fr0333_image_quality_runtime_genius.py
python3 test_fr0333_image_quality_runtime_genius.py
```

The Genius rail is `TWELVE.IN -> TWELVE.OUT` and HumanLock remains active.
