"""Later live path for a flyable H50 or H25 flight.

Importing this module does not read an API key, open a socket, or start a
flight. The operator starts a live run with ``--live`` and a ceiling. U, E,
and official L are not sent. Generation under ``DeepSeek-V3.2-Exp-FC`` is
refused. Scoring is the pinned BFCL evaluate-from-saved-outputs command.
"""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import json
import subprocess
import time

from tool_compression.config import DEFAULT_CONFIG
from tool_compression.compress import compress
from tool_compression.exploratory import (
    ARM_NAMES,
    EVALUATE_DECODER_ALIAS,
    EXPLORATORY_LABELS,
    GENERATION_MODEL,
    GENERATION_MODEL_VERSION,
    NOT_REFLOWN,
    ExploratoryFlightRefused,
    accept_ceiling,
    assert_ceiling_not_raised,
    assert_evaluate_command,
    assert_flight_members,
    assert_generation_body,
    billed_basis_t,
    classify_case,
    flight_groups,
    frozen_config,
    official_evaluate_argv,
    refuse_generation_alias,
)
from tool_compression.flight_spec import (
    API_BASE_URL,
    format_cny,
    is_peak,
    pre_call_reserve_cny,
    rate_card,
)
from tool_compression.load import VERSION_PREFIX
from tool_compression.prepare import assemble_request, convert_record, request_hash
from tool_compression.provider import (
    flight_request,
    parse_fc_response,
    response_thinking_disabled,
    scrub,
)
from tool_compression.provider import ProviderError
from tool_compression.runner import FlightAccount
from tool_compression.usage import usage_from_mapping

CATEGORIES = ("multiple", "simple_python", "irrelevance")


def exploratory_record(label: str, ceiling: Decimal) -> dict:
    """Frozen record. The ceiling is the value the caller just supplied."""
    if label not in EXPLORATORY_LABELS:
        raise ExploratoryFlightRefused("unknown exploratory setting")
    amount = accept_ceiling(ceiling)
    config = frozen_config(label)
    return {
        "purpose": "exploratory-retention",
        "official_settlement": False,
        "official_accuracy": False,
        "official_target_lowered": False,
        "official_result_retuned": False,
        "model": GENERATION_MODEL,
        "model_version": GENERATION_MODEL_VERSION,
        "handler_alias": None,
        "generation_refused_aliases": [
            "DeepSeek-V3.2-Exp",
            "DeepSeek-V3.2-Exp-FC",
            "DeepSeek-V3.2-Exp-thinking",
            "deepseek-chat",
            "deepseek-reasoner",
        ],
        "thinking": {"type": "disabled", "pinned_before_any_call": True},
        "provider_options": {"temperature": 0.001, "store": False, "thinking": {"type": "disabled"}},
        "rate_card": rate_card(),
        "spending_ceiling": {
            "amount": format_cny(amount),
            "currency": "CNY",
            "hard": True,
            "do_not_lift": True,
            "supplied_at_runtime": True,
            "hardcoded": False,
        },
        "billed_basis": "provider_prompt_tokens",
        "price_weighted_substitute_for_T": False,
        "setting": label,
        "settings": config.as_dict(),
        "not_reflown": list(NOT_REFLOWN),
        "api_base_url": API_BASE_URL,
        "api_key_in_repository": False,
        "frozen": True,
        "started_by_import": False,
    }


def assert_exploratory_record(record: dict, ceiling: Decimal, label: str) -> None:
    if not isinstance(record, dict):
        raise ExploratoryFlightRefused("execution record is missing")
    if record.get("setting") != label or label not in EXPLORATORY_LABELS:
        raise ExploratoryFlightRefused("execution record setting is not H50 or H25")
    if record.get("purpose") != "exploratory-retention":
        raise ExploratoryFlightRefused("this path is the exploratory retention flight")
    if record.get("official_settlement") is not False or record.get("official_accuracy") is not False:
        raise ExploratoryFlightRefused("this flight does not settle the official result")
    if record.get("official_target_lowered") is not False or record.get("official_result_retuned") is not False:
        raise ExploratoryFlightRefused("the official target is not lowered")
    recorded = accept_ceiling(record.get("spending_ceiling", {}).get("amount"))
    assert_ceiling_not_raised(accept_ceiling(ceiling), recorded)
    ceiling_record = record.get("spending_ceiling") or {}
    if ceiling_record.get("do_not_lift") is not True or ceiling_record.get("hard") is not True:
        raise ExploratoryFlightRefused("ceiling must not be lifted")
    if ceiling_record.get("hardcoded") is not False or ceiling_record.get("supplied_at_runtime") is not True:
        raise ExploratoryFlightRefused("ceiling must be supplied at run time")
    refuse_generation_alias(str(record.get("model")))
    if record.get("model") != GENERATION_MODEL or record.get("model_version") != GENERATION_MODEL_VERSION:
        raise ExploratoryFlightRefused("generation model must be thinking-off deepseek-flash")
    if record.get("handler_alias"):
        refuse_generation_alias(str(record.get("handler_alias")))
    thinking = record.get("thinking") or {}
    options = record.get("provider_options") or {}
    if thinking.get("type") != "disabled" or options.get("thinking") != {"type": "disabled"}:
        raise ExploratoryFlightRefused("thinking must be disabled")
    if record.get("rate_card") != rate_card():
        raise ExploratoryFlightRefused("rate card is not the locked off-peak card")
    if record.get("settings") != frozen_config(label).as_dict():
        raise ExploratoryFlightRefused("settings are not the frozen exploratory config")
    if record.get("billed_basis") != "provider_prompt_tokens" or record.get("price_weighted_substitute_for_T") is not False:
        raise ExploratoryFlightRefused("T is provider prompt_tokens")
    for name in NOT_REFLOWN:
        if name not in (record.get("not_reflown") or []):
            raise ExploratoryFlightRefused("U, E, and official L are not re-flown")
    if record.get("api_key_in_repository") is not False:
        raise ExploratoryFlightRefused("refusing a record that stores an API key")


def build_flight_plans(study: dict, label: str, counter) -> tuple[list[dict], dict]:
    """Compress with the frozen config. Keep only requests that differ from U and official L."""
    frozen_config(label)
    plans = []
    failures = []
    identical_u = []
    identical_l = []
    coincide = []
    new_cases = 0
    cases = 0
    for category in CATEGORIES:
        for record in study[category]:
            cases += 1
            try:
                messages = record["question"][0]
                if not isinstance(messages, list):
                    raise TypeError("question turn is not a message list")
                catalogue = convert_record(record)
            except Exception:
                failures.append({"category": category, "id": record.get("id"), "reason": "preparation_failure"})
                continue
            hashes, catalogues = _compress_hashes(catalogue, messages, frozen_config(label), counter)
            official = {}
            for method in ARM_NAMES:
                produced = compress(catalogue, method, DEFAULT_CONFIG, counter)["catalogue"]
                official[method] = request_hash(assemble_request(messages, produced))
            classified = classify_case(hashes, {"U": hashes["U"], **official})
            identical_u.append(classified["identical_to_u"])
            identical_l.append(classified["identical_to_official_l"])
            coincide.append(classified["p_i_c_coincide"])
            groups = flight_groups(label, hashes, classified["official_l_hash"])
            if groups:
                new_cases += 1
            for members in groups:
                source = "P" if members == (label,) else members[0]
                body = flight_request(messages, catalogues[source])
                assert_generation_body(body)
                assert_flight_members(members)
                digest = request_hash(body)
                plans.append(
                    {
                        "category": category,
                        "case_id": str(record["id"]),
                        "replicate": 0,
                        "members": members,
                        "response_group_id": f"exploratory/{label}/{category}/{record['id']}/r0/{digest}",
                        "request_sha256": digest,
                        "body": body,
                    }
                )
    stats = {
        "cases": cases,
        "preparation_failures": failures,
        "cases_with_new_request": new_cases,
        "identical_to_u": bool(identical_u) and all(identical_u) and not failures,
        "identical_to_official_l": bool(identical_l) and all(identical_l) and not failures,
        "p_i_c_coincide": bool(coincide) and all(coincide) and not failures,
        "groups": len(plans),
    }
    return plans, stats


def prepare_exploratory_flight(study, label: str, ceiling: Decimal, audit_setting: dict, out: Path, counter) -> tuple[dict, list[dict]]:
    """Write the plan and the evaluate command. Do not construct a provider client."""
    if not isinstance(audit_setting, dict) or audit_setting.get("flyable") is not True:
        reason = audit_setting.get("flyable_reason") if isinstance(audit_setting, dict) else "missing"
        raise ExploratoryFlightRefused("setting is not flyable: " + str(reason))
    if audit_setting.get("label") != label:
        raise ExploratoryFlightRefused("audit setting does not match the requested flight")
    if audit_setting.get("provider_called") is not False or audit_setting.get("network_used") is not False:
        raise ExploratoryFlightRefused("refusing an audit that claims a provider call")
    record = exploratory_record(label, ceiling)
    assert_exploratory_record(record, ceiling, label)
    plans, stats = build_flight_plans(study, label, counter)
    if stats["preparation_failures"]:
        raise ExploratoryFlightRefused("preparation failed for " + str(len(stats["preparation_failures"])) + " cases")
    if stats["cases_with_new_request"] != audit_setting.get("cases_with_new_request"):
        raise ExploratoryFlightRefused("audit does not match a fresh compression")
    if stats["identical_to_u"] != audit_setting.get("identical_to_u"):
        raise ExploratoryFlightRefused("audit identity versus U does not match a fresh compression")
    if stats["identical_to_official_l"] != audit_setting.get("identical_to_official_l"):
        raise ExploratoryFlightRefused("audit identity versus official L does not match a fresh compression")
    if not plans:
        raise ExploratoryFlightRefused("no request differs from U and official L")
    summary = _base_summary(record, ceiling, label)
    summary.update(
        {
            "started": False,
            "provider_called": False,
            "network_used": False,
            "stop_reason": "not_started",
            "groups_planned": len(plans),
            "cases_with_new_request": stats["cases_with_new_request"],
            "p_i_c_coincide": stats["p_i_c_coincide"],
            "reporting_label": label if stats["p_i_c_coincide"] else None,
            "arms_separate": not stats["p_i_c_coincide"],
            "identical_to_u": stats["identical_to_u"],
            "identical_to_official_l": stats["identical_to_official_l"],
        }
    )
    _write_plan(out, record, summary, plans)
    return summary, plans


def execute_exploratory_flight(
    record: dict,
    plans: list[dict],
    ceiling: Decimal,
    out: Path,
    *,
    client,
    live: bool,
    clock=None,
    sleep=None,
) -> dict:
    """Send the planned requests. A non-live client is not a provider call."""
    label = record["setting"]
    assert_exploratory_record(record, ceiling, label)
    if not plans:
        raise ExploratoryFlightRefused("no request differs from U and official L")
    client_type = _deepseek_client_type()
    if live and not isinstance(client, client_type):
        raise ExploratoryFlightRefused("live flight requires the DeepSeek client")
    if not live and isinstance(client, client_type):
        raise ExploratoryFlightRefused("refusing the live client when the flight is not live")
    for plan in plans:
        plan.setdefault("protocol_shared_response_id", plan["response_group_id"])
        assert_flight_members(plan["members"])
        assert_generation_body(plan["body"])
        if any(name in NOT_REFLOWN for name in plan["members"]):
            raise ExploratoryFlightRefused("U, E, and official L are not re-flown")
    clock = clock or (lambda: datetime.now(timezone.utc))
    sleep = sleep or time.sleep
    account = FlightAccount(ceiling, pre_call_reserve_cny())
    assert_ceiling_not_raised(ceiling, account.ceiling)
    summary = _base_summary(record, ceiling, label)
    summary["official_evaluate"] = _evaluate_block(out)
    summary.update(
        {
            "started": True,
            "live": bool(live),
            "provider_called": False,
            "network_used": False,
            "groups_planned": len(plans),
            "stop_reason": None,
        }
    )
    rows = {name: [] for name in CATEGORIES}
    request_lines = []
    provider_called = False
    policy = _runtime_failure_policy(ceiling)
    stop = None
    for plan in plans:
        retries = 0
        while True:
            assert_ceiling_not_raised(ceiling, account.ceiling)
            assert_generation_body(plan["body"])
            if is_peak(clock()):
                stop = "peak_hours"
                break
            if not account.allows():
                stop = "remaining_budget_may_be_insufficient"
                break
            try:
                if live:
                    provider_called = True
                payload = client.complete(plan["body"])
            except ProviderError as exc:
                account.add_failure(plan, exc)
                if exc.kind in {"auth", "payment"}:
                    stop = exc.kind
                    break
                if exc.kind == "transient" and retries < policy["max_retries"]:
                    sleep(policy["backoff_seconds"][retries])
                    retries += 1
                    continue
                stop = "transient_exhausted" if exc.kind == "transient" else "request_error"
                break
            usage = usage_from_mapping(payload)
            billed = billed_basis_t(payload)
            if billed["price_weighted"] or billed["cache_subtracted"] or billed["T"] != usage.total_input_tokens:
                raise RuntimeError("billed basis drifted away from prompt_tokens")
            if billed["basis"] != "provider_prompt_tokens":
                raise RuntimeError("billed basis drifted away from prompt_tokens")
            thinking_ok = response_thinking_disabled(payload)
            code = account.add_received(plan, payload, usage, thinking_ok)
            request_lines.append(
                {
                    "response_group_id": plan["response_group_id"],
                    "members": list(plan["members"]),
                    "request_sha256": plan["request_sha256"],
                    "category": plan["category"],
                    "case_id": plan["case_id"],
                }
            )
            if code is None and billed["T"] is not None and thinking_ok:
                parsed = parse_fc_response(payload)
                rows[plan["category"]].append(
                    {
                        "id": plan["case_id"],
                        "result": parsed.get("model_responses"),
                        "input_token_count": billed["T"],
                        "output_token_count": usage.output_tokens,
                    }
                )
            if code:
                stop = code
                break
            break
        if stop:
            break
    summary["provider_called"] = provider_called
    summary["network_used"] = provider_called
    summary["stop_reason"] = stop
    summary["groups_completed"] = len(account.logical)
    summary["physical_attempts"] = len(account.attempts)
    summary["cumulative_cny"] = format_cny(account.spent)
    summary["ceiling_cny"] = format_cny(ceiling)
    received = [row["input_tokens"] for row in account.attempts if row["status"] == "received"]
    summary["billed_basis_T_prompt_tokens"] = None if any(item is None for item in received) else sum(received)
    summary["billed_basis_note"] = "Sum of provider prompt_tokens on received calls. Not a price-weighted token count."
    summary["ok"] = stop is None and summary["groups_completed"] == len(plans)
    _write_execution(out, record, summary, request_lines, rows, account, provider_called)
    return summary


def live_client(record: dict):
    """Construct the DeepSeek client. Callers must already have decided to go live."""
    refuse_generation_alias(str(record.get("model")))
    if record.get("handler_alias"):
        refuse_generation_alias(str(record.get("handler_alias")))
    from tool_compression.provider import DeepSeekClient, UrllibChatTransport, require_api_key

    return DeepSeekClient(require_api_key(), UrllibChatTransport(), record["api_base_url"])


def score_live_outputs(summary: dict, bfcl_root: Path, out: Path) -> dict:
    """Score a finished live flight. A plan or a dry executor cannot start this."""
    if not summary.get("provider_called"):
        raise ExploratoryFlightRefused("refusing to score a run that did not call the provider")
    scored = invoke_official_evaluate(bfcl_root, Path(out) / "bfcl_result", Path(out) / "bfcl_score")
    summary["official_evaluate"] = scored
    _write_json(Path(out) / "flight_summary.json", summary)
    _write_json(Path(out) / "official_evaluate_command.json", scored)
    return summary


def invoke_official_evaluate(bfcl_root: Path, result_dir: Path, score_dir: Path) -> dict:
    """Run ``bfcl evaluate`` on saved outputs. Refuses a generate command."""
    argv = official_evaluate_argv(result_dir, score_dir)
    assert_evaluate_command(argv)
    package = _bfcl_package(bfcl_root)
    completed = subprocess.run(argv, cwd=package, check=False)
    return {
        "argv": argv,
        "invoked": True,
        "returncode": completed.returncode,
        "command": "evaluate",
        "generate": False,
    }


def _compress_hashes(catalogue, messages, config, counter):
    hashes = {}
    catalogues = {}
    for method in ("U", *ARM_NAMES):
        produced = compress(catalogue, method, config, counter)["catalogue"]
        catalogues[method] = produced
        hashes[method] = request_hash(assemble_request(messages, produced))
    return hashes, catalogues


def _base_summary(record: dict, ceiling: Decimal, label: str) -> dict:
    result_dir = None
    return {
        "purpose": "exploratory-retention",
        "setting": label,
        "model": GENERATION_MODEL,
        "model_version": GENERATION_MODEL_VERSION,
        "thinking": "disabled",
        "handler_alias": None,
        "generation_refused_aliases": record["generation_refused_aliases"],
        "not_reflown": list(NOT_REFLOWN),
        "rate_card": rate_card(),
        "ceiling_cny": format_cny(ceiling),
        "ceiling_hardcoded": False,
        "ceiling_raised": False,
        "billed_basis": "provider_prompt_tokens",
        "price_weighted_substitute_for_T": False,
        "official_target_lowered": False,
        "official_result_retuned": False,
        "official_settlement": False,
        "u_e_official_l_reflown": False,
        "pre_call_reserve_cny": format_cny(pre_call_reserve_cny()),
        "official_evaluate": _evaluate_block(result_dir),
    }


def _evaluate_block(out: Path | None) -> dict:
    result_dir = Path("bfcl_result") if out is None else Path(out) / "bfcl_result"
    score_dir = Path("bfcl_score") if out is None else Path(out) / "bfcl_score"
    argv = official_evaluate_argv(result_dir, score_dir)
    return {
        "argv": argv,
        "invoked": False,
        "command": "evaluate",
        "generate": False,
        "decoder_alias": EVALUATE_DECODER_ALIAS,
        "decoder_is_not_the_generation_model": True,
        "generation_model": GENERATION_MODEL,
        "note": (
            "bfcl evaluate reads saved outputs. The decoder alias is the pinned "
            "BFCL function-calling handler. Generation under that alias is refused."
        ),
    }


def _write_plan(out: Path, record: dict, summary: dict, plans: list[dict]) -> None:
    out = Path(out)
    result_dir = out / "bfcl_result"
    score_dir = out / "bfcl_score"
    summary["official_evaluate"] = _evaluate_block(out)
    summary["official_evaluate"]["result_dir"] = str(result_dir)
    summary["official_evaluate"]["score_dir"] = str(score_dir)
    _write_json(out / "execution_record.json", record)
    _write_json(out / "flight_summary.json", summary)
    _write_json(out / "official_evaluate_command.json", summary["official_evaluate"])
    index = [
        {
            "category": plan["category"],
            "case_id": plan["case_id"],
            "members": list(plan["members"]),
            "request_sha256": plan["request_sha256"],
        }
        for plan in plans
    ]
    _write_jsonl(out / "plan_index.jsonl", index)
    _write_text(
        out / "official_evaluate" / "README.txt",
        "Score saved outputs with bfcl evaluate. Do not run bfcl generate.\n"
        "Generation under DeepSeek-V3.2-Exp-FC is refused.\n"
        "The generation model is deepseek-flash with thinking disabled.\n",
    )


def _write_execution(out, record, summary, request_lines, rows, account, provider_called) -> None:
    out = Path(out)
    summary["official_evaluate"] = _evaluate_block(out)
    summary["official_evaluate"]["invoked"] = False
    summary["bfcl_results_are_provider_outputs"] = bool(provider_called)
    _write_json(out / "execution_record.json", record)
    _write_json(out / "flight_summary.json", summary)
    _write_json(out / "official_evaluate_command.json", summary["official_evaluate"])
    _write_jsonl(out / "requests.jsonl", request_lines)
    _write_json(
        out / "spend_ledger.json",
        {
            "currency": "CNY",
            "ceiling_cny": summary["ceiling_cny"],
            "ceiling_raised": False,
            "cumulative_cny": summary["cumulative_cny"],
            "billed_basis": "provider_prompt_tokens",
            "physical": account.attempts,
        },
    )
    if provider_called:
        _write_bfcl_results(out / "bfcl_result" / EVALUATE_DECODER_ALIAS, rows)


def _write_bfcl_results(directory: Path, rows: dict) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for category, items in rows.items():
        ordered = sorted(items, key=lambda row: int(str(row["id"]).rsplit("_", 1)[1]))
        path = directory / f"{VERSION_PREFIX}_{category}_result.json"
        _write_jsonl(path, ordered)


def _runtime_failure_policy(ceiling: Decimal) -> dict:
    return {
        "auth_or_payment": "stop",
        "max_retries": 2,
        "backoff_seconds": [1, 2],
        "ceiling_cny": format_cny(ceiling),
        "do_not_raise_ceiling": True,
        "spend": "hard_stop_before_call_when_remaining_may_be_insufficient",
    }


def _deepseek_client_type():
    from tool_compression.provider import DeepSeekClient

    return DeepSeekClient


def _bfcl_package(root: Path) -> Path:
    root = Path(root)
    for candidate in (root, root / "berkeley-function-call-leaderboard"):
        if (candidate / "bfcl_eval" / "__main__.py").is_file():
            return candidate
    raise ExploratoryFlightRefused("bfcl_eval package not found")


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=_json_default) + "\n"
    path.write_text(scrub(text, None), encoding="utf-8")


def _write_jsonl(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(row, sort_keys=True, ensure_ascii=False, default=_json_default) for row in rows]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _json_default(value):
    if isinstance(value, Decimal):
        return format_cny(value)
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(type(value).__name__)
