#!/usr/bin/env python3
"""Bounded local evidence-package validation. No network, scheduling or theology scoring."""
import copy, hashlib, json, sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
INDEX = ROOT.parent / "fr0333_golden_chain_index_0001.json"
def read(p): return json.loads(p.read_text())
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def conditions(m, sources, baseline, index, study):
    return {
        "prior_entries_preserved": index["entries"][:-1] == baseline["entries"],
        "prior_public_index_preserved": index["public_index"][:-1] == baseline["public_index"],
        "prior_rules_preserved": index["rules"] == baseline["rules"],
        "new_entry_resolves": index["entries"][-1]["index"] == "0.9" and index["entries"][-1]["artifact"].endswith("/METRICS.json") and index["entries"][-1]["identifier"] == m["identifier"],
        "unique_source_identifiers": len({s["id"] for s in sources}) == len(sources),
        "gate_sources_resolve": all(s in {r["id"] for r in sources} for g in m["gates"] for s in g["basis"]),
        "collation_holds_preserved": all(next(g for g in m["gates"] if g["id"] == x)["state"] == "HOLD" for x in ["G.4","G.5"]),
        "no_fabricated_geez_or_andemta": m["study"]["geez_text"] is None and m["study"]["andemta_quote"] is None,
        "no_unnamed_base_translation": m["study"]["english_base_translation"] is None,
        "one_unanswered_question": study.count("?") == 1 and "AWAITING USER" in study,
        "on_demand_only": m["mode"] == "ON_DEMAND" and m["schedule_created"] is False,
        "count_units_preserved": all("unit" in r for r in m["observations"]) and m["observations"][0]["value"] + m["observations"][1]["value"] == m["observations"][2]["value"]
    }
m = read(ROOT/"METRICS.json")
sources = read(ROOT/"SOURCES.json")
baseline = read(ROOT/"BASELINE_INDEX.json")
index = read(INDEX)
study = (ROOT/"STUDY.0001.md").read_text()
checks = conditions(m,sources,baseline,index,study)
if not all(checks.values()):
    print(json.dumps({"status":"FAIL","checks":checks},indent=2)); sys.exit(1)
# Mutation controls test failure boundaries, not textual or theological truth.
mutation_checks = {}
changed = copy.deepcopy(index); changed["entries"][0]["state"] = "MUTATED"
mutation_checks["reject_prior_entry_mutation"] = not all(conditions(m,sources,baseline,changed,study).values())
changed = copy.deepcopy(m); changed["gates"][3]["state"] = "PASS"
mutation_checks["reject_geez_hold_promotion"] = not all(conditions(changed,sources,baseline,index,study).values())
changed = copy.deepcopy(m); changed["gates"][0]["basis"] = ["MISSING"]
mutation_checks["reject_unresolved_source"] = not all(conditions(changed,sources,baseline,index,study).values())
mutation_checks["reject_missing_question"] = not all(conditions(m,sources,baseline,index,study.replace("?","")).values())
changed = copy.deepcopy(m); changed["study"]["andemta_quote"] = "invented"
mutation_checks["reject_fabricated_andemta"] = not all(conditions(changed,sources,baseline,index,study).values())
if not all(mutation_checks.values()): raise RuntimeError("Mutation guard failed")
if "--issue" in sys.argv:
    stamp = datetime.now(ZoneInfo("America/New_York")).isoformat()
    payloads = [p for p in ROOT.iterdir() if p.is_file() and p.name not in {"CERTIFICATE.json","RECEIPT.json","SHA256SUMS.json"}] + [INDEX]
    bindings = {str(p.relative_to(ROOT.parent)):digest(p) for p in sorted(payloads)}
    receipt = {"id":"RECEIPT.FR0333.ETHIOPIAN.ORTHODOX.STUDY.0001","timestamp":stamp,
        "action":"LOCAL_DOCUMENTATION_VALIDATION","checks":checks,"mutation_checks":mutation_checks,
        "passed":sum(checks.values())+sum(mutation_checks.values()),"failed":0,
        "research_access_date":"2026-10-22","source_access_details":"SOURCES.json",
        "source_snapshot_policy":"Summaries and locators only; original webpage/PDF bytes not archived",
        "base_commit":"417f4094e1df8fe3c332177d2ac3698af62317c7",
        "remote_commit_status":"NOT_ESTABLISHED_BY_THIS_LOCAL_RECEIPT",
        "boundary":"LOCAL_CHECKS_NE_CI_NE_CHURCH_ENDORSEMENT_NE_TEXTUAL_COLLATION"}
    (ROOT/"RECEIPT.json").write_text(json.dumps(receipt,indent=2)+"\n")
    cert = {"id":"CERT.FR0333.ETHIOPIAN.ORTHODOX.STUDY.0001","issued_at":stamp,
        "issuer":"Assistant-generated internal self-issued record",
        "scope":"Local artifact structure, preserved prior index entries, traceability fields and stated holds",
        "result":"PASS_WITH_EXPLICIT_HOLDS","bindings_sha256":bindings,
        "receipt_sha256":digest(ROOT/"RECEIPT.json"),
        "exclusions":["Church endorsement","Independent theological verification","Exact Ge'ez or Andemta collation","Original source-byte archiving","Mainline promotion","External runtime or CI pass"],
        "humanlock":"REQUIRED_FOR_MAINLINE_PROMOTION"}
    (ROOT/"CERTIFICATE.json").write_text(json.dumps(cert,indent=2)+"\n")
    allfiles = [p for p in ROOT.iterdir() if p.is_file() and p.name != "SHA256SUMS.json"]+[INDEX]
    (ROOT/"SHA256SUMS.json").write_text(json.dumps({str(p.relative_to(ROOT.parent)):digest(p) for p in sorted(allfiles)},indent=2)+"\n")
cert = read(ROOT/"CERTIFICATE.json")
manifest = read(ROOT/"SHA256SUMS.json")
for name,h in manifest.items():
    if digest(ROOT.parent/name) != h: raise RuntimeError("File hash mismatch: "+name)
for name,h in cert["bindings_sha256"].items():
    if digest(ROOT.parent/name) != h: raise RuntimeError("Certificate hash mismatch: "+name)
if digest(ROOT/"RECEIPT.json") != cert["receipt_sha256"]: raise RuntimeError("Receipt hash mismatch")
print(json.dumps({"status":"PASS","structural_checks":len(checks),"mutation_controls":len(mutation_checks),"manifest_bindings":len(manifest),"certificate":"SELF_ISSUED_BOUNDED","geez_and_andemta":"HOLD"}))

