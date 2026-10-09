# FR0333.ZBOARD.HARDENING.0001

Status: DESIGN.CANDIDATE / U.21.HOLD. These documents are **proposed certificates**, not signed or verified operational certifications. No runtime, integration, or production hardening is established by documentation alone.

Authority: one main Z-Board, 64 ACTIVE.METRICS and 64 PASSIVE.MATRIX logical lanes; six engines plus Linking Bus remain unchanged. Main supervisory control is not an additional lane. Decision vocabulary: T.20.PASS / U.21.HOLD / F.6.FAIL. HumanLock remains active.

## TAB.05 / PASSIVE_MATRIX

**Certificate ID:** CERT.HARD.05

**Reference pin:** PIN.HARD.05

**Purpose:** Maintain immutable or tamper-evident evidence of original inputs, transitions, and recovery.

**Fault-injection test:** Attempt receipt tampering, missing receipt, out-of-order replay.

**Required behavior:** Preserve source and finding separately; flag missing or altered receipts; do not decide operational permission.

**Evidence / pin payload:** Append-only receipt sequence, provenance, digest chain, retention and access policy.

**Safety invariant:** Same component must not be able to silently modify its own audit trail.

**Acceptance state:** U.21.HOLD until executable tests, signed/traceable receipts, and HumanLock review establish compliance.

**Backlink:** [Eight-tab index](README.md). **Scope:** proposal only; not a claim of installed control.

## Recovery subcategory / RECOVERY.05

**Recovery reference pin:** PIN.RECOVERY.05 (subordinate to PIN.HARD.05; original certificate unchanged).

**Category:** Evidence Preservation.

**Proposed recovery function:** PASSIVE.MATRIX may accept an uncertain artifact as untrusted evidence, preserving original bytes, metadata, source/finding separation and lineage. It never independently certifies truth or authorizes execution.

**Recovery safety invariant:** PASSIVE.ACCEPT != ACTIVE.VERIFIED != ENGINE.PROMOTED; no silent mutation of evidence.

**Required recovery receipt:** Source identifier, original-artifact digest, paired passive evidence reference, active test scope and result, decision state, lineage backlink, and HumanLock approval if promotion is requested. Unknown or unverified inputs remain U.21.HOLD.

**Status:** DESIGN.CANDIDATE / U.21.HOLD. Documentation only; no executable salvage pipeline or certification established.
