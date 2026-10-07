#!/usr/bin/env python3
"""Hourly official-page change screen for the existing TB.SONAR engine lane.

This screen detects changes to allowlisted provider pages. It does not turn a
page edit into a verified product, pricing, availability, or benchmark claim.
"""

import difflib
import hashlib
import html
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STATE_PATH = Path(".raven-cache/provider-change/provider-pages.json")
RECEIPT_PATH = ROOT / "dist/provider_change_monitor.json"
CONFIG_PATH = ROOT / "fr0333_provider_change_watch_0001.json"
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
SOURCES = CONFIG["sources"]

MATERIAL_TERMS = re.compile(
    r"\b(launch|launched|introducing|available|availability|rollout|preview|"
    r"general availability|pricing|price|per million|token|subscription|plan|"
    r"enterprise|model|API|access|rate limit|context window)\b|[$€£]",
    re.IGNORECASE,
)


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "svg", "noscript"}:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "svg", "noscript"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden:
            text = " ".join(data.split())
            if text:
                self.parts.append(text)


def extract_text(markup):
    parser = TextExtractor()
    parser.feed(markup)
    return " ".join(parser.parts)


def classify_lane(source, added_text):
    if source["lane_hint"] == "COST":
        return "COST", "Published API pricing may have changed; exact model, token units, and effective date require source review."
    lowered = added_text.lower()
    if any(term in lowered for term in ("pricing", "price", "per million", "token", "$", "€", "£")):
        return "COST", "A pricing-related source passage changed; exact price and scope require source review."
    if any(term in lowered for term in ("launch", "launched", "introducing", "new model", "model release", "model")):
        return "MODEL_CAPABILITY", "A product or model announcement passage changed; exact model and benchmark effect require source review."
    if any(term in lowered for term in ("available", "availability", "access", "rollout", "preview", "general availability")):
        return "ACCESS", "A source passage about access or availability changed; eligibility and release state require source review."
    if any(term in lowered for term in ("plan", "subscription", "enterprise", "package", "tier")):
        return "PACKAGING", "A source passage about plans or packaging changed; included features and limits require source review."
    if "api" in lowered:
        return "MODEL_CAPABILITY", "A product or model announcement passage changed; exact model and benchmark effect require source review."
    return "UNRESOLVED", "The page changed, but no benchmark lane can be assigned from the changed text."


def observe_source(source, fetcher=None):
    fetcher = fetcher or fetch_page
    body = fetcher(source["url"])
    text = extract_text(body)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {"source_id": source["id"], "text": text, "sha256": digest}


def diff_candidate(source, previous_text, current_text):
    old = set(re.findall(r"[^.!?\n]+[.!?]?", previous_text))
    new = [line.strip() for line in re.findall(r"[^.!?\n]+[.!?]?", current_text) if line.strip() and line.strip() not in old]
    added = " ".join(new)
    if not added or not MATERIAL_TERMS.search(added):
        return None
    lane, assumption = classify_lane(source, added)
    return {
        "source_id": source["id"],
        "provider": source["provider"],
        "product": source["product"],
        "source_url": source["url"],
        "source_class": "PRIMARY_OFFICIAL_PAGE_ALLOWLISTED",
        "source_observation": "OFFICIAL_PAGE_TEXT_CHANGED",
        "added_text_excerpt": added[:1200],
        "benchmark_lane_candidate": lane,
        "benchmark_assumption_candidate": assumption,
        "interpretation": "Screening signal only. This page diff does not establish a product launch, a price change, general availability, or a benchmark result.",
        "surface_identity": {
            "provider": source["provider"],
            "product": source["product"],
            "surface": "PROVIDER_NEWS_OR_PRICING_PAGE",
            "transport": "PUBLIC_WEB_PAGE",
            "model_reported": "REQUIRES_SOURCE_REVIEW",
            "account_context": "PUBLIC_PAGE",
            "personalization_state": "NOT_APPLICABLE_OR_UNKNOWN",
            "session_context": "SINGLE_PAGE_FETCH",
        },
        "workbench_map_state": "UNRESOLVED_DISTINCT_WORKBENCH_MAP_NOT_LOCATED",
        "status": "SOURCE_CHANGE_CANDIDATE_REVIEW_REQUIRED" if lane != "UNRESOLVED" else "HOLD",
    }


def run_monitor(fetcher=None, state_path=STATE_PATH, receipt_path=RECEIPT_PATH):
    state_path = Path(state_path)
    receipt_path = Path(receipt_path)
    previous = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    next_state = {}
    candidates, unresolved = [], []
    first_run = not bool(previous)

    for source in SOURCES:
        try:
            observed = observe_source(source, fetcher)
        except Exception as exc:  # network errors are isolated to their source
            unresolved.append({"source_id": source["id"], "source_url": source["url"], "state": "UNRESOLVED_SOURCE_ACCESS", "error_type": type(exc).__name__})
            if source["id"] in previous:
                next_state[source["id"]] = previous[source["id"]]
            continue
        old = previous.get(source["id"])
        if old and old.get("sha256") != observed["sha256"]:
            candidate = diff_candidate(source, old.get("text", ""), observed["text"])
            if candidate:
                candidate["prior_sha256"] = old["sha256"]
                candidate["current_sha256"] = observed["sha256"]
                candidates.append(candidate)
        next_state[source["id"]] = observed

    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(next_state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt = {
        "identifier": "FR0333.PROVIDER.CHANGE.SOURCE.SCREEN.0001",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "taskbar_binding": CONFIG["taskbar_binding"],
        "workbench_map_state": CONFIG["workbench_map_state"],
        "run_state": "BASELINE_INITIALIZED" if first_run else ("SOURCE_CHANGE_CANDIDATES" if candidates else "STAY"),
        "source_count": len(SOURCES),
        "sources_observed": len(next_state),
        "candidates": candidates,
        "unresolved_sources": unresolved,
        "evidence_boundary": "PAGE_CHANGE != VERIFIED_PRODUCT_CHANGE; OBSERVED != CORRELATED != CAUSAL",
        "notification_boundary": "WORKFLOW_SUMMARY_AND_ARTIFACT_ONLY",
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def fetch_page(url):
    request = urllib.request.Request(url, headers={"User-Agent": "FR0333-SONAR/1.0 (+https://github.com/awsmith888-creator/FR0333_REVENUE_ENGINE)"})
    with urllib.request.urlopen(request, timeout=25) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP_{response.status}")
        return response.read().decode("utf-8", errors="replace")


def main():
    receipt = run_monitor()
    print(json.dumps(receipt, indent=2))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        lines = ["## FR0333 Provider Source Screen", "", f"**Run state:** `{receipt['run_state']}`", f"**Pages observed:** {receipt['sources_observed']} / {receipt['source_count']}", "", "Page changes are screening signals. They do not establish product facts or benchmark outcomes.", ""]
        for item in receipt["candidates"]:
            lines += [f"### {item['provider']} — {item['source_id']}", f"- Source: {item['source_url']}", f"- Candidate lane: `{item['benchmark_lane_candidate']}`", f"- Candidate assumption: {item['benchmark_assumption_candidate']}", f"- Interpretation: {item['interpretation']}", f"- Changed text: {item['added_text_excerpt']}", ""]
        for item in receipt["unresolved_sources"]:
            lines.append(f"- **Unresolved source access:** {item['source_id']} ({item['error_type']})")
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write("\n".join(lines) + "\n")
    if receipt["candidates"]:
        print("::warning::Provider source pages changed; review the FR0333 provider-change artifact.")


if __name__ == "__main__":
    main()
