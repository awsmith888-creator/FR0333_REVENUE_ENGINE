# FR0333.ZBOARD.HARDENING.0001

Status: DESIGN.CANDIDATE / U.21.HOLD. These documents are **proposed certificates**, not signed or verified operational certifications. No runtime, integration, or production hardening is established by documentation alone.

Authority: one main Z-Board, 64 ACTIVE.METRICS and 64 PASSIVE.MATRIX logical lanes; six engines plus Linking Bus remain unchanged. Main supervisory control is not an additional lane. Decision vocabulary: T.20.PASS / U.21.HOLD / F.6.FAIL. HumanLock remains active.

## TAB.01 / SONAR

**Certificate ID:** CERT.HARD.01

**Reference pin:** PIN.HARD.01

**Purpose:** Detect anomalous signal, missing heartbeat, latency, or interrupted data before propagation.

**Fault-injection test:** Synthetic signal with bounded baseline; injected deviation and silent sensor.

**Required behavior:** Record observation and threshold version; flag anomaly to main gate; fail closed on missing telemetry.

**Evidence / pin payload:** Detection timestamp, baseline ID, raw sample hash, signal source, gate decision.

**Safety invariant:** A blind sonar or missing telemetry is HOLD, not PASS.

**Acceptance state:** U.21.HOLD until executable tests, signed/traceable receipts, and HumanLock review establish compliance.

**Backlink:** [Eight-tab index](README.md). **Scope:** proposal only; not a claim of installed control.
