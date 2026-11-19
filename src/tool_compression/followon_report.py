"""Handover, reporting shell, and manifest for the offline follow-on package."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tool_compression.artifacts import sha256_file, verify_manifest
from tool_compression.evaluation import PINS
from tool_compression.followon_config import T1_CONFIG, T2_CONFIG
from tool_compression.load import STUDY_CATEGORIES

BASE_COMMIT = "3a02e64888c5359f48d2b417ac659161cd3eadae"
SCHEMA = "tool-compression.followon-manifest.v1"

PACKAGE_PATHS = (
    "FOLLOWON-SPECIFICATION.md",
    "followon/audit_summary.json",
    "followon/case_hashes.jsonl",
    "followon/field_traces.jsonl",
    "followon/reporting_shell.json",
    "followon/HANDOVER.md",
    "followon/REPORTING.md",
    "src/tool_compression/phrase.py",
    "src/tool_compression/phrase_select.py",
    "src/tool_compression/phrase_compress.py",
    "src/tool_compression/followon_config.py",
    "src/tool_compression/followon_audit.py",
    "src/tool_compression/followon_report.py",
    "src/tool_compression/followon_bind.py",
    "tests/test_followon.py",
)


def reporting_shell(summary: dict, historical: dict) -> dict:
    rows = []
    for category in STUDY_CATEGORIES:
        block = summary["categories"][category]
        for arm in ("U", "T1", "T2"):
            rows.append(
                {
                    "category": category,
                    "arm": arm,
                    "replicate": None,
                    "status": "offline_only",
                    "cases": block["n"],
                    "prepared_cases": block["prepared"],
                    "complete_pairs": None,
                    "changed_requests_vs_U": 0 if arm == "U" else block["changed_cases_vs_U"][arm],
                    "changed_fields_vs_U": 0 if arm == "U" else block["changed_fields_vs_U"][arm],
                    "changed_fields_t2_t1": block["changed_fields_t2_t1"],
                    "f_new_numerator": block["f_new"]["numerator"],
                    "f_new_denominator": block["f_new"]["denominator"],
                    "f_new_unknown": block["f_new"]["unknown"],
                    "request_groups": block["request_groups"],
                    "local_tokens_sum": block["local_tokens"][arm]["sum"],
                    "preprocessing_seconds": block["wall_seconds"],
                    "mean_T": None,
                    "paired_saving": None,
                    "official_correct": None,
                    "official_n": block["n"],
                    "paired_gains": None,
                    "paired_losses": None,
                    "name_hits": None,
                    "abstention_counts": None,
                    "provider_measured": False,
                    "quality_measured": False,
                    "note": "not measured until backed by matched saved responses",
                }
            )
    historical_rows = []
    for category, block in historical["categories"].items():
        for arm in ("U", "L", "E"):
            historical_rows.append(
                {
                    "category": category,
                    "arm": arm,
                    "replicate": "2026-11-18-thinking-off-flash",
                    "status": "historical_recorded",
                    "contemporaneous_comparator_for_followon": False,
                    "official_correct": block["correct"][arm],
                    "official_n": block["n"],
                    "provider_total_input_sum": block["provider_input_sum"][arm],
                    "provider_measured": True,
                    "quality_measured": True,
                    "source": historical["source"],
                }
            )
    return {
        "measured": False,
        "followon_rows": rows,
        "historical_rows_not_comparators": historical_rows,
        "provider_and_quality_cells": "null until matched saved responses exist",
    }


def render_handover(summary: dict, historical: dict) -> str:
    primary = summary["categories"]["multiple"]
    lines = [
        "# Follow-on handover",
        "",
        "This package is ready for a separately authorized evaluation. It is not a measured result. No provider was called, and no price was invented.",
        "",
        "## What is already closed",
        "",
        "Evaluation Protocol v1.1 and the submitted proposal govern the thinking-off Flash reference run only. That run, its hashes, snapshots, and the 10% C-versus-U target stay as recorded. The target was not met: primary L removed "
        f"{historical['categories']['multiple']['saving_numerator_L_vs_U']} of "
        f"{historical['categories']['multiple']['saving_denominator_L_vs_U']} provider input tokens, and official accuracy was U "
        f"{historical['categories']['multiple']['correct']['U']}/200, L "
        f"{historical['categories']['multiple']['correct']['L']}/200, E "
        f"{historical['categories']['multiple']['correct']['E']}/200. "
        "Those thresholds are historical reference, not a reset test for T1 or T2.",
        "",
        "Pull request #4, at `3a02e64888c5359f48d2b417ac659161cd3eadae`, supplied the saved-output scoring package. This branch starts from that commit and does not merge it. `DeepSeek-V3.2-Exp-FC` remains a scoring alias. Generation under that alias is refused because its registry model name is `deepseek-chat`.",
        "",
        "## What these two conditions are",
        "",
        "T1 and T2 are one phrase-level extractive compressor. T1 ranks optional aliases and illustrations with the tool's own identifier overlap. T2 adds `1/2 × q`, the pinned prior neighbour score from `lexical.contrast_q`, on those same pieces. The cap `max(floor(0.75 × d), p)` and the weight `1/2` are new-trial settings. They do not retune `week1.0`.",
        "",
        "The frozen rules are `FOLLOWON-SPECIFICATION.md`. Fixture catalogues are not benchmark rows.",
        "",
        "## Offline audit",
        "",
        f"Ready for evaluation: {str(summary['ready_for_evaluation']).lower()}. Measured: false. Implementation defects: {len(summary['implementation_defects'])}.",
        "",
        f"Primary eligible fields observed {summary['primary_field_inventory']['observed']} against the Week 1 inventory {summary['primary_field_inventory']['week1']} (reconciled: {str(summary['primary_field_inventory']['reconciled']).lower()}).",
        "",
        _funnel_table(primary["funnel"]),
        "",
        _category_table(summary),
        "",
        _stop_table(summary),
        "",
        (
            "Optional fragments marked by the frozen grammar: "
            + ", ".join(
                f"{category} {summary['categories'][category]['optional_fragments']}"
                for category in STUDY_CATEGORIES
            )
            + ". With no optional fragment, no field has two pieces that can compete, so every funnel row is zero. "
            "T1, T2, and U requests were compared as raw JSON. The identical counts above mean there is no request difference on which to score a model. "
            "The grammar and scores were not adjusted to raise these counts."
        ),
        "",
        "Single-tool controls are `simple_python` and `irrelevance`. A T2 versus T1 request difference there is an implementation defect.",
        "",
        "## Scoring path",
        "",
        "Historical official counts were recomputed from `official/settlement/official_settlement.json` with network access unused. "
        f"Reproduction ok: {str(historical['ok']).lower()}. "
        "The raw 18 November flight trees are not in this repository; their manifest digests stay null. The committed settlement is the saved-output reproduction. Archived answers are not attached to T1 or T2. A join fails on duplicate, missing, or hash-mismatched rows.",
        "",
        "Provider input `T`, official accuracy, name hits, and abstention counts for T1 and T2 are unmeasured. The reporting shell leaves those cells null.",
        "",
        "## What a later flight would still need",
        "",
        "A separate authorization would have to freeze the model, thinking-off options, cohort, scorer, grouping, order, cache metadata, retry rule, and a financial ceiling. This package does not supply a price. It does not schedule extra runs of historical L or E.",
        "",
    ]
    if summary["implementation_defects"]:
        lines.extend(["## Defects", "", *[f"- {item}" for item in summary["implementation_defects"]], ""])
    return "\n".join(lines)


def build_followon_manifest(root: Path, summary: dict, input_hashes: dict) -> dict:
    root = Path(root)
    official = root / "official" / "artifact_manifest.json"
    official_issues = []
    if official.is_file():
        official_issues = verify_manifest(json.loads(official.read_text(encoding="utf-8")), root)
    artifacts = []
    for relative in PACKAGE_PATHS:
        path = root / relative
        artifacts.append(
            {
                "path": relative,
                "present": path.is_file(),
                "sha256": sha256_file(path) if path.is_file() else None,
            }
        )
    return {
        "schema": SCHEMA,
        "base_commit": BASE_COMMIT,
        "base_pull_request": "https://github.com/jacky-wong9273/tool-compression/pull/4",
        "spec_version": T1_CONFIG.spec_version,
        "run_identity": "followon.1 offline audit; no measurement flight; model UNSELECTED",
        "pins": dict(PINS),
        "converter": "tool_compression.convert.to_openai_completions_tools",
        "q": "tool_compression.lexical.contrast_q",
        "tokenizer": T1_CONFIG.tokenizer_name,
        "t1": T1_CONFIG.as_dict(),
        "t2": T2_CONFIG.as_dict(),
        "input_sha256": input_hashes,
        "official_manifest_issues": official_issues,
        "official_artifacts_unchanged": not official_issues,
        "closed_target_preserved": True,
        "provider_called": False,
        "ready_for_evaluation": summary["ready_for_evaluation"],
        "artifacts": artifacts,
    }


def verify_followon_manifest(manifest: dict, root: Path) -> list[str]:
    issues = []
    if manifest.get("schema") != SCHEMA:
        issues.append("schema")
    if manifest.get("base_commit") != BASE_COMMIT:
        issues.append("base commit")
    if manifest.get("provider_called") is not False:
        issues.append("provider_called")
    if manifest.get("t2", {}).get("retunes_closed_official_run") is not False:
        issues.append("t2 retune flag")
    for item in manifest.get("artifacts", []):
        path = Path(root) / item["path"]
        if not path.is_file():
            issues.append(f"missing {item['path']}")
            continue
        digest = sha256_file(path)
        if digest != item.get("sha256"):
            issues.append(f"hash {item['path']}")
    return issues


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_package(repo_root: Path, bfcl_root: Path, out_dir: Path) -> dict:
    """Run the offline audit and write the handover package. No network and no model."""
    from tool_compression.count import study_counters
    from tool_compression.followon_audit import audit_study
    from tool_compression.followon_bind import reproduce_historical_official_counts
    from tool_compression.load import VERSION_PREFIX, load_study, resolve_data_dir
    from tool_compression.publish import dump_jsonl, dump_public

    repo_root = Path(repo_root)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    study = load_study(bfcl_root)
    counter, _sensitivity = study_counters()
    audited = audit_study(study, counter)
    data_dir = resolve_data_dir(bfcl_root)
    input_hashes = {
        f"{VERSION_PREFIX}_{category}.json": file_sha256(data_dir / f"{VERSION_PREFIX}_{category}.json")
        for category in STUDY_CATEGORIES
    }
    historical = reproduce_historical_official_counts(repo_root)
    summary = audited["summary"]
    summary["input_sha256"] = input_hashes
    summary["bfcl_commit"] = "6ea57973c7a6097fd7c5915698c54c17c5b1b6c8"
    summary["historical_reproduction_ok"] = historical["ok"]
    summary["historical_target_reached"] = historical["target_reached"]
    summary["historical_target_is_reset_test_for_followon"] = False
    summary["network_used"] = False
    if not historical["ok"]:
        summary["ready_for_evaluation"] = False
        summary["implementation_defects"] = [
            *summary["implementation_defects"],
            "historical reproduction failed",
        ]
    dump_public(out_dir / "audit_summary.json", _short_strings(summary))
    dump_jsonl(out_dir / "case_hashes.jsonl", [_short_strings(row) for row in audited["cases"]])
    dump_jsonl(out_dir / "field_traces.jsonl", [_short_strings(row) for row in audited["fields"]])
    shell = reporting_shell(summary, historical)
    dump_public(out_dir / "reporting_shell.json", _short_strings(shell))
    handover = render_handover(summary, historical)
    (out_dir / "HANDOVER.md").write_text(handover, encoding="utf-8")
    manifest = build_followon_manifest(repo_root, summary, input_hashes)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def _short_strings(value):
    if isinstance(value, str):
        if len(value) <= 400:
            return value
        return hashlib.sha256(value.encode("utf-8")).hexdigest()
    if isinstance(value, dict):
        return {str(key): _short_strings(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_short_strings(item) for item in value]
    return value


def _stop_table(summary: dict) -> str:
    lines = [
        "| Category | Stop reason | Cases |",
        "| --- | --- | --- |",
    ]
    for category in STUDY_CATEGORIES:
        reasons = summary["categories"][category]["stop_reasons"]
        for name in sorted(reasons):
            lines.append(f"| {category} | {name} | {reasons[name]} |")
    return "\n".join(lines)


def _funnel_table(funnel: dict) -> str:
    lines = [
        "| Row | Name | Fields | Cases |",
        "| --- | --- | --- | --- |",
    ]
    for row in funnel["rows"]:
        lines.append(
            f"| {row['row']} | {row['name']} | {row['fields']} / {row['fields_denominator']} | {row['cases']} / {row['cases_denominator']} |"
        )
    return "\n".join(lines)


def _category_table(summary: dict) -> str:
    lines = [
        "| Category | n | f_new | Request groups | T1 fields changed vs U | T2 fields changed vs U | Fields T2≠T1 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for category in STUDY_CATEGORIES:
        block = summary["categories"][category]
        fraction = block["f_new"]
        lines.append(
            "| {category} | {n} | {num}/{den} | {groups} | {t1} | {t2} | {delta} |".format(
                category=category,
                n=block["n"],
                num=fraction["numerator"],
                den=fraction["denominator"],
                groups=block["request_groups"],
                t1=block["changed_fields_vs_U"]["T1"],
                t2=block["changed_fields_vs_U"]["T2"],
                delta=block["changed_fields_t2_t1"],
            )
        )
    return "\n".join(lines)
