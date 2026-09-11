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

## Build

```bash
python3 build.py
```

Output: `dist/index.html`, JSON registries and `SHA256SUMS`.

## AI image-tool metrics

`FR0333.AI.IMAGE.TOOL.METRICS.0001` is registered at Golden Chain position `GC.SB.0027`. It measures identity preservation, remastering, native 9:16 output, batch/split workflows and runtime reliability. Verified releases, previews, vendor claims and unverified material remain separate. The rail is manual-run only; no scheduled task or monitor is created. See `README_ai_image_tool_metrics.md`.

## Mariah Carey CHOMP reference pack

`FR0333.ADOBE.MARIAH.CAREY.CHOMP.0001` is attached as a child reference pack of the AI image-tool metrics rail. It contains 51 statistical bits, 9 separated money bits, 9 chronological periods and 7 explicit data holds. Its compiler enforces one 9:16 canvas per input, rejects count mismatch and collage policy, excludes disputed facts from safe context and requires an attached image for identity lock. It claims no new Golden Chain position and no external Adobe execution. See `README_mariah_carey_chomp.md`.
