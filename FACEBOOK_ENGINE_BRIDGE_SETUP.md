# FACEBOOK_ENGINE_BRIDGE.1

State: `STAY_1 / INTAKE`

Evidence boundary: `OBSERVED != VERIFIED != CORRELATED != CAUSAL`

## Purpose

Receive Meta/Facebook Page webhook events, verify that Meta signed each delivery, preserve the raw event fragment, extract a compact Raven vector, and expose recent intake events to the FR0333 engine without automatically promoting any claim.

## Runtime environment

Set these variables in the deployment environment. Never commit the actual secret values.

- `META_VERIFY_TOKEN` — a long random value you create. Enter the same value in the Meta webhook configuration.
- `META_APP_SECRET` — the App Secret from the Meta developer app.
- `FACEBOOK_EVENT_LOG` — optional JSONL event-log path. Default: `/tmp/fr0333_facebook_events.jsonl`.
- `FACEBOOK_MAX_MEMORY_EVENTS` — optional recent-event buffer. Default: `500`.

## Public routes

- `GET /healthz` — engine health; includes the bridge version.
- `GET /facebook/status` — confirms whether the verify token and app secret are configured. It never returns either secret.
- `GET /facebook/webhook` — Meta subscription verification callback.
- `POST /facebook/webhook` — signed Meta event receiver. Requires `X-Hub-Signature-256`.
- `GET /facebook/events?limit=25` — recent normalized intake vectors from the current runtime.

## Meta-side configuration

1. Create or select a Meta developer app that is authorized for the Facebook Page you control.
2. Add the Webhooks product and select the Page object.
3. Deploy this FastAPI application to a public HTTPS endpoint.
4. Set the Meta Callback URL to:

   `https://YOUR_PUBLIC_HOST/facebook/webhook`

5. Set Meta's Verify Token to exactly the same value as `META_VERIFY_TOKEN` in the deployment environment.
6. Subscribe only to the Page fields you actually need. Start narrow and expand after the first verified delivery.
7. Complete Meta's Page-access-token and permissions flow separately. The bridge does not store a Page access token and does not publish to Facebook.

## First proof sequence

Do not mark the bridge live merely because the files exist.

1. `GET /facebook/status` returns the expected bridge version and both configuration flags are `true`.
2. Meta successfully completes the webhook verification challenge.
3. Meta sends a real signed Page event and receives HTTP 200.
4. `GET /facebook/events` shows the corresponding event with:
   - `evidence_class = OBSERVED`
   - `raven_state = INTAKE`
   - `promotion = NONE`
5. Preserve the Meta-side webhook-delivery evidence and the runtime response as the deployment receipt.

Only after steps 1–5 are demonstrated should runtime status advance from `BUILT / NOT_RUNTIME_VERIFIED` to `LIVE / VERIFIED_DELIVERY`.

## Event contract

Each normalized event contains:

- `engine`
- `source`
- `event_id`
- `observed_at`
- `object`
- `raw`
- `vector`
- `raven_state`
- `evidence_class`
- `evidence_boundary`
- `promotion`

The event ID is a deterministic SHA-256 fingerprint of the received payload plus its entry/change coordinates. Raw content is preserved alongside the vector.

## Persistence boundary

The default JSONL path is local to the running deployment. If the host uses an ephemeral filesystem, that file is not durable across restarts. Attach a persistent volume or replace the log sink with a durable store before treating it as a permanent engine ledger.

## Security boundary

- Do not expose `META_APP_SECRET`, Page access tokens, or verify tokens in chat, source control, screenshots, or event payloads.
- Incoming POST requests are rejected unless the Meta HMAC SHA-256 signature matches the raw request body.
- This version is intake-only. It does not publish, delete, reply, or modify Facebook content.
