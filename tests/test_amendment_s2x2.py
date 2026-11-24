"""Offline S2/X2/SX2 amendment. No provider call and no question."""

import json
from pathlib import Path

import pytest

from tool_compression.__main__ import main
from tool_compression.amendment_bundle import GCD_CUE, _fixture_errors, check, edit_case
from tool_compression.amendment_s2 import edit_tool

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
