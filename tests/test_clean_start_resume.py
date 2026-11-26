"""Resume and bounded retry, with mocked transports and executors only.

No test reads a provider key or opens a socket. The archived c47b186c and
0bf829c6 flights are copied into a temporary directory before anything is
inspected or moved.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import http.client
import json
import shutil

import pytest

from tool_compression.clean_start.categories import result_group
from tool_compression.clean_start.pilot import study_dir
from tool_compression.clean_start.rate_card import spend_usd
from tool_compression.clean_start.resume import apply_resume, describe, inspect_resume
from tool_compression.clean_start.runner import (
    RETRY_BACKOFF_SECONDS,
    RETRY_LIMIT,
    ProviderHTTPError,
    RunStopped,
    TotalDeadlineExceeded,
    build_slots,
    execute,
    is_transport_failure,
    write_plan,
)
from tool_compression.clean_start.scoring import result_relative

NOON = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)
STUDY = study_dir()


def _clock():
    return NOON


def _function(name: str = "echo") -> dict:
    return {
        "name": name,
        "description": "Echo a value.",
        "parameters": {
            "type": "dict",
            "properties": {"value": {"type": "string", "description": "A value."}},
            "required": ["value"],
        },
    }


def _usage() -> dict:
    return {"prompt_tokens": 1000, "prompt_cache_hit_tokens": 200, "prompt_cache_miss_tokens": 800, "completion_tokens": 50}


def _tool(value: str = "a", call_id: str = "call_1") -> dict:
    return {
        "choices": [{"message": {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"id": call_id, "type": "function", "function": {
                "name": "echo", "arguments": json.dumps({"value": value}),
            }}],
        }}],
        "usage": _usage(),
    }


def _text(text: str = "done") -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": text}}], "usage": _usage()}


def _one() -> Decimal:
    return spend_usd(cache_hit=200, cache_miss=800, output=50, at=NOON)[0]


class _Scripted:
    def __init__(self, responses):
        self.responses = list(responses)
        self.bodies = []

    def __call__(self, body):
        self.bodies.append(body)
        if not self.responses:
            raise AssertionError("script exhausted")
        item = self.responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class _Executor:
    def __init__(self):
        self.calls = []

    def initialize(self, case, config):
        self.calls.append(("init", case["id"]))
        return {"GorillaFileSystem": object()}

    def execute_calls(self, strings, case, config):
        self.calls.append(("call", case["id"], list(strings)))
        return [f"ran {item}" for item in strings]


class _BoxLost(BaseException):
    """The process dies here. Nothing in the runner catches it."""


class _DiskMemory:
    """The pinned memory snapshot rules, on disk, without BFCL.

    The ``-0`` prerequisite starts empty. Every other entry loads
    ``<scenario>_final.json``. A prerequisite flush writes its checkpoint, then
    the final file. ``echo(value=x)`` appends x.
    """

    def __init__(self, die_after_flush: str | None = None):
        self.loaded = []
        self.flushed = []
        self.die_after_flush = die_after_flush

    def _folder(self, case, config):
        root = config["initial_config"]["MemoryAPI_kv"]["model_result_dir"]
        return Path(root) / result_group(case["category"]) / "memory_snapshot"

    def initialize(self, case, config):
        folder = self._folder(case, config)
        final = folder / f"{case['scenario']}_final.json"
        if (case.get("prereq") and case["id"].endswith("-0")) or not final.exists():
            notes = []
        else:
            notes = json.loads(final.read_text(encoding="utf-8"))["notes"]
        self.loaded.append((case["id"], list(notes)))
        return {"MemoryAPI_kv": {"notes": notes, "folder": folder, "final": final}}

    def memory_prompt(self, question, case, instances):
        self.current = instances["MemoryAPI_kv"]
        return question

    def execute_calls(self, strings, case, config):
        for item in strings:
            self.current["notes"].append(item.split("'")[1])
        return ["stored" for _ in strings]

    def flush_prereq(self, case, instances):
        instance = instances["MemoryAPI_kv"]
        data = json.dumps({"notes": instance["notes"]}, indent=4)
        checkpoint = instance["folder"] / "prereq_checkpoints" / f"{case['id']}.json"
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        checkpoint.write_text(data)
        instance["final"].write_text(data)
        self.flushed.append(case["id"])
        if case["id"] == self.die_after_flush:
            raise _BoxLost(case["id"])


def _single(case_id: str) -> dict:
    return {
        "id": case_id,
        "category": "multiple",
        "question": [[{"role": "user", "content": "q"}]],
        "function": [_function()],
        "prereq": False,
    }


def _trajectory(case_id: str = "multi_turn_base_0", turns: int = 1) -> dict:
    return {
        "id": case_id,
        "category": "multi_turn_base",
        "question": [[{"role": "user", "content": f"turn {index}"}] for index in range(turns)],
        "function": [_function()],
        "involved_classes": ["GorillaFileSystem"],
        "initial_config": {},
        "prereq": False,
    }


def _memory(case_id: str, prereq: bool) -> dict:
    return {
        "id": case_id,
        "category": "memory_kv",
        "question": [[{"role": "user", "content": f"remember for {case_id}"}]],
        "function": [_function()],
        "involved_classes": ["MemoryAPI_kv"],
        "initial_config": {},
        "prereq": prereq,
        "scenario": "customer",
    }


def _lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _u_slots(cases):
    return [slot for slot in build_slots(cases, ("off",)) if slot["arm"] == "U"]


def _snapshot(out: Path, name: str) -> Path:
    return out / "result/deepseek-flash-thinking-off-U/agentic/memory/kv/memory_snapshot" / name


IDENTITY = {"study": "clean-start-usx", "draw_sha256": "draw-a", "editor_rules": {"S": "s", "X": "x"}}


def test_resume_skips_finished_slots_and_sends_the_stopped_slot_from_its_start(tmp_path):
    cases = [_single("multiple_0"), _trajectory(turns=2), _single("multiple_1")]
    slots = _u_slots(cases)
    first = _Scripted([_text(), _tool("a"), _tool("b"), TimeoutError("read timed out")])
    stopped = execute(
        cases, slots, tmp_path, first, ceiling_usd=Decimal("1"), thinking_modes=("off",),
        clock=_clock, executor=_Executor(), identity=IDENTITY,
    )
    assert stopped["complete"] is False and stopped["slots_sent"] == 1
    old_sidecar = json.loads((tmp_path / "model_outputs/deepseek-flash-thinking-off/U/multi_turn_base_0.json").read_text())
    assert old_sidecar["status"] == "stopped" and len(old_sidecar["steps"]) == 2
    bills_before = (tmp_path / "bills.jsonl").read_bytes()
    attempts_before = (tmp_path / "attempts.jsonl").read_bytes()

    second = _Scripted([_tool("a"), _text("turn 0 done"), _text("turn 1 done"), _text()])
    executor = _Executor()
    result = execute(
        cases, slots, tmp_path, second, ceiling_usd=Decimal("1"), thinking_modes=("off",),
        clock=_clock, executor=executor, identity=IDENTITY, resume=True,
    )
    assert result["complete"] is True
    assert result["session"] == 2
    assert result["slots_sent"] == 3
    assert second.bodies[0]["messages"] == first.bodies[1]["messages"]
    assert [kind for kind, *_rest in executor.calls][0] == "init"
    assert len(second.bodies) == 4
    assert (tmp_path / "bills.jsonl").read_bytes().startswith(bills_before)
    assert (tmp_path / "attempts.jsonl").read_bytes().startswith(attempts_before)
    bills = _lines(tmp_path / "bills.jsonl")
    assert len(bills) == 3 + 4
    assert [row["session"] for row in bills] == [1, 1, 1, 2, 2, 2, 2]
    assert Decimal(result["running_usd"]) == _one() * 7 == sum(Decimal(row["usd"]) for row in bills)
    attempts = _lines(tmp_path / "attempts.jsonl")
    assert [row["attempt"] for row in attempts if row["event"] == "sent"] == list(range(1, 9))
    assert result["unbilled_attempts"] == [
        {"attempt": 4, "event": "failed", "session": 1, "case_id": "multi_turn_base_0", "arm": "U"}
    ]
    for case in cases:
        rows = _lines(tmp_path / result_relative(case["id"], "off", "U"))
        assert [row["id"] for row in rows].count(case["id"]) == 1
    sidecar = json.loads((tmp_path / "model_outputs/deepseek-flash-thinking-off/U/multi_turn_base_0.json").read_text())
    assert sidecar["status"] == "finished" and sidecar["session"] == 2
    kept = tmp_path / "resume/session-2/model_outputs/deepseek-flash-thinking-off/U/multi_turn_base_0.json"
    assert json.loads(kept.read_text()) == old_sidecar
    assert json.loads((tmp_path / "resume/session-2/prior_run.json").read_text())["status"] == "incomplete"
    log = _lines(tmp_path / "resume.jsonl")
    assert len(log) == 1 and log[0]["finished_slots"] == 1
    assert log[0]["next_slot"]["case_id"] == "multi_turn_base_0"
    assert Decimal(log[0]["abandoned_partial_usd"]) == _one() * 2
    assert [row["session"] for row in result["sessions"]] == [1, 2]
    assert result["sessions"][1]["resumed"] is True


def test_resume_counts_recorded_spend_against_the_same_ceiling(tmp_path):
    cases = [_single(f"multiple_{index}") for index in range(5)]
    slots = _u_slots(cases)
    ceiling = _one() * Decimal("2.5")
    execute(
        cases, slots, tmp_path, _Scripted([_text(), _text(), ProviderHTTPError(500, "x")]),
        ceiling_usd=ceiling, thinking_modes=("off",), clock=_clock, identity=IDENTITY,
    )
    again = _Scripted([_text() for _ in range(5)])
    result = execute(
        cases, slots, tmp_path, again, ceiling_usd=ceiling, thinking_modes=("off",),
        clock=_clock, identity=IDENTITY, resume=True,
    )
    assert len(again.bodies) == 1
    assert result["reason"] == "ceiling"
    assert result["slots_sent"] == 3
    assert Decimal(result["running_usd"]) == _one() * 3
    with pytest.raises(RunStopped) as wrong:
        execute(
            cases, slots, tmp_path, _Scripted([]), ceiling_usd=ceiling * 2, thinking_modes=("off",),
            clock=_clock, identity=IDENTITY, resume=True,
        )
    assert wrong.value.reason == "resume_ceiling_mismatch"


def test_resume_refuses_another_draw_slot_order_identity_or_state(tmp_path):
    cases = [_single(f"multiple_{index}") for index in range(3)]
    slots = _u_slots(cases)
    execute(
        cases, slots, tmp_path, _Scripted([_text(), ProviderHTTPError(500, "x")]),
        ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock, identity=IDENTITY,
    )
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir() if path.is_file()}
    refusals = {
        "resume_draw_mismatch": dict(identity={**IDENTITY, "draw_sha256": "draw-b"}),
        "resume_identity_mismatch:editor_rules": dict(identity={**IDENTITY, "editor_rules": {"S": "t", "X": "x"}}),
        "resume_slot_mismatch": dict(slots=list(reversed(slots))),
        "resume_thinking_mismatch": dict(thinking_modes=("off", "on")),
    }
    for reason, change in refusals.items():
        script = _Scripted([_text()])
        kwargs = dict(ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock, identity=IDENTITY, resume=True)
        kwargs.update({key: value for key, value in change.items() if key != "slots"})
        with pytest.raises(RunStopped) as stopped:
            execute(cases, change.get("slots", slots), tmp_path, script, **kwargs)
        assert stopped.value.reason == reason
        assert script.bodies == []
    assert {path.name: path.read_bytes() for path in tmp_path.iterdir() if path.is_file()} == before
    assert not (tmp_path / "resume").exists()

    with pytest.raises(RunStopped) as fresh:
        execute(cases, slots, tmp_path / "empty", _Scripted([]), ceiling_usd=Decimal("1"),
                thinking_modes=("off",), clock=_clock, resume=True)
    assert fresh.value.reason == "resume_without_prior_run"
    write_plan(cases, tmp_path / "plan", pilot=False, thinking_modes=("off",))
    with pytest.raises(RunStopped) as planned:
        execute(cases, slots, tmp_path / "plan", _Scripted([]), ceiling_usd=Decimal("1"),
                thinking_modes=("off",), clock=_clock, resume=True)
    assert planned.value.reason == "resume_without_provider_evidence"

    done = tmp_path / "done"
    execute(cases, slots, done, _Scripted([_text()] * 3), ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock)
    with pytest.raises(RunStopped) as finished:
        execute(cases, slots, done, _Scripted([]), ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock, resume=True)
    assert finished.value.reason == "resume_already_complete"

    broken = tmp_path / "broken"
    execute(cases, slots, broken, _Scripted([_text(), _text(), ProviderHTTPError(500, "x")]),
            ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock)
    rows = _lines(broken / "bills.jsonl")
    rows[1]["usd"] = "0.5"
    (broken / "bills.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    with pytest.raises(RunStopped) as ledger:
        execute(cases, slots, broken, _Scripted([]), ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock, resume=True)
    assert ledger.value.reason == "resume_bill_ledger_inconsistent:2"

    gap = tmp_path / "gap"
    execute(cases, slots, gap, _Scripted([_text(), ProviderHTTPError(500, "x")]),
            ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock)
    later = gap / result_relative("multiple_2", "off", "U")
    with later.open("a") as handle:
        handle.write(json.dumps({"id": "multiple_2", "result": "x"}) + "\n")
    with pytest.raises(RunStopped) as prefix:
        execute(cases, slots, gap, _Scripted([]), ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock, resume=True)
    assert prefix.value.reason == "resume_finished_slots_not_a_prefix:multiple_2:U"


def test_a_result_line_written_just_before_the_box_was_lost_is_moved_aside(tmp_path, monkeypatch):
    import tool_compression.clean_start.runner as runner

    cases = [_single("multiple_0"), _trajectory(), _single("multiple_1")]
    slots = _u_slots(cases)
    original = runner._write_sidecar

    def lose_box(out_dir, slot, sidecar):
        if sidecar.get("status") == "finished" and slot["case_id"] == "multi_turn_base_0":
            raise _BoxLost("after the result line")
        original(out_dir, slot, sidecar)

    monkeypatch.setattr(runner, "_write_sidecar", lose_box)
    with pytest.raises(_BoxLost):
        execute(cases, slots, tmp_path, _Scripted([_text(), _text("lost")]), ceiling_usd=Decimal("1"),
                thinking_modes=("off",), clock=_clock, executor=_Executor(), identity=IDENTITY)
    monkeypatch.setattr(runner, "_write_sidecar", original)
    path = tmp_path / result_relative("multi_turn_base_0", "off", "U")
    assert [row["result"] for row in _lines(path)] == [[["lost"]]]
    assert json.loads((tmp_path / "run.json").read_text())["status"] == "running"

    plan = inspect_resume(tmp_path, cases, slots, identity=IDENTITY, ceiling_usd=Decimal("1"), thinking_modes=("off",))
    assert plan["finished_slots"] == 1
    assert [action["kind"] for action in plan["actions"]] == ["drop_result_line", "quarantine"]
    result = execute(cases, slots, tmp_path, _Scripted([_text("kept"), _text()]), ceiling_usd=Decimal("1"),
                     thinking_modes=("off",), clock=_clock, executor=_Executor(), identity=IDENTITY, resume=True)
    assert result["complete"] is True
    assert [row["result"] for row in _lines(path)] == [[["kept"]]]
    dropped = _lines(tmp_path / "resume/session-2/dropped_result_lines.jsonl")
    assert json.loads(dropped[0]["text"])["result"] == [["lost"]]


def test_a_memory_flush_that_landed_for_the_stopped_prerequisite_is_rolled_back(tmp_path):
    cases = [
        _memory("memory_kv_prereq_0-customer-0", True),
        _memory("memory_kv_prereq_1-customer-1", True),
        _memory("memory_kv_7-customer-7", False),
    ]
    slots = _u_slots(cases)
    dying = _DiskMemory(die_after_flush="memory_kv_prereq_1-customer-1")
    with pytest.raises(_BoxLost):
        execute(cases, slots, tmp_path, _Scripted([_tool("a"), _text(), _tool("b"), _text()]),
                ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock, executor=dying, identity=IDENTITY)
    final = _snapshot(tmp_path, "customer_final.json")
    p0 = _snapshot(tmp_path, "prereq_checkpoints/memory_kv_prereq_0-customer-0.json")
    p1 = _snapshot(tmp_path, "prereq_checkpoints/memory_kv_prereq_1-customer-1.json")
    assert json.loads(final.read_text())["notes"] == ["a", "b"]
    assert p1.exists()

    plan = inspect_resume(tmp_path, cases, slots, identity=IDENTITY, ceiling_usd=Decimal("1"), thinking_modes=("off",))
    assert plan["finished_slots"] == 1
    restore = [action for action in plan["actions"] if action["kind"] == "restore_snapshot"]
    assert restore == [{
        "kind": "restore_snapshot",
        "path": "result/deepseek-flash-thinking-off-U/agentic/memory/kv/memory_snapshot/customer_final.json",
        "from": "result/deepseek-flash-thinking-off-U/agentic/memory/kv/memory_snapshot/prereq_checkpoints/memory_kv_prereq_0-customer-0.json",
        "quarantine": [
            "result/deepseek-flash-thinking-off-U/agentic/memory/kv/memory_snapshot/prereq_checkpoints/memory_kv_prereq_1-customer-1.json",
            "result/deepseek-flash-thinking-off-U/agentic/memory/kv/memory_snapshot/customer_final.json",
        ],
    }]

    memory = _DiskMemory()
    result = execute(cases, slots, tmp_path, _Scripted([_tool("c"), _text(), _text("answer")]),
                     ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock, executor=memory,
                     identity=IDENTITY, resume=True)
    assert result["complete"] is True
    assert memory.loaded == [
        ("memory_kv_prereq_1-customer-1", ["a"]),
        ("memory_kv_7-customer-7", ["a", "c"]),
    ]
    assert json.loads(final.read_text())["notes"] == ["a", "c"]
    assert final.read_bytes() == p1.read_bytes()
    assert json.loads(p0.read_text())["notes"] == ["a"]
    kept = tmp_path / "resume/session-2" / p1.relative_to(tmp_path)
    assert json.loads(kept.read_text())["notes"] == ["a", "b"]


def _repairs(plan: dict) -> list[dict]:
    return [action for action in plan["actions"] if action["kind"] != "quarantine"]


def test_a_box_lost_while_resume_repairs_the_directory_is_resumed_again(tmp_path, monkeypatch):
    import tool_compression.clean_start.resume as resume

    def lose_box(path, data):
        raise _BoxLost("during the repair")

    def inspect(out, cases, slots):
        return inspect_resume(out, cases, slots, identity=IDENTITY, ceiling_usd=Decimal("1"), thinking_modes=("off",))

    memory_out = tmp_path / "memory"
    cases = [
        _memory("memory_kv_prereq_0-customer-0", True),
        _memory("memory_kv_prereq_1-customer-1", True),
        _memory("memory_kv_7-customer-7", False),
    ]
    slots = _u_slots(cases)
    with pytest.raises(_BoxLost):
        execute(cases, slots, memory_out, _Scripted([_tool("a"), _text(), _tool("b"), _text()]),
                ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock,
                executor=_DiskMemory(die_after_flush="memory_kv_prereq_1-customer-1"), identity=IDENTITY)
    first = inspect(memory_out, cases, slots)
    original = resume._fsync_write
    monkeypatch.setattr(resume, "_fsync_write", lose_box)
    with pytest.raises(_BoxLost):
        apply_resume(memory_out, first, NOON.isoformat())
    monkeypatch.setattr(resume, "_fsync_write", original)
    final = _snapshot(memory_out, "customer_final.json")
    assert json.loads(final.read_text())["notes"] == ["a", "b"]
    second = inspect(memory_out, cases, slots)
    assert second["session"] == first["session"] + 1
    assert _repairs(second) == _repairs(first) != []
    result = execute(cases, slots, memory_out, _Scripted([_tool("c"), _text(), _text("answer")]),
                     ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock, executor=_DiskMemory(),
                     identity=IDENTITY, resume=True)
    assert result["complete"] is True
    assert json.loads(final.read_text())["notes"] == ["a", "c"]

    lines_out = tmp_path / "lines"
    import tool_compression.clean_start.runner as runner

    cases = [_trajectory("multi_turn_base_0"), _trajectory("multi_turn_base_1")]
    slots = _u_slots(cases)
    write_sidecar = runner._write_sidecar

    def lose_box_after_the_line(out_dir, slot, sidecar):
        if sidecar.get("status") == "finished" and slot["case_id"] == "multi_turn_base_1":
            raise _BoxLost("after the result line")
        write_sidecar(out_dir, slot, sidecar)

    monkeypatch.setattr(runner, "_write_sidecar", lose_box_after_the_line)
    with pytest.raises(_BoxLost):
        execute(cases, slots, lines_out, _Scripted([_text("first"), _text("lost")]), ceiling_usd=Decimal("1"),
                thinking_modes=("off",), clock=_clock, executor=_Executor(), identity=IDENTITY)
    monkeypatch.setattr(runner, "_write_sidecar", write_sidecar)
    path = lines_out / result_relative("multi_turn_base_1", "off", "U")
    assert path == lines_out / result_relative("multi_turn_base_0", "off", "U")
    first = inspect(lines_out, cases, slots)
    assert first["finished_slots"] == 1
    monkeypatch.setattr(resume, "_fsync_write", lose_box)
    with pytest.raises(_BoxLost):
        apply_resume(lines_out, first, NOON.isoformat())
    monkeypatch.setattr(resume, "_fsync_write", original)
    assert [row["result"] for row in _lines(path)] == [[["first"]], [["lost"]]]
    second = inspect(lines_out, cases, slots)
    assert second["finished_slots"] == 1
    assert _repairs(second) == _repairs(first) != []
    result = execute(cases, slots, lines_out, _Scripted([_text("kept")]), ceiling_usd=Decimal("1"),
                     thinking_modes=("off",), clock=_clock, executor=_Executor(), identity=IDENTITY, resume=True)
    assert result["complete"] is True
    assert [row["result"] for row in _lines(path)] == [[["first"]], [["kept"]]]


def test_a_memory_snapshot_that_matches_no_checkpoint_is_refused(tmp_path):
    cases = [
        _memory("memory_kv_prereq_0-customer-0", True),
        _memory("memory_kv_prereq_1-customer-1", True),
    ]
    slots = _u_slots(cases)
    execute(cases, slots, tmp_path, _Scripted([_tool("a"), _text(), ProviderHTTPError(500, "x")]),
            ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock, executor=_DiskMemory(), identity=IDENTITY)
    final = _snapshot(tmp_path, "customer_final.json")
    final.write_text(json.dumps({"notes": ["edited"]}))
    with pytest.raises(RunStopped) as stopped:
        inspect_resume(tmp_path, cases, slots, identity=IDENTITY, ceiling_usd=Decimal("1"), thinking_modes=("off",))
    assert stopped.value.reason.startswith("resume_memory_snapshot_unexpected:")


def test_a_transport_failure_is_sent_again_with_the_same_body_within_the_limit(tmp_path):
    case = _single("multiple_0")
    slots = _u_slots([case])
    waits = []
    script = _Scripted([http.client.IncompleteRead(b"partial"), _text()])
    result = execute([case], slots, tmp_path, script, ceiling_usd=Decimal("1"), thinking_modes=("off",),
                     clock=_clock, retry_limit=RETRY_LIMIT, sleep=waits.append)
    assert result["complete"] is True
    assert script.bodies[0] == script.bodies[1]
    assert waits == [RETRY_BACKOFF_SECONDS[0]]
    assert result["retries"] == 1
    attempts = _lines(tmp_path / "attempts.jsonl")
    assert [(row["attempt"], row["event"]) for row in attempts] == [
        (1, "sent"), (1, "failed"), (2, "sent"), (2, "completed"),
    ]
    assert attempts[1]["retried"] is True and attempts[1]["may_be_billed"] is True
    assert attempts[2]["retry_of"] == 1
    assert attempts[0]["body_sha256"] == attempts[2]["body_sha256"]
    assert result["unbilled_attempts"] == [
        {"attempt": 1, "event": "failed", "session": 1, "case_id": "multiple_0", "arm": "U"}
    ]
    assert _lines(tmp_path / "bills.jsonl")[0]["attempt"] == 2


def test_retry_is_bounded_and_skips_failures_a_resend_cannot_fix(tmp_path):
    case = _single("multiple_0")
    slots = _u_slots([case])
    waits = []
    script = _Scripted([TimeoutError("t"), TotalDeadlineExceeded("d"), ConnectionResetError("r"), _text()])
    result = execute([case], slots, tmp_path / "bounded", script, ceiling_usd=Decimal("1"), thinking_modes=("off",),
                     clock=_clock, retry_limit=2, sleep=waits.append)
    assert len(script.bodies) == 3
    assert result["reason"] == "provider_error:ConnectionResetError"
    assert result["uncertain_attempts"] == [3]
    assert [row["attempt"] for row in result["unbilled_attempts"]] == [1, 2, 3]
    assert waits == list(RETRY_BACKOFF_SECONDS)
    for index, failure in enumerate((ProviderHTTPError(402, "balance"), ProviderHTTPError(400, "bad"), ValueError("x"))):
        script = _Scripted([failure, _text()])
        stopped = execute([case], slots, tmp_path / f"final-{index}", script, ceiling_usd=Decimal("1"),
                          thinking_modes=("off",), clock=_clock, retry_limit=2, sleep=waits.append)
        assert len(script.bodies) == 1 and stopped["complete"] is False
    assert waits == list(RETRY_BACKOFF_SECONDS)
    unusable = _Scripted([{"choices": [], "usage": _usage()}, _text()])
    stopped = execute([case], slots, tmp_path / "unusable", unusable, ceiling_usd=Decimal("1"),
                      thinking_modes=("off",), clock=_clock, retry_limit=2, sleep=waits.append)
    assert len(unusable.bodies) == 1 and stopped["reason"] == "provider_choice_missing"
    assert is_transport_failure(ProviderHTTPError(503, "busy"))
    assert is_transport_failure(ProviderHTTPError(429, "slow"))
    assert is_transport_failure(http.client.RemoteDisconnected("gone"))
    assert not is_transport_failure(ProviderHTTPError(402, "balance"))
    assert not is_transport_failure(json.JSONDecodeError("x", "y", 0))


def _copy(tmp_path: Path, relative: str) -> Path:
    target = tmp_path / Path(relative).name
    shutil.copytree(STUDY / relative, target)
    return target


def test_resume_reads_the_archived_c47b186c_stop_exactly(tmp_path):
    from tool_compression.clean_start.__main__ import _select_cases

    archive = "evidence/pilot-2026-11-25-revised-c47b186c/original/live-c47b186c"
    before = sha256((STUDY / archive / "attempts.jsonl").read_bytes()).hexdigest()
    out = _copy(tmp_path, archive)
    prior = json.loads((out / "run.json").read_text())
    cases = _select_cases(True, "matched")
    slots = build_slots(cases, ("off",))
    plan = inspect_resume(out, cases, slots, identity=prior["identity"], ceiling_usd=Decimal("20"), thinking_modes=("off",))
    summary = describe(plan)
    assert summary["finished_slots"] == 140 == prior["slots_sent"]
    assert summary["next_slot"]["case_id"] == "memory_kv_prereq_3-customer-3"
    assert summary["next_slot"]["arm"] == "SX"
    assert Decimal(summary["prior_spend_usd"]) == Decimal("0.287883432")
    assert summary["prior_billed"] == 899 and summary["max_attempt"] == 900
    assert [row["attempt"] for row in summary["unbilled_attempts"]] == [900]
    assert summary["unbilled_attempts"][0]["event"] == "failed"
    assert summary["actions"] == [{
        "kind": "quarantine",
        "path": "model_outputs/deepseek-flash-thinking-off/SX/memory_kv_prereq_3-customer-3.json",
        "why": "sidecar of the slot sent again, status stopped",
    }]
    apply_resume(out, plan, NOON.isoformat())
    again = inspect_resume(out, cases, slots, identity=prior["identity"], ceiling_usd=Decimal("20"), thinking_modes=("off",))
    assert again["actions"] == [] and again["finished_slots"] == 140 and again["session"] == 3
    with pytest.raises(RunStopped) as other:
        inspect_resume(out, cases, slots, identity={**prior["identity"], "draw_sha256": "0" * 64},
                       ceiling_usd=Decimal("20"), thinking_modes=("off",))
    assert other.value.reason == "resume_draw_mismatch"
    assert sha256((STUDY / archive / "attempts.jsonl").read_bytes()).hexdigest() == before


def test_resume_reads_the_archived_0bf829c6_box_loss_from_the_ledgers_not_the_stale_run_json(tmp_path):
    from tool_compression.clean_start.validation import select_validation_cases

    out = _copy(tmp_path, "evidence/validation-2026-11-25-0bf829c6/original/live-0bf829c6")
    prior = json.loads((out / "run.json").read_text())
    assert prior["status"] == "running"
    cases = select_validation_cases()
    slots = build_slots(cases, ("off",))
    plan = inspect_resume(out, cases, slots, identity=prior["identity"], ceiling_usd=Decimal("20"), thinking_modes=("off",))
    assert plan["finished_slots"] == 1234
    assert plan["next_slot"]["case_id"] == "memory_kv_136-notetaker-6" and plan["next_slot"]["arm"] == "X"
    assert plan["prior_spend_usd"] == Decimal("0.346230789")
    assert Decimal(prior["running_usd"]) == Decimal("0.346140159")
    assert plan["unbilled_attempts"] == [{
        "attempt": 2482, "event": "no_outcome_recorded", "session": 1,
        "case_id": "memory_kv_136-notetaker-6", "arm": "X",
    }]
    assert plan["actions"] == []
