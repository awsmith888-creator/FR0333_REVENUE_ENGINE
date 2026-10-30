# FR-0333 bounded agent runtime 0.14 candidate

This is an independent FR-0333 controller prototype, not a copy of Meta Muse. It uses the openly released Muse Glimmer weights only when a local inference service is configured. It does not use Anthropic, install model weights, contact an inference provider, or call Adobe by default.

## Offline check

```bash
python3 fr0333_agent_runtime_0001.py --self-check
python3 -m unittest -v test_fr0333_agent_runtime_0001.py
```

The source has no third-party dependencies, shell execution, self-install path, dynamic imports, file deletion, or background process. The default model endpoint is loopback only. `--self-check` makes zero network calls.

## Model connection

Run a locally administered inference server for `meta-models/Muse-Glimmer-30B` and set `FR0333_LOCAL_MODEL_URL` to its loopback OpenAI-compatible API URL. This prototype does not download weights or start a model server. Model/API compatibility and model quality remain unverified until a pinned local deployment is exercised with receipts.

The model cannot choose arbitrary tools. Action names are fixed in code. Sensitive Adobe actions require a direct operator approval flag from the trusted host; model-generated text cannot set that flag.

## Adobe boundary

The Adobe tools available inside ChatGPT are not exported as reusable credentials or a runtime endpoint. This code can perform a read-only MCP initialize plus `tools/list` discovery only if an operator configures an Adobe-owned HTTPS MCP endpoint and a short-lived bearer token using `FR0333_ADOBE_MCP_URL` and `FR0333_ADOBE_BEARER_TOKEN`. `--discover-adobe` performs that live read-only handshake; it does not call a tool or write to Adobe. With no configuration it returns `U.21.HOLD.DISCONNECTED` and makes no network request.

No Adobe MCP endpoint or OAuth credential was provided in this change, so a live Adobe connection is **not claimed**. The next gate is to bind an authorized Adobe endpoint and token, run discovery, then test one non-destructive read operation. Image generation and board writes stay disabled until their exact schemas and approval receipts are verified.

## Probabilities

Probabilities are estimates over distinct receipt hashes for one named task class. The program emits no probability below ten receipt records. At ten or more it reports the observed proportion and a 95% Wilson interval. It validates that callers marked each outcome independently verified, but this prototype does not cryptographically authenticate that declaration. Model self-reported confidence, vendor benchmark numbers, and synthetic fixtures do not count as runtime success receipts.

## Evidence states

`T.20.PASS` means a local check passed. `U.21.HOLD` means required runtime evidence is absent. `F.6.REJECT` means a policy or validation gate rejected an input. These states do not assert that the software is bug-free or virus-free; review and independent security scanning remain separate evidence.
