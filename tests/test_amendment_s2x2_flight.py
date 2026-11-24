"""Offline checks for the U/S2/X2/SX2 runner. No provider call and no API key."""

from datetime import datetime
from decimal import Decimal
from pathlib import Path
import json
import socket
import subprocess
import urllib.request

import pytest

from tool_compression.amendment_s2x2_flight import (
    ARMS,
    CATALOGUE_TIP,
    HARD_CAP_CNY,
    MAX_TOKENS,
    AmendmentFlightRefused,
    accept_run_ceiling,
    build_flight,
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
    wire_slots,
    worst_case_cny,
)
from tool_compression.count import dump_request
from tool_compression.official_840 import generation_body as official_generation_body
from tool_compression.usx_flight import SHANGHAI, rate_card, schedule_at, spend_cny

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
    with pytest.raises(AmendmentFlightRefused, match="80.00 hard cap"):
        accept_run_ceiling(Decimal("80.01"))
    with pytest.raises(AmendmentFlightRefused, match="Decimal"):
        accept_run_ceiling(80.0)  # type: ignore[arg-type]


def test_runner_source_does_not_read_a_key_or_open_a_socket():
    text = MODULE.read_text(encoding="utf-8")
    for banned in (
        "DEEPSEEK_API_KEY",
        "OPENAI_API_KEY",
        "urlopen",
        "import tool_compression.official_840_provider",
        "from tool_compression.official_840_provider",
        "import tool_compression.usx_provider",
        "from tool_compression.usx_provider",
        "execute_plans",
        "api.deepseek.com",
        "getenv",
    ):
        assert banned not in text
    assert text.count("build_live_client") == 1
    before_sender, sender_and_after = text.split("# Request-by-request sender.", 1)
    assert "def _official_provider_client" in before_sender
    assert "build_live_client" in before_sender
    sender, cli = sender_and_after.split("\ndef main(", 1)
    assert "build_live_client" not in sender
    for banned in ("DEEPSEEK_API_KEY", "urlopen", "build_live_client", "os.environ", "getenv"):
        assert banned not in cli


def test_live_flag_refuses_without_a_provider_call(monkeypatch, capsys, tmp_path):
    secret = "sk-test-secret"
    monkeypatch.setenv("DEEPSEEK_API_KEY", secret)
    opened = []

    def deny(*_args, **_kwargs):
        opened.append(True)
        raise AssertionError("socket opened")

    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket.socket, "connect", deny)
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
    slots, total = _slot_total(plans)
    out = tmp_path / "timeout"
    secret = "sk-test-secret"
    first = TimeoutThen(secret)
    with pytest.raises(AmendmentFlightRefused, match="unknown charge held") as caught:
        execute_scripted(plans, out, total, _offpeak, first, dispatch=True)
    assert secret not in str(caught.value)
    assert len(first.bodies) == 1
    assert first.bodies[0]["max_tokens"] == MAX_TOKENS
    stop = _read(out / "stop.json")
    hold = _read(out / "cap-hold.json")
    assert stop["complete"] is False
    assert stop["would_label_complete"] is False
    assert stop["spend_cny"] == "0"
    assert Decimal(hold["outstanding_unknown_timeout_cny"]) == worst_case_cny(slots[0]["body"])
    assert hold["pending_call"] is None
    assert secret not in (out / "stop.json").read_text(encoding="utf-8")
    assert secret not in (out / "cap-hold.json").read_text(encoding="utf-8")
    assert not (out / "live.json").exists()

    resume = Scripted()
    with pytest.raises(AmendmentFlightRefused, match="remaining worst-case"):
        execute_scripted(plans, out, total, _offpeak, resume, dispatch=True)
    assert resume.bodies == []
    reloaded = load_cap_state(out)
    assert reloaded.unknown == worst_case_cny(slots[0]["body"])
    assert reloaded.loaded_events == 1
    assert not (out / "live.json").exists()
    assert _read(out / "stop.json")["complete"] is False


def test_in_flight_hold_is_reloaded_and_blocks_a_resume(tmp_path):
    plans = _tiny_plans()
    slots, total = _slot_total(plans)
    out = tmp_path / "crash"
    out.mkdir()
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
    row = {"slot_id": slots[0]["slot_id"], "bill": {"spend_cny": "1.00"}}
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
    slots, total = _slot_total(plans)
    short = total - Decimal("0.000001")
    blocked = Scripted()
    with pytest.raises(AmendmentFlightRefused, match="remaining worst-case"):
        execute_scripted(plans, tmp_path / "short", short, _offpeak, blocked, dispatch=True)
    assert blocked.bodies == []
    assert not (tmp_path / "short" / "live.json").exists()

    client = Scripted()
    record = execute_scripted(plans, tmp_path / "done", total, _offpeak, client, dispatch=True)
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
    execute_scripted(plans, tmp_path / "done", total, _offpeak, again, dispatch=True)
    assert again.bodies == []


def test_slack_after_a_timeout_may_finish_and_still_remembers_the_hold(tmp_path):
    plans = _tiny_plans()
    slots, total = _slot_total(plans)
    first_cost = worst_case_cny(slots[0]["body"])
    ceiling = total + first_cost
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
    _, total = _slot_total(plans)
    client = Scripted()
    with pytest.raises(AmendmentFlightRefused, match="peak_hours"):
        execute_scripted(plans, tmp_path / "peak", total, _peak, client, dispatch=True)
    assert client.bodies == []
    assert _read(tmp_path / "peak" / "stop.json")["stop_reason"] == "peak_hours"
    assert not (tmp_path / "peak" / "live.json").exists()


def test_dispatch_false_and_bad_response_do_not_label_a_run_complete(tmp_path):
    plans = _tiny_plans()
    _, total = _slot_total(plans)
    client = Scripted()
    with pytest.raises(AmendmentFlightRefused, match="does not authorize a flight"):
        execute_scripted(plans, tmp_path / "nodispatch", total, _offpeak, client, dispatch=False)
    assert client.bodies == []
    assert not (tmp_path / "nodispatch" / "live.json").exists()

    bad = Scripted({"choices": [], "usage": {"prompt_tokens": 3, "completion_tokens": 1}})
    with pytest.raises(AmendmentFlightRefused, match="unknown charge held"):
        execute_scripted(plans, tmp_path / "bad", total, _offpeak, bad, dispatch=True)
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


def test_official_sample_refuses_when_underfunded_and_when_the_cap_would_fund_it(official_flight, tmp_path, monkeypatch):
    flight, _summary = official_flight
    opened = []

    def deny(*_args, **_kwargs):
        opened.append(True)
        raise AssertionError("socket opened")

    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(urllib.request, "urlopen", deny)
    under = Scripted()
    with pytest.raises(AmendmentFlightRefused, match="remaining worst-case"):
        execute_scripted(flight["plans"], tmp_path / "yen40", Decimal("40.00"), _offpeak, under, dispatch=True)
    assert under.bodies == []
    stop = _read(tmp_path / "yen40" / "stop.json")
    assert stop["complete"] is False
    assert stop["would_label_complete"] is False
    assert stop["calls_already_settled"] == 0
    assert Decimal(stop["remaining_worst_case_cny"]) == Decimal("71.751836")
    assert Decimal(stop["ceiling_cny"]) == Decimal("40.00")
    assert not (tmp_path / "yen40" / "live.json").exists()

    funded = Scripted()
    with pytest.raises(AmendmentFlightRefused, match="paid flight is not authorized"):
        execute_scripted(flight["plans"], tmp_path / "yen80", HARD_CAP_CNY, _offpeak, funded, dispatch=True)
    assert funded.bodies == []
    assert _read(tmp_path / "yen80" / "stop.json")["complete"] is False
    assert not (tmp_path / "yen80" / "live.json").exists()
    assert opened == []


def test_preflight_reports_the_bound_and_does_not_call(official_flight, tmp_path, capsys):
    gate = preflight(PIN, tmp_path / "gate", _offpeak)
    assert gate["flight_ready"] is False
    assert gate["paid_flight_ready"] is False
    assert gate["provider_call_authorized"] is False
    assert gate["live_dispatch"] == "refused"
    assert gate["provider_called"] is False
    assert gate["calls_dispatched"] == 0
    assert gate["hard_cap_cny"] == "80.00"
    assert gate["hard_cap_funds_remaining_run"] is True
    assert gate["start_refused"] is False
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
    assert not (tmp_path / "gate" / "live.json").exists()
    assert not (tmp_path / "gate" / "stop.json").exists()
    assert main(["--bfcl-root", str(PIN), "--out", str(tmp_path / "cli")]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["paid_flight_ready"] is False
    assert printed["hard_cap_funds_remaining_run"] is True
    assert printed["remaining_run_worst_case_cny"] == "71.751836"
    assert printed["provider_called"] is False
