#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "RavenCloudTaskbar" / "dist"
TASKBARS = ROOT / "RavenCloudTaskbar" / "taskbars.json"
OUT = DIST / "fr0333_weekly_log.md"
RECEIPT = DIST / "fr0333_weekly_log_receipt.json"
ET = ZoneInfo("America/New_York")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> None:
    DIST.mkdir(parents=True, exist_ok=True)
    observed_at = datetime.now(timezone.utc).astimezone(ET)
    taskbar = json.loads(TASKBARS.read_text(encoding="utf-8"))

    raw = git(
        "log",
        "--since=7.days",
        "--date=iso-strict",
        "--pretty=format:%H%x09%ad%x09%s",
    )
    commits = []
    if raw:
        for line in raw.splitlines():
            sha, date, subject = line.split("\t", 2)
            commits.append({"sha": sha, "date": date, "subject": subject})

    changed_raw = git("log", "--since=7.days", "--name-only", "--pretty=format:")
    changed_files = sorted({p for p in changed_raw.splitlines() if p.strip()})

    active = []
    holds = []
    for item in taskbar.get("taskbars", []):
        row = {
            "id": item.get("id"),
            "project": item.get("project"),
            "state": item.get("state"),
            "evidence_state": item.get("evidence_state"),
            "execution_state": item.get("execution_state"),
            "next_action": item.get("next_action"),
        }
        if str(item.get("state", "")).upper() == "HOLD" or "HOLD" in str(item.get("execution_state", "")).upper():
            holds.append(row)
        else:
            active.append(row)

    lines = [
        "# FR-0333 Weekly Log",
        "",
        "**DRAFT — USER REVIEW REQUIRED**",
        "",
        f"Observed at (ET): {observed_at.isoformat()}",
        "",
        "## Verified repository progress",
    ]
    if commits:
        for c in commits:
            lines.append(f"- `{c['sha'][:12]}` — {c['subject']} ({c['date']})")
    else:
        lines.append("- No commits observed in the repository during the seven-day window.")

    lines += ["", "## Changed artifacts"]
    if changed_files:
        for path in changed_files:
            lines.append(f"- `{path}`")
    else:
        lines.append("- No changed repository files observed in the seven-day window.")

    lines += ["", "## Current Raven taskbar state"]
    for row in active:
        lines.append(
            f"- `{row['id']}` — state={row['state']}; evidence={row['evidence_state']}; "
            f"execution={row['execution_state']}; next={row['next_action']}"
        )

    lines += ["", "## Holds / unresolved evidence"]
    if holds:
        for row in holds:
            lines.append(
                f"- `{row['id']}` — state={row['state']}; evidence={row['evidence_state']}; "
                f"execution={row['execution_state']}; next={row['next_action']}"
            )
    else:
        lines.append("- No HOLD-state taskbar entries observed.")

    lines += [
        "",
        "## Evidence boundary",
        "- Repository commits and paths above are observed from Git history.",
        "- Taskbar states above are observed from `RavenCloudTaskbar/taskbars.json`.",
        "- No Google Drive, Gmail, paid API, or external-account state is inferred by this workflow.",
        "- Unverified completion is not promoted.",
        "",
        "**OBSERVED != CORRELATED != CAUSAL**",
        "",
        "**DRAFT — USER REVIEW REQUIRED**",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    receipt = {
        "system": "FR0333_RAVEN_WEEKLY_LOG",
        "observed_at_et": observed_at.isoformat(),
        "window": "7_days",
        "commit_count": len(commits),
        "changed_file_count": len(changed_files),
        "taskbar_active_count": len(active),
        "taskbar_hold_count": len(holds),
        "output": str(OUT.relative_to(ROOT)),
        "state": "DRAFT_USER_REVIEW_REQUIRED",
        "evidence_gate": "OBSERVED != CORRELATED != CAUSAL",
        "external_calls": 0,
        "paid_calls": 0,
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(OUT)
    print(RECEIPT)


if __name__ == "__main__":
    main()
