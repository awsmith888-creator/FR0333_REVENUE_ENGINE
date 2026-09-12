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

## Golden Chain GC.SB.0028 package

The evidence gate is registered in the draft Golden Chain package `GC.SB.0028` as `FR0333.HUMAN.CENTERED.EVIDENCE.ACCESS.PACKAGE.0001`.

Linked specifications:

- `FR0333.TRANSCRIPT.CONFIDENCE.HUMANLOCK.0001` v0.12 — calibrated exact-span confidence, non-independence protection, and mandatory HumanLock when `C12` remains unknown.
- `FR0333.PUBLIC.BENEFIT.HUMAN.CENTERED.0001` v0.20 — `STRICT.SYSTEM -> COMPASSIONATE.INTERFACE`, false-denial control, no silent denial, and human advocacy routing.

Three North Star visual artifacts are hash-bound in `fr0333_golden_chain_gc_sb_0028.json` and stored as symbolic assets. They are explicitly not evidence.

`GC.SB.0028` remains `REGISTERED.DRAFT.UNMERGED`. Promotion requires `GC.SB.0027` to exist in target history first, preserving Golden Chain order.

The base local fixture suite is 10 tests and the human-centered extension suite adds 12 deterministic tests. These establish schema/spec behavior only. `RUNTIME = NOT.ESTABLISHED.UNTIL.RECEIPT` remains controlling; neither local validation nor CI can manufacture an authenticated external runtime receipt.

## Golden Chain GC.SB.0029 public-litigation evidence register

`FR0333.TRUMP.BBC.DEFAMATION.LITIGATION.EVIDENCE.0001` is registered at draft position `GC.SB.0029` with predecessor `GC.SB.0028`.

The record preserves the public procedural state of *Donald J. Trump v. British Broadcasting Corporation et al.* while preventing procedural events or party positions from being promoted into final merits conclusions.

Controlling boundaries:

```text
ACKNOWLEDGED.MISLEADING.EDIT != DEFAMATION.LIABILITY
DISCOVERY.RESISTANCE != FEAR.PROVEN
AMENDED.DAMAGES.THEORY != MOTIVE.PROVEN
ACTIVE.CASE != FINAL.WINNER
TRIAL.SCHEDULED != LIABILITY.ESTABLISHED
PARTY.ASSERTION != COURT.FINDING
PROCEDURAL.DELAY != MERITS.VICTORY
```

Current register state is `U.21.HOLD` because liability, final damages and final outcome remain unresolved. `GC.SB.0029` is `REGISTERED.DRAFT.UNMERGED`; it cannot be promoted until `GC.SB.0028` exists in target history and the current head passes review and CI.

The litigation rail adds 12 deterministic evidence-boundary tests. Combined expected validation count before the Genius Bar rail is 34 tests: 10 base, 12 human-centered extension, and 12 litigation-evidence tests.

## Golden Chain GC.SB.0030 Genius Bar comparability-normalization rail

`FR0333.GENIUS.BAR.COMPARABILITY.NORMALIZATION.0001` is registered at draft position `GC.SB.0030` with predecessor `GC.SB.0029`.

Its controlling pipeline is:

`RAW.STATISTIC → STRUCTURAL.SCHEMA → SEMANTIC.INVARIANT.VALIDATOR → DENOMINATOR.LOCK → REFERENCE.FRAME.LOCK → NORMALIZE → REVERSIBILITY.GATE → CANONICAL.JSON.V1 → SHA256.COMPARABILITY.KEY → CONSUMER.CAPABILITY.GATE → OUTPUT.REPORT`

The rail enforces measurement normalization and semantic binding. Database normalization is retained only as a conceptual analogue; it is not treated as independent validation of the FR0333 measurement rules.

Controlling boundaries include:

```text
EXACT.CANONICAL.DECIMAL.EQUALITY != RAW.BYTE.IDENTITY
FORMATTING.DIFFERENCE != SEMANTIC.DIFFERENCE
RAW.STATE != CANONICAL.STATE
NUMERIC.IDENTITY != SEMANTIC.IDENTITY
REVERSIBLE.REPRESENTATION != EXACT.UNDERLYING.TRUTH
VALID.RECORD != VALID.FOR.EVERY.USE
NORMALIZED != COMPARABLE
COMPARABLE != CONSUMER.COMPATIBLE
SCHEMA.VALID != SEMANTICALLY.VALID
SPECIFICATION.PASS != IMPLEMENTATION.PASS
IMPLEMENTATION.PASS != RUNTIME.ENFORCEMENT
HASH_BOUND.RECEIPT != CRYPTOGRAPHICALLY.SIGNED.RECEIPT
```

The implementation adds a strict Draft 2020-12 JSON Schema, semantic/inverse validator, versioned canonical JSON serialization, SHA-256 comparability key, consumer precision-laundering gate, N.01–N.12 adversarial fixtures, range/partition checks, and deterministic unsigned receipt generation. The new suite adds 19 tests, bringing the expected combined deterministic count to 53.

`GC.SB.0030` remains `REGISTERED.DRAFT.UNMERGED`. Promotion requires `GC.SB.0029` in target history plus successful exact-head CI. CI proves repository behavior only; external runtime enforcement and cryptographic signing remain unestablished.

See `README_genius_bar_comparability_normalization.md`, `fr0333_genius_bar_comparability_normalization_0001.schema.json`, `fr0333_genius_bar_comparability_normalization_0001.py`, `fr0333_genius_bar_comparability_fixtures_0001.json`, `test_fr0333_genius_bar_comparability_normalization.py`, and `fr0333_golden_chain_gc_sb_0030.json`.
