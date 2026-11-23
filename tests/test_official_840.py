"""Official 840-case preparation. No provider call and no peak continuation."""

from datetime import datetime
from decimal import Decimal
from pathlib import Path
import inspect
import json

import pytest

from tool_compression.__main__ import main
from tool_compression.evaluation import evaluation_manifest
from tool_compression.official_840 import (
    AIMED_CLOCK,
    ARMS,
    CATEGORY_COUNTS,
    CATEGORY_SHA256,
    CEILING_ENV,
    DRY_RUN_CLOCK,
    MODEL,
    build_flight,
    compute_frozen_hashes,
    evaluate_argv,
    execute_plans,
    generation_body,
    load_fresh,
    make_plan,
    package_dir,
    peak_blocks,
    repo_root,
    run_live,
    run_no_api_gate,
    u_path,
    verify_package,
)
from tool_compression.semantic_audit import load_json, package_dir as pilot_package_dir
from tool_compression.usx_flight import UsxFlightRefused, assert_generation_body, generation_body as systems_generation_body

PIN = Path("/tmp/bfcl-pin")
SHANGHAI_SAMPLE = DRY_RUN_CLOCK.tzinfo
SECRET = "sk-test-secret-value"


def _moment(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=SHANGHAI_SAMPLE)


def _pin_or_skip():
    if not (PIN / "BFCL_v4_multiple.json").is_file():
        pytest.skip("pinned BFCL files are not in this environment")
    return PIN


def _tool(name, description):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": {}},
        },
    }


def _payload(reasoning=None):
    message = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call-1",
                "type": "function",
                "function": {"name": "calculate_triangle_area", "arguments": "{}"},
            }
        ],
    }
    if reasoning is not None:
        message["reasoning_content"] = reasoning
    return {
        "choices": [{"message": message}],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 4,
            "prompt_cache_hit_tokens": 3,
            "prompt_cache_miss_tokens": 7,
        },
    }


class ScriptedClient:
    def __init__(self, payload):
        self.payload = payload
        self.bodies = []

    def complete(self, body):
        self.bodies.append(body)
        return self.payload


def _synthetic_plans():
    shared = _tool("alpha", "One short claim.")
    edited = _tool("alpha", "One short claim kept.")
    other = _tool("beta", "A different claim.")
    messages_b = [{"role": "user", "content": "synthetic-b"}]
    plans = []
    specs = [
        (
            "case-a",
            [{"role": "user", "content": "synthetic-a"}],
            {"U": [shared], "S": [edited], "X": [shared], "SX": [edited]},
        ),
        (
            "case-b",
            messages_b,
            {"U": [other], "S": [other], "X": [other], "SX": [other]},
        ),
        (
            "case-c",
            messages_b,
            {"U": [other], "S": [other], "X": [other], "SX": [other]},
        ),
    ]
    for pass_name in ("off", "on"):
        for case_id, messages, rendered in specs:
            plans.append(make_plan(case_id, "multiple", messages, rendered, pass_name))
    return plans


def test_package_counts_identities_and_leaves_the_pilot_unsealed():
    summary = verify_package()
    counts = summary["counts"]
    assert summary["cases"] == 840
    assert summary["sealed"] == 18
    assert summary["remaining"] == 822
    assert summary["provider_called"] is False
    assert summary["official_settlement"] is False
    assert counts["single_tool_cases"] == 640
    assert counts["multi_tool_cases"] == 200
    assert counts["cued_cases"] == 9
    assert counts["uncued_cases"] == 9
    assert counts["uncued_single_tool"] == 6
    assert counts["uncued_multi_tool"] == 3
    assert counts["s_equals_u"] == 13
    assert counts["x_equals_u"] == 9
    assert counts["sx_equals_s"] == 9
    assert counts["sx_equals_x"] == 13
    assert counts["sx_equals_u"] == 7
    assert counts["four_distinct"] == 3
    assert counts["four_distinct_ids"] == ["multiple_9", "multiple_21", "multiple_73"]
    assert counts["x_equals_u_ids"] == counts["uncued_ids"]
    assert counts["sx_equals_s_ids"] == counts["uncued_ids"]
    assert counts["sx_equals_x_ids"] == counts["s_equals_u_ids"]
    assert counts["cued_ids"] == [
        "multiple_2",
        "multiple_4",
        "multiple_9",
        "multiple_21",
        "multiple_27",
        "multiple_33",
        "multiple_45",
        "multiple_57",
        "multiple_73",
    ]
    assert counts["fact_counts"]["lost"] == 0
    assert counts["fact_counts"]["unsupported_additions"] == 0
    assert counts["flight_ready"] is False
    assert evaluation_manifest()["target_provider_input_reduction"] == "1/10"
    assert evaluation_manifest()["official_accuracy_in_scope"] is False
    pilot = load_json(pilot_package_dir() / "selection" / "manifest.json")
    sealed = set(counts["cued_ids"]) | set(counts["uncued_ids"])
    for row in pilot["selected"]:
        case_id = row["case_id"]
        assert case_id not in sealed
        official = load_json(u_path(case_id))["tools"]
        pilot_u = load_json(pilot_package_dir() / "rendered" / case_id / "U.json")["tools"]
        assert official == pilot_u
        assert not (package_dir() / "rendered" / case_id).exists()


def test_frozen_files_and_the_closed_target_are_unchanged():
    saved = load_json(package_dir() / "checks" / "frozen-integrity.json")
    current = compute_frozen_hashes()
    assert saved["files"] == current["files"]
    assert "src/tool_compression/usx_flight.py" in saved["files"]
    assert "src/tool_compression/evaluation.py" in saved["files"]
    assert "docs/semantic-audit-pilot/cue-revision/edits/x-record.json" in saved["files"]
    assert len(saved["files"]) > 80
    flight = (repo_root() / "src/tool_compression/usx_flight.py").read_text(encoding="utf-8")
    assert "authorize-peak" in flight
    assert "usx-12-systems-test" in flight
    source = (repo_root() / "src/tool_compression/official_840.py").read_text(encoding="utf-8")
    assert "authorize_peak" not in source
    assert "authorize-peak" not in source
    assert 'Decimal("50")' not in source
    assert source.split("def build_live_client")[0].count("official_840_provider") == 0
    assert "authorize_peak" not in inspect.signature(run_live).parameters
    assert "authorize_peak" not in inspect.signature(execute_plans).parameters


def test_identity_sharing_stays_inside_one_cell(tmp_path):
    plans = _synthetic_plans()
    off = [plan for plan in plans if plan["thinking"] == "off"]
    assert [group["arms"] for group in off[0]["groups"]] == [["U", "X"], ["S", "SX"]]
    assert off[1]["groups"][0]["arms"] == ["U", "S", "X", "SX"]
    assert off[1]["groups"][0]["request_sha256"] == off[2]["groups"][0]["request_sha256"]
    assert off[1]["cell"] != off[2]["cell"]
    client = ScriptedClient(_payload())
    record = execute_plans(plans, tmp_path, Decimal("1000"), lambda: _moment(2026, 11, 22, 19, 0), client, sealed=True)
    assert len(client.bodies) == 8
    assert len(record["calls"]) == 8
    assert record["official_settlement"] is False
    assert record["peak_card_used"] is False
    assert {call["schedule"] for call in record["calls"]} == {"off-peak"}
    assert record["calls"][0]["arms"] == ["U", "X"]
    assert record["calls"][0]["shared"] is True
    assert record["calls"][1]["arms"] == ["S", "SX"]
    shared_across = [call for call in record["calls"] if call["case_id"] in {"case-b", "case-c"} and call["thinking"] == "off"]
    assert len(shared_across) == 2
    assert shared_across[0]["request_sha256"] == shared_across[1]["request_sha256"]
    assert record["calls"][0]["bill"]["T"] == 10
    assert record["calls"][0]["rate_card"]["cache_miss"] == "1"


def test_thinking_on_is_a_second_pass_and_does_not_loosen_the_systems_test(tmp_path):
    messages = [{"role": "user", "content": "synthetic-a"}]
    tools = [_tool("alpha", "One short claim.")]
    rendered = {arm: tools for arm in ARMS}
    off = make_plan("case-a", "multiple", messages, rendered, "off")
    on = make_plan("case-a", "multiple", messages, rendered, "on")
    off_body = off["_bodies"][off["groups"][0]["request_sha256"]]
    on_body = on["_bodies"][on["groups"][0]["request_sha256"]]
    assert off_body["tools"] == on_body["tools"] == tools
    assert off_body["messages"] == on_body["messages"]
    assert off_body["thinking"] == {"type": "disabled"}
    assert on_body["thinking"] == {"type": "enabled"}
    assert off["groups"][0]["request_sha256"] != on["groups"][0]["request_sha256"]
    assert off_body == systems_generation_body(messages, tools)
    assert_generation_body(off_body)
    with pytest.raises(UsxFlightRefused):
        assert_generation_body(on_body)
    client = ScriptedClient(_payload(reasoning="trace"))
    with pytest.raises(UsxFlightRefused, match="thinking-off"):
        execute_plans([off, on], tmp_path / "stop", Decimal("1000"), lambda: _moment(2026, 11, 22, 19), client, sealed=True)
    assert len(client.bodies) == 1
    assert client.bodies[0]["thinking"] == {"type": "disabled"}
    assert list((tmp_path / "stop").rglob("*_result.json")) == []
    client = ScriptedClient(_payload())
    client.payloads = [_payload(), _payload(reasoning="trace")]

    def complete(body):
        client.bodies.append(body)
        return client.payloads.pop(0)

    client.complete = complete
    record = execute_plans([off, on], tmp_path / "on", Decimal("1000"), lambda: _moment(2026, 11, 22, 19), client, sealed=True)
    assert [body["thinking"]["type"] for body in client.bodies] == ["disabled", "enabled"]
    assert len(record["calls"]) == 2
    assert record["calls"][1]["thinking"] == "on"
    assert record["official_settlement"] is False
    with pytest.raises(UsxFlightRefused, match="thinking-on pass cannot start"):
        execute_plans([on], tmp_path / "order", Decimal("1000"), lambda: _moment(2026, 11, 22, 19), ScriptedClient(_payload()), sealed=True)


def test_off_peak_stop_has_no_continuation_switch(tmp_path, monkeypatch):
    plans = _synthetic_plans()[:1]
    client = ScriptedClient(_payload())
    with pytest.raises(UsxFlightRefused, match="peak_hours"):
        execute_plans(plans, tmp_path / "peak", Decimal("1000"), lambda: _moment(2026, 11, 23, 17, 25), client, sealed=True)
    assert client.bodies == []
    stop = json.loads((tmp_path / "peak" / "stop.json").read_text(encoding="utf-8"))
    assert stop["stop_reason"] == "peak_hours"
    assert stop["provider_called"] is False
    assert stop["peak_card_used"] is False
    assert stop["spend_cny"] == "0"
    assert stop["official_settlement"] is False
    assert not (tmp_path / "peak" / "live.json").exists()

    def explode():
        raise AssertionError("live client built")

    monkeypatch.setattr("tool_compression.official_840.build_live_client", explode)
    with pytest.raises(UsxFlightRefused, match="peak_hours"):
        execute_plans(plans, tmp_path / "no-client", Decimal("1000"), lambda: _moment(2026, 11, 23, 10), None, sealed=True)
    with pytest.raises(UsxFlightRefused, match="reserve"):
        execute_plans(plans, tmp_path / "reserve", Decimal("0.01"), lambda: _moment(2026, 11, 22, 19), None, sealed=True)
    moments = [_moment(2026, 11, 22, 19), _moment(2026, 11, 23, 15)]

    def clock():
        return moments.pop(0)

    both = [plan for plan in _synthetic_plans() if plan["case_id"] == "case-b"]
    caller = ScriptedClient(_payload())
    with pytest.raises(UsxFlightRefused, match="peak_hours"):
        execute_plans(both, tmp_path / "mid", Decimal("1000"), clock, caller, sealed=True)
    assert len(caller.bodies) == 1
    assert caller.bodies[0]["thinking"] == {"type": "disabled"}
    mid = json.loads((tmp_path / "mid" / "stop.json").read_text(encoding="utf-8"))
    assert mid["provider_called"] is True
    assert mid["peak_card_used"] is False
    assert mid["schedule_at_stop"] == "peak"
    assert Decimal(mid["spend_cny"]) > 0
    with pytest.raises(UsxFlightRefused, match="not fully sealed"):
        run_live(Path("/tmp/not-used"), tmp_path / "package", Decimal("1000"), lambda: _moment(2026, 11, 22, 19), ScriptedClient(_payload()))
    assert peak_blocks(_moment(2026, 11, 23, 17, 25)) is True
    assert peak_blocks(_moment(2026, 11, 23, 19, 0)) is False
    assert peak_blocks(_moment(2026, 11, 22, 10, 0)) is False


def test_cli_refuses_a_peak_switch_and_refuses_live_while_unsealed(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DEEPSEEK_API_KEY", SECRET)
    monkeypatch.setenv(CEILING_ENV, "0.01")
    monkeypatch.setattr("urllib.request.urlopen", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("socket")))

    def key_read():
        raise AssertionError("api key read")

    monkeypatch.setattr("tool_compression.official_840_provider.require_api_key", key_read)
    with pytest.raises(SystemExit) as exc:
        main(["usx-840", "--authorize-peak", "--bfcl-root", str(PIN), "--out", str(tmp_path / "flag")])
    assert exc.value.code == 2
    monkeypatch.delenv(CEILING_ENV, raising=False)
    assert main(["usx-840", "--no-api", "--bfcl-root", str(PIN), "--out", str(tmp_path / "missing")]) == 2
    monkeypatch.setenv(CEILING_ENV, "0.01")
    assert main(["usx-840", "--live", "--bfcl-root", str(PIN), "--out", str(tmp_path / "live")]) == 1
    assert "not fully sealed" in capsys.readouterr().out
    assert not (tmp_path / "live" / "live.json").exists()


def test_committed_gate_is_a_no_api_peak_stop():
    gate = load_json(package_dir() / "dry-run" / "gate.json")
    assert gate["stage"] == "A"
    assert gate["provider_called"] is False
    assert gate["api_key_read"] is False
    assert gate["live"] is False
    assert gate["spend_cny"] == "0"
    assert gate["official_settlement"] is False
    assert gate["sample_cases"] == 840
    assert gate["sealed_cases"] == 18
    assert gate["blocked_cases"] == 822
    assert gate["flight_ready"] is False
    assert gate["partial_live_refused"] is True
    assert gate["live_requires_all_840_sealed"] is True
    assert gate["unique_payloads_if_the_sealed_cells_were_sent"] == 70
    assert gate["thinking_passes"] == ["off", "on"]
    assert gate["thinking_on_is_catalogue_change"] is False
    assert gate["schedule_at_gate"] == "peak"
    assert gate["stopped_for_peak"] is True
    assert gate["live_would_start"] is False
    assert gate["off_peak_only"] is True
    assert gate["peak_continuation_switch"] is False
    assert gate["peak_card_used"] is False
    assert gate["aimed_offpeak_example"]["clock"] == AIMED_CLOCK.isoformat()
    assert gate["aimed_offpeak_example"]["schedule"] == "off-peak"
    assert gate["aimed_offpeak_example"]["live_permitted"] is False
    assert gate["pre_call_reserve_cny"] == "2.572864"
    assert gate["peak_reserve_not_used_cny"] == "5.145728"
    assert gate["reserve_fits_supplied_ceiling"] is False
    assert gate["ceiling_cny"] == "0.01"
    assert gate["ceiling_hardcoded"] is False
    assert gate["evaluate"]["ran"] is False
    assert gate["evaluate"]["partial_eval"] is False
    assert gate["quality"]["scores"] is None
    assert gate["quality"]["contrast_values"] == {"S-U": None, "X-U": None, "SX-S": None, "SX-X": None, "SX-U": None}
    assert gate["not_arms"] == ["L", "E", "T1", "T2", "P", "I", "C"]
    off = {cell["case_id"]: cell for cell in gate["passes"]["off"]}
    on = {cell["case_id"]: cell for cell in gate["passes"]["on"]}
    assert list(off) == list(on)
    assert off["multiple_28"]["groups"][0]["arms"] == ["U", "S", "X", "SX"]
    assert [group["arms"] for group in off["multiple_2"]["groups"]] == [["U", "S"], ["X", "SX"]]
    assert [group["arms"] for group in off["multiple_24"]["groups"]] == [["U", "X"], ["S", "SX"]]
    assert [group["arms"] for group in off["multiple_9"]["groups"]] == [["U"], ["S"], ["X"], ["SX"]]
    assert off["multiple_28"]["groups"][0]["request_sha256"] != on["multiple_28"]["groups"][0]["request_sha256"]
    text = json.dumps(gate)
    assert "question" not in text
    assert SECRET not in text
    argv = evaluate_argv("off", "U", Path("result/thinking-off/U"), Path("score/thinking-off/U"))
    assert "--partial-eval" not in argv
    assert MODEL not in argv
    assert "DeepSeek-V3.2-Exp-FC" in argv
    with pytest.raises(UsxFlightRefused):
        evaluate_argv("off", "L", Path("result"), Path("score"))


def test_pin_regenerates_the_gate_and_the_fresh_u(tmp_path):
    _pin_or_skip()
    fresh_gate = run_no_api_gate(PIN, tmp_path, Decimal("0.01"), lambda: DRY_RUN_CLOCK)
    assert fresh_gate == load_json(package_dir() / "dry-run" / "gate.json")
    order, fresh = load_fresh(PIN)
    manifest = load_json(package_dir() / "selection" / "manifest.json")
    assert order == manifest["ids_in_file_order"]
    assert [manifest["counts"][category] for category in ("multiple", "simple_python", "irrelevance")] == [200, 400, 240]
    assert manifest["counts"] == CATEGORY_COUNTS
    assert manifest["category_sha256"] == CATEGORY_SHA256
    for case_id in order:
        assert load_json(u_path(case_id))["tools"] == fresh[case_id]["tools"]
    question = fresh["multiple_2"]["messages"][0]["content"]
    assert question not in json.dumps(fresh_gate)
    flight = build_flight(PIN)
    assert len(flight["plans"]) == 36
    assert [plan["thinking"] for plan in flight["plans"][:18]] == ["off"] * 18
    assert [plan["thinking"] for plan in flight["plans"][18:]] == ["on"] * 18
    assert [plan["case_id"] for plan in flight["plans"][:18]] == [plan["case_id"] for plan in flight["plans"][18:]]
    for off, onward in zip(flight["plans"][:18], flight["plans"][18:]):
        for arm in ARMS:
            off_hash = next(group["request_sha256"] for group in off["groups"] if arm in group["arms"])
            on_hash = next(group["request_sha256"] for group in onward["groups"] if arm in group["arms"])
            assert off["_bodies"][off_hash]["tools"] == onward["_bodies"][on_hash]["tools"]
            assert off["_bodies"][off_hash]["messages"] == onward["_bodies"][on_hash]["messages"]
            assert off_hash != on_hash
