"""Packages B and C. Saved-output scoring, settlement, and the alias guard.

No provider is called. Locked official figures are checked, not replaced.
"""

from pathlib import Path
import json
import math
import subprocess

import pytest

from tool_compression.accounting import contrast_usage_accounting, locked_usage_issues, spend_cny
from tool_compression.analysis import class_join_issues, join_cases, uncertainty_analysis
from tool_compression.artifacts import build_manifest, verify_manifest
from tool_compression.claims import QUALITY_STATEMENT, SIGN_STATEMENT
from tool_compression.convert import to_openai_completions_tools
from tool_compression.official_score import (
    FLIGHT_MODEL,
    REGISTRY_MODEL_NAME,
    SCORING_ALIAS,
    ScoringAliasGenerateRefused,
    accuracy_change_points,
    build_bfcl_argv,
    call_names,
    decode_saved_fc_responses,
    dotted_name_count,
    guard_bfcl_argv,
    locked_settlement_issues,
    map_saved_outputs,
    recorded_conversion_parity,
    settle_from_saved,
    tool_names_in_request_body,
)
from tool_compression.overhead import measure_preprocessing, synthetic_catalogues
from tool_compression.__main__ import main

ROOT = Path(__file__).resolve().parents[1]
NEW_MODULES = (
    "official_score.py",
    "accounting.py",
    "analysis.py",
    "artifacts.py",
    "overhead.py",
    "claims.py",
)


def test_locked_settlement_recomputes_and_keeps_the_recorded_result():
    settlement = _load("official/settlement/official_settlement.json")
    assert locked_settlement_issues(settlement) == []
    primary = settlement["categories"]["multiple"]
    assert primary["S_LU"]["ratio_numerator"] == 1398
    assert primary["S_LU"]["ratio_denominator"] == 121018
    assert primary["accuracy"]["U"]["correct"] == 186
    assert primary["accuracy"]["L"]["correct"] == 185
    assert primary["accuracy"]["E"]["correct"] == 186
    points = accuracy_change_points(-1, 200)
    assert points["l_minus_u_percentage_points"] == -0.5
    assert points["observed_accuracy_loss_points"] == 0.5
    assert "accuracy loss -0.5" not in points["wording"]
    assert "accuracy loss −0.5" not in points["wording"]
    assert settlement["reference_target_L_represents_C"]["combine_targets"]["target_reached"] is False


def test_usage_contrast_is_a_different_measurement_from_billed_basis_t():
    usage = _load("official/tables/usage_accounting.json")
    assert locked_usage_issues(usage) == []
    contrast = contrast_usage_accounting(usage)
    primary = contrast["categories"]["multiple"]
    assert primary["token_numerator"] == 1398
    assert primary["price_weighted_input_is_study_statistic"] is False
    assert primary["price_weighted_input_establishes_token_target"] is False
    assert primary["isolates_compression_caused_deployment_savings"] is False
    assert primary["establishes_total_cost"] is False
    assert primary["token_order"] == ["U", "E", "L"]
    assert primary["price_weighted_order"] == ["U", "L", "E"]
    assert math.isclose(primary["price_weighted_ratio_float"], 0.1302478611568131, abs_tol=1e-12)
    assert contrast["stage_b_spend_cny"] == "1.24290304"
    assert spend_cny(669623, 83702, 163827) == spend_cny(669623, 83702, 163827)


def test_change_class_join_matches_week1_counts_and_official_totals():
    recorded = _load("official/tables/change_class_join.json")
    characterization = _load("evidence/week1_characterization.json")
    settlement = _load("official/settlement/official_settlement.json")
    assert class_join_issues(characterization, settlement, recorded) == []
    joined = join_cases(
        [
            {
                "category": "multiple",
                "case_id": "multiple_0",
                "change_class": "unchanged",
                "correct_U": True,
                "correct_L": True,
                "input_tokens_U": 10,
                "input_tokens_L": 10,
            },
            {
                "category": "multiple",
                "case_id": "multiple_1",
                "change_class": "suffix_only",
                "correct_U": True,
                "correct_L": False,
                "input_tokens_U": 20,
                "input_tokens_L": 12,
            },
            {
                "category": "multiple",
                "case_id": "multiple_2",
                "change_class": "other_change",
                "correct_U": False,
                "correct_L": False,
                "input_tokens_U": None,
                "input_tokens_L": None,
            },
        ]
    )
    assert joined["issues"] == []
    by_class = {row["change_class"]: row for row in joined["classes"]}
    assert by_class["unchanged"]["provider_input_removed_L_vs_U"] == 0
    assert by_class["suffix_only"]["provider_input_removed_L_vs_U"] == 8
    assert by_class["other_change"]["token_coverage_U"] == "incomplete"
    assert by_class["other_change"]["sum_T_U"] is None
    disagreed = join_cases(
        [
            {
                "category": "multiple",
                "case_id": "multiple_0",
                "change_class": "unchanged",
                "correct_U": True,
                "correct_L": False,
                "input_tokens_U": 5,
                "input_tokens_L": 4,
            }
        ]
    )
    assert any("official outcome" in item for item in disagreed["issues"])
    assert any("billed-basis T" in item for item in disagreed["issues"])


def test_evaluate_from_saved_outputs_maps_and_settles_a_fixture(tmp_path):
    stage_b = tmp_path / "stage_b"
    stage_b.mkdir()
    logical = {
        "independent_observations": 5,
        "responses": [
            _group("g-shared", "multiple_0", ["U", "L"], reused=["L"], tokens=10, output=1),
            _group("g-e", "multiple_0", ["E"], tokens=9, output=1),
            _group("g-u", "multiple_1", ["U"], tokens=8, output=2),
            _group("g-l", "multiple_1", ["L"], tokens=7, output=2),
            _group("g-e2", "multiple_1", ["E"], tokens=8, output=2),
        ],
    }
    (stage_b / "logical_ledger.json").write_text(json.dumps(logical), encoding="utf-8")
    attempts = []
    parsed = []
    calls = {
        "g-shared": [{"keep_tool": "{\"x\": 1}"}],
        "g-e": [{"keep_tool": "{\"x\": 1}"}],
        "g-u": [{"other_tool": "{\"x\": 2}"}],
        "g-l": [{"other_tool": "{\"x\": 3}"}],
        "g-e2": [{"other_tool": "{\"x\": 2}"}],
    }
    for group in logical["responses"]:
        gid = group["response_group_id"]
        attempts.append(
            {
                "response_group_id": gid,
                "status": "received",
                "usage": {"total_input_tokens": group["input_tokens"]},
            }
        )
        parsed.append(
            {
                "response_group_id": gid,
                "thinking_disabled": True,
                "model_responses": calls[gid],
            }
        )
    (stage_b / "usage_ledger.json").write_text(
        json.dumps({"count": 5, "physical_attempts": attempts}),
        encoding="utf-8",
    )
    (stage_b / "parsed.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in parsed),
        encoding="utf-8",
    )
    out = tmp_path / "official"
    summary = map_saved_outputs(
        stage_b,
        out,
        categories={"multiple": 2},
        expected_groups=5,
    )
    assert summary["ok"] is True
    result_path = out / "bfcl_project" / "result_l" / SCORING_ALIAS / "BFCL_v4_multiple_result.json"
    rows = [json.loads(line) for line in result_path.read_text(encoding="utf-8").splitlines()]
    assert rows[0] == {"id": "multiple_0", "result": calls["g-shared"]}
    assert rows[1]["result"] == calls["g-l"]
    assert dotted_name_count(call_names(rows[0]["result"])) == 0
    score_root = out / "bfcl_project"
    _write_score(score_root, "u", ["multiple_1"])
    _write_score(score_root, "l", ["multiple_1"])
    _write_score(score_root, "e", [])
    settled = settle_from_saved(
        score_root,
        out / "mapping" / "arm_case_mapping.jsonl",
        categories={"multiple": 2},
    )
    assert settled["paid_provider_called"] is False
    assert settled["invented_scores"] is False
    assert settled["generate_refused"] is True
    assert settled["categories"]["multiple"]["provider_total_input"]["U"]["sum"] == 18
    assert settled["categories"]["multiple"]["provider_total_input"]["L"]["sum"] == 17
    assert settled["categories"]["multiple"]["accuracy"]["E"]["correct"] == 2
    assert settled["reference_target_L_represents_C"]["study_target_status"]["reason"] == (
        "execution_record_not_supplied"
    )
    assert not (stage_b / "bfcl_project").exists()


def test_handler_alias_cannot_generate_and_decode_checks_stay_on_saved_text():
    with pytest.raises(ScoringAliasGenerateRefused) as caught:
        build_bfcl_argv(
            "generate",
            model=SCORING_ALIAS,
            test_category="multiple",
            result_dir="result_u",
            score_dir="score_u",
        )
    assert REGISTRY_MODEL_NAME in str(caught.value)
    assert FLIGHT_MODEL in str(caught.value)
    with pytest.raises(ScoringAliasGenerateRefused):
        guard_bfcl_argv(["bfcl", "generate", "--model", SCORING_ALIAS])
    argv = build_bfcl_argv(
        "evaluate",
        model=SCORING_ALIAS,
        test_category="simple_python,multiple,irrelevance",
        result_dir="result_u",
        score_dir="score_u",
    )
    assert argv[1] == "evaluate"
    assert "generate" not in argv
    assert SCORING_ALIAS in argv
    chain = _load("official/tables/measurement_chain.json")
    assert chain["official_handler_alias"] == SCORING_ALIAS
    assert chain["official_registry_model_name_if_generate_were_used"] == REGISTRY_MODEL_NAME
    assert chain["all_requests_deepseek_flash"] is True
    assert chain["all_responses_deepseek_flash"] is True
    assert chain["dotted_tool_names_in_requests"] == 0
    assert chain["dotted_names_in_parsed_calls"] == 0
    assert chain["official_registry_flags"] == {"is_fc_model": True, "underscore_to_dot": True}
    characterization = _load("evidence/week1_characterization.json")
    parity = recorded_conversion_parity(characterization)
    assert parity["checked_records"] == 840
    assert parity["mismatches"] == 0
    converted = to_openai_completions_tools(
        [
            {
                "name": "video_games.store_price",
                "description": "Price.",
                "parameters": {
                    "type": "dict",
                    "properties": {"amount": {"type": "float", "description": "Amount."}},
                    "required": ["amount"],
                },
            }
        ]
    )
    assert converted[0]["function"]["name"] == "video_games_store_price"
    assert dotted_name_count(tool_names_in_request_body({"tools": converted})) == 0
    stored = [{"video_games_store_price": "{\"amount\": 1}"}]
    assert decode_saved_fc_responses(json.dumps(stored)) == stored
    assert dotted_name_count(call_names(stored)) == 0
    assert dotted_name_count(call_names([{"video_games.store_price": "{}"}])) == 1


def test_manifest_hashes_repository_files_and_leaves_absent_flight_trees_null(tmp_path):
    manifest = build_manifest(ROOT)
    assert verify_manifest(manifest, ROOT) == []
    committed = json.loads((ROOT / "official" / "artifact_manifest.json").read_text(encoding="utf-8"))
    assert verify_manifest(committed, ROOT) == []
    absent = [item for item in manifest["artifacts"] if not item["in_repository"]]
    assert absent
    assert all(item["sha256"] is None for item in absent)
    assert all(item["historical_path_portable"] is False for item in absent)
    present = [item for item in manifest["artifacts"] if item["in_repository"]]
    assert all(item["sha256"] for item in present)
    stray = {"id": "made_up", "in_repository": False, "sha256": "abc", "historical_path_portable": False, "present": False, "historical_path": "/tmp/x"}
    broken = dict(manifest)
    broken["artifacts"] = list(manifest["artifacts"]) + [stray]
    assert verify_manifest(broken, ROOT)


def test_preprocessing_timing_is_per_condition_and_calls_no_model():
    catalogues = synthetic_catalogues(n=4, tools=3)

    class Words:
        name = "words"

        def count(self, text: str) -> int:
            return len(text.split())

    measured = measure_preprocessing(catalogues, Words(), repeats=2)
    assert measured["model_called"] is False
    assert set(measured["seconds"]) == {"P", "I", "C"}
    assert measured["catalogues"] == 4
    assert measured["median_C_minus_I_seconds"] == (
        measured["seconds"]["C"]["median"] - measured["seconds"]["I"]["median"]
    )
    assert measured["selections_coincide_on_this_corpus"] is True


def test_uncertainty_record_states_the_limits_of_one_replicate():
    settlement = _load("official/settlement/official_settlement.json")
    record = uncertainty_analysis(settlement)
    assert record["replicates"] == 1
    assert record["statistical_non_inferiority"] == "not_tested"
    assert record["confidence_interval"] is None
    assert record["general_quality_preservation"] is False
    assert record["reused_members_are_independent_observations"] is False
    assert record["primary_independent_request_groups"] == 438
    assert record["primary_reused_members"] == 162
    assert record["quality_statement"] == QUALITY_STATEMENT
    assert record["sign_statement"] == SIGN_STATEMENT
    assert "a full BFCL leaderboard result" in record["claims_not_established"]


def test_recorded_prose_keeps_the_required_wording():
    files = [
        ROOT / "README.md",
        ROOT / "official" / "RESULTS.md",
        ROOT / "official" / "COMMANDS.md",
        ROOT / "official" / "README.md",
    ]
    plan = (ROOT / "Controlled_Tool_Description_Compression_Agent_Plan.md").read_text(encoding="utf-8")
    start = plan.index("#### Current handoff (recorded 18–19 November 2026 result)")
    stop = plan.index("### Research questions and estimands")
    texts = {path.name: path.read_text(encoding="utf-8") for path in files}
    texts["handoff"] = plan[start:stop]
    forbidden = (
        "accuracy loss -0.5",
        "accuracy loss −0.5",
        "billing coincidence",
        "cannot be estimated",
        "provider-token ceiling",
        "provider token ceiling",
        "uniquely fixes",
        "uniquely fix",
    )
    for name, text in texts.items():
        assert QUALITY_STATEMENT in text, name
        assert SIGN_STATEMENT in text, name
        for phrase in forbidden:
            assert phrase not in text, f"{name} contains {phrase}"
    packet = (ROOT / "evidence" / "WEEK1_EVIDENCE_PACKET.md").read_text(encoding="utf-8")
    assert "**stop**" in packet


def test_shell_evaluate_script_refuses_generate():
    completed = subprocess.run(
        ["bash", str(ROOT / "scripts" / "run_official_evaluate.sh"), "generate"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 2
    assert "deepseek-chat" in completed.stderr
    assert FLIGHT_MODEL in completed.stderr


def test_official_check_accepts_the_committed_record():
    assert main(["official-check"]) == 0


def test_commands_refuse_generate_and_new_modules_stay_offline():
    assert main(["official-guard", "--action", "generate", "--model", SCORING_ALIAS]) == 2
    assert main(["official-guard", "--action", "evaluate", "--model", SCORING_ALIAS]) == 0
    package = ROOT / "src" / "tool_compression"
    for name in NEW_MODULES:
        text = (package / name).read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if not (stripped.startswith("import ") or stripped.startswith("from ")):
                continue
            module = stripped.split()[1].split(".")[0].rstrip(",")
            assert module not in {"openai", "httpx", "urllib", "requests", "socket"}


def _load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def _group(gid, case_id, members, tokens, output, reused=None):
    return {
        "response_group_id": gid,
        "case_id": case_id,
        "category": "multiple",
        "replicate": 0,
        "members": members,
        "reused_members": reused or [],
        "input_tokens": tokens,
        "cache_hit_tokens": 0,
        "output_tokens": output,
        "request_sha256": "abc",
    }


def _write_score(score_root: Path, arm: str, failed_ids: list[str]) -> None:
    denominator = 2
    rows = [
        {
            "accuracy": (denominator - len(failed_ids)) / denominator,
            "correct_count": denominator - len(failed_ids),
            "total_count": denominator,
        }
    ]
    for case_id in failed_ids:
        rows.append({"id": case_id, "valid": False, "error_type": "fixture", "error": []})
    path = (
        score_root
        / f"score_{arm}"
        / SCORING_ALIAS
        / "non_live"
        / "BFCL_v4_multiple_score.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
