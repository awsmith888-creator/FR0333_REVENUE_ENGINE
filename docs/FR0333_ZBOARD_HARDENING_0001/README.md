# FR0333.ZBOARD.HARDENING.0001

Status: DESIGN.CANDIDATE / U.21.HOLD. These documents are **proposed certificates**, not signed or verified operational certifications. No runtime, integration, or production hardening is established by documentation alone.

Authority: one main Z-Board, 64 ACTIVE.METRICS and 64 PASSIVE.MATRIX logical lanes; six engines plus Linking Bus remain unchanged. Main supervisory control is not an additional lane. Decision vocabulary: T.20.PASS / U.21.HOLD / F.6.FAIL. HumanLock remains active.

## Eight tabs and pins

| Tab | Certificate | Reference pin | Gate |
|---|---|---|---|
| 01 | [SONAR](TAB_01_SONAR.md) | PIN.HARD.01 | U.21.HOLD |
| 02 | [KERNEL_GUARD](TAB_02_KERNEL_GUARD.md) | PIN.HARD.02 | U.21.HOLD |
| 03 | [NODE_ISOLATION](TAB_03_NODE_ISOLATION.md) | PIN.HARD.03 | U.21.HOLD |
| 04 | [MAIN_CIRCUIT_BREAKER](TAB_04_MAIN_CIRCUIT_BREAKER.md) | PIN.HARD.04 | U.21.HOLD |
| 05 | [PASSIVE_MATRIX](TAB_05_PASSIVE_MATRIX.md) | PIN.HARD.05 | U.21.HOLD |
| 06 | [ACTIVE_METRICS](TAB_06_ACTIVE_METRICS.md) | PIN.HARD.06 | U.21.HOLD |
| 07 | [RECOVERY_GATE](TAB_07_RECOVERY_GATE.md) | PIN.HARD.07 | U.21.HOLD |
| 08 | [HUMANLOCK](TAB_08_HUMANLOCK.md) | PIN.HARD.08 | U.21.HOLD |

## Control sequence

SOURCE_LOCK -> SONAR -> ACTIVE.METRICS -> KERNEL_GUARD -> NODE_ISOLATION -> MAIN_CIRCUIT_BREAKER -> PASSIVE.MATRIX receipt -> RECOVERY_GATE -> HUMANLOCK -> OUTPUT_GATE.

Passive Matrix is evidence-only, not an independent decision authority. For any missing telemetry, unverifiable receipt, unknown dependency, shared-kernel integrity fault, or unauthorized recovery: HOLD. Distinguish source evidence, machine finding, edited summary; observation is not causation; local test pass is not deployment.

## Reference pin rules

Every PIN.HARD.XX links a certificate, affected node/lane, baseline version, fault injection, expected and observed outcome, evidence digest, and recovery receipt. Pins are navigation/reference identifiers, not proof of execution. Original failures must remain traceable. Preserve all eight entries (eight in, eight out).

## Existing learnings and regression targets

- FR0333.CATCH.CONVERT.0002.99.1V: local YAML artifact-action detector; prior reported 24/24 controlled tests. Does not certify live workflows.
- Indirect reusable-workflow/composite-action coverage gap; unknown dependency must HOLD rather than false PASS.
- Duplicate YAML key ambiguity; reject or quarantine before promotion.
- Separate literal HEAD.SHA from synthetic MERGE.SHA; do not claim exact-head CI from merge-only execution.
- Prior 128-lane synthetic simulation is a limited model, not proof of parallel runtime, uptime, or production correctness.

## Required acceptance evidence

1. Implement guards in executable engine code and add deterministic tests for each certificate.
2. Inject lane-local, node, shared-bus, sonar-silence, receipt-tamper, and unauthorized-recovery faults.
3. Verify 64 active decisions and 64 paired passive receipts per complete cycle, including no loss or duplication.
4. Obtain independently checkable CI receipts bound to exact commit and workflow context.
5. Require HumanLock approval before merge, promotion, or deployment.

## Change control

This branch contains documentation only. No live gate is installed, no background monitor is running, and no production certification is asserted. Proposed promotion remains U.21.HOLD.

## Eight-tab conversion train recovery index

Existing hardening certificates and PIN.HARD.01-08 remain authoritative and unchanged. Recovery categories are subordinate annotations inside those eight tabs; no ninth tab, extra main board, or separate engine is introduced. Preserve 8 IN -> 8 OUT.

| Existing tab | Recovery category | Subordinate recovery pin | State |
|---|---|---|---|
| 01 / SONAR | Discovery and Intake | PIN.RECOVERY.01 | U.21.HOLD |
| 02 / KERNEL_GUARD | Authenticity and Integrity | PIN.RECOVERY.02 | U.21.HOLD |
| 03 / NODE_ISOLATION | Crypto Salvage | PIN.RECOVERY.03 | U.21.HOLD |
| 04 / MAIN_CIRCUIT_BREAKER | Interruption and Recovery | PIN.RECOVERY.04 | U.21.HOLD |
| 05 / PASSIVE_MATRIX | Evidence Preservation | PIN.RECOVERY.05 | U.21.HOLD |
| 06 / ACTIVE_METRICS | Analysis and Conversion | PIN.RECOVERY.06 | U.21.HOLD |
| 07 / RECOVERY_GATE | Golden Chain and Lineage | PIN.RECOVERY.07 | U.21.HOLD |
| 08 / HUMANLOCK | Authorization and Final Pin | PIN.RECOVERY.08 | U.21.HOLD |

Conversion-train research path (proposed, not runtime execution): intake -> CHOMP/source preservation -> passive evidence quarantine -> active metrics verification -> principle extraction/conversion -> main-circuit gate -> recovery lineage -> HumanLock authorization and final reference pin. The existing safety control sequence above remains authoritative; this is an evidence-processing view, not a replacement execution order.

**Invariant:** PASSIVE.ACCEPT != ACTIVE.VERIFIED != ENGINE.PROMOTED. Hashes verify consistency, not truth. Unknown provenance, unsupported claims, fabricated references, and unverified functionality remain HOLD. Proposed cross-reference: PIN.EVOLUTION.HALLUCINATION.001; not a deployed detector. All changes here are documentation-only and require independent implementation and test receipts before certification.
