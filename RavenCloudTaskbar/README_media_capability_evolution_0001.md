# FR-0333 Media Capability Evolution 0001

## Engineering objective (not creator marketing)
On 2026-10-26, Meta began limited testing of Instagram Features (up to 90-minute horizontal long-form video with short-video links). We use that **public capability signal** to evolve the FR-0333 internal media evidence architecture. We do **not** claim access to the Meta API or pilot and do not connect, upload, monetize or publish.

### Passive MATRIX = 10 indexed numerical/reference nodes
`M01..M10` live in `fr0333_media_capability_evolution_0001.json`. Published pilot limit 5,400,000 ms is not a universal video system limit or general availability. Meta June 2026 is vendor future-preview, independent October reports corroborate limited release. Some matrix nodes are independently designed FR-0333 controls, **not** capabilities claimed to exist in Meta.

### Active METRICS = 10 operational definitions
`A01..A10` align 1:1 with `M01..M10`. Initially null and HOLD. Off-platform media indexing operates with local files and `ffprobe`. The ingestion runtime hashes source and clip bytes, measures actual dimensions/duration, validates unique IDs, safe relative paths, declared clipping ranges, exact source/clip parent mapping, and fails closed. It emits structured JSON receipts. The runtime **never** uploads, executes transformations, confirms content derivation, or updates the Golden Chain.

```bash
python3 RavenCloudTaskbar/fr0333_media_evolution_runtime_0001.py --manifest /path/to/manifest.json --root /path/to/media --receipt /path/to/local_receipt.json
python3 RavenCloudTaskbar/test_fr0333_media_evolution_runtime_0001.py
python3 RavenCloudTaskbar/validate_media_capability_evolution_0001.py
```

Example manifest format (sha256 and bytes must match actual files, duration_ms must match local ffprobe ±120 ms):

```json
{
  "assets": [
    {"id":"EP01","role":"episode","file":"episode.mp4","sha256":"<64 actual hex chars>","bytes":12345,"width":1920,"height":1080,"duration_ms":300000},
    {"id":"CL01","role":"clip","file":"clip.mp4","sha256":"<64 actual hex chars>","bytes":1234,"width":1080,"height":1920,"duration_ms":10000}
  ],
  "links":[{"clip_id":"CL01","episode_id":"EP01","source_start_ms":1000,"source_end_ms":11000}]
}
```

### Evidence classification
`PASS.OFFLINE_INTEGRITY_ONLY` proves readable local file bytes and duration/dimensions via ffprobe plus consistency of **declared** parent offsets. It does **not** prove that clip images/audio were actually derived from the stated parent. That demands a separate authenticated transformation execution receipt and/or independent frame/audio comparison. No such runtime proof is represented here.

Publishing eligibility, vendor access, content authenticity, operator HumanLock promotion and live integration stay `U.21.HOLD`. An exposed 90-minute *pilot* limit does not establish codec profiles, account eligibility, transcoding rules or generally available upload APIs.

### Routing
`ACTIVE.RESEARCH → FAN.OUT → MULTI.SOURCE → SECOND.LOOK → VERIFY → COMPARE.PASSIVE → GENIUS → HUMANLOCK → PROMOTE`. Golden Chain `0.11` appends to `0.10` without modifying older records. NEVER automatically promote a source as an observed local capability. No tasks or monitors are installed. Real ffmpeg/ffprobe smoke tests are **local synthetic videos**: evidence of our gate, not evidence of Meta uploads or AI intelligence.
