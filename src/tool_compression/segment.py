"""Conservative sentence and newline segmentation, plus source-order rendering."""

import re

# A period in one of these tokens does not end a span.
ABBREVIATIONS = frozenset(
    {
        "e.g.",
        "i.e.",
        "etc.",
        "vs.",
        "dr.",
        "mr.",
        "mrs.",
        "ms.",
        "fig.",
        "eq.",
        "vol.",
        "al.",
        "st.",
    }
)

_CLOSERS = "\"'”’"
_LEADING_MARK = re.compile(r"^[^a-z]+")


def segment_spans(text: str) -> list[tuple[int, int]]:
    """Return non-overlapping content spans.

    Newlines are boundaries. `.`, `!`, and `?` end a span only when they are
    followed by whitespace or the end of the text, are not inside an ellipsis,
    are not a decimal point, and are not a listed abbreviation. Anything else
    stays in one span. Empty and whitespace-only strings yield no spans.
    """
    if not text or not text.strip():
        return []
    ends: list[int] = []
    index = 0
    limit = len(text)
    while index < limit:
        char = text[index]
        if char == "\n":
            ends.append(index)
            index += 1
            continue
        if char in ".!?" and not (index > 0 and text[index - 1] == "."):
            if char == "." and index > 0 and text[index - 1].isdigit():
                index += 1
                continue
            cursor = index + 1
            while cursor < limit and text[cursor] in _CLOSERS:
                cursor += 1
            at_boundary = cursor >= limit or text[cursor].isspace()
            if at_boundary and not _is_abbreviation(text, index):
                ends.append(cursor)
                index = cursor
                continue
        index += 1
    if not ends or ends[-1] < limit:
        tail = ends[-1] if ends else 0
        if text[tail:].strip():
            ends.append(limit)
    spans: list[tuple[int, int]] = []
    previous = 0
    for end in ends:
        start = previous
        stop = end
        while start < stop and text[start].isspace():
            start += 1
        while stop > start and text[stop - 1].isspace():
            stop -= 1
        if start < stop:
            spans.append((start, stop))
        previous = end
    return spans


def render(text: str, spans: list[tuple[int, int]], keep: set[int]) -> str:
    """Join kept spans in source order.

    Keeping every span returns the original string. A kept first span keeps
    the original prefix. A kept last span keeps the original suffix. Adjacent
    kept spans keep the original characters between them. A gap of one or more
    dropped spans is replaced by a single ASCII space.
    """
    if not spans or len(keep) == len(spans):
        return text
    ordered = [index for index in range(len(spans)) if index in keep]
    if not ordered:
        return ""
    parts: list[str] = []
    first = ordered[0]
    if first == 0:
        parts.append(text[: spans[0][1]])
    else:
        parts.append(text[spans[first][0] : spans[first][1]])
    for previous, current in zip(ordered, ordered[1:]):
        if current == previous + 1:
            parts.append(text[spans[previous][1] : spans[current][1]])
        else:
            parts.append(" ")
            parts.append(text[spans[current][0] : spans[current][1]])
    if ordered[-1] == len(spans) - 1:
        parts.append(text[spans[-1][1] :])
    return "".join(parts)


def _is_abbreviation(text: str, period_index: int) -> bool:
    start = period_index
    while start > 0 and not text[start - 1].isspace():
        start -= 1
    token = _LEADING_MARK.sub("", text[start : period_index + 1].lower())
    return token in ABBREVIATIONS
