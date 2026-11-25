"""Render U, S, X, and SX for one converted tool catalogue.

U is the unmodified model-facing catalogue. S edits one tool at a time.
X qualifies rivals on U, with S hidden. SX starts from S and appends the X cue
bytes. Questions are not arguments.
"""

from __future__ import annotations

from copy import deepcopy

from tool_compression.clean_start.editor_s import edit_tool
from tool_compression.clean_start.editor_x import qualify_catalogue
from tool_compression.clean_start.pin import ARMS
from tool_compression.clean_start.prepare import JAVA_HINT, JAVASCRIPT_HINT, PYTHON_HINT

_HINTS = (PYTHON_HINT, JAVA_HINT, JAVASCRIPT_HINT)

CUE_SEPARATOR = " "


def render_tools(tools: list[dict]) -> dict:
    if not isinstance(tools, list):
        raise ValueError("render_tools expected a tool list")
    original = deepcopy(tools)
    # The official language hint is shared boilerplate. X qualifies the wording
    # underneath it, then the cue is appended after the hint on the text we send.
    qualification = _without_language_hint(original)
    edited_s = []
    s_changes = []
    for tool in original:
        updated, rows = edit_tool(deepcopy(tool))
        edited_s.append(updated)
        for row in rows:
            if row.get("adopted"):
                s_changes.append({
                    "arm": "S",
                    "function": row.get("function_name"),
                    "pointer": row.get("pointer"),
                    "before": row.get("original"),
                    "after": row.get("final"),
                    "change_class": row.get("change_class"),
                })
    decisions = qualify_catalogue(qualification)
    if len(decisions) != len(original):
        raise RuntimeError("editor X returned a different tool count")
    edited_x = []
    edited_sx = []
    x_changes = []
    for tool, edited, decision in zip(original, edited_s, decisions):
        cue = decision.get("cue") or ""
        edited_x.append(_with_cue(tool, cue))
        edited_sx.append(_with_cue(edited, cue))
        if cue:
            x_changes.append({
                "arm": "X",
                "function": decision.get("function_name"),
                "pointer": "/function/description",
                "rival": (decision.get("rival") or {}).get("function_name"),
                "cue": cue,
                "axis": decision.get("axis"),
            })
    rendered = {
        "U": original,
        "S": edited_s,
        "X": edited_x,
        "SX": edited_sx,
    }
    unknown = [name for name in rendered if name not in ARMS]
    if unknown or tuple(rendered) != ARMS:
        raise RuntimeError("arm names must be U, S, X, SX")
    return {
        "arms": rendered,
        "changes": s_changes + x_changes,
        "x_decisions": [
            {
                "function": row.get("function_name"),
                "cue": row.get("cue") or "",
                "rival": (row.get("rival") or {}).get("function_name"),
                "no_cue_reason": row.get("no_cue_reason"),
                "control": row.get("control"),
            }
            for row in decisions
        ],
    }


def _without_language_hint(tools: list[dict]) -> list[dict]:
    shadow = deepcopy(tools)
    for tool in shadow:
        description = tool["function"].get("description")
        if not isinstance(description, str):
            continue
        for hint in _HINTS:
            if description.endswith(hint):
                tool["function"]["description"] = description[: -len(hint)]
                break
    return shadow


def _with_cue(tool: dict, cue: str) -> dict:
    copied = deepcopy(tool)
    if not cue:
        return copied
    description = copied["function"]["description"]
    copied["function"]["description"] = description + CUE_SEPARATOR + cue
    return copied
