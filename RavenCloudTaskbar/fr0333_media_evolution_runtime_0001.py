#!/usr/bin/env python3
"""FR0333 offline media source/clip integrity gate (on-demand only).

No network access, no uploads, no video editing, no provider commands.
ffprobe inspects local file metadata; no claim that the content of a clip
actually derives from the alleged parent (separate evidence gate).
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

ID = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$")
MAX_MANIFEST_ASSETS = 100
MAX_MANIFEST_LINKS = 300

def sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            size += len(chunk)
            digest.update(chunk)
    return digest.hexdigest(), size

def resolved_local_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError("unsafe file path")
    part = PurePosixPath(relative)
    if part.is_absolute() or part.as_posix() in (".", "..") or ".." in part.parts or "." in part.parts:
        raise ValueError("unsafe file path")
    path = (root / relative).resolve(strict=True)
    path.relative_to(root.resolve(strict=True))
    if not path.is_file():
        raise ValueError("asset is not a file")
    return path

def ffprobe_local(path: Path) -> dict:
    run = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=codec_type,width,height", "-of", "json", str(path)],
        capture_output=True, text=True, timeout=30, check=True
    )
    record = json.loads(run.stdout)
    videos = [s for s in record.get("streams", []) if s.get("codec_type") == "video"]
    if not videos:
        raise ValueError("missing video stream")
    fmt = record.get("format", {})
    duration_ms = round(float(fmt["duration"]) * 1000)
    video = videos[0]
    width, height = int(video["width"]), int(video["height"])
    if min(duration_ms, width, height) <= 0:
        raise ValueError("invalid probed media measurement")
    return {"duration_ms": duration_ms, "width": width, "height": height}

def inspect(manifest: dict, root: Path, probe_fn=ffprobe_local) -> dict:
    """Return a fail-closed receipt without writing or transmitting source media."""
    errors = []
    files = []
    linked = []
    assets = manifest.get("assets", [])
    links = manifest.get("links", [])
    if (not isinstance(assets, list) or not isinstance(links, list)
            or not 1 <= len(assets) <= MAX_MANIFEST_ASSETS
            or len(links) > MAX_MANIFEST_LINKS):
        return {"state":"F.6.REJECT", "errors":["invalid asset/link counts"],"verified_assets":0}
    seen_ids = set()
    seen_hashes = set()
    indexed = {}
    for asset in assets:
        aid = asset.get("id")
        try:
            if not isinstance(aid, str) or not ID.fullmatch(aid) or aid in seen_ids:
                raise ValueError("invalid or duplicate asset ID")
            seen_ids.add(aid)
            if asset.get("role") not in ("episode", "clip"):
                raise ValueError("unknown media role")
            path = resolved_local_file(root, asset["file"])
            actual_sha, bytes_count = sha256_file(path)
            if bytes_count <= 0 or actual_sha != asset.get("sha256") or bytes_count != asset.get("bytes"):
                raise ValueError("unverified bytes or hash mismatch")
            if actual_sha in seen_hashes:
                raise ValueError("identical video payload duplicated under two identifiers")
            seen_hashes.add(actual_sha)
            measured = probe_fn(path)
            if measured["width"] != asset.get("width") or measured["height"] != asset.get("height"):
                raise ValueError("dimension mismatch")
            if abs(measured["duration_ms"] - asset.get("duration_ms", -99999999)) > 120:
                raise ValueError("duration mismatch")
            if min(measured["width"], measured["height"], measured["duration_ms"]) <= 0:
                raise ValueError("invalid positive measurement")
            indexed[aid] = {"role":asset["role"],**measured}
            files.append({"id":aid,"role":asset["role"],"sha256":actual_sha,
                          "bytes":bytes_count,**measured,"status":"T.20.PASS.BYTE_AND_METADATA"})
        except (KeyError, ValueError, OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired,
                FileNotFoundError, TypeError, OverflowError, json.JSONDecodeError) as exc:
            errors.append(f"asset {aid!r}: {type(exc).__name__}: {str(exc)[:140]}")
    clip_ids = {a["id"] for a in files if a["role"]=="clip"}
    episode_ids = {a["id"] for a in files if a["role"]=="episode"}
    recorded_clip_ids = set()
    for link in links:
        try:
            clip = link["clip_id"]
            episode = link["episode_id"]
            start = link["source_start_ms"]
            end = link["source_end_ms"]
            if clip not in clip_ids or episode not in episode_ids or clip in recorded_clip_ids:
                raise ValueError("duplicate clip link or unresolved parent")
            if type(start) is not int or type(end) is not int or not 0 <= start < end <= indexed[episode]["duration_ms"]:
                raise ValueError("invalid source offsets")
            if abs(indexed[clip]["duration_ms"] - (end - start)) > 200:
                raise ValueError("clip duration inconsistent with declared trim window")
            recorded_clip_ids.add(clip)
            linked.append({"clip_id":clip,"episode_id":episode,"source_start_ms":start,
                           "source_end_ms":end,"link_state":"T.20.PASS.DECLARED_OFFSETS_ONLY",
                           "content_derivation":"U.21.HOLD"})
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"link: {type(exc).__name__}: {str(exc)[:140]}")
    if clip_ids != recorded_clip_ids:
        errors.append("every clip requires exactly one valid declared parent link")
    if not episode_ids:
        errors.append("at least one root episode is required")
    state = "F.6.REJECT" if errors else "T.20.PASS.OFFLINE_INTEGRITY_ONLY"
    return {
        "identifier":"FR0333.MEDIA.LOCAL.READBACK.0001",
        "state":state,
        "verified_assets":len(files),
        "verified_links":len(linked),
        "files":files,
        "links":linked,
        "errors":errors,
        "source_content_derivation":"U.21.HOLD",
        "publisher_eligibility":"U.21.HOLD",
        "external_delivery":"U.21.HOLD",
        "canonical_promotion":"U.21.HOLD",
        "provider_actions":0
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--manifest",required=True,type=Path)
    parser.add_argument("--root",required=True,type=Path)
    parser.add_argument("--receipt",type=Path,default=None)
    args=parser.parse_args()
    manifest=json.loads(args.manifest.read_text(encoding="utf-8"))
    result=inspect(manifest,args.root)
    encoded=json.dumps(result,indent=2,sort_keys=True)+"\n"
    if args.receipt:
        args.receipt.write_text(encoded,encoding="utf-8")
    print(encoded,end="")
    raise SystemExit(0 if result["state"].startswith("T.20.") else 1)

if __name__=="__main__":
    main()
