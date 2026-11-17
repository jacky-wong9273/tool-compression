"""DeepSeek Chat Completions client for the validation flight.

The live transport is unused by tests. The key is read only from
``DEEPSEEK_API_KEY`` and is never written into an exception, log, or artifact.
Every request body is refused unless thinking is disabled.
"""

from copy import deepcopy
import json
import os
from urllib.parse import urlparse

from tool_compression.config import BFCL_DEFAULT_TEMPERATURE, BFCL_STORE
from tool_compression.flight_spec import API_BASE_URL, MODEL, THINKING_DISABLED
from tool_compression.prepare import request_hash


class MissingApiKey(RuntimeError):
    """DEEPSEEK_API_KEY is missing or blank. The value is not part of this error."""


class ProviderError(RuntimeError):
    def __init__(self, kind: str, message: str, status: int | None = None):
        self.kind = kind
        self.status = status
        super().__init__(message)


def require_api_key() -> str:
    """Read the key from the environment. Never from a flag, file, or literal."""
    if "DEEPSEEK_API_KEY" not in os.environ:
        raise MissingApiKey(
            "DEEPSEEK_API_KEY is not set. Export it in the environment. "
            "This message does not include a key."
        )
    value = os.environ.get("DEEPSEEK_API_KEY", "")
    if value.strip() == "":
        raise MissingApiKey(
            "DEEPSEEK_API_KEY is blank. This message does not include a key."
        )
    return value


def flight_request(messages: list, catalogue: list) -> dict:
    """Body actually sent. Thinking is pinned off here, not copied from a caller."""
    request = {
        "messages": deepcopy(messages),
        "model": MODEL,
        "temperature": BFCL_DEFAULT_TEMPERATURE,
        "store": BFCL_STORE,
        "thinking": dict(THINKING_DISABLED),
    }
    if catalogue:
        request["tools"] = deepcopy(catalogue)
    assert_request_thinking_off(request)
    return request


def assert_request_thinking_off(body: dict) -> None:
    if body.get("model") != MODEL:
        raise ProviderError("request", "refusing a request whose model is not deepseek-flash")
    if body.get("thinking") != THINKING_DISABLED:
        raise ProviderError("request", "refusing a request that does not disable thinking")
    if "reasoning_effort" in body:
        raise ProviderError("request", "refusing a request that sets reasoning_effort")
    if body.get("temperature") != BFCL_DEFAULT_TEMPERATURE or body.get("store") is not False:
        raise ProviderError("request", "refusing a request that drops the BFCL temperature or store default")


def response_thinking_disabled(payload: dict) -> bool:
    """Absent or empty reasoning is disabled. A non-empty trace is thinking on."""
    choices = payload.get("choices") if isinstance(payload, dict) else None
    if not isinstance(choices, list) or not choices:
        return False
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        return False
    if "reasoning_content" in message and not _empty_reasoning(message.get("reasoning_content")):
        return False
    if "thinking" in message and not _empty_reasoning(message.get("thinking")):
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


def parse_fc_response(payload: dict) -> dict:
    """BFCL ``_parse_query_response_FC`` shape, without vendoring the handler.

    Tool-call arguments stay strings. ``reasoning_content`` is kept on the
    parse for the thinking check and is left out of the chat-history message.
    Token fields follow the handler: ``input_token`` from ``prompt_tokens``
    and ``output_token`` from ``completion_tokens``.
    """
    message = {}
    try:
        message = payload["choices"][0]["message"]
        tool_calls = message["tool_calls"]
        if not tool_calls:
            raise ValueError("no tool calls")
        model_responses = [
            {call["function"]["name"]: call["function"]["arguments"]}
            for call in tool_calls
        ]
        tool_call_ids = [call["id"] for call in tool_calls]
        history = {
            "role": "assistant",
            "content": message.get("content"),
            "tool_calls": [
                {
                    "id": call["id"],
                    "type": call.get("type", "function"),
                    "function": {
                        "name": call["function"]["name"],
                        "arguments": call["function"]["arguments"],
                    },
                }
                for call in tool_calls
            ],
        }
    except (KeyError, TypeError, ValueError, IndexError):
        model_responses = message.get("content") if isinstance(message, dict) else None
        tool_call_ids = []
        history = {
            "role": "assistant",
            "content": message.get("content") if isinstance(message, dict) else None,
        }
    parsed = {
        "model_responses": model_responses,
        "model_responses_message_for_chat_history": history,
        "tool_call_ids": tool_call_ids,
        "input_token": _usage_field(payload, "prompt_tokens"),
        "output_token": _usage_field(payload, "completion_tokens"),
    }
    if isinstance(message, dict) and "reasoning_content" in message:
        parsed["reasoning_content"] = message.get("reasoning_content")
    return parsed


def _usage_field(payload: dict, key: str):
    usage = payload.get("usage") if isinstance(payload, dict) else None
    if not isinstance(usage, dict):
        return None
    return usage.get(key)


def classify_status(status: int, payload) -> str:
    if status in (401, 403):
        return "auth"
    if status == 402:
        return "payment"
    if status in (429, 500, 502, 503, 504):
        return "transient"
    text = _error_blob(payload)
    if any(token in text for token in ("invalid_api_key", "authentication", "unauthorized", "permission")):
        return "auth"
    if any(token in text for token in ("insufficient_quota", "billing", "payment", "insufficient balance")):
        return "payment"
    return "request"


def _error_blob(payload) -> str:
    if not isinstance(payload, dict):
        return ""
    error = payload.get("error")
    if isinstance(error, dict):
        parts = [str(error.get("code") or ""), str(error.get("type") or "")]
        return " ".join(parts).lower()
    return ""


def safe_error(payload) -> str:
    if isinstance(payload, dict):
        error = payload.get("error")
        code = error.get("code") if isinstance(error, dict) else None
        if isinstance(code, str) and code and len(code) <= 40 and " " not in code:
            return "provider error " + code
    return "provider error"


def scrub(text: str, secret: str | None) -> str:
    if secret:
        return text.replace(secret, "[redacted]")
    return text


class DryRunClient:
    """Local completion stand-in. It does not read a key or open a socket."""

    def __init__(self) -> None:
        self.bodies: list[dict] = []

    def __repr__(self) -> str:
        return "DryRunClient()"

    def complete(self, body: dict) -> dict:
        assert_request_thinking_off(body)
        self.bodies.append(deepcopy(body))
        return dry_run_response(body)


class ScriptedClient:
    """Test double. ``handler`` returns ``(status, payload)`` and is not a network."""

    def __init__(self, handler) -> None:
        self.handler = handler
        self.bodies: list[dict] = []

    def complete(self, body: dict) -> dict:
        assert_request_thinking_off(body)
        self.bodies.append(deepcopy(body))
        status, payload = self.handler(body)
        if status == 200 and isinstance(payload, dict):
            return payload
        raise ProviderError(classify_status(status, payload), safe_error(payload), status)


def dry_run_response(body: dict) -> dict:
    digest = request_hash(body)
    prompt = 800 + (int(digest[:6], 16) % 400)
    completion = 12
    usage = {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
    }
    if int(digest[6], 16) % 2 == 0:
        hit = min(100, prompt)
        usage["prompt_tokens_details"] = {"cached_tokens": hit}
    message = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call_dry_run",
                "type": "function",
                "function": {"name": "noop", "arguments": "{}"},
            }
        ],
    }
    return {
        "id": "dry-run",
        "object": "chat.completion",
        "model": body.get("model"),
        "choices": [{"index": 0, "message": message, "finish_reason": "tool_calls"}],
        "usage": usage,
    }


class DeepSeekClient:
    """HTTPS Chat Completions against the official DeepSeek host."""

    def __init__(self, api_key: str, transport, base_url: str = API_BASE_URL, timeout: float = 120):
        if not isinstance(api_key, str) or api_key.strip() == "":
            raise MissingApiKey("DEEPSEEK_API_KEY is blank. This message does not include a key.")
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
        assert_request_thinking_off(body)
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
        raise ProviderError(classify_status(status, payload), safe_error(payload), status)


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
                payload = {"error": {"message": "unreadable provider error"}}
            return exc.code, payload
        except (TimeoutError, urllib.error.URLError):
            raise ProviderError("transient", "request timed out or the connection failed")
