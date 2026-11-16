"""Query-agnostic, deterministic, extractive description compression."""

from collections import Counter
from copy import deepcopy

from tool_compression.adapter import description_slots, is_supported_tool, unlisted_description_pointers
from tool_compression.config import METHODS, Config
from tool_compression.lexical import (
    description_features,
    description_unigram_counts,
    select_neighbours,
    tool_feature_set,
)
from tool_compression.select import select_field
from tool_compression.validate import catalogue_violations


def compress(catalogue: list, method: str, config: Config, counter) -> dict:
    """Return a new catalogue. The input list and its tools are not modified.

    ``counter`` counts tokens in one field or rendering. It is the local budget
    tokenizer, not a provider usage meter. ``method`` is U, P, I, or C.
    """
    if method not in METHODS:
        raise ValueError(f"unknown method {method}")
    original = deepcopy(catalogue)
    if method == "U":
        return {
            "catalogue": original,
            "method": method,
            "spec_version": config.spec_version,
            "unchanged": True,
            "unsupported_tools": sum(not is_supported_tool(tool) for tool in original),
            "unlisted_descriptions": sum(len(unlisted_description_pointers(tool)) for tool in original if isinstance(tool, dict)),
            "traces": [],
            "structural_violations": [],
        }
    supported = [is_supported_tool(tool) for tool in original]
    feature_sets = [tool_feature_set(tool) if flag else set() for tool, flag in zip(original, supported)]
    neighbours = select_neighbours(
        feature_sets,
        max_neighbours=config.max_neighbours,
        numerator=config.jaccard_numerator,
        denominator=config.jaccard_denominator,
    )
    features = [description_features(tool) if flag else set() for tool, flag in zip(original, supported)]
    counts = [description_unigram_counts(tool) if flag else Counter() for tool, flag in zip(original, supported)]
    edited = deepcopy(original)
    traces = []
    unsupported = 0
    unlisted = 0
    for index, tool in enumerate(edited):
        if not supported[index]:
            unsupported += 1
            traces.append({"tool": index, "unsupported": True, "fields": []})
            continue
        if isinstance(original[index], dict):
            unlisted += len(unlisted_description_pointers(original[index]))
        neighbour_indexes, _candidate_count = neighbours[index]
        neighbour_features = [features[other] for other in neighbour_indexes]
        fields = []
        for pointer, container, key in description_slots(tool):
            updated, trace = select_field(
                container[key],
                method,
                config,
                counter,
                counts[index],
                neighbour_features,
            )
            container[key] = updated
            fields.append({"pointer": pointer, **trace})
        traces.append(
            {
                "tool": index,
                "unsupported": False,
                "neighbours": neighbour_indexes,
                "neighbour_candidates": _candidate_count,
                "fields": fields,
            }
        )
    violations = catalogue_violations(original, edited)
    if violations:
        raise RuntimeError("description edit left the allowlisted boundary: " + ", ".join(violations[:8]))
    unchanged = all(field["unchanged"] for trace in traces for field in trace["fields"])
    return {
        "catalogue": edited,
        "method": method,
        "spec_version": config.spec_version,
        "unchanged": unchanged,
        "unsupported_tools": unsupported,
        "unlisted_descriptions": unlisted,
        "traces": traces,
        "structural_violations": violations,
    }
