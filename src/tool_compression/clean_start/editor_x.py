"""Editor X contrast cues. Each target is qualified on the unmodified catalogue.

Editor S text is not an input. A rival has to serve one common user need, with
evidence on both sides from the original function text, parameter text, or
immutable schema. One unrelated tool does not veto a pair. A one-tool catalogue
gets no cue. Nothing here reads a provider, a key, a question, or a gold answer.
"""

from __future__ import annotations

import re

from tool_compression.adapter import description_slots

CUE_POINTER = "/function/description"
CUE_SEPARATOR = " "
BANNED = ("only this", "cannot", "can't", "exclusively", "unable to", "does not handle", "can't handle")
_STOP = {
    "a", "an", "the", "of", "to", "for", "and", "or", "in", "on", "with", "from", "by",
    "into", "over", "under", "between", "across", "based", "such", "if", "as", "at",
}
_COEF = re.compile(r"coefficient|constant term|degree", re.IGNORECASE)
_ROOTS = re.compile(r"(?i)^calculate the roots of (?:a|an) (\w+) equation\.?$")
_MEASURE = re.compile(r"(?i)\b(?:of|between)\s+two\s+(?:numbers|integers|values)\b")


def qualify_catalogue(tools: list[dict]) -> list[dict]:
    """Return one decision per tool, in catalogue order. ``tools`` is original U."""
    if len(tools) == 1:
        tool = tools[0]
        return [{
            "tool_index": 0,
            "function_name": tool["function"]["name"],
            "pointer": CUE_POINTER,
            "cue": "",
            "rival": None,
            "axis": None,
            "evidence": None,
            "rejected_rivals": [],
            "no_cue_reason": "Single-tool control. Controls receive no cue.",
            "control": True,
        }]
    names = [tool["function"]["name"] for tool in tools]
    rows = []
    for index, tool in enumerate(tools):
        rivals = []
        rejected = []
        for other, candidate in enumerate(tools):
            if other == index:
                continue
            match = _pair(tool, candidate)
            if match is None:
                rejected.append({
                    "tool_index": other,
                    "function_name": candidate["function"]["name"],
                    "reason": _reject_reason(tool, candidate),
                })
                continue
            rivals.append({"tool_index": other, "function_name": candidate["function"]["name"], **match})
        chosen, not_chosen = _closest(tool, rivals)
        if chosen is None:
            rows.append(_uncued(index, tool, rejected))
            continue
        cue = _cue(tool, tools[chosen["tool_index"]], chosen)
        problem = _cue_problem(cue, names, tool["function"]["name"], chosen["function_name"])
        if problem:
            rejected.append({
                "tool_index": chosen["tool_index"],
                "function_name": chosen["function_name"],
                "reason": problem,
            })
            rows.append(_uncued(index, tool, rejected + _as_rejected(not_chosen)))
            continue
        for item in not_chosen:
            rejected.append({
                "tool_index": item["tool_index"],
                "function_name": item["function_name"],
                "reason": "Also qualifies. The longer shared wording, then the lower original index, was kept.",
            })
        rows.append({
            "tool_index": index,
            "function_name": tool["function"]["name"],
            "pointer": CUE_POINTER,
            "cue": cue,
            "rival": {
                "tool_index": chosen["tool_index"],
                "function_name": chosen["function_name"],
            },
            "axis": chosen["axis"],
            "evidence": chosen["evidence"],
            "rejected_rivals": rejected,
            "no_cue_reason": None,
            "control": False,
        })
    return rows


def _uncued(index: int, tool: dict, rejected: list[dict]) -> dict:
    if rejected:
        reason = "No rival serves a common user need with evidence on both sides. " + rejected[0]["reason"]
    else:
        reason = "No other tool is in this catalogue."
    return {
        "tool_index": index,
        "function_name": tool["function"]["name"],
        "pointer": CUE_POINTER,
        "cue": "",
        "rival": None,
        "axis": None,
        "evidence": None,
        "rejected_rivals": rejected,
        "no_cue_reason": reason,
        "control": False,
    }


def _as_rejected(rivals: list[dict]) -> list[dict]:
    return [
        {
            "tool_index": item["tool_index"],
            "function_name": item["function_name"],
            "reason": "Also qualifies, and was not needed after the closest cue was refused.",
        }
        for item in rivals
    ]


def _pair(target: dict, rival: dict) -> dict | None:
    interface = _interface_pair(target, rival)
    if interface is not None:
        return interface
    return _parallel_pair(target, rival)


def _parallel_pair(target: dict, rival: dict) -> dict | None:
    left = target["function"]["description"]
    right = rival["function"]["description"]
    if _verb(left) != _verb(right) or not _verb(left):
        return None
    if _required(target) != _required(rival) or not _required(target):
        return None
    aligned = _align(left, right)
    if aligned is None:
        return None
    pre, mid_left, mid_right, suf = aligned
    kind = _accept(pre, mid_left, mid_right, suf)
    if not kind:
        return None
    if any(word.lower() in {"not", "no", "without", "only", "cannot"} for word in mid_left + mid_right):
        return None
    axis = {
        "measure": "common-value-of-two-numbers",
        "shared-head": "shared-head-" + suf[0].lower(),
        "parallel-object": "parallel-object",
    }[kind]
    target_excerpt = _phrase(left, mid_left)
    rival_excerpt = _phrase(right, mid_right)
    return {
        "kind": kind,
        "axis": axis,
        "pre": pre,
        "mid_left": mid_left,
        "mid_right": mid_right,
        "suf": suf,
        "target_description": left,
        "rival_description": right,
        "score": (_jaccard(left, right), len(pre) + len(suf), -0),
        "evidence": {
            "target": {
                "function_excerpt": target_excerpt,
                "function_text": left,
                "schema_required": _required_records(target),
            },
            "rival": {
                "function_excerpt": rival_excerpt,
                "function_text": right,
                "schema_required": _required_records(rival),
            },
            "shared_kind": kind,
        },
    }


def _interface_pair(target: dict, rival: dict) -> dict | None:
    left = target["function"]["description"].strip()
    right = rival["function"]["description"].strip()
    if _verb(left) != _verb(right):
        return None
    left_kind = _ROOTS.match(left)
    right_kind = _ROOTS.match(right)
    if left_kind is None or right_kind is None:
        return None
    named_target = _named_coefficients(target)
    array_target = _ordered_array(target)
    named_rival = _named_coefficients(rival)
    array_rival = _ordered_array(rival)
    if named_target and array_rival:
        target_is_named = True
        array_tool, named_tool = rival, target
    elif array_target and named_rival:
        target_is_named = False
        array_tool, named_tool = target, rival
    else:
        return None
    array = _array_parameter(array_tool)
    named = _named_parameter_notes(named_tool)
    return {
        "kind": "interface",
        "axis": "named-coefficients-versus-ordered-array",
        "target_kind": left_kind.group(1).lower(),
        "rival_kind": right_kind.group(1).lower(),
        "target_is_named": target_is_named,
        "score": (_jaccard(left, right), 0, -0),
        "evidence": {
            "target": {
                "function_excerpt": left,
                "function_text": left,
                "parameter_excerpts": named,
                "schema_required": _required_records(target),
            },
            "rival": {
                "function_excerpt": right,
                "function_text": right,
                "parameter_excerpts": [array],
                "schema_required": _required_records(rival),
                "order_support": array["description"],
            },
            "shared_kind": "roots-from-coefficients",
        },
    }


def _closest(tool: dict, rivals: list[dict]) -> tuple[dict | None, list[dict]]:
    if not rivals:
        return None, []
    def key(item):
        _jaccard, skeleton, _index = item["score"]
        # Longer shared wording is closer. Equal wording keeps the earlier tool.
        return (skeleton, -item["tool_index"])
    ordered = sorted(rivals, key=key, reverse=True)
    return ordered[0], ordered[1:]


def _cue(target: dict, rival: dict, match: dict) -> str:
    if match["kind"] == "interface":
        rival_name = rival["function"]["name"]
        kind = match["target_kind"]
        if match["target_is_named"]:
            return (
                f"Unlike {rival_name}, which takes an ordered coefficient array, "
                f"this takes named {kind} coefficients."
            )
        return (
            f"Unlike {rival_name}, which takes named {match['rival_kind']} coefficients, "
            f"this takes an ordered coefficient array."
        )
    rival_name = rival["function"]["name"]
    left = _clause(match["target_description"], match["pre"], match["mid_left"], match["suf"], match["kind"])
    # Rebuild the rival clause with the rival's own prefix and middle.
    rival_aligned = _align(match["rival_description"], match["target_description"])
    pre_r, mid_r, _mid_t, suf_r = rival_aligned
    right = _clause(match["rival_description"], pre_r, mid_r, suf_r, match["kind"])
    return f"Unlike {rival_name}, which {right}, this {left}."


def _clause(description: str, pre: list[str], mid: list[str], suf: list[str], kind: str) -> str:
    """Keep the original word order through the axis, and the shared head when it follows."""
    chosen = list(pre) + list(mid)
    if kind == "shared-head" and suf:
        chosen = chosen + [suf[0]]
    span = _phrase(description, chosen)
    parts = span.split(" ", 1)
    verb = _third(parts[0])
    return verb if len(parts) == 1 else f"{verb} {parts[1]}"


def _cue_problem(cue: str, names: list[str], target: str, rival: str) -> str | None:
    if not cue or cue != cue.strip() or "\n" in cue or not cue.endswith("."):
        return "The cue is empty or not one sentence."
    lowered = cue.lower()
    for banned in BANNED:
        if banned in lowered:
            return f"The cue would use exclusive wording {banned!r}."
    if cue.count(rival) != 1:
        return "The cue does not name exactly one rival."
    if target in cue:
        return "The cue names the target as well as the rival."
    others = [name for name in names if name not in {target, rival} and name in cue]
    if others:
        return "The cue names a third tool."
    return None


def _accept(pre, mid_left, mid_right, suf) -> str | None:
    if not (1 <= len(mid_left) <= 4 and 1 <= len(mid_right) <= 4):
        return None
    if len(pre) + len(suf) < 5:
        return None
    if suf and suf[0].lower() not in _STOP and suf[0][:1].isalpha():
        return "shared-head"
    if _MEASURE.search(" ".join(suf)):
        return "measure"
    if _content(mid_left) == 1 and _content(mid_right) == 1 and len(suf) >= 3 and len(pre) >= 2:
        return "parallel-object"
    return None


def _align(left: str, right: str):
    a, b = _words(left), _words(right)
    i = 0
    while i < len(a) and i < len(b) and a[i].lower() == b[i].lower():
        i += 1
    j = 0
    while j < len(a) - i and j < len(b) - i and a[-1 - j].lower() == b[-1 - j].lower():
        j += 1
    mid_a = a[i:len(a) - j if j else len(a)]
    mid_b = b[i:len(b) - j if j else len(b)]
    if not mid_a or not mid_b:
        return None
    return a[:i], mid_a, mid_b, a[len(a) - j:] if j else []


def _reject_reason(target: dict, rival: dict) -> str:
    left = target["function"]["description"]
    right = rival["function"]["description"]
    if _verb(left) != _verb(right):
        return (
            f"Different actions ({_words(left)[:1]} versus {_words(right)[:1]}). "
            "An unrelated tool does not veto any other pair."
        )
    if _required(target) != _required(rival):
        return (
            "Required parameter names or types differ "
            f"({_required(target)} versus {_required(rival)}). "
            "An unrelated tool does not veto any other pair."
        )
    return "The function texts do not share one short supported axis. An unrelated tool does not veto any other pair."


def _required(tool: dict) -> tuple:
    function = tool["function"]
    props = function["parameters"].get("properties") or {}
    found = []
    for name in function["parameters"].get("required") or []:
        schema = props.get(name) or {}
        kind = schema.get("type")
        if kind == "array":
            kind = "array:" + str((schema.get("items") or {}).get("type"))
        found.append((name, kind))
    return tuple(found)


def _required_records(tool: dict) -> list[dict]:
    return [{"name": name, "type": kind} for name, kind in _required(tool)]


def _named_coefficients(tool: dict) -> bool:
    function = tool["function"]
    props = function["parameters"].get("properties") or {}
    required = function["parameters"].get("required") or []
    if len(required) < 3:
        return False
    for name in required:
        schema = props.get(name) or {}
        if schema.get("type") not in {"integer", "number"}:
            return False
        if not _COEF.search(schema.get("description") or ""):
            return False
    return True


def _ordered_array(tool: dict) -> bool:
    return _array_parameter(tool) is not None


def _array_parameter(tool: dict) -> dict | None:
    function = tool["function"]
    props = function["parameters"].get("properties") or {}
    required = function["parameters"].get("required") or []
    if len(required) != 1:
        return None
    name = required[0]
    schema = props.get(name) or {}
    if schema.get("type") != "array":
        return None
    if (schema.get("items") or {}).get("type") not in {"number", "integer"}:
        return None
    description = schema.get("description") or ""
    if not re.search(r"coefficient", description, re.IGNORECASE):
        return None
    if not re.search(r"highest degree|starting from|decreasing order", description, re.IGNORECASE):
        return None
    return {"name": name, "description": description, "type": "array", "items": (schema.get("items") or {}).get("type")}


def _named_parameter_notes(tool: dict) -> list[dict]:
    function = tool["function"]
    props = function["parameters"].get("properties") or {}
    notes = []
    for name in function["parameters"].get("required") or []:
        schema = props.get(name) or {}
        notes.append({"name": name, "description": schema.get("description") or "", "type": schema.get("type")})
    return notes


def _verb(text: str) -> str:
    words = _words(text)
    if not words:
        return ""
    return _lemma(words[0])


def _lemma(word: str) -> str:
    irregular = {
        "calculates": "calculate", "calculate": "calculate", "fetches": "fetch", "fetch": "fetch",
        "retrieves": "retrieve", "retrieve": "retrieve", "gets": "get", "get": "get",
        "finds": "find", "find": "find", "estimates": "estimate", "estimate": "estimate",
        "returns": "return", "return": "return", "applies": "apply", "apply": "apply",
        "provides": "provide", "provide": "provide", "searches": "search", "search": "search",
        "converts": "convert", "convert": "convert", "locates": "locate", "locate": "locate",
    }
    lowered = word.lower()
    if lowered in irregular:
        return irregular[lowered]
    if len(lowered) > 4 and lowered.endswith("s") and not lowered.endswith("ss"):
        return lowered[:-1]
    return lowered


def _third(word: str) -> str:
    lowered = word.lower()
    if lowered.endswith("s"):
        return lowered
    if lowered.endswith("y") and len(lowered) > 2 and lowered[-2] not in "aeiou":
        return lowered[:-1] + "ies"
    if lowered.endswith(("s", "x", "z", "ch", "sh")):
        return lowered + "es"
    return lowered + "s"


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9']+", text)


def _content(words: list[str]) -> int:
    return sum(1 for word in words if word.lower() not in _STOP)


def _phrase(description: str, words: list[str]) -> str:
    if not words:
        return ""
    pattern = r"\b" + r"\b[\s(),\-]*\b".join(re.escape(word) for word in words) + r"\b"
    match = re.search(pattern, description, re.IGNORECASE)
    if match is None:
        return " ".join(words)
    phrase = match.group(0)
    end = match.end()
    if end < len(description) and description[end] == ")":
        phrase += ")"
    return phrase


def _jaccard(left: str, right: str) -> float:
    a = {word.lower() for word in _words(left) if word.lower() not in _STOP}
    b = {word.lower() for word in _words(right) if word.lower() not in _STOP}
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def parameter_texts(tool: dict) -> list[str]:
    """Own-tool parameter descriptions. Used by the ledger, not by editor S."""
    found = []
    for pointer, _container, _key in description_slots(tool):
        if pointer != CUE_POINTER:
            found.append(pointer)
    return found
