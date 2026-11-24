"""U/S2/X2/SX2 runner for the frozen amendment catalogues at 96795322.

The official sender (``official_840`` / ``usx_flight``) still selects U/S/X/SX,
puts no output limit on the wire, and on a timeout leaves spend at the last
settled call. A resume can therefore send more calls and write ``live.json``.
This module does not modify that sender and does not retarget official v1.1.

What this runner does:

- loads arms U, S2, X2, and SX2 from ``docs/amendment-s2x2/rendered`` at
  catalogue tip 96795322
- builds the question-inclusive ``official_840.generation_body`` (model
  ``deepseek-flash``, temperature 0.001, store false, thinking off then on)
  and keeps that body, without ``max_tokens``, as the plan-hash identity
- sends a wire body that is the plan body plus explicit ``max_tokens`` 8192
- shares one payload only inside one case and one thinking pass
- reports the local off-peak o200k model (¥71.751836 for the full wire plan)
  as estimated to fit ¥80; that figure is not a spending cap and not an invoice
- before any send, reserves a documented per-call upper bound (context window,
  maximum output, and the higher published tariff) and does not send when
  settled spend, unknown holds, and those reservations would pass the ceiling
- keeps an unknown charge reserved until it is reconciled, and does not delete
  the last record of exposure when a resume is refused
- refuses a resume whose ledger, hold, stop, and completion records disagree
  about exposure, whose ledger is missing while a summary claims spend, or
  whose final ledger entry is torn
- pins the wire manifest before a funded or unfunded preflight returns, rehashes
  the body before sending, and matches settlements to that manifest before
  completion
- lets only one process own the run directory; accounting writes require that
  lock, and the public recovery read does not rewrite the files
- does not read an API key and does not open a provider socket
- does not claim a provider-enforced ¥80 spend limit; the public DeepSeek Flash
  chat API does not expose one this run can set

Resume and ceiling notes are in ``amendment_s2x2_flight_resume.md`` beside this
file. The paid flight is not ready.

Run the offline gate with ``python -m tool_compression.amendment_s2x2_flight``.
``--live`` is refused before a plan is built. The frozen ``amendment-s2x2``
command is left unchanged so its packet hash stays the catalogue revision.

8192 is the next power of two above the #12 840-case ledger maximum of 7063
output tokens (p99 1010; three calls above 2048). It is a wire limit, not a
retune of official r or lambda. Plan hashes omit the field on purpose. Wire
hashes differ because the field is present; it is not dropped to preserve the
plan hash.

Jacky's ceiling for this dig is ¥80.00. The local model is estimated to fit
¥80. That estimate is not a cap. Official settlement stays false. Human review
was not performed. The paid flight is not ready. Local o200k counts are not
provider T. This module does not authorize a paid flight.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
from typing import NoReturn
import argparse
import contextvars
import fcntl
import hashlib
import json
import os
import socket

from tool_compression.config import BFCL_DEFAULT_TEMPERATURE, BFCL_STORE
from tool_compression.count import TiktokenCounter, dump_request
from tool_compression.official_840 import (
    CATEGORY_COUNTS,
    GORILLA_COMMIT,
    PASSES,
    assert_official_body,
    generation_body as official_generation_body,
    load_fresh,
    thinking_body,
)
from tool_compression.usx_flight import (
    MODEL,
    SHANGHAI,
    UsxFlightRefused,
    _thinking_stayed_off,
    rate_card,
    request_sha256,
    schedule_at,
    spend_cny,
    usage_bill,
)

PURPOSE = "amendment-s2x2-flight"
CATALOGUE_TIP = "96795322fc12c27f0eebe538448666588b573176"
ARMS = ("U", "S2", "X2", "SX2")
MAX_TOKENS = 8192
MAX_TOKENS_FIELD = "max_tokens"
HARD_CAP_CNY = Decimal("80.00")
# Documented deepseek-flash caps from the public list-models example and the
# pricing page, checked 2026-11-24. Not a live /models call. Input and output
# share the context window; reserving both caps overstates one call on purpose.
DOCUMENTED_CONTEXT_TOKENS = 1_048_576
DOCUMENTED_MAX_OUTPUT_TOKENS = 384 * 1024
OFFPEAK = "off-peak"
RESERVE_SCHEDULE = "peak"
HUMAN_REVIEW = "not performed (not passed)"
OFFICIAL_V11 = "closed"
SAMPLE = "official-840"
CONTROL_CATEGORIES = ("simple_python", "irrelevance")
IDENTITY_PAIRS = {
    "S2_equals_U": ("S2", "U"),
    "X2_equals_U": ("X2", "U"),
    "SX2_equals_S2": ("SX2", "S2"),
    "SX2_equals_X2": ("SX2", "X2"),
    "SX2_equals_U": ("SX2", "U"),
}
MAX_TOKENS_NOTE = (
    "8192 is the next power of two above the #12 840-case ledger maximum of "
    "7063 output tokens (p99 1010; three calls above 2048). It is an explicit "
    "wire limit on this follow-on runner. It does not retune official r or "
    "lambda. Plan hashes omit it and remain the identity check. Wire hashes "
    "differ because the field is present; the field is not removed to keep "
    "the plan hash."
)
HARD_CAP_NOTE = (
    "Jacky's ceiling for this dig is ¥80.00. The local o200k model is "
    "estimated to fit ¥80. That estimate is not a spending cap and not a "
    "provider invoice. No provider-enforced spend limit is available for this "
    "run. The runner reserves the documented per-call bound and does not send "
    "when that reservation would pass the ceiling. The ceiling is not "
    "authorization to fly. Official v1.1 stays closed. Human review was not "
    "performed. The paid flight is not ready."
)
REMAINING_RUN_NOTE = (
    "The local estimate prices every not-yet-settled wire send as off-peak "
    "all-miss o200k tokens of that body plus max_tokens output. It is "
    "estimated to fit ¥80 for the full plan and is not a cap. Before a send, "
    "the runner reserves the documented context window and maximum output at "
    "the higher published tariff. A timed-out call stays incomplete and keeps "
    "that reservation until the charge is reconciled. Local tokens are not "
    "provider T."
)
ESTIMATED_TO_FIT = "estimated to fit ¥80"
CAP_STOP = "remaining worst-case would pass the supplied ceiling"
TIMEOUT_STOP = "provider timed out; unknown charge held at this call's documented reserve"
UNKNOWN_STOP = "provider call failed; unknown charge held at this call's documented reserve"
LEDGER_MISSING = "calls ledger is missing; refusing to reset settled spend to zero"
LEDGER_TORN = "calls ledger final entry is torn and cannot be repaired"
LEDGER_INCONSISTENT = "cap state does not match the calls ledger; refusing to reset settled spend"
EXPOSURE_UNRESOLVED = "unresolved exposure is not itemized; refusing to reset it to zero"
EXPOSURE_DISAGREE = "ledger, hold, stop, or completion records disagree about exposure"
MANIFEST_MISMATCH = "resumed plans do not match the frozen wire manifest"
HASH_LABEL_MISMATCH = "wire body does not match its stored hash label"
SEND_HASH_MISMATCH = "refusing to send a body that does not match the frozen manifest"
SETTLEMENT_MISMATCH = "settled call does not match the frozen manifest"
OWNER_WRITE = "accounting write requires the run owner lock"
OVER_RESERVE_STOP = "returned bill exceeded the documented per-call reserve"
MANIFEST_MISSING = "resume is missing the frozen wire manifest for this run"
OWNER_HELD = "another operator holds this run directory"
ACCOUNTING_NAMES = ("calls-ledger.jsonl", "cap-hold.json", "stop.json", "live.json")
MANIFEST_NAME = "wire-manifest.json"
LOCK_NAME = "run.lock"
LIVE_STOP = (
    "provider call refused; this dig does not authorize a flight; "
    "official settlement stays false; human review was not performed"
)
OFFICIAL_DISPATCH_STOP = "refusing to dispatch the official 840 sample; the paid flight is not authorized"
OVER_CAP_STOP = "supplied ceiling exceeds ¥80.00"
_RUN_OWNER: contextvars.ContextVar[str | None] = contextvars.ContextVar("amendment_s2x2_run_owner", default=None)


class AmendmentFlightRefused(UsxFlightRefused):
    """A closed stop. The message names the reason and carries no secret."""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def rendered_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / "docs" / "amendment-s2x2" / "rendered"


def refuse_provider_call() -> None:
    """Refuse a live provider call. Does not read a key or open a socket."""
    raise AmendmentFlightRefused(LIVE_STOP)


def _pin_tokenizer_cache() -> None:
    """Point tiktoken at the committed BPE tables. This does not read a secret."""
    from tool_compression.amendment_bundle import TOKENIZER_CACHE

    cache = repo_root() / "src" / "tool_compression" / "tiktoken_cache"
    for name, pin in TOKENIZER_CACHE.items():
        path = cache / pin["cache_key"]
        if not path.is_file():
            raise AmendmentFlightRefused(f"tokenizer cache missing for {name}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != pin["sha256"]:
            raise AmendmentFlightRefused(f"tokenizer cache mismatch for {name}")
    os.environ["TIKTOKEN_CACHE_DIR"] = str(cache)


def local_counter() -> TiktokenCounter:
    _pin_tokenizer_cache()
    return TiktokenCounter("o200k_base")


_COUNTER: TiktokenCounter | None = None


def _counter() -> TiktokenCounter:
    global _COUNTER
    if _COUNTER is None:
        _COUNTER = local_counter()
    return _COUNTER


@lru_cache(maxsize=8192)
def _tokens_of(serialized: str) -> int:
    return _counter().count(serialized)


def local_input_tokens(body: dict) -> int:
    """o200k_base tokens of the serialized body. Not provider prompt_tokens."""
    return _tokens_of(dump_request(body))


def worst_case_cny(body: dict) -> Decimal:
    """Local off-peak estimate: all-miss o200k input of the wire body, plus max_tokens output.

    This is the ¥71.751836 model when summed over the official wire plan. It is
    estimated to fit ¥80. It is not the pre-send reservation and not an invoice.
    """
    if body.get(MAX_TOKENS_FIELD) != MAX_TOKENS:
        raise AmendmentFlightRefused("worst case requires the explicit max_tokens wire body")
    return spend_cny(OFFPEAK, local_input_tokens(body), 0, MAX_TOKENS)


def documented_call_reserve_cny() -> Decimal:
    """Upper bound reserved before one send, under the published peak card.

    There is no verified provider-enforced spend limit on this chat API that
    this run can set. The bound is the documented context window at the peak
    miss rate plus the documented maximum output at the peak output rate.
    Chat completions say input and generated tokens together cannot exceed the
    context length, so adding both caps overstates one call and stays an upper
    bound. ``max_tokens`` 8192 is still sent, but the chat-completions text does
    not explicitly put reasoning tokens inside that field, so the output cap
    used here is the model's documented maximum output (384K). DeepSeek says
    prices may change; this reservation is not a contractual freeze and is not
    a spending guarantee.
    """
    return spend_cny(RESERVE_SCHEDULE, DOCUMENTED_CONTEXT_TOKENS, 0, DOCUMENTED_MAX_OUTPUT_TOKENS)


def accept_run_ceiling(value: Decimal) -> Decimal:
    """A positive Decimal at or under ¥80.00. Floats are refused.

    This only bounds the ceiling the caller supplied. It is not a claim that
    provider spend cannot pass ¥80.
    """
    if isinstance(value, bool) or not isinstance(value, Decimal):
        raise AmendmentFlightRefused("ceiling must be a Decimal")
    if not value.is_finite() or value <= 0:
        raise AmendmentFlightRefused("ceiling must be a positive Decimal")
    if value > HARD_CAP_CNY:
        raise AmendmentFlightRefused(OVER_CAP_STOP)
    return value


def plan_body(messages: list, tools: list, pass_name: str) -> dict:
    """Question-inclusive official body. No max_tokens, so the plan hash is unchanged."""
    body = official_generation_body(messages, tools, pass_name)
    if MAX_TOKENS_FIELD in body:
        raise AmendmentFlightRefused("plan body must omit max_tokens")
    return body


def wire_body(messages: list, tools: list, pass_name: str) -> dict:
    """Plan body plus the explicit output limit. The wire hash therefore differs."""
    body = plan_body(messages, tools, pass_name)
    body[MAX_TOKENS_FIELD] = MAX_TOKENS
    _assert_wire_is_plan_plus_limit(
        {key: value for key, value in body.items() if key != MAX_TOKENS_FIELD},
        body,
    )
    return body


def _assert_wire_is_plan_plus_limit(plan: dict, wire: dict) -> None:
    if set(wire) != set(plan) | {MAX_TOKENS_FIELD}:
        raise AmendmentFlightRefused("wire body changes more than max_tokens")
    if wire.get(MAX_TOKENS_FIELD) != MAX_TOKENS:
        raise AmendmentFlightRefused("wire body is missing the explicit output-token limit")
    for key, value in plan.items():
        if wire[key] != value:
            raise AmendmentFlightRefused("wire body changes a plan field")
    assert_official_body(wire)
    if request_sha256(plan) == request_sha256(wire):
        raise AmendmentFlightRefused("wire hash collapsed into the plan hash")


def catalogue_identities(rendered: dict[str, list]) -> dict:
    return {name: rendered[left] == rendered[right] for name, (left, right) in IDENTITY_PAIRS.items()}


def _group_payloads(bodies_by_arm: dict[str, dict]) -> list[dict]:
    """Share one payload inside one cell. Arms stay in U, S2, X2, SX2 order."""
    groups: list[dict] = []
    index: dict[str, int] = {}
    for arm in ARMS:
        body = bodies_by_arm[arm]
        digest = request_sha256(body)
        slot = index.get(digest)
        if slot is None:
            index[digest] = len(groups)
            groups.append({"request_sha256": digest, "arms": [arm], "body": body})
        else:
            groups[slot]["arms"].append(arm)
    return groups


def _public_groups(groups: list[dict]) -> list[dict]:
    return [
        {
            "request_sha256": group["request_sha256"],
            "arms": list(group["arms"]),
            "shared": len(group["arms"]) > 1,
        }
        for group in groups
    ]


def make_plan(case_id: str, category: str, messages: list, rendered: dict[str, list], pass_name: str) -> dict:
    """One case and one thinking pass. Sharing does not cross cells."""
    if pass_name not in PASSES:
        raise AmendmentFlightRefused(f"unknown thinking pass {pass_name}")
    if list(rendered) != list(ARMS) and set(rendered) != set(ARMS):
        raise AmendmentFlightRefused(f"rendered arms are not U/S2/X2/SX2 for {case_id}")
    plan_bodies = {arm: plan_body(messages, rendered[arm], pass_name) for arm in ARMS}
    wire_bodies = {arm: wire_body(messages, rendered[arm], pass_name) for arm in ARMS}
    for arm in ARMS:
        _assert_wire_is_plan_plus_limit(plan_bodies[arm], wire_bodies[arm])
        if plan_bodies[arm]["thinking"] != thinking_body(pass_name):
            raise AmendmentFlightRefused("thinking field does not match the pass")
    plan_groups = _group_payloads(plan_bodies)
    wire_groups = _group_payloads(wire_bodies)
    if [group["arms"] for group in plan_groups] != [group["arms"] for group in wire_groups]:
        raise AmendmentFlightRefused(f"max_tokens changed within-cell sharing for {case_id} {pass_name}")
    flags = catalogue_identities(rendered)
    located = {arm: group["request_sha256"] for group in plan_groups for arm in group["arms"]}
    for name, (left, right) in IDENTITY_PAIRS.items():
        if (located[left] == located[right]) is not flags[name]:
            raise AmendmentFlightRefused(f"payload groups do not match catalogue identity for {case_id} {pass_name}")
    return {
        "case_id": case_id,
        "category": category,
        "thinking": pass_name,
        "cell": f"{case_id}:{pass_name}",
        "catalogue_identities": flags,
        "plan_groups": _public_groups(plan_groups),
        "wire_groups": _public_groups(wire_groups),
        "_plan_bodies": {group["request_sha256"]: group["body"] for group in plan_groups},
        "_wire_bodies": {group["request_sha256"]: group["body"] for group in wire_groups},
    }


def load_amendment_tools(case_id: str, arm: str, category: str, root: Path | None = None) -> list:
    path = rendered_dir(root) / case_id / f"{arm}.json"
    if not path.is_file():
        raise AmendmentFlightRefused(f"rendered catalogue missing {case_id} {arm}")
    document = json.loads(path.read_text(encoding="utf-8"))
    # U.json is the byte copy of the official catalogue. S2/X2/SX2 carry the amendment sample id.
    expected_sample = SAMPLE if arm == "U" else "amendment-s2x2"
    if document.get("sample") != expected_sample or document.get("case_id") != case_id:
        raise AmendmentFlightRefused(f"rendered document mismatch {case_id} {arm}")
    if document.get("condition") != arm or document.get("category") != category:
        raise AmendmentFlightRefused(f"rendered document mismatch {case_id} {arm}")
    tools = document.get("tools")
    if not isinstance(tools, list):
        raise AmendmentFlightRefused(f"rendered tools missing {case_id} {arm}")
    return tools


def _assert_passes_distinct(plans: list[dict]) -> None:
    seen_on = False
    by_case: dict[str, dict] = {}
    for plan in plans:
        if plan["thinking"] == "on":
            seen_on = True
        elif plan["thinking"] == "off" and seen_on:
            raise AmendmentFlightRefused("thinking-off pass follows thinking-on")
        elif plan["thinking"] not in PASSES:
            raise AmendmentFlightRefused(f"unknown thinking pass {plan['thinking']}")
        by_case.setdefault(plan["case_id"], {})[plan["thinking"]] = plan
    for case_id, passes in by_case.items():
        if set(passes) != set(PASSES):
            raise AmendmentFlightRefused(f"missing thinking pass {case_id}")
        for arm in ARMS:
            off_hash = _hash_for_arm(passes["off"], "plan_groups", arm)
            on_hash = _hash_for_arm(passes["on"], "plan_groups", arm)
            if off_hash == on_hash:
                raise AmendmentFlightRefused(f"thinking passes collapsed {case_id} {arm}")
            off_body = passes["off"]["_plan_bodies"][off_hash]
            on_body = passes["on"]["_plan_bodies"][on_hash]
            if off_body.get("messages") != on_body.get("messages") or off_body.get("tools") != on_body.get("tools"):
                raise AmendmentFlightRefused(f"thinking pass changed the catalogue or the question {case_id}")


def _hash_for_arm(plan: dict, group_key: str, arm: str) -> str:
    matches = [group["request_sha256"] for group in plan[group_key] if arm in group["arms"]]
    if len(matches) != 1:
        raise AmendmentFlightRefused(f"arm {arm} is not in exactly one group for {plan['cell']}")
    return matches[0]


def build_flight(bfcl_root: Path, repo: Path | None = None) -> dict:
    """Plan all 840 cases, both thinking passes, from the frozen rendered catalogues."""
    root = repo or repo_root()
    order, fresh = load_fresh(bfcl_root)
    if len(order) != sum(CATEGORY_COUNTS.values()):
        raise AmendmentFlightRefused("fresh conversion did not yield 840 cases")
    plans = []
    control_cases = 0
    x2_equals_u = 0
    sx2_equals_s2 = 0
    for pass_name in PASSES:
        for case_id in order:
            category = fresh[case_id]["category"]
            rendered = {arm: load_amendment_tools(case_id, arm, category, root) for arm in ARMS}
            if rendered["U"] != fresh[case_id]["tools"]:
                raise AmendmentFlightRefused(f"amendment U does not match fresh conversion {case_id}")
            if category in CONTROL_CATEGORIES:
                if pass_name == "off":
                    control_cases += 1
                    x2_equals_u += int(rendered["X2"] == rendered["U"])
                    sx2_equals_s2 += int(rendered["SX2"] == rendered["S2"])
                if rendered["X2"] != rendered["U"] or rendered["SX2"] != rendered["S2"]:
                    raise AmendmentFlightRefused(f"control catalogue identity drifted {case_id}")
            plans.append(make_plan(case_id, category, fresh[case_id]["messages"], rendered, pass_name))
    _assert_passes_distinct(plans)
    if control_cases != CATEGORY_COUNTS["simple_python"] + CATEGORY_COUNTS["irrelevance"]:
        raise AmendmentFlightRefused("control case count is not 640")
    if x2_equals_u != control_cases or sx2_equals_s2 != control_cases:
        raise AmendmentFlightRefused("X2=U and SX2=S2 did not hold on every control")
    return {
        "purpose": PURPOSE,
        "catalogue_tip": CATALOGUE_TIP,
        "arms": list(ARMS),
        "max_tokens": MAX_TOKENS,
        "gorilla_commit": GORILLA_COMMIT,
        "official_settlement": False,
        "official_v1_1": OFFICIAL_V11,
        "human_review": HUMAN_REVIEW,
        "flight_ready": False,
        "provider_call_authorized": False,
        "plans": plans,
        "order": order,
        "control_cases": control_cases,
        "control_x2_equals_u": x2_equals_u,
        "control_sx2_equals_s2": sx2_equals_s2,
    }


def _slots(plans: list[dict], group_key: str, body_key: str) -> list[dict]:
    slots = []
    for plan in plans:
        bodies = plan[body_key]
        for group in plan[group_key]:
            digest = group["request_sha256"]
            slots.append(
                {
                    "slot_id": f"{plan['cell']}:{digest}",
                    "request_sha256": digest,
                    "arms": list(group["arms"]),
                    "case_id": plan["case_id"],
                    "category": plan["category"],
                    "thinking": plan["thinking"],
                    "cell": plan["cell"],
                    "body": bodies[digest],
                }
            )
    return slots


def wire_slots(plans: list[dict]) -> list[dict]:
    return _slots(plans, "wire_groups", "_wire_bodies")


def plan_slots(plans: list[dict]) -> list[dict]:
    return _slots(plans, "plan_groups", "_plan_bodies")


def is_official_sample(plans: list[dict]) -> bool:
    off = [plan for plan in plans if plan.get("thinking") == "off"]
    on = [plan for plan in plans if plan.get("thinking") == "on"]
    if len(off) != sum(CATEGORY_COUNTS.values()) or len(on) != len(off):
        return False
    if [plan["case_id"] for plan in on] != [plan["case_id"] for plan in off]:
        return False
    counts: dict[str, int] = {}
    for plan in off:
        counts[plan["category"]] = counts.get(plan["category"], 0) + 1
    return counts == dict(CATEGORY_COUNTS)


def _arm_tokens(plan: dict, group_key: str, body_key: str) -> dict[str, int]:
    totals = {arm: 0 for arm in ARMS}
    bodies = plan[body_key]
    for group in plan[group_key]:
        tokens = local_input_tokens(bodies[group["request_sha256"]])
        for arm in group["arms"]:
            totals[arm] += tokens
    return totals


def _add_scope(bucket: dict, category: str, pass_name: str, arm_totals: dict[str, int]) -> None:
    for arm, tokens in arm_totals.items():
        bucket["all_840"][pass_name][arm] += tokens
        bucket[category][pass_name][arm] += tokens
        if category in CONTROL_CATEGORIES:
            bucket["controls"][pass_name][arm] += tokens


def summarize_flight(plans: list[dict], counter: TiktokenCounter | None = None) -> dict:
    """Local o200k totals and unique hashes for plan bodies and wire bodies.

    ``counter`` is accepted so callers can show which tokenizer they pinned.
    Counts go through the committed o200k cache either way.
    """
    if counter is not None and counter.name != "o200k_base":
        raise AmendmentFlightRefused("local bound requires o200k_base")
    _pin_tokenizer_cache()
    scopes = ("all_840", "multiple", "simple_python", "irrelevance", "controls")
    totals = {
        kind: {scope: {pass_name: {arm: 0 for arm in ARMS} for pass_name in PASSES} for scope in scopes}
        for kind in ("plan", "wire")
    }
    unique = {kind: {pass_name: set() for pass_name in PASSES} for kind in ("plan", "wire")}
    unique_scope = {
        kind: {scope: {pass_name: set() for pass_name in PASSES} for scope in scopes}
        for kind in ("plan", "wire")
    }
    deltas: set[int] = set()
    for plan in plans:
        pass_name = plan["thinking"]
        category = plan["category"]
        plan_totals = _arm_tokens(plan, "plan_groups", "_plan_bodies")
        wire_totals = _arm_tokens(plan, "wire_groups", "_wire_bodies")
        _add_scope(totals["plan"], category, pass_name, plan_totals)
        _add_scope(totals["wire"], category, pass_name, wire_totals)
        for arm in ARMS:
            deltas.add(wire_totals[arm] - plan_totals[arm])
        for kind, group_key in (("plan", "plan_groups"), ("wire", "wire_groups")):
            for group in plan[group_key]:
                digest = group["request_sha256"]
                unique[kind][pass_name].add(digest)
                unique_scope[kind]["all_840"][pass_name].add(digest)
                unique_scope[kind][category][pass_name].add(digest)
                if category in CONTROL_CATEGORIES:
                    unique_scope[kind]["controls"][pass_name].add(digest)
    wire = wire_slots(plans)
    costs: dict[str, Decimal] = {}
    for slot in wire:
        digest = slot["request_sha256"]
        if digest not in costs:
            costs[digest] = worst_case_cny(slot["body"])
    slot_bound = sum((costs[slot["request_sha256"]] for slot in wire), Decimal("0"))
    unique_bound = sum(costs.values(), Decimal("0"))
    plan_union = set().union(*(unique["plan"][pass_name] for pass_name in PASSES))
    wire_union = set().union(*(unique["wire"][pass_name] for pass_name in PASSES))
    return {
        "token_totals_plan": totals["plan"],
        "token_totals_wire": totals["wire"],
        "unique_plan_hashes": {pass_name: len(unique["plan"][pass_name]) for pass_name in PASSES},
        "unique_wire_hashes": {pass_name: len(unique["wire"][pass_name]) for pass_name in PASSES},
        "unique_plan_union": len(plan_union),
        "unique_wire_union": len(wire_union),
        "plan_and_wire_hash_sets_disjoint": plan_union.isdisjoint(wire_union),
        "unique_by_scope_plan": {
            scope: {pass_name: len(unique_scope["plan"][scope][pass_name]) for pass_name in PASSES}
            for scope in scopes
        },
        "wire_minus_plan_token_deltas": sorted(deltas),
        "send_slots": len(wire),
        "cross_cell_duplicate_sends": len(wire) - len(wire_union),
        "slot_worst_case_cny": slot_bound,
        "unique_hash_worst_case_cny": unique_bound,
        "remaining_run_worst_case_cny": slot_bound,
    }


class CapState:
    """Settled spend from the ledger, plus unknown holds that must survive a resume."""

    def __init__(self, settled: Decimal, calls: list, events: list, pending: dict | None, loaded_events: int):
        self.settled = settled
        self.calls = calls
        self.events = events
        self.pending = pending
        self.loaded_events = loaded_events
        self.sticky: str | None = None
        # Greatest observed provider-prompt / local-o200k ratio. 1/1 means no overrun.
        self.ratio_num = 1
        self.ratio_den = 1
        self.input_unbounded = False

    @property
    def input_ratio(self) -> Decimal:
        if self.input_unbounded or self.ratio_den <= 0:
            return Decimal("Infinity")
        return Decimal(self.ratio_num) / Decimal(self.ratio_den)

    def note_input(self, local_tokens: int, billed_tokens: int) -> None:
        """Remember a provider input count above the local estimate. A later slot is repriced from it."""
        if isinstance(local_tokens, bool) or isinstance(billed_tokens, bool):
            raise AmendmentFlightRefused("input token count is corrupt")
        if local_tokens < 0 or billed_tokens < 0:
            raise AmendmentFlightRefused("input token count is corrupt")
        if billed_tokens <= local_tokens:
            return
        if local_tokens == 0:
            self.input_unbounded = True
            return
        if billed_tokens * self.ratio_den > self.ratio_num * local_tokens:
            self.ratio_num = billed_tokens
            self.ratio_den = local_tokens

    @property
    def unknown(self) -> Decimal:
        return sum((Decimal(event["held_worst_case_cny"]) for event in self.events), Decimal("0"))

    @property
    def pending_amount(self) -> Decimal:
        if not self.pending:
            return Decimal("0")
        return Decimal(self.pending["held_worst_case_cny"])

    @property
    def exposure_base(self) -> Decimal:
        """Settled spend plus holds. Does not include calls that have not been attempted."""
        return self.settled + self.unknown + self.pending_amount


def _decimal_field(value, label: str) -> Decimal:
    if isinstance(value, bool) or isinstance(value, float) or value is None:
        raise AmendmentFlightRefused(f"{label} is corrupt")
    try:
        amount = Decimal(str(value))
    except InvalidOperation as exc:
        raise AmendmentFlightRefused(f"{label} is corrupt") from exc
    if not amount.is_finite() or amount < 0:
        raise AmendmentFlightRefused(f"{label} is corrupt")
    return amount


def _optional_decimal(value, label: str) -> Decimal:
    if value is None:
        return Decimal("0")
    return _decimal_field(value, label)


def _money(amount: Decimal) -> str:
    return format(amount, "f")


def _require_owner(out: Path) -> None:
    owned = _RUN_OWNER.get()
    if owned != str(Path(out).resolve()):
        raise AmendmentFlightRefused(OWNER_WRITE)


def _atomic_json(path: Path, payload: dict) -> None:
    _require_owner(path.parent)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _hold_path(out: Path) -> Path:
    return Path(out) / "cap-hold.json"


def _stop_path(out: Path) -> Path:
    return Path(out) / "stop.json"


def _ledger_path(out: Path) -> Path:
    return Path(out) / "calls-ledger.jsonl"


def _live_path(out: Path) -> Path:
    return Path(out) / "live.json"


def _discard_live(out: Path) -> None:
    """Drop a completion marker only after a stop record has kept the spend."""
    _require_owner(out)
    path = _live_path(out)
    if path.is_file():
        path.unlink()


def _fail_accounting(out: Path, reason: str) -> NoReturn:
    """Refuse without rewriting or deleting evidence.

    A completion marker can be the last surviving record of spend. Deleting it
    on the way out would make the next restart look like a fresh run.
    """
    del out
    raise AmendmentFlightRefused(reason)


def _hold_payload(state: CapState) -> dict:
    return {
        "purpose": PURPOSE,
        "catalogue_tip": CATALOGUE_TIP,
        "official_settlement": False,
        "flight_ready": False,
        "provider_call_authorized": False,
        "human_review": HUMAN_REVIEW,
        "complete": False,
        "settled_spend_cny": _money(state.settled),
        "outstanding_unknown_timeout_cny": _money(state.unknown),
        "conservative_held_cny": _money(state.settled + state.unknown),
        "timeout_events": state.events,
        "pending_call": state.pending,
        "sticky_stop_reason": state.sticky,
        "input_ratio_numerator": state.ratio_num,
        "input_ratio_denominator": state.ratio_den,
        "input_ratio_unbounded": state.input_unbounded,
        "local_token_estimate_is_provider_bill": False,
        "note": REMAINING_RUN_NOTE,
    }


def _write_hold(out: Path, state: CapState) -> None:
    _atomic_json(_hold_path(out), _hold_payload(state))


def _write_stop(out: Path, state: CapState, ceiling: Decimal, reason: str, extra: dict | None = None) -> None:
    _require_owner(out)
    _write_hold(out, state)
    record = {
        "purpose": PURPOSE,
        "catalogue_tip": CATALOGUE_TIP,
        "official_settlement": False,
        "official_v1_1": OFFICIAL_V11,
        "human_review": HUMAN_REVIEW,
        "flight_ready": False,
        "provider_call_authorized": False,
        "complete": False,
        "would_label_complete": False,
        "provider_called": False,
        "provider_network": False,
        "api_key_in_record": False,
        "spend_cny": _money(state.settled),
        "outstanding_unknown_timeout_cny": _money(state.unknown),
        "conservative_held_cny": _money(state.settled + state.unknown),
        "stop_reason": reason,
        "ceiling_cny": _money(ceiling),
        "hard_cap_cny": _money(HARD_CAP_CNY),
        "ceiling_lifted": False,
        "calls_already_settled": len(state.calls),
        "live_json_written": False,
        "max_tokens": MAX_TOKENS,
        "spending_guarantee": False,
        "provider_enforced_spend_limit": False,
        "money_limit": ESTIMATED_TO_FIT,
        "documented_call_reserve_cny": _money(documented_call_reserve_cny()),
    }
    if extra:
        record.update(extra)
    _atomic_json(_stop_path(out), record)
    _discard_live(out)


def _load_ledger(path: Path) -> list[dict]:
    """Load settled calls. A torn final line is refused. This read does not repair or delete.

    Skipping a torn tail would drop its spend. The newline repair is an accounting
    write, so it happens under the owner lock in ``_append_ledger``, before the
    next record is added. An invalid final fragment is not truncated and is not ignored.
    """
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        _fail_accounting(path.parent, "calls ledger is corrupt")
    needs_newline = bool(text) and not text.endswith("\n")
    if needs_newline:
        last = text.splitlines()[-1]
        if last.strip():
            try:
                json.loads(last)
            except json.JSONDecodeError:
                _fail_accounting(path.parent, LEDGER_TORN)
    lines = text.splitlines()
    calls = []
    last_index = len(lines) - 1
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            reason = LEDGER_TORN if index == last_index else "calls ledger is corrupt"
            _fail_accounting(path.parent, reason)
        bill = item.get("bill") if isinstance(item, dict) else None
        if not isinstance(bill, dict) or "spend_cny" not in bill:
            _fail_accounting(path.parent, "calls ledger is corrupt")
        _decimal_field(bill["spend_cny"], "ledger spend")
        calls.append(item)
    return calls


def _read_json_object(path: Path, label: str) -> dict | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AmendmentFlightRefused(f"{label} is corrupt") from exc
    if not isinstance(payload, dict):
        raise AmendmentFlightRefused(f"{label} is corrupt")
    return payload


def _claimed_settled(hold: dict | None, stop: dict | None, live: dict | None) -> Decimal | None:
    """The highest settled spend a summary still claims. A missing key is not a zero."""
    found: list[Decimal] = []
    if hold is not None and "settled_spend_cny" in hold and hold.get("settled_spend_cny") is not None:
        found.append(_decimal_field(hold["settled_spend_cny"], "settled spend"))
    if stop is not None and "spend_cny" in stop and stop.get("spend_cny") is not None:
        found.append(_decimal_field(stop["spend_cny"], "stop spend"))
    if live is not None and "spend_cny" in live and live.get("spend_cny") is not None:
        found.append(_decimal_field(live["spend_cny"], "live spend"))
    if not found:
        return None
    return max(found)


def _claimed_unresolved(stop: dict | None, live: dict | None) -> Decimal | None:
    """Highest unresolved amount a stop or completion record still claims.

    The hold is not included. Its own outstanding figure is folded into the
    events loaded from that file. A missing key is not a claim of zero.
    """
    found: list[Decimal] = []
    if stop is not None and "outstanding_unknown_timeout_cny" in stop and stop.get("outstanding_unknown_timeout_cny") is not None:
        found.append(_decimal_field(stop["outstanding_unknown_timeout_cny"], "stop unresolved"))
    if live is not None and "outstanding_unknown_timeout_cny" in live and live.get("outstanding_unknown_timeout_cny") is not None:
        found.append(_decimal_field(live["outstanding_unknown_timeout_cny"], "live unresolved"))
    if not found:
        return None
    return max(found)


def _claimed_calls(stop: dict | None) -> int:
    if stop is None or "calls_already_settled" not in stop or stop.get("calls_already_settled") is None:
        return 0
    value = stop["calls_already_settled"]
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise AmendmentFlightRefused("stop record is corrupt")
    return value


def _note_recorded_inputs(state: CapState, calls: list[dict], hold: dict | None) -> None:
    for row in calls:
        if "local_input_tokens" not in row and "billed_input_tokens" not in row:
            continue
        local = row.get("local_input_tokens")
        billed = row.get("billed_input_tokens")
        if (
            isinstance(local, bool)
            or isinstance(billed, bool)
            or not isinstance(local, int)
            or not isinstance(billed, int)
            or local < 0
            or billed < 0
        ):
            raise AmendmentFlightRefused("calls ledger is corrupt")
        state.note_input(local, billed)
    if hold is None:
        return
    unbounded = hold.get("input_ratio_unbounded")
    if unbounded is True:
        state.input_unbounded = True
    elif unbounded not in (None, False):
        raise AmendmentFlightRefused("cap hold is corrupt")
    if "input_ratio_numerator" not in hold and "input_ratio_denominator" not in hold:
        return
    numerator = hold.get("input_ratio_numerator")
    denominator = hold.get("input_ratio_denominator")
    if (
        isinstance(numerator, bool)
        or isinstance(denominator, bool)
        or not isinstance(numerator, int)
        or not isinstance(denominator, int)
        or numerator < 0
        or denominator <= 0
    ):
        raise AmendmentFlightRefused("cap hold is corrupt")
    state.note_input(denominator, numerator)


def _events_from_hold(hold: dict) -> list[dict]:
    raw = hold.get("timeout_events") or []
    if not isinstance(raw, list):
        raise AmendmentFlightRefused("cap hold is corrupt")
    events = []
    for item in raw:
        if not isinstance(item, dict) or "held_worst_case_cny" not in item:
            raise AmendmentFlightRefused("cap hold is corrupt")
        amount = _decimal_field(item["held_worst_case_cny"], "timeout hold")
        events.append(
            {
                "slot_id": item.get("slot_id"),
                "request_sha256": item.get("request_sha256"),
                "case_id": item.get("case_id"),
                "thinking": item.get("thinking"),
                "held_worst_case_cny": _money(amount),
                "clock": item.get("clock"),
                "reason": item.get("reason") or "unknown charge",
            }
        )
    return events


def load_cap_state(out: Path) -> CapState:
    """Read settled spend and unknown holds. This does not write the run directory.

    A missing ledger is a fresh run only when no summary claims spend. A summary
    that is higher than the itemized ledger is refused, so spend cannot come
    back as zero. A summary that is lower can be a stop file left from before a
    later settled call; the ledger is kept. A missing hold is not a zero when a
    stop or completion record still claims unresolved exposure. Disagreement is
    refused and the files are left as they were.
    """
    out = Path(out)
    ledger_path = _ledger_path(out)
    ledger_exists = ledger_path.is_file()
    calls = _load_ledger(ledger_path) if ledger_exists else []
    settled = Decimal("0")
    settled_slots: set[str] = set()
    for row in calls:
        settled += Decimal(row["bill"]["spend_cny"])
        slot_id = row.get("slot_id")
        if not isinstance(slot_id, str) or slot_id == "":
            _fail_accounting(out, "calls ledger is missing slot_id")
        if slot_id in settled_slots:
            _fail_accounting(out, "calls ledger repeats a slot")
        settled_slots.add(slot_id)
    hold_path = _hold_path(out)
    hold = _read_json_object(hold_path, "cap hold")
    stop = _read_json_object(_stop_path(out), "stop record")
    live = _read_json_object(_live_path(out), "live record")
    floor = _claimed_settled(hold, stop, live)
    claimed = _claimed_calls(stop)
    if not ledger_exists:
        if live is not None or claimed > 0 or (floor is not None and floor > 0):
            _fail_accounting(out, LEDGER_MISSING)
    elif floor is not None and floor > settled:
        _fail_accounting(out, LEDGER_INCONSISTENT)
    elif claimed > len(calls):
        _fail_accounting(out, LEDGER_INCONSISTENT)
    elif live is not None and live.get("spend_cny") is not None:
        if _decimal_field(live["spend_cny"], "live spend") != settled:
            _fail_accounting(out, LEDGER_INCONSISTENT)
    events: list[dict] = []
    pending = None
    stored_unknown = Decimal("0")
    sticky = None
    if hold is not None:
        events = _events_from_hold(hold)
        pending = hold.get("pending_call")
        stored_unknown = _optional_decimal(hold.get("outstanding_unknown_timeout_cny"), "outstanding hold")
        sticky = hold.get("sticky_stop_reason")
        if sticky is not None and not isinstance(sticky, str):
            raise AmendmentFlightRefused("cap hold is corrupt")
    loaded_events = len(events)
    if pending:
        if not isinstance(pending, dict) or "held_worst_case_cny" not in pending:
            raise AmendmentFlightRefused("cap hold is corrupt")
        amount = _decimal_field(pending["held_worst_case_cny"], "pending hold")
        slot_id = pending.get("slot_id")
        if slot_id not in settled_slots:
            events.append(
                {
                    "slot_id": slot_id,
                    "request_sha256": pending.get("request_sha256"),
                    "case_id": pending.get("case_id"),
                    "thinking": pending.get("thinking"),
                    "held_worst_case_cny": _money(amount),
                    "clock": pending.get("clock"),
                    "reason": "in-flight call was not settled",
                }
            )
        pending = None
    from_events = sum((Decimal(event["held_worst_case_cny"]) for event in events), Decimal("0"))
    if stored_unknown > from_events:
        events.append(
            {
                "slot_id": None,
                "request_sha256": None,
                "case_id": None,
                "thinking": None,
                "held_worst_case_cny": _money(stored_unknown - from_events),
                "clock": None,
                "reason": "unitemized outstanding hold reloaded",
            }
        )
    reconstructed = sum((Decimal(event["held_worst_case_cny"]) for event in events), Decimal("0"))
    claimed_unknown = _claimed_unresolved(stop, live)
    if claimed_unknown is not None and claimed_unknown > reconstructed:
        _fail_accounting(out, EXPOSURE_UNRESOLVED)
    if live is not None and live.get("outstanding_unknown_timeout_cny") is not None:
        if _decimal_field(live["outstanding_unknown_timeout_cny"], "live unresolved") != reconstructed:
            _fail_accounting(out, EXPOSURE_DISAGREE)
    if hold is None and reconstructed == 0 and claimed_unknown is not None and claimed_unknown > 0:
        _fail_accounting(out, EXPOSURE_UNRESOLVED)
    state = CapState(settled, calls, events, None, loaded_events)
    state.sticky = sticky
    _note_recorded_inputs(state, calls, hold)
    return state


def _append_ledger(path: Path, row: dict) -> None:
    _require_owner(path.parent)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        existing = path.read_bytes()
        if existing and not existing.endswith(b"\n"):
            with path.open("ab") as handle:
                handle.write(b"\n")
                handle.flush()
                os.fsync(handle.fileno())
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _is_timeout(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return True
    text = str(exc).lower()
    return "timed out" in text or "timeout" in text


def _pending_record(slot: dict, amount: Decimal, moment) -> dict:
    return {
        "slot_id": slot["slot_id"],
        "request_sha256": slot["request_sha256"],
        "case_id": slot["case_id"],
        "thinking": slot["thinking"],
        "held_worst_case_cny": _money(amount),
        "clock": moment.isoformat(),
        "reason": "in flight",
    }


def _hold_pending(state: CapState, reason: str, actual: Decimal | None = None) -> None:
    pending = state.pending
    if not isinstance(pending, dict):
        raise AmendmentFlightRefused("missing in-flight hold")
    amount = Decimal(pending["held_worst_case_cny"])
    if actual is not None and actual > amount:
        amount = actual
    event = dict(pending)
    event["held_worst_case_cny"] = _money(amount)
    event["reason"] = reason
    state.events.append(event)
    state.pending = None


def _remaining(slots: list[dict], incomplete: set[str], costs: dict[str, Decimal]) -> Decimal:
    return sum((costs[slot["request_sha256"]] for slot in slots if slot["slot_id"] in incomplete), Decimal("0"))


def _reserved_remaining(incomplete: set[str]) -> Decimal:
    return documented_call_reserve_cny() * len(incomplete)


def _budget_exceeds(state: CapState, incomplete: set[str], ceiling: Decimal) -> bool:
    """True when settled spend, unknown holds, and documented reservations pass the ceiling."""
    return state.exposure_base + _reserved_remaining(incomplete) > ceiling


def _cap_extra(
    state: CapState,
    reserved: Decimal,
    local_remaining: Decimal,
    slots: list[dict],
    incomplete: set[str],
) -> dict:
    return {
        "remaining_worst_case_cny": _money(reserved),
        "local_estimate_remaining_cny": _money(local_remaining),
        "held_plus_remaining_cny": _money(state.exposure_base + reserved),
        "slots_remaining": len(incomplete),
        "slots_planned": len(slots),
        "loaded_timeout_events": state.loaded_events,
        "documented_call_reserve_cny": _money(documented_call_reserve_cny()),
        "spending_guarantee": False,
        "provider_enforced_spend_limit": False,
        "ceiling_is_hard_stop": False,
        "local_estimate_is_not_an_invoice": True,
        "money_limit": ESTIMATED_TO_FIT,
    }


def _refuse_live_client(client) -> None:
    name = type(client).__name__
    module = type(client).__module__
    if name == "LiveClient" or module.endswith("official_840_provider") or module.endswith("usx_provider"):
        raise AmendmentFlightRefused(OFFICIAL_DISPATCH_STOP)


def _response_bill(payload) -> tuple[dict | None, Decimal | None]:
    usage = payload.get("usage") if isinstance(payload, dict) else None
    try:
        bill = usage_bill(OFFPEAK, usage)
    except UsxFlightRefused:
        return None, None
    return bill, Decimal(bill["spend_cny"])


def _acceptable(slot: dict, payload, bill: dict | None) -> bool:
    if bill is None or not isinstance(payload, dict) or not payload.get("choices"):
        return False
    if bill["output_tokens"] > MAX_TOKENS:
        return False
    if slot["thinking"] == "off" and not _thinking_stayed_off(payload):
        return False
    return True


def _write_live(out: Path, state: CapState, ceiling: Decimal) -> dict:
    _require_owner(out)
    if state.pending is not None:
        raise AmendmentFlightRefused("in-flight hold is still open")
    if state.settled + state.unknown > ceiling or state.settled + state.unknown > HARD_CAP_CNY:
        raise AmendmentFlightRefused("settled spend plus unknown holds would pass the supplied ceiling")
    record = {
        "purpose": PURPOSE,
        "catalogue_tip": CATALOGUE_TIP,
        "official_settlement": False,
        "official_v1_1": OFFICIAL_V11,
        "human_review": HUMAN_REVIEW,
        "flight_ready": False,
        "provider_call_authorized": False,
        "complete": True,
        "synthetic": True,
        "live": False,
        "provider_called": False,
        "provider_network": False,
        "spend_cny": _money(state.settled),
        "outstanding_unknown_timeout_cny": _money(state.unknown),
        "unknown_charges_reconciled": state.unknown == 0,
        "ceiling_cny": _money(ceiling),
        "hard_cap_cny": _money(HARD_CAP_CNY),
        "ceiling_lifted": False,
        "slots_settled": len(state.calls),
        "max_tokens": MAX_TOKENS,
        "arms": list(ARMS),
        "spending_guarantee": False,
        "provider_enforced_spend_limit": False,
        "money_limit": ESTIMATED_TO_FIT,
        "documented_call_reserve_cny": _money(documented_call_reserve_cny()),
        "note": (
            "Scripted completion whose ceiling covered settled spend, unknown holds, "
            "and the documented per-call reservation. The local model is estimated "
            "to fit ¥80 and is not a spending cap. This is not a provider call and "
            "not a paid flight."
        ),
    }
    _write_hold(out, state)
    stop_file = _stop_path(out)
    if stop_file.is_file():
        stop_file.unlink()
    _atomic_json(_live_path(out), record)
    return record


def wire_manifest(plans: list[dict]) -> dict:
    """Identity of one entire wire plan. A resume has to match this manifest."""
    slots = wire_slots(plans)
    if len({slot["slot_id"] for slot in slots}) != len(slots):
        raise AmendmentFlightRefused("wire slots are not unique")
    entries = []
    for index, slot in enumerate(slots):
        if slot["body"].get(MAX_TOKENS_FIELD) != MAX_TOKENS:
            raise AmendmentFlightRefused("frozen manifest requires the explicit max_tokens wire body")
        fresh = request_sha256(slot["body"])
        if fresh != slot["request_sha256"]:
            raise AmendmentFlightRefused(HASH_LABEL_MISMATCH)
        entries.append(
            {
                "index": index,
                "slot_id": slot["slot_id"],
                "request_sha256": fresh,
                "arms": list(slot["arms"]),
                "case_id": slot["case_id"],
                "category": slot["category"],
                "thinking": slot["thinking"],
                "cell": slot["cell"],
                "max_tokens": MAX_TOKENS,
            }
        )
    encoded = json.dumps(entries, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return {
        "purpose": PURPOSE,
        "catalogue_tip": CATALOGUE_TIP,
        "frozen": True,
        "entire_original_plan": True,
        "slot_count": len(entries),
        "manifest_sha256": digest,
        "slots": entries,
    }


def _manifest_path(out: Path) -> Path:
    return Path(out) / MANIFEST_NAME


def _accounting_present(out: Path) -> bool:
    return any((Path(out) / name).exists() for name in ACCOUNTING_NAMES)


def _peek_accounting(out: Path) -> None:
    """Refuse unreadable records before a resume is allowed to adopt a plan."""
    _read_json_object(_hold_path(out), "cap hold")
    _read_json_object(_stop_path(out), "stop record")
    _read_json_object(_live_path(out), "live record")
    ledger = _ledger_path(out)
    if ledger.is_file():
        _load_ledger(ledger)


def _refuse_if_spend_would_reset(out: Path) -> None:
    """Refuse before a resume can treat missing evidence as zero spend.

    The read is the public recovery path: it does not rewrite accounting.
    """
    load_cap_state(out)


def _bind_wire_manifest(out: Path, plans: list[dict]) -> dict:
    expected = wire_manifest(plans)
    _peek_accounting(out)
    _refuse_if_spend_would_reset(out)
    path = _manifest_path(out)
    if path.is_file():
        stored = _read_json_object(path, "frozen wire manifest")
        if stored is None:
            raise AmendmentFlightRefused("frozen wire manifest is corrupt")
        if stored.get("catalogue_tip") != CATALOGUE_TIP or stored.get("entire_original_plan") is not True:
            raise AmendmentFlightRefused(MANIFEST_MISMATCH)
        if stored.get("manifest_sha256") != expected["manifest_sha256"] or stored.get("slots") != expected["slots"]:
            raise AmendmentFlightRefused(MANIFEST_MISMATCH)
        if stored.get("slot_count") != expected["slot_count"]:
            raise AmendmentFlightRefused(MANIFEST_MISMATCH)
        return stored
    if _accounting_present(out):
        raise AmendmentFlightRefused(MANIFEST_MISSING)
    _atomic_json(path, expected)
    return expected


def _acquire_run(out: Path) -> tuple[int, contextvars.Token]:
    """Exclusive owner of one run directory. The lock dies with this process."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    fd = os.open(out / LOCK_NAME, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        os.close(fd)
        raise AmendmentFlightRefused(OWNER_HELD) from exc
    token = _RUN_OWNER.set(str(out.resolve()))
    try:
        os.ftruncate(fd, 0)
        os.write(fd, f"pid={os.getpid()}\n".encode())
    except OSError:
        pass
    return fd, token


def _release_run(fd: int, token: contextvars.Token) -> None:
    try:
        _RUN_OWNER.reset(token)
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def execute_scripted(
    plans: list[dict],
    out: Path,
    ceiling: Decimal,
    clock,
    client,
    counter: TiktokenCounter | None = None,
    *,
    dispatch: bool = False,
) -> dict:
    """Run cap checks. Dispatch only a scripted non-official sample when asked.

    The official 840 sample is never dispatched. ``dispatch`` false never calls
    ``client``. A partial run does not write ``live.json``. A second process
    that resumes the same directory is refused.
    """
    if counter is not None and counter.name != "o200k_base":
        raise AmendmentFlightRefused("local bound requires o200k_base")
    ceiling = accept_run_ceiling(ceiling)
    if not plans:
        raise AmendmentFlightRefused("no plans")
    _assert_passes_distinct(plans)
    out = Path(out)
    owner = _acquire_run(out)
    try:
        return _execute_owned(plans, out, ceiling, clock, client, dispatch=dispatch)
    finally:
        _release_run(*owner)


def _manifest_index(manifest: dict) -> dict[str, dict]:
    slots = manifest.get("slots")
    if not isinstance(slots, list):
        raise AmendmentFlightRefused("frozen wire manifest is corrupt")
    index: dict[str, dict] = {}
    for entry in slots:
        if not isinstance(entry, dict) or not isinstance(entry.get("slot_id"), str) or entry["slot_id"] == "":
            raise AmendmentFlightRefused("frozen wire manifest is corrupt")
        if entry["slot_id"] in index:
            raise AmendmentFlightRefused("frozen wire manifest is corrupt")
        index[entry["slot_id"]] = entry
    return index


def _settlement_conflict(state: CapState, by_slot: dict[str, dict]) -> str | None:
    """A stored hash that is not the manifest entry blocks another send."""
    for row in state.calls:
        entry = by_slot.get(row.get("slot_id"))
        if entry is None:
            return SETTLEMENT_MISMATCH
        label = row.get("request_sha256")
        if label is not None and label != entry.get("request_sha256"):
            return SETTLEMENT_MISMATCH
    return None


def _completion_conflict(state: CapState, by_slot: dict[str, dict]) -> str | None:
    """Completion requires every settlement to match one manifest entry."""
    if len(state.calls) != len(by_slot):
        return SETTLEMENT_MISMATCH
    seen: set[str] = set()
    for row in state.calls:
        slot_id = row.get("slot_id")
        entry = by_slot.get(slot_id)
        if entry is None or row.get("request_sha256") != entry.get("request_sha256"):
            return SETTLEMENT_MISMATCH
        seen.add(slot_id)
    if seen != set(by_slot):
        return SETTLEMENT_MISMATCH
    return None


def _execute_owned(plans: list[dict], out: Path, ceiling: Decimal, clock, client, *, dispatch: bool) -> dict:
    _pin_tokenizer_cache()
    manifest = _bind_wire_manifest(out, plans)
    by_slot = _manifest_index(manifest)
    slots = wire_slots(plans)
    costs: dict[str, Decimal] = {}
    for slot in slots:
        digest = slot["request_sha256"]
        if digest not in costs:
            costs[digest] = worst_case_cny(slot["body"])
    state = load_cap_state(out)
    plan_ids = {slot["slot_id"] for slot in slots}
    for row in state.calls:
        if row["slot_id"] not in plan_ids:
            _fail_accounting(out, "calls ledger does not match these plans")
    conflict = _settlement_conflict(state, by_slot)
    if conflict:
        _fail_accounting(out, conflict)
    incomplete = {slot["slot_id"] for slot in slots} - {row["slot_id"] for row in state.calls}
    reserve = documented_call_reserve_cny()

    def stop(reason: str, extra: dict | None = None) -> None:
        reserved = _reserved_remaining(incomplete)
        local_remaining = _remaining(slots, incomplete, costs)
        payload = _cap_extra(state, reserved, local_remaining, slots, incomplete)
        if extra:
            payload.update(extra)
        _write_stop(out, state, ceiling, reason, payload)

    if state.sticky:
        stop(state.sticky)
        raise AmendmentFlightRefused(state.sticky)
    if _budget_exceeds(state, incomplete, ceiling):
        if not incomplete:
            reason = "settled spend plus unknown holds would pass the supplied ceiling"
        else:
            reason = CAP_STOP
        stop(reason)
        raise AmendmentFlightRefused(reason)
    if not incomplete:
        if is_official_sample(plans):
            stop(OFFICIAL_DISPATCH_STOP)
            raise AmendmentFlightRefused(OFFICIAL_DISPATCH_STOP)
        if state.settled + state.unknown > ceiling:
            stop("settled spend plus unknown holds would pass the supplied ceiling")
            raise AmendmentFlightRefused("settled spend plus unknown holds would pass the supplied ceiling")
        completion = _completion_conflict(state, by_slot)
        if completion:
            _fail_accounting(out, completion)
        return _write_live(out, state, ceiling)
    if not dispatch:
        stop(LIVE_STOP)
        raise AmendmentFlightRefused(LIVE_STOP)
    if is_official_sample(plans):
        stop(OFFICIAL_DISPATCH_STOP)
        raise AmendmentFlightRefused(OFFICIAL_DISPATCH_STOP)
    if client is None:
        stop(LIVE_STOP)
        raise AmendmentFlightRefused(LIVE_STOP)
    _refuse_live_client(client)

    for slot in slots:
        if slot["slot_id"] not in incomplete:
            continue
        moment = clock()
        if schedule_at(moment) != OFFPEAK:
            stop("peak_hours")
            raise AmendmentFlightRefused("peak_hours")
        body = slot["body"]
        if body.get(MAX_TOKENS_FIELD) != MAX_TOKENS or body.get("model") != MODEL:
            raise AmendmentFlightRefused("refusing to send a body without the explicit output-token limit")
        if body.get("temperature") != BFCL_DEFAULT_TEMPERATURE or body.get("store") is not False:
            raise AmendmentFlightRefused("refusing a wire body that drops temperature 0.001 or store false")
        if body["thinking"] != thinking_body(slot["thinking"]):
            raise AmendmentFlightRefused("thinking field does not match the pass")
        if _budget_exceeds(state, incomplete, ceiling):
            stop(CAP_STOP, {"next_call_reserve_cny": _money(reserve)})
            raise AmendmentFlightRefused(CAP_STOP)
        outgoing = deepcopy(body)
        fresh = request_sha256(outgoing)
        entry = by_slot.get(slot["slot_id"])
        if entry is None or fresh != entry.get("request_sha256") or fresh != slot["request_sha256"]:
            raise AmendmentFlightRefused(SEND_HASH_MISMATCH)
        state.pending = _pending_record(slot, reserve, moment)
        _write_hold(out, state)
        try:
            payload = client.complete(outgoing)
        except AmendmentFlightRefused:
            _hold_pending(state, "call refused")
            stop(UNKNOWN_STOP)
            raise AmendmentFlightRefused(UNKNOWN_STOP) from None
        except Exception as exc:
            timeout = _is_timeout(exc)
            reason = "timeout" if timeout else "call failed before a settled bill"
            _hold_pending(state, reason)
            stop_reason = TIMEOUT_STOP if timeout else UNKNOWN_STOP
            stop(stop_reason, {"timed_out_request_sha256": fresh})
            raise AmendmentFlightRefused(stop_reason) from None
        bill, actual = _response_bill(payload)
        local_in = local_input_tokens(outgoing)
        billed_in = bill.get("T") if isinstance(bill, dict) else None
        if isinstance(billed_in, bool) or not isinstance(billed_in, int) or billed_in < 0:
            billed_in = None
        if billed_in is not None:
            state.note_input(local_in, billed_in)
        input_gap = {
            "local_input_tokens": local_in,
            "billed_input_tokens": billed_in,
            "input_above_local_estimate": billed_in is not None and billed_in > local_in,
            "documented_call_reserve_cny": _money(reserve),
            "returned_bill_above_documented_reserve": actual is not None and actual > reserve,
        }
        if not _acceptable(slot, payload, bill):
            _hold_pending(state, "response was not a settled off-peak completion", actual)
            stop(UNKNOWN_STOP, input_gap)
            raise AmendmentFlightRefused(UNKNOWN_STOP)
        state.settled += actual
        state.pending = None
        observation = {
            "slot_id": slot["slot_id"],
            "case_id": slot["case_id"],
            "cell": slot["cell"],
            "thinking": slot["thinking"],
            "arms": list(slot["arms"]),
            "shared": len(slot["arms"]) > 1,
            "request_sha256": fresh,
            "schedule": OFFPEAK,
            "max_tokens": MAX_TOKENS,
            "clock": moment.isoformat(),
            "bill": bill,
            "local_input_tokens": local_in,
            "billed_input_tokens": billed_in,
            "input_above_local_estimate": billed_in is not None and billed_in > local_in,
            "provider_called": False,
            "provider_network": False,
            "scripted": True,
        }
        state.calls.append(observation)
        _append_ledger(_ledger_path(out), observation)
        _write_hold(out, state)
        incomplete.discard(slot["slot_id"])
        if actual > reserve or _budget_exceeds(state, incomplete, ceiling):
            if actual > reserve:
                reason = OVER_RESERVE_STOP
            elif not incomplete:
                reason = "settled spend plus unknown holds would pass the supplied ceiling"
            else:
                reason = "settled spend passed the supplied ceiling"
            stop(reason, input_gap)
            raise AmendmentFlightRefused(reason)
    if incomplete:
        stop("run ended with incomplete slots")
        raise AmendmentFlightRefused("run ended with incomplete slots")
    if state.settled + state.unknown > ceiling:
        stop("settled spend plus unknown holds would pass the supplied ceiling")
        raise AmendmentFlightRefused("settled spend plus unknown holds would pass the supplied ceiling")
    completion = _completion_conflict(state, by_slot)
    if completion:
        _fail_accounting(out, completion)
    return _write_live(out, state, ceiling)


def _gate(summary: dict, moment, reservation_fits: bool, manifest: dict, reservation: Decimal) -> dict:
    plan_totals = summary["token_totals_plan"]["all_840"]
    wire_totals = summary["token_totals_wire"]["all_840"]
    estimate = summary["remaining_run_worst_case_cny"]
    estimate_fits = estimate <= HARD_CAP_CNY
    return {
        "purpose": PURPOSE,
        "catalogue_tip": CATALOGUE_TIP,
        "official_settlement": False,
        "official_v1_1": OFFICIAL_V11,
        "human_review": HUMAN_REVIEW,
        "flight_ready": False,
        "provider_call_authorized": False,
        "paid_flight_ready": False,
        "live_dispatch": "refused",
        "calls_dispatched": 0,
        "provider_called": False,
        "provider_network": False,
        "api_key_in_record": False,
        "live_json_written": False,
        "arms": list(ARMS),
        "model": MODEL,
        "temperature": BFCL_DEFAULT_TEMPERATURE,
        "store": BFCL_STORE,
        "thinking_passes": list(PASSES),
        "off_peak_only": True,
        "schedule_at_gate": schedule_at(moment),
        "max_tokens": MAX_TOKENS,
        "max_tokens_note": MAX_TOKENS_NOTE,
        "hard_cap_cny": _money(HARD_CAP_CNY),
        "hard_cap_note": HARD_CAP_NOTE,
        "hard_cap_funds_remaining_run": reservation_fits,
        "start_refused": not reservation_fits,
        "spending_guarantee": False,
        "provider_enforced_spend_limit": False,
        "money_limit": ESTIMATED_TO_FIT if estimate_fits else "local estimate exceeds ¥80",
        "local_estimate_fits_ceiling": estimate_fits,
        "documented_reservation_fits_ceiling": reservation_fits,
        "documented_call_reserve_cny": _money(documented_call_reserve_cny()),
        "documented_reservation_cny": _money(reservation),
        "manifest_sha256": manifest["manifest_sha256"],
        "manifest_persisted_before_send": True,
        "remaining_run_note": REMAINING_RUN_NOTE,
        "remaining_run_worst_case_cny": _money(estimate),
        "unique_hash_worst_case_cny": _money(summary["unique_hash_worst_case_cny"]),
        "send_slots": summary["send_slots"],
        "cross_cell_duplicate_sends": summary["cross_cell_duplicate_sends"],
        "rate_card": rate_card(OFFPEAK),
        "rate_card_applied_as": "off-peak all-miss local input plus max_tokens output",
        "local_tokens_are_provider_T": False,
        "plan_hash_identity": {
            "builder": "tool_compression.official_840.generation_body",
            "includes_questions": True,
            "question_turn": 0,
            "includes_max_tokens": False,
            "unique_per_pass": summary["unique_plan_hashes"],
            "unique_union": summary["unique_plan_union"],
            "unique_by_scope": summary["unique_by_scope_plan"],
            "local_o200k_totals_by_arm_and_mode": plan_totals,
            "local_o200k_totals_by_scope": summary["token_totals_plan"],
            "note": "Plan hashes omit max_tokens. They are the four-arm identity check.",
        },
        "wire_hash_identity": {
            "includes_max_tokens": MAX_TOKENS,
            "only_added_field": MAX_TOKENS_FIELD,
            "hashes_equal_plan_hashes": False,
            "plan_and_wire_hash_sets_disjoint": summary["plan_and_wire_hash_sets_disjoint"],
            "unique_per_pass": summary["unique_wire_hashes"],
            "unique_union": summary["unique_wire_union"],
            "local_o200k_totals_by_arm_and_mode": wire_totals,
            "local_o200k_totals_by_scope": summary["token_totals_wire"],
            "wire_minus_plan_token_deltas": summary["wire_minus_plan_token_deltas"],
            "note": (
                "Every wire body is the plan body plus max_tokens. "
                "The field is not removed to keep the plan hash. "
                "Local o200k counts are not provider T."
            ),
        },
    }


def preflight(bfcl_root: Path, out: Path, clock, repo: Path | None = None) -> dict:
    """Write the offline gate. Does not call a provider or authorize a flight."""
    out = Path(out)
    owner = _acquire_run(out)
    try:
        return _preflight_owned(bfcl_root, out, clock, repo)
    finally:
        _release_run(*owner)


def _preflight_owned(bfcl_root: Path, out: Path, clock, repo: Path | None) -> dict:
    for name in (*ACCOUNTING_NAMES, MANIFEST_NAME):
        if (out / name).exists():
            raise AmendmentFlightRefused("preflight directory already has a run record; refusing to relabel it")
    flight = build_flight(bfcl_root, repo)
    summary = summarize_flight(flight["plans"], local_counter())
    manifest = wire_manifest(flight["plans"])
    # Pin the verified manifest before this function returns, including the
    # path that would later be allowed to send if the reservation fit.
    _atomic_json(_manifest_path(out), manifest)
    moment = clock()
    reservation = documented_call_reserve_cny() * summary["send_slots"]
    reservation_fits = reservation <= HARD_CAP_CNY
    gate = _gate(summary, moment, reservation_fits, manifest, reservation)
    gate["control_cases"] = flight["control_cases"]
    gate["control_x2_equals_u"] = flight["control_x2_equals_u"]
    gate["control_sx2_equals_s2"] = flight["control_sx2_equals_s2"]
    gate["sample_cases"] = len(flight["order"])
    _atomic_json(out / "gate.json", gate)
    if not reservation_fits:
        state = CapState(Decimal("0"), [], [], None, 0)
        _write_stop(
            out,
            state,
            HARD_CAP_CNY,
            CAP_STOP,
            {
                "remaining_worst_case_cny": _money(reservation),
                "local_estimate_remaining_cny": _money(summary["remaining_run_worst_case_cny"]),
                "held_plus_remaining_cny": _money(reservation),
                "slots_remaining": summary["send_slots"],
                "slots_planned": summary["send_slots"],
                "unique_wire_hashes": summary["unique_wire_union"],
                "documented_reservation_cny": _money(reservation),
            },
        )
    return gate


def main(argv: list[str] | None = None) -> int:
    """Offline gate. ``--live`` is refused and does not read a key or open a socket."""
    parser = argparse.ArgumentParser(prog="tool_compression.amendment_s2x2_flight")
    parser.add_argument("--bfcl-root", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args(argv)
    if args.live:
        try:
            refuse_provider_call()
        except AmendmentFlightRefused as exc:
            print(str(exc))
            return 2
    if args.bfcl_root is None or args.out is None:
        print("bfcl root and out are required")
        return 2

    def clock():
        return datetime.now(SHANGHAI)

    try:
        gate = preflight(args.bfcl_root, args.out, clock)
    except AmendmentFlightRefused as exc:
        print(str(exc))
        return 1
    print(
        json.dumps(
            {
                "provider_called": gate["provider_called"],
                "provider_call_authorized": gate["provider_call_authorized"],
                "flight_ready": gate["flight_ready"],
                "paid_flight_ready": gate["paid_flight_ready"],
                "hard_cap_cny": gate["hard_cap_cny"],
                "hard_cap_funds_remaining_run": gate["hard_cap_funds_remaining_run"],
                "remaining_run_worst_case_cny": gate["remaining_run_worst_case_cny"],
                "send_slots": gate["send_slots"],
                "unique_plan_union": gate["plan_hash_identity"]["unique_union"],
                "unique_wire_union": gate["wire_hash_identity"]["unique_union"],
                "official_settlement": gate["official_settlement"],
                "human_review": gate["human_review"],
            },
            sort_keys=True,
        )
    )
    if not gate["hard_cap_funds_remaining_run"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
