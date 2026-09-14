#!/usr/bin/env python3
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
TASKBARS = ROOT / "taskbars.json"
LUMEN = ROOT / "lumen_gateway.json"
IMAGE_QUALITY = ROOT / "fr0333_image_quality_gate_0004.json"
ADOBE_RECEIPT = ROOT / "fr0333_adobe_image_runtime_receipt_0001.json"
ADOBE_QUEUE_FAILURE = ROOT / "fr0333_adobe_image_queue_runtime_receipt_0002.json"
ADOBE_QUEUE_RUNTIME = ROOT / "fr0333_adobe_image_queue_runtime_receipt_0003.json"

REQUIRED_TASKBAR_FIELDS = {
    "id", "project", "lane", "state", "evidence_state",
    "execution_state", "cloud_mode", "next_action"
}

REQUIRED_STATUS = {
    "BUILD.VALIDATION": "T.20.PASS",
    "CONNECTOR.RUNTIME": "T.20.PASS.BOUNDED",
    "QUEUE.RUNTIME": "T.20.PASS.BOUNDED",
    "FR0333.ADOBE.IMAGE.TESTED.SURFACE": "T.20.PASS.BOUNDED",
    "QUALITY.PROMOTION": "U.21.HOLD",
    "UNIVERSAL.ADOBE.SURFACE": "U.21.HOLD",
    "OVERALL.SYSTEM.STATUS": "U.21.HOLD",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_and_validate():
    taskbars = load_json(TASKBARS)
    lumen = load_json(LUMEN)
    gate = load_json(IMAGE_QUALITY)
    connector = load_json(ADOBE_RECEIPT)
    historical_failure = load_json(ADOBE_QUEUE_FAILURE)
    runtime = load_json(ADOBE_QUEUE_RUNTIME)

    assert taskbars["humanlock"] is True
    assert taskbars.get("humanlock_state", "ACTIVE_IMMUTABLE") == "ACTIVE_IMMUTABLE"
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

    assert gate["identifier"] == "FR0333.IMAGE.QUALITY.GATE.0004"
    assert gate["humanlock"] is True
    assert gate["status_output_contract"] == REQUIRED_STATUS

    queue = gate["queue_contract"]
    assert queue["requested_count_must_equal_delivered_count"] is True
    assert queue["one_slot_one_canvas_one_image"] is True
    assert queue["independent_9_16_canvas_per_slot"] is True
    assert queue["exact_1080_1920_required"] is True
    assert queue["max_user_queue"] == 10
    assert queue["collage"] == "REJECT"
    assert queue["contact_sheet"] == "REJECT"
    assert queue["multi_panel"] == "REJECT"

    caps = gate["provider_batch_caps"]
    for operation in ("IMAGE_GENERATE", "IMAGE_INSTRUCT_EDIT"):
        cap = caps[operation]
        assert cap["state"] == "T.20.BOUNDED_EFFECTIVE_CONNECTOR_CAP"
        assert cap["schema_n_max"] == 4
        assert cap["max_variations_per_call"] == 1
        assert cap["ten_slot_chunk_plan"] == [1] * 10
        assert cap["ten_slot_provider_call_count"] == 10
    assert caps["schema_cap_ne_effective_runtime_cap"] is True
    assert caps["successful_slots_must_not_be_regenerated"] is True

    defaults = gate["adobe_execution_defaults"]
    assert defaults["requested_generation_width"] == 1080
    assert defaults["requested_generation_height"] == 1920
    assert defaults["observed_native_generation_width"] == 1072
    assert defaults["observed_native_generation_height"] == 1920
    assert defaults["delivery_width"] == 1080
    assert defaults["delivery_height"] == 1920
    assert defaults["dimension_normalization_operation"] == "image_crop_and_resize"
    assert defaults["dimension_normalization_required_when_native_drift_observed"] is True
    assert defaults["post_normalization_visual_readback"] == "REQUIRED"

    bindings = gate["runtime_receipt_bindings"]
    assert bindings["connector_runtime"] == "RavenCloudTaskbar/fr0333_adobe_image_runtime_receipt_0001.json"
    assert bindings["queue_failure_historical"] == "RavenCloudTaskbar/fr0333_adobe_image_queue_runtime_receipt_0002.json"
    assert bindings["queue_runtime_bounded"] == "RavenCloudTaskbar/fr0333_adobe_image_queue_runtime_receipt_0003.json"

    assert connector["provider"] == "ADOBE"
    assert connector["provider_receipt"]["execution_state"] == "PASS_RUNTIME"
    assert historical_failure["identifier"] == "FR0333.ADOBE.IMAGE.QUEUE.RUNTIME.RECEIPT.0002"
    assert historical_failure["result"]["queue_contract"] == "F.6.FAIL"

    assert runtime["identifier"] == "FR0333.ADOBE.IMAGE.QUEUE.RUNTIME.RECEIPT.0003"
    assert runtime["humanlock"] is True
    assert runtime["effective_connector_caps"]["IMAGE_GENERATE"]["effective_outputs_per_call"] == 1
    assert runtime["effective_connector_caps"]["IMAGE_INSTRUCT_EDIT"]["effective_outputs_per_call"] == 1
    assert runtime["effective_connector_caps"]["ten_slot_dispatch_plan"] == [1] * 10
    assert runtime["dimension_observation"]["observed_native_generation_size"] == [1072, 1920]
    assert runtime["dimension_observation"]["normalized_delivery_size"] == [1080, 1920]
    assert runtime["queue"]["requested_count"] == 10
    assert runtime["queue"]["final_delivered_count"] == 10
    assert runtime["queue"]["final_unique_slots"] == 10
    assert runtime["queue"]["retried_slots"] == ["Q09"]
    assert len(runtime["queue"]["preserved_successful_slots"]) == 9
    assert runtime["queue"]["final_visual_readback"] == "PASS"
    assert runtime["result"]["fr0333_adobe_image_tested_surface"] == "T.20.PASS.BOUNDED"
    assert runtime["result"]["ten_slot_generate_runtime"] == "T.20.PASS.BOUNDED"
    assert runtime["result"]["exact_1080_1920_after_normalization"] == "T.20.PASS.BOUNDED"
    assert runtime["result"]["universal_adobe_surface"] == "U.21.HOLD"
    assert runtime["quality_promotion"]["state"] == "U.21"

    hard = set(gate["hard_boundaries"])
    for boundary in (
        "TEN.REQUESTED = TEN.DELIVERED",
        "CURRENT.EFFECTIVE.CONNECTOR.OUTPUTS.PER.CALL = 1",
        "NATIVE.1072x1920 -> NORMALIZE -> 1080x1920",
        "RETRY.FAILED.SLOT != REGENERATE.SUCCESSFUL.SLOTS",
        "TEN.SLOT.RUNTIME.PASS != UNIVERSAL.ADOBE.PRODUCT.CAPACITY",
        "USER.REJECT = OUTPUT.HOLD",
    ):
        assert boundary in hard

    assert gate["golden_chain_route"].count("CHOMP") == 2
    return taskbars, lumen, gate, connector, historical_failure, runtime


def card(item):
    e = lambda v: html.escape(str(v))
    return f'''<article class="card"><div class="rail"><span>{e(item['lane'])}</span><strong>{e(item['state'])}</strong></div><h2>{e(item['project'])}</h2><p class="id">{e(item['id'])}</p><dl><dt>EVIDENCE</dt><dd>{e(item['evidence_state'])}</dd><dt>EXECUTION</dt><dd>{e(item['execution_state'])}</dd><dt>CLOUD</dt><dd>{e(item['cloud_mode'])}</dd><dt>NEXT</dt><dd>{e(item['next_action'])}</dd></dl></article>'''


def build_html(taskbars, lumen):
    cards = "\n".join(card(x) for x in taskbars["taskbars"])
    bars = " → ".join(taskbars["three_bars"])
    caps = " · ".join(lumen["capabilities"][:4])
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Raven Cloud Taskbar</title><style>:root{{--bg:#0b0d0d;--panel:#171a1a;--line:#b9c1c3;--text:#f3f5f5;--muted:#9ca5a7}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:15px/1.45 system-ui,sans-serif}}main{{max-width:1180px;margin:auto;padding:28px 18px 60px}}header{{border:1px solid #343a3b;padding:22px;margin-bottom:18px}}h1{{margin:0;font-size:clamp(28px,5vw,54px)}}.sub{{color:var(--muted)}}.status,.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;margin:18px 0}}.status div,.card{{border:1px solid #343a3b;background:var(--panel);padding:14px}}.rail{{display:flex;justify-content:space-between}}.id{{font-family:monospace;color:var(--muted)}}dl{{display:grid;grid-template-columns:82px 1fr;gap:7px}}dd{{margin:0}}</style></head><body><main><header><h1>RAVEN CLOUD TASKBAR</h1><p class="sub">{html.escape(bars)} · HumanLock active</p></header><section class="status"><div><b>CONTROL PLANE</b><br>{html.escape(taskbars['state'])}</div><div><b>LUMEN</b><br>{html.escape(lumen['provisioning_state'])}</div><div><b>CAPABILITY</b><br>{html.escape(caps)}</div></section><section class="grid">{cards}</section></main></body></html>'''


def main():
    taskbars, lumen, gate, connector, historical_failure, runtime = load_and_validate()
    DIST.mkdir(exist_ok=True)
    docs = {
        "taskbars.json": taskbars,
        "lumen_gateway.json": lumen,
        "fr0333_image_quality_gate_0004.json": gate,
        "fr0333_adobe_image_runtime_receipt_0001.json": connector,
        "fr0333_adobe_image_queue_runtime_receipt_0002.json": historical_failure,
        "fr0333_adobe_image_queue_runtime_receipt_0003.json": runtime,
    }
    (DIST / "index.html").write_text(build_html(taskbars, lumen), encoding="utf-8")
    for name, doc in docs.items():
        (DIST / name).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    files = [DIST / "index.html"] + [DIST / name for name in docs]
    sums = "\n".join(f"{sha256(p)}  {p.name}" for p in files) + "\n"
    (DIST / "SHA256SUMS").write_text(sums, encoding="utf-8")
    for key, value in REQUIRED_STATUS.items():
        print(f"{key}={value}")
    print(sums, end="")


if __name__ == "__main__":
    main()
