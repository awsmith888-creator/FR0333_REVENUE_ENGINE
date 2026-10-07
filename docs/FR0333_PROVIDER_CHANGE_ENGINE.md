# FR0333 Provider Change Engine Lane

**Record:** `FR0333.PROVIDER.CHANGE.ENGINE.0001`  
**State:** `IMPLEMENTED_LOCALLY / SOURCE_DISCOVERY_NOT_IMPLEMENTED / HUMAN_REVIEW_REQUIRED`  
**Scope:** deterministic intake for official provider product, pricing, plan, access, and packaging observations.

## Route

`SOURCE_OBSERVATION -> SURFACE_IDENTITY -> FACTS_AND_INTERPRETATION -> BENCHMARK_LANE -> HOLD_OR_REVIEW`

The API endpoint `/provider-change/evaluate` accepts one candidate observation and returns a structured review receipt. It requires an official primary-source classification, source URL, dated documented facts, a separately labeled interpretation, a mapped benchmark lane and affected assumption, and explicit product/surface/transport/model/account/personalization/session fields.

The engine does **not** crawl OpenAI, Anthropic, Google, or xAI pages and does not independently authenticate the submitted source classification. A passing input is `MATERIAL_CANDIDATE_REVIEW`, not a verified change or a benchmark result. Source verification and promotion remain separate human-reviewed steps. Historical baselines are never mutated by this intake route.

## Evidence boundary

- `SOURCE_CLASS_ASSERTED != SOURCE_INDEPENDENTLY_VERIFIED`
- `DOCUMENTED_FACTS != INTERPRETATION`
- `API_SURFACE != CONSUMER_SURFACE`
- `ANNOUNCED != GENERALLY_AVAILABLE`
- `MATERIAL_CANDIDATE_REVIEW != PROMOTION`
- `OBSERVED != CORRELATED != CAUSAL`

If no distinct Workbench-specific cross-provider map is supplied, the intake may use the FR-0333 Vector Production Spine's documented surface identity fields. It must HOLD when the affected benchmark lane or assumption is missing; it must not invent either.

## Change history

- `2026-10-07` — Initial engine intake gate and API route; source discovery intentionally remains outside this component.
