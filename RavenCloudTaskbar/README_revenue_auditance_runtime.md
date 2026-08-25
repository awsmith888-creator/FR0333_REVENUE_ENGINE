# FR0333 Revenue Auditance Runtime 001

State: `SIMULATION_ONLY` until CI passes and a separate live observation adapter is implemented and independently verified.

## Purpose

`FR0333.REVENUE.AUDITANCE.RUNTIME.001` accepts one money-event record, validates its state transitions, generates a deterministic SHA-256 receipt, and refuses to convert unknown protection states into positive safety claims.

## Non-equivalence gates

- `MONEY_IN != REVENUE`
- `AVAILABLE != SETTLED`
- `SETTLED != RECONCILED`
- `RECONCILED != PROTECTED`
- `PROTECTED != INSURED`
- `TRANSACTION_VALUE != REALIZED_FR0333_VALUE`
- `UNKNOWN_PROTECTION_STATE = UNKNOWN`, not `SAFE`
- `SYNTHETIC != LIVE_FINANCIAL_EXECUTION`

## Arithmetic rule

For the current simulation schema:

`amount_net = amount_gross - fee_amount - reserve_amount`

`refund_exposure` and `chargeback_exposure` are risk exposures, not automatic cash deductions, so they are not subtracted from `amount_net` unless converted to an actual reserve/refund/chargeback event in a future version.

## Promotion ceiling

The runtime may be promoted to `SIMULATION_VERIFIED` only after:

1. schema and gate tests pass;
2. expected-failure fixtures fail with the correct codes;
3. synthetic receipts are generated with deterministic hashes;
4. CI confirms `live_money_movement = 0` and `live_financial_execution = 0`.

`OBSERVED_LIVE` events are intentionally rejected by the simulation runtime unless a separate observation adapter explicitly enables live validation. That adapter is not implemented in this generation.
