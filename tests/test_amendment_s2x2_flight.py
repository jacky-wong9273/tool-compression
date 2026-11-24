"""Offline checks for the U/S2/X2/SX2 runner. No provider call and no API key."""

from datetime import datetime
from decimal import Decimal
from pathlib import Path
import json
import socket
import subprocess
import threading
import urllib.request

import pytest

from tool_compression.amendment_s2x2_flight import (
    ARMS,
    CATALOGUE_TIP,
    HARD_CAP_CNY,
    MAX_TOKENS,
    SPENDING_ALERT_CNY,
    AmendmentFlightRefused,
    accept_run_ceiling,
    build_flight,
    documented_call_reserve_cny,
    execute_scripted,
    is_official_sample,
    load_cap_state,
    local_counter,
    local_input_tokens,
    main,
    make_plan,
    plan_body,
    preflight,
    refuse_provider_call,
    summarize_flight,
    wire_body,
    wire_manifest,
    wire_slots,
    worst_case_cny,
)
from tool_compression.count import dump_request
from tool_compression.official_840 import generation_body as official_generation_body
from tool_compression.usx_flight import SHANGHAI, rate_card, request_sha256, schedule_at, spend_cny

ROOT = Path(__file__).resolve().parents[1]
PIN = Path("/tmp/bfcl-pin")
# Subtree of docs/amendment-s2x2 at catalogue tip 96795322fc12c27f0eebe538448666588b573176.
# A one-commit checkout contains this tree. Matching ids means the directory is unchanged.
CATALOGUE_TREE = "20fc64601bb74bca5330ae0a2a63faf01ae9e473"
MODULE = ROOT / "src" / "tool_compression" / "amendment_s2x2_flight.py"
PLAN_TOTALS = {"U": 184011, "S2": 181119, "X2": 184649, "SX2": 181757}
WIRE_TOTALS = {"U": 189051, "S2": 186159, "X2": 189689, "SX2": 186797}
SCOPE_PLAN = {
    "multiple": {"U": 73735, "S2": 72295, "X2": 74373, "SX2": 72933},
    "simple_python": {"U": 69796, "S2": 69300, "X2": 69796, "SX2": 69300},
    "irrelevance": {"U": 40480, "S2": 39524, "X2": 40480, "SX2": 39524},
    "controls": {"U": 110276, "S2": 108824, "X2": 110276, "SX2": 108824},
}
SCOPE_UNIQUE = {"multiple": 303, "simple_python": 469, "irrelevance": 315, "controls": 784}
ORDERED_SLOT_DIGEST = "f9311c325819064255b4cd35d39526a5c05c40c669969857148c5c82117353bd"


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


def _plans(cases: list[tuple[str, str, dict[str, list]]]) -> list[dict]:
    plans = []
    for pass_name in ("off", "on"):
        for case_id, content, rendered in cases:
            plans.append(make_plan(case_id, "multiple", [{"role": "user", "content": content}], rendered, pass_name))
    return plans


def _shared(name: str, description: str) -> dict[str, list]:
    tool = [_tool(name, description)]
    return {arm: tool for arm in ARMS}


def _tiny_plans() -> list[dict]:
    return _plans(
        [
            ("tiny_a", "a", _shared("alpha", "One short claim.")),
            ("tiny_b", "b", _shared("beta", "A different claim.")),
        ]
    )


def _slot_total(plans: list[dict]) -> tuple[list[dict], Decimal]:
    slots = wire_slots(plans)
    costs: dict[str, Decimal] = {}
    total = Decimal("0")
    for slot in slots:
        digest = slot["request_sha256"]
        if digest not in costs:
            costs[digest] = worst_case_cny(slot["body"])
        total += costs[digest]
    return slots, total


def _send_ceiling(slots: list[dict], extra_calls: int = 0) -> Decimal:
    """Ceiling that covers the documented reservation, still at or under ¥80."""
    ceiling = documented_call_reserve_cny() * (len(slots) + extra_calls)
    assert ceiling <= HARD_CAP_CNY
    return ceiling


class Scripted:
    def __init__(self, payload=None):
        self.bodies = []
        self.payload = payload or {
            "choices": [{"message": {"role": "assistant", "content": "ok"}}],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 4,
                "prompt_cache_hit_tokens": 0,
                "prompt_cache_miss_tokens": 10,
            },
        }

    def complete(self, body):
        self.bodies.append(body)
        return self.payload


class TimeoutThen:
    def __init__(self, secret: str = ""):
        self.bodies = []
        self.secret = secret

    def complete(self, body):
        self.bodies.append(body)
        raise TimeoutError(f"The read operation timed out {self.secret}".strip())


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _deny_network(monkeypatch) -> None:
    def deny(*_args, **_kwargs):
        raise AssertionError("socket opened")

    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(urllib.request, "urlopen", deny)


def _install_manifest(out: Path, plans: list[dict]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "wire-manifest.json").write_text(
        json.dumps(wire_manifest(plans), indent=2) + "\n",
        encoding="utf-8",
    )


def _usage(prompt: int, output: int = 4) -> dict:
    return {
        "choices": [{"message": {"role": "assistant", "content": "ok"}}],
        "usage": {
            "prompt_tokens": prompt,
            "completion_tokens": output,
            "prompt_cache_hit_tokens": 0,
            "prompt_cache_miss_tokens": prompt,
        },
    }


def _usage_priced(amount: Decimal, output: int = 1) -> dict:
    """Off-peak miss-priced usage whose bill is exactly ``amount``."""
    prompt = int(amount * Decimal(1_000_000)) - 4 * output
    assert spend_cny("off-peak", prompt, 0, output) == amount
    return _usage(prompt, output)


class _HoldClient:
    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()
        self.bodies = []

    def complete(self, body):
        self.bodies.append(body)
        self.started.set()
        assert self.release.wait(10)
        return _usage(10)


def test_schedule_examples_match_the_offpeak_rule():
    assert schedule_at(_offpeak()) == "off-peak"
    assert schedule_at(_peak()) == "peak"


def test_rate_card_is_offpeak_flash_and_worst_case_uses_it():
    card = rate_card("off-peak")
    assert card["cache_hit"] == "0.02"
    assert card["cache_miss"] == "1"
    assert card["output"] == "4"
    assert spend_cny("off-peak", 1_000_000, 1_000_000, 0) == Decimal("0.02")
    assert spend_cny("off-peak", 1_000_000, 0, 0) == Decimal("1")
    assert spend_cny("off-peak", 0, 0, 1_000_000) == Decimal("4")
    messages = [{"role": "user", "content": "synthetic"}]
    tools = [_tool("alpha", "One short claim.")]
    plan = plan_body(messages, tools, "off")
    wire = wire_body(messages, tools, "off")
    assert plan == official_generation_body(messages, tools, "off")
    assert "max_tokens" not in plan
    assert dump_request(wire) == dump_request(plan)[:-1] + ',"max_tokens":8192}'
    tokens = local_input_tokens(wire)
    assert worst_case_cny(wire) == spend_cny("off-peak", tokens, 0, MAX_TOKENS)
    assert accept_run_ceiling(HARD_CAP_CNY) == HARD_CAP_CNY
    with pytest.raises(AmendmentFlightRefused, match="exceeds ¥80.00"):
        accept_run_ceiling(Decimal("80.01"))
    with pytest.raises(AmendmentFlightRefused, match="Decimal"):
        accept_run_ceiling(80.0)  # type: ignore[arg-type]


def test_runner_source_does_not_name_a_key_or_a_provider_client():
    text = MODULE.read_text(encoding="utf-8")
    for banned in (
        "DEEPSEEK_API_KEY",
        "OPENAI_API_KEY",
        "urlopen",
        "build_live_client",
        "import tool_compression.official_840_provider",
        "from tool_compression.official_840_provider",
        "import tool_compression.usx_provider",
        "from tool_compression.usx_provider",
        "execute_plans",
        "api.deepseek.com",
    ):
        assert banned not in text
    cli = MODULE.read_text(encoding="utf-8").split("def main(", 1)[1]
    for banned in ("DEEPSEEK_API_KEY", "urlopen", "build_live_client", "os.environ"):
        assert banned not in cli


def test_live_flag_refuses_without_a_provider_call(monkeypatch, capsys, tmp_path):
    secret = "sk-test-secret"
    monkeypatch.setenv("DEEPSEEK_API_KEY", secret)
    opened = []

    def deny(*_args, **_kwargs):
        opened.append(True)
        raise AssertionError("socket opened")

    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(urllib.request, "urlopen", deny)
    with pytest.raises(AmendmentFlightRefused, match="does not authorize a flight"):
        refuse_provider_call()
    assert main(["--live", "--bfcl-root", str(tmp_path), "--out", str(tmp_path / "out")]) == 2
    captured = capsys.readouterr().out
    assert "does not authorize a flight" in captured
    assert secret not in captured
    assert opened == []
    assert not (tmp_path / "out").exists()


def test_underfunded_synthetic_stops_before_any_call(tmp_path):
    plans = _tiny_plans()
    client = Scripted()
    with pytest.raises(AmendmentFlightRefused, match="remaining worst-case"):
        execute_scripted(plans, tmp_path / "under", Decimal("0.01"), _offpeak, client, local_counter(), dispatch=True)
    assert client.bodies == []
    stop = _read(tmp_path / "under" / "stop.json")
    assert stop["complete"] is False
    assert stop["would_label_complete"] is False
    assert stop["live_json_written"] is False
    assert stop["calls_already_settled"] == 0
    assert stop["provider_called"] is False
    assert not (tmp_path / "under" / "live.json").exists()


def test_timeout_hold_blocks_an_unsafe_resume_and_keeps_the_secret_out(tmp_path):
    plans = _tiny_plans()
    # The unresolved peak reserve plus the next request no longer fits.
    ceiling = documented_call_reserve_cny() * 2 - Decimal("0.000001")
    out = tmp_path / "timeout"
    secret = "sk-test-secret"
    first = TimeoutThen(secret)
    with pytest.raises(AmendmentFlightRefused, match="unknown charge held") as caught:
        execute_scripted(plans, out, ceiling, _offpeak, first, dispatch=True)
    assert secret not in str(caught.value)
    assert len(first.bodies) == 1
    assert first.bodies[0]["max_tokens"] == MAX_TOKENS
    stop = _read(out / "stop.json")
    hold = _read(out / "cap-hold.json")
    assert stop["complete"] is False
    assert stop["would_label_complete"] is False
    assert stop["spend_cny"] == "0"
    assert Decimal(hold["outstanding_unknown_timeout_cny"]) == documented_call_reserve_cny()
    assert hold["pending_call"] is None
    assert secret not in (out / "stop.json").read_text(encoding="utf-8")
    assert secret not in (out / "cap-hold.json").read_text(encoding="utf-8")
    assert not (out / "live.json").exists()

    resume = Scripted()
    with pytest.raises(AmendmentFlightRefused, match="remaining worst-case"):
        execute_scripted(plans, out, ceiling, _offpeak, resume, dispatch=True)
    assert resume.bodies == []
    reloaded = load_cap_state(out)
    assert reloaded.unknown == documented_call_reserve_cny()
    assert reloaded.loaded_events == 1
    assert not (out / "live.json").exists()
    assert _read(out / "stop.json")["complete"] is False


def test_in_flight_hold_is_reloaded_and_blocks_a_resume(tmp_path):
    plans = _tiny_plans()
    slots, total = _slot_total(plans)
    out = tmp_path / "crash"
    out.mkdir()
    _install_manifest(out, plans)
    amount = worst_case_cny(slots[0]["body"])
    (out / "cap-hold.json").write_text(
        json.dumps(
            {
                "outstanding_unknown_timeout_cny": "0",
                "timeout_events": [],
                "pending_call": {
                    "slot_id": slots[0]["slot_id"],
                    "request_sha256": slots[0]["request_sha256"],
                    "case_id": slots[0]["case_id"],
                    "thinking": slots[0]["thinking"],
                    "held_worst_case_cny": format(amount, "f"),
                    "clock": _offpeak().isoformat(),
                    "reason": "in flight",
                },
            }
        ),
        encoding="utf-8",
    )
    client = Scripted()
    with pytest.raises(AmendmentFlightRefused, match="remaining worst-case"):
        execute_scripted(plans, out, total, _offpeak, client, dispatch=True)
    assert client.bodies == []
    hold = _read(out / "cap-hold.json")
    assert hold["pending_call"] is None
    assert Decimal(hold["outstanding_unknown_timeout_cny"]) == amount
    assert hold["timeout_events"][0]["reason"] == "in-flight call was not settled"
    assert not (out / "live.json").exists()


def test_settled_spend_is_reloaded_and_not_forgotten(tmp_path):
    plans = _tiny_plans()
    slots, total = _slot_total(plans)
    out = tmp_path / "settled"
    out.mkdir()
    _install_manifest(out, plans)
    row = {
        "slot_id": slots[0]["slot_id"],
        "request_sha256": slots[0]["request_sha256"],
        "bill": {"spend_cny": "1.00"},
    }
    (out / "calls-ledger.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    client = Scripted()
    with pytest.raises(AmendmentFlightRefused, match="remaining worst-case"):
        execute_scripted(plans, out, total, _offpeak, client, dispatch=True)
    assert client.bodies == []
    stop = _read(out / "stop.json")
    assert stop["spend_cny"] == "1.00"
    assert stop["calls_already_settled"] == 1
    assert stop["complete"] is False
    assert not (out / "live.json").exists()


def test_resume_refuses_a_missing_ledger_instead_of_zeroing_spend(tmp_path, monkeypatch):
    _deny_network(monkeypatch)
    plans = _tiny_plans()
    _, total = _slot_total(plans)
    out = tmp_path / "missing-ledger"
    _install_manifest(out, plans)
    hold = {
        "settled_spend_cny": "1.00",
        "outstanding_unknown_timeout_cny": "0",
        "timeout_events": [],
        "pending_call": None,
    }
    (out / "cap-hold.json").write_text(json.dumps(hold), encoding="utf-8")
    client = Scripted()
    with pytest.raises(AmendmentFlightRefused, match="calls ledger is missing"):
        execute_scripted(plans, out, total, _offpeak, client, dispatch=True)
    assert client.bodies == []
    assert not (out / "live.json").exists()
    assert _read(out / "cap-hold.json")["settled_spend_cny"] == "1.00"

    bare = tmp_path / "missing-ledger-and-manifest"
    bare.mkdir()
    (bare / "cap-hold.json").write_text(json.dumps(hold), encoding="utf-8")
    with pytest.raises(AmendmentFlightRefused, match="calls ledger is missing"):
        execute_scripted(plans, bare, total, _offpeak, client, dispatch=True)
    assert client.bodies == []
    assert _read(bare / "cap-hold.json")["settled_spend_cny"] == "1.00"
    assert not (bare / "live.json").exists()
    assert not (bare / "wire-manifest.json").exists()

    claimed = tmp_path / "live-without-ledger"
    _install_manifest(claimed, plans)
    marker = json.dumps({"spend_cny": "0.50", "complete": True})
    (claimed / "live.json").write_text(marker, encoding="utf-8")
    with pytest.raises(AmendmentFlightRefused, match="calls ledger is missing"):
        execute_scripted(plans, claimed, total, _offpeak, client, dispatch=True)
    assert client.bodies == []
    assert (claimed / "live.json").read_text(encoding="utf-8") == marker
    with pytest.raises(AmendmentFlightRefused, match="calls ledger is missing"):
        execute_scripted(plans, claimed, total, _offpeak, client, dispatch=True)
    assert client.bodies == []
    assert (claimed / "live.json").read_text(encoding="utf-8") == marker


def test_resume_refuses_cap_state_above_the_ledger(tmp_path, monkeypatch):
    _deny_network(monkeypatch)
    plans = _tiny_plans()
    slots, total = _slot_total(plans)
    out = tmp_path / "thinner-ledger"
    _install_manifest(out, plans)
    (out / "calls-ledger.jsonl").write_text(
        json.dumps({"slot_id": slots[0]["slot_id"], "bill": {"spend_cny": "0.10"}}) + "\n",
        encoding="utf-8",
    )
    (out / "cap-hold.json").write_text(
        json.dumps({"settled_spend_cny": "1.00", "timeout_events": [], "pending_call": None}),
        encoding="utf-8",
    )
    client = Scripted()
    with pytest.raises(AmendmentFlightRefused, match="refusing to reset settled spend"):
        execute_scripted(plans, out, total, _offpeak, client, dispatch=True)
    assert client.bodies == []
    assert not (out / "live.json").exists()
    assert _read(out / "cap-hold.json")["settled_spend_cny"] == "1.00"

    counted = tmp_path / "short-count"
    _install_manifest(counted, plans)
    (counted / "calls-ledger.jsonl").write_text(
        json.dumps({"slot_id": slots[0]["slot_id"], "bill": {"spend_cny": "0.10"}}) + "\n",
        encoding="utf-8",
    )
    (counted / "cap-hold.json").write_text(
        json.dumps({"settled_spend_cny": "0.10", "timeout_events": [], "pending_call": None}),
        encoding="utf-8",
    )
    (counted / "stop.json").write_text(
        json.dumps({"spend_cny": "0.10", "calls_already_settled": 2}),
        encoding="utf-8",
    )
    before = (counted / "calls-ledger.jsonl").read_bytes()
    with pytest.raises(AmendmentFlightRefused, match="refusing to reset settled spend"):
        execute_scripted(plans, counted, total, _offpeak, client, dispatch=True)
    assert client.bodies == []
    assert (counted / "calls-ledger.jsonl").read_bytes() == before
    assert not (counted / "live.json").exists()


def test_torn_final_ledger_entry_is_not_dropped_or_appended(tmp_path, monkeypatch):
    _deny_network(monkeypatch)
    plans = _tiny_plans()
    slots, total = _slot_total(plans)
    out = tmp_path / "torn"
    _install_manifest(out, plans)
    intact = json.dumps({"slot_id": slots[0]["slot_id"], "bill": {"spend_cny": "1.00"}})
    (out / "calls-ledger.jsonl").write_text(intact + "\n" + "{\"slot_id\":\"torn\"", encoding="utf-8")
    (out / "cap-hold.json").write_text(
        json.dumps({"settled_spend_cny": "1.00", "timeout_events": [], "pending_call": None}),
        encoding="utf-8",
    )
    before = (out / "calls-ledger.jsonl").read_bytes()
    client = Scripted()
    with pytest.raises(AmendmentFlightRefused, match="torn and cannot be repaired"):
        execute_scripted(plans, out, total, _offpeak, client, dispatch=True)
    assert client.bodies == []
    assert (out / "calls-ledger.jsonl").read_bytes() == before
    assert _read(out / "cap-hold.json")["settled_spend_cny"] == "1.00"
    assert not (out / "live.json").exists()


def test_missing_newline_is_repaired_before_a_later_append(tmp_path, monkeypatch):
    _deny_network(monkeypatch)
    plans = _tiny_plans()
    slots, total = _slot_total(plans)
    out = tmp_path / "newline"
    _install_manifest(out, plans)
    planted = json.dumps(
        {
            "slot_id": slots[0]["slot_id"],
            "request_sha256": slots[0]["request_sha256"],
            "bill": {"spend_cny": "0.000001"},
        }
    )
    (out / "calls-ledger.jsonl").write_bytes(planted.encode("utf-8"))
    client = Scripted()
    record = execute_scripted(plans, out, _send_ceiling(slots), _offpeak, client, dispatch=True)
    assert len(client.bodies) == 3
    assert request_sha256(client.bodies[0]) == slots[1]["request_sha256"]
    text = (out / "calls-ledger.jsonl").read_text(encoding="utf-8")
    assert text.startswith(planted + "\n")
    assert "}{" not in text
    lines = text.splitlines()
    assert len(lines) == 4
    assert [json.loads(line)["slot_id"] for line in lines] == [slot["slot_id"] for slot in slots]
    assert record["complete"] is True
    assert record["provider_called"] is False
    assert Decimal(record["spend_cny"]) >= Decimal("0.000001")


def test_in_flight_ledger_line_is_kept_and_not_sent_again(tmp_path, monkeypatch):
    _deny_network(monkeypatch)
    plans = _tiny_plans()
    slots, total = _slot_total(plans)
    out = tmp_path / "crash-after-append"
    _install_manifest(out, plans)
    (out / "calls-ledger.jsonl").write_text(
        json.dumps(
            {
                "slot_id": slots[0]["slot_id"],
                "request_sha256": slots[0]["request_sha256"],
                "bill": {"spend_cny": "0.010000"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (out / "cap-hold.json").write_text(
        json.dumps(
            {
                "settled_spend_cny": "0",
                "outstanding_unknown_timeout_cny": "0",
                "timeout_events": [],
                "pending_call": {
                    "slot_id": slots[0]["slot_id"],
                    "request_sha256": slots[0]["request_sha256"],
                    "case_id": slots[0]["case_id"],
                    "thinking": slots[0]["thinking"],
                    "held_worst_case_cny": format(worst_case_cny(slots[0]["body"]), "f"),
                    "clock": _offpeak().isoformat(),
                    "reason": "in flight",
                },
            }
        ),
        encoding="utf-8",
    )
    client = Scripted()
    record = execute_scripted(plans, out, _send_ceiling(slots), _offpeak, client, dispatch=True)
    assert [request_sha256(body) for body in client.bodies] == [slot["request_sha256"] for slot in slots[1:]]
    assert record["complete"] is True
    assert record["provider_called"] is False
    assert Decimal(record["outstanding_unknown_timeout_cny"]) == 0
    assert Decimal(record["spend_cny"]) > Decimal("0.01")
    assert not any(request_sha256(body) == slots[0]["request_sha256"] for body in client.bodies)


def test_resume_is_bound_to_the_frozen_wire_manifest(tmp_path, monkeypatch):
    _deny_network(monkeypatch)
    plans = _tiny_plans()
    slots, _total = _slot_total(plans)
    ceiling = _send_ceiling(slots)
    out = tmp_path / "manifest"
    with pytest.raises(AmendmentFlightRefused, match="unknown charge held"):
        execute_scripted(plans, out, ceiling, _offpeak, TimeoutThen(), dispatch=True)
    manifest = out / "wire-manifest.json"
    frozen = manifest.read_bytes()
    stored = _read(manifest)
    assert stored["entire_original_plan"] is True
    assert stored["slot_count"] == len(slots) == 4
    partial = _plans([("tiny_a", "a", _shared("alpha", "One short claim."))])
    client = Scripted()
    with pytest.raises(AmendmentFlightRefused, match="frozen wire manifest"):
        execute_scripted(partial, out, ceiling, _offpeak, client, dispatch=True)
    changed = _plans(
        [
            ("tiny_a", "a different question", _shared("alpha", "One short claim.")),
            ("tiny_b", "b", _shared("beta", "A different claim.")),
        ]
    )
    with pytest.raises(AmendmentFlightRefused, match="frozen wire manifest"):
        execute_scripted(changed, out, ceiling, _offpeak, client, dispatch=True)
    assert client.bodies == []
    assert manifest.read_bytes() == frozen
    assert not (out / "live.json").exists()
    assert _read(out / "stop.json")["complete"] is False


def test_second_operator_cannot_resume_the_same_run(tmp_path, monkeypatch):
    _deny_network(monkeypatch)
    plans = _tiny_plans()
    slots, _total = _slot_total(plans)
    ceiling = _send_ceiling(slots)
    out = tmp_path / "owner"
    holder = _HoldClient()
    errors = []

    def run():
        try:
            execute_scripted(plans, out, ceiling, _offpeak, holder, dispatch=True)
        except Exception as exc:
            errors.append(exc)

    thread = threading.Thread(target=run)
    thread.start()
    try:
        assert holder.started.wait(10)
        second = Scripted()
        with pytest.raises(AmendmentFlightRefused, match="another operator"):
            execute_scripted(plans, out, ceiling, _offpeak, second, dispatch=True)
        assert second.bodies == []
        assert not (out / "live.json").exists()
    finally:
        holder.release.set()
        thread.join(10)
    assert not thread.is_alive()
    assert errors == []
    assert holder.bodies


def test_local_estimate_does_not_authorize_a_send(tmp_path, monkeypatch):
    _deny_network(monkeypatch)
    plans = _tiny_plans()
    slots, total = _slot_total(plans)
    assert total < documented_call_reserve_cny()
    assert total < Decimal("80.00")
    client = Scripted()
    with pytest.raises(AmendmentFlightRefused, match="remaining worst-case"):
        execute_scripted(plans, tmp_path / "local-only", total, _offpeak, client, dispatch=True)
    assert client.bodies == []
    stop = _read(tmp_path / "local-only" / "stop.json")
    assert stop["complete"] is False
    assert stop["would_label_complete"] is False
    assert stop["provider_called"] is False
    assert stop["spending_guarantee"] is False
    assert stop["provider_enforced_spend_limit"] is False
    assert stop["ceiling_is_hard_stop"] is False
    assert stop["money_limit"] == "estimated to fit ¥80"
    assert Decimal(stop["documented_call_reserve_cny"]) == documented_call_reserve_cny()
    assert Decimal(stop["remaining_worst_case_cny"]) > Decimal(stop["ceiling_cny"])
    assert not (tmp_path / "local-only" / "calls-ledger.jsonl").exists()
    assert not (tmp_path / "local-only" / "live.json").exists()
    del slots


def test_provider_bill_over_the_eighty_yuan_ceiling_is_kept_and_not_completed(tmp_path, monkeypatch):
    _deny_network(monkeypatch)
    plans = _tiny_plans()
    slots, total = _slot_total(plans)
    local = local_input_tokens(slots[0]["body"])
    billed = 80_000_001
    actual = spend_cny("off-peak", billed, 0, 1)
    assert total < Decimal("80.00")
    assert actual > Decimal("80.00")
    assert actual > documented_call_reserve_cny()
    out = tmp_path / "over-eighty"
    client = Scripted(_usage(billed, output=1))
    with pytest.raises(AmendmentFlightRefused, match="documented per-call reserve"):
        execute_scripted(plans, out, Decimal("80.00"), _offpeak, client, dispatch=True)
    assert len(client.bodies) == 1
    assert client.bodies[0]["max_tokens"] == 8192
    assert not (out / "live.json").exists()
    stop = _read(out / "stop.json")
    assert stop["complete"] is False
    assert stop["would_label_complete"] is False
    assert stop["hard_cap_cny"] == "80.00"
    assert Decimal(stop["ceiling_cny"]) == Decimal("80.00")
    assert Decimal(stop["spend_cny"]) == actual
    assert Decimal(stop["spend_cny"]) > Decimal("80.00")
    assert stop["billed_input_tokens"] == billed
    assert stop["local_input_tokens"] == local
    assert stop["ceiling_is_hard_stop"] is False
    assert stop["spending_guarantee"] is False
    ledger = (out / "calls-ledger.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(ledger) == 1
    assert Decimal(json.loads(ledger[0])["bill"]["spend_cny"]) == actual

    again = Scripted(_usage(billed, output=1))
    with pytest.raises(AmendmentFlightRefused, match="documented per-call reserve"):
        execute_scripted(plans, out, Decimal("80.00"), _offpeak, again, dispatch=True)
    assert again.bodies == []
    assert (out / "calls-ledger.jsonl").read_text(encoding="utf-8").splitlines() == ledger
    assert not (out / "live.json").exists()
    assert Decimal(_read(out / "stop.json")["spend_cny"]) == actual


def test_billed_input_above_the_estimate_can_finish_only_inside_the_ceiling(tmp_path, monkeypatch):
    _deny_network(monkeypatch)
    plans = _tiny_plans()
    slots, total = _slot_total(plans)
    local = local_input_tokens(slots[0]["body"])
    billed = local + 1
    per_call = spend_cny("off-peak", billed, 0, 4)
    ceiling = _send_ceiling(slots)
    out = tmp_path / "hot-but-inside"
    client = Scripted(_usage(billed))
    record = execute_scripted(plans, out, ceiling, _offpeak, client, dispatch=True)
    assert len(client.bodies) == len(slots)
    assert record["complete"] is True
    assert record["provider_called"] is False
    assert record["flight_ready"] is False
    assert Decimal(record["spend_cny"]) == per_call * len(slots)
    assert Decimal(record["spend_cny"]) < total
    assert Decimal(record["spend_cny"]) < ceiling
    assert Decimal(record["spend_cny"]) < Decimal("80.00")
    assert record["spending_guarantee"] is False
    assert Decimal(record["hard_cap_cny"]) == Decimal("80.00")
    rows = [json.loads(line) for line in (out / "calls-ledger.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == len(slots)
    assert all(row["input_above_local_estimate"] is True for row in rows)
    assert all(row["billed_input_tokens"] == billed for row in rows)
    assert all(row["local_input_tokens"] == local for row in rows)
    assert sum((Decimal(row["bill"]["spend_cny"]) for row in rows), Decimal("0")) == Decimal(record["spend_cny"])


def test_resume_note_states_the_eighty_yuan_hard_stop():
    note = (MODULE.parent / "amendment_s2x2_flight_resume.md").read_text(encoding="utf-8")
    assert "71.751836" in note
    assert "80.00" in note
    assert "prompt_tokens" in note
    assert "live.json" in note
    assert "partial run is not labeled complete" in note
    assert "The paid flight is not ready." in note
    assert "not a provider invoice" in note
    assert "estimated to fit" in note
    assert "capped at ¥80" not in note
    assert "not authorization to start a paid flight" in note
    assert "1,048,576" in note
    assert "may stop short" in note
    assert "not a forecast" in note
    assert "5.00" in note
    assert "next request" in note
    assert "not the funding gate" in note
    assert "not a spending guarantee" in note
    source = MODULE.read_text(encoding="utf-8")
    assert "capped at ¥80" not in source
    assert 'documented_call_reserve_cny() * summary["send_slots"]' not in source
    assert "documented_call_reserve_cny() * len(incomplete)" not in source
    assert documented_call_reserve_cny() <= HARD_CAP_CNY
    assert SPENDING_ALERT_CNY == Decimal("5.00")
    assert SPENDING_ALERT_CNY < documented_call_reserve_cny()
    plans = _tiny_plans()
    _, total = _slot_total(plans)
    assert total < Decimal("80.00")
    assert documented_call_reserve_cny() * 2174 > Decimal("80.00")


def test_corrupt_hold_does_not_resume_as_zero(tmp_path):
    plans = _tiny_plans()
    _, total = _slot_total(plans)
    out = tmp_path / "corrupt"
    out.mkdir()
    (out / "cap-hold.json").write_text("{", encoding="utf-8")
    client = Scripted()
    with pytest.raises(AmendmentFlightRefused, match="corrupt"):
        execute_scripted(plans, out, total, _offpeak, client, dispatch=True)
    assert client.bodies == []
    assert not (out / "live.json").exists()


def test_funded_synthetic_completes_only_when_the_bound_fits(tmp_path):
    plans = _tiny_plans()
    slots, _total = _slot_total(plans)
    ceiling = _send_ceiling(slots)
    short = documented_call_reserve_cny() - Decimal("0.000001")
    blocked = Scripted()
    with pytest.raises(AmendmentFlightRefused, match="remaining worst-case"):
        execute_scripted(plans, tmp_path / "short", short, _offpeak, blocked, dispatch=True)
    assert blocked.bodies == []
    assert not (tmp_path / "short" / "live.json").exists()

    client = Scripted()
    record = execute_scripted(plans, tmp_path / "done", ceiling, _offpeak, client, dispatch=True)
    assert len(client.bodies) == len(slots) == 4
    assert {body["thinking"]["type"] for body in client.bodies} == {"disabled", "enabled"}
    assert all(body["max_tokens"] == MAX_TOKENS for body in client.bodies)
    assert all(body["model"] == "deepseek-flash" for body in client.bodies)
    assert all(body["temperature"] == 0.001 and body["store"] is False for body in client.bodies)
    assert record["complete"] is True
    assert record["live"] is False
    assert record["provider_called"] is False
    assert record["flight_ready"] is False
    assert record["synthetic"] is True
    assert record["spend_cny"] == "0.000104"
    live = _read(tmp_path / "done" / "live.json")
    assert live["complete"] is True
    assert live["unknown_charges_reconciled"] is True
    ledger = (tmp_path / "done" / "calls-ledger.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(ledger) == 4
    assert all(json.loads(line)["arms"] == list(ARMS) for line in ledger)

    again = Scripted()
    execute_scripted(plans, tmp_path / "done", ceiling, _offpeak, again, dispatch=True)
    assert again.bodies == []


def test_slack_after_a_timeout_may_finish_and_still_remembers_the_hold(tmp_path):
    plans = _tiny_plans()
    slots, _total = _slot_total(plans)
    first_cost = documented_call_reserve_cny()
    ceiling = _send_ceiling(slots, extra_calls=1)
    out = tmp_path / "slack"
    timeout = TimeoutThen()
    with pytest.raises(AmendmentFlightRefused, match="unknown charge held"):
        execute_scripted(plans, out, ceiling, _offpeak, timeout, dispatch=True)
    assert len(timeout.bodies) == 1
    resume = Scripted()
    record = execute_scripted(plans, out, ceiling, _offpeak, resume, dispatch=True)
    assert len(resume.bodies) == 4
    assert record["complete"] is True
    assert Decimal(record["outstanding_unknown_timeout_cny"]) == first_cost
    assert record["unknown_charges_reconciled"] is False
    assert _read(out / "live.json")["complete"] is True
    assert Decimal(_read(out / "cap-hold.json")["outstanding_unknown_timeout_cny"]) == first_cost


def test_peak_clock_stops_before_a_funded_call(tmp_path):
    plans = _tiny_plans()
    slots, _total = _slot_total(plans)
    client = Scripted()
    with pytest.raises(AmendmentFlightRefused, match="peak_hours"):
        execute_scripted(plans, tmp_path / "peak", _send_ceiling(slots), _peak, client, dispatch=True)
    assert client.bodies == []
    assert _read(tmp_path / "peak" / "stop.json")["stop_reason"] == "peak_hours"
    assert not (tmp_path / "peak" / "live.json").exists()


def test_dispatch_false_and_bad_response_do_not_label_a_run_complete(tmp_path):
    plans = _tiny_plans()
    slots, _total = _slot_total(plans)
    ceiling = _send_ceiling(slots)
    client = Scripted()
    with pytest.raises(AmendmentFlightRefused, match="does not authorize a flight"):
        execute_scripted(plans, tmp_path / "nodispatch", ceiling, _offpeak, client, dispatch=False)
    assert client.bodies == []
    assert not (tmp_path / "nodispatch" / "live.json").exists()

    bad = Scripted({"choices": [], "usage": {"prompt_tokens": 3, "completion_tokens": 1}})
    with pytest.raises(AmendmentFlightRefused, match="unknown charge held"):
        execute_scripted(plans, tmp_path / "bad", ceiling, _offpeak, bad, dispatch=True)
    assert len(bad.bodies) == 1
    assert Decimal(_read(tmp_path / "bad" / "cap-hold.json")["outstanding_unknown_timeout_cny"]) > 0
    assert not (tmp_path / "bad" / "live.json").exists()


def test_identical_payloads_are_not_shared_across_cells():
    rendered = _shared("alpha", "One short claim.")
    plans = _plans(
        [
            ("same_a", "same question", rendered),
            ("same_b", "same question", rendered),
        ]
    )
    summary = summarize_flight(plans, local_counter())
    assert summary["send_slots"] == 4
    assert summary["unique_wire_union"] == 2
    assert summary["cross_cell_duplicate_sends"] == 2
    assert summary["remaining_run_worst_case_cny"] == summary["unique_hash_worst_case_cny"] * 2
    assert is_official_sample(plans) is False


def _snapshot(out: Path) -> dict[str, bytes]:
    names = (
        "calls-ledger.jsonl",
        "cap-hold.json",
        "stop.json",
        "live.json",
        "wire-manifest.json",
    )
    return {name: (out / name).read_bytes() for name in names if (out / name).exists()}


def test_unresolved_exposure_survives_a_missing_hold_and_a_second_restart(tmp_path, monkeypatch):
    _deny_network(monkeypatch)
    plans = _tiny_plans()
    slots, _total = _slot_total(plans)
    ceiling = _send_ceiling(slots)
    out = tmp_path / "missing-hold"
    with pytest.raises(AmendmentFlightRefused, match="unknown charge held"):
        execute_scripted(plans, out, ceiling, _offpeak, TimeoutThen(), dispatch=True)
    unresolved = _read(out / "stop.json")["outstanding_unknown_timeout_cny"]
    assert Decimal(unresolved) == documented_call_reserve_cny()
    (out / "cap-hold.json").unlink()
    client = Scripted()
    with pytest.raises(AmendmentFlightRefused, match="refusing to reset it to zero"):
        execute_scripted(plans, out, ceiling, _offpeak, client, dispatch=True)
    assert client.bodies == []
    assert not (out / "cap-hold.json").exists()
    assert _read(out / "stop.json")["outstanding_unknown_timeout_cny"] == unresolved
    with pytest.raises(AmendmentFlightRefused, match="refusing to reset it to zero"):
        load_cap_state(out)
    with pytest.raises(AmendmentFlightRefused, match="refusing to reset it to zero"):
        execute_scripted(plans, out, ceiling, _offpeak, client, dispatch=True)
    assert client.bodies == []
    assert not (out / "cap-hold.json").exists()
    assert _read(out / "stop.json")["outstanding_unknown_timeout_cny"] == unresolved
    assert not (out / "live.json").exists()


def test_refusal_keeps_a_completion_marker_that_is_the_last_spend_evidence(tmp_path, monkeypatch):
    _deny_network(monkeypatch)
    plans = _tiny_plans()
    slots, _total = _slot_total(plans)
    out = tmp_path / "last-evidence"
    _install_manifest(out, plans)
    marker = json.dumps(
        {"spend_cny": "0.50", "complete": True, "outstanding_unknown_timeout_cny": "0.25"}
    )
    (out / "live.json").write_text(marker, encoding="utf-8")
    before = _snapshot(out)
    client = Scripted()
    ceiling = _send_ceiling(slots)
    with pytest.raises(AmendmentFlightRefused, match="calls ledger is missing"):
        execute_scripted(plans, out, ceiling, _offpeak, client, dispatch=True)
    assert client.bodies == []
    assert _snapshot(out) == before
    with pytest.raises(AmendmentFlightRefused, match="calls ledger is missing"):
        load_cap_state(out)
    with pytest.raises(AmendmentFlightRefused, match="calls ledger is missing"):
        execute_scripted(plans, out, ceiling, _offpeak, client, dispatch=True)
    assert client.bodies == []
    assert _snapshot(out) == before


def test_rehash_rejects_a_mutated_body_that_keeps_its_hash_label(tmp_path, monkeypatch):
    _deny_network(monkeypatch)
    plans = _tiny_plans()
    slots, _total = _slot_total(plans)
    out = tmp_path / "mutated"
    _install_manifest(out, plans)
    frozen = (out / "wire-manifest.json").read_bytes()
    body = plans[0]["_wire_bodies"][slots[0]["request_sha256"]]
    body["messages"] = [{"role": "user", "content": "mutated question"}]
    assert request_sha256(body) != slots[0]["request_sha256"]
    client = Scripted()
    with pytest.raises(AmendmentFlightRefused, match="stored hash label"):
        execute_scripted(plans, out, _send_ceiling(slots), _offpeak, client, dispatch=True)
    assert client.bodies == []
    assert (out / "wire-manifest.json").read_bytes() == frozen
    assert not (out / "live.json").exists()
    assert not (out / "calls-ledger.jsonl").exists()


def test_completion_requires_each_settlement_to_match_the_manifest(tmp_path, monkeypatch):
    _deny_network(monkeypatch)
    plans = _tiny_plans()
    slots = wire_slots(plans)
    out = tmp_path / "mismatch"
    _install_manifest(out, plans)
    lines = []
    for index, slot in enumerate(slots):
        digest = "0" * 64 if index == 0 else slot["request_sha256"]
        lines.append(
            json.dumps(
                {
                    "slot_id": slot["slot_id"],
                    "request_sha256": digest,
                    "bill": {"spend_cny": "0.000001"},
                }
            )
        )
    ledger = out / "calls-ledger.jsonl"
    ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")
    before = _snapshot(out)
    client = Scripted()
    with pytest.raises(AmendmentFlightRefused, match="does not match the frozen manifest"):
        execute_scripted(plans, out, _send_ceiling(slots), _offpeak, client, dispatch=True)
    assert client.bodies == []
    assert not (out / "live.json").exists()
    assert _snapshot(out) == before
    with pytest.raises(AmendmentFlightRefused, match="does not match the frozen manifest"):
        execute_scripted(plans, out, _send_ceiling(slots), _offpeak, client, dispatch=True)
    assert client.bodies == []
    assert _snapshot(out) == before


def test_recovery_does_not_rewrite_accounting_without_the_owner_lock(tmp_path, monkeypatch):
    _deny_network(monkeypatch)
    plans = _tiny_plans()
    slots, _total = _slot_total(plans)
    out = tmp_path / "readonly"
    _install_manifest(out, plans)
    amount = documented_call_reserve_cny()
    (out / "cap-hold.json").write_text(
        json.dumps(
            {
                "settled_spend_cny": "0",
                "outstanding_unknown_timeout_cny": "0",
                "timeout_events": [],
                "pending_call": {
                    "slot_id": slots[0]["slot_id"],
                    "request_sha256": slots[0]["request_sha256"],
                    "held_worst_case_cny": format(amount, "f"),
                    "reason": "in flight",
                },
            }
        ),
        encoding="utf-8",
    )
    (out / "stop.json").write_text(
        json.dumps({"spend_cny": "0", "outstanding_unknown_timeout_cny": "0", "calls_already_settled": 0}),
        encoding="utf-8",
    )
    before = _snapshot(out)
    state = load_cap_state(out)
    assert state.unknown == amount
    assert state.settled == 0
    assert _snapshot(out) == before
    held = threading.Event()
    release = threading.Event()

    def occupy():
        import fcntl
        import os

        fd = os.open(out / "run.lock", os.O_CREAT | os.O_RDWR, 0o644)
        fcntl.flock(fd, fcntl.LOCK_EX)
        held.set()
        assert release.wait(10)
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)

    thread = threading.Thread(target=occupy)
    thread.start()
    assert held.wait(10)
    try:
        again = load_cap_state(out)
        assert again.unknown == amount
        assert _snapshot(out) == before
    finally:
        release.set()
        thread.join(10)
    assert not thread.is_alive()


def test_documented_reserve_is_held_before_send(tmp_path, monkeypatch):
    _deny_network(monkeypatch)
    plans = _tiny_plans()
    slots, _total = _slot_total(plans)
    reserve = documented_call_reserve_cny()
    assert reserve == spend_cny("peak", 1_048_576, 0, 384 * 1024)
    assert reserve * 2174 > Decimal("80.00")
    out = tmp_path / "reserve"
    seen = {}

    class Watch:
        def complete(self, body):
            hold = _read(out / "cap-hold.json")
            seen["held"] = Decimal(hold["pending_call"]["held_worst_case_cny"])
            return _usage(10)

    record = execute_scripted(plans, out, _send_ceiling(slots), _offpeak, Watch(), dispatch=True)
    assert seen["held"] == reserve
    assert record["complete"] is True
    assert record["spending_guarantee"] is False
    assert record["provider_called"] is False
    blocked = Scripted()
    with pytest.raises(AmendmentFlightRefused, match="remaining worst-case"):
        execute_scripted(
            plans,
            tmp_path / "one-short",
            reserve - Decimal("0.000001"),
            _offpeak,
            blocked,
            dispatch=True,
        )
    assert blocked.bodies == []
    note = (MODULE.parent / "amendment_s2x2_flight_resume.md").read_text(encoding="utf-8")
    assert "estimated to fit" in note
    assert "capped at ¥80" not in note
    assert "capped at ¥80" not in MODULE.read_text(encoding="utf-8")


def test_charge_above_reservation_blocks_restarts_until_reconciled(tmp_path, monkeypatch):
    """On cac42dd8 a restart after this bill made three further mock calls."""
    _deny_network(monkeypatch)
    plans = _tiny_plans()
    slots = wire_slots(plans)
    reserve = documented_call_reserve_cny()
    amount = reserve + Decimal("0.01")
    assert amount < HARD_CAP_CNY
    assert amount + reserve * 3 < HARD_CAP_CNY
    out = tmp_path / "over-reserve"
    first = Scripted(_usage_priced(amount))
    with pytest.raises(AmendmentFlightRefused, match="documented per-call reserve"):
        execute_scripted(plans, out, HARD_CAP_CNY, _offpeak, first, dispatch=True)
    assert len(first.bodies) == 1
    ledger = (out / "calls-ledger.jsonl").read_bytes()
    assert Decimal(json.loads(ledger.decode().splitlines()[0])["bill"]["spend_cny"]) == amount
    assert not (out / "live.json").exists()
    assert not (out / "charge-reconciliation.json").exists()

    hold = _read(out / "cap-hold.json")
    hold["sticky_stop_reason"] = None
    (out / "cap-hold.json").write_text(json.dumps(hold), encoding="utf-8")
    for _ in range(2):
        again = Scripted()
        with pytest.raises(AmendmentFlightRefused, match="documented per-call reserve"):
            execute_scripted(plans, out, HARD_CAP_CNY, _offpeak, again, dispatch=True)
        assert again.bodies == []
    assert (out / "calls-ledger.jsonl").read_bytes() == ledger
    assert not (out / "live.json").exists()

    wrong = {
        "entries": [
            {"slot_id": slots[0]["slot_id"], "spend_cny": "1.00", "reconciled": True},
        ]
    }
    (out / "charge-reconciliation.json").write_text(json.dumps(wrong), encoding="utf-8")
    blocked = Scripted()
    with pytest.raises(AmendmentFlightRefused, match="documented per-call reserve"):
        execute_scripted(plans, out, HARD_CAP_CNY, _offpeak, blocked, dispatch=True)
    assert blocked.bodies == []
    assert (out / "calls-ledger.jsonl").read_bytes() == ledger

    reconciled = {
        "entries": [
            {
                "slot_id": slots[0]["slot_id"],
                "spend_cny": format(amount, "f"),
                "reconciled": True,
            }
        ]
    }
    (out / "charge-reconciliation.json").write_text(json.dumps(reconciled), encoding="utf-8")
    resumed = Scripted()
    record = execute_scripted(plans, out, HARD_CAP_CNY, _offpeak, resumed, dispatch=True)
    assert len(resumed.bodies) == 3
    assert record["complete"] is True
    assert record["spending_guarantee"] is False
    assert record["provider_called"] is False
    assert Decimal(record["spend_cny"]) > amount
    assert json.loads((out / "calls-ledger.jsonl").read_text(encoding="utf-8").splitlines()[0])["bill"]["spend_cny"] == format(amount, "f")


def test_unconfirmed_quote_above_the_reserve_blocks_restart(tmp_path, monkeypatch):
    _deny_network(monkeypatch)
    plans = _tiny_plans()
    reserve = documented_call_reserve_cny()
    amount = reserve + Decimal("0.01")
    out = tmp_path / "unconfirmed-over"
    payload = _usage_priced(amount)
    payload["choices"] = []

    class Bad:
        def __init__(self):
            self.bodies = []

        def complete(self, body):
            self.bodies.append(body)
            return payload

    bad = Bad()
    with pytest.raises(AmendmentFlightRefused, match="documented per-call reserve"):
        execute_scripted(plans, out, HARD_CAP_CNY, _offpeak, bad, dispatch=True)
    assert len(bad.bodies) == 1
    assert Decimal(_read(out / "cap-hold.json")["outstanding_unknown_timeout_cny"]) == amount
    again = Scripted()
    with pytest.raises(AmendmentFlightRefused, match="documented per-call reserve"):
        execute_scripted(plans, out, HARD_CAP_CNY, _offpeak, again, dispatch=True)
    assert again.bodies == []
    assert not (out / "live.json").exists()
    assert not (out / "calls-ledger.jsonl").exists()


def test_missing_request_hash_blocks_before_another_send(tmp_path, monkeypatch):
    """On cac42dd8 this ledger was sent three more times and rejected only at completion."""
    _deny_network(monkeypatch)
    plans = _tiny_plans()
    slots = wire_slots(plans)
    for label in (None, ""):
        out = tmp_path / f"missing-hash-{label!r}"
        _install_manifest(out, plans)
        row = {"slot_id": slots[0]["slot_id"], "bill": {"spend_cny": "0.000001"}}
        if label is not None:
            row["request_sha256"] = label
        ledger = out / "calls-ledger.jsonl"
        ledger.write_text(json.dumps(row) + "\n", encoding="utf-8")
        before = ledger.read_bytes()
        client = Scripted()
        with pytest.raises(AmendmentFlightRefused, match="does not match the frozen manifest"):
            execute_scripted(plans, out, HARD_CAP_CNY, _offpeak, client, dispatch=True)
        assert client.bodies == []
        with pytest.raises(AmendmentFlightRefused, match="does not match the frozen manifest"):
            execute_scripted(plans, out, HARD_CAP_CNY, _offpeak, client, dispatch=True)
        assert client.bodies == []
        assert ledger.read_bytes() == before
        assert not (out / "live.json").exists()


def test_unconfirmed_offpeak_quote_does_not_release_the_peak_reserve(tmp_path, monkeypatch):
    _deny_network(monkeypatch)
    plans = _tiny_plans()
    reserve = documented_call_reserve_cny()
    cheap = spend_cny("off-peak", 10, 0, 4)
    assert cheap < reserve
    ceiling = reserve + cheap
    out = tmp_path / "unconfirmed"
    bad_payload = {
        "choices": [],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 4,
            "prompt_cache_hit_tokens": 0,
            "prompt_cache_miss_tokens": 10,
        },
    }

    class Bad:
        def __init__(self):
            self.bodies = []

        def complete(self, body):
            self.bodies.append(body)
            return bad_payload

    bad = Bad()
    with pytest.raises(AmendmentFlightRefused, match="unknown charge held"):
        execute_scripted(plans, out, ceiling, _offpeak, bad, dispatch=True)
    assert len(bad.bodies) == 1
    hold = _read(out / "cap-hold.json")
    assert Decimal(hold["outstanding_unknown_timeout_cny"]) == reserve
    assert Decimal(hold["settled_spend_cny"]) == 0
    again = Scripted()
    with pytest.raises(AmendmentFlightRefused, match="remaining worst-case"):
        execute_scripted(plans, out, ceiling, _offpeak, again, dispatch=True)
    assert again.bodies == []
    assert Decimal(_read(out / "cap-hold.json")["outstanding_unknown_timeout_cny"]) == reserve
    assert not (out / "live.json").exists()


def test_spending_alert_does_not_stop_a_run_under_the_eighty_yuan_ceiling(tmp_path, monkeypatch):
    _deny_network(monkeypatch)
    plans = _tiny_plans()
    slots = wire_slots(plans)
    reserve = documented_call_reserve_cny()
    per_call = Decimal("5.10")
    assert SPENDING_ALERT_CNY < per_call < reserve
    out = tmp_path / "alert"
    client = Scripted(_usage_priced(per_call))
    record = execute_scripted(plans, out, HARD_CAP_CNY, _offpeak, client, dispatch=True)
    assert len(client.bodies) == len(slots) == 4
    assert record["complete"] is True
    assert record["spending_guarantee"] is False
    assert record["spending_alert_is_hard_cap"] is False
    assert record["spending_alert_is_forecast"] is False
    assert record["spending_alert_reached"] is True
    assert Decimal(record["spending_alert_cny"]) == SPENDING_ALERT_CNY
    assert Decimal(record["spend_cny"]) == per_call * len(slots)
    assert Decimal(record["spend_cny"]) > SPENDING_ALERT_CNY
    assert Decimal(record["spend_cny"]) < HARD_CAP_CNY
    assert record["provider_called"] is False


def test_run_stops_short_when_the_next_request_would_pass_the_ceiling(tmp_path, monkeypatch):
    _deny_network(monkeypatch)
    plans = _tiny_plans()
    reserve = documented_call_reserve_cny()
    per_call = Decimal("5.10")
    assert per_call < reserve
    ceiling = per_call + reserve - Decimal("0.000001")
    assert ceiling < HARD_CAP_CNY
    out = tmp_path / "short-run"
    client = Scripted(_usage_priced(per_call))
    with pytest.raises(AmendmentFlightRefused, match="remaining worst-case"):
        execute_scripted(plans, out, ceiling, _offpeak, client, dispatch=True)
    assert len(client.bodies) == 1
    stop = _read(out / "stop.json")
    assert stop["complete"] is False
    assert stop["would_label_complete"] is False
    assert stop["spending_guarantee"] is False
    assert stop["run_may_stop_short"] is True
    assert Decimal(stop["spend_cny"]) == per_call
    assert Decimal(stop["slots_remaining"]) == 3
    assert not (out / "live.json").exists()
    again = Scripted(_usage_priced(per_call))
    with pytest.raises(AmendmentFlightRefused, match="remaining worst-case"):
        execute_scripted(plans, out, ceiling, _offpeak, again, dispatch=True)
    assert again.bodies == []


def _git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def test_frozen_amendment_catalogues_are_unchanged_vs_the_catalogue_tip():
    status = _git(["status", "--porcelain", "--", "docs/amendment-s2x2"])
    assert status.returncode == 0, status.stderr
    assert status.stdout == ""
    current = _git(["rev-parse", "HEAD:docs/amendment-s2x2"])
    assert current.returncode == 0, current.stderr
    assert current.stdout.strip() == CATALOGUE_TREE
    # This object is absent from a depth-1 push or pull_request checkout.
    if _git(["cat-file", "-e", f"{CATALOGUE_TIP}^{{commit}}"]).returncode == 0:
        recorded = _git(["rev-parse", f"{CATALOGUE_TIP}:docs/amendment-s2x2"])
        assert recorded.returncode == 0, recorded.stderr
        assert recorded.stdout.strip() == CATALOGUE_TREE
        diff = _git(["diff", "--exit-code", CATALOGUE_TIP, "--", "docs/amendment-s2x2"])
        assert diff.returncode == 0, diff.stderr or diff.stdout


@pytest.fixture(scope="module")
def official_flight():
    if not (PIN / "BFCL_v4_multiple.json").is_file():
        pytest.skip("pinned BFCL files are not in this environment")
    flight = build_flight(PIN)
    summary = summarize_flight(flight["plans"], local_counter())
    return flight, summary


def _arm_body(plan: dict, kind: str, arm: str) -> dict:
    digest = next(group["request_sha256"] for group in plan[f"{kind}_groups"] if arm in group["arms"])
    return plan[f"_{kind}_bodies"][digest]


def test_plan_identity_and_wire_diff_for_the_official_840(official_flight):
    flight, summary = official_flight
    assert flight["control_cases"] == 640
    assert flight["control_x2_equals_u"] == 640
    assert flight["control_sx2_equals_s2"] == 640
    assert flight["flight_ready"] is False
    assert is_official_sample(flight["plans"]) is True
    assert summary["unique_plan_hashes"] == {"off": 1087, "on": 1087}
    assert summary["unique_wire_hashes"] == {"off": 1087, "on": 1087}
    assert summary["unique_plan_union"] == 2174
    assert summary["unique_wire_union"] == 2174
    assert summary["send_slots"] == 2174
    assert summary["cross_cell_duplicate_sends"] == 0
    assert summary["plan_and_wire_hash_sets_disjoint"] is True
    assert summary["wire_minus_plan_token_deltas"] == [6]
    for pass_name in ("off", "on"):
        assert summary["token_totals_plan"]["all_840"][pass_name] == PLAN_TOTALS
        assert summary["token_totals_wire"]["all_840"][pass_name] == WIRE_TOTALS
        for scope, totals in SCOPE_PLAN.items():
            assert summary["token_totals_plan"][scope][pass_name] == totals
            assert summary["unique_by_scope_plan"][scope][pass_name] == SCOPE_UNIQUE[scope]
    compared = {"off": 0, "on": 0}
    for plan in flight["plans"]:
        for arm in ARMS:
            plan_dump = dump_request(_arm_body(plan, "plan", arm))
            wire_dump = dump_request(_arm_body(plan, "wire", arm))
            assert "max_tokens" not in _arm_body(plan, "plan", arm)
            assert wire_dump == plan_dump[:-1] + ',"max_tokens":8192}'
            compared[plan["thinking"]] += 1
    assert compared == {"off": 3360, "on": 3360}
    independent = Decimal("0")
    counter = local_counter()
    for slot in wire_slots(flight["plans"]):
        tokens = counter.count(dump_request(slot["body"]))
        independent += spend_cny("off-peak", tokens, 0, MAX_TOKENS)
    assert independent == summary["remaining_run_worst_case_cny"] == Decimal("71.751836")
    assert independent <= HARD_CAP_CNY
    assert independent > Decimal("40.00")
    manifest = wire_manifest(flight["plans"])
    assert manifest["slot_count"] == 2174
    assert manifest["manifest_sha256"] == ORDERED_SLOT_DIGEST


def test_official_sample_refuses_when_underfunded_and_when_the_cap_would_fund_it(official_flight, tmp_path, monkeypatch):
    flight, _summary = official_flight
    opened = []

    def deny(*_args, **_kwargs):
        opened.append(True)
        raise AssertionError("socket opened")

    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(urllib.request, "urlopen", deny)
    reserve = documented_call_reserve_cny()
    under = Scripted()
    with pytest.raises(AmendmentFlightRefused, match="remaining worst-case"):
        execute_scripted(flight["plans"], tmp_path / "yen1", Decimal("1.00"), _offpeak, under, dispatch=True)
    assert under.bodies == []
    stop = _read(tmp_path / "yen1" / "stop.json")
    assert stop["complete"] is False
    assert stop["would_label_complete"] is False
    assert stop["calls_already_settled"] == 0
    assert Decimal(stop["local_estimate_remaining_cny"]) == Decimal("71.751836")
    assert Decimal(stop["remaining_worst_case_cny"]) == reserve
    assert Decimal(stop["remaining_worst_case_cny"]) > Decimal(stop["ceiling_cny"])
    assert stop["spending_guarantee"] is False
    assert stop["full_run_peak_prereservation_is_funding_gate"] is False
    assert stop["ceiling_is_hard_stop"] is False
    assert Decimal(stop["ceiling_cny"]) == Decimal("1.00")
    assert not (tmp_path / "yen1" / "live.json").exists()

    # ¥40 does not cover the local estimate. The next request still fits, so
    # the refusal is the unauthorized official start, and the run is not
    # described as guaranteed to finish.
    for name, ceiling in (("yen40", Decimal("40.00")), ("yen80", HARD_CAP_CNY)):
        client = Scripted()
        with pytest.raises(AmendmentFlightRefused, match="paid flight is not authorized"):
            execute_scripted(flight["plans"], tmp_path / name, ceiling, _offpeak, client, dispatch=True)
        assert client.bodies == []
        record = _read(tmp_path / name / "stop.json")
        assert record["complete"] is False
        assert record["provider_call_authorized"] is False
        assert record["spending_guarantee"] is False
        assert record["completion_guaranteed"] is False
        assert record["run_may_stop_short"] is True
        assert record["full_run_peak_prereservation_is_funding_gate"] is False
        assert Decimal(record["local_estimate_remaining_cny"]) == Decimal("71.751836")
        assert Decimal(record["remaining_worst_case_cny"]) == reserve
        assert Decimal(record["remaining_worst_case_cny"]) <= ceiling
        assert not (tmp_path / name / "live.json").exists()
    assert opened == []


def test_official_sample_stays_unauthorized_when_a_reservation_would_fit(official_flight, tmp_path, monkeypatch):
    _deny_network(monkeypatch)
    monkeypatch.setattr(
        "tool_compression.amendment_s2x2_flight.documented_call_reserve_cny",
        lambda: Decimal("0.01"),
    )
    flight, _summary = official_flight
    client = Scripted()
    with pytest.raises(AmendmentFlightRefused, match="paid flight is not authorized"):
        execute_scripted(flight["plans"], tmp_path / "forced-fit", HARD_CAP_CNY, _offpeak, client, dispatch=True)
    assert client.bodies == []
    assert _read(tmp_path / "forced-fit" / "stop.json")["complete"] is False
    assert not (tmp_path / "forced-fit" / "live.json").exists()
    # 2,174 sends at ¥0.01 would fit in ¥80. That used to be treated as a
    # funded guaranteed start. It is still refused, and spending_guarantee stays false.
    assert Decimal("0.01") * 2174 <= HARD_CAP_CNY
    gate = preflight(PIN, tmp_path / "forced-gate", _offpeak)
    assert gate["start_refused"] is True
    assert gate["hard_cap_funds_remaining_run"] is False
    assert gate["spending_guarantee"] is False
    assert gate["completion_guaranteed"] is False
    assert gate["official_plan_budgetable_under_hard_cap"] is True
    assert gate["provider_call_authorized"] is False


def test_preflight_reports_the_bound_and_does_not_call(official_flight, tmp_path, capsys):
    gate = preflight(PIN, tmp_path / "gate", _offpeak)
    assert gate["flight_ready"] is False
    assert gate["paid_flight_ready"] is False
    assert gate["provider_call_authorized"] is False
    assert gate["live_dispatch"] == "refused"
    assert gate["provider_called"] is False
    assert gate["calls_dispatched"] == 0
    assert gate["hard_cap_cny"] == "80.00"
    assert gate["hard_cap_funds_remaining_run"] is False
    assert gate["start_refused"] is True
    assert gate["spending_guarantee"] is False
    assert gate["provider_enforced_spend_limit"] is False
    assert gate["completion_guaranteed"] is False
    assert gate["run_may_stop_short"] is True
    assert gate["money_limit"] == "estimated to fit ¥80"
    assert gate["local_estimate_fits_ceiling"] is True
    assert gate["documented_reservation_scope"] == "next request only"
    assert gate["documented_reservation_fits_ceiling"] is True
    assert gate["next_request_reserve_fits_ceiling"] is True
    assert Decimal(gate["documented_reservation_cny"]) == documented_call_reserve_cny()
    assert Decimal(gate["next_request_reserve_cny"]) == documented_call_reserve_cny()
    assert Decimal(gate["documented_reservation_cny"]) < Decimal("80.00")
    assert gate["full_run_peak_prereservation_is_funding_gate"] is False
    assert gate["official_plan_budgetable_under_hard_cap"] is True
    assert Decimal(gate["spending_alert_cny"]) == SPENDING_ALERT_CNY
    assert gate["spending_alert_is_hard_cap"] is False
    assert gate["spending_alert_is_forecast"] is False
    assert gate["spending_alert_reached"] is False
    assert gate["manifest_sha256"] == ORDERED_SLOT_DIGEST
    assert gate["manifest_persisted_before_send"] is True
    assert gate["remaining_run_worst_case_cny"] == "71.751836"
    assert gate["max_tokens"] == 8192
    assert gate["plan_hash_identity"]["includes_max_tokens"] is False
    assert gate["plan_hash_identity"]["unique_union"] == 2174
    assert gate["wire_hash_identity"]["only_added_field"] == "max_tokens"
    assert gate["wire_hash_identity"]["hashes_equal_plan_hashes"] is False
    assert gate["wire_hash_identity"]["wire_minus_plan_token_deltas"] == [6]
    assert gate["local_tokens_are_provider_T"] is False
    assert gate["human_review"] == "not performed (not passed)"
    assert gate["official_settlement"] is False
    manifest = _read(tmp_path / "gate" / "wire-manifest.json")
    assert manifest["manifest_sha256"] == ORDERED_SLOT_DIGEST
    assert manifest["slot_count"] == 2174
    assert not (tmp_path / "gate" / "live.json").exists()
    assert _read(tmp_path / "gate" / "stop.json")["complete"] is False
    assert main(["--bfcl-root", str(PIN), "--out", str(tmp_path / "cli")]) == 1
    printed = json.loads(capsys.readouterr().out)
    assert printed["paid_flight_ready"] is False
    assert printed["hard_cap_funds_remaining_run"] is False
    assert printed["official_plan_budgetable_under_hard_cap"] is True
    assert printed["spending_guarantee"] is False
    assert printed["completion_guaranteed"] is False
    assert printed["next_request_reserve_fits_ceiling"] is True
    assert printed["remaining_run_worst_case_cny"] == "71.751836"
    assert printed["provider_called"] is False
    assert "capped at ¥80" not in json.dumps(gate)
