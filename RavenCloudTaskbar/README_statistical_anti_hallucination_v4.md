# FR0333 Statistical Anti-Hallucination Hardener 0004

`FR0333.SYSTEM.STATISTICAL.ANTI.HALLUCINATION.HARDENER.0004` extends
`FR0333.OPERATOR.FOUR.KERNEL.UPGRADE.0003`. It does not rewrite the existing
four-kernel hardener and does not change model weights or platform permissions.

## Kernel contract

All four named kernels must remain active:

`NEWSFLASH -> ESPN.FANTASY.SPORTS -> NELSON -> GENIUS.BAR`

The required bitword is `1111`. Any zero produces `HOLD`.

## Statistical gates

1. Every source has a publisher, lane, evidence class, access date, access
   state, and HTTPS URL.
2. Every promoted claim has a unit, explicit period, truth state, evidence
   relation, and source binding.
3. Derived values are recomputed from recorded inputs; copied arithmetic is not
   trusted.
4. Final sports scores must be dated no later than the reference point. Game
   identifiers must be unique and aggregate totals must recompute.
5. Blocked, JavaScript-only, future-dated, or internally conflicting pages
   cannot promote a `T.20` claim.
6. Sports statistics calibrate date, score, count, arithmetic, and stale-page
   handling. They do not prove art accuracy, cultural causation, image quality,
   revenue, or model leadership.
7. `OBSERVED != DERIVED != CORRELATED != CAUSAL`.
8. HumanLock remains active and automatic promotion remains disabled.

## Frozen reference fixture

The September 20, 2026 fixture contains the Sunday visual-culture statistics,
September 19 MLB finals, the September 17 NFL final, and an ESPN week-routing
conflict preserved as a negative control. It is historical evidence, not a live
feed. A future refresh must create a new dated fixture rather than rewriting it.

## Verification

```bash
python -m unittest -v tests.test_statistical_anti_hallucination_v4
```

Passing structural tests establish validator behavior against the frozen
fixture. They do not establish that every external statistic remains current.
