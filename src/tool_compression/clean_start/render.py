"""Render U, S, X, and SX for one converted tool catalogue.

U is the unmodified model-facing catalogue. S edits one tool at a time.
X qualifies rivals on U, with S hidden. SX starts from S and appends the X cue
bytes. Questions are not arguments.
"""

from __future__ import annotations

from copy import deepcopy
import json

from tool_compression.adapter import description_slots
from tool_compression.clean_start.editor_s import S_RULES_VERSION, edit_tool
from tool_compression.clean_start.editor_x import X_RULES_VERSION, qualify_catalogue
from tool_compression.clean_start.pin import ARMS

CUE_SEPARATOR = " "
CUE_POINTER = "/function/description"


def render_tools(tools: list[dict]) -> dict:
    if not isinstance(tools, list):
        raise ValueError("render_tools expected a tool list")
    original = deepcopy(tools)
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
    decisions = qualify_catalogue(deepcopy(original))
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
                "pointer": CUE_POINTER,
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
    verify_arms(rendered, [decision.get("cue") or "" for decision in decisions])
    return {
        "arms": rendered,
        "rules": {"S": S_RULES_VERSION, "X": X_RULES_VERSION},
        "changes": s_changes + x_changes,
        "x_decisions": [
            {
                "function": row.get("function_name"),
                "cue": row.get("cue") or "",
                "rival": (row.get("rival") or {}).get("function_name"),
                "axis": row.get("axis"),
                "no_cue_reason": row.get("no_cue_reason"),
                "control": row.get("control"),
            }
            for row in decisions
        ],
    }


def verify_arms(arms: dict, cues: list[str]) -> None:
    """Fail closed unless every arm keeps U outside its authorised description bytes.

    Membership, order, names, and every non-description byte equal U. X equals U
    plus one space and the cue on the function description. SX equals S plus the
    same bytes at the same path. A tool without a cue is byte-identical to U in X
    and to S in SX.
    """
    original = arms["U"]
    for arm in ARMS:
        if len(arms[arm]) != len(original):
            raise RuntimeError(f"arm {arm} changed tool membership")
        for tool, base in zip(arms[arm], original):
            if _skeleton(tool) != _skeleton(base):
                raise RuntimeError(f"arm {arm} changed a non-description byte of {base['function']['name']}")
    for index, cue in enumerate(cues):
        u_text = original[index]["function"]["description"]
        s_tool = arms["S"][index]
        for arm, base in (("X", original[index]), ("SX", s_tool)):
            tool = arms[arm][index]
            if not cue:
                if _dump(tool) != _dump(base):
                    raise RuntimeError(f"arm {arm} changed an uncued tool")
                continue
            expected = deepcopy(base)
            expected["function"]["description"] = base["function"]["description"] + CUE_SEPARATOR + cue
            if _dump(tool) != _dump(expected):
                raise RuntimeError(f"arm {arm} is not its base plus the exact cue bytes")
        if _dump({**arms["X"][index], "function": {**arms["X"][index]["function"], "description": u_text}}) != _dump(original[index]):
            raise RuntimeError("arm X changed more than the function description")


def _skeleton(tool: dict) -> str:
    copied = deepcopy(tool)
    for _pointer, container, key in description_slots(copied):
        container[key] = ""
    return _dump(copied)


def _dump(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=False, separators=(",", ":"))


def _with_cue(tool: dict, cue: str) -> dict:
    copied = deepcopy(tool)
    if not cue:
        return copied
    description = copied["function"]["description"]
    copied["function"]["description"] = description + CUE_SEPARATOR + cue
    return copied
