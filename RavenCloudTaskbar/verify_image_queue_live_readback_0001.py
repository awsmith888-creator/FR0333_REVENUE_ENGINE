#!/usr/bin/env python3
"""Read-only FR-0333 gate for existing Adobe receipt 0003. No provider calls."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

IDENTIFIER = "FR.0333.GOLDEN.CHAIN.IMAGE.QUEUE.LIVE.READBACK.0001"
RECEIPT_ID = "FR0333.ADOBE.IMAGE.QUEUE.RUNTIME.RECEIPT.0003"
EXPECTED_SLOTS = [f"Q{i:02d}" for i in range(1, 11)]
EXPECTED_SIZE = (1080, 1920)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def confined(base, name):
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ValueError("missing or absolute evidence filename")
    base = base.resolve()
    path = (base / name).resolve()
    if not path.is_relative_to(base) or path == base:
        raise ValueError("evidence path escapes evidence directory")
    return path


def run(receipt_path, evidence_dir):
    result = {
        "identifier": IDENTIFIER,
        "receipt_identifier": RECEIPT_ID,
        "mode": "READ_ONLY_EXISTING_OUTPUTS",
        "provider_calls": 0,
        "workflow_runs": 0,
        "requested_count": 10,
        "verified_byte_count": 0,
        "unique_final_sha256_count": 0,
        "verified_provider_record_slots": 0,
        "state": "U.21.HOLD",
        "quality_promotion": "U.21.HOLD",
        "mainline_merge": "U.21.HOLD",
        "per_slot": [],
        "hold": [],
        "reject": [],
    }
    def hold(message):
        result["hold"].append(message)
    def reject(message):
        result["reject"].append(message)

    try:
        receipt_bytes = receipt_path.read_bytes()
        receipt = json.loads(receipt_bytes)
        result["receipt_sha256"] = digest(receipt_bytes)
    except (OSError, ValueError) as exc:
        hold("receipt missing or unreadable: " + str(exc))
        return result
    if receipt.get("identifier") != RECEIPT_ID:
        reject("receipt identifier mismatch")
    rows = receipt.get("slots", [])
    if not isinstance(rows, list) or len(rows) != 10:
        reject("receipt must contain exactly ten slots")
        rows = []
    slots = {r.get("slot_id"): r for r in rows if isinstance(r, dict)}
    if len(slots) != 10 or set(slots) != set(EXPECTED_SLOTS):
        reject("receipt slot cardinality/uniqueness mismatch")
    if receipt.get("queue", {}).get("final_delivered_count") != 10:
        reject("existing receipt does not claim ten final outputs")

    manifest_path = evidence_dir / "provider_export_manifest.json"
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes)
        result["provider_export_manifest_sha256"] = digest(manifest_bytes)
    except (OSError, ValueError) as exc:
        hold("provider_export_manifest.json absent/unreadable: " + str(exc))
        manifest = {}
    if manifest:
        if manifest.get("receipt_identifier") != RECEIPT_ID:
            reject("provider manifest receipt identifier mismatch")
        if manifest.get("source_class") != "EXISTING_ADOBE_PROVIDER_RESPONSE_EXPORT":
            reject("manifest source_class must identify existing provider response export")
    manifest_rows = manifest.get("slots", []) if isinstance(manifest, dict) else []
    if manifest and (not isinstance(manifest_rows, list) or len(manifest_rows) != 10):
        reject("provider manifest requires ten slot bindings")
        manifest_rows = []
    indexed_rows = {r.get("slot_id"): r for r in manifest_rows if isinstance(r, dict)}
    if manifest and (len(indexed_rows) != 10 or set(indexed_rows) != set(EXPECTED_SLOTS)):
        reject("provider manifest slot IDs duplicate or missing")

    seen_hashes = {}
    seen_final_urls = {}
    seen_ids = {}
    for slot_id in EXPECTED_SLOTS:
        slot = slots.get(slot_id, {})
        evidence = indexed_rows.get(slot_id, {})
        row = {"slot_id": slot_id, "image_bytes": "HOLD", "provider_binding": "HOLD"}
        result["per_slot"].append(row)
        if not slot:
            hold(slot_id + ": absent in receipt")
            continue
        gen_id = slot.get("retry_generation_request_id") if slot_id == "Q09" else slot.get("generation_request_id")
        gen_url = slot.get("retry_generation_output_url") if slot_id == "Q09" else slot.get("generation_output_url")
        norm_id = slot.get("normalization_request_id")
        final_url = slot.get("final_output_url")
        if not all([gen_id, gen_url, norm_id, final_url]):
            reject(slot_id + ": missing generation/normalization provenance identifiers")
            continue
        if final_url in seen_final_urls:
            reject(slot_id + ": repeated final output URL with " + seen_final_urls[final_url])
        seen_final_urls[final_url] = slot_id
        if gen_id in seen_ids or norm_id in seen_ids:
            reject(slot_id + ": reused provider request identifier")
        seen_ids[gen_id] = slot_id
        seen_ids[norm_id] = slot_id
        if slot.get("final_dimensions") != [1080, 1920]:
            reject(slot_id + ": receipt dimension claim mismatch")
        if slot.get("readback") != "PASS":
            reject(slot_id + ": receipt visual readback is not PASS")
        if not evidence:
            hold(slot_id + ": provider evidence not supplied")
            continue
        for key, expected in (
            ("generation_request_id", gen_id),
            ("generation_output_url", gen_url),
            ("normalization_request_id", norm_id),
            ("final_output_url", final_url),
        ):
            if evidence.get(key) != expected:
                reject(slot_id + ": " + key + " does not match receipt")
        try:
            gen_path = confined(evidence_dir, evidence.get("generation_response_file"))
            norm_path = confined(evidence_dir, evidence.get("normalization_response_file"))
            gen_bytes = gen_path.read_bytes()
            norm_bytes = norm_path.read_bytes()
        except (OSError, ValueError) as exc:
            hold(slot_id + ": raw provider response unavailable: " + str(exc))
        else:
            if not gen_bytes or not norm_bytes:
                reject(slot_id + ": empty provider response file")
            elif gen_id.encode() not in gen_bytes or gen_url.encode() not in gen_bytes:
                reject(slot_id + ": generation response not bound to recorded ID/URL")
            elif norm_id.encode() not in norm_bytes or final_url.encode() not in norm_bytes:
                reject(slot_id + ": normalization response not bound to recorded ID/URL")
            else:
                row["provider_binding"] = "T.20.BOUNDED_RECORD_MATCH"
                row["generation_response_sha256"] = digest(gen_bytes)
                row["normalization_response_sha256"] = digest(norm_bytes)
                result["verified_provider_record_slots"] += 1
        try:
            file_path = confined(evidence_dir, evidence.get("final_file"))
            data = file_path.read_bytes()
        except (OSError, ValueError) as exc:
            hold(slot_id + ": final image unavailable: " + str(exc))
            continue
        if not data:
            reject(slot_id + ": zero-byte output")
            continue
        file_hash = digest(data)
        row["final_sha256"] = file_hash
        row["final_byte_count"] = len(data)
        if file_hash in seen_hashes:
            reject(slot_id + ": duplicate output bytes match " + seen_hashes[file_hash])
        seen_hashes[file_hash] = slot_id
        try:
            from PIL import Image
            with Image.open(file_path) as im:
                fmt = im.format
                dimensions = im.size
                im.verify()
            with Image.open(file_path) as im:
                im.load()
        except ImportError:
            hold(slot_id + ": Pillow required to decode and verify final image")
            continue
        except Exception as exc:
            reject(slot_id + ": output image cannot be decoded: " + str(exc))
            continue
        if dimensions != EXPECTED_SIZE or fmt not in ("PNG", "JPEG", "WEBP"):
            reject(slot_id + ": decoded format/dimensions not accepted")
            continue
        row["format"] = fmt
        row["decoded_dimensions"] = list(dimensions)
        row["image_bytes"] = "T.20.BOUNDED_DECODED_BYTES"
        result["verified_byte_count"] += 1
    result["unique_final_sha256_count"] = len(seen_hashes)
    if result["reject"]:
        result["state"] = "F.6.REJECT"
    elif result["hold"]:
        result["state"] = "U.21.HOLD"
    elif (result["verified_byte_count"] == 10
          and result["verified_provider_record_slots"] == 10
          and len(seen_hashes) == 10):
        result["state"] = "T.20.BOUNDED_FILE_AND_PROVIDER_RECORD_MATCH"
    else:
        result["state"] = "U.21.HOLD"
    result["provenance_limit"] = (
        "This is a read-only consistency check of supplied existing files and "
        "provider response exports, not provider-signed attestation. "
        "No visual quality or user acceptance is inferred."
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parent
    parser.add_argument("--receipt", type=Path, default=root / "fr0333_adobe_image_queue_runtime_receipt_0003.json")
    parser.add_argument("--evidence-dir", type=Path, default=root / "image_queue_live_evidence_0003")
    parser.add_argument("--write-certificate", type=Path, help="Optional local JSON output; never writes to GitHub")
    args = parser.parse_args()
    result = run(args.receipt, args.evidence_dir)
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.write_certificate:
        args.write_certificate.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if result["state"].startswith("T.20.") else 2


if __name__ == "__main__":
    sys.exit(main())
