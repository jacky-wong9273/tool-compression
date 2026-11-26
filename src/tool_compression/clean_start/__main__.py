"""CLI for the clean-start study. The default path does not contact a provider."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from tool_compression.clean_start.pilot import build_draw, freeze, study_dir
from tool_compression.clean_start.pin import STUDY_ID, study_manifest
from tool_compression.clean_start.runner import (
    FULL_FLY_POLICY,
    RETRY_LIMIT,
    OfficialBfclExecutor,
    RunStopped,
    authorized_transport,
    build_slots,
    execute,
    parse_thinking_modes,
    plan_summary,
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
    validation_report = sub.add_parser("report-validation", help="the interrupted 0bf829c6 validation flight")
    validation_report.add_argument("--evidence", type=Path)
    validation_report.add_argument("--out", type=Path)
    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("--out", required=True, type=Path)
    evaluate.add_argument("--bfcl-root", required=True, type=Path)
    evaluate.add_argument("--thinking", required=True)

    run = sub.add_parser("run")
    run.add_argument("--out", required=True, type=Path)
    run.add_argument("--pilot", action="store_true")
    run.add_argument("--validation", action="store_true", help="the fresh validation draw, thinking off")
    run.add_argument(
        "--preliminary",
        action="store_true",
        help="the 20% preliminary draw, thinking off, $42 ceiling",
    )
    run.add_argument(
        "--full",
        action="store_true",
        help="the full in-scope catalogue, thinking off, 12,952 slots: 20 s first deadline, "
        "one 60 s retry, then the slot is skipped and recorded in failures.jsonl",
    )
    run.add_argument("--live", action="store_true")
    run.add_argument("--authorize-live", action="store_true")
    run.add_argument("--thinking", help="off, on, or off,on; required with --live")
    run.add_argument(
        "--memory-prereqs",
        choices=("none", "matched"),
        help="required with --pilot --live, with --validation, with --preliminary, and with --full: "
        "none, or the prerequisite conversations of the scenarios the drawn questions use",
    )
    run.add_argument("--ceiling-usd", type=str)
    run.add_argument("--bfcl-root", type=Path)
    run.add_argument(
        "--resume",
        action="store_true",
        help="--preliminary or --full: continue the stopped run in --out. Finished and skipped "
        "slots are not sent again, the stopped slot is sent again from its start, and recorded "
        "spend counts against the same ceiling. Without --live it only reports what a resume "
        "would do.",
    )

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
    if args.command == "report-validation":
        from tool_compression.clean_start.report import VALIDATION_EVIDENCE, write_validation_flight_report

        summary = write_validation_flight_report(
            args.evidence or study_dir() / VALIDATION_EVIDENCE,
            args.out or study_dir() / "package" / "validation_2026_11_25_analysis.json",
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
    if sum((args.pilot, args.validation, args.preliminary, args.full)) > 1:
        print("refusing: --pilot, --validation, --preliminary, and --full are different draws", file=sys.stderr)
        return 2
    if args.memory_prereqs and not (args.pilot or args.validation or args.preliminary or args.full):
        print(
            "refusing: --memory-prereqs applies to --pilot, --validation, --preliminary, or --full",
            file=sys.stderr,
        )
        return 2
    if args.pilot and args.live and args.memory_prereqs is None:
        print("refusing: --pilot --live requires --memory-prereqs none or matched", file=sys.stderr)
        return 2
    if args.validation:
        if modes != ("off",):
            print("refusing: --validation is thinking off only", file=sys.stderr)
            return 2
        if args.memory_prereqs != "matched":
            print("refusing: --validation requires --memory-prereqs matched", file=sys.stderr)
            return 2
        if args.ceiling_usd is None:
            print("refusing: --validation requires --ceiling-usd", file=sys.stderr)
            return 2
        ceiling = Decimal(args.ceiling_usd)
        if ceiling <= 0:
            print("refusing: --ceiling-usd must be greater than 0", file=sys.stderr)
            return 2
    if args.preliminary:
        if modes != ("off",):
            print("refusing: --preliminary is thinking off only", file=sys.stderr)
            return 2
        if args.memory_prereqs != "matched":
            print("refusing: --preliminary requires --memory-prereqs matched", file=sys.stderr)
            return 2
        if args.ceiling_usd is None:
            print("refusing: --preliminary requires --ceiling-usd", file=sys.stderr)
            return 2
        ceiling = Decimal(args.ceiling_usd)
        if ceiling <= 0:
            print("refusing: --ceiling-usd must be greater than 0", file=sys.stderr)
            return 2
        from tool_compression.clean_start.preliminary import CEILING_USD

        if ceiling != CEILING_USD:
            if ceiling > CEILING_USD:
                print(
                    f"refusing: --preliminary ceiling ${ceiling} exceeds the 280 CNY cap of ${CEILING_USD}",
                    file=sys.stderr,
                )
            else:
                print(
                    f"refusing: --preliminary ceiling ${ceiling} is not the authorized ${CEILING_USD} cap",
                    file=sys.stderr,
                )
            return 2
    if args.full:
        if modes != ("off",):
            print("refusing: --full is thinking off only", file=sys.stderr)
            return 2
        if args.memory_prereqs != "matched":
            print("refusing: --full requires --memory-prereqs matched", file=sys.stderr)
            return 2
        if args.ceiling_usd is None:
            print("refusing: --full requires --ceiling-usd; Jacky names the full-fly ceiling", file=sys.stderr)
            return 2
        ceiling = Decimal(args.ceiling_usd)
        if ceiling <= 0:
            print("refusing: --ceiling-usd must be greater than 0", file=sys.stderr)
            return 2
    if args.resume and not (args.preliminary or args.full):
        print("refusing: --resume applies to --preliminary or --full only", file=sys.stderr)
        return 2
    memory_prereqs = args.memory_prereqs or (
        "none" if args.pilot or args.validation or args.preliminary else "all"
    )
    if not args.resume:
        reused = refuse_reuse(args.out)
        if reused:
            print(
                f"refusing: {reused}; use a new --out directory, or --resume to continue that run",
                file=sys.stderr,
            )
            return 2
    if args.validation:
        from tool_compression.clean_start.validation import load_committed_cost, select_validation_cases

        try:
            cost = load_committed_cost()
            cases = select_validation_cases()
        except RuntimeError as exc:
            print(f"refusing: {exc}", file=sys.stderr)
            return 2
        upper = Decimal(cost["planning_upper_usd"])
        if ceiling < upper:
            print(
                f"refusing: validation planning upper ${upper} exceeds ceiling ${ceiling}",
                file=sys.stderr,
            )
            return 2
    elif args.preliminary:
        from tool_compression.clean_start.preliminary import (
            COMMITTED_SLOT_SHA256,
            load_committed_cost,
            select_preliminary_cases,
        )

        try:
            cost = load_committed_cost()
            cases = select_preliminary_cases()
        except RuntimeError as exc:
            print(f"refusing: {exc}", file=sys.stderr)
            return 2
        # The allowance upper is above the $42 ceiling on purpose and is not
        # compared with it. The ceiling has to cover the observed-mean path
        # with its Friday-peak slice billed at double.
        peaked = Decimal(cost["observed_mean_with_friday_peak_usd"])
        if ceiling < peaked:
            print(
                f"refusing: observed-mean path with the Friday peak ${peaked} exceeds ceiling ${ceiling}",
                file=sys.stderr,
            )
            return 2
        if plan_summary(build_slots(cases, modes), modes)["slot_sha256"] != COMMITTED_SLOT_SHA256:
            print("refusing: preliminary slot order is not the committed thinking-off order", file=sys.stderr)
            return 2
    elif args.full:
        from tool_compression.clean_start import full

        try:
            cost = full.load_committed_cost()
            cases = full.select_full_cases()
        except RuntimeError as exc:
            print(f"refusing: {exc}", file=sys.stderr)
            return 2
        floor = Decimal(cost["ceiling_floor_usd"])
        if ceiling < floor:
            print(
                f"refusing: --full ceiling ${ceiling} is under the ${floor} floor "
                f"({cost['ceiling_floor_profile']} with its peak premium and hung tries); "
                "the fly would stop before the observed-mean path finishes",
                file=sys.stderr,
            )
            return 2
        if plan_summary(build_slots(cases, modes), modes)["slot_sha256"] != full.COMMITTED_SLOT_SHA256:
            print("refusing: full slot order is not the committed thinking-off order", file=sys.stderr)
            return 2
        if args.live:
            problems = full.start_gate(_now(), resume=args.resume)
            if problems:
                for problem in problems:
                    print(f"refusing before any request: {problem}", file=sys.stderr)
                return 2
    else:
        cost = None
        cases = _select_cases(args.pilot, memory_prereqs)
        if args.live and not args.pilot:
            covered = {case["id"] for case in cases}
            if covered >= {case["id"] for case in select_full_run_cases()}:
                print(
                    "refusing: the full catalogue flies only with --full (20 s / 60 s deadlines, "
                    "skip-and-record, --resume, thinking off)",
                    file=sys.stderr,
                )
                return 2
    identity = run_identity(
        cases,
        pilot=args.pilot,
        memory_prereqs=memory_prereqs,
        validation=args.validation,
        preliminary=args.preliminary,
        full=args.full,
        cost=cost,
    )
    if args.resume:
        from tool_compression.clean_start.resume import describe, inspect_resume

        try:
            plan = inspect_resume(
                args.out, cases, build_slots(cases, modes),
                identity=identity, ceiling_usd=ceiling, thinking_modes=modes,
            )
        except RunStopped as stopped:
            print(f"refusing to resume: {stopped.reason}", file=sys.stderr)
            return 2
        if not args.live:
            print(json.dumps({"resume_check": True, "provider_contacted": False, **describe(plan)}, sort_keys=True))
            return 0
    if not args.live:
        extra = None
        if args.validation:
            extra = {
                "validation": True,
                "replicate_u": False,
                "memory_prereqs": "matched",
                "planning_upper_usd": cost["planning_upper_usd"],
                "first_request_floor_usd": cost["first_request_floor_usd"],
                "structural_cap_usd": cost["structural_cap_usd"],
            }
        if args.preliminary:
            extra = {
                "preliminary": True,
                "replicate_u": False,
                "memory_prereqs": "matched",
                "planning_upper_usd": cost["planning_upper_usd"],
                "first_request_floor_usd": cost["first_request_floor_usd"],
                "structural_cap_usd": cost["structural_cap_usd"],
                "fraction": cost["fraction"],
            }
        if args.full:
            extra = {
                "full": True,
                "replicate_u": False,
                "memory_prereqs": "matched",
                "observed_mean_usd": cost["observed_mean_usd"],
                "planning_upper_usd": cost["planning_upper_usd"],
                "ceiling_floor_usd": cost["ceiling_floor_usd"],
                "not_before_hkt": cost["not_before_hkt"],
                "retry_policy": FULL_FLY_POLICY.describe(),
                "read_timeout_seconds": FULL_FLY_POLICY.describe()["read_timeout_seconds"],
                "total_deadline_seconds": FULL_FLY_POLICY.describe()["total_deadline_seconds"],
            }
        write_plan(
            cases,
            args.out,
            pilot=args.pilot,
            thinking_modes=modes,
            ceiling_usd=str(ceiling) if args.validation or args.full else None,
            extra=extra,
        )
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
            identity=identity,
            resume=args.resume,
            retry_limit=RETRY_LIMIT if args.preliminary else 0,
            policy=FULL_FLY_POLICY if args.full else None,
        )
    except RunStopped as stopped:
        print(f"refusing before any request: {stopped.reason}", file=sys.stderr)
        return 2
    print(json.dumps({
        "complete": result["complete"],
        "status": result["status"],
        "reason": result["reason"],
        "running_usd": result["running_usd"],
        "session": result.get("session"),
        "slots_sent": result.get("slots_sent"),
        "slots_skipped": result.get("slots_skipped", 0),
        "slots_total": result.get("slots_total"),
        "tokens": result.get("tokens"),
        "uncertain_attempts": result.get("uncertain_attempts", []),
        "unbilled_attempts": len(result.get("unbilled_attempts", [])),
    }, sort_keys=True))
    return 0 if result["complete"] else 1


def _now() -> datetime:
    return datetime.now(timezone.utc)


def run_identity(
    cases: list[dict],
    *,
    pilot: bool,
    memory_prereqs: str,
    validation: bool = False,
    preliminary: bool = False,
    full: bool = False,
    cost: dict | None = None,
) -> dict:
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
    if validation:
        from tool_compression.clean_start.validation import DRAW_FILE

        identity["validation"] = True
        identity["replicate_u"] = False
        identity["draw_sha256"] = sha256((study_dir() / DRAW_FILE).read_bytes()).hexdigest()
        if cost is not None:
            identity["planning_upper_usd"] = cost["planning_upper_usd"]
            identity["first_request_floor_usd"] = cost["first_request_floor_usd"]
    if preliminary:
        from tool_compression.clean_start.preliminary import DRAW_FILE
        from tool_compression.clean_start.resume import source_sha256

        identity["preliminary"] = True
        identity["replicate_u"] = False
        identity["draw_sha256"] = sha256((study_dir() / DRAW_FILE).read_bytes()).hexdigest()
        identity["source_sha256"] = source_sha256()
        if cost is not None:
            identity["planning_upper_usd"] = cost["planning_upper_usd"]
            identity["first_request_floor_usd"] = cost["first_request_floor_usd"]
    if full:
        from tool_compression.clean_start.full import PLAN_FILE
        from tool_compression.clean_start.resume import source_sha256

        identity["full"] = True
        identity["replicate_u"] = False
        identity["draw_sha256"] = sha256((study_dir() / PLAN_FILE).read_bytes()).hexdigest()
        identity["source_sha256"] = source_sha256()
        identity["retry_policy"] = FULL_FLY_POLICY.name
        identity["attempt_deadlines_seconds"] = list(FULL_FLY_POLICY.attempt_deadlines)
        if cost is not None:
            identity["planning_upper_usd"] = cost["planning_upper_usd"]
            identity["ceiling_floor_usd"] = cost["ceiling_floor_usd"]
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
