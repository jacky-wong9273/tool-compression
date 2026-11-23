"""DeepSeek client for a later USX live run.

Stage A does not import this module. The key is read from ``DEEPSEEK_API_KEY``
and is never written into an exception or an artifact.
"""

from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from tool_compression.usx_flight import (
    API_BASE_URL,
    API_PATH,
    MODEL,
    UsxFlightRefused,
    assert_generation_body,
)

API_KEY_ENV = "DEEPSEEK_API_KEY"


def require_api_key() -> str:
    if API_KEY_ENV not in os.environ:
        raise UsxFlightRefused(f"{API_KEY_ENV} is not set")
    value = os.environ.get(API_KEY_ENV, "")
    if value.strip() == "":
        raise UsxFlightRefused(f"{API_KEY_ENV} is blank")
    return value


class LiveClient:
    """One Chat Completions POST. Callers already checked the ceiling."""

    def __init__(self, api_key: str, opener=None):
        if not isinstance(api_key, str) or api_key.strip() == "":
            raise UsxFlightRefused("refusing a live client without a key")
        self._api_key = api_key
        self._opener = opener or urlopen

    def complete(self, body: dict) -> dict:
        assert_generation_body(body)
        if body.get("model") != MODEL:
            raise UsxFlightRefused("refusing a generation body that is not deepseek-flash")
        request = Request(
            API_BASE_URL + API_PATH,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with self._opener(request, timeout=120) as response:
                raw = response.read()
        except HTTPError as exc:
            raise UsxFlightRefused(f"provider HTTP {exc.code}") from None
        except URLError:
            raise UsxFlightRefused("provider connection failed") from None
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise UsxFlightRefused("provider response was not JSON") from None
        if not isinstance(payload, dict):
            raise UsxFlightRefused("provider response was not an object")
        return payload
