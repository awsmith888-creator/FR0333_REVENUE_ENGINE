# FR0333.ZBOARD.HARDENING.0001

Status: DESIGN.CANDIDATE / U.21.HOLD. These documents are **proposed certificates**, not signed or verified operational certifications. No runtime, integration, or production hardening is established by documentation alone.

Authority: one main Z-Board, 64 ACTIVE.METRICS and 64 PASSIVE.MATRIX logical lanes; six engines plus Linking Bus remain unchanged. Main supervisory control is not an additional lane. Decision vocabulary: T.20.PASS / U.21.HOLD / F.6.FAIL. HumanLock remains active.

## TAB.06 / ACTIVE_METRICS

**Certificate ID:** CERT.HARD.06

**Reference pin:** PIN.HARD.06

**Purpose:** Evaluate signals continuously against fixed, versioned rules and produce traceable decisions.

**Fault-injection test:** Retired artifact version, unknown version, indirect reusable workflow, duplicate YAML keys.

**Required behavior:** Emit PASS/HOLD/FAIL or REVIEW only with coverage completeness; unresolved indirect dependencies HOLD.

**Evidence / pin payload:** Metric inputs, threshold/policy version, coverage manifest, exact head SHA and merge SHA separately.

**Safety invariant:** A version-screen PASS is not whole-workflow certification.

**Acceptance state:** U.21.HOLD until executable tests, signed/traceable receipts, and HumanLock review establish compliance.

**Backlink:** [Eight-tab index](README.md). **Scope:** proposal only; not a claim of installed control.

## Recovery subcategory / RECOVERY.06

**Recovery reference pin:** PIN.RECOVERY.06 (subordinate to PIN.HARD.06; original certificate unchanged).

**Category:** Analysis and Conversion.

**Proposed recovery function:** ACTIVE.METRICS evaluates provenance, authenticity claims, functional behavior, contradictions, vulnerabilities and salvage feasibility with reproducible, versioned tests. Track fabricated references and simulated capabilities presented as real using proposed PIN.EVOLUTION.HALLUCINATION.001.

**Recovery safety invariant:** No verified-function claim without a linked test receipt and declared test scope; unknown dependencies HOLD.

**Required recovery receipt:** Source identifier, original-artifact digest, paired passive evidence reference, active test scope and result, decision state, lineage backlink, and HumanLock approval if promotion is requested. Unknown or unverified inputs remain U.21.HOLD.

**Status:** DESIGN.CANDIDATE / U.21.HOLD. Documentation only; no executable salvage pipeline or certification established.

## Anti-looping cross-reference / PIN.HARD.04.ANTI.LOOP.001

**Status:** DESIGN.CANDIDATE / U.21.HOLD. Cross-tab pin anchored to TAB.04; no ninth tab and no executable loop breaker claimed.

**Rule:** REPEAT.DETECT -> COMPARE.DELTA -> INTERRUPT -> HOLD -> VERIFY.CHANGE -> RECOVER.

**Authority:** PIN.HARD.06 / PIN.RECOVERY.06. Compare a versioned operation identity, state fingerprint, output fingerprint, dependency path, and measurable progress delta over a configured observation window. Distinguish legitimate periodic work, bounded retries and idempotent repeats from non-progress loops, recursion cycles, or oscillation. Use a configurable retry/time/recurrence budget rather than an invented universal threshold.

**Test candidate:** Distinguish a legitimate 10-cycle scheduled poll from 10 no-progress retries; flag A->B->A dependency cycle and alternating A/B state flapping.

**Required receipt:** Cycle identity, input/output/state digests, iteration number, elapsed window, progress delta, versioned policy threshold, affected dependency scope, decision, original evidence link and restart authorization when applicable.
