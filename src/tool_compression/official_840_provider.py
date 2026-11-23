"""DeepSeek client for a later official 840-case flight.

Stage A does not import this module. The key is read from ``DEEPSEEK_API_KEY``
and is never written into an exception or an artifact.

This client is separate from the 12-case client. That client refuses a body
whose thinking field is anything other than disabled. The 840-case flight
sends thinking off on the first pass and thinking on on the second, so it
cannot reuse that assertion.

``urlopen(..., timeout=120)`` is an inactivity timeout on one socket.
``socket.create_connection`` applies it again for every DNS address, so a run
of unreachable addresses waits 120 seconds times the number of addresses and
still ends as a timeout. The 20:08 and 20:41 HKT stops matched that shape.
This client bounds the whole call with a wall clock, gives each address only
the time left (and at most ``CONNECT_TIMEOUT_SECONDS`` to connect), and shuts
the active socket down when the clock expires. ``RemoteDisconnected`` is raised
from ``getresponse`` and is not wrapped in ``URLError``; it is a refusal.
"""

from __future__ import annotations

import errno
import json
import os
import socket
import ssl
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request

import http.client

from tool_compression.official_840 import (
    API_BASE_URL,
    API_PATH,
    MODEL,
    UsxFlightRefused,
    assert_official_body,
)

API_KEY_ENV = "DEEPSEEK_API_KEY"
CALL_DEADLINE_SECONDS = 120
CONNECT_TIMEOUT_SECONDS = 10


def require_api_key() -> str:
    if API_KEY_ENV not in os.environ:
        raise UsxFlightRefused(f"{API_KEY_ENV} is not set")
    value = os.environ.get(API_KEY_ENV, "")
    if value.strip() == "":
        raise UsxFlightRefused(f"{API_KEY_ENV} is blank")
    return value


class LiveClient:
    """One Chat Completions POST. Callers already checked the ceiling and the clock."""

    def __init__(self, api_key: str, opener=None, *, deadline_seconds: float = CALL_DEADLINE_SECONDS):
        if not isinstance(api_key, str) or api_key.strip() == "":
            raise UsxFlightRefused("refusing a live client without a key")
        self._api_key = api_key
        self._opener = opener
        self._deadline_seconds = deadline_seconds

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
        abort = _Abort()
        outcome: dict = {}

        def attempt() -> None:
            try:
                if self._opener is None:
                    outcome["payload"] = _complete_bounded(request, self._deadline_seconds, abort)
                else:
                    # The socket hint stays 120s. The wall clock is deadline_seconds,
                    # so an opener that ignores its timeout still cannot hold the flight.
                    outcome["payload"] = _complete_with_opener(self._opener, request)
            except Exception as exc:
                outcome["error"] = exc

        worker = threading.Thread(target=attempt, name="usx840-provider", daemon=True)
        worker.start()
        worker.join(self._deadline_seconds)
        if worker.is_alive():
            abort()
            if abort.has_socket():
                worker.join(1.0)
            raise UsxFlightRefused("provider timed out")
        if "error" in outcome:
            error = outcome["error"]
            if isinstance(error, UsxFlightRefused):
                raise error from None
            refusal = _refusal_for(error)
            if refusal is None:
                raise error
            raise refusal from None
        return outcome["payload"]


class _Abort:
    """Close the socket the call is blocked on. Fired means the deadline won."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.fired = False
        self._sock = None

    def arm(self, sock) -> None:
        with self._lock:
            self._sock = sock
            fired = self.fired
        if fired:
            _shutdown(sock)

    def has_socket(self) -> bool:
        with self._lock:
            return self._sock is not None

    def triggered(self) -> bool:
        with self._lock:
            return self.fired

    def __call__(self) -> None:
        with self._lock:
            self.fired = True
            sock = self._sock
        if sock is not None:
            _shutdown(sock)


def _shutdown(sock) -> None:
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    try:
        sock.close()
    except OSError:
        pass


def _complete_with_opener(opener, request: Request) -> dict:
    try:
        with opener(request, timeout=CALL_DEADLINE_SECONDS) as response:
            raw = response.read()
    except UsxFlightRefused:
        raise
    except Exception as exc:
        refusal = _refusal_for(exc)
        if refusal is None:
            raise
        raise refusal from None
    return _decode_payload(raw)


def _complete_bounded(request: Request, deadline_seconds: float, abort: _Abort | None = None, ssl_context=None) -> dict:
    """POST one body and return the JSON object. The socket is closed at the deadline."""
    if abort is None:
        abort = _Abort()
    deadline_at = time.monotonic() + deadline_seconds
    timer = threading.Timer(deadline_seconds, abort)
    timer.daemon = True
    timer.start()
    try:
        try:
            status, raw = _post(request, deadline_at, abort, ssl_context)
        except UsxFlightRefused:
            raise
        except Exception as exc:
            if abort.triggered() or _is_timeout(exc):
                raise UsxFlightRefused("provider timed out") from None
            refusal = _refusal_for(exc)
            if refusal is None:
                raise
            raise refusal from None
    finally:
        timer.cancel()
    if status >= 400:
        raise UsxFlightRefused(f"provider HTTP {status}")
    return _decode_payload(raw)


def _post(request: Request, deadline_at: float, abort: _Abort, ssl_context) -> tuple[int, bytes]:
    host, port = _host_port(request)
    context = ssl_context or ssl.create_default_context()
    conn = _DeadlineHTTPSConnection(host, port, deadline_at, abort, context)
    try:
        if abort.triggered() or time.monotonic() >= deadline_at:
            raise TimeoutError("timed out")
        conn.request(
            request.get_method() or "POST",
            request.selector or "/",
            body=request.data,
            headers=_headers(request),
        )
        remaining = deadline_at - time.monotonic()
        if remaining <= 0 or abort.triggered():
            raise TimeoutError("timed out")
        if conn.sock is not None:
            conn.sock.settimeout(remaining)
            abort.arm(conn.sock)
        response = conn.getresponse()
        return response.status, response.read()
    finally:
        conn.close()


class _DeadlineHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, port: int, deadline_at: float, abort: _Abort, context: ssl.SSLContext):
        super().__init__(host, port, timeout=CONNECT_TIMEOUT_SECONDS, context=context)
        self._deadline_at = deadline_at
        self._abort = abort

    def connect(self) -> None:
        if self._abort.triggered() or time.monotonic() >= self._deadline_at:
            raise TimeoutError("timed out")
        infos = _resolve(self.host, self.port, self._deadline_at, self._abort)
        last_error: Exception | None = None
        for family, socktype, proto, _canon, address in infos:
            if self._abort.triggered() or time.monotonic() >= self._deadline_at:
                raise TimeoutError("timed out")
            remaining = self._deadline_at - time.monotonic()
            raw = socket.socket(family, socktype, proto)
            raw.settimeout(min(CONNECT_TIMEOUT_SECONDS, remaining))
            self._abort.arm(raw)
            try:
                if self.source_address:
                    raw.bind(self.source_address)
                raw.connect(address)
            except OSError as exc:
                last_error = exc
                _shutdown(raw)
                if self._abort.triggered() or time.monotonic() >= self._deadline_at:
                    raise TimeoutError("timed out") from None
                continue
            try:
                raw.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except OSError as exc:
                if exc.errno != errno.ENOPROTOOPT:
                    _shutdown(raw)
                    raise
            remaining = self._deadline_at - time.monotonic()
            if remaining <= 0 or self._abort.triggered():
                _shutdown(raw)
                raise TimeoutError("timed out")
            try:
                tls = self._context.wrap_socket(
                    raw,
                    server_hostname=self.host,
                    do_handshake_on_connect=False,
                )
            except OSError as exc:
                last_error = exc
                _shutdown(raw)
                if self._abort.triggered() or time.monotonic() >= self._deadline_at or _is_timeout(exc):
                    raise TimeoutError("timed out") from None
                raise
            tls.settimeout(remaining)
            self._abort.arm(tls)
            try:
                tls.do_handshake()
            except OSError as exc:
                last_error = exc
                _shutdown(tls)
                if self._abort.triggered() or time.monotonic() >= self._deadline_at or _is_timeout(exc):
                    raise TimeoutError("timed out") from None
                raise
            self.sock = tls
            return
        if last_error is not None and (_is_timeout(last_error) or time.monotonic() >= self._deadline_at):
            raise TimeoutError("timed out") from None
        if last_error is not None:
            raise last_error
        raise OSError("getaddrinfo returns an empty list")


def _resolve(host: str, port: int, deadline_at: float, abort: _Abort):
    """DNS is not covered by a socket timeout. Abandon it when the clock expires."""
    if abort.triggered() or time.monotonic() >= deadline_at:
        raise TimeoutError("timed out")
    holder: dict = {}

    def run() -> None:
        try:
            holder["infos"] = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except Exception as exc:
            holder["error"] = exc

    resolver = threading.Thread(target=run, name="usx840-dns", daemon=True)
    resolver.start()
    resolver.join(max(0.0, deadline_at - time.monotonic()))
    if resolver.is_alive() or abort.triggered() or time.monotonic() >= deadline_at:
        raise TimeoutError("timed out")
    if "error" in holder:
        raise holder["error"]
    return holder.get("infos") or []


def _host_port(request: Request) -> tuple[str, int]:
    host = request.host
    default = 443 if request.type == "https" else 80
    if host.startswith("["):
        name, _, rest = host[1:].partition("]")
        if rest.startswith(":"):
            return name, int(rest[1:])
        return name, default
    if host.count(":") == 1:
        name, _, port_text = host.partition(":")
        return name, int(port_text)
    return host, default


def _headers(request: Request) -> dict[str, str]:
    return {key: value for key, value in request.header_items() if key.lower() != "host"}


def _decode_payload(raw: bytes) -> dict:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise UsxFlightRefused("provider response was not JSON") from None
    if not isinstance(payload, dict):
        raise UsxFlightRefused("provider response was not an object")
    return payload


def _refusal_for(exc: Exception) -> UsxFlightRefused | None:
    """Map a provider failure to a fixed message. The original text is dropped."""
    if isinstance(exc, UsxFlightRefused):
        return exc
    if isinstance(exc, HTTPError):
        return UsxFlightRefused(f"provider HTTP {exc.code}")
    if _is_timeout(exc):
        return UsxFlightRefused("provider timed out")
    if isinstance(exc, (OSError, http.client.HTTPException)):
        return UsxFlightRefused("provider connection failed")
    return None


def _is_timeout(exc: object) -> bool:
    """True for socket timeouts and SSL read timeouts. The key is not read from the exception."""
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return True
    reason = getattr(exc, "reason", None)
    if reason is not None and reason is not exc and _is_timeout(reason):
        return True
    text = str(exc).lower()
    return "timed out" in text or "timeout" in text
