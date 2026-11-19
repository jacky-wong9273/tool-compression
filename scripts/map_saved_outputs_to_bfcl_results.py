#!/usr/bin/env python3
"""Map saved stage B ledgers onto BFCL result files.

Does not score and does not call a provider. Paths are arguments. Historical
machine directories are not defaults.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tool_compression.official_score import SavedOutputError, map_saved_outputs  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage-b", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--expected-groups", type=int)
    args = parser.parse_args(argv)
    try:
        summary = map_saved_outputs(
            args.stage_b,
            args.out,
            expected_groups=args.expected_groups,
        )
    except SavedOutputError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"wrote {summary['mapping']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
