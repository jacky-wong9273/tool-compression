"""Editor S. One tool at a time. No sibling catalogue, no question, no label.

Visit every function description and parameter description. A shorter candidate
is kept only when this tool's own schema or wording proves it. The original
stays otherwise. Nothing here reads a provider, a key, or a gold answer.

Rules, in ``S_RULES_VERSION``:

- ``schema_guaranteed``: drop a parameter clause the unchanged schema states
  (pinned float suffix with ``format: float``, an enum list equal to ``enum``,
  a prose default equal to ``default``).
- ``suite_context``: when the tool's own text labels its description with
  ``Tool description:``, keep the membership sentence ``This tool belongs to
  <suite>.`` and the description, and drop the suite elaboration and the label.
- ``direct_action``: drop a leading ``This function ...`` subject frame and
  keep the verb as written.
- ``within_tool_duplicate`` and ``flag_normalization`` as before.

The official language hint is never edited. Deletions touch only their seams.
"""

from __future__ import annotations

from hashlib import sha256
import json
import re

from tool_compression.adapter import description_slots
from tool_compression.clean_start.descriptions import leading_frame, split_protected, suite_preamble

S_RULES_VERSION = "s-rules-2026-11-25"
FLOAT_SUFFIX = " This is a float type value."
KEEP_REASONS = ("already_minimal", "ambiguous_source", "no_shorter_faithful_candidate")
_STOP = {
    "a", "an", "the", "of", "to", "for", "and", "or", "in", "on", "with", "from", "by",
    "into", "over", "under", "between", "across", "at", "as", "if", "is", "are", "be",
    "this", "that", "these", "those", "it", "its", "their", "when", "which", "who",
}
_NEGATION = re.compile(r"\b(?:not|no|never|none|without|cannot|can't)\b", re.IGNORECASE)
_WHETHER = re.compile(r"\bwhether\b", re.IGNORECASE)
_INTERNAL = re.compile(r"\binternal\b", re.IGNORECASE)
_ONLY = re.compile(r"\bonly\b", re.IGNORECASE)
_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_QUOTED = re.compile(r"'[^']+'|\"[^\"]+\"")
_UNIT = re.compile(
    r"\b(?:celsius|fahrenheit|degrees?|percent(?:age)?|met(?:er|re)s?|kilomet(?:er|re)s?|"
    r"seconds?|minutes?|hours?|days?|bytes?|pixels?|miles?|feet|foot|inches?|inch|"
    r"lit(?:er|re)s?|gallons?|watts?|kilograms?|grams?|kg|km|cm|mm|mb|gb|hz|ms)\b|%|°",
    re.IGNORECASE,
)
_FLAG = re.compile(
    r"^(A flag to determine )(whether to )(.+?)(\. Default is )(true|false)(\.)$",
    re.IGNORECASE,
)
_INDICATES = re.compile(
    r"^(Indicates if )(.+?)( should be included )(in the result)(\. Default is )(true|false)(\.)$",
    re.IGNORECASE,
)
_FOR_WHICH = re.compile(r"^(?P<keep>.+?)(?P<bridge> for which to )(?P<rest>.+)\.$")
_PAREN_DEFAULT = re.compile(
    r"\s*\((?:defaults?|default)\s+(?:is|to)\s+(.+?)\)",
    re.IGNORECASE,
)
_DEFAULT_SENTENCE = re.compile(
    r"(?i)^(?P<head>default\s+value\s+is|defaults?\s+(?:is|to|:)|default\s+(?:is|to|:)|default)\s+(?P<value>.+?)\.?$"
)
_ENUM_SENTENCE = re.compile(
    r"(?i)^(?:Supported values:|Possible values are|\[Enum\]:)\s+(.+?)\.?$"
)


def context_id(tool: dict) -> str:
    raw = json.dumps(tool, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(raw.encode("utf-8")).hexdigest()


def edit_tool(tool: dict) -> tuple[dict, list[dict]]:
    """Return a copied tool and one ledger row per eligible description.

    ``tool`` is the target's complete original definition. Callers must not
    pass the rest of the catalogue.
    """
    if not isinstance(tool, dict):
        raise ValueError("editor S expected one tool object")
    original_slots = list(description_slots(tool))
    function = tool.get("function") if isinstance(tool.get("function"), dict) else {}
    function_text = function.get("description") if isinstance(function.get("description"), str) else ""
    decisions = []
    for pointer, container, key in original_slots:
        decisions.append(
            _decide_field(
                tool,
                pointer,
                container[key],
                container,
                function_text if pointer != "/function/description" else "",
            )
        )
    # A parameter may drop a clause only when the final function text still carries it.
    final_function = function_text
    for row in decisions:
        if row["pointer"] == "/function/description":
            final_function = row["final"]
    for row in decisions:
        if row["pointer"] == "/function/description" or row["final"] == row["original"]:
            continue
        for fact in row["facts"]:
            excerpt = fact.get("recovery_excerpt")
            if fact.get("recovery_pointer") == "/function/description" and excerpt and excerpt not in final_function:
                row["rejected_candidate"] = row["final"]
                row["final"] = row["original"]
                row["adopted"] = False
                row["change_class"] = None
                row["keep_reason"] = "no_shorter_faithful_candidate"
                row["keep_detail"] = (
                    f"{row['pointer']} lost the recovery excerpt in the final function description, "
                    "so the shorter parameter text was not adopted."
                )
                break
    edited = json.loads(json.dumps(tool))
    slot_index = {pointer: (container_path, key) for pointer, container_path, key in _slot_paths(edited)}
    for row in decisions:
        pointer = row["pointer"]
        container, key = _resolve_slot(edited, pointer)
        if container[key] != row["original"]:
            raise ValueError(f"editor S lost the original at {pointer}")
        container[key] = row["final"]
        slot_index[pointer] = container[key]
    return edited, decisions


def _slot_paths(tool: dict):
    return description_slots(tool)


def _resolve_slot(tool: dict, pointer: str):
    for found, container, key in description_slots(tool):
        if found == pointer:
            return container, key
    raise KeyError(pointer)


def _decide_field(tool: dict, pointer: str, original: str, schema: dict, function_text: str) -> dict:
    proposals: list[dict] = []
    conflict = _conflict(original, schema)
    proposals.extend(_schema_candidates(original, schema, pointer))
    accepted_schema = [item for item in proposals if item["ok"]]
    duplicate_source = accepted_schema[0]["text"] if accepted_schema else original
    duplicate_candidate = _duplicate_candidate(original, duplicate_source, function_text, pointer)
    if duplicate_candidate is not None:
        proposals.append(duplicate_candidate)
    if pointer == "/function/description":
        proposals.extend(_function_candidates(original))
    flagged = _flag_candidate(original, schema, function_text, pointer)
    if flagged is not None:
        proposals.append(flagged)
    indicated = _indicates_candidate(original, schema, pointer)
    if indicated is not None:
        proposals.append(indicated)

    accepted = [item for item in proposals if item["ok"] and len(item["text"]) < len(original) and item["text"] != original]
    rejected = [item for item in proposals if item not in accepted]
    if accepted:
        accepted.sort(key=lambda item: (len(item["text"]), -_shared_prefix(original, item["text"])))
        chosen = accepted[0]
        return _row(
            tool, pointer, original, chosen["text"], chosen["text"], True, None,
            chosen["detail"], chosen["facts"], chosen["change_class"], conflict, True,
            [item["text"] for item in rejected],
        )
    if conflict and not accepted:
        reason = "ambiguous_source"
        detail = conflict
    elif rejected:
        reason = "no_shorter_faithful_candidate"
        detail = rejected[0]["detail"]
    else:
        reason = "already_minimal"
        detail = f"{pointer} has no schema-guaranteed clause, repeated clause, or frame that a shorter faithful candidate can drop."
    proposed = rejected[0]["text"] if rejected else original
    return _row(
        tool, pointer, original, proposed, original, False, reason, detail,
        [{"excerpt": original, "span": [0, len(original)], "decision": "KEEP", "after": original, "note": detail}],
        None, conflict, bool(rejected or conflict), [item["text"] for item in rejected],
    )


def _row(tool, pointer, original, candidate, final, adopted, reason, detail, facts, change_class, conflict, nontrivial, rejected_texts):
    if reason is not None and reason not in KEEP_REASONS:
        raise ValueError(reason)
    _check_facts(original, final, facts, adopted)
    return {
        "rules_version": S_RULES_VERSION,
        "context_id": context_id(tool),
        "function_name": tool.get("function", {}).get("name"),
        "pointer": pointer,
        "original": original,
        "candidate": candidate,
        "final": final,
        "adopted": adopted,
        "keep_reason": reason,
        "keep_detail": detail,
        "facts": facts,
        "change_class": change_class,
        "conflict": conflict,
        "nontrivial": nontrivial or adopted,
        "rejected_candidates": rejected_texts,
        "meaningful": bool(adopted and change_class),
        "cosmetic": False,
    }


def _check_facts(original: str, final: str, facts: list[dict], adopted: bool) -> None:
    if not facts:
        raise ValueError("editor S field has no fact")
    for fact in facts:
        start, end = fact["span"]
        if original[start:end] != fact["excerpt"]:
            raise ValueError("editor S fact span does not match the source")
        if fact.get("after") and fact["after"] not in final and not fact.get("recovery_pointer") and fact.get("decision") != "SCHEMA":
            if adopted and fact.get("decision") == "KEEP":
                raise ValueError("editor S kept fact is missing from the final text")
    if adopted:
        for claim in _stems(final):
            if claim not in _stems(original) and claim not in _ALLOWED_NEW:
                raise ValueError(f"editor S final claim {claim} is not in the source")


_ALLOWED_NEW = {"include", "whether"}


def _schema_candidates(original: str, schema: dict, pointer: str) -> list[dict]:
    proposals = []
    removals = []
    if original.endswith(FLOAT_SUFFIX) and schema.get("format") == "float" and schema.get("type") == "number":
        start = len(original) - len(FLOAT_SUFFIX)
        removals.append({
            "span": [start, len(original)],
            "excerpt": original[start:],
            "decision": "SCHEMA",
            "schema_path": _sibling_path(pointer, "format"),
            "schema_equals": "float",
            "note": "The float sentence is the pinned conversion suffix. format float and type number stay on the schema.",
        })
    enum_removal = _enum_removal(original, schema, pointer)
    if enum_removal is not None:
        removals.append(enum_removal)
    for item in _default_facts(original, schema, pointer):
        if item.get("ok"):
            removals.append(item["fact"])
        else:
            proposals.append({
                "ok": False,
                "text": item["text"],
                "facts": [],
                "change_class": None,
                "detail": item["detail"],
            })
    if not removals:
        return proposals
    if _overlap(removals):
        proposals.append({
            "ok": False,
            "text": original,
            "facts": [],
            "change_class": None,
            "detail": f"{pointer} has overlapping schema clauses, so none was removed.",
        })
        return proposals
    text = _delete_spans(original, [item["span"] for item in removals])
    facts = [_kept_between(original, text, removals), *removals]
    ok, detail = _faithful(original, text, removals)
    proposals.append({
        "ok": ok,
        "text": text,
        "facts": facts,
        "change_class": "schema_guaranteed" if ok else None,
        "detail": detail if not ok else f"{pointer} drops prose already guaranteed by the unchanged schema.",
    })
    return proposals


def _enum_removal(original: str, schema: dict, pointer: str):
    enum = schema.get("enum")
    if not isinstance(enum, list) or not enum:
        return None
    found = None
    for sentence, start, end in _sentences(original):
        match = _ENUM_SENTENCE.match(sentence.strip())
        if match is None:
            continue
        if re.search(r"\b(?:means|meaning|gives|provides)\b", sentence, re.IGNORECASE):
            continue
        quoted = [item[1:-1] for item in _QUOTED.findall(sentence)]
        if quoted and set(quoted) == {str(item) for item in enum}:
            found = (sentence.strip().rstrip("."), start, end)
    if found is None:
        return None
    sentence, start, end = found
    at = original.find(sentence, max(0, start - 1))
    if at < 0:
        return None
    stop = at + len(sentence)
    if stop < len(original) and original[stop] == ".":
        stop += 1
        sentence = original[at:stop]
    if at > 0 and original[at - 1] == " ":
        at -= 1
        sentence = original[at:stop]
    return {
        "span": [at, stop],
        "excerpt": sentence,
        "decision": "SCHEMA",
        "schema_path": _sibling_path(pointer, "enum"),
        "schema_equals": list(enum),
        "note": "The quoted list matches the schema enum and adds no definition.",
    }


def _default_facts(original: str, schema: dict, pointer: str) -> list[dict]:
    found = []
    for match in _PAREN_DEFAULT.finditer(original):
        found.append((match.group(0), match.group(1), match.start(), match.end()))
    for sentence, start, end in _sentences(original):
        match = _DEFAULT_SENTENCE.match(sentence.strip())
        if match is None:
            continue
        excerpt = sentence.strip()
        at = original.find(excerpt, start)
        if at < 0:
            continue
        found.append((excerpt, match.group("value"), at, at + len(excerpt)))
    results = []
    for excerpt, raw_value, start, _end in found:
        if "default" not in schema:
            results.append({
                "ok": False,
                "text": _delete_spans(original, [[start, start + len(excerpt)]]),
                "detail": (
                    f"{pointer} states {excerpt!r}, and the schema has no default to point at, "
                    "so the prose default stays."
                ),
            })
            continue
        parsed = _parse_default(raw_value, schema["default"])
        if parsed is None or parsed != schema["default"]:
            results.append({
                "ok": False,
                "text": _delete_spans(original, [[start, start + len(excerpt)]]),
                "detail": (
                    f"{pointer} states {excerpt!r}, which is not the schema default {schema['default']!r}. "
                    "The prose stays."
                ),
            })
            continue
        results.append({
            "ok": True,
            "fact": {
                "span": [start, start + len(excerpt)],
                "excerpt": excerpt,
                "decision": "SCHEMA",
                "schema_path": _sibling_path(pointer, "default"),
                "schema_equals": schema["default"],
                "note": "The prose default equals the unchanged schema default.",
            },
        })
    return results


def _sentences(text: str):
    start = 0
    for match in re.finditer(r"[.]", text):
        end = match.end()
        yield text[start:end], start, end
        start = end
    if start < len(text):
        yield text[start:], start, len(text)


def _parse_default(raw: str, schema_default):
    text = raw.strip().rstrip(".").strip()
    text = re.sub(r"\s+if\s+not\s+(?:specified|provided|given)\s*$", "", text, flags=re.IGNORECASE).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        text = text[1:-1]
    if isinstance(schema_default, bool):
        if text.lower() == "true":
            return True
        if text.lower() == "false":
            return False
        return None
    if isinstance(schema_default, int):
        if re.fullmatch(r"-?\d+", text):
            return int(text)
        return None
    if isinstance(schema_default, float):
        if re.fullmatch(r"-?\d+(?:\.\d+)?", text) and float(text) == schema_default:
            return schema_default
        return None
    if isinstance(schema_default, str):
        return text if text == schema_default else None
    return None


def _duplicate_candidate(original: str, working: str, function_text: str, pointer: str) -> dict | None:
    if not function_text or pointer == "/function/description":
        return None
    match = _FOR_WHICH.search(working)
    if match is None:
        return None
    rest = match.group("rest")
    if not set(_stems(rest)) <= set(_stems(function_text)):
        return {
            "ok": False,
            "text": working,
            "facts": [],
            "change_class": None,
            "detail": f"{pointer} repeats part of the function description, but not every word, so the clause stays.",
        }
    recovery = _recovery_excerpt(rest, function_text)
    if recovery is None:
        return {
            "ok": False,
            "text": working,
            "facts": [],
            "change_class": None,
            "detail": f"{pointer} repeats part of the function description, but not every word, so the clause stays.",
        }
    if _NUMBER.search(rest) or _QUOTED.search(rest) or _NEGATION.search(rest):
        return {
            "ok": False,
            "text": working,
            "facts": [],
            "change_class": None,
            "detail": f"{pointer} carries a literal, negation, or quote in the repeated clause, so the clause stays.",
        }
    bridge = match.group("bridge")
    rest_span_text = bridge + match.group("rest")
    start = original.find(rest_span_text)
    if start < 0:
        return None
    candidate = original[:start].rstrip()
    if original.endswith(".") and not candidate.endswith("."):
        candidate += "."
    fact = {
        "span": [start, start + len(rest_span_text)],
        "excerpt": original[start:start + len(rest_span_text)],
        "decision": "DUPLICATE",
        "recovery_pointer": "/function/description",
        "recovery_excerpt": recovery,
        "note": "The purpose clause repeats the function description of this same tool.",
    }
    kept = {
        "span": [0, start],
        "excerpt": original[:start],
        "decision": "KEEP",
        "after": candidate,
        "note": "The parameter's own name stays.",
    }
    ok, detail = _faithful(original, candidate, [fact])
    return {
        "ok": ok,
        "text": candidate,
        "facts": [kept, fact],
        "change_class": "within_tool_duplicate" if ok else None,
        "detail": detail if not ok else f"{pointer} drops a purpose clause already stated on this tool's function description.",
    }


def _recovery_excerpt(rest: str, function_text: str) -> str | None:
    if not function_text:
        return None
    if rest.lower() in function_text.lower():
        at = function_text.lower().find(rest.lower())
        return function_text[at:at + len(rest)]
    words = rest.split()
    for index in range(1, len(words)):
        tail = " ".join(words[index:])
        if len(tail) > 8 and tail.lower() in function_text.lower():
            at = function_text.lower().find(tail.lower())
            return function_text[at:at + len(tail)]
    return None


def _function_candidates(original: str) -> list[dict]:
    """Suite-context and direct-action candidates, alone and together.

    Every candidate is the original with spans replaced. Nothing outside the
    protected official hint is added except the period that already closed the
    membership sentence and the capital on the kept verb.
    """
    head, _suffix = split_protected(original)
    suite = suite_preamble(head)
    frame = leading_frame(head, suite["core_start"] if suite else 0)
    options = []
    if suite is not None:
        options.append(("suite_context", suite, None))
    if frame is not None:
        options.append(("direct_action", None, frame))
    if suite is not None and frame is not None:
        options.append(("suite_context+direct_action", suite, frame))
    proposals = []
    for change_class, use_suite, use_frame in options:
        edits = []
        if use_suite is not None:
            membership = use_suite["membership"]
            elaboration = use_suite["elaboration"]
            label = use_suite["label"]
            edits.append({
                "span": elaboration,
                "replacement": ".",
                "decision": "SUITE_CONTEXT",
                "note": (
                    "The elaboration describes the suite this tool belongs to, not this tool. "
                    "The membership sentence stays, so the suite is still named."
                ),
            })
            edits.append({
                "span": label,
                "replacement": " ",
                "decision": "FRAME",
                "note": "The label only marks where the tool's own description starts.",
            })
            kept_membership = {
                "span": membership,
                "excerpt": original[membership[0]:membership[1]],
                "decision": "KEEP",
                "after": original[membership[0]:membership[1]],
                "note": "Suite membership stays.",
            }
        if use_frame is not None:
            start, end = use_frame["frame"]
            verb = use_frame["verb"]
            edits.append({
                "span": [start, end + 1],
                "replacement": verb[:1].upper(),
                "decision": "FRAME",
                "note": "The subject frame is not a separate claim. The verb stays as written.",
            })
        candidate = _replace_spans(original, edits)
        facts = []
        if use_suite is not None:
            facts.append(kept_membership)
        for edit in edits:
            start, end = edit["span"]
            facts.append({
                "span": [start, end],
                "excerpt": original[start:end],
                "decision": edit["decision"],
                "after": "",
                "replacement": edit["replacement"],
                "note": edit["note"],
            })
        removed = [item for item in facts if item["decision"] != "KEEP"]
        ok, detail = _faithful(original, candidate, removed)
        proposals.append({
            "ok": ok,
            "text": candidate,
            "facts": facts,
            "change_class": change_class if ok else None,
            "detail": detail if not ok else f"The function description keeps its own action text ({change_class}).",
        })
    return proposals


def _replace_spans(text: str, edits: list[dict]) -> str:
    out = []
    cursor = 0
    for edit in sorted(edits, key=lambda item: item["span"][0]):
        start, end = edit["span"]
        if start < cursor:
            raise ValueError("editor S replacement spans overlap")
        out.append(text[cursor:start])
        out.append(edit["replacement"])
        cursor = end
    out.append(text[cursor:])
    return "".join(out)


def _flag_candidate(original: str, schema: dict, function_text: str, pointer: str) -> dict | None:
    match = _FLAG.match(original)
    if match is None or schema.get("type") != "boolean":
        return None
    body = match.group(3)
    flag = match.group(5).lower()
    expected = flag == "true"
    if schema.get("default") is not expected:
        return {
            "ok": False,
            "text": "Whether to " + body,
            "facts": [],
            "change_class": None,
            "detail": f"{pointer} says the default is {flag}, which is not the schema default {schema.get('default')!r}.",
        }
    duplicate = None
    noun_match = re.search(r"\sof\s+(\w+)$", body)
    if noun_match and function_text and re.search(rf"\b{re.escape(noun_match.group(1))}\b", function_text, re.IGNORECASE):
        duplicate = noun_match.group(1)
        body = body[:noun_match.start()]
    candidate = "Whether to " + body
    # Partition the original.
    frame = match.group(1)
    whether = match.group(2) + match.group(3)
    facts = [{
        "span": [0, len(frame)],
        "excerpt": frame,
        "decision": "FRAME",
        "after": "",
        "note": "The flag frame is the whether-clause, not a separate action.",
    }]
    keep_excerpt = "whether to " + body
    keep_at = original.lower().find(keep_excerpt.lower())
    facts.append({
        "span": [keep_at, keep_at + len(keep_excerpt)],
        "excerpt": original[keep_at:keep_at + len(keep_excerpt)],
        "decision": "KEEP",
        "after": candidate,
        "note": "Whether, the verb, and the qualifiers stay. The flag is not turned into an action.",
    })
    if duplicate:
        dup_text = " of " + duplicate
        dup_at = original.lower().rfind(dup_text.lower())
        facts.append({
            "span": [dup_at, dup_at + len(dup_text)],
            "excerpt": original[dup_at:dup_at + len(dup_text)],
            "decision": "DUPLICATE",
            "recovery_pointer": "/function/description",
            "recovery_excerpt": duplicate,
            "note": "The tool object is already in this tool's function description.",
        })
    default_text = match.group(4) + match.group(5) + match.group(6)
    default_at = original.rfind(default_text)
    facts.append({
        "span": [default_at, default_at + len(default_text)],
        "excerpt": default_text,
        "decision": "SCHEMA",
        "schema_path": _sibling_path(pointer, "default"),
        "schema_equals": schema.get("default"),
        "note": "The prose default equals the unchanged schema default.",
    })
    ok, detail = _faithful(original, candidate, [item for item in facts if item["decision"] != "KEEP"])
    if "whether" not in candidate.lower():
        ok = False
    return {
        "ok": ok,
        "text": candidate,
        "facts": facts,
        "change_class": "flag_normalization" if ok else None,
        "detail": detail if not ok else f"{pointer} keeps the whether-clause and points the default at the schema.",
    }


def _indicates_candidate(original: str, schema: dict, pointer: str) -> dict | None:
    match = _INDICATES.match(original)
    if match is None or schema.get("type") != "boolean":
        return None
    flag = match.group(6).lower() == "true"
    if schema.get("default") is not flag:
        return {
            "ok": False,
            "text": original,
            "facts": [],
            "change_class": None,
            "detail": f"{pointer} default prose does not equal the schema default.",
        }
    obj = match.group(2)
    candidate = f"Whether to include {obj} in the result."
    facts = [
        {"span": [0, len(match.group(1))], "excerpt": match.group(1), "decision": "FRAME", "after": "Whether to ", "note": "Indicates-if is the whether-clause."},
        {"span": [len(match.group(1)), len(match.group(1)) + len(obj)], "excerpt": obj, "decision": "KEEP", "after": obj, "note": "The included object stays."},
        {"span": [original.lower().find(" in the result"), original.lower().find(" in the result") + len(" in the result")], "excerpt": " in the result", "decision": "KEEP", "after": " in the result.", "note": "The result location stays."},
    ]
    default_text = match.group(5) + match.group(6) + match.group(7)
    default_at = original.rfind(default_text)
    facts.append({
        "span": [default_at, default_at + len(default_text)],
        "excerpt": default_text,
        "decision": "SCHEMA",
        "schema_path": _sibling_path(pointer, "default"),
        "schema_equals": schema.get("default"),
        "note": "The prose default equals the unchanged schema default.",
    })
    ok, detail = _faithful(original, candidate, [item for item in facts if item["decision"] == "SCHEMA"])
    return {
        "ok": ok and "whether" in candidate.lower(),
        "text": candidate,
        "facts": facts,
        "change_class": "flag_normalization" if ok else None,
        "detail": detail if not ok else f"{pointer} stays a whether-clause and points the default at the schema.",
    }


def _words_only(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9]+", text.lower())


def _faithful(original: str, candidate: str, removals: list[dict]) -> tuple[bool, str]:
    if not candidate or candidate == original or len(candidate) >= len(original):
        return False, "The candidate is not shorter."
    if _words_only(original) == _words_only(candidate):
        return False, "The candidate changes only punctuation or casing."
    if _WHETHER.search(original) and not _WHETHER.search(candidate):
        return False, "The candidate drops whether and would turn a flag into an action."
    if _INTERNAL.search(original) and not _INTERNAL.search(candidate):
        return False, "The candidate drops internal."
    if _NEGATION.search(original) and not _NEGATION.search(candidate):
        return False, "The candidate drops a negation."
    if _ONLY.search(original) and not _ONLY.search(candidate):
        return False, "The candidate drops only."
    removed_text = " ".join(item.get("excerpt", "") for item in removals)
    for number in _NUMBER.findall(original):
        if number not in candidate and number not in removed_text:
            return False, f"The candidate drops the literal {number}."
    for quoted in _QUOTED.findall(original):
        if quoted not in candidate and quoted not in removed_text:
            return False, f"The candidate drops the literal {quoted}."
    for unit in _UNIT.findall(original):
        if unit.lower() not in candidate.lower() and unit.lower() not in removed_text.lower():
            return False, f"The candidate drops the unit {unit}."
    original_stems = set(_stems(original))
    for stem in _stems(candidate):
        if stem not in original_stems and stem not in _ALLOWED_NEW:
            return False, f"The candidate adds {stem}."
    return True, ""


def _conflict(original: str, schema: dict) -> str | None:
    if schema.get("type") == "object" and re.search(r"\bdictionary\b", original, re.IGNORECASE):
        return "Prose says dictionary and the schema type is object. The word is left as written."
    return None


def _delete_spans(text: str, spans: list[list[int]]) -> str:
    """Delete spans and tidy whitespace only where a deletion joined two pieces."""
    out = ""
    cursor = 0
    for start, end in sorted(spans):
        out = _join(out, text[cursor:start])
        cursor = end
    out = _join(out, text[cursor:])
    if text == text.lstrip():
        out = out.lstrip()
    if text == text.rstrip():
        out = out.rstrip()
    return out


def _join(left: str, right: str) -> str:
    if not left:
        return right
    if not right:
        return left
    if right[0] in ".,;:" and left[-1].isspace():
        left = left.rstrip()
    elif left[-1].isspace() and right[0].isspace():
        right = right.lstrip()
    return left + right


def _overlap(removals: list[dict]) -> bool:
    spans = sorted(item["span"] for item in removals)
    for (start, end), (nxt, stop) in zip(spans, spans[1:]):
        if nxt < end:
            return True
    return False


def _kept_between(original: str, final: str, removals: list[dict]) -> dict:
    return {
        "span": [0, len(original)],
        "excerpt": original,
        "decision": "KEEP",
        "after": final,
        "note": "Source text that is not in a removed schema clause remains, including this whole-string trace.",
        "removed_spans": [item["span"] for item in removals],
    }


def _shared_prefix(left: str, right: str) -> int:
    n = 0
    for a, b in zip(left, right):
        if a != b:
            break
        n += 1
    return n


def _sibling_path(pointer: str, key: str) -> str:
    if pointer.endswith("/description"):
        return pointer[: -len("description")] + key
    return pointer + "/" + key


def _stems(text: str) -> list[str]:
    found = []
    for raw in re.findall(r"[A-Za-z0-9']+", text):
        word = raw.lower()
        if word in _STOP or word.isdigit():
            continue
        if word.endswith("ies") and len(word) > 4:
            word = word[:-3] + "y"
        elif word.endswith("es") and len(word) > 4 and not word.endswith("ss"):
            word = word[:-2]
        elif word.endswith("s") and len(word) > 3 and not word.endswith("ss"):
            word = word[:-1]
        found.append(word)
    return found
