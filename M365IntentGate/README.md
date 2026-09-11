# FR0333 M365 Intent Gate Metrics Fixtures

`FR0333.M365.INTENT.GATE.METRICS.FIXTURES.0001` is the deterministic local fixture suite for `FR0333.M365.INTENT.GATE.METRICS.0001`, bound to parent matrix `FR0333.M365.INTENT.GATE.MATRIX.0001`.

## State

`LOCAL.EVALUATION`

The classifier consumes explicit structural categories. It does not infer routing confidence from the natural-language meaning of `SOURCE.INTENT`.

## Baseline

- 12 inputs
- 12 classified outputs
- 7 exact matches
- 3 strong matches
- 1 ambiguous input
- 1 no-match input
- 0 dropped outputs
- 0 duplicated outputs
- 1 contradiction flag
- 1 HumanLock requirement
- 0 accepted C.9 outputs
- 0 external executions
- 0 provider request envelopes

F.11 uses `C.8.REJECT` as its primary consequence and `C.7.CONTRADICTION.DETECTED` as a secondary flag. It remains one classified output.

F.12 deliberately repeats F.02 wording while retaining an independent fixture identifier. Duplicate detection operates on record identity rather than repeated language.

## Mutation boundary

Four mutations independently attempt to drop an output, duplicate an output, set external execution to one, and break the confidence-count sum. Each must return `C.9.BOUNDARY.BREACH` with no receipt.

## Receipt

The accepted baseline serializes inputs and outputs canonically, computes SHA-256 digests, and emits a local evaluation receipt with HumanLock active. The deterministic fixture run uses an injected UUIDv4 and timestamp; production randomness is not claimed.

## Run

```bash
python3 -m unittest M365IntentGate.test_m365_intent_gate_metrics -v
python3 -m M365IntentGate.run_fixture_suite
```

## Boundaries

`LOCAL.TEST.PASS != AUTHENTICATED.RUNTIME`

`C.9.COUNT.0 != PROOF.OF.PRODUCTION.SAFETY`

`PROVIDER.ENVELOPE.STATE.BLOCKED`

`EXTERNAL.EXECUTION.COUNT.0`
