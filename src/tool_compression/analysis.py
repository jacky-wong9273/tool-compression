"""Join of change class, official outcomes, and billed-basis T.

The recorded class table is the 19 November diagnosis aggregate. Per-case
flight token rows are not in this repository. ``join_cases`` recomputes the
same summary when those rows are supplied. Missing token values stay missing.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from tool_compression.claims import (
    PRIMARY_OBSERVED_ACCURACY_LOSS_POINTS,
    PRIMARY_L_MINUS_U_PERCENTAGE_POINTS,
    QUALITY_STATEMENT,
    SIGN_STATEMENT,
)

CHANGE_CLASSES = ("unchanged", "suffix_only", "other_change")


def join_cases(rows: list[dict]) -> dict:
    """Join one row per case.

    Required keys: ``category``, ``case_id``, ``change_class``, ``correct_U``,
    ``correct_L``. Optional: ``correct_E``, ``input_tokens_U``, ``input_tokens_L``,
    ``input_tokens_E``.
    """
    issues: list[str] = []
    seen: set[tuple[str, str]] = set()
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        category = row["category"]
        case_id = row["case_id"]
        change_class = row["change_class"]
        key = (category, case_id)
        if key in seen:
            issues.append(f"duplicate case {case_id}")
            continue
        seen.add(key)
        if change_class not in CHANGE_CLASSES:
            issues.append(f"unknown change class for {case_id}")
            continue
        if change_class == "unchanged" and row["correct_U"] != row["correct_L"]:
            issues.append(f"unchanged case {case_id} disagrees on official outcome")
        if change_class == "unchanged" and _both_present(row, "input_tokens_U", "input_tokens_L"):
            if row["input_tokens_U"] != row["input_tokens_L"]:
                issues.append(f"unchanged case {case_id} disagrees on billed-basis T")
        grouped[(category, change_class)].append(row)
    classes = []
    for (category, change_class), members in sorted(grouped.items()):
        classes.append(_summarize_class(category, change_class, members))
    return {"rows": len(rows), "issues": issues, "classes": classes}


def class_join_issues(characterization: dict, settlement: dict, recorded: dict) -> list[str]:
    """Check the recorded class table against Week 1 counts and official totals."""
    issues = []
    for category, block in recorded["categories"].items():
        counts = block["classes"]
        total = sum(item["n"] for item in counts.values())
        denominator = settlement["categories"][category]["denominator"]
        if total != denominator:
            issues.append(f"{category} class counts do not sum to the denominator")
        week1 = characterization["categories"][category]
        suffix = week1["records_changed_only_by_float_suffix"]["C"]
        other = week1["records_with_other_description_changes"]["C"]
        unchanged = week1["n_records"] - suffix - other
        if counts["suffix_only"]["n"] != suffix or counts["other_change"]["n"] != other:
            issues.append(f"{category} class sizes do not match the Week 1 characterization")
        if counts["unchanged"]["n"] != unchanged:
            issues.append(f"{category} unchanged count does not match Week 1")
        if week1["request_differences"]["C_vs_I"] != 0 or week1["request_differences"]["P_vs_I"] != 0:
            issues.append(f"{category} Week 1 local requests do not coincide")
        for arm in ("U", "L"):
            correct = sum(item[f"correct_{arm}"] for item in counts.values())
            official = settlement["categories"][category]["accuracy"][arm]["correct"]
            if correct != official:
                issues.append(f"{category} class-conditional {arm} counts do not sum to the official total")
        if counts["unchanged"]["correct_U"] != counts["unchanged"]["correct_L"]:
            issues.append(f"{category} unchanged class is not tied")
    primary = recorded["primary_provider_input_removed_by_class"]
    removed = primary["suffix_only"] + primary["other_change"] + primary["unchanged"]
    numerator = settlement["categories"]["multiple"]["S_LU"]["ratio_numerator"]
    if removed != numerator or primary["sum"] != numerator:
        issues.append("primary class token split does not sum to the official numerator")
    if primary["suffix_only"] != 850 or primary["other_change"] != 548 or primary["unchanged"] != 0:
        issues.append("primary class token split was altered")
    official_losses = {
        "multiple": set(settlement["categories"]["multiple"]["disagreements_L_vs_U"]["losses"]),
        "simple_python": set(settlement["categories"]["simple_python"]["disagreements_L_vs_U"]["losses"]),
        "irrelevance": set(settlement["categories"]["irrelevance"]["disagreements_L_vs_U"]["losses"]),
    }
    official_gains = {
        category: set(settlement["categories"][category]["disagreements_L_vs_U"]["gains"])
        for category in official_losses
    }
    classed_losses = {category: set() for category in official_losses}
    classed_gains = {category: set() for category in official_losses}
    for case in recorded["classed_disagreements"]:
        category = case["category"]
        if case["pair"] != "L_vs_U":
            continue
        if case["direction"] == "loss":
            classed_losses[category].add(case["case_id"])
        elif case["direction"] == "gain":
            classed_gains[category].add(case["case_id"])
        else:
            issues.append(f"unknown direction for {case['case_id']}")
        if case["change_class"] not in CHANGE_CLASSES:
            issues.append(f"unknown class for {case['case_id']}")
    if classed_losses != official_losses or classed_gains != official_gains:
        issues.append("classed L-vs-U cases do not match the official disagreement lists")
    split = recorded["irrelevance_decode_split"]
    for arm, row in split.items():
        correct = settlement["categories"]["irrelevance"]["accuracy"][arm]["correct"]
        if row["official_correct"] != correct:
            issues.append(f"irrelevance {arm} decode split does not match official accuracy")
        if row["parse_or_decode_failure_counted_as_correct"] != 0:
            issues.append(f"irrelevance {arm} parse failures were altered")
        if row["true_text_no_call"] != row["official_correct"]:
            issues.append(f"irrelevance {arm} no-call split was altered")
        if row["official_incorrect"] + row["official_correct"] != 240:
            issues.append(f"irrelevance {arm} decode split does not cover 240")
        if row["decoded_function_call"] != row["official_incorrect"]:
            issues.append(f"irrelevance {arm} decoded-call split was altered")
    return issues


def uncertainty_analysis(settlement: dict) -> dict:
    """Protocol section 6 for this one replicate.

    No interval is computed. Shared responses are not extra observations.
    Cross-case dependence is recorded and not modelled.
    """
    groups = settlement["primary_request_groups"]
    primary = settlement["categories"]["multiple"]["paired_accuracy_L_vs_U"]
    return {
        "protocol_section": "6",
        "replicates": 1,
        "thinking": {"type": "disabled"},
        "model": "deepseek-flash",
        "statistical_non_inferiority": "not_tested",
        "confidence_interval": None,
        "general_quality_preservation": False,
        "quality_statement": QUALITY_STATEMENT,
        "sign_statement": SIGN_STATEMENT,
        "primary_l_minus_u_percentage_points": PRIMARY_L_MINUS_U_PERCENTAGE_POINTS,
        "primary_observed_accuracy_loss_points": PRIMARY_OBSERVED_ACCURACY_LOSS_POINTS,
        "primary_delta_numerator": primary["delta_numerator"],
        "primary_delta_denominator": primary["delta_denominator"],
        "primary_independent_request_groups": groups["independent_observations"],
        "primary_reused_members": groups["reused_members"],
        "primary_logical_arm_assignments": groups["logical_arm_assignments"],
        "reused_members_are_independent_observations": False,
        "cross_case_dependence_modelled": False,
        "reason_no_interval": (
            "One replicate does not identify a sampling distribution. "
            "Shared request groups are not independent observations, and "
            "cross-case dependence is not modelled."
        ),
        "same_setting_replicates_in_this_package": False,
        "same_setting_replicates_would_establish_general_safety": False,
        "claims_not_established": [
            "statistical non-inferiority",
            "general quality preservation",
            "a full BFCL leaderboard result",
            "a behavioural comparison of different contrast-aware and independent selections",
            "isolation of compression-caused deployment savings from cache state, request order, or prefix reuse",
            "a total-cost claim",
        ],
    }


def _summarize_class(category: str, change_class: str, members: list[dict]) -> dict:
    summary = {
        "category": category,
        "change_class": change_class,
        "n": len(members),
        "correct_U": sum(bool(row["correct_U"]) for row in members),
        "correct_L": sum(bool(row["correct_L"]) for row in members),
    }
    if all("correct_E" in row and row["correct_E"] is not None for row in members):
        summary["correct_E"] = sum(bool(row["correct_E"]) for row in members)
    for arm in ("U", "L", "E"):
        key = f"input_tokens_{arm}"
        if all(key in row and row[key] is not None for row in members):
            summary[f"sum_T_{arm}"] = int(sum(row[key] for row in members))
            summary[f"token_coverage_{arm}"] = "complete"
        else:
            summary[f"sum_T_{arm}"] = None
            summary[f"token_coverage_{arm}"] = "incomplete"
    if summary["sum_T_U"] is not None and summary["sum_T_L"] is not None:
        summary["provider_input_removed_L_vs_U"] = summary["sum_T_U"] - summary["sum_T_L"]
    else:
        summary["provider_input_removed_L_vs_U"] = None
    return summary


def _both_present(row: dict, left: str, right: str) -> bool:
    return left in row and right in row and row[left] is not None and row[right] is not None


def load_recorded_join(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
