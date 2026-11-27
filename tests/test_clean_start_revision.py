"""Editor revision after the c47b186c flight: evidence, report, and general editor rules."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import io
import json
import os
import subprocess
import sys
import tarfile

import pytest

from tool_compression.clean_start.editor_s import edit_catalogue
from tool_compression.clean_start.editor_x import qualify_catalogue, qualify_presented
from tool_compression.clean_start.pilot import study_dir
from tool_compression.clean_start.render import render_tools, verify_cue_phrases
from tool_compression.clean_start.report import (
    REVISED_DIGEST,
    REVISED_EVIDENCE,
    REVISED_POPULATION,
    REVISED_TIP,
    write_revised_pilot_report,
)
from tool_compression.clean_start.runner import arm_tools

REPO = Path(__file__).resolve().parents[1]
PACKAGE = study_dir() / "package"
EVIDENCE = study_dir() / REVISED_EVIDENCE
HINT = " Note that the provided function is in Python 3 syntax."


def _tool(name: str, description: str, properties=None, required=None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties or {"value": {"type": "string", "description": "A value."}},
                "required": required if required is not None else ["value"],
            },
        },
    }


def _suite(name: str, action: str, elaboration: str = ", which provides tools to water and prune plants") -> dict:
    return _tool(name, f"This tool belongs to the Garden API{elaboration}. Tool description: {action}{HINT}")


def test_revised_pilot_evidence_is_byte_identical_to_its_checksums():
    lines = (EVIDENCE / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 397
    for line in lines:
        digest, relative = line.split("  ", 1)
        assert sha256((EVIDENCE / "original" / relative).read_bytes()).hexdigest() == digest, relative
    listed = {line.split("  ", 1)[1].removeprefix("./") for line in lines}
    present = {str(path.relative_to(EVIDENCE / "original")) for path in (EVIDENCE / "original").rglob("*") if path.is_file()}
    assert present == listed
    run = json.loads((EVIDENCE / "original/live-c47b186c/run.json").read_text(encoding="utf-8"))
    assert run["status"] == "incomplete" and run["reason"] == "provider_error:IncompleteRead"


def test_revised_pilot_report_regenerates_from_the_archived_evidence(tmp_path):
    out = tmp_path / "revised.json"
    summary = write_revised_pilot_report(EVIDENCE, out)
    assert out.read_bytes() == (PACKAGE / "pilot_2026_11_25_revised_analysis.json").read_bytes()
    assert summary == {
        "sent": 900,
        "sent_matching_flown_digest": 900,
        "matched_cases": 32,
        "matched_correct": {"U": 27, "S": 26, "X": 28, "SX": 25},
        "discordant_cases": 3,
    }
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["official_settlement"] is False
    assert report["source"]["flown_tip"] == REVISED_TIP
    assert report["source"]["uncertain_attempts"] == [900]
    runner = report["runner"]
    assert [(row["case_id"], row["arm"]) for row in runner["forced_quit_slots"]] == [("memory_kv_prereq_2-customer-2", "U")]
    assert runner["partial_slots"][0]["result_row_written"] is False
    assert all(row["final_equals_last_checkpoint"] for row in runner["memory_snapshots"].values())
    first = report["tokens"]["first_request"]["delta_vs_U"]
    assert first["S"]["tokens"] < 0 < first["X"]["tokens"]


def test_s_states_suite_membership_and_hint_once_on_their_first_carrier():
    kitchen = "This tool belongs to the Kitchen API, which provides tools for recipes. Tool description: Bake a cake."
    tools = [
        _suite("water", "Water one plant."),
        _suite("prune", "Prune one plant."),
        _tool("other", kitchen + HINT),
        _suite("feed", "Feed one plant."),
    ]
    edited, rows = edit_catalogue(deepcopy(tools))
    texts = [tool["function"]["description"] for tool in edited]
    assert texts == [tools[0]["function"]["description"], "Garden API: Prune one plant.", kitchen, "Garden API: Feed one plant."]
    for name, expected in (
        ("suite_context_state", ["first_in_request", "carried_earlier", "first_in_request", "carried_earlier"]),
        ("membership_state", ["first_in_request", "carried_earlier", "first_in_request", "carried_earlier"]),
        ("hint_state", ["first_in_request", "carried_earlier", "carried_earlier", "carried_earlier"]),
    ):
        assert [tool_rows[0][name] for tool_rows in rows] == expected
    carriers = {
        (index, fact["decision"]): (fact["carried_excerpt"], fact["carried_by_tool_index"])
        for index, tool_rows in enumerate(rows) for row in tool_rows for fact in row["facts"]
        if "carried_by_tool_index" in fact
    }
    context = "This tool belongs to the Garden API, which provides tools to water and prune plants."
    assert carriers == {
        (1, "SUITE_CONTEXT"): (context, 0), (1, "SUITE_LABEL"): ("This tool belongs to the Garden API", 0),
        (1, "HINT_CONTEXT"): (HINT, 0), (2, "HINT_CONTEXT"): (HINT, 0),
        (3, "SUITE_CONTEXT"): (context, 0), (3, "SUITE_LABEL"): ("This tool belongs to the Garden API", 0),
        (3, "HINT_CONTEXT"): (HINT, 0),
    }
    alone, _rows = edit_catalogue(deepcopy(tools[1:2]))
    assert alone[0] == tools[1]


def test_s_suite_rule_is_append_only_and_ignores_different_elaborations():
    tools = [_suite("water", "Water one plant."), _suite("prune", "Prune one plant.", ", which provides pruning only")]
    edited, _rows = edit_catalogue(deepcopy(tools))
    assert edited[0] == tools[0]
    assert edited[1]["function"]["description"] == tools[1]["function"]["description"].removesuffix(HINT)
    grown, _rows = edit_catalogue(deepcopy(tools + [_suite("feed", "Feed one plant.")]))
    assert grown[:2] == edited
    assert grown[2]["function"]["description"] == "Garden API: Feed one plant."


def test_s_membership_without_elaboration_becomes_a_label_after_its_first_carrier():
    bare = [
        _tool("water", "This tool belongs to the Garden API. Tool description: Water one plant." + HINT),
        _tool("prune", "This tool belongs to the Garden API. Tool description: Prune one plant." + HINT),
    ]
    edited, rows = edit_catalogue(deepcopy(bare))
    assert [tool["function"]["description"] for tool in edited] == [
        "This tool belongs to the Garden API. Water one plant." + HINT,
        "Garden API: Prune one plant.",
    ]
    assert rows[1][0]["change_class"] == "suite_context+suite_label+hint_context"


def test_s_hint_needs_an_earlier_carrier_and_never_empties_a_description():
    first = _tool("first", "Add two numbers." + HINT)
    second = _tool("second", "Subtract two numbers." + HINT)
    only_hint = _tool("hint_only", HINT)
    java = _tool("java", "Add two numbers. Note that the provided function is in Java 8 SDK syntax.")
    edited, rows = edit_catalogue(deepcopy([first, second, only_hint, java]))
    texts = [tool["function"]["description"] for tool in edited]
    assert texts == [
        "Add two numbers." + HINT,
        "Subtract two numbers.",
        HINT,
        "Add two numbers. Note that the provided function is in Java 8 SDK syntax.",
    ]
    assert rows[3][0]["hint_state"] == "first_in_request"
    alone, _rows = edit_catalogue(deepcopy([second]))
    assert alone[0] == second


def test_s_keeps_enum_sentences_that_gloss_values():
    glossed = {
        "type": "string",
        "description": "The sort order. Possible values are 'asc' for ascending and 'desc' for descending.",
        "enum": ["asc", "desc"],
    }
    bare = {"type": "string", "description": "The unit. Supported values: 'm' or 'cm'.", "enum": ["m", "cm"]}
    tool = _tool("sorter", "Sort the rows.", {"order": glossed, "unit": bare}, ["order", "unit"])
    edited, _rows = edit_catalogue([deepcopy(tool)])
    properties = edited[0]["function"]["parameters"]["properties"]
    assert properties["order"] == glossed
    assert properties["unit"]["description"] == "The unit."


def test_x_refuses_a_cue_whose_target_already_claims_the_rival_object():
    rival = _tool("tool_b", "Delete a folder in current folder.")
    for joined in ("Delete a file or folder.", "Delete a file and folder."):
        rows = qualify_catalogue([_tool("tool_a", joined), rival])
        assert rows[0]["cue"] == ""
        assert "target's differing words end in a coordinator" in rows[0]["rejected_rivals"][0]["reason"]
        assert rows[1]["cue"] == ""
        assert "rival's differing words end in a coordinator" in rows[1]["rejected_rivals"][0]["reason"]
    rows = qualify_catalogue([_tool("tool_a", "Delete a file from folder."), rival])
    assert rows[0]["cue"] == ""
    assert "different objects (file versus folder)" in rows[0]["no_cue_reason"]


def test_x_name_spells_a_difference_by_abbreviation_or_compound():
    spelled = [
        _tool("max_value", "Find the maximum value in a list of numbers."),
        _tool("min_value", "Find the minimum value in a list of numbers."),
    ]
    rows = qualify_catalogue(spelled)
    assert [row["cue"] for row in rows] == ["", ""]
    assert all("already spells" in row["no_cue_reason"] for row in rows)
    opaque = [
        _tool("tool_a", "Find the maximum value in a list of numbers."),
        _tool("tool_b", "Find the minimum value in a list of numbers."),
    ]
    assert [row["cue"] for row in qualify_catalogue(opaque)] == [
        "For the minimum value, use tool_b.",
        "For the maximum value, use tool_a.",
    ]
    stores = [
        _tool("safeway_products", "Get the vegan products at Safeway store."),
        _tool("wholefoods_products", "Get the vegan products at Whole Foods store."),
    ]
    rows = qualify_catalogue(stores)
    assert rows[0]["cue"] == ""
    assert "already spells" in rows[0]["rejected_rivals"][0]["reason"]
    short = [
        _tool("set_go_mode", "Sets the golden mode of the lamp."),
        _tool("set_red_mode", "Sets the red mode of the lamp."),
    ]
    assert qualify_catalogue(short)[1]["cue"] == "For the golden mode, use set_go_mode."
    camel = [
        _tool("AmazonGameStore_recommend", "Recommend games from the Amazon Game Store."),
        _tool("BoardGameGeek_recommend", "Recommend games from the BoardGameGeek store."),
    ]
    assert qualify_catalogue(camel)[0]["cue"] == ""
    assert "already spells" in qualify_catalogue(camel)[0]["no_cue_reason"]
    camel[1]["function"]["name"] = "tool_b"
    assert qualify_catalogue(camel)[0]["cue"] == "For the BoardGameGeek store, use tool_b."
    phrase = [
        _tool("google_books_search", "Search for a book in the Google Books library with optional parameters"),
        _tool("openlibrary_books_search", "Search for a book in the Open Library with optional parameters"),
    ]
    assert qualify_catalogue(phrase)[0]["cue"] == ""
    phrase[1]["function"]["name"] = "tool_b"
    assert qualify_catalogue(phrase)[0]["cue"] == "For the Open Library, use tool_b."
    inside_a_part = [
        _tool("error_entries", "Get the error entries of the server."),
        _tool("login_entries", "Get the log entries of the server."),
    ]
    assert qualify_catalogue(inside_a_part)[0]["cue"] == "For the log entries, use login_entries."


def test_s_default_value_and_unset_condition_are_not_negations():
    properties = {
        "file_name": {
            "type": "string",
            "description": "The name of the file to write to. Defaults to None.",
            "default": "None",
        },
        "host": {
            "type": "string",
            "description": "The host. Defaults to 'localhost' if not specified. Do not add a port.",
            "default": "localhost",
        },
        "null_default": {"type": "string", "description": "The proxy. Defaults to None.", "default": None},
        "other": {"type": "string", "description": "The mode. Defaults to none if not given.", "default": "auto"},
    }
    tool = _tool("writer", "Write a file.", properties, ["file_name"])
    edited, rows = edit_catalogue([deepcopy(tool)])
    finals = {name: value["description"] for name, value in edited[0]["function"]["parameters"]["properties"].items()}
    assert finals == {
        "file_name": "The name of the file to write to.",
        "host": "The host. Do not add a port.",
        "null_default": "The proxy. Defaults to None.",
        "other": "The mode. Defaults to none if not given.",
    }
    by_pointer = {row["pointer"]: row for row in rows[0]}
    assert by_pointer["/function/parameters/properties/file_name/description"]["change_class"] == "schema_guaranteed"


def test_s_empty_defaults_match_empty_schema_values():
    properties = {
        "text": {"type": "string", "description": "Description of the ticket. Defaults to an empty string.", "default": ""},
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Tags to add. Default is an empty list.",
            "default": [],
        },
        "extra": {"type": "object", "description": "Extra fields. Defaults to an empty object.", "default": {}},
        "term": {"type": "string", "description": "Search term. Defaults to an empty string.", "default": "all"},
        "items": {"type": "array", "items": {"type": "string"}, "description": "Items. Defaults to an empty list.", "default": ["a"]},
    }
    tool = _tool("ticket", "Create a ticket.", properties, ["text"])
    edited, _rows = edit_catalogue([deepcopy(tool)])
    finals = {name: value["description"] for name, value in edited[0]["function"]["parameters"]["properties"].items()}
    assert finals == {
        "text": "Description of the ticket.",
        "tags": "Tags to add.",
        "extra": "Extra fields.",
        "term": "Search term. Defaults to an empty string.",
        "items": "Items. Defaults to an empty list.",
    }


def test_s_drops_only_the_whitespace_that_ends_a_field():
    first = _tool(
        "first",
        "Count lines in a file.  " + HINT,
        {"path": {"type": "string", "description": "The file path.  "}, "mode": {"type": "string", "description": "A  mode. "}},
        ["path"],
    )
    second = _tool("second", "Count words in a file. " + HINT)
    only_hint = _tool("third", " " + HINT)
    edited, rows = edit_catalogue(deepcopy([first, second, only_hint]))
    assert [tool["function"]["description"] for tool in edited] == [
        "Count lines in a file." + HINT,
        "Count words in a file.",
        " " + HINT,
    ]
    properties = edited[0]["function"]["parameters"]["properties"]
    assert properties["path"]["description"] == "The file path."
    assert properties["mode"]["description"] == "A  mode."
    classes = {(index, row["pointer"]): row["change_class"] for index, tool_rows in enumerate(rows) for row in tool_rows}
    assert classes[(0, "/function/description")] == "trailing_space"
    assert classes[(0, "/function/parameters/properties/path/description")] == "trailing_space"
    assert classes[(1, "/function/description")] == "hint_context+trailing_space"
    assert classes[(2, "/function/description")] is None
    trimmed = rows[0][0]
    assert trimmed["cosmetic"] is True and trimmed["meaningful"] is False and trimmed["adopted"] is True
    assert [fact["excerpt"] for fact in trimmed["facts"] if fact["decision"] == "WHITESPACE"] == ["  "]
    for tool_rows in rows:
        for row in tool_rows:
            for fact in row["facts"]:
                if fact["decision"] == "KEEP" and row["adopted"]:
                    assert fact["after"] in row["final"]


def test_x_cue_phrase_keeps_the_head_noun_before_of_or_on():
    tools = [
        _tool("tool_a", "Calculates the return on assets (ROA) for a firm."),
        _tool("tool_b", "Calculates the return on equity (ROE) for a firm."),
    ]
    cues = [row["cue"] for row in qualify_catalogue(tools)]
    assert cues == [
        "For the return on equity (ROE), use tool_b.",
        "For the return on assets (ROA), use tool_a.",
    ]


def test_cue_phrase_must_survive_in_the_rival_s_text():
    tools = [_tool("tool_a", "Sets the front lights of the vehicle."), _tool("tool_b", "Sets the rear lights of the vehicle.")]
    rendered = render_tools(tools)
    decisions = qualify_catalogue(tools)
    assert decisions[0]["cue"] == "For the rear lights, use tool_b."
    verify_cue_phrases(rendered["arms"], decisions)
    broken = deepcopy(rendered["arms"])
    broken["S"][1]["function"]["description"] = "Sets the vehicle."
    with pytest.raises(RuntimeError, match="not in the S text"):
        verify_cue_phrases(broken, decisions)


def test_held_out_tools_never_change_tools_already_sent():
    initial = [_tool("tool_a", "Sets the front lights of the vehicle."), _tool("tool_b", "Computes the sum of two numbers.")]
    late = [_tool("tool_c", "Sets the rear lights of the vehicle.")]
    flat = qualify_catalogue(initial + late)
    assert flat[0]["cue"] == "For the rear lights, use tool_c."
    staged = qualify_presented(initial + late, (2,))
    assert staged[0]["cue"] == "" and staged[2]["cue"] == "For the front lights, use tool_a."
    before = render_tools(deepcopy(initial))["arms"]
    after = render_tools(deepcopy(initial + late), (2,))["arms"]
    for arm in before:
        assert after[arm][:2] == before[arm]


def test_runner_sends_held_out_batches_as_appends(monkeypatch):
    functions = [
        {"name": "tool_a", "description": "Sets the front lights of the vehicle.",
         "parameters": {"type": "dict", "properties": {"value": {"type": "string", "description": "A value."}}, "required": ["value"]}},
        {"name": "tool_b", "description": "Computes the sum of two numbers.",
         "parameters": {"type": "dict", "properties": {"value": {"type": "string", "description": "A value."}}, "required": ["value"]}},
    ]
    held = [[{"name": "tool_c", "description": "Sets the rear lights of the vehicle.",
              "parameters": {"type": "dict", "properties": {"value": {"type": "string", "description": "A value."}}, "required": ["value"]}}]]
    for arm in ("U", "S", "X", "SX"):
        first = arm_tools(functions, "multi_turn_miss_func", arm)
        later = arm_tools(functions, "multi_turn_miss_func", arm, held)
        assert later[:2] == first and len(later) == 3


def test_editor_modules_read_no_files_and_no_evaluation_artifacts():
    for name in ("editor_s.py", "editor_x.py", "descriptions.py", "render.py"):
        text = (REPO / "src/tool_compression/clean_start" / name).read_text(encoding="utf-8")
        for forbidden in ("open(", "read_text", "read_bytes", "studies", "evidence/", "model_outputs",
                          "attempts", "case_id", "held_out", "clean_start.report", "clean_start.revision",
                          "clean_start.package", "clean_start.runner", "clean_start.pilot"):
            assert forbidden not in text, (name, forbidden)


def _commit_available(commit: str) -> bool:
    try:
        subprocess.run(["git", "-C", str(REPO), "cat-file", "-e", f"{commit}^{{commit}}"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    return True


def _extract(commit: str, root: Path) -> None:
    archive = subprocess.run(
        ["git", "-C", str(REPO), "archive", "--format=tar", commit, "src",
         "studies/clean-start-usx/bfcl", "studies/clean-start-usx/scope.json", "studies/clean-start-usx/pilot/draw.json"],
        check=True, capture_output=True,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(root, filter="data")


@pytest.mark.skipif(not _commit_available(REVISED_TIP), reason="flown tip not in local history (shallow checkout)")
@pytest.mark.parametrize("mode, committed", [("conversations", REVISED_DIGEST), ("population", REVISED_POPULATION)])
def test_flown_editor_digests_reproduce_from_the_flown_commit(tmp_path, mode, committed):
    _extract(REVISED_TIP, tmp_path)
    env = {key: value for key, value in os.environ.items() if not key.endswith("_API_KEY")}
    env["PYTHONPATH"] = str(tmp_path / "src")
    out = subprocess.run(
        [sys.executable, str(REPO / "scripts/clean_start_sent_digest.py"), mode],
        check=True, capture_output=True, env=env, cwd=tmp_path,
    ).stdout
    payload = json.loads(out)
    payload["source_commit"] = REVISED_TIP
    expected = json.loads((EVIDENCE / committed).read_text(encoding="utf-8"))
    assert payload == expected
