# FR0333 Raven Cloud Taskbar v1

Purpose: one cloud-visible project control plane for FR-0333/Raven without forcing local-only engines into the network.

## Architecture

`PROJECT → TASKBAR → EVIDENCE STATE → EXECUTION STATE → HASH/RECEIPT → CLOUD METADATA`

Network layer:

`RAVEN TASKBAR CONTROL PLANE → LUMEN MULTI-CLOUD GATEWAY (transport) → cloud/provider endpoints`

The Lumen layer is recorded as **verified capability / not provisioned**. No tenant ID, gateway ID, interface, BGP session, cloud account, or credential is fabricated.

## Hard boundaries

- HumanLock remains active.
- Raw private evidence stays local unless explicitly promoted.
- Local-only engines may publish hashes, receipts, build results and status without uploading their raw working data.
- Historical records are append-only; no backfill or retroactive replacement.
- `OBSERVED != CORRELATED != CAUSAL` remains the evidence gate.
- Recovery is not called deployed until authenticated state, redundant storage, recovery manifest and restore tests exist.

## Find Hub remembered-state boundary

`FR0333.FIND.HUB.REMEMBERED.STATE.BOUNDARY.0001` is registered as a Zero Lion Logic Gate working specification.

Governing law:

`RECORD.OF.WHERE.IT.WAS.SAVED != LIVE.EVIDENCE.OF.WHERE.IT.IS`

The rail preserves `USER_ASSERTED` and `SENSOR_ASSISTED_CAPTURE` as distinct state-input classes, separates remembered-item persistence from Find Hub device/accessory location runtime and people location-sharing lanes, and prevents Gemini readback or a saved Find Hub record from being promoted into independent live-location verification.

Canonical consequence grammar remains `T.20`, `U.21`, and `F.6`. Record validity and present physical-state validity are evaluated separately so a valid remembered record can pass while a current-location claim remains on hold.

Dedicated package:

- `fr0333_find_hub_remembered_state_boundary_0001.json`
- `fr0333_find_hub_remembered_state_boundary_genius.py`
- `test_fr0333_find_hub_remembered_state_boundary_genius.py`
- `README_find_hub_remembered_state_boundary_0001.md`
- `.github/workflows/fr0333-find-hub-remembered-state-boundary-validate.yml`

Boundary: `REPOSITORY.WRITE != FIND.HUB.WRITE`. The package does not perform a Google account mutation, live item lookup, tracker read, Gemini invocation, or external runtime execution. HumanLock remains required for canonical promotion.

## Build

```bash
python3 build.py
```

Output: `dist/index.html`, JSON registries and `SHA256SUMS`.
