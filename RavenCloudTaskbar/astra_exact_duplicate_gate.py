"""FR-0333 Astra exact-byte duplicate *audit*, with no mutation capability.

Input files must be locally accessible. Same dimensions, similar names or matching
perceptual hashes are not evidence of byte identity; no delete decisions are made.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

IMAGE_SUFFIXES = frozenset({'.png', '.jpg', '.jpeg', '.webp', '.tif', '.tiff', '.bmp', '.gif'})


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def audit(paths: Iterable[str]) -> dict:
    """Return verifiable candidates only; neither select keepers nor delete files."""
    unique_paths: dict[str, Path] = {}
    rejects: list[dict] = []
    for raw in paths:
        path = Path(raw)
        if not path.is_file():
            rejects.append({'path': str(path), 'reason': 'NOT_A_READABLE_FILE'})
            continue
        if path.suffix.lower() not in IMAGE_SUFFIXES:
            rejects.append({'path': str(path), 'reason': 'NOT_SUPPORTED_IMAGE_EXTENSION'})
            continue
        unique_paths[str(path.resolve())] = path

    sizes: dict[int, list[Path]] = {}
    for path in unique_paths.values():
        sizes.setdefault(path.stat().st_size, []).append(path)

    exact_groups: list[dict] = []
    hashed_files = 0
    for size, candidates in sorted(sizes.items()):
        if len(candidates) < 2:
            continue
        hashes: dict[str, list[str]] = {}
        for path in candidates:
            hashed_files += 1
            hashes.setdefault(digest_file(path), []).append(str(path))
        for sha, members in sorted(hashes.items()):
            if len(members) > 1:
                exact_groups.append({
                    'sha256': sha,
                    'size_bytes': size,
                    'files': sorted(members),
                    'copies_beyond_one': len(members) - 1,
                    'classification': 'EXACT_BYTE_DUPLICATE',
                    'deletion_authorized': False,
                })

    return {
        'identifier': 'FR0333.ASTRA.EXACT.DUPLICATE.AUDIT.0001',
        'evidence_class': 'LOCAL_FILE_BYTES_SHA256',
        'state': 'AUDIT_ONLY_NO_MUTATION',
        'input_unique_paths': len(unique_paths),
        'size_collision_files_hashed': hashed_files,
        'exact_duplicate_groups': sorted(exact_groups, key=lambda x: x['files'][0]),
        'exact_duplicate_excess_copies': sum(x['copies_beyond_one'] for x in exact_groups),
        'rejected_inputs': rejects,
        'selected_canonical_file': None,
        'deleted_files': [],
        'library_mutations': 0,
        'limitations': [
            'Only local input paths examined; not a complete ChatGPT Library inventory',
            'Identical visual content with differing bytes is not classified as an exact duplicate',
            'No retention priority, Library deletion or provider delivery is established',
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Astra duplicate audit; NEVER deletes')
    parser.add_argument('images', nargs='*', help='Paths to accessible image files')
    args = parser.parse_args()
    print(json.dumps(audit(args.images), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
