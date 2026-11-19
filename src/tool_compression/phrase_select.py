"""Own-tool scores, the pinned prior q, and the follow-on field selector.

T1 ranks optional pieces by the own-tool overlap ratio only. T2 adds
``contrast_weight × q`` on those same pieces. Protected pieces are kept.
Ties break toward the earlier source offset. Each optional piece is tried
once against the re-rendered field.
"""

from __future__ import annotations

from fractions import Fraction
import hashlib

from tool_compression.adapter import property_names
from tool_compression.followon_config import FollowOnConfig
from tool_compression.lexical import contrast_q, unigrams
from tool_compression.phrase import Piece, Parse, boundary_problem, contains_float_cue, render_pieces


def fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def nominal_cap(token_count: int, config: FollowOnConfig) -> int:
    if token_count <= 0:
        return 0
    return (token_count * config.retention_numerator) // config.retention_denominator


def field_budget(original_tokens: int, protected_tokens: int, config: FollowOnConfig) -> tuple[int | None, int]:
    """Return ``(budget, nominal)``. A null budget is the non-expansion case."""
    nominal = nominal_cap(original_tokens, config)
    if protected_tokens > original_tokens:
        return None, nominal
    return max(nominal, protected_tokens), nominal


def identifier_terms(tool: dict) -> set[str]:
    """Case-folded terms of the original function name and property names."""
    terms: set[str] = set()
    function = tool.get("function") if isinstance(tool, dict) else None
    if isinstance(function, dict) and isinstance(function.get("name"), str):
        terms.update(unigrams(function["name"]))
    for name in property_names(tool):
        terms.update(unigrams(str(name)))
    return {term for term in terms if term}


def own_score(fragment: str, identifiers: set[str]) -> Fraction:
    terms = {term for term in unigrams(fragment) if term}
    if not terms:
        return Fraction(0)
    return Fraction(len(terms & identifiers), len(terms))


def condition_score(own: Fraction, q_value: Fraction, config: FollowOnConfig) -> Fraction:
    weight = Fraction(config.contrast_numerator, config.contrast_denominator)
    return own + weight * q_value


def select_parsed_field(
    text: str,
    parse: Parse,
    identifiers: set[str],
    neighbour_features: list[set[str]],
    counter,
    conditions: tuple[FollowOnConfig, ...],
) -> dict:
    """Select pieces for every condition. The input string is not edited in place."""
    if parse.status == "empty_or_whitespace":
        return _uniform(text, counter, conditions, status="empty_or_whitespace", reason="empty_or_whitespace", pieces=())
    if parse.status != "parsed":
        return _uniform(
            text,
            counter,
            conditions,
            status=f"fallback_{parse.reason}",
            reason=parse.reason,
            pieces=parse.pieces,
        )
    pieces = parse.pieces
    protected = {index for index, piece in enumerate(pieces) if piece.kind != "optional"}
    optional = [index for index, piece in enumerate(pieces) if piece.kind == "optional"]
    protected_problem = boundary_problem(text, pieces, protected)
    if protected_problem:
        return _uniform(
            text,
            counter,
            conditions,
            status="fallback_broken_boundary",
            reason=protected_problem,
            pieces=pieces,
        )
    protected_text = render_pieces(text, pieces, protected)
    original_tokens = counter.count(text)
    protected_tokens = counter.count(protected_text)
    budget, nominal = field_budget(original_tokens, protected_tokens, conditions[0])
    q_values = [contrast_q(piece.text(text), neighbour_features) for piece in pieces]
    own_values = [own_score(piece.text(text), identifiers) for piece in pieces]
    score_table = {
        config.condition: [condition_score(own, q_value, config) for own, q_value in zip(own_values, q_values)]
        for config in conditions
    }
    base = {
        "d": original_tokens,
        "p": protected_tokens,
        "nominal": nominal,
        "budget": budget,
        "optional_count": len(optional),
        "single_content_clause": _single_clause(pieces),
        "pieces": pieces,
        "own_scores": own_values,
        "q_scores": q_values,
        "score_table": score_table,
        "protected": protected,
        "optional": optional,
    }
    if budget is None:
        payload = _uniform(
            text,
            counter,
            conditions,
            status="non_expansion",
            reason="protected_rendering_exceeds_original",
            pieces=pieces,
        )
        payload.update(base)
        return payload
    alone_fits = {}
    for index in optional:
        rendered = render_pieces(text, pieces, protected | {index})
        problem = boundary_problem(text, pieces, protected | {index})
        tokens = counter.count(rendered)
        alone_fits[index] = problem is None and tokens <= budget and tokens <= original_tokens
    competing = []
    for left_index, left in enumerate(optional):
        for right in optional[left_index + 1 :]:
            if not (alone_fits[left] and alone_fits[right]):
                continue
            both = protected | {left, right}
            rendered = render_pieces(text, pieces, both)
            problem = boundary_problem(text, pieces, both)
            tokens = counter.count(rendered)
            if problem is not None or tokens > budget or tokens > original_tokens:
                competing.append((left, right))
    outputs = {}
    for config in conditions:
        outputs[config.condition] = _choose(
            text,
            pieces,
            protected,
            optional,
            score_table[config.condition],
            counter,
            budget,
            original_tokens,
        )
    statuses = {output["status"] for output in outputs.values()}
    if statuses == {"identity_all_kept"}:
        status = "identity_all_kept"
    elif "float_cue_restored" in statuses:
        status = "float_cue_restored"
    elif any(item.startswith("fallback_") for item in statuses):
        status = "fallback_broken_boundary"
    else:
        status = "selected"
    return {
        **base,
        "status": status,
        "reason": None,
        "alone_fits": alone_fits,
        "competing_pairs": competing,
        "outputs": outputs,
        "protected_fills_cap": bool(optional) and not any(alone_fits.values()),
    }


def _choose(text, pieces, protected, optional, scores, counter, budget, original_tokens) -> dict:
    selected = set(protected)
    decisions = {index: "protected" for index in protected}
    order = sorted(optional, key=lambda index: (-scores[index], pieces[index].start, index))
    for index in order:
        trial = selected | {index}
        rendered = render_pieces(text, pieces, trial)
        problem = boundary_problem(text, pieces, trial)
        tokens = counter.count(rendered)
        if problem is None and tokens <= budget and tokens <= original_tokens:
            selected.add(index)
            decisions[index] = "kept"
        else:
            decisions[index] = "skipped_does_not_fit" if problem is None else "skipped_broken_boundary"
    if selected == set(range(len(pieces))):
        rendered = text
        status = "identity_all_kept"
    else:
        rendered = render_pieces(text, pieces, selected)
        problem = boundary_problem(text, pieces, selected)
        if problem is not None or counter.count(rendered) > original_tokens:
            rendered = text
            selected = set(range(len(pieces)))
            status = "fallback_broken_boundary"
            decisions = {index: "protected" for index in range(len(pieces))}
        elif contains_float_cue(text) and not contains_float_cue(rendered):
            rendered = text
            selected = set(range(len(pieces)))
            status = "float_cue_restored"
            decisions = {index: "protected" for index in range(len(pieces))}
        else:
            status = "selected"
    if rendered == text:
        rendered = text
    return {
        "text": rendered,
        "status": status,
        "selected": tuple(sorted(selected)),
        "decisions": decisions,
        "achieved": counter.count(rendered),
        "unchanged": rendered == text,
        "order": order,
    }


def _uniform(text, counter, conditions, status, reason, pieces) -> dict:
    tokens = counter.count(text)
    outputs = {}
    for config in conditions:
        outputs[config.condition] = {
            "text": text,
            "status": status,
            "selected": tuple(range(len(pieces))),
            "decisions": {index: "protected" for index in range(len(pieces))},
            "achieved": tokens,
            "unchanged": True,
            "order": [],
        }
    return {
        "status": status,
        "reason": reason,
        "d": tokens,
        "p": tokens,
        "nominal": nominal_cap(tokens, conditions[0]) if conditions else tokens,
        "budget": tokens,
        "optional_count": 0,
        "single_content_clause": True,
        "pieces": pieces,
        "own_scores": [],
        "q_scores": [],
        "score_table": {config.condition: [] for config in conditions},
        "protected": set(range(len(pieces))),
        "optional": [],
        "alone_fits": {},
        "competing_pairs": [],
        "outputs": outputs,
        "protected_fills_cap": False,
    }


def _single_clause(pieces: tuple[Piece, ...]) -> bool:
    content = [piece for piece in pieces if piece.kind != "terminal"]
    return len(content) <= 1 and all(piece.kind != "optional" for piece in pieces)
