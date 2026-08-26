# GitHub Webhook Evidence Brief

Evidence date: 2026-08-26 UTC

## Target PR snapshot

Observed through the connected GitHub repository on 2026-08-26 UTC:

- PR #1: open, draft, unmerged, and GitHub-reported mergeable
- Head branch and SHA: `zllg-1.0.1-prototype` at `0bfb49f90d893496162391a0dbea05a8e0367253`
- Current-head workflow evidence: `ZLLG Rust CI` run #66, run ID `32695461330`, completed with conclusion `success`
- Review submissions: 0
- Review threads: 0
- Combined PR comments/review timeline items: 0
- Commit statuses returned by the connected status read: 0

This is a point-in-time observation, not a continuing monitor and not deployment evidence. The receiver is configured to establish later deltas from signed deliveries and live read-only refreshes.

## Observed public record

| Date | Observed change | Evidence |
|---|---|---|
| 2014-02-11 | GitHub described webhooks as its most widely adopted integration and expanded repository configuration and delivery inspection/redelivery. | [Webhooks Level Up](https://github.blog/news-insights/webhooks-level-up/) |
| 2014-12-03 | GitHub introduced organization webhooks. | [Introducing organization webhooks](https://github.blog/news-insights/product-news/introducing-organization-webhooks/) |
| 2018-08-13 | GitHub added repository-import completion/failure webhooks. | [GitHub Importer webhook](https://github.blog/changelog/2018-08-13-porter-webhooks/) |
| 2020-01-13 | GitHub added sponsorship webhooks. | [GitHub Sponsors webhooks](https://github.blog/changelog/2020-01-13-github-sponsors-webhooks/) |
| 2021-03-30 | GitHub released Discussions webhook events in public beta. | [GitHub Discussions webhooks](https://github.blog/changelog/2021-03-30-github-discussions-webhooks-public-beta/) |
| 2021-06-30 | GitHub added REST endpoints to list, inspect, and redeliver webhook deliveries. | [Webhook Deliveries API](https://github.blog/changelog/2021-06-30-webhook-deliveries-api/) |
| 2022-10-06 | GitHub introduced a Dependabot-alert webhook to supersede the older repository-vulnerability event. | [Dependabot alerts webhook](https://github.blog/changelog/2022-10-06-new-dependabot-alerts-webhook/) |
| 2022-11-16 | GitHub began generating webhook reference documentation from its OpenAPI schema. | [Webhook docs from OpenAPI](https://github.blog/changelog/2022-11-16-webhook-docs-generated-from-the-openapi-schema/) |
| 2023-04-11 | GitHub CLI webhook forwarding became generally available for local development. | [Webhook forwarding in GitHub CLI](https://github.blog/changelog/2023-04-11-webhook-forwarding-in-the-github-cli/) |
| 2023-07-12 | Merge queue GA added and corrected `merge_group` and `pull_request.dequeued` webhook behavior. | [Pull request merge queue GA](https://github.blog/changelog/2023-07-12-pull-request-merge-queue-is-now-generally-available/) |
| 2023-10-17 | GitHub reduced UI delivery-log retention to three days, reinforcing the need for an owned receipt ledger. | [Webhook delivery log retention](https://github.blog/changelog/2023-10-17-webhook-delivery-logs-will-only-be-retained-for-3-days/) |
| 2024-02-12 | Secret-scanning webhooks added validity-check state. | [Secret scanning validity webhooks](https://github.blog/changelog/2024-02-12-secret-scanning-adds-webhook-support-for-validity-checks/) |
| 2024-06-27 | Projects added webhook support for project status updates and custom-field changes. | [Projects webhook updates](https://github.blog/changelog/2024-06-27-github-issues-projects-graphql-and-webhook-support-for-project-status-updates-and-more/) |
| 2024-11-05 | GitHub Actions documented a per-repository webhook-trigger rate limit of 1,500 events per ten seconds. | [GitHub Actions breaking changes](https://github.blog/changelog/2024-11-05-notice-of-breaking-changes-for-github-actions/) |
| 2025-04-07 | GitHub changed the repository object sent in push webhook payloads. | [Push webhook repository-object change](https://github.blog/changelog/2025-04-07-changes-to-the-repository-object-in-push-webhook/) |
| 2025-08-21 | Issue dependencies became supported in GitHub APIs and webhooks. | [Dependencies on issues](https://github.blog/changelog/2025-08-21-dependencies-on-issues/) |
| 2025 report | GitHub reported more than 180 million developers, 630 million total repositories, and 518.7 million pull requests merged, with merged PRs up 29% year over year. | [Octoverse 2025](https://github.blog/news-insights/octoverse/octoverse-a-new-developer-joins-github-every-second-as-ai-leads-typescript-to-1/) |
| 2026-03-10 | GitHub released REST API version `2026-03-10`, which this bridge requests explicitly. | [GitHub REST API versions](https://docs.github.com/en/rest/about-the-rest-api/api-versions) |

GitHub webhooks therefore have a public operating history of at least twelve years as of this evidence date.

This table is a material-milestone review, not a claim to enumerate every event-field addition or correction GitHub has ever shipped. GitHub's generated [webhook event and payload reference](https://docs.github.com/en/webhooks/webhook-events-and-payloads) is the authoritative current schema surface.

## What is not publicly established

The reviewed GitHub sources do not publish an exact count of unique webhook users, active webhook configurations, or webhook delivery volume over time. GitHub-wide developer, repository, and pull-request counts are platform-scale context; they are not webhook adoption counts.

Accordingly:

- Exact current webhook users: **INSUFFICIENT PUBLIC EVIDENCE**
- Exact former webhook users: **INSUFFICIENT PUBLIC EVIDENCE**
- Webhook volume increasing or decreasing: **NOT DIRECTLY MEASURED IN THE PUBLIC SOURCES REVIEWED**
- Inference: continuing event additions, delivery tooling, and GitHub platform growth are consistent with increased webhook opportunity and traffic, but they do not prove a webhook-specific growth rate

## Engineering implications used in this build

- Own the receipt ledger because GitHub's UI log window is short.
- Treat payload schemas as versioned inputs because GitHub changes fields and event surfaces.
- Make replay safe because redelivery is a standard operating path.
- Bind CI evidence to the current PR head SHA.
- Keep raw comment and review text out of telemetry.
- Keep observed state, interpretation, and next action in distinct fields.
- Acknowledge quickly and perform live state resolution in the background.

## Candidate comparison

Baseline commit `bd89668` contained no GitHub webhook receiver or GitHub-specific fixture suite. The candidate adds a 64-case GitHub suite. The absolute fixture-coverage delta is +64; a multiplicative “10×” ratio is undefined against a zero-case baseline. Live usefulness, false-alert rate, delivery loss, and time-to-alert remain uncalibrated until production outcomes exist.

`99.1V` is retained as a build/version label only. It is not represented as a probability.
