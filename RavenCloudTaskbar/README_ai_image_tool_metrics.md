# FR0333 AI Image Tool Metrics

`FR0333.AI.IMAGE.TOOL.METRICS.0001` is bound to Golden Chain position `GC.SB.0027`.

It is a manual, runnable metrics rail. It does not create a scheduled task, monitor, external connection, or autonomous promotion path.

## Metric axes

- Identity preservation
- Remastering
- Native 9:16 output
- Batch and split workflows
- Runtime reliability

Each change receives a consequence rank from `0` through `3`. Evidence weights are `3` for a verified release, `2` for a preview, `1` for a vendor claim, and `0` for unverified material. The deterministic metric is evidence weight multiplied by consequence, producing `0` through `9`. It is not a percentage. Metrics are totaled only inside their evidence lane; no combined total may mix verified releases with previews or claims.

## Evidence gate

`VERIFIED_RELEASE != PREVIEW != VENDOR_CLAIM`

`OBSERVED != CORRELATED != CAUSAL`

A verified release requires an availability receipt. Release availability does not establish runtime verification. Runtime reliability requires its own runtime receipt before it may enter the verified-release lane. Records remain separated by evidence lane in every compiled report.

## Run

```bash
python3 -m unittest RavenCloudTaskbar.test_ai_image_tool_metrics -v
```

## Inventory

Machine-readable registration is stored in `ai_image_tool_metrics_inventory.json`. The Raven taskbar carries the corresponding control-plane inventory record.
