"""Locks for the offline 12-case U/S/X/SX pilot. No model calls."""

from pathlib import Path

import pytest

from tool_compression.adapter import unlisted_description_pointers
from tool_compression.semantic_audit import (
    GORILLA_COMMIT,
    RANKED_TSV_SHA256,
    SELECTED_TSV_SHA256,
    SOURCE_SHA256,
    composition_errors,
    field_token_rows,
    file_sha256,
    load_json,
    load_package,
    local_counter,
    package_dir,
    rank_ids,
    ranked_tsv,
    render_conditions,
    request_token_totals,
    saving,
    selection_digest,
    structural_errors,
    verify_package,
)
from tool_compression.__main__ import main

FLOAT = " This is a float type value."
ROOT = package_dir()


def test_package_verification_locks_the_pilot():
    summary = verify_package()
    assert summary["provider_called"] is False
    assert summary["cases"] == 12
    assert summary["fields"] == 95
    assert summary["cue_cases"] == 6
    assert summary["fact_counts"]["lost"] == 0
    assert summary["fact_counts"]["unsupported_additions"] == 0
    assert summary["fact_counts"]["preserved"] == 201
    assert summary["fact_counts"]["uncertain_retained"] == 17


def test_selection_hashes_and_digests():
    assert file_sha256(ROOT / "selection" / "ranked-ids.tsv") == RANKED_TSV_SHA256
    assert file_sha256(ROOT / "selection" / "selected-ids.tsv") == SELECTED_TSV_SHA256
    manifest = load_json(ROOT / "selection" / "manifest.json")
    assert manifest["gorilla_commit"] == GORILLA_COMMIT
    assert [row["case_id"] for row in manifest["selected"]] == [
        "multiple_35",
        "multiple_0",
        "multiple_11",
        "multiple_12",
        "multiple_7",
        "multiple_92",
        "multiple_153",
        "multiple_100",
        "simple_python_175",
        "simple_python_34",
        "irrelevance_59",
        "irrelevance_50",
    ]
    for row in manifest["selected"]:
        assert selection_digest(row["category"], row["case_id"]) == row["sha256"]
        assert SOURCE_SHA256[row["category"]] == manifest["source_files"][row["category"]]["sha256"]


def test_rank_ids_sorts_inside_each_category_only():
    pairs = [
        ("simple_python", "b"),
        ("multiple", "m2"),
        ("multiple", "m1"),
        ("irrelevance", "i"),
    ]
    ranked = rank_ids(pairs)
    text = ranked_tsv(ranked)
    by_category = {}
    for row in ranked:
        by_category.setdefault(row["category"], []).append(row)
    for rows in by_category.values():
        keys = [(row["sha256"], row["case_id"]) for row in rows]
        assert keys == sorted(keys)
        assert [row["rank"] for row in rows] == list(range(1, len(rows) + 1))
    assert text.count("\n") == 4
    assert "\n" not in f"semantic-audit-pilot-01|multiple|m1"


def test_saving_is_one_minus_the_ratio_of_totals():
    assert saving(1051, 909) == pytest.approx(1 - (909 / 1051))
    assert saving(3363, 3221) == pytest.approx(1 - (3221 / 3363))
    tokens = load_json(ROOT / "checks" / "tokens.json")
    assert tokens["local_only"] is True
    assert tokens["provider_usage"] is False
    assert tokens["official_score"] is False
    for block_name in ("field", "request"):
        totals = tokens[block_name]["overall"]["totals"]
        for condition in ("S", "X", "SX"):
            assert tokens[block_name]["overall"]["saving_vs_U"][condition] == pytest.approx(
                1 - (totals[condition] / totals["U"])
            )


def test_float_sentences_and_unlisted_slots_stay_put():
    _manifest, s_record, _x_record, catalogues = load_package()
    seen = 0
    for case in s_record["cases"]:
        for field in case["fields"]:
            if field["original"].endswith(FLOAT):
                seen += 1
                assert field["replacement"].endswith(FLOAT)
        for tool in catalogues[case["case_id"]]:
            assert unlisted_description_pointers(tool) == []
    assert seen == 14


def test_no_cue_cases_keep_x_equal_to_u_and_sx_equal_to_s():
    manifest, s_record, x_record, catalogues = load_package()
    fields = {case["case_id"]: case["fields"] for case in s_record["cases"]}
    cues = {case["case_id"]: case["tools"] for case in x_record["cases"]}
    quiet = {"multiple_153", "multiple_100", "simple_python_175", "simple_python_34", "irrelevance_59", "irrelevance_50"}
    for case in manifest["selected"]:
        case_id = case["case_id"]
        rendered = render_conditions(catalogues[case_id], fields[case_id], cues[case_id])
        assert composition_errors(rendered, fields[case_id], cues[case_id]) == []
        assert structural_errors(rendered) == []
        if case_id in quiet:
            assert rendered["X"] == rendered["U"]
            assert rendered["SX"] == rendered["S"]
        if case_id == "multiple_92":
            assert rendered["S"] == rendered["U"]
            assert rendered["X"] != rendered["U"]


def test_sales_pair_is_outside_the_denominator_and_sx_is_composed():
    payload = load_json(ROOT / "illustration" / "sales-pair.json")
    assert payload["invented"] is True
    assert payload["in_pilot_denominator"] is False
    manifest = load_json(ROOT / "selection" / "manifest.json")
    assert "record_completed_sale" not in {row["case_id"] for row in manifest["selected"]}
    rendered = render_conditions(payload["tools"], payload["fields"], payload["cues"])
    assert composition_errors(rendered, payload["fields"], payload["cues"]) == []
    assert structural_errors(rendered) == []
    rows = field_token_rows("sales-pair", rendered, local_counter())
    totals = {condition: sum(row[condition] for row in rows) for condition in ("U", "S", "X", "SX")}
    assert totals == payload["field_tokens_o200k_base"]
    quote = rendered["S"][1]["function"]["description"]
    assert "rather than a completed sale" in quote
    assert rendered["SX"][0]["function"]["description"].endswith(payload["cues"][0]["cue"])
    assert rendered["X"][0]["function"]["description"].endswith(payload["cues"][0]["cue"])


def test_semantic_audit_command_prints_the_summary(capsys):
    assert main(["semantic-audit"]) == 0
    captured = capsys.readouterr().out
    assert '"provider_called": false' in captured or '"provider_called": false' in captured.lower()
    assert "multiple_35" not in captured


def test_pinned_gorilla_files_reproduce_selection_and_request_tokens():
    pin = Path("/tmp/bfcl-pin")
    multiple = pin / "BFCL_v4_multiple.json"
    if not multiple.is_file():
        pytest.skip("pinned BFCL files are not in this environment")
    for category, filename in (
        ("multiple", "BFCL_v4_multiple.json"),
        ("simple_python", "BFCL_v4_simple_python.json"),
        ("irrelevance", "BFCL_v4_irrelevance.json"),
    ):
        assert file_sha256(pin / filename) == SOURCE_SHA256[category]
    import json

    pairs = []
    for category, filename in (
        ("multiple", "BFCL_v4_multiple.json"),
        ("simple_python", "BFCL_v4_simple_python.json"),
        ("irrelevance", "BFCL_v4_irrelevance.json"),
    ):
        text = (pin / filename).read_text(encoding="utf-8")
        rows = json.loads(text) if text.lstrip().startswith("[") else [json.loads(line) for line in text.splitlines() if line.strip()]
        pairs.extend((category, row["id"]) for row in rows)
    digest = __import__("hashlib").sha256(ranked_tsv(rank_ids(pairs)).encode("utf-8")).hexdigest()
    assert digest == RANKED_TSV_SHA256
    manifest, s_record, x_record, catalogues = load_package()
    fields = {case["case_id"]: case["fields"] for case in s_record["cases"]}
    cues = {case["case_id"]: case["tools"] for case in x_record["cases"]}
    rendered = {
        case["case_id"]: render_conditions(catalogues[case["case_id"]], fields[case["case_id"]], cues[case["case_id"]])
        for case in manifest["selected"]
    }
    totals = request_token_totals(pin, rendered)
    saved = load_json(ROOT / "checks" / "tokens.json")["request"]["by_case"]
    for case_id, counts in totals.items():
        assert counts == saved[case_id]["totals"]
