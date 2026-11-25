"""Runner failure modes, with mocked transports and executors only.

No test reads a provider key or opens a socket. The last test runs the real
pinned BFCL executor and memory backend when ``CLEAN_START_BFCL_ROOT`` points at
a checkout whose dependencies import; it is skipped otherwise.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import json
import os
import threading

import pytest

from tool_compression.clean_start.pin import ARMS, STEP_LIMIT
from tool_compression.clean_start.prepare import HOLDOUT_USER_PROMPT, PYTHON_HINT
from tool_compression.clean_start.rate_card import spend_usd
from tool_compression.clean_start.runner import (
    ProviderHTTPError,
    RunStopped,
    TotalDeadlineExceeded,
    arm_order,
    build_slots,
    execute,
    parse_thinking_modes,
    post_chat,
    preflight,
    write_plan,
)
from tool_compression.clean_start.scoring import decode_execute, is_empty_execute_response, result_relative

NOON = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)


def _clock():
    return NOON


def _function(name: str = "echo", description: str = "Echo a value.") -> dict:
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "dict",
            "properties": {"value": {"type": "integer", "description": "A value."}},
            "required": ["value"],
        },
    }


def _usage() -> dict:
    return {
        "prompt_tokens": 1000,
        "prompt_cache_hit_tokens": 200,
        "prompt_cache_miss_tokens": 800,
        "completion_tokens": 50,
    }


def _tool(name: str = "echo", arguments: str = "{\"value\": 1}", call_id: str = "call_1") -> dict:
    return {
        "choices": [{"message": {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"id": call_id, "type": "function", "function": {"name": name, "arguments": arguments}}],
        }}],
        "usage": _usage(),
    }


def _text(text: str = "done") -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": text}}], "usage": _usage()}


def _one_request_usd() -> Decimal:
    amount, _band = spend_usd(cache_hit=200, cache_miss=800, output=50, at=NOON)
    return amount


class _Scripted:
    """Return scripted payloads; an exception instance in the script is raised."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.bodies = []

    def __call__(self, body):
        self.bodies.append(body)
        if not self.responses:
            raise AssertionError("script exhausted")
        item = self.responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class _Executor:
    def __init__(self, outputs=None):
        self.calls = []
        self.flushed = []
        self.prompted = []
        self.outputs = outputs

    def initialize(self, case, config):
        self.calls.append(("init", [], config["instance_name"]))
        return {config["involved_classes"][0]: object()}

    def memory_prompt(self, question, case, instances):
        self.prompted.append(case["id"])
        first = [{"role": "system", "content": "MEMORY PROMPT"}, *question[0]]
        return [first, *question[1:]]

    def execute_calls(self, strings, case, config):
        self.calls.append(("call", list(strings), config["instance_name"]))
        return list(self.outputs) if self.outputs is not None else [f"ran {item}" for item in strings]

    def flush_prereq(self, case, instances):
        self.flushed.append(case["id"])


def _trajectory_case(case_id: str = "multi_turn_base_0", turns: int = 1, **extra) -> dict:
    case = {
        "id": case_id,
        "category": case_id.rsplit("_", 1)[0] if not case_id.startswith("memory") else "memory_kv",
        "question": [[{"role": "user", "content": f"turn {index}"}] for index in range(turns)],
        "function": [_function("echo"), _function("other", "Return another value.")],
        "involved_classes": ["GorillaFileSystem"],
        "initial_config": {},
        "prereq": False,
    }
    case.update(extra)
    return case


def _single_case(case_id: str = "multiple_0") -> dict:
    return {
        "id": case_id,
        "category": "multiple",
        "question": [[{"role": "user", "content": "q"}]],
        "function": [_function("echo"), _function("other", "Return another value.")],
        "prereq": False,
    }


def _lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_thinking_modes_are_explicit_and_never_expand(tmp_path):
    assert parse_thinking_modes("off") == ("off",)
    assert parse_thinking_modes("on,off") == ("off", "on")
    for bad in ("", "both", "off,off", "OFF", "off,maybe"):
        with pytest.raises(ValueError):
            parse_thinking_modes(bad)
    case = _single_case()
    off_only = build_slots([case], ("off",))
    assert {slot["thinking"] for slot in off_only} == {"off"}
    every = build_slots([case], ("off", "on"))
    script = _Scripted([])
    with pytest.raises(RunStopped) as stopped:
        execute([case], every, tmp_path / "run", script, ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock)
    assert stopped.value.reason == "thinking_mode_not_authorized:on"
    assert script.bodies == []
    assert not (tmp_path / "run").exists()


def test_every_body_carries_the_authorised_thinking_field(tmp_path):
    case = _single_case()
    script = _Scripted([_text() for _ in range(4)])
    result = execute(
        [case], build_slots([case], ("on",)), tmp_path, script,
        ceiling_usd=Decimal("1"), thinking_modes=("on",), clock=_clock,
    )
    assert result["complete"] is True
    assert [body["thinking"] for body in script.bodies] == [{"type": "enabled"}] * 4
    assert all("max_tokens" not in body for body in script.bodies)
    assert not (tmp_path / "result" / "deepseek-flash-thinking-off-U").exists()


def test_attempt_is_journalled_before_the_send_and_timeout_keeps_partial_steps(tmp_path):
    case = _trajectory_case()
    seen_before_send = []

    def transport(body):
        attempts = _lines(tmp_path / "attempts.jsonl")
        seen_before_send.append(attempts[-1])
        return script(body)

    script = _Scripted([_tool(), _tool(), TimeoutError("read timed out")])
    executor = _Executor()
    result = execute(
        [case], build_slots([case], ("off",))[:1], tmp_path, transport,
        ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock, executor=executor,
    )
    assert [row["event"] for row in seen_before_send] == ["sent"] * 3
    assert [row["attempt"] for row in seen_before_send] == [1, 2, 3]
    assert result["complete"] is False
    assert result["status"] == "incomplete"
    assert result["reason"] == "provider_error:TimeoutError"
    assert result["uncertain_attempts"] == [3]
    assert result["partial_slots"] == [
        {"case_id": case["id"], "arm": "U", "thinking": "off", "billed_steps": 2}
    ]
    attempts = _lines(tmp_path / "attempts.jsonl")
    assert [(row["attempt"], row["event"]) for row in attempts] == [
        (1, "sent"), (1, "completed"), (2, "sent"), (2, "completed"), (3, "sent"), (3, "failed"),
    ]
    assert attempts[-1]["may_be_billed"] is True
    assert len(_lines(tmp_path / "bills.jsonl")) == 2
    sidecar = json.loads(
        (tmp_path / "model_outputs/deepseek-flash-thinking-off/U/multi_turn_base_0.json").read_text(encoding="utf-8")
    )
    assert sidecar["status"] == "stopped"
    assert sidecar["scorable"] is False
    assert sidecar["stop_reason"] == "provider_error:TimeoutError"
    assert len(sidecar["steps"]) == 2
    assert sidecar["steps"][0]["tool_outputs"] == ["ran echo(value=1)"]
    assert not list(tmp_path.rglob("*_result.json"))
    spend = json.loads((tmp_path / "spend.json").read_text(encoding="utf-8"))
    assert spend["uncertain_attempts"] == [3]
    assert spend["complete"] is False


def test_http_error_is_named_and_not_retried(tmp_path):
    case = _single_case()
    script = _Scripted([ProviderHTTPError(429, "rate limited"), _text()])
    result = execute(
        [case], build_slots([case], ("off",)), tmp_path, script,
        ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock,
    )
    assert len(script.bodies) == 1
    assert result["reason"] == "provider_error:ProviderHTTPError"
    failed = _lines(tmp_path / "attempts.jsonl")[-1]
    assert failed["event"] == "failed" and failed["http_status"] == 429


def test_unusable_payload_is_journalled_as_possibly_billed(tmp_path):
    case = _single_case()
    script = _Scripted([{"choices": [], "usage": _usage()}])
    result = execute(
        [case], build_slots([case], ("off",)), tmp_path, script,
        ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock,
    )
    assert result["reason"] == "provider_choice_missing"
    assert result["uncertain_attempts"] == [1]
    last = _lines(tmp_path / "attempts.jsonl")[-1]
    assert last["event"] == "unusable_response" and last["may_be_billed"] is True


def test_out_dir_with_provider_evidence_is_refused(tmp_path):
    case = _single_case()
    slots = build_slots([case], ("off",))[:1]
    execute([case], slots, tmp_path, _Scripted([_text()]), ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock)
    before = (tmp_path / "bills.jsonl").read_bytes()
    again = _Scripted([_text()])
    with pytest.raises(RunStopped) as stopped:
        execute([case], slots, tmp_path, again, ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock)
    assert stopped.value.reason.startswith("out_dir_has_provider_evidence")
    assert again.bodies == []
    assert (tmp_path / "bills.jsonl").read_bytes() == before
    from tool_compression.clean_start.__main__ import main

    run_json = (tmp_path / "run.json").read_bytes()
    assert main(["run", "--out", str(tmp_path)]) == 2
    assert (tmp_path / "run.json").read_bytes() == run_json
    plan_dir = tmp_path / "plan"
    write_plan([case], plan_dir, pilot=False, thinking_modes=("off",))
    execute([case], slots, plan_dir, _Scripted([_text()]), ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock)


def test_ceiling_is_checked_before_every_request_inside_a_trajectory(tmp_path):
    case = _trajectory_case()
    script = _Scripted([_tool(), _tool(), _tool(), _text()])
    result = execute(
        [case], build_slots([case], ("off",))[:1], tmp_path, script,
        ceiling_usd=_one_request_usd() * Decimal("1.5"), thinking_modes=("off",), clock=_clock, executor=_Executor(),
    )
    assert len(script.bodies) == 2
    assert result["reason"] == "ceiling"
    assert result["uncertain_attempts"] == []
    assert result["partial_slots"][0]["billed_steps"] == 2
    sidecar = json.loads(
        (tmp_path / "model_outputs/deepseek-flash-thinking-off/U/multi_turn_base_0.json").read_text(encoding="utf-8")
    )
    assert sidecar["status"] == "stopped" and sidecar["stop_reason"] == "ceiling"


def test_pinned_decode_failures_end_the_turn_not_the_run(tmp_path):
    assert decode_execute([{"echo": "{\"value\": 1}"}]) == ["echo(value=1)"]
    assert decode_execute({"echo": {"value": "a"}}) == ["echo(value='a')"]
    assert is_empty_execute_response(decode_execute([])) is True
    assert is_empty_execute_response(decode_execute("")) is True
    with pytest.raises(Exception):
        decode_execute("plain text answer")
    with pytest.raises(Exception):
        decode_execute([{"echo": "{not json"}])
    case = _trajectory_case(turns=2)
    script = _Scripted([_tool(arguments="{not json"), _text("second turn")])
    executor = _Executor()
    result = execute(
        [case], build_slots([case], ("off",))[:1], tmp_path, script,
        ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock, executor=executor,
    )
    assert result["complete"] is True
    assert [kind for kind, *_rest in executor.calls] == ["init"]
    entry = _lines(tmp_path / result_relative(case["id"], "off", "U"))[0]
    assert entry["result"] == [[[{"echo": "{not json"}]], ["second turn"]]
    sidecar = json.loads(
        (tmp_path / "model_outputs/deepseek-flash-thinking-off/U/multi_turn_base_0.json").read_text(encoding="utf-8")
    )
    assert sidecar["steps"][0]["turn_end"] == "decode_error:JSONDecodeError"
    assert sidecar["status"] == "finished"


def test_step_limit_matches_the_pinned_loop(tmp_path):
    case = _trajectory_case(turns=2)
    script = _Scripted([_tool() for _ in range(STEP_LIMIT + 1)])
    result = execute(
        [case], build_slots([case], ("off",))[:1], tmp_path, script,
        ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock, executor=_Executor(),
    )
    assert result["complete"] is True
    assert len(script.bodies) == STEP_LIMIT + 1 == 21
    entry = _lines(tmp_path / result_relative(case["id"], "off", "U"))[0]
    assert entry["forced_quit"] is True
    assert len(entry["result"]) == 1 and len(entry["result"][0]) == STEP_LIMIT + 1
    tool_messages = [message for message in script.bodies[1]["messages"] if message["role"] == "tool"]
    assert tool_messages == [{"role": "tool", "content": "ran echo(value=1)", "tool_call_id": "call_1"}]


def test_memory_prompt_flush_and_result_dir_follow_the_pinned_loop(tmp_path):
    prereq = _trajectory_case(
        "memory_kv_prereq_0-customer-0", category="memory_kv", prereq=True, scenario="customer",
        involved_classes=["MemoryAPI_kv"],
    )
    question = _trajectory_case(
        "memory_kv_7-customer-7", category="memory_kv", scenario="customer", involved_classes=["MemoryAPI_kv"],
    )
    executor = _Executor()
    configs = []
    original = executor.initialize

    def initialize(case, config):
        configs.append(config)
        return original(case, config)

    executor.initialize = initialize
    script = _Scripted([_text("stored"), _text("answer")])
    result = execute(
        [prereq, question], [slot for slot in build_slots([prereq, question], ("off",)) if slot["arm"] == "S"],
        tmp_path, script, ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock, executor=executor,
    )
    assert result["complete"] is True
    assert executor.prompted == [prereq["id"], question["id"]]
    assert executor.flushed == [prereq["id"]]
    assert script.bodies[0]["messages"][0] == {"role": "system", "content": "MEMORY PROMPT"}
    agentic = script.bodies[1]["messages"]
    assert agentic[0]["content"] == "MEMORY PROMPT"
    assert agentic[1]["role"] == "system" and "final answer" in agentic[1]["content"]
    root = configs[0]["initial_config"]["MemoryAPI_kv"]["model_result_dir"]
    assert isinstance(root, Path)
    assert root == tmp_path / "result" / "deepseek-flash-thinking-off-S"
    assert configs[0]["initial_config"]["MemoryAPI_kv"]["test_category"] == "memory_kv_prereq"


def test_held_out_docs_are_sent_without_the_language_hint(tmp_path):
    held = _function("sort", "Sort the files.")
    case = _trajectory_case("multi_turn_miss_func_0", turns=2, held_out={"1": [held]})
    case["question"][1] = []
    script = _Scripted([_text("first"), _text("second")])
    execute(
        [case], build_slots([case], ("off",))[:1], tmp_path, script,
        ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock, executor=_Executor(),
    )
    first, second = script.bodies
    assert [tool["function"]["name"] for tool in first["tools"]] == ["echo", "other"]
    assert [tool["function"]["name"] for tool in second["tools"]] == ["echo", "other", "sort"]
    assert first["tools"][0]["function"]["description"].endswith(PYTHON_HINT)
    assert second["tools"][2]["function"]["description"] == "Sort the files."
    assert second["messages"][-1] == {"role": "user", "content": HOLDOUT_USER_PROMPT}


def test_arm_order_is_counterbalanced_across_cases():
    cases = [_single_case(f"multiple_{index}") for index in range(8)]
    slots = build_slots(cases, ("off",))
    firsts = [slots[index * 4]["arm"] for index in range(8)]
    assert firsts == list(ARMS) * 2
    for index in range(8):
        assert sorted(slot["arm"] for slot in slots[index * 4:index * 4 + 4]) == sorted(ARMS)
        assert tuple(slot["arm"] for slot in slots[index * 4:index * 4 + 4]) == arm_order(index)


def test_preflight_names_missing_backends_and_credentials_without_values():
    web = {"id": "web_search_base_0", "category": "web_search_base", "involved_classes": ["WebSearchAPI"], "prereq": False}
    vector = {"id": "memory_vector_0-student-0", "category": "memory_vector", "involved_classes": ["MemoryAPI_vector"], "prereq": False}
    slots = build_slots([web, vector], ("off",))
    problems = preflight(
        [web, vector], slots, bfcl_root=None, environ={}, find_spec=lambda name: None if name == "faiss" else object(),
    )
    assert "bfcl_root_missing: a trajectory category needs --bfcl-root" in problems
    assert any(problem.startswith("serpapi_key_missing") for problem in problems)
    assert "backend_module_missing: MemoryAPI_vector needs faiss" in problems
    assert "provider_key_missing: DEEPSEEK_API_KEY is not set" in problems
    secret = "sk-should-never-be-echoed"
    clean = preflight(
        [web, vector], slots, bfcl_root=Path("/x"),
        environ={"SERPAPI_API_KEY": secret, "DEEPSEEK_API_KEY": secret}, find_spec=lambda name: object(),
    )
    assert clean == []
    assert secret not in json.dumps(problems)
    single = _single_case()
    assert preflight([single], build_slots([single], ("off",)), bfcl_root=None, environ={"DEEPSEEK_API_KEY": "x"}) == []


def test_cli_refuses_a_live_web_run_without_serpapi_before_the_key_is_read(tmp_path, monkeypatch):
    from tool_compression.clean_start.__main__ import main

    web = {
        "id": "web_search_base_0", "category": "web_search_base", "involved_classes": ["WebSearchAPI"],
        "question": [[{"role": "user", "content": "q"}]], "function": [_function()], "prereq": False,
    }
    monkeypatch.setattr("tool_compression.clean_start.__main__._select_cases", lambda _pilot, _prereqs: [web])
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "placeholder-not-a-key")
    monkeypatch.setattr(
        "tool_compression.clean_start.__main__.authorized_transport",
        lambda: (_ for _ in ()).throw(AssertionError("key read")),
    )
    code = main([
        "run", "--live", "--authorize-live", "--thinking", "off", "--ceiling-usd", "1",
        "--bfcl-root", str(tmp_path), "--out", str(tmp_path / "out"),
    ])
    assert code == 2
    assert not (tmp_path / "out").exists()


def test_pilot_live_run_needs_an_explicit_memory_prerequisite_choice(tmp_path, monkeypatch):
    from tool_compression.clean_start.__main__ import _select_cases, main

    monkeypatch.setattr(
        "tool_compression.clean_start.__main__.authorized_transport",
        lambda: (_ for _ in ()).throw(AssertionError("key read")),
    )
    assert main([
        "run", "--pilot", "--live", "--authorize-live", "--thinking", "off", "--ceiling-usd", "1",
        "--out", str(tmp_path),
    ]) == 2
    assert main(["run", "--memory-prereqs", "matched", "--out", str(tmp_path)]) == 2
    plain = _select_cases(True, "none")
    matched = _select_cases(True, "matched")
    assert [case["id"] for case in matched if not case.get("prereq")] == [case["id"] for case in plain]
    assert len(plain) == 41
    prereqs = [case for case in matched if case.get("prereq")]
    drawn = {(case["category"], case["scenario"]) for case in plain if case["category"].startswith("memory_")}
    assert {(case["category"], case["scenario"]) for case in prereqs} == drawn
    positions = {case["id"]: index for index, case in enumerate(matched)}
    for case in plain:
        if case["category"].startswith("memory_"):
            earlier = [item for item in prereqs if item["category"] == case["category"] and item["scenario"] == case["scenario"]]
            assert all(positions[item["id"]] < positions[case["id"]] for item in earlier)
            assert any(item["id"].endswith("-0") for item in earlier)


def test_supported_pilot_omits_web_search_and_does_not_need_serpapi():
    from tool_compression.clean_start.__main__ import _select_cases

    cases = _select_cases(True, "matched")
    slots = build_slots(cases, ("off",))
    assert len(cases) == 95
    assert sum(1 for case in cases if case.get("prereq")) == 54
    assert len(slots) == 380
    assert sum(1 for slot in slots if slot["prereq"]) == 216
    assert sum(1 for slot in slots if not slot["prereq"]) == 164
    assert {slot["thinking"] for slot in slots} == {"off"}
    assert {slot["arm"] for slot in slots} == set(ARMS)
    assert not any(slot["category"].startswith("web_search") for slot in slots)
    assert not any(case["category"].startswith("web_search") for case in cases)
    paths = [result_relative("memory_kv_7-customer-7", "off", arm) for arm in ARMS]
    assert len(set(paths)) == 4
    asked = []

    def find_spec(name):
        asked.append(name)
        if name in {"serpapi", "bs4", "html2text", "requests"}:
            raise AssertionError(f"supported scope looked up {name}")
        return object()

    problems = preflight(
        cases, slots, bfcl_root=Path("/bfcl"),
        environ={"DEEPSEEK_API_KEY": "present"}, find_spec=find_spec,
    )
    assert problems == []
    assert "serpapi" not in asked
    missing_key = preflight(
        cases, slots, bfcl_root=Path("/bfcl"), environ={}, find_spec=lambda _name: object(),
    )
    assert missing_key == ["provider_key_missing: DEEPSEEK_API_KEY is not set"]
    missing_faiss = preflight(
        cases, slots, bfcl_root=Path("/bfcl"),
        environ={"DEEPSEEK_API_KEY": "present"},
        find_spec=lambda name: None if name == "faiss" else object(),
    )
    assert missing_faiss == ["backend_module_missing: MemoryAPI_vector needs faiss"]


def test_evaluation_registration_keeps_underscore_to_dot(monkeypatch):
    import sys
    import types

    from tool_compression.clean_start.evaluate import model_names, register_models
    from tool_compression.clean_start.pin import REQUEST_MODEL

    assert model_names(("off",)) == [
        "deepseek-flash-thinking-off-U",
        "deepseek-flash-thinking-off-S",
        "deepseek-flash-thinking-off-X",
        "deepseek-flash-thinking-off-SX",
    ]
    created = {}

    class ModelConfig:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            created[kwargs["display_name"]] = kwargs

    reference = types.SimpleNamespace(is_fc_model=True, underscore_to_dot=True)
    mapping = {"DeepSeek-V3.2-Exp-FC": reference}
    modules = {
        "bfcl_eval": types.ModuleType("bfcl_eval"),
        "bfcl_eval.constants": types.ModuleType("bfcl_eval.constants"),
        "bfcl_eval.constants.model_config": types.ModuleType("bfcl_eval.constants.model_config"),
        "bfcl_eval.model_handler": types.ModuleType("bfcl_eval.model_handler"),
        "bfcl_eval.model_handler.api_inference": types.ModuleType("bfcl_eval.model_handler.api_inference"),
        "bfcl_eval.model_handler.api_inference.deepseek": types.ModuleType(
            "bfcl_eval.model_handler.api_inference.deepseek"
        ),
    }
    modules["bfcl_eval.constants.model_config"].MODEL_CONFIG_MAPPING = mapping
    modules["bfcl_eval.constants.model_config"].ModelConfig = ModelConfig
    modules["bfcl_eval.model_handler.api_inference.deepseek"].DeepSeekAPIHandler = object
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)
    register_models(model_names(("off",)))
    for name, config in created.items():
        assert config["model_name"] == REQUEST_MODEL
        assert config["is_fc_model"] is True
        assert config["underscore_to_dot"] is True
        assert name.startswith("deepseek-flash-thinking-off-")


class _FakeResponse:
    def __init__(self, status, data):
        self.status = status
        self._data = data

    def read(self):
        return self._data


class _FakeConnection:
    def __init__(self, status=200, data=b"{}", hang: threading.Event | None = None):
        self.status = status
        self.data = data
        self.hang = hang
        self.closed = False
        self.sent = None

    def request(self, method, path, body=None, headers=None):
        self.sent = (method, path, body, headers)

    def getresponse(self):
        if self.hang is not None:
            self.hang.wait(10)
        return _FakeResponse(self.status, self.data)

    def close(self):
        self.closed = True
        if self.hang is not None:
            self.hang.set()


def test_post_chat_total_deadline_and_status_without_a_socket():
    ok = _FakeConnection(data=json.dumps(_text()).encode())
    payload = post_chat({"model": "deepseek-flash"}, "placeholder", connection_factory=lambda: ok)
    assert payload["choices"][0]["message"]["content"] == "done"
    assert ok.sent[0] == "POST" and ok.sent[1] == "/chat/completions"
    assert ok.sent[3]["Authorization"] == "Bearer placeholder"
    hung = _FakeConnection(hang=threading.Event())
    with pytest.raises(TotalDeadlineExceeded):
        post_chat({}, "placeholder", total_deadline=0.2, connection_factory=lambda: hung)
    assert hung.closed is True
    refused = _FakeConnection(status=503, data=b"busy")
    with pytest.raises(ProviderHTTPError) as error:
        post_chat({}, "placeholder", connection_factory=lambda: refused)
    assert error.value.status == 503


def test_total_deadline_stops_the_run_and_marks_the_attempt_uncertain(tmp_path):
    case = _single_case()
    script = _Scripted([TotalDeadlineExceeded("deadline"), _text()])
    result = execute(
        [case], build_slots([case], ("off",)), tmp_path, script,
        ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock,
    )
    assert len(script.bodies) == 1
    assert result["reason"] == "provider_error:TotalDeadlineExceeded"
    assert result["uncertain_attempts"] == [1]
    assert result["retries"] == 0


def _pinned_root() -> Path | None:
    root = os.environ.get("CLEAN_START_BFCL_ROOT")
    if not root:
        return None
    try:
        from tool_compression.clean_start.runner import OfficialBfclExecutor, resolve_bfcl_package

        OfficialBfclExecutor(resolve_bfcl_package(Path(root)), "probe")
        from bfcl_eval.model_handler.utils import add_memory_instruction_system_prompt  # noqa: F401
        import rank_bm25  # noqa: F401
    except Exception:
        return None
    return resolve_bfcl_package(Path(root))


@pytest.mark.skipif(_pinned_root() is None, reason="CLEAN_START_BFCL_ROOT with importable pinned BFCL not set")
def test_real_pinned_executor_runs_memory_and_file_system_offline(tmp_path):
    from tool_compression.clean_start.load import load_prereqs
    from tool_compression.clean_start.runner import OfficialBfclExecutor
    from tool_compression.clean_start.scope import in_scope_questions

    executor = OfficialBfclExecutor(_pinned_root(), "deepseek_flash")
    prereq = next(case for case in load_prereqs("memory_kv") if case["id"].endswith("-customer-0"))
    question = next(case for case in in_scope_questions("memory_kv") if case["scenario"] == "customer")
    base = in_scope_questions("multi_turn_base")[0]
    add = _tool("core_memory_add", json.dumps({"key": "favourite", "value": "blue"}))
    script = _Scripted([add, _text("noted"), *[_text("ok") for _ in prereq["question"][1:]],
                        _text("blue"), *[_text("ok") for _ in question["question"][1:]],
                        _tool("ls", "{}"), *[_text("listed") for _ in base["question"]]])
    slots = [slot for slot in build_slots([prereq, question, base], ("off",)) if slot["arm"] == "X"]
    result = execute(
        [prereq, question, base], slots, tmp_path, script,
        ceiling_usd=Decimal("1"), thinking_modes=("off",), clock=_clock, executor=executor,
    )
    assert result["complete"] is True, result
    first = script.bodies[0]["messages"][0]
    assert first["role"] == "system" and "memory" in first["content"].lower()
    snapshot = tmp_path / "result/deepseek-flash-thinking-off-X/agentic/memory/kv/memory_snapshot/customer_final.json"
    assert json.loads(snapshot.read_text(encoding="utf-8"))["core_memory"]["favourite"] == "blue"
    tool_texts = [
        message["content"]
        for body in script.bodies
        for message in body["messages"]
        if message.get("role") == "tool"
    ]
    assert any("current_directory_content" in text for text in tool_texts)
