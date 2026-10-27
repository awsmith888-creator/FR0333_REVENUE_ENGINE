#!/usr/bin/env python3
"""Mock-probe mutation tests, plus actual ffmpeg/ffprobe local video smoke test."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from fr0333_media_evolution_runtime_0001 import inspect, resolved_local_file

def digest(blob):
    return hashlib.sha256(blob).hexdigest()

def build_mock(root):
    a,b=b"fixture episode bytes 0001",b"fixture clip bytes 0002"
    (root/"episode.bin").write_bytes(a)
    (root/"clip.bin").write_bytes(b)
    records=[
        {"id":"EP01","role":"episode","file":"episode.bin","sha256":digest(a),
         "bytes":len(a),"width":1920,"height":1080,"duration_ms":5000},
        {"id":"CL01","role":"clip","file":"clip.bin","sha256":digest(b),
         "bytes":len(b),"width":1080,"height":1920,"duration_ms":1000}
    ]
    return {"assets":records,"links":[{"clip_id":"CL01","episode_id":"EP01",
            "source_start_ms":1000,"source_end_ms":2000}]}

def mock_probe(path):
    if path.name=="episode.bin":
        return {"width":1920,"height":1080,"duration_ms":5000}
    return {"width":1080,"height":1920,"duration_ms":1000}

with tempfile.TemporaryDirectory() as folder:
    root=Path(folder)
    original=build_mock(root)
    good=inspect(original,root,mock_probe)
    assert good["state"]=="T.20.PASS.OFFLINE_INTEGRITY_ONLY",good
    assert good["verified_assets"]==2 and good["verified_links"]==1
    assert good["source_content_derivation"]=="U.21.HOLD"
    assert good["provider_actions"]==0
    mutations=[
        ("changed hash", lambda d: d["assets"][0].update(sha256="0"*64)),
        ("changed dimensions", lambda d: d["assets"][1].update(width=720)),
        ("false duration", lambda d: d["assets"][0].update(duration_ms=9000)),
        ("missing parent", lambda d: d["links"][0].update(episode_id="EP99")),
        ("invalid offsets", lambda d: d["links"][0].update(source_end_ms=6000)),
        ("disconnected clip", lambda d: d["links"].clear()),
        ("duplicate asset ID", lambda d: d["assets"][1].update(id="EP01")),
        ("escaped file path", lambda d: d["assets"][0].update(file="../escape.bin")),
    ]
    for label,mutation in mutations:
        broken=copy.deepcopy(original)
        mutation(broken)
        result=inspect(broken,root,mock_probe)
        assert result["state"]=="F.6.REJECT",(label,result)
    external=root.parent/"unsafe-external-file.mp4"
    try:
        (root/"link.mp4").symlink_to(external)
        assert False,"symlink fixture should not pass"
    except OSError:
        pass
    else:
        try:
            resolved_local_file(root,"link.mp4")
        except (ValueError,FileNotFoundError):
            pass
        else:
            raise AssertionError("symlink outside root accepted")

if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
    raise RuntimeError("real local-video smoke test requires ffmpeg and ffprobe")
with tempfile.TemporaryDirectory() as folder:
    root=Path(folder)
    full=root/"full.mp4"
    clip=root/"short.mp4"
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","lavfi",
                    "-i","color=c=black:s=320x180:r=10","-t","3",
                    "-an","-c:v","mpeg4",str(full)],check=True,timeout=30)
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
                    "-ss","1","-i",str(full),"-t","1",
                    "-an","-c:v","mpeg4",str(clip)],check=True,timeout=30)
    from fr0333_media_evolution_runtime_0001 import ffprobe_local,sha256_file
    full_meta=ffprobe_local(full)
    clip_meta=ffprobe_local(clip)
    def asset(asset_id,role,path,meta):
        hash_value,byte_size=sha256_file(path)
        return {"id":asset_id,"role":role,"file":path.name,"sha256":hash_value,
                "bytes":byte_size,**meta}
    manifest={
        "assets":[asset("EP01","episode",full,full_meta),asset("CL01","clip",clip,clip_meta)],
        "links":[{"clip_id":"CL01","episode_id":"EP01",
                  "source_start_ms":1000,"source_end_ms":2000}]
    }
    measured=inspect(manifest,root)
    assert measured["state"]=="T.20.PASS.OFFLINE_INTEGRITY_ONLY",measured
    assert measured["verified_assets"]==2 and measured["verified_links"]==1
    assert all(f["bytes"]>0 for f in measured["files"])
    assert measured["source_content_derivation"]=="U.21.HOLD"
    print(json.dumps({"state":"T.20.PASS.OFFLINE_ONLY",
       "mock_mutations_rejected":len(mutations),
       "real_generated_video_files_verified":2,
       "real_ffprobe_validations":2,
       "provider_actions":0,
       "source_derivation":"U.21.HOLD","publication":"U.21.HOLD"}))
