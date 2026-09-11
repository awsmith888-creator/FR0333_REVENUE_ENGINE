# FR0333.HUMAN.TOOL.CONTRIBUTION.EVIDENCE.0001

**State:** `SPECIFICATION`  
**HumanLock:** `ACTIVE`  
**Runtime:** `NOT.ESTABLISHED.UNTIL.RECEIPT`  
**Promotion:** `CLAIM.SPECIFIC`

## Purpose

Trace work from contribution through tool use, execution, evidence, accessibility, attribution, and receipt without allowing publication, configuration, source prestige, or vendor-originated statistics to auto-promote a claim.

## Canonical pipeline

```text
HUMAN.CONTRIBUTION
→ TOOL
→ EXECUTION
→ EVIDENCE
→ ACCESSIBILITY
→ ATTRIBUTION
→ RECEIPT
```

## Implementation order

```text
SPEC
→ JSON.SCHEMA
→ VALIDATOR
→ FIXTURES
→ CI
→ INVENTORY
→ README
→ RUNTIME.RECEIPT
```

`RUNTIME.RECEIPT` is not produced by local validation. It remains absent until an authenticated runtime event is independently observed and recorded.

## Terminal states

```text
T.20.PASS
U.21.HOLD
F.6.REJECT
```

Aggregation is deterministic:

1. Any applicable rail in `F.6.REJECT` makes the bundle `F.6.REJECT`.
2. Otherwise, any applicable rail in `U.21.HOLD` makes the bundle `U.21.HOLD`.
3. Otherwise, all applicable rails must be `T.20.PASS`.

## Hard invariants

```text
WORK.PERFORMED != WORK.CREDITED
TOOL.CONFIGURED != TOOL.EXECUTED
COMMAND.VISIBLE != RUNTIME.RECEIPT
CONTENT.CREATED != CONTENT.ACCESSIBLE
SOURCE.PRESENT != CONTENT.EXTRACTED
VENDOR.CLAIM != INDEPENDENT.VERIFICATION
CLAIM.PUBLISHED != CLAIM.VERIFIED
EVIDENCE.CLASS MUST.NOT AUTO.PROMOTE BASED.ON SOURCE.NAME
```

The final invariant is enforced as a global rejection condition: `source_name_used_to_auto_promote` must always be false.

## Rails

### C.01.ATTRIBUTION

A pass requires completed work, credited work, a contribution receipt, and an attribution receipt.

Contradiction example: credit claimed for work that is not recorded as performed.

### C.02.ACCESSIBILITY

A pass requires completed content, completed alt text, a passing contrast check, and a passing accessibility gate.

`CONTENT.CREATED` alone never establishes `CONTENT.ACCESSIBLE`.

### C.03.EXECUTION

A pass requires configuration, execution, explicit authorization, and a runtime receipt.

`COMMAND.VISIBLE` and `TOOL.CONFIGURED` are observation states only.

### C.04.SOURCE.EXTRACTION

A pass requires source presence, completed extraction, an extracted-payload hash, and claim-specific promotion.

If a source is present but extraction is incomplete, promotion must remain `HOLD`.

### C.05.VERIFICATION

Vendor survey data can pass only as correctly classified vendor evidence. It cannot be labeled as an independent outcome study without independent evidence.

An `INDEPENDENT.OUTCOME.STUDY` pass requires an independent source relationship and a corroboration receipt.

## Evidence boundary

A source name, institution, publisher, repository, signature, or vendor brand does not determine evidence class. Evidence class is claim-specific and must be justified by an explicit classification basis.

## Runtime boundary

```text
LOCAL.SCHEMA.PASS != AUTHENTICATED.RUNTIME
CI.PASS != EXTERNAL.RUNTIME.EXECUTION
RUNTIME.RECEIPT = null UNTIL AUTHENTICATED.RUNTIME IS OBSERVED
```
