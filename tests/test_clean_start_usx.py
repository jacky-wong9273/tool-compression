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
    request_body,
    turn_messages,
    write_plan,
)
from tool_compression.clean_start.scoring import evaluate_instructions, result_relative
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
    assert edited["description"].startswith("Calculate the area of a rectangle.")
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
    assert internal["description"] == "Whether to calculate the internal angles"
    assert internal["default"] is True
    assert edited["parameters"]["properties"]["label"]["description"] == "A label. Default is true."
    assert edited["response"]["description"] == original["response"]["description"]
    alone, _rows = edit_tool(deepcopy(rendered["arms"]["U"][0]))
    assert rendered["arms"]["S"][0] == alone

    pair = {case["id"]: case for case in load_questions("multiple")}
    compiled = compile_case(pair["multiple_34"])
    cues = {change["function"]: change for change in compiled["changes"] if change["arm"] == "X"}
    assert set(cues) == {"math_gcd", "math_lcm"}
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
    assert axes["math_roots_quadratic"] == "named-coefficients-versus-ordered-array"
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
    assert memory["initial_config"]["MemoryAPI_kv"]["model_result_dir"] == str(tmp_path)
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
    assert result_relative("simple_python_0", "off") == Path(
        "result/deepseek-flash-thinking-off/non_live/BFCL_v4_simple_python_result.json"
    )
    assert result_group("memory_kv") == "agentic/memory/kv"
    assert result_group("memory_kv_prereq") == "agentic/memory/kv"
    assert category_from_id("memory_kv_0-customer-0") == "memory_kv"
    assert category_from_id("web_search_no_snippet_3") == "web_search_no_snippet"
    text = evaluate_instructions()
    assert "bfcl evaluate" in text
    assert "deepseek-flash-thinking-off" in text
    assert "not by a scorer in this repo" in text


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
        clock=lambda: _utc(2026, 11, 25, 12, 0),
    )
    assert result["complete"] is True
    assert result["status"] == "complete"
    assert result["official_settlement"] is False
    assert result["max_tokens_sent"] is False
    lines = (tmp_path / "result/deepseek-flash-thinking-off/non_live/BFCL_v4_simple_python_result.json").read_text(encoding="utf-8").splitlines()
    on_lines = (tmp_path / "result/deepseek-flash-thinking-on/non_live/BFCL_v4_simple_python_result.json").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 4 and len(on_lines) == 4
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
        clock=lambda: _utc(2026, 11, 25, 12, 0),
    )
    assert result["complete"] is False
    assert result["status"] == "incomplete"
    assert result["reason"] == "ceiling"
    assert result["slots_sent"] == 1
    assert len(script.bodies) == 1
    lines = (tmp_path / "result/deepseek-flash-thinking-off/non_live/BFCL_v4_simple_python_result.json").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
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
        clock=lambda: _utc(2026, 11, 25, 12, 0),
    )
    assert result["complete"] is False
    assert result["reason"] == "usage_missing"
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

        def execute(self, result, case, config):
            self.calls.append((result, config["instance_name"], config["long_context"]))
            return ["listed"]

    executor = Executor()
    script = _Scripted([_tool_response(), _content_response("done"), _content_response("next")])
    result = execute(
        [case],
        build_slots([case])[:1],
        tmp_path,
        script,
        ceiling_usd=Decimal("1"),
        clock=lambda: _utc(2026, 11, 25, 12, 0),
        executor=executor,
    )
    assert result["complete"] is True
    entry = json.loads(
        (tmp_path / "result/deepseek-flash-thinking-off/multi_turn/BFCL_v4_multi_turn_long_context_result.json")
        .read_text(encoding="utf-8")
    )
    assert entry["result"][0][0] == [{"echo": "{\"value\": 1}"}]
    assert entry["result"][0][1] == "done"
    assert entry["result"][1] == ["next"]
    assert entry["input_token_count"] == [[1000, 1000], [1000]]
    assert executor.calls[0][1] == "deepseek_flash_thinking_off"
    assert executor.calls[0][2] is True
    assert script.bodies[1]["messages"][1]["reasoning_content"] == "because"
    assert script.bodies[2]["messages"][-1] == {"role": "user", "content": HOLDOUT_USER_PROMPT}
    assert any(tool["function"]["name"] == "sort" for tool in script.bodies[2]["tools"])
    assert not any(tool["function"]["name"] == "sort" for tool in script.bodies[0]["tools"])


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
    monkeypatch.setattr("tool_compression.clean_start.__main__._select_cases", lambda _pilot: [_simple_case()])
    monkeypatch.setattr("tool_compression.clean_start.__main__.build_slots", lambda cases: build_slots(cases)[:1])
    monkeypatch.setattr("tool_compression.clean_start.__main__.authorized_transport", lambda: script)
    code = main([
        "run", "--live", "--authorize-live", "--ceiling-usd", "1", "--out", str(tmp_path),
    ])
    assert code == 0
    assert script.bodies and script.bodies[0]["model"] == "deepseek-flash"
    assert (tmp_path / "bills.jsonl").is_file()
    assert list(tmp_path.rglob("*_result.json"))


def test_pilot_draw_is_reproducible_and_renders_match(tmp_path):
    first = build_draw()
    assert build_draw() == first
    assert first["seed"] == PILOT_SEED == 20261125
    assert first["k"] == PILOT_K == 3
    assert first["official_settlement"] is False
    committed = json.loads((study_dir() / "pilot" / "draw.json").read_text(encoding="utf-8"))
    assert committed == first
    assert len(first["rows"]) == len(ALL_SCORING_CATEGORIES) * 3
    by_category: dict[str, list[str]] = {}
    questions = {category: {case["id"]: case for case in load_questions(category)} for category in ALL_SCORING_CATEGORIES}
    for row in first["rows"]:
        by_category.setdefault(row["category"], []).append(row["case_id"])
        assert "_prereq" not in row["case_id"]
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
    assert all(len(ids) == 3 and len(set(ids)) == 3 for ids in by_category.values())
    note = (study_dir() / "NOTE.md").read_text(encoding="utf-8")
    for row in first["rows"]:
        assert row["case_id"] in note
    assert "20261125" in note


def test_coverage_matches_the_committed_limitations_and_names_are_consistent():
    record = coverage()
    committed = json.loads((study_dir() / "limitations.json").read_text(encoding="utf-8"))
    assert committed == record
    assert record["official_settlement"] is False
    assert record["unsendable"] == 0
    java = record["categories"]["simple_java"]
    assert java["questions"] == 100 and java["sendable"] == 100
    assert "java_js_parameters_stringified_before_edit" in java["limitations"]
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
    assert plan["slots_total"] == len(ALL_SCORING_CATEGORIES) * 3 * 2 * 4
    assert calls == []
