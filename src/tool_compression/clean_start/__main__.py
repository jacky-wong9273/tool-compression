"""CLI for the clean-start study. The default path does not contact a provider."""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from tool_compression.clean_start.pilot import build_draw, freeze, study_dir
from tool_compression.clean_start.pin import STUDY_ID, study_manifest
from tool_compression.clean_start.runner import (
    OfficialBfclExecutor,
    RunStopped,
    authorized_transport,
    build_slots,
    execute,
    parse_thinking_modes,
    preflight,
    refuse_reuse,
    resolve_bfcl_package,
    write_plan,
)
from tool_compression.clean_start.scope import in_scope_questions, select_full_run_cases, study_categories
from tool_compression.clean_start.scoring import evaluate_instructions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tool-compression.clean_start")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("manifest")
    sub.add_parser("freeze")
    sub.add_parser("evaluate-help")
    package = sub.add_parser("package")
    package.add_argument("--out", type=Path)
    report = sub.add_parser("report-pilot")
    report.add_argument("--evidence", type=Path)
    report.add_argument("--out", type=Path)
    report.add_argument("--revised", action="store_true", help="the c47b186c flight instead of the 0c0284d one")
    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("--out", required=True, type=Path)
    evaluate.add_argument("--bfcl-root", required=True, type=Path)
    evaluate.add_argument("--thinking", required=True)

    run = sub.add_parser("run")
    run.add_argument("--out", required=True, type=Path)
    run.add_argument("--pilot", action="store_true")
    run.add_argument("--live", action="store_true")
    run.add_argument("--authorize-live", action="store_true")
    run.add_argument("--thinking", help="off, on, or off,on; required with --live")
    run.add_argument(
        "--memory-prereqs",
        choices=("none", "matched"),
        help="pilot only, required with --pilot --live: none, or the prerequisite "
        "conversations of the scenarios the drawn memory questions use",
    )
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
    if args.command == "package":
        from tool_compression.clean_start.package import build_package

        summary = build_package(args.out or study_dir() / "package")
        print(json.dumps(summary, sort_keys=True))
        return 0
    if args.command == "report-pilot" and args.revised:
        from tool_compression.clean_start.report import REVISED_EVIDENCE, write_revised_pilot_report

        summary = write_revised_pilot_report(
            args.evidence or study_dir() / REVISED_EVIDENCE,
            args.out or study_dir() / "package" / "pilot_2026_11_25_revised_analysis.json",
        )
        print(json.dumps(summary, sort_keys=True))
        return 0
    if args.command == "report-pilot":
        from tool_compression.clean_start.report import PILOT_EVIDENCE, write_pilot_report

        summary = write_pilot_report(
            args.evidence or study_dir() / PILOT_EVIDENCE,
            args.out or study_dir() / "package" / "pilot_2026_11_25_analysis.json",
        )
        print(json.dumps(summary, sort_keys=True))
        return 0
    if args.command == "evaluate":
        from tool_compression.clean_start.evaluate import run_official_evaluation

        try:
            modes = parse_thinking_modes(args.thinking)
        except ValueError as exc:
            print(f"refusing: {exc}", file=sys.stderr)
            return 2
        summary = run_official_evaluation(args.out, args.bfcl_root, modes)
        print(json.dumps({"ok": summary["ok"], "runs": len(summary["runs"]), "failed": summary["failed"]}, sort_keys=True))
        return 0 if summary["ok"] else 1
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
    if args.live and args.thinking is None:
        print("refusing: --live requires --thinking off, on, or off,on", file=sys.stderr)
        return 2
    try:
        modes = parse_thinking_modes(args.thinking or "off,on")
    except ValueError as exc:
        print(f"refusing: {exc}", file=sys.stderr)
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
    if args.memory_prereqs and not args.pilot:
        print("refusing: --memory-prereqs applies to --pilot; the full run sends every prerequisite", file=sys.stderr)
        return 2
    if args.pilot and args.live and args.memory_prereqs is None:
        print("refusing: --pilot --live requires --memory-prereqs none or matched", file=sys.stderr)
        return 2
    memory_prereqs = args.memory_prereqs or ("none" if args.pilot else "all")
    reused = refuse_reuse(args.out)
    if reused:
        print(f"refusing: {reused}; use a new --out directory", file=sys.stderr)
        return 2
    cases = _select_cases(args.pilot, memory_prereqs)
    if not args.live:
        write_plan(cases, args.out, pilot=args.pilot, thinking_modes=modes)
        print(f"wrote dry plan {args.out / 'run.json'}")
        return 0
    slots = build_slots(cases, modes)
    problems = preflight(cases, slots, bfcl_root=args.bfcl_root)
    if problems:
        for problem in problems:
            print(f"refusing before any request: {problem}", file=sys.stderr)
        return 2
    executor = None
    if any(slot["kind"] == "trajectory" for slot in slots):
        try:
            package = resolve_bfcl_package(args.bfcl_root)
            executor = OfficialBfclExecutor(package, "deepseek_flash")
        except (FileNotFoundError, ImportError) as exc:
            print(f"refusing before any request: {exc}", file=sys.stderr)
            return 2
    # Key read and socket use happen only after the checks above.
    transport = authorized_transport()
    try:
        result = execute(
            cases,
            slots,
            args.out,
            transport,
            ceiling_usd=ceiling,
            thinking_modes=modes,
            executor=executor,
            identity=run_identity(cases, pilot=args.pilot, memory_prereqs=memory_prereqs),
        )
    except RunStopped as stopped:
        print(f"refusing before any request: {stopped.reason}", file=sys.stderr)
        return 2
    print(json.dumps({
        "complete": result["complete"],
        "status": result["status"],
        "reason": result["reason"],
        "running_usd": result["running_usd"],
        "uncertain_attempts": result.get("uncertain_attempts", []),
    }, sort_keys=True))
    return 0 if result["complete"] else 1


def run_identity(cases: list[dict], *, pilot: bool, memory_prereqs: str) -> dict:
    """What makes the pilot and the full run the same pipeline on different case lists."""
    from tool_compression.clean_start.editor_s import S_RULES_VERSION
    from tool_compression.clean_start.editor_x import X_RULES_VERSION

    identity = {
        "study": STUDY_ID,
        "pilot": pilot,
        "memory_prereqs": memory_prereqs,
        "case_count": len(cases),
        "prereq_count": sum(1 for case in cases if case.get("prereq")),
        "case_ids_sha256": sha256(json.dumps([case["id"] for case in cases]).encode("utf-8")).hexdigest(),
        "editor_rules": {"S": S_RULES_VERSION, "X": X_RULES_VERSION},
        "runner": "tool_compression.clean_start.runner.execute",
    }
    if pilot:
        draw = study_dir() / "pilot" / "draw.json"
        identity["draw_sha256"] = sha256(draw.read_bytes()).hexdigest()
    return identity


def _select_cases(pilot: bool, memory_prereqs: str = "none") -> list[dict]:
    """Full run, or the frozen pilot draw.

    ``matched`` puts, before each drawn memory category, the prerequisite
    conversations of the scenarios its drawn questions use, in loader order.
    The drawn questions themselves never change.
    """
    if not pilot:
        return select_full_run_cases()
    if memory_prereqs not in {"none", "matched"}:
        raise ValueError(memory_prereqs)
    draw = build_draw()
    committed = json.loads((study_dir() / "pilot" / "draw.json").read_text(encoding="utf-8"))
    if committed != draw:
        raise RuntimeError("pilot draw differs from the committed pilot/draw.json")
    wanted = [(row["category"], row["case_id"]) for row in draw["rows"]]
    by_id = {
        (category, case["id"]): case
        for category in study_categories()
        for case in in_scope_questions(category)
    }
    chosen = []
    for key in wanted:
        case = by_id.get(key)
        if case is None:
            raise RuntimeError("pilot draw does not match the in-scope questions")
        chosen.append(case)
    if len(chosen) != len(wanted):
        raise RuntimeError("pilot draw does not match the in-scope questions")
    if memory_prereqs == "none":
        return chosen
    from tool_compression.clean_start.load import load_prereqs

    ordered: list[dict] = []
    seen: set[str] = set()
    for case in chosen:
        category = case["category"]
        if case.get("scenario") is not None and category.startswith("memory_") and category not in seen:
            seen.add(category)
            scenarios = {item["scenario"] for item in chosen if item["category"] == category}
            ordered.extend(item for item in load_prereqs(category) if item["scenario"] in scenarios)
        ordered.append(case)
    return ordered


def _study_dir() -> Path:
    return study_dir()


if __name__ == "__main__":
    raise SystemExit(main())
