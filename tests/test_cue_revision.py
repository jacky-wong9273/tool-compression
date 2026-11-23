"""Locks for the cue-revision pass. No model calls. The frozen pilot stays byte-identical."""

from pathlib import Path

import pytest

from tool_compression.semantic_audit import (
    file_sha256,
    load_json,
    load_package,
    package_dir,
    render_conditions,
    request_token_totals,
    saving,
    verify_cue_revision,
)
from tool_compression.__main__ import main

ROOT = package_dir()
REVISION = ROOT / "cue-revision"
OLD_POLYNOMIAL_CUE = (
    "Unlike math_roots_quadratic, which calculates the roots of a quadratic equation, "
    "this calculates the roots of a polynomial equation."
)


def test_cue_revision_locks_counts_and_frozen_bytes():
    summary = verify_cue_revision()
    assert summary["provider_called"] is False
    assert summary["frozen_record_intact"] is True
    assert summary["coverage_changed"] is False
    assert summary["cue_cases"] == 6
    assert summary["revised_cues"] == 15
    assert summary["structural_violations"] == 0
    assert summary["request_totals"] == {"U": 3363, "S": 3221, "X": 3700, "SX": 3558}
    assert summary["request_delta_vs_frozen"] == {"U": 0, "S": 0, "X": -246, "SX": -246}
    assert summary["request_delta_vs_U"] == {"S": -142, "X": 337, "SX": 195}
    tokens = load_json(REVISION / "checks" / "tokens.json")
    assert tokens["local_only"] is True
    assert tokens["provider_usage"] is False
    assert tokens["official_score"] is False
    assert tokens["shorter_is_not_success"] is True
    overall = tokens["request"]["overall"]
    for label in ("frozen", "cue_revision"):
        block = overall["saving_vs_U"][label]
        totals = overall[label]
        for condition in ("S", "X", "SX"):
            assert block[condition] == pytest.approx(saving(totals["U"], totals[condition]))
    eleven = tokens["request"]["by_case"]["multiple_11"]
    assert eleven["cue_revision"]["X"] - eleven["frozen"]["X"] == 4
    finance = tokens["request"]["by_case"]["multiple_12"]
    assert finance["frozen"]["X"] - finance["frozen"]["U"] == 190
    assert finance["cue_revision"]["X"] - finance["cue_revision"]["U"] == 80
    assert finance["frozen"]["U"] - finance["frozen"]["S"] == 12


def test_polynomial_cue_replaces_the_class_exclusion_without_touching_the_frozen_render():
    frozen = load_json(ROOT / "rendered" / "multiple_11" / "X.json")
    revised = load_json(REVISION / "rendered" / "multiple_11" / "X.json")
    frozen_text = frozen["tools"][2]["function"]["description"]
    revised_text = revised["tools"][2]["function"]["description"]
    assert OLD_POLYNOMIAL_CUE in frozen_text
    assert OLD_POLYNOMIAL_CUE not in revised_text
    assert "coefficient array in highest-degree-first order" in revised_text
    assert revised_text.startswith("Calculate the roots of a polynomial equation.")
    record = load_json(REVISION / "edits" / "x-record.json")
    cue = record["cases"][2]["tools"][2]["cue"]
    assert "polynomial equation" not in cue
    assert "quadratic equation" not in cue


def test_new_sx_appends_the_new_cue_and_uncued_cases_stay_put():
    manifest, s_record, new_x, catalogues = _revision_package()
    fields = {case["case_id"]: case["fields"] for case in s_record["cases"]}
    cues = {case["case_id"]: case["tools"] for case in new_x["cases"]}
    quiet = {
        "multiple_153",
        "multiple_100",
        "simple_python_175",
        "simple_python_34",
        "irrelevance_59",
        "irrelevance_50",
    }
    for case in manifest["selected"]:
        case_id = case["case_id"]
        frozen_u = (ROOT / "rendered" / case_id / "U.json").read_bytes()
        frozen_s = (ROOT / "rendered" / case_id / "S.json").read_bytes()
        assert (REVISION / "rendered" / case_id / "U.json").read_bytes() == frozen_u
        assert (REVISION / "rendered" / case_id / "S.json").read_bytes() == frozen_s
        rendered = render_conditions(catalogues[case_id], fields[case_id], cues[case_id])
        if case_id in quiet:
            assert rendered["X"] == rendered["U"]
            assert rendered["SX"] == rendered["S"]
            assert all(not item.get("cue") for item in cues[case_id])
        for item in cues[case_id]:
            cue = item.get("cue") or ""
            if not cue:
                continue
            index = item["tool_index"]
            original = rendered["U"][index]["function"]["description"]
            compressed = rendered["S"][index]["function"]["description"]
            assert rendered["X"][index]["function"]["description"] == original + " " + cue
            assert rendered["SX"][index]["function"]["description"] == compressed + " " + cue


def test_errata_points_at_frozen_explanations():
    _manifest, s_record, old_x, catalogues = load_package()
    roa = old_x["cases"][3]["tools"][2]
    assert roa["function_name"] == "financial_ratios_calculate_ROA"
    assert "earlier than the growth-rate tool" in roa["rival"]["why_this_rival"]
    revised = load_json(REVISION / "edits" / "x-record.json")["cases"][3]["tools"][2]
    assert "earlier than the growth-rate tool" not in revised["rival"]["why_this_rival"]
    assert "more similar return ratio" in revised["rival"]["why_this_rival"]
    species = next(
        field
        for case in s_record["cases"]
        if case["case_id"] == "multiple_7"
        for field in case["fields"]
        if field["pointer"] == "/function/parameters/properties/species/description"
    )
    assert "analyzes" in species["reason"]
    growth = catalogues["multiple_7"][0]["function"]["description"]
    assert growth.startswith("Assesses")
    law_u = _law_type(catalogues["simple_python_175"][0])
    rendered_s = load_json(ROOT / "rendered" / "simple_python_175" / "S.json")["tools"][0]
    law_s = _law_type(rendered_s)
    assert "Bankruptcy" in law_u
    assert "Bankruptcy" not in law_s
    assert "enum" not in rendered_s["function"]["parameters"]["properties"]["law_type"]
    reread = (REVISION / "reread.md").read_text(encoding="utf-8")
    assert "same sitting" in reread
    assert "3700" not in reread
    assert "self-review" in reread


def test_semantic_audit_command_includes_the_revision_without_case_ids(capsys):
    assert main(["semantic-audit"]) == 0
    captured = capsys.readouterr().out
    assert '"provider_called": false' in captured
    assert '"frozen_record_intact": true' in captured
    assert "multiple_35" not in captured
    assert "calculate_lcm" not in captured


def test_pinned_requests_match_the_cue_revision_table():
    pin = Path("/tmp/bfcl-pin")
    if not (pin / "BFCL_v4_multiple.json").is_file():
        pytest.skip("pinned BFCL files are not in this environment")
    manifest, s_record, new_x, catalogues = _revision_package()
    fields = {case["case_id"]: case["fields"] for case in s_record["cases"]}
    cues = {case["case_id"]: case["tools"] for case in new_x["cases"]}
    rendered = {
        case["case_id"]: render_conditions(catalogues[case["case_id"]], fields[case["case_id"]], cues[case["case_id"]])
        for case in manifest["selected"]
    }
    totals = request_token_totals(pin, rendered)
    saved = load_json(REVISION / "checks" / "tokens.json")["request"]["by_case"]
    for case_id, counts in totals.items():
        assert counts == saved[case_id]["cue_revision"]
        assert counts["U"] == saved[case_id]["frozen"]["U"]
        assert counts["S"] == saved[case_id]["frozen"]["S"]


def _revision_package():
    manifest, s_record, _old_x, catalogues = load_package()
    new_x = load_json(REVISION / "edits" / "x-record.json")
    return manifest, s_record, new_x, catalogues


def _law_type(tool: dict) -> str:
    return tool["function"]["parameters"]["properties"]["law_type"]["description"]
