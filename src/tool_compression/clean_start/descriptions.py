"""Structural parse of one original function description.

Editors S and X both read original text through this parse. It recognises three
things by grammar on the tool's own text, never by tool name, suite name, case id,
question, or answer:

- the official language hint at the end (official preparation, never edited);
- a suite preamble ``This tool belongs to <suite>[, which ...]. [It ...]. Tool description: ``
  that the tool's own text separates from its description with that label;
- a leading subject frame such as ``This function retrieves`` before the action.
"""

from __future__ import annotations

import re

from tool_compression.clean_start.prepare import JAVA_HINT, JAVASCRIPT_HINT, PYTHON_HINT

PROTECTED_SUFFIXES = (PYTHON_HINT, JAVA_HINT, JAVASCRIPT_HINT)

_SUITE = re.compile(
    r"^(?P<membership>This tool belongs to (?:the )?[^.,]+?(?: that [^.,]+?)?)"
    r"(?P<elaboration>(?:, which [^.]*)?\.(?: It [^.]*(?:\betc)?\.)?)"
    r"(?P<label> Tool description: ?)"
)
_FRAME_SUBJECT = r"(?:This|The) (?:function|tool|API|method|endpoint|service|operation)"
_FRAME_INFINITIVE = (
    r"(?:is used|is designed|was designed|can be used|is intended|is meant) to |"
    r"(?:allows|enables|lets|helps) (?:you|users|the user|a user)(?: to)? |"
    r"(?:will|can) "
)
_FRAME = re.compile(
    rf"^(?P<frame>{_FRAME_SUBJECT} (?P<aux>{_FRAME_INFINITIVE})?)(?P<verb>[a-z][a-z-]*)\b"
)
_AUXILIARY = {"is", "was", "has", "does", "are", "were", "had"}


def split_protected(text: str) -> tuple[str, str]:
    """Return ``(head, protected_suffix)``. The suffix is official preparation."""
    for suffix in PROTECTED_SUFFIXES:
        if text.endswith(suffix):
            return text[: -len(suffix)], suffix
    return text, ""


def suite_preamble(head: str) -> dict | None:
    """Spans of the suite preamble when the tool's own text labels its description."""
    match = _SUITE.match(head)
    if match is None:
        return None
    core_start = match.end()
    if core_start >= len(head):
        return None
    return {
        "membership": [match.start("membership"), match.end("membership")],
        "elaboration": [match.start("elaboration"), match.end("elaboration")],
        "label": [match.start("label"), match.end("label")],
        "core_start": core_start,
    }


def leading_frame(text: str, offset: int = 0) -> dict | None:
    """A subject frame before the action at ``text[offset:]``.

    With an infinitive or modal frame the next word is the bare verb. With a bare
    subject the next word has to read as a third-person present verb.
    """
    match = _FRAME.match(text[offset:])
    if match is None:
        return None
    verb = match.group("verb")
    if match.group("aux") is None:
        if verb in _AUXILIARY or not verb.endswith("s") or verb.endswith("ss"):
            return None
    return {
        "frame": [offset, offset + match.end("frame")],
        "verb": verb,
        "infinitive": match.group("aux") is not None,
    }


def core_start(description: str) -> int:
    """Offset where the tool's own action text begins."""
    head, _suffix = split_protected(description)
    suite = suite_preamble(head)
    start = suite["core_start"] if suite else 0
    frame = leading_frame(head, start)
    if frame is not None:
        start = frame["frame"][1]
    return start


def action_sentence(description: str) -> tuple[str, int]:
    """First sentence of the tool's own action text, and its offset."""
    head, _suffix = split_protected(description)
    start = core_start(description)
    core = head[start:]
    match = re.search(r"(?<!\be\.g)(?<!\bi\.e)\.(?:\s|$)", core)
    end = match.start() + 1 if match else len(core)
    return core[:end].strip(), start
