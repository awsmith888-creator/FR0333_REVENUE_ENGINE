# FR0333.ZBOARD.HARDENING.0001

Status: DESIGN.CANDIDATE / U.21.HOLD. These documents are **proposed certificates**, not signed or verified operational certifications. No runtime, integration, or production hardening is established by documentation alone.

Authority: one main Z-Board, 64 ACTIVE.METRICS and 64 PASSIVE.MATRIX logical lanes; six engines plus Linking Bus remain unchanged. Main supervisory control is not an additional lane. Decision vocabulary: T.20.PASS / U.21.HOLD / F.6.FAIL. HumanLock remains active.

## TAB.03 / NODE_ISOLATION

**Certificate ID:** CERT.HARD.03

**Reference pin:** PIN.HARD.03

**Purpose:** Prevent faulty processing node from contaminating other nodes or lanes.

**Fault-injection test:** Inject malformed node output, timeout, and dependency failure.

**Required behavior:** Quarantine affected node and dependent operations; unaffected paths may continue only with verified separation.

**Evidence / pin payload:** Node ID, dependency graph, isolation receipt, downstream checks.

**Safety invariant:** Shared dependencies invalidate assumed isolation.

**Acceptance state:** U.21.HOLD until executable tests, signed/traceable receipts, and HumanLock review establish compliance.

**Backlink:** [Eight-tab index](README.md). **Scope:** proposal only; not a claim of installed control.
