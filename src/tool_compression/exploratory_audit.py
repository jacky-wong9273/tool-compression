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
    ARM_NAMES,
    BASE_COMMIT,
    CLOSED_OFFICIAL_RESULT,
    EXPLORATORY_LABELS,
    classify_case,
    frozen_config,
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
        "retention_decimal": "0.50" if label == "H50" else "0.25",
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
