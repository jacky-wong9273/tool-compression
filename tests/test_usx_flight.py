"""Systems-test flight path for the 12-case U/S/X/SX pilot. No provider call."""

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo
import json

import pytest

from tool_compression.__main__ import main
from tool_compression.semantic_audit import load_json, package_dir
from tool_compression.usx_flight import (
    CEILING_ENV,
    EVALUATE_ALIAS,
    MAX_INPUT_TOKENS,
    MAX_OUTPUT_TOKENS,
    MODEL,
    UsxFlightRefused,
    accept_ceiling,
    assert_ceiling_not_raised,
    billed_basis_t,
    build_plans,
    classify_irrelevance,
    classify_multiple,
    evaluate_argv,
    generation_body,
    pre_call_reserve_cny,
    rate_card,
    read_ceiling_from_env,
    run_live,
    run_no_api_gate,
    schedule_at,
    shorter_request_is_not_a_call,
    spend_cny,
    usage_bill,
)

PIN = Path("/tmp/bfcl-pin")
SHANGHAI = ZoneInfo("Asia/Shanghai")
SECRET = "sk-test-secret-value"


def _pin_or_skip():
    if not (PIN / "BFCL_v4_multiple.json").is_file():
        pytest.skip("pinned BFCL files are not in this environment")
    return PIN


def _moment(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=SHANGHAI)


def _payload(reasoning=None, hit=3, miss=7, prompt=10, output=4):
    message = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {"id": "call-1", "type": "function", "function": {"name": "calculate_lcm", "arguments": "{}"}}
        ],
    }
    if reasoning is not None:
        message["reasoning_content"] = reasoning
    return {
        "choices": [{"message": message}],
        "usage": {
            "prompt_tokens": prompt,
            "completion_tokens": output,
            "prompt_cache_hit_tokens": hit,
            "prompt_cache_miss_tokens": miss,
        },
    }


class ScriptedClient:
    def __init__(self, payload):
        self.payload = payload
        self.bodies = []

    def complete(self, body):
        self.bodies.append(body)
        return self.payload


def test_ceiling_has_no_default_and_rejects_inexact_values(monkeypatch):
    monkeypatch.delenv(CEILING_ENV, raising=False)
    with pytest.raises(UsxFlightRefused):
        read_ceiling_from_env()
    with pytest.raises(UsxFlightRefused):
        accept_ceiling(None)
    with pytest.raises(UsxFlightRefused):
        accept_ceiling(1.5)
    with pytest.raises(UsxFlightRefused):
        accept_ceiling("0")
    with pytest.raises(UsxFlightRefused):
        accept_ceiling("-2")
    with pytest.raises(UsxFlightRefused):
        accept_ceiling("")
    assert accept_ceiling("0.01") == Decimal("0.01")
    with pytest.raises(UsxFlightRefused):
        assert_ceiling_not_raised(Decimal("1"), Decimal("1.01"))
    source = Path(__import__("tool_compression.usx_flight", fromlist=["usx_flight"]).__file__).read_text(encoding="utf-8")
    assert f"{CEILING_ENV} =" not in source
    assert "Decimal(\"50\")" not in source


def test_public_flash_card_and_peak_windows():
    off = rate_card("off-peak")
    peak = rate_card("peak")
    assert off["cache_hit"] == "0.02"
    assert off["cache_miss"] == "1"
    assert off["output"] == "4"
    assert peak["cache_hit"] == "0.04"
    assert peak["cache_miss"] == "2"
    assert peak["output"] == "8"
    assert off["locked_offpeak_validation_card"] is False
    assert peak["locked_offpeak_validation_card"] is False
    assert off["source"] == "https://api-docs.deepseek.com/zh-cn/quick_start/pricing/"
    assert schedule_at(_moment(2026, 11, 16, 8, 59)) == "off-peak"
    assert schedule_at(_moment(2026, 11, 16, 9, 0)) == "peak"
    assert schedule_at(_moment(2026, 11, 16, 11, 59)) == "peak"
    assert schedule_at(_moment(2026, 11, 16, 12, 0)) == "off-peak"
    assert schedule_at(_moment(2026, 11, 16, 13, 59)) == "off-peak"
    assert schedule_at(_moment(2026, 11, 16, 14, 0)) == "peak"
    assert schedule_at(_moment(2026, 11, 16, 17, 59)) == "peak"
    assert schedule_at(_moment(2026, 11, 16, 18, 0)) == "off-peak"
    assert schedule_at(_moment(2026, 11, 21, 15, 0)) == "off-peak"
    assert schedule_at(_moment(2026, 11, 22, 10, 0)) == "off-peak"
    assert pre_call_reserve_cny("off-peak") == spend_cny("off-peak", MAX_INPUT_TOKENS, 0, MAX_OUTPUT_TOKENS)
    assert pre_call_reserve_cny("peak") == Decimal("5.145728")
    assert pre_call_reserve_cny("peak") > pre_call_reserve_cny("off-peak")


def test_billed_basis_keeps_cache_hits_inside_t_and_keeps_prices_off_t():
    basis = billed_basis_t(10)
    assert basis == {"T": 10, "field": "prompt_tokens", "cache_hits_subtracted": False, "prices_applied": False}
    bill = usage_bill("peak", _payload()["usage"])
    assert bill["T"] == 10
    assert bill["cache_hit_tokens"] == 3
    assert bill["cache_miss_tokens_billed"] == 7
    assert bill["spend_cny"] == format(spend_cny("peak", 10, 3, 4), "f")
    assert Decimal(bill["spend_cny"]) == (Decimal("3") * Decimal("0.04") + Decimal("7") * Decimal("2") + Decimal("4") * Decimal("8")) / Decimal("1000000")
    missing = usage_bill("off-peak", {"prompt_tokens": 10, "completion_tokens": 4})
    assert missing["T"] == 10
    assert missing["cache_hit_tokens"] == 0
    assert missing["cache_split_missing_billed_as_miss"] is True
    assert Decimal(missing["spend_cny"]) == spend_cny("off-peak", 10, 0, 4)


def test_generation_body_is_flash_with_thinking_disabled():
    body = generation_body([{"role": "user", "content": "q"}], [{"type": "function", "function": {"name": "f"}}])
    assert body["model"] == "deepseek-flash"
    assert body["temperature"] == 0.001
    assert body["store"] is False
    assert body["thinking"] == {"type": "disabled"}
    assert "reasoning_effort" not in body
    bad = generation_body([{"role": "user", "content": "q"}], [])
    bad["model"] = EVALUATE_ALIAS
    from tool_compression.usx_flight import assert_generation_body
    with pytest.raises(UsxFlightRefused):
        assert_generation_body(bad)


def test_evaluate_argv_is_partial_and_uses_the_scoring_alias_only():
    argv = evaluate_argv(["multiple", "simple_python", "irrelevance"], Path("result"), Path("score"))
    assert argv[3] == "evaluate"
    assert "--partial-eval" in argv
    assert argv[argv.index("--model") + 1] == EVALUATE_ALIAS
    assert MODEL not in argv
    assert "generate" not in argv
    joined = " ".join(argv)
    assert "openfunctions_evaluation" not in joined
    with pytest.raises(UsxFlightRefused):
        evaluate_argv(["multiple"], Path("result"), Path("score"))


def test_quality_labels_split_multiple_and_refuse_parse_failure_as_abstention():
    assert classify_multiple(True, None) == "correct"
    assert classify_multiple(False, "simple_function_checker:wrong_func_name") == "wrong_name"
    assert classify_multiple(False, "simple_function_checker:missing_required") == "right_name_wrong_args"
    assert classify_multiple(False, "value_error:string") == "right_name_wrong_args"
    assert classify_multiple(False, "type_error:float") == "right_name_wrong_args"
    assert classify_multiple(False, "ast_decoder:decoder_failed") == "parse_failure"
    assert classify_multiple(False, "multiple_function_checker:wrong_count") == "wrong_call_shape"
    failed = classify_irrelevance(decode_failed=True, contained_function_call=False)
    assert failed["abstention"] is False
    assert failed["correct"] is False
    assert failed["official_runner_would_count_success"] is True
    called = classify_irrelevance(decode_failed=False, contained_function_call=True)
    assert called["correct"] is False
    held = classify_irrelevance(decode_failed=False, contained_function_call=False)
    assert held["label"] == "abstention"
    assert held["correct"] is True
    assert shorter_request_is_not_a_call("wrong_name", 1) == "wrong_name"
    assert shorter_request_is_not_a_call("wrong_name", 1000) == "wrong_name"


def test_no_api_gate_shares_identical_payloads_and_calls_nothing(tmp_path, monkeypatch):
    _pin_or_skip()
    monkeypatch.setenv("DEEPSEEK_API_KEY", SECRET)
    monkeypatch.setenv(CEILING_ENV, "0.01")

    def explode(*_args, **_kwargs):
        raise AssertionError("provider socket opened")

    monkeypatch.setattr("urllib.request.urlopen", explode)
    plans = build_plans(PIN)
    assert len(plans) == 12
    cues = {case["case_id"]: case["cue_applied"] for case in load_json(package_dir() / "cue-revision" / "edits" / "x-record.json")["cases"]}
    unique = 0
    for plan in plans:
        hashes = {}
        for group in plan["groups"]:
            unique += 1
            assert group["arms"]
            for arm in group["arms"]:
                hashes[arm] = group["request_sha256"]
            body = plan["_bodies"][group["request_sha256"]]
            assert body["model"] == MODEL
            assert body["thinking"] == {"type": "disabled"}
        assert set(hashes) == {"U", "S", "X", "SX"}
        if not cues[plan["case_id"]]:
            assert hashes["U"] == hashes["X"]
            assert hashes["S"] == hashes["SX"]
        else:
            assert hashes["U"] != hashes["X"]
            assert hashes["S"] != hashes["SX"]
    assert unique == 32
    gate = run_no_api_gate(PIN, tmp_path, Decimal("0.01"), lambda: _moment(2026, 11, 23, 14, 17))
    assert gate["provider_called"] is False
    assert gate["api_key_read"] is False
    assert gate["spend_cny"] == "0"
    assert gate["official_settlement"] is False
    assert gate["stopped_for_peak"] is False
    assert gate["schedule_at_gate"] == "peak"
    assert gate["unique_payloads"] == unique
    assert gate["reserve_fits_supplied_ceiling"] is False
    assert gate["rate_card"]["schedule"] == "peak"
    assert gate["rate_card"]["locked_offpeak_validation_card"] is False
    assert gate["quality"]["contrast_values"] == {"S-U": None, "X-U": None, "SX-S": None, "SX-X": None, "SX-U": None}
    text = (tmp_path / "gate.json").read_text(encoding="utf-8")
    assert SECRET not in text
    assert "question" not in text


def test_live_path_bills_the_clock_shares_one_call_and_stops_on_the_ceiling(tmp_path, monkeypatch):
    _pin_or_skip()
    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("socket")))
    client = ScriptedClient(_payload())
    with pytest.raises(UsxFlightRefused, match="authorize-peak"):
        run_live(PIN, tmp_path / "unauth", Decimal("1000"), lambda: _moment(2026, 11, 23, 15, 0), client, authorize_peak=False)
    assert client.bodies == []
    reserve = pre_call_reserve_cny("peak")
    with pytest.raises(UsxFlightRefused, match="reserve"):
        run_live(PIN, tmp_path / "tight", reserve, lambda: _moment(2026, 11, 23, 15, 0), client, authorize_peak=True)
    assert len(client.bodies) == 1
    stop = json.loads((tmp_path / "tight" / "stop.json").read_text(encoding="utf-8"))
    assert stop["provider_called"] is True
    assert Decimal(stop["spend_cny"]) == spend_cny("peak", 10, 3, 4)
    assert stop["schedule"] == "peak"
    assert stop["ceiling_lifted"] is False
    client.bodies.clear()
    moments = [_moment(2026, 11, 23, 15, 0), _moment(2026, 11, 22, 15, 0)]

    def clock():
        return moments.pop(0) if moments else _moment(2026, 11, 22, 15, 0)

    record = run_live(PIN, tmp_path / "ok", Decimal("1000"), clock, client, authorize_peak=True)
    plans = build_plans(PIN)
    expected_calls = sum(len(plan["groups"]) for plan in plans)
    assert len(client.bodies) == expected_calls
    assert len(record["calls"]) == expected_calls
    assert record["calls"][0]["schedule"] == "peak"
    assert record["calls"][0]["rate_card"]["cache_miss"] == "2"
    assert record["calls"][1]["schedule"] == "off-peak"
    assert record["calls"][1]["rate_card"]["cache_miss"] == "1"
    assert record["calls"][1]["rate_card"]["locked_offpeak_validation_card"] is False
    assert record["official_settlement"] is False
    assert record["quality"]["scores"] is None
    shared = [call for call in record["calls"] if len(call["arms"]) > 1]
    assert shared
    assert all(call["bill"]["T"] == 10 for call in record["calls"])
    peak_spend = spend_cny("peak", 10, 3, 4)
    off_spend = spend_cny("off-peak", 10, 3, 4)
    assert Decimal(record["spend_cny"]) == peak_spend + off_spend * (expected_calls - 1)


def test_a_thinking_response_stops_the_live_path(tmp_path):
    _pin_or_skip()
    client = ScriptedClient(_payload(reasoning="trace"))
    with pytest.raises(UsxFlightRefused, match="thinking"):
        run_live(PIN, tmp_path, Decimal("1000"), lambda: _moment(2026, 11, 22, 15, 0), client, authorize_peak=True)
    assert len(client.bodies) == 1
    assert list(tmp_path.rglob("*_result.json")) == []


def test_cli_no_api_gate_never_reads_the_key(tmp_path, monkeypatch, capsys):
    _pin_or_skip()
    monkeypatch.setenv("DEEPSEEK_API_KEY", SECRET)
    monkeypatch.delenv(CEILING_ENV, raising=False)
    monkeypatch.setattr("urllib.request.urlopen", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("socket")))

    def key_read():
        raise AssertionError("api key read")

    monkeypatch.setattr("tool_compression.usx_provider.require_api_key", key_read)
    assert main(["usx-flight", "--no-api", "--bfcl-root", str(PIN), "--out", str(tmp_path / "missing")]) == 2
    assert CEILING_ENV in capsys.readouterr().out
    monkeypatch.setenv(CEILING_ENV, "0.01")
    assert main(["usx-flight", "--no-api", "--bfcl-root", str(PIN), "--out", str(tmp_path / "gate")]) == 0
    gate = json.loads((tmp_path / "gate" / "gate.json").read_text(encoding="utf-8"))
    assert gate["provider_called"] is False
    assert gate["api_key_read"] is False
    assert gate["spend_cny"] == "0"
    assert SECRET not in json.dumps(gate)
    stdout = capsys.readouterr().out
    assert "multiple_35" not in stdout
    assert main(["usx-flight", "--live", "--bfcl-root", str(PIN), "--out", str(tmp_path / "noflag")]) == 2
    built = {"called": False}

    def refuse_client():
        built["called"] = True
        raise AssertionError("live client built")

    monkeypatch.setattr("tool_compression.usx_flight.build_live_client", refuse_client)
    assert main(["usx-flight", "--live", "--authorize-peak", "--bfcl-root", str(PIN), "--out", str(tmp_path / "live")]) == 1
    assert "reserve" in capsys.readouterr().out
    assert built["called"] is False
    assert not (tmp_path / "live" / "live.json").exists()


def test_committed_gate_proves_the_dry_run_spent_nothing():
    gate = json.loads((package_dir() / "systems-test" / "dry-run" / "gate.json").read_text(encoding="utf-8"))
    assert gate["stage"] == "A"
    assert gate["provider_called"] is False
    assert gate["api_key_read"] is False
    assert gate["live"] is False
    assert gate["spend_cny"] == "0"
    assert gate["official_settlement"] is False
    assert gate["cases"] == 12
    assert gate["unique_payloads"] == 32
    assert gate["schedule_at_gate"] == "peak"
    assert gate["stopped_for_peak"] is False
    assert gate["ceiling_cny"] == "0.01"
    assert gate["ceiling_hardcoded"] is False
    assert gate["ceiling_authorizes_spend_by_itself"] is False
    assert gate["reserve_fits_supplied_ceiling"] is False
    assert gate["pre_call_reserve_cny"] == "5.145728"
    assert gate["rate_card"]["locked_offpeak_validation_card"] is False
    assert gate["rate_card"]["cache_miss"] == "2"
    assert gate["scoring_alias_is_generation_model"] is False
    assert gate["evaluate"]["ran"] is False
    assert gate["evaluate"]["argv_by_arm"]["U"][-1] == "--partial-eval"
    assert gate["quality"]["scores"] is None
    assert SECRET not in json.dumps(gate)
