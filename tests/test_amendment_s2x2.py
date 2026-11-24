"""Offline S2/X2/SX2 amendment. No provider call and no question."""

import json
from pathlib import Path

import pytest

from tool_compression.__main__ import main
from tool_compression.amendment_bundle import GCD_CUE, POLYNOMIAL_CUE, _fixture_errors, check, edit_case
from tool_compression.amendment_s2 import edit_tool, suffix_only_float_removal
from tool_compression.amendment_x2 import ownership_problems, qualify_catalogue

ROOT = Path(__file__).resolve().parents[1]
U = ROOT / "docs" / "official-840" / "catalogues" / "U"


def _load(case_id: str) -> dict:
    document = json.loads((U / f"{case_id}.json").read_text(encoding="utf-8"))
    return edit_case(document["tools"], case_id, document["category"])


def test_locked_fixtures():
    ids = [
        "multiple_34",
        "multiple_35",
        "multiple_11",
        "multiple_12",
        "multiple_0",
        "simple_python_0",
        "irrelevance_0",
    ]
    cases = {case_id: _load(case_id) for case_id in ids}
    assert _fixture_errors(cases) == []
    gcd = cases["multiple_34"]["tools"]
    assert gcd["SX2"][0]["function"]["description"].encode("utf-8") == (
        gcd["S2"][0]["function"]["description"].encode("utf-8") + b" " + GCD_CUE.encode("utf-8")
    )
    assert gcd["X2"][1]["function"]["description"] == gcd["U"][1]["function"]["description"]


def test_polynomial_evidence_points_at_its_own_tool():
    case = _load("multiple_11")
    tools = case["tools"]["U"]
    rows = {row["function_name"]: row for row in case["x2_rows"]}
    polynomial = rows["math_roots_polynomial"]
    quadratic = rows["math_roots_quadratic"]
    cubic = rows["math_roots_cubic"]
    assert ownership_problems(tools, polynomial) == []
    assert ownership_problems(tools, quadratic) == []
    assert ownership_problems(tools, cubic) == []
    assert polynomial["cue"] == POLYNOMIAL_CUE
    order = tools[2]["function"]["parameters"]["properties"]["coefficients"]["description"]
    assert [item["name"] for item in polynomial["evidence"]["target"]["parameter_excerpts"]] == ["coefficients"]
    assert [item["name"] for item in polynomial["evidence"]["rival"]["parameter_excerpts"]] == ["a", "b", "c"]
    assert polynomial["evidence"]["target"]["order_support"] == order
    assert "order_support" not in polynomial["evidence"]["rival"]
    assert polynomial["evidence"]["target"]["tool_index"] == 2
    assert polynomial["evidence"]["rival"]["tool_index"] == 0
    assert quadratic["evidence"]["rival"]["order_support"] == order
    assert "order_support" not in quadratic["evidence"]["target"]
    assert [item["name"] for item in cubic["evidence"]["target"]["parameter_excerpts"]] == ["a", "b", "c", "d"]


def test_every_cue_is_owned_in_both_directions():
    ids = json.loads((ROOT / "docs" / "official-840" / "selection" / "manifest.json").read_text(encoding="utf-8"))
    problems = []
    seen = 0
    for case_id in ids["ids_in_file_order"]:
        document = json.loads((U / f"{case_id}.json").read_text(encoding="utf-8"))
        for row in qualify_catalogue(document["tools"]):
            if not row["cue"]:
                continue
            seen += 1
            problems.extend(f"{case_id} {row['function_name']}: {item}" for item in ownership_problems(document["tools"], row))
    assert seen == 30
    assert problems == []


def test_multiple_12_stays_uncued():
    case = _load("multiple_12")
    assert [row["cue"] for row in case["x2_rows"]] == ["", "", ""]
    assert [row["rival"] for row in case["x2_rows"]] == [None, None, None]


def test_suffix_only_count_is_separate_from_other_adopted_edits():
    ids = json.loads((ROOT / "docs" / "official-840" / "selection" / "manifest.json").read_text(encoding="utf-8"))
    suffix = 0
    other = 0
    changed = {}
    for case_id in ids["ids_in_file_order"]:
        document = json.loads((U / f"{case_id}.json").read_text(encoding="utf-8"))
        for tool in document["tools"]:
            _edited, rows = edit_tool(tool)
            for row in rows:
                assert "meaningful" not in row
                assert "cosmetic" not in row
                if not row["adopted"]:
                    continue
                if suffix_only_float_removal(row["original"], row["final"]):
                    suffix += 1
                    changed.setdefault(case_id, set()).add("suffix")
                else:
                    other += 1
                    changed.setdefault(case_id, set()).add("other")
    suffix_cases = sum(1 for kinds in changed.values() if kinds == {"suffix"})
    assert suffix == 373
    assert other == 56
    assert suffix + other == 429
    assert len(changed) == 230
    assert suffix_cases == 187


def test_s2_receives_one_tool():
    document = json.loads((U / "multiple_34.json").read_text(encoding="utf-8"))
    case = edit_case(document["tools"], "multiple_34", "multiple")
    alone, _rows = edit_tool(document["tools"][0])
    assert alone == case["tools"]["S2"][0]
    assert document["tools"][1]["function"]["name"] == "math_sqrt"


def test_amendment_sources_do_not_call_a_provider():
    for relative in (
        "src/tool_compression/amendment_s2.py",
        "src/tool_compression/amendment_x2.py",
        "src/tool_compression/amendment_bundle.py",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        for banned in (
            "DEEPSEEK_API_KEY",
            "OPENAI_API_KEY",
            "urlopen",
            "import tool_compression.official_840_provider",
            "import tool_compression.usx_provider",
            "from tool_compression.official_840_provider",
            "from tool_compression.usx_provider",
        ):
            assert banned not in text, relative


def test_live_flag_is_rejected():
    with pytest.raises(SystemExit) as caught:
        main(["amendment-s2x2", "--check", "--live"])
    assert caught.value.code != 0


def test_frozen_bundle_matches():
    status = check()
    assert status["passed"] is True
    assert status["cases"] == 840
