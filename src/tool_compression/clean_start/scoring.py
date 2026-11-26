"""Official BFCL result files. This module does not score.

``bfcl_eval evaluate`` reads JSONL lines with ``id`` and ``result``. Decoding
uses the OpenAI-completions function-calling handler: a tool call is
``{function_name: arguments_json}`` and a turn without a tool call is the
assistant content string. Multi-turn and agentic results are nested lists of
those steps. Gold stays in the pinned Gorilla tree.
"""

from __future__ import annotations

from pathlib import Path
import json
import os

from tool_compression.clean_start.categories import category_from_id, result_group
from tool_compression.clean_start.pin import (
    ARMS,
    BFCL_COMMIT,
    BFCL_VERSION_PREFIX,
    REQUEST_MODEL,
    THINKING_ORDER,
)


def registry_dir(thinking: str) -> str:
    if thinking not in {"off", "on"}:
        raise ValueError(thinking)
    return f"deepseek-flash-thinking-{thinking}"


def result_model_name(thinking: str, arm: str) -> str:
    """Directory name ``bfcl evaluate --model`` selects.

    Official files are ``result/<model>/<group>/BFCL_v4_<category>_result.json``.
    The evaluator has no arm field, so the arm is part of the model directory.
    """
    if arm not in ARMS:
        raise ValueError(arm)
    return f"{registry_dir(thinking)}-{arm}"


def result_relative(case_id: str, thinking: str, arm: str) -> Path:
    category = category_from_id(case_id)
    filename = f"{BFCL_VERSION_PREFIX}_{category}_result.json"
    return Path("result") / result_model_name(thinking, arm) / result_group(category) / filename


def parse_fc_message(message: dict) -> tuple[object, list[dict]]:
    """Return the official ``result`` object and the tool calls, if any."""
    tool_calls = message.get("tool_calls") or []
    if tool_calls:
        result = []
        calls = []
        for call in tool_calls:
            function = call.get("function") or {}
            name = function.get("name")
            arguments = function.get("arguments")
            if not isinstance(arguments, str):
                arguments = json.dumps(arguments, ensure_ascii=False, separators=(",", ":"))
            result.append({name: arguments})
            calls.append({
                "id": call.get("id"),
                "name": name,
                "arguments": arguments,
            })
        return result, calls
    content = message.get("content")
    return "" if content is None else content, []


def assistant_history(message: dict) -> dict:
    """History entry. Thinking-mode tool turns must carry reasoning_content back."""
    history = {
        "role": "assistant",
        "content": message.get("content"),
    }
    if message.get("tool_calls"):
        history["tool_calls"] = message["tool_calls"]
    if message.get("reasoning_content"):
        history["reasoning_content"] = message["reasoning_content"]
    return history


def decode_execute(result: object) -> list[str]:
    """Port of pinned ``convert_to_function_call`` for an FC model.

    Raises exactly where the pinned decoder raises: a content string, a non-JSON
    argument string, or arguments that are not an object. The official loop
    ends the turn on that exception.
    """
    calls = [result] if isinstance(result, dict) else result
    strings = []
    for call in calls:
        for name, value in call.items():
            if isinstance(value, str):
                value = json.loads(value)
            strings.append(f"{name}({','.join(f'{key}={repr(item)}' for key, item in value.items())})")
    return strings


def is_empty_execute_response(decoded: list) -> bool:
    """Port of pinned ``is_empty_execute_response``."""
    if len(decoded) == 0:
        return True
    return len(decoded) == 1 and len(decoded[0]) == 0


def to_execution_strings(result: object) -> list[str]:
    """Same shape as BFCL ``convert_to_function_call`` for the official executor."""
    if not isinstance(result, list):
        return []
    strings = []
    for call in result:
        if not isinstance(call, dict) or len(call) != 1:
            continue
        name, raw = next(iter(call.items()))
        args = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(args, dict):
            args = {}
        strings.append(f"{name}({','.join(f'{key}={repr(value)}' for key, value in args.items())})")
    return strings


def append_result(out_dir: Path, case_id: str, thinking: str, entry: dict, arm: str) -> Path:
    path = out_dir / result_relative(case_id, thinking, arm)
    path.parent.mkdir(parents=True, exist_ok=True)
    created = not path.exists()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    if created:
        descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    return path


def evaluate_instructions() -> str:
    from tool_compression.clean_start.scope import require_recorded_scope

    scope = require_recorded_scope()
    kept = ", ".join(scope["keep"])
    dropped = ", ".join(scope["drop"])
    mixed = ", ".join(row["category"] for row in scope["mixed"])
    directories = [
        result_model_name(thinking, arm) for thinking in THINKING_ORDER for arm in ARMS
    ]
    commands = "\n".join(
        "  bfcl evaluate --model "
        f"{name} --test-category <category> --result-dir <out>/result --partial-eval"
        for name in directories
    )
    return (
        "Accuracy is recovered by the official evaluator at gorilla commit "
        f"{BFCL_COMMIT}, not by a scorer in this repo. Gold files stay in that tree "
        "under bfcl_eval/data/possible_answer and are not editor inputs. "
        "This packaging is not official settlement.\n\n"
        "Result lines are JSONL objects with id and result. bfcl evaluate reads "
        "result/<model>/<group>/BFCL_v4_<category>_result.json and has no arm field, "
        "so each arm of each thinking pass is its own model directory:\n"
        "  <out>/result/deepseek-flash-thinking-<off|on>-<U|S|X|SX>/<group>/BFCL_v4_<category>_result.json\n"
        "U, S, X, and SX do not append into the same BFCL_v4_<category>_result.json. "
        f"The eight directories are {', '.join(directories)}. "
        "The API model on every request is "
        f"{REQUEST_MODEL}. Memory snapshots for a trajectory are written under that "
        "same per-arm directory:\n"
        "  <out>/result/deepseek-flash-thinking-<off|on>-<U|S|X|SX>/<group>/memory_snapshot/<scenario>_final.json\n"
        "The executor instance name is deepseek_flash_thinking_<off|on>_<arm>. "
        "U, S, X, and SX do not share an in-process class instance or a snapshot file. "
        "bfcl evaluate reads the BFCL_v4 result files and does not read memory_snapshot.\n\n"
        "This study's categories, in order, are: "
        f"{kept}. "
        f"Dropped from this study: {dropped}. "
        f"Mixed categories ({mixed}) include only the in-scope ids in "
        "studies/clean-start-usx/scope.json. Their result files omit the other ids "
        "in that official category. A missing one-tool id is outside this study, "
        "not an incomplete result file. Do not pass all_scoring.\n\n"
        "The pinned BFCL model list has no deepseek-flash entry. Register each of "
        "the eight directory names before evaluate, with model_name "
        f"'{REQUEST_MODEL}', is_fc_model True, underscore_to_dot True, and "
        "DeepSeekAPIHandler, the same flags as the pinned DeepSeek-V3.2-Exp-FC entry. "
        "underscore_to_dot must be True: tool names are sent with '.' replaced by '_', "
        "and with False every dotted gold name scores as wrong_func_name. "
        "python -m tool_compression.clean_start evaluate --out <out> --bfcl-root <checkout> "
        "--thinking <off|on|off,on> does this registration in-process. Otherwise, from "
        "the berkeley-function-call-leaderboard checkout, run one study category "
        "and one model directory at a time. --result-dir is the directory that "
        "contains those eight model directories. Pass an absolute path when "
        "<out> is outside that checkout:\n"
        f"{commands}\n"
        "--partial-eval is required because "
        "the result file holds this study's ids, not every official id in the category. "
        "Each command scores one arm. "
        "format_sensitivity is not a scoring category and is not in this package."
    )
