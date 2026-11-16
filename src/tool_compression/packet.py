"""Render the Week 1 evidence packet from aggregate JSON only."""

from pathlib import Path

from tool_compression.decision import recommend

CATEGORIES = ("multiple", "simple_python", "irrelevance")


def shared_request_groups(local_rows: list[dict], arm_rows: list[dict]) -> dict:
    """Distinct prepared requests per case once a boundary-compatible E hash is included."""
    extra = {}
    for row in arm_rows:
        if row.get("ok") and row.get("hash"):
            extra[(row.get("category"), row.get("id"))] = row["hash"]
    counts: dict[str, dict[str, int]] = {}
    for row in local_rows:
        if row.get("preparation_failure"):
            continue
        hashes = set(row.get("hashes", {}).values())
        found = extra.get((row.get("category"), row.get("id")))
        if found:
            hashes.add(found)
        bucket = counts.setdefault(row["category"], {})
        key = str(len(hashes))
        bucket[key] = bucket.get(key, 0) + 1
    return counts


def write_packet(path: Path, characterization: dict, arm_e: dict) -> dict:
    decision = recommend(characterization, arm_e)
    if decision["utility_aim_established"] or decision["paid_inference"] or decision["phase_2_started"]:
        raise RuntimeError("Week 1 packet invariant failed")
    Path(path).write_text(render(characterization, arm_e, decision), encoding="utf-8")
    return decision


def render(characterization: dict, arm_e: dict, decision: dict) -> str:
    lines = [
        "# Week 1 evidence packet",
        "",
        "Label-blind audit of prepared native requests. This file does not start Phase 2, does not call a model, and does not treat a local token counter as the provider-input target.",
        "",
        "## Decision",
        "",
        f"**{decision['decision']}**",
        "",
        _narrative(characterization, arm_e, decision),
        "",
        "Reasons:",
        "",
    ]
    for reason in decision["reasons"]:
        lines.append(f"- `{reason}`")
    lines.extend(
        [
            "",
            f"Utility aim established: `{decision['utility_aim_established']}`.",
            f"Paid inference in this packet: `{decision['paid_inference']}`.",
            f"Phase 2 started: `{decision['phase_2_started']}`.",
            "",
            "Hard stop: do not harden the package and do not start Phases 2–6 until this packet is reviewed.",
            "",
            "## Provenance",
            "",
            _provenance(characterization, arm_e),
            "",
            "## Original counts and prepared requests",
            "",
            _counts_table(characterization),
            "",
            "The prepared request is the OpenAI Chat Completions object: `messages` (question turn 0 only), `model=\"UNSELECTED\"`, `temperature=0.001`, `store=false`, and `tools` when the catalogue is non-empty. Identity for `f` includes that configuration. No request was truncated to fit a context window. The model is unselected, so no context-window check was applied.",
            "",
            "## Description opportunity",
            "",
            _fields(characterization),
            "",
            "Protection reasons overlap; a span can carry more than one. Single-span fields and optional spans retained by a cue are not mutually exclusive causes. `r=0.75` is a per-field cap, not an exact retained fraction. Floor uplift and frozen fields are separate from nominal attainment. A single-span uplift is mechanical: the only span is protected, so the protected rendering is the original and sits above the nominal cap. A multi-span uplift means the protected rendering itself is already above that cap, so the effective cap is the protected rendering. Whole-span selection can also finish below the nominal cap when the next span does not fit. Suffix-removed counts include fields that also change other text; suffix-only counts do not.",
            "",
            "## Local arms on complete requests",
            "",
            _requests(characterization),
            "",
            "Active fraction `f` uses every original primary case as the denominator. With response sharing and complete scoring, the absolute observed paired C–I correctness difference is at most `f`. That is an interpretation bound, not a power claim. `f=0` means C and I are the same intervention. It does not by itself bound token differences between C and U.",
            "",
            "Local cohort ratios use `(sum U - sum arm) / sum U` on prepared records. The mean of per-case ratios is stored beside it and is not the estimand. These ratios are local serializations. They are not provider `usage.prompt_tokens`.",
            "",
            "## Neighbours and schema proxies",
            "",
            _neighbours(characterization),
            "",
            "The closed-class degree is a diagnostic. The selector does not remove those words. Schema figures are name and type-signature overlap counts, not a claim that prose is unnecessary.",
            "",
            "## Arm E",
            "",
            _arm_e(arm_e),
            "",
            "LLMLingua2 was not started. A second compressor would be a new method project. It is unused both when TSCG meets the boundary and when the decision is to narrow the original scope.",
            "",
            "## Target, workload, and unresolved limits",
            "",
            _target(characterization, arm_e, decision),
            "",
            "## Stop",
            "",
            "Week 1 ends with this packet. Settings stay at the provisional values `r=0.75`, Jaccard at least 1/5, at most two neighbours, and `lambda=1/2`. They were not tuned on labels or on `f`. No benchmark questions, answers, or tool prose are in this packet.",
            "",
        ]
    )
    return "\n".join(lines)


def _narrative(characterization: dict, arm_e: dict, decision: dict) -> str:
    primary = characterization["categories"]["multiple"]
    active = primary["active_fraction_c_vs_i"]
    diffs = primary["request_differences"]
    if decision["decision"] == "narrow-to-local":
        return (
            "Arm E is not a boundary-compatible prepared arm. The original comparative scope, "
            "which includes that external comparator, is not a go. The decision is narrow-to-local. "
            "Incompatible E output is not repaired and is not counted as an E request."
        )
    if "primary_c_requests_identical_to_u" in decision["reasons"]:
        return (
            "Every prepared primary C request equals U. For any accounting that is a function of "
            "the request alone, provider total input tokens are equal and S_CU is zero. That "
            "identity does not use a local tokenizer. Stop."
        )
    return (
        f"Arm E is boundary-compatible (`{arm_e.get('boundary_compatible')}`), so the decision is not narrow-to-local. "
        f"Primary active fraction f is {active['numerator']}/{active['denominator']}. "
        f"Primary request differences are P≠U {diffs.get('P_vs_U', 0)}, I≠U {diffs.get('I_vs_U', 0)}, "
        f"C≠U {diffs.get('C_vs_U', 0)}, C≠I {diffs.get('C_vs_I', 0)}, P≠I {diffs.get('P_vs_I', 0)} "
        f"out of {primary['n_records']} original cases. "
        + (
            "P, I, and C keep the same spans, so they are one intervention. "
            if diffs.get("C_vs_I", 0) == 0 and diffs.get("P_vs_I", 0) == 0
            else "The local arms are not identical. "
        )
        + (
            f"Primary neighbour degree counts are `{primary.get('neighbour_graph', {}).get('degree_counts')}`. "
            "Inactive contrast is not an empty-neighbour artifact on that category. "
        )
        + _suffix_clause(primary)
        + "This measured picture does not justify the original paid comparison. "
        "The 10% provider total-input target is unverified. The local ratios are not a proof that the target is impossible."
    )


def _suffix_clause(primary: dict) -> str:
    suffix_only = primary.get("records_changed_only_by_float_suffix", {}).get("C")
    other = primary.get("records_with_other_description_changes", {}).get("C")
    changed = primary.get("request_differences", {}).get("C_vs_U")
    if suffix_only is None or other is None:
        return ""
    partition = " These two record counts partition C≠U." if suffix_only + other == changed else ""
    return (
        f"Primary records changed only by removing the handler float suffix: {suffix_only}. "
        f"Primary records with any other description change: {other}.{partition} "
    )


def _provenance(characterization: dict, arm_e: dict) -> str:
    provenance = characterization.get("provenance", {})
    documents = characterization.get("source_documents", {})
    tscg = arm_e.get("tscg", {})
    counting = characterization.get("counting", {})
    lines = [
        f"- Spec `{characterization.get('spec_version')}` at settings `{characterization.get('settings', {}).get('retention_r')}`, neighbours `{characterization.get('settings', {}).get('jaccard_min')}` / max `{characterization.get('settings', {}).get('max_neighbours')}`, lambda `{characterization.get('settings', {}).get('lambda')}`.",
        f"- BFCL `{provenance.get('bfcl_repository')}` commit `{provenance.get('bfcl_commit')}`.",
        f"- Conversion `{provenance.get('conversion')}`. Handler `{provenance.get('handler')}`.",
        (
            f"- Conversion parity against the pinned functions: checked `{characterization.get('conversion_parity', {}).get('checked_records')}`, mismatches `{characterization.get('conversion_parity', {}).get('mismatches')}`."
            if characterization.get("conversion_parity")
            else "- Conversion parity was not recorded in this JSON."
        ),
        f"- TSCG `{tscg.get('repository')}` commit `{tscg.get('commit')}`, `{tscg.get('package')}` `{tscg.get('version')}`, entry `{tscg.get('entrypoint')}`, options `{tscg.get('options')}`.",
        f"- Budget tokenizer `{counting.get('budget_tokenizer')}` via `{counting.get('budget_backend')}`. Sensitivity recount `{counting.get('sensitivity_tokenizer')}` via `{counting.get('sensitivity_backend')}`. Sensitivity does not select spans.",
        f"- Revised proposal present: `{documents.get('revised_proposal_present')}`. Agent plan present: `{documents.get('agent_plan_present')}`. Unrevised tex present: `{documents.get('unrevised_proposal_named_by_plan_present')}`.",
        f"- Conflict rule: {documents.get('conflict_rule')}",
        f"- Counting note: {counting.get('note')}",
    ]
    data_files = provenance.get("data_files") or {}
    if data_files:
        lines.append("- Data file sha256 (not vendored):")
        for name in sorted(data_files):
            lines.append(f"  - `{name}` `{data_files[name]}`")
    sources = provenance.get("source_files") or {}
    if sources:
        lines.append("- Pinned BFCL source sha256:")
        for name in sorted(sources):
            lines.append(f"  - `{name}` `{sources[name]}`")
    return "\n".join(lines)


def _counts_table(characterization: dict) -> str:
    header = "| Category | Role | Records | Prepared | Failures | Tools | Tools/record min–max | Unsupported tools | Unlisted descriptions | Max turns |"
    rule = "|---|---|---:|---:|---:|---:|---|---:|---:|---:|"
    rows = [header, rule]
    for name in CATEGORIES:
        item = characterization["categories"][name]
        tools = item["tools_per_record"]
        span = f"{tools.get('min')}–{tools.get('max')}"
        rows.append(
            "| {category} | {role} | {n_records} | {prepared_records} | {preparation_failures} | {n_tools} | {span} | {unsupported_tools} | {unlisted_description_strings} | {max_question_turns} |".format(
                span=span, **item
            )
        )
    return "\n".join(rows)


def _fields(characterization: dict) -> str:
    blocks = []
    for name in CATEGORIES:
        item = characterization["categories"][name]
        blocks.append(f"### {name}")
        blocks.append("")
        blocks.append(
            "Float-suffix fields removed: `{removed}`. Of the changed fields, suffix-only `{suffix_only}`; other description changes `{other}`. Records whose only description edits are suffix removal: `{records}`. Records with any other description change: `{other_records}`.".format(
                removed=item.get("float_suffix_removed_fields"),
                suffix_only=item.get("float_suffix_only_fields"),
                other=item.get("other_changed_fields"),
                records=item.get("records_changed_only_by_float_suffix"),
                other_records=item.get("records_with_other_description_changes"),
            )
        )
        blocks.append(f"Span-choice differences (not only request hashes): `{item.get('selection_differences')}`.")
        blocks.append("")
        blocks.append("| Arm | Fields | Single-span | Single-span with another cue | With optional | Optional kept | Optional all dropped | Changed | Unchanged | Uplift | Frozen | Below nominal | Stopped early |")
        blocks.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for method in ("P", "I", "C"):
            counts = item["fields"][method]["counts"]
            blocks.append(
                "| {method} | {fields} | {single_span} | {single_span_with_other_cue} | {fields_with_optional} | {optional_retained_fields} | {optional_all_dropped_fields} | {changed} | {unchanged} | {uplift} | {frozen} | {achieved_below_nominal} | {stopped_early} |".format(
                    method=method,
                    fields=counts.get("fields", 0),
                    single_span=counts.get("single_span", 0),
                    single_span_with_other_cue=counts.get("single_span_with_other_cue", 0),
                    fields_with_optional=counts.get("fields_with_optional", 0),
                    optional_retained_fields=counts.get("optional_retained_fields", 0),
                    optional_all_dropped_fields=counts.get("optional_all_dropped_fields", 0),
                    changed=counts.get("changed", 0),
                    unchanged=counts.get("unchanged", 0),
                    uplift=counts.get("uplift", 0),
                    frozen=counts.get("frozen", 0),
                    achieved_below_nominal=counts.get("achieved_below_nominal", 0),
                    stopped_early=counts.get("stopped_early", 0),
                )
            )
        blocks.append("")
        blocks.append("Token sums are the local budget tokenizer on fields, not provider totals.")
        blocks.append("")
        blocks.append("| Arm | d | protected-only p | nominal | budget | achieved | span 1 | span 2 | span 3 | span 4+ |")
        blocks.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for method in ("P", "I", "C"):
            counts = item["fields"][method]["counts"]
            blocks.append(
                "| {method} | {tokens_d} | {tokens_p} | {tokens_nominal} | {tokens_budget} | {tokens_achieved} | {span_hist_1} | {span_hist_2} | {span_hist_3} | {span_hist_4_plus} |".format(
                    method=method,
                    tokens_d=counts.get("tokens_d", 0),
                    tokens_p=counts.get("tokens_p", 0),
                    tokens_nominal=counts.get("tokens_nominal", 0),
                    tokens_budget=counts.get("tokens_budget", 0),
                    tokens_achieved=counts.get("tokens_achieved", 0),
                    span_hist_1=counts.get("span_hist_1", 0),
                    span_hist_2=counts.get("span_hist_2", 0),
                    span_hist_3=counts.get("span_hist_3", 0),
                    span_hist_4_plus=counts.get("span_hist_4_plus", 0),
                )
            )
        blocks.append("")
        for method in ("P", "I", "C"):
            reasons = item["fields"][method]["reasons"]
            roles = item["fields"][method]["changed_by_role"]
            blocks.append(f"`{method}` protection-reason span counts `{reasons}`; changed fields by role `{roles}`.")
        blocks.append("")
    return "\n".join(blocks).rstrip()


def _requests(characterization: dict) -> str:
    blocks = []
    for name in CATEGORIES:
        item = characterization["categories"][name]
        diffs = item["request_differences"]
        active = item["active_fraction_c_vs_i"]
        blocks.append(
            f"- `{name}`: P≠U `{diffs.get('P_vs_U', 0)}`, I≠U `{diffs.get('I_vs_U', 0)}`, C≠U `{diffs.get('C_vs_U', 0)}`, C≠I `{diffs.get('C_vs_I', 0)}` of `{item['n_records']}` original records. `f` numerator `{active['numerator']}`, denominator `{active['denominator']}`, value `{active['value']}`."
        )
        blocks.append(f"  Within-case distinct local requests (U/P/I/C): `{item['within_case_distinct_local_requests']}`.")
        ratios = item["local_cohort_ratio_vs_U"]
        for method in ("P", "I", "C"):
            for tokenizer, ratio in ratios[method].items():
                if method == "U":
                    continue
                blocks.append(
                    f"  Local `{method}` vs U on `{tokenizer}`: ratio of means `{ratio.get('ratio_of_means')}`, mean of per-case ratios `{ratio.get('mean_of_per_case_ratios')}`, n `{ratio.get('n')}`."
                )
        blank = item["blank_descriptions_orientation"]
        for key, ratio in blank.items():
            if not isinstance(ratio, dict):
                continue
            blocks.append(
                f"  Blank-description orientation on `{key}`: ratio of means `{ratio.get('ratio_of_means')}`. Not a saving ceiling and not used by the selector."
            )
    return "\n".join(blocks)


def _neighbours(characterization: dict) -> str:
    blocks = []
    for name in CATEGORIES:
        item = characterization["categories"][name]
        graph = item["neighbour_graph"]
        diagnostic = item["diagnostic_closed_class_removed"]
        schema = item["schema_overlap"]
        blocks.append(
            f"- `{name}` degree counts `{graph['degree_counts']}`, mean degree `{graph['mean_degree']}`, undirected pairs at the threshold `{graph['undirected_pairs_at_or_above_threshold']}`, candidate counts `{graph['candidate_counts']}`, tools above the cap of 2 `{graph['tools_with_more_candidates_than_cap']}`."
        )
        blocks.append(
            f"  Closed-class diagnostic (unused by the compressor): degree counts `{diagnostic['degree_counts']}`, undirected pairs `{diagnostic['undirected_pairs_at_or_above_threshold']}`."
        )
        blocks.append(
            f"  Schema: property-name pairs `{schema['within_request_property_name_pairs']}`, pairs at the Jaccard threshold `{schema['pairs_with_jaccard_at_least_threshold']}`, repeated corpus signatures `{schema['corpus_signatures_repeated']}` covering `{schema['tools_in_repeated_signatures']}` tools, within-request duplicate function names `{schema['within_request_duplicate_function_names']}`."
        )
    return "\n".join(blocks)


def _arm_e(arm_e: dict) -> str:
    lines = [
        f"- Check completed: `{arm_e.get('check_completed')}`. Boundary compatible: `{arm_e.get('boundary_compatible')}`.",
        f"- Output repaired: `{arm_e.get('output_repaired')}`. Local cap applied: `{arm_e.get('local_cap_applied')}`.",
        f"- TSCG `estimateTokens` used as provider usage: `{arm_e.get('tscg_estimate_tokens_used_as_provider_usage')}`.",
        f"- Options passed: `{arm_e.get('options')}`. Documented policy: {arm_e.get('documented_policy')}.",
        f"- Principles observed: `{arm_e.get('principles')}`.",
        f"- Runtime failures: `{arm_e.get('runtime_failures')}`. Preprocessing seconds: `{arm_e.get('preprocessing_seconds')}`.",
        f"- Description change classes ({arm_e.get('description_change_classes_scope')}): `{arm_e.get('description_change_classes')}` over `{arm_e.get('description_fields_compared')}` fields.",
        f"- Violation shapes: `{arm_e.get('violation_shapes')}`.",
    ]
    failure = arm_e.get("failure")
    if failure:
        kind = failure.get("kind")
        code = failure.get("returncode")
        lines.append(f"- Process failure kind `{kind}`, return code `{code}`. Stderr is not stored.")
    for name, bucket in (arm_e.get("categories") or {}).items():
        lines.append(
            f"- `{name}`: records `{bucket.get('records')}`, runtime failures `{bucket.get('runtime_failures')}`, boundary failures `{bucket.get('boundary_failures')}`, changed records `{bucket.get('changed_records')}`, distinct from U `{bucket.get('records_distinct_from_U')}`."
        )
        ratios = bucket.get("local_cohort_ratio_vs_U")
        if isinstance(ratios, dict):
            for tokenizer, ratio in ratios.items():
                lines.append(
                    f"  Local E vs U on `{tokenizer}`: ratio of means `{ratio.get('ratio_of_means')}`, mean of per-case ratios `{ratio.get('mean_of_per_case_ratios')}`. Local estimate only."
                )
    if not arm_e.get("boundary_compatible"):
        lines.append(
            "- E is not in the original comparative scope. The decision is narrow-to-local. Incompatible output was not repaired and is not reported as an E request."
        )
    return "\n".join(lines)


def _target(characterization: dict, arm_e: dict, decision: dict) -> str:
    primary = characterization["categories"]["multiple"]
    same = primary["request_differences"].get("C_vs_U", 0) == 0
    identity = (
        "Every prepared primary C request equals U. For any accounting that is a function of the request alone, provider total input tokens are equal and `S_CU=0`. That identity does not use a local tokenizer."
        if same
        else "Some prepared primary C requests differ from U. A local tokenizer cannot show that the 10% provider total-input target is possible or impossible. The target stays unverified."
    )
    groups = primary["within_case_distinct_local_requests"]
    return "\n".join(
        [
            identity,
            f"Decision `{decision['decision']}` does not establish the utility aim.",
            f"Primary within-case distinct local requests: `{groups}`. Distinct requests once a boundary-compatible E hash is added: `{arm_e.get('shared_request_groups')}`. No dollar range is stated: there is no authorized rate card.",
            f"Local preprocessing seconds for P/I/C characterization: `{characterization.get('preprocessing_seconds')}`. Arm E bridge seconds: `{arm_e.get('preprocessing_seconds')}`. These are observations on this machine, not a benchmark.",
            f"Primary local U request-token orientation: `{primary.get('local_U_request_tokens')}`. Baseline context feasibility is unresolved because the model is unselected. Nothing was dropped to force a fit. This orientation is not a context-window result.",
            "Unresolved: provider usage, official accuracy, the selected model and options beyond the pinned handler defaults used here, dependence components, and any rate. Missing usage stays missing. Exploratory caps 0.50 and 0.25 were not run.",
        ]
    )
