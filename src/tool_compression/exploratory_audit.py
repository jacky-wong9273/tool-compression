"""Offline audit of H50 and H25 on the Week 1 catalogue.

The official P/I/C compressor and ``characterize_study`` produce the counts.
No provider is called and no socket is opened.
"""

from collections import Counter
from pathlib import Path
import json

from tool_compression.characterize import characterize_study, file_sha256
from tool_compression.config import DEFAULT_CONFIG, LOCAL_TOKENIZER
from tool_compression.evaluation import DENOMINATORS, PINS, summarize_hash_rows
from tool_compression.exploratory import (
    A_LABEL,
    ARM_NAMES,
    B_LABEL,
    BASE_COMMIT,
    CLOSED_OFFICIAL_RESULT,
    EXPLORATORY_LABELS,
    FULL_CATALOGUE_BASE_COMMIT,
    FULL_CATALOGUE_LABELS,
    classify_case,
    frozen_config,
    full_catalogue_plan_decision,
    setting_flyability,
)
from tool_compression.load import VERSION_PREFIX, resolve_data_dir
from tool_compression.publish import dump_jsonl, dump_public

PINNED_DATA_SHA256 = {
    "BFCL_v4_irrelevance.json": "2b6ed4c2e992cdcf5f1678a701851f944bef7550ee026ed1ddb89efed5be01a6",
    "BFCL_v4_multiple.json": "aef168155ebd74b7ac2401198b201343bc7d16d7a3d7e0d4e6d8ee82c6969b2a",
    "BFCL_v4_simple_python.json": "82dd63ba502eb2520c6b5d1d9a5c4b590e03ff261565175561f6228a367d1991",
}
STATUS_NOTE = (
    "Field status and stop reasons are the characterize_study counts and reason "
    "tallies: stopped_early, frozen, empty_or_whitespace, and the cue reasons."
)


def load_hash_rows(path: Path) -> list[dict]:
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def audit_study(
    study,
    official_rows: list[dict],
    arm_rows: list[dict],
    budget,
    sensitivity,
    *,
    data_pin: dict | None = None,
) -> tuple[dict, dict]:
    """Return the public audit and per-setting hash rows. Both are free of tool prose."""
    reproduction = reproduce_official_hashes(study, official_rows, budget, sensitivity)
    data_pin = data_pin or {"matched": False, "source": "not_supplied"}
    official_groups = summarize_hash_rows(official_rows, arm_rows)
    settings = {}
    hash_rows = {}
    for label in EXPLORATORY_LABELS:
        report, rows = audit_setting(
            study,
            label,
            official_rows,
            budget,
            sensitivity,
            hash_reproduction_matched=reproduction["matched"],
            data_pin_matched=bool(data_pin.get("matched")),
        )
        settings[label] = report
        hash_rows[label] = rows
    payload = {
        "base_commit": BASE_COMMIT,
        "official_compressor": "week1.0 P/I/C",
        "official_retention_unchanged": DEFAULT_CONFIG.as_dict()["retention_r"],
        "lambda": "1/2",
        "jaccard_min": "1/5",
        "max_neighbours": 2,
        "local_tokenizer": LOCAL_TOKENIZER,
        "protections_changed": False,
        "segmentation_changed": False,
        "provider_called": False,
        "network_used": False,
        "official_target_lowered": False,
        "official_result": CLOSED_OFFICIAL_RESULT,
        "local_sums_are_not_provider_T": True,
        "historical_primary_U_billed_basis_T": 121018,
        "accuracy_versus_historical_U_is_a_different_draw": True,
        "historical_L_is_the_closed_baseline": True,
        "E_is_out_of_scope": True,
        "a_later_hit_does_not_revise_the_official_result": True,
        "denominators": dict(DENOMINATORS),
        "cases": sum(DENOMINATORS.values()),
        "official_unique_request_groups": official_groups["provisional_unique_request_groups_per_replicate"],
        "official_hash_reproduction": reproduction,
        "data_pin": data_pin,
        "pins": dict(PINS),
        "counting": {
            "budget_tokenizer": budget.name,
            "budget_backend": getattr(budget, "backend", budget.name),
            "sensitivity_tokenizer_not_used_for_selection": sensitivity.name,
            "provider_usage_measured": False,
        },
        "settings": settings,
        "h50_h25_request_identity": _h50_h25_identity(hash_rows),
    }
    return payload, hash_rows


def audit_setting(
    study,
    label,
    official_rows,
    budget,
    sensitivity,
    *,
    hash_reproduction_matched: bool,
    data_pin_matched: bool,
):
    config = frozen_config(label)
    payload, rows = characterize_study(study, budget, sensitivity, config)
    official = _index_rows(official_rows)
    classified_rows = []
    failures = []
    for row in rows:
        key = (row.get("category"), row.get("id"))
        if row.get("preparation_failure"):
            failures.append({"category": row.get("category"), "id": row.get("id"), "reason": "preparation_failure"})
            classified_rows.append(
                {
                    "category": row.get("category"),
                    "id": row.get("id"),
                    "preparation_failure": True,
                    "identical_to_u": False,
                    "identical_to_official_l": False,
                    "new_request": False,
                    "p_i_c_coincide": False,
                }
            )
            continue
        official_row = official.get(key)
        official_hashes = None if official_row is None or official_row.get("preparation_failure") else official_row.get("hashes")
        classified = classify_case(row["hashes"], official_hashes)
        classified_rows.append(
            {
                "category": row["category"],
                "id": row["id"],
                "preparation_failure": False,
                "hashes": row["hashes"],
                "official_l_hash": classified["official_l_hash"],
                "official_u_hash": classified["official_u_hash"],
                "u_matches_official_u": classified["u_matches_official_u"],
                "p_i_c_coincide": classified["p_i_c_coincide"],
                "identical_to_u": classified["identical_to_u"],
                "identical_to_official_l": classified["identical_to_official_l"],
                "new_arms": classified["new_arms"],
                "new_request": classified["new_request"],
                "C_vs_I": row["hashes"]["C"] != row["hashes"]["I"],
                "C_vs_U": row["hashes"]["C"] != row["hashes"]["U"],
                "P_vs_I": row["hashes"]["P"] != row["hashes"]["I"],
                "P_vs_U": row["hashes"]["P"] != row["hashes"]["U"],
                "I_vs_U": row["hashes"]["I"] != row["hashes"]["U"],
            }
        )
        if official_row is None or official_row.get("preparation_failure"):
            failures.append({"category": row["category"], "id": row["id"], "reason": "missing_official_L_row"})
    counts = Counter(row["category"] for row in rows)
    coverage_complete = (
        not failures
        and all(counts.get(name) == expected for name, expected in DENOMINATORS.items())
        and set(counts) == set(DENOMINATORS)
    )
    fly = setting_flyability(
        classified_rows,
        coverage_complete=coverage_complete,
        hash_reproduction_matched=hash_reproduction_matched and data_pin_matched,
    )
    if not data_pin_matched:
        fly = {**fly, "flyable": False, "reason": "bfcl_data_pin_mismatch"}
    prepared = [row for row in classified_rows if not row["preparation_failure"]]
    coincide_cases = sum(1 for row in prepared if row["p_i_c_coincide"])
    diverge_cases = len(prepared) - coincide_cases
    arms_separate = diverge_cases > 0
    categories = {}
    for name in DENOMINATORS:
        categories[name] = _category_report(
            name,
            payload["categories"][name],
            [row for row in classified_rows if row["category"] == name],
            [item for item in failures if item["category"] == name],
            payload["counting"]["budget_tokenizer"],
            hash_reproduction_matched and data_pin_matched,
        )
    structural = payload["structural_violations"]
    measurement_agrees = all(category["measurement_agrees"] for category in categories.values())
    ready = (
        coverage_complete
        and hash_reproduction_matched
        and data_pin_matched
        and structural == 0
        and not failures
        and measurement_agrees
    )
    u_mismatch = [
        {"category": row["category"], "id": row["id"]}
        for row in prepared
        if row.get("u_matches_official_u") is False
    ]
    if u_mismatch:
        ready = False
        fly = {
            **fly,
            "flyable": False,
            "reason": "u_hash_does_not_match_official_u",
        }
    token_sums = _sum_tokens(categories, payload["counting"]["budget_tokenizer"])
    shared = not arms_separate
    report = {
        "label": label,
        "spec_version": config.spec_version,
        "retention_r": config.as_dict()["retention_r"],
        "retention_decimal": f"{config.retention_numerator / config.retention_denominator:.2f}",
        "lambda": config.as_dict()["lambda"],
        "jaccard_min": config.as_dict()["jaccard_min"],
        "max_neighbours": config.max_neighbours,
        "tuned": False,
        "p_i_c_coincide": shared and coverage_complete and coincide_cases == len(prepared) and len(prepared) > 0,
        "p_i_c_coincide_cases": coincide_cases,
        "p_i_c_diverge_cases": diverge_cases,
        "arms_separate": arms_separate,
        "reporting_label": None if arms_separate or not coverage_complete else label,
        "coverage_complete": coverage_complete,
        "failures": failures,
        "structural_violations": structural,
        "flyable": fly["flyable"],
        "flyable_reason": fly["reason"],
        "identical_to_u": fly["identical_to_u"],
        "identical_to_official_l": fly["identical_to_official_l"],
        "cases": len(classified_rows),
        "cases_with_new_request": fly["cases_with_new_request"],
        "new_request_ids": [
            f"{row['category']}/{row['id']}" for row in prepared if row.get("new_request")
        ],
        "ready_for_evaluation": ready,
        "provider_called": False,
        "network_used": False,
        "u_hash_mismatches": u_mismatch,
        "local_token_sums": token_sums,
        "unique_request_groups_u_and_setting": _group_counts(prepared, label),
        "categories": categories,
        "cap_was_loosened": False,
    }
    return report, classified_rows


def reproduce_official_hashes(study, official_rows, budget, sensitivity) -> dict:
    """Recompute r=0.75 with the official config and compare it to the committed hashes."""
    payload, rows = characterize_study(study, budget, sensitivity, DEFAULT_CONFIG)
    tokenizer_name = payload["counting"]["budget_tokenizer"]
    official = _index_rows(official_rows)
    mismatches = []
    if len(rows) != len(official_rows):
        mismatches.append({"reason": "row_count", "found": len(rows), "official": len(official_rows)})
    for row in rows:
        key = (row.get("category"), row.get("id"))
        previous = official.get(key)
        if previous is None:
            mismatches.append({"category": row.get("category"), "id": row.get("id"), "reason": "missing_official_row"})
            continue
        if bool(row.get("preparation_failure")) != bool(previous.get("preparation_failure")):
            mismatches.append({"category": key[0], "id": key[1], "reason": "preparation_failure_mismatch"})
            continue
        if row.get("preparation_failure"):
            continue
        if row.get("hashes") != previous.get("hashes"):
            mismatches.append({"category": key[0], "id": key[1], "reason": "hash_mismatch"})
        elif not (previous["hashes"]["P"] == previous["hashes"]["I"] == previous["hashes"]["C"]):
            mismatches.append({"category": key[0], "id": key[1], "reason": "official_p_i_c_diverge"})
    local_sums = {
        name: _token_block(payload["categories"][name], tokenizer_name)["sums"] for name in DENOMINATORS
    }
    return {
        "config": "week1.0",
        "retention_r": "3/4",
        "matched": not mismatches,
        "cases": len(rows),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches[:30],
        "local_token_sums": {
            "tokenizer": tokenizer_name,
            "by_category": local_sums,
            "local_only": True,
            "provider_T": False,
        },
    }


def write_audit(study, official_rows, arm_rows, out_dir: Path, budget, sensitivity, *, bfcl_root: Path | None = None) -> dict:
    data_pin = data_pin_for_root(bfcl_root) if bfcl_root is not None else {"matched": False, "source": "not_supplied"}
    payload, hash_rows = audit_study(
        study, official_rows, arm_rows, budget, sensitivity, data_pin=data_pin
    )
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dump_public(out_dir / "audit.json", payload)
    for label, rows in hash_rows.items():
        public_rows = [_public_hash_row(row) for row in rows]
        dump_jsonl(out_dir / f"{label.lower()}_request_hashes.jsonl", public_rows)
    return payload


def _h50_h25_identity(hash_rows: dict) -> dict:
    left = {(row.get("category"), row.get("id")): row for row in hash_rows["H50"]}
    right = {(row.get("category"), row.get("id")): row for row in hash_rows["H25"]}
    if set(left) != set(right):
        raise ValueError("H50 and H25 case ids differ")
    different = []
    for key, row in left.items():
        other = right[key]
        if row.get("preparation_failure") or other.get("preparation_failure"):
            different.append({"category": key[0], "id": key[1], "reason": "preparation_failure"})
            continue
        if row.get("hashes") != other.get("hashes"):
            different.append({"category": key[0], "id": key[1]})
    return {
        "cases": len(left),
        "identical_cases": len(left) - len(different),
        "different_cases": len(different),
        "different_ids": different,
        "complete_requests_identical": not different and len(left) == 840,
        "note": (
            "H50 and H25 are compared with each other here. Flyability is still "
            "identity versus U and versus official L, not versus the other cap."
        ),
    }


def _public_hash_row(row: dict) -> dict:
    if row.get("preparation_failure"):
        return {
            "category": row.get("category"),
            "id": row.get("id"),
            "preparation_failure": True,
        }
    return {
        "C_vs_I": row["C_vs_I"],
        "C_vs_U": row["C_vs_U"],
        "I_vs_U": row["I_vs_U"],
        "P_vs_I": row["P_vs_I"],
        "P_vs_U": row["P_vs_U"],
        "category": row["category"],
        "hashes": row["hashes"],
        "id": row["id"],
        "identical_to_official_l": row["identical_to_official_l"],
        "identical_to_u": row["identical_to_u"],
        "new_request": row["new_request"],
        "official_l_hash": row["official_l_hash"],
        "p_i_c_coincide": row["p_i_c_coincide"],
        "preparation_failure": False,
        "u_matches_official_u": row["u_matches_official_u"],
    }


def _category_report(name, summary, rows, failures, tokenizer_name, reproduction_ok) -> dict:
    prepared = [row for row in rows if not row.get("preparation_failure")]
    n = summary["n_records"]
    identical_u = sum(1 for row in prepared if row["identical_to_u"])
    identical_l = sum(1 for row in prepared if row["identical_to_official_l"])
    new_cases = sum(1 for row in prepared if row["new_request"])
    coincide = sum(1 for row in prepared if row["p_i_c_coincide"])
    hash_c_vs_i = sum(1 for row in prepared if row.get("C_vs_I"))
    measured_c_vs_i = summary["request_differences"].get("C_vs_I", 0)
    token_sums = _token_block(summary, tokenizer_name)
    fields = {
        method: {
            "counts": summary["fields"][method]["counts"],
            "reasons": summary["fields"][method]["reasons"],
            "changed_by_role": summary["fields"][method]["changed_by_role"],
        }
        for method in ARM_NAMES
    }
    uplift = {
        method: {
            "fields": summary["fields"][method]["counts"].get("uplift", 0),
            "description_fields": summary["fields"][method]["counts"].get("fields", 0),
            "single_span": summary["fields"][method]["counts"].get("uplift_single_span", 0),
            "multi_span": summary["fields"][method]["counts"].get("uplift_multi_span", 0),
        }
        for method in ARM_NAMES
    }
    coverage_complete = (
        summary["preparation_failures"] == 0
        and summary["prepared_records"] == DENOMINATORS[name]
        and n == DENOMINATORS[name]
        and not failures
    )
    measurement_agrees = hash_c_vs_i == measured_c_vs_i
    ready = coverage_complete and reproduction_ok and measurement_agrees
    return {
        "category": name,
        "role": summary["role"],
        "n_records": n,
        "prepared_records": summary["prepared_records"],
        "preparation_failures": summary["preparation_failures"],
        "failures": failures,
        "coverage_complete": coverage_complete,
        "p_i_c_coincide": bool(prepared) and coincide == len(prepared),
        "p_i_c_coincide_cases": coincide,
        "p_i_c_diverge_cases": len(prepared) - coincide,
        "request_identity_versus_u": {
            "cases_identical": identical_u,
            "cases_different": len(prepared) - identical_u,
            "complete_requests_identical": bool(prepared) and identical_u == len(prepared),
        },
        "request_identity_versus_official_l": {
            "cases_identical": identical_l,
            "cases_different": len(prepared) - identical_l,
            "complete_requests_identical": bool(prepared) and identical_l == len(prepared),
        },
        "cases_with_new_request": new_cases,
        "per_arm_cases_different_from_u": {
            method: sum(1 for row in prepared if row["hashes"][method] != row["hashes"]["U"]) for method in ARM_NAMES
        },
        "per_arm_cases_different_from_official_l": {
            method: sum(
                1
                for row in prepared
                if row.get("official_l_hash") and row["hashes"][method] != row["official_l_hash"]
            )
            for method in ARM_NAMES
        },
        "local_token_sums": token_sums,
        "uplift": uplift,
        "contrast_activity_f": summary["active_fraction_c_vs_i"],
        "c_minus_i_cases": measured_c_vs_i,
        "c_minus_i_fields": summary["selection_differences"]["fields"].get("C_vs_I", 0),
        "hash_c_minus_i_cases": hash_c_vs_i,
        "measurement_agrees": measurement_agrees,
        "stop_and_field_status": {"note": STATUS_NOTE, "arms": fields},
        "ready_for_evaluation": ready,
        "provider_called": False,
        "network_used": False,
    }


def _token_block(summary, tokenizer_name) -> dict:
    block = summary["local_cohort_ratio_vs_U"]
    sums = {}
    ratios = {}
    for method in ("U", *ARM_NAMES):
        ratio = block[method][tokenizer_name]
        sums[method] = ratio["sum_variant"]
        ratios[method] = {
            "ratio_of_means": ratio["ratio_of_means"],
            "sum_baseline": ratio["sum_baseline"],
            "sum_variant": ratio["sum_variant"],
            "n": ratio["n"],
            "local_only": True,
            "provider_T": False,
        }
    return {
        "tokenizer": tokenizer_name,
        "sums": sums,
        "versus_u": ratios,
        "local_only": True,
        "provider_T": False,
    }


def _sum_tokens(categories, tokenizer_name) -> dict:
    sums = {method: 0 for method in ("U", *ARM_NAMES)}
    for category in categories.values():
        for method, value in category["local_token_sums"]["sums"].items():
            sums[method] += value
    shared = len(set(sums[method] for method in ARM_NAMES)) == 1
    return {
        "tokenizer": tokenizer_name,
        "sums": sums,
        "p_i_c_sums_equal": shared,
        "shared_sum": sums["P"] if shared else None,
        "local_only": True,
        "provider_T": False,
    }


def _group_counts(prepared: list[dict], label: str) -> dict:
    counts = {name: 0 for name in DENOMINATORS}
    for row in prepared:
        hashes = row["hashes"]
        if row["p_i_c_coincide"]:
            values = {hashes["U"], hashes["P"]}
        else:
            values = {hashes[name] for name in ("U", *ARM_NAMES)}
        counts[row["category"]] += len(values)
    counts["all_categories"] = sum(counts[name] for name in DENOMINATORS)
    counts["label_when_p_i_c_coincide"] = label
    counts["includes_E"] = False
    return counts


def _index_rows(rows: list[dict]) -> dict:
    index = {}
    for row in rows:
        key = (row.get("category"), row.get("id"))
        if key in index:
            raise ValueError(f"duplicate hash row {key}")
        index[key] = row
    return index


def data_pin_for_root(bfcl_root: Path) -> dict:
    data_dir = resolve_data_dir(bfcl_root)
    found = {}
    mismatches = []
    for name, expected in PINNED_DATA_SHA256.items():
        path = data_dir / name
        digest = file_sha256(path)
        found[name] = digest
        if digest != expected:
            mismatches.append(name)
    prefix_ok = all(name.startswith(VERSION_PREFIX) for name in PINNED_DATA_SHA256)
    return {
        "matched": not mismatches and prefix_ok,
        "bfcl_commit": PINS["bfcl_commit"],
        "files": found,
        "mismatches": mismatches,
    }


def write_full_catalogue_audit(
    study,
    official_rows: list[dict],
    h50_rows: list[dict],
    out_dir: Path,
    budget,
    sensitivity,
    *,
    bfcl_root: Path,
    counter,
) -> dict:
    """Audit settings A and B and write the plan index. No provider call."""
    from tool_compression.exploratory_flight import build_full_catalogue_plans

    data_pin = data_pin_for_root(bfcl_root)
    reproduction = reproduce_official_hashes(study, official_rows, budget, sensitivity)
    reproduction_ok = bool(reproduction["matched"] and data_pin.get("matched"))
    settings = {}
    hash_rows = {}
    plans = {}
    for label in FULL_CATALOGUE_LABELS:
        report, rows = audit_setting(
            study,
            label,
            official_rows,
            budget,
            sensitivity,
            hash_reproduction_matched=reproduction["matched"],
            data_pin_matched=bool(data_pin.get("matched")),
        )
        decision = full_catalogue_plan_decision(
            rows,
            coverage_complete=report["coverage_complete"],
            hash_reproduction_matched=reproduction_ok,
        )
        if report.get("u_hash_mismatches") or not report["ready_for_evaluation"]:
            decision = {
                **decision,
                "plan_ready": False,
                "reason": "u_hash_does_not_match_official_u"
                if report.get("u_hash_mismatches")
                else decision["reason"],
            }
        report["identity"] = _identity_summary(report)
        report["differing_only_would_send"] = report["flyable"]
        report["differing_only_reason"] = report["flyable_reason"]
        report["full_catalogue_plan_ready"] = bool(decision["plan_ready"] and report["ready_for_evaluation"])
        report["full_catalogue_reason"] = decision["reason"]
        report["drops_identical_to_official_l"] = False
        report["cases_identical_to_official_l"] = decision["cases_identical_to_official_l"]
        report["cases_planned"] = decision["cases_planned"] if report["full_catalogue_plan_ready"] else 0
        report["paid_call_started"] = False
        report["lambda_loosened_to_force_a_difference"] = False
        report["protections_loosened"] = False
        settings[label] = report
        hash_rows[label] = rows
        if report["full_catalogue_plan_ready"]:
            label_plans, stats = build_full_catalogue_plans(study, label, counter)
            if stats["preparation_failures"]:
                raise RuntimeError("full catalogue preparation failed")
            if stats["cases_planned"] != report["cases_planned"]:
                raise RuntimeError("plan case count does not match the audit")
            if stats["cases_with_new_request"] != report["cases_with_new_request"]:
                raise RuntimeError("plan identity does not match the audit")
            if stats["identical_to_official_l"] != report["identical_to_official_l"]:
                raise RuntimeError("plan official-L identity does not match the audit")
            if stats["identical_to_official_l_cases_planned"] != report["cases_identical_to_official_l"]:
                raise RuntimeError("plan official-L count does not match the audit")
            if stats["p_i_c_coincide"] != report["p_i_c_coincide"]:
                raise RuntimeError("plan arm coincidence does not match the audit")
            if report["p_i_c_coincide"] and stats["groups"] != stats["cases_planned"]:
                raise RuntimeError("coinciding arms did not plan one request per case")
            report["plan"] = {
                "cases_planned": stats["cases_planned"],
                "groups": stats["groups"],
                "drops_identical_to_official_l": False,
                "identical_to_official_l_cases_planned": stats["identical_to_official_l_cases_planned"],
                "cases_with_new_request": stats["cases_with_new_request"],
                "started": False,
                "live": False,
                "provider_called": False,
                "network_used": False,
                "paid_call_started": False,
                "ceiling_supplied": False,
            }
            plans[label] = [_plan_index_row(plan) for plan in label_plans]
        else:
            report["plan"] = {
                "cases_planned": 0,
                "groups": 0,
                "drops_identical_to_official_l": False,
                "started": False,
                "provider_called": False,
                "paid_call_started": False,
                "ceiling_supplied": False,
            }
            plans[label] = []
    h50_identity = _hash_identity(hash_rows[A_LABEL], h50_rows, "setting A", "H50")
    comparison = build_token_comparison(settings, reproduction["local_token_sums"]["by_category"])
    payload = {
        "base_commit": FULL_CATALOGUE_BASE_COMMIT,
        "status": "exploratory_only",
        "revises_official_C_versus_U": False,
        "official_baseline_closed": True,
        "official_target_lowered": False,
        "official_result_rewritten": False,
        "official_result": CLOSED_OFFICIAL_RESULT,
        "sample_size": sum(DENOMINATORS.values()),
        "denominators": dict(DENOMINATORS),
        "evaluation_method": "bfcl evaluate from saved outputs",
        "generation_model_when_flown": "deepseek-flash",
        "thinking": "disabled",
        "decoder_alias_is_scoring_only": True,
        "provider_called": False,
        "network_used": False,
        "paid_call_started": False,
        "lambda_or_protections_loosened_to_force_a_difference": False,
        "official_compressor": "week1.0 P/I/C",
        "official_hash_reproduction": reproduction,
        "data_pin": data_pin,
        "pins": dict(PINS),
        "counting": {
            "budget_tokenizer": budget.name,
            "budget_backend": getattr(budget, "backend", budget.name),
            "sensitivity_tokenizer_not_used_for_selection": sensitivity.name,
            "provider_usage_measured": False,
        },
        "local_sums_are_not_provider_T": True,
        "h50_reconfirmation": h50_identity,
        "settings": settings,
        "comparison": comparison,
        "later_live_run": _later_live_run(),
    }
    if payload["provider_called"] or payload["network_used"] or payload["paid_call_started"]:
        raise RuntimeError("full-catalogue audit must not call a provider")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dump_public(out_dir / "audit.json", payload)
    for label, rows in hash_rows.items():
        dump_jsonl(out_dir / f"{label.lower()}_request_hashes.jsonl", [_public_hash_row(row) for row in rows])
    for label, index in plans.items():
        dump_jsonl(out_dir / f"{label.lower()}_plan_index.jsonl", index)
    text = render_full_catalogue_markdown(payload)
    (out_dir / "COMPARISON.md").write_text(text, encoding="utf-8")
    return payload


def build_token_comparison(settings: dict, official_local_by_category: dict) -> dict:
    """Local sums beside the closed billed baseline. Unflown provider T stays absent."""
    official_s = CLOSED_OFFICIAL_RESULT["S_LU"]
    official_u = CLOSED_OFFICIAL_RESULT["primary_U_provider_prompt_tokens"]
    numerator, denominator = official_s.split("/")
    if int(denominator) != official_u:
        raise ValueError("official S_LU denominator is not the recorded primary U T")
    derived_l = official_u - int(numerator)
    categories = {}
    totals = {"U": 0, "official_L": 0, A_LABEL: 0, B_LABEL: 0}
    for name in DENOMINATORS:
        official = official_local_by_category[name]
        if len({official["P"], official["I"], official["C"]}) != 1:
            raise ValueError("official local P/I/C sums diverge")
        row = {"U": official["U"], "official_L": official["P"]}
        for label in FULL_CATALOGUE_LABELS:
            sums = settings[label]["categories"][name]["local_token_sums"]["sums"]
            if len({sums["P"], sums["I"], sums["C"]}) != 1:
                raise ValueError(f"{label} local P/I/C sums diverge in {name}")
            row[label] = sums["P"]
            if sums["U"] != official["U"]:
                raise ValueError(f"{label} local U sum does not match the official recomputation")
        categories[name] = row
        for key, value in row.items():
            totals[key] += value
    local_kind = "local_o200k_base_sum"
    comparison = {
        "exploratory_only": True,
        "revises_official_S_LU": False,
        "revises_official_C_versus_U": False,
        "local_tokenizer": "o200k_base",
        "local_sums_are_not_provider_T": True,
        "denominator_note": (
            "Local o200k_base sums count the prepared request serialization. "
            "Official S_LU uses provider prompt_tokens on the primary cohort. "
            "Those denominators differ. Local savings do not revise S_LU."
        ),
        "official_billed": {
            "cohort": "primary multiple 200",
            "basis": "provider_prompt_tokens",
            "cache_subtracted": False,
            "price_weighted": False,
            "U": official_u,
            "S_LU": official_s,
            "S_LU_approximation": CLOSED_OFFICIAL_RESULT["S_LU_approximation"],
            "derived_L": derived_l,
            "derived_L_note": "Subtract the closed S_LU numerator from the recorded primary U T.",
            "all_840_provider_T": None,
            "provider_T_A": None,
            "provider_T_B": None,
            "three_case_h50_provider_figures_spliced": False,
        },
        "local_o200k_base": {
            "by_category": categories,
            "all_840": totals,
            "saving_versus_U_all_840": {
                "official_L": _saving(totals["U"], totals["official_L"], local_kind + "_all_840"),
                A_LABEL: _saving(totals["U"], totals[A_LABEL], local_kind + "_all_840"),
                B_LABEL: _saving(totals["U"], totals[B_LABEL], local_kind + "_all_840"),
            },
            "saving_versus_official_L_all_840": {
                A_LABEL: _saving(totals["official_L"], totals[A_LABEL], local_kind + "_official_L_all_840"),
                B_LABEL: _saving(totals["official_L"], totals[B_LABEL], local_kind + "_official_L_all_840"),
            },
            "primary_saving_versus_U": {
                "official_L": _saving(categories["multiple"]["U"], categories["multiple"]["official_L"], local_kind + "_primary"),
                A_LABEL: _saving(categories["multiple"]["U"], categories["multiple"][A_LABEL], local_kind + "_primary"),
                B_LABEL: _saving(categories["multiple"]["U"], categories["multiple"][B_LABEL], local_kind + "_primary"),
            },
        },
        "provider_T_for_unflown_arms": {A_LABEL: None, B_LABEL: None},
    }
    return comparison


def render_full_catalogue_markdown(payload: dict) -> str:
    """Operator write-up. Numbers come from the audit payload."""
    official = payload["official_result"]
    comparison = payload["comparison"]
    billed = comparison["official_billed"]
    local = comparison["local_o200k_base"]
    totals = local["all_840"]
    later = payload["later_live_run"]
    lines = [
        "# Exploratory full-catalogue comparison",
        "",
        "This comparison is exploratory only. Official C versus U stays the closed result. "
        f"Official S_LU stays {official['S_LU']} (about {official['S_LU_approximation']}). "
        "The 10% token target stays 1/10. No provider call was made.",
        "",
        "Sample size is 840 cases: multiple 200, simple_python 400, irrelevance 240. "
        "The evaluation method is official `bfcl evaluate` on saved outputs. "
        "The handler alias `DeepSeek-V3.2-Exp-FC` is scoring-only. "
        "A later generation stays `deepseek-flash` with thinking disabled.",
        "",
        "## Three measurements",
        "",
        "1. Baseline, already collected and not re-flown. r=0.75, λ=1/2, thinking off, "
        f"{official['model_version']}. Primary accuracy U {official['primary_accuracy']['U']} (93.00%), "
        f"L {official['primary_accuracy']['L']} (92.50%), E {official['primary_accuracy']['E']} (93.00%). "
        f"S_LU = {official['S_LU']}.",
        "2. Setting A. r=0.50, λ=1/2, all 840 cases. "
        f"Spec `{payload['settings']['A']['spec_version']}`.",
        "3. Setting B. r=0.75, λ=1/4, all 840 cases. "
        f"Spec `{payload['settings']['B']['spec_version']}`. "
        "Jaccard stays at least 1/5, the neighbour cap stays at two, and the tokenizer stays `o200k_base`.",
        "",
        "H25 (r=0.25, λ=1/2) stays on the #7 audit. These measurements are the closed baseline, setting A, and setting B.",
        "",
        "## Request identity",
        "",
    ]
    for label in ("A", "B"):
        setting = payload["settings"][label]
        identity = setting["identity"]
        lines.append(f"### Setting {label}")
        lines.append("")
        lines.append(
            f"P, I, and C coincide on {setting['p_i_c_coincide_cases']} of {setting['cases']} cases. "
            f"Cases identical to U: {identity['versus_u']['cases_identical']}. "
            f"Cases identical to official L: {identity['versus_official_l']['cases_identical']}. "
            f"Cases different from official L: {identity['versus_official_l']['cases_different']}."
        )
        lines.append("")
        if setting["identical_to_official_l"]:
            lines.append(
                "Every request is identical to official L. "
                "λ stays 1/4, and protections, Jaccard, the neighbour cap, and the tokenizer stay as frozen. "
                "The full-catalogue plan still lists every case and does not start a paid call."
            )
        else:
            joined = ", ".join(f"`{item}`" for item in setting["new_request_ids"])
            lines.append(
                f"Requests that differ from both U and official L: {joined}. "
                "The full-catalogue plan still lists every case, including the requests identical to official L."
            )
        lines.append("")
        lines.append("| Category | Cases | Identical to U | Identical to official L | Contrast f | C−I cases | C−I fields |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
        for name in ("multiple", "simple_python", "irrelevance"):
            category = setting["categories"][name]
            fraction = category["contrast_activity_f"]
            lines.append(
                f"| {name} | {category['n_records']} | "
                f"{category['request_identity_versus_u']['cases_identical']} | "
                f"{category['request_identity_versus_official_l']['cases_identical']} | "
                f"{fraction['numerator']}/{fraction['denominator']} | "
                f"{category['c_minus_i_cases']} | {category['c_minus_i_fields']} |"
            )
        lines.append("")
    h50 = payload["h50_reconfirmation"]
    lines.extend(
        [
            f"Setting A matches the #7 H50 request hashes on {h50['identical_cases']} of {h50['cases']} cases. "
            "The flight prepared here is the full 840-case plan. It is separate from the #7 plan, which sends only the cases that differ from official L.",
            "",
            "## Token savings",
            "",
            "This table is exploratory only. It leaves official S_LU where the closed result put it.",
            "",
            "### Official billed basis",
            "",
            "Cohort: primary `multiple`, 200 cases. Basis: provider `prompt_tokens`. "
            "Cache hits stay in T. Prices stay off T.",
            "",
            f"- U = {billed['U']}",
            f"- S_LU = {billed['S_LU']} ≈ {billed['S_LU_approximation']}",
            f"- Derived primary L = {billed['derived_L']}, from {billed['U']} minus the closed numerator {billed['S_LU'].split('/')[0]}. "
            "That subtraction restates the closed ratio. It is not a new measurement.",
            "- Provider T for all 840 cases is absent from the closed figures used here.",
            "- Provider T for setting A is not measured.",
            "- Provider T for setting B is not measured.",
            "- The later 3-case H50 provider figures stay out of this table.",
            "",
            "### Local `o200k_base` sums",
            "",
            comparison["denominator_note"],
            "",
            "| Category | U | Official L | A | B |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for name in ("multiple", "simple_python", "irrelevance"):
        row = local["by_category"][name]
        lines.append(f"| {name} | {row['U']} | {row['official_L']} | {row['A']} | {row['B']} |")
    lines.append(
        f"| all 840 | {totals['U']} | {totals['official_L']} | {totals['A']} | {totals['B']} |"
    )
    lines.append("")
    lines.append("Local ratio of sums versus U, `(sum U − sum arm) / sum U`:")
    lines.append("")
    for label in ("official_L", "A", "B"):
        saving = local["saving_versus_U_all_840"][label]
        lines.append(
            f"- {label}, all 840: {saving['numerator']}/{saving['denominator']} ≈ {_percent(saving['numerator'], saving['denominator'])}"
        )
    for label in ("official_L", "A", "B"):
        saving = local["primary_saving_versus_U"][label]
        lines.append(
            f"- {label}, primary: {saving['numerator']}/{saving['denominator']} ≈ {_percent(saving['numerator'], saving['denominator'])}"
        )
    lines.append("")
    versus_l = local["saving_versus_official_L_all_840"]
    lines.append(
        f"Local tokens versus official L, all 840: A removes {versus_l['A']['numerator']}; "
        f"B removes {versus_l['B']['numerator']}."
    )
    lines.append("")
    lines.extend(
        [
            "## Later live run and scoring",
            "",
            "The plan commands require `--ceiling-cny`. The code supplies no ceiling and does not read one from the environment. "
            f"An operator may pass the remaining authorized amount, ¥{later['remaining_authorized_cny']} of ¥{later['authorized_total_cny']}, as that flag. "
            "This package does not pass it.",
            "",
            f"The locked pre-call reserve stays ¥{later['pre_call_reserve_cny']}. "
            f"Under the remaining authorized amount that reserve allows {later['max_calls_before_reserve_stops']} calls before the run stops. "
            f"The plan still lists {later['cases_in_plan']} cases. "
            "A stopped run has incomplete coverage, and its partial `prompt_tokens` sum is not a cohort T. "
            "This package leaves the reserve unchanged.",
            "",
            "Plan only, no provider call. Repeat with `--setting B` and a separate `--out` directory.",
            "",
            "```bash",
            "python -m tool_compression full-catalogue-flight \\",
            "  --setting A \\",
            "  --ceiling-cny \"$EXPLORATORY_CEILING_CNY\" \\",
            "  --audit evidence/full-catalogue/audit.json \\",
            "  --bfcl-root PATH_TO_GORILLA \\",
            "  --out artifacts/full-catalogue/A",
            "```",
            "",
            "A later operator adds `--live` only after exporting `DEEPSEEK_API_KEY` and supplying the ceiling. "
            "Thinking stays disabled. Generation under `DeepSeek-V3.2-Exp-FC` is refused.",
            "",
            "Score a finished live run from saved outputs. This command does not generate:",
            "",
            "```bash",
            "python -m tool_compression full-catalogue-flight \\",
            "  --setting A \\",
            "  --bfcl-root PATH_TO_GORILLA \\",
            "  --out artifacts/full-catalogue/A \\",
            "  --score",
            "```",
            "",
            "That runs `python -m bfcl_eval evaluate` with `--model DeepSeek-V3.2-Exp-FC` and "
            "`--test-category multiple,simple_python,irrelevance`. The alias is the decoder directory for saved outputs.",
            "",
            "Add billed-basis T to this same comparison from `flight_summary.json` field `billed_basis_T_prompt_tokens`, "
            "and from each saved result row's `input_token_count`. Sum provider `prompt_tokens` on received calls. "
            "Keep cache hits in the sum. Leave prices off the sum. "
            "Put the figure on the arm that was flown, and name the cohort (primary 200, or all 840, only when coverage is complete). "
            "Leave official S_LU unchanged. Leave an unflown arm blank. Leave a partial run out of the cohort ratio.",
            "",
            "Re-run the offline audit with:",
            "",
            "```bash",
            "python -m tool_compression full-catalogue-audit \\",
            "  --bfcl-root PATH_TO_GORILLA \\",
            "  --out evidence/full-catalogue",
            "```",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def _later_live_run() -> dict:
    from decimal import Decimal

    from tool_compression.flight_spec import format_cny, pre_call_reserve_cny

    remaining = Decimal("48.74670004")
    reserve = pre_call_reserve_cny()
    return {
        "command": "full-catalogue-flight",
        "ceiling_flag": "--ceiling-cny",
        "ceiling_environment_name": "EXPLORATORY_CEILING_CNY",
        "code_reads_environment": False,
        "default_in_code": False,
        "this_package_starts_live": False,
        "remaining_authorized_cny": format(remaining, "f"),
        "authorized_total_cny": "50",
        "pre_call_reserve_cny": format_cny(reserve),
        "reserve_changed": False,
        "max_calls_before_reserve_stops": int(remaining / reserve),
        "cases_in_plan": 840,
        "scoring": "bfcl evaluate on saved outputs",
        "generation_model": "deepseek-flash",
        "thinking": "disabled",
        "decoder_alias": "DeepSeek-V3.2-Exp-FC",
        "decoder_generates": False,
        "billed_basis_field": "billed_basis_T_prompt_tokens",
        "per_case_field": "input_token_count",
        "cache_subtracted": False,
        "price_weighted": False,
        "splice_three_case_h50": False,
    }


def _identity_summary(report: dict) -> dict:
    versus_u = {"cases_identical": 0, "cases_different": 0}
    versus_l = {"cases_identical": 0, "cases_different": 0}
    fractions = {}
    c_cases = 0
    c_fields = 0
    for name, category in report["categories"].items():
        versus_u["cases_identical"] += category["request_identity_versus_u"]["cases_identical"]
        versus_u["cases_different"] += category["request_identity_versus_u"]["cases_different"]
        versus_l["cases_identical"] += category["request_identity_versus_official_l"]["cases_identical"]
        versus_l["cases_different"] += category["request_identity_versus_official_l"]["cases_different"]
        fraction = category["contrast_activity_f"]
        fractions[name] = {"numerator": fraction["numerator"], "denominator": fraction["denominator"]}
        c_cases += category["c_minus_i_cases"]
        c_fields += category["c_minus_i_fields"]
    return {
        "versus_u": versus_u,
        "versus_official_l": versus_l,
        "p_i_c_coincide": report["p_i_c_coincide"],
        "p_i_c_coincide_cases": report["p_i_c_coincide_cases"],
        "p_i_c_diverge_cases": report["p_i_c_diverge_cases"],
        "contrast_activity_f": fractions,
        "c_minus_i_cases": c_cases,
        "c_minus_i_fields": c_fields,
        "complete_requests_identical_to_official_l": report["identical_to_official_l"],
        "complete_requests_identical_to_u": report["identical_to_u"],
    }


def _hash_identity(left_rows: list[dict], right_rows: list[dict], left_name: str, right_name: str) -> dict:
    left = _index_rows(left_rows)
    right = _index_rows(right_rows)
    if set(left) != set(right):
        raise ValueError(f"{left_name} and {right_name} case ids differ")
    different = []
    for key, row in left.items():
        other = right[key]
        if row.get("preparation_failure") or other.get("preparation_failure"):
            different.append({"category": key[0], "id": key[1], "reason": "preparation_failure"})
            continue
        if row.get("hashes") != other.get("hashes"):
            different.append({"category": key[0], "id": key[1]})
    return {
        "left": left_name,
        "right": right_name,
        "cases": len(left),
        "identical_cases": len(left) - len(different),
        "different_cases": len(different),
        "different_ids": [f"{item['category']}/{item['id']}" for item in different],
        "complete_requests_identical": not different and len(left) == 840,
    }


def _plan_index_row(plan: dict) -> dict:
    row = {
        "case_id": plan["case_id"],
        "category": plan["category"],
        "identical_to_official_l": plan["identical_to_official_l"],
        "identical_to_u": plan["identical_to_u"],
        "members": list(plan["members"]),
        "new_request": plan["new_request"],
        "request_sha256": plan["request_sha256"],
    }
    if "body" in row or "description" in row:
        raise RuntimeError("plan index must not carry a request body")
    return row


def _saving(baseline: int, variant: int, kind: str) -> dict:
    if baseline < 0 or variant < 0:
        raise ValueError("token sums are non-negative")
    return {
        "numerator": baseline - variant,
        "denominator": baseline,
        "denominator_kind": kind,
        "provider_T": False,
        "revises_official_S_LU": False,
    }


def _percent(numerator: int, denominator: int) -> str:
    from decimal import Decimal, ROUND_HALF_UP

    if denominator <= 0:
        raise ValueError("percent denominator must be positive")
    value = (Decimal(numerator) * Decimal(100) / Decimal(denominator)).quantize(
        Decimal("0.001"), rounding=ROUND_HALF_UP
    )
    return f"{value}%"
