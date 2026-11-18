"""TSCG catalogue unwrap. No network, no provider key, and no live model call."""

from copy import deepcopy
from pathlib import Path

import pytest

from tool_compression.config import DEFAULT_CONFIG
from tool_compression.evaluation import prepare_case
from tool_compression.external import compress_external_catalogues
from tool_compression.implementations import ExternalSnapshot, reference_implementations
from tool_compression.prepare import convert_record
from tool_compression.runner import build_plans, prepare_study_cases
from tool_compression.validate import catalogue_violations


class Words:
    name = "words"

    def count(self, text: str) -> int:
        return len(text.split())


def tool():
    return {
        "type": "function",
        "function": {
            "name": "ta",
            "description": "Hello there.",
            "parameters": {
                "type": "object",
                "properties": {
                    "n": {
                        "type": "integer",
                        "description": "count",
                        "default": 1.0,
                        "enum": [1.0, 2.5],
                    }
                },
                "required": ["n"],
            },
        },
    }


def edited_tools():
    tools = deepcopy(tool_list())
    tools[0]["function"]["description"] = "Hello."
    return tools


def tool_list():
    return [tool()]


def stub(monkeypatch, catalogs):
    def fake(tscg_root, script_path, incoming, timeout=300):
        return {"ok": True, "catalogs": catalogs}

    monkeypatch.setattr("tool_compression.external._invoke", fake)


def test_tscg_wrapper_unwraps_to_the_canonical_tools_list(monkeypatch):
    original = tool_list()
    tools = edited_tools()
    wrapper = {"ok": True, "tools": tools, "principles": ["SDM"]}
    assert catalogue_violations(original, wrapper) == ["/type"]
    stub(monkeypatch, [wrapper])
    returned = compress_external_catalogues([original], Path("tscg"), Path("script.mjs"))
    assert returned == [
        [
            {
                "type": "function",
                "function": {
                    "name": "ta",
                    "description": "Hello.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "n": {
                                "type": "integer",
                                "description": "count",
                                "default": 1,
                                "enum": [1, 2.5],
                            }
                        },
                        "required": ["n"],
                    },
                },
            }
        ]
    ]
    assert type(returned[0][0]["function"]["parameters"]["properties"]["n"]["default"]) is int
    assert type(returned[0][0]["function"]["parameters"]["properties"]["n"]["enum"][0]) is int
    assert type(returned[0][0]["function"]["parameters"]["properties"]["n"]["enum"][1]) is float
    assert catalogue_violations(original, returned[0]) == [
        "/0/function/parameters/properties/n/default",
        "/0/function/parameters/properties/n/enum/0",
    ]
    canonical = deepcopy(original)
    canonical[0]["function"]["description"] = "Hello."
    canonical[0]["function"]["parameters"]["properties"]["n"]["default"] = 1
    canonical[0]["function"]["parameters"]["properties"]["n"]["enum"][0] = 1
    assert catalogue_violations(canonical, returned[0]) == []


def test_unwrapped_catalogue_passes_the_boundary_the_wrapper_fails(monkeypatch):
    original = tool_list()
    original[0]["function"]["parameters"]["properties"]["n"]["default"] = 1
    original[0]["function"]["parameters"]["properties"]["n"]["enum"] = [1, "two"]
    tools = deepcopy(original)
    tools[0]["function"]["description"] = "Hello."
    wrapper = {"ok": True, "tools": tools, "principles": ["SDM"]}
    stub(monkeypatch, [wrapper])
    returned = compress_external_catalogues([original], Path("tscg"), Path("script.mjs"))
    messages = [{"role": "user", "content": "task"}]
    prepared = prepare_case(
        original,
        messages,
        {**reference_implementations(), "E": ExternalSnapshot(returned[0])},
        DEFAULT_CONFIG,
        Words(),
    )
    assert prepared["catalogues"]["E"] == tools
    assert prepared["structural_violations"] == []
    with pytest.raises(RuntimeError, match="description edit left the allowlisted boundary: /type"):
        prepare_case(
            original,
            messages,
            {**reference_implementations(), "E": ExternalSnapshot(wrapper)},
            DEFAULT_CONFIG,
            Words(),
        )


def test_rejected_tscg_results_are_not_treated_as_catalogues(monkeypatch):
    original = tool_list()
    cases = [
        ([{"ok": False, "error_name": "TypeError", "tools": edited_tools()}], r"result 0 is not ok \(TypeError\)"),
        ([{"ok": False}], r"result 0 is not ok \(Error\)"),
        ([{"ok": True, "principles": ["SDM"]}], "result 0 tools field is missing or not a list"),
        ([{"ok": True, "tools": {"type": "function"}, "principles": []}], "result 0 tools field is missing or not a list"),
        ([{"ok": True, "tools": "nope"}], "result 0 tools field is missing or not a list"),
        (["tools"], "result 0 is not a TSCG result"),
        (
            [{"ok": True, "tools": edited_tools(), "principles": []}, {"ok": False, "error_name": "RangeError"}],
            r"result 1 is not ok \(RangeError\)",
        ),
    ]
    for catalogs, message in cases:
        stub(monkeypatch, catalogs)
        with pytest.raises(RuntimeError, match=message):
            compress_external_catalogues([original] * len(catalogs), Path("tscg"), Path("script.mjs"))


def test_prepare_study_cases_uses_the_unwrapped_tools_list(monkeypatch):
    record = {
        "id": "multiple_8",
        "question": [[{"role": "user", "content": "task"}]],
        "function": [
            {
                "name": "alpha",
                "description": "Alpha beta gamma.",
                "parameters": {
                    "type": "dict",
                    "properties": {"city": {"type": "string", "description": "City name."}},
                    "required": ["city"],
                },
            }
        ],
    }
    study = {name: [] for name in ("multiple", "simple_python", "irrelevance")}
    study["multiple"].append(record)
    converted = convert_record(record)

    def fake(tscg_root, script_path, incoming, timeout=300):
        assert incoming == [converted]
        edited = deepcopy(converted)
        edited[0]["function"]["description"] = "Alpha."
        return {"ok": True, "catalogs": [{"ok": True, "tools": edited, "principles": ["SDM"]}]}

    monkeypatch.setattr("tool_compression.external._invoke", fake)
    cases = prepare_study_cases(
        study,
        Path("tscg"),
        Path("script.mjs"),
        ids=[("multiple", "multiple_8")],
    )
    assert [case["id"] for case in cases] == ["multiple_8"]
    external = cases[0]["catalogues"]["E"]
    assert isinstance(external, list)
    assert external[0]["function"]["description"] == "Alpha."
    assert "ok" not in external[0]
    assert set(cases[0]["catalogues"]) == {"U", "P", "I", "C", "E"}
    plans, mismatches = build_plans(cases, "stage_a")
    assert mismatches == []
    assert plans
