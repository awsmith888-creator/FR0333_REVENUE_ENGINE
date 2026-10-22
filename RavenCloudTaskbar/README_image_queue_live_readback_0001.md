# FR-0333 existing-image readback gate 0001

Parent Golden Chain entry: **0.9 FR.0333.GOLDEN.CHAIN.IMAGE.QUEUE.METRICS.0001**.
Preserved diagnosis: **0.8 FR.0333.GOLDEN.CHAIN.IMAGE.QUEUE.FAILURE.CLOSURE.0001**.

## Two lanes

- **ACTIVE / on demand:** \`verify_image_queue_live_readback_0001.py\` reads receipt 0003, independently saved original Adobe request/response exports and final image files. It checks Q01..Q10, exact binding of generation and normalization request IDs/URLs, nonempty bytes, real image decoding, 1080×1920 final dimensions and ten unique SHA-256 values. Optional certificate is local. It never calls Adobe or GitHub and never submits a workflow.
- **PASSIVE / evidence ledger:** missing original records or files remain \`U.21.HOLD\`; a supplied mismatch becomes \`F.6.REJECT\`. The existing receipt's ten-delivery assertion is not promoted by being indexed. Quality review, aesthetics, collage/double-panel inspection, user acceptance and merge remain separate HOLD gates.

## Required input directory (not committed)

\`\`\`
RavenCloudTaskbar/image_queue_live_evidence_0003/
  provider_export_manifest.json
  Q01.generate.response.json
  Q01.normalize.response.json
  Q01.png
  ...
  Q09.generate.response.json  # successful retry response, not rejected initial attempt
  Q09.normalize.response.json
  Q09.png
  ...
  Q10.normalize.response.json
  Q10.png
\`\`\`

Manifest schema (repeat for each Q01..Q10, use IDs and URLs from existing receipt only):

\`\`\`json
{
  "receipt_identifier": "FR0333.ADOBE.IMAGE.QUEUE.RUNTIME.RECEIPT.0003",
  "source_class": "EXISTING_ADOBE_PROVIDER_RESPONSE_EXPORT",
  "slots": [
    {
      "slot_id": "Q01",
      "generation_request_id": "<existing generation request id>",
      "generation_output_url": "<existing generation output url>",
      "normalization_request_id": "<existing normalization request id>",
      "final_output_url": "<existing normalized output url>",
      "generation_response_file": "Q01.generate.response.json",
      "normalization_response_file": "Q01.normalize.response.json",
      "final_file": "Q01.png"
    }
  ]
}
\`\`\`

Q09 binds to \`retry_generation_request_id\` and \`retry_generation_output_url\` from receipt 0003; preserve the failed first attempt in history.

Raw response files must contain the matching IDs and URLs. An operator should export the **original** provider response bodies; self-written substitutes are not independent provenance. Saved files and their SHA-256 values establish a bounded consistency certificate, not a provider-signed attestation.

## Manual offline command

Install the image decoder: \`python -m pip install Pillow\`.

\`\`\`bash
python RavenCloudTaskbar/verify_image_queue_live_readback_0001.py --evidence-dir RavenCloudTaskbar/image_queue_live_evidence_0003 --write-certificate image_queue_readback_certificate.json
python RavenCloudTaskbar/test_image_queue_live_readback_0001.py
\`\`\`

Verification exit codes: 0 only when all ten output bytes and provider-response references reconcile; 2 for HOLD or REJECT. A real T.20 bounded result still does **not** promote artistic quality. Never retry generation or dispatch automatically.

## Current observation and anti-loop

On 2026-10-22 Adobe inline readback of Q01 and Q02 existing final-output short URLs returned \`NotFound: The asset is not available\`. These two attempted readbacks establish only the sampled link's current unavailability. Do not infer the status of Q03..Q10. Adobe asset discovery showed a named FR0333 diagnostic asset, not a ten-file byte set matched to Q01..Q10. No new Adobe image generation, queue dispatch or GitHub Actions workflow rerun occurred in this audit.

Source integrity and PR #70 historical closure remain bounded and intact. Do not alter entry 0.8 or rewrite receipt 0003 to assert delivery. Revise this passive HOLD only upon newly recovered evidence, not elapsed time or a repeated failed lookup.
