# FR0333 Raven Cloud Taskbar v1

Purpose: one cloud-visible project control plane for FR-0333/Raven without forcing local-only engines into the network.

## Architecture

`PROJECT → TASKBAR → EVIDENCE STATE → EXECUTION STATE → HASH/RECEIPT → CLOUD METADATA`

Network layer:

`RAVEN TASKBAR CONTROL PLANE → LUMEN MULTI-CLOUD GATEWAY (transport) → cloud/provider endpoints`

The Lumen layer is recorded as **verified capability / not provisioned**. No tenant ID, gateway ID, interface, BGP session, cloud account, or credential is fabricated.

## Golden Chain active index

`0.5.FR.0333.GOLDEN.CHAIN.MOTORCYCLE.AI.CONTINUUM.0001` is indexed on its working branch as `PROMOTED.WORKING.SPEC.GOLDEN_CHAIN.INDEXED`.

Primary artifact: `RavenCloudTaskbar/fr0333_motorcycle_ai_continuum_matrix_0001.json`

Validation: `RavenCloudTaskbar/fr0333_motorcycle_ai_continuum_genius.py` plus its local test rail and GitHub Actions workflow.

Boundary: `GOLDEN_CHAIN.INDEX.ACTIVE != EXTERNAL.RUNTIME.DEPLOYED`.

## Sports BITS/BONES reference-point rail

`FR0333.SPORTS.BITS.BONES.0001` is active as an evidence-bounded reference-point specification.

Primary artifact: `RavenCloudTaskbar/fr0333_sports_bits_bones_0001.json`

Reference fixture: `RP.FIXTURE.MLB.SUBWAY.SERIES.2026.09.12.0001`

The first fixture separates structural BONES from measurable BITS:

`BONES = SPORT + LEAGUE + TEAM + EVENT + DATE + VENUE + SERIES + SCHEDULE`

`BITS = SCORE + INNING + TIME + RESULT + STANDINGS + PITCHER.DATA + AUDIENCE.DATA + MEDIA.VIEWS + VIDEO.RUNTIME`

The fixture contains four reference points: the observed ongoing Mets-Yankees game state, four listed completed games used to derive a 2-2 completed-row baseline, the scheduled 2026-09-13 game, and the observed MLB YouTube 165,000-view media metric.

Validation: `RavenCloudTaskbar/fr0333_sports_bits_bones_genius.py` plus `RavenCloudTaskbar/test_fr0333_sports_bits_bones_genius.py` and `.github/workflows/fr0333-sports-bits-bones-validate.yml`.

Key boundaries:

- `SCREENSHOT.OBSERVED != INDEPENDENT.VERIFICATION`
- `ONGOING.SCORE != FINAL.RESULT`
- `VIDEO.VIEWS != TV.RATINGS`
- `VIDEO.VIEWS != TOTAL.GAME.REACH`
- `SCHEDULED.EVENT != COMPLETED.EVENT`
- `UNKNOWN != ZERO != PASS`
- `DERIVED.RECORD != SOURCE.REPORTED.RECORD`

The Raven build imports this validator directly, so the control-plane build fails if these reference-point controls are broken.

## Hard boundaries

- HumanLock remains active.
- Raw private evidence stays local unless explicitly promoted.
- Local-only engines may publish hashes, receipts, build results and status without uploading their raw working data.
- Historical records are append-only; no backfill or retroactive replacement.
- `OBSERVED != CORRELATED != CAUSAL` remains the evidence gate.
- Recovery is not called deployed until authenticated state, redundant storage, recovery manifest and restore tests exist.

## Build

```bash
python3 build.py
```

Output: `dist/index.html`, JSON registries and `SHA256SUMS`.
