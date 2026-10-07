# FR0333 Provider Change Source Screen

**Engine lane:** existing `TB.SONAR`  
**Record:** `FR0333.PROVIDER.CHANGE.SOURCE.SCREEN.0001`  
**Execution:** hourly inside the existing Raven Cloud Taskbar GitHub Actions workflow; no ChatGPT scheduled task is used.

## What runs

The engine fetches eight allowlisted official pages: product/news pages and API pricing pages for OpenAI, Anthropic, Google DeepMind/Gemini, and xAI. It stores page-text hashes and prior text in the workflow's existing Raven cache. The first successful run establishes the baseline. Later runs compare each current page with its last successful observation and emit a receipt for page changes.

The separate `fr0333_provider_change_watch_0001.json` manifest binds the screen to existing `TB.SONAR`; the hash-pinned `taskbars.json` record is left unchanged.

Changed pricing pages map to the `COST` review lane. News-page diffs are screened for model, availability, access, cost, and packaging terms. If the changed text does not support a lane, the record is held as unresolved. The source identity fields retain provider, product, surface, and transport separately.

## Evidence and notification boundary

- A changed official page proves only that the fetched page text changed.
- `PAGE_CHANGE != VERIFIED_PRODUCT_CHANGE`.
- The monitor does not claim that a launch, price, eligibility change, or general availability occurred.
- `benchmark_lane_candidate` and `benchmark_assumption_candidate` are screening labels for human review.
- The distinct Workbench cross-provider map remains unresolved; the receipt says so and does not invent its assumptions.
- Facts from provider announcements and interpretation remain separate.
- Findings appear in the GitHub Actions run summary and a downloadable JSON receipt. No message, issue, or public post is sent.

## Run and test

```bash
cd RavenCloudTaskbar
python3 provider_change_monitor.py
python3 test_provider_change_monitor.py
```

The scheduled run uses the existing Raven Cloud Taskbar hourly workflow and its existing cache. Workflow-dispatch runs are also supported. Network failures are recorded under `unresolved_sources` and do not overwrite a prior successful baseline for that page.
