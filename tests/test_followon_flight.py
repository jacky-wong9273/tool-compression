"""T1/T2 flight preparation. No provider call and no --live invocation."""

from datetime import datetime
from decimal import Decimal
from pathlib import Path
import json
import os

import pytest

from tool_compression.__main__ import main
from tool_compression.followon_config import T1_CONFIG, T2_CONFIG
from tool_compression.followon_flight import (
    ARMS,
    CEILING_ENV,
    EXPECTED_CASES,
    REMAINING_AUTHORIZED_CNY,
    REDRAW_SENTENCE,
    SCORING_ALIAS,
    SOURCE_TIP,
    CeilingRequired,
    FollowOnFlightRefused,
    accept_ceiling,
    arm_rows,
    catalogue_plan,
    comparison_versus_official_u,
    flight_body,
    is_peak,
    official_evaluate_argv,
    plan_record,
    pre_call_reserve_cny,
    reconfirm_committed_identity,
    resolve_ceiling,
    sequential_groups,
)
from tool_compression.official_score import ScoringAliasGenerateRefused

ROOT = Path(__file__).resolve().parents[1]
def _hkt(year, month, day, hour, minute=0):
    from zoneinfo import ZoneInfo

    return datetime(year, month, day, hour, minute, tzinfo=ZoneInfo("Asia/Hong_Kong"))


def _record(category, index, description="Find records.", param_type="string"):
    return {
        "id": f"{category}_{index}",
        "question": [[{"role": "user", "content": f"Question {category} {index}"}]],
        "function": [
            {
                "name": "lookup",
                "description": description,
                "parameters": {
                    "type": "dict",
                    "properties": {"zone": {"type": param_type, "description": "Zone name."}},
                    "required": ["zone"],
                },
            }
        ],
    }


def _study(description="Find records."):
    sizes = {"multiple": 200, "simple_python": 400, "irrelevance": 240}
    return {
        category: [_record(category, index, description) for index in range(count)]
        for category, count in sizes.items()
    }


class One:
    name = "one"

    def count(self, text: str) -> int:
        return 1 if text else 0


def test_ceiling_has_no_default_and_rejects_a_lift():
    assert resolve_ceiling.__defaults__ == (None,)
    with pytest.raises(CeilingRequired):
        accept_ceiling(None)
    with pytest.raises(CeilingRequired):
        accept_ceiling("")
    with pytest.raises(CeilingRequired):
        accept_ceiling(1.5)
    with pytest.raises(CeilingRequired):
        resolve_ceiling(None, {})
    with pytest.raises(CeilingRequired):
        accept_ceiling("50")
    supplied = accept_ceiling("48.74670004")
    assert supplied == REMAINING_AUTHORIZED_CNY
    assert resolve_ceiling(None, {CEILING_ENV: "1.00"}) == Decimal("1.00")
    assert CEILING_ENV not in os.environ or os.environ.get(CEILING_ENV) != ""


def test_peak_window_matches_the_2000_hkt_slot():
    assert is_peak(_hkt(2026, 11, 23, 10, 39)) is True
    assert is_peak(_hkt(2026, 11, 23, 18, 0)) is False
    assert is_peak(_hkt(2026, 11, 23, 20, 0)) is False
    assert is_peak(_hkt(2026, 11, 22, 11, 0)) is False


def test_committed_audit_identity_is_a_redraw_of_u():
    report = reconfirm_committed_identity(ROOT)
    assert report["source_tip"] == SOURCE_TIP
    assert report["parent_tip"] == "3a02e64888c5359f48d2b417ac659161cd3eadae"
    assert report["cases"] == 840
    assert report["identity_holds"] is True
    assert report["same_request_redraw_of_u"] is True
    assert report["hash_mismatches"] == []
    assert report["f_new"]["multiple"]["text"] == "0/200"
    assert report["f_new"]["simple_python"]["text"] == "0/400"
    assert report["f_new"]["irrelevance"]["text"] == "0/240"
    assert report["provider_called"] is False
    assert report["measured"] is False
    readiness = json.loads((ROOT / "followon" / "flight_readiness.json").read_text(encoding="utf-8"))
    assert readiness["identity_holds"] is True
    assert readiness["same_request_redraw_of_u"] is True
    assert readiness["later_flight_interpretation"] == REDRAW_SENTENCE
    assert readiness["provider_called"] is False
    assert readiness["provider_T"] is None
    assert readiness["measured"] is False
    assert readiness["official_scores_rewritten"] is False
    assert readiness["official_target_lowered"] is False
    assert readiness["ceiling"]["default"] is None
    assert readiness["ceiling"]["remaining_is_not_a_default"] is True
    assert readiness["flight_paths"]["T1"]["cases"] == 840
    assert readiness["flight_paths"]["T2"]["cases"] == 840
    assert readiness["flight_paths"]["T1"]["dropped"] == 0
    assert readiness["not_the_official_compressor_robustness_flights"] is True
    assert readiness["ready_at_is_peak"] is False
    index = [
        json.loads(line)
        for line in (ROOT / "followon" / "flight_plan_index.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(index) == 1680
    assert sum(row["arm"] == "T1" and row["included"] and not row["dropped"] for row in index) == 840
    assert sum(row["arm"] == "T2" and row["identical_to_u"] for row in index) == 840
    assert all(row["shares_official_u_answer"] is False for row in index)


def test_full_catalogue_plan_keeps_every_case():
    from tool_compression.count import study_counters

    counter, _sensitivity = study_counters()
    rows = catalogue_plan(_study(), counter)
    assert len(rows) == EXPECTED_CASES * len(ARMS)
    for arm in ARMS:
        selected = arm_rows(rows, arm)
        assert len(selected) == 840
        assert all(row["included"] and row["dropped"] is False for row in selected)
        assert all(row["identical_to_u"] for row in selected)
        assert {row["category"] for row in selected} == {"multiple", "simple_python", "irrelevance"}
    groups = sequential_groups(rows)
    assert sum(group["logical_assignments"] for group in groups) == 1680
    assert len(groups) == 840
    assert all(group["shares_official_u_answer"] is False for group in groups)
    assert all(group["members"] == ["T1", "T2"] for group in groups)


def test_identical_to_u_is_not_a_reason_to_drop_and_alias_case_stays():
    station = "Find station records; also called station search; also called railhead search."
    rows = plan_record(_record("multiple", 0, station), One(), "multiple")
    assert len(rows) == 2
    assert all(row["dropped"] is False and row["included"] is True for row in rows)
    plain = plan_record(_record("multiple", 1), One(), "multiple")
    assert all(row["identical_to_u"] and row["dropped"] is False for row in plain)


def test_generation_body_is_thinking_off_flash_and_refuses_the_scoring_alias():
    from tool_compression.followon_flight import assert_generation_body

    body = flight_body(
        [{"role": "user", "content": "List stations."}],
        [{"type": "function", "function": {"name": "lookup"}}],
    )
    assert body["model"] == "deepseek-flash"
    assert body["thinking"] == {"type": "disabled"}
    assert body["temperature"] == 0.001
    assert body["store"] is False
    refused = dict(body)
    refused["model"] = SCORING_ALIAS
    with pytest.raises(ScoringAliasGenerateRefused):
        assert_generation_body(refused)


def test_plan_command_does_not_go_live_or_import_the_client(tmp_path, monkeypatch):
    import tool_compression.followon_live as live

    monkeypatch.delenv(CEILING_ENV, raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr(live, "live_client", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("live client")))
    monkeypatch.setattr(live, "require_api_key", lambda: (_ for _ in ()).throw(AssertionError("api key")))
    code = main(
        [
            "followon-flight",
            "--arm",
            "T1",
            "--bfcl-root",
            str(tmp_path),
            "--out",
            str(tmp_path / "out"),
            "--live",
        ]
    )
    assert code == 2


def test_plan_writes_840_without_calling_a_provider(tmp_path, monkeypatch):
    import tool_compression.followon_live as live

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr(live, "live_client", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("live client")))
    data = tmp_path / "data"
    data.mkdir()
    for category, count in (("multiple", 200), ("simple_python", 400), ("irrelevance", 240)):
        lines = [json.dumps(_record(category, index)) for index in range(count)]
        (data / f"BFCL_v4_{category}.json").write_text("\n".join(lines) + "\n", encoding="utf-8")
    out = tmp_path / "plan"
    code = main(
        [
            "followon-flight",
            "--arm",
            "both",
            "--ceiling-cny",
            "48.74670004",
            "--bfcl-root",
            str(data),
            "--out",
            str(out),
        ]
    )
    assert code == 0
    for arm in ARMS:
        summary = json.loads((out / arm / "flight_summary.json").read_text(encoding="utf-8"))
        assert summary["started"] is False
        assert summary["provider_called"] is False
        assert summary["live"] is False
        assert summary["arms"][arm]["cases"] == 840
        assert summary["arms"][arm]["provider_T_sum"] is None
        assert summary["provider_T_invented"] is False
        assert summary["ceiling_default"] is None
        index = [
            json.loads(line)
            for line in (out / arm / "plan_index.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert len(index) == 840
        evaluate = json.loads((out / arm / "official_evaluate_command.json").read_text(encoding="utf-8"))
        assert evaluate["generate"] is False
        assert evaluate["invoked"] is False
        assert "evaluate" in evaluate["argv"]
        assert "generate" not in evaluate["argv"]
        comparison = json.loads((out / arm / "comparison_versus_official_u.json").read_text(encoding="utf-8"))
        assert comparison["provider_T_invented"] is False
        assert comparison["revises_official_c_versus_u"] is False
        assert all(row["provider_T_sum"] is None for row in comparison["rows"])


def test_compare_leaves_unflown_t_null_and_does_not_rewrite_official_scores(tmp_path):
    settlement = (ROOT / "official" / "settlement" / "official_settlement.json").read_bytes()
    identity = reconfirm_committed_identity(ROOT)
    report = comparison_versus_official_u(ROOT, None, identity)
    assert report["same_request_redraw_of_u"] is True
    assert report["interpretation"] == REDRAW_SENTENCE
    assert report["official_primary_S_LU"] == {"numerator": 1398, "denominator": 121018, "revised": False}
    assert all(row["status"] == "unflown" and row["provider_T_sum"] is None for row in report["rows"])
    assert all(row["official_target_applies_to_this_comparison"] is False for row in report["rows"])
    usage = {
        "T1": {"categories": {"multiple": [10] * 200, "simple_python": [10] * 400, "irrelevance": [10] * 240}},
        "T2": {"categories": {"multiple": [10] * 199}},
    }
    measured = comparison_versus_official_u(ROOT, usage, identity)
    t1 = next(row for row in measured["rows"] if row["arm"] == "T1" and row["category"] == "multiple")
    t2 = next(row for row in measured["rows"] if row["arm"] == "T2" and row["category"] == "multiple")
    assert t1["status"] == "measured"
    assert t1["provider_T_sum"] == 2000
    assert t1["saving_versus_official_U"]["denominator"] == 121018
    assert t1["prices_applied_to_T"] is False
    assert t1["cache_hits_subtracted"] is False
    assert t1["revises_official_c_versus_u"] is False
    assert t2["status"] == "unflown"
    assert t2["provider_T_sum"] is None
    destination = tmp_path / "comparison.json"
    code = main(["followon-compare", "--out", str(destination)])
    assert code == 0
    saved = json.loads(destination.read_text(encoding="utf-8"))
    assert saved["provider_T_invented"] is False
    assert (ROOT / "official" / "settlement" / "official_settlement.json").read_bytes() == settlement


def test_score_command_evaluates_and_does_not_forward_a_key(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    seen = tmp_path / "seen.json"
    bfcl = tmp_path / "bfcl"
    bfcl.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys\n"
        f"open({str(seen)!r}, 'w').write(json.dumps({{'argv': sys.argv, 'key': os.environ.get('DEEPSEEK_API_KEY')}}))\n",
        encoding="utf-8",
    )
    bfcl.chmod(0o755)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sentinel-not-a-key")
    code = main(
        [
            "followon-score",
            "--arm",
            "T1",
            "--bfcl",
            str(bfcl),
            "--project-root",
            str(project),
        ]
    )
    assert code == 0
    payload = json.loads(seen.read_text(encoding="utf-8"))
    assert payload["argv"][1] == "evaluate"
    assert "generate" not in payload["argv"]
    assert payload["key"] == "UNUSED_OFFICIAL_EVAL_NO_PROVIDER_CALL"
    argv = official_evaluate_argv(project / "bfcl_result", project / "bfcl_score", bfcl="bfcl")
    assert argv[1] == "evaluate"
    with pytest.raises(ScoringAliasGenerateRefused):
        from tool_compression.official_score import build_bfcl_argv

        build_bfcl_argv(
            "generate",
            model=SCORING_ALIAS,
            test_category="multiple",
            result_dir="result",
            score_dir="score",
        )


def test_scripted_execution_keeps_prompt_tokens_whole(tmp_path):
    from tool_compression.followon_live import ScriptedClient, execute_plans

    body = flight_body([{"role": "user", "content": "List stations."}], [{"type": "function", "function": {"name": "lookup"}}])
    calls = {"n": 0}

    def handler(_body):
        calls["n"] += 1
        if calls["n"] == 1:
            return 503, {"error": {"code": "overloaded"}}
        return 200, {
            "choices": [{"message": {"role": "assistant", "content": "none"}}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 4,
                "prompt_tokens_details": {"cached_tokens": 40},
            },
        }

    delays = []
    summary = execute_plans(
        [
            {
                "category": "multiple",
                "case_id": "multiple_0",
                "members": ["T1"],
                "body": body,
            }
        ],
        ceiling=Decimal("48.74670004"),
        client=ScriptedClient(handler),
        out=tmp_path / "live",
        clock=lambda: _hkt(2026, 11, 23, 20, 0),
        sleep=delays.append,
    )
    assert summary["provider_called"] is True
    assert summary["prices_applied_to_T"] is False
    assert summary["cache_hits_subtracted_from_T"] is False
    assert delays == [1]
    ledger = json.loads((tmp_path / "live" / "spend_ledger.json").read_text(encoding="utf-8"))
    received = [row for row in ledger["physical"] if row["status"] == "received"]
    assert received[0]["prompt_tokens"] == 100
    assert received[0]["cached_input_tokens"] == 40
    assert received[0]["cache_hits_subtracted"] is False
    with pytest.raises(FollowOnFlightRefused):
        execute_plans(
            [{"category": "multiple", "case_id": "multiple_0", "members": ["T1"], "body": body}],
            ceiling=Decimal("48.74670004"),
            client=ScriptedClient(handler),
            out=tmp_path / "peak",
            clock=lambda: _hkt(2026, 11, 23, 10, 0),
            sleep=lambda _seconds: None,
        )


def test_refused_response_model_does_not_become_provider_t(tmp_path):
    from tool_compression.followon_live import ScriptedClient, execute_plans

    body = flight_body([{"role": "user", "content": "List stations."}], [])
    summary = execute_plans(
        [{"category": "multiple", "case_id": "multiple_0", "members": ["T1"], "body": body}],
        ceiling=Decimal("48.74670004"),
        client=ScriptedClient(
            lambda _body: (
                200,
                {
                    "model": "deepseek-chat",
                    "choices": [{"message": {"role": "assistant", "content": "x"}}],
                    "usage": {"prompt_tokens": 9, "completion_tokens": 1},
                },
            )
        ),
        out=tmp_path / "bad-model",
        clock=lambda: _hkt(2026, 11, 23, 20, 0),
        sleep=lambda _seconds: None,
    )
    assert summary["stop_reason"] == "response_model"
    assert summary["provider_T_invented"] is False
    saved = json.loads((tmp_path / "bad-model" / "prompt_tokens.json").read_text(encoding="utf-8"))
    assert saved["arms"]["T1"]["categories"] == {}


def test_configs_are_the_phrase_pair_not_the_official_compressor_retunes():
    assert T1_CONFIG.contrast_numerator == 0
    assert T2_CONFIG.contrast_numerator == 1
    assert T2_CONFIG.contrast_denominator == 2
    assert T1_CONFIG.retention_numerator == 3
    assert T1_CONFIG.retention_denominator == 4
    assert T1_CONFIG.as_dict()["retunes_closed_official_run"] is False
    text = (ROOT / "followon" / "FLIGHT.md").read_text(encoding="utf-8")
    assert "does not implement the official-compressor robustness flights" in text
    assert pre_call_reserve_cny() == Decimal("2.572864")


def test_shell_refuses_generate(tmp_path):
    import subprocess

    script = ROOT / "scripts" / "run_followon_evaluate.sh"
    completed = subprocess.run(["bash", str(script), "generate"], check=False, capture_output=True, text=True)
    assert completed.returncode == 2
