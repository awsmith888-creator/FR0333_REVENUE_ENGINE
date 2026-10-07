# FR0333 Provider Change Source Screen

**Engine lane:** existing `TB.SONAR`  
**Record:** `FR0333.PROVIDER.CHANGE.SOURCE.SCREEN.0001`  
**Execution:** hourly inside the existing Raven Cloud Taskbar GitHub Actions workflow; no ChatGPT scheduled task is used.

## What runs

The engine fetches fourteen allowlisted official pages: provider product/news pages, API pricing pages, consumer plan pages for all four providers, the OpenAI status page, and OpenAI's ChatGPT Library help article. Active status incidents are screened on first observation and on page changes. It stores page-text hashes and prior text in the workflow's existing Raven cache. The first successful run establishes the baseline. Later runs compare each current page with its last successful observation and emit a receipt for page changes.

The separate `fr0333_provider_change_watch_0001.json` manifest binds the screen to existing `TB.SONAR`; the hash-pinned `taskbars.json` record is left unchanged.

Each run loads the existing `FR0333.FRONTIER.MODEL.MASTER.BENCHMARK.0001` provider inventory and workload benchmark, records its SHA-256 in the receipt, and matches each candidate to the provider row. Candidate records carry that row's documented frontier options, plan signal, strength tags, existing workload candidates, comparator assumptions, and the unchanged `U.21.UNMEASURED` performance state. Cost candidates point to the `COST` measure and `cost_or_plan_context`; plan/access candidates point to `PROVIDER_ELIGIBILITY_GATE` and plan-access boundaries; model candidates map from existing provider strength tags to workload candidates. These are review routes, not measured outcomes.

The surface comparison keeps the observed official web page separate from the affected product surface. API-price pages map as API observations; news-page candidates keep product/surface unresolved until the exact announcement is identified. The OpenAI status-page source identifies the affected candidate surface and transport as ChatGPT Work thread creation in the desktop application; the Library help article identifies the ChatGPT Library file workflow in the web application. Each retains its official public page as the observed surface. Provider row matches therefore return `PROVIDER_ROW_MATCHED_SURFACE_REVIEW_REQUIRED`. The cross-provider map's runtime states remain controlling: OpenAI is scoped to the current ChatGPT environment, while Anthropic, Google, and xAI remain `U.21.NOT_CONNECTED` in the master. The evidence does not establish cross-provider runtime access.

## Evidence and notification boundary

- A changed official page proves only that the fetched page text changed.
- `PAGE_CHANGE != VERIFIED_PRODUCT_CHANGE`.
- The monitor does not claim that a launch, price, eligibility change, or general availability occurred.
- `benchmark_lane_candidate` and `benchmark_assumption_candidate` are screening labels for human review.
- The receipt names and hashes the existing benchmark map. It does not rewrite that baseline or promote candidates into verified map updates.
- Facts from provider announcements and interpretation remain separate.
- Findings appear in the GitHub Actions run summary and a downloadable JSON receipt. No message, issue, or public post is sent.

## Run and test

```bash
cd RavenCloudTaskbar
python3 provider_change_monitor.py
python3 test_provider_change_monitor.py
```

The scheduled run uses the existing Raven Cloud Taskbar hourly workflow and its existing cache. Workflow-dispatch runs are also supported. Network failures are recorded under `unresolved_sources` and do not overwrite a prior successful baseline for that page.
