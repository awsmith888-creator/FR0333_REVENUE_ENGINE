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

## Human / tool / contribution evidence gate

`FR0333.HUMAN.TOOL.CONTRIBUTION.EVIDENCE.0001` is a schema-first evidence contract for tracing contribution through tool use, execution, evidence, accessibility, attribution and receipt.

Its five rails are `C.01.ATTRIBUTION`, `C.02.ACCESSIBILITY`, `C.03.EXECUTION`, `C.04.SOURCE.EXTRACTION` and `C.05.VERIFICATION`. Terminal states are `T.20.PASS`, `U.21.HOLD` and `F.6.REJECT`.

Hard boundaries include `TOOL.CONFIGURED != TOOL.EXECUTED`, `SOURCE.PRESENT != CONTENT.EXTRACTED`, `VENDOR.CLAIM != INDEPENDENT.VERIFICATION`, and the rule that evidence class must never auto-promote from a source name or institutional reputation.

The local fixture suite is 10 of 10 pass. That establishes schema/validator behavior only. `RUNTIME = NOT.ESTABLISHED.UNTIL.RECEIPT` remains controlling; neither local validation nor CI can manufacture an authenticated external runtime receipt. See `README_human_tool_contribution_evidence.md` and `human_tool_contribution_evidence_inventory.json`.
