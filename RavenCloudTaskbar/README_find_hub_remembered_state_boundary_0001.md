# FR0333 Find Hub Remembered State Boundary 0001

## Purpose

`FR0333.FIND.HUB.REMEMBERED.STATE.BOUNDARY.0001` prevents a saved Find Hub remembered-item record from being promoted into a claim about an item's present physical location without separate runtime evidence.

## Governing distinction

`RECORD.OF.WHERE.IT.WAS.SAVED != LIVE.EVIDENCE.OF.WHERE.IT.IS`

Find Hub is the system of record for remembered items. Gemini and the direct Find Hub UI are read/write interfaces to that record. A remembered item may be populated by a user's statement or by sensor-assisted capture of the device's current address at record creation or update. That capture is still not continuous object tracking.

## Source classes

- `USER_ASSERTED`: the user supplies the storage spot or location.
- `SENSOR_ASSISTED_CAPTURE`: Find Hub captures the device location/address when the record is added or updated and appropriate location permission is granted.

These classes remain distinct. Sensor-assisted capture does not become a tracker-tag observation and does not establish that the item remains there later.

## Runtime lane separation

The product family contains separate evidence lanes:

- Remembered items: persistence-oriented declared-state records.
- Online/offline device and compatible accessory finding: location-runtime evidence.
- Google Location Sharing surfaced through Find Hub: separate people-location-sharing functionality.

The shared product name does not collapse these evidence classes.

## Terminal logic

The rail uses the canonical terminal grammar `T.20`, `U.21`, and `F.6`.

A valid remembered record can be `T.20` as a recorded-state fact while the present physical-state claim remains `U.21`. The validator therefore reports separate `record_state` and `present_state` consequences.

- `record_state = T.20`: required record fields exist, source class is known, timestamp is present, and value is readable.
- `present_state = U.21`: the record exists but no separate runtime evidence verifies the item's current physical state.
- `present_state = T.20`: only when a separate runtime-evidence flag accompanies a verified present-state observation.
- `F.6`: missing/invalid records, invalid source classes, invalid state, or contradiction of the present-state claim.

## Zero Lion control laws

- `REMEMBERED.LOCATION != CURRENT.VERIFIED.LOCATION`
- `USER.ASSERTED.STATE != SENSOR.OBSERVATION`
- `SENSOR.ASSISTED.CAPTURE != CONTINUOUS.TRACKING`
- `LAST.KNOWN.RECORDED.STATE != PRESENT.PHYSICAL.STATE`
- `GEMINI.INTERFACE != SYSTEM.OF.RECORD`
- `FIND.HUB.REMEMBERED.ITEM != FIND.HUB.REAL.TIME.LOCATION.SHARE`
- `SAME.PRODUCT.NAME != SAME.EVIDENCE.CLASS`
- `LOCATION.PERMISSION != CONTINUOUS.OBJECT.TRACKING`
- `OBSERVED != CORRELATED != CAUSAL`

## Source lock

The specification is grounded in Google Android documentation current on 2026-09-13:

1. Google Android Help, **Remembered items in Find Hub**: documents saving/updating remembered items, Gemini interaction, manual location fields, and automatic current-address capture when location permission is granted.
2. Android product documentation, **Find Hub Remembered items**: states that the Remembered tab does not track the real-time location of items and that accuracy depends on user-provided information.
3. Google Android Help, **How Find Hub protects your data**: documents separate current/recent/offline location behavior for devices/accessories and separate Google Location Sharing functionality.

## Validation

Run:

```bash
cd RavenCloudTaskbar
python fr0333_find_hub_remembered_state_boundary_genius.py
python -m unittest -v test_fr0333_find_hub_remembered_state_boundary_genius.py
```

The validator is fail-closed and enforces 12 gates. Mutation tests prove that removing a governing law, converting sensor-assisted capture into continuous tracking, or changing the canonical terminal grammar fails validation.

## Repository/runtime boundary

`SPECIFICATION.PRESENT != EXTERNAL.RUNTIME`

`LOCAL.TEST.PASS != GOOGLE.PROVIDER.RUNTIME`

`GITHUB.ACTIONS.PASS != LIVE.LOCATION.VERIFICATION`

`REPOSITORY.WRITE != FIND.HUB.WRITE`

No Google account action, Find Hub write, live item lookup, tracker read, Gemini invocation, or external runtime execution is performed by this package. HumanLock remains required for canonical promotion.
