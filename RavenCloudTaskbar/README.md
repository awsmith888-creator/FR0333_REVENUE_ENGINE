# FR0333 Raven Cloud Taskbar v1

Purpose: one cloud-visible project control plane for FR-0333/Raven without forcing local-only engines into the network.

## Architecture

`PROJECT → TASKBAR → EVIDENCE STATE → EXECUTION STATE → HASH/RECEIPT → CLOUD METADATA`

Network layer:

`RAVEN TASKBAR CONTROL PLANE → LUMEN MULTI-CLOUD GATEWAY (transport) → cloud/provider endpoints`

The Lumen layer is recorded as **verified capability / not provisioned**. No tenant ID, gateway ID, interface, BGP session, cloud account, or credential is fabricated.

## Hard boundaries

- HumanLock is `ACTIVE_IMMUTABLE`; it cannot be disabled by a completed action.
- Operator authorization is required per controlled mutation; authorization changes action state, not HumanLock state.
- Raw private evidence stays local unless explicitly promoted.
- Local-only engines may publish hashes, receipts, build results and status without uploading their raw working data.
- Historical records are append-only; no backfill or retroactive replacement.
- `OBSERVED != CORRELATED != CAUSAL` remains the evidence gate.
- Recovery is not called deployed until authenticated state, redundant storage, recovery manifest and restore tests exist.

## Find Hub remembered-state boundary

`FR0333.FIND.HUB.REMEMBERED.STATE.BOUNDARY.0001` is registered as an active canonical Zero Lion Logic Gate repository specification.

Governing law:

`RECORD.OF.WHERE.IT.WAS.SAVED != LIVE.EVIDENCE.OF.WHERE.IT.IS`

The rail preserves `USER_ASSERTED` and `SENSOR_ASSISTED_CAPTURE` as distinct state-input classes, separates remembered-item persistence from Find Hub device/accessory location runtime and people location-sharing lanes, and prevents Gemini readback or a saved Find Hub record from being promoted into independent live-location verification.

Canonical consequence grammar remains `T.20`, `U.21`, and `F.6`. Record validity and present physical-state validity are evaluated separately so a valid remembered record can pass while a current-location claim remains on hold.

HumanLock permanence:

`HUMANLOCK.STATE = ACTIVE.IMMUTABLE`

`HUMANLOCK.CAN_BE_DISABLED = FALSE`

`AUTHORIZED.ACTION.COMPLETE != HUMANLOCK.REMOVED`

Dedicated package:

- `fr0333_find_hub_remembered_state_boundary_0001.json`
- `fr0333_find_hub_remembered_state_boundary_genius.py`
- `test_fr0333_find_hub_remembered_state_boundary_genius.py`
- `README_find_hub_remembered_state_boundary_0001.md`
- `.github/workflows/fr0333-find-hub-remembered-state-boundary-validate.yml`

Boundary: `REPOSITORY.WRITE != FIND.HUB.WRITE` and `CANONICAL.ACTIVE != EXTERNAL.RUNTIME`. The package does not perform a Google account mutation, live item lookup, tracker read, Gemini invocation, or external runtime execution. HumanLock remains permanently active for controlled mutations.

## Build

```bash
python3 build.py
```

Output: `dist/index.html`, JSON registries and `SHA256SUMS`.

## AI image-tool metrics

`FR0333.AI.IMAGE.TOOL.METRICS.0001` is registered at Golden Chain position `GC.SB.0027`. It measures identity preservation, remastering, native 9:16 output, batch/split workflows and runtime reliability. Verified releases, previews, vendor claims and unverified material remain separate. The rail is manual-run only; no scheduled task or monitor is created. See `README_ai_image_tool_metrics.md`.

## Mariah Carey CHOMP reference pack

`FR0333.ADOBE.MARIAH.CAREY.CHOMP.0001` is attached as a child reference pack of the AI image-tool metrics rail. It contains 51 statistical bits, 9 separated money bits, 9 chronological periods and 7 explicit data holds. Its compiler enforces one 9:16 canvas per input, rejects count mismatch and collage policy, excludes disputed facts from safe context and requires an attached image for identity lock. It claims no new Golden Chain position and no external Adobe execution. See `README_mariah_carey_chomp.md`.
