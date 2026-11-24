"""Request-by-request sender. Fake client only. No provider call and no API key."""

from datetime import datetime
from decimal import Decimal
from pathlib import Path
import inspect
import json
import os
import socket
import subprocess
import sys
import urllib.request

import pytest

from tool_compression.amendment_s2x2_flight import (
    ARMS,
    CATALOGUE_TIP,
    HARD_CAP_CNY,
    MAX_TOKENS,
    AmendmentFlightRefused,
    _is_official_provider_client,
    _official_provider_client,
    build_flight,
    load_attempts,
    main,
    make_plan,
    note_confirmed_charge,
    send_evaluation,
    send_frozen_plan,
    wire_slots,
)
from tool_compression.count import dump_request
from tool_compression.usx_flight import SHANGHAI, pre_call_reserve_cny, spend_cny

ROOT = Path(__file__).resolve().parents[1]
PIN = Path("/tmp/bfcl-pin")
MODULE = ROOT / "src" / "tool_compression" / "amendment_s2x2_flight.py"


def _offpeak():
    return datetime(2026, 11, 28, 19, 0, tzinfo=SHANGHAI)


def _peak():
    return datetime(2026, 11, 23, 10, 0, tzinfo=SHANGHAI)


def _tool(name: str, description: str) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": {}},
        },
    }


def _plans() -> list[dict]:
    shared = {arm: [_tool("alpha", "One short claim.")] for arm in ARMS}
    other = {arm: [_tool("beta", "A different claim.")] for arm in ARMS}
    plans = []
    for pass_name in ("off", "on"):
        for case_id, content, rendered in (
            ("tiny_a", "a", shared),
            ("tiny_b", "b", other),
        ):
            plans.append(make_plan(case_id, "multiple", [{"role": "user", "content": content}], rendered, pass_name))
    return plans


def _usage(prompt: int, completion: int = 4) -> dict:
    return {
        "choices": [{"message": {"role": "assistant", "content": "ok"}}],
        "usage": {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "prompt_cache_hit_tokens": 0,
            "prompt_cache_miss_tokens": prompt,
        },
    }


def _charge(prompt: int, completion: int = 4, schedule: str = "off-peak") -> Decimal:
    return spend_cny(schedule, prompt, 0, completion)


class Fake:
    """In-memory client. Records how many ledger lines existed before each send."""

    def __init__(self, payloads, out: Path | None = None):
        self.payloads = list(payloads)
        self.out = out
        self.bodies = []
        self.ledger_lines_before = []

    def complete(self, body):
        if self.out is not None:
            path = self.out / "attempt-ledger.jsonl"
            lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
            self.ledger_lines_before.append(len([line for line in lines if line.strip()]))
        self.bodies.append(body)
        payload = self.payloads.pop(0)
        if isinstance(payload, BaseException):
            raise payload
        return payload


class LiveClient:
    def complete(self, body):
        raise AssertionError("provider client called")


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def deny(*_args, **_kwargs):
        raise AssertionError("socket opened")

    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(urllib.request, "urlopen", deny)


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sender_section() -> str:
    text = MODULE.read_text(encoding="utf-8")
    return text.split("# Request-by-request sender.", 1)[1].split("\ndef main(", 1)[0]


def test_sender_section_has_no_reserve_gate_and_no_key():
    section = _sender_section()
    for banned in (
        "pre_call_reserve",
        "CAP_STOP",
        "exposure_base",
        "urlopen",
        "environ",
        "getenv",
        "DEEPSEEK",
        "OPENAI",
        "api.deepseek.com",
        "build_live_client",
        "official_840_provider",
        "usx_provider",
        "MAX_INPUT_TOKENS",
        "execute_plans",
    ):
        assert banned not in section
    assert "remaining_run_bound_used_as_stop" in section
    assert inspect.signature(send_evaluation).parameters["frozen_official"].default is False
    assert inspect.signature(send_evaluation).parameters["authorize_official_live"].default is False
    assert inspect.signature(send_frozen_plan).parameters["authorize_official_live"].default is False


def test_live_flag_still_exits_before_a_plan(monkeypatch, capsys, tmp_path):
    secret = "sk-test-secret"
    monkeypatch.setenv("DEEPSEEK_API_KEY", secret)

    def explode(*_args, **_kwargs):
        raise AssertionError("plan built")

    def provider(*_args, **_kwargs):
        raise AssertionError("provider client built")

    monkeypatch.setattr("tool_compression.amendment_s2x2_flight.build_flight", explode)
    monkeypatch.setattr("tool_compression.amendment_s2x2_flight.send_evaluation", explode)
    monkeypatch.setattr("tool_compression.amendment_s2x2_flight.send_frozen_plan", explode)
    monkeypatch.setattr("tool_compression.amendment_s2x2_flight._official_provider_client", provider)
    monkeypatch.setattr("tool_compression.official_840.build_live_client", provider)
    assert main(["--live", "--bfcl-root", str(tmp_path), "--out", str(tmp_path / "out")]) == 2
    captured = capsys.readouterr().out
    assert "does not authorize a flight" in captured
    assert secret not in captured
    assert not (tmp_path / "out").exists()


def test_provider_client_is_refused_before_a_plan_is_built(monkeypatch, tmp_path):
    def explode(*_args, **_kwargs):
        raise AssertionError("plan built")

    monkeypatch.setattr("tool_compression.amendment_s2x2_flight.build_flight", explode)
    with pytest.raises(AmendmentFlightRefused):
        send_frozen_plan(PIN, tmp_path / "live", LiveClient(), _offpeak)
    assert not (tmp_path / "live").exists()


def test_spend_is_recorded_after_each_request_and_ten_yuan_does_not_stop(tmp_path):
    out = tmp_path / "ten"
    plans = _plans()
    prompts = [3_000_000, 3_000_000, 3_000_000, 3_000_000]
    client = Fake([_usage(prompt, 0) for prompt in prompts], out)
    status = send_evaluation(plans, out, client, _offpeak)
    assert client.ledger_lines_before == [0, 1, 2, 3]
    assert len(client.bodies) == 4
    assert {body["thinking"]["type"] for body in client.bodies} == {"disabled", "enabled"}
    assert all(body["max_tokens"] == MAX_TOKENS for body in client.bodies)
    assert all("max_tokens" not in body for plan in plans for body in plan["_plan_bodies"].values())
    spent = sum((_charge(prompt, 0) for prompt in prompts), Decimal("0"))
    assert spent == Decimal("12")
    assert Decimal(status["spend_cny"]) == spent
    assert Decimal(status["comfortable_expectation_cny"]) == Decimal("10")
    assert status["comfortable_expectation_is_a_stop_line"] is False
    assert status["hard_ceiling_reached"] is False
    assert status["further_sends_stopped"] is False
    assert status["full_840_labeled"] is False
    assert status["labeled_case_count"] is None
    assert status["peak_rate_next_request_reserve"] is False
    assert status["precharge_funding_gate"] is False
    assert status["remaining_run_bound_used_as_stop"] is False
    assert status["provider_called"] is False
    assert status["human_review"] == "not performed (not passed)"
    assert status["official_v1_1"] == "closed"
    assert status["catalogue_tip"] == CATALOGUE_TIP
    assert not (out / "ceiling-notice.json").exists()
    assert not (out / "live.json").exists()
    ledger = load_attempts(out)
    assert [row["kind"] for row in ledger] == ["attempt"] * 4
    assert [Decimal(row["spend_cny"]) for row in ledger] == [_charge(prompt, 0) for prompt in prompts]


def test_next_request_is_sent_when_a_peak_reserve_would_not_fit(tmp_path):
    assert Decimal("79") + pre_call_reserve_cny("peak") > HARD_CAP_CNY
    out = tmp_path / "continue"
    prompts = [79_000_000, 10, 10, 10]
    client = Fake([_usage(prompts[0], 0), _usage(10), _usage(10), _usage(10)], out)
    status = send_evaluation(_plans(), out, client, _offpeak)
    assert len(client.bodies) == 4
    assert client.ledger_lines_before == [0, 1, 2, 3]
    assert Decimal(status["spend_cny"]) == _charge(prompts[0], 0) + _charge(10) * 3
    assert Decimal(status["spend_cny"]) < HARD_CAP_CNY
    assert status["hard_ceiling_reached"] is False
    assert not (out / "ceiling-notice.json").exists()
    assert status["full_840_labeled"] is False


def test_peak_clock_still_sends_and_records_the_confirmed_peak_charge(tmp_path):
    out = tmp_path / "peak"
    client = Fake([_usage(10), _usage(10), _usage(10), _usage(10)], out)
    status = send_evaluation(_plans(), out, client, _peak)
    assert len(client.bodies) == 4
    assert Decimal(status["spend_cny"]) == _charge(10, schedule="peak") * 4
    assert status["hard_ceiling_reached"] is False
    assert not (out / "stop.json").exists()


def test_ceiling_stops_further_sends_and_writes_the_operator_notice(tmp_path):
    plans = _plans()
    out = tmp_path / "cap"
    client = Fake([_usage(40_000_000, 0), _usage(40_000_000, 0), _usage(10), _usage(10)], out)
    status = send_evaluation(plans, out, client, _offpeak)
    assert len(client.bodies) == 2
    assert client.ledger_lines_before == [0, 1]
    assert Decimal(status["spend_cny"]) == Decimal("80")
    assert status["hard_ceiling_reached"] is True
    assert status["further_sends_stopped"] is True
    assert status["full_840_labeled"] is False
    assert status["labeled_case_count"] is None
    assert status["evaluation_slots_complete"] is False
    assert "Tell the operator" in status["operator_notice"]
    assert "not the full 840" in status["operator_notice"]
    notice = _read(out / "ceiling-notice.json")
    assert notice["operator_notice"] == status["operator_notice"]
    assert notice["further_sends_stopped"] is True
    assert notice["full_840_labeled"] is False
    assert notice["provider_called"] is False
    assert notice["human_review"] == "not performed (not passed)"
    assert not (out / "live.json").exists()

    resume = Fake([_usage(10)], out)
    again = send_evaluation(plans, out, resume, _offpeak)
    assert resume.bodies == []
    assert Decimal(again["spend_cny"]) == Decimal("80")
    assert again["full_840_labeled"] is False
    assert _read(out / "ceiling-notice.json")["further_sends_stopped"] is True


def test_unresolved_attempt_stays_until_settled_and_a_retry_is_counted(tmp_path):
    plans = _plans()
    slots = wire_slots(plans)
    out = tmp_path / "retry"
    secret = "sk-test-secret"
    first = Fake([TimeoutError(f"timed out {secret}"), _usage(10), _usage(10), _usage(10)], out)
    status = send_evaluation(plans, out, first, _offpeak)
    assert secret not in (out / "attempt-ledger.jsonl").read_text(encoding="utf-8")
    assert secret not in (out / "sender-status.json").read_text(encoding="utf-8")
    evidence = Decimal(load_attempts(out)[0]["spend_cny"])
    assert evidence > 0
    confirmed = _charge(10) * 3
    assert Decimal(status["spend_cny"]) == evidence + confirmed
    assert Decimal(status["unresolved_spend_cny"]) == evidence
    assert status["unresolved_attempts"] == 1
    assert status["attempts"] == 4
    assert status["full_840_labeled"] is False

    resume = Fake([_usage(10)], out)
    resumed = send_evaluation(plans, out, resume, _offpeak)
    assert len(resume.bodies) == 1
    assert resume.bodies[0]["max_tokens"] == MAX_TOKENS
    rows = load_attempts(out)
    slot_attempts = [row for row in rows if row["slot_id"] == slots[0]["slot_id"] and row["kind"] == "attempt"]
    assert [row["attempt_index"] for row in slot_attempts] == [1, 2]
    assert Decimal(resumed["spend_cny"]) == evidence + _charge(10) * 4
    assert Decimal(resumed["spend_cny"]) != _charge(10) * 4
    assert resumed["unresolved_attempts"] == 1

    settled = note_confirmed_charge(plans, out, slot_attempts[0]["attempt_id"], Decimal("0.25"))
    assert Decimal(settled["spend_cny"]) == Decimal("0.25") + _charge(10) * 4
    assert Decimal(settled["unresolved_spend_cny"]) == 0
    assert settled["unresolved_attempts"] == 0
    kept = load_attempts(out)
    assert kept[0]["charge"] == "unresolved"
    latest = [row for row in kept if row["attempt_id"] == slot_attempts[0]["attempt_id"]][-1]
    assert latest["kind"] == "settlement"
    assert Decimal(latest["spend_cny"]) == Decimal("0.25")
    assert sum(1 for row in kept if row["kind"] == "attempt" and row["slot_id"] == slots[0]["slot_id"]) == 2


def test_same_confirmed_charge_is_not_replaced_by_a_smaller_one(tmp_path):
    plans = _plans()
    out = tmp_path / "keep"
    send_evaluation(plans, out, Fake([_usage(10)] * 4), _offpeak)
    attempt_id = load_attempts(out)[0]["attempt_id"]
    with pytest.raises(AmendmentFlightRefused, match="already recorded"):
        note_confirmed_charge(plans, out, attempt_id, Decimal("0"))
    assert Decimal(_read(out / "sender-status.json")["spend_cny"]) == _charge(10) * 4


def test_corrupt_ledger_does_not_resume_as_zero(tmp_path):
    plans = _plans()
    out = tmp_path / "corrupt"
    out.mkdir()
    (out / "attempt-ledger.jsonl").write_text("{", encoding="utf-8")
    client = Fake([_usage(10)] * 4)
    with pytest.raises(AmendmentFlightRefused, match="corrupt"):
        send_evaluation(plans, out, client, _offpeak)
    assert client.bodies == []


def test_tiny_plan_is_not_labeled_as_the_full_840_even_if_asked(tmp_path):
    out = tmp_path / "label"
    status = send_evaluation(_plans(), out, Fake([_usage(10)] * 4), _offpeak, frozen_official=True)
    assert status["evaluation_slots_complete"] is True
    assert status["full_840_labeled"] is False
    assert status["labeled_case_count"] is None
    assert status["official_840_plan"] is False


@pytest.fixture(scope="module")
def official_flight():
    if not (PIN / "BFCL_v4_multiple.json").is_file():
        pytest.skip("pinned BFCL files are not in this environment")
    return build_flight(PIN)


def test_frozen_official_plan_sends_both_passes_under_the_ceiling(official_flight, tmp_path):
    out = tmp_path / "official"
    slots = wire_slots(official_flight["plans"])
    client = Fake([_usage(10)] * len(slots), out)
    status = send_frozen_plan(PIN, out, client, _offpeak)
    assert len(client.bodies) == len(slots) == 2174
    assert client.ledger_lines_before == list(range(2174))
    assert {body["thinking"]["type"] for body in client.bodies} == {"disabled", "enabled"}
    assert all(body["max_tokens"] == MAX_TOKENS and body["model"] == "deepseek-flash" for body in client.bodies)
    assert all(body["temperature"] == 0.001 and body["store"] is False for body in client.bodies)
    plan = official_flight["plans"][0]
    plan_body = next(iter(plan["_plan_bodies"].values()))
    wire_body = next(iter(plan["_wire_bodies"].values()))
    assert "max_tokens" not in plan_body
    assert dump_request(wire_body) == dump_request(plan_body)[:-1] + ',"max_tokens":8192}'
    assert Decimal(status["spend_cny"]) == _charge(10) * 2174
    assert Decimal(status["spend_cny"]) < Decimal("10")
    assert status["hard_ceiling_reached"] is False
    assert status["full_840_labeled"] is True
    assert status["labeled_case_count"] == 840
    assert status["official_settlement"] is False
    assert status["provider_called"] is False
    assert status["provider_call_authorized"] is False
    assert status["live_dispatch"] == "refused"
    assert status["human_review"] == "not performed (not passed)"
    assert status["catalogue_tip"] == CATALOGUE_TIP
    assert not (out / "ceiling-notice.json").exists()
    assert not (out / "live.json").exists()
    again = Fake([_usage(10)], out)
    send_frozen_plan(PIN, out, again, _offpeak)
    assert again.bodies == []


def test_official_plan_stops_at_eighty_and_is_not_labeled_full(official_flight, tmp_path):
    out = tmp_path / "official-cap"
    client = Fake([_usage(80_000_000, 0)] + [_usage(10)] * 5, out)
    status = send_frozen_plan(PIN, out, client, _offpeak)
    assert len(client.bodies) == 1
    assert Decimal(status["spend_cny"]) == Decimal("80")
    assert status["full_840_labeled"] is False
    assert status["labeled_case_count"] is None
    assert status["slots_usable"] == 1
    assert status["slots_planned"] == 2174
    notice = _read(out / "ceiling-notice.json")
    assert "Tell the operator" in notice["operator_notice"]
    assert "not the full 840" in notice["operator_notice"]
    assert notice["full_840_labeled"] is False
    resume = Fake([_usage(10)], out)
    send_frozen_plan(PIN, out, resume, _offpeak)
    assert resume.bodies == []


def _recording_client(payloads):
    class LiveClient:
        def __init__(self):
            self.bodies = []
            self._payloads = list(payloads)

        def complete(self, body):
            self.bodies.append(body)
            payload = self._payloads.pop(0)
            if isinstance(payload, BaseException):
                raise payload
            return payload

    return LiveClient()


def test_authorize_flag_without_live_does_not_build_a_plan(monkeypatch, capsys, tmp_path):
    def explode(*_args, **_kwargs):
        raise AssertionError("plan or provider client built")

    monkeypatch.setattr("tool_compression.amendment_s2x2_flight.build_flight", explode)
    monkeypatch.setattr("tool_compression.amendment_s2x2_flight._official_provider_client", explode)
    monkeypatch.setattr("tool_compression.official_840.build_live_client", explode)
    assert main(["--authorize-official-live", "--bfcl-root", str(tmp_path), "--out", str(tmp_path / "out")]) == 2
    assert "requires --live" in capsys.readouterr().out
    assert not (tmp_path / "out").exists()


def test_authorized_command_without_paths_does_not_build_a_client(monkeypatch, capsys):
    def explode(*_args, **_kwargs):
        raise AssertionError("provider client built")

    monkeypatch.setattr("tool_compression.amendment_s2x2_flight._official_provider_client", explode)
    monkeypatch.setattr("tool_compression.official_840.build_live_client", explode)
    assert main(["--live", "--authorize-official-live"]) == 2
    assert "required" in capsys.readouterr().out


def test_help_names_the_authorized_live_path(capsys):
    with pytest.raises(SystemExit) as caught:
        main(["--help"])
    assert caught.value.code == 0
    text = capsys.readouterr().out
    assert "--authorize-official-live" in text
    assert "--live" in text


def test_provider_factory_delegates_without_calling_the_real_builder(monkeypatch):
    sentinel = object()

    def builder():
        return sentinel

    monkeypatch.setattr("tool_compression.official_840.build_live_client", builder)
    assert _official_provider_client() is sentinel


def test_only_the_official_provider_module_counts_as_a_provider_call():
    class LiveClient:
        def complete(self, body):
            return body

    assert _is_official_provider_client(LiveClient()) is False
    LiveClient.__module__ = "tool_compression.official_840_provider"
    assert _is_official_provider_client(LiveClient()) is True
    LiveClient.__module__ = "tool_compression.usx_provider"
    assert _is_official_provider_client(LiveClient()) is False


def test_authorization_must_be_a_real_bool(tmp_path):
    client = Fake([_usage(10)] * 4)
    with pytest.raises(AmendmentFlightRefused, match="explicit"):
        send_evaluation(_plans(), tmp_path / "bad", client, _offpeak, authorize_official_live="yes")
    assert client.bodies == []
    assert not (tmp_path / "bad").exists()


def test_authorized_command_sends_the_plan_through_a_fake_client(monkeypatch, capsys, tmp_path):
    secret = "sk-test-secret"
    monkeypatch.setenv("DEEPSEEK_API_KEY", secret)

    def explode(*_args, **_kwargs):
        raise AssertionError("provider client built")

    monkeypatch.setattr("tool_compression.official_840.build_live_client", explode)
    plans = _plans()

    def flight(*_args, **_kwargs):
        return {"catalogue_tip": CATALOGUE_TIP, "plans": plans}

    monkeypatch.setattr("tool_compression.amendment_s2x2_flight.build_flight", flight)
    client = Fake([_usage(10)] * 4)
    monkeypatch.setattr("tool_compression.amendment_s2x2_flight._official_provider_client", lambda: client)
    out = tmp_path / "live"
    code = main(
        ["--live", "--authorize-official-live", "--bfcl-root", str(tmp_path), "--out", str(out)]
    )
    assert code == 1
    assert len(client.bodies) == 4
    assert all(body["max_tokens"] == MAX_TOKENS for body in client.bodies)
    assert {body["thinking"]["type"] for body in client.bodies} == {"disabled", "enabled"}
    captured = capsys.readouterr().out
    assert secret not in captured
    printed = json.loads(captured)
    assert printed["authorized_official_live"] is True
    assert printed["live_dispatch"] == "authorized"
    assert printed["provider_called"] is False
    assert printed["provider_network"] is False
    assert printed["full_840_labeled"] is False
    assert printed["official_settlement"] is False
    assert printed["human_review"] == "not performed (not passed)"
    assert printed["catalogue_tip"] == CATALOGUE_TIP
    status = _read(out / "sender-status.json")
    assert status["authorized_official_live"] is True
    assert status["provider_call_authorized"] is True
    assert status["provider_called"] is False
    assert status["live_dispatch"] == "authorized"
    assert status["official_v1_1"] == "closed"
    assert status["comfortable_expectation_is_a_stop_line"] is False
    assert Decimal(status["spend_cny"]) < Decimal("10")
    assert status["hard_ceiling_reached"] is False
    assert secret not in (out / "attempt-ledger.jsonl").read_text(encoding="utf-8")
    assert secret not in (out / "sender-status.json").read_text(encoding="utf-8")
    assert not (out / "live.json").exists()


def test_authorized_send_accepts_a_provider_shaped_client_and_builds_the_plan(monkeypatch, tmp_path):
    plans = _plans()
    built = {"count": 0}

    def flight(*_args, **_kwargs):
        built["count"] += 1
        return {"catalogue_tip": CATALOGUE_TIP, "plans": plans}

    monkeypatch.setattr("tool_compression.amendment_s2x2_flight.build_flight", flight)
    client = _recording_client([_usage(10)] * 4)
    out = tmp_path / "shaped"
    status = send_frozen_plan(tmp_path, out, client, _offpeak, authorize_official_live=True)
    assert built["count"] == 1
    assert len(client.bodies) == 4
    assert all(body["max_tokens"] == MAX_TOKENS for body in client.bodies)
    assert all("max_tokens" not in plan_body for plan in plans for plan_body in plan["_plan_bodies"].values())
    assert status["authorized_official_live"] is True
    assert status["provider_called"] is False
    assert status["provider_network"] is False
    assert status["full_840_labeled"] is False
    assert status["official_settlement"] is False
    assert status["catalogue_tip"] == CATALOGUE_TIP
    assert not (out / "live.json").exists()


def test_authorized_path_stops_at_the_ceiling_and_does_not_label_the_full_840(tmp_path):
    client = _recording_client([_usage(80_000_000, 0), _usage(10), _usage(10), _usage(10)])
    out = tmp_path / "auth-cap"
    status = send_evaluation(_plans(), out, client, _offpeak, authorize_official_live=True)
    assert len(client.bodies) == 1
    assert Decimal(status["spend_cny"]) == Decimal("80")
    assert status["further_sends_stopped"] is True
    assert status["full_840_labeled"] is False
    assert status["labeled_case_count"] is None
    assert status["authorized_official_live"] is True
    assert status["live_dispatch"] == "authorized"
    assert status["provider_called"] is False
    notice = _read(out / "ceiling-notice.json")
    assert notice["operator_notice"] == status["operator_notice"]
    assert "not the full 840" in notice["operator_notice"]
    assert notice["full_840_labeled"] is False
    assert notice["live_dispatch"] == "authorized"
    assert notice["provider_call_authorized"] is True
    assert notice["provider_called"] is False
    assert not (out / "live.json").exists()
    resume = _recording_client([_usage(10)])
    again = send_evaluation(_plans(), out, resume, _offpeak, authorize_official_live=True)
    assert resume.bodies == []
    assert again["full_840_labeled"] is False


def test_authorized_path_still_sends_when_a_peak_reserve_would_not_fit(tmp_path):
    assert Decimal("79") + pre_call_reserve_cny("peak") > HARD_CAP_CNY
    prompts = [79_000_000, 10, 10, 10]
    client = Fake([_usage(prompts[0], 0), _usage(10), _usage(10), _usage(10)])
    status = send_evaluation(_plans(), tmp_path / "fit", client, _offpeak, authorize_official_live=True)
    assert len(client.bodies) == 4
    assert Decimal(status["spend_cny"]) == _charge(prompts[0], 0) + _charge(10) * 3
    assert status["hard_ceiling_reached"] is False
    assert status["peak_rate_next_request_reserve"] is False
    assert status["precharge_funding_gate"] is False
    assert status["remaining_run_bound_used_as_stop"] is False
    assert status["comfortable_expectation_is_a_stop_line"] is False
    assert status["authorized_official_live"] is True


def test_authorized_unresolved_attempt_stays_and_a_retry_is_a_new_attempt(tmp_path):
    plans = _plans()
    out = tmp_path / "auth-retry"
    secret = "sk-test-secret"
    client = _recording_client([TimeoutError(f"timed out {secret}"), _usage(10), _usage(10), _usage(10)])
    status = send_evaluation(plans, out, client, _offpeak, authorize_official_live=True)
    ledger = (out / "attempt-ledger.jsonl").read_text(encoding="utf-8")
    assert secret not in ledger
    assert secret not in (out / "sender-status.json").read_text(encoding="utf-8")
    evidence = Decimal(load_attempts(out)[0]["spend_cny"])
    assert Decimal(status["spend_cny"]) == evidence + _charge(10) * 3
    assert status["unresolved_attempts"] == 1
    assert status["full_840_labeled"] is False
    assert status["authorized_official_live"] is True
    resume = _recording_client([_usage(10)])
    resumed = send_evaluation(plans, out, resume, _offpeak, authorize_official_live=True)
    assert len(resume.bodies) == 1
    slot_attempts = [
        row for row in load_attempts(out) if row["slot_id"] == wire_slots(plans)[0]["slot_id"] and row["kind"] == "attempt"
    ]
    assert [row["attempt_index"] for row in slot_attempts] == [1, 2]
    assert Decimal(resumed["spend_cny"]) == evidence + _charge(10) * 4
    settled = note_confirmed_charge(plans, out, slot_attempts[0]["attempt_id"], Decimal("0.25"))
    assert Decimal(settled["spend_cny"]) == Decimal("0.25") + _charge(10) * 4
    assert settled["authorized_official_live"] is True
    assert settled["live_dispatch"] == "authorized"
    assert settled["unresolved_attempts"] == 0
    with pytest.raises(AmendmentFlightRefused, match="authorization"):
        send_evaluation(plans, out, Fake([_usage(10)]), _offpeak)


def test_official_provider_marker_is_recorded_for_that_client_only(tmp_path):
    class LiveClient:
        def __init__(self):
            self.bodies = []

        def complete(self, body):
            self.bodies.append(body)
            return _usage(10)

    LiveClient.__module__ = "tool_compression.official_840_provider"
    client = LiveClient()
    status = send_evaluation(_plans(), tmp_path / "mark", client, _offpeak, authorize_official_live=True)
    assert len(client.bodies) == 4
    assert status["provider_called"] is True
    assert status["provider_network"] is True
    assert status["provider_call_authorized"] is True
    assert all(row["provider_called"] is True for row in load_attempts(tmp_path / "mark"))


def test_import_and_refused_live_do_not_load_a_provider_or_open_a_socket(tmp_path):
    script = r"""
import socket
import sys
import urllib.request

def deny(*_args, **_kwargs):
    raise SystemExit("socket opened")

socket.create_connection = deny
socket.socket.connect = deny
urllib.request.urlopen = deny
import tool_compression.amendment_s2x2_flight as flight
banned = [name for name in sys.modules if name.endswith("official_840_provider") or name.endswith("usx_provider")]
assert banned == [], banned
code = flight.main(["--live", "--bfcl-root", sys.argv[1], "--out", sys.argv[2]])
assert code == 2, code
banned = [name for name in sys.modules if name.endswith("official_840_provider") or name.endswith("usx_provider")]
assert banned == [], banned
from pathlib import Path
assert not Path(sys.argv[2]).exists()
"""
    out = tmp_path / "refused"
    env = {"PYTHONPATH": str(ROOT / "src"), "PATH": os.environ.get("PATH", "")}
    home = os.environ.get("HOME")
    if home:
        env["HOME"] = home
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path), str(out)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert not out.exists()


def test_authorized_official_plan_labels_the_full_840(official_flight, tmp_path):
    out = tmp_path / "official-auth"
    slots = wire_slots(official_flight["plans"])
    client = _recording_client([_usage(10)] * len(slots))
    status = send_frozen_plan(PIN, out, client, _offpeak, authorize_official_live=True)
    assert len(client.bodies) == len(slots) == 2174
    assert all(body["max_tokens"] == MAX_TOKENS and body["model"] == "deepseek-flash" for body in client.bodies)
    plan = official_flight["plans"][0]
    plan_body = next(iter(plan["_plan_bodies"].values()))
    wire_body = client.bodies[0]
    assert "max_tokens" not in plan_body
    assert wire_body["max_tokens"] == MAX_TOKENS
    assert status["full_840_labeled"] is True
    assert status["labeled_case_count"] == 840
    assert status["authorized_official_live"] is True
    assert status["live_dispatch"] == "authorized"
    assert status["provider_called"] is False
    assert status["provider_network"] is False
    assert status["official_settlement"] is False
    assert status["official_v1_1"] == "closed"
    assert status["human_review"] == "not performed (not passed)"
    assert status["catalogue_tip"] == CATALOGUE_TIP
    assert Decimal(status["spend_cny"]) < Decimal("10")
    assert status["hard_ceiling_reached"] is False
    assert not (out / "ceiling-notice.json").exists()
    assert not (out / "live.json").exists()
