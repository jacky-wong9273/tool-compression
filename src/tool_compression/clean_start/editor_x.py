"""Editor X contrast cues. Each target is qualified on the unmodified catalogue.

Editor S text is not an input. Every tool is read through the same structural
parse of its original text (``descriptions.action_sentence``): the official hint,
a labelled suite preamble, and a leading ``This function`` frame are set aside, so
shared suite boilerplate never enters the comparison.

A rival qualifies for a target when both action sentences use the same verb and
differ in one short window (at most four words on each side, at least one content
word each, no negation), and the wording they share is at least as long as that
window and carries a content word beyond the verb. That is evidence on both sides
that the two tools serve one user need and differ on one named axis. When the required parameters differ in shape (one numeric
array against two or more numeric scalars) the axis is the interface, read from
the immutable schema. One unrelated tool never vetoes a pair. A one-tool
catalogue gets no cue. Nothing here reads a provider, a key, a question, or a
gold answer.

The cue is one positive sentence naming one rival:
``For <rival's own differing phrase>, use <rival>.`` It says where the rival
fits and does not say the target cannot do it. A text cue is dropped, and the
next rival tried, when the rival's name already spells every content word of
its differing window: the name is in the request, so such a cue says nothing new.

A pair is also refused when the target's own text claims the object the rival's
phrase names: the target's differing words end in ``or``/``and`` joined to the
shared wording (``Remove a file or directory`` against ``Remove a directory ...``).
A cue there would send a use the target documents to the rival.

The rival's phrase starts at its determiner. When the differing words follow
``of`` or ``on`` with no determiner, the phrase keeps the head noun that the
preposition belongs to (``the return on equity (ROE)``, not ``equity (ROE)``).

Cues are decided on the catalogue the model has been shown. ``render_tools``
passes the presented prefixes, so a tool already sent keeps its cue when
held-out tools are appended later.
"""

from __future__ import annotations

import re

from tool_compression.clean_start.descriptions import action_sentence

X_RULES_VERSION = "x-rules-2026-11-25.3"
CUE_POINTER = "/function/description"
CUE_SEPARATOR = " "
BANNED = ("only this", "cannot", "can't", "exclusively", "unable to", "does not handle", "can't handle")
MAX_WINDOW_WORDS = 4
MAX_SPAN_WORDS = 6
MIN_SHARED_CONTENT_WORDS = 2
_STOP = {
    "a", "an", "the", "of", "to", "for", "and", "or", "in", "on", "with", "from", "by",
    "into", "over", "under", "between", "across", "based", "such", "if", "as", "at",
    "its", "their", "this", "that", "these", "those", "it", "is", "are", "be", "any",
}
_PHRASE_BREAK = _STOP | {
    "given", "using", "including", "via", "per", "within", "during", "about", "like", "than",
    "through", "after", "before", "against", "among", "around", "toward", "towards", "upon",
    "versus", "handling", "regarding", "detailing", "where", "which", "who", "whose",
}
_DETERMINERS = {"a", "an", "the"}
_JOINERS = {" ", "-", " (", ") "}
_NOT_A_VERB = {"a", "an", "the", "this", "that", "these", "those", "it", "its"}
_NEGATION = {"not", "no", "never", "without", "only", "cannot", "except"}
_NUMERIC = {"integer", "number"}
_COORDINATORS = {"or", "and"}
_HEAD_PREPOSITIONS = {"of", "on"}


def qualify_catalogue(tools: list[dict]) -> list[dict]:
    """Return one decision per tool, in catalogue order. ``tools`` is original U."""
    if len(tools) == 1:
        tool = tools[0]
        return [{
            "rules_version": X_RULES_VERSION,
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
            match, reason = _pair(tool, candidate)
            if match is None:
                rejected.append({
                    "tool_index": other,
                    "function_name": candidate["function"]["name"],
                    "reason": reason,
                })
                continue
            rivals.append({"tool_index": other, "function_name": candidate["function"]["name"], **match})
        ordered = sorted(rivals, key=_closeness)
        chosen = None
        for position, item in enumerate(ordered):
            cue = _cue(tools[item["tool_index"]], item)
            problem = _redundant_with_name(item) or _cue_problem(
                cue, names, tool["function"]["name"], item["function_name"]
            )
            if problem:
                rejected.append({
                    "tool_index": item["tool_index"],
                    "function_name": item["function_name"],
                    "reason": problem,
                })
                continue
            chosen = (item, cue)
            for later in ordered[position + 1:]:
                rejected.append({
                    "tool_index": later["tool_index"],
                    "function_name": later["function_name"],
                    "reason": (
                        "Also qualifies. A schema interface axis, then more shared words, "
                        "then the lower original index, was kept."
                    ),
                })
            break
        if chosen is None:
            rows.append(_uncued(index, tool, rejected))
            continue
        item, cue = chosen
        rows.append({
            "rules_version": X_RULES_VERSION,
            "tool_index": index,
            "function_name": tool["function"]["name"],
            "pointer": CUE_POINTER,
            "cue": cue,
            "rival": {
                "tool_index": item["tool_index"],
                "function_name": item["function_name"],
            },
            "axis": item["axis"],
            "evidence": item["evidence"],
            "rejected_rivals": sorted(rejected, key=lambda row: row["tool_index"]),
            "no_cue_reason": None,
            "control": False,
        })
    return rows


def qualify_presented(tools: list[dict], presented: tuple[int, ...] = ()) -> list[dict]:
    """Decisions where each tool is qualified on the first presented prefix that holds it.

    ``presented`` lists catalogue lengths the model has already been sent, in
    any order. Tools past the last one are qualified on the whole catalogue.
    """
    rows = qualify_catalogue(tools)
    for bound in sorted({n for n in presented if 0 < n < len(tools)}, reverse=True):
        rows[:bound] = qualify_catalogue(tools[:bound])
    return rows


def _closeness(item: dict) -> tuple:
    return (0 if item["kind"] == "interface" else 1, -item["shared_words"], item["tool_index"])


def _uncued(index: int, tool: dict, rejected: list[dict]) -> dict:
    rejected = sorted(rejected, key=lambda row: row["tool_index"])
    if rejected:
        reason = "No rival qualifies. Closest refusal: " + rejected[0]["reason"]
    else:
        reason = "No other tool is in this catalogue."
    return {
        "rules_version": X_RULES_VERSION,
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


def _pair(target: dict, rival: dict) -> tuple[dict | None, str]:
    target_text, _ = action_sentence(target["function"].get("description") or "")
    rival_text, _ = action_sentence(rival["function"].get("description") or "")
    target_words = _words(target_text)
    rival_words = _words(rival_text)
    if not target_words or not rival_words:
        return None, "One side has no action text."
    first_t, first_r = target_words[0][0].lower(), rival_words[0][0].lower()
    if first_t in _NOT_A_VERB or first_r in _NOT_A_VERB:
        return None, "One action text does not open with a verb."
    if _lemma(first_t) != _lemma(first_r):
        return None, f"Different actions ({target_words[0][0]} versus {rival_words[0][0]})."
    shared = _shared_content(target_words, rival_words)
    window = _window(target_words, rival_words)
    shape_t, shape_r = _shape(target), _shape(rival)
    interface = {shape_t, shape_r} == {"array", "scalars"}
    if window is None and not interface:
        return None, "The action texts are identical and the interfaces do not differ in shape."
    if window is not None:
        prefix, mid_t, mid_r, suffix = window
        problem = (
            _window_problem(mid_t, mid_r)
            or _context_problem(target_words, prefix, suffix, mid_t, mid_r)
            or _scope_problem(mid_t, suffix)
        )
        if problem:
            return None, problem
        shared_words = prefix + suffix
    else:
        mid_t = mid_r = []
        shared_words = len(target_words)
    evidence = {
        "target": {
            "action_text": target_text,
            "differing_words": [word for word, _span in mid_t],
            "schema_required": _required_records(target),
        },
        "rival": {
            "action_text": rival_text,
            "differing_words": [word for word, _span in mid_r],
            "schema_required": _required_records(rival),
        },
        "shared_content_ratio": round(shared, 4),
    }
    if interface:
        evidence["target"]["interface"] = shape_t
        evidence["rival"]["interface"] = shape_r
        return {
            "kind": "interface",
            "axis": "interface:numeric-array-versus-numeric-scalars",
            "shared_words": shared_words,
            "rival_shape": shape_r,
            "rival_parameters": [name for name, _kind in _required(rival)],
            "evidence": evidence,
        }, ""
    span = _rival_span(rival_text, rival_words, prefix, mid_r)
    if span is None:
        return None, "The rival's differing phrase is not one complete short noun phrase."
    evidence["rival"]["cue_phrase"] = span
    return {
        "kind": "text",
        "axis": "text:" + " ".join(word.lower() for word, _span in mid_t) + "|" + " ".join(word.lower() for word, _span in mid_r),
        "shared_words": shared_words,
        "rival_phrase": span,
        "evidence": evidence,
    }, ""


def _window(left: list, right: list):
    a = [word.lower() for word, _span in left]
    b = [word.lower() for word, _span in right]
    i = 0
    while i < len(a) and i < len(b) and a[i] == b[i]:
        i += 1
    j = 0
    while j < len(a) - i and j < len(b) - i and a[-1 - j] == b[-1 - j]:
        j += 1
    mid_a = left[i:len(left) - j]
    mid_b = right[i:len(right) - j]
    if not mid_a and not mid_b:
        return None
    return i, mid_a, mid_b, j


def _window_problem(mid_t: list, mid_r: list) -> str | None:
    if not (1 <= len(mid_t) <= MAX_WINDOW_WORDS and 1 <= len(mid_r) <= MAX_WINDOW_WORDS):
        return f"The differing wording is not one window of one to {MAX_WINDOW_WORDS} words on each side."
    words_t = [word.lower() for word, _span in mid_t]
    words_r = [word.lower() for word, _span in mid_r]
    if not any(word not in _STOP for word in words_t) or not any(word not in _STOP for word in words_r):
        return "The differing window has no content word on one side."
    if _NEGATION & (set(words_t) | set(words_r)):
        return "The differing window carries a negation or only."
    return None


def _context_problem(words: list, prefix: int, suffix: int, mid_t: list, mid_r: list) -> str | None:
    """The shared wording has to outweigh the difference and say more than the verb."""
    shared = [word.lower() for word, _span in words[:prefix]]
    if suffix:
        shared += [word.lower() for word, _span in words[len(words) - suffix:]]
    if len(shared) < max(len(mid_t), len(mid_r)):
        return "The shared wording is shorter than the differing window."
    if sum(1 for word in shared if word not in _STOP) < MIN_SHARED_CONTENT_WORDS:
        return "The shared wording has no content word beyond the verb."
    return None


def _scope_problem(mid_t: list, suffix: int) -> str | None:
    """The target's own text must not claim what the rival's phrase names."""
    words_t = [word.lower() for word, _span in mid_t]
    if suffix and words_t and words_t[-1] in _COORDINATORS:
        return (
            "The target's differing words end in a coordinator joined to the shared wording, so the "
            "target's own text claims the object the rival's phrase names."
        )
    return None


def _rival_span(text: str, words: list, start: int, mid: list) -> str | None:
    """The rival's own phrase for the axis, copied verbatim.

    Determiner, the differing words, and the shared words that finish the noun
    phrase. A bare noun after ``of``/``on`` keeps the head noun and determiner
    before the preposition. A trailing function word or participle is trimmed.
    A phrase that would need more than ``MAX_SPAN_WORDS`` words is refused, not cut.
    """
    lowered = [word.lower() for word, _span in words]
    end = start + len(mid) - 1
    first = start
    for back in range(start - 1, max(0, start - 3), -1):
        if back == 0:
            break
        if lowered[back] in _DETERMINERS:
            first = back
            break
    if (
        first == start
        and start >= 3
        and lowered[start - 1] in _HEAD_PREPOSITIONS
        and lowered[start - 2] not in _STOP
    ):
        first = start - 2
        if first - 1 >= 1 and lowered[first - 1] in _DETERMINERS:
            first -= 1
    def trailing(index: int) -> bool:
        if lowered[index] in _PHRASE_BREAK:
            return True
        return index > first and _participle(lowered[index]) and lowered[index - 1] not in _STOP

    last = end
    if not trailing(last):
        while last + 1 < len(words):
            between = text[words[last][1][1]:words[last + 1][1][0]]
            if between not in _JOINERS or trailing(last + 1):
                break
            last += 1
    while last > first and trailing(last):
        last -= 1
    for index in range(first, last):
        between = text[words[index][1][1]:words[index + 1][1][0]]
        if between not in _JOINERS:
            return None
    if last - first + 1 > MAX_SPAN_WORDS:
        return None
    if not any(word not in _STOP for word in lowered[first:last + 1]):
        return None
    phrase = text[words[first][1][0]:words[last][1][1]]
    if phrase.count("(") > phrase.count(")"):
        if text[words[last][1][1]:words[last][1][1] + 1] != ")":
            return None
        phrase += ")"
    if phrase.count("(") != phrase.count(")"):
        return None
    return phrase


def _participle(word: str) -> bool:
    return len(word) > 5 and word.endswith(("ing", "ed"))


def _cue(rival: dict, match: dict) -> str:
    name = rival["function"]["name"]
    if match["kind"] == "interface":
        if match["rival_shape"] == "array":
            noun = match["rival_parameters"][0].replace("_", " ")
            return f"For an array of {noun}, use {name}."
        names = match["rival_parameters"]
        listed = ", ".join(names[:-1]) + " and " + names[-1]
        return f"For separate {listed} arguments, use {name}."
    return f"For {match['rival_phrase']}, use {name}."


def _cue_problem(cue: str, names: list[str], target: str, rival: str) -> str | None:
    if not cue or cue != cue.strip() or "\n" in cue or not cue.endswith(".") or cue.count(".") != 1 + rival.count("."):
        return "The cue is empty or not one sentence."
    if len(cue.split()) > MAX_SPAN_WORDS + 6:
        return "The cue is longer than the cue limit."
    lowered = cue.lower()
    for banned in BANNED:
        if banned in lowered:
            return f"The cue would use exclusive wording {banned!r}."
    if len(_name_hits(cue, rival)) != 1:
        return "The cue does not name exactly one rival."
    if _name_hits(cue, target):
        return "The cue names the target as well as the rival."
    if any(_name_hits(cue, name) for name in names if name not in {target, rival}):
        return "The cue names a third tool."
    return None


def _name_hits(text: str, name: str) -> list:
    return re.findall(rf"(?<![\w.]){re.escape(name)}(?![\w])", text)


def _redundant_with_name(item: dict) -> str | None:
    """A text cue whose rival-side difference the rival's name already spells adds nothing.

    The name is in every request, so ``For the headlights, use setHeadlights.``
    costs tokens and carries no information the model lacked.
    """
    if item["kind"] != "text":
        return None
    differing = {
        _lemma(word)
        for word in item["evidence"]["rival"]["differing_words"]
        if word.lower() not in _STOP
    }
    if differing and differing <= _name_tokens(item["function_name"]):
        return "The rival's name already spells its differing words."
    return None


def _name_tokens(name: str) -> set[str]:
    parts = re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+", name)
    return {_lemma(part) for part in parts}


def _shape(tool: dict) -> str | None:
    required = _required(tool)
    if len(required) == 1 and required[0][1] in {"array:number", "array:integer"}:
        return "array"
    if len(required) >= 2 and all(kind in _NUMERIC for _name, kind in required):
        return "scalars"
    return None


def _required(tool: dict) -> tuple:
    function = tool["function"]
    parameters = function.get("parameters") or {}
    props = parameters.get("properties") or {}
    found = []
    for name in parameters.get("required") or []:
        schema = props.get(name) or {}
        kind = schema.get("type")
        if kind == "array":
            kind = "array:" + str((schema.get("items") or {}).get("type"))
        found.append((name, kind))
    return tuple(found)


def _signature(tool: dict) -> tuple:
    return tuple(sorted(str(kind) for _name, kind in _required(tool)))


def _required_records(tool: dict) -> list[dict]:
    return [{"name": name, "type": kind} for name, kind in _required(tool)]


def _shared_content(left: list, right: list) -> float:
    a = {_lemma(word.lower()) for word, _span in left if word.lower() not in _STOP}
    b = {_lemma(word.lower()) for word, _span in right if word.lower() not in _STOP}
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _lemma(word: str) -> str:
    lowered = word.lower()
    if len(lowered) > 4 and lowered.endswith("ies"):
        return lowered[:-3] + "y"
    if len(lowered) > 4 and lowered.endswith(("ches", "shes", "sses", "xes", "zes")):
        return lowered[:-2]
    if len(lowered) > 3 and lowered.endswith("s") and not lowered.endswith("ss"):
        return lowered[:-1]
    return lowered


def _words(text: str) -> list:
    return [(match.group(0), match.span()) for match in re.finditer(r"[A-Za-z0-9']+", text)]
