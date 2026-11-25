"""Clean-start U/S/X/SX package.

Catalogue identity hashes the vendored files and compares them with
manifest.json. It does not call git, so a shallow GitHub Actions checkout
still passes. No test contacts a provider or reads a provider key.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import json
import re
import socket
import urllib.request

import pytest

from tool_compression.clean_start.categories import (
    ALL_SCORING_CATEGORIES,
    OUT_OF_SCOPE,
    category_from_id,
    is_java,
    result_group,
)
from tool_compression.clean_start.editor_s import edit_tool
from tool_compression.clean_start.editor_x import qualify_catalogue
from tool_compression.clean_start.load import (
    bfcl_root,
    identity_rows,
    load_prereqs,
    load_questions,
    prompt_manifest,
    read_jsonl,
)
from tool_compression.clean_start.pilot import (
    PILOT_K,
    PILOT_SEED,
    build_draw,
    compile_case,
    coverage,
    render_document,
    study_dir,
)
from tool_compression.clean_start.scope import (
    OFFICIAL_SIMPLE_CATEGORIES,
    build_scope_document,
    in_scope_questions,
    load_scope,
    question_in_scope,
    u_tool_count,
)
from tool_compression.clean_start.pin import ARMS, REQUEST_MODEL, RETIRED_ROUTE_ALIAS, study_manifest
from tool_compression.clean_start.prepare import (
    AGENTIC_SYSTEM_PROMPT,
    HOLDOUT_USER_PROMPT,
    JAVA_HINT,
    model_facing_tools,
)
from tool_compression.clean_start.rate_card import is_peak, spend_usd
from tool_compression.clean_start.render import render_tools
from tool_compression.clean_start.runner import (
    build_slots,
    execute,
    execution_config,
    executor_instance_name,
    request_body,
    turn_messages,
    write_plan,
)
from tool_compression.clean_start.scoring import append_result, evaluate_instructions, result_relative
from tool_compression.evaluation import evaluation_manifest

REPO = Path(__file__).resolve().parents[1]
QUESTION_COUNTS = {
    "simple_python": 400,
    "simple_java": 100,
    "simple_javascript": 50,
    "multiple": 200,
    "parallel": 200,
    "parallel_multiple": 200,
    "irrelevance": 240,
    "live_simple": 258,
    "live_multiple": 1053,
    "live_parallel": 16,
    "live_parallel_multiple": 24,
    "live_irrelevance": 884,
    "live_relevance": 16,
    "multi_turn_base": 200,
    "multi_turn_miss_func": 200,
    "multi_turn_miss_param": 200,
    "multi_turn_long_context": 200,
    "memory_kv": 155,
    "memory_vector": 155,
    "memory_rec_sum": 155,
    "web_search_base": 100,
    "web_search_no_snippet": 100,
}
BANNED_CUE = ("only this", "cannot", "can't", "exclusively", "unable to", "does not handle", "can't handle")
LEGACY_ARM = re.compile(r"\b(?:S2|X2|SX2)\b")


def _utc(*parts: int) -> datetime:
    return datetime(*parts, tzinfo=timezone.utc)


def _echo_function() -> dict:
    return {
        "name": "echo",
        "description": "Echo a value.",
        "parameters": {
            "type": "dict",
            "properties": {
                "value": {"type": "integer", "description": "A value."},
            },
            "required": ["value"],
        },
    }


def _usage(**extra) -> dict:
    usage = {
        "prompt_tokens": 1000,
        "prompt_cache_hit_tokens": 200,
        "prompt_cache_miss_tokens": 800,
        "completion_tokens": 50,
        "completion_tokens_details": {"reasoning_tokens": 12},
    }
    usage.update(extra)
    return usage


def _tool_response(name: str = "echo") -> dict:
    return {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": None,
                "reasoning_content": "because",
                "tool_calls": [{
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": name, "arguments": "{\"value\": 1}"},
                }],
            }
        }],
        "usage": _usage(),
    }


def _content_response(text: str = "done") -> dict:
    return {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": text,
                "reasoning_content": "ok",
            }
        }],
        "usage": _usage(),
    }


def _simple_case() -> dict:
    return {
        "id": "simple_python_0",
        "category": "simple_python",
        "question": [[{"role": "user", "content": "What is 1?"}]],
        "function": [_echo_function()],
        "prereq": False,
    }


def _off_peak_cost() -> Decimal:
    amount, band = spend_usd(
        cache_hit=200,
        cache_miss=800,
        output=50,
        at=_utc(2026, 11, 25, 12, 0),
    )
    assert band == "off_peak"
    return amount


class _Scripted:
    def __init__(self, responses: list[dict]):
        self.responses = list(responses)
        self.bodies: list[dict] = []

    def __call__(self, body: dict) -> dict:
        self.bodies.append(body)
        if not self.responses:
            raise RuntimeError("script exhausted")
        return self.responses.pop(0)


def test_study_is_not_official_v1_1_and_settlement_stays_false():
    manifest = study_manifest()
    assert manifest["official_settlement"] is False
    assert manifest["extends_official_v1_1"] is False
    assert manifest["request_model"] == "deepseek-flash"
    assert manifest["served_as"] == "DeepSeek-V4.1-Flash-1017"
    assert manifest["retired_route_alias_not_sent"] == "deepseek-v4-flash"
    assert manifest["max_tokens_sent"] is False
    assert manifest["paid_inference_authorized_by_this_package"] is False
    assert tuple(manifest["arms"]) == ARMS == ("U", "S", "X", "SX")
    assert "official_settlement" not in evaluation_manifest()
    evaluation = (REPO / "src" / "tool_compression" / "evaluation.py").read_text(encoding="utf-8")
    assert "official_settlement" not in evaluation


def test_catalogue_identity_matches_manifest_without_git():
    recorded = prompt_manifest()
    assert recorded["bfcl_commit"] == "6ea57973c7a6097fd7c5915698c54c17c5b1b6c8"
    fresh = identity_rows()
    assert sorted(fresh, key=lambda row: row["path"]) == sorted(recorded["files"], key=lambda row: row["path"])
    root = bfcl_root()
    names = {path.name for path in root.rglob("*") if path.is_file()}
    assert "manifest.json" in names
    for banned in ("possible_answer", "format_sensitivity", "unused_datasets"):
        assert banned not in {part for path in root.rglob("*") for part in path.parts}
    for category in OUT_OF_SCOPE:
        assert not list(root.rglob(f"*{category}*"))


def test_scoring_set_counts_and_rewritten_ids():
    assert list(QUESTION_COUNTS) == list(ALL_SCORING_CATEGORIES)
    for category, count in QUESTION_COUNTS.items():
        questions = load_questions(category)
        assert len(questions) == count
        assert all(category_from_id(case["id"]) == category for case in questions)
        assert all("possible_answer" not in case for case in questions)
        assert all("path" not in case for case in questions)
    for category in ("memory_kv", "memory_vector", "memory_rec_sum"):
        assert len(load_prereqs(category)) == 37
        assert load_questions(category)[0]["id"].startswith(f"{category}_")
        assert load_questions(category)[0]["involved_classes"] == [f"MemoryAPI_{category.split('_', 1)[1]}"]
    assert load_questions("web_search_base")[0]["id"].startswith("web_search_base_")
    assert load_questions("web_search_no_snippet")[0]["id"].startswith("web_search_no_snippet_")
    assert is_java("simple_java") and not is_java("simple_javascript")


def test_loader_refuses_gold_paths():
    with pytest.raises(RuntimeError, match="possible_answer"):
        read_jsonl(bfcl_root() / "possible_answer" / "BFCL_v4_simple_python.json")


def test_multi_turn_path_is_not_an_editor_input_and_holdout_is_recorded():
    raw_path = bfcl_root() / "prompts" / "BFCL_v4_multi_turn_base.json"
    raw = json.loads(raw_path.read_text(encoding="utf-8").splitlines()[0])
    loaded = load_questions("multi_turn_base")[0]
    assert "path" in raw and "path" not in loaded
    document = render_document(loaded)
    dumped = json.dumps(document)
    assert json.dumps(raw["path"]) not in dumped
    assert raw["question"][0][0]["content"] not in dumped
    held = load_questions("multi_turn_miss_func")[0]
    assert "sort" in [doc.get("name") for docs in held["held_out"].values() for doc in docs]
    initial_names = [doc.get("name") for doc in held["function"]]
    assert "sort" not in initial_names
    excluded = [
        case for case in load_questions("multi_turn_base")
        if case["excluded_function"]
    ]
    assert excluded, "pinned loader leaves excluded_function in the catalogue"
    sample = excluded[0]
    present = {doc.get("name") for doc in sample["function"]}
    assert set(sample["excluded_function"]) <= present
    rendered = render_document(sample)
    assert rendered["excluded_function_present"] == sample["excluded_function"]


def test_java_stringification_is_recorded_and_web_docs_match():
    java = load_questions("simple_java")[0]
    compiled = compile_case(java)
    assert compiled["sendable"] and compiled["editable"]
    assert "java_js_parameters_stringified_before_edit" in compiled["limitations"]
    facing = compiled["arms"]["U"]
    assert facing[0]["function"]["description"].endswith(JAVA_HINT)
    for prop in facing[0]["function"]["parameters"]["properties"].values():
        assert prop["type"] == "string"
    raw_names = [doc["name"].replace(".", "_") for doc in java["function"]]
    assert [tool["function"]["name"] for tool in facing] == raw_names
    raw_required = java["function"][0]["parameters"].get("required")
    assert facing[0]["function"]["parameters"].get("required") == raw_required
    base = compile_case(load_questions("web_search_base")[0])
    hidden = compile_case(load_questions("web_search_no_snippet")[0])
    assert base["arms"]["U"] == hidden["arms"]["U"]
    assert "snippet_flag_is_execution_setting" in base["limitations"]
    assert AGENTIC_SYSTEM_PROMPT not in json.dumps(base)


def test_questions_and_gold_do_not_change_the_render():
    case = load_questions("multiple")[10]
    original = compile_case(case)
    mutated = deepcopy(case)
    mutated["question"] = [[{"role": "user", "content": "A question the editor must not see."}]]
    mutated["possible_answer"] = {"secret": "gold"}
    mutated["initial_config"] = {"unused": "state"}
    assert compile_case(mutated)["arms"] == original["arms"]
    assert "A question the editor must not see." not in json.dumps(original)


def test_editor_s_keeps_schema_facts_and_x_hides_s():
    raw = {
        "name": "area",
        "description": "This function calculates the area of a rectangle.",
        "parameters": {
            "type": "dict",
            "properties": {
                "width": {"type": "float", "description": "Width in meters."},
                "unit": {
                    "type": "string",
                    "description": "The unit. Supported values: 'm' or 'cm'.",
                    "enum": ["m", "cm"],
                },
                "internal": {
                    "type": "boolean",
                    "description": "A flag to determine whether to calculate the internal angles. Default is true.",
                    "default": True,
                },
                "label": {"type": "string", "description": "A label. Default is true."},
            },
            "required": ["width"],
        },
        "response": {"description": "A response description that stays."},
    }
    rendered = render_tools(model_facing_tools([raw], "simple_python"))
    edited = rendered["arms"]["S"][0]["function"]
    original = rendered["arms"]["U"][0]["function"]
    assert edited["description"].startswith("Calculates the area of a rectangle.")
    assert edited["description"].endswith(" Note that the provided function is in Python 3 syntax.")
    width = edited["parameters"]["properties"]["width"]
    assert width["type"] == "number" and width["format"] == "float"
    assert "This is a float type value." not in width["description"]
    assert "Width in meters." in width["description"]
    unit = edited["parameters"]["properties"]["unit"]
    assert unit["enum"] == ["m", "cm"]
    assert "Supported values" not in unit["description"]
    assert "The unit." in unit["description"]
    internal = edited["parameters"]["properties"]["internal"]
    assert internal["description"] == "Whether to calculate the internal angles."
    assert internal["default"] is True
    assert edited["parameters"]["properties"]["label"]["description"] == "A label. Default is true."
    assert edited["response"]["description"] == original["response"]["description"]
    alone, _rows = edit_tool(deepcopy(rendered["arms"]["U"][0]))
    assert rendered["arms"]["S"][0] == alone

    pair = {case["id"]: case for case in load_questions("multiple")}
    different = model_facing_tools(pair["multiple_34"]["function"], "multiple")
    assert not [change for change in render_tools(different)["changes"] if change["arm"] == "X"]
    refusals = {
        (row["function_name"], rival["function_name"]): rival["reason"]
        for row in qualify_catalogue(different) for rival in row["rejected_rivals"]
    }
    assert "different objects (divisor versus multiple)" in refusals[("math_gcd", "math_lcm")]
    assert "different objects (multiple versus divisor)" in refusals[("math_lcm", "math_gcd")]
    compiled = compile_case(pair["multiple_12"])
    cues = {change["function"]: change for change in compiled["changes"] if change["arm"] == "X"}
    assert set(cues) == {"financial_ratios_calculate_ROA", "financial_ratios_calculate_ROE"}
    for tool_u, tool_s, tool_x, tool_sx in zip(*(compiled["arms"][arm] for arm in ARMS)):
        name = tool_u["function"]["name"]
        cue = cues.get(name, {}).get("cue", "")
        rival = cues.get(name, {}).get("rival")
        if not cue:
            assert tool_x == tool_u
            assert tool_sx == tool_s
            continue
        assert tool_x["function"]["description"] == tool_u["function"]["description"] + " " + cue
        assert tool_sx["function"]["description"] == tool_s["function"]["description"] + " " + cue
        assert cue.count(rival) == 1
        lowered = cue.lower()
        for phrase in BANNED_CUE:
            assert phrase not in lowered
    extra = model_facing_tools([_echo_function()], "multiple")
    with_extra = render_tools(compiled["arms"]["U"] + extra)
    extra_cues = {
        change["function"]: change["cue"]
        for change in with_extra["changes"]
        if change["arm"] == "X"
    }
    assert {name: row["cue"] for name, row in cues.items()} == {
        name: extra_cues[name] for name in cues
    }


def test_single_tool_control_has_no_cue_and_names_are_u_s_x_sx():
    rendered = render_tools(model_facing_tools([_echo_function()], "simple_python"))
    assert tuple(rendered["arms"]) == ARMS
    assert rendered["arms"]["X"] == rendered["arms"]["U"]
    assert rendered["arms"]["SX"] == rendered["arms"]["S"]
    assert rendered["x_decisions"][0]["cue"] == ""
    assert rendered["x_decisions"][0]["control"] is True
    roots = {case["id"]: case for case in load_questions("multiple")}["multiple_11"]
    compiled = compile_case(roots)
    axes = {change["function"]: change["axis"] for change in compiled["changes"] if change["arm"] == "X"}
    assert axes["math_roots_quadratic"] == "interface:numeric-array-versus-numeric-scalars"
    assert "math_sqrt" not in axes or axes.get("math_sqrt", "") == ""


def test_rate_card_peak_windows_holidays_and_published_prices():
    assert _utc(2026, 1, 5).weekday() == 0
    assert is_peak(_utc(2026, 1, 5, 1, 0))
    assert is_peak(_utc(2026, 1, 5, 3, 59))
    assert not is_peak(_utc(2026, 1, 5, 4, 0))
    assert not is_peak(_utc(2026, 1, 5, 5, 30))
    assert is_peak(_utc(2026, 1, 5, 6, 0))
    assert is_peak(_utc(2026, 1, 5, 9, 59))
    assert not is_peak(_utc(2026, 1, 5, 10, 0))
    assert not is_peak(_utc(2026, 1, 10, 2, 0))
    assert not is_peak(_utc(2026, 1, 4, 2, 0))
    assert not is_peak(_utc(2026, 1, 1, 2, 0))
    assert not is_peak(_utc(2026, 2, 16, 2, 30))
    assert not is_peak(_utc(2026, 2, 23, 2, 0))
    assert is_peak(_utc(2027, 1, 1, 2, 0))
    with pytest.raises(ValueError):
        is_peak(datetime(2026, 1, 5, 2, 0))
    off, off_band = spend_usd(cache_hit=200, cache_miss=800, output=50, at=_utc(2026, 11, 25, 12, 0))
    expected = (
        Decimal(200) * Decimal("0.003")
        + Decimal(800) * Decimal("0.15")
        + Decimal(50) * Decimal("0.6")
    ) / Decimal(1_000_000)
    assert off_band == "off_peak"
    assert off == expected.quantize(Decimal("0.000000000001"))
    peak, peak_band = spend_usd(cache_hit=200, cache_miss=800, output=50, at=_utc(2026, 1, 5, 2, 30))
    assert peak_band == "peak"
    assert peak == off * 2


def test_request_body_sets_thinking_and_omits_max_tokens():
    off = request_body([{"role": "user", "content": "hi"}], [{"type": "function"}], "off")
    on = request_body([{"role": "user", "content": "hi"}], [], "on")
    assert off["model"] == REQUEST_MODEL == "deepseek-flash"
    assert off["model"] != RETIRED_ROUTE_ALIAS
    assert off["thinking"] == {"type": "disabled"}
    assert on["thinking"] == {"type": "enabled"}
    assert "max_tokens" not in off and "max_tokens" not in on
    assert "tools" in off and "tools" not in on
    assert off["temperature"] == 0.001


def test_execution_config_separates_snippet_memory_and_long_context(tmp_path):
    hidden = execution_config(
        {"id": "web_search_no_snippet_0", "category": "web_search_no_snippet", "prereq": False},
        tmp_path,
    )
    shown = execution_config(
        {"id": "web_search_base_0", "category": "web_search_base", "prereq": False},
        tmp_path,
    )
    assert hidden["initial_config"]["WebSearchAPI"]["show_snippet"] is False
    assert shown["initial_config"]["WebSearchAPI"]["show_snippet"] is True
    memory = execution_config(
        {
            "id": "memory_kv_prereq_0-student-0",
            "category": "memory_kv",
            "prereq": True,
            "scenario": "student",
            "involved_classes": ["MemoryAPI_kv"],
        },
        tmp_path,
    )
    assert memory["initial_config"]["MemoryAPI_kv"]["test_category"] == "memory_kv_prereq"
    # Pinned MemoryAPI._prepare_snapshot joins this with "/", so it must stay a Path.
    assert memory["initial_config"]["MemoryAPI_kv"]["model_result_dir"] == tmp_path
    assert isinstance(memory["initial_config"]["MemoryAPI_kv"]["model_result_dir"], Path)
    long_context = execution_config(
        {"id": "multi_turn_long_context_0", "category": "multi_turn_long_context", "prereq": False, "initial_config": {}},
        tmp_path,
    )
    assert long_context["long_context"] is True
    memory_case = {
        "id": "memory_kv_0-student-0",
        "category": "memory_kv",
        "question": [[{"role": "user", "content": "Remember this."}]],
        "prereq": False,
    }
    assert turn_messages(memory_case, 0)[0] == {"role": "system", "content": AGENTIC_SYSTEM_PROMPT}
    prereq = dict(memory_case, prereq=True)
    assert turn_messages(prereq, 0)[0]["role"] == "user"


def test_result_paths_match_the_official_groups():
    assert result_relative("simple_python_0", "off", "U") == Path(
        "result/deepseek-flash-thinking-off-U/non_live/BFCL_v4_simple_python_result.json"
    )
    assert result_relative("memory_kv_0-customer-0", "on", "SX") == Path(
        "result/deepseek-flash-thinking-on-SX/agentic/memory/kv/BFCL_v4_memory_kv_result.json"
    )
    assert result_relative("web_search_no_snippet_3", "off", "X") == Path(
        "result/deepseek-flash-thinking-off-X/agentic/BFCL_v4_web_search_no_snippet_result.json"
    )
    paths = {
        (thinking, arm): result_relative("multiple_0", thinking, arm)
        for thinking in ("off", "on")
        for arm in ARMS
    }
    assert len(set(paths.values())) == 8
    assert {path.name for path in paths.values()} == {"BFCL_v4_multiple_result.json"}
    assert paths[("off", "U")] != paths[("off", "S")]
    assert result_group("memory_kv") == "agentic/memory/kv"
    assert result_group("memory_kv_prereq") == "agentic/memory/kv"
    assert category_from_id("memory_kv_0-customer-0") == "memory_kv"
    assert category_from_id("web_search_no_snippet_3") == "web_search_no_snippet"
    text = evaluate_instructions()
    assert "bfcl evaluate" in text
    assert "not by a scorer in this repo" in text
    assert "not official settlement" in text
    assert "BFCL_v4_<category>_result.json" in text
    for thinking in ("off", "on"):
        for arm in ARMS:
            name = f"deepseek-flash-thinking-{thinking}-{arm}"
            assert (
                f"--model {name} --test-category <category> --result-dir <out>/result --partial-eval"
                in text
            )
    assert "--model deepseek-flash-thinking-off --test-category" not in text
    assert "--model deepseek-flash-thinking-on --test-category" not in text
    note = (study_dir() / "NOTE.md").read_text(encoding="utf-8")
    assert (
        "result/deepseek-flash-thinking-<off|on>-<U|S|X|SX>/<group>/BFCL_v4_<category>_result.json"
        in note
    )
    assert "result/deepseek-flash-thinking-<off|on>/<group>/BFCL_v4_<category>_result.json" not in note


def test_two_arms_do_not_append_into_the_same_result_file(tmp_path):
    case_id = "multiple_0"
    unmodified = append_result(
        tmp_path,
        case_id,
        "off",
        {"id": case_id, "result": [{"echo": "{\"value\": 1}"}]},
        "U",
    )
    edited = append_result(
        tmp_path,
        case_id,
        "off",
        {"id": case_id, "result": "different"},
        "S",
    )
    assert unmodified != edited
    assert unmodified.name == edited.name == "BFCL_v4_multiple_result.json"
    assert json.loads(unmodified.read_text(encoding="utf-8"))["result"] != json.loads(
        edited.read_text(encoding="utf-8")
    )["result"]
    assert len(unmodified.read_text(encoding="utf-8").splitlines()) == 1
    assert len(edited.read_text(encoding="utf-8").splitlines()) == 1
    again = append_result(
        tmp_path,
        case_id,
        "on",
        {"id": case_id, "result": "later"},
        "U",
    )
    assert again != unmodified
    assert len(unmodified.read_text(encoding="utf-8").splitlines()) == 1

    case = _simple_case()
    slots = [
        slot
        for slot in build_slots([case])
        if slot["thinking"] == "off" and slot["arm"] in {"U", "X"}
    ]
    script = _Scripted([_tool_response("echo"), _content_response("plain")])
    execute(
        [case],
        slots,
        tmp_path / "run",
        script,
        ceiling_usd=Decimal("1"),
        thinking_modes=("off",),
        clock=lambda: _utc(2026, 11, 25, 12, 0),
    )
    u_lines = (
        tmp_path / "run" / result_relative(case["id"], "off", "U")
    ).read_text(encoding="utf-8").splitlines()
    x_lines = (
        tmp_path / "run" / result_relative(case["id"], "off", "X")
    ).read_text(encoding="utf-8").splitlines()
    assert len(u_lines) == 1 and len(x_lines) == 1
    assert json.loads(u_lines[0])["result"] != json.loads(x_lines[0])["result"]
    assert not (
        tmp_path / "run/result/deepseek-flash-thinking-off/non_live/BFCL_v4_simple_python_result.json"
    ).exists()
    assert not (tmp_path / "run" / result_relative(case["id"], "off", "S")).exists()
    assert not (tmp_path / "run" / result_relative(case["id"], "off", "SX")).exists()


def test_runner_persists_scorable_output_usage_and_spend(tmp_path):
    case = _simple_case()
    slots = build_slots([case])
    script = _Scripted([_tool_response() for _ in slots])
    result = execute(
        [case],
        slots,
        tmp_path,
        script,
        ceiling_usd=Decimal("1"),
        thinking_modes=("off", "on"),
        clock=lambda: _utc(2026, 11, 25, 12, 0),
    )
    assert result["complete"] is True
    assert result["status"] == "complete"
    assert result["official_settlement"] is False
    assert result["max_tokens_sent"] is False
    lines = (tmp_path / result_relative("simple_python_0", "off", "U")).read_text(encoding="utf-8").splitlines()
    on_lines = (tmp_path / result_relative("simple_python_0", "on", "U")).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1 and len(on_lines) == 1
    for arm in ARMS:
        for thinking in ("off", "on"):
            arm_lines = (tmp_path / result_relative("simple_python_0", thinking, arm)).read_text(encoding="utf-8").splitlines()
            assert len(arm_lines) == 1
            assert json.loads(arm_lines[0])["id"] == "simple_python_0"
    assert not (
        tmp_path / "result/deepseek-flash-thinking-off/non_live/BFCL_v4_simple_python_result.json"
    ).exists()
    entry = json.loads(lines[0])
    assert entry["id"] == "simple_python_0"
    assert entry["result"] == [{"echo": "{\"value\": 1}"}]
    bills = [json.loads(line) for line in (tmp_path / "bills.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(bills) == 8
    assert bills[0]["prompt_tokens"] == 1000
    assert bills[0]["prompt_cache_hit_tokens"] == 200
    assert bills[0]["prompt_cache_miss_tokens"] == 800
    assert bills[0]["output_tokens"] == 50
    assert bills[0]["reasoning_tokens"] == 12
    assert Decimal(bills[0]["usd"]) == _off_peak_cost()
    assert Decimal(bills[-1]["running_usd"]) == _off_peak_cost() * 8
    spend = json.loads((tmp_path / "spend.json").read_text(encoding="utf-8"))
    assert spend["complete"] is True
    assert Decimal(spend["running_usd"]) == Decimal(bills[-1]["running_usd"])
    assert spend["rate_card"]["off_peak"] == {"cache_hit": "0.003", "cache_miss": "0.15", "output": "0.6"}
    sidecar = json.loads((tmp_path / "model_outputs/deepseek-flash-thinking-off/U/simple_python_0.json").read_text(encoding="utf-8"))
    assert sidecar["scorable"] is True
    assert sidecar["steps"][0]["reasoning_content"] == "because"
    assert [body["thinking"]["type"] for body in script.bodies] == ["disabled"] * 4 + ["enabled"] * 4
    assert [body["model"] for body in script.bodies] == ["deepseek-flash"] * 8
    assert all("max_tokens" not in body for body in script.bodies)
    assert script.bodies[0]["messages"][0]["content"] == "What is 1?"


def test_ceiling_stops_later_sends_and_partial_is_not_complete(tmp_path):
    case = _simple_case()
    slots = [slot for slot in build_slots([case]) if slot["thinking"] == "off"][:2]
    script = _Scripted([_tool_response(), _tool_response()])
    result = execute(
        [case],
        slots,
        tmp_path,
        script,
        ceiling_usd=_off_peak_cost(),
        thinking_modes=("off",),
        clock=lambda: _utc(2026, 11, 25, 12, 0),
    )
    assert result["complete"] is False
    assert result["status"] == "incomplete"
    assert result["reason"] == "ceiling"
    assert result["slots_sent"] == 1
    assert len(script.bodies) == 1
    lines = (tmp_path / result_relative("simple_python_0", "off", "U")).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert not (tmp_path / result_relative("simple_python_0", "off", "S")).exists()
    assert not (tmp_path / "model_outputs/deepseek-flash-thinking-off/S/simple_python_0.json").exists()
    spend = json.loads((tmp_path / "spend.json").read_text(encoding="utf-8"))
    assert spend["complete"] is False
    assert spend["status"] == "incomplete"
    assert result["partial_presented_as_complete"] is False


def test_missing_usage_does_not_invent_a_bill_or_a_result(tmp_path):
    case = _simple_case()
    payload = _tool_response()
    del payload["usage"]
    script = _Scripted([payload])
    result = execute(
        [case],
        build_slots([case])[:1],
        tmp_path,
        script,
        ceiling_usd=Decimal("1"),
        thinking_modes=("off",),
        clock=lambda: _utc(2026, 11, 25, 12, 0),
    )
    assert result["complete"] is False
    assert result["reason"] == "usage_missing"
    assert result["uncertain_attempts"] == [1]
    assert result["slots_sent"] == 0
    assert not (tmp_path / "bills.jsonl").exists()
    assert not list(tmp_path.rglob("*_result.json"))
    spend = json.loads((tmp_path / "spend.json").read_text(encoding="utf-8"))
    assert spend["running_usd"] == "0"
    assert spend["complete"] is False


def test_absent_cache_split_is_billed_as_all_miss_and_named(tmp_path):
    case = _simple_case()
    payload = _content_response()
    del payload["usage"]["prompt_cache_hit_tokens"]
    del payload["usage"]["prompt_cache_miss_tokens"]
    script = _Scripted([payload])
    execute(
        [case],
        build_slots([case])[:1],
        tmp_path,
        script,
        ceiling_usd=Decimal("1"),
        thinking_modes=("off",),
        clock=lambda: _utc(2026, 11, 25, 12, 0),
    )
    bill = json.loads((tmp_path / "bills.jsonl").read_text(encoding="utf-8"))
    assert bill["cache_fields"] == "assumed_all_miss"
    assert bill["prompt_cache_hit_tokens"] == 0
    assert bill["prompt_cache_miss_tokens"] == 1000
    assert bill["reasoning_tokens"] == 12
    amount, _band = spend_usd(cache_hit=0, cache_miss=1000, output=50, at=_utc(2026, 11, 25, 12, 0))
    assert Decimal(bill["usd"]) == amount


def test_trajectory_persists_nested_results_and_holdout_prompt(tmp_path):
    held = _echo_function()
    held["name"] = "sort"
    case = {
        "id": "multi_turn_long_context_0",
        "category": "multi_turn_long_context",
        "question": [
            [{"role": "user", "content": "list the files"}],
            [],
        ],
        "function": [_echo_function()],
        "held_out": {"1": [held]},
        "involved_classes": ["GorillaFileSystem"],
        "initial_config": {"GorillaFileSystem": {"root": "/tmp"}},
        "prereq": False,
    }

    class Executor:
        def __init__(self):
            self.calls = []

        def initialize(self, case, config):
            self.calls.append(([], config["instance_name"], config["long_context"]))
            return {"GorillaFileSystem": object()}

        def execute_calls(self, strings, case, config):
            self.calls.append((strings, config["instance_name"], config["long_context"]))
            return ["listed"]

    executor = Executor()
    script = _Scripted([_tool_response(), _content_response("done"), _content_response("next")])
    result = execute(
        [case],
        build_slots([case])[:1],
        tmp_path,
        script,
        ceiling_usd=Decimal("1"),
        thinking_modes=("off",),
        clock=lambda: _utc(2026, 11, 25, 12, 0),
        executor=executor,
    )
    assert result["complete"] is True
    assert executor.calls[0][0] == [] and executor.calls[1][0] == ["echo(value=1)"]
    entry = json.loads(
        (tmp_path / result_relative("multi_turn_long_context_0", "off", "U")).read_text(encoding="utf-8")
    )
    assert entry["result"][0][0] == [{"echo": "{\"value\": 1}"}]
    assert entry["result"][0][1] == "done"
    assert entry["result"][1] == ["next"]
    assert entry["input_token_count"] == [[1000, 1000], [1000]]
    assert executor.calls[0][1] == executor_instance_name("off", "U") == "deepseek_flash_thinking_off_U"
    assert executor.calls[0][2] is True
    assert script.bodies[1]["messages"][1]["reasoning_content"] == "because"
    assert script.bodies[2]["messages"][-1] == {"role": "user", "content": HOLDOUT_USER_PROMPT}
    assert any(tool["function"]["name"] == "sort" for tool in script.bodies[2]["tools"])
    assert not any(tool["function"]["name"] == "sort" for tool in script.bodies[0]["tools"])


def _bfcl_instance_key(model_name: str, test_entry_id: str, class_name: str) -> str:
    """Same key as pinned gorilla ``execute_multi_turn_func_call`` at 6ea57973."""
    instance_name = f"{model_name}_{test_entry_id}_{class_name}_instance"
    return re.sub(r"[-./:]", "_", instance_name)


def _snapshot_file(model_result_dir: str, case_id: str, scenario: str) -> Path:
    """Same file as pinned ``MemoryAPI._prepare_snapshot`` at 6ea57973."""
    category = category_from_id(case_id)
    return Path(model_result_dir) / result_group(category) / "memory_snapshot" / f"{scenario}_final.json"


def test_trajectory_arms_do_not_share_instances_or_snapshots(tmp_path):
    memory = {
        "id": "memory_kv_0-customer-0",
        "category": "memory_kv",
        "question": [[{"role": "user", "content": "Remember this."}]],
        "function": [_echo_function()],
        "involved_classes": ["MemoryAPI_kv"],
        "scenario": "customer",
        "prereq": False,
    }
    multi = {
        "id": "multi_turn_base_0",
        "category": "multi_turn_base",
        "question": [[{"role": "user", "content": "list the files"}]],
        "function": [_echo_function()],
        "involved_classes": ["GorillaFileSystem"],
        "initial_config": {},
        "prereq": False,
    }
    web = {
        "id": "web_search_base_0",
        "category": "web_search_base",
        "question": [[{"role": "user", "content": "search"}]],
        "function": [_echo_function()],
        "involved_classes": ["WebSearchAPI"],
        "prereq": False,
    }
    cases = [memory, multi, web]
    slots = [
        slot
        for slot in build_slots(cases)
        if slot["thinking"] == "off" and slot["arm"] in {"U", "S"}
    ]
    assert [(slot["case_id"], slot["arm"]) for slot in slots] == [
        ("memory_kv_0-customer-0", "U"),
        ("memory_kv_0-customer-0", "S"),
        ("multi_turn_base_0", "S"),
        ("multi_turn_base_0", "U"),
        ("web_search_base_0", "U"),
        ("web_search_base_0", "S"),
    ]

    class PinKeyedExecutor:
        """Reuse rule from the pinned executor: one globals() entry per key."""

        def __init__(self):
            self.globals = {}
            self.trace = []

        def initialize(self, case, config):
            self.execute_calls([], case, config)
            return {config["involved_classes"][0]: self.globals[self.trace[-1]["key"]]}

        def memory_prompt(self, question, case, instances):
            return question

        def execute_calls(self, strings, case, config):
            class_name = config["involved_classes"][0]
            key = _bfcl_instance_key(config["instance_name"], case["id"], class_name)
            created = key not in self.globals
            if created:
                self.globals[key] = {"loaded_scenario": True, "instance_name": config["instance_name"]}
            self.trace.append({
                "key": key,
                "created": created,
                "instance": self.globals[key],
                "instance_name": config["instance_name"],
                "initial_config": config["initial_config"],
            })
            return ["stored"]

    executor = PinKeyedExecutor()
    responses = []
    for _slot in slots:
        responses.extend([_tool_response(), _tool_response(), _content_response("done")])
    result = execute(
        cases,
        slots,
        tmp_path,
        _Scripted(responses),
        ceiling_usd=Decimal("1"),
        thinking_modes=("off",),
        clock=lambda: _utc(2026, 11, 25, 12, 0),
        executor=executor,
    )
    assert result["complete"] is True
    assert result["official_settlement"] is False
    by_key: dict[str, list[dict]] = {}
    for event in executor.trace:
        by_key.setdefault(event["key"], []).append(event)
    assert len(by_key) == 6
    for events in by_key.values():
        assert events[0]["created"] is True
        assert len(events) == 3
        assert all(event["created"] is False for event in events[1:])
        assert all(event["instance"] is events[0]["instance"] for event in events[1:])
    for case, class_name in (
        (memory, "MemoryAPI_kv"),
        (multi, "GorillaFileSystem"),
        (web, "WebSearchAPI"),
    ):
        unmodified = executor_instance_name("off", "U")
        edited = executor_instance_name("off", "S")
        assert unmodified == "deepseek_flash_thinking_off_U"
        assert edited == "deepseek_flash_thinking_off_S"
        u_key = _bfcl_instance_key(unmodified, case["id"], class_name)
        s_key = _bfcl_instance_key(edited, case["id"], class_name)
        assert u_key != s_key
        assert by_key[u_key][0]["instance"] is not by_key[s_key][0]["instance"]
        shared = _bfcl_instance_key("deepseek_flash_thinking_off", case["id"], class_name)
        assert u_key != shared and s_key != shared
    u_memory = next(
        event for event in executor.trace
        if event["instance_name"].endswith("_U") and "MemoryAPI_kv" in event["initial_config"]
    )
    s_memory = next(
        event for event in executor.trace
        if event["instance_name"].endswith("_S") and "MemoryAPI_kv" in event["initial_config"]
    )
    u_root = Path(u_memory["initial_config"]["MemoryAPI_kv"]["model_result_dir"])
    s_root = Path(s_memory["initial_config"]["MemoryAPI_kv"]["model_result_dir"])
    assert u_root == tmp_path / "result" / "deepseek-flash-thinking-off-U"
    assert s_root == tmp_path / "result" / "deepseek-flash-thinking-off-S"
    u_snapshot = _snapshot_file(str(u_root), memory["id"], "customer")
    s_snapshot = _snapshot_file(str(s_root), memory["id"], "customer")
    assert u_snapshot != s_snapshot
    assert u_snapshot == (
        tmp_path
        / "result/deepseek-flash-thinking-off-U/agentic/memory/kv/memory_snapshot/customer_final.json"
    )
    assert s_snapshot.name == "customer_final.json"
    for case in cases:
        u_result = tmp_path / result_relative(case["id"], "off", "U")
        s_result = tmp_path / result_relative(case["id"], "off", "S")
        assert u_result != s_result
        assert len(u_result.read_text(encoding="utf-8").splitlines()) == 1
        assert len(s_result.read_text(encoding="utf-8").splitlines()) == 1
    assert not (tmp_path / "result/deepseek-flash-thinking-off").exists()
    help_text = evaluate_instructions()
    note = (study_dir() / "NOTE.md").read_text(encoding="utf-8")
    snapshot = (
        "result/deepseek-flash-thinking-<off|on>-<U|S|X|SX>/<group>/"
        "memory_snapshot/<scenario>_final.json"
    )
    for text in (help_text, note):
        assert snapshot in text
        assert "deepseek_flash_thinking_<off|on>_<arm>" in text
        assert "result/deepseek-flash-thinking-<off|on>/" not in text


def test_trajectory_without_executor_stops_before_a_request(tmp_path):
    case = {
        "id": "multi_turn_base_0",
        "category": "multi_turn_base",
        "question": [[{"role": "user", "content": "hi"}]],
        "function": [_echo_function()],
        "prereq": False,
    }
    script = _Scripted([_content_response()])
    result = execute(
        [case],
        build_slots([case])[:1],
        tmp_path,
        script,
        ceiling_usd=Decimal("1"),
        thinking_modes=("off",),
        clock=lambda: _utc(2026, 11, 25, 12, 0),
    )
    assert result["complete"] is False
    assert result["reason"] == "trajectory_executor_required"
    assert script.bodies == []
    assert not list(tmp_path.rglob("*_result.json"))


def test_dry_plan_does_not_send(tmp_path):
    plan = write_plan([_simple_case()], tmp_path, pilot=False)
    assert plan["status"] == "not_sent"
    assert plan["complete"] is False
    assert plan["provider_contacted"] is False
    assert plan["slots_total"] == 8
    assert not list(tmp_path.rglob("*_result.json"))
    assert not (tmp_path / "bills.jsonl").exists()


def test_live_without_authorization_exits_without_a_network_call(tmp_path, monkeypatch):
    calls = []

    def refuse(*_args, **_kwargs):
        calls.append("network")
        raise AssertionError("network")

    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    monkeypatch.setattr(
        "tool_compression.clean_start.runner.read_provider_key",
        lambda: calls.append("key") or (_ for _ in ()).throw(AssertionError("key")),
    )
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    from tool_compression.clean_start.__main__ import main

    assert main(["run", "--live", "--out", str(tmp_path)]) == 2
    assert main(["run", "--authorize-live", "--ceiling-usd", "1", "--out", str(tmp_path)]) == 2
    assert main(["run", "--pilot", "--live", "--out", str(tmp_path / "pilot")]) == 2
    assert main(["run", "--live", "--authorize-live", "--ceiling-usd", "0", "--out", str(tmp_path / "zero")]) == 2
    assert calls == []
    assert not (tmp_path / "run.json").exists()


def test_authorized_command_uses_the_injected_transport(tmp_path, monkeypatch):
    from tool_compression.clean_start.__main__ import main

    script = _Scripted([_content_response("ok")])
    monkeypatch.setattr("tool_compression.clean_start.__main__._select_cases", lambda _pilot, _prereqs: [_simple_case()])
    monkeypatch.setattr(
        "tool_compression.clean_start.__main__.build_slots",
        lambda cases, modes: build_slots(cases, modes)[:1],
    )
    monkeypatch.setattr("tool_compression.clean_start.__main__.authorized_transport", lambda: script)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "placeholder-not-a-key")
    assert main([
        "run", "--live", "--authorize-live", "--ceiling-usd", "1", "--out", str(tmp_path),
    ]) == 2
    assert script.bodies == []
    code = main([
        "run", "--live", "--authorize-live", "--thinking", "off", "--ceiling-usd", "1", "--out", str(tmp_path),
    ])
    assert code == 0
    assert script.bodies and script.bodies[0]["model"] == "deepseek-flash"
    assert [body["thinking"]["type"] for body in script.bodies] == ["disabled"]
    assert (tmp_path / "bills.jsonl").is_file()
    assert list(tmp_path.rglob("*_result.json"))
    again = _Scripted([_content_response("ok")])
    monkeypatch.setattr("tool_compression.clean_start.__main__.authorized_transport", lambda: again)
    assert main([
        "run", "--live", "--authorize-live", "--thinking", "off", "--ceiling-usd", "1", "--out", str(tmp_path),
    ]) == 2
    assert again.bodies == []


UNCHANGED_PILOT = {
    "multiple": ["multiple_142", "multiple_66", "multiple_77"],
    "parallel_multiple": ["parallel_multiple_191", "parallel_multiple_150", "parallel_multiple_192"],
    "live_multiple": ["live_multiple_943-196-1", "live_multiple_988-219-0", "live_multiple_447-144-7"],
    "live_parallel_multiple": [
        "live_parallel_multiple_3-2-1",
        "live_parallel_multiple_8-7-0",
        "live_parallel_multiple_20-17-0",
    ],
    "multi_turn_base": ["multi_turn_base_120", "multi_turn_base_86", "multi_turn_base_198"],
    "multi_turn_miss_func": ["multi_turn_miss_func_189", "multi_turn_miss_func_95", "multi_turn_miss_func_167"],
    "multi_turn_miss_param": ["multi_turn_miss_param_187", "multi_turn_miss_param_78", "multi_turn_miss_param_31"],
    "multi_turn_long_context": [
        "multi_turn_long_context_140",
        "multi_turn_long_context_6",
        "multi_turn_long_context_31",
    ],
    "memory_kv": ["memory_kv_146-notetaker-16", "memory_kv_58-finance-3", "memory_kv_7-customer-7"],
    "memory_vector": ["memory_vector_107-student-27", "memory_vector_90-student-10", "memory_vector_123-student-43"],
    "memory_rec_sum": ["memory_rec_sum_32-healthcare-2", "memory_rec_sum_121-student-41", "memory_rec_sum_62-finance-7"],
}
REMOVED_WEB_PILOT = (
    "web_search_base_37",
    "web_search_base_46",
    "web_search_base_58",
    "web_search_no_snippet_83",
    "web_search_no_snippet_92",
    "web_search_no_snippet_58",
)


def test_pilot_draw_is_reproducible_and_renders_match(tmp_path):
    first = build_draw()
    assert build_draw() == first
    assert first["seed"] == PILOT_SEED == 20261125
    assert first["k"] == PILOT_K == 3
    assert first["official_settlement"] is False
    committed = json.loads((study_dir() / "pilot" / "draw.json").read_text(encoding="utf-8"))
    assert committed == first
    scope = load_scope()
    assert first["categories"] == scope["keep"]
    assert len(first["rows"]) == 41
    by_category: dict[str, list[str]] = {}
    questions = {
        category: {case["id"]: case for case in in_scope_questions(category)}
        for category in first["categories"]
    }
    for row in first["rows"]:
        by_category.setdefault(row["category"], []).append(row["case_id"])
        assert "_prereq" not in row["case_id"]
        assert row["category"] not in scope["drop"]
        assert row["case_id"] in scope["in_scope_ids"][row["category"]]
        case = questions[row["category"]][row["case_id"]]
        document = render_document(case)
        path = study_dir() / "pilot" / "rendered" / row["category"] / f"{row['case_id']}.json"
        assert json.loads(path.read_text(encoding="utf-8")) == document
        assert set(document["arms"]) == set(ARMS)
        dumped = path.read_text(encoding="utf-8")
        assert AGENTIC_SYSTEM_PROMPT not in dumped
        for turn in case["question"]:
            for message in turn:
                content = message.get("content")
                if isinstance(content, str) and len(content) >= 40:
                    assert content not in dumped
    for item in first["draws"]:
        ids = by_category[item["category"]]
        assert len(ids) == len(set(ids)) == item["frozen"]
        if item["method"] == "sample":
            assert item["population"] >= 3 and item["frozen"] == 3
        else:
            assert item["method"] == "all_in_scope_under_k"
            assert item["frozen"] == item["population"] < 3
    assert by_category["live_parallel"] == ["live_parallel_6-3-0", "live_parallel_7-3-1"]
    for category, ids in UNCHANGED_PILOT.items():
        assert by_category[category] == ids
    drawn_ids = [row["case_id"] for row in first["rows"]]
    assert set(REMOVED_WEB_PILOT).isdisjoint(drawn_ids)
    assert "web_search_base" not in by_category and "web_search_no_snippet" not in by_category
    note = (study_dir() / "NOTE.md").read_text(encoding="utf-8")
    for row in first["rows"]:
        assert row["case_id"] in note
    assert "20261125" in note
    assert scope["unscope_package"]["tip"] in note
    assert "simple_python_212" not in note
    rendered_root = study_dir() / "pilot" / "rendered"
    on_disk = {path.stem for path in rendered_root.rglob("*.json")}
    assert on_disk == {row["case_id"] for row in first["rows"]}
    for category in scope["drop"]:
        assert not (rendered_root / category).exists()


def test_coverage_matches_the_committed_limitations_and_names_are_consistent():
    record = coverage()
    committed = json.loads((study_dir() / "limitations.json").read_text(encoding="utf-8"))
    assert committed == record
    assert record["official_settlement"] is False
    assert record["unsendable"] == 0
    assert record["in_scope_questions"] == 3127
    scope = load_scope()
    assert set(record["categories"]) == set(scope["keep"])
    assert "simple_java" not in record["categories"]
    assert "parallel" not in record["categories"]
    assert "irrelevance" not in record["categories"]
    assert record["categories"]["live_parallel"]["questions"] == 2
    assert record["categories"]["live_parallel"]["s_cases_different_from_u"] == 2
    assert record["categories"]["live_parallel"]["x_cases_different_from_u"] == 0
    assert record["categories"]["live_irrelevance"]["questions"] == 372
    assert "miss_func_holdout_absent_from_initial_tools" in record["categories"]["multi_turn_miss_func"]["limitations"]
    assert "memory_prereq_required_for_a_full_score" in record["categories"]["memory_kv"]["limitations"]
    assert "excluded_function_left_in_catalogue" in record["categories"]["multi_turn_base"]["limitations"]
    assert record["categories"]["memory_kv"]["x_cases_different_from_u"] == 155
    texts = [path.read_text(encoding="utf-8") for path in (REPO / "src" / "tool_compression" / "clean_start").rglob("*.py")]
    texts.append((study_dir() / "NOTE.md").read_text(encoding="utf-8"))
    texts.append((study_dir() / "limitations.json").read_text(encoding="utf-8"))
    texts.append((study_dir() / "pilot" / "draw.json").read_text(encoding="utf-8"))
    for text in texts:
        assert LEGACY_ARM.search(text) is None


def test_package_command_forwards_and_dry_pilot_stays_offline(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(urllib.request, "urlopen", lambda *_a, **_k: calls.append("url") or (_ for _ in ()).throw(AssertionError("url")))
    from tool_compression.__main__ import main

    assert main(["clean-start", "manifest"]) == 0
    code = main(["clean-start", "run", "--pilot", "--out", str(tmp_path)])
    assert code == 0
    plan = json.loads((tmp_path / "run.json").read_text(encoding="utf-8"))
    assert plan["status"] == "not_sent"
    assert plan["provider_contacted"] is False
    assert plan["complete"] is False
    assert plan["slots_total"] == len(build_draw()["rows"]) * 2 * 4 == 41 * 8
    assert calls == []


def test_scope_rule_census_and_runner_use_multi_tool_questions_only():
    fresh = build_scope_document()
    assert fresh == load_scope()
    assert fresh["official_settlement"] is False
    assert fresh["official_simple_multi_tool_ids"] == []
    assert fresh["scoring_questions"] == 5106
    assert fresh["in_scope_questions"] == 3127
    assert fresh["out_of_scope_questions"] == 1979
    assert fresh["drop"] == [
        "simple_python",
        "simple_java",
        "simple_javascript",
        "parallel",
        "irrelevance",
        "live_simple",
        "web_search_base",
        "web_search_no_snippet",
    ]
    assert fresh["unscope_package"]["pull_request"] == 24
    assert fresh["unscope_package"]["tip"] == "c1df4bbf439151abad2ed79b103d401a61443412"
    assert fresh["unscope_package"]["pilot_cases"] == 66
    assert fresh["unscope_package"]["scoring_categories"] == len(ALL_SCORING_CATEGORIES) == 22
    by_category = {row["category"]: row for row in fresh["census"]}
    assert list(by_category) == list(ALL_SCORING_CATEGORIES)
    for category in OFFICIAL_SIMPLE_CATEGORIES:
        row = by_category[category]
        assert row["questions"] == row["one_tool"]
        assert row["multi_tool"] == 0 and row["zero_tool"] == 0
        assert row["disposition"] == "dropped" and row["in_scope"] == 0
    assert by_category["parallel"]["one_tool"] == 200 and by_category["parallel"]["disposition"] == "dropped"
    assert by_category["irrelevance"]["one_tool"] == 240 and by_category["irrelevance"]["disposition"] == "dropped"
    assert by_category["parallel_multiple"]["median_tools"] == 2.5
    assert by_category["live_parallel"]["in_scope"] == 2
    assert by_category["live_irrelevance"]["zero_tool"] == 4
    assert by_category["live_irrelevance"]["one_tool"] == 508
    assert by_category["live_irrelevance"]["multi_tool"] == 372
    assert by_category["live_relevance"]["one_tool"] == 5
    assert by_category["live_relevance"]["multi_tool"] == 11
    assert fresh["memory_prerequisites"]["in_study_population"] is False
    assert fresh["memory_prerequisites"]["backends"]["memory_kv"]["conversations"] == 37
    assert fresh["memory_prerequisites"]["backends"]["memory_kv"]["min_tools"] == 15
    empty = next(row for row in fresh["surprises"] if row["kind"] == "empty_loaded_catalogue")
    assert empty["ids"] == [
        "live_irrelevance_120-9-0",
        "live_irrelevance_121-9-1",
        "live_irrelevance_122-9-2",
        "live_irrelevance_123-9-3",
    ]
    for example in fresh["checked_examples"]:
        case = next(item for item in load_questions(example["category"]) if item["id"] == example["id"])
        compiled = compile_case(case)
        assert len(compiled["arms"]["U"]) == example["tools"] == u_tool_count(case)
        assert question_in_scope(case) is example["in_scope"]
    echo_b = _echo_function()
    echo_b["name"] = "echo_b"
    two_tools = [_echo_function(), echo_b]
    simple = {
        "id": "simple_python_synthetic",
        "category": "simple_python",
        "function": two_tools,
        "prereq": False,
    }
    assert u_tool_count(simple) == 2
    assert question_in_scope(simple) is False
    multiple = dict(simple, id="multiple_synthetic", category="multiple")
    assert question_in_scope(multiple) is True
    assert question_in_scope(dict(multiple, function=[_echo_function()])) is False
    held = load_questions("multi_turn_miss_func")[0]
    assert u_tool_count(held) == len(held["function"]) > 1
    assert "sort" not in [doc.get("name") for doc in held["function"]]
    assert question_in_scope(held) is True
    prereq = load_prereqs("memory_kv")[0]
    assert prereq["prereq"] is True and u_tool_count(prereq) == 15
    assert question_in_scope(prereq) is False
    assert (bfcl_root() / "prompts" / "BFCL_v4_simple_python.json").is_file()
    assert (bfcl_root() / "prompts" / "BFCL_v4_parallel.json").is_file()
    assert (bfcl_root() / "prompts" / "BFCL_v4_irrelevance.json").is_file()
    for row in fresh["mixed"]:
        population = [case["id"] for case in load_questions(row["category"])]
        chosen = fresh["in_scope_ids"][row["category"]]
        assert set(row["out_of_scope_ids"]).isdisjoint(chosen)
        assert set(row["out_of_scope_ids"]) | set(chosen) == set(population)
        assert len(chosen) == row["in_scope"]
    from tool_compression.clean_start.__main__ import _select_cases

    pilot = _select_cases(True)
    assert [case["id"] for case in pilot] == [row["case_id"] for row in build_draw()["rows"]]
    assert all(not case.get("prereq") for case in pilot)
    assert {case["category"] for case in pilot}.isdisjoint(fresh["drop"])
    full = _select_cases(False)
    prereqs = [case for case in full if case.get("prereq")]
    scoring = [case for case in full if not case.get("prereq")]
    assert len(prereqs) == 37 * 3
    assert {case["category"] for case in prereqs} == {"memory_kv", "memory_vector", "memory_rec_sum"}
    assert [case["id"] for case in scoring] == [
        case_id
        for category in fresh["keep"]
        for case_id in fresh["in_scope_ids"][category]
    ]
    assert all(case["category"] not in fresh["drop"] for case in scoring)
    assert all("_prereq" not in case_id for ids in fresh["in_scope_ids"].values() for case_id in ids)
    text = evaluate_instructions()
    assert "--test-category all_scoring" not in text
    assert "Do not pass all_scoring." in text
    for category in fresh["keep"] + fresh["drop"]:
        assert category in text
    note = (study_dir() / "NOTE.md").read_text(encoding="utf-8")
    assert "Study population" in note
    assert "3127" in note
    web = next(case for case in load_questions("web_search_base") if case["id"] == "web_search_base_0")
    assert u_tool_count(web) == 2
    assert question_in_scope(web) is False
    assert "web_search_base" not in fresh["in_scope_ids"]
    assert "web_search_no_snippet" not in fresh["in_scope_ids"]
    assert "PR #24" in note
