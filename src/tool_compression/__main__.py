"""Preparation commands and official scoring from saved outputs. No model calls."""

from pathlib import Path
import argparse
import importlib.util
import json
import subprocess
import sys

from tool_compression.accounting import contrast_usage_accounting, locked_usage_issues
from tool_compression.analysis import class_join_issues, join_cases, load_recorded_join, uncertainty_analysis
from tool_compression.artifacts import verify_manifest, write_manifest
from tool_compression.characterize import characterize_study, file_sha256
from tool_compression.config import DEFAULT_CONFIG
from tool_compression.count import study_counters
from tool_compression.evaluation import evaluation_manifest, summarize_hash_rows
from tool_compression.external import public_report, run_arm_e
from tool_compression.followon_bind import reproduce_historical_official_counts
from tool_compression.followon_report import verify_followon_manifest, write_package
from tool_compression.load import STUDY_CATEGORIES, VERSION_PREFIX, load_study, resolve_data_dir
from tool_compression.official_score import (
    ScoringAliasGenerateRefused,
    build_bfcl_argv,
    guard_bfcl_argv,
    locked_settlement_issues,
    map_saved_outputs,
    settle_from_saved,
)
from tool_compression.overhead import exercise_record
from tool_compression.packet import shared_request_groups, write_packet
from tool_compression.publish import dump_jsonl, dump_public
from tool_compression.suffix import float_suffix_report

BFCL_REPOSITORY = "https://github.com/ShishirPatil/gorilla"
TSCG_REPOSITORY = "https://github.com/SKZL-AI/tscg"
BFCL_SOURCES = (
    "bfcl_eval/constants/category_mapping.py",
    "bfcl_eval/constants/type_mappings.py",
    "bfcl_eval/model_handler/api_inference/openai_completion.py",
    "bfcl_eval/model_handler/utils.py",
    "bfcl_eval/model_handler/base_handler.py",
    "bfcl_eval/eval_checker/ast_eval/ast_checker.py",
    "bfcl_eval/eval_checker/eval_runner.py",
    "bfcl_eval/__main__.py",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tool-compression")
    sub = parser.add_subparsers(dest="command", required=True)

    characterize = sub.add_parser("characterize")
    characterize.add_argument("--bfcl-root", required=True, type=Path)
    characterize.add_argument("--out", required=True, type=Path)
    characterize.add_argument("--hashes", type=Path)

    arm_e = sub.add_parser("arm-e")
    arm_e.add_argument("--bfcl-root", required=True, type=Path)
    arm_e.add_argument("--tscg-root", required=True, type=Path)
    arm_e.add_argument("--out", required=True, type=Path)
    arm_e.add_argument("--hashes", type=Path)
    arm_e.add_argument("--script", type=Path, default=_default_script())

    packet = sub.add_parser("packet")
    packet.add_argument("--characterization", required=True, type=Path)
    packet.add_argument("--arm-e", required=True, type=Path)
    packet.add_argument("--out", required=True, type=Path)

    sub.add_parser("manifest")
    sub.add_parser("inspect-suffix")
    groups = sub.add_parser("groups")
    groups.add_argument("--local", type=Path)
    groups.add_argument("--arm-e", type=Path)
    groups.add_argument("--out", type=Path)

    official_map = sub.add_parser("official-map")
    official_map.add_argument("--stage-b", required=True, type=Path)
    official_map.add_argument("--out", required=True, type=Path)
    official_map.add_argument("--expected-groups", type=int)

    official_settle = sub.add_parser("official-settle")
    official_settle.add_argument("--score-root", required=True, type=Path)
    official_settle.add_argument("--mapping", required=True, type=Path)
    official_settle.add_argument("--out", required=True, type=Path)
    official_settle.add_argument("--execution-record", type=Path)

    official_guard = sub.add_parser("official-guard")
    official_guard.add_argument("--action", required=True, choices=("evaluate", "generate"))
    official_guard.add_argument("--model", required=True)
    official_guard.add_argument("--test-category", default="simple_python,multiple,irrelevance")
    official_guard.add_argument("--result-dir", default="result_u")
    official_guard.add_argument("--score-dir", default="score_u")
    official_guard.add_argument("--bfcl", default="bfcl")

    sub.add_parser("official-check")

    artifact = sub.add_parser("artifact-manifest")
    artifact.add_argument("--out", type=Path)
    artifact.add_argument("--check", type=Path)

    timing = sub.add_parser("time-preprocessing")
    timing.add_argument("--out", type=Path)
    timing.add_argument("--repeats", type=int, default=5)
    timing.add_argument("--catalogues", type=int, default=48)

    followon = sub.add_parser("followon-audit")
    followon.add_argument("--bfcl-root", required=True, type=Path)
    followon.add_argument("--out", type=Path)

    followon_manifest = sub.add_parser("followon-manifest")
    followon_manifest.add_argument("--check", type=Path)

    sub.add_parser("followon-historical")

    join = sub.add_parser("join-outcomes")
    join.add_argument("--rows", required=True, type=Path)
    join.add_argument("--out", type=Path)

    args = parser.parse_args(argv)
    if args.command == "characterize":
        return _characterize(args)
    if args.command == "arm-e":
        return _arm_e(args)
    if args.command == "packet":
        return _packet(args)
    if args.command == "manifest":
        return _manifest()
    if args.command == "inspect-suffix":
        return _inspect_suffix()
    if args.command == "groups":
        return _groups(args)
    if args.command == "official-map":
        return _official_map(args)
    if args.command == "official-settle":
        return _official_settle(args)
    if args.command == "official-guard":
        return _official_guard(args)
    if args.command == "official-check":
        return _official_check()
    if args.command == "artifact-manifest":
        return _artifact_manifest(args)
    if args.command == "time-preprocessing":
        return _time_preprocessing(args)
    if args.command == "followon-audit":
        return _followon_audit(args)
    if args.command == "followon-manifest":
        return _followon_manifest(args)
    if args.command == "followon-historical":
        return _followon_historical()
    if args.command == "join-outcomes":
        return _join_outcomes(args)
    return 2


def _characterize(args) -> int:
    budget, sensitivity = study_counters()
    study = load_study(args.bfcl_root)
    payload, rows = characterize_study(study, budget, sensitivity, DEFAULT_CONFIG)
    payload["provenance"] = _provenance(args.bfcl_root)
    payload["source_documents"] = _source_documents()
    parity = _conversion_parity(args.bfcl_root)
    if parity is not None:
        payload["conversion_parity"] = parity
    dump_public(args.out, payload)
    dump_jsonl(args.hashes or args.out.with_name("week1_request_hashes.jsonl"), rows)
    print(f"wrote {args.out}")
    return 0


def _arm_e(args) -> int:
    budget, sensitivity = study_counters()
    study = load_study(args.bfcl_root)
    report = run_arm_e(study, args.tscg_root, args.script, budget, sensitivity)
    rows = [
        {key: value for key, value in row.items() if key != "tools"}
        for row in report.get("rows", [])
    ]
    public = public_report(report)
    public["provenance"] = _provenance(args.bfcl_root)
    public["tscg"] = _tscg_pin(args.tscg_root)
    public["source_documents"] = _source_documents()
    dump_public(args.out, public)
    dump_jsonl(args.hashes or args.out.with_name("week1_arm_e_hashes.jsonl"), rows)
    print(f"wrote {args.out} boundary_compatible={public['boundary_compatible']}")
    return 0


def _packet(args) -> int:
    characterization = json.loads(args.characterization.read_text(encoding="utf-8"))
    arm_e = json.loads(args.arm_e.read_text(encoding="utf-8"))
    local_rows = _read_jsonl(args.characterization.with_name("week1_request_hashes.jsonl"))
    arm_rows = _read_jsonl(args.arm_e.with_name("week1_arm_e_hashes.jsonl"))
    if local_rows and arm_rows:
        arm_e["shared_request_groups"] = shared_request_groups(local_rows, arm_rows)
        dump_public(args.arm_e, arm_e)
    write_packet(args.out, characterization, arm_e)
    print(f"wrote {args.out}")
    return 0


def _manifest() -> int:
    print(json.dumps(evaluation_manifest(), indent=2, sort_keys=True))
    return 0


def _inspect_suffix() -> int:
    print(json.dumps(float_suffix_report(), indent=2, sort_keys=True))
    return 0


def _official_map(args) -> int:
    summary = map_saved_outputs(
        args.stage_b,
        args.out,
        expected_groups=args.expected_groups,
    )
    print(json.dumps({"ok": summary["ok"], "mapping": summary["mapping"]}, indent=2))
    return 0


def _official_settle(args) -> int:
    record = None
    if args.execution_record is not None:
        record = json.loads(args.execution_record.read_text(encoding="utf-8"))
    payload = settle_from_saved(args.score_root, args.mapping, execution_record=record)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


def _official_guard(args) -> int:
    try:
        if args.action == "generate":
            guard_bfcl_argv(["bfcl", "generate", "--model", args.model])
        argv = build_bfcl_argv(
            args.action,
            model=args.model,
            test_category=args.test_category,
            result_dir=args.result_dir,
            score_dir=args.score_dir,
            bfcl=args.bfcl,
        )
    except ScoringAliasGenerateRefused as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps({"allowed": True, "argv": argv}))
    return 0


def _official_check() -> int:
    root = _repo_root()
    settlement = json.loads((root / "official" / "settlement" / "official_settlement.json").read_text(encoding="utf-8"))
    usage = json.loads((root / "official" / "tables" / "usage_accounting.json").read_text(encoding="utf-8"))
    recorded = load_recorded_join(root / "official" / "tables" / "change_class_join.json")
    characterization = json.loads((root / "evidence" / "week1_characterization.json").read_text(encoding="utf-8"))
    manifest_path = root / "official" / "artifact_manifest.json"
    issues = []
    issues.extend(f"settlement: {item}" for item in locked_settlement_issues(settlement))
    issues.extend(f"usage: {item}" for item in locked_usage_issues(usage))
    issues.extend(f"join: {item}" for item in class_join_issues(characterization, settlement, recorded))
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        issues.extend(f"manifest: {item}" for item in verify_manifest(manifest, root))
    else:
        issues.append("manifest: artifact_manifest.json is missing")
    uncertainty = uncertainty_analysis(settlement)
    payload = {
        "ok": not issues,
        "issues": issues,
        "primary_target_reached": settlement["reference_target_L_represents_C"]["combine_targets"]["target_reached"],
        "statistical_non_inferiority": uncertainty["statistical_non_inferiority"],
        "price_weighted_is_study_statistic": contrast_usage_accounting(usage)["price_weighted_input_is_study_statistic"],
    }
    print(json.dumps(payload, indent=2))
    return 0 if not issues else 1


def _artifact_manifest(args) -> int:
    root = _repo_root()
    if args.check is not None:
        manifest = json.loads(args.check.read_text(encoding="utf-8"))
        issues = verify_manifest(manifest, root)
        print(json.dumps({"ok": not issues, "issues": issues}, indent=2))
        return 0 if not issues else 1
    destination = args.out or root / "official" / "artifact_manifest.json"
    write_manifest(destination, root)
    print(f"wrote {destination}")
    return 0


def _time_preprocessing(args) -> int:
    counter, _sensitivity = study_counters()
    payload = exercise_record(counter, n=args.catalogues, repeats=args.repeats)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(json.dumps(payload, indent=2))
    return 0


def _followon_audit(args) -> int:
    root = _repo_root()
    destination = args.out or root / "followon"
    summary = write_package(root, args.bfcl_root, destination)
    print(
        json.dumps(
            {
                "ready_for_evaluation": summary["ready_for_evaluation"],
                "measured": summary["measured"],
                "defects": summary["implementation_defects"],
                "primary_f_new": summary["categories"]["multiple"]["f_new"],
                "out": str(destination),
            },
            indent=2,
        )
    )
    return 0 if summary["ready_for_evaluation"] else 1


def _followon_manifest(args) -> int:
    root = _repo_root()
    path = args.check or root / "followon" / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    issues = verify_followon_manifest(manifest, root)
    print(json.dumps({"ok": not issues, "issues": issues}, indent=2))
    return 0 if not issues else 1


def _followon_historical() -> int:
    payload = reproduce_historical_official_counts(_repo_root())
    print(json.dumps({"ok": payload["ok"], "target_reached": payload["target_reached"], "network_used": False, "categories": payload["categories"]}, indent=2))
    return 0 if payload["ok"] else 1


def _join_outcomes(args) -> int:
    rows = [json.loads(line) for line in args.rows.read_text(encoding="utf-8").splitlines() if line.strip()]
    payload = join_cases(rows)
    if args.out is not None:
        args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(json.dumps(payload, indent=2))
    return 0 if not payload["issues"] else 1


def _groups(args) -> int:
    root = _repo_root()
    local_path = args.local or root / "evidence" / "week1_request_hashes.jsonl"
    arm_path = args.arm_e or root / "evidence" / "week1_arm_e_hashes.jsonl"
    summary = summarize_hash_rows(_read_jsonl(local_path), _read_jsonl(arm_path))
    if args.out:
        dump_public(args.out, summary)
        print(f"wrote {args.out}")
    else:
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _provenance(bfcl_root: Path) -> dict:
    package = _bfcl_package(bfcl_root)
    data_dir = resolve_data_dir(bfcl_root)
    return {
        "bfcl_repository": BFCL_REPOSITORY,
        "bfcl_commit": _git_commit(package),
        "version_prefix": VERSION_PREFIX,
        "categories": list(STUDY_CATEGORIES),
        "handler": "OpenAICompletionsHandler._query_FC",
        "conversion": "convert_to_tool(..., GORILLA_TO_OPENAPI, OPENAI_COMPLETIONS)",
        "data_files": {
            f"{VERSION_PREFIX}_{category}.json": file_sha256(data_dir / f"{VERSION_PREFIX}_{category}.json")
            for category in STUDY_CATEGORIES
        },
        "source_files": {
            relative: file_sha256(package / relative)
            for relative in BFCL_SOURCES
            if (package / relative).is_file()
        },
    }


def _tscg_pin(tscg_root: Path) -> dict:
    package_json = Path(tscg_root) / "packages" / "core" / "package.json"
    version = json.loads(package_json.read_text(encoding="utf-8"))["version"]
    return {
        "repository": TSCG_REPOSITORY,
        "commit": _git_commit(tscg_root),
        "package": "@tscg/core",
        "version": version,
        "entrypoint": "packages/core/src/index.ts compressDescriptions",
        "options": None,
    }


def _source_documents() -> dict:
    root = _repo_root()
    revised = root / "Controlled_Tool_Description_Compression_Proposal_Revised.tex"
    plan = root / "Controlled_Tool_Description_Compression_Agent_Plan.md"
    unrevised = root / "Controlled_Tool_Description_Compression_Proposal.tex"
    return {
        "revised_proposal_present": revised.is_file(),
        "agent_plan_present": plan.is_file(),
        "unrevised_proposal_named_by_plan_present": unrevised.is_file(),
        "revised_proposal_sha256": file_sha256(revised) if revised.is_file() else None,
        "agent_plan_sha256": file_sha256(plan) if plan.is_file() else None,
        "conflict_rule": (
            "The plan names Controlled_Tool_Description_Compression_Proposal.tex. "
            "The revised proposal is the source of truth."
        ),
    }


def _conversion_parity(bfcl_root: Path) -> dict | None:
    package = _bfcl_package(bfcl_root)
    utils = package / "bfcl_eval" / "model_handler" / "utils.py"
    script = _default_script().with_name("check_conversion_parity.py")
    if not utils.is_file() or not script.is_file():
        return None
    spec = importlib.util.spec_from_file_location("conversion_parity", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.summarize(bfcl_root, utils)


def _bfcl_package(root: Path) -> Path:
    for candidate in (root, root / "berkeley-function-call-leaderboard"):
        if (candidate / "bfcl_eval" / "model_handler" / "utils.py").is_file():
            return candidate
    raise FileNotFoundError(f"bfcl_eval package not found under {root}")


def _git_commit(path: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return "unknown"
    return completed.stdout.strip()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_script() -> Path:
    return _repo_root() / "scripts" / "tscg_compress_descriptions.mjs"


if __name__ == "__main__":
    sys.exit(main())
