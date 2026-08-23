#!/usr/bin/env python3
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
TASKBARS = ROOT / "taskbars.json"
LUMEN = ROOT / "lumen_gateway.json"

REQUIRED_TASKBAR_FIELDS = {
    "id", "project", "lane", "state", "evidence_state",
    "execution_state", "cloud_mode", "next_action"
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_and_validate():
    taskbars = json.loads(TASKBARS.read_text(encoding="utf-8"))
    lumen = json.loads(LUMEN.read_text(encoding="utf-8"))
    assert taskbars["humanlock"] is True
    assert taskbars["state"] == "CONTROL_PLANE_BUILT_NOT_CLOUD_PROVISIONED"
    assert taskbars["evidence_gate"] == "OBSERVED != CORRELATED != CAUSAL"
    ids = set()
    for item in taskbars["taskbars"]:
        missing = REQUIRED_TASKBAR_FIELDS - set(item)
        assert not missing, f"{item.get('id', '<unknown>')} missing {sorted(missing)}"
        assert item["id"] not in ids, f"duplicate taskbar id {item['id']}"
        ids.add(item["id"])
    assert lumen["provisioning_state"] == "NOT_PROVISIONED"
    assert lumen["credentials"] == "NOT_STORED"
    return taskbars, lumen


def card(item):
    def e(v): return html.escape(str(v))
    return f'''<article class="card">
      <div class="rail"><span>{e(item['lane'])}</span><strong>{e(item['state'])}</strong></div>
      <h2>{e(item['project'])}</h2>
      <p class="id">{e(item['id'])}</p>
      <dl>
        <dt>EVIDENCE</dt><dd>{e(item['evidence_state'])}</dd>
        <dt>EXECUTION</dt><dd>{e(item['execution_state'])}</dd>
        <dt>CLOUD</dt><dd>{e(item['cloud_mode'])}</dd>
        <dt>NEXT</dt><dd>{e(item['next_action'])}</dd>
      </dl>
    </article>'''


def build_html(taskbars, lumen):
    cards = "\n".join(card(x) for x in taskbars["taskbars"])
    bars = " → ".join(taskbars["three_bars"])
    caps = " · ".join(lumen["capabilities"][:4])
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Raven Cloud Taskbar</title>
<style>
:root{{--bg:#0b0d0d;--panel:#171a1a;--line:#b9c1c3;--text:#f3f5f5;--muted:#9ca5a7;--ok:#d8e0e2}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:15px/1.45 system-ui,sans-serif}}
main{{max-width:1180px;margin:auto;padding:28px 18px 60px}}header{{border:1px solid #343a3b;padding:22px;margin-bottom:18px}}
h1{{margin:0;font-size:clamp(28px,5vw,54px);letter-spacing:.04em}}.sub{{color:var(--muted);margin:6px 0 0}}
.status{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin:18px 0}}
.status div{{border:1px solid #343a3b;background:#101212;padding:12px}}.status b{{display:block;color:var(--line);font-size:12px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}}.card{{background:var(--panel);border:1px solid #343a3b;padding:16px}}
.rail{{display:flex;justify-content:space-between;border-bottom:1px solid #343a3b;padding-bottom:8px;color:var(--line);font-size:12px}}
h2{{font-size:20px;margin:14px 0 2px}}.id{{font-family:ui-monospace,monospace;color:var(--muted);font-size:12px;margin-top:0}}
dl{{display:grid;grid-template-columns:82px 1fr;gap:7px 10px;margin:14px 0 0}}dt{{font-size:11px;color:var(--muted)}}dd{{margin:0;font-size:13px}}
footer{{margin-top:20px;color:var(--muted);font-family:ui-monospace,monospace;font-size:12px}}
</style></head>
<body><main>
<header><h1>RAVEN CLOUD TASKBAR</h1><p class="sub">{html.escape(bars)} · HumanLock active</p></header>
<section class="status">
<div><b>CONTROL PLANE</b>{html.escape(taskbars['state'])}</div>
<div><b>ZERO-LINE BUS</b>{html.escape(taskbars['zero_line_bus'])}</div>
<div><b>EVIDENCE GATE</b>{html.escape(taskbars['evidence_gate'])}</div>
<div><b>LUMEN TRANSPORT</b>{html.escape(lumen['provisioning_state'])}</div>
</section>
<section class="status"><div><b>LUMEN VERIFIED CAPABILITY</b>{html.escape(caps)}</div><div><b>BOUNDARY</b>Taskbar = control plane · Lumen = transport · local-only stays local</div></section>
<section class="grid">{cards}</section>
<footer>FR0333_RAVEN_CLOUD_TASKBAR v{html.escape(taskbars['version'])} · generated {html.escape(taskbars['generated_at'])}</footer>
</main></body></html>'''


def main():
    taskbars, lumen = load_and_validate()
    DIST.mkdir(exist_ok=True)
    (DIST / "index.html").write_text(build_html(taskbars, lumen), encoding="utf-8")
    (DIST / "taskbars.json").write_text(json.dumps(taskbars, indent=2) + "\n", encoding="utf-8")
    (DIST / "lumen_gateway.json").write_text(json.dumps(lumen, indent=2) + "\n", encoding="utf-8")
    files = [DIST / "index.html", DIST / "taskbars.json", DIST / "lumen_gateway.json"]
    sums = "\n".join(f"{sha256(p)}  {p.name}" for p in files) + "\n"
    (DIST / "SHA256SUMS").write_text(sums, encoding="utf-8")
    print(f"PASS taskbars={len(taskbars['taskbars'])} lumen={lumen['provisioning_state']}")
    print(sums, end="")

if __name__ == "__main__":
    main()
