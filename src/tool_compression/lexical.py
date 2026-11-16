"""Own-tool frequency, neighbour sets, and the contrast feature q.

Neighbours and features are computed from the converted catalogue before
any description is edited. Questions are not an input.
"""

from collections import Counter
from fractions import Fraction
import re

from tool_compression.adapter import description_slots, property_names
from tool_compression.config import JACCARD_DENOMINATOR, JACCARD_NUMERATOR, MAX_NEIGHBOURS

_CAMEL = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+")
_RAW = re.compile(r"[A-Za-z0-9]+")


def unigrams(text: str) -> list[str]:
    grams: list[str] = []
    for raw in _RAW.findall(text):
        pieces = _CAMEL.findall(raw)
        grams.extend(piece.lower() for piece in pieces if piece)
    return grams


def bigrams(grams: list[str]) -> list[str]:
    return [f"{left} {right}" for left, right in zip(grams, grams[1:])]


def tool_feature_set(tool: dict) -> set[str]:
    """Unigrams of allowlisted descriptions plus function and property names."""
    grams: set[str] = set()
    function = tool.get("function") if isinstance(tool, dict) else None
    if isinstance(function, dict) and isinstance(function.get("name"), str):
        grams.update(unigrams(function["name"]))
    for name in property_names(tool):
        grams.update(unigrams(name))
    for _, container, key in description_slots(tool):
        grams.update(unigrams(container[key]))
    return grams


def description_features(tool: dict) -> set[str]:
    """Unigrams and within-field bigrams of allowlisted original descriptions."""
    features: set[str] = set()
    for _, container, key in description_slots(tool):
        grams = unigrams(container[key])
        features.update(grams)
        features.update(bigrams(grams))
    return features


def description_unigram_counts(tool: dict) -> Counter[str]:
    counts: Counter[str] = Counter()
    for _, container, key in description_slots(tool):
        counts.update(unigrams(container[key]))
    return counts


def jaccard_at_least(left: set[str], right: set[str], numerator: int, denominator: int) -> tuple[bool, int, int]:
    if not left and not right:
        return False, 0, 0
    intersection = len(left & right)
    union = len(left | right)
    if union == 0:
        return False, 0, 0
    return intersection * denominator >= numerator * union, intersection, union


def select_neighbours(
    feature_sets: list[set[str]],
    max_neighbours: int = MAX_NEIGHBOURS,
    numerator: int = JACCARD_NUMERATOR,
    denominator: int = JACCARD_DENOMINATOR,
) -> list[tuple[tuple[int, ...], int]]:
    """At most `max_neighbours` other tools, highest Jaccard first.

    Equal Jaccard keeps the earlier catalogue index. The tool itself is excluded.
    Each result is ``(selected indexes, candidate count before the cap)``.
    """
    chosen: list[tuple[tuple[int, ...], int]] = []
    for index, features in enumerate(feature_sets):
        candidates: list[tuple[int, int, int]] = []
        for other, other_features in enumerate(feature_sets):
            if other == index:
                continue
            meets, intersection, union = jaccard_at_least(features, other_features, numerator, denominator)
            if meets:
                candidates.append((intersection, union, other))
        candidates.sort(key=lambda item: (-Fraction(item[0], item[1]), item[2]))
        chosen.append((tuple(item[2] for item in candidates[:max_neighbours]), len(candidates)))
    return chosen


def position_preference(index: int, n_spans: int) -> Fraction:
    if n_spans <= 1:
        return Fraction(1)
    return Fraction(n_spans - 1 - index, n_spans - 1)


def span_frequency(span_text: str, counts: Counter[str]) -> Fraction:
    grams = list(dict.fromkeys(unigrams(span_text)))
    if not grams or not counts:
        return Fraction(0)
    maximum = max(counts.values())
    if maximum <= 0:
        return Fraction(0)
    return sum((Fraction(counts[gram], maximum) for gram in grams), Fraction(0)) / len(grams)


def span_features(span_text: str) -> list[str]:
    grams = unigrams(span_text)
    features = list(dict.fromkeys(grams))
    features.extend(dict.fromkeys(bigrams(grams)))
    return features


def contrast_q(span_text: str, neighbour_features: list[set[str]]) -> Fraction:
    """Mean fraction of neighbours whose original descriptions lack each feature.

    No neighbours, or a span with no lexical features, yields zero.
    """
    if not neighbour_features:
        return Fraction(0)
    features = span_features(span_text)
    if not features:
        return Fraction(0)
    total = Fraction(0)
    width = len(neighbour_features)
    for feature in features:
        absent = sum(1 for features_present in neighbour_features if feature not in features_present)
        total += Fraction(absent, width)
    return total / len(features)
