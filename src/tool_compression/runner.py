"""Two-stage validation flight. Stage B starts only after stage A validates.

This module does not score official accuracy or the 10% provider target.
Week 1 request digests stay provisional: flight identity is recomputed after
the model and the sent options, including thinking disabled, are substituted.
"""

from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import json
import time

from tool_compression.config import DEFAULT_CONFIG
from tool_compression.evaluation import (
    DENOMINATORS,
    PaidInferenceRefused,
    assert_inference_allowed,
    prepare_case,
)
from tool_compression.flight_spec import (
    CEILING_CNY,
    PLACEHOLDER_MODEL,
    format_cny,
    is_peak,
    pre_call_reserve_cny,
    remaining_allows_call,
    spend_cny,
)
from tool_compression.grouping import comparison_condition_hashes, group_exact_requests
from tool_compression.implementations import ExternalSnapshot, reference_implementations
from tool_compression.prepare import dump_request, request_hash
from tool_compression.provider import (
    DryRunClient,
    assert_request_thinking_off,
    flight_request,
    parse_fc_response,
    response_thinking_disabled,
    scrub,
)
from tool_compression.provider import ProviderError
from tool_compression.usage import ProviderUsage, UsageLedger, usage_from_mapping

CATEGORIES = ("multiple", "simple_python", "irrelevance")
OFFICIAL_EVALUATOR_NOTE = (
    "Place later official-evaluator output in this directory.\n"
    "This validation flight does not write official accuracy and does not\n"
    "settle the 10% provider-input target. Do not treat stage A or stage B\n"
    "artifacts as that settlement.\n"
)


class FlightAccount:
    """Physical attempts, logical shared responses, and cumulative CNY."""

    def __init__(self, ceiling: Decimal, reserve: Decimal, opening: Decimal = Decimal("0")):
        self.ceiling = ceiling
        self.reserve = reserve
        self.spent = opening
        self.attempts: list[dict] = []
        self.logical: list[dict] = []
        self.ledger = UsageLedger()
        self.payloads: list[dict] = []
        self.parsed: list[dict] = []

    def allows(self) -> bool:
        return remaining_allows_call(self.spent, self.ceiling, self.reserve)

    def add_failure(self, plan: dict, error: ProviderError) -> None:
        usage = ProviderUsage()
        self.ledger.record_attempt(
            response_group_id=plan["response_group_id"],
            case_id=plan["case_id"],
            replicate=plan["replicate"],
            members=plan["members"],
            status="failed",
            usage=usage,
        )
        self.attempts.append(_attempt_row(plan, status="failed", usage=usage, cny=None, assumption=None, http_status=error.status, note=error.kind))
        self.payloads.append({"error": str(error), "http_status": error.status})
        self.parsed.append({"thinking_disabled": None, "error": error.kind, "http_status": error.status})

    def add_received(self, plan: dict, payload: dict, usage: ProviderUsage, thinking_ok: bool) -> str | None:
        """Record one HTTP 200. Return a stop code, or None when the call is usable."""
        assumption = None
        amount = None
        code = None
        cache_missing = usage.cached_input_tokens is None
        if usage.total_input_tokens is None or usage.output_tokens is None:
            code = "missing_usage"
        else:
            cache_for_bill = 0 if cache_missing else usage.cached_input_tokens
            if cache_missing:
                assumption = "absent_cache_billed_as_miss"
            try:
                amount = spend_cny(usage.total_input_tokens, cache_for_bill, usage.output_tokens)
            except ValueError:
                code = "accounting_error"
            else:
                self.spent += amount
                if amount > self.reserve:
                    code = "spend_above_pre_call_reserve"
        usable = code in {None, "spend_above_pre_call_reserve"} and thinking_ok
        status = "received" if usable else "failed"
        self.ledger.record_attempt(
            response_group_id=plan["response_group_id"],
            case_id=plan["case_id"],
            replicate=plan["replicate"],
            members=plan["members"],
            status=status,
            usage=usage,
        )
        self.attempts.append(
            _attempt_row(
                plan,
                status=status,
                usage=usage,
                cny=amount,
                assumption=assumption,
                http_status=200,
                note=None if thinking_ok else "thinking_enabled",
            )
        )
        self.payloads.append(payload)
        try:
            parsed = parse_fc_response(payload)
        except Exception:
            parsed = {}
        parsed = dict(parsed)
        parsed["thinking_disabled"] = thinking_ok
        parsed["response_group_id"] = plan["response_group_id"]
        self.parsed.append(parsed)
        if usable:
            self.logical.append(_logical_row(plan, usage, assumption))
        if not thinking_ok:
            return "thinking_enabled"
        if code in {"missing_usage", "accounting_error"}:
            return code
        if self.spent > self.ceiling:
            return "ceiling_exceeded"
        return code


def _attempt_row(plan, *, status, usage: ProviderUsage, cny, assumption, http_status, note) -> dict:
    return {
        "response_group_id": plan["response_group_id"],
        "protocol_shared_response_id": plan["protocol_shared_response_id"],
        "case_id": plan["case_id"],
        "category": plan["category"],
        "replicate": plan["replicate"],
        "members": list(plan["members"]),
        "reused_members": list(plan["members"][1:]),
        "request_sha256": plan["request_sha256"],
        "status": status,
        "http_status": http_status,
        "input_tokens": usage.total_input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_hit_tokens": usage.cached_input_tokens,
        "cache_assumption": assumption,
        "cny": None if cny is None else format_cny(cny),
        "note": note,
        "logical_usage_is_not_multiplied_by_members": True,
    }


def _logical_row(plan, usage: ProviderUsage, assumption) -> dict:
    return {
        "response_group_id": plan["response_group_id"],
        "protocol_shared_response_id": plan["protocol_shared_response_id"],
        "case_id": plan["case_id"],
        "category": plan["category"],
        "replicate": plan["replicate"],
        "members": list(plan["members"]),
        "reused_members": list(plan["members"][1:]),
        "originating_request_group": plan["protocol_shared_response_id"],
        "group_is_one_independent_observation": True,
        "reused_members_are_not_independent_observations": len(plan["members"]) > 1,
        "request_sha256": plan["request_sha256"],
        "input_tokens": usage.total_input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_hit_tokens": usage.cached_input_tokens,
        "cache_hit_missing": usage.cached_input_tokens is None,
        "cache_assumption": assumption,
        "physical_attempt_indexes": "see spend ledger",
    }


def select_validation_sample(local_rows: list[dict], arm_rows: list[dict]) -> list[dict]:
    """Pick a cheap U/L/E sample from provisional Week 1 hashes.

    The hashes select cases. They are not the flight request identity.
    """
    arm = {(row.get("category"), row.get("id")): row for row in arm_rows}
    buckets = {name: [] for name in CATEGORIES}
    for row in local_rows:
        if row.get("preparation_failure"):
            continue
        category = row.get("category")
        hashes = row.get("hashes") or {}
        if category not in buckets or any(name not in hashes for name in ("U", "P", "I", "C")):
            continue
        if not (hashes["P"] == hashes["I"] == hashes["C"]):
            continue
        external = arm.get((category, row.get("id")))
        if not external or not external.get("ok") or not external.get("hash"):
            continue
        buckets[category].append(
            {
                "category": category,
                "id": row["id"],
                "u": hashes["U"],
                "l": hashes["P"],
                "e": external["hash"],
                "provisional": True,
            }
        )
    chosen = []
    for category in CATEGORIES:
        match = next((item for item in buckets[category] if len({item["u"], item["l"], item["e"]}) == 3), None)
        if match is None:
            raise ValueError(f"no distinct provisional U/L/E case in {category}")
        chosen.append(dict(match))
    share = next(
        (item for item in buckets["multiple"] if item["u"] == item["l"] and item["e"] != item["u"]),
        None,
    )
    if share is None:
        raise ValueError("no provisional case where U and L coincide and E differs")
    chosen.append(dict(share))
    return chosen


def attach_provisional(cases: list[dict], local_rows: list[dict], arm_rows: list[dict]) -> None:
    """Attach Week 1 equality partitions so the flight can recheck them.

    The stored digests are not copied into request identity.
    """
    arm = {(row.get("category"), row.get("id")): row for row in arm_rows}
    index = {}
    for row in local_rows:
        if row.get("preparation_failure"):
            continue
        hashes = row.get("hashes") or {}
        if any(name not in hashes for name in ("U", "P", "I", "C")):
            continue
        external = arm.get((row.get("category"), row.get("id")))
        if not external or not external.get("ok") or not external.get("hash"):
            continue
        local = {name: hashes[name] for name in ("U", "P", "I", "C")}
        index[(row.get("category"), row.get("id"))] = comparison_condition_hashes(local, external["hash"])
    for case in cases:
        provisional = index.get((case.get("category"), case.get("id")))
        if provisional is not None:
            case["provisional"] = provisional


def select_prepared_sample(cases: list[dict]) -> list[dict]:
    """Same sample rule as the Week 1 selector, using flight request partitions."""
    described = []
    for case in cases:
        plans, mismatches = build_plans([case], "stage_a")
        if mismatches:
            raise ValueError("provisional partition does not match the flight request")
        described.append((case, [frozenset(plan["members"]) for plan in plans]))
    chosen = []
    distinct = {frozenset({"U"}), frozenset({"L"}), frozenset({"E"})}
    for category in CATEGORIES:
        match = next((case for case, members in described if case["category"] == category and distinct <= set(members)), None)
        if match is None:
            raise ValueError(f"no distinct U/L/E case in {category}")
        chosen.append(match)
    share = next(
        (
            case
            for case, members in described
            if case["category"] == "multiple" and frozenset({"U", "L"}) in members and frozenset({"E"}) in members
        ),
        None,
    )
    if share is None:
        raise ValueError("no case where U and L coincide and E differs")
    chosen.append(share)
    return chosen


def prepare_study_cases(study: dict, tscg_root: Path, script: Path, *, ids: list[tuple[str, str]] | None = None, timeout: int = 300) -> list[dict]:
    """Compress the selected BFCL records locally and with pinned TSCG. No model call."""
    from tool_compression.count import study_counters
    from tool_compression.external import compress_external_catalogues
    from tool_compression.prepare import convert_record

    ordered = []
    for category in CATEGORIES:
        for record in study[category]:
            if ids is not None and (category, record["id"]) not in ids:
                continue
            ordered.append((category, record))
    if ids is not None:
        by_key = {(category, record["id"]): record for category, record in ordered}
        missing = [key for key in ids if key not in by_key]
        if missing:
            raise ValueError("selected case is not in the BFCL study: " + ",".join(f"{a}/{b}" for a, b in missing))
        ordered = [(category, by_key[(category, case_id)]) for category, case_id in ids]
    catalogues = [convert_record(record) for _, record in ordered]
    produced = compress_external_catalogues(catalogues, Path(tscg_root), Path(script), timeout=timeout)
    counter = study_counters()[0]
    cases = []
    for (category, record), catalogue, external in zip(ordered, catalogues, produced):
        messages = record["question"][0]
        prepared = prepare_case(
            catalogue,
            messages,
            {**reference_implementations(), "E": ExternalSnapshot(external)},
            DEFAULT_CONFIG,
            counter,
            category=category,
            case_id=str(record["id"]),
            model="deepseek-flash",
        )
        cases.append(
            {
                "category": category,
                "id": record["id"],
                "messages": messages,
                "catalogues": prepared["catalogues"],
            }
        )
    return cases


def build_plans(cases: list[dict], stage: str, replicate: int = 0) -> tuple[list[dict], list[dict]]:
    plans = []
    mismatches = []
    for case in cases:
        _require_case(case)
        requests = {}
        hashes = {}
        for name, catalogue in case["catalogues"].items():
            body = flight_request(case["messages"], catalogue)
            requests[name] = body
            hashes[name] = request_hash(body)
        local = {name: hashes[name] for name in ("U", "P", "I", "C")}
        conditions = comparison_condition_hashes(local, hashes.get("E"))
        groups = group_exact_requests(case["category"], str(case["id"]), replicate, conditions)
        flight_map = {member: group.request_hash for group in groups for member in group.members}
        provisional = case.get("provisional")
        if isinstance(provisional, dict):
            if _partition(provisional) != _partition(flight_map):
                mismatches.append(
                    {
                        "category": case["category"],
                        "id": case["id"],
                        "provisional_partition": _partition_lists(provisional),
                        "flight_partition": _partition_lists(flight_map),
                    }
                )
        for group in groups:
            body = _body_for(group.members[0], requests, hashes)
            digest = request_hash(body)
            if digest != group.request_hash:
                raise RuntimeError("flight request hash does not match the group")
            plans.append(
                {
                    "stage": stage,
                    "category": case["category"],
                    "case_id": str(case["id"]),
                    "replicate": replicate,
                    "members": group.members,
                    "response_group_id": f"{stage}/{group.shared_response_id}",
                    "protocol_shared_response_id": group.shared_response_id,
                    "request_sha256": digest,
                    "body": body,
                    "body_json": dump_request(body),
                }
            )
    return plans, mismatches


def run_validation_flight(
    record: dict,
    out: Path,
    *,
    cases_a: list[dict] | None = None,
    cases_b: list[dict] | None = None,
    client=None,
    live: bool = False,
    clock=None,
    sleep=None,
    stage: str = "all",
) -> dict:
    """Run stage A and, only when that sample validates, stage B.

    ``--no-api`` uses ``DryRunClient``. A failed sample does not start B.
    """
    if stage not in {"all", "a", "b"}:
        raise ValueError("stage must be all, a, or b")
    assert_inference_allowed(record)
    if client is None:
        client = _default_client(record, live)
    secret = getattr(client, "_api_key", None)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    _write_text(out / "official_evaluator" / "README.txt", OFFICIAL_EVALUATOR_NOTE, secret)
    _write_json(out / "execution_record.json", record, secret)
    clock = clock or (lambda: datetime.now(timezone.utc))
    sleep = sleep or time.sleep
    ceiling = CEILING_CNY
    reserve = pre_call_reserve_cny()
    result = {
        "ok": False,
        "purpose": "validation-and-prep",
        "official_accuracy": False,
        "official_settlement": False,
        "target_reached": None,
        "target_status": "not_assessed_validation_and_prep",
        "dry_run": not live,
        "live_provider": live,
        "stage_a_validated": False,
        "stage_b_started": False,
        "stage_b_completed": False,
        "stop_reason": None,
        "cumulative_cny": "0",
        "all_category_replicate": False,
        "settings_retuned": False,
        "out": str(out),
    }
    try:
        if stage == "b":
            return _continue_stage_b(record, out, cases_b or [], client, live, clock, sleep, ceiling, reserve, secret, result)
        if cases_a is None:
            raise ValueError("stage A needs prepared cases")
        opening = Decimal("0")
        if is_peak(clock()):
            result["stop_reason"] = "peak_hours"
            _write_identity(out, [], [], secret)
            _write_json(out / "flight_summary.json", result, secret)
            return result
        plans, mismatches = build_plans(cases_a, "stage_a")
        _write_identity(out, cases_a, mismatches, secret)
        if mismatches:
            result["stop_reason"] = "identity_mismatch"
            _write_stage(out / "stage_a", plans, FlightAccount(ceiling, reserve), "identity_mismatch", live, False, secret)
            _write_json(out / "flight_summary.json", result, secret)
            return result
        account = FlightAccount(ceiling, reserve, opening)
        stop = _execute(plans, account, client, record, clock, sleep)
        validated = _stage_a_checks(plans, account, stop, cases_a)
        if not validated and stop is None:
            stop = "stage_a_failed"
        _write_stage(out / "stage_a", plans, account, stop, live, validated, secret)
        result["stage_a_validated"] = validated
        result["cumulative_cny"] = format_cny(account.spent)
        if stage == "a":
            result["ok"] = validated
            result["stop_reason"] = None if validated else stop
            _write_json(out / "flight_summary.json", result, secret)
            return result
        if not validated:
            result["stop_reason"] = stop or "stage_a_failed"
            result["stage_b_started"] = False
            _write_json(out / "flight_summary.json", result, secret)
            return result
        if not cases_b:
            result["stop_reason"] = "stage_b_cases_missing"
            _write_json(out / "flight_summary.json", result, secret)
            return result
        return _run_stage_b(record, out, cases_b, client, live, clock, sleep, account, secret, result)
    except PaidInferenceRefused:
        raise
    except Exception as exc:
        result["stop_reason"] = "runner_error"
        result["error"] = scrub(str(exc), secret)[:200]
        _write_json(out / "flight_summary.json", result, secret)
        raise


def load_cases_file(path: Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = data["cases"] if isinstance(data, dict) else data
    if not isinstance(cases, list) or not cases:
        raise ValueError("cases file is empty")
    for case in cases:
        _require_case(case)
    return cases


def cumulative_from_ledger(path: Path) -> Decimal:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    total = Decimal("0")
    for row in payload["physical"]:
        if row["cny"] is not None:
            total += Decimal(row["cny"])
    if Decimal(payload["cumulative_cny"]) != total:
        raise ValueError("spend ledger cumulative does not match its rows")
    return total


def _continue_stage_b(record, out, cases_b, client, live, clock, sleep, ceiling, reserve, secret, result):
    summary_path = out / "stage_a" / "summary.json"
    if not summary_path.is_file():
        result["stop_reason"] = "stage_a_not_validated"
        _write_json(out / "flight_summary.json", result, secret)
        return result
    prior = json.loads(summary_path.read_text(encoding="utf-8"))
    if prior.get("validated") is not True or prior.get("live_provider") is not live:
        result["stop_reason"] = "stage_a_not_validated"
        _write_json(out / "flight_summary.json", result, secret)
        return result
    if not cases_b:
        result["stop_reason"] = "stage_b_cases_missing"
        _write_json(out / "flight_summary.json", result, secret)
        return result
    opening = cumulative_from_ledger(out / "stage_a" / "spend_ledger.json")
    account = FlightAccount(ceiling, reserve, opening)
    result["stage_a_validated"] = True
    return _run_stage_b(record, out, cases_b, client, live, clock, sleep, account, secret, result)


def _run_stage_b(record, out, cases_b, client, live, clock, sleep, account, secret, result):
    result["stage_b_started"] = True
    before = len(account.attempts)
    if is_peak(clock()):
        result["stop_reason"] = "peak_hours"
        result["stage_b_completed"] = False
        _write_json(out / "flight_summary.json", result, secret)
        return result
    plans, mismatches = build_plans(cases_b, "stage_b")
    if mismatches:
        result["stop_reason"] = "identity_mismatch"
        _write_stage(out / "stage_b", plans, account, "identity_mismatch", live, False, secret, opening_attempts=before)
        _write_json(out / "flight_summary.json", result, secret)
        return result
    stop = _execute(plans, account, client, record, clock, sleep)
    completed = stop is None and _groups_completed(plans, account, before)
    _write_stage(out / "stage_b", plans, account, stop, live, completed, secret, opening_attempts=before)
    result["stage_b_completed"] = completed
    result["stop_reason"] = stop
    result["ok"] = completed
    result["cumulative_cny"] = format_cny(account.spent)
    result["all_category_replicate"] = _full_replicate(cases_b) and completed
    result["stage_b_cases"] = len(cases_b)
    _write_json(out / "flight_summary.json", result, secret)
    return result


def _execute(plans, account: FlightAccount, client, record, clock, sleep) -> str | None:
    policy = record["failure_policy"]
    for plan in plans:
        assert_inference_allowed(record)
        assert_request_thinking_off(plan["body"])
        retries = 0
        while True:
            if is_peak(clock()):
                return "peak_hours"
            if not account.allows():
                return "remaining_budget_may_be_insufficient"
            try:
                payload = client.complete(plan["body"])
            except ProviderError as exc:
                account.add_failure(plan, exc)
                if exc.kind in {"auth", "payment"}:
                    return exc.kind
                if exc.kind == "transient" and retries < policy["max_retries"]:
                    sleep(policy["backoff_seconds"][retries])
                    retries += 1
                    continue
                if exc.kind == "transient":
                    return "transient_exhausted"
                return "request_error"
            usage = usage_from_mapping(payload)
            thinking_ok = response_thinking_disabled(payload)
            code = account.add_received(plan, payload, usage, thinking_ok)
            if code:
                return code
            break
    return None


def _stage_a_checks(plans, account: FlightAccount, stop, cases) -> bool:
    if stop is not None or not _groups_completed(plans, account, 0):
        return False
    if not plans:
        return False
    if any(plan["body"].get("thinking") != {"type": "disabled"} for plan in plans):
        return False
    if any(row.get("note") == "thinking_enabled" for row in account.attempts):
        return False
    if any(item.get("thinking_disabled") is False for item in account.parsed):
        return False
    if any(row["status"] == "received" and (row["input_tokens"] is None or row["output_tokens"] is None) for row in account.attempts):
        return False
    if len(account.logical) != len(plans):
        return False
    members = {member for plan in plans for member in plan["members"]}
    categories = {case["category"] for case in cases}
    shared = any(len(plan["members"]) > 1 for plan in plans)
    distinct = _has_distinct_ule(plans)
    return {"U", "L", "E"} <= members and len(categories) >= 2 and shared and distinct


def _groups_completed(plans, account: FlightAccount, start: int) -> bool:
    done = {
        row["response_group_id"]
        for row in account.logical
    }
    return all(plan["response_group_id"] in done for plan in plans) and len(account.attempts) >= start


def _has_distinct_ule(plans) -> bool:
    by_case = {}
    for plan in plans:
        by_case.setdefault(plan["case_id"], []).append(frozenset(plan["members"]))
    needed = {frozenset({"U"}), frozenset({"L"}), frozenset({"E"})}
    return any(needed <= set(groups) for groups in by_case.values())


def _full_replicate(cases: list[dict]) -> bool:
    counts = Counter(case["category"] for case in cases)
    return all(counts.get(name) == expected for name, expected in DENOMINATORS.items())


def _write_stage(directory: Path, plans, account: FlightAccount, stop, live: bool, validated: bool, secret, opening_attempts: int = 0) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    rows = account.attempts[opening_attempts:]
    payloads = account.payloads[opening_attempts:]
    parsed = account.parsed[opening_attempts:]
    if plans:
        prefix = plans[0]["stage"] + "/"
        logical = [row for row in account.logical if str(row["response_group_id"]).startswith(prefix)]
    else:
        logical = []
    request_lines = []
    response_lines = []
    parsed_lines = []
    sent = {row["response_group_id"] for row in rows}
    for plan in plans:
        if plan["response_group_id"] not in sent:
            continue
        request_lines.append(
            {
                "response_group_id": plan["response_group_id"],
                "members": list(plan["members"]),
                "request_sha256": plan["request_sha256"],
                "body_json": plan["body_json"],
            }
        )
    for payload, item in zip(payloads, parsed):
        response_lines.append(payload)
        parsed_lines.append(item)
    _write_jsonl(directory / "requests.jsonl", request_lines, secret)
    _write_jsonl(directory / "responses.jsonl", response_lines, secret)
    _write_jsonl(directory / "parsed.jsonl", parsed_lines, secret)
    _write_json(directory / "usage_ledger.json", _usage_dump(account.ledger, opening_attempts), secret)
    _write_json(directory / "logical_ledger.json", {"responses": logical, "independent_observations": len(logical)}, secret)
    physical_cny = [Decimal(row["cny"]) for row in rows if row["cny"] is not None]
    stage_cny = sum(physical_cny, Decimal("0"))
    spend = {
        "currency": "CNY",
        "rate_card": "off-peak locked ¥0.02 cache hit, ¥1 cache miss, ¥4 output per million",
        "ceiling_cny": "50",
        "physical": rows,
        "groups": _group_rollup(rows, logical),
        "stage_cny": format_cny(stage_cny),
        "cumulative_cny": format_cny(account.spent),
        "logical_usage_is_not_multiplied_by_members": True,
    }
    _write_json(directory / "spend_ledger.json", spend, secret)
    members = sorted({member for plan in plans for member in plan["members"]})
    summary = {
        "purpose": "validation-and-prep",
        "official_accuracy": False,
        "official_settlement": False,
        "target_reached": None,
        "target_status": "not_assessed_validation_and_prep",
        "dry_run": not live,
        "live_provider": live,
        "thinking_off_confirmed_by_provider": bool(live and validated),
        "validated": validated,
        "stop_reason": stop,
        "groups_planned": len(plans),
        "groups_completed": len(logical),
        "physical_attempts": len(rows),
        "logical_responses": len(logical),
        "categories": sorted({plan["category"] for plan in plans}),
        "case_ids": list(dict.fromkeys(plan["case_id"] for plan in plans)),
        "members_seen": members,
        "cumulative_cny": format_cny(account.spent),
        "stage_cny": format_cny(stage_cny),
        "ceiling_cny": "50",
        "usage_accounted": all(row["cny"] is not None or row["status"] != "received" for row in rows),
    }
    _write_json(directory / "summary.json", summary, secret)


def _group_rollup(rows: list[dict], logical: list[dict]) -> list[dict]:
    logical_by_id = {row["response_group_id"]: row for row in logical}
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["response_group_id"], []).append(row)
    rollup = []
    for group_id, attempts in grouped.items():
        known = [Decimal(item["cny"]) for item in attempts if item["cny"] is not None]
        shared = logical_by_id.get(group_id)
        rollup.append(
            {
                "response_group_id": group_id,
                "members": attempts[0]["members"],
                "reused_members": attempts[0]["reused_members"],
                "input_tokens": None if shared is None else shared["input_tokens"],
                "output_tokens": None if shared is None else shared["output_tokens"],
                "cache_hit_tokens": None if shared is None else shared["cache_hit_tokens"],
                "cache_hit_missing": None if shared is None else shared["cache_hit_missing"],
                "cache_assumption": None if shared is None else shared["cache_assumption"],
                "physical_attempts": len(attempts),
                "cny": format_cny(sum(known, Decimal("0"))) if known else None,
                "group_is_one_independent_observation": shared is not None,
                "reused_members_are_not_independent_observations": bool(attempts[0]["reused_members"]),
            }
        )
    return rollup


def _usage_dump(ledger: UsageLedger, start: int) -> dict:
    rows = []
    for row in ledger.attempts[start:]:
        usage = row["usage"]
        rows.append(
            {
                "response_group_id": row["response_group_id"],
                "case_id": row["case_id"],
                "replicate": row["replicate"],
                "members": list(row["members"]),
                "status": row["status"],
                "usage": {
                    "total_input_tokens": usage.total_input_tokens,
                    "cached_input_tokens": usage.cached_input_tokens,
                    "output_tokens": usage.output_tokens,
                },
            }
        )
    return {"physical_attempts": rows, "count": len(rows)}


def _write_identity(out: Path, cases: list[dict], mismatches: list[dict], secret) -> None:
    checked = []
    for case in cases:
        if not isinstance(case.get("provisional"), dict):
            checked.append({"category": case.get("category"), "id": case.get("id"), "provisional": False})
            continue
        checked.append(
            {
                "category": case.get("category"),
                "id": case.get("id"),
                "provisional": True,
                "matches_flight_partition": not any(
                    item["id"] == case.get("id") and item["category"] == case.get("category") for item in mismatches
                ),
            }
        )
    payload = {
        "week1_model": PLACEHOLDER_MODEL,
        "flight_model": "deepseek-flash",
        "week1_digests_are_flight_identity": False,
        "coincidence_preserved_when_options_are_uniform": True,
        "checked_cases": checked,
        "mismatches": mismatches,
        "note": (
            "Week 1 hashes used model UNSELECTED and omitted thinking. Flight "
            "identity is recomputed from the model, messages, catalogue, and "
            "the options actually sent, including thinking disabled. Uniform "
            "options preserve which conditions coincide. The provisional "
            "digest strings are not reused as flight identity."
        ),
    }
    _write_json(out / "identity_recheck.json", payload, secret)


def _default_client(record, live: bool):
    if not live:
        return DryRunClient()
    from tool_compression.provider import DeepSeekClient, UrllibChatTransport, require_api_key

    return DeepSeekClient(require_api_key(), UrllibChatTransport(), record["api_base_url"])


def _require_case(case: dict) -> None:
    if not isinstance(case.get("messages"), list):
        raise ValueError("case messages must be the question turn list")
    catalogues = case.get("catalogues")
    if not isinstance(catalogues, dict):
        raise ValueError("case is missing catalogues")
    for name in ("U", "P", "I", "C", "E"):
        if not isinstance(catalogues.get(name), list):
            raise ValueError(f"case {case.get('id')} is missing catalogue {name}")


def _body_for(member: str, requests: dict, hashes: dict) -> dict:
    if member == "L":
        if not (hashes["P"] == hashes["I"] == hashes["C"]):
            raise RuntimeError("L is only the label for coinciding P, I, and C requests")
        return requests["P"]
    return requests[member]


def _partition(mapping: dict) -> frozenset:
    buckets: dict[str, set] = {}
    for name, digest in mapping.items():
        buckets.setdefault(digest, set()).add(name)
    return frozenset(frozenset(members) for members in buckets.values())


def _partition_lists(mapping: dict) -> list[list[str]]:
    grouped: dict[str, list[str]] = {}
    for name, digest in mapping.items():
        grouped.setdefault(digest, []).append(name)
    return [sorted(members) for members in grouped.values()]


def _write_json(path: Path, payload, secret) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    text = scrub(text, secret)
    if secret and secret in text:
        raise RuntimeError("refusing to write an artifact that still contains the API key")
    path.write_text(text, encoding="utf-8")


def _write_jsonl(path: Path, rows: list, secret) -> None:
    lines = []
    for row in rows:
        text = json.dumps(row, sort_keys=True, ensure_ascii=False)
        text = scrub(text, secret)
        if secret and secret in text:
            raise RuntimeError("refusing to write an artifact that still contains the API key")
        lines.append(text)
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _write_text(path: Path, text: str, secret) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cleaned = scrub(text, secret)
    path.write_text(cleaned, encoding="utf-8")


def read_hash_rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
