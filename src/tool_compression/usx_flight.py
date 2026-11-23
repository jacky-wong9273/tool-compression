"""12-case U/S/X/SX systems-test flight path.

This is a formative scored pilot, not official settlement. Stage A writes a
gate and does not read an API key or call a provider. A later operator can
start the paid path only after supplying ``EXPLORATORY_CEILING_CNY``. That
amount has no default here and is never raised to make a call fit.

Peak continuation is scoped to this systems test and requires ``--authorize-peak``.
The official validation flight's off-peak stop is not in this branch and is
not changed. Spend, when a live call is later made, uses the public Flash
card for the Asia/Shanghai clock at that call. Peak spend is not the locked
off-peak validation card.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
import json
import os

from tool_compression.config import BFCL_DEFAULT_TEMPERATURE, BFCL_STORE
from tool_compression.convert import to_openai_completions_tools
from tool_compression.count import dump_request
from tool_compression.load import STUDY_CATEGORIES, load_category
from tool_compression.semantic_audit import load_json, package_dir

PURPOSE = "usx-12-systems-test"
STAGE_A = "A"
MODEL = "deepseek-flash"
MODEL_VERSION = "DeepSeek-V4.1-Flash-1017"
API_BASE_URL = "https://api.deepseek.com"
API_PATH = "/chat/completions"
API_KEY_ENV = "DEEPSEEK_API_KEY"
THINKING_DISABLED = {"type": "disabled"}
EVALUATE_ALIAS = "DeepSeek-V3.2-Exp-FC"
REFUSED_GENERATION_MODELS = frozenset({
    EVALUATE_ALIAS,
    "DeepSeek-V3.2-Exp",
    "DeepSeek-V3.2-Exp-thinking",
    "deepseek-chat",
    "deepseek-reasoner",
})
ARMS = ("U", "S", "X", "SX")
CONTRASTS = ("S-U", "X-U", "SX-S", "SX-X", "SX-U")
CEILING_ENV = "EXPLORATORY_CEILING_CNY"
PRICE_PAGE = "https://api-docs.deepseek.com/zh-cn/quick_start/pricing/"
PRICE_VERIFIED_ON = "2026-11-23"
PRICE_MODEL = "deepseek-flash"
MILLION = Decimal("1000000")
MAX_INPUT_TOKENS = 1_000_000
MAX_OUTPUT_TOKENS = 384 * 1024
SHANGHAI = ZoneInfo("Asia/Shanghai")
PEAK_WINDOWS = ((9, 0, 12, 0), (14, 0, 18, 0))
RESULT_VERSION_PREFIX = "BFCL_v4"
PEAK_AUTHORIZATION = {
    "reference": "t2524u/t2525u",
    "when": "2026-11-23T14:17:00+08:00",
    "scope": "this 12-case USX systems test only",
    "official_validation_guard_unchanged": True,
}

_RATE = {
    "off-peak": {"hit": Decimal("0.02"), "miss": Decimal("1"), "output": Decimal("4")},
    "peak": {"hit": Decimal("0.04"), "miss": Decimal("2"), "output": Decimal("8")},
}


class UsxFlightRefused(RuntimeError):
    """A closed stop. The message names the reason and carries no secret."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def accept_ceiling(value) -> Decimal:
    """Accept one positive decimal. No default, and a float is not exact."""
    if value is None or isinstance(value, bool):
        raise UsxFlightRefused(f"{CEILING_ENV} is missing")
    if isinstance(value, float):
        raise UsxFlightRefused(f"{CEILING_ENV} must be a decimal string, not a float")
    if isinstance(value, int):
        text = str(value)
    else:
        text = str(value).strip()
    if text == "":
        raise UsxFlightRefused(f"{CEILING_ENV} is empty")
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise UsxFlightRefused(f"{CEILING_ENV} is not a decimal") from exc
    if not amount.is_finite() or amount <= 0:
        raise UsxFlightRefused(f"{CEILING_ENV} must be a positive decimal")
    return amount


def read_ceiling_from_env(environ: dict | None = None) -> Decimal:
    source = os.environ if environ is None else environ
    if CEILING_ENV not in source:
        raise UsxFlightRefused(f"{CEILING_ENV} is missing")
    return accept_ceiling(source.get(CEILING_ENV))


def assert_ceiling_not_raised(supplied: Decimal, used: Decimal) -> None:
    if used > supplied:
        raise UsxFlightRefused("ceiling raised above the supplied value")


def schedule_at(moment: datetime) -> str:
    """Public Flash schedule. A weekday window is peak.

    No PRC holiday calendar is bundled. A public holiday that falls inside a
    weekday window is billed as peak, which is the higher published card.
    That is not a third price.
    """
    if moment.tzinfo is None:
        raise UsxFlightRefused("schedule clock must be timezone-aware")
    local = moment.astimezone(SHANGHAI)
    if local.weekday() > 4:
        return "off-peak"
    minute = local.hour * 60 + local.minute
    for start_h, start_m, end_h, end_m in PEAK_WINDOWS:
        if start_h * 60 + start_m <= minute < end_h * 60 + end_m:
            return "peak"
    return "off-peak"


def rate_card(schedule: str) -> dict:
    if schedule not in _RATE:
        raise UsxFlightRefused(f"unknown schedule {schedule}")
    rates = _RATE[schedule]
    return {
        "model": PRICE_MODEL,
        "schedule": schedule,
        "currency": "CNY",
        "per": "million tokens",
        "cache_hit": format(rates["hit"], "f"),
        "cache_miss": format(rates["miss"], "f"),
        "output": format(rates["output"], "f"),
        "source": PRICE_PAGE,
        "verified_on": PRICE_VERIFIED_ON,
        "locked_offpeak_validation_card": False,
        "holiday_calendar": "not_applied",
        "weekday_holiday_inside_window_billed_as": "peak",
    }


def spend_cny(schedule: str, total_input: int, cache_hit: int, output: int) -> Decimal:
    """Bill the schedule's card. ``total_input`` is the billed-basis T."""
    _tokens(total_input, "input")
    _tokens(cache_hit, "cache_hit")
    _tokens(output, "output")
    if cache_hit > total_input:
        raise UsxFlightRefused("cache hit exceeds billed input")
    rates = _RATE[schedule]
    miss = total_input - cache_hit
    return (
        Decimal(cache_hit) * rates["hit"]
        + Decimal(miss) * rates["miss"]
        + Decimal(output) * rates["output"]
    ) / MILLION


def pre_call_reserve_cny(schedule: str) -> Decimal:
    """Worst case for one call: the whole input at the miss rate, plus max output."""
    return spend_cny(schedule, MAX_INPUT_TOKENS, 0, MAX_OUTPUT_TOKENS)


def remaining_allows_call(spent: Decimal, ceiling: Decimal, reserve: Decimal) -> bool:
    assert_ceiling_not_raised(ceiling, ceiling)
    return spent + reserve <= ceiling


def billed_basis_t(prompt_tokens: int) -> dict:
    """T is provider ``prompt_tokens``. Cache hits stay inside T. Prices do not."""
    _tokens(prompt_tokens, "prompt_tokens")
    return {
        "T": prompt_tokens,
        "field": "prompt_tokens",
        "cache_hits_subtracted": False,
        "prices_applied": False,
    }


def usage_bill(schedule: str, usage: dict) -> dict:
    """Bill one response. A missing cache split is billed entirely at the miss rate."""
    if not isinstance(usage, dict) or "prompt_tokens" not in usage or "completion_tokens" not in usage:
        raise UsxFlightRefused("provider usage is missing prompt_tokens or completion_tokens")
    prompt = _tokens(usage.get("prompt_tokens"), "prompt_tokens")
    output = _tokens(usage.get("completion_tokens"), "completion_tokens")
    hit = usage.get("prompt_cache_hit_tokens")
    miss = usage.get("prompt_cache_miss_tokens")
    anomaly = False
    if isinstance(hit, bool) or isinstance(miss, bool):
        anomaly = True
        hit_n, miss_n = 0, prompt
    elif isinstance(hit, int) and isinstance(miss, int) and hit + miss == prompt and hit >= 0 and miss >= 0:
        hit_n, miss_n = hit, miss
    else:
        anomaly = True
        hit_n, miss_n = 0, prompt
    amount = spend_cny(schedule, prompt, hit_n, output)
    basis = billed_basis_t(prompt)
    return {
        "schedule": schedule,
        "T": basis["T"],
        "cache_hit_tokens": hit_n,
        "cache_miss_tokens_billed": prompt - hit_n,
        "output_tokens": output,
        "spend_cny": format(amount, "f"),
        "provider_cache_miss_tokens": None if anomaly else miss_n,
        "cache_split_missing_billed_as_miss": anomaly,
        "cache_hits_subtracted_from_T": False,
        "prices_applied_to_T": False,
        "locked_offpeak_validation_card": False,
    }


def generation_body(messages: list, tools: list) -> dict:
    if MODEL in REFUSED_GENERATION_MODELS or MODEL != "deepseek-flash":
        raise UsxFlightRefused("generation model is not deepseek-flash")
    body = {
        "model": MODEL,
        "messages": deepcopy(messages),
        "temperature": BFCL_DEFAULT_TEMPERATURE,
        "store": BFCL_STORE,
        "thinking": dict(THINKING_DISABLED),
    }
    if tools:
        body["tools"] = deepcopy(tools)
    assert_generation_body(body)
    return body


def assert_generation_body(body: dict) -> None:
    if body.get("model") != MODEL or body.get("model") in REFUSED_GENERATION_MODELS:
        raise UsxFlightRefused("refusing a generation body that is not deepseek-flash")
    if body.get("thinking") != THINKING_DISABLED:
        raise UsxFlightRefused("refusing a generation body that does not disable thinking")
    if "reasoning_effort" in body:
        raise UsxFlightRefused("refusing a generation body that sets reasoning_effort")
    if body.get("temperature") != BFCL_DEFAULT_TEMPERATURE or body.get("store") is not False:
        raise UsxFlightRefused("refusing a generation body that drops temperature 0.001 or store false")


def request_sha256(body: dict) -> str:
    return hashlib.sha256(dump_request(body).encode("utf-8")).hexdigest()


def evaluate_argv(categories: list[str], result_dir: Path, score_dir: Path) -> list[str]:
    if list(categories) != list(STUDY_CATEGORIES):
        raise UsxFlightRefused("evaluate categories must be the three categories this systems test flies")
    flown = list(STUDY_CATEGORIES)
    argv = [
        "python",
        "-m",
        "bfcl_eval",
        "evaluate",
        "--model",
        EVALUATE_ALIAS,
        "--test-category",
        ",".join(flown),
        "--result-dir",
        str(result_dir),
        "--score-dir",
        str(score_dir),
        "--partial-eval",
    ]
    assert_evaluate_argv(argv)
    return argv


def assert_evaluate_argv(argv: list[str]) -> None:
    text = " ".join(argv)
    if "generate" in argv or "openfunctions_evaluation" in text:
        raise UsxFlightRefused("evaluate argv must not generate")
    if "--partial-eval" not in argv:
        raise UsxFlightRefused("a 12-case subset needs --partial-eval")
    if EVALUATE_ALIAS not in argv:
        raise UsxFlightRefused("evaluate argv is missing the scoring alias")
    if MODEL in argv:
        raise UsxFlightRefused("the generation model is not the evaluate --model alias")


def classify_multiple(valid: bool, error_type: str | None) -> str:
    """Official full-call label, split when the name is wrong and when it is right."""
    if valid:
        return "correct"
    kind = error_type or ""
    if kind == "simple_function_checker:wrong_func_name":
        return "wrong_name"
    if kind == "multiple_function_checker:wrong_count":
        return "wrong_call_shape"
    if kind.startswith("ast_decoder:"):
        return "parse_failure"
    argument_markers = (
        "simple_function_checker:missing_required",
        "simple_function_checker:unexpected_param",
        "simple_function_checker:missing_optional",
        "type_error:",
        "value_error:",
        "dict_checker:",
        "list_dict_checker:",
        "parallel_function_checker_no_order:",
    )
    if any(marker in kind for marker in argument_markers):
        return "right_name_wrong_args"
    return "other"


def classify_irrelevance(*, decode_failed: bool, contained_function_call: bool) -> dict:
    """A decode failure is not abstention and is not a correct irrelevance call.

    The pinned official runner scores a decode failure as success because no
    function call was decoded. This report keeps that raw flag separate and
    does not count it as abstention.
    """
    if decode_failed:
        return {
            "label": "parse_failure",
            "abstention": False,
            "correct": False,
            "official_runner_would_count_success": True,
        }
    if contained_function_call:
        return {
            "label": "called_tool",
            "abstention": False,
            "correct": False,
            "official_runner_would_count_success": False,
        }
    return {
        "label": "abstention",
        "abstention": True,
        "correct": True,
        "official_runner_would_count_success": True,
    }


def shorter_request_is_not_a_call(label: str, prompt_tokens: int) -> str:
    """Prompt length does not change a quality label."""
    _tokens(prompt_tokens, "prompt_tokens")
    return label


def quality_plan() -> dict:
    return {
        "official_settlement": False,
        "matched_length_comparison": False,
        "resets_official_10_percent_target": False,
        "shorter_request_counts_as_correct": False,
        "quality": "official full-call accuracy on the saved outputs",
        "multiple_split": ["wrong_name", "right_name_wrong_args"],
        "irrelevance_parse_failure_is_abstention": False,
        "contrasts": list(CONTRASTS),
        "contrast_values": {name: None for name in CONTRASTS},
        "scores": None,
    }


def build_plans(bfcl_root: Path) -> list[dict]:
    """One plan per selected case. Identical bodies inside the case share one call."""
    root = package_dir()
    manifest = load_json(root / "selection" / "manifest.json")
    by_category: dict[str, dict] = {}
    for category in STUDY_CATEGORIES:
        _, records = load_category(bfcl_root, category)
        by_category[category] = {record["id"]: record for record in records}
    plans = []
    for item in manifest["selected"]:
        case_id = item["case_id"]
        category = item["category"]
        record = by_category[category].get(case_id)
        if record is None:
            raise UsxFlightRefused(f"selected case {case_id} is missing from the pinned questions")
        tools = _arm_tools(root, case_id, record)
        messages = record["question"][0]
        groups: dict[str, dict] = {}
        for arm in ARMS:
            body = generation_body(messages, tools[arm])
            digest = request_sha256(body)
            group = groups.get(digest)
            if group is None:
                groups[digest] = {"request_sha256": digest, "arms": [arm], "body": body}
            else:
                group["arms"].append(arm)
        plans.append({
            "case_id": case_id,
            "category": category,
            "groups": [
                {"request_sha256": group["request_sha256"], "arms": group["arms"]}
                for group in groups.values()
            ],
            "_bodies": {group["request_sha256"]: group["body"] for group in groups.values()},
        })
    return plans


def run_no_api_gate(bfcl_root: Path, out: Path, ceiling: Decimal, clock) -> dict:
    """Stage A. Writes the gate. Does not read a key, open a socket, or score."""
    plans = build_plans(bfcl_root)
    moment = clock()
    schedule = schedule_at(moment)
    reserve = pre_call_reserve_cny(schedule)
    unique = sum(len(plan["groups"]) for plan in plans)
    gate = {
        "purpose": PURPOSE,
        "stage": STAGE_A,
        "official_settlement": False,
        "official_scores_closed": True,
        "target_10_percent_unchanged": True,
        "no_api": True,
        "live": False,
        "provider_called": False,
        "api_key_read": False,
        "spend_cny": "0",
        "ceiling_env": CEILING_ENV,
        "ceiling_cny": format(ceiling, "f"),
        "ceiling_hardcoded": False,
        "ceiling_lifted": False,
        "ceiling_authorizes_spend_by_itself": False,
        "ceiling_note": "The value is whatever this process was given in the environment. It is not a default, and it does not authorize a later process to spend.",
        "model": MODEL,
        "model_version": MODEL_VERSION,
        "thinking": dict(THINKING_DISABLED),
        "temperature": BFCL_DEFAULT_TEMPERATURE,
        "store": BFCL_STORE,
        "scoring_alias": EVALUATE_ALIAS,
        "scoring_alias_is_generation_model": False,
        "arms": list(ARMS),
        "u_source": "fresh conversion of the pinned BFCL record, checked equal to the frozen rendered U",
        "u_backfill": False,
        "s_source": "frozen first-pilot rendered S",
        "x_source": "cue-revision rendered X",
        "sx_source": "cue-revision rendered SX",
        "cases": len(plans),
        "unique_payloads": unique,
        "shared_within_case_only": True,
        "cells": [_public_cell(plan) for plan in plans],
        "peak_authorization": {
            **PEAK_AUTHORIZATION,
            "flag": "--authorize-peak",
            "required_for_live": True,
            "dry_run_called_provider": False,
        },
        "clock": moment.isoformat(),
        "schedule_at_gate": schedule,
        "rate_card": rate_card(schedule),
        "pre_call_reserve_cny": format(reserve, "f"),
        "reserve_fits_supplied_ceiling": remaining_allows_call(Decimal("0"), ceiling, reserve),
        "stopped_for_peak": False,
        "live_would_start": False,
        "evaluate": {
            "argv_by_arm": {
                arm: evaluate_argv(list(STUDY_CATEGORIES), Path("result") / arm, Path("score") / arm)
                for arm in ARMS
            },
            "partial_eval": True,
            "categories": list(STUDY_CATEGORIES),
            "why_partial": "The pinned full evaluate refuses a model-result file shorter than the category. Pass --partial-eval for the categories actually flown.",
            "result_layout": "result/<arm>/DeepSeek-V3.2-Exp-FC/BFCL_v4_<category>_result.json",
            "ran": False,
        },
        "billed_basis_T": billed_basis_t(0) | {"T": None, "note": "T is recorded per live call from prompt_tokens. The gate has no call."},
        "quality": quality_plan(),
    }
    if gate["provider_called"] or gate["api_key_read"] or Decimal(gate["spend_cny"]) != 0:
        raise UsxFlightRefused("no-api gate recorded a call or a spend")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "gate.json").write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")
    return gate


def run_live(bfcl_root: Path, out: Path, ceiling: Decimal, clock, client, authorize_peak: bool) -> dict:
    """Paid path. The CLI constructs ``client`` only after these stops pass.

    This function is not the Stage A gate. Tests pass a scripted client.
    """
    if not authorize_peak:
        raise UsxFlightRefused("peak continuation requires --authorize-peak for this systems test")
    plans = build_plans(bfcl_root)
    spent = Decimal("0")
    calls = []
    out = Path(out)
    result_root = out / "result"
    for plan in plans:
        for group in plan["groups"]:
            moment = clock()
            schedule = schedule_at(moment)
            reserve = pre_call_reserve_cny(schedule)
            if not remaining_allows_call(spent, ceiling, reserve):
                _write_live_stop(out, spent, schedule, reserve, ceiling, calls, "pre-call reserve would pass the supplied ceiling")
                raise UsxFlightRefused("pre-call reserve would pass the supplied ceiling")
            if client is None:
                client = build_live_client()
            body = plan["_bodies"][group["request_sha256"]]
            assert_generation_body(body)
            payload = client.complete(body)
            bill = usage_bill(schedule, payload.get("usage") if isinstance(payload, dict) else None)
            spent += Decimal(bill["spend_cny"])
            observation = {
                "case_id": plan["case_id"],
                "arms": list(group["arms"]),
                "request_sha256": group["request_sha256"],
                "schedule": schedule,
                "rate_card": rate_card(schedule),
                "clock": moment.isoformat(),
                "bill": bill,
                "provider_called": True,
            }
            calls.append(observation)
            if spent > ceiling:
                _write_live_stop(out, spent, schedule, reserve, ceiling, calls, "settled spend passed the supplied ceiling")
                raise UsxFlightRefused("settled spend passed the supplied ceiling")
            if not _thinking_stayed_off(payload):
                _write_live_stop(out, spent, schedule, reserve, ceiling, calls, "provider response included thinking")
                raise UsxFlightRefused("provider response included thinking")
            for arm in group["arms"]:
                _append_result(result_root, arm, plan["category"], plan["case_id"], payload, bill)
    record = {
        "purpose": PURPOSE,
        "official_settlement": False,
        "live": True,
        "provider_called": True,
        "spend_cny": format(spent, "f"),
        "ceiling_cny": format(ceiling, "f"),
        "calls": calls,
        "quality": quality_plan(),
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "live.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def _write_live_stop(out: Path, spent: Decimal, schedule: str, reserve: Decimal, ceiling: Decimal, calls: list, reason: str) -> None:
    out.mkdir(parents=True, exist_ok=True)
    record = {
        "purpose": PURPOSE,
        "official_settlement": False,
        "provider_called": bool(calls),
        "api_key_in_record": False,
        "spend_cny": format(spent, "f"),
        "stop_reason": reason,
        "schedule": schedule,
        "pre_call_reserve_cny": format(reserve, "f"),
        "ceiling_cny": format(ceiling, "f"),
        "ceiling_lifted": False,
    }
    (out / "stop.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def _arm_tools(root: Path, case_id: str, record: dict) -> dict[str, list]:
    frozen_u = load_json(root / "rendered" / case_id / "U.json")["tools"]
    fresh_u = to_openai_completions_tools(record["function"])
    if fresh_u != frozen_u:
        raise UsxFlightRefused(f"fresh U for {case_id} does not match the frozen rendered U")
    frozen_s = load_json(root / "rendered" / case_id / "S.json")["tools"]
    revised_x = load_json(root / "cue-revision" / "rendered" / case_id / "X.json")["tools"]
    revised_sx = load_json(root / "cue-revision" / "rendered" / case_id / "SX.json")["tools"]
    copied_u = load_json(root / "cue-revision" / "rendered" / case_id / "U.json")["tools"]
    copied_s = load_json(root / "cue-revision" / "rendered" / case_id / "S.json")["tools"]
    if copied_u != frozen_u or copied_s != frozen_s:
        raise UsxFlightRefused(f"cue-revision U/S copy for {case_id} is not the frozen rendering")
    return {"U": fresh_u, "S": frozen_s, "X": revised_x, "SX": revised_sx}


def _public_cell(plan: dict) -> dict:
    return {
        "case_id": plan["case_id"],
        "category": plan["category"],
        "groups": [
            {
                "request_sha256": group["request_sha256"],
                "arms": list(group["arms"]),
                "shared": len(group["arms"]) > 1,
            }
            for group in plan["groups"]
        ],
    }


def _append_result(result_root: Path, arm: str, category: str, case_id: str, payload: dict, bill: dict) -> None:
    directory = result_root / arm / EVALUATE_ALIAS
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{RESULT_VERSION_PREFIX}_{category}_result.json"
    row = {
        "id": case_id,
        "result": _fc_result(payload),
        "input_token_count": bill["T"],
        "output_token_count": bill["output_tokens"],
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _fc_result(payload: dict):
    message = {}
    try:
        message = payload["choices"][0]["message"]
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            raise ValueError("no tool calls")
        return [{call["function"]["name"]: call["function"]["arguments"]} for call in tool_calls]
    except (KeyError, TypeError, ValueError, IndexError):
        if isinstance(message, dict):
            return message.get("content")
        return None


def _thinking_stayed_off(payload: dict) -> bool:
    if not isinstance(payload, dict):
        return False
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return False
    message = choices[0].get("message")
    if not isinstance(message, dict):
        return False
    for key in ("reasoning_content", "thinking"):
        value = message.get(key)
        if isinstance(value, str) and value.strip():
            return False
        if isinstance(value, (list, dict)) and value:
            return False
    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    details = usage.get("completion_tokens_details") if isinstance(usage.get("completion_tokens_details"), dict) else {}
    reasoning = details.get("reasoning_tokens")
    if isinstance(reasoning, int) and not isinstance(reasoning, bool) and reasoning > 0:
        return False
    return True


def _tokens(value, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise UsxFlightRefused(f"{label} must be a non-negative integer")
    return value


def build_live_client():
    """Read the key and return a client. Stage A never calls this."""
    from tool_compression.usx_provider import LiveClient, require_api_key

    return LiveClient(require_api_key())
