"""Render U, S, X, and SX for one converted tool catalogue.

U is the unmodified model-facing catalogue. S edits one tool at a time, in
request order. X qualifies rivals on U, with S hidden. SX starts from S and
appends the X cue bytes. Questions are not arguments.

``presented`` lists catalogue lengths already sent in this conversation (the
initial tools before held-out tools arrive). Every arm keeps the bytes of tools
already sent; only appended tools are new.
"""

from __future__ import annotations

from copy import deepcopy
import json

from tool_compression.adapter import description_slots
from tool_compression.clean_start.editor_s import S_RULES_VERSION, edit_catalogue
from tool_compression.clean_start.editor_x import X_RULES_VERSION, qualify_presented
from tool_compression.clean_start.pin import ARMS

CUE_SEPARATOR = " "
CUE_POINTER = "/function/description"


def render_tools(tools: list[dict], presented: tuple[int, ...] = ()) -> dict:
    if not isinstance(tools, list):
        raise ValueError("render_tools expected a tool list")
    presented = tuple(sorted({n for n in presented if 0 < n < len(tools)}))
    original = deepcopy(tools)
    edited_s, s_rows = edit_catalogue(deepcopy(original))
    s_changes = []
    for rows in s_rows:
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
    decisions = qualify_presented(deepcopy(original), presented)
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
    verify_cue_phrases(rendered, decisions)
    if presented:
        bound = presented[-1]
        earlier = render_tools(deepcopy(original[:bound]), presented[:-1])["arms"]
        for arm in ARMS:
            if _dump(rendered[arm][:bound]) != _dump(earlier[arm]):
                raise RuntimeError(f"arm {arm} changed a tool that was already sent")
    return {
        "arms": rendered,
        "rules": {"S": S_RULES_VERSION, "X": X_RULES_VERSION},
        "presented": list(presented),
        "changes": s_changes + x_changes,
        "x_decisions": [
            {
                "function": row.get("function_name"),
                "cue": row.get("cue") or "",
                "rival": (row.get("rival") or {}).get("function_name"),
                "rival_index": (row.get("rival") or {}).get("tool_index"),
                "rival_phrase": ((row.get("evidence") or {}).get("rival") or {}).get("cue_phrase"),
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


def verify_cue_phrases(arms: dict, decisions: list[dict]) -> None:
    """Fail closed unless each text cue quotes words its rival still says in U and in S.

    SX appends the X cue to S text, so the rival's phrase has to survive S for
    the SX request to stay coherent.
    """
    for row in decisions:
        phrase = ((row.get("evidence") or {}).get("rival") or {}).get("cue_phrase")
        if not row.get("cue") or not phrase:
            continue
        index = row["rival"]["tool_index"]
        for arm in ("U", "S"):
            if phrase not in arms[arm][index]["function"]["description"]:
                raise RuntimeError(f"cue phrase {phrase!r} is not in the {arm} text of its rival")


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
