# FR0333 Work Trunk Branch Fabric 0005

`FR0333.WORK.TRUNK.BRANCH.FABRIC.0005` is stacked on the exact PR #54 head
`11521564aee008ab21fdced77e75f78b93f7d912`.

## Boundary

This is a durable workflow control plane. It does not alter ChatGPT, Adobe, or
any model weights; grant account entitlements; or guarantee that an external
provider never fails. It makes authorized work recoverable after a worker,
process, or individual branch stops.

`WORKER.STOPS != WORK.LOST`

`BRANCH.FAILS != SYSTEM.FAILS`

`RETRY != DUPLICATE.EXECUTION`

`CONTINUITY != HUMANLOCK.BYPASS`

## Controls

- SQLite WAL durable queue and canonical ledger
- transactional single-worker claims
- expiring worker leases and standby reassignment
- checkpoint/resume without conversational-memory authority
- deterministic idempotency keys and unique output hashes
- lane-local circuit breakers for Chat, Engine, and Adobe
- dead-letter preservation and HumanLock-controlled replay
- append-only SHA-256 receipt chain
- exact output-count enforcement, including `TEN_IN -> TEN_OUT`
- shadow mode blocking every external action

## State flow

`QUEUED -> CLAIMED -> EXECUTING -> COMPLETED`

Temporary failures enter `RETRY.WAIT`. Exhausted retries enter
`DEAD.LETTER`; the checkpoint remains intact. Expired `CLAIMED` or `EXECUTING`
leases return to `QUEUED` and may be claimed by a standby worker.

## Branch isolation

An open circuit blocks only its own lane. An Adobe outage does not stop Chat or
Engine. A Chat disconnect does not erase queued work. HumanLock stays active
during claim, checkpoint, completion, failover, and dead-letter replay.

## Shadow-mode limits

The fabric may create local receipts and test fixtures. It cannot publish,
deploy, merge, spend, transfer data, or promote economic events. Those actions
require separate per-action authorization and are not implemented here.

## Verification

```bash
python -m unittest -v tests.test_work_trunk_branch_fabric_v5
python -m unittest discover -s tests -v
```

Passing tests establish local continuity behavior under simulated faults. They
do not establish 24/7 hosting, provider uptime, or production deployment.
