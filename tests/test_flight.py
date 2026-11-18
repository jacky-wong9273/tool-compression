"""Validation-flight runner. No network, no provider key, and no live DeepSeek call."""

from copy import deepcopy
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo
import json

import pytest

from tool_compression.config import DEFAULT_CONFIG, PLACEHOLDER_MODEL
from tool_compression.evaluation import (
    DENOMINATORS,
    PaidInferenceRefused,
    assert_inference_allowed,
    execution_record_gaps,
    execution_record_template,
    freeze_execution_record,
)
from tool_compression.flight_spec import (
    CEILING_CNY,
    is_peak,
    pre_call_reserve_cny,
    remaining_allows_call,
    spend_cny,
    validation_flight_record,
)
from tool_compression.prepare import assemble_request, identity_components, request_hash
from tool_compression.provider import (
    DeepSeekClient,
    DryRunClient,
    MissingApiKey,
    ProviderError,
    ScriptedClient,
    flight_request,
    parse_fc_response,
    require_api_key,
    response_thinking_disabled,
)
from tool_compression.runner import (
    read_hash_rows,
    run_validation_flight,
    select_validation_sample,
)
from tool_compression.usage import usage_from_mapping
from tool_compression.__main__ import main

ROOT = Path(__file__).resolve().parents[1]
SHANGHAI = ZoneInfo("Asia/Shanghai")


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    import urllib.request

    def banned(*args, **kwargs):
        raise AssertionError("live network is disabled in tests")

    monkeypatch.setattr(urllib.request, "urlopen", banned)


def tool(description):
    return {
        "type": "function",
        "function": {
            "name": "ta",
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {"x": {"type": "string", "description": "xxxx"}},
                "required": ["x"],
            },
        },
    }


def case(category, case_id, uncompressed, local, external):
    local_catalogue = [tool(local)]
    return {
        "category": category,
        "id": case_id,
        "messages": [{"role": "user", "content": "task " + case_id}],
        "catalogues": {
            "U": [tool(uncompressed)],
            "P": deepcopy(local_catalogue),
            "I": deepcopy(local_catalogue),
            "C": deepcopy(local_catalogue),
            "E": [tool(external)],
        },
    }


def sample_cases():
    return [
        case("multiple", "m-distinct", "uncompressed", "local text", "external text"),
        case("simple_python", "s-distinct", "uncompressed", "local text", "external text"),
        case("irrelevance", "i-distinct", "uncompressed", "local text", "external text"),
        case("multiple", "m-share", "same text", "same text", "external only"),
    ]


def frozen_record():
    return freeze_execution_record(validation_flight_record())


def off_peak():
    return datetime(2026, 11, 22, 10, 0, tzinfo=SHANGHAI)


def completion(prompt, output, cached=None, reasoning=None):
    usage = {
        "prompt_tokens": prompt,
        "completion_tokens": output,
        "total_tokens": prompt + output,
    }
    if cached is not None:
        usage["prompt_tokens_details"] = {"cached_tokens": cached}
    message = {"role": "assistant", "content": "ok"}
    if reasoning is not None:
        message["reasoning_content"] = reasoning
    return {"choices": [{"index": 0, "message": message, "finish_reason": "stop"}], "usage": usage}


def test_empty_record_and_unlocked_ceiling_and_thinking_stay_refused():
    assert execution_record_template()["paid_inference_authorized"] is False
    with pytest.raises(PaidInferenceRefused):
        assert_inference_allowed(execution_record_template())
    unfrozen = validation_flight_record()
    assert execution_record_gaps(unfrozen) == ["frozen"]
    with pytest.raises(PaidInferenceRefused):
        assert_inference_allowed(unfrozen)
    record = frozen_record()
    assert_inference_allowed(record)
    enabled = deepcopy(record)
    enabled["thinking"] = {"type": "enabled", "pinned_before_any_call": True}
    enabled["provider_options"] = dict(enabled["provider_options"])
    enabled["provider_options"]["thinking"] = {"type": "enabled"}
    with pytest.raises(PaidInferenceRefused):
        assert_inference_allowed(enabled)
    lifted = deepcopy(record)
    lifted["spending_ceiling"] = dict(lifted["spending_ceiling"])
    lifted["spending_ceiling"]["amount"] = "51"
    with pytest.raises(PaidInferenceRefused):
        assert_inference_allowed(lifted)
    missing_ceiling = deepcopy(record)
    missing_ceiling["spending_ceiling"] = None
    assert "spending_ceiling" in execution_record_gaps(missing_ceiling)
    with pytest.raises(PaidInferenceRefused):
        assert_inference_allowed(missing_ceiling)
    unauthorized = deepcopy(record)
    unauthorized["paid_inference_authorized"] = False
    with pytest.raises(PaidInferenceRefused):
        assert_inference_allowed(unauthorized)
    assert record["analysis_configuration"]["target_provider_input_reduction"] == "1/10"
    assert record["analysis_configuration"]["settings"]["retention_r"] == "3/4"
    assert record["analysis_configuration"]["settings"]["lambda"] == "1/2"
    assert record["analysis_configuration"]["retune"] == {
        "r": False,
        "lambda": False,
        "protections": False,
        "neighbour_limits": False,
        "target": False,
    }
    assert record["analysis_configuration"]["denominators"] == DENOMINATORS
    assert record["analysis_configuration"]["l_is_compressor"] is False
    assert DEFAULT_CONFIG.retention_numerator == 3
    assert DEFAULT_CONFIG.lambda_numerator == 1


def test_flight_identity_rehashes_model_and_thinking_without_changing_coincidence():
    messages = [{"role": "user", "content": "task"}]
    same = [tool("alpha")]
    other = [tool("beta")]
    week1 = assemble_request(messages, same)
    selected = assemble_request(messages, same, model="deepseek-flash")
    sent = flight_request(messages, same)
    assert week1["model"] == PLACEHOLDER_MODEL
    assert "thinking" not in week1
    assert sent["model"] == "deepseek-flash"
    assert sent["thinking"] == {"type": "disabled"}
    assert sent["temperature"] == 0.001
    assert sent["store"] is False
    assert "reasoning_effort" not in sent
    assert request_hash(week1) != request_hash(selected)
    assert request_hash(selected) != request_hash(sent)
    parts = identity_components(sent)
    assert parts["provisional"] is False
    assert parts["provider_options"]["thinking"] == {"type": "disabled"}
    assert request_hash(flight_request(messages, same)) == request_hash(flight_request(messages, deepcopy(same)))
    assert request_hash(flight_request(messages, same)) != request_hash(flight_request(messages, other))
    assert (request_hash(assemble_request(messages, same)) == request_hash(assemble_request(messages, other))) is False


def test_week1_sample_ids_are_provisional_selection_not_flight_digests():
    local = read_hash_rows(ROOT / "evidence" / "week1_request_hashes.jsonl")
    arm = read_hash_rows(ROOT / "evidence" / "week1_arm_e_hashes.jsonl")
    selected = select_validation_sample(local, arm)
    assert [item["id"] for item in selected] == [
        "multiple_8",
        "simple_python_38",
        "irrelevance_6",
        "multiple_3",
    ]
    assert [item["category"] for item in selected] == [
        "multiple",
        "simple_python",
        "irrelevance",
        "multiple",
    ]
    assert all(item["provisional"] is True for item in selected)
    assert len({selected[0]["u"], selected[0]["l"], selected[0]["e"]}) == 3
    assert selected[3]["u"] == selected[3]["l"]
    assert selected[3]["e"] != selected[3]["u"]


def test_spend_uses_the_locked_off_peak_card_and_stops_near_the_ceiling():
    assert spend_cny(1_000_000, 1_000_000, 0) == Decimal("0.02")
    assert spend_cny(1_000_000, 0, 0) == Decimal("1")
    assert spend_cny(0, 0, 1_000_000) == Decimal("4")
    assert spend_cny(1_000_000, 500_000, 250_000) == Decimal("1.51")
    reserve = pre_call_reserve_cny()
    assert reserve == Decimal("2.572864")
    assert remaining_allows_call(Decimal("47.427136"), CEILING_CNY, reserve) is True
    assert remaining_allows_call(Decimal("47.427137"), CEILING_CNY, reserve) is False
    assert remaining_allows_call(CEILING_CNY, CEILING_CNY, reserve) is False
    assert remaining_allows_call(Decimal("0"), CEILING_CNY, Decimal("0")) is False
    cost = spend_cny(2_000_000, 0, 0)
    spent = Decimal("0")
    expected = 0
    while remaining_allows_call(spent, CEILING_CNY, reserve):
        expected += 1
        spent += cost
    assert expected == 24
    assert spent <= CEILING_CNY
    assert remaining_allows_call(spent, CEILING_CNY, reserve) is False
    calls = {"n": 0}

    def handler(body):
        calls["n"] += 1
        return 200, completion(2_000_000, 0, cached=0)

    cases = [case("multiple", f"c{index}", "same", "same", "same") for index in range(30)]
    result, out, client = _run(cases, ScriptedClient(handler), stage="a")
    assert client.bodies
    assert calls["n"] == 24
    assert result["stop_reason"] == "remaining_budget_may_be_insufficient"
    assert result["stage_b_started"] is False
    assert Decimal(result["cumulative_cny"]) == spent
    assert not (out / "stage_b").exists()


def test_cache_hit_and_missing_cache_are_billed_differently(tmp_path):
    seen = {"n": 0}

    def handler(body):
        seen["n"] += 1
        if seen["n"] == 1:
            return 200, completion(1_000_000, 0, cached=1_000_000)
        if seen["n"] == 2:
            payload = completion(1_000_000, 0, cached=None)
            payload["usage"]["prompt_cache_hit_tokens"] = 1_000_000
            return 200, payload
        return 200, completion(1, 0, cached=0)

    result, out, client = _run(sample_cases(), ScriptedClient(handler), stage="a")
    assert result["stage_a_validated"] is True
    assert result["target_reached"] is None
    ledger = json.loads((out / "stage_a" / "spend_ledger.json").read_text(encoding="utf-8"))
    first, second = ledger["physical"][0], ledger["physical"][1]
    assert first["cache_hit_tokens"] == 1_000_000
    assert first["cache_assumption"] is None
    assert Decimal(first["cny"]) == Decimal("0.02")
    assert second["cache_hit_tokens"] is None
    assert second["cache_assumption"] == "absent_cache_billed_as_miss"
    assert Decimal(second["cny"]) == Decimal("1")
    usage_ledger = json.loads((out / "stage_a" / "usage_ledger.json").read_text(encoding="utf-8"))
    assert usage_ledger["physical_attempts"][1]["usage"]["cached_input_tokens"] is None
    assert usage_from_mapping({"prompt_tokens": 10, "completion_tokens": 1, "prompt_cache_hit_tokens": 4}).cached_input_tokens is None
    assert all(body["thinking"] == {"type": "disabled"} for body in client.bodies)


def test_auth_payment_and_thinking_stop_before_the_replicate(tmp_path):
    later = [case("multiple", "later", "u", "l", "e")]
    auth = ScriptedClient(lambda body: (401, {"error": {"code": "invalid_api_key"}}))
    result, out, client = _run(sample_cases(), auth, cases_b=later)
    assert result["stop_reason"] == "auth"
    assert result["stage_a_validated"] is False
    assert result["stage_b_started"] is False
    assert len(client.bodies) == 1
    assert not (out / "stage_b").exists()
    slept = []
    payment = ScriptedClient(lambda body: (402, {"error": {"code": "billing"}}))
    result, _, client = _run(sample_cases(), payment, cases_b=later, sleep=slept.append)
    assert result["stop_reason"] == "payment"
    assert result["stage_b_started"] is False
    assert len(client.bodies) == 1
    assert slept == []
    thinking = ScriptedClient(lambda body: (200, completion(10, 1, cached=0, reasoning="chain of thought")))
    result, out, client = _run(sample_cases(), thinking, cases_b=later)
    assert result["stop_reason"] == "thinking_enabled"
    assert result["stage_b_started"] is False
    assert len(client.bodies) == 1
    assert not (out / "stage_b").exists()
    assert response_thinking_disabled(completion(1, 1, reasoning="")) is True
    assert response_thinking_disabled(completion(1, 1)) is True
    assert response_thinking_disabled(completion(1, 1, reasoning="on")) is False


def test_transient_retries_are_bounded_and_a_bad_sample_does_not_start_stage_b():
    slept = []
    state = {"n": 0}

    def handler(body):
        state["n"] += 1
        if state["n"] < 3:
            return 429, {"error": {"code": "rate_limit"}}
        return 200, completion(8, 1, cached=0)

    one = [case("multiple", "only", "same", "same", "same")]
    later = [case("simple_python", "later", "u", "l", "e")]
    result, out, client = _run(one, ScriptedClient(handler), cases_b=later, sleep=slept.append)
    assert state["n"] == 3
    assert slept == [1, 2]
    assert len(client.bodies) == 3
    assert result["stage_a_validated"] is False
    assert result["stage_b_started"] is False
    assert result["stop_reason"] == "stage_a_failed"
    assert not (out / "stage_b").exists()
    usage = json.loads((out / "stage_a" / "usage_ledger.json").read_text(encoding="utf-8"))
    assert [row["status"] for row in usage["physical_attempts"]] == ["failed", "failed", "received"]
    logical = json.loads((out / "stage_a" / "logical_ledger.json").read_text(encoding="utf-8"))
    assert logical["independent_observations"] == 1


def test_shared_requests_are_one_logical_response_and_distinct_groups_call_once_each(tmp_path):
    result, out, client = _run(sample_cases(), DryRunClient(), stage="a", live=False)
    assert result["stage_a_validated"] is True
    assert result["official_settlement"] is False
    assert result["target_reached"] is None
    assert len(client.bodies) == 11
    logical = json.loads((out / "stage_a" / "logical_ledger.json").read_text(encoding="utf-8"))
    shared = [row for row in logical["responses"] if row["members"] == ["U", "L"]]
    assert len(shared) == 1
    assert shared[0]["reused_members"] == ["L"]
    assert shared[0]["group_is_one_independent_observation"] is True
    assert shared[0]["reused_members_are_not_independent_observations"] is True
    distinct = [row for row in logical["responses"] if row["case_id"] == "m-distinct"]
    assert [row["members"] for row in distinct] == [["U"], ["L"], ["E"]]
    assert len({row["request_sha256"] for row in distinct}) == 3
    requests = [
        json.loads(line)
        for line in (out / "stage_a" / "requests.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert all(json.loads(row["body_json"])["thinking"] == {"type": "disabled"} for row in requests)
    parsed = [
        json.loads(line)
        for line in (out / "stage_a" / "parsed.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert parsed[0]["model_responses"] == [{"noop": "{}"}]
    assert parsed[0]["input_token"] is not None
    assert "reasoning_content" not in parsed[0]["model_responses_message_for_chat_history"]
    note = (out / "official_evaluator" / "README.txt").read_text(encoding="utf-8")
    assert "settle the 10% provider-input target" in note


def test_peak_hours_guard_uses_an_injectable_shanghai_clock(tmp_path):
    assert is_peak(datetime(2026, 11, 16, 8, 59, 59, tzinfo=SHANGHAI)) is False
    assert is_peak(datetime(2026, 11, 16, 9, 0, tzinfo=SHANGHAI)) is True
    assert is_peak(datetime(2026, 11, 16, 11, 59, 59, tzinfo=SHANGHAI)) is True
    assert is_peak(datetime(2026, 11, 16, 12, 0, tzinfo=SHANGHAI)) is False
    assert is_peak(datetime(2026, 11, 16, 13, 59, 59, tzinfo=SHANGHAI)) is False
    assert is_peak(datetime(2026, 11, 16, 14, 0, tzinfo=SHANGHAI)) is True
    assert is_peak(datetime(2026, 11, 16, 17, 59, 59, tzinfo=SHANGHAI)) is True
    assert is_peak(datetime(2026, 11, 16, 18, 0, tzinfo=SHANGHAI)) is False
    assert is_peak(datetime(2026, 11, 21, 10, 0, tzinfo=SHANGHAI)) is False
    assert is_peak(datetime(2026, 11, 22, 15, 0, tzinfo=SHANGHAI)) is False
    client = ScriptedClient(lambda body: (200, completion(5, 1, cached=0)))
    result, _, _ = _run(
        sample_cases(),
        client,
        clock=lambda: datetime(2026, 11, 16, 10, 0, tzinfo=SHANGHAI),
    )
    assert result["stop_reason"] == "peak_hours"
    assert client.bodies == []
    state = {"now": off_peak()}

    def handler(body):
        state["now"] = datetime(2026, 11, 16, 10, 0, tzinfo=SHANGHAI)
        return 200, completion(5, 1, cached=0)

    client = ScriptedClient(handler)
    result, out, _ = _run(sample_cases(), client, clock=lambda: state["now"])
    assert len(client.bodies) == 1
    assert result["stop_reason"] == "peak_hours"
    assert result["stage_b_started"] is False
    assert (out / "stage_a" / "spend_ledger.json").is_file()


def test_identity_mismatch_stops_before_a_call_and_parse_follows_the_handler_shape():
    mismatched = sample_cases()
    mismatched[0] = dict(mismatched[0])
    mismatched[0]["provisional"] = {"U": "same", "L": "same", "E": "same"}
    client = ScriptedClient(lambda body: (200, completion(5, 1, cached=0)))
    result, _, _ = _run(mismatched, client, stage="a")
    assert result["stop_reason"] == "identity_mismatch"
    assert client.bodies == []
    payload = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "get_weather", "arguments": "{\"city\":\"Paris\"}"},
                        }
                    ],
                    "reasoning_content": None,
                }
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 2, "prompt_tokens_details": {"cached_tokens": 4}},
    }
    parsed = parse_fc_response(payload)
    assert parsed["model_responses"] == [{"get_weather": "{\"city\":\"Paris\"}"}]
    assert parsed["tool_call_ids"] == ["call_1"]
    assert parsed["input_token"] == 10
    assert parsed["output_token"] == 2
    assert "reasoning_content" not in parsed["model_responses_message_for_chat_history"]
    assert response_thinking_disabled(payload) is True
    plain = {"choices": [{"message": {"role": "assistant", "content": "hello"}}], "usage": {"prompt_tokens": 3, "completion_tokens": 1}}
    assert parse_fc_response(plain)["model_responses"] == "hello"
    with pytest.raises(ProviderError):
        ScriptedClient(lambda body: (200, completion(1, 1))).complete(
            {"model": "deepseek-flash", "messages": [], "temperature": 0.001, "store": False}
        )


def test_cli_freezes_the_record_and_dry_run_does_not_need_a_key(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    record_path = tmp_path / "execution_record.json"
    assert main(["freeze-record", "--out", str(record_path)]) == 0
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["frozen"] is True
    assert record["thinking"]["type"] == "disabled"
    assert record["spending_ceiling"]["amount"] == "50"
    assert record["purpose"] == "validation-and-prep"
    assert record["api_key_source"] == "DEEPSEEK_API_KEY"
    assert "api_key" not in record
    assert_inference_allowed(record)
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(json.dumps(sample_cases()), encoding="utf-8")
    out = tmp_path / "flight"

    # The CLI reads the wall clock. Sunday morning in Shanghai is off-peak,
    # so this dry run does not stop for the weekday peak window.
    class _OffPeak(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 22, 10, 0, tzinfo=SHANGHAI)

    monkeypatch.setattr("tool_compression.runner.datetime", _OffPeak)
    status = main(
        [
            "validate-flight",
            "--record",
            str(record_path),
            "--cases",
            str(cases_path),
            "--out",
            str(out),
            "--no-api",
        ]
    )
    assert status == 0
    summary = json.loads((out / "flight_summary.json").read_text(encoding="utf-8"))
    assert summary["stage_a_validated"] is True
    assert summary["stage_b_started"] is True
    assert summary["stage_b_completed"] is True
    assert summary["dry_run"] is True
    assert summary["official_accuracy"] is False
    assert summary["target_reached"] is None
    assert summary["all_category_replicate"] is False
    blob = "\n".join(path.read_text(encoding="utf-8") for path in out.rglob("*") if path.is_file())
    assert "Bearer " not in blob
    identity = json.loads((out / "identity_recheck.json").read_text(encoding="utf-8"))
    assert identity["week1_digests_are_flight_identity"] is False
    assert identity["week1_model"] == "UNSELECTED"
    monkeypatch.setenv("DEEPSEEK_API_KEY", "   ")
    with pytest.raises(MissingApiKey) as caught:
        require_api_key()
    assert "blank" in str(caught.value)
    monkeypatch.delenv("DEEPSEEK_API_KEY")
    with pytest.raises(MissingApiKey) as missing:
        require_api_key()
    assert "not set" in str(missing.value)


def test_a_dry_run_sample_does_not_unlock_a_live_replicate(tmp_path):
    out = tmp_path / "flight"
    first = run_validation_flight(
        frozen_record(),
        out,
        cases_a=sample_cases(),
        live=False,
        clock=off_peak,
        sleep=lambda seconds: None,
        stage="a",
    )
    assert first["stage_a_validated"] is True
    assert first["live_provider"] is False
    client = ScriptedClient(lambda body: (200, completion(3, 1, cached=0)))
    second = run_validation_flight(
        frozen_record(),
        out,
        cases_b=sample_cases(),
        client=client,
        live=True,
        clock=off_peak,
        sleep=lambda seconds: None,
        stage="b",
    )
    assert second["stage_b_started"] is False
    assert second["stop_reason"] == "stage_a_not_validated"
    assert client.bodies == []


def test_client_does_not_echo_a_placeholder_and_refuses_other_hosts(monkeypatch):
    import urllib.request

    placeholder = "placeholder-value"
    seen = {}

    class Response:
        status = 200

        def read(self):
            return json.dumps(completion(4, 1, cached=0)).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(request, timeout=None):
        seen["header"] = request.get_header("Authorization")
        seen["body"] = request.data.decode("utf-8")
        return Response()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    from tool_compression.provider import UrllibChatTransport

    client = DeepSeekClient(placeholder, UrllibChatTransport())
    assert placeholder not in repr(client)
    body = flight_request([{"role": "user", "content": "task"}], [tool("alpha")])
    payload = client.complete(body)
    assert payload["usage"]["prompt_tokens"] == 4
    assert seen["header"] == "Bearer " + placeholder
    assert placeholder not in seen["body"]
    assert '"type": "disabled"' in seen["body"] or '"type":"disabled"' in seen["body"]
    with pytest.raises(ProviderError):
        DeepSeekClient(placeholder, UrllibChatTransport(), "http://api.deepseek.com")
    with pytest.raises(ProviderError):
        DeepSeekClient(placeholder, UrllibChatTransport(), "https://example.com")

    def timed_out(request, timeout=None):
        raise TimeoutError("timed out")

    monkeypatch.setattr(urllib.request, "urlopen", timed_out)
    with pytest.raises(ProviderError) as caught:
        client.complete(body)
    assert caught.value.kind == "transient"
    assert placeholder not in str(caught.value)


def _run(cases, client, *, cases_b=None, stage="all", clock=None, sleep=None, live=True):
    from tempfile import mkdtemp

    out = Path(mkdtemp())
    result = run_validation_flight(
        frozen_record(),
        out,
        cases_a=cases,
        cases_b=cases_b,
        client=client,
        live=live,
        clock=clock or off_peak,
        sleep=sleep or (lambda seconds: None),
        stage=stage,
    )
    return result, out, client
