"""Send U/S/X/SX with thinking off, then thinking on.

The default path does not read a provider key and does not open a socket.
``--live`` without ``--authorize-live`` exits before either of those. There is
no max_tokens budget and no pre-send reserve. After each completed response the
billed usage is recorded and the running spend is compared with the ceiling.
A run that stops early is marked incomplete.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import json
import os

from tool_compression.clean_start.categories import is_agentic, is_trajectory
from tool_compression.clean_start.pin import (
    ARMS,
    OFFICIAL_SETTLEMENT,
    REQUEST_MODEL,
    STUDY_ID,
    TEMPERATURE,
    THINKING_ORDER,
    STEP_LIMIT,
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
    parse_fc_message,
    registry_dir,
)

class RunStopped(RuntimeError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


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


def post_chat(body: dict, api_key: str) -> dict:
    """POST one chat completion. Imported only after authorization."""
    import urllib.request

    payload = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


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


def turn_messages(case: dict, turn_index: int) -> list[dict]:
    turn = case["question"][turn_index]
    if not turn and str(turn_index) in case.get("held_out", {}):
        messages = [{"role": "user", "content": HOLDOUT_USER_PROMPT}]
    else:
        messages = [dict(item) for item in turn]
    if turn_index == 0 and is_agentic(case["category"]) and not case.get("prereq"):
        messages = [{"role": "system", "content": AGENTIC_SYSTEM_PROMPT}, *messages]
    return messages


def arm_tools(functions: list[dict], category: str, arm: str) -> list[dict]:
    facing = model_facing_tools(functions, category)
    if arm == "U":
        return facing
    return render_tools(facing)["arms"][arm]


def build_slots(cases: list[dict]) -> list[dict]:
    slots = []
    for thinking in THINKING_ORDER:
        for case in cases:
            for arm in ARMS:
                slots.append({
                    "case_id": case["id"],
                    "category": case["category"],
                    "arm": arm,
                    "thinking": thinking,
                    "prereq": bool(case.get("prereq")),
                    "kind": "trajectory" if is_trajectory(case["category"]) else "single",
                })
    return slots


def execution_config(case: dict, result_dir: Path) -> dict:
    classes = list(case.get("involved_classes") or [])
    if case["category"].startswith("memory_"):
        class_name = classes[0]
        return {
            "initial_config": {
                class_name: {
                    "model_result_dir": str(result_dir),
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


class OfficialBfclExecutor:
    """Call the pinned ``execute_multi_turn_func_call``. Constructed only for an authorized run."""

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

    def execute(self, result: object, case: dict, config: dict) -> list[str]:
        from tool_compression.clean_start.scoring import to_execution_strings
        strings = to_execution_strings(result)
        outputs, _instances = self._execute(
            strings,
            config["initial_config"],
            config["involved_classes"],
            config.get("instance_name") or self._instance_name,
            case["id"],
            long_context=bool(config["long_context"]),
            is_evaL_run=False,
        )
        return list(outputs)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _status(out_dir: Path, **fields) -> dict:
    payload = {
        "study": STUDY_ID,
        "official_settlement": OFFICIAL_SETTLEMENT,
        "model": REQUEST_MODEL,
        "arms": list(ARMS),
        "thinking_order": list(THINKING_ORDER),
        "rate_card": rate_card(),
        "max_tokens_sent": False,
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
        "complete": payload["complete"],
        "status": payload["status"],
        "reason": payload.get("reason"),
        "rate_card": rate_card(),
    }
    _write_json(out_dir / "spend.json", spend)
    return payload


def write_plan(cases: list[dict], out_dir: Path, *, pilot: bool) -> dict:
    slots = build_slots(cases)
    counts: dict[str, int] = {}
    for slot in slots:
        key = f"{slot['thinking']}:{slot['arm']}:{slot['kind']}"
        counts[key] = counts.get(key, 0) + 1
    return _status(
        out_dir,
        status="not_sent",
        complete=False,
        reason="dry_plan",
        pilot=pilot,
        slots_total=len(slots),
        slots_sent=0,
        running_usd="0",
        ceiling_usd=None,
        order="thinking off for every case and arm, then thinking on; arms are U, S, X, SX",
        counts=counts,
        provider_contacted=False,
    )


def execute(
    cases: list[dict],
    slots: list[dict],
    out_dir: Path,
    transport,
    *,
    ceiling_usd: Decimal,
    clock=None,
    executor=None,
) -> dict:
    if ceiling_usd <= 0:
        raise RunStopped("ceiling_not_positive")
    clock = clock or (lambda: datetime.now(timezone.utc))
    by_id = {}
    for case in cases:
        if case["id"] in by_id:
            raise ValueError(f"duplicate case id {case['id']}")
        by_id[case["id"]] = case
    running = Decimal("0")
    sent = 0
    bills = out_dir / "bills.jsonl"
    bills.parent.mkdir(parents=True, exist_ok=True)
    state = _status(
        out_dir,
        status="running",
        complete=False,
        reason=None,
        slots_total=len(slots),
        slots_sent=0,
        running_usd=str(running),
        ceiling_usd=str(ceiling_usd),
        provider_contacted=True,
    )

    def bill(slot: dict, step: dict, at: datetime, parsed: dict) -> None:
        nonlocal running, sent
        amount, band = spend_usd(
            cache_hit=parsed["prompt_cache_hit_tokens"],
            cache_miss=parsed["prompt_cache_miss_tokens"],
            output=parsed["output_tokens"],
            at=at,
        )
        running += amount
        row = {
            "case_id": slot["case_id"],
            "category": slot["category"],
            "arm": slot["arm"],
            "thinking": slot["thinking"],
            "turn": step["turn"],
            "step": step["step"],
            "completed_at": at.isoformat(),
            "band": band,
            "prompt_tokens": parsed["prompt_tokens"],
            "prompt_cache_hit_tokens": parsed["prompt_cache_hit_tokens"],
            "prompt_cache_miss_tokens": parsed["prompt_cache_miss_tokens"],
            "output_tokens": parsed["output_tokens"],
            "reasoning_tokens": parsed["reasoning_tokens"],
            "cache_fields": parsed["cache_fields"],
            "usage_inconsistent": parsed["usage_inconsistent"],
            "usd": str(amount),
            "running_usd": str(running),
            "request_model": REQUEST_MODEL,
            "billed": True,
        }
        with bills.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            handle.flush()

    def stop(reason: str, scorable_case: bool) -> dict:
        return _status(
            out_dir,
            status="incomplete",
            complete=False,
            reason=reason,
            slots_total=len(slots),
            slots_sent=sent,
            running_usd=str(running),
            ceiling_usd=str(ceiling_usd),
            provider_contacted=True,
            partial_presented_as_complete=False,
        )

    for slot in slots:
        if running >= ceiling_usd:
            return stop("ceiling", False)
        if slot["kind"] == "trajectory" and executor is None:
            return stop("trajectory_executor_required", False)
        case = by_id[slot["case_id"]]
        try:
            finished = _run_slot(
                case, slot, out_dir, transport, clock, executor, bill,
            )
        except RunStopped as stopped:
            return stop(stopped.reason, False)
        if not finished:
            return stop("slot_not_finished", False)
        sent += 1
        _status(
            out_dir,
            status="running",
            complete=False,
            reason=None,
            slots_total=len(slots),
            slots_sent=sent,
            running_usd=str(running),
            ceiling_usd=str(ceiling_usd),
            provider_contacted=True,
        )
    return _status(
        out_dir,
        status="complete",
        complete=True,
        reason="finished",
        slots_total=len(slots),
        slots_sent=sent,
        running_usd=str(running),
        ceiling_usd=str(ceiling_usd),
        provider_contacted=True,
    )


def _run_slot(case, slot, out_dir, transport, clock, executor, bill) -> bool:
    thinking = slot["thinking"]
    arm = slot["arm"]
    result_dir = out_dir / "result" / registry_dir(thinking)
    config = execution_config(case, result_dir)
    config["instance_name"] = f"deepseek_flash_thinking_{thinking}"
    sidecar = {
        "case_id": case["id"],
        "category": case["category"],
        "arm": arm,
        "thinking": thinking,
        "request_model": REQUEST_MODEL,
        "steps": [],
        "scorable": False,
    }
    if slot["kind"] == "single":
        messages = turn_messages(case, 0)
        tools = arm_tools(case["function"], case["category"], arm)
        body = request_body(messages, tools, thinking)
        message, parsed, at = _exchange(body, transport, clock)
        bill(slot, {"turn": 0, "step": 0}, at, parsed)
        result, _calls = parse_fc_message(message)
        entry = {
            "id": case["id"],
            "result": result,
            "input_token_count": parsed["prompt_tokens"],
            "output_token_count": parsed["output_tokens"],
        }
        append_result(out_dir, case["id"], thinking, entry)
        sidecar["steps"].append(_step_record(message, result, parsed))
        sidecar["scorable"] = True
        sidecar["result"] = result
        _write_sidecar(out_dir, slot, sidecar)
        return True

    messages: list[dict] = []
    functions = list(case["function"])
    turns: list[list] = []
    input_counts: list[list[int]] = []
    output_counts: list[list[int]] = []
    forced = False
    for turn_index in range(len(case["question"])):
        if str(turn_index) in case.get("held_out", {}):
            functions = functions + list(case["held_out"][str(turn_index)])
        messages.extend(turn_messages(case, turn_index))
        steps: list = []
        turn_in: list[int] = []
        turn_out: list[int] = []
        for step_index in range(STEP_LIMIT):
            tools = arm_tools(functions, case["category"], arm)
            body = request_body(messages, tools, thinking)
            message, parsed, at = _exchange(body, transport, clock)
            bill(slot, {"turn": turn_index, "step": step_index}, at, parsed)
            result, calls = parse_fc_message(message)
            messages.append(assistant_history(message))
            steps.append(result)
            turn_in.append(parsed["prompt_tokens"])
            turn_out.append(parsed["output_tokens"])
            sidecar["steps"].append(_step_record(message, result, parsed, turn_index, step_index))
            if not calls:
                break
            outputs = executor.execute(result, case, config)
            if len(outputs) != len(calls):
                raise RunStopped("executor_result_count")
            for call, output in zip(calls, outputs):
                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": output,
                })
        else:
            forced = True
        turns.append(steps)
        input_counts.append(turn_in)
        output_counts.append(turn_out)
        if forced:
            break
    entry = {
        "id": case["id"],
        "result": turns,
        "input_token_count": input_counts,
        "output_token_count": output_counts,
        "forced_quit": forced,
    }
    append_result(out_dir, case["id"], thinking, entry)
    sidecar["scorable"] = True
    sidecar["result"] = turns
    sidecar["forced_quit"] = forced
    _write_sidecar(out_dir, slot, sidecar)
    return True


def _exchange(body: dict, transport, clock):
    if "max_tokens" in body:
        raise RunStopped("max_tokens_present")
    try:
        payload = transport(body)
    except RunStopped:
        raise
    except Exception as exc:
        raise RunStopped(f"provider_error:{exc.__class__.__name__}") from exc
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
