"""Conservative phrase segmentation for the follow-on compressor.

Pieces are character offsets into the original field. A kept piece is that
slice. Concatenation adds no glue. If the grammar cannot establish a complete
anchor, or a detachable alias or illustration is ambiguous, the whole field
is kept.

This module does not see questions, labels, or other cases.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from tool_compression.convert import FLOAT_SUFFIX
from tool_compression.cues import CUE_PATTERNS, cue_reasons
from tool_compression.lexical import unigrams
from tool_compression.segment import _is_abbreviation

SEMICOLON = ";"
EM_DASH = "\u2014"
ALIAS_MARKERS = ("also called", "also known as", "for example")
CLOSERS = "\"'”’"
VALUE_WORDS = (
    "must",
    "shall",
    "required",
    "only",
    "valid",
    "accepted",
    "allowed",
    "one of",
    "either",
    "equal",
    "equals",
    "means",
)

# Completeness lexicon. A missing verb keeps the field. It is not a score.
ACTION_VERBS = frozenset(
    {
        "add",
        "analyse",
        "analyze",
        "append",
        "apply",
        "assign",
        "book",
        "build",
        "calculate",
        "call",
        "cancel",
        "check",
        "choose",
        "classify",
        "close",
        "compare",
        "compute",
        "convert",
        "count",
        "create",
        "decode",
        "delete",
        "describe",
        "determine",
        "disable",
        "display",
        "download",
        "enable",
        "encode",
        "enter",
        "estimate",
        "evaluate",
        "exclude",
        "execute",
        "extract",
        "fetch",
        "filter",
        "find",
        "format",
        "generate",
        "get",
        "identify",
        "include",
        "input",
        "insert",
        "invoke",
        "list",
        "load",
        "locate",
        "lookup",
        "make",
        "match",
        "measure",
        "merge",
        "normalize",
        "normalise",
        "obtain",
        "open",
        "parse",
        "perform",
        "pick",
        "predict",
        "provide",
        "query",
        "read",
        "recommend",
        "remove",
        "replace",
        "request",
        "reserve",
        "resolve",
        "retrieve",
        "return",
        "round",
        "run",
        "save",
        "schedule",
        "search",
        "select",
        "send",
        "set",
        "show",
        "sort",
        "specify",
        "start",
        "stop",
        "submit",
        "suggest",
        "summarize",
        "summarise",
        "translate",
        "update",
        "upload",
        "validate",
        "write",
    }
)

DETERMINERS = frozenset({"a", "an", "the", "this", "that", "these", "those"})
PREPOSITIONS = frozenset(
    {
        "about",
        "across",
        "after",
        "against",
        "among",
        "as",
        "at",
        "before",
        "between",
        "by",
        "down",
        "during",
        "for",
        "from",
        "in",
        "into",
        "near",
        "of",
        "off",
        "on",
        "out",
        "over",
        "per",
        "through",
        "to",
        "toward",
        "towards",
        "under",
        "up",
        "upon",
        "via",
        "with",
        "within",
        "without",
    }
)
CONJUNCTIONS = frozenset({"and", "or", "but", "nor", "yet", "so"})
AUXILIARIES = frozenset(
    {
        "am",
        "are",
        "be",
        "been",
        "being",
        "can",
        "could",
        "did",
        "do",
        "does",
        "had",
        "has",
        "have",
        "is",
        "may",
        "might",
        "must",
        "shall",
        "should",
        "was",
        "were",
        "will",
        "would",
    }
)
PRONOUNS = frozenset({"her", "his", "it", "its", "our", "their", "them", "they", "we", "you", "your"})
ADVERBS = frozenset({"also", "here", "just", "not", "only", "then", "there", "than", "very"})
CLOSED = DETERMINERS | PREPOSITIONS | CONJUNCTIONS | AUXILIARIES | PRONOUNS | ADVERBS
DANGLING = PREPOSITIONS | DETERMINERS | CONJUNCTIONS | AUXILIARIES | frozenset({"also"})
ADJECTIVE_ONLY = frozenset(
    {
        "absolute",
        "current",
        "empty",
        "full",
        "invalid",
        "local",
        "maximum",
        "minimum",
        "new",
        "old",
        "optional",
        "partial",
        "previous",
        "raw",
        "relative",
        "total",
        "valid",
    }
)
BLOCKING_GUARDS = frozenset(
    {
        "condition",
        "default",
        "direction",
        "float_type_cue",
        "negation",
        "restriction",
        "return",
        "type",
        "unit",
    }
)

_OPENERS = {'"': '"', "'": "'", "“": "”", "‘": "’"}
_ALIAS_HEAD = re.compile(r"(?i)^(?:also called|also known as|for example)\b")
_LEAD = re.compile(r"^[\s;\u2014()]+")
_TRAIL = re.compile(r"[)\]\s.;!?]+$")
_VALUE = re.compile(
    r"(?i)\b(?:must|shall|required|only|valid|accepted|allowed|one of|either|equals?|means)\b"
    r"|\"[^\"]+\"|'[^']+'|“[^”]+”|‘[^’]+’"
)
_COORDINATOR = re.compile(r"(?i)^(and|or|but|nor|yet)\b")
_DIRECTION = re.compile(
    r"\b(?:above|below|before|after|left|right|north|south|east|west|upstream|downstream|toward|towards)\b",
    re.IGNORECASE,
)
_TYPE = re.compile(
    r"\b(?:float|integer|int|string|boolean|bool|number|array|object)\s+type\b",
    re.IGNORECASE,
)
_RETURN = re.compile(r"\breturns?\b|\breturning\b|\breturn value\b", re.IGNORECASE)
_RANGE_WORD = re.compile(r"\b(?:range|inclusive|exclusive)\b", re.IGNORECASE)
FLOAT_SENTENCE = FLOAT_SUFFIX.strip()
FLOAT_STEM = FLOAT_SENTENCE[:-1] if FLOAT_SENTENCE.endswith(".") else FLOAT_SENTENCE


def contains_float_cue(text: str) -> bool:
    """True when the converted prose float sentence is present, with or without its period."""
    return FLOAT_STEM in text


@dataclass(frozen=True)
class Piece:
    start: int
    end: int
    kind: str
    reasons: tuple[str, ...]

    def text(self, source: str) -> str:
        return source[self.start : self.end]


@dataclass(frozen=True)
class Parse:
    status: str
    reason: str | None
    pieces: tuple[Piece, ...]


def parse_field(text: str, role: str) -> Parse:
    """Return offset pieces or a whole-field fallback.

    ``role`` is ``function`` or ``parameter``.
    """
    if role not in {"function", "parameter"}:
        raise ValueError(role)
    if text is None:
        raise TypeError("description must be a string")
    if text == "" or not text.strip():
        return Parse("empty_or_whitespace", "empty_or_whitespace", ())
    mask = _literal_mask(text)
    if mask is None:
        return _whole(text, "unclosed_literal")
    parens = _parentheticals(text, mask)
    if parens is None:
        return _whole(text, "unbalanced_parenthetical")
    ranges = _ranges(text, mask, parens)
    if ranges is None:
        return _whole(text, "parse_gap")
    return _classify(text, role, ranges)


def render_pieces(text: str, pieces: tuple[Piece, ...] | list[Piece], selected: set[int]) -> str:
    """Concatenate kept slices. Keeping every piece returns ``text`` itself."""
    if not pieces or len(selected) == len(pieces):
        return text
    ordered = sorted(selected)
    return "".join(text[pieces[index].start : pieces[index].end] for index in ordered)


def boundary_problem(text: str, pieces: tuple[Piece, ...] | list[Piece], selected: set[int]) -> str | None:
    """Return a reason when a subset would glue tokens or unbalance delimiters."""
    if not pieces:
        return None
    if "".join(text[piece.start : piece.end] for piece in pieces) != text:
        return "parse_does_not_tile"
    ordered = sorted(selected)
    if not ordered:
        return "empty_selection"
    parts: list[str] = []
    previous_end = None
    for index in ordered:
        piece = pieces[index]
        if previous_end is not None and piece.start != previous_end:
            left = text[previous_end - 1 : previous_end]
            right = text[piece.start : piece.start + 1]
            if left.isalnum() and right.isalnum():
                return "joined_alphanumerics"
        previous_end = piece.end
        parts.append(text[piece.start : piece.end])
    rendered = "".join(parts)
    if rendered[:1].isspace() and not text[:1].isspace():
        return "leading_whitespace"
    if rendered[-1:].isspace() and not text[-1:].isspace():
        return "trailing_whitespace"
    if rendered.count("(") != rendered.count(")"):
        return "unbalanced_parentheses"
    if _literal_mask(rendered) is None:
        return "unbalanced_quotes"
    return None


def guard_reasons(text: str) -> tuple[str, ...]:
    """v1 cue categories plus the follow-on direction, quantity, type, and return labels."""
    reasons = list(cue_reasons(text))
    if _DIRECTION.search(text):
        reasons.append("direction")
    if _RANGE_WORD.search(text) or re.search(r"\d", text):
        reasons.append("quantity")
    if contains_float_cue(text) or _TYPE.search(text):
        reasons.append("type")
    if contains_float_cue(text):
        reasons.append("float_type_cue")
    if _RETURN.search(text):
        reasons.append("return")
    return tuple(dict.fromkeys(reasons))


def anchor_complete(text: str, role: str) -> bool:
    tokens = unigrams(text)
    if not tokens or _ends_dangling(tokens):
        return False
    if role == "parameter" and _noun_phrase_complete(tokens):
        return True
    if len(tokens) < 2:
        return False
    return _action_complete(tokens)


def _whole(text: str, reason: str) -> Parse:
    piece = Piece(0, len(text), "protected", (reason, "unclassified"))
    return Parse("fallback", reason, (piece,))


def _classify(text: str, role: str, ranges: list[tuple[int, int]]) -> Parse:
    pieces: list[Piece] = []
    ambiguous = False
    anchor_set = False
    for start, end in ranges:
        fragment = text[start:end]
        if _is_terminal(fragment):
            pieces.append(Piece(start, end, "terminal", ("terminal_punctuation",)))
            continue
        detach = _detach_status(fragment)
        if detach == "ambiguous":
            ambiguous = True
            reasons = guard_reasons(fragment) or ("ambiguous_detach",)
            pieces.append(Piece(start, end, "protected", tuple(dict.fromkeys(("protected",) + tuple(reasons)))))
            continue
        if detach == "optional":
            pieces.append(Piece(start, end, "optional", ("detachable_alias_or_illustration",)))
            continue
        if not anchor_set:
            if anchor_complete(fragment, role):
                reasons = tuple(dict.fromkeys(("anchor",) + guard_reasons(fragment)))
                pieces.append(Piece(start, end, "anchor", reasons))
                anchor_set = True
                continue
            return _whole(text, "incomplete_anchor")
        reasons = guard_reasons(fragment)
        if reasons:
            reasons = tuple(dict.fromkeys(("protected",) + reasons))
        else:
            reasons = ("unclassified",)
        pieces.append(Piece(start, end, "protected", reasons))
    if ambiguous:
        return _whole(text, "ambiguous_detach")
    if not anchor_set:
        return _whole(text, "incomplete_anchor")
    if "".join(text[piece.start : piece.end] for piece in pieces) != text:
        return _whole(text, "parse_gap")
    return Parse("parsed", None, tuple(pieces))


def _detach_status(fragment: str) -> str:
    core = _TRAIL.sub("", _LEAD.sub("", fragment))
    if not _ALIAS_HEAD.match(core):
        return "no"
    if "," in fragment or _VALUE.search(fragment):
        return "ambiguous"
    if set(guard_reasons(fragment)) & BLOCKING_GUARDS:
        return "ambiguous"
    return "optional"


def _noun_phrase_complete(tokens: list[str]) -> bool:
    if not tokens or tokens[0] in PREPOSITIONS:
        return False
    content = [token for token in tokens if token not in CLOSED and token not in DANGLING]
    if not content:
        return False
    return any(token not in ADJECTIVE_ONLY for token in content)


def _action_complete(tokens: list[str]) -> bool:
    verb_at = None
    for index, token in enumerate(tokens):
        if _is_verb(token):
            verb_at = index
            break
        if token not in CLOSED and token not in DANGLING:
            return False
    if verb_at is None:
        return False
    return any(
        token not in CLOSED and token not in DANGLING and not _is_verb(token) for token in tokens[verb_at + 1 :]
    )


def _ends_dangling(tokens: list[str]) -> bool:
    return not tokens or tokens[-1] in DANGLING


def _is_verb(token: str) -> bool:
    if token in ACTION_VERBS:
        return True
    for suffix in ("es", "s", "ed", "ing", "d"):
        if token.endswith(suffix) and len(token) > len(suffix):
            stem = token[: -len(suffix)]
            if stem in ACTION_VERBS or (suffix in {"ing", "d", "ed"} and f"{stem}e" in ACTION_VERBS):
                return True
    return False


def _is_terminal(fragment: str) -> bool:
    core = fragment.strip(CLOSERS + " \t")
    return core in {".", "!", "?"} and len(fragment) <= 6


def _ranges(text: str, mask: list[bool], parens: list[tuple[int, int]]) -> list[tuple[int, int]] | None:
    blocks: list[tuple[int, int]] = []
    for start, end in parens:
        left = start
        while left > 0 and text[left - 1].isspace() and not mask[left - 1]:
            left -= 1
        right = end
        if left == 0:
            while right < len(text) and text[right].isspace() and not mask[right]:
                right += 1
        blocks.append((left, right))
    blocks = _reject_overlap(blocks)
    if blocks is None:
        return None
    inside = [False] * len(text)
    for start, end in blocks:
        for index in range(start, end):
            inside[index] = True
    cuts = {0, len(text)}
    for start, end in blocks:
        cuts.add(start)
        cuts.add(end)
    for index in _semicolon_starts(text, mask, inside):
        cuts.add(index)
    for index in _emdash_starts(text, mask, inside):
        cuts.add(index)
    for index in _sentence_starts(text, mask, inside):
        cuts.add(index)
    ordered = [cut for cut in sorted(cuts) if not any(start < cut < end for start, end in blocks)]
    ranges = [(left, right) for left, right in zip(ordered, ordered[1:]) if left < right]
    if "".join(text[left:right] for left, right in ranges) != text:
        return None
    return _peel_terminal(text, ranges, mask)


def _reject_overlap(blocks: list[tuple[int, int]]) -> list[tuple[int, int]] | None:
    if not blocks:
        return []
    ordered = sorted(blocks)
    merged = [ordered[0]]
    for start, end in ordered[1:]:
        _, previous_end = merged[-1]
        if start < previous_end:
            return None
        merged.append((start, end))
    return merged


def _literal_mask(text: str) -> list[bool] | None:
    mask = [False] * len(text)
    index = 0
    limit = len(text)
    while index < limit:
        char = text[index]
        if char in _OPENERS and _can_open(text, index, char):
            closer = _OPENERS[char]
            cursor = index + 1
            closed = None
            while cursor < limit:
                if text[cursor] == "\\" and closer in {'"', "'"} and cursor + 1 < limit:
                    cursor += 2
                    continue
                if text[cursor] == closer and _can_close(text, cursor, closer):
                    closed = cursor
                    break
                cursor += 1
            if closed is None:
                if char == "'":
                    index += 1
                    continue
                return None
            for position in range(index, closed + 1):
                mask[position] = True
            index = closed + 1
            continue
        index += 1
    return mask


def _can_open(text: str, index: int, char: str) -> bool:
    if char == "'" and index > 0 and text[index - 1].isalnum():
        return False
    return True


def _can_close(text: str, index: int, closer: str) -> bool:
    if closer == "'" and index + 1 < len(text) and text[index + 1].isalnum():
        return False
    return True


def _parentheticals(text: str, mask: list[bool]) -> list[tuple[int, int]] | None:
    depth = 0
    start = None
    ranges: list[tuple[int, int]] = []
    for index, char in enumerate(text):
        if mask[index]:
            continue
        if char == "(":
            if depth == 0:
                start = index
            depth += 1
        elif char == ")":
            if depth == 0 or start is None:
                return None
            depth -= 1
            if depth == 0:
                ranges.append((start, index + 1))
                start = None
    if depth != 0:
        return None
    return ranges


def _semicolon_starts(text: str, mask: list[bool], inside: list[bool]) -> list[int]:
    starts = []
    for index, char in enumerate(text):
        if char != SEMICOLON or mask[index] or inside[index]:
            continue
        if _coordinated_negation(text, index):
            continue
        starts.append(index)
    return starts


def _emdash_starts(text: str, mask: list[bool], inside: list[bool]) -> list[int]:
    starts = []
    for index, char in enumerate(text):
        if char != EM_DASH or mask[index] or inside[index]:
            continue
        if index == 0 or index + 1 >= len(text):
            continue
        if not text[index - 1].isspace() or not text[index + 1].isspace():
            continue
        start = index - 1
        while start > 0 and text[start - 1].isspace() and not mask[start - 1] and not inside[start - 1]:
            start -= 1
        if _coordinated_negation(text, start):
            continue
        starts.append(start)
    return starts


def _sentence_starts(text: str, mask: list[bool], inside: list[bool]) -> list[int]:
    starts = []
    index = 0
    limit = len(text)
    while index < limit:
        if mask[index] or inside[index]:
            index += 1
            continue
        char = text[index]
        if char in ".!?" and not (index > 0 and text[index - 1] == "."):
            if char == "." and index > 0 and text[index - 1].isdigit():
                index += 1
                continue
            cursor = index + 1
            while cursor < limit and text[cursor] in CLOSERS and not mask[cursor] and not inside[cursor]:
                cursor += 1
            at_boundary = cursor >= limit or text[cursor].isspace()
            if at_boundary and not _is_abbreviation(text, index):
                if cursor < limit:
                    starts.append(cursor)
                index = cursor
                continue
        index += 1
    return starts


def _coordinated_negation(text: str, piece_start: int) -> bool:
    rest = re.sub(r"^[\s;\u2014]+", "", text[piece_start:])
    if not _COORDINATOR.match(rest):
        return False
    negation = next(pattern for name, pattern in CUE_PATTERNS if name == "negation")
    return negation.search(text[:piece_start]) is not None


def _peel_terminal(text: str, ranges: list[tuple[int, int]], mask: list[bool]) -> list[tuple[int, int]] | None:
    if not ranges:
        return ranges
    start, end = ranges[-1]
    if end != len(text) or start >= end:
        return ranges
    index = end - 1
    while index >= start and text[index] in CLOSERS:
        index -= 1
    if index <= start or text[index] not in ".!?":
        return ranges
    if mask[index]:
        return ranges
    if text[index] == "." and index > 0 and (text[index - 1].isdigit() or text[index - 1] == "."):
        return ranges
    if text[index] == "." and _is_abbreviation(text, index):
        return ranges
    return ranges[:-1] + [(start, index), (index, end)]
