#!/usr/bin/env python3
"""Validate the PR #65 Green Dot documentation index and emit a run receipt.

This is a repository-content check only. It does not execute FR-0333 runtime
services, the proposed instruction/image regressions, or HumanLock promotion.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


VERSION = "1.0.0"
WRITE_ME = "certifications/FR0333.GREEN.DOT.VALIDATION.WRITE.ME.0001.md"
EXPECTED_DOCS = [
    "certifications/FR0333.GREEN.DOT.ALIAS.ROUTER.0001.md",
    "certifications/FR0333.GREEN.DOT.HOME.THUMBTACKS.METRICS.0001.md",
    "certifications/FR0333.GREEN.DOT.INTEGRATION.INDEX.0001.md",
    "certifications/FR0333.GREEN.DOT.PROBABILITY.0001.md",
    "certifications/FR0333.GREEN.DOT.TWO.LANES.0001.md",
    "certifications/FR0333.GREEN.DOT.WRITE.ME.0001.md",
    "certifications/FR0333.SPORTS.METRICS.SPINE.0001.md",
    "certifications/FR0333.SUNDAY.SPORTS.METRICS.0001.md",
    WRITE_ME,
]


def fail(message: str) -> None:
    raise ValueError(message)


def run(root: Path) -> dict:
    checks: list[dict[str, str]] = []
    manifest_path = root / WRITE_ME
    if not manifest_path.is_file():
        fail(f"missing index/write-me: {WRITE_ME}")
    manifest = manifest_path.read_text(encoding="utf-8")

    table_rows = re.findall(
        r"^\|\s*TAB\.(\d{2})\s*\|\s*[^|]+\|\s*`([^`]+)`\s*\|\s*$",
        manifest,
        flags=re.MULTILINE,
    )
    tab_numbers = [int(number) for number, _ in table_rows]
    tab_paths = [path for _, path in table_rows]
    if tab_numbers != list(range(1, len(tab_numbers) + 1)):
        fail("WRITE-ME tab index must be unique and contiguous from TAB.01")
    if tab_paths != EXPECTED_DOCS:
        fail("WRITE-ME tab paths do not match the ordered certification document set")
    checks.append({"id": "INDEX.TABS", "result": "PASS"})

    loaded: dict[str, str] = {}
    for relative in EXPECTED_DOCS:
        path = root / relative
        if not path.is_file():
            fail(f"indexed document is missing: {relative}")
        text = path.read_text(encoding="utf-8")
        if not text.strip() or not re.search(r"^#\s+\S", text, flags=re.MULTILINE):
            fail(f"document is empty or has no Markdown title: {relative}")
        loaded[relative] = text
    checks.append({"id": "INDEX.PATHS_AND_MARKDOWN", "result": "PASS"})

    for relative, text in loaded.items():
        declarations = re.findall(r"^TAB\.(\d{2})\b", text, flags=re.MULTILINE)
        if declarations:
            numbers = [int(number) for number in declarations]
            if numbers != list(range(1, len(numbers) + 1)):
                fail(f"TAB declarations are duplicated or non-contiguous: {relative}")
        for target in re.findall(r"`(certifications/[A-Za-z0-9._/-]+\.md)`", text):
            if not (root / target).is_file():
                fail(f"broken internal certification path in {relative}: {target}")
    checks.append({"id": "DOCUMENT.TABS_AND_INTERNAL_PATHS", "result": "PASS"})

    probability_path = "certifications/FR0333.GREEN.DOT.PROBABILITY.0001.md"
    probability = loaded[probability_path]
    required_pins = [f"PIN.{number:04d}" for number in range(1, 5)]
    if not all(re.search(rf"^##\s+{re.escape(pin)}\b", probability, flags=re.MULTILINE) for pin in required_pins):
        fail("probability extension must retain PIN.0001 through PIN.0004")
    checks.append({"id": "PROBABILITY.PINS.0001_0004", "result": "PASS"})

    for relative, text in loaded.items():
        upper = text.upper()
        if not any(state in upper for state in ("HOLD", "PENDING", "NOT EXECUTED", "NOT CERTIFIED")):
            fail(f"certification boundary state is not explicit: {relative}")
    checks.append({"id": "CERTIFICATION.BOUNDARY.PRESENT", "result": "PASS"})

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    receipt = {
        "receipt_id": "FR0333.GREEN.DOT.REPOSITORY.VALIDATION.RECEIPT.0001",
        "validator_version": VERSION,
        "scope": "repository_document_index_and_internal_references_only",
        "commit_sha": os.environ.get("GITHUB_SHA", "UNSET_LOCAL_TEST"),
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "checked_documents": EXPECTED_DOCS,
        "checks": checks,
        "result": "PASS",
        "runtime_execution": "NOT_TESTED",
        "instruction_regression": "NOT_TESTED",
        "image_regression": "NOT_TESTED",
        "humanlock_promotion": "NOT_AUTHORIZED",
        "created_at_utc": now,
    }
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--receipt", type=Path, default=Path("green_dot_repository_validation_receipt.json"))
    args = parser.parse_args()
    try:
        receipt = run(args.root.resolve())
    except (OSError, UnicodeError, ValueError) as error:
        print(f"VALIDATION=FAIL: {error}", file=sys.stderr)
        return 1
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
