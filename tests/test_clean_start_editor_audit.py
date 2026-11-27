"""Corpus-wide audits of S, X and SX on every in-scope catalogue, plus exposed-draw regressions.

The audits re-derive each invariant from the arms themselves rather than from
the editors' own ledgers, so a wrong ledger cannot hide a wrong edit.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import builtins
import json
import re

import pytest

from tool_compression.adapter import description_slots
from tool_compression.clean_start.descriptions import action_sentence, split_protected, suite_preamble
from tool_compression.clean_start.editor_s import edit_catalogue
from tool_compression.clean_start.editor_x import _object_head, _words, qualify_catalogue
from tool_compression.clean_start.pilot import study_dir
from tool_compression.clean_start.pin import ARMS
from tool_compression.clean_start.prepare import JAVA_HINT, JAVASCRIPT_HINT, PYTHON_HINT, model_facing_tools
from tool_compression.clean_start.render import render_tools
from tool_compression.clean_start.report import VALIDATION_DIGEST, VALIDATION_EVIDENCE
from tool_compression.clean_start.runner import arm_tools
from tool_compression.clean_start.scope import in_scope_questions, study_categories

HINTS = (PYTHON_HINT, JAVA_HINT, JAVASCRIPT_HINT)
_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_QUOTED = re.compile(r"'[^']+'|\"[^\"]+\"")
_KEPT_WORDS = re.compile(r"\b(?:not|no|never|none|without|cannot|can't|only|whether|internal)\b", re.IGNORECASE)
_STOP = {
    "a", "an", "the", "of", "to", "for", "and", "or", "in", "on", "with", "from", "by",
    "into", "over", "under", "between", "across", "at", "as", "if", "is", "are", "be",
    "this", "that", "these", "those", "it", "its", "their", "when", "which", "who",
}


@pytest.fixture(scope="module")
def corpus() -> list[dict]:
    seen: dict[str, dict] = {}
    for category in study_categories():
        for case in in_scope_questions(category):
            tools = model_facing_tools(case["function"], case["category"])
            key = sha256(json.dumps(tools, sort_keys=True).encode("utf-8")).hexdigest()
            if key not in seen:
                seen[key] = {"tools": tools, "rendered": render_tools(deepcopy(tools))}
    assert len(seen) == 1020
    return list(seen.values())


def _description(tool: dict) -> str:
    return tool["function"]["description"]


def _stems(text: str) -> set[str]:
    found = set()
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
        found.add(word)
    return found


def test_s_states_each_language_hint_once_on_its_first_carrier(corpus):
    dropped = 0
    for entry in corpus:
        u, s = entry["tools"], entry["rendered"]["arms"]["S"]
        for hint in HINTS:
            carriers = [index for index, tool in enumerate(u) if _description(tool).endswith(hint)]
            if not carriers:
                assert not any(hint in _description(tool) for tool in s)
                continue
            for index in carriers:
                blank = not split_protected(_description(u[index]))[0].strip()
                if index == carriers[0] or blank:
                    assert _description(s[index]).endswith(hint)
                else:
                    assert hint not in _description(s[index])
                    dropped += 1
    assert dropped > 0


def test_s_suite_labels_name_a_suite_an_earlier_tool_states_verbatim(corpus):
    labels = 0
    for entry in corpus:
        u, s = entry["tools"], entry["rendered"]["arms"]["S"]
        for index, (before, after) in enumerate(zip(u, s)):
            head, _hint = split_protected(_description(before))
            suite = suite_preamble(head)
            if suite is None or _description(after).startswith("This tool belongs to"):
                continue
            membership = head[suite["membership"][0]:suite["membership"][1]]
            name = re.sub(r"^This tool belongs to (?:the )?", "", membership)
            assert _description(after).startswith(name[:1].upper() + name[1:] + ": ")
            assert any(_description(earlier).startswith(membership) for earlier in s[:index])
            labels += 1
    assert labels > 0


def test_s_adds_no_claim_and_keeps_literals_negations_and_qualifiers(corpus):
    for entry in corpus:
        for before, after in zip(entry["tools"], entry["rendered"]["arms"]["S"]):
            pairs = zip(description_slots(deepcopy(before)), description_slots(deepcopy(after)))
            for (pointer, container, key), (_p, edited, edited_key) in pairs:
                original, final = container[key], edited[edited_key]
                if original == final:
                    continue
                assert _stems(final) <= _stems(original) | {"include", "whether"}, (pointer, original, final)
                for word in {match.lower() for match in _KEPT_WORDS.findall(original)}:
                    if _only_in_dropped_schema_defaults(word, original, final, container):
                        continue
                    assert re.search(rf"\b{re.escape(word)}\b", final, re.IGNORECASE), (word, original, final)
                head = split_protected(original)[0] if pointer == "/function/description" else original
                schema_values = {str(value) for value in container.get("enum") or []}
                if "default" in container:
                    schema_values.add(str(container["default"]))
                    schema_values.add(json.dumps(container["default"]))
                for literal in _NUMBER.findall(head) + _QUOTED.findall(head):
                    if literal not in final:
                        assert literal.strip("'\"") in schema_values, (literal, original, final)


def _only_in_dropped_schema_defaults(word: str, original: str, final: str, schema: dict) -> bool:
    """Every occurrence of ``word`` sits in a dropped sentence that states exactly the schema default."""
    if "default" not in schema:
        return False
    for match in re.finditer(rf"\b{re.escape(word)}\b", original, re.IGNORECASE):
        start = original.rfind(". ", 0, match.start())
        start = 0 if start < 0 else start + 2
        end = original.find(".", match.end())
        sentence = original[start:len(original) if end < 0 else end + 1].strip()
        if sentence in final:
            return False
        stated = re.fullmatch(
            r"(?i)defaults?\s+(?:is|to)\s+(.+?)(?:\s+if\s+not\s+(?:specified|provided|given))?\.?", sentence
        )
        if stated is None:
            return False
        value = stated.group(1).strip("'\"")
        default = schema["default"]
        empty = isinstance(default, (str, list, dict)) and not default and value.lower().split()[-1] in {
            "string", "list", "array", "dictionary", "dict", "object",
        } and "empty" in value.lower()
        if value not in {str(default), json.dumps(default)} and not empty:
            return False
    return True


def test_x_cues_join_tools_that_act_on_one_object(corpus):
    cues = 0
    for entry in corpus:
        u, s = entry["tools"], entry["rendered"]["arms"]["S"]
        for row in qualify_catalogue(deepcopy(u)):
            if not row["cue"]:
                continue
            cues += 1
            rival = row["rival"]["tool_index"]
            target_words = _words(action_sentence(_description(u[row["tool_index"]]))[0])
            rival_words = _words(action_sentence(_description(u[rival]))[0])
            assert _object_head(target_words) == _object_head(rival_words)
            assert row["cue"].endswith(f", use {u[rival]['function']['name']}.")
            phrase = (row["evidence"]["rival"] or {}).get("cue_phrase")
            if phrase:
                assert row["cue"] == f"For {phrase}, use {u[rival]['function']['name']}."
                assert phrase in _description(u[rival]) and phrase in _description(s[rival])
    assert cues > 0


def test_sx_is_exactly_s_plus_the_x_cue_and_no_arm_touches_the_schema(corpus):
    for entry in corpus:
        arms = entry["rendered"]["arms"]
        cues = [row["cue"] for row in entry["rendered"]["x_decisions"]]
        for index, cue in enumerate(cues):
            tail = " " + cue if cue else ""
            assert _description(arms["X"][index]) == _description(arms["U"][index]) + tail
            assert _description(arms["SX"][index]) == _description(arms["S"][index]) + tail
            skeletons = set()
            for arm in ARMS:
                copied = deepcopy(arms[arm][index])
                for _pointer, container, key in description_slots(copied):
                    container[key] = ""
                skeletons.add(json.dumps(copied, sort_keys=False))
            assert len(skeletons) == 1


def test_no_multi_turn_catalogue_gets_an_x_cue_so_sx_sends_s_bytes():
    from tool_compression.convert import to_openai_completions_tools

    rendered: dict[str, dict] = {}
    checked = 0
    for category in study_categories():
        if not category.startswith("multi_turn_"):
            continue
        for case in in_scope_questions(category):
            facing = model_facing_tools(case["function"], case["category"])
            presented: list[int] = []
            stages = [(facing, ())]
            for turn in sorted(case.get("held_out") or {}, key=int):
                presented.append(len(facing))
                facing = facing + to_openai_completions_tools(deepcopy(list(case["held_out"][turn])))
                stages.append((facing, tuple(presented)))
            for tools, bounds in stages:
                key = sha256(json.dumps([tools, bounds], sort_keys=True).encode("utf-8")).hexdigest()
                if key not in rendered:
                    rendered[key] = render_tools(deepcopy(tools), bounds)
                arms = rendered[key]["arms"]
                assert not any(row["cue"] for row in rendered[key]["x_decisions"]), case["id"]
                assert arms["X"] == arms["U"] and arms["SX"] == arms["S"], case["id"]
                checked += 1
    assert checked >= 800


def test_editors_never_look_ahead(corpus):
    for entry in corpus:
        tools = entry["tools"]
        if len(tools) < 2:
            continue
        full_s, _rows = edit_catalogue(deepcopy(tools))
        for bound in sorted({1, len(tools) // 2, len(tools) - 1}):
            prefix_s, _rows = edit_catalogue(deepcopy(tools[:bound]))
            assert prefix_s == full_s[:bound]
        bound = len(tools) // 2
        staged = render_tools(deepcopy(tools), (bound,))["arms"]
        alone = render_tools(deepcopy(tools[:bound]))["arms"]
        for arm in ARMS:
            assert staged[arm][:bound] == alone[arm]


def test_editors_run_without_any_file_access(corpus, monkeypatch):
    sample = [entry for entry in corpus if len(entry["tools"]) > 3][:25]

    def refuse(*_args, **_kwargs):
        raise AssertionError("an editor tried to read a file")

    monkeypatch.setattr(builtins, "open", refuse)
    monkeypatch.setattr(Path, "open", refuse)
    monkeypatch.setattr(Path, "read_text", refuse)
    monkeypatch.setattr(Path, "read_bytes", refuse)
    for entry in sample:
        assert render_tools(deepcopy(entry["tools"]))["arms"] == entry["rendered"]["arms"]


def test_exposed_validation_draw_only_gains_s_edits_and_only_loses_x_cues():
    digest = json.loads((study_dir() / VALIDATION_EVIDENCE / VALIDATION_DIGEST).read_text(encoding="utf-8"))
    cases = {
        case["id"]: case
        for category in study_categories()
        for case in in_scope_questions(category)
        if case["id"] in digest["cases"]
    }
    gained_s = lost_x = 0
    for case_id, flown in digest["cases"].items():
        case = cases.get(case_id)
        if case is None:
            continue
        initial = {arm: arm_tools(case["function"], case["category"], arm) for arm in ("U", "S", "X")}
        slots = {
            arm: [(tool["function"]["name"], pointer, container[key])
                  for tool in initial[arm] for pointer, container, key in description_slots(tool)]
            for arm in ("U", "S")
        }
        changed = {
            (name, pointer) for (name, pointer, text), (_n, _p, edited) in zip(slots["U"], slots["S"]) if text != edited
        }
        cued = {tool["function"]["name"] for tool, x in zip(initial["U"], initial["X"]) if tool != x}
        flown_changed = {tuple(slot) for slot in flown["initial_edits"]["s_changed_slots"]}
        flown_cued = set(flown["initial_edits"]["x_cued_tools"])
        assert flown_changed <= changed, case_id
        assert cued <= flown_cued, case_id
        gained_s += len(changed - flown_changed)
        lost_x += len(flown_cued - cued)
    assert gained_s > 0 and lost_x > 0
