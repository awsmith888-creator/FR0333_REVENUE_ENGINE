# FR0333 Genius Bar Comparability Normalization

`FR0333.GENIUS.BAR.COMPARABILITY.NORMALIZATION.0001` is the controlling specification and implementation rail for converting source statistics into canonical reference-point records without laundering semantics, denominators, uncertainty, or precision.

## Controlling pipeline

`RAW.STATISTIC → STRUCTURAL.SCHEMA → SEMANTIC.INVARIANT.VALIDATOR → DENOMINATOR.LOCK → REFERENCE.FRAME.LOCK → NORMALIZE → REVERSIBILITY.GATE → CANONICAL.JSON.V1 → SHA256.COMPARABILITY.KEY → CONSUMER.CAPABILITY.GATE → OUTPUT.REPORT`

The database-normalization comparison is conceptual only. This rail performs measurement normalization and semantic binding; it does not claim that relational third-normal-form theory independently validates FR0333 rules.

## Three-state grammar

Only `T.20.PASS`, `U.21.HOLD`, and `F.6.REJECT` are terminal gate states. Approximate values do not create a fourth state. A record may pass normalization while a specific exact-only consumer returns `U.21.HOLD`.

## Reference frames

- `RELATIVE.INCREASE` and `OF.BASELINE`: `REFERENCE.BASE = 100`.
- `COMPOSITION.SHARE`: `FIELD.BASE = 100`.
- A relative increase of 71 maps to `BASE.100 → CURRENT.171`.
- A value of 71 of baseline maps to `BASE.100 → CURRENT.71 → DELTA.-29`.
- A composition share of 74.2 maps to `FIELD.100 → CURRENT.74.2` while retaining composition semantics.

## Precision inheritance

`VALUE + QUALIFIER + PRECISION.STATE + UNCERTAINTY.BOUNDS + ROUNDING.RULE = ATOMIC.MEASUREMENT.STATE`

`REVERSIBLE.REPRESENTATION != EXACT.UNDERLYING.TRUTH` remains controlling. `APPROX` and `RANGE` qualifiers survive normalization. A consumer that attempts to detach the precision profile is rejected as `PRECISION.LAUNDERING.DETECTION`.

## Canonical equality and hashing

`EXACT.CANONICAL.DECIMAL.EQUALITY != RAW.BYTE.IDENTITY`: `71`, `71.0`, and `71.0000` may represent the same decimal value.

The comparison fingerprint uses a versioned structured object rather than raw string concatenation:

`RAW.METADATA → CANONICAL.SEMANTIC.OBJECT → CANONICAL.JSON.V1 → UTF8 → SHA256`

Whitespace and case noise in fields declared case-insensitive are normalized before hashing. Semantic changes such as denominator, time basis, semantic operator, method compatibility class, segmentation schema, precision class, or transform version fracture the key.

## Validation layers

1. `STRUCTURAL.SCHEMA`
2. `SEMANTIC.INVARIANT.VALIDATOR`
3. `COMPARABILITY.VALIDATION`
4. `CONSUMER.CAPABILITY.GATE`

`SCHEMA.VALID != SEMANTICALLY.VALID != COMPARABLE != CONSUMER.COMPATIBLE`.

## Receipt boundary

The implementation can issue a `HASH_BOUND.DETERMINISTIC.EXECUTION.RECEIPT`. It is explicitly `NOT.CRYPTOGRAPHICALLY.SIGNED`. A signed receipt may be claimed only after a signing key, signature algorithm, signer identity, and verification path are established.

CI proves repository behavior only. `SPECIFICATION.PASS != IMPLEMENTATION.PASS != RUNTIME.ENFORCEMENT`; external runtime enforcement remains unestablished until a separate authenticated execution receipt exists.

## Golden Chain

Draft registration: `GC.SB.0030`, predecessor `GC.SB.0029`. Promotion is blocked until predecessor order and review gates are satisfied.
