# FR0333 Cash App Observation 001

`FR0333.REVENUE.AUDITANCE.CASHAPP.OBSERVATION.001` is a read-only evidence normalization layer. It does not authenticate to Cash App, call Cash App APIs, move money, initiate payments, infer bank status, or grant authority to transact.

## Required input

- `SOURCE_EVENT_ID`
- `SOURCE_RECORD_TYPE`
- `SOURCE_TIMESTAMP`
- `SOURCE_AMOUNT`
- `SOURCE_STATUS`
- `SOURCE_PARTIES`
- `SOURCE_FEE`
- `SOURCE_REFERENCE`
- `SOURCE_DOCUMENT_HASH`
- `SOURCE_EVIDENCE_CLASS`

The adapter also requires `PROVIDER=CASH_APP` and `MODE=READ_ONLY`.

## Provider evidence gate

Only `SOURCE_EVIDENCE_CLASS=PROVIDER_RECORD` can be normalized as an observed provider record. Screenshot-only, user-asserted, or other evidence remains below that gate.

`CASH_APP_SCREENSHOT_ONLY != PROVIDER_RECORD_VERIFIED`

## No automatic promotion

A provider record is evidence that Cash App recorded something. It does not by itself prove legal settlement, reconciliation, deposit insurance, surety-bond coverage, revenue recognition, realized FR0333 value, ownership transfer, reserve amount, refund exposure, or chargeback exposure.

Therefore the normalized runtime event defaults to:

- `SETTLEMENT_STATUS=UNKNOWN`
- `RECONCILIATION_STATUS=NOT_RECONCILED`
- `BOND_STATUS=NOT_VERIFIED`
- `INSURANCE_STATUS=NOT_VERIFIED`
- `FDIC_STATUS=NOT_VERIFIED`
- `ENCUMBRANCE_STATUS=NOT_VERIFIED`
- `REFUND_EXPOSURE=UNKNOWN`
- `CHARGEBACK_EXPOSURE=UNKNOWN`
- `RESERVE_AMOUNT=UNKNOWN`
- `AMOUNT_NET=UNKNOWN`
- `VALUE_REALIZED=UNKNOWN`

The raw provider `SOURCE_STATUS` is preserved separately and is never mapped directly to `SETTLED`.

## Runtime relationship

The adapter is the only intended path in this generation that calls `validate_event(..., allow_live=True)`. The base runtime continues to reject `OBSERVED_LIVE` events presented directly without the adapter.

## Authority ceiling

Every observation receipt fixes:

- `live_money_movement = 0`
- `live_financial_execution = 0`
- `authority_to_move_funds = false`

No Cash App credentials or live API calls are used by this implementation or its CI fixtures.
