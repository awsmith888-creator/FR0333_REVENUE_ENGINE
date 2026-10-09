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
