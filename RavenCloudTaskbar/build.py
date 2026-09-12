#!/usr/bin/env python3
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
TASKBARS = ROOT / "taskbars.json"
LUMEN = ROOT / "lumen_gateway.json"
IMAGE_QUALITY = ROOT / "fr0333_image_quality_gate_0003.json"
ADOBE_RECEIPT = ROOT / "fr0333_adobe_image_runtime_receipt_0001.json"

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
    image_quality = json.loads(IMAGE_QUALITY.read_text(encoding="utf-8"))
    adobe_receipt = json.loads(ADOBE_RECEIPT.read_text(encoding="utf-8"))

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

    assert image_quality["identifier"] == "FR0333.IMAGE.QUALITY.GATE.0003"
    assert image_quality["humanlock"] is True
    assert image_quality["reference_scale"]["percent_symbols_prohibited"] is True
    assert image_quality["reference_scale"]["minimum_promotable_reference"] == 8

    queue = image_quality["queue_contract"]
    assert queue["n_in_equals_n_out"] is True
    assert queue["one_run_one_canvas_one_image"] is True
    assert queue["independent_9_16_canvas_per_slot"] is True
    assert queue["collage"] == "REJECT"
    assert queue["duplicate_output"] == "REJECT"
    assert queue["count_mismatch"] == "REJECT"

    mode = image_quality["mode_gate"]
    assert mode["edit_ne_regenerate"] is True
    assert mode["remaster_ne_reinvent"] is True

    dimensions = image_quality["photorealism_dimensions"]
    assert len(dimensions) == 14
    assert "VEHICLE.MECHANICAL.GEOMETRY" in dimensions
    assert "LOAD.BALANCE.CONTACT.PHYSICS" in dimensions
    assert "VISUAL.READBACK" in dimensions

    defaults = image_quality["adobe_execution_defaults"]
    assert defaults["generation_prompt_reasoner"] == "quality"
    assert defaults["edit_prompt_reasoner"] == "quality"
    assert defaults["target_resolution_level"] == "4MP"
    assert defaults["output_format"] == "png"
    assert defaults["post_edit_visual_readback"] == "REQUIRED"

    promo = image_quality["promotion_gate"]
    for field in (
        "identity_reference_min", "anatomy_reference_min",
        "vehicle_geometry_reference_min", "physics_reference_min",
        "camera_geometry_reference_min", "lighting_reference_min",
        "material_realism_reference_min", "crop_reference_min",
        "artifact_control_reference_min", "aesthetic_reference_min",
        "user_intent_reference_min"
    ):
        assert promo[field] >= 8, f"quality threshold too low: {field}={promo[field]}"
    assert promo["visual_readback_required"] is True
    assert promo["user_reject_overrides_promotion"] is True
    assert promo["runtime_receipt_required_for_external_execution_claim"] is True
    assert "USER.REJECT = OUTPUT.HOLD" in image_quality["hard_boundaries"]
    assert "TONE.IMPROVEMENT != STRUCTURAL.REALISM.REPAIR" in image_quality["hard_boundaries"]

    assert adobe_receipt["provider"] == "ADOBE"
    assert adobe_receipt["provider_receipt"]["execution_state"] == "PASS_RUNTIME"
    assert adobe_receipt["readback"]["quality_promotion_state"] == "U.21.HOLD"
    assert adobe_receipt["readback"]["user_acceptance"] == "NOT_OBSERVED"
    assert adobe_receipt["result"]["connector_runtime"] == "T.20.PASS"
    assert adobe_receipt["result"]["external_adobe_full_capacity"] == "NOT_ESTABLISHED"

    return taskbars, lumen, image_quality, adobe_receipt


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
    taskbars, lumen, image_quality, adobe_receipt = load_and_validate()
    DIST.mkdir(exist_ok=True)
    (DIST / "index.html").write_text(build_html(taskbars, lumen), encoding="utf-8")
    (DIST / "taskbars.json").write_text(json.dumps(taskbars, indent=2) + "\n", encoding="utf-8")
    (DIST / "lumen_gateway.json").write_text(json.dumps(lumen, indent=2) + "\n", encoding="utf-8")
    (DIST / "fr0333_image_quality_gate_0003.json").write_text(json.dumps(image_quality, indent=2) + "\n", encoding="utf-8")
    (DIST / "fr0333_adobe_image_runtime_receipt_0001.json").write_text(json.dumps(adobe_receipt, indent=2) + "\n", encoding="utf-8")
    files = [
        DIST / "index.html",
        DIST / "taskbars.json",
        DIST / "lumen_gateway.json",
        DIST / "fr0333_image_quality_gate_0003.json",
        DIST / "fr0333_adobe_image_runtime_receipt_0001.json"
    ]
    sums = "\n".join(f"{sha256(p)}  {p.name}" for p in files) + "\n"
    (DIST / "SHA256SUMS").write_text(sums, encoding="utf-8")
    print(
        f"PASS taskbars={len(taskbars['taskbars'])} "
        f"lumen={lumen['provisioning_state']} "
        f"image_quality_min={image_quality['reference_scale']['minimum_promotable_reference']} "
        f"adobe_connector={adobe_receipt['result']['connector_runtime']} "
        f"quality_promotion={adobe_receipt['result']['photorealism_promotion']}"
    )
    print(sums, end="")


if __name__ == "__main__":
    main()
