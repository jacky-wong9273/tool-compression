"""Full-catalogue settings A and B. No provider call and no network."""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import json

import pytest

from tool_compression.config import DEFAULT_CONFIG, Config
from tool_compression.exploratory import (
    A_SPEC_VERSION,
    B_SPEC_VERSION,
    H50_SPEC_VERSION,
    accept_ceiling,
    assert_frozen,
    flight_groups,
    frozen_config,
    full_catalogue_groups,
    ExploratoryFlightRefused,
)
from tool_compression.exploratory_audit import build_token_comparison
from tool_compression.exploratory_flight import (
    build_flight_plans,
    build_full_catalogue_plans,
    execute_exploratory_flight,
    full_catalogue_record,
    prepare_full_catalogue_flight,
)
from tool_compression.provider import ScriptedClient, flight_request
from tool_compression.__main__ import main

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "full-catalogue"


class Words:
    name = "words"

    def count(self, text: str) -> int:
        return len(text.split())


def tool(description):
    return {
        "type": "function",
        "function": {
            "name": "ta",
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {"x": {"type": "string", "description": "xxxx"}},
                "required": ["x"],
            },
        },
    }


def bfcl_record(case_id, description_text):
    return {
        "id": case_id,
        "question": [[{"role": "user", "content": "q"}]],
        "function": [
            {
                "name": "fn",
                "description": description_text,
                "parameters": {
                    "type": "dict",
                    "properties": {"x": {"type": "string", "description": "name"}},
                },
            }
        ],
    }


def study_with(records):
    return {"multiple": records, "simple_python": [], "irrelevance": []}


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    import urllib.request

    def banned(*args, **kwargs):
        raise AssertionError("live network is disabled in tests")

    monkeypatch.setattr(urllib.request, "urlopen", banned)


def test_setting_b_keeps_lambda_one_quarter_and_official_pair_stays_closed():
    setting_b = frozen_config("B")
    setting_a = frozen_config("A")
    assert (setting_b.retention_numerator, setting_b.retention_denominator) == (3, 4)
    assert (setting_b.lambda_numerator, setting_b.lambda_denominator) == (1, 4)
    assert setting_b.spec_version == B_SPEC_VERSION
    assert setting_b.jaccard_numerator == 1 and setting_b.jaccard_denominator == 5
    assert setting_b.max_neighbours == 2
    assert setting_b.tokenizer_name == "o200k_base"
    assert (setting_a.retention_numerator, setting_a.retention_denominator) == (1, 2)
    assert (setting_a.lambda_numerator, setting_a.lambda_denominator) == (1, 2)
    assert setting_a.spec_version == A_SPEC_VERSION
    assert_frozen("B", setting_b)
    with pytest.raises(ValueError, match="not setting B"):
        assert_frozen(
            "B",
            Config(
                spec_version=B_SPEC_VERSION,
                retention_numerator=3,
                retention_denominator=4,
                lambda_numerator=1,
                lambda_denominator=2,
            ),
        )
    with pytest.raises(ValueError, match="keeps lambda at 1/4"):
        assert_frozen(
            "B",
            Config(
                spec_version=B_SPEC_VERSION,
                retention_numerator=3,
                retention_denominator=4,
                lambda_numerator=1,
                lambda_denominator=8,
            ),
        )
    with pytest.raises(ValueError, match="lambda stays 1/2"):
        assert_frozen(
            "A",
            Config(
                spec_version=A_SPEC_VERSION,
                retention_numerator=1,
                retention_denominator=2,
                lambda_numerator=1,
                lambda_denominator=4,
            ),
        )
    with pytest.raises(ValueError, match="official r=0.75 is not an exploratory setting"):
        assert_frozen(
            "H50",
            Config(spec_version=H50_SPEC_VERSION, retention_numerator=3, retention_denominator=4),
        )
    assert (DEFAULT_CONFIG.retention_numerator, DEFAULT_CONFIG.retention_denominator) == (3, 4)
    assert (DEFAULT_CONFIG.lambda_numerator, DEFAULT_CONFIG.lambda_denominator) == (1, 2)


def test_full_catalogue_plan_keeps_cases_identical_to_official_l():
    same = {"U": "u", "P": "l", "I": "l", "C": "l"}
    assert flight_groups("H50", same, "l") == []
    assert full_catalogue_groups("A", same) == [("A",)]
    assert full_catalogue_groups("B", same) == [("B",)]
    study = study_with(
        [
            bfcl_record("multiple_0", "AAAA."),
            bfcl_record("multiple_1", "AAAA. bb. cc. dd. ee."),
        ]
    )
    plans, stats = build_full_catalogue_plans(study, "A", Words())
    assert stats["cases"] == 2
    assert stats["groups"] == 2
    assert stats["drops_identical_to_official_l"] is False
    assert stats["identical_to_official_l_cases_planned"] == 1
    assert stats["cases_planned"] == 2
    assert {plan["case_id"] for plan in plans} == {"multiple_0", "multiple_1"}
    identical = [plan for plan in plans if plan["identical_to_official_l"]]
    assert len(identical) == 1
    assert identical[0]["members"] == ("A",)
    assert "L" not in identical[0]["members"]
    differing_only, differing_stats = build_flight_plans(study, "H50", Words())
    assert differing_stats["groups"] == 1
    assert {plan["case_id"] for plan in differing_only} == {"multiple_1"}
    planned_b, stats_b = build_full_catalogue_plans(study, "B", Words())
    assert stats_b["cases"] == 2
    assert stats_b["groups"] == 2
    assert stats_b["identical_to_official_l"] is True
    assert stats_b["identical_to_official_l_cases_planned"] == 2
    assert stats_b["cases_with_new_request"] == 0
    assert all(plan["members"] == ("B",) for plan in planned_b)
    assert all(plan["identical_to_official_l"] for plan in planned_b)


def test_plan_does_not_start_a_provider_and_requires_a_supplied_ceiling(tmp_path, monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("live client constructed")

    monkeypatch.setattr("tool_compression.exploratory_flight.live_client", boom)
    monkeypatch.setattr("tool_compression.__main__.live_client", boom)
    study = study_with([bfcl_record("multiple_0", "AAAA.")])
    plans, stats = build_full_catalogue_plans(study, "B", Words())
    audit = {
        "label": "B",
        "full_catalogue_plan_ready": True,
        "full_catalogue_reason": "complete_requests_identical_to_official_L",
        "drops_identical_to_official_l": False,
        "provider_called": False,
        "network_used": False,
        "paid_call_started": False,
        "cases_with_new_request": stats["cases_with_new_request"],
        "identical_to_u": stats["identical_to_u"],
        "identical_to_official_l": stats["identical_to_official_l"],
        "cases_identical_to_official_l": stats["identical_to_official_l_cases_planned"],
        "cases_planned": stats["cases_planned"],
    }
    summary, planned = prepare_full_catalogue_flight(study, "B", Decimal("10"), audit, tmp_path, Words())
    assert summary["started"] is False
    assert summary["live"] is False
    assert summary["provider_called"] is False
    assert summary["network_used"] is False
    assert summary["paid_call_started"] is False
    assert summary["cases_planned"] == 1
    assert planned[0]["identical_to_official_l"] is True
    assert planned[0]["members"] == ("B",)
    written = (tmp_path / "plan_index.jsonl").read_text(encoding="utf-8")
    assert "AAAA" not in written
    assert '"B"' in written
    command = json.loads((tmp_path / "official_evaluate_command.json").read_text(encoding="utf-8"))
    assert command["invoked"] is False
    assert command["command"] == "evaluate"
    assert "generate" not in command["argv"]
    with pytest.raises(ExploratoryFlightRefused):
        accept_ceiling(None)
    assert main(["full-catalogue-flight", "--setting", "B", "--bfcl-root", "x", "--out", str(tmp_path)]) == 1
    with pytest.raises(SystemExit):
        main(["full-catalogue-audit", "--bfcl-root", "x", "--out", "y", "--lambda", "1/4"])
    with pytest.raises(SystemExit):
        main(
            [
                "full-catalogue-flight",
                "--setting",
                "H50",
                "--ceiling-cny",
                "10",
                "--bfcl-root",
                "x",
                "--out",
                str(tmp_path),
            ]
        )


def test_live_flag_refuses_a_scripted_client(tmp_path):
    record = full_catalogue_record("B", Decimal("10"))
    assert record["purpose"] == "exploratory-full-catalogue"
    assert record["spending_ceiling"]["hardcoded"] is False
    assert record["drops_identical_to_official_l"] is False
    assert record["settings"]["lambda"] == "1/4"
    body = flight_request([{"role": "user", "content": "q"}], [tool("short")])
    from tool_compression.prepare import request_hash

    plan = {
        "category": "multiple",
        "case_id": "multiple_0",
        "replicate": 0,
        "members": ("B",),
        "response_group_id": "g/multiple_0",
        "request_sha256": request_hash(body),
        "body": body,
    }
    client = ScriptedClient(lambda payload: (200, _payload(10, 1)))
    with pytest.raises(ExploratoryFlightRefused):
        execute_exploratory_flight(record, [plan], Decimal("10"), tmp_path, client=client, live=True)
    assert client.bodies == []
    summary = execute_exploratory_flight(
        record,
        [plan],
        Decimal("10"),
        tmp_path,
        client=client,
        live=False,
        clock=lambda: datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc),
        sleep=lambda _seconds: None,
    )
    assert summary["provider_called"] is False
    assert summary["paid_call_started"] is False
    assert summary["network_used"] is False
    assert summary["full_catalogue"] is True
    assert client.bodies[0]["model"] == "deepseek-flash"
    assert client.bodies[0]["thinking"] == {"type": "disabled"}


def test_flight_source_does_not_default_a_ceiling():
    flight = (ROOT / "src" / "tool_compression" / "exploratory_flight.py").read_text(encoding="utf-8")
    entry = (ROOT / "src" / "tool_compression" / "__main__.py").read_text(encoding="utf-8")
    for text in (flight, entry):
        assert "48.74670004" not in text
        assert "EXPLORATORY_CEILING_CNY" not in text
        assert 'Decimal("50")' not in text
    assert "os.environ" not in flight


def test_comparison_keeps_official_s_lu_and_leaves_unflown_provider_t_empty():
    official = {
        "multiple": {"U": 10, "P": 8, "I": 8, "C": 8},
        "simple_python": {"U": 10, "P": 9, "I": 9, "C": 9},
        "irrelevance": {"U": 10, "P": 10, "I": 10, "C": 10},
    }

    def setting(arm_by_category):
        categories = {}
        for name, arm in arm_by_category.items():
            categories[name] = {
                "local_token_sums": {"sums": {"U": official[name]["U"], "P": arm, "I": arm, "C": arm}}
            }
        return {"categories": categories}

    comparison = build_token_comparison(
        {"A": setting({"multiple": 7, "simple_python": 9, "irrelevance": 10}), "B": setting({"multiple": 8, "simple_python": 9, "irrelevance": 10})},
        official,
    )
    assert comparison["exploratory_only"] is True
    assert comparison["revises_official_S_LU"] is False
    assert comparison["official_billed"]["S_LU"] == "1398/121018"
    assert comparison["official_billed"]["U"] == 121018
    assert comparison["official_billed"]["derived_L"] == 119620
    assert comparison["provider_T_for_unflown_arms"] == {"A": None, "B": None}
    assert comparison["official_billed"]["provider_T_A"] is None
    assert comparison["official_billed"]["provider_T_B"] is None
    assert comparison["official_billed"]["three_case_h50_provider_figures_spliced"] is False
    assert comparison["local_o200k_base"]["saving_versus_U_all_840"]["A"]["numerator"] == 4
    assert comparison["local_o200k_base"]["saving_versus_official_L_all_840"]["B"]["numerator"] == 0


def test_committed_full_catalogue_audit_reports_identity_and_plans_every_case():
    payload = json.loads((EVIDENCE / "audit.json").read_text(encoding="utf-8"))
    closed = json.loads((ROOT / "evidence" / "exploratory" / "audit.json").read_text(encoding="utf-8"))
    assert payload["status"] == "exploratory_only"
    assert payload["revises_official_C_versus_U"] is False
    assert payload["official_result_rewritten"] is False
    assert payload["official_result"] == closed["official_result"]
    assert payload["official_result"]["S_LU"] == "1398/121018"
    assert payload["official_result"]["primary_accuracy"]["U"] == "186/200"
    assert payload["official_result"]["primary_accuracy"]["L"] == "185/200"
    assert payload["official_result"]["target_lowered"] is False
    assert payload["provider_called"] is False
    assert payload["network_used"] is False
    assert payload["paid_call_started"] is False
    assert payload["sample_size"] == 840
    assert payload["official_hash_reproduction"]["matched"] is True
    assert payload["data_pin"]["matched"] is True
    assert payload["h50_reconfirmation"]["complete_requests_identical"] is True
    assert payload["h50_reconfirmation"]["identical_cases"] == 840
    assert payload["comparison"]["provider_T_for_unflown_arms"] == {"A": None, "B": None}
    assert payload["comparison"]["revises_official_S_LU"] is False
    assert payload["comparison"]["official_billed"]["all_840_provider_T"] is None
    assert payload["later_live_run"]["default_in_code"] is False
    assert payload["later_live_run"]["code_reads_environment"] is False
    assert payload["later_live_run"]["this_package_starts_live"] is False
    assert payload["later_live_run"]["splice_three_case_h50"] is False
    assert payload["later_live_run"]["remaining_authorized_cny"] == "48.74670004"
    h50 = closed["settings"]["H50"]
    official_local = payload["official_hash_reproduction"]["local_token_sums"]["by_category"]
    for label, filename in (("A", "a_request_hashes.jsonl"), ("B", "b_request_hashes.jsonl")):
        setting = payload["settings"][label]
        rows = _jsonl(EVIDENCE / filename)
        plan = _jsonl(EVIDENCE / f"{label.lower()}_plan_index.jsonl")
        assert len(rows) == 840
        assert len(plan) == 840
        assert setting["cases_planned"] == 840
        assert setting["plan"]["groups"] == 840
        assert setting["plan"]["drops_identical_to_official_l"] is False
        assert setting["plan"]["started"] is False
        assert setting["plan"]["provider_called"] is False
        assert setting["plan"]["ceiling_supplied"] is False
        assert setting["drops_identical_to_official_l"] is False
        assert setting["p_i_c_coincide"] is True
        assert setting["p_i_c_coincide_cases"] == 840
        assert setting["coverage_complete"] is True
        assert setting["failures"] == []
        assert setting["lambda_loosened_to_force_a_difference"] is False
        assert setting["protections_loosened"] is False
        assert setting["cap_was_loosened"] is False
        assert setting["provider_called"] is False
        assert setting["paid_call_started"] is False
        assert setting["local_token_sums"]["provider_T"] is False
        assert setting["local_token_sums"]["tokenizer"] == "o200k_base"
        identity = setting["identity"]
        assert identity["c_minus_i_cases"] == 0
        assert identity["c_minus_i_fields"] == 0
        for fraction in identity["contrast_activity_f"].values():
            assert fraction["numerator"] == 0
        planned = {(row["category"], row["case_id"]): row for row in plan}
        assert len(planned) == 840
        identical_l = 0
        for row in rows:
            assert row["preparation_failure"] is False
            assert row["p_i_c_coincide"] is True
            assert row["u_matches_official_u"] is True
            key = (row["category"], row["id"])
            assert key in planned
            assert planned[key]["identical_to_official_l"] is row["identical_to_official_l"]
            assert planned[key]["members"] == [label]
            assert "body" not in planned[key]
            assert "description" not in planned[key]
            if row["identical_to_official_l"]:
                identical_l += 1
                assert row["new_request"] is False
        assert identical_l == setting["cases_identical_to_official_l"]
        assert setting["plan"]["identical_to_official_l_cases_planned"] == identical_l
        for name, category in setting["categories"].items():
            assert category["contrast_activity_f"]["numerator"] == 0
            assert category["local_token_sums"]["sums"]["P"] == category["local_token_sums"]["sums"]["C"]
            assert category["provider_called"] is False
    setting_a = payload["settings"]["A"]
    setting_b = payload["settings"]["B"]
    assert setting_b["lambda"] == "1/4"
    assert setting_b["retention_r"] == "3/4"
    assert setting_a["lambda"] == "1/2"
    assert setting_a["retention_r"] == "1/2"
    assert setting_a["cases_with_new_request"] == 3
    assert setting_a["new_request_ids"] == [
        "multiple/multiple_40",
        "simple_python/simple_python_99",
        "simple_python/simple_python_316",
    ]
    assert setting_a["cases_identical_to_official_l"] == 837
    assert setting_a["identical_to_official_l"] is False
    assert setting_a["full_catalogue_plan_ready"] is True
    assert setting_b["identical_to_official_l"] is True
    assert setting_b["cases_identical_to_official_l"] == 840
    assert setting_b["cases_with_new_request"] == 0
    assert setting_b["new_request_ids"] == []
    assert setting_b["full_catalogue_reason"] == "complete_requests_identical_to_official_L"
    assert setting_b["full_catalogue_plan_ready"] is True
    assert setting_b["differing_only_would_send"] is False
    assert setting_a["local_token_sums"]["sums"] == h50["local_token_sums"]["sums"]
    assert setting_b["local_token_sums"]["shared_sum"] == (
        official_local["multiple"]["P"] + official_local["simple_python"]["P"] + official_local["irrelevance"]["P"]
    )
    comparison = payload["comparison"]["local_o200k_base"]
    assert comparison["all_840"]["B"] == comparison["all_840"]["official_L"]
    assert comparison["saving_versus_official_L_all_840"]["B"]["numerator"] == 0
    assert comparison["saving_versus_official_L_all_840"]["A"]["numerator"] == 35
    assert comparison["all_840"]["U"] == 177291
    assert comparison["all_840"]["official_L"] == 174224
    assert comparison["all_840"]["A"] == 174189
    text = (EVIDENCE / "COMPARISON.md").read_text(encoding="utf-8")
    assert "exploratory only" in text
    assert "1398/121018" in text
    assert "Every request is identical to official L." in text
    assert "multiple_40" in text
    assert "Provider T for setting A is not measured." in text
    assert "Provider T for setting B is not measured." in text
    assert "3-case H50" in text
    assert "bfcl evaluate" in text
    assert "48.74670004" in text
    assert "prompt_tokens" in text
    from tool_compression.exploratory_audit import render_full_catalogue_markdown

    assert render_full_catalogue_markdown(payload) == text


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _payload(prompt, completion):
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {"id": "call", "type": "function", "function": {"name": "fn", "arguments": "{}"}}
                    ],
                }
            }
        ],
        "usage": {"prompt_tokens": prompt, "completion_tokens": completion, "total_tokens": prompt + completion},
    }
