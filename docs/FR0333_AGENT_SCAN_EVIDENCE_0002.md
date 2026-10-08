# FR0333.AGENT.SCAN.EVIDENCE.0002
Version: 0.1.1
Date checked: 2026-10-07
Parent: FR0333.AGENT.SCAN.0001
State: U.21.DOCUMENTATION.OBSERVED.NO.INTEGRATION
Scope: official documentation review, not independent vendor runtime testing.

## Source-bound TAB findings
### FR0333.TAB.AGENT.01 Meta
State: U.21.SOURCE.PENDING. Official developer evidence for Facebook/Instagram agent persistence, authorization and API access has not yet been recorded. Do not promote prior conversational claims.

### FR0333.TAB.AGENT.02 X.xAI
State: U.21.SOURCE.PENDING. Official current API evidence and limits have not yet been recorded. Do not promote prior conversational claims.

### FR0333.TAB.AGENT.03 Google
State: U.21.SOURCE.PENDING. Official current persistent-agent evidence and limits have not yet been recorded. Do not promote prior conversational claims.

### FR0333.TAB.AGENT.04 Microsoft
REFERENCE.ID: FR0333.TAB.AGENT.04.EVIDENCE.0001
PRODUCT: Copilot Studio autonomous agents
CLAIM: Event triggers can initiate agent actions without a user prompt; scoped permissions and audit logs are recommended.
SOURCE.URL: https://learn.microsoft.com/microsoft-copilot-studio/guidance/autonomous-agents
SOURCE.DATE: 2026-06-11 (page last updated)
CHECKED.DATE: 2026-10-07
EVIDENCE.CLASS: VENDOR.DOCUMENTATION
ACCESS.STATUS: DOCUMENTED; account, licensing, and authorization not tested
TEST.RESULT: NOT.RUN
HUMANLOCK: HOLD
NEXT.ACTION: Validate quotas, state recovery, costs and audit export in a bounded sandbox.

### FR0333.TAB.AGENT.05 Amazon
REFERENCE.ID: FR0333.TAB.AGENT.05.EVIDENCE.0001
PRODUCT: Amazon Bedrock AgentCore Runtime
CLAIM: Managed agent hosting with isolated sessions; documentation describes MCP/A2A and multi-day instances.
SOURCE.URL: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html
SOURCE.DATE: NOT.CONFIRMED
CHECKED.DATE: 2026-10-07
EVIDENCE.CLASS: VENDOR.DOCUMENTATION
ACCESS.STATUS: DOCUMENTED; account, price, quotas and region not tested
TEST.RESULT: NOT.RUN
HUMANLOCK: HOLD
NEXT.ACTION: Compare session persistence and shutdown receipts against FR0333 baseline without deployment.

### FR0333.TAB.AGENT.06 Salesforce
REFERENCE.ID: FR0333.TAB.AGENT.06.EVIDENCE.0001
PRODUCT: Agentforce Agent API
CLAIM: REST API starts sessions, sends/receives messages, and ends sessions; requires an activated agent and external client app.
SOURCE.URL: https://developer.salesforce.com/docs/ai/agentforce/guide/agent-api-get-started.html
SOURCE.DATE: NOT.CONFIRMED
CHECKED.DATE: 2026-10-07
EVIDENCE.CLASS: VENDOR.DOCUMENTATION
ACCESS.STATUS: DOCUMENTED; account authorization and cost not tested
TEST.RESULT: NOT.RUN
HUMANLOCK: HOLD
NEXT.ACTION: Verify license, scopes, availability and session state before any integration.

### FR0333.TAB.AGENT.07 OpenAI
REFERENCE.ID: FR0333.TAB.AGENT.07.EVIDENCE.0001
PRODUCT: OpenAI Agents SDK
CLAIM: SDK documents tools, handoffs, guardrails, tracing, sessions, human-in-loop, and sandbox workspaces.
SOURCE.URL: https://openai.github.io/openai-agents-python/
SOURCE.DATE: NOT.CONFIRMED
CHECKED.DATE: 2026-10-07
EVIDENCE.CLASS: OFFICIAL.SDK.DOCUMENTATION
ACCESS.STATUS: DOCUMENTED; API key and agent execution not tested
TEST.RESULT: NOT.RUN
HUMANLOCK: HOLD
NEXT.ACTION: Design no-cost local mocked test of PIN/TAB retrieval and receipts.

## Certification and receipt
RESEARCH.RECEIPT: Official vendor documentation for four of seven company lanes examined and source URLs recorded. Three lanes remain SOURCE.PENDING.
OBSERVED: Documented product capabilities.
NOT.OBSERVED: Live vendor agent runs, uptime, external integration, FR0333 interoperability, cost, political/government ties.
BASELINE: FR0333.AGENT.SCAN.0001 v0.1.0, all lanes U.21.
DELTA: Four source-backed vendor documentation entries added; zero external integrations.
CERTIFICATION: U.21.DOCUMENTATION.ONLY
HUMANLOCK: ACTIVE

## Append-only history
- 2026-10-07 v0.1.1: Added four official vendor documentation records, held three unverified lanes, retained deployment boundary.
