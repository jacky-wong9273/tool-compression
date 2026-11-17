"""Week 1 preparation commands, plus an opt-in validation flight.

The preparation commands do not call a model. ``validate-flight`` calls
DeepSeek only when ``--no-api`` is absent. The key is read from the
environment variable ``DEEPSEEK_API_KEY`` and is never a flag or a file.
"""

from pathlib import Path
import argparse
import importlib.util
import json
import os
import subprocess
import sys

from tool_compression.characterize import characterize_study, file_sha256
from tool_compression.config import DEFAULT_CONFIG
from tool_compression.count import study_counters
from tool_compression.evaluation import (
    PaidInferenceRefused,
    assert_inference_allowed,
    evaluation_manifest,
    freeze_execution_record,
    summarize_hash_rows,
)
from tool_compression.flight_spec import validation_flight_record
from tool_compression.provider import MissingApiKey, scrub
from tool_compression.runner import (
    attach_provisional,
    load_cases_file,
    prepare_study_cases,
    read_hash_rows,
    run_validation_flight,
    select_prepared_sample,
    select_validation_sample,
)
from tool_compression.external import public_report, run_arm_e
from tool_compression.load import STUDY_CATEGORIES, VERSION_PREFIX, load_study, resolve_data_dir
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

    freeze = sub.add_parser(
        "freeze-record",
        help="Write the frozen validation-flight execution record. Does not call a provider.",
    )
    freeze.add_argument("--out", required=True, type=Path)

    flight = sub.add_parser(
        "validate-flight",
        help=(
            "Run the validation-and-prep flight. Stage B starts only after stage A validates. "
            "This is not an official settlement. Pass --no-api to avoid the network."
        ),
    )
    flight.add_argument("--record", required=True, type=Path)
    flight.add_argument("--out", required=True, type=Path)
    flight.add_argument("--bfcl-root", type=Path)
    flight.add_argument("--tscg-root", type=Path)
    flight.add_argument("--cases", type=Path, help="Prepared cases for a --no-api harness run.")
    flight.add_argument("--local-hashes", type=Path)
    flight.add_argument("--arm-e-hashes", type=Path)
    flight.add_argument("--no-api", action="store_true", help="Do not call DeepSeek and do not read an API key.")
    flight.add_argument("--stage", choices=("all", "a", "b"), default="all")

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
    if args.command == "freeze-record":
        return _freeze_record(args)
    if args.command == "validate-flight":
        return _validate_flight(args)
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


def _freeze_record(args) -> int:
    record = freeze_execution_record(validation_flight_record())
    from tool_compression.runner import _write_json

    _write_json(args.out, record, None)
    print(f"wrote {args.out}")
    return 0


def _validate_flight(args) -> int:
    live = not args.no_api
    if args.cases and live:
        print("A --cases file is only for --no-api harness runs.", file=sys.stderr)
        return 2
    if args.cases is None and (args.bfcl_root is None or args.tscg_root is None):
        print("A flight needs --bfcl-root and --tscg-root, or --no-api --cases.", file=sys.stderr)
        return 2
    try:
        record = json.loads(args.record.read_text(encoding="utf-8"))
        assert_inference_allowed(record)
    except (OSError, json.JSONDecodeError, PaidInferenceRefused) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    try:
        if args.cases is not None:
            return _flight_from_cases(args, record, live)
        return _flight_from_study(args, record, live)
    except MissingApiKey as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except PaidInferenceRefused as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        secret = os.environ.get("DEEPSEEK_API_KEY")
        if not secret or not secret.strip():
            secret = None
        print(scrub(str(exc), secret)[:400], file=sys.stderr)
        return 2


def _flight_from_cases(args, record, live: bool) -> int:
    cases = load_cases_file(args.cases)
    if args.stage == "b":
        result = run_validation_flight(record, args.out, cases_b=cases, live=live, stage="b")
        return _flight_status(result)
    sample = select_prepared_sample(cases)
    result = run_validation_flight(record, args.out, cases_a=sample, live=live, stage="a")
    if args.stage == "a" or not result.get("stage_a_validated"):
        return _flight_status(result)
    result = run_validation_flight(record, args.out, cases_b=cases, live=live, stage="b")
    return _flight_status(result)


def _flight_from_study(args, record, live: bool) -> int:
    from tool_compression.load import load_study

    root = _repo_root()
    local_path = args.local_hashes or root / "evidence" / "week1_request_hashes.jsonl"
    arm_path = args.arm_e_hashes or root / "evidence" / "week1_arm_e_hashes.jsonl"
    local_rows = read_hash_rows(local_path)
    arm_rows = read_hash_rows(arm_path)
    script = _default_script()
    study = load_study(args.bfcl_root)
    if args.stage == "b":
        cases = prepare_study_cases(study, args.tscg_root, script, timeout=1800)
        attach_provisional(cases, local_rows, arm_rows)
        result = run_validation_flight(record, args.out, cases_b=cases, live=live, stage="b")
        return _flight_status(result)
    sample = select_validation_sample(local_rows, arm_rows)
    ids = [(item["category"], item["id"]) for item in sample]
    cases_a = prepare_study_cases(study, args.tscg_root, script, ids=ids, timeout=300)
    attach_provisional(cases_a, local_rows, arm_rows)
    result = run_validation_flight(record, args.out, cases_a=cases_a, live=live, stage="a")
    if args.stage == "a" or not result.get("stage_a_validated"):
        return _flight_status(result)
    cases_b = prepare_study_cases(study, args.tscg_root, script, timeout=1800)
    attach_provisional(cases_b, local_rows, arm_rows)
    result = run_validation_flight(record, args.out, cases_b=cases_b, live=live, stage="b")
    return _flight_status(result)


def _flight_status(result: dict) -> int:
    print(
        "purpose=validation-and-prep "
        f"stage_a_validated={result.get('stage_a_validated')} "
        f"stage_b_started={result.get('stage_b_started')} "
        f"stage_b_completed={result.get('stage_b_completed')} "
        f"stop_reason={result.get('stop_reason')} "
        f"target_reached={result.get('target_reached')}"
    )
    return 0 if result.get("ok") else 2


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
