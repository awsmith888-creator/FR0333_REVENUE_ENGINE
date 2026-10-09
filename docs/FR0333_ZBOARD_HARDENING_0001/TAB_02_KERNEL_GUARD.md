# FR0333.ZBOARD.HARDENING.0001

Status: DESIGN.CANDIDATE / U.21.HOLD. These documents are **proposed certificates**, not signed or verified operational certifications. No runtime, integration, or production hardening is established by documentation alone.

Authority: one main Z-Board, 64 ACTIVE.METRICS and 64 PASSIVE.MATRIX logical lanes; six engines plus Linking Bus remain unchanged. Main supervisory control is not an additional lane. Decision vocabulary: T.20.PASS / U.21.HOLD / F.6.FAIL. HumanLock remains active.

## TAB.02 / KERNEL_GUARD

**Certificate ID:** CERT.HARD.02

**Reference pin:** PIN.HARD.02

**Purpose:** Enforce lane permissions, execution limits, and integrity of the shared control kernel.

**Fault-injection test:** Attempt unauthorized operation, changed kernel policy, or stale authority.

**Required behavior:** Reject unauthorized operations; require versioned kernel policy and independent integrity check.

**Evidence / pin payload:** Kernel policy digest, attempted action, authorization result, control receipt.

**Safety invariant:** Kernel integrity uncertainty escalates to main-board HOLD.

**Acceptance state:** U.21.HOLD until executable tests, signed/traceable receipts, and HumanLock review establish compliance.

**Backlink:** [Eight-tab index](README.md). **Scope:** proposal only; not a claim of installed control.
