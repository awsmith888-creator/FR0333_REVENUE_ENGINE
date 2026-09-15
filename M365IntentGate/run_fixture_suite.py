from __future__ import annotations

import json
from pathlib import Path

from M365IntentGate.m365_intent_gate_metrics import classify_suite, compile_receipt, load_fixtures


ROOT = Path(__file__).parent
RUN_ID = "00000000-0000-4000-8000-000000000001"
OBSERVED_AT = "2026-09-11T09:00:00Z"


def main() -> None:
    fixtures = load_fixtures(ROOT / "fixtures.json")
    outputs = classify_suite(fixtures)
    receipt = compile_receipt(fixtures, outputs, RUN_ID, OBSERVED_AT)
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
