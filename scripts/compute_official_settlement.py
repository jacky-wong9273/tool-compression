#!/usr/bin/env python3
"""Recompute an official settlement from saved score files and a mapping.

Does not call a provider. The study statistic remains billed-basis total input.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tool_compression.official_score import SavedOutputError, settle_from_saved  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--score-root", required=True, type=Path)
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--execution-record", type=Path)
    args = parser.parse_args(argv)
    record = None
    if args.execution_record is not None:
        record = json.loads(args.execution_record.read_text(encoding="utf-8"))
    try:
        payload = settle_from_saved(args.score_root, args.mapping, execution_record=record)
    except SavedOutputError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    status = payload["reference_target_L_represents_C"]["combine_targets"] or {}
    print(json.dumps({"out": str(args.out), "target_reached": status.get("target_reached")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
