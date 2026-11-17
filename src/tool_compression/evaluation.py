"""Reproducible evaluation scaffold for protocol v1.1.

The default execution record stays empty and unpaid. A frozen validation-flight
record can authorize the DeepSeek client; an incomplete record cannot. Official
accuracy and the 10% provider target are not settled from an unfilled or unrun
record. L is a reporting label only. Representing C by L does not test the
contrast term. Preparation uses the reference implementations and the
description boundary. Group counts from the Week 1 hashes are provisional
under model UNSELECTED.
"""

from collections import Counter
from copy import deepcopy

from tool_compression.config import DEFAULT_CONFIG, PLACEHOLDER_MODEL, SPEC_VERSION, Config
from tool_compression.flight_spec import flight_record_gaps
from tool_compression.grouping import (
    comparison_condition_hashes,
    group_exact_requests,
    local_reporting_label,
)
from tool_compression.implementations import reference_implementations
from tool_compression.prepare import assemble_request, request_hash
from tool_compression.usage import cohort_provider_saving, combine_targets, paired_accuracy_change
from tool_compression.validate import catalogue_violations

PROTOCOL = "1.1"
DENOMINATORS = {
    "multiple": 200,
    "simple_python": 400,
    "irrelevance": 240,
}
OTHER_CHANGE_CASES = 36
CONDITIONS = ("U", "P", "I", "C", "E")
PINS = {
    "bfcl_repository": "https://github.com/ShishirPatil/gorilla",
    "bfcl_commit": "6ea57973c7a6097fd7c5915698c54c17c5b1b6c8",
    "tscg_repository": "https://github.com/SKZL-AI/tscg",
    "tscg_commit": "dfcba63d6190285c45a7c412268dbcc757664ab2",
    "tscg_package": "@tscg/core",
    "tscg_version": "1.4.3",
    "handler": "OpenAICompletionsHandler._query_FC",
    "conversion": "convert_to_tool(..., GORILLA_TO_OPENAPI, OPENAI_COMPLETIONS)",
}
REQUIRED_BEFORE_INFERENCE = (
    "model",
    "provider_options",
    "replicate_count",
    "failure_policy",
    "analysis_configuration",
    "spending_ceiling",
)


class PaidInferenceRefused(RuntimeError):
    """The execution record does not permit a provider call."""


def evaluation_manifest() -> dict:
    return {
        "protocol": PROTOCOL,
        "spec_version": SPEC_VERSION,
        "settings": DEFAULT_CONFIG.as_dict(),
        "pins": dict(PINS),
        "denominators": dict(DENOMINATORS),
        "other_change_cases_not_a_denominator": OTHER_CHANGE_CASES,
        "reference_comparison": "C-U",
        "reference_represented_by": "L where P, I, and C requests coincide",
        "l_is_reporting_label_only": True,
        "representing_c_by_l_tests_contrast": False,
        "week1_primary_active_fraction_f": "0/200",
        "contrast_term_tested": False,
        "official_accuracy_in_scope": False,
        "provider_usage_measurement_in_scope": False,
        "external_comparison": "E-U at the pinned TSCG operating point",
        "e_versus_u_can_satisfy_reference_target": False,
        "target_provider_input_reduction": "1/10",
        "observed_accuracy_loss_limit": "1/50",
        "accuracy_limit_is_non_inferiority": False,
        "paid_inference_authorized": False,
        "paid_inference_implemented": True,
        "paid_inference_scope": "validation-and-prep flight only; the default record stays unauthorized",
        "second_compressor": False,
        "implementation_corrections": [],
        "preparation_outputs_regenerated": False,
        "model": PLACEHOLDER_MODEL,
        "identity": "provisional_until_model_and_options_are_selected",
        "execution_record": execution_record_template(),
    }


def execution_record_template() -> dict:
    return {
        "model": None,
        "provider_options": None,
        "replicate_count": None,
        "failure_policy": None,
        "analysis_configuration": None,
        "paid_inference_authorized": False,
        "spending_ceiling": None,
        "frozen": False,
    }


def execution_record_gaps(record: dict) -> list[str]:
    gaps = [key for key in REQUIRED_BEFORE_INFERENCE if record.get(key) is None]
    if not record.get("paid_inference_authorized"):
        gaps.append("paid_inference_authorized")
    for name in flight_record_gaps(record):
        if name not in gaps:
            gaps.append(name)
    return gaps


def assert_inference_allowed(record: dict) -> None:
    """Allow only a complete, authorized, frozen validation record.

    The empty template is refused. Thinking must be disabled and the ceiling
    must be the locked ¥50 before any provider call.
    """
    gaps = execution_record_gaps(record)
    if gaps:
        raise PaidInferenceRefused(
            "Paid inference is refused. Incomplete or unauthorized execution record: "
            + ", ".join(gaps)
        )


def freeze_execution_record(record: dict) -> dict:
    """Return a frozen copy. Refuses a record that would still be incomplete."""
    candidate = deepcopy(record)
    candidate["frozen"] = True
    gaps = execution_record_gaps(candidate)
    if gaps:
        raise ValueError("cannot freeze an incomplete execution record: " + ", ".join(gaps))
    return candidate


def study_target_status(record: dict, token: dict | None = None, accuracy: dict | None = None) -> dict:
    """The provider target stays unresolved until the analysis record is frozen and supplied."""
    if record.get("analysis_configuration") is None or not record.get("frozen"):
        return {
            "attainment": "unresolved",
            "reason": "analysis_configuration_not_frozen",
            "target_reached": None,
            "target_lowered": False,
        }
    if token is None or accuracy is None:
        return {
            "attainment": "unresolved",
            "reason": "outcomes_not_supplied",
            "target_reached": None,
            "target_lowered": False,
        }
    return combine_targets(token, accuracy)


def reference_target_from_external(saving: float) -> dict:
    """An E–U saving is reported on its own. It cannot pass the C–U target."""
    _ = saving
    return {
        "comparison": "E-U",
        "can_satisfy_c_u_target": False,
        "reference_comparison": "C-U",
    }


def prepare_reference_case(
    catalogue: list,
    messages: list,
    counter,
    *,
    config: Config = DEFAULT_CONFIG,
    category: str = "fixture",
    case_id: str = "case",
    replicate: int = 0,
    model: str = PLACEHOLDER_MODEL,
):
    return prepare_case(
        catalogue,
        messages,
        reference_implementations(),
        config,
        counter,
        category=category,
        case_id=case_id,
        replicate=replicate,
        model=model,
    )


def prepare_case(
    catalogue: list,
    messages: list,
    implementations: dict,
    config: Config,
    counter,
    *,
    category: str = "fixture",
    case_id: str = "case",
    replicate: int = 0,
    model: str = PLACEHOLDER_MODEL,
) -> dict:
    """Run interchangeable implementations, validate the boundary, and group requests."""
    if any(name == "L" for name in implementations):
        raise ValueError("L is a reporting label, not a compression implementation")
    unknown = [name for name in implementations if name not in CONDITIONS]
    if unknown:
        raise ValueError("unknown condition " + ",".join(unknown))
    if "U" not in implementations:
        raise ValueError("U is required")
    caller = deepcopy(catalogue)
    outputs = {}
    for name in CONDITIONS:
        implementation = implementations.get(name)
        if implementation is None:
            continue
        result = implementation.apply(deepcopy(caller), config, counter)
        produced = result["catalogue"]
        violations = catalogue_violations(caller, produced)
        if violations:
            raise RuntimeError(
                "description edit left the allowlisted boundary: " + ", ".join(violations[:8])
            )
        outputs[name] = result
    if catalogue != caller:
        raise RuntimeError("compressor mutated the caller catalogue")
    hashes = {}
    for name, result in outputs.items():
        request = assemble_request(messages, result["catalogue"], model=model)
        hashes[name] = request_hash(request)
    label = local_reporting_label(hashes)
    local_hashes = {name: hashes[name] for name in ("U", "P", "I", "C") if name in hashes}
    conditions = comparison_condition_hashes(local_hashes, hashes.get("E"))
    groups = group_exact_requests(category, case_id, replicate, conditions)
    traces = {
        name: outputs[name].get("traces", [])
        for name in ("P", "I", "C")
        if name in outputs
    }
    return {
        "spec_version": config.spec_version,
        "hashes": hashes,
        "reporting_label": label["label"],
        "label_is_compressor": False,
        "label_is_selected_winner": False,
        "traces": traces,
        "groups": [group.as_dict() for group in groups],
        "catalogues": {name: deepcopy(result["catalogue"]) for name, result in outputs.items()},
        "identity_provisional": model == PLACEHOLDER_MODEL,
        "structural_violations": [],
    }


def summarize_hash_rows(local_rows: list[dict], arm_rows: list[dict]) -> dict:
    """Provisional U/L/E groups from the committed Week 1 request hashes."""
    _require_full_denominators(local_rows)
    arm = {}
    for row in arm_rows:
        key = (row.get("category"), row.get("id"))
        if key in arm:
            raise ValueError("duplicate arm row")
        arm[key] = row
    seen = set()
    histogram = {name: {} for name in DENOMINATORS}
    labelled = {name: 0 for name in DENOMINATORS}
    unlabelled = {name: 0 for name in DENOMINATORS}
    contrast_active = {name: 0 for name in DENOMINATORS}
    failures = {name: 0 for name in DENOMINATORS}
    group_counts = {name: 0 for name in DENOMINATORS}
    logical = 0
    reused = 0
    for row in local_rows:
        category = row["category"]
        key = (category, row.get("id"))
        if key in seen:
            raise ValueError("duplicate local row")
        seen.add(key)
        if row.get("preparation_failure"):
            failures[category] += 1
            continue
        e_row = arm.get(key)
        e_hash = e_row.get("hash") if e_row and e_row.get("ok") and e_row.get("hash") else None
        hashes = row["hashes"]
        label = local_reporting_label(hashes)
        if label["coincide"]:
            labelled[category] += 1
        else:
            unlabelled[category] += 1
        if hashes.get("C") != hashes.get("I"):
            contrast_active[category] += 1
        conditions = comparison_condition_hashes(row["hashes"], e_hash)
        groups = group_exact_requests(category, str(row["id"]), 0, conditions)
        group_counts[category] += len(groups)
        logical += sum(len(group.members) for group in groups)
        reused += sum(max(0, len(group.members) - 1) for group in groups)
        size = str(len(groups))
        bucket = histogram[category]
        bucket[size] = bucket.get(size, 0) + 1
    per_replicate = dict(group_counts)
    per_replicate["all_categories"] = sum(group_counts.values())
    return {
        "protocol": PROTOCOL,
        "spec_version": SPEC_VERSION,
        "model": PLACEHOLDER_MODEL,
        "identity": "provisional_until_model_and_options_are_selected",
        "replicate_count_selected": None,
        "provisional_replicate_index": 0,
        "paid_inference": False,
        "paid_inference_authorized": False,
        "denominators": dict(DENOMINATORS),
        "other_change_cases_not_a_denominator": OTHER_CHANGE_CASES,
        "preparation_failures": failures,
        "cases_with_reporting_label_L": labelled,
        "cases_without_reporting_label_L": unlabelled,
        "reporting_label_covers": ["P", "I", "C"],
        "label_is_compressor": False,
        "label_is_selected_winner": False,
        "c_represented_by": "L" if sum(unlabelled.values()) == 0 else "mixed",
        "l_is_reporting_label_only": True,
        "representing_c_by_l_tests_contrast": False,
        "primary_active_fraction_f": {
            "numerator": contrast_active["multiple"],
            "denominator": DENOMINATORS["multiple"],
        },
        "contrast_term_tested": contrast_active["multiple"] > 0,
        "official_accuracy_in_scope": False,
        "provider_usage_measurement_in_scope": False,
        "size_histogram": histogram,
        "provisional_unique_request_groups_per_replicate": per_replicate,
        "logical_condition_assignments": logical,
        "reused_logical_assignments": reused,
        "independent_responses_per_replicate": per_replicate["all_categories"],
        "physical_attempts": 0,
        "provider_usage_measured": False,
        "target_provider_input_reduction": "1/10",
        "target_reached": None,
        "target_status": "unresolved_provider_usage_not_measured",
        "reference_comparison": "C-U",
        "e_versus_u_can_satisfy_reference_target": False,
        "implementation_corrections": [],
        "preparation_outputs_regenerated": False,
        "pins": dict(PINS),
    }


def primary_provider_saving(total_input_u: list, total_input_l: list) -> dict:
    _reject_other_change_subset(total_input_u, total_input_l)
    return cohort_provider_saving(
        total_input_u,
        total_input_l,
        denominator=DENOMINATORS["multiple"],
    )


def primary_accuracy_change(correct_u: list, correct_l: list) -> dict:
    _reject_other_change_subset(correct_u, correct_l)
    return paired_accuracy_change(
        correct_u,
        correct_l,
        denominator=DENOMINATORS["multiple"],
    )


def _reject_other_change_subset(*series) -> None:
    for values in series:
        if len(values) == OTHER_CHANGE_CASES:
            raise ValueError("the 36 other-change cases are not the primary denominator")


def _require_full_denominators(local_rows: list[dict]) -> None:
    counts = Counter(row["category"] for row in local_rows)
    extra = set(counts) - set(DENOMINATORS)
    if extra:
        raise ValueError("unexpected category")
    for name, expected in DENOMINATORS.items():
        if counts.get(name, 0) != expected:
            raise ValueError(f"{name} denominator is {expected}")
