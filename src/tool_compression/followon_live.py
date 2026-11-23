"""Live T1/T2 generation. Importing this module does not read a key or open a socket.

The caller must already have passed ``--live`` and a supplied ceiling. Tests
inject a client. The urllib transport is constructed only by ``live_client``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import json
import os
from urllib.parse import urlparse

from tool_compression.followon_flight import (
    API_BASE_URL,
    API_KEY_ENV,
    ARMS,
    CATEGORIES,
    GENERATION_REFUSED,
    SCORING_ALIAS,
    FollowOnFlightRefused,
    accept_ceiling,
    assert_generation_body,
    billed_basis_t,
    format_cny,
    is_peak,
    pre_call_reserve_cny,
    remaining_allows_call,
    result_filename,
    spend_cny,
)
from tool_compression.official_score import FLIGHT_MODEL
from tool_compression.usage import usage_from_mapping


class MissingApiKey(RuntimeError):
    """DEEPSEEK_API_KEY is missing or blank. The value is not part of this error."""


class ProviderError(RuntimeError):
    def __init__(self, kind: str, message: str, status: int | None = None):
        self.kind = kind
        self.status = status
        super().__init__(message)


def require_api_key() -> str:
    """Read the key from the environment. Never from a flag, file, or literal."""
    if API_KEY_ENV not in os.environ:
        raise MissingApiKey(
            f"{API_KEY_ENV} is not set. Export it in the environment. "
            "This message does not include a key."
        )
    value = os.environ.get(API_KEY_ENV, "")
    if value.strip() == "":
        raise MissingApiKey(f"{API_KEY_ENV} is blank. This message does not include a key.")
    return value


def live_client(ceiling: Decimal):
    """Build the DeepSeek client. Call only after ``--live`` and a ceiling check."""
    from tool_compression.followon_flight import execution_record

    record = execution_record(ceiling, ARMS)
    if record["model"] != FLIGHT_MODEL or record["scoring_alias_may_generate"] is not False:
        raise FollowOnFlightRefused("refusing a live client for the scoring alias")
    return DeepSeekClient(require_api_key(), UrllibChatTransport(), API_BASE_URL)


class DeepSeekClient:
    def __init__(self, api_key: str, transport, base_url: str = API_BASE_URL, timeout: float = 120):
        if not isinstance(api_key, str) or api_key.strip() == "":
            raise MissingApiKey(f"{API_KEY_ENV} is blank. This message does not include a key.")
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or parsed.netloc != "api.deepseek.com":
            raise ProviderError("request", "refusing a provider host other than https://api.deepseek.com")
        self._api_key = api_key
        self.transport = transport
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def __repr__(self) -> str:
        return "DeepSeekClient(api_key='[redacted]', base_url='https://api.deepseek.com')"

    def complete(self, body: dict) -> dict:
        assert_generation_body(body)
        if body.get("model") == SCORING_ALIAS:
            raise FollowOnFlightRefused("refusing generation under the scoring alias")
        url = self.base_url + "/chat/completions"
        headers = {
            "Authorization": "Bearer " + self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        try:
            status, payload = self.transport.post_json(url, headers, body, self.timeout)
        except ProviderError:
            raise
        except Exception:
            raise ProviderError("transient", "connection failed")
        if status == 200 and isinstance(payload, dict):
            return payload
        raise ProviderError(_classify(status, payload), "provider error", status)


class UrllibChatTransport:
    """Stdlib POST. Tests substitute another transport and do not construct this."""

    def post_json(self, url: str, headers: dict, body: dict, timeout: float):
        import urllib.error
        import urllib.request

        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
                return response.status, json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {"error": {"code": "unreadable"}}
            return exc.code, payload
        except (TimeoutError, urllib.error.URLError):
            raise ProviderError("transient", "request timed out or the connection failed")


class ScriptedClient:
    """In-process stand-in. ``handler`` returns ``(status, payload)`` and is not a socket."""

    def __init__(self, handler):
        self.handler = handler
        self.bodies: list[dict] = []

    def complete(self, body: dict) -> dict:
        assert_generation_body(body)
        self.bodies.append(body)
        status, payload = self.handler(body)
        if status == 200 and isinstance(payload, dict):
            return payload
        raise ProviderError(_classify(status, payload), "provider error", status)


def execute_plans(
    plans: list[dict],
    *,
    ceiling: Decimal,
    client,
    out: Path,
    clock=None,
    sleep=None,
) -> dict:
    """Send prepared bodies. ``plans`` already passed the no-drop catalogue check."""
    amount = accept_ceiling(format_cny(ceiling))
    now = clock or (lambda: datetime.now(timezone.utc))
    if is_peak(now()):
        raise FollowOnFlightRefused("refusing to start or continue inside a peak window")
    pause = sleep or (lambda _seconds: None)
    reserve = pre_call_reserve_cny()
    spent = Decimal("0")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    attempts = []
    rows = {category: [] for category in CATEGORIES}
    prompt_tokens = {arm: {category: [] for category in CATEGORIES} for arm in ARMS}
    stop = None
    provider_called = False
    for plan in plans:
        if not remaining_allows_call(spent, amount, reserve):
            stop = "pre_call_reserve"
            break
        if is_peak(now()):
            stop = "peak_window"
            break
        try:
            payload = _complete_with_retries(client, plan["body"], pause)
        except ProviderError as exc:
            provider_called = True
            attempts.append({"case_id": plan["case_id"], "members": list(plan["members"]), "status": "failed", "kind": exc.kind})
            if exc.kind in {"auth", "payment"}:
                stop = exc.kind
                break
            stop = exc.kind
            break
        provider_called = True
        response_model = payload.get("model")
        if isinstance(response_model, str) and response_model in GENERATION_REFUSED:
            attempts.append(
                {
                    "case_id": plan["case_id"],
                    "members": list(plan["members"]),
                    "status": "failed",
                    "response_model": response_model,
                    "prompt_tokens": None,
                }
            )
            stop = "response_model"
            break
        usage = usage_from_mapping(payload)
        basis = billed_basis_t({"prompt_tokens": usage.total_input_tokens})
        thinking_ok = _thinking_disabled(payload)
        if basis["T"] is None or usage.output_tokens is None or not thinking_ok:
            attempts.append(
                {
                    "case_id": plan["case_id"],
                    "members": list(plan["members"]),
                    "status": "failed",
                    "prompt_tokens": basis["T"],
                    "cache_hits_subtracted": False,
                    "prices_applied_to_T": False,
                }
            )
            stop = "thinking_enabled" if not thinking_ok else "missing_usage"
            break
        cache_for_bill = 0 if usage.cached_input_tokens is None else usage.cached_input_tokens
        bill = spend_cny(basis["T"], cache_for_bill, usage.output_tokens)
        spent += bill
        attempts.append(
            {
                "case_id": plan["case_id"],
                "category": plan["category"],
                "members": list(plan["members"]),
                "status": "received",
                "prompt_tokens": basis["T"],
                "cached_input_tokens": usage.cached_input_tokens,
                "output_tokens": usage.output_tokens,
                "cny": format_cny(bill),
                "cache_hits_subtracted": False,
                "prices_applied_to_T": False,
            }
        )
        parsed = _model_responses(payload)
        for arm in plan["members"]:
            if arm not in prompt_tokens:
                continue
            prompt_tokens[arm][plan["category"]].append(basis["T"])
            rows[plan["category"]].append({"id": plan["case_id"], "result": parsed, "arm": arm})
        if spent > amount:
            stop = "ceiling_exceeded"
            break
    summary = {
        "provider_called": provider_called,
        "network_used": provider_called,
        "started": provider_called,
        "live": True,
        "stop_reason": stop,
        "groups_completed": sum(1 for row in attempts if row["status"] == "received"),
        "groups_planned": len(plans),
        "ceiling_cny": format_cny(amount),
        "cumulative_cny": format_cny(spent),
        "billed_basis": "provider_prompt_tokens",
        "prices_applied_to_T": False,
        "cache_hits_subtracted_from_T": False,
        "provider_T_invented": False,
        "revises_official_c_versus_u": False,
        "ok": stop is None and summary_complete(attempts, plans),
    }
    _write_json(out / "live_summary.json", summary)
    _write_json(out / "spend_ledger.json", {"currency": "CNY", "physical": attempts, "applied_to_T": False})
    if provider_called:
        _write_results(out / "bfcl_result" / SCORING_ALIAS, rows)
        _write_json(out / "prompt_tokens.json", _usage_document(prompt_tokens))
    return summary


def summary_complete(attempts: list[dict], plans: list[dict]) -> bool:
    received = [row for row in attempts if row["status"] == "received"]
    return len(received) == len(plans)


def plans_from_study(study: dict, counter, arms: tuple[str, ...], *, sequential: bool) -> list[dict]:
    """Attach bodies for a live run. Separate arms do not share a call."""
    from tool_compression.followon_flight import prepare_case, require_official_denominators

    require_official_denominators(study)
    plans = []
    for category in CATEGORIES:
        for record in study[category]:
            prepared = prepare_case(record, counter)
            raw = prepared["raw"]
            if sequential and arms == ARMS and raw["T1"] == raw["T2"]:
                plans.append(
                    {
                        "category": category,
                        "case_id": str(record["id"]),
                        "members": ["T1", "T2"],
                        "body": prepared["bodies"]["T1"],
                        "identical_to_u": raw["T1"] == raw["U"],
                    }
                )
            else:
                for arm in arms:
                    plans.append(
                        {
                            "category": category,
                            "case_id": str(record["id"]),
                            "members": [arm],
                            "body": prepared["bodies"][arm],
                            "identical_to_u": raw[arm] == raw["U"],
                        }
                    )
    return plans


def _complete_with_retries(client, body: dict, sleep) -> dict:
    delays = (0, 1, 2)
    last = None
    for attempt, delay in enumerate(delays):
        if delay:
            sleep(delay)
        try:
            return client.complete(body)
        except ProviderError as exc:
            last = exc
            if exc.kind != "transient" or attempt == len(delays) - 1:
                raise
    raise last


def _model_responses(payload: dict):
    try:
        message = payload["choices"][0]["message"]
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            return message.get("content")
        return [{call["function"]["name"]: call["function"]["arguments"]} for call in tool_calls]
    except (KeyError, TypeError, IndexError):
        return None


def _usage_document(prompt_tokens: dict) -> dict:
    categories = {}
    for arm, blocks in prompt_tokens.items():
        categories[arm] = {
            "categories": {category: values for category, values in blocks.items() if values}
        }
    return {
        "basis": "provider_prompt_tokens",
        "cache_hits_subtracted": False,
        "prices_applied": False,
        "arms": categories,
    }


def _thinking_disabled(payload: dict) -> bool:
    """Absent or empty reasoning is disabled. A non-empty trace is thinking on."""
    choices = payload.get("choices") if isinstance(payload, dict) else None
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return False
    message = choices[0].get("message")
    if not isinstance(message, dict):
        return False
    for key in ("reasoning_content", "thinking"):
        if key in message and not _empty_reasoning(message.get(key)):
            return False
    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    details = usage.get("completion_tokens_details") if isinstance(usage.get("completion_tokens_details"), dict) else {}
    reasoning_tokens = details.get("reasoning_tokens")
    if isinstance(reasoning_tokens, int) and not isinstance(reasoning_tokens, bool) and reasoning_tokens > 0:
        return False
    return True


def _empty_reasoning(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def _classify(status: int, payload) -> str:
    if status in (401, 403):
        return "auth"
    if status == 402:
        return "payment"
    if status in (429, 500, 502, 503, 504):
        return "transient"
    text = ""
    if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
        text = str(payload["error"].get("code") or "").lower()
    if "timeout" in text or "connection" in text:
        return "transient"
    return "request"


def _write_results(directory: Path, rows: dict) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for category, items in rows.items():
        deduped = []
        seen = set()
        for item in items:
            key = (item["id"], item["arm"])
            if key in seen:
                continue
            seen.add(key)
            deduped.append({"id": item["id"], "result": item["result"]})
        path = directory / result_filename(category)
        lines = [json.dumps(row, sort_keys=True, ensure_ascii=False) for row in deduped]
        path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
