# FR0333.AGENT.SCAN.EVIDENCE.0003
Version: 0.1.2
Date checked: 2026-10-07
Parent: FR0333.AGENT.SCAN.0001
Predecessor: FR0333.AGENT.SCAN.EVIDENCE.0002
State: U.21.DOCUMENTATION.OBSERVED.NO.INTEGRATION
Owner: FR-0333 / AW Smith

## FR0333.TAB.AGENT.01 — Meta
REFERENCE.ID: FR0333.TAB.AGENT.01.EVIDENCE.0001
PRODUCT: Meta Business Agent / Meta Business Agent Platform
CLAIM: Meta announced business customer-response agents on WhatsApp and Messenger, expansion to Instagram, human handoff, and enterprise integration capabilities. The announcement says starting access on Instagram is free, with future subscription options; this is not a guarantee of universal access.
SOURCE.URL: https://about.fb.com/news/2026/06/meta-business-agent
SOURCE.DATE: 2026-06-03
CHECKED.DATE: 2026-10-07
EVIDENCE.CLASS: VENDOR.ANNOUNCEMENT
ACCESS.STATUS: VENDOR.REPORTED.ROLLOUT; eligibility, terms, API and geography NOT.TESTED
PLATFORM.SUBREFERENCE: FACEBOOK.01 — Messenger-related vendor announcement; independent Facebook agent runtime NOT.TESTED
PLATFORM.SUBREFERENCE: INSTAGRAM.02 — Instagram expansion vendor-announced; activation and permissions NOT.TESTED
PLATFORM.SUBREFERENCE: WHATSAPP.03 — vendor-reported existing business use; NOT.INDEPENDENTLY.VERIFIED
TEST.RESULT: NOT.RUN
HUMANLOCK: HOLD
NEXT.ACTION: Verify public developer documentation, enrollment/permission gates, pricing and independent state continuity.

## FR0333.TAB.AGENT.02 — X.xAI
REFERENCE.ID: FR0333.TAB.AGENT.02.EVIDENCE.0001
PRODUCT: Grok xAI API Tools and Function Calling
CLAIM: xAI documents server-side built-in web/X search, code execution, and custom function calling, where developer executes requested custom functions and returns results.
SOURCE.URL: https://docs.x.ai/developers/tools/overview
SECONDARY.SOURCE.URL: https://docs.x.ai/developers/tools/function-calling
SOURCE.DATE: NOT.CONFIRMED
CHECKED.DATE: 2026-10-07
EVIDENCE.CLASS: OFFICIAL.API.DOCUMENTATION
ACCESS.STATUS: API.DOCUMENTED; key, pricing, rate limits, region and long-running orchestration NOT.TESTED
PLATFORM.SUBREFERENCE: X.01 — X Search is a documented tool, not proof of direct X account agent control
PLATFORM.SUBREFERENCE: GROK.02 — tool calling documented, no FR0333 runtime test
TEST.RESULT: NOT.RUN
HUMANLOCK: HOLD
NEXT.ACTION: Build a mocked tool-calling contract test before requesting credentials or live API calls.

## FR0333.TAB.AGENT.03 — Google
REFERENCE.ID: FR0333.TAB.AGENT.03.EVIDENCE.0001
PRODUCT: Vertex AI Agent Engine Sessions and Memory Bank
CLAIM: Official documentation describes creation/listing/retrieval of sessions, events and expiration settings, and a Memory Bank with memory generation and retrieval; it requires Google Cloud project permissions and setup.
SOURCE.URL: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/sessions/manage-sessions-api
SECONDARY.SOURCE.URL: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/memory-bank/set-up
SOURCE.DATE: NOT.CONFIRMED
CHECKED.DATE: 2026-10-07
EVIDENCE.CLASS: OFFICIAL.CLOUD.DOCUMENTATION
ACCESS.STATUS: API.DOCUMENTED; account, cost, regions, persistence across failures and performance NOT.TESTED
PLATFORM.SUBREFERENCE: GEMINI.01 — Agent platform documentation, not proof any consumer Gemini account can host a continuous agent
PLATFORM.SUBREFERENCE: CLOUD.02 — Cloud project, IAM and billing requirements must be assessed before integration
TEST.RESULT: NOT.RUN
HUMANLOCK: HOLD
NEXT.ACTION: Compare session/event semantics to FR0333 SQLite WAL receipts using an offline simulated adapter.

## Evidence and certification gates
BASELINE: FR0333.AGENT.SCAN.EVIDENCE.0002; four documented company lanes and three source-pending.
DELTA: Three additional official vendor source records; seven of seven company lanes now have at least one official vendor documentation or announcement record. No vendor runtime testing.
PROVENANCE: URLs and evidence class bound to each TAB. Vendor documentation is not independent confirmation of advertised performance.
GOVERNMENT.RELATIONSHIPS: SEPARATE.TRACK.NOT.RESEARCHED; do not infer technical capabilities from political meetings.
RECEIPT: GitHub commit and subsequent read-back of this file are the durable research-write receipt; no external API test receipt exists.
CERTIFICATION: U.21.DOCUMENTATION.ONLY
HUMANLOCK: ACTIVE
Z.BOARD: UNCHANGED
DEPLOYMENT: NONE
PURCHASES: NONE

## Append-only history
- 2026-10-07 v0.1.2: Official-source findings for Meta, X.xAI, and Google; retained separate Facebook and Instagram references; no claims of runtime certification.
