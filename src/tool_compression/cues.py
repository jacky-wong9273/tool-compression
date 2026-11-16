"""Provisional protection cues.

A span is protected when it is the first span in its field or when its
text matches one of these lexical cues. The cues are a fallible heuristic,
not a semantic guarantee, and they were not searched against labels.
"""

import re

# Reason code -> pattern. Order is the reported order.
CUE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "negation",
        re.compile(r"\b(?:not|no|never|none|without|cannot|can't)\b|n't\b", re.IGNORECASE),
    ),
    (
        "condition",
        re.compile(r"\b(?:if|unless|when|whether|except|otherwise|provided)\b", re.IGNORECASE),
    ),
    (
        "unit",
        re.compile(
            r"\b(?:celsius|fahrenheit|degrees?|percent(?:age)?|met(?:er|re)s?|kilomet(?:er|re)s?|"
            r"seconds?|minutes?|hours?|days?|bytes?|pixels?|miles?|feet|foot|inches?|inch|"
            r"lit(?:er|re)s?|gallons?|watts?|kilograms?|grams?|kg|km|cm|mm|mb|gb|hz|ms)\b|%|°",
            re.IGNORECASE,
        ),
    ),
    (
        "default",
        re.compile(
            r"\bdefaults?\b|\bby default\b|\bif not provided\b|\bif omitted\b|\botherwise\b",
            re.IGNORECASE,
        ),
    ),
    (
        "restriction",
        re.compile(
            r"\b(?:must|required|shall|only|minimum|maximum|between)\b|"
            r"\bat least\b|\bat most\b|\bno more than\b|\bno less than\b|"
            r"\bgreater than\b|\bless than\b",
            re.IGNORECASE,
        ),
    ),
    (
        "literal",
        re.compile(r"\d|'[^']+'|\"[^\"]+\""),
    ),
)


def cue_reasons(text: str) -> tuple[str, ...]:
    return tuple(name for name, pattern in CUE_PATTERNS if pattern.search(text))
