# FR-0333 Adobe Studio Alignment Runbook

Status: `CODE_ALIGNED / RUNTIME_HOLD`

Observed on: 2026-08-24

## Controlling definition

`FR0333.ADOBE.STUDIO` is the FR-0333 orchestration, receipt, and release-control lane that uses Adobe Firefly Services as an image provider. It is not the Adobe Firefly web application and it does not become an Adobe-owned product by name or integration.

The governing execution chain is:

`SOURCE_LOCK -> REQUEST_ASSERT -> OAUTH -> ASYNC_SUBMIT -> BOUNDED_POLL -> DOWNLOAD_ALLOWLIST -> DECODE -> 1080x1920 -> SHA256 -> PROVENANCE_INSPECTION -> HUMAN_APPROVAL -> MERGE -> PRODUCTION`

## Compatibility result

| Layer | Current code state | Required runtime evidence | Gate |
|---|---|---|---|
| Evidence gate | Append-only observations and exact-byte SHA-256 are implemented | CI pass on current head | Merge |
| Render engine | PNG/JPEG decode, 9:16 validation, and artifact hash are implemented | Exact 1080x1920 provider artifact | Staging |
| Adobe authentication | OAuth server-to-server exchange is implemented | Successful token exchange with protected secrets | Staging |
| Adobe generation | Current v3 async and opt-in v4/Image5 profiles are implemented | Job ID, bounded status polling, successful result | Staging |
| Network safety | HTTPS status/output allowlists and bounded retries are implemented | No rejected redirect or unexpected host | Staging |
| Engine/kernel alignment | Evidence, lifecycle, receipt, index, stackbar, and compatibility modules remain separated | Full current-head CI | Merge |
| Content Credentials | Adobe states that Firefly API outputs receive Content Credentials | Inspect the exact downloaded bytes | Publicity |
| Public release | Automatic posting is disabled | Content Credentials pass plus direct human approval | Publicity |
| Merge | Automatic merge is disabled | Current head, successful CI, review state, and accurate PR body | Merge |
| Production | No public endpoint is created | Separate security, hosting, rollback, and operational receipts | Production |

## Genius statistics contract

The score is descriptive evidence accounting, not prediction:

- `evidence_coverage_bps = covered checks / total checks * 10000`
- `verified_alignment_bps = verified checks / total checks * 10000`
- `weighted_alignment_bps = verified weight / total weight * 10000`
- A release target opens only when every check assigned to that target is `VERIFIED`.

`OBSERVED != VERIFIED != PROBABLE != CAUSAL`

The receipt preserves raw check states so a high percentage cannot override one required `HOLD` or `FAILED` check.

## Adobe API profiles

### `v3_async` — default

Endpoint: `POST https://firefly-api.adobe.io/v3/images/generate-async`

This matches Adobe's current general quickstart and permits the FR-0333 request to specify width and height. It is the default until Image5 completes a repository-specific live receipt.

### `v4_image5` — opt-in

Endpoint: `POST https://firefly-api.adobe.io/v4/images/generate-async`

The request uses `aspectRatio: 9:16`, `modelId: firefly_image`, one variation, no reference blobs for text-to-image, and the quality prompt reasoner. Adobe describes Image5 as the newer realism-oriented model. Because the v4 request specifies aspect ratio rather than an exact output size, the returned artifact must still pass the exact 1080x1920 master gate.

## Secret and rate controls

Create a protected GitHub Environment named `adobe-staging`. Store these only as Environment secrets:

- `FIREFLY_SERVICES_CLIENT_ID`
- `FIREFLY_SERVICES_CLIENT_SECRET`

Never place the secret, access token, signed output URL, or raw authorization headers in source, workflow inputs, logs, PR comments, or receipts.

The provider defaults to a 15-second polling interval. Adobe currently documents a default Firefly API limit of four requests per minute per organization and recommends `Retry-After` or exponential backoff for HTTP 429. The implementation retries 429 and server errors within a bounded window.

## Safe execution

The `Adobe Staging Gate` workflow is manual only.

Simulation:

1. Select `simulation`.
2. The job compiles and tests every target.
3. It emits a deterministic local 1080x1920 PNG and an alignment receipt.
4. The receipt remains `SIMULATION`; Adobe runtime, publicity, merge, and production stay closed.

Live staging:

1. Select `live`.
2. Select `v3_async` or opt into `v4_image5`.
3. Enter exactly `STAGING_ONLY` in the confirmation field.
4. The protected environment supplies the credentials.
5. One variation is requested, polled, downloaded, decoded, dimension-checked, and hashed.
6. The raw provider artifact and JSON receipt are retained for seven days.
7. No public endpoint, post, merge, or production deployment occurs.

## Publicity gate

Adobe's official documentation says Content Credentials are automatically applied to Firefly and API-generated content. That vendor statement is a source claim. FR-0333 still requires artifact-level inspection of the exact downloaded bytes before public release.

The publicity gate requires:

- exact artifact SHA-256;
- exact 1080x1920 dimensions;
- inspected Content Credentials on the exact bytes;
- prompt/source lineage retained without secrets;
- identity, anatomy, text, logo, and drift review;
- direct human approval for the exact final artifact.

No successful API response bypasses these controls.

## Merge gate

Before merging PR #1:

- re-fetch the current head SHA;
- require successful CI for that exact head;
- inspect review and comment state;
- correct stale SHA or CI claims in the PR body;
- retain runtime, publicity, and production items as unchecked unless their separate receipts exist.

`CI_SUCCESS != ADOBE_RUNTIME_SUCCESS != PUBLICATION_APPROVAL != PRODUCTION_DEPLOYMENT`

## Official Adobe basis

- [Firefly API quickstart](https://developer.adobe.com/firefly-services/docs/firefly-api/guides/)
- [Firefly asynchronous API](https://developer.adobe.com/firefly-services/docs/firefly-api/guides/how-tos/using-async-apis)
- [Image5 feature guide](https://developer.adobe.com/firefly-services/docs/firefly-api/guides/how-tos/cm-generate-image/feature-guide)
- [Firefly API usage notes](https://developer.adobe.com/firefly-services/docs/firefly-api/getting-started/usage-notes/)
- [Adobe Developer Console authentication](https://developer.adobe.com/firefly-services/docs/firefly-api/getting-started/dev-console/)
- [Content Credentials overview](https://helpx.adobe.com/creative-cloud/apps/adobe-content-authenticity/content-credentials/overview.html)
- [Adobe Firefly product description](https://helpx.adobe.com/legal/product-descriptions/adobe-firefly.html)
