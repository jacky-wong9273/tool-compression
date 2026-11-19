"""Apply one phrase compressor under one or more contrast weights.

T1 and T2 share the parse, guards, renderer, cap, and selector. Only the
optional-piece score changes. The input catalogue is not mutated.
"""

from __future__ import annotations

from copy import deepcopy

from tool_compression.adapter import description_slots, is_supported_tool, unlisted_description_pointers
from tool_compression.followon_config import T1_CONFIG, T2_CONFIG, FollowOnConfig, same_transform
from tool_compression.lexical import description_features, select_neighbours, tool_feature_set
from tool_compression.phrase import parse_field
from tool_compression.phrase_select import (
    fraction_text,
    identifier_terms,
    select_parsed_field,
    sha256_text,
)
from tool_compression.validate import catalogue_violations


def compress_conditions(
    catalogue: list,
    counter,
    conditions: tuple[FollowOnConfig, ...] = (T1_CONFIG, T2_CONFIG),
) -> dict:
    """Return a catalogue per condition plus field traces without source prose."""
    if not conditions:
        raise ValueError("at least one follow-on condition is required")
    names = tuple(config.condition for config in conditions)
    if len(names) != len(set(names)):
        raise ValueError("condition names must be unique")
    first = conditions[0]
    for config in conditions[1:]:
        if not same_transform(first, config):
            raise ValueError("T1 and T2 must share the transform and differ only by contrast weight")
    original = deepcopy(catalogue)
    supported = [is_supported_tool(tool) for tool in original]
    feature_sets = [tool_feature_set(tool) if flag else set() for tool, flag in zip(original, supported)]
    neighbours = select_neighbours(
        feature_sets,
        max_neighbours=first.max_neighbours,
        numerator=first.jaccard_numerator,
        denominator=first.jaccard_denominator,
    )
    features = [description_features(tool) if flag else set() for tool, flag in zip(original, supported)]
    copies = {name: deepcopy(original) for name in names}
    slot_lists = {
        name: [description_slots(tool) if flag else [] for tool, flag in zip(copies[name], supported)]
        for name in names
    }
    traces = []
    unsupported = 0
    unlisted = 0
    for index, flag in enumerate(supported):
        if not flag:
            unsupported += 1
            traces.append({"tool": index, "unsupported": True, "neighbours": [], "fields": []})
            continue
        if isinstance(original[index], dict):
            unlisted += len(unlisted_description_pointers(original[index]))
        neighbour_indexes, candidate_count = neighbours[index]
        neighbour_features = [features[other] for other in neighbour_indexes]
        identifiers = identifier_terms(original[index])
        fields = []
        slots = slot_lists[names[0]][index]
        for slot_index, (pointer, container, key) in enumerate(slots):
            text = container[key]
            role = "function" if pointer == "/function/description" else "parameter"
            parsed = parse_field(text, role)
            chosen = select_parsed_field(text, parsed, identifiers, neighbour_features, counter, conditions)
            for name in names:
                _, target, target_key = slot_lists[name][index][slot_index]
                updated = chosen["outputs"][name]["text"]
                target[target_key] = updated if updated != target[target_key] else target[target_key]
            field = _public_field(pointer, role, neighbour_indexes, chosen)
            field["original_sha256"] = sha256_text(text)
            field["length"] = len(text)
            fields.append(field)
        traces.append(
            {
                "tool": index,
                "unsupported": False,
                "neighbours": list(neighbour_indexes),
                "neighbour_candidates": candidate_count,
                "fields": fields,
            }
        )
    violations = {name: catalogue_violations(original, copies[name]) for name in names}
    for name, found in violations.items():
        if found:
            raise RuntimeError(f"{name} left the allowlisted boundary: " + ", ".join(found[:8]))
    unchanged = {
        name: all(field["by_condition"][name]["unchanged"] for trace in traces for field in trace["fields"])
        for name in names
    }
    return {
        "catalogues": copies,
        "conditions": names,
        "spec_version": first.spec_version,
        "unchanged": unchanged,
        "unsupported_tools": unsupported,
        "unlisted_descriptions": unlisted,
        "traces": traces,
        "structural_violations": violations,
    }


def _public_field(pointer: str, role: str, neighbours: tuple[int, ...], chosen: dict) -> dict:
    pieces = []
    for index, piece in enumerate(chosen["pieces"]):
        row = {
            "index": index,
            "start": piece.start,
            "end": piece.end,
            "kind": piece.kind,
            "reasons": list(piece.reasons),
        }
        if chosen["own_scores"]:
            row["own_score"] = fraction_text(chosen["own_scores"][index])
            row["q"] = fraction_text(chosen["q_scores"][index])
            row["scores"] = {
                name: fraction_text(scores[index]) for name, scores in chosen["score_table"].items()
            }
        pieces.append(row)
    by_condition = {}
    for name, output in chosen["outputs"].items():
        by_condition[name] = {
            "status": output["status"],
            "achieved": output["achieved"],
            "unchanged": output["unchanged"],
            "selected": list(output["selected"]),
            "order": list(output["order"]),
            "decisions": {str(index): decision for index, decision in output["decisions"].items()},
            "sha256": sha256_text(output["text"]),
        }
    return {
        "pointer": pointer,
        "role": role,
        "status": chosen["status"],
        "reason": chosen["reason"],
        "neighbours": list(neighbours),
        "d": chosen["d"],
        "p": chosen["p"],
        "nominal": chosen["nominal"],
        "budget": chosen["budget"],
        "optional_count": chosen["optional_count"],
        "single_content_clause": chosen["single_content_clause"],
        "protected_fills_cap": chosen["protected_fills_cap"],
        "alone_fits": {str(index): fits for index, fits in chosen["alone_fits"].items()},
        "competing_pairs": [list(pair) for pair in chosen["competing_pairs"]],
        "pieces": pieces,
        "by_condition": by_condition,
    }
