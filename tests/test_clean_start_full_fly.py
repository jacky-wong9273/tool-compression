"""The full-fly send policy, skip-and-record, resume with skips, and the --full package.

No test reads a real provider key or reaches the provider. Deadline tests talk
to a local HTTP server on 127.0.0.1 that answers the way a queued DeepSeek
request does: headers, then blank lines, then nothing. One test waits out the
real 20 s deadline; the rest are scaled.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo
import http.client
import json
import os
import socket
import threading
import time

import pytest

from tool_compression.clean_start.categories import result_group
from tool_compression.clean_start.resume import describe, inspect_resume
from tool_compression.clean_start.runner import (
    FULL_FLY_POLICY,
    PRELIMINARY_POLICY,
    ProviderHTTPError,
    RunStopped,
    SendPolicy,
    TotalDeadlineExceeded,
    authorized_transport,
    build_slots,
    execute,
    post_chat,
)
from tool_compression.clean_start.scoring import result_relative

HKT = ZoneInfo("Asia/Hong_Kong")
NOON = datetime(2026, 11, 28, 4, 0, tzinfo=timezone.utc)
IDENTITY = {"study": "clean-start-usx", "draw_sha256": "full-a", "retry_policy": FULL_FLY_POLICY.name}
SLACK = 0.6


def _clock():
    return NOON


def _function() -> dict:
    return {
        "name": "echo",
        "description": "Echo a value.",
        "parameters": {
            "type": "dict",
            "properties": {"value": {"type": "string", "description": "A value."}},
            "required": ["value"],
        },
    }


def _usage() -> dict:
    return {"prompt_tokens": 1000, "prompt_cache_hit_tokens": 200, "prompt_cache_miss_tokens": 800, "completion_tokens": 50}


def _text(text: str = "done") -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": text}}], "usage": _usage()}


def _tool(value: str = "a") -> dict:
    return {
        "choices": [{"message": {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"id": "call_1", "type": "function", "function": {
                "name": "echo", "arguments": json.dumps({"value": value}),
            }}],
        }}],
        "usage": _usage(),
    }


def _single(case_id: str) -> dict:
    return {
        "id": case_id,
        "category": "multiple",
        "question": [[{"role": "user", "content": "q"}]],
        "function": [_function()],
        "prereq": False,
    }


def _trajectory(case_id: str = "multi_turn_base_0", turns: int = 2) -> dict:
    return {
        "id": case_id,
        "category": "multi_turn_base",
        "question": [[{"role": "user", "content": f"turn {index}"}] for index in range(turns)],
        "function": [_function()],
        "involved_classes": ["GorillaFileSystem"],
        "initial_config": {},
        "prereq": False,
    }


def _memory(case_id: str, prereq: bool, scenario: str = "customer") -> dict:
    return {
        "id": case_id,
        "category": "memory_kv",
        "question": [[{"role": "user", "content": f"remember for {case_id}"}]],
        "function": [_function()],
        "involved_classes": ["MemoryAPI_kv"],
        "initial_config": {},
        "prereq": prereq,
        "scenario": scenario,
    }


def _u_slots(cases):
    return [slot for slot in build_slots(cases, ("off",)) if slot["arm"] == "U"]


def _lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _timeout(seconds: float = 20.0) -> TotalDeadlineExceeded:
    return TotalDeadlineExceeded("late", deadline_seconds=seconds, elapsed_seconds=seconds)


class _Deadlined:
    """A scripted transport that takes the policy's deadline, as the live one does."""

    enforces_deadline = True

    def __init__(self, responses):
        self.responses = list(responses)
        self.bodies = []
        self.deadlines = []

    def __call__(self, body, deadline=None):
        self.bodies.append(body)
        self.deadlines.append(deadline)
        if not self.responses:
            raise AssertionError("script exhausted")
        item = self.responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class _Executor:
    def initialize(self, case, config):
        return {"GorillaFileSystem": object()}

    def execute_calls(self, strings, case, config):
        return [f"ran {item}" for item in strings]


class _DiskMemory:
    """Pinned memory snapshot rules on disk: ``-0`` starts empty, others load ``<scenario>_final.json``."""

    def __init__(self):
        self.loaded = []

    def initialize(self, case, config):
        root = config["initial_config"]["MemoryAPI_kv"]["model_result_dir"]
        folder = Path(root) / result_group(case["category"]) / "memory_snapshot"
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


class _BoxLost(BaseException):
    """The process dies here. Nothing in the runner catches it."""


class _Server:
    """127.0.0.1 HTTP server. Each connection takes the next behaviour.

    ``trickle``: 200 headers, then a blank line every 50 ms, the DeepSeek
    keep-alive for a queued non-streaming request. ``silent``: reads the request
    and never answers. Any dict is sent back as a complete JSON response.
    """

    def __init__(self, behaviours):
        self.behaviours = list(behaviours)
        self.requests = 0
        self.closed_by_client = []
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(8)
        self.port = self.listener.getsockname()[1]
        threading.Thread(target=self._accept, daemon=True).start()

    def _accept(self):
        while True:
            try:
                connection, _ = self.listener.accept()
            except OSError:
                return
            behaviour = self.behaviours.pop(0) if self.behaviours else "silent"
            threading.Thread(target=self._serve, args=(connection, behaviour), daemon=True).start()

    @staticmethod
    def _read_request(connection) -> bool:
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = connection.recv(65536)
            if not chunk:
                return False
            data += chunk
        head, _, rest = data.partition(b"\r\n\r\n")
        length = 0
        for line in head.split(b"\r\n"):
            if line.lower().startswith(b"content-length:"):
                length = int(line.split(b":", 1)[1])
        while len(rest) < length:
            chunk = connection.recv(65536)
            if not chunk:
                return False
            rest += chunk
        return True

    def _serve(self, connection, behaviour):
        started = time.monotonic()
        try:
            if not self._read_request(connection):
                return
            self.requests += 1
            if behaviour in ("trickle", "trickle_close"):
                close = b"Connection: close\r\n" if behaviour == "trickle_close" else b""
                connection.sendall(
                    b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n" + close
                    + b"Transfer-Encoding: chunked\r\n\r\n"
                )
                while time.monotonic() - started < 120:
                    connection.sendall(b"1\r\n\n\r\n")
                    time.sleep(0.05)
            elif behaviour == "silent":
                connection.settimeout(120)
                if connection.recv(1) == b"":
                    self.closed_by_client.append(time.monotonic() - started)
            else:
                body = json.dumps(behaviour).encode("utf-8")
                connection.sendall(
                    b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: "
                    + str(len(body)).encode() + b"\r\nConnection: close\r\n\r\n" + body
                )
        except OSError:
            self.closed_by_client.append(time.monotonic() - started)
        finally:
            connection.close()

    def factory(self, timeout: float):
        return lambda: http.client.HTTPConnection("127.0.0.1", self.port, timeout=timeout)

    def close(self):
        self.listener.close()


def _scaled_transport(server: _Server, scale: float):
    """The live transport's deadline mapping, on the local server, at ``scale`` seconds per policy second."""

    def transport(body, deadline=None):
        seconds = deadline * scale
        return post_chat(body, "placeholder", read_timeout=seconds, total_deadline=seconds,
                         connection_factory=server.factory(seconds))

    transport.enforces_deadline = True
    return transport


# The class of bug: run.json said 120 s, the request failed after 473 s.


def test_keep_alive_bytes_do_not_extend_the_deadline():
    server = _Server(["trickle"])
    began = time.monotonic()
    with pytest.raises(TotalDeadlineExceeded) as late:
        post_chat({}, "placeholder", read_timeout=0.4, total_deadline=0.4, connection_factory=server.factory(0.4))
    elapsed = time.monotonic() - began
    server.close()
    assert 0.4 <= elapsed < 0.4 + SLACK
    assert late.value.deadline_seconds == 0.4
    assert 0.4 <= late.value.elapsed_seconds < 0.4 + SLACK


def test_the_total_deadline_fires_on_a_trickle_even_with_a_long_socket_timeout():
    server = _Server(["trickle"])
    began = time.monotonic()
    with pytest.raises(TotalDeadlineExceeded):
        post_chat({}, "placeholder", read_timeout=30.0, total_deadline=0.5, connection_factory=server.factory(30.0))
    assert time.monotonic() - began < 0.5 + SLACK
    server.close()


def test_a_silent_server_is_cut_at_the_deadline_and_the_socket_is_shut():
    server = _Server(["silent"])
    began = time.monotonic()
    with pytest.raises(TotalDeadlineExceeded):
        post_chat({}, "placeholder", read_timeout=0.3, total_deadline=0.3, connection_factory=server.factory(0.3))
    assert time.monotonic() - began < 0.3 + SLACK
    deadline = time.monotonic() + 2
    while not server.closed_by_client and time.monotonic() < deadline:
        time.sleep(0.02)
    server.close()
    assert server.closed_by_client and server.closed_by_client[0] < 0.3 + SLACK


def test_a_connection_close_response_is_still_severed_at_the_deadline():
    server = _Server(["trickle_close"])
    began = time.monotonic()
    with pytest.raises(TotalDeadlineExceeded):
        post_chat({}, "placeholder", read_timeout=5.0, total_deadline=0.3, connection_factory=server.factory(5.0))
    assert time.monotonic() - began < 0.3 + SLACK
    deadline = time.monotonic() + 2
    while not server.closed_by_client and time.monotonic() < deadline:
        time.sleep(0.02)
    server.close()
    assert server.closed_by_client and server.closed_by_client[0] < 0.3 + SLACK + 0.2


def test_the_deadline_covers_connect_and_nothing_is_sent_after_it():
    release = threading.Event()
    sent = []

    class _SlowConnect:
        sock = None

        def connect(self):
            release.wait(5)
            self.sock = object()

        def request(self, *args, **kwargs):
            sent.append(args)

        def getresponse(self):
            raise AssertionError("no response expected")

        def close(self):
            pass

    began = time.monotonic()
    with pytest.raises(TotalDeadlineExceeded):
        post_chat({}, "placeholder", read_timeout=0.3, total_deadline=0.3, connection_factory=_SlowConnect)
    assert time.monotonic() - began < 0.3 + SLACK
    release.set()
    time.sleep(0.2)
    assert sent == []


def test_a_complete_answer_inside_the_deadline_is_returned():
    server = _Server([_text("fine")])
    payload = post_chat({}, "placeholder", read_timeout=2.0, total_deadline=2.0, connection_factory=server.factory(2.0))
    server.close()
    assert payload["choices"][0]["message"]["content"] == "fine"


def test_the_live_transport_maps_the_policy_deadline_onto_both_timeouts(monkeypatch):
    import tool_compression.clean_start.runner as runner

    seen = []
    monkeypatch.setenv("DEEPSEEK_API_KEY", "placeholder-not-a-key")
    monkeypatch.setattr(runner, "post_chat", lambda body, key, **kwargs: seen.append(kwargs) or _text())
    transport = authorized_transport()
    assert transport.enforces_deadline is True
    transport({"x": 1}, deadline=20.0)
    transport({"x": 1}, deadline=60.0)
    transport({"x": 1})
    assert seen == [
        {"read_timeout": 20.0, "total_deadline": 20.0},
        {"read_timeout": 60.0, "total_deadline": 60.0},
        {},
    ]


def test_the_real_20s_first_deadline_fires_at_20s_and_the_60s_retry_answers(tmp_path, monkeypatch):
    """The live transport, unscaled, on a server that trickles keep-alive forever on the first try."""
    server = _Server(["trickle", _text("after retry")])
    monkeypatch.setenv("DEEPSEEK_API_KEY", "placeholder-not-a-key")

    def local_https(host, timeout=None, context=None):
        return http.client.HTTPConnection("127.0.0.1", server.port, timeout=timeout)

    monkeypatch.setattr(http.client, "HTTPSConnection", local_https)
    waits = []
    cases = [_single("multiple_0")]
    began = time.monotonic()
    result = execute(
        cases, _u_slots(cases), tmp_path, authorized_transport(), ceiling_usd=Decimal("1"),
        thinking_modes=("off",), clock=_clock, identity=IDENTITY, policy=FULL_FLY_POLICY, sleep=waits.append,
    )
    elapsed = time.monotonic() - began
    server.close()
    assert result["complete"] is True and result["slots_skipped"] == 0
    assert 20.0 <= elapsed < 20.0 + 2 * SLACK + 1.0
    attempts = _lines(tmp_path / "attempts.jsonl")
    failed = [row for row in attempts if row["event"] == "failed"]
    assert len(failed) == 1
    assert failed[0]["error"] == "TotalDeadlineExceeded"
    assert failed[0]["deadline_seconds"] == 20.0
    assert 20.0 <= failed[0]["elapsed_seconds"] < 20.0 + SLACK
    assert failed[0]["may_be_billed"] is True and failed[0]["retried"] is True
    sent = [row for row in attempts if row["event"] == "sent"]
    assert [(row["try"], row["deadline_seconds"]) for row in sent] == [(1, 20.0), (2, 60.0)]
    assert sent[1]["retry_of"] == sent[0]["attempt"]
    assert waits == []


@pytest.mark.skipif(os.environ.get("TC_REAL_DEADLINES") != "1", reason="waits 80 s; set TC_REAL_DEADLINES=1")
def test_the_real_60s_retry_deadline_fires_at_60s_and_the_slot_is_skipped(tmp_path, monkeypatch):
    server = _Server(["trickle", "trickle", _text()])
    monkeypatch.setenv("DEEPSEEK_API_KEY", "placeholder-not-a-key")
    monkeypatch.setattr(
        http.client, "HTTPSConnection",
        lambda host, timeout=None, context=None: http.client.HTTPConnection("127.0.0.1", server.port, timeout=timeout),
    )
    cases = [_single("multiple_0"), _single("multiple_1")]
    result = execute(
        cases, _u_slots(cases), tmp_path, authorized_transport(), ceiling_usd=Decimal("1"),
        thinking_modes=("off",), clock=_clock, identity=IDENTITY, policy=FULL_FLY_POLICY,
    )
    server.close()
    assert result["complete"] is True and result["slots_skipped"] == 1
    record = _lines(tmp_path / "failures.jsonl")[0]
    assert [row["deadline_seconds"] for row in record["attempts"]] == [20.0, 60.0]
    assert 60.0 <= record["attempts"][1]["elapsed_seconds"] < 60.0 + SLACK


def test_scaled_20s_then_60s_through_the_runner_skip_on_two_trickles(tmp_path):
    server = _Server(["trickle", "trickle", _text("next")])
    cases = [_single("multiple_0"), _single("multiple_1")]
    began = time.monotonic()
    result = execute(
        cases, _u_slots(cases), tmp_path, _scaled_transport(server, 0.01), ceiling_usd=Decimal("1"),
        thinking_modes=("off",), clock=_clock, identity=IDENTITY, policy=FULL_FLY_POLICY,
    )
    elapsed = time.monotonic() - began
    server.close()
    assert result["complete"] is True and result["slots_skipped"] == 1
    assert elapsed < 0.2 + 0.6 + 3 * SLACK
    record = _lines(tmp_path / "failures.jsonl")[0]
    assert [row["deadline_seconds"] for row in record["attempts"]] == [20.0, 60.0]
    assert 0.2 <= record["attempts"][0]["elapsed_seconds"] < 0.2 + SLACK
    assert 0.6 <= record["attempts"][1]["elapsed_seconds"] < 0.6 + SLACK


# Policy and skip-and-record with scripted transports.


def test_full_policy_is_20s_then_60s_one_retry_then_skip():
    assert FULL_FLY_POLICY.retry_limit == 1
    assert FULL_FLY_POLICY.attempt_deadlines == (20.0, 60.0)
    assert FULL_FLY_POLICY.exhausted == "skip"
    assert FULL_FLY_POLICY.backoff(0, _timeout()) == 0.0
    assert FULL_FLY_POLICY.backoff(0, ProviderHTTPError(503, "busy")) == 2.0
    described = FULL_FLY_POLICY.describe()
    assert described["read_timeout_seconds"] == [20.0, 60.0]
    assert described["after_last_failure"] == "skip_and_record"
    assert PRELIMINARY_POLICY.retry_limit == 2 and PRELIMINARY_POLICY.attempt_deadlines is None
    assert PRELIMINARY_POLICY.describe()["read_timeout_seconds"] == 120.0
    assert PRELIMINARY_POLICY.describe()["total_deadline_seconds"] == 900.0
    with pytest.raises(ValueError):
        SendPolicy("bad", 1, (20.0,), (0.0,), None, "skip")


def test_first_try_gets_20s_and_the_retry_60s_with_no_pause(tmp_path):
    transport = _Deadlined([_timeout(20.0), _text()])
    waits = []
    cases = [_single("multiple_0")]
    result = execute(
        cases, _u_slots(cases), tmp_path, transport, ceiling_usd=Decimal("1"), thinking_modes=("off",),
        clock=_clock, identity=IDENTITY, policy=FULL_FLY_POLICY, sleep=waits.append,
    )
    assert result["complete"] is True and result["retries"] == 1
    assert transport.deadlines == [20.0, 60.0]
    assert waits == []
    assert not (tmp_path / "failures.jsonl").exists()
    run = json.loads((tmp_path / "run.json").read_text())
    assert run["retry_policy"]["name"] == FULL_FLY_POLICY.name
    assert run["read_timeout_seconds"] == [20.0, 60.0]
    assert run["total_deadline_seconds"] == [20.0, 60.0]


def test_a_full_policy_refuses_a_transport_that_cannot_enforce_deadlines(tmp_path):
    def plain(body):
        raise AssertionError("never sent")

    cases = [_single("multiple_0")]
    with pytest.raises(RunStopped) as refused:
        execute(cases, _u_slots(cases), tmp_path, plain, ceiling_usd=Decimal("1"), thinking_modes=("off",),
                clock=_clock, policy=FULL_FLY_POLICY)
    assert refused.value.reason == "transport_does_not_enforce_deadline"


def test_two_failed_tries_skip_the_slot_and_record_it_durably(tmp_path, monkeypatch):
    fsynced = []
    real_fsync = os.fsync

    def recording_fsync(descriptor):
        try:
            fsynced.append(os.readlink(f"/proc/self/fd/{descriptor}"))
        except OSError:
            pass
        real_fsync(descriptor)

    monkeypatch.setattr(os, "fsync", recording_fsync)
    transport = _Deadlined([_timeout(20.0), http.client.RemoteDisconnected("gone"), _text("next")])
    cases = [_single("multiple_0"), _single("multiple_1")]
    result = execute(
        cases, _u_slots(cases), tmp_path, transport, ceiling_usd=Decimal("1"), thinking_modes=("off",),
        clock=_clock, identity=IDENTITY, policy=FULL_FLY_POLICY,
    )
    assert result["complete"] is True and result["status"] == "complete"
    assert result["slots_sent"] == 2 and result["slots_skipped"] == 1 and result["slots_finished"] == 1
    assert transport.deadlines == [20.0, 60.0, 20.0]
    failures = _lines(tmp_path / "failures.jsonl")
    assert len(failures) == 1
    record = failures[0]
    assert record["kind"] == "skipped"
    assert (record["case_id"], record["arm"], record["thinking"], record["turn"], record["step"]) == (
        "multiple_0", "U", "off", 0, 0,
    )
    assert record["error"] == "RemoteDisconnected"
    assert record["may_be_billed"] is True
    assert [(row["attempt"], row["try"], row["error"], row["deadline_seconds"]) for row in record["attempts"]] == [
        (1, 1, "TotalDeadlineExceeded", 20.0),
        (2, 2, "RemoteDisconnected", 60.0),
    ]
    assert all(row["sent_at"] and row["failed_at"] and row["may_be_billed"] for row in record["attempts"])
    assert record["policy"] == FULL_FLY_POLICY.name
    assert "incomplete" in record["scoring"]
    assert [row["id"] for row in _lines(tmp_path / result_relative("multiple_1", "off", "U"))] == ["multiple_1"]
    sidecar = json.loads((tmp_path / "model_outputs/deepseek-flash-thinking-off/U/multiple_0.json").read_text())
    assert sidecar["status"] == "skipped" and sidecar["scorable"] is False
    assert sidecar["skip"] == record
    assert str(tmp_path / "failures.jsonl") in fsynced
    assert str(tmp_path) in fsynced
    spend = json.loads((tmp_path / "spend.json").read_text())
    assert spend["slots_skipped"] == 1
    assert spend["tokens"]["total_tokens"] == 1050 and spend["tokens"]["output_tokens"] == 50
    bills = _lines(tmp_path / "bills.jsonl")
    assert [row["case_id"] for row in bills] == ["multiple_1"]
    assert bills[0]["running_usd"] == result["running_usd"]


def test_a_fast_429_or_5xx_waits_2s_then_skips(tmp_path):
    transport = _Deadlined([ProviderHTTPError(503, "busy"), ProviderHTTPError(429, "slow down"), _text()])
    waits = []
    cases = [_single("multiple_0"), _single("multiple_1")]
    result = execute(
        cases, _u_slots(cases), tmp_path, transport, ceiling_usd=Decimal("1"), thinking_modes=("off",),
        clock=_clock, identity=IDENTITY, policy=FULL_FLY_POLICY, sleep=waits.append,
    )
    assert waits == [2.0]
    assert result["slots_skipped"] == 1
    assert _lines(tmp_path / "failures.jsonl")[0]["http_status"] == 429


def test_a_non_transport_failure_stops_instead_of_skipping(tmp_path):
    transport = _Deadlined([_timeout(), ProviderHTTPError(402, "balance")])
    cases = [_single("multiple_0"), _single("multiple_1")]
    result = execute(
        cases, _u_slots(cases), tmp_path, transport, ceiling_usd=Decimal("1"), thinking_modes=("off",),
        clock=_clock, identity=IDENTITY, policy=FULL_FLY_POLICY,
    )
    assert result["complete"] is False and result["reason"] == "provider_error:ProviderHTTPError"
    assert not (tmp_path / "failures.jsonl").exists()
    assert len(transport.bodies) == 2


def test_a_third_skip_in_a_row_stops_the_run_and_resume_starts_there(tmp_path):
    cases = [_single(f"multiple_{index}") for index in range(4)]
    slots = _u_slots(cases)
    transport = _Deadlined([_timeout()] * 6)
    result = execute(
        cases, slots, tmp_path, transport, ceiling_usd=Decimal("1"), thinking_modes=("off",),
        clock=_clock, identity=IDENTITY, policy=FULL_FLY_POLICY,
    )
    assert result["complete"] is False
    assert result["reason"] == "skip_streak:3:TotalDeadlineExceeded"
    assert result["slots_skipped"] == 2 and result["slots_sent"] == 2
    assert [row["case_id"] for row in _lines(tmp_path / "failures.jsonl")] == ["multiple_0", "multiple_1"]

    plan = inspect_resume(tmp_path, cases, slots, identity=IDENTITY, ceiling_usd=Decimal("1"), thinking_modes=("off",))
    assert plan["finished_slots"] == 2 and plan["prior_skipped"] == 2
    assert plan["next_slot"]["case_id"] == "multiple_2"
    assert describe(plan)["skipped_slots"] == 2
    again = _Deadlined([_text(), _text()])
    resumed = execute(
        cases, slots, tmp_path, again, ceiling_usd=Decimal("1"), thinking_modes=("off",),
        clock=_clock, identity=IDENTITY, policy=FULL_FLY_POLICY, resume=True,
    )
    assert resumed["complete"] is True
    assert resumed["slots_skipped"] == 2 and resumed["slots_finished"] == 2
    assert len(again.bodies) == 2


def test_a_success_resets_the_skip_streak(tmp_path):
    cases = [_single(f"multiple_{index}") for index in range(5)]
    transport = _Deadlined([_timeout()] * 4 + [_text()] + [_timeout()] * 4)
    result = execute(
        cases, _u_slots(cases), tmp_path, transport, ceiling_usd=Decimal("1"), thinking_modes=("off",),
        clock=_clock, identity=IDENTITY, policy=FULL_FLY_POLICY,
    )
    assert result["complete"] is True and result["slots_skipped"] == 4


def test_a_skipped_prerequisite_skips_the_rest_of_its_chain_without_sending(tmp_path):
    cases = [
        _memory("memory_kv_prereq_0-customer-0", True),
        _memory("memory_kv_prereq_1-customer-1", True),
        _memory("memory_kv_7-customer-7", False),
        _memory("memory_kv_prereq_0-student-0", True, "student"),
        _memory("memory_kv_9-student-9", False, "student"),
    ]
    slots = _u_slots(cases)
    transport = _Deadlined([_timeout(), _timeout(), _tool("s"), _text(), _text("answer")])
    memory = _DiskMemory()
    result = execute(
        cases, slots, tmp_path, transport, ceiling_usd=Decimal("1"), thinking_modes=("off",),
        clock=_clock, executor=memory, identity=IDENTITY, policy=FULL_FLY_POLICY,
    )
    assert result["complete"] is True and result["slots_skipped"] == 3
    failures = _lines(tmp_path / "failures.jsonl")
    assert [(row["case_id"], row["kind"], row["depends_on"]) for row in failures] == [
        ("memory_kv_prereq_0-customer-0", "skipped", None),
        ("memory_kv_prereq_1-customer-1", "dependency_skipped", "memory_kv_prereq_0-customer-0"),
        ("memory_kv_7-customer-7", "dependency_skipped", "memory_kv_prereq_0-customer-0"),
    ]
    assert failures[1]["attempts"] == [] and failures[1]["may_be_billed"] is False
    assert len(transport.bodies) == 5
    assert [case_id for case_id, _notes in memory.loaded] == [
        "memory_kv_prereq_0-customer-0", "memory_kv_prereq_0-student-0", "memory_kv_9-student-9",
    ]
    scored = [row["id"] for row in _lines(tmp_path / result_relative("memory_kv_9-student-9", "off", "U"))]
    assert "memory_kv_9-student-9" in scored and "memory_kv_7-customer-7" not in scored


def test_resume_after_a_skip_keeps_the_chain_broken_and_does_not_resend(tmp_path):
    cases = [
        _memory("memory_kv_prereq_0-customer-0", True),
        _single("multiple_0"),
        _memory("memory_kv_prereq_1-customer-1", True),
        _memory("memory_kv_7-customer-7", False),
    ]
    slots = _u_slots(cases)
    with pytest.raises(_BoxLost):
        execute(
            cases, slots, tmp_path, _Deadlined([_timeout(), _timeout(), _BoxLost("box")]),
            ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock, executor=_DiskMemory(),
            identity=IDENTITY, policy=FULL_FLY_POLICY,
        )
    failures_before = (tmp_path / "failures.jsonl").read_bytes()
    plan = inspect_resume(tmp_path, cases, slots, identity=IDENTITY, ceiling_usd=Decimal("1"), thinking_modes=("off",))
    assert plan["finished_slots"] == 1 and plan["prior_skipped"] == 1
    assert plan["next_slot"]["case_id"] == "multiple_0"
    assert plan["broken_chains"] == [{
        "thinking": "off", "arm": "U", "category": "memory_kv", "scenario": "customer",
        "prereq": "memory_kv_prereq_0-customer-0",
    }]
    again = _Deadlined([_text()])
    result = execute(
        cases, slots, tmp_path, again, ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock,
        executor=_DiskMemory(), identity=IDENTITY, policy=FULL_FLY_POLICY, resume=True,
    )
    assert result["complete"] is True and result["session"] == 2
    assert result["slots_skipped"] == 3 and result["slots_finished"] == 1
    assert len(again.bodies) == 1
    assert (tmp_path / "failures.jsonl").read_bytes().startswith(failures_before)
    kinds = [(row["case_id"], row["kind"], row["session"]) for row in _lines(tmp_path / "failures.jsonl")]
    assert kinds == [
        ("memory_kv_prereq_0-customer-0", "skipped", 1),
        ("memory_kv_prereq_1-customer-1", "dependency_skipped", 2),
        ("memory_kv_7-customer-7", "dependency_skipped", 2),
    ]


def test_a_box_lost_after_the_failure_line_marks_the_sidecar_on_resume(tmp_path, monkeypatch):
    import tool_compression.clean_start.runner as runner

    cases = [_single("multiple_0"), _single("multiple_1")]
    slots = _u_slots(cases)
    original = runner._write_sidecar

    def lose_box(out_dir, slot, sidecar):
        if sidecar.get("status") == "skipped":
            raise _BoxLost("between the failure line and the sidecar")
        original(out_dir, slot, sidecar)

    monkeypatch.setattr(runner, "_write_sidecar", lose_box)
    with pytest.raises(_BoxLost):
        execute(cases, slots, tmp_path, _Deadlined([_timeout(), _timeout()]), ceiling_usd=Decimal("1"),
                thinking_modes=("off",), clock=_clock, identity=IDENTITY, policy=FULL_FLY_POLICY)
    monkeypatch.setattr(runner, "_write_sidecar", original)
    assert len(_lines(tmp_path / "failures.jsonl")) == 1
    assert not (tmp_path / "model_outputs/deepseek-flash-thinking-off/U/multiple_0.json").exists()

    plan = inspect_resume(tmp_path, cases, slots, identity=IDENTITY, ceiling_usd=Decimal("1"), thinking_modes=("off",))
    assert plan["finished_slots"] == 1
    assert [action["kind"] for action in plan["actions"]] == ["mark_skipped"]
    again = _Deadlined([_text()])
    result = execute(cases, slots, tmp_path, again, ceiling_usd=Decimal("1"), thinking_modes=("off",),
                     clock=_clock, identity=IDENTITY, policy=FULL_FLY_POLICY, resume=True)
    assert result["complete"] is True and len(again.bodies) == 1
    sidecar = json.loads((tmp_path / "model_outputs/deepseek-flash-thinking-off/U/multiple_0.json").read_text())
    assert sidecar["status"] == "skipped" and sidecar["marked_on_resume"] is True


def test_resume_after_a_mid_slot_stop_resends_that_slot_from_its_first_request(tmp_path):
    cases = [_single("multiple_0"), _trajectory(turns=2), _single("multiple_1")]
    slots = _u_slots(cases)
    first = _Deadlined([_timeout(), _timeout(), _tool("a"), _text("turn 0"), _BoxLost("box")])
    with pytest.raises(_BoxLost):
        execute(cases, slots, tmp_path, first, ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock,
                executor=_Executor(), identity=IDENTITY, policy=FULL_FLY_POLICY)
    stopped = json.loads((tmp_path / "model_outputs/deepseek-flash-thinking-off/U/multi_turn_base_0.json").read_text())
    assert len(stopped["steps"]) == 2
    plan = inspect_resume(tmp_path, cases, slots, identity=IDENTITY, ceiling_usd=Decimal("1"), thinking_modes=("off",))
    assert plan["finished_slots"] == 1 and plan["prior_skipped"] == 1
    assert plan["next_slot"]["case_id"] == "multi_turn_base_0"
    assert plan["abandoned_partial_usd"] > 0
    second = _Deadlined([_tool("a"), _text("turn 0"), _text("turn 1"), _text()])
    result = execute(cases, slots, tmp_path, second, ceiling_usd=Decimal("1"), thinking_modes=("off",),
                     clock=_clock, executor=_Executor(), identity=IDENTITY, policy=FULL_FLY_POLICY, resume=True)
    assert result["complete"] is True
    assert second.bodies[0]["messages"] == first.bodies[2]["messages"]
    assert second.deadlines == [20.0] * 4
    bills = _lines(tmp_path / "bills.jsonl")
    assert Decimal(result["running_usd"]) == sum(Decimal(row["usd"]) for row in bills)
    assert result["tokens"]["prompt_tokens"] == 1000 * len(bills)


def test_resume_refuses_failure_records_that_do_not_match_the_journal(tmp_path):
    cases = [_single(f"multiple_{index}") for index in range(3)]
    slots = _u_slots(cases)
    execute(cases, slots, tmp_path, _Deadlined([_timeout(), _timeout(), ProviderHTTPError(402, "stop")]),
            ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock, identity=IDENTITY, policy=FULL_FLY_POLICY)
    path = tmp_path / "failures.jsonl"
    good = path.read_text()
    record = json.loads(good)

    def refused(text: str) -> str:
        path.write_text(text)
        with pytest.raises(RunStopped) as stopped:
            inspect_resume(tmp_path, cases, slots, identity=IDENTITY, ceiling_usd=Decimal("1"), thinking_modes=("off",))
        return stopped.value.reason

    assert refused(good + good) == "resume_failure_recorded_twice:multiple_0:U"
    later = {**record, "case_id": "multiple_2", "kind": "dependency_skipped", "attempts": []}
    assert refused(good + json.dumps(later) + "\n") == "resume_failure_beyond_the_stop:multiple_2:U"
    moved = {**record, "case_id": "multiple_1"}
    assert refused(json.dumps(moved) + "\n") == "resume_failure_attempt_mismatch:1"
    ghost = {**record, "attempts": [{**record["attempts"][0], "attempt": 99}]}
    assert refused(json.dumps(ghost) + "\n") == "resume_failure_without_its_attempt:99"
    assert refused(json.dumps({**record, "kind": "invented"}) + "\n") == "resume_failure_record_for_no_slot:1"
    path.write_text(good)
    result_file = tmp_path / result_relative("multiple_0", "off", "U")
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(json.dumps({"id": "multiple_0", "result": "invented"}) + "\n")
    with pytest.raises(RunStopped) as invented:
        inspect_resume(tmp_path, cases, slots, identity=IDENTITY, ceiling_usd=Decimal("1"), thinking_modes=("off",))
    assert invented.value.reason == "resume_result_line_for_skipped_slot:multiple_0:U"


def test_the_preliminary_policy_is_unchanged(tmp_path):
    from tool_compression.clean_start.runner import RETRY_BACKOFF_SECONDS

    calls = []

    def plain(body):
        calls.append(body)
        if len(calls) < 3:
            raise TimeoutError("read timed out")
        return _text()

    waits = []
    cases = [_single("multiple_0")]
    result = execute(cases, _u_slots(cases), tmp_path, plain, ceiling_usd=Decimal("1"), thinking_modes=("off",),
                     clock=_clock, retry_limit=2, sleep=waits.append)
    assert result["complete"] is True
    assert waits == list(RETRY_BACKOFF_SECONDS)
    run = json.loads((tmp_path / "run.json").read_text())
    assert run["retry_policy"]["name"] == PRELIMINARY_POLICY.name
    assert run["read_timeout_seconds"] == 120.0 and run["total_deadline_seconds"] == 900.0
    assert "deadline_seconds" not in _lines(tmp_path / "attempts.jsonl")[0]


def test_evaluation_ledger_lists_skips_tokens_and_spend(tmp_path):
    from tool_compression.clean_start.evaluate import ledger_summary

    cases = [_single("multiple_0"), _single("multiple_1")]
    execute(cases, _u_slots(cases), tmp_path, _Deadlined([_timeout(), _timeout(), _text()]),
            ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock, identity=IDENTITY, policy=FULL_FLY_POLICY)
    summary = ledger_summary(tmp_path)
    assert summary["skipped_slots"] == 1
    assert summary["skipped"] == {"deepseek-flash-thinking-off-U": {"multiple": [{
        "id": "multiple_0", "kind": "skipped", "prereq": False, "error": "TotalDeadlineExceeded", "depends_on": None,
    }]}}
    assert summary["tokens"]["total_tokens"] == 1050
    assert summary["requests_billed"] == 1
    assert Decimal(summary["spend_usd"]) > 0


# The --full package and CLI.


def test_full_package_numbers_and_regeneration():
    from tool_compression.clean_start import full

    cost = full.load_committed_cost()
    assert (cost["scoring"], cost["prerequisites"], cost["slots"]) == (3127, 111, 12952)
    assert cost["slot_sha256"] == full.COMMITTED_SLOT_SHA256
    assert cost["official_settlement"] is False
    assert cost["observed_mean_usd"] == "58.692511"
    assert cost["observed_mean_sends"] == "70144.240105"
    assert cost["higher_step_sends"] == "81987.110947"
    assert cost["planning_upper_usd"] == "254.432685"
    assert cost["allowance_requests"] == 139988
    assert cost["ceiling_floor_usd"] == "68.54"
    assert cost["allowance_with_monday_peak_usd"] == "286.003642"
    hours = {name: row["hours"] for name, row in cost["profiles"].items()}
    assert hours["mean_1.9s_hang_1.5pct"] == "42.87"
    assert hours["mean_2.0s_hang_1.5pct"] == "44.81"
    assert hours["mean_memory_3.3s_rest_2.0s_hang_1.5pct"] == "50.10"
    assert hours["higher_step_memory_3.3s_rest_2.0s_hang_3pct"] == "67.36"
    assert hours["mean_3.3s_hang_3pct"] == "75.99"
    assert hours["allowance_1.9s_no_hang"] == "73.88"
    assert cost["profiles"]["mean_1.9s_hang_1.5pct"]["peak_premium_usd"] == "0.000000"
    assert cost["ten_hours"]["sends_in_ten_hours_at_1.9s"] == "18947"
    rebuilt = full.full_report(full.stored_planning(cost))
    stored = {key: value for key, value in cost.items() if key not in ("plan_sha256", "single_turn_allowance_usd")}
    assert json.loads(json.dumps(rebuilt)) == stored


@pytest.mark.skipif(os.environ.get("TC_FULL_PLANNING") != "1", reason="tokenises 3,238 cases, about 2 min")
def test_full_planning_upper_recomputes_from_the_catalogue():
    from tool_compression.clean_start import full

    cost = full.load_committed_cost()
    assert full.compute_planning(full.select_full_cases()) == full.stored_planning(cost)


def test_start_gate():
    from tool_compression.clean_start.full import NOT_BEFORE_HKT, start_gate

    assert start_gate(NOT_BEFORE_HKT - timedelta(seconds=1), resume=False)
    assert start_gate(NOT_BEFORE_HKT, resume=False) == []
    monday_peak = datetime(2026, 11, 30, 10, 0, tzinfo=HKT)
    assert any("off-peak" in problem for problem in start_gate(monday_peak, resume=False))
    assert start_gate(monday_peak, resume=True) == []


FULL = ["run", "--full", "--thinking", "off", "--memory-prereqs", "matched"]


def _no_key(monkeypatch):
    monkeypatch.setattr(
        "tool_compression.clean_start.__main__.authorized_transport",
        lambda: (_ for _ in ()).throw(AssertionError("key read")),
    )


@pytest.mark.parametrize("argv, message", [
    (["run", "--full", "--thinking", "on", "--memory-prereqs", "matched", "--ceiling-usd", "70"], "thinking off only"),
    (["run", "--full", "--memory-prereqs", "matched", "--ceiling-usd", "70"], "thinking off only"),
    (["run", "--full", "--thinking", "off", "--memory-prereqs", "none", "--ceiling-usd", "70"], "matched"),
    (FULL, "Jacky names"),
    (FULL + ["--ceiling-usd", "70", "--preliminary"], "different draws"),
    (FULL + ["--ceiling-usd", "68.53"], "under the $68.54 floor"),
])
def test_full_refusals(tmp_path, monkeypatch, capsys, argv, message):
    from tool_compression.clean_start.__main__ import main

    _no_key(monkeypatch)
    assert main(argv + ["--out", str(tmp_path / "out")]) == 2
    assert message in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_full_dry_plan_advertises_the_deadlines_it_will_use(tmp_path, monkeypatch):
    from tool_compression.clean_start.__main__ import main

    _no_key(monkeypatch)
    assert main(FULL + ["--ceiling-usd", "68.54", "--out", str(tmp_path)]) == 0
    plan = json.loads((tmp_path / "run.json").read_text())
    assert plan["provider_contacted"] is False and plan["full"] is True
    assert plan["slots_total"] == 12952
    assert plan["slot_sha256"] == "8fff8cd902b3c523473cf38591a20d3719b0c028138728f46632867fc655047f"
    assert plan["read_timeout_seconds"] == [20.0, 60.0]
    assert plan["total_deadline_seconds"] == [20.0, 60.0]
    assert plan["retry_policy"]["after_last_failure"] == "skip_and_record"
    assert plan["official_settlement"] is False


def test_full_live_waits_for_friday_18_hkt_and_off_peak(tmp_path, monkeypatch, capsys):
    import tool_compression.clean_start.__main__ as cli

    _no_key(monkeypatch)
    live = FULL + ["--live", "--authorize-live", "--ceiling-usd", "70"]
    monkeypatch.setattr(cli, "_now", lambda: datetime(2026, 11, 27, 17, 59, 59, tzinfo=HKT))
    assert cli.main(live + ["--out", str(tmp_path / "early")]) == 2
    assert "not before 2026-11-27T18:00:00+08:00" in capsys.readouterr().err
    monkeypatch.setattr(cli, "_now", lambda: datetime(2026, 11, 30, 10, 0, tzinfo=HKT))
    assert cli.main(live + ["--out", str(tmp_path / "peak")]) == 2
    assert "off-peak" in capsys.readouterr().err
    monkeypatch.setattr(cli, "_now", lambda: datetime(2026, 11, 27, 18, 0, tzinfo=HKT))
    monkeypatch.setattr(cli, "preflight", lambda cases, slots, bfcl_root=None: ["box preflight stands in here"])
    assert cli.main(live + ["--out", str(tmp_path / "go")]) == 2
    assert "refusing before any request: box preflight stands in here" in capsys.readouterr().err
    for name in ("early", "peak", "go"):
        assert not (tmp_path / name / "attempts.jsonl").exists()


def test_full_resume_check_and_the_plain_path_guard(tmp_path, monkeypatch, capsys):
    from tool_compression.clean_start.__main__ import main

    _no_key(monkeypatch)
    assert main(FULL + ["--ceiling-usd", "70", "--resume", "--out", str(tmp_path / "none")]) == 2
    assert "resume_without_prior_run" in capsys.readouterr().err
    assert main(["run", "--resume", "--out", str(tmp_path / "none")]) == 2
    assert "--preliminary or --full only" in capsys.readouterr().err
    assert main([
        "run", "--live", "--authorize-live", "--thinking", "off", "--ceiling-usd", "100",
        "--out", str(tmp_path / "plain"),
    ]) == 2
    assert "flies only with --full" in capsys.readouterr().err
    assert not (tmp_path / "plain").exists()
