"""Send U/S/X/SX for the thinking modes a person authorised, one request at a time.

The default path does not read a provider key and does not open a socket.
``--live`` without ``--authorize-live`` exits before either of those. There is
no max_tokens budget and no pre-send reserve. Before each request the running
spend is compared with the ceiling and an attempt line is journalled. After each
completed response the billed usage is recorded and the step is written to its
sidecar, so a stopped trajectory keeps every billed step. A run that stops
early is marked incomplete.

A ``SendPolicy`` says how long one try may take, how many tries a request
gets, and what happens after the last one. By default nothing is retried and a
failure stops the run. The preliminary policy sends a transport failure (timeout,
dropped or incomplete read, HTTP 429 or 5xx) again with the same body at most
twice, after 10 s and 30 s, and then stops. The full-fly policy gives the first
try 20 s and one retry 60 s, both enforced by a timer armed when that try is
journaled, and then skips the slot and records it in ``failures.jsonl``. Each try is its own journalled
attempt, the ceiling is checked before each, and a failed one stays listed as
possibly billed. Nothing else in the slot has changed by then.

A skipped slot writes no result line, so official scoring sees it as missing.
When a memory prerequisite is skipped, the rest of that arm's scenario chain is
recorded as ``dependency_skipped`` and not sent, because its memory would not
be the state pinned BFCL builds.

A fresh run refuses an output directory that already holds provider evidence.
``resume=True`` is the only way back into one: see ``resume.py``. Finished and
skipped slots are not sent again, the stopped slot is sent again from its first
request, and the bill ledger's sum counts against the same ceiling.

Trajectory categories follow the pinned BFCL function-calling loop: class
instances are created before the first request, memory categories get the
pinned memory instruction prompt, a turn ends on an empty or undecodable reply,
a turn is forced to quit after more than ``STEP_LIMIT`` executed steps, held-out
documents arrive without the language hint, and a memory prerequisite flushes
its snapshot at the end. Reasoning content is passed back on tool turns because
the provider requires it when tools are sent.
"""

from __future__ import annotations

from copy import deepcopy
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import http.client
import importlib.util
import json
import os
import socket
import threading
import time

from tool_compression.clean_start.categories import is_agentic, is_memory, is_trajectory, is_web_search
from tool_compression.clean_start.pin import (
    API_URL,
    ARMS,
    OFFICIAL_SETTLEMENT,
    REQUEST_MODEL,
    STEP_LIMIT,
    STUDY_ID,
    TEMPERATURE,
    THINKING_ORDER,
)
from tool_compression.clean_start.prepare import (
    AGENTIC_SYSTEM_PROMPT,
    HOLDOUT_USER_PROMPT,
    model_facing_tools,
)
from tool_compression.clean_start.rate_card import rate_card, spend_usd
from tool_compression.clean_start.render import render_tools
from tool_compression.clean_start.scoring import (
    append_result,
    assistant_history,
    decode_execute,
    is_empty_execute_response,
    parse_fc_message,
    registry_dir,
    result_model_name,
)
from tool_compression.convert import to_openai_completions_tools

READ_TIMEOUT_SECONDS = 120.0
TOTAL_DEADLINE_SECONDS = 900.0
FAILURES_FILE = "failures.jsonl"
EVIDENCE_FILES = ("attempts.jsonl", "bills.jsonl", FAILURES_FILE, "run.json")
ARM_ORDER = "rotated by case position: case i sends ARMS[i % 4:] + ARMS[:i % 4]"
RETRY_LIMIT = 2
RETRY_BACKOFF_SECONDS = (10.0, 30.0)
RETRY_HTTP_STATUSES = frozenset({429, 500, 502, 503, 504})
# After the deadline the socket is shut down; the worker thread then returns at
# once. This bounds how long the caller waits for it to exit, not the deadline.
SEVER_GRACE_SECONDS = 0.5
# How often a try's timer thread re-reads the clocks. Short enough that a
# forward jump of civil time is acted on at the jump, not at the end of one
# long monotonic sleep. ``time.sleep`` is relative, so a backward step of
# CLOCK_REALTIME does not stretch a slice.
DEADLINE_POLL_SECONDS = 0.02
# Civil time this far ahead of monotonic time is a step or a resume, not
# scheduling noise between the two clock reads.
DEADLINE_WALL_JUMP_SECONDS = 0.25
DEADLINE_SCOPE = (
    "from the journaled start of the try, including the sent-line fsync, DNS, "
    "connect, TLS, request write, response headers and the whole body. A timer "
    "thread shuts the socket down when monotonic time reaches the budget, or "
    "sooner if civil time jumps ahead. Keep-alive bytes do not extend it, and a "
    "backward civil-time step cannot extend it either."
)


@dataclass(frozen=True)
class SendPolicy:
    """How long one try may take, how many tries a request gets, and what follows the last.

    ``attempt_deadlines`` are wall-clock seconds for the first try and each
    retry, passed to the transport. ``None`` leaves the transport's own
    ``READ_TIMEOUT_SECONDS`` per read and ``TOTAL_DEADLINE_SECONDS`` per try.
    ``exhausted`` is ``stop`` or ``skip``. ``skip_streak_limit`` is how many
    consecutive skipped slots are allowed before the next would-be skip stops
    the run instead, so an outage does not skip its way through the catalogue.
    """

    name: str
    retry_limit: int
    attempt_deadlines: tuple[float, ...] | None
    backoff_seconds: tuple[float, ...]
    status_backoff_seconds: float | None
    exhausted: str
    skip_streak_limit: int | None = None

    def __post_init__(self):
        if self.retry_limit < 0:
            raise ValueError("retry_limit must not be negative")
        if self.exhausted not in {"stop", "skip"}:
            raise ValueError(self.exhausted)
        if self.attempt_deadlines is not None:
            if len(self.attempt_deadlines) != self.retry_limit + 1 or min(self.attempt_deadlines) <= 0:
                raise ValueError("one positive deadline per try")
        if self.retry_limit and not self.backoff_seconds:
            raise ValueError("a retrying policy names its backoff")

    def deadline(self, tries: int) -> float | None:
        if self.attempt_deadlines is None:
            return None
        return self.attempt_deadlines[tries]

    def backoff(self, tries: int, exc: BaseException) -> float:
        if self.status_backoff_seconds is not None and isinstance(exc, ProviderHTTPError):
            return self.status_backoff_seconds
        return self.backoff_seconds[min(tries, len(self.backoff_seconds) - 1)]

    def describe(self) -> dict:
        deadlines = None if self.attempt_deadlines is None else list(self.attempt_deadlines)
        return {
            "name": self.name,
            "tries": self.retry_limit + 1,
            "retries": self.retry_limit,
            "attempt_deadlines_seconds": deadlines,
            "deadline_scope": DEADLINE_SCOPE if deadlines else None,
            "read_timeout_seconds": deadlines or READ_TIMEOUT_SECONDS,
            "total_deadline_seconds": deadlines or TOTAL_DEADLINE_SECONDS,
            "backoff_seconds": list(self.backoff_seconds),
            "status_backoff_seconds": self.status_backoff_seconds,
            "retried": "timeouts, dropped or incomplete reads, TLS and DNS errors, HTTP 429 and 5xx",
            "after_last_failure": "skip_and_record" if self.exhausted == "skip" else "stop",
            "skip_streak_limit": self.skip_streak_limit,
        }


class RunStopped(RuntimeError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class TotalDeadlineExceeded(TimeoutError):
    """The try outlived its wall-clock deadline. It may still be billed."""

    def __init__(self, message: str, *, deadline_seconds: float | None = None, elapsed_seconds: float | None = None):
        super().__init__(message)
        self.deadline_seconds = deadline_seconds
        self.elapsed_seconds = elapsed_seconds


class SlotSkipped(Exception):
    """The last try of a request failed in transport under a skipping policy."""

    def __init__(self, turn: int, step: int, attempts: list[dict], error: BaseException):
        super().__init__(error.__class__.__name__)
        self.turn = turn
        self.step = step
        self.attempts = attempts
        self.error = error


class ProviderHTTPError(RuntimeError):
    def __init__(self, status: int, body: str):
        super().__init__(f"HTTP {status}")
        self.status = status
        self.body = body


def is_transport_failure(exc: BaseException) -> bool:
    """Failures where sending the same body again is the whole fix.

    Timeouts (including the total deadline), dropped connections, incomplete
    reads, TLS and DNS errors, and HTTP 429 or 5xx. Not other 4xx, such as 402
    for an empty balance, and not a 200 whose body is unusable.
    """
    if isinstance(exc, ProviderHTTPError):
        return exc.status in RETRY_HTTP_STATUSES
    return isinstance(exc, (OSError, http.client.HTTPException))


NO_RETRY_POLICY = SendPolicy(
    name="no-retry",
    retry_limit=0,
    attempt_deadlines=None,
    backoff_seconds=(),
    status_backoff_seconds=None,
    exhausted="stop",
)
# The policy the 20% preliminary flight started with on 69f33cdc. Unchanged.
PRELIMINARY_POLICY = SendPolicy(
    name="retry-2-backoff-10s-30s-stop",
    retry_limit=RETRY_LIMIT,
    attempt_deadlines=None,
    backoff_seconds=RETRY_BACKOFF_SECONDS,
    status_backoff_seconds=None,
    exhausted="stop",
)
# Full in-scope fly. No pause after a timeout or a dropped connection: the
# 20 s already waited is the pause. A fast 429 or 5xx answer waits 2 s first.
FULL_FLY_POLICY = SendPolicy(
    name="deadline-20s-retry-60s-skip",
    retry_limit=1,
    attempt_deadlines=(20.0, 60.0),
    backoff_seconds=(0.0,),
    status_backoff_seconds=2.0,
    exhausted="skip",
    skip_streak_limit=2,
)


def legacy_policy(retry_limit: int) -> SendPolicy:
    if retry_limit < 0:
        raise RunStopped("retry_limit_negative")
    if retry_limit == 0:
        return NO_RETRY_POLICY
    if retry_limit == RETRY_LIMIT:
        return PRELIMINARY_POLICY
    return SendPolicy(
        name=f"retry-{retry_limit}-backoff-10s-30s-stop",
        retry_limit=retry_limit,
        attempt_deadlines=None,
        backoff_seconds=RETRY_BACKOFF_SECONDS,
        status_backoff_seconds=None,
        exhausted="stop",
    )


def parse_thinking_modes(text: str) -> tuple[str, ...]:
    """``off``, ``on``, or ``off,on``. Nothing else, and no silent default."""
    modes = tuple(part.strip() for part in str(text).split(",") if part.strip())
    if not modes or len(set(modes)) != len(modes) or any(mode not in THINKING_ORDER for mode in modes):
        raise ValueError(f"thinking modes must be off, on, or off,on; got {text!r}")
    return tuple(mode for mode in THINKING_ORDER if mode in modes)


def request_body(messages: list[dict], tools: list[dict], thinking: str) -> dict:
    if thinking == "on":
        mode = "enabled"
    elif thinking == "off":
        mode = "disabled"
    else:
        raise ValueError(thinking)
    body = {
        "model": REQUEST_MODEL,
        "messages": deepcopy(messages),
        "temperature": TEMPERATURE,
        "thinking": {"type": mode},
    }
    if tools:
        body["tools"] = tools
    if "max_tokens" in body or body["model"] != REQUEST_MODEL:
        raise RuntimeError("request body must name deepseek-flash and omit max_tokens")
    return body


def read_provider_key() -> str:
    """Read the provider key. Callers must already be on the authorized live path."""
    key = os.environ["DEEPSEEK_API_KEY"]
    if not key or not str(key).strip():
        raise RuntimeError("DEEPSEEK_API_KEY is empty")
    return str(key)


def _sever(connection, sock=None) -> None:
    """Unblock a reader at once. Do not run an SSL close notify from this thread.

    ``SSLSocket.shutdown`` and ``close`` can block on the close notify or on
    the lock the reader holds. TCP shutdown on the raw fd returns and wakes a
    blocked read. There is no ``os.shutdown``: a second socket object on the
    same fd calls ``shutdown``, then ``detach`` so this thread does not close
    the fd the reader still owns. ``sock`` is the socket captured at connect.
    ``http.client`` drops ``connection.sock`` once a ``Connection: close``
    response has its headers. With no fd yet (DNS or connect still running, or
    a fake connection) the connection is closed so a test double unblocks.
    """
    if sock is None and connection is not None:
        sock = getattr(connection, "sock", None)
    if sock is not None:
        shut = False
        try:
            fd = sock.fileno()
        except Exception:
            fd = -1
        if isinstance(fd, int) and fd >= 0:
            try:
                # A fresh socket object on the same fd issues TCP shutdown.
                # SSLSocket.shutdown would block in the close notify. detach
                # leaves the fd open for the reader, which wakes on the reset.
                raw = socket.socket(fileno=fd)
                try:
                    socket.socket.shutdown(raw, socket.SHUT_RDWR)
                finally:
                    raw.detach()
                shut = True
            except OSError:
                pass
        if not shut:
            try:
                if isinstance(sock, socket.socket):
                    socket.socket.shutdown(sock, socket.SHUT_RDWR)
                elif hasattr(sock, "shutdown"):
                    sock.shutdown(socket.SHUT_RDWR)
                else:
                    raise AttributeError
                shut = True
            except (OSError, AttributeError):
                pass
        if shut:
            return
    if connection is None:
        return
    try:
        connection.close()
    except Exception:
        pass


class DeadlineTimer:
    """One armed timer per try. It cancels the in-flight socket from its own thread.

    The budget starts when the timer is constructed. It is spent when monotonic
    time reaches it, or sooner when civil time (``time.time``) jumps ahead of
    monotonic time by more than ``DEADLINE_WALL_JUMP_SECONDS``. A backward step
    of the civil clock cannot extend the budget: monotonic time still fires.
    Keep-alive bytes never reset it. The thread exists so the cut still happens
    while the caller is blocked in the sent-line fsync or the reader is blocked
    in ``recv``.
    """

    def __init__(self, seconds: float, *, monotonic=time.monotonic, wall=time.time):
        self.seconds = float(seconds)
        self._monotonic = monotonic
        self._wall = wall
        self._mono0 = monotonic()
        self._wall0 = wall()
        self.fired = threading.Event()
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._connection = None
        self._sock = None
        self._thread = threading.Thread(target=self._run, name="request-deadline", daemon=True)
        self._thread.start()

    def elapsed(self) -> tuple[float, float]:
        return (self._monotonic() - self._mono0, self._wall() - self._wall0)

    def due(self) -> bool:
        mono, wall = self.elapsed()
        if mono >= self.seconds:
            return True
        return wall >= self.seconds and wall > mono + DEADLINE_WALL_JUMP_SECONDS

    def remaining(self) -> float:
        mono, wall = self.elapsed()
        mono_left = self.seconds - mono
        if wall > mono + DEADLINE_WALL_JUMP_SECONDS:
            return min(mono_left, self.seconds - wall)
        return mono_left

    def _run(self) -> None:
        try:
            while not self._stop.is_set():
                if self.due():
                    self.cut()
                    return
                delay = self.remaining()
                if delay <= 0:
                    if not self._stop.is_set():
                        self.cut()
                    return
                time.sleep(min(DEADLINE_POLL_SECONDS, delay))
        except Exception:
            if not self._stop.is_set():
                self.cut()

    def cut(self) -> None:
        """The budget is spent. Shut the socket down if one is attached."""
        with self._lock:
            self.fired.set()
            connection, sock = self._connection, self._sock
        if connection is not None or sock is not None:
            _sever(connection, sock)

    def attach(self, connection, sock=None) -> None:
        with self._lock:
            self._connection = connection
            if sock is None and connection is not None:
                sock = getattr(connection, "sock", None)
            if sock is not None:
                self._sock = sock
            fired = self.fired.is_set()
            connection, sock = self._connection, self._sock
        if fired and (connection is not None or sock is not None):
            _sever(connection, sock)

    def cancel(self) -> None:
        """The try finished. Do not shut the socket down on the way out."""
        self._stop.set()
        if threading.current_thread() is not self._thread:
            self._thread.join(SEVER_GRACE_SECONDS)


_ATTEMPT_TIMER: ContextVar[DeadlineTimer | None] = ContextVar("attempt_deadline", default=None)


def _deadline_due(*timers: DeadlineTimer | None) -> bool:
    return any(timer is not None and (timer.fired.is_set() or timer.due()) for timer in timers)


def _deadline_exceeded(deadline: float, elapsed: float) -> TotalDeadlineExceeded:
    return TotalDeadlineExceeded(
        f"no complete response within {deadline} seconds",
        deadline_seconds=deadline,
        elapsed_seconds=elapsed,
    )


def post_chat(
    body: dict,
    api_key: str,
    *,
    read_timeout: float = READ_TIMEOUT_SECONDS,
    total_deadline: float = TOTAL_DEADLINE_SECONDS,
    connection_factory=None,
    monotonic=time.monotonic,
    wall=time.time,
) -> dict:
    """POST one chat completion. ``total_deadline`` bounds the whole try.

    ``read_timeout`` is only the per-operation socket timeout. DeepSeek keeps a
    queued non-streaming request open by sending blank lines, and every byte
    restarts that socket timer. On 69f33cdc a request advertised at 120 s failed
    with ``TimeoutError`` after 473 s: blank lines for about six minutes, then
    120 s of silence. The try's budget is a separate timer thread, armed before
    the body is encoded. It shuts the raw socket down when monotonic time
    reaches the budget, or sooner if civil time jumps ahead. The caller may
    already have armed the same kind of timer at ``sent_at``, before the
    sent-line fsync; that one is in ``_ATTEMPT_TIMER`` and cuts this socket too.
    A try cut here may already be billed. The caller journals it as possibly
    billed, with no usage.
    """
    from urllib.parse import urlsplit

    url = urlsplit(API_URL)
    per_operation = min(read_timeout, total_deadline)
    if connection_factory is None:
        import ssl

        def connection_factory():
            return http.client.HTTPSConnection(
                url.hostname, timeout=per_operation, context=ssl.create_default_context()
            )

    outer = _ATTEMPT_TIMER.get()
    began = monotonic()
    own = DeadlineTimer(total_deadline, monotonic=monotonic, wall=wall)
    done = threading.Event()
    outcome: dict = {}
    worker: threading.Thread | None = None
    try:
        if _deadline_due(own, outer):
            raise _deadline_exceeded(total_deadline, monotonic() - began)
        payload = json.dumps(body).encode("utf-8")
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        if _deadline_due(own, outer):
            raise _deadline_exceeded(total_deadline, monotonic() - began)
        connection = connection_factory()
        own.attach(connection)
        if outer is not None:
            outer.attach(connection)

        def work():
            try:
                if _deadline_due(own, outer):
                    raise TotalDeadlineExceeded("abandoned before the request was written")
                connect = getattr(connection, "connect", None)
                if connect is not None and getattr(connection, "sock", None) is None:
                    connect()
                sock = getattr(connection, "sock", None)
                own.attach(connection, sock)
                if outer is not None:
                    outer.attach(connection, sock)
                if _deadline_due(own, outer):
                    raise TotalDeadlineExceeded("abandoned before the request was written")
                connection.request("POST", url.path, body=payload, headers=headers)
                response = connection.getresponse()
                data = response.read()
                if _deadline_due(own, outer):
                    raise TotalDeadlineExceeded("abandoned while reading the response")
                outcome["status"] = response.status
                outcome["data"] = data
            except BaseException as exc:
                outcome["error"] = exc
            finally:
                try:
                    connection.close()
                except Exception:
                    pass
                done.set()

        worker = threading.Thread(target=work, name="request-read", daemon=True)
        worker.start()
        while not done.is_set():
            if _deadline_due(own, outer):
                break
            wait = own.remaining()
            if outer is not None:
                wait = min(wait, outer.remaining())
            if wait <= 0:
                break
            done.wait(min(DEADLINE_POLL_SECONDS, max(0.0, wait)))
        if not done.is_set() or _deadline_due(own, outer):
            own.cut()
            if outer is not None:
                outer.cut()
            if not done.is_set():
                worker.join(SEVER_GRACE_SECONDS)
            raise _deadline_exceeded(total_deadline, monotonic() - began)
        if "error" in outcome:
            raise outcome["error"]
        if outcome.get("status") != 200:
            raise ProviderHTTPError(
                int(outcome.get("status") or 0), outcome.get("data", b"")[:500].decode("utf-8", "replace")
            )
        return json.loads(outcome["data"].decode("utf-8"))
    finally:
        own.cancel()


def authorized_transport():
    """Build the live transport. This is the first point that reads the key.

    Without ``deadline`` a try keeps the 120 s socket timeout and 900 s total
    deadline the earlier flights used. With one, both are that many seconds.
    """
    api_key = read_provider_key()

    def transport(body: dict, deadline: float | None = None) -> dict:
        if deadline is None:
            return post_chat(body, api_key)
        return post_chat(body, api_key, read_timeout=deadline, total_deadline=deadline)

    transport.enforces_deadline = True
    return transport


def parse_usage(usage: dict | None) -> dict:
    if not isinstance(usage, dict):
        return {"billed": False, "reason": "usage_missing"}
    if "prompt_tokens" not in usage or "completion_tokens" not in usage:
        return {"billed": False, "reason": "usage_missing_billed_fields"}
    prompt = int(usage["prompt_tokens"])
    output = int(usage["completion_tokens"])
    details = usage.get("prompt_tokens_details") if isinstance(usage.get("prompt_tokens_details"), dict) else {}
    hit = usage.get("prompt_cache_hit_tokens")
    miss = usage.get("prompt_cache_miss_tokens")
    if hit is None and details.get("cached_tokens") is not None:
        hit = details["cached_tokens"]
    assumption = "reported"
    if hit is None and miss is None:
        hit, miss, assumption = 0, prompt, "assumed_all_miss"
    elif hit is None:
        hit, assumption = prompt - int(miss), "derived_hit"
    elif miss is None:
        miss, assumption = prompt - int(hit), "derived_miss"
    hit, miss = int(hit), int(miss)
    if hit < 0 or miss < 0:
        return {"billed": False, "reason": "usage_cache_split_negative"}
    completion_details = usage.get("completion_tokens_details")
    if not isinstance(completion_details, dict):
        completion_details = {}
    reasoning = usage.get("reasoning_tokens", completion_details.get("reasoning_tokens"))
    return {
        "billed": True,
        "prompt_tokens": prompt,
        "prompt_cache_hit_tokens": hit,
        "prompt_cache_miss_tokens": miss,
        "output_tokens": output,
        "reasoning_tokens": None if reasoning is None else int(reasoning),
        "cache_fields": assumption,
        "usage_inconsistent": hit + miss != prompt,
    }


def prepared_question(case: dict) -> list[list[dict]]:
    """Turns as the pinned loader leaves them: the agentic format prompt on turn 0."""
    question = deepcopy(case["question"])
    if is_agentic(case["category"]) and not case.get("prereq") and question:
        question[0] = [{"role": "system", "content": AGENTIC_SYSTEM_PROMPT}, *question[0]]
    return question


def turn_messages(case: dict, turn_index: int, question: list[list[dict]] | None = None) -> list[dict]:
    question = prepared_question(case) if question is None else question
    turn = question[turn_index]
    if not turn and str(turn_index) in case.get("held_out", {}):
        return [{"role": "user", "content": HOLDOUT_USER_PROMPT}]
    return [dict(item) for item in turn]


def arm_tools(
    functions: list[dict], category: str, arm: str, held_out_batches: list[list[dict]] | None = None
) -> list[dict]:
    """Model-facing tools for one arm.

    ``held_out_batches`` are the held-out docs added so far, one list per turn
    that added them, in order. They are converted without the hint and appended.
    Tools sent before a batch arrived keep their bytes in every arm.
    """
    facing = model_facing_tools(functions, category)
    presented = []
    for batch in held_out_batches or []:
        presented.append(len(facing))
        facing = facing + to_openai_completions_tools(deepcopy(list(batch)))
    if arm == "U":
        return facing
    return render_tools(facing, tuple(presented))["arms"][arm]


def arm_order(position: int) -> tuple[str, ...]:
    shift = position % len(ARMS)
    return ARMS[shift:] + ARMS[:shift]


def build_slots(cases: list[dict], thinking_modes: tuple[str, ...] = THINKING_ORDER) -> list[dict]:
    """Slots for the given thinking modes only, in mode, case, then rotated arm order.

    The arm rotation spreads provider prefix-cache warming evenly over the arms.
    Memory prerequisites keep their position before their backend's questions.
    """
    modes = parse_thinking_modes(",".join(thinking_modes))
    slots = []
    for thinking in modes:
        for position, case in enumerate(cases):
            for arm in arm_order(position):
                slots.append({
                    "case_id": case["id"],
                    "category": case["category"],
                    "arm": arm,
                    "thinking": thinking,
                    "prereq": bool(case.get("prereq")),
                    "kind": "trajectory" if is_trajectory(case["category"]) else "single",
                })
    return slots


def executor_instance_name(thinking: str, arm: str) -> str:
    """``model_name`` passed to the pinned ``execute_multi_turn_func_call``.

    The pinned function stores one class instance in ``globals()`` under
    ``{model_name}_{test_entry_id}_{class_name}_instance``, after replacing
    ``-./:`` with ``_``. A second arm of the same thinking pass and case id
    reuses that instance and skips ``_load_scenario`` when this name has no arm.
    """
    if thinking not in THINKING_ORDER:
        raise ValueError(thinking)
    if arm not in ARMS:
        raise ValueError(arm)
    return f"deepseek_flash_thinking_{thinking}_{arm}"


def execution_config(case: dict, result_dir: Path) -> dict:
    classes = list(case.get("involved_classes") or [])
    if case["category"].startswith("memory_"):
        class_name = classes[0]
        return {
            "initial_config": {
                class_name: {
                    "model_result_dir": Path(result_dir),
                    "scenario": case.get("scenario"),
                    "test_id": case["id"],
                    "test_category": case["category"] if not case.get("prereq") else f"{case['category']}_prereq",
                }
            },
            "long_context": False,
            "involved_classes": classes,
        }
    if case["category"].startswith("web_search"):
        return {
            "initial_config": {
                "WebSearchAPI": {"show_snippet": "no_snippet" not in case["id"]}
            },
            "long_context": False,
            "involved_classes": classes or ["WebSearchAPI"],
        }
    return {
        "initial_config": case.get("initial_config") or {},
        "long_context": "long_context" in case["category"],
        "involved_classes": classes,
    }


BACKEND_MODULES = {
    "WebSearchAPI": ("serpapi", "bs4", "html2text", "requests"),
    "MemoryAPI_kv": ("rank_bm25",),
    "MemoryAPI_vector": ("sentence_transformers", "faiss", "numpy"),
    "MemoryAPI_rec_sum": (),
}


def preflight(cases: list[dict], slots: list[dict], *, bfcl_root: Path | None, environ=None, find_spec=None) -> list[str]:
    """Problems that would waste spend if found after the first request.

    Reads only whether variables are set, never their values into any output.
    """
    environ = os.environ if environ is None else environ
    find_spec = importlib.util.find_spec if find_spec is None else find_spec
    problems = []
    by_id = {case["id"]: case for case in cases}
    trajectory = [slot for slot in slots if slot["kind"] == "trajectory"]
    if trajectory and bfcl_root is None:
        problems.append("bfcl_root_missing: a trajectory category needs --bfcl-root")
    classes = set()
    for slot in trajectory:
        classes.update(by_id[slot["case_id"]].get("involved_classes") or [])
        if is_web_search(slot["category"]):
            classes.add("WebSearchAPI")
    for class_name in sorted(classes):
        for module in BACKEND_MODULES.get(class_name, ()):
            if find_spec(module) is None:
                problems.append(f"backend_module_missing: {class_name} needs {module}")
    if "WebSearchAPI" in classes and not str(environ.get("SERPAPI_API_KEY") or "").strip():
        problems.append(
            "serpapi_key_missing: web_search slots would run with every search returning an error string"
        )
    if not str(environ.get("DEEPSEEK_API_KEY") or "").strip():
        problems.append("provider_key_missing: DEEPSEEK_API_KEY is not set")
    return problems


class OfficialBfclExecutor:
    """Call the pinned BFCL executor and memory helpers. Constructed only for an authorized run."""

    def __init__(self, package_root: Path, instance_name: str):
        import sys
        root = Path(package_root)
        if not (root / "bfcl_eval").is_dir():
            nested = root / "berkeley-function-call-leaderboard"
            if (nested / "bfcl_eval").is_dir():
                root = nested
        marker = root / "bfcl_eval" / "eval_checker" / "multi_turn_eval" / "multi_turn_utils.py"
        if not marker.is_file():
            raise FileNotFoundError(f"pinned BFCL package not found under {package_root}")
        sys.path.insert(0, str(root))
        from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_utils import (
            execute_multi_turn_func_call,
        )
        self._execute = execute_multi_turn_func_call
        self._instance_name = instance_name

    def _call(self, strings: list[str], case: dict, config: dict):
        return self._execute(
            strings,
            config["initial_config"],
            config["involved_classes"],
            config.get("instance_name") or self._instance_name,
            case["id"],
            long_context=bool(config["long_context"]),
            is_evaL_run=False,
        )

    def initialize(self, case: dict, config: dict) -> dict:
        _outputs, instances = self._call([], case, config)
        return instances

    def memory_prompt(self, question: list[list[dict]], case: dict, instances: dict) -> list[list[dict]]:
        from bfcl_eval.model_handler.utils import add_memory_instruction_system_prompt

        if len(instances) != 1:
            raise RunStopped("memory_instance_count")
        instance = next(iter(instances.values()))
        category = case["id"].rsplit("_", 1)[0]
        return add_memory_instruction_system_prompt(question, category, case["scenario"], instance)

    def execute_calls(self, strings: list[str], case: dict, config: dict) -> list[str]:
        outputs, _instances = self._call(strings, case, config)
        return list(outputs)

    def flush_prereq(self, case: dict, instances: dict) -> None:
        if len(instances) != 1:
            raise RunStopped("memory_instance_count")
        instance = next(iter(instances.values()))
        instance._flush_memory_to_local_file()
        folder = getattr(instance, "snapshot_folder", None)
        written = [getattr(instance, "latest_snapshot_file", None)]
        if folder is not None:
            written.append(Path(folder) / f"{case['id']}.json")
        for path in written:
            if path is not None and Path(path).is_file():
                _fsync_file(Path(path))
                fsync_dir(Path(path).parent)


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def fsync_dir(path: Path) -> None:
    """Make a rename or a new entry in ``path`` survive a power loss."""
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)
    fsync_dir(path.parent)


def _append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    created = not path.exists()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    if created:
        fsync_dir(path.parent)


TOKEN_FIELDS = (
    "prompt_tokens",
    "prompt_cache_hit_tokens",
    "prompt_cache_miss_tokens",
    "output_tokens",
    "reasoning_tokens",
)
TOKEN_RULE = (
    "total_tokens is prompt_tokens plus output_tokens over every billed request in bills.jsonl. "
    "reasoning_tokens are inside output_tokens and are not added again."
)


def empty_tokens() -> dict:
    return {field: 0 for field in TOKEN_FIELDS}


def add_tokens(tally: dict, parsed: dict) -> None:
    for field in TOKEN_FIELDS:
        tally[field] += int(parsed.get(field) or 0)


def token_summary(tally: dict) -> dict:
    return {**tally, "total_tokens": tally["prompt_tokens"] + tally["output_tokens"], "rule": TOKEN_RULE}


def _status(out_dir: Path, **fields) -> dict:
    payload = {
        "study": STUDY_ID,
        "official_settlement": OFFICIAL_SETTLEMENT,
        "model": REQUEST_MODEL,
        "arms": list(ARMS),
        "arm_order": ARM_ORDER,
        "rate_card": rate_card(),
        "max_tokens_sent": False,
        "retries": 0,
        "read_timeout_seconds": READ_TIMEOUT_SECONDS,
        "total_deadline_seconds": TOTAL_DEADLINE_SECONDS,
    }
    payload.update(fields)
    payload["complete"] = bool(payload.get("complete"))
    if payload["complete"]:
        payload["status"] = "complete"
    _write_json(out_dir / "run.json", payload)
    spend = {
        "running_usd": payload.get("running_usd", "0"),
        "ceiling_usd": payload.get("ceiling_usd"),
        "slots_sent": payload.get("slots_sent", 0),
        "slots_total": payload.get("slots_total", 0),
        "slots_skipped": payload.get("slots_skipped", 0),
        "requests_billed": payload.get("requests_billed", 0),
        "complete": payload["complete"],
        "status": payload["status"],
        "reason": payload.get("reason"),
        "uncertain_attempts": payload.get("uncertain_attempts", []),
        "unbilled_attempts": payload.get("unbilled_attempts", []),
        "session": payload.get("session"),
        "tokens": payload.get("tokens"),
        "rate_card": rate_card(),
    }
    _write_json(out_dir / "spend.json", spend)
    return payload


def plan_summary(slots: list[dict], thinking_modes: tuple[str, ...]) -> dict:
    counts: dict[str, int] = {}
    for slot in slots:
        key = f"{slot['thinking']}:{slot['arm']}:{slot['kind']}"
        counts[key] = counts.get(key, 0) + 1
    return {
        "thinking_modes_authorized": list(thinking_modes),
        "slots_total": len(slots),
        "prereq_slots": sum(1 for slot in slots if slot.get("prereq")),
        "counts": counts,
        "order": f"thinking {', then '.join(thinking_modes)}; cases in list order; arms {ARM_ORDER}",
        "slot_sha256": sha256(json.dumps(
            [[slot["thinking"], slot["case_id"], slot["arm"]] for slot in slots]
        ).encode("utf-8")).hexdigest(),
    }


def write_plan(
    cases: list[dict],
    out_dir: Path,
    *,
    pilot: bool,
    thinking_modes: tuple[str, ...] = THINKING_ORDER,
    ceiling_usd: str | None = None,
    extra: dict | None = None,
) -> dict:
    slots = build_slots(cases, thinking_modes)
    fields = {
        "status": "not_sent",
        "complete": False,
        "reason": "dry_plan",
        "pilot": pilot,
        "slots_sent": 0,
        "running_usd": "0",
        "ceiling_usd": ceiling_usd,
        "provider_contacted": False,
        **plan_summary(slots, thinking_modes),
    }
    if extra:
        fields.update(extra)
    return _status(out_dir, **fields)


def refuse_reuse(out_dir: Path) -> str | None:
    for name in EVIDENCE_FILES:
        path = out_dir / name
        if not path.exists():
            continue
        if name == "run.json":
            try:
                if not json.loads(path.read_text(encoding="utf-8")).get("provider_contacted"):
                    continue
            except (OSError, ValueError):
                pass
        return f"out_dir_has_provider_evidence:{name}"
    return None


def execute(
    cases: list[dict],
    slots: list[dict],
    out_dir: Path,
    transport,
    *,
    ceiling_usd: Decimal,
    thinking_modes: tuple[str, ...],
    clock=None,
    executor=None,
    identity: dict | None = None,
    resume: bool = False,
    retry_limit: int = 0,
    sleep=None,
    policy: SendPolicy | None = None,
    monotonic=None,
) -> dict:
    """Send ``slots`` in order. ``thinking_modes`` is what a person authorised.

    ``resume`` continues the run already in ``out_dir``. ``policy`` decides
    deadlines, retries and what follows the last failed try. Without it,
    ``retry_limit`` 0 is the no-retry policy and 2 is the preliminary policy.
    """
    out_dir = Path(out_dir)
    if ceiling_usd <= 0:
        raise RunStopped("ceiling_not_positive")
    if retry_limit < 0:
        raise RunStopped("retry_limit_negative")
    if policy is None:
        policy = legacy_policy(retry_limit)
    elif retry_limit and retry_limit != policy.retry_limit:
        raise RunStopped("retry_limit_disagrees_with_policy")
    if policy.attempt_deadlines is not None and not getattr(transport, "enforces_deadline", False):
        raise RunStopped("transport_does_not_enforce_deadline")
    modes = parse_thinking_modes(",".join(thinking_modes))
    leaked = sorted({slot["thinking"] for slot in slots} - set(modes))
    if leaked:
        raise RunStopped(f"thinking_mode_not_authorized:{','.join(leaked)}")
    by_id = {}
    for case in cases:
        if case["id"] in by_id:
            raise ValueError(f"duplicate case id {case['id']}")
        by_id[case["id"]] = case
    missing = [slot["case_id"] for slot in slots if slot["case_id"] not in by_id]
    if missing:
        raise RunStopped(f"slot_without_case:{missing[0]}")
    plan = None
    if resume:
        from tool_compression.clean_start.resume import apply_resume, inspect_resume

        plan = inspect_resume(
            out_dir, cases, slots, identity=identity or {}, ceiling_usd=ceiling_usd, thinking_modes=modes,
        )
    else:
        reused = refuse_reuse(out_dir)
        if reused:
            raise RunStopped(reused)
    clock = clock or (lambda: datetime.now(timezone.utc))
    sleep = sleep or time.sleep
    monotonic = monotonic or time.monotonic
    state = {
        "running": plan["prior_spend_usd"] if plan else Decimal("0"),
        "sent": plan["finished_slots"] if plan else 0,
        "billed": plan["prior_billed"] if plan else 0,
        "attempt": plan["max_attempt"] if plan else 0,
        "open_attempt": None,
        "partial": [],
        "retries": plan["prior_retries"] if plan else 0,
        "unbilled": list(plan["unbilled_attempts"]) if plan else [],
        "session": plan["session"] if plan else 1,
        "skipped": plan["prior_skipped"] if plan else 0,
        "streak": 0,
        "tokens": dict(plan["prior_tokens"]) if plan else empty_tokens(),
    }
    broken: dict[tuple, str] = {}
    for row in (plan["broken_chains"] if plan else []):
        broken[(row["thinking"], row["arm"], row["category"], row["scenario"])] = row["prereq"]
    started = clock().isoformat()
    session_record = {"session": state["session"], "started_at": started, "resumed": plan is not None}
    if plan:
        applied = apply_resume(out_dir, plan, started)
        session_record.update({
            "prior_spend_usd": applied["prior_spend_usd"],
            "finished_slots_skipped": applied["finished_slots"],
            "next_slot": applied["next_slot"],
            "abandoned_partial_usd": applied["abandoned_partial_usd"],
            "actions": applied["actions"],
        })
    described = policy.describe()
    common = {
        "slots_total": len(slots),
        "ceiling_usd": str(ceiling_usd),
        "provider_contacted": True,
        "identity": identity or {},
        "session": state["session"],
        "sessions": (plan["prior_sessions"] if plan else []) + [session_record],
        "retry_limit": policy.retry_limit,
        "retry_backoff_seconds": list(policy.backoff_seconds),
        "retry_policy": described,
        "read_timeout_seconds": described["read_timeout_seconds"],
        "total_deadline_seconds": described["total_deadline_seconds"],
        "failures_file": FAILURES_FILE,
        **{key: value for key, value in plan_summary(slots, modes).items() if key != "slots_total"},
    }

    def status(**fields) -> dict:
        return _status(
            out_dir,
            slots_sent=state["sent"],
            slots_finished=state["sent"] - state["skipped"],
            slots_skipped=state["skipped"],
            requests_billed=state["billed"],
            running_usd=str(state["running"]),
            partial_slots=state["partial"],
            retries=state["retries"],
            unbilled_attempts=list(state["unbilled"]),
            tokens=token_summary(state["tokens"]),
            **common,
            **fields,
        )

    status(status="running", complete=False, reason=None, uncertain_attempts=[])
    attempts = out_dir / "attempts.jsonl"
    bills = out_dir / "bills.jsonl"
    failures = out_dir / FAILURES_FILE

    def send(slot: dict, body: dict, turn: int, step: int) -> tuple[dict, dict, datetime]:
        if body.get("thinking", {}).get("type") != {"off": "disabled", "on": "enabled"}[slot["thinking"]]:
            raise RunStopped("thinking_field_mismatch")
        if slot["thinking"] not in modes:
            raise RunStopped("thinking_mode_not_authorized")
        if "max_tokens" in body:
            raise RunStopped("max_tokens_present")
        encoded = json.dumps(body, ensure_ascii=False, sort_keys=True).encode("utf-8")
        tools_sha256 = sha256(
            json.dumps(body.get("tools") or [], ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        retry_of = None
        tries = 0
        failed: list[dict] = []
        while True:
            if state["running"] >= ceiling_usd:
                raise RunStopped("ceiling")
            state["attempt"] += 1
            number = state["attempt"]
            deadline = policy.deadline(tries)
            sent_at = clock()
            row = {
                "attempt": number,
                "event": "sent",
                "case_id": slot["case_id"],
                "arm": slot["arm"],
                "thinking": slot["thinking"],
                "turn": turn,
                "step": step,
                "sent_at": sent_at.isoformat(),
                "body_sha256": sha256(encoded).hexdigest(),
                "tools_sha256": tools_sha256,
                "request_bytes": len(encoded),
                "session": state["session"],
            }
            if deadline is not None:
                row["try"] = tries + 1
                row["deadline_seconds"] = deadline
            if retry_of is not None:
                row["retry_of"] = retry_of
            # The budget starts with the journaled send, before the sent-line
            # fsync. A stall there is uninterruptible, so the timer cannot
            # record the failure until the write returns, but it must not then
            # open a fresh provider call on a budget that is already spent.
            began = monotonic()
            timer = None
            token = None
            if deadline is not None:
                timer = DeadlineTimer(deadline)
                token = _ATTEMPT_TIMER.set(timer)
            try:
                _append_jsonl(attempts, row)
                state["open_attempt"] = number
                if timer is not None and (timer.fired.is_set() or timer.due()):
                    raise _deadline_exceeded(deadline, monotonic() - began)
                payload = transport(body) if deadline is None else transport(body, deadline=deadline)
            except RunStopped:
                raise
            except Exception as exc:
                elapsed = monotonic() - began
                transport_failure = is_transport_failure(exc)
                again = tries < policy.retry_limit and transport_failure
                failed_at = clock()
                outcome = {
                    "attempt": number,
                    "event": "failed",
                    "at": failed_at.isoformat(),
                    "error": exc.__class__.__name__,
                    "http_status": getattr(exc, "status", None),
                    "may_be_billed": True,
                    "retried": again,
                }
                if deadline is not None:
                    outcome["deadline_seconds"] = deadline
                    outcome["elapsed_seconds"] = round(elapsed, 3)
                _append_jsonl(attempts, outcome)
                state["unbilled"].append({
                    "attempt": number, "event": "failed", "session": state["session"],
                    "case_id": slot["case_id"], "arm": slot["arm"],
                })
                failed.append({
                    "attempt": number,
                    "try": tries + 1,
                    "sent_at": sent_at.isoformat(),
                    "failed_at": failed_at.isoformat(),
                    "error": exc.__class__.__name__,
                    "http_status": getattr(exc, "status", None),
                    "deadline_seconds": deadline,
                    "elapsed_seconds": round(elapsed, 3),
                    "may_be_billed": True,
                })
                if not again:
                    if transport_failure and policy.exhausted == "skip":
                        state["open_attempt"] = None
                        raise SlotSkipped(turn, step, failed, exc) from exc
                    raise RunStopped(f"provider_error:{exc.__class__.__name__}") from exc
                state["open_attempt"] = None
                state["retries"] += 1
                wait = policy.backoff(tries, exc)
                if wait > 0:
                    sleep(wait)
                tries += 1
                retry_of = number
                continue
            else:
                break
            finally:
                if timer is not None:
                    timer.cancel()
                    _ATTEMPT_TIMER.reset(token)
        try:
            message, parsed, at = _read_payload(payload, clock)
        except RunStopped as stopped:
            _append_jsonl(attempts, {
                "attempt": number,
                "event": "unusable_response",
                "at": clock().isoformat(),
                "reason": stopped.reason,
                "may_be_billed": True,
            })
            state["unbilled"].append({
                "attempt": number, "event": "unusable_response", "session": state["session"],
                "case_id": slot["case_id"], "arm": slot["arm"],
            })
            raise
        amount, band = spend_usd(
            cache_hit=parsed["prompt_cache_hit_tokens"],
            cache_miss=parsed["prompt_cache_miss_tokens"],
            output=parsed["output_tokens"],
            at=at,
        )
        _sent_amount, band_at_send = spend_usd(cache_hit=0, cache_miss=0, output=0, at=sent_at)
        state["running"] += amount
        state["billed"] += 1
        add_tokens(state["tokens"], parsed)
        _append_jsonl(bills, {
            "attempt": number,
            "case_id": slot["case_id"],
            "category": slot["category"],
            "arm": slot["arm"],
            "thinking": slot["thinking"],
            "turn": turn,
            "step": step,
            "sent_at": sent_at.isoformat(),
            "completed_at": at.isoformat(),
            "band": band,
            "band_at_send": band_at_send,
            "prompt_tokens": parsed["prompt_tokens"],
            "prompt_cache_hit_tokens": parsed["prompt_cache_hit_tokens"],
            "prompt_cache_miss_tokens": parsed["prompt_cache_miss_tokens"],
            "output_tokens": parsed["output_tokens"],
            "reasoning_tokens": parsed["reasoning_tokens"],
            "cache_fields": parsed["cache_fields"],
            "usage_inconsistent": parsed["usage_inconsistent"],
            "usd": str(amount),
            "running_usd": str(state["running"]),
            "request_model": REQUEST_MODEL,
            "billed": True,
            "session": state["session"],
        })
        _append_jsonl(attempts, {"attempt": number, "event": "completed", "at": at.isoformat(), "billed": True})
        state["open_attempt"] = None
        return message, parsed, at

    def stop(reason: str) -> dict:
        uncertain = [state["open_attempt"]] if state["open_attempt"] is not None else []
        return status(
            status="incomplete",
            complete=False,
            reason=reason,
            uncertain_attempts=uncertain,
            partial_presented_as_complete=False,
        )

    def stop_in_slot(slot: dict, sidecar: dict, reason: str) -> dict:
        if sidecar["steps"] or sidecar.get("stage"):
            sidecar["status"] = "stopped"
            sidecar["stop_reason"] = reason
            _write_sidecar(out_dir, slot, sidecar)
            state["partial"].append({
                "case_id": slot["case_id"],
                "arm": slot["arm"],
                "thinking": slot["thinking"],
                "billed_steps": len(sidecar["steps"]),
            })
        return stop(reason)

    def record_skip(slot: dict, sidecar: dict, record: dict) -> None:
        """The failure line is durable first. A box lost before the sidecar is repaired by resume."""
        _append_jsonl(failures, record)
        sidecar["status"] = "skipped"
        sidecar["scorable"] = False
        sidecar["skip"] = record
        sidecar.pop("stage", None)
        _write_sidecar(out_dir, slot, sidecar)
        state["sent"] += 1
        state["skipped"] += 1
        status(status="running", complete=False, reason=None, uncertain_attempts=[])

    skip = state["sent"]
    for index, slot in enumerate(slots):
        if index < skip:
            continue
        case = by_id[slot["case_id"]]
        chain = memory_chain(slot, case)
        sidecar = _new_sidecar(case, slot)
        sidecar["session"] = state["session"]
        if chain is not None and chain in broken:
            record_skip(slot, sidecar, _skip_record(
                "dependency_skipped", slot, case, policy, state["session"], clock(),
                depends_on=broken[chain],
            ))
            continue
        if state["running"] >= ceiling_usd:
            return stop("ceiling")
        if slot["kind"] == "trajectory" and executor is None:
            return stop("trajectory_executor_required")
        try:
            if slot["kind"] == "single":
                _run_single(case, slot, out_dir, send, sidecar)
            else:
                _run_trajectory(case, slot, out_dir, send, executor, sidecar)
        except SlotSkipped as skipped:
            if policy.skip_streak_limit is not None and state["streak"] >= policy.skip_streak_limit:
                return stop_in_slot(
                    slot, sidecar,
                    f"skip_streak:{state['streak'] + 1}:{skipped.error.__class__.__name__}",
                )
            record = _skip_record(
                "skipped", slot, case, policy, state["session"], clock(),
                turn=skipped.turn, step=skipped.step, attempts=skipped.attempts, error=skipped.error,
                billed_steps=len(sidecar["steps"]),
            )
            record_skip(slot, sidecar, record)
            state["streak"] += 1
            if chain is not None and slot["prereq"]:
                broken[chain] = slot["case_id"]
            continue
        except RunStopped as stopped:
            return stop_in_slot(slot, sidecar, stopped.reason)
        state["streak"] = 0
        state["sent"] += 1
        status(status="running", complete=False, reason=None, uncertain_attempts=[])
    return status(status="complete", complete=True, reason="finished", uncertain_attempts=[])


def memory_chain(slot: dict, case: dict) -> tuple | None:
    """Memory slots that share one ``<scenario>_final.json``: one arm, one backend, one scenario."""
    if not is_memory(case["category"]) or case.get("scenario") is None:
        return None
    return (slot["thinking"], slot["arm"], case["category"], case["scenario"])


def _skip_record(
    kind: str,
    slot: dict,
    case: dict,
    policy: SendPolicy,
    session: int,
    at: datetime,
    *,
    turn: int | None = None,
    step: int | None = None,
    attempts: list[dict] | None = None,
    error: BaseException | None = None,
    billed_steps: int = 0,
    depends_on: str | None = None,
) -> dict:
    return {
        "kind": kind,
        "case_id": slot["case_id"],
        "category": slot["category"],
        "arm": slot["arm"],
        "thinking": slot["thinking"],
        "prereq": bool(slot.get("prereq")),
        "scenario": case.get("scenario") if is_memory(case["category"]) else None,
        "turn": turn,
        "step": step,
        "error": None if error is None else error.__class__.__name__,
        "http_status": None if error is None else getattr(error, "status", None),
        "attempts": list(attempts or []),
        "may_be_billed": bool(attempts),
        "billed_steps_before_skip": billed_steps,
        "depends_on": depends_on,
        "policy": policy.name,
        "session": session,
        "recorded_at": at.isoformat(),
        "scoring": "incomplete: no result line is written, so official evaluation has no output for this id and arm",
    }


def _new_sidecar(case: dict, slot: dict) -> dict:
    return {
        "case_id": case["id"],
        "category": case["category"],
        "arm": slot["arm"],
        "thinking": slot["thinking"],
        "request_model": REQUEST_MODEL,
        "status": "in_progress",
        "steps": [],
        "scorable": False,
    }


def _run_single(case: dict, slot: dict, out_dir: Path, send, sidecar: dict) -> None:
    thinking, arm = slot["thinking"], slot["arm"]
    messages = turn_messages(case, 0)
    tools = arm_tools(case["function"], case["category"], arm)
    body = request_body(messages, tools, thinking)
    message, parsed, _at = send(slot, body, 0, 0)
    result, _calls = parse_fc_message(message)
    sidecar["steps"].append(_step_record(message, result, parsed))
    _write_sidecar(out_dir, slot, sidecar)
    append_result(out_dir, case["id"], thinking, {
        "id": case["id"],
        "result": result,
        "input_token_count": parsed["prompt_tokens"],
        "output_token_count": parsed["output_tokens"],
    }, arm)
    sidecar["status"] = "finished"
    sidecar["scorable"] = True
    sidecar["result"] = result
    _write_sidecar(out_dir, slot, sidecar)


def _run_trajectory(case: dict, slot: dict, out_dir: Path, send, executor, sidecar: dict) -> None:
    thinking, arm = slot["thinking"], slot["arm"]
    result_dir = out_dir / "result" / result_model_name(thinking, arm)
    config = execution_config(case, result_dir)
    config["instance_name"] = executor_instance_name(thinking, arm)
    sidecar["stage"] = "initialize"
    initialize = getattr(executor, "initialize", None)
    instances = initialize(case, config) if initialize else {}
    question = prepared_question(case)
    if is_memory(case["category"]):
        memory_prompt = getattr(executor, "memory_prompt", None)
        if memory_prompt is None:
            raise RunStopped("memory_prompt_unavailable")
        question = memory_prompt(question, case, instances)
    sidecar["stage"] = "turns"
    messages: list[dict] = []
    held_out: list[list[dict]] = []
    turns: list[list] = []
    input_counts: list[list[int]] = []
    output_counts: list[list[int]] = []
    forced = False
    for turn_index in range(len(question)):
        if str(turn_index) in case.get("held_out", {}):
            held_out = held_out + [list(case["held_out"][str(turn_index)])]
        messages.extend(turn_messages(case, turn_index, question))
        steps: list = []
        turn_in: list[int] = []
        turn_out: list[int] = []
        count = 0
        while True:
            tools = arm_tools(case["function"], case["category"], arm, held_out)
            body = request_body(messages, tools, thinking)
            message, parsed, _at = send(slot, body, turn_index, count)
            result, calls = parse_fc_message(message)
            messages.append(assistant_history(message))
            steps.append(result)
            turn_in.append(parsed["prompt_tokens"])
            turn_out.append(parsed["output_tokens"])
            record = _step_record(message, result, parsed, turn_index, count)
            sidecar["steps"].append(record)
            _write_sidecar(out_dir, slot, sidecar)
            try:
                decoded = decode_execute(result)
            except Exception as exc:
                record["turn_end"] = f"decode_error:{exc.__class__.__name__}"
                _write_sidecar(out_dir, slot, sidecar)
                break
            if is_empty_execute_response(decoded):
                record["turn_end"] = "empty_response"
                _write_sidecar(out_dir, slot, sidecar)
                break
            outputs = _execute_calls(executor, decoded, case, config)
            record["executed"] = decoded
            record["tool_outputs"] = outputs
            _write_sidecar(out_dir, slot, sidecar)
            for output, call in zip(outputs, calls):
                messages.append({"role": "tool", "content": output, "tool_call_id": call["id"]})
            count += 1
            if count > STEP_LIMIT:
                forced = True
                record["turn_end"] = "forced_quit"
                break
        turns.append(steps)
        input_counts.append(turn_in)
        output_counts.append(turn_out)
        if forced:
            break
    if case.get("prereq") and is_memory(case["category"]):
        flush = getattr(executor, "flush_prereq", None)
        if flush is None:
            raise RunStopped("memory_flush_unavailable")
        flush(case, instances)
    append_result(out_dir, case["id"], thinking, {
        "id": case["id"],
        "result": turns,
        "input_token_count": input_counts,
        "output_token_count": output_counts,
        "forced_quit": forced,
    }, arm)
    sidecar["status"] = "finished"
    sidecar["scorable"] = True
    sidecar["result"] = turns
    sidecar["forced_quit"] = forced
    sidecar.pop("stage", None)
    _write_sidecar(out_dir, slot, sidecar)


def _execute_calls(executor, decoded: list[str], case: dict, config: dict) -> list[str]:
    run = getattr(executor, "execute_calls", None)
    if run is None:
        raise RunStopped("executor_interface")
    try:
        return list(run(decoded, case, config))
    except RunStopped:
        raise
    except Exception as exc:
        raise RunStopped(f"executor_error:{exc.__class__.__name__}") from exc


def _read_payload(payload, clock):
    if not isinstance(payload, dict):
        raise RunStopped("provider_payload")
    choices = payload.get("choices") or []
    parsed = parse_usage(payload.get("usage"))
    if not parsed.get("billed"):
        raise RunStopped(parsed.get("reason") or "unbilled_response")
    if not choices or not isinstance(choices[0], dict):
        raise RunStopped("provider_choice_missing")
    message = choices[0].get("message") or {}
    at = clock()
    if at.tzinfo is None:
        raise RunStopped("clock_must_be_timezone_aware")
    return message, parsed, at


def _step_record(message: dict, result: object, parsed: dict, turn: int = 0, step: int = 0) -> dict:
    return {
        "turn": turn,
        "step": step,
        "result": result,
        "content": message.get("content"),
        "reasoning_content": message.get("reasoning_content"),
        "tool_calls": message.get("tool_calls"),
        "prompt_tokens": parsed["prompt_tokens"],
        "prompt_cache_hit_tokens": parsed["prompt_cache_hit_tokens"],
        "prompt_cache_miss_tokens": parsed["prompt_cache_miss_tokens"],
        "output_tokens": parsed["output_tokens"],
        "reasoning_tokens": parsed["reasoning_tokens"],
    }


def _write_sidecar(out_dir: Path, slot: dict, sidecar: dict) -> None:
    path = (
        out_dir / "model_outputs" / registry_dir(slot["thinking"]) / slot["arm"] / f"{slot['case_id']}.json"
    )
    _write_json(path, sidecar)


def resolve_bfcl_package(root: Path) -> Path:
    root = Path(root)
    if (root / "bfcl_eval").is_dir():
        return root
    nested = root / "berkeley-function-call-leaderboard"
    if (nested / "bfcl_eval").is_dir():
        return nested
    raise FileNotFoundError(f"no bfcl_eval package under {root}")
