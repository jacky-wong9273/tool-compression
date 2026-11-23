"""Week 1 commands. Preparation only: no model calls and no scoring."""

from datetime import datetime
from pathlib import Path
import argparse
import importlib.util
import json
import subprocess
import sys

from tool_compression.characterize import characterize_study, file_sha256
from tool_compression.config import DEFAULT_CONFIG
from tool_compression.count import study_counters
from tool_compression.evaluation import evaluation_manifest, summarize_hash_rows
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

    sub.add_parser("semantic-audit")
    flight = sub.add_parser("usx-flight")
    flight.add_argument("--bfcl-root", required=True, type=Path)
    flight.add_argument("--out", required=True, type=Path)
    flight.add_argument("--no-api", action="store_true")
    flight.add_argument("--live", action="store_true")
    flight.add_argument("--authorize-peak", action="store_true")

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
    if args.command == "semantic-audit":
        return _semantic_audit()
    if args.command == "usx-flight":
        return _usx_flight(args)
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


def _semantic_audit() -> int:
    from tool_compression.semantic_audit import public_audit_summary

    print(json.dumps(public_audit_summary(), indent=2, sort_keys=True))
    return 0


def _usx_flight(args) -> int:
    """Stage A unless ``--live`` is set. This process does not start a paid call by default."""
    from tool_compression.usx_flight import (
        SHANGHAI,
        UsxFlightRefused,
        read_ceiling_from_env,
        run_live,
        run_no_api_gate,
    )

    if args.live and args.no_api:
        print("pass only one of --live and --no-api")
        return 2
    try:
        ceiling = read_ceiling_from_env()
    except UsxFlightRefused as exc:
        print(str(exc))
        return 2
    def clock():
        return datetime.now(SHANGHAI)

    if not args.live:
        try:
            gate = run_no_api_gate(args.bfcl_root, args.out, ceiling, clock)
        except UsxFlightRefused as exc:
            print(str(exc))
            return 1
        print(json.dumps({
            "stage": gate["stage"],
            "provider_called": gate["provider_called"],
            "api_key_read": gate["api_key_read"],
            "spend_cny": gate["spend_cny"],
            "cases": gate["cases"],
            "unique_payloads": gate["unique_payloads"],
            "schedule_at_gate": gate["schedule_at_gate"],
            "reserve_fits_supplied_ceiling": gate["reserve_fits_supplied_ceiling"],
            "official_settlement": gate["official_settlement"],
        }, sort_keys=True))
        return 0
    if not args.authorize_peak:
        print("refusing --live without --authorize-peak")
        return 2
    try:
        run_live(args.bfcl_root, args.out, ceiling, clock, client=None, authorize_peak=True)
    except UsxFlightRefused as exc:
        print(str(exc))
        return 1
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
