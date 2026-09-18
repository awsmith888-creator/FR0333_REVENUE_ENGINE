# FR0333 Raven Major Hardening 0005

This candidate hardening layer is authorized by the human operator for Raven, the connected Adobe runtime boundary, and the FR0333 engine. It extends `FR0333.AI.SELF.IMPROVEMENT.0004` without renumbering or replacing its ten-token sequence.

## Authority boundary

```text
HUMAN.OPERATOR                  FINAL.CONTROLLER
Z.26.21.HUMANLOCK               ACTIVE_IMMUTABLE
EXTERNAL.ADVISOR.AUTHORITY      NONE
SELF.AUTHORIZATION              FALSE
MODEL.WEIGHT.CHANGE             FALSE
PROVIDER.PERMISSION.ESCALATION  FALSE
SECRET.ACCESS.EXPANSION         FALSE
```

The operator authorized hardening work, validators, regression tests, and CI. This authorization does **not** imply merge, deployment, canonical promotion, or capability-improvement promotion.

```text
HARDENING.AUTHORIZED            TRUE
MERGE                           FALSE
DEPLOYMENT                      FALSE
CANONICAL.SPEC                  U.21.HOLD
CAPABILITY.IMPROVEMENT          NOT.ESTABLISHED
```

## Raven hardening

The predecessor remains exactly ten ordered tokens:

```text
RAVEN_SOURCE
RAVEN_ROUTE
RAVEN_WATCH
RAVEN_VERIFY
RAVEN_RECEIPT
LOCK_REFERENCE
LOCK_APPROVAL
LOCK_BOUNDARY
LOCK_APPEND
LOCK_INTEGRITY
```

The 0005 validator rejects token drift, an eleventh token, HumanLock downgrade, external-advisor authority, self-authorization, provider-permission escalation, model-weight mutation, hidden secret access, predecessor overwrite, or automatic promotion.

## Read-only behavioral gate

The next admissible capability-evidence path is now executable rather than descriptive. `evaluate_behavioral_receipt()` requires:

```text
SAME.INPUT.CORPUS
SAME.SOURCE.SNAPSHOT
SAME.RUNTIME.ENVELOPE
EXACT.BASELINE.REVISION
EXACT.CANDIDATE.REVISION
HUMANLOCK.ACTIVE_IMMUTABLE
HUMAN.OPERATOR.AUTHORITY
INDEPENDENT/READONLY.EVIDENCE.ORIGIN
```

The two target metrics are:

```text
SOURCE.SELECTION.ERROR
ROUTING.ERROR
```

Neither may regress and their combined error count must decrease. These remain zero-tolerance failures:

```text
STALE.STATE.ERROR
UNSUPPORTED.PROMOTION
AUTHORIZATION.BYPASS
RECEIPT.COMPLETENESS.ERROR
LINEAGE.ERROR
```

A passing behavioral receipt still returns:

```text
CANONICAL.PROMOTION       U.21.HOLD
CAPABILITY.IMPROVEMENT    NOT.ESTABLISHED
PROMOTION.AUTHORIZED      FALSE
```

That is deliberate. Behavioral evidence is evidence; it is not authority.

## Adobe runtime hardening

The Adobe rail is bound only to the connected runtime behavior already observed in the repository. It does not claim universal Adobe capacity.

```text
QUEUE.LENGTH              REQUESTED.COUNT
OUTPUT.COUNT             REQUESTED.COUNT
COUNT.INVARIANT           N.IN=N.OUT
SEPARATE.IMAGES           REQUIRED
COLLAGE                   FALSE
DELIVERY.RATIO            9:16
DELIVERY.DIMENSIONS       1080x1920
FAILED.SLOT.RETRY         ONLY.FAILED.SLOT
SUCCESSFUL.REGENERATION   FALSE
SLOT.IDENTITY             PRESERVED
```

Because the previously observed connected Adobe generation surface returned one provider output per call, provider dispatch remains:

```text
SINGLETON_UNTIL_BATCH.RUNTIME.VERIFIED
```

This does not override the general queue rule that queue length equals the user's requested count. It only constrains how this specific connected Adobe runtime is dispatched until a verified multi-output receipt exists.

## Engine hardening

```text
TRUTH.STATES              T.20 U.21 F.6
EVIDENCE.AXIOM            OBSERVED!=CORRELATED!=CAUSAL
PROMOTION.DEFAULT         U.21.HOLD
SOURCE.RECEIPT            REQUIRED
TRANSITION.RECEIPT        REQUIRED
UNSUPPORTED.CLAIM         FAIL.CLOSED
PREDECESSOR.OVERWRITE     FALSE
```

## Regression surface

The CI suite tests the positive path plus deliberate fault injection for:

- HumanLock downgrade
- external-advisor authority escalation
- self-authorization
- merge/deployment drift
- baseline/candidate context mismatch
- source/routing regression
- authorization bypass
- self-generated evidence
- false improvement claims
- Adobe queue-count mismatch
- collage creation
- wrong delivery dimensions
- retrying a previously successful slot
- regenerating successful slots

## Evidence boundary

```text
VALIDATOR.PASS != CAPABILITY.IMPROVEMENT
BEHAVIORAL.RECEIPT != CANONICAL.PROMOTION
MERGE != DEPLOYMENT
OBSERVATION != EXECUTION
ROUTING != AUTHORIZATION
EXTERNAL.ADVISOR != AUTHORITY
ADOBE.RUNTIME.PASS != UNIVERSAL.ADOBE.CAPACITY
```

This is a hardening candidate, not a self-granted promotion.
