# FR0333 Revenue Auditance Runtime 001

State: `SIMULATION_CI_VERIFIED` for the runtime meter. Live money movement and live financial execution remain `0`.

## Purpose

`FR0333.REVENUE.AUDITANCE.RUNTIME.001` accepts one money-event record, validates its state transitions, generates a deterministic SHA-256 receipt, and refuses to convert unknown monetary or protection states into positive claims.

## Non-equivalence gates

- `MONEY_IN != REVENUE`
- `AVAILABLE != SETTLED`
- `SETTLED != RECONCILED`
- `RECONCILED != PROTECTED`
- `PROTECTED != INSURED`
- `TRANSACTION_VALUE != REALIZED_FR0333_VALUE`
- `UNKNOWN_PROTECTION_STATE = UNKNOWN`, not `SAFE`
- `UNVERIFIED_EXPOSURE != ZERO_EXPOSURE`
- `UNVERIFIED_MONEY_STATE != ZERO`
- `SYNTHETIC != LIVE_FINANCIAL_EXECUTION`

## Arithmetic and unknown-money rule

When `reserve_amount` is known, the runtime requires:

`amount_net = amount_gross - fee_amount - reserve_amount`

When `reserve_amount = UNKNOWN`, the runtime requires `amount_net = UNKNOWN` rather than inventing a numeric value.

`refund_exposure`, `chargeback_exposure`, and `value_realized` may also remain `UNKNOWN` when evidence does not establish them.

## Cash App observation boundary

`FR0333.REVENUE.AUDITANCE.CASHAPP.OBSERVATION.001` is now implemented as a separate read-only adapter and CI-validated against synthetic provider-record fixtures.

The adapter does not call Cash App APIs, use Cash App credentials, or move money. It is the only intended path in this generation that may call runtime validation with `allow_live=True`, and only after `SOURCE_EVIDENCE_CLASS=PROVIDER_RECORD` passes the provider-evidence gate.

Even then, a provider record is not automatically promoted to settlement, reconciliation, FDIC insurance, bond coverage, revenue, reserve amount, net availability, or realized value.

The base runtime still rejects direct `OBSERVED_LIVE` ingestion that bypasses the adapter.
