"""Offline audit of T1 and T2. No model call and no labels.

The opportunity funnel counts every original case. Preparation failures stay
unknown: they are not treated as equal requests.
"""

from __future__ import annotations

from collections import Counter
from fractions import Fraction
import hashlib
import time

from tool_compression.adapter import is_supported_tool
from tool_compression.config import BFCL_DEFAULT_TEMPERATURE, BFCL_STORE, PLACEHOLDER_MODEL
from tool_compression.count import dump_request
from tool_compression.evaluation import DENOMINATORS
from tool_compression.followon_config import T1_CONFIG, T2_CONFIG, FollowOnConfig
from tool_compression.load import STUDY_CATEGORIES
from tool_compression.phrase_compress import compress_conditions
from tool_compression.prepare import assemble_request, convert_record

# Week 1 eligible-field inventory, reconciled against U rather than imposed.
WEEK1_FIELD_INVENTORY = {
    "multiple": 2101,
    "simple_python": 1570,
    "irrelevance": 933,
}
PRIMARY = "multiple"
CONTROLS = ("simple_python", "irrelevance")
PLANNING_GROUP_BOUNDS = {
    "multiple": (200, 600),
    "simple_python": (400, 800),
    "irrelevance": (240, 480),
}


def analyze_record(
    record: dict,
    counter,
    conditions: tuple[FollowOnConfig, ...] = (T1_CONFIG, T2_CONFIG),
    *,
    repeat: bool = True,
) -> tuple[dict, list[dict]]:
    """Prepare one case. The compressor receives the converted catalogue only."""
    cpu_started = time.process_time()
    wall_started = time.perf_counter()
    turns = record.get("question") or []
    if not turns or not isinstance(turns[0], list):
        raise TypeError("question_turn")
    messages = turns[0]
    catalogue = convert_record(record)
    produced = compress_conditions(catalogue, counter, conditions)
    if repeat:
        again = compress_conditions(catalogue, counter, conditions)
        if again["catalogues"] != produced["catalogues"] or again["traces"] != produced["traces"]:
            raise RuntimeError("repeat_mismatch")
    requests = {"U": assemble_request(messages, catalogue)}
    for name in produced["conditions"]:
        requests[name] = assemble_request(messages, produced["catalogues"][name])
    _require_options(requests, messages)
    raw = {name: dump_request(request) for name, request in requests.items()}
    hashes = {name: hashlib.sha256(payload.encode("utf-8")).hexdigest() for name, payload in raw.items()}
    raw_equal = {
        "T1_T2": raw["T1"] == raw["T2"],
        "T1_U": raw["T1"] == raw["U"],
        "T2_U": raw["T2"] == raw["U"],
    }
    hash_matches_raw = all((hashes[left] == hashes[right]) == equal for (left, right), equal in (
        (("T1", "T2"), raw_equal["T1_T2"]),
        (("T1", "U"), raw_equal["T1_U"]),
        (("T2", "U"), raw_equal["T2_U"]),
    ))
    if not hash_matches_raw:
        raise RuntimeError("hash_raw_mismatch")
    fields = []
    units_dropped = Counter()
    changed_fields = Counter()
    for trace in produced["traces"]:
        if trace.get("unsupported"):
            continue
        for field in trace["fields"]:
            enriched = _enrich_field(field, raw_equal["T1_T2"] is False)
            enriched["tool"] = trace["tool"]
            fields.append(enriched)
            for name in ("T1", "T2"):
                decisions = field["by_condition"][name]["decisions"]
                units_dropped[name] += sum(item.startswith("skipped") for item in decisions.values())
                if field["by_condition"][name]["sha256"] != field["original_sha256"]:
                    changed_fields[f"{name}_U"] += 1
            if field["by_condition"]["T1"]["sha256"] != field["by_condition"]["T2"]["sha256"]:
                changed_fields["T2_T1"] += 1
    supported = sum(is_supported_tool(tool) for tool in catalogue)
    row = {
        "preparation_failure": False,
        "failure_reason": None,
        "tool_count": len(catalogue),
        "supported_tool_count": supported,
        "hashes": hashes,
        "raw_equal": raw_equal,
        "hash_matches_raw": True,
        "local_tokens": {name: counter.count(payload) for name, payload in raw.items()},
        "fields_changed": dict(changed_fields),
        "units_dropped": {"T1": units_dropped["T1"], "T2": units_dropped["T2"]},
        "fallback_fields": sum(str(field["status"]).startswith("fallback_") for field in fields),
        "stop_reason": case_stop(fields, not raw_equal["T1_T2"], False),
        "funnel": {
            "opportunity": any(field["opportunity"] for field in fields),
            "neighbour": any(field["opportunity"] and field["neighbour"] for field in fields),
            "ranking": any(field["ranking"] for field in fields),
            "delivered": any(field["delivered"] for field in fields),
        },
        "cpu_seconds": time.process_time() - cpu_started,
        "wall_seconds": time.perf_counter() - wall_started,
        "field_count": len(fields),
    }
    return row, fields


def case_stop(fields: list[dict], request_differs: bool, preparation_failure: bool) -> str:
    """Exclusive stop label. The funnel rows are cumulative and use the same field."""
    if preparation_failure:
        return "preparation_failure"
    if any(field["delivered"] for field in fields) and request_differs:
        return "delivered_change"
    if any(field["ranking"] for field in fields):
        return "different_order_same_selection"
    if any(field["opportunity"] and field["neighbour"] for field in fields):
        return "same_order"
    if any(field["opportunity"] for field in fields):
        return "no_neighbour"
    if any(field["protected_fills_cap"] for field in fields):
        return "protected_text_fills_cap"
    if not fields or all(field["single_content_clause"] for field in fields):
        return "indivisible_single_clause"
    return "no_two_optional_fragments"


def audit_study(study: dict, counter, conditions: tuple[FollowOnConfig, ...] = (T1_CONFIG, T2_CONFIG)) -> dict:
    cases = []
    field_rows = []
    for category in STUDY_CATEGORIES:
        records = study[category]
        if len(records) != DENOMINATORS[category]:
            raise RuntimeError(f"{category} denominator {len(records)} != {DENOMINATORS[category]}")
        for record in records:
            try:
                case_row, fields = analyze_record(record, counter, conditions, repeat=True)
            except Exception as exc:
                case_row = _failure_row(exc)
                fields = []
            case_row["category"] = category
            case_row["id"] = record.get("id")
            cases.append(case_row)
            for field in fields:
                field_rows.append(
                    {
                        "category": category,
                        "id": record.get("id"),
                        **field,
                    }
                )
    summary = summarize(cases, field_rows)
    return {"summary": summary, "cases": cases, "fields": field_rows}


def summarize(cases: list[dict], fields: list[dict]) -> dict:
    categories = {}
    defects = []
    for category in STUDY_CATEGORIES:
        rows = [row for row in cases if row["category"] == category]
        field_set = [row for row in fields if row["category"] == category]
        block = _category_summary(category, rows, field_set)
        categories[category] = block
        if category in CONTROLS and block["f_new"]["numerator"] != 0:
            defects.append(f"{category} T2 request differs from T1")
        if category in CONTROLS and any(row["supported_tool_count"] != 1 for row in rows if not row["preparation_failure"]):
            defects.append(f"{category} control is not single-tool")
        if block["hash_raw_mismatches"]:
            defects.append(f"{category} hash does not match raw identity")
        if block["repeat_failures"]:
            defects.append(f"{category} repeated transform mismatch")
        internal = [
            row["id"]
            for row in rows
            if row["failure_reason"] in {
                "repeat_mismatch",
                "hash_raw_mismatch",
                "model_option",
                "temperature_option",
                "store_option",
                "messages_changed",
            }
        ]
        if internal:
            defects.append(f"{category} internal failure {internal[:8]}")
    anchor_failures = sum(1 for field in fields if not field["purpose_anchor_kept"]["T1"] or not field["purpose_anchor_kept"]["T2"])
    constraint_failures = sum(
        1 for field in fields if not field["constraint_pieces_kept"]["T1"] or not field["constraint_pieces_kept"]["T2"]
    )
    if anchor_failures:
        defects.append("purpose anchor dropped")
    if constraint_failures:
        defects.append("protected piece dropped")
    primary_fields = categories[PRIMARY]["fields"]
    return {
        "spec_version": T1_CONFIG.spec_version,
        "measured": False,
        "provider_called": False,
        "labels_used": False,
        "ready_for_evaluation": not defects and all(
            categories[category]["preparation_failures"] == 0 for category in STUDY_CATEGORIES
        ),
        "implementation_defects": defects,
        "conditions": ["U", "T1", "T2"],
        "new_trial_settings": T2_CONFIG.as_dict(),
        "tokenizer": T1_CONFIG.tokenizer_name,
        "primary_field_inventory": {
            "week1": WEEK1_FIELD_INVENTORY[PRIMARY],
            "observed": primary_fields,
            "reconciled": primary_fields == WEEK1_FIELD_INVENTORY[PRIMARY],
        },
        "categories": categories,
        "funnel": categories[PRIMARY]["funnel"],
        "anchor_failures": anchor_failures,
        "constraint_failures": constraint_failures,
    }


def _category_summary(category: str, rows: list[dict], fields: list[dict]) -> dict:
    n = len(rows)
    failures = [row for row in rows if row["preparation_failure"]]
    prepared = [row for row in rows if not row["preparation_failure"]]
    differ = [row for row in prepared if not row["raw_equal"]["T1_T2"]]
    equal = [row for row in prepared if row["raw_equal"]["T1_T2"]]
    unknown = len(failures)
    stop = Counter(row["stop_reason"] for row in rows)
    if sum(stop.values()) != n:
        raise RuntimeError(f"{category} stop reasons do not partition the category")
    groups = sum(len(set(row["hashes"].values())) for row in prepared)
    token_sums = {
        name: sum(row["local_tokens"][name] for row in prepared) for name in ("U", "T1", "T2")
    }
    funnel = _funnel(fields, n, len(fields))
    status_counts = Counter(field["status"] for field in fields)
    return {
        "n": n,
        "expected_n": DENOMINATORS[category],
        "prepared": len(prepared),
        "preparation_failures": unknown,
        "fields": len(fields),
        "week1_field_inventory": WEEK1_FIELD_INVENTORY[category],
        "field_inventory_reconciled": len(fields) == WEEK1_FIELD_INVENTORY[category],
        "f_new": {
            "numerator": len(differ),
            "denominator": n,
            "confirmed_equal": len(equal),
            "unknown": unknown,
            "possible_low_numerator": len(differ),
            "possible_high_numerator": len(differ) + unknown,
        },
        "request_groups": groups,
        "planning_group_bounds": {
            "low": PLANNING_GROUP_BOUNDS[category][0],
            "high": PLANNING_GROUP_BOUNDS[category][1],
            "replaced_by_exact_count": True,
        },
        "changed_cases_vs_U": {
            "T1": sum(not row["raw_equal"]["T1_U"] for row in prepared),
            "T2": sum(not row["raw_equal"]["T2_U"] for row in prepared),
        },
        "changed_fields_vs_U": {
            "T1": sum(field["by_condition"]["T1"]["sha256"] != field["original_sha256"] for field in fields),
            "T2": sum(field["by_condition"]["T2"]["sha256"] != field["original_sha256"] for field in fields),
        },
        "changed_fields_t2_t1": sum(
            field["by_condition"]["T1"]["sha256"] != field["by_condition"]["T2"]["sha256"] for field in fields
        ),
        "local_tokens": {
            name: {"sum": token_sums[name], "n": len(prepared)} for name in ("U", "T1", "T2")
        },
        "stop_reasons": dict(stop),
        "funnel": funnel,
        "field_status": dict(status_counts),
        "fallback_fields": sum(str(field["status"]).startswith("fallback_") for field in fields),
        "unchanged_fields": {
            "T1": sum(field["by_condition"]["T1"]["unchanged"] for field in fields),
            "T2": sum(field["by_condition"]["T2"]["unchanged"] for field in fields),
        },
        "units_dropped": {
            "T1": sum(row["units_dropped"]["T1"] for row in prepared),
            "T2": sum(row["units_dropped"]["T2"] for row in prepared),
        },
        "optional_fragments": sum(field["optional_count"] for field in fields),
        "outside_proxy_case_ids": [row["id"] for row in differ if row["stop_reason"] != "delivered_change"],
        "request_change_case_ids": [row["id"] for row in differ],
        "hash_raw_mismatches": sum(not row["hash_matches_raw"] for row in prepared),
        "repeat_failures": sum(row["failure_reason"] == "repeat_mismatch" for row in failures),
        "cpu_seconds": round(sum(row["cpu_seconds"] for row in rows), 6),
        "wall_seconds": round(sum(row["wall_seconds"] for row in rows), 6),
        "single_tool": all(row["supported_tool_count"] == 1 for row in prepared) if category in CONTROLS else False,
    }


def _funnel(fields: list[dict], case_denominator: int, field_denominator: int) -> dict:
    """Four cumulative rows. A case is counted once per row on a qualifying field."""
    definitions = (
        ("opportunity", lambda field: field["opportunity"]),
        ("neighbour", lambda field: field["opportunity"] and field["neighbour"]),
        ("ranking", lambda field: field["ranking"]),
        ("delivered", lambda field: field["delivered"]),
    )
    rows = []
    previous_fields = None
    previous_cases = None
    for name, predicate in definitions:
        matched = [field for field in fields if predicate(field)]
        case_ids = {field["id"] for field in matched}
        if previous_fields is not None and len(matched) > previous_fields:
            raise RuntimeError(f"funnel row {name} is not cumulative for fields")
        if previous_cases is not None and len(case_ids) > previous_cases:
            raise RuntimeError(f"funnel row {name} is not cumulative for cases")
        previous_fields = len(matched)
        previous_cases = len(case_ids)
        rows.append(
            {
                "row": len(rows) + 1,
                "name": name,
                "fields": len(matched),
                "fields_denominator": field_denominator,
                "cases": len(case_ids),
                "cases_denominator": case_denominator,
            }
        )
    return {
        "cumulative": True,
        "case_denominator_includes_unedited": True,
        "rows": rows,
        "prepared_cases_in_stop_partition": case_denominator,
    }


def _enrich_field(field: dict, request_differs: bool) -> dict:
    pieces = field["pieces"]
    reversed_pairs = []
    selection_changed = False
    for pair in field["competing_pairs"]:
        if _order(pieces, pair, "T1") == _order(pieces, pair, "T2"):
            continue
        reversed_pairs.append(list(pair))
        kept_t1 = tuple(index for index in pair if _kept(field, "T1", index))
        kept_t2 = tuple(index for index in pair if _kept(field, "T2", index))
        if kept_t1 != kept_t2:
            selection_changed = True
    text_changed = field["by_condition"]["T1"]["sha256"] != field["by_condition"]["T2"]["sha256"]
    neighbour = len(field["neighbours"]) >= 1
    opportunity = len(field["competing_pairs"]) >= 1
    ranking = bool(reversed_pairs) and opportunity and neighbour
    public = {
        "tool": field.get("tool"),
        "pointer": field["pointer"],
        "role": field["role"],
        "status": field["status"],
        "reason": field["reason"],
        "length": field["length"],
        "d": field["d"],
        "p": field["p"],
        "nominal": field["nominal"],
        "budget": field["budget"],
        "optional_count": field["optional_count"],
        "single_content_clause": field["single_content_clause"],
        "protected_fills_cap": field["protected_fills_cap"],
        "neighbours": list(field["neighbours"]),
        "neighbour": neighbour,
        "competing_pairs": field["competing_pairs"],
        "reversed_pairs": reversed_pairs,
        "opportunity": opportunity,
        "ranking": ranking,
        "pair_selection_changed": selection_changed,
        "text_changed_t2_t1": text_changed,
        "delivered": ranking and selection_changed and text_changed and request_differs,
        "original_sha256": field["original_sha256"],
        "pieces": pieces,
        "by_condition": field["by_condition"],
        "purpose_anchor_kept": {
            name: _anchor_kept(field, name) for name in ("T1", "T2")
        },
        "constraint_pieces_kept": {
            name: _constraints_kept(field, name) for name in ("T1", "T2")
        },
    }
    return public


def _order(pieces: list[dict], pair: list[int], condition: str) -> tuple[int, ...]:
    def key(index: int):
        score = Fraction(pieces[index]["scores"][condition])
        return (-score, pieces[index]["start"], index)

    return tuple(sorted(pair, key=key))


def _kept(field: dict, condition: str, index: int) -> bool:
    return field["by_condition"][condition]["decisions"].get(str(index)) == "kept"


def _anchor_kept(field: dict, condition: str) -> bool:
    selected = set(field["by_condition"][condition]["selected"])
    anchors = [piece["index"] for piece in field["pieces"] if piece["kind"] == "anchor"]
    if not anchors:
        return field["by_condition"][condition]["unchanged"]
    return all(index in selected for index in anchors)


def _constraints_kept(field: dict, condition: str) -> bool:
    selected = set(field["by_condition"][condition]["selected"])
    for piece in field["pieces"]:
        if piece["kind"] == "optional":
            continue
        if piece["index"] not in selected:
            return False
    return True


def _failure_row(exc: Exception) -> dict:
    known = {
        "repeat_mismatch",
        "hash_raw_mismatch",
        "model_option",
        "temperature_option",
        "store_option",
        "messages_changed",
        "question_turn",
    }
    reason = str(exc) if str(exc) in known else type(exc).__name__
    return {
        "preparation_failure": True,
        "failure_reason": reason,
        "tool_count": 0,
        "supported_tool_count": 0,
        "hashes": {},
        "raw_equal": {"T1_T2": None, "T1_U": None, "T2_U": None},
        "hash_matches_raw": False,
        "local_tokens": {"U": None, "T1": None, "T2": None},
        "fields_changed": {},
        "units_dropped": {"T1": 0, "T2": 0},
        "fallback_fields": 0,
        "stop_reason": "preparation_failure",
        "funnel": {"opportunity": False, "neighbour": False, "ranking": False, "delivered": False},
        "cpu_seconds": 0.0,
        "wall_seconds": 0.0,
        "field_count": 0,
    }


def _require_options(requests: dict, messages: list) -> None:
    for request in requests.values():
        if request.get("model") != PLACEHOLDER_MODEL:
            raise RuntimeError("model_option")
        if request.get("temperature") != BFCL_DEFAULT_TEMPERATURE:
            raise RuntimeError("temperature_option")
        if request.get("store") is not BFCL_STORE:
            raise RuntimeError("store_option")
        if request.get("messages") != messages:
            raise RuntimeError("messages_changed")
        if "tools" in request:
            _ = request["tools"]
