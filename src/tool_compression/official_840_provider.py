"""DeepSeek client for a later official 840-case flight.

Stage A does not import this module. The key is read from ``DEEPSEEK_API_KEY``
and is never written into an exception or an artifact.

This client is separate from the 12-case client. That client refuses a body
whose thinking field is anything other than disabled. The 840-case flight
sends thinking off on the first pass and thinking on on the second, so it
cannot reuse that assertion.
"""

from __future__ import annotations

import json
import os
import socket
import ssl
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from tool_compression.official_840 import (
    API_BASE_URL,
    API_PATH,
    MODEL,
    UsxFlightRefused,
    assert_official_body,
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
    """One Chat Completions POST. Callers already checked the ceiling and the clock."""

    def __init__(self, api_key: str, opener=None):
        if not isinstance(api_key, str) or api_key.strip() == "":
            raise UsxFlightRefused("refusing a live client without a key")
        self._api_key = api_key
        self._opener = opener or urlopen

    def complete(self, body: dict) -> dict:
        assert_official_body(body)
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
        except URLError as exc:
            if _is_timeout(exc.reason):
                raise UsxFlightRefused("provider timed out") from None
            raise UsxFlightRefused("provider connection failed") from None
        except (TimeoutError, socket.timeout):
            raise UsxFlightRefused("provider timed out") from None
        except ssl.SSLError as exc:
            if _is_timeout(exc):
                raise UsxFlightRefused("provider timed out") from None
            raise UsxFlightRefused("provider connection failed") from None
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise UsxFlightRefused("provider response was not JSON") from None
        if not isinstance(payload, dict):
            raise UsxFlightRefused("provider response was not an object")
        return payload


def _is_timeout(exc: object) -> bool:
    """True for socket timeouts and SSL read timeouts. The key is not read from the exception."""
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return True
    text = str(exc).lower()
    return "timed out" in text or "timeout" in text
