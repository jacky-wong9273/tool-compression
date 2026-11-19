"""Follow-on T1/T2 checks. Fixture prose is not benchmark data. No model calls."""

from pathlib import Path
import json

import pytest

from tool_compression.artifacts import verify_manifest
from tool_compression.config import DEFAULT_CONFIG, METHODS
from tool_compression.convert import FLOAT_SUFFIX, to_openai_completions_tools
from tool_compression.count import TiktokenCounter
from tool_compression.followon_audit import analyze_record, case_stop
from tool_compression.followon_bind import (
    ArchivedAnswerRefused,
    FollowOnJoinError,
    bind_saved_answer,
    join_followon_records,
    reproduce_historical_official_counts,
)
from tool_compression.followon_config import T1_CONFIG, T2_CONFIG, T2_ZERO_CONFIG
from tool_compression.followon_report import verify_followon_manifest
from tool_compression.lexical import contrast_q, description_features, select_neighbours, tool_feature_set
from tool_compression.official_score import (
    SCORING_ALIAS,
    ScoringAliasGenerateRefused,
    build_bfcl_argv,
    guard_bfcl_argv,
)
from tool_compression.phrase import ALIAS_MARKERS, EM_DASH, SEMICOLON, parse_field, render_pieces
from tool_compression.phrase_compress import compress_conditions
from tool_compression.phrase_select import field_budget, nominal_cap
from tool_compression.validate import catalogue_violations

ROOT = Path(__file__).resolve().parents[1]
STATION = "Find station records; also called station search; also called railhead search."
AMBIGUOUS = "Do not include closed stations, except stations marked open, or stations without a code."
NEGATION = "Find station records. Do not include closed stations; also called depot search."


class One:
    name = "one"

    def count(self, text: str) -> int:
        return 1 if text else 0


class ProtectedExpands:
    name = "protected-expands"

    def count(self, text: str) -> int:
        if text == "Find station records.":
            return 100
        return max(1, len(text.split()))


def tool(name, description, param="Zone.", key="zone"):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {key: {"type": "string", "description": param}},
                "required": [key],
            },
        },
    }


def station_catalogue():
    return [
        tool("locate", STATION, "Zone.", "zone"),
        tool("nearby", "also called station search", "Area.", "area"),
    ]


def test_frozen_markers_and_new_trial_flags():
    assert SEMICOLON == ";"
    assert EM_DASH == "\u2014"
    assert ALIAS_MARKERS == ("also called", "also known as", "for example")
    assert T2_CONFIG.contrast_numerator == 1
    assert T2_CONFIG.contrast_denominator == 2
    assert T1_CONFIG.contrast_numerator == 0
    recorded = T2_CONFIG.as_dict()
    assert recorded["new_trial_settings"] is True
    assert recorded["retunes_closed_official_run"] is False
    assert recorded["closed_target_is_reset_test"] is False
    assert DEFAULT_CONFIG.spec_version == "week1.0"
    assert METHODS == ("U", "P", "I", "C")
    spec = (ROOT / "FOLLOWON-SPECIFICATION.md").read_text(encoding="utf-8")
    for marker in ALIAS_MARKERS:
        assert marker in spec
    assert "max(floor(0.75 × d), p)" in spec


def test_station_ranges_and_pinned_budget():
    parsed = parse_field(STATION, "function")
    assert parsed.status == "parsed"
    texts = [(piece.kind, STATION[piece.start : piece.end]) for piece in parsed.pieces]
    assert texts == [
        ("anchor", "Find station records"),
        ("optional", "; also called station search"),
        ("optional", "; also called railhead search"),
        ("terminal", "."),
    ]
    counter = TiktokenCounter("o200k_base")
    protected = {0, 3}
    one_station = counter.count(render_pieces(STATION, parsed.pieces, protected | {1}))
    one_rail = counter.count(render_pieces(STATION, parsed.pieces, protected | {2}))
    both = counter.count(render_pieces(STATION, parsed.pieces, protected | {1, 2}))
    budget, nominal = field_budget(counter.count(STATION), counter.count(render_pieces(STATION, parsed.pieces, protected)), T1_CONFIG)
    assert nominal == budget
    assert one_station <= budget
    assert one_rail <= budget
    assert both > budget


def test_selector_keeps_station_then_railhead_and_real_q_orders_them():
    counter = TiktokenCounter("o200k_base")
    catalogue = station_catalogue()
    result = compress_conditions(catalogue, counter)
    assert result["catalogues"]["T1"][0]["function"]["description"] == "Find station records; also called station search."
    assert result["catalogues"]["T2"][0]["function"]["description"] == "Find station records; also called railhead search."
    field = result["traces"][0]["fields"][0]
    assert field["competing_pairs"] == [[1, 2]]
    assert field["by_condition"]["T1"]["order"] == [1, 2]
    assert field["by_condition"]["T2"]["order"] == [2, 1]
    features = [tool_feature_set(item) for item in catalogue]
    assert select_neighbours(features)[0][0] == (1,)
    neighbour_features = [description_features(catalogue[1])]
    station_q = contrast_q("; also called station search", neighbour_features)
    rail_q = contrast_q("; also called railhead search", neighbour_features)
    assert rail_q > station_q
    assert field["pieces"][1]["q"] == "0/1"
    assert field["pieces"][2]["q"] == f"{rail_q.numerator}/{rail_q.denominator}"


def test_contrast_is_inoperative_without_a_neighbour_or_with_zero_weight():
    counter = TiktokenCounter("o200k_base")
    alone = compress_conditions([station_catalogue()[0]], counter)
    assert alone["catalogues"]["T1"] == alone["catalogues"]["T2"]
    assert alone["traces"][0]["neighbours"] == []
    zero = compress_conditions(station_catalogue(), counter, (T1_CONFIG, T2_ZERO_CONFIG))
    assert zero["catalogues"]["T1"] == zero["catalogues"]["T2"]
    assert zero["catalogues"]["T1"][0]["function"]["description"].endswith("station search.")


def test_repeated_transform_protected_ranges_and_exact_identity():
    counter = TiktokenCounter("o200k_base")
    catalogue = [tool("locate", NEGATION)]
    snapshot = json.loads(json.dumps(catalogue))
    first = compress_conditions(catalogue, counter)
    second = compress_conditions(catalogue, counter)
    assert catalogue == snapshot
    assert first["catalogues"] == second["catalogues"]
    assert first["traces"] == second["traces"]
    for name in ("T1", "T2"):
        updated = first["catalogues"][name][0]["function"]["description"]
        assert "Do not include closed stations" in updated
        assert "also called depot search" not in updated
        assert catalogue_violations(snapshot, first["catalogues"][name]) == []
    kept = "Find station records for a city."
    identity = compress_conditions([tool("locate", kept)], counter)
    assert identity["catalogues"]["T1"][0]["function"]["description"] is kept
    assert identity["catalogues"]["T2"][0]["function"]["description"] is kept
    optional = compress_conditions([tool("locate", STATION)], One())
    assert optional["catalogues"]["T1"][0]["function"]["description"] is STATION
    assert optional["traces"][0]["fields"][0]["status"] == "identity_all_kept"


def test_ambiguous_comma_field_is_not_split_and_float_cue_survives():
    counter = TiktokenCounter("o200k_base")
    parsed = parse_field(AMBIGUOUS, "function")
    assert parsed.status == "parsed"
    assert [piece.kind for piece in parsed.pieces] == ["anchor", "terminal"]
    result = compress_conditions([tool("locate", AMBIGUOUS)], counter)
    assert result["catalogues"]["T1"][0]["function"]["description"] is AMBIGUOUS
    assert result["traces"][0]["fields"][0]["optional_count"] == 0
    converted = to_openai_completions_tools(
        [
            {
                "name": "measure",
                "description": "Measure distance.",
                "parameters": {
                    "type": "dict",
                    "properties": {"v": {"type": "float", "description": "Distance."}},
                    "required": ["v"],
                },
            }
        ]
    )
    original = converted[0]["function"]["parameters"]["properties"]["v"]["description"]
    assert original == "Distance." + FLOAT_SUFFIX
    compressed = compress_conditions(converted, counter)
    for name in ("T1", "T2"):
        updated = compressed["catalogues"][name][0]["function"]["parameters"]["properties"]["v"]["description"]
        assert updated == original
        assert "This is a float type value." in updated
    reasons = []
    for piece in compressed["traces"][0]["fields"][1]["pieces"]:
        reasons.extend(piece["reasons"])
    assert "float_type_cue" in reasons


def test_non_expansion_and_cap_formula():
    result = compress_conditions([tool("locate", "Find station records; also called depot search.")], ProtectedExpands())
    field = result["traces"][0]["fields"][0]
    assert field["status"] == "non_expansion"
    assert result["catalogues"]["T1"][0]["function"]["description"] == "Find station records; also called depot search."
    assert nominal_cap(10, T1_CONFIG) == 7
    assert field_budget(10, 4, T1_CONFIG) == (7, 7)
    assert field_budget(10, 8, T1_CONFIG) == (8, 7)
    assert field_budget(10, 11, T1_CONFIG)[0] is None


def test_only_permitted_fields_change_and_questions_stay_out():
    catalogue = station_catalogue()
    catalogue[0]["function"]["parameters"]["properties"]["zone"]["default"] = {"description": "KEEP_ME"}
    snapshot = json.loads(json.dumps(catalogue))
    result = compress_conditions(catalogue, TiktokenCounter("o200k_base"))
    assert catalogue == snapshot
    edited = result["catalogues"]["T2"]
    assert edited[0]["function"]["parameters"]["properties"]["zone"]["default"]["description"] == "KEEP_ME"
    assert catalogue_violations(snapshot, edited) == []
    broken = json.loads(json.dumps(edited))
    broken[0]["function"]["name"] = "renamed"
    assert catalogue_violations(edited, broken)
    record = {
        "id": "multiple_0",
        "question": [[{"role": "user", "content": "fixture-question"}]],
        "function": [
            {
                "name": "locate",
                "description": STATION,
                "parameters": {"type": "dict", "properties": {"zone": {"type": "string", "description": "Zone."}}},
            },
            {
                "name": "nearby",
                "description": "also called station search",
                "parameters": {"type": "dict", "properties": {"area": {"type": "string", "description": "Area."}}},
            },
        ],
    }
    case_row, _fields = analyze_record(record, TiktokenCounter("o200k_base"), repeat=True)
    assert case_row["funnel"] == {
        "opportunity": True,
        "neighbour": True,
        "ranking": True,
        "delivered": True,
    }
    assert case_row["stop_reason"] == "delivered_change"
    assert "fixture-question" not in json.dumps(result["catalogues"])


def test_stop_reasons_partition_and_rows_are_cumulative():
    fields = [
        {"delivered": False, "ranking": False, "opportunity": False, "neighbour": False, "protected_fills_cap": False, "single_content_clause": True},
    ]
    assert case_stop(fields, False, False) == "indivisible_single_clause"
    assert case_stop(fields, False, True) == "preparation_failure"
    competing = {
        "delivered": False,
        "ranking": False,
        "opportunity": True,
        "neighbour": True,
        "protected_fills_cap": False,
        "single_content_clause": False,
    }
    assert case_stop([competing], False, False) == "same_order"
    competing["neighbour"] = False
    assert case_stop([competing], False, False) == "no_neighbour"
    competing["neighbour"] = True
    competing["ranking"] = True
    assert case_stop([competing], True, False) == "different_order_same_selection"
    competing["delivered"] = True
    assert case_stop([competing], True, False) == "delivered_change"


def test_historical_counts_reproduce_offline_and_generation_is_refused(monkeypatch):
    import urllib.request

    def blocked(*_args, **_kwargs):
        raise AssertionError("network")

    monkeypatch.setattr(urllib.request, "urlopen", blocked)
    historical = reproduce_historical_official_counts(ROOT)
    assert historical["network_used"] is False
    assert historical["ok"] is True
    assert historical["target_reached"] is False
    assert historical["target_is_reset_test_for_followon"] is False
    multiple = historical["categories"]["multiple"]
    assert multiple["correct"] == {"U": 186, "L": 185, "E": 186}
    assert multiple["saving_numerator_L_vs_U"] == 1398
    assert multiple["saving_denominator_L_vs_U"] == 121018
    with pytest.raises(ScoringAliasGenerateRefused):
        build_bfcl_argv(
            "generate",
            model=SCORING_ALIAS,
            test_category="multiple",
            result_dir="result_u",
            score_dir="score_u",
        )
    with pytest.raises(ScoringAliasGenerateRefused):
        guard_bfcl_argv(["bfcl", "generate", "--model", SCORING_ALIAS])


def test_archived_answers_and_joins_fail_closed():
    with pytest.raises(ArchivedAnswerRefused):
        bind_saved_answer(
            archived_condition="L",
            archived_case="multiple_0",
            archived_replicate="r0",
            archived_request_hash="abc",
            target_condition="T2",
            target_case="multiple_0",
            target_replicate="r0",
            target_request_hash="abc",
        )
    with pytest.raises(ArchivedAnswerRefused):
        bind_saved_answer(
            archived_condition="T1",
            archived_case="multiple_0",
            archived_replicate="r0",
            archived_request_hash="abc",
            target_condition="T1",
            target_case="multiple_1",
            target_replicate="r0",
            target_request_hash="abc",
        )
    with pytest.raises(ArchivedAnswerRefused):
        bind_saved_answer(
            archived_condition="T1",
            archived_case="multiple_0",
            archived_replicate="r0",
            archived_request_hash="abc",
            target_condition="T1",
            target_case="multiple_0",
            target_replicate="r0",
            target_request_hash="def",
        )
    bound = bind_saved_answer(
        archived_condition="T1",
        archived_case="multiple_0",
        archived_replicate="r0",
        archived_request_hash="abc",
        target_condition="T2",
        target_case="multiple_0",
        target_replicate="r0",
        target_request_hash="abc",
    )
    assert bound["shared_request"] is True
    row = {
        "case_id": "multiple_0",
        "replicate": "r0",
        "condition": "T1",
        "request_group": "g",
        "request_hash": "abc",
        "verified_request_hash": "abc",
    }
    assert join_followon_records([row], expected=[("multiple_0", "r0", "T1", "g")])["records"] == 1
    with pytest.raises(FollowOnJoinError):
        join_followon_records([row, row])
    with pytest.raises(FollowOnJoinError):
        join_followon_records([row], expected=[("multiple_0", "r0", "T2", "g")])
    mismatch = dict(row, verified_request_hash="nope")
    with pytest.raises(FollowOnJoinError):
        join_followon_records([mismatch])


def test_committed_audit_covers_every_case_without_measuring():
    path = ROOT / "followon" / "audit_summary.json"
    if not path.is_file():
        pytest.skip("follow-on audit has not been written")
    summary = json.loads(path.read_text(encoding="utf-8"))
    assert summary["measured"] is False
    assert summary["provider_called"] is False
    assert summary["historical_target_is_reset_test_for_followon"] is False
    assert summary["primary_field_inventory"] == {"week1": 2101, "observed": 2101, "reconciled": True}
    assert [row["name"] for row in summary["funnel"]["rows"]] == [
        "opportunity",
        "neighbour",
        "ranking",
        "delivered",
    ]
    for category, denominator in (("multiple", 200), ("simple_python", 400), ("irrelevance", 240)):
        block = summary["categories"][category]
        assert block["n"] == denominator
        assert block["prepared"] == denominator
        assert block["preparation_failures"] == 0
        assert block["f_new"]["denominator"] == denominator
        assert block["f_new"]["unknown"] == 0
        assert sum(block["stop_reasons"].values()) == denominator
        assert block["field_inventory_reconciled"] is True
    assert summary["categories"]["simple_python"]["single_tool"] is True
    assert summary["categories"]["irrelevance"]["single_tool"] is True
    assert summary["categories"]["simple_python"]["f_new"]["numerator"] == summary["categories"]["simple_python"]["changed_fields_t2_t1"]
    assert summary["implementation_defects"] == []


def test_official_manifest_still_matches_and_followon_manifest_matches_when_present():
    official = json.loads((ROOT / "official" / "artifact_manifest.json").read_text(encoding="utf-8"))
    assert verify_manifest(official, ROOT) == []
    manifest_path = ROOT / "followon" / "manifest.json"
    if not manifest_path.is_file():
        pytest.skip("follow-on package has not been written")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert verify_followon_manifest(manifest, ROOT) == []
    assert manifest["provider_called"] is False
    assert manifest["base_commit"] == "3a02e64888c5359f48d2b417ac659161cd3eadae"
