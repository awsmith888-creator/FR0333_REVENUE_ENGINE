# FR0333.MIGRATION.RECEIPT.COMPILER.0001

## Observation block

- Observation date: `2026-09-14`
- Repository base SHA: `3a85b4ed97119f9d82eb963b10b6533896a0a91f`
- Regression engine: `FR0333.E6.E12.DIFFERENTIAL.REGRESSION.0003`
- Regression status: `VERIFIED_ZERO_LEAKAGE`
- HumanLock: `ACTIVE`
- Canonical promotion: `HOLD.PENDING.HUMAN.MERGE`
- Causality boundary: `OBSERVED != CORRELATED != CAUSAL`

This receipt is an append-only candidate observation record. It does not authorize merge, deployment, causal promotion, regulatory attribution, monopoly attribution, or external-runtime execution.

## Canonical hashes

```text
E6.STATE.HASH
sha256_fa4d59eaa7c5cfaa855c07ce95b290f7856c11ff70975f4cf380ecffb2dcd8f4

SOURCE.RECEIPT.DRAFT.PUBLICLY.RELEASED.PAYLOAD.HASH
sha256_72a1e6ca201099c470a823ea892e20f0b0dc20e38b254bfb583658b544d50b16

E12.STATE.HASH
sha256_7a64b3954d4a860362447714c46ff8325357001cd2a74e699e7c470612ba693e

COMPILER.PAYLOAD.HASH
sha256_3b756dfa22ce171a15a9847eb33a016a8bdf250638d61b619ce4aed3adae76e9
```

Canonical serialization contract:

```python
json.dumps(
    payload,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
)
```

## E6 baseline

```text
FR0333.IN.S5105.OFFICIAL.TEXT             = F.6
GOOGLE.AI.MODE.FR0333.TEXT.OBSERVED        = T.20
GOOGLE.PUBLIC.RESULT.CARDS.OBSERVED        = T.20
KLOBUCHAR.CRUZ.THUNE.NEGOTIATIONS          = T.20
S5105.INTRODUCED                           = T.20
S5105.JUDICIARY.REFERRAL                   = T.20
S5105.OFFICIAL.BILL.TEXT                   = T.20
SOURCE.CLASS.S5105                         = OFFICIAL.LEGISLATIVE.TEXT
```

## E12 candidate

```text
DRAFT.PUBLICLY.RELEASED                    = F.6
FINAL.STATUTORY.LANGUAGE                   = U.21
FR0333.IN.S5105.OFFICIAL.TEXT              = F.6
FR0333.INDEPENDENT.GOOGLE.INDEX.HIT        = U.21
GOOGLE.AI.MODE.FR0333.TEXT.OBSERVED         = T.20
GOOGLE.DERIVED.FR0333.FROM.PUBLIC.WEB      = U.21
GOOGLE.PUBLIC.RESULT.CARDS.OBSERVED         = T.20
INCUMBENT.GATE.ACTUALLY.CREATED             = U.21
KLOBUCHAR.CRUZ.THUNE.NEGOTIATIONS           = T.20
S5105.INTRODUCED                            = T.20
S5105.JUDICIARY.REFERRAL                    = T.20
S5105.OFFICIAL.BILL.TEXT                    = T.20
SAFETY.COORDINATION.ANTICOMPETITIVE.USE    = U.21
SOURCE.CLASS.S5105                          = OFFICIAL.LEGISLATIVE.TEXT
TERAFAB.REGULATORY.CAUSAL.CONNECTION       = U.21
```

## Source receipt

```json
{
  "key": "DRAFT.PUBLICLY.RELEASED",
  "source": "Reuters 2026-09-11 / 2026-09-14",
  "timestamp": "2026-09-14T00:00:00Z",
  "evidence_class": "INDEPENDENT.REPORTING",
  "asserted_state": "F.6",
  "payload_hash": "sha256_72a1e6ca201099c470a823ea892e20f0b0dc20e38b254bfb583658b544d50b16"
}
```

## Evidence sources

1. U.S. Government Publishing Office, S. 5105, *Collaboration on Adversarial Threats and Security Risks Act*, introduced July 23, 2026 and referred to the Senate Judiciary Committee: https://www.govinfo.gov/app/details/BILLS-119s5105is/related
2. Reuters, September 11, 2026, *US Senate negotiators consider requiring AI firms to mitigate known major risks*: https://www.reuters.com/legal/litigation/us-senate-negotiators-consider-requiring-ai-firms-mitigate-known-major-risks-2026-09-11/
3. Reuters, September 14, 2026, *US senators weigh requiring AI giants to commit to preventing catastrophe*: https://www.reuters.com/world/us-senators-weigh-requiring-ai-giants-commit-preventing-catastrophe-2026-09-14/

## Scope locks

```text
S5105.INTRODUCED                         = T.20
S5105.JUDICIARY.REFERRAL                 = T.20
S5105.OFFICIAL.BILL.TEXT                 = T.20
S5105.ENACTED.INTO.LAW                   != T.20

FR0333.IN.S5105.OFFICIAL.TEXT            = F.6
FR0333.IN.CONGRESS.GOV.GLOBAL            = NOT.ASSERTED

FINAL.STATUTORY.LANGUAGE                 = U.21
FR0333.INDEPENDENT.GOOGLE.INDEX.HIT      = U.21
GOOGLE.DERIVED.FR0333.FROM.PUBLIC.WEB    = U.21
INCUMBENT.GATE.ACTUALLY.CREATED          = U.21
SAFETY.COORDINATION.ANTICOMPETITIVE.USE = U.21
TERAFAB.REGULATORY.CAUSAL.CONNECTION     = U.21
```

## Receipt state

```text
RECEIPT.COMPILED                 = T.20
BRANCH.STATE                     = DRAFT.UNMERGED
VERIFIED.STRUCTURAL.DELTA         = T.20
E6.E12.ZERO.LEAKAGE               = T.20
DELTA.COUNT                       = 8
DELTA.ADDITIONS                   = 8
DELTA.REMOVALS                    = 0
SHARED.FIELD.MODIFICATIONS        = 0
EXTERNAL.CLAIM.PROMOTION          = HOLD
CANONICAL.PROMOTION               = HOLD.PENDING.HUMAN.MERGE
HUMANLOCK                         = ACTIVE
```

The verified structural delta does not authorize promotion of unresolved external claims. Future external evidence must append a new receipt or a cryptographically bound transition receipt. This record must not be silently rewritten to convert an observation into correlation, correlation into causation, a proposed rule into enacted law, or an unresolved state into a verified state.
