# FR0333 GitHub Webhook Bridge

State: **BUILT AND FIXTURE-VERIFIED; NOT DEPLOYED; NOT PRODUCTION-RUNTIME-VERIFIED**

`FR0333_GITHUB_WEBHOOK.99.1V.1` is a read-only GitHub webhook receiver for actionable changes on `awsmith888-creator/FR0333_REVENUE_ENGINE` pull request #1. The `99.1V` string is a version label. It is not a 99.1% probability or a calibrated reliability claim.

## What it monitors

- Review submissions, review comments, conversation comments, and review-thread resolution changes
- GitHub Actions workflow runs, check suites, and commit statuses bound to the configured PR head
- PR head, draft, open/close, and merge state changes
- Mergeability changes found by an optional read-only GitHub API refresh

Every alert keeps these fields separate:

- `observed_state`: normalized fields taken from the signed delivery or a live GitHub API read
- `evidence`: delivery ID, payload hash, timestamp, source, repository, and PR binding
- `interpretation`: bounded explanation; never presented as observation
- `next_review_action`: the next human review step; the bridge does not merge, comment, rerun CI, or deploy

## Security and reliability controls

- HMAC-SHA256 verification against the untouched request body
- UUID delivery-ID validation and durable SQLite replay protection
- Different-payload delivery-ID collision rejection
- Repository, event, branch, and PR filters
- Streaming payload limit, with a maximum configurable value no higher than GitHub's 25 MB delivery limit
- No raw payload retention; comment, title, review, and PR-body text becomes SHA-256 evidence only
- Protected receipt, event, alert, and metric endpoints
- Bounded invalid-signature receipt retention
- Background read-only state resolution, so the webhook can acknowledge promptly
- HTTPS-only GitHub API reads with redirects rejected before a read token could cross hosts
- SQLite WAL ledger with full synchronization and restart-persistent deduplication
- Structured alert records on stdout for deployment telemetry, plus a protected alert API
- Non-root container process with an HTTP health check

## Runtime routes

| Route | Access | Purpose |
|---|---|---|
| `GET /github/status` | Public, no secrets | Configuration booleans and build boundary |
| `POST /github/webhook` | GitHub signature required | Delivery intake |
| `GET /github/alerts` | `X-FR0333-Read-Token` | Actionable-change records |
| `GET /github/events` | `X-FR0333-Read-Token` | Privacy-reduced event vectors |
| `GET /github/receipts` | `X-FR0333-Read-Token` | Delivery and resolution receipts |
| `GET /github/metrics` | `X-FR0333-Read-Token` | Counts and local processing latency |

## Required deployment configuration

Keep every secret outside source control.

```text
GITHUB_WEBHOOK_SECRET=<at least 32 random bytes>
GITHUB_BRIDGE_READ_TOKEN=<at least 24 random bytes>
GITHUB_WEBHOOK_REPOSITORY=awsmith888-creator/FR0333_REVENUE_ENGINE
GITHUB_WEBHOOK_PULL_REQUEST=1
GITHUB_WEBHOOK_HEAD_BRANCH=zllg-1.0.1-prototype
GITHUB_WEBHOOK_BASE_BRANCH=main
GITHUB_WEBHOOK_DB=/var/lib/fr0333/github-webhook.sqlite3
GITHUB_MAX_PAYLOAD_BYTES=2000000
GITHUB_MAX_REJECTION_RECEIPTS=1000
GITHUB_ALERT_STDOUT=true
```

For live mergeability and current-state confirmation, add:

```text
GITHUB_LIVE_RESOLUTION=true
GITHUB_READ_TOKEN=<fine-grained, read-only GitHub token>
```

The token needs read access sufficient for the configured repository's pull request, reviews, issue comments, Actions runs, checks, and commit statuses. A token is normally required for a private repository and raises the API rate limit for a public one. No write permission is needed.

Mount `/var/lib/fr0333` on persistent encrypted storage. If the database is left under `/tmp`, restart-persistent deduplication is not guaranteed by the hosting platform.

Run one writable receiver instance against this SQLite ledger. Before horizontally scaling the receiver, move the receipt reservation, event ledger, and alert ledger to a shared transactional database or queue with an atomic delivery-ID constraint.

## GitHub repository webhook

After the service has a public HTTPS URL:

1. Open the repository's **Settings → Webhooks → Add webhook** page.
2. Set the payload URL to `https://<host>/github/webhook`.
3. Select `application/json`.
4. Enter the same high-entropy value used for `GITHUB_WEBHOOK_SECRET`.
5. Keep SSL verification enabled.
6. Select individual events for pushes, pull requests, pull-request reviews, pull-request review comments, issue comments, workflow runs, check suites, and commit statuses. Add review-thread events if GitHub exposes that selection for the repository/app configuration. Push events are filtered to the configured PR head and base branches and trigger a read-only mergeability refresh.
7. Confirm the initial `ping` delivery returns HTTP 200, then inspect its delivery ID and matching local receipt.

GitHub recommends returning a 2xx response within ten seconds, validating `X-Hub-Signature-256` against the raw body, using `X-GitHub-Delivery` for replay protection, and processing work asynchronously. This implementation follows those controls.

## Verification

```bash
python -m unittest discover -s tests -v
python github_webhook_benchmark.py --output /tmp/fr0333-github-benchmark.json
docker build -t fr0333-github-webhook:local .
```

The benchmark must report exactly 64 fixtures, 64 passes, and zero critical failures. A test pass is not deployment proof. Production runtime verification additionally requires a real GitHub `ping`, a signed target event, protected telemetry retrieval, restart/replay verification on the deployed volume, and an alert observed through the chosen live telemetry channel.

The baseball live-data lane is separate. Its telemetry neither hosts nor validates this receiver.

## Evidence boundary

`OBSERVED != INTERPRETATION; TEST_PASS != DEPLOYMENT; MERGEABLE != MERGED`

The bridge performs no repository writes and no paid external calls.
