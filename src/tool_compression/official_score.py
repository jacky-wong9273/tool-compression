"""Official scoring from saved outputs. No provider call.

``DeepSeek-V3.2-Exp-FC`` is a decode and check alias. The 18 November flight
model was ``deepseek-flash``. The alias's official registry ``model_name`` is
``deepseek-chat``, so this package refuses ``bfcl generate`` under the alias.

Mapping and settlement follow the 19 November adapter: expand shared request
groups into per-arm result rows, then read unchanged official score files.
Scores are not created here.
"""

from __future__ import annotations

import json
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

from tool_compression.evaluation import (
    DENOMINATORS,
    primary_accuracy_change,
    primary_provider_saving,
    reference_target_from_external,
    study_target_status,
)
from tool_compression.usage import cohort_provider_saving, combine_targets, paired_accuracy_change

SCORING_ALIAS = "DeepSeek-V3.2-Exp-FC"
REGISTRY_MODEL_NAME = "deepseek-chat"
FLIGHT_MODEL = "deepseek-flash"
FLIGHT_MODEL_VERSION = "DeepSeek-V4.1-Flash-1017"
GORILLA_COMMIT = "6ea57973c7a6097fd7c5915698c54c17c5b1b6c8"
ALIAS_FLAGS = {"is_fc_model": True, "underscore_to_dot": True}
ARMS = ("U", "L", "E")
CATEGORIES = dict(DENOMINATORS)
VERSION_PREFIX = "BFCL_v4"
PRIMARY = "multiple"

# Pinned official figures. Tests fail if the committed settlement is edited.
LOCKED_ACCURACY = {
    "multiple": {"U": 186, "L": 185, "E": 186, "n": 200},
    "simple_python": {"U": 379, "L": 373, "E": 377, "n": 400},
    "irrelevance": {"U": 184, "L": 187, "E": 186, "n": 240},
}
LOCKED_SAVING = {
    "multiple": {"S_LU": (1398, 121018), "S_EU": (311, 121018)},
    "simple_python": {"S_LU": (702, 149432), "S_EU": (278, 149432)},
    "irrelevance": {"S_LU": (959, 88495), "S_EU": (196, 88495)},
}
LOCKED_PRIMARY_L_VS_U = {
    "gains": ["multiple_132"],
    "losses": ["multiple_45", "multiple_186"],
    "delta_numerator": -1,
}


class ScoringAliasGenerateRefused(RuntimeError):
    """``bfcl generate`` under the scoring alias would target ``deepseek-chat``."""


class SavedOutputError(RuntimeError):
    def __init__(self, issues: list[str]):
        self.issues = issues
        super().__init__("; ".join(issues[:8]))


def alias_record() -> dict:
    return {
        "handler_alias": SCORING_ALIAS,
        "registry_model_name": REGISTRY_MODEL_NAME,
        "flight_model": FLIGHT_MODEL,
        "flight_model_version": FLIGHT_MODEL_VERSION,
        "gorilla_commit": GORILLA_COMMIT,
        "flags": dict(ALIAS_FLAGS),
        "generate_allowed": False,
        "evaluate_from_saved_outputs_allowed": True,
        "leaderboard_claim": False,
        "reason": (
            f"{FLIGHT_MODEL} is not in the pinned official registry. "
            f"{SCORING_ALIAS} is used only so official evaluate can decode "
            "already-parsed function calls. The same registry entry sets "
            f"model_name={REGISTRY_MODEL_NAME!r}, so generate under this alias "
            "would request a different model."
        ),
    }


def build_bfcl_argv(
    action: str,
    *,
    model: str,
    test_category: str,
    result_dir: str,
    score_dir: str,
    bfcl: str = "bfcl",
) -> list[str]:
    """Build an evaluate command. Generate is refused, including under the alias."""
    if action != "evaluate":
        raise ScoringAliasGenerateRefused(_generate_refusal(model))
    if model != SCORING_ALIAS:
        raise ScoringAliasGenerateRefused(
            "This package builds evaluate commands only for the documented scoring alias "
            f"{SCORING_ALIAS}."
        )
    argv = [
        bfcl,
        "evaluate",
        "--model",
        model,
        "--test-category",
        test_category,
        "--result-dir",
        result_dir,
        "--score-dir",
        score_dir,
    ]
    guard_bfcl_argv(argv)
    return argv


def guard_bfcl_argv(argv: list[str]) -> None:
    """Allow evaluate under the scoring alias. Refuse generate."""
    if not argv:
        raise ValueError("empty bfcl argv")
    tokens = [str(item) for item in argv]
    action = _subcommand(tokens)
    model = _option(tokens, "--model")
    if action == "generate" or "generate" in tokens:
        raise ScoringAliasGenerateRefused(_generate_refusal(model or SCORING_ALIAS))
    if action != "evaluate":
        raise ScoringAliasGenerateRefused(
            "This package authorizes bfcl evaluate on saved result files only."
        )
    if model == SCORING_ALIAS:
        return
    if model is None:
        raise ScoringAliasGenerateRefused(
            f"evaluate requires --model {SCORING_ALIAS}."
        )
    raise ScoringAliasGenerateRefused(
        f"Refusing evaluate under {model!r}. The documented scoring alias is {SCORING_ALIAS}."
    )


def _generate_refusal(model: str) -> str:
    if model == SCORING_ALIAS or model == "":
        return (
            f"Refusing bfcl generate under {SCORING_ALIAS}. "
            f"That registry entry's model_name is {REGISTRY_MODEL_NAME}, "
            f"not the flight model {FLIGHT_MODEL}."
        )
    return (
        "This package does not build or run bfcl generate. "
        f"Generate under {SCORING_ALIAS} is refused because its registry "
        f"model_name is {REGISTRY_MODEL_NAME}, not {FLIGHT_MODEL}."
    )


def _subcommand(argv: list[str]) -> str | None:
    for token in argv:
        if token in {"evaluate", "generate"}:
            return token
    return None


def _option(argv: list[str], name: str) -> str | None:
    for index, token in enumerate(argv):
        if token == name and index + 1 < len(argv):
            return argv[index + 1]
        if token.startswith(name + "="):
            return token.split("=", 1)[1]
    return None


def decode_saved_fc_responses(model_responses):
    """Load an already-parsed function-calling result.

    For ``is_fc_model=True``, official ``decode_ast`` JSON-loads the stored
    result. It does not call a model. A value that is already a list or object
    is returned as stored.
    """
    if isinstance(model_responses, str):
        return json.loads(model_responses)
    return model_responses


def call_names(model_responses) -> list[str]:
    parsed = decode_saved_fc_responses(model_responses)
    if isinstance(parsed, dict):
        items = [parsed]
    elif isinstance(parsed, list):
        items = parsed
    else:
        return []
    names: list[str] = []
    for item in items:
        if isinstance(item, dict):
            names.extend(str(key) for key in item)
        elif isinstance(item, str):
            names.append(item.split("(", 1)[0])
    return names


def dotted_name_count(names: list[str]) -> int:
    return sum(1 for name in names if "." in str(name))


def recorded_conversion_parity(characterization: dict) -> dict:
    block = characterization["conversion_parity"]
    return {
        "checked_records": block["checked_records"],
        "mismatches": block["mismatches"],
        "official_functions": block["official_functions"],
        "style": block["style"],
        "source": "evidence/week1_characterization.json",
        "path": "convert_to_tool(..., GORILLA_TO_OPENAPI, OPENAI_COMPLETIONS)",
    }


def tool_names_in_request_body(body: dict) -> list[str]:
    names = []
    for tool in body.get("tools") or []:
        function = tool.get("function") if isinstance(tool, dict) else None
        if isinstance(function, dict) and isinstance(function.get("name"), str):
            names.append(function["name"])
    return names


def map_saved_outputs(
    stage_b: Path,
    out_root: Path,
    *,
    categories: dict[str, int] | None = None,
    expected_groups: int | None = None,
    handler_alias: str = SCORING_ALIAS,
) -> dict:
    """Expand stage B ledgers into per-arm BFCL result files.

    ``stage_b`` is read only. Result rows are ``{"id", "result"}`` taken from
    ``parsed.jsonl`` ``model_responses``. This function does not score.
    """
    stage_b = Path(stage_b)
    out_root = Path(out_root)
    categories = dict(categories or CATEGORIES)
    logical = _load_json(stage_b / "logical_ledger.json")
    usage = _load_json(stage_b / "usage_ledger.json")
    parsed_rows = _load_jsonl(stage_b / "parsed.jsonl")
    parsed = {row["response_group_id"]: row for row in parsed_rows}
    usage_by_gid = {row["response_group_id"]: row for row in usage["physical_attempts"]}
    issues: list[str] = []
    if expected_groups is not None and logical.get("independent_observations") != expected_groups:
        issues.append(
            f"independent_observations={logical.get('independent_observations')} "
            f"(expected {expected_groups})"
        )
    if expected_groups is not None and len(logical["responses"]) != expected_groups:
        issues.append(f"logical responses={len(logical['responses'])} (expected {expected_groups})")
    if expected_groups is not None and len(parsed) != expected_groups:
        issues.append(f"parsed groups={len(parsed)} (expected {expected_groups})")
    if expected_groups is not None and (
        usage.get("count") != expected_groups or len(usage["physical_attempts"]) != expected_groups
    ):
        issues.append(f"usage attempts={usage.get('count')} (expected {expected_groups})")

    assignment: dict[tuple[str, str, int], dict[str, dict]] = defaultdict(dict)
    mapping_rows: list[dict] = []
    for group in logical["responses"]:
        gid = group["response_group_id"]
        case_id = group["case_id"]
        category = group["category"]
        replicate = group["replicate"]
        members = list(group["members"])
        reused = list(group.get("reused_members") or [])
        if gid not in parsed:
            issues.append(f"missing parsed row for {gid}")
            continue
        parsed_row = parsed[gid]
        if gid not in usage_by_gid:
            issues.append(f"missing usage row for {gid}")
            continue
        usage_row = usage_by_gid[gid]
        if usage_row.get("status") != "received":
            issues.append(f"usage status {usage_row.get('status')} for {gid}")
        tokens = (usage_row.get("usage") or {}).get("total_input_tokens")
        if tokens is None:
            issues.append(f"missing total_input_tokens for {gid}")
        if tokens is not None and tokens != group.get("input_tokens"):
            issues.append(f"token mismatch for {gid}")
        if parsed_row.get("thinking_disabled") is not True:
            issues.append(f"thinking_disabled is not True for {gid}")
        if set(reused) - set(members):
            issues.append(f"reused_members not subset of members for {gid}")
        for arm in members:
            key = (category, case_id, replicate)
            if arm in assignment[key]:
                issues.append(f"duplicate assignment {category}/{case_id}/r{replicate}/{arm}")
                continue
            record = {
                "case_id": case_id,
                "category": category,
                "replicate": replicate,
                "arm": arm,
                "response_group_id": gid,
                "request_sha256": group.get("request_sha256"),
                "members": members,
                "reused_member": arm in reused,
                "independent_observation": arm not in reused,
                "input_tokens": group.get("input_tokens"),
                "cache_hit_tokens": group.get("cache_hit_tokens"),
                "output_tokens": group.get("output_tokens"),
                "usage_status": usage_row.get("status"),
                "thinking_disabled": parsed_row.get("thinking_disabled"),
            }
            assignment[key][arm] = {
                "mapping": record,
                "model_responses": parsed_row["model_responses"],
            }
            mapping_rows.append(record)

    coverage = {}
    for category, count in categories.items():
        missing = []
        present = 0
        for case_id in _expected_ids(category, count):
            arms = assignment.get((category, case_id, 0), {})
            if set(arms) != set(ARMS):
                missing.append({"case_id": case_id, "arms": sorted(arms)})
            else:
                present += 1
        coverage[category] = {
            "denominator": count,
            "present": present,
            "missing_or_incomplete": missing,
        }
        if missing:
            issues.append(f"{category} incomplete: {len(missing)} cases")
    if issues:
        raise SavedOutputError(issues)

    mapping_path = out_root / "mapping" / "arm_case_mapping.jsonl"
    _write_jsonl(
        mapping_path,
        sorted(mapping_rows, key=lambda row: (row["category"], row["case_id"], row["arm"])),
    )
    written = {}
    for arm in ARMS:
        arm_dir = out_root / "bfcl_project" / f"result_{arm.lower()}" / handler_alias
        files = {}
        for category, count in categories.items():
            rows = []
            for case_id in _expected_ids(category, count):
                payload = assignment[(category, case_id, 0)][arm]
                rows.append({"id": case_id, "result": payload["model_responses"]})
            path = arm_dir / f"{VERSION_PREFIX}_{category}_result.json"
            _write_jsonl(path, rows)
            files[category] = {"path": str(path), "n": len(rows)}
        written[arm] = files
    summary = {
        "source_stage_b": str(stage_b),
        "source_left_intact": True,
        "handler_alias": handler_alias,
        "registry_model_name": REGISTRY_MODEL_NAME,
        "generate_refused": True,
        "flight_model": FLIGHT_MODEL,
        "mapping_rows": len(mapping_rows),
        "coverage": coverage,
        "result_files": written,
        "issues": [],
        "ok": True,
    }
    coverage_path = out_root / "mapping" / "coverage.json"
    coverage_path.parent.mkdir(parents=True, exist_ok=True)
    coverage_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    summary["mapping"] = str(mapping_path)
    summary["coverage_path"] = str(coverage_path)
    return summary


def official_correctness(path: Path, category: str, denominator: int) -> dict:
    rows = _load_jsonl(path)
    if not rows:
        raise SavedOutputError([f"empty score file {path}"])
    header = rows[0]
    failures = rows[1:]
    failed_ids = [row["id"] for row in failures]
    expected = _expected_ids(category, denominator)
    if header.get("total_count") != denominator:
        raise SavedOutputError([f"{path} total_count={header.get('total_count')} != {denominator}"])
    if header.get("correct_count") + len(failures) != denominator:
        raise SavedOutputError([f"{path} correct_count + failures != denominator"])
    if any(row.get("valid") is not False for row in failures):
        raise SavedOutputError([f"{path} has a failure row without valid=false"])
    extra = set(failed_ids) - set(expected)
    if extra:
        raise SavedOutputError([f"{path} unexpected failure ids"])
    if len(failed_ids) != len(set(failed_ids)):
        raise SavedOutputError([f"{path} duplicate failure ids"])
    failed = set(failed_ids)
    correct = {case_id: case_id not in failed for case_id in expected}
    n_correct = sum(correct.values())
    if n_correct != header["correct_count"]:
        raise SavedOutputError([f"{path} reconstructed correct != header"])
    return {
        "header": {
            "accuracy": header["accuracy"],
            "correct_count": header["correct_count"],
            "total_count": header["total_count"],
        },
        "correct_by_id": correct,
        "correct_vector": [correct[case_id] for case_id in expected],
        "failed_ids": [case_id for case_id in expected if case_id in failed],
    }


def settle_from_saved(
    score_root: Path,
    mapping_path: Path,
    *,
    categories: dict[str, int] | None = None,
    execution_record: dict | None = None,
    handler_alias: str = SCORING_ALIAS,
) -> dict:
    """Join official score files to billed-basis total input from the mapping.

    The token statistic is the ratio of cohort means of provider total input.
    A missing execution record leaves ``study_target_status`` unresolved.
    """
    categories = dict(categories or CATEGORIES)
    score_root = Path(score_root)
    correctness = {}
    for arm in ARMS:
        correctness[arm] = {}
        for category, count in categories.items():
            path = (
                score_root
                / f"score_{arm.lower()}"
                / handler_alias
                / "non_live"
                / f"{VERSION_PREFIX}_{category}_score.json"
            )
            correctness[arm][category] = official_correctness(path, category, count)
    usage = _usage_vectors(mapping_path, categories)
    category_reports = {}
    for category, count in categories.items():
        category_reports[category] = _category_report(
            category, count, correctness, usage
        )
    token_lu = category_reports[PRIMARY]["S_LU"] if PRIMARY in category_reports else None
    acc_lu = category_reports[PRIMARY]["paired_accuracy_L_vs_U"] if PRIMARY in category_reports else None
    reference = None
    target_status = {
        "attainment": "unresolved",
        "reason": "primary_category_absent",
        "target_reached": None,
        "target_lowered": False,
    }
    external = None
    if token_lu is not None and acc_lu is not None:
        reference = combine_targets(token_lu, acc_lu)
        if execution_record is None:
            target_status = {
                "attainment": "unresolved",
                "reason": "execution_record_not_supplied",
                "target_reached": None,
                "target_lowered": False,
            }
        else:
            target_status = study_target_status(execution_record, token=token_lu, accuracy=acc_lu)
        token_eu = category_reports[PRIMARY]["S_EU"]
        external = reference_target_from_external(token_eu.get("ratio_of_means") or 0.0)
    return {
        "protocol": "1.1",
        "official_accuracy": True,
        "invented_scores": False,
        "paid_provider_called": False,
        "handler_alias": handler_alias,
        "handler_alias_is_the_flight_model": False,
        "registry_model_name": REGISTRY_MODEL_NAME,
        "generate_refused": True,
        "flight_model": FLIGHT_MODEL,
        "reference_comparison": "C-U",
        "l_is_reporting_label_only": True,
        "e_versus_u_can_satisfy_reference_target": False,
        "categories": category_reports,
        "reference_target_L_represents_C": {
            "S_LU": token_lu,
            "paired_accuracy_L_vs_U": acc_lu,
            "combine_targets": reference,
            "study_target_status": target_status,
        },
        "E_versus_U_reported_separately": {
            "reference_target_from_external": external,
        },
    }


def locked_settlement_issues(settlement: dict) -> list[str]:
    """Recompute the committed settlement from its failed ids and token sums.

    Per-case provider token vectors are not in this checkout, so the mean of
    per-case ratios is checked for presence and is not treated as ``S_LU``.
    """
    issues: list[str] = []
    if settlement.get("invented_scores") is not False:
        issues.append("invented_scores")
    if settlement.get("paid_provider_called") is not False:
        issues.append("paid_provider_called")
    if settlement.get("e_versus_u_can_satisfy_reference_target") is not False:
        issues.append("external comparator marked as able to meet the C-U target")
    reference = settlement["reference_target_L_represents_C"]
    combined = combine_targets(reference["S_LU"], reference["paired_accuracy_L_vs_U"])
    if combined != reference["combine_targets"]:
        issues.append("combine_targets does not match the stored hook inputs")
    if combined != reference["study_target_status"]:
        issues.append("study_target_status does not match combine_targets")
    if combined.get("target_reached") is not False or combined.get("target_lowered") is not False:
        issues.append("recorded target status was altered")
    if combined.get("statistical_non_inferiority") != "not_tested":
        issues.append("non-inferiority flag was altered")
    if combined.get("reference_comparison") != "C-U":
        issues.append("reference comparison was altered")

    for category, expected in LOCKED_ACCURACY.items():
        block = settlement["categories"][category]
        count = expected["n"]
        vectors = {}
        for arm in ARMS:
            accuracy = block["accuracy"][arm]
            failed = accuracy["failed_ids"]
            if accuracy["correct"] != expected[arm] or accuracy["denominator"] != count:
                issues.append(f"{category} {arm} accuracy does not match the locked count")
            if accuracy["official_header"]["correct_count"] != expected[arm]:
                issues.append(f"{category} {arm} official header was altered")
            if accuracy["official_header"]["total_count"] != count:
                issues.append(f"{category} {arm} denominator was altered")
            if len(failed) != count - expected[arm]:
                issues.append(f"{category} {arm} failure list length")
            if len(failed) != len(set(failed)):
                issues.append(f"{category} {arm} duplicate failures")
            vectors[arm] = [f"{category}_{i}" not in set(failed) for i in range(count)]
            if sum(vectors[arm]) != expected[arm]:
                issues.append(f"{category} {arm} failed ids do not reconstruct the locked count")
        for label, left, right in (
            ("L_vs_U", "U", "L"),
            ("E_vs_U", "U", "E"),
        ):
            if category == PRIMARY and label == "L_vs_U":
                hook = primary_accuracy_change(vectors["U"], vectors["L"])
            else:
                hook = paired_accuracy_change(vectors[left], vectors[right], denominator=count)
            stored = block[f"paired_accuracy_{label}"]
            if hook != stored:
                issues.append(f"{category} paired accuracy {label} does not recompute")
            names = _expected_ids(category, count)
            gained = [case_id for case_id, base, other in zip(names, vectors[left], vectors[right]) if other and not base]
            lost = [case_id for case_id, base, other in zip(names, vectors[left], vectors[right]) if base and not other]
            recorded = block[f"disagreements_{label}"]
            if recorded["gains"] != gained or recorded["losses"] != lost:
                issues.append(f"{category} disagreement ids {label} do not match failed lists")
        for key, pair in (("S_LU", "S_LU"), ("S_EU", "S_EU")):
            numerator, denominator = LOCKED_SAVING[category][pair]
            variant = "L" if key == "S_LU" else "E"
            base_sum = block["provider_total_input"]["U"]["sum"]
            other_sum = block["provider_total_input"][variant]["sum"]
            saving = block[key]
            if (base_sum, other_sum) != (
                denominator,
                denominator - numerator,
            ):
                issues.append(f"{category} {key} sums do not match the locked saving")
            if saving["ratio_numerator"] != numerator or saving["ratio_denominator"] != denominator:
                issues.append(f"{category} {key} ratio was altered")
            if saving["ratio_of_means"] != numerator / denominator:
                issues.append(f"{category} {key} ratio_of_means was altered")
            if saving["target_reached"] is not False or saving["target"] != "1/10":
                issues.append(f"{category} {key} target flag was altered")
            if saving["statistical_non_inferiority"] != "not_tested":
                issues.append(f"{category} {key} non-inferiority flag was altered")
            if "mean_of_per_case_ratios" not in saving:
                issues.append(f"{category} {key} is missing the per-case mean")
            if saving["mean_of_per_case_ratios"] == saving["ratio_of_means"]:
                issues.append(f"{category} {key} collapsed the two ratio definitions")
            reached = Fraction(numerator, denominator) >= Fraction(1, 10)
            if reached:
                issues.append(f"{category} {key} would meet 10 percent, which the locked result does not")
            if block["provider_total_input"]["U"]["n"] != count:
                issues.append(f"{category} usage coverage is not the full denominator")
    primary = settlement["categories"][PRIMARY]
    if primary["disagreements_L_vs_U"]["gains"] != LOCKED_PRIMARY_L_VS_U["gains"]:
        issues.append("primary L vs U gains were altered")
    if primary["disagreements_L_vs_U"]["losses"] != LOCKED_PRIMARY_L_VS_U["losses"]:
        issues.append("primary L vs U losses were altered")
    if primary["paired_accuracy_L_vs_U"]["delta_numerator"] != LOCKED_PRIMARY_L_VS_U["delta_numerator"]:
        issues.append("primary accuracy delta was altered")
    loss = accuracy_change_points(
        primary["paired_accuracy_L_vs_U"]["delta_numerator"],
        primary["paired_accuracy_L_vs_U"]["delta_denominator"],
    )
    if loss["l_minus_u_percentage_points"] != -0.5:
        issues.append("primary L-U percentage points were altered")
    if loss["observed_accuracy_loss_points"] != 0.5:
        issues.append("primary observed accuracy loss was altered")
    groups = settlement["primary_request_groups"]
    if groups["independent_observations"] != 438 or groups["reused_members"] != 162:
        issues.append("primary request-group accounting was altered")
    if groups["logical_arm_assignments"] != 600:
        issues.append("primary logical assignments were altered")
    return issues


def accuracy_change_points(delta_numerator: int, denominator: int) -> dict:
    """L−U in percentage points, and the observed accuracy loss in points.

    A negative L−U is a positive observed loss. The primary result is L−U of
    −0.5 percentage points and an observed accuracy loss of +0.5 points.
    """
    if denominator <= 0:
        raise ValueError("denominator")
    l_minus_u = 100 * delta_numerator / denominator
    observed_loss = -l_minus_u
    return {
        "l_minus_u_percentage_points": l_minus_u,
        "observed_accuracy_loss_points": observed_loss,
        "wording": (
            f"L−U is {_signed_points(l_minus_u)} percentage points; "
            f"the observed accuracy loss is {_signed_points(observed_loss)} points."
        ),
    }


def _signed_points(value: float) -> str:
    if value < 0:
        return f"−{abs(value):g}"
    if value > 0:
        return f"+{value:g}"
    return "0"


def _category_report(category: str, count: int, correctness: dict, usage: dict) -> dict:
    ids = _expected_ids(category, count)
    accuracy = {}
    tokens = {}
    for arm in ARMS:
        vector = correctness[arm][category]["correct_vector"]
        series = usage[category][arm]
        accuracy[arm] = {
            "correct": sum(vector),
            "denominator": count,
            "accuracy": sum(vector) / count,
            "official_header": correctness[arm][category]["header"],
            "failed_ids": correctness[arm][category]["failed_ids"],
        }
        tokens[arm] = {
            "n": len(series),
            "sum": int(sum(series)),
            "mean": sum(series) / len(series),
        }
    return {
        "category": category,
        "denominator": count,
        "is_primary": category == PRIMARY,
        "accuracy": accuracy,
        "provider_total_input": tokens,
        "S_LU": _saving(category, count, usage[category]["U"], usage[category]["L"]),
        "S_EU": _saving(category, count, usage[category]["U"], usage[category]["E"]),
        "paired_accuracy_L_vs_U": _accuracy_hook(
            category, count, correctness["U"][category]["correct_vector"], correctness["L"][category]["correct_vector"]
        ),
        "paired_accuracy_E_vs_U": _accuracy_hook(
            category, count, correctness["U"][category]["correct_vector"], correctness["E"][category]["correct_vector"]
        ),
        "disagreements_L_vs_U": _disagreements(
            ids, correctness["U"][category]["correct_vector"], correctness["L"][category]["correct_vector"]
        ),
        "disagreements_E_vs_U": _disagreements(
            ids, correctness["U"][category]["correct_vector"], correctness["E"][category]["correct_vector"]
        ),
    }


def _saving(category: str, count: int, baseline: list[int], variant: list[int]) -> dict:
    if category == PRIMARY and count == DENOMINATORS[PRIMARY]:
        return primary_provider_saving(baseline, variant)
    return cohort_provider_saving(baseline, variant, denominator=count)


def _accuracy_hook(category: str, count: int, baseline: list[bool], variant: list[bool]) -> dict:
    if category == PRIMARY and count == DENOMINATORS[PRIMARY]:
        return primary_accuracy_change(baseline, variant)
    return paired_accuracy_change(baseline, variant, denominator=count)


def _disagreements(ids: list[str], baseline: list[bool], variant: list[bool]) -> dict:
    gains = [case_id for case_id, base, other in zip(ids, baseline, variant) if other and not base]
    losses = [case_id for case_id, base, other in zip(ids, baseline, variant) if base and not other]
    return {"gains": gains, "losses": losses, "n_gains": len(gains), "n_losses": len(losses)}


def _usage_vectors(mapping_path: Path, categories: dict[str, int]) -> dict:
    rows = _load_jsonl(mapping_path)
    by = {}
    issues = []
    for row in rows:
        key = (row["category"], row["case_id"], row["arm"])
        if key in by:
            issues.append(f"duplicate mapping {key}")
        if row.get("usage_status") != "received" or row.get("input_tokens") is None:
            issues.append(f"incomplete usage {key}")
        by[key] = row
    if issues:
        raise SavedOutputError(issues)
    out = {}
    for category, count in categories.items():
        out[category] = {}
        for arm in ARMS:
            series = []
            for index in range(count):
                case_id = f"{category}_{index}"
                series.append(int(by[(category, case_id, arm)]["input_tokens"]))
            out[category][arm] = series
    return out


def _expected_ids(category: str, count: int) -> list[str]:
    return [f"{category}_{index}" for index in range(count)]


def _load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
