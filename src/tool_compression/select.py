"""Shared field budgets and the P, I, and C selectors.

P adds optional spans in source order and stops at the first span that does
not fit. I and C rank optional spans by score per token, keep source order in
the output, and skip a span that does not fit. Every acceptance re-tokenizes
the complete candidate rendering.
"""

from collections import Counter
from fractions import Fraction

from tool_compression.config import Config
from tool_compression.cues import cue_reasons
from tool_compression.lexical import contrast_q, position_preference, span_frequency
from tool_compression.segment import render, segment_spans


def nominal_cap(token_count: int, config: Config) -> int:
    if token_count <= 0:
        return 0
    return (token_count * config.retention_numerator) // config.retention_denominator


def select_field(
    text: str,
    method: str,
    config: Config,
    counter,
    own_counts: Counter[str],
    neighbour_features: list[set[str]],
) -> tuple[str, dict]:
    if method not in {"P", "I", "C"}:
        raise ValueError(method)
    if text == "" or not text.strip():
        return text, _trace(text, counter, status="empty_or_whitespace", spans=0)
    spans = segment_spans(text)
    if not spans:
        return text, _trace(text, counter, status="empty_or_whitespace", spans=0)
    protected = []
    reasons = []
    for index, (start, stop) in enumerate(spans):
        found = []
        if index == 0:
            found.append("first_span")
        found.extend(cue_reasons(text[start:stop]))
        is_protected = bool(found)
        protected.append(is_protected)
        reasons.append(tuple(dict.fromkeys(found)))
    d_tokens = counter.count(text)
    protected_keep = {index for index, flag in enumerate(protected) if flag}
    protected_text = render(text, spans, protected_keep)
    p_tokens = counter.count(protected_text)
    optional = [index for index, flag in enumerate(protected) if not flag]
    base = {
        "spans": len(spans),
        "optional_spans": len(optional),
        "protected_spans": len(protected_keep),
        "reasons": reasons,
        "d": d_tokens,
        "p": p_tokens,
        "nominal": nominal_cap(d_tokens, config),
        "single_span": len(spans) == 1,
    }
    if p_tokens > d_tokens:
        return text, {
            **base,
            "budget": base["nominal"],
            "achieved": d_tokens,
            "frozen": True,
            "uplift": False,
            "unchanged": True,
            "selected": tuple(range(len(spans))),
            "skipped_optional": 0,
            "stopped_early": False,
            "status": "frozen_protected_rendering_expands",
        }
    budget = max(base["nominal"], p_tokens)
    scores = _scores(text, spans, method, config, counter, own_counts, neighbour_features)
    selected, skipped, stopped = _choose(text, spans, protected_keep, optional, scores, method, counter, budget)
    updated = render(text, spans, selected)
    achieved = counter.count(updated)
    if achieved > budget and updated != text:
        # Defensive: never emit a non-frozen rendering over the cap.
        updated = text
        achieved = d_tokens
        selected = set(range(len(spans)))
        status = "reverted_cap_violation"
    else:
        status = "selected"
    return updated, {
        **base,
        "budget": budget,
        "achieved": achieved,
        "frozen": False,
        "uplift": budget > base["nominal"],
        "unchanged": updated == text,
        "selected": tuple(sorted(selected)),
        "skipped_optional": skipped,
        "stopped_early": stopped,
        "status": status,
    }


def _scores(text, spans, method, config, counter, own_counts, neighbour_features) -> list[Fraction]:
    scores: list[Fraction] = []
    n_spans = len(spans)
    lam = Fraction(config.lambda_numerator, config.lambda_denominator)
    for index, (start, stop) in enumerate(spans):
        piece = text[start:stop]
        score_i = (position_preference(index, n_spans) + span_frequency(piece, own_counts)) / 2
        if method == "C":
            score_i = score_i + lam * contrast_q(piece, neighbour_features)
        token_count = counter.count(piece)
        if token_count <= 0:
            scores.append(Fraction(-1))
        else:
            scores.append(score_i / token_count)
    return scores


def _choose(text, spans, protected_keep, optional, scores, method, counter, budget):
    selected = set(protected_keep)
    skipped = 0
    stopped = False
    if method == "P":
        order = list(optional)
    else:
        order = sorted(optional, key=lambda index: (-scores[index], index))
    for index in order:
        if scores[index] < 0:
            skipped += 1
            continue
        trial = selected | {index}
        rendered = render(text, spans, trial)
        if counter.count(rendered) <= budget:
            selected.add(index)
        elif method == "P":
            stopped = True
            skipped += len(order) - order.index(index)
            break
        else:
            skipped += 1
    return selected, skipped, stopped


def _trace(text: str, counter, status: str, spans: int) -> dict:
    tokens = counter.count(text)
    return {
        "spans": spans,
        "optional_spans": 0,
        "protected_spans": 0,
        "reasons": [],
        "d": tokens,
        "p": tokens,
        "nominal": tokens,
        "budget": tokens,
        "achieved": tokens,
        "frozen": False,
        "uplift": False,
        "unchanged": True,
        "selected": tuple(range(spans)),
        "skipped_optional": 0,
        "stopped_early": False,
        "single_span": spans == 1,
        "status": status,
    }
