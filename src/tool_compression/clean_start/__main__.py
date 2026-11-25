"""CLI for the clean-start study. The default path does not contact a provider."""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

from tool_compression.clean_start.load import load_prereqs, load_questions
from tool_compression.clean_start.pilot import build_draw, freeze, study_dir
from tool_compression.clean_start.pin import study_manifest
from tool_compression.clean_start.runner import (
    OfficialBfclExecutor,
    authorized_transport,
    build_slots,
    execute,
    resolve_bfcl_package,
    write_plan,
)
from tool_compression.clean_start.scoring import evaluate_instructions
from tool_compression.clean_start.categories import ALL_SCORING_CATEGORIES


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tool-compression.clean_start")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("manifest")
    sub.add_parser("freeze")
    sub.add_parser("evaluate-help")

    run = sub.add_parser("run")
    run.add_argument("--out", required=True, type=Path)
    run.add_argument("--pilot", action="store_true")
    run.add_argument("--live", action="store_true")
    run.add_argument("--authorize-live", action="store_true")
    run.add_argument("--ceiling-usd", type=str)
    run.add_argument("--bfcl-root", type=Path)

    args = parser.parse_args(argv)
    if args.command == "manifest":
        print(json.dumps(study_manifest(), indent=2, sort_keys=True))
        return 0
    if args.command == "evaluate-help":
        print(evaluate_instructions())
        return 0
    if args.command == "freeze":
        summary = freeze()
        print(json.dumps(summary, sort_keys=True))
        return 0
    if args.command == "run":
        return _run(args)
    return 2


def _run(args) -> int:
    if args.live != args.authorize_live:
        print(
            "refusing to contact the provider: --live and --authorize-live are both required",
            file=sys.stderr,
        )
        return 2
    if args.live:
        if args.ceiling_usd is None:
            print("refusing: --authorize-live requires --ceiling-usd", file=sys.stderr)
            return 2
        ceiling = Decimal(args.ceiling_usd)
        if ceiling <= 0:
            print("refusing: --ceiling-usd must be greater than 0", file=sys.stderr)
            return 2
    else:
        ceiling = None
    cases = _select_cases(args.pilot)
    if not args.live:
        write_plan(cases, args.out, pilot=args.pilot)
        print(f"wrote dry plan {args.out / 'run.json'}")
        return 0
    slots = build_slots(cases)
    needs_backend = any(slot["kind"] == "trajectory" for slot in slots)
    if needs_backend and args.bfcl_root is None:
        print(
            "refusing before any request: a trajectory category needs --bfcl-root "
            "pointing at the pinned Gorilla checkout",
            file=sys.stderr,
        )
        return 2
    executor = None
    if needs_backend:
        try:
            package = resolve_bfcl_package(args.bfcl_root)
        except FileNotFoundError as exc:
            print(f"refusing before any request: {exc}", file=sys.stderr)
            return 2
        executor = OfficialBfclExecutor(package, "deepseek_flash")
    # Key read and socket use happen only after the checks above.
    transport = authorized_transport()
    result = execute(
        cases,
        slots,
        args.out,
        transport,
        ceiling_usd=ceiling,
        executor=executor,
    )
    print(json.dumps({
        "complete": result["complete"],
        "status": result["status"],
        "reason": result["reason"],
        "running_usd": result["running_usd"],
    }, sort_keys=True))
    return 0 if result["complete"] else 1


def _select_cases(pilot: bool) -> list[dict]:
    if not pilot:
        cases = []
        for category in ALL_SCORING_CATEGORIES:
            cases.extend(load_prereqs(category))
            cases.extend(load_questions(category))
        return cases
    draw = build_draw()
    wanted = {(row["category"], row["case_id"]) for row in draw["rows"]}
    chosen = []
    for category in ALL_SCORING_CATEGORIES:
        for case in load_questions(category):
            if (category, case["id"]) in wanted:
                chosen.append(case)
    if len(chosen) != len(wanted):
        raise RuntimeError("pilot draw does not match the loaded questions")
    return chosen


def _study_dir() -> Path:
    return study_dir()


if __name__ == "__main__":
    raise SystemExit(main())
