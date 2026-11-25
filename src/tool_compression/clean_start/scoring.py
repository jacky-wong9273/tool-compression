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

from tool_compression.clean_start.categories import category_from_id, result_group
from tool_compression.clean_start.pin import BFCL_COMMIT, BFCL_VERSION_PREFIX, REQUEST_MODEL


def registry_dir(thinking: str) -> str:
    if thinking not in {"off", "on"}:
        raise ValueError(thinking)
    return f"deepseek-flash-thinking-{thinking}"


def result_relative(case_id: str, thinking: str) -> Path:
    category = category_from_id(case_id)
    filename = f"{BFCL_VERSION_PREFIX}_{category}_result.json"
    return Path("result") / registry_dir(thinking) / result_group(category) / filename


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


def append_result(out_dir: Path, case_id: str, thinking: str, entry: dict) -> Path:
    path = out_dir / result_relative(case_id, thinking)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        handle.flush()
    return path


def evaluate_instructions() -> str:
    return (
        "Accuracy is recovered by the official evaluator at gorilla commit "
        f"{BFCL_COMMIT}, not by a scorer in this repo. Gold files stay in that tree "
        "under bfcl_eval/data/possible_answer and are not editor inputs.\n\n"
        "Result lines are JSONL objects with id and result, under\n"
        "  <out>/result/deepseek-flash-thinking-off/<group>/BFCL_v4_<category>_result.json\n"
        "  <out>/result/deepseek-flash-thinking-on/<group>/BFCL_v4_<category>_result.json\n"
        "The API model on every request is "
        f"{REQUEST_MODEL}. The directory suffix separates the two thinking passes "
        "so memory snapshots are not shared.\n\n"
        "The pinned BFCL model list has no deepseek-flash entry. Register both "
        "directory names before evaluate, with model_name "
        f"'{REQUEST_MODEL}', is_fc_model True, and DeepSeekAPIHandler. Then, from "
        "the berkeley-function-call-leaderboard checkout:\n"
        "  bfcl evaluate --model deepseek-flash-thinking-off --test-category all_scoring "
        "--result-dir <path> --partial-eval\n"
        "Repeat for deepseek-flash-thinking-on. --partial-eval is for a pilot subset. "
        "A full run omits it only after every scoring id is present.\n"
        "format_sensitivity is not a scoring category and is not in this package."
    )
