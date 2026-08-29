#!/usr/bin/env python3
"""FR-0333 reference-point integrity gate.

This gate treats FR-0333 addresses as exact string tokens, never as floating-point
numbers. Any increment-symbol Delta token in repository text must use the
canonical four-field address grammar: 1.<DELTA>.1.<ADDRESS>.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_FILE = ROOT / "RavenCloudTaskbar" / "fr0333_andalusia_year_reference_points_0001.json"

INCREMENT = chr(0x2206)      # U+2206, canonical FR-0333 Delta glyph
GREEK_DELTA = chr(0x0394)    # U+0394, prohibited glyph drift
CANONICAL = re.compile(r"(?<![A-Za-z0-9_.])1\." + re.escape(INCREMENT) + r"\.1\.[0-9]+(?![A-Za-z0-9_.])")

TEXT_SUFFIXES = {
    ".py", ".json", ".md", ".txt", ".yml", ".yaml", ".xml", ".gradle", ".properties", ".toml", ".ini"
}
IGNORE_NAMES = {"fr0333_reference_point_gate.py", "test_fr0333_reference_point_gate.py"}


def validate_delta_text(text: str, source: str) -> list[str]:
    errors: list[str] = []
    if GREEK_DELTA in text:
        errors.append(f"{source}: prohibited U+0394 Greek Delta found; canonical glyph is U+2206 inside full reference form")

    for match in re.finditer(re.escape(INCREMENT), text):
        pos = match.start()
        window_start = max(0, pos - 32)
        window_end = min(len(text), pos + 48)
        window = text[window_start:window_end]
        local_pos = pos - window_start
        valid = False
        for token in CANONICAL.finditer(window):
            if token.start() <= local_pos < token.end():
                valid = True
                break
        if not valid:
            line = text.count("\n", 0, pos) + 1
            errors.append(f"{source}:{line}: Delta glyph is not bound to canonical 1.<DELTA>.1.<ADDRESS> reference structure")
    return errors


def validate_reference_file() -> list[str]:
    errors: list[str] = []
    data = json.loads(REFERENCE_FILE.read_text(encoding="utf-8"))

    rule = data.get("rule", "")
    if "INDEX_TOKENS_ARE_STRING_IDENTIFIERS" not in rule:
        errors.append("reference-point file: exact-string index rule missing")
    if "MUST_NOT_BE_NORMALIZED" not in rule:
        errors.append("reference-point file: anti-normalization rule missing")

    sequence = data.get("ordered_reference_sequence", [])
    if not all(isinstance(item, str) for item in sequence):
        errors.append("reference-point file: every ordered reference token must remain a string")
    if "1.8" not in sequence or "1.80" not in sequence:
        errors.append("reference-point file: required distinct tokens 1.8 and 1.80 are missing")
    if sequence.count("1.8") != 1 or sequence.count("1.80") != 1:
        errors.append("reference-point file: 1.8 / 1.80 token multiplicity changed")

    binding = data.get("critical_binding", {})
    if binding.get("1.8_ne_1.80") is not True:
        errors.append("reference-point file: 1.8 != 1.80 binding is not locked true")
    if binding.get("normalization") != "FORBIDDEN":
        errors.append("reference-point file: normalization must remain FORBIDDEN")
    if binding.get("trailing_zero_preservation") != "REQUIRED":
        errors.append("reference-point file: trailing-zero preservation must remain REQUIRED")

    for item in data.get("reference_points", []):
        if not isinstance(item.get("index"), str):
            errors.append(f"reference-point file: non-string index found: {item!r}")
    return errors


def iter_repo_text_files():
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.name in IGNORE_NAMES:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {"Dockerfile"}:
            continue
        yield path


def run_gate() -> list[str]:
    errors = validate_reference_file()
    scanned = 0
    for path in iter_repo_text_files():
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        errors.extend(validate_delta_text(text, str(path.relative_to(ROOT))))

    print(f"FR0333_REFERENCE_POINT_GATE scanned_files={scanned}")
    if errors:
        print(f"FR0333_REFERENCE_POINT_GATE FAIL count={len(errors)}")
        for error in errors:
            print(f"FAIL: {error}")
    else:
        print("FR0333_REFERENCE_POINT_GATE PASS")
        print("LOCK: reference tokens remain strings; numeric collapse forbidden")
        print("LOCK: Delta form = 1.<DELTA>.1.<ADDRESS>")
    return errors


if __name__ == "__main__":
    sys.exit(1 if run_gate() else 0)
