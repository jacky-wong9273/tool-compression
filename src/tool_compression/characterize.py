"""Label-blind prepared-request characterization. No model is called."""

from collections import Counter
import hashlib
import time

from tool_compression.adapter import property_names
from tool_compression.compress import compress
from tool_compression.config import METHODS, Config
from tool_compression.convert import FLOAT_SUFFIX
from tool_compression.count import dump_request
from tool_compression.lexical import jaccard_at_least, tool_feature_set
from tool_compression.load import CATEGORY_ROLE, PRIMARY_CATEGORY
from tool_compression.prepare import assemble_request, cohort_ratio, convert_record, request_hash

# Closed-class probe only. The compressor does not import this set.
DIAGNOSTIC_CLOSED_CLASS = frozenset(
    {
        "a", "an", "the", "of", "for", "to", "and", "or", "in", "on", "with", "from", "by",
        "at", "as", "is", "are", "be", "this", "that", "it", "its", "into", "over", "under",
        "via", "than", "then", "if", "so", "but", "not", "no", "nor", "per",
    }
)


def characterize_study(study, budget_counter, sensitivity_counter, config: Config):
    started = time.perf_counter()
    categories = {}
    rows = []
    structural = 0
    for category, records in study.items():
        summary, category_rows, violations = _category(
            category, records, budget_counter, sensitivity_counter, config
        )
        structural += violations
        categories[category] = summary
        rows.extend(category_rows)
    payload = {
        "spec_version": config.spec_version,
        "utility_aim_established": False,
        "structural_violations": structural,
        "counting": {
            "budget_tokenizer": budget_counter.name,
            "budget_backend": getattr(budget_counter, "backend", budget_counter.name),
            "sensitivity_tokenizer": sensitivity_counter.name,
            "sensitivity_backend": getattr(sensitivity_counter, "backend", sensitivity_counter.name),
            "serialization": (
                "json.dumps ensure_ascii=False separators=(',', ':') of "
                "messages, model, temperature, store, tools"
            ),
            "provider_usage_measured": False,
            "note": (
                "Local counts are not provider total-input tokens and do not "
                "establish the 10% target."
            ),
        },
        "settings": config.as_dict(),
        "preprocessing_seconds": round(time.perf_counter() - started, 3),
        "categories": categories,
    }
    return payload, rows


def _category(category, records, budget_counter, sensitivity_counter, config):
    field_stats = {method: Counter() for method in ("P", "I", "C")}
    reason_stats = {method: Counter() for method in ("P", "I", "C")}
    role_changed = {method: Counter() for method in ("P", "I", "C")}
    differences = Counter()
    degrees = []
    candidate_counts = []
    diagnostic_degrees = []
    undirected_pairs = 0
    diagnostic_pairs = 0
    schema_pairs = 0
    schema_pairs_meeting = 0
    signature_counts = Counter()
    within_request_duplicate_names = 0
    tools_per_record = []
    roles = Counter()
    content_types = Counter()
    multi_turn = 0
    max_turns = 0
    unsupported_tools = 0
    unlisted = 0
    cases_with_unsupported = 0
    preparation_failures = 0
    suffix_removed = Counter()
    suffix_only_fields = Counter()
    other_changed_fields = Counter()
    suffix_only_records = Counter()
    other_changed_records = Counter()
    selection_case_differences = Counter()
    selection_field_differences = Counter()
    distinct_groups = Counter()
    blank_tokens = []
    token_lists = {
        method: {budget_counter.name: [], sensitivity_counter.name: []} for method in METHODS
    }
    rows = []
    violations = 0
    for record in records:
        turns = record.get("question") or []
        max_turns = max(max_turns, len(turns))
        if len(turns) != 1:
            multi_turn += 1
        try:
            messages = turns[0]
            if not isinstance(messages, list):
                raise TypeError("question turn is not a message list")
            for message in messages:
                roles[str(message.get("role"))] += 1
                content_types[type(message.get("content")).__name__] += 1
            catalogue = convert_record(record)
        except Exception:
            preparation_failures += 1
            rows.append(
                {"category": category, "id": record.get("id"), "preparation_failure": True}
            )
            continue
        tools_per_record.append(len(catalogue))
        _overlap(catalogue, signature_counts)
        within_request_duplicate_names += _within_duplicates(catalogue)
        undirected_pairs += _pair_count(catalogue, diagnostic=False)
        diagnostic_pairs += _pair_count(catalogue, diagnostic=True)
        schema_hit, schema_total = _schema_pairs(catalogue)
        schema_pairs += schema_total
        schema_pairs_meeting += schema_hit
        outputs = {}
        requests = {}
        for method in METHODS:
            result = compress(catalogue, method, config, budget_counter)
            violations += len(result["structural_violations"])
            outputs[method] = result
            requests[method] = assemble_request(messages, result["catalogue"])
            if method == "P":
                unsupported_tools += result["unsupported_tools"]
                unlisted += result["unlisted_descriptions"]
        if outputs["P"]["unsupported_tools"]:
            cases_with_unsupported += 1
        for method in ("P", "I", "C"):
            _accumulate(
                outputs[method]["traces"],
                field_stats[method],
                reason_stats[method],
                role_changed[method],
            )
        for trace in outputs["P"]["traces"]:
            if trace.get("unsupported"):
                continue
            degrees.append(len(trace["neighbours"]))
            candidate_counts.append(trace["neighbour_candidates"])
            diagnostic_degrees.append(_diagnostic_degree(catalogue, trace["tool"], config))
        for method in ("P", "I", "C"):
            suffix_fields, other_fields, suffix_case, other_case = _change_split(
                outputs["U"]["catalogue"], outputs[method]["catalogue"]
            )
            suffix_removed[method] += _suffix_removals(
                outputs["U"]["catalogue"], outputs[method]["catalogue"]
            )
            suffix_only_fields[method] += suffix_fields
            other_changed_fields[method] += other_fields
            suffix_only_records[method] += suffix_case
            other_changed_records[method] += other_case
        for left, right, label in (
            ("C", "I", "C_vs_I"),
            ("P", "I", "P_vs_I"),
        ):
            field_delta = _selection_delta(outputs[left]["traces"], outputs[right]["traces"])
            selection_field_differences[label] += field_delta
            selection_case_differences[label] += int(field_delta > 0)
        hashes = {method: request_hash(requests[method]) for method in METHODS}
        flags = {
            "P_vs_U": hashes["P"] != hashes["U"],
            "I_vs_U": hashes["I"] != hashes["U"],
            "C_vs_U": hashes["C"] != hashes["U"],
            "C_vs_I": hashes["C"] != hashes["I"],
            "P_vs_I": hashes["P"] != hashes["I"],
        }
        differences.update({key: int(value) for key, value in flags.items()})
        distinct_groups[len(set(hashes.values()))] += 1
        blank_tokens.append(budget_counter.count(dump_request(assemble_request(messages, _blank(catalogue)))))
        for method in METHODS:
            text = dump_request(requests[method])
            token_lists[method][budget_counter.name].append(budget_counter.count(text))
            if sensitivity_counter.name != budget_counter.name:
                token_lists[method][sensitivity_counter.name].append(sensitivity_counter.count(text))
        rows.append(
            {
                "category": category,
                "id": record["id"],
                "preparation_failure": False,
                "hashes": hashes,
                **flags,
            }
        )
    n = len(records)
    prepared = n - preparation_failures
    names = (budget_counter.name, sensitivity_counter.name)
    summary = {
        "category": category,
        "role": CATEGORY_ROLE[category],
        "primary": category == PRIMARY_CATEGORY,
        "n_records": n,
        "prepared_records": prepared,
        "preparation_failures": preparation_failures,
        "records_with_more_than_one_turn": multi_turn,
        "max_question_turns": max_turns,
        "prepared_request_uses_turn": 0,
        "message_roles": dict(roles),
        "message_content_types": dict(content_types),
        "tools_per_record": _integer_summary(tools_per_record),
        "n_tools": sum(tools_per_record),
        "unsupported_tools": unsupported_tools,
        "cases_with_unsupported_tool": cases_with_unsupported,
        "unlisted_description_strings": unlisted,
        "request_differences": dict(differences),
        "active_fraction_c_vs_i": _fraction(differences["C_vs_I"], n),
        "within_case_distinct_local_requests": {str(k): distinct_groups[k] for k in (1, 2, 3, 4)},
        "neighbour_graph": {
            "tools": len(degrees),
            "degree_counts": {str(k): sum(item == k for item in degrees) for k in (0, 1, 2)},
            "mean_degree": _mean(degrees),
            "undirected_pairs_at_or_above_threshold": undirected_pairs,
            "tools_with_more_candidates_than_cap": sum(item > 2 for item in candidate_counts),
            "candidate_counts": {
                "0": sum(item == 0 for item in candidate_counts),
                "1": sum(item == 1 for item in candidate_counts),
                "2": sum(item == 2 for item in candidate_counts),
                "3_or_more": sum(item >= 3 for item in candidate_counts),
            },
        },
        "diagnostic_closed_class_removed": {
            "used_by_compressor": False,
            "mean_degree": _mean(diagnostic_degrees),
            "degree_counts": {
                str(k): sum(item == k for item in diagnostic_degrees) for k in (0, 1, 2)
            },
            "undirected_pairs_at_or_above_threshold": diagnostic_pairs,
        },
        "schema_overlap": {
            "within_request_property_name_pairs": schema_pairs,
            "pairs_with_jaccard_at_least_threshold": schema_pairs_meeting,
            "within_request_duplicate_function_names": within_request_duplicate_names,
            "corpus_signatures": len(signature_counts),
            "corpus_signatures_repeated": sum(count > 1 for count in signature_counts.values()),
            "tools_in_repeated_signatures": sum(
                count for count in signature_counts.values() if count > 1
            ),
        },
        "float_suffix_removed_fields": dict(suffix_removed),
        "float_suffix_only_fields": dict(suffix_only_fields),
        "other_changed_fields": dict(other_changed_fields),
        "records_changed_only_by_float_suffix": dict(suffix_only_records),
        "records_with_other_description_changes": dict(other_changed_records),
        "selection_differences": {
            "cases": dict(selection_case_differences),
            "fields": dict(selection_field_differences),
        },
        "fields": {
            method: {
                "counts": dict(field_stats[method]),
                "reasons": dict(reason_stats[method]),
                "changed_by_role": dict(role_changed[method]),
            }
            for method in ("P", "I", "C")
        },
        "blank_descriptions_orientation": {
            "used_by_selector": False,
            "note": (
                "Replacing every allowlisted description with an empty string. "
                "A local orientation of description share only. BPE counts are not "
                "monotonic, so this is not a maximum-saving proof and not the provider target."
            ),
            budget_counter.name: (
                cohort_ratio(token_lists["U"][budget_counter.name], blank_tokens)
                if blank_tokens
                else {"n": 0}
            ),
        },
        "local_U_request_tokens": {
            name: _integer_summary(token_lists["U"][name]) for name in names
        },
        "local_cohort_ratio_vs_U": {
            method: {
                name: (
                    cohort_ratio(token_lists["U"][name], token_lists[method][name])
                    if token_lists["U"][name]
                    else {"n": 0}
                )
                for name in names
            }
            for method in METHODS
        },
    }
    return summary, rows, violations


def _accumulate(traces, counts, reasons, roles) -> None:
    for trace in traces:
        if trace.get("unsupported"):
            continue
        for field in trace["fields"]:
            counts["fields"] += 1
            counts["spans"] += field["spans"]
            counts["optional_spans"] += field["optional_spans"]
            counts["protected_spans"] += field["protected_spans"]
            counts["tokens_d"] += field["d"]
            counts["tokens_p"] += field["p"]
            counts["tokens_nominal"] += field["nominal"]
            counts["tokens_budget"] += field["budget"]
            counts["tokens_achieved"] += field["achieved"]
            extra_reasons = [reason for reason_set in field["reasons"] for reason in reason_set if reason != "first_span"]
            counts["single_span"] += int(field["single_span"])
            counts["single_span_with_other_cue"] += int(field["single_span"] and bool(extra_reasons))
            counts["multi_span_all_protected"] += int(
                field["spans"] > 1 and field["optional_spans"] == 0
            )
            counts["fields_with_optional"] += int(field["optional_spans"] > 0)
            counts["empty_or_whitespace"] += int(field["status"] == "empty_or_whitespace")
            counts["frozen"] += int(field["frozen"])
            counts["uplift"] += int(field["uplift"])
            counts["uplift_single_span"] += int(field["uplift"] and field["single_span"])
            counts["uplift_multi_span"] += int(field["uplift"] and field["spans"] > 1)
            counts["unchanged"] += int(field["unchanged"])
            counts["changed"] += int(not field["unchanged"])
            counts["achieved_below_nominal"] += int(
                (not field["frozen"]) and field["achieved"] < field["nominal"]
            )
            counts["stopped_early"] += int(field["stopped_early"])
            counts["skipped_optional"] += field["skipped_optional"]
            kept_optional = len(field["selected"]) - field["protected_spans"]
            counts["optional_retained_fields"] += int(
                field["optional_spans"] > 0 and kept_optional > 0
            )
            counts["optional_all_dropped_fields"] += int(
                field["optional_spans"] > 0 and kept_optional == 0
            )
            pointer = field["pointer"]
            role = "function" if pointer.endswith("/function/description") else "parameter"
            if not field["unchanged"]:
                roles[role] += 1
            for reason_set in field["reasons"]:
                for reason in reason_set:
                    reasons[reason] += 1
            if field["spans"] <= 1:
                counts[f"span_hist_{field['spans']}"] += 1
            elif field["spans"] == 2:
                counts["span_hist_2"] += 1
            elif field["spans"] == 3:
                counts["span_hist_3"] += 1
            else:
                counts["span_hist_4_plus"] += 1


def _blank(catalogue: list) -> list:
    from copy import deepcopy

    from tool_compression.adapter import description_slots

    copied = deepcopy(catalogue)
    for tool in copied:
        for _pointer, container, key in description_slots(tool):
            container[key] = ""
    return copied


def _change_split(before, after):
    from tool_compression.adapter import description_slots

    suffix_fields = 0
    other_fields = 0
    for left, right in zip(before, after):
        for pointer, container, key in description_slots(left):
            original = container[key]
            updated = _lookup(right, pointer)
            if original == updated:
                continue
            if _suffix_only(original, updated):
                suffix_fields += 1
            else:
                other_fields += 1
    return suffix_fields, other_fields, int(suffix_fields > 0 and other_fields == 0), int(other_fields > 0)


def _suffix_only(before, after) -> bool:
    if not isinstance(before, str) or not isinstance(after, str):
        return False
    if FLOAT_SUFFIX not in before or FLOAT_SUFFIX in after:
        return False
    removed = before.replace(FLOAT_SUFFIX, "")
    return after == removed or after.strip() == removed.strip()


def _selection_delta(left_traces, right_traces) -> int:
    delta = 0
    for left, right in zip(left_traces, right_traces):
        if left.get("unsupported") or right.get("unsupported"):
            continue
        for left_field, right_field in zip(left["fields"], right["fields"]):
            if left_field["selected"] != right_field["selected"]:
                delta += 1
    return delta


def _suffix_removals(before, after) -> int:
    from tool_compression.adapter import description_slots

    removed = 0
    for left, right in zip(before, after):
        for pointer, container, key in description_slots(left):
            original = container[key]
            updated = _lookup(right, pointer)
            if (
                isinstance(original, str)
                and FLOAT_SUFFIX in original
                and isinstance(updated, str)
                and FLOAT_SUFFIX not in updated
            ):
                removed += 1
    return removed


def _lookup(tool, pointer: str):
    node = tool
    for part in pointer.strip("/").split("/"):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return node


def _overlap(catalogue, signatures) -> None:
    for tool in catalogue:
        function = tool.get("function") if isinstance(tool, dict) else None
        if not isinstance(function, dict):
            continue
        parameters = function.get("parameters")
        properties = parameters.get("properties", {}) if isinstance(parameters, dict) else {}
        if not isinstance(properties, dict):
            properties = {}
        signature = (
            function.get("name"),
            tuple(
                (name, schema.get("type") if isinstance(schema, dict) else None)
                for name, schema in properties.items()
            ),
        )
        signatures[signature] += 1


def _within_duplicates(catalogue) -> int:
    seen = Counter()
    for tool in catalogue:
        function = tool.get("function") if isinstance(tool, dict) else None
        if isinstance(function, dict):
            seen[function.get("name")] += 1
    return sum(1 for count in seen.values() if count > 1)


def _pair_count(catalogue, diagnostic: bool) -> int:
    sets = []
    for tool in catalogue:
        features = tool_feature_set(tool)
        if diagnostic:
            features = {gram for gram in features if gram not in DIAGNOSTIC_CLOSED_CLASS}
        sets.append(features)
    count = 0
    for index, left in enumerate(sets):
        for right in sets[index + 1 :]:
            meets, _, _ = jaccard_at_least(left, right, 1, 5)
            if meets:
                count += 1
    return count


def _diagnostic_degree(catalogue, tool_index: int, config: Config) -> int:
    sets = [
        {gram for gram in tool_feature_set(tool) if gram not in DIAGNOSTIC_CLOSED_CLASS}
        for tool in catalogue
    ]
    if tool_index >= len(sets):
        return 0
    hits = 0
    for other, features in enumerate(sets):
        if other == tool_index:
            continue
        meets, _, _ = jaccard_at_least(
            sets[tool_index],
            features,
            config.jaccard_numerator,
            config.jaccard_denominator,
        )
        if meets:
            hits += 1
    return min(hits, config.max_neighbours)


def _schema_pairs(catalogue) -> tuple[int, int]:
    sets = [set(property_names(tool)) for tool in catalogue]
    total = 0
    hits = 0
    for index, left in enumerate(sets):
        for right in sets[index + 1 :]:
            total += 1
            meets, _, _ = jaccard_at_least(left, right, 1, 5)
            if meets:
                hits += 1
    return hits, total


def _fraction(numerator: int, denominator: int) -> dict:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": None if denominator == 0 else numerator / denominator,
    }


def _mean(values):
    if not values:
        return None
    return sum(values) / len(values)


def _integer_summary(values) -> dict:
    if not values:
        return {"n": 0}
    ordered = sorted(values)
    return {
        "n": len(values),
        "min": ordered[0],
        "p50": ordered[round(0.5 * (len(ordered) - 1))],
        "p90": ordered[round(0.9 * (len(ordered) - 1))],
        "max": ordered[-1],
        "mean": sum(values) / len(values),
    }


def file_sha256(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()
