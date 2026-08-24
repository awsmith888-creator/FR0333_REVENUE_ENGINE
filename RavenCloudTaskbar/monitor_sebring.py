#!/usr/bin/env python3
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

CASES = ["26-005016", "26-006056", "26-007064", "26-007079"]
SOURCES = {
    "sebring_police_log": "https://www.westernreservenews.com/cancellations/SEBRINGPOLICEREPORTS.htm",
    "mahoning_court_3": "https://www.mahoningcountyoh.gov/245/Court-3---Sebring",
    "mahoning_court_services": "https://www.mahoningcountyoh.gov/590/Court-Services",
}
UA = "FR0333-Raven-PublicRecordMonitor/1.0 (+metadata-only; public sources)"


def fetch(url: str) -> dict:
    req = Request(url, headers={"User-Agent": UA})
    try:
        with urlopen(req, timeout=30) as r:
            body = r.read()
            text = body.decode("utf-8", errors="replace")
            return {
                "ok": True,
                "status": getattr(r, "status", 200),
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "text": text,
                "error": None,
            }
    except Exception as exc:
        return {
            "ok": False,
            "status": None,
            "bytes": 0,
            "sha256": None,
            "text": "",
            "error": f"{type(exc).__name__}: {exc}",
        }


def load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default=".raven-cache/sebring_state.json")
    ap.add_argument("--output", default="RavenCloudTaskbar/dist/sebring_monitor.json")
    args = ap.parse_args()

    state_path = Path(args.state)
    out_path = Path(args.output)
    previous = load_state(state_path)

    now_utc = datetime.now(timezone.utc)
    now_et = now_utc.astimezone(ZoneInfo("America/New_York"))

    source_results = {}
    raw_text = {}
    for name, url in SOURCES.items():
        r = fetch(url)
        raw_text[name] = r.pop("text")
        source_results[name] = {"url": url, **r}

    police_text = raw_text.get("sebring_police_log", "")
    case_presence = {case: (case in police_text) for case in CASES}

    current_state = {
        "source_sha256": {k: v["sha256"] for k, v in source_results.items()},
        "case_presence": case_presence,
    }

    changes = []
    prev_hashes = previous.get("source_sha256", {})
    prev_cases = previous.get("case_presence", {})
    if previous:
        for name, value in current_state["source_sha256"].items():
            if prev_hashes.get(name) != value:
                changes.append({"type": "SOURCE_HASH_CHANGED", "source": name})
        for case, present in case_presence.items():
            if prev_cases.get(case) != present:
                changes.append({
                    "type": "CASE_PRESENCE_CHANGED",
                    "case": case,
                    "from": prev_cases.get(case),
                    "to": present,
                })

    report = {
        "system": "FR0333_RAVEN_PUBLIC_RECORD_MONITOR",
        "taskbar_id": "TB.SEBRING.CASE.MONITORING",
        "observed_at_utc": now_utc.isoformat(),
        "observed_at_et": now_et.isoformat(),
        "evidence_gate": "OBSERVED != CORRELATED != CAUSAL",
        "scope": "PUBLIC_RECORD_METADATA_ONLY",
        "case_numbers": CASES,
        "sources": source_results,
        "case_presence_in_sebring_police_log": case_presence,
        "first_run": not bool(previous),
        "changed_since_prior_run": bool(changes),
        "changes": changes,
        "interpretation": "NONE_AUTOMATIC",
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(current_state, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "observed_at_et": report["observed_at_et"],
        "first_run": report["first_run"],
        "changed": report["changed_since_prior_run"],
        "changes": report["changes"],
        "case_presence": case_presence,
        "source_ok": {k: v["ok"] for k, v in source_results.items()},
    }, indent=2))


if __name__ == "__main__":
    main()
