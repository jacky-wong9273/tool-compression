"""Send U/S/X/SX for the thinking modes a person authorised, one request at a time.

The default path does not read a provider key and does not open a socket.
``--live`` without ``--authorize-live`` exits before either of those. There is
no max_tokens budget and no pre-send reserve. Before each request the running
spend is compared with the ceiling and an attempt line is journalled. After each
completed response the billed usage is recorded and the step is written to its
sidecar, so a stopped trajectory keeps every billed step. A run that stops
early is marked incomplete.

By default nothing is retried. With ``retry_limit`` above 0, a send that fails
in transport (timeout, dropped or incomplete read, HTTP 429 or 5xx) is sent
again with the same body, at most ``retry_limit`` times, after the ceiling is
checked again. Each try is its own journalled attempt, and a failed one stays
listed as possibly billed. Nothing else in the slot has changed by then.

A fresh run refuses an output directory that already holds provider evidence.
``resume=True`` is the only way back into one: see ``resume.py``. Finished
slots are skipped, the stopped slot is sent again from its first request, and
the bill ledger's sum counts against the same ceiling.

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
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import http.client
import importlib.util
import json
import os
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
EVIDENCE_FILES = ("attempts.jsonl", "bills.jsonl", "run.json")
ARM_ORDER = "rotated by case position: case i sends ARMS[i % 4:] + ARMS[:i % 4]"
RETRY_LIMIT = 2
RETRY_BACKOFF_SECONDS = (10.0, 30.0)
RETRY_HTTP_STATUSES = frozenset({429, 500, 502, 503, 504})


class RunStopped(RuntimeError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class TotalDeadlineExceeded(TimeoutError):
    """The whole request outlived the total deadline. It may still be billed."""


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


def post_chat(
    body: dict,
    api_key: str,
    *,
    read_timeout: float = READ_TIMEOUT_SECONDS,
    total_deadline: float = TOTAL_DEADLINE_SECONDS,
    connection_factory=None,
) -> dict:
    """POST one chat completion with a per-read timeout and a total deadline.

    A socket timeout only bounds each read, so a server that keeps a queued
    request alive can hold it far longer. The total deadline closes the
    connection from outside and raises ``TotalDeadlineExceeded``. Either way the
    request may already be billed. The caller journals it as possibly billed and
    either stops or, within its retry limit, sends the same body again.
    """
    import threading
    from urllib.parse import urlsplit

    url = urlsplit(API_URL)
    if connection_factory is None:
        import http.client
        import ssl

        def connection_factory():
            return http.client.HTTPSConnection(
                url.hostname, timeout=read_timeout, context=ssl.create_default_context()
            )

    payload = json.dumps(body).encode("utf-8")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    connection = connection_factory()
    outcome: dict = {}

    def work():
        try:
            connection.request("POST", url.path, body=payload, headers=headers)
            response = connection.getresponse()
            outcome["status"] = response.status
            outcome["data"] = response.read()
        except BaseException as exc:
            outcome["error"] = exc

    worker = threading.Thread(target=work, daemon=True)
    worker.start()
    worker.join(total_deadline)
    if worker.is_alive():
        try:
            connection.close()
        finally:
            raise TotalDeadlineExceeded(f"no complete response within {total_deadline} seconds")
    connection.close()
    if "error" in outcome:
        raise outcome["error"]
    if outcome.get("status") != 200:
        raise ProviderHTTPError(int(outcome.get("status") or 0), outcome.get("data", b"")[:500].decode("utf-8", "replace"))
    return json.loads(outcome["data"].decode("utf-8"))


def authorized_transport():
    """Build the live transport. This is the first point that reads the key."""
    api_key = read_provider_key()

    def transport(body: dict) -> dict:
        return post_chat(body, api_key)

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


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def _append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


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
        "requests_billed": payload.get("requests_billed", 0),
        "complete": payload["complete"],
        "status": payload["status"],
        "reason": payload.get("reason"),
        "uncertain_attempts": payload.get("uncertain_attempts", []),
        "unbilled_attempts": payload.get("unbilled_attempts", []),
        "session": payload.get("session"),
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
) -> dict:
    """Send ``slots`` in order. ``thinking_modes`` is what a person authorised.

    ``resume`` continues the run already in ``out_dir``. ``retry_limit`` is how
    many times one failed send may be sent again.
    """
    out_dir = Path(out_dir)
    if ceiling_usd <= 0:
        raise RunStopped("ceiling_not_positive")
    if retry_limit < 0:
        raise RunStopped("retry_limit_negative")
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
    }
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
    common = {
        "slots_total": len(slots),
        "ceiling_usd": str(ceiling_usd),
        "provider_contacted": True,
        "identity": identity or {},
        "session": state["session"],
        "sessions": (plan["prior_sessions"] if plan else []) + [session_record],
        "retry_limit": retry_limit,
        "retry_backoff_seconds": list(RETRY_BACKOFF_SECONDS),
        **{key: value for key, value in plan_summary(slots, modes).items() if key != "slots_total"},
    }

    def status(**fields) -> dict:
        return _status(
            out_dir,
            slots_sent=state["sent"],
            requests_billed=state["billed"],
            running_usd=str(state["running"]),
            partial_slots=state["partial"],
            retries=state["retries"],
            unbilled_attempts=list(state["unbilled"]),
            **common,
            **fields,
        )

    status(status="running", complete=False, reason=None, uncertain_attempts=[])
    attempts = out_dir / "attempts.jsonl"
    bills = out_dir / "bills.jsonl"

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
        while True:
            if state["running"] >= ceiling_usd:
                raise RunStopped("ceiling")
            state["attempt"] += 1
            number = state["attempt"]
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
            if retry_of is not None:
                row["retry_of"] = retry_of
            _append_jsonl(attempts, row)
            state["open_attempt"] = number
            try:
                payload = transport(body)
            except RunStopped:
                raise
            except Exception as exc:
                again = tries < retry_limit and is_transport_failure(exc)
                _append_jsonl(attempts, {
                    "attempt": number,
                    "event": "failed",
                    "at": clock().isoformat(),
                    "error": exc.__class__.__name__,
                    "http_status": getattr(exc, "status", None),
                    "may_be_billed": True,
                    "retried": again,
                })
                state["unbilled"].append({
                    "attempt": number, "event": "failed", "session": state["session"],
                    "case_id": slot["case_id"], "arm": slot["arm"],
                })
                if not again:
                    raise RunStopped(f"provider_error:{exc.__class__.__name__}") from exc
                state["open_attempt"] = None
                state["retries"] += 1
                sleep(RETRY_BACKOFF_SECONDS[min(tries, len(RETRY_BACKOFF_SECONDS) - 1)])
                tries += 1
                retry_of = number
                continue
            break
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

    skip = state["sent"]
    for index, slot in enumerate(slots):
        if index < skip:
            continue
        if state["running"] >= ceiling_usd:
            return stop("ceiling")
        if slot["kind"] == "trajectory" and executor is None:
            return stop("trajectory_executor_required")
        case = by_id[slot["case_id"]]
        sidecar = _new_sidecar(case, slot)
        sidecar["session"] = state["session"]
        try:
            if slot["kind"] == "single":
                _run_single(case, slot, out_dir, send, sidecar)
            else:
                _run_trajectory(case, slot, out_dir, send, executor, sidecar)
        except RunStopped as stopped:
            if sidecar["steps"] or sidecar.get("stage"):
                sidecar["status"] = "stopped"
                sidecar["stop_reason"] = stopped.reason
                _write_sidecar(out_dir, slot, sidecar)
                state["partial"].append({
                    "case_id": slot["case_id"],
                    "arm": slot["arm"],
                    "thinking": slot["thinking"],
                    "billed_steps": len(sidecar["steps"]),
                })
            return stop(stopped.reason)
        state["sent"] += 1
        status(status="running", complete=False, reason=None, uncertain_attempts=[])
    return status(status="complete", complete=True, reason="finished", uncertain_attempts=[])


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
