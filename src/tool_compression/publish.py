"""JSON written by Week 1. Long strings are refused so benchmark prose cannot land in git."""

import json
from pathlib import Path

MAX_STRING = 400


def dump_public(path: Path, payload: dict) -> None:
    cleaned = _clean(payload)
    _assert_short(cleaned)
    Path(path).write_text(json.dumps(cleaned, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def dump_jsonl(path: Path, rows: list[dict]) -> None:
    lines = []
    for row in rows:
        cleaned = _clean(row)
        _assert_short(cleaned)
        lines.append(json.dumps(cleaned, sort_keys=True, separators=(",", ":")))
    Path(path).write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _clean(value):
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, dict):
        return {str(key): _clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value]
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    raise TypeError(type(value).__name__)


def _assert_short(value, path="$") -> None:
    if isinstance(value, str):
        if len(value) > MAX_STRING:
            raise RuntimeError(f"refusing long string at {path} ({len(value)} chars)")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _assert_short(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _assert_short(item, f"{path}[{index}]")
