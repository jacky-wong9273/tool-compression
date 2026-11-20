"""Exploratory H50 and H25. No provider call and no network."""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import json

import pytest

from tool_compression.compress import compress
from tool_compression.config import DEFAULT_CONFIG
from tool_compression.exploratory import (
    EVALUATE_DECODER_ALIAS,
    H50_SPEC_VERSION,
    accept_ceiling,
    assert_ceiling_not_raised,
    assert_frozen,
    billed_basis_t,
    classify_case,
    flight_groups,
    frozen_config,
    official_evaluate_argv,
    refuse_generation_alias,
    setting_flyability,
    ExploratoryFlightRefused,
)
from tool_compression.exploratory_flight import (
    _write_bfcl_results,
    assert_exploratory_record,
    build_flight_plans,
    execute_exploratory_flight,
    exploratory_record,
    prepare_exploratory_flight,
)
from tool_compression.flight_spec import pre_call_reserve_cny, rate_card
from tool_compression.provider import ScriptedClient, flight_request
from tool_compression.__main__ import main

ROOT = Path(__file__).resolve().parents[1]


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


def description(result):
    return result["catalogue"][0]["function"]["description"]


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


def study_with(description_text, case_id="multiple_0"):
    return {
        "multiple": [bfcl_record(case_id, description_text)],
        "simple_python": [],
        "irrelevance": [],
    }


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    import urllib.request

    def banned(*args, **kwargs):
        raise AssertionError("live network is disabled in tests")

    monkeypatch.setattr(urllib.request, "urlopen", banned)


def test_h50_and_h25_are_frozen_and_the_official_cap_stays():
    h50 = frozen_config("H50")
    h25 = frozen_config("H25")
    assert (h50.retention_numerator, h50.retention_denominator) == (1, 2)
    assert (h25.retention_numerator, h25.retention_denominator) == (1, 4)
    assert h50.spec_version == H50_SPEC_VERSION
    assert h50.lambda_numerator == 1 and h50.lambda_denominator == 2
    assert h50.jaccard_numerator == 1 and h50.jaccard_denominator == 5
    assert h50.max_neighbours == 2
    assert h25.lambda_numerator == 1 and h25.max_neighbours == 2
    assert (DEFAULT_CONFIG.retention_numerator, DEFAULT_CONFIG.retention_denominator) == (3, 4)
    assert DEFAULT_CONFIG.spec_version == "week1.0"
    with pytest.raises(ValueError):
        assert_frozen(
            "H50",
            frozen_config("H50").__class__(
                spec_version=H50_SPEC_VERSION,
                retention_numerator=1,
                retention_denominator=2,
                lambda_numerator=3,
            ),
        )


def test_tighter_caps_change_optional_spans_without_touching_the_official_config():
    catalogue = [tool("AAAA. bb. cc. dd. ee.")]
    official = description(compress(catalogue, "C", DEFAULT_CONFIG, Words()))
    h50 = description(compress(catalogue, "C", frozen_config("H50"), Words()))
    h25 = description(compress(catalogue, "C", frozen_config("H25"), Words()))
    assert official == "AAAA. bb. cc."
    assert h50 == "AAAA. bb."
    assert h25 == "AAAA."
    assert description(compress(catalogue, "P", frozen_config("H50"), Words())) == h50
    lifted = compress([tool("One two three four. x.")], "C", frozen_config("H25"), Words())
    assert lifted["traces"][0]["fields"][0]["uplift"] is True


def test_identity_and_flyability_do_not_treat_u_or_official_l_as_a_new_request():
    same = {"U": "u", "P": "l", "I": "l", "C": "l"}
    official = {"U": "u", "P": "l", "I": "l", "C": "l"}
    classified = classify_case(same, official)
    assert classified["identical_to_official_l"] is True
    assert classified["new_request"] is False
    assert flight_groups("H50", same, "l") == []
    changed = {"U": "u", "P": "h", "I": "h", "C": "h"}
    assert flight_groups("H50", changed, "l") == [("H50",)]
    split = {"U": "u", "P": "l", "I": "n", "C": "n"}
    assert flight_groups("H25", split, "l") == [("I", "C")]
    blocked = setting_flyability(
        [{"preparation_failure": False, "identical_to_u": False, "identical_to_official_l": True, "new_request": False}],
        coverage_complete=True,
        hash_reproduction_matched=True,
    )
    assert blocked["flyable"] is False
    assert blocked["reason"] == "complete_requests_identical_to_official_L"
    open_setting = setting_flyability(
        [{"preparation_failure": False, "identical_to_u": False, "identical_to_official_l": False, "new_request": True}],
        coverage_complete=True,
        hash_reproduction_matched=True,
    )
    assert open_setting["flyable"] is True


def test_ceiling_is_required_and_cannot_be_raised():
    with pytest.raises(ExploratoryFlightRefused):
        accept_ceiling(None)
    with pytest.raises(ExploratoryFlightRefused):
        accept_ceiling("0")
    with pytest.raises(ExploratoryFlightRefused):
        accept_ceiling(1.5)
    assert accept_ceiling("12.50") == Decimal("12.50")
    with pytest.raises(ExploratoryFlightRefused):
        assert_ceiling_not_raised(Decimal("10"), Decimal("11"))
    record = exploratory_record("H50", Decimal("10"))
    assert record["spending_ceiling"]["amount"] == "10"
    assert record["spending_ceiling"]["hardcoded"] is False
    assert record["rate_card"] == rate_card()
    assert record["model"] == "deepseek-flash"
    assert record["handler_alias"] is None
    record["spending_ceiling"]["amount"] = "11"
    with pytest.raises(ExploratoryFlightRefused):
        assert_exploratory_record(record, Decimal("10"), "H50")


def test_generation_alias_is_refused_and_evaluate_is_not_generate():
    with pytest.raises(ExploratoryFlightRefused):
        refuse_generation_alias("DeepSeek-V3.2-Exp-FC")
    argv = official_evaluate_argv(Path("/tmp/results"), Path("/tmp/scores"))
    assert argv[3] == "evaluate"
    assert "generate" not in argv
    assert EVALUATE_DECODER_ALIAS in argv
    assert "deepseek-flash" not in argv


def test_billed_basis_is_prompt_tokens():
    payload = {
        "usage": {
            "prompt_tokens": 1000,
            "completion_tokens": 4,
            "prompt_tokens_details": {"cached_tokens": 800},
        }
    }
    billed = billed_basis_t(payload)
    assert billed["T"] == 1000
    assert billed["basis"] == "provider_prompt_tokens"
    assert billed["price_weighted"] is False
    assert billed["cache_subtracted"] is False


def test_plan_does_not_start_a_provider_and_skips_official_l(tmp_path, monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("live client constructed")

    monkeypatch.setattr("tool_compression.exploratory_flight.live_client", boom)
    study = study_with("AAAA. bb. cc. dd. ee.")
    plans, stats = build_flight_plans(study, "H50", Words())
    assert stats["cases_with_new_request"] == 1
    assert stats["identical_to_official_l"] is False
    assert stats["identical_to_u"] is False
    assert plans[0]["members"] == ("H50",)
    audit = {
        "label": "H50",
        "flyable": True,
        "provider_called": False,
        "network_used": False,
        "cases_with_new_request": stats["cases_with_new_request"],
        "identical_to_u": stats["identical_to_u"],
        "identical_to_official_l": stats["identical_to_official_l"],
    }
    summary, planned = prepare_exploratory_flight(study, "H50", Decimal("10"), audit, tmp_path, Words())
    assert summary["started"] is False
    assert summary["provider_called"] is False
    assert summary["network_used"] is False
    assert summary["stop_reason"] == "not_started"
    assert planned[0]["members"] == ("H50",)
    written = (tmp_path / "plan_index.jsonl").read_text(encoding="utf-8")
    assert "AAAA" not in written
    assert '"H50"' in written
    command = json.loads((tmp_path / "official_evaluate_command.json").read_text(encoding="utf-8"))
    assert command["invoked"] is False
    assert "generate" not in command["argv"]
    with pytest.raises(ExploratoryFlightRefused):
        prepare_exploratory_flight(
            study,
            "H50",
            Decimal("10"),
            {"label": "H50", "flyable": False, "flyable_reason": "complete_requests_identical_to_official_L"},
            tmp_path,
            Words(),
        )


def test_executor_stops_on_the_supplied_ceiling_without_a_provider_call(tmp_path):
    record = exploratory_record("H50", Decimal("3"))
    plans = [_manual_plan("multiple_0"), _manual_plan("multiple_1")]

    def handler(body):
        assert body["model"] == "deepseek-flash"
        assert body["thinking"] == {"type": "disabled"}
        return 200, _payload(1_000_000, 393216)

    client = ScriptedClient(handler)
    summary = execute_exploratory_flight(
        record,
        plans,
        Decimal("3"),
        tmp_path,
        client=client,
        live=False,
        clock=lambda: datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc),
        sleep=lambda _seconds: None,
    )
    assert len(client.bodies) == 1
    assert summary["provider_called"] is False
    assert summary["network_used"] is False
    assert summary["stop_reason"] == "remaining_budget_may_be_insufficient"
    assert summary["ceiling_cny"] == "3"
    assert summary["ceiling_raised"] is False
    assert Decimal(summary["cumulative_cny"]) <= Decimal("3")
    assert summary["billed_basis_T_prompt_tokens"] == 1_000_000
    assert summary["billed_basis_T_prompt_tokens"] != pre_call_reserve_cny()


def test_live_flag_refuses_a_scripted_client_and_alias_bodies_are_not_sent(tmp_path):
    record = exploratory_record("H25", Decimal("10"))
    plan = _manual_plan("multiple_0", members=("H25",))
    client = ScriptedClient(lambda body: (200, _payload(10, 1)))
    with pytest.raises(ExploratoryFlightRefused):
        execute_exploratory_flight(record, [plan], Decimal("10"), tmp_path, client=client, live=True)
    assert client.bodies == []
    plan["body"]["model"] = "DeepSeek-V3.2-Exp-FC"
    with pytest.raises(ExploratoryFlightRefused):
        execute_exploratory_flight(record, [plan], Decimal("10"), tmp_path, client=client, live=False)
    assert client.bodies == []
    plan = _manual_plan("multiple_2", members=("U",))
    with pytest.raises(ExploratoryFlightRefused):
        execute_exploratory_flight(record, [plan], Decimal("10"), tmp_path, client=client, live=False)
    assert client.bodies == []


def test_saved_output_files_use_the_bfcl_result_name(tmp_path):
    _write_bfcl_results(
        tmp_path / "DeepSeek-V3.2-Exp-FC",
        {"multiple": [{"id": "multiple_0", "result": [{"fn": "{}"}], "input_token_count": 5, "output_token_count": 1}]},
    )
    path = tmp_path / "DeepSeek-V3.2-Exp-FC" / "BFCL_v4_multiple_result.json"
    row = json.loads(path.read_text(encoding="utf-8"))
    assert row["input_token_count"] == 5
    assert row["id"] == "multiple_0"


def test_cli_refuses_a_missing_ceiling_and_a_score_without_saved_provider_output(tmp_path):
    assert main(["exploratory-flight", "--setting", "H50", "--bfcl-root", "x", "--out", str(tmp_path)]) == 1
    with pytest.raises(SystemExit):
        main(["exploratory-audit", "--bfcl-root", "x", "--out", "y", "--lambda", "1"])
    assert main(["exploratory-flight", "--setting", "H50", "--bfcl-root", "x", "--out", str(tmp_path), "--score"]) == 1


def test_flight_source_does_not_hard_code_a_ceiling():
    text = (ROOT / "src" / "tool_compression" / "exploratory_flight.py").read_text(encoding="utf-8")
    assert 'Decimal("50")' not in text
    assert 'Decimal("100")' not in text
    assert "CEILING_CNY" not in text


def test_historical_packet_and_official_config_are_untouched():
    packet = (ROOT / "evidence" / "WEEK1_EVIDENCE_PACKET.md").read_text(encoding="utf-8")
    assert "Exploratory caps 0.50 and 0.25 were not run." in packet
    assert DEFAULT_CONFIG.as_dict()["retention_r"] == "3/4"


def test_committed_audit_matches_its_hash_rows():
    audit_path = ROOT / "evidence" / "exploratory" / "audit.json"
    payload = json.loads(audit_path.read_text(encoding="utf-8"))
    assert payload["provider_called"] is False
    assert payload["network_used"] is False
    assert payload["official_target_lowered"] is False
    assert payload["official_result"]["target_lowered"] is False
    assert payload["official_result"]["S_LU"] == "1398/121018"
    assert payload["official_hash_reproduction"]["matched"] is True
    assert payload["data_pin"]["matched"] is True
    assert payload["official_unique_request_groups"]["all_categories"] == 1513
    assert payload["cases"] == 840
    identity = payload["h50_h25_request_identity"]
    assert identity["complete_requests_identical"] is True
    assert identity["different_cases"] == 0
    assert identity["identical_cases"] == 840
    for label, filename in (("H50", "h50_request_hashes.jsonl"), ("H25", "h25_request_hashes.jsonl")):
        setting = payload["settings"][label]
        rows = [
            json.loads(line)
            for line in (ROOT / "evidence" / "exploratory" / filename).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert len(rows) == 840
        assert setting["provider_called"] is False
        assert setting["network_used"] is False
        assert setting["coverage_complete"] is True
        assert setting["failures"] == []
        assert setting["ready_for_evaluation"] is True
        assert setting["cap_was_loosened"] is False
        counts = {name: 0 for name in ("multiple", "simple_python", "irrelevance")}
        new_cases = 0
        coincide = 0
        for row in rows:
            counts[row["category"]] += 1
            assert row["preparation_failure"] is False
            assert row["u_matches_official_u"] is True
            if row["new_request"]:
                new_cases += 1
            if row["p_i_c_coincide"]:
                coincide += 1
            if row["identical_to_official_l"] or row["identical_to_u"]:
                assert row["new_request"] is False
        assert counts == {"multiple": 200, "simple_python": 400, "irrelevance": 240}
        assert setting["cases_with_new_request"] == new_cases
        assert setting["p_i_c_coincide"] is (coincide == 840)
        assert setting["flyable"] is (new_cases > 0)
        assert setting["new_request_ids"] == [
            "multiple/multiple_40",
            "simple_python/simple_python_99",
            "simple_python/simple_python_316",
        ]
        if setting["identical_to_official_l"] or setting["identical_to_u"]:
            assert setting["flyable"] is False
        for category, summary in setting["categories"].items():
            assert summary["provider_called"] is False
            assert summary["network_used"] is False
            assert summary["n_records"] == counts[category]
            assert summary["coverage_complete"] is True
            assert summary["local_token_sums"]["tokenizer"] == "o200k_base"
            assert summary["local_token_sums"]["provider_T"] is False
            assert "uplift" in summary
            assert "contrast_activity_f" in summary
            assert "c_minus_i_cases" in summary
            assert summary["stop_and_field_status"]["arms"]["C"]["reasons"]


def _manual_plan(case_id, members=("H50",)):
    body = flight_request([{"role": "user", "content": "q"}], [tool("short")])
    from tool_compression.prepare import request_hash

    return {
        "category": "multiple",
        "case_id": case_id,
        "replicate": 0,
        "members": members,
        "response_group_id": "g/" + case_id,
        "request_sha256": request_hash(body),
        "body": body,
    }


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
