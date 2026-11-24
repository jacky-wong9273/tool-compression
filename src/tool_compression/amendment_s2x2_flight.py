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
- bills a remaining-run worst case of off-peak all-miss local o200k tokens of
  each still-unsettled wire send, plus ``max_tokens`` output
- refuses to start when settled spend + unknown-timeout holds + that remaining
  sum would pass the ceiling, and never writes ``live.json`` for a partial run
- after a timeout, or any call whose charge is unknown, holds that call's
  worst case and will not send further calls unless the ceiling still covers
  the hold plus the remaining-run worst case; a resume reloads the hold
- does not read an API key and does not open a provider socket on the offline gate

Run the offline gate with ``python -m tool_compression.amendment_s2x2_flight``.
``--live`` alone is refused before a plan is built. The authorized command is
``--live --authorize-official-live``. The frozen ``amendment-s2x2`` command is
left unchanged so its packet hash stays the catalogue revision.

8192 is the next power of two above the #12 840-case ledger maximum of 7063
output tokens (p99 1010; three calls above 2048). It is a wire limit, not a
retune of official r or lambda. Plan hashes omit the field on purpose. Wire
hashes differ because the field is present; it is not dropped to preserve the
plan hash.

Jacky set the hard cap at ¥80.00 for this runner dig. That is not authorization
to fly. Official settlement stays false. Human review was not performed.
The paid flight is not ready. Local o200k counts are not provider T.

``send_evaluation`` / ``send_frozen_plan`` send the frozen U/S2/X2/SX2 plan,
both thinking passes, and record spend after each request completes. The
confirmed charge is used when the response has one. An unresolved attempt,
such as a timeout, stays in the running total until a confirmed charge for
that same attempt is noted. Another try is a separate attempt and is counted
too. The hard ceiling is ¥80.00 across both passes. Reaching it stops further
sends and writes ``ceiling-notice.json``. About ¥10 is a comfortable
expectation, not a stop. The sender does not reserve the next request and
does not stop early on a remaining-run worst case. ``--live`` alone returns
before a plan is built and does not read a key. ``--live
--authorize-official-live`` builds the frozen plan and uses the provider
client. Official settlement stays false. Human review was not performed.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
import argparse
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
OFFPEAK = "off-peak"
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
    "Jacky set a hard spending cap of ¥80.00 for this runner dig. The cap is "
    "not authorization to fly. Official v1.1 stays closed. Human review was "
    "not performed. The paid flight is not ready."
)
REMAINING_RUN_NOTE = (
    "Remaining-run worst case sums every not-yet-settled within-cell wire "
    "send: off-peak all-miss local o200k tokens of that wire body, plus "
    "max_tokens output. Identical payloads are shared only inside one case "
    "and one thinking pass, so a repeated hash in another cell is another "
    "send. A timed-out call stays incomplete and is also held as an unknown "
    "charge. Local tokens are not provider T."
)
CAP_STOP = "remaining worst-case would pass the supplied ceiling"
TIMEOUT_STOP = "provider timed out; unknown charge held at this call's worst-case bound"
UNKNOWN_STOP = "provider call failed; unknown charge held at this call's worst-case bound"
LIVE_STOP = (
    "provider call refused; this dig does not authorize a flight; "
    "official settlement stays false; human review was not performed"
)
OFFICIAL_DISPATCH_STOP = "refusing to dispatch the official 840 sample; the paid flight is not authorized"
OVER_CAP_STOP = "ceiling exceeds the ¥80.00 hard cap"
COMFORTABLE_EXPECTATION_CNY = Decimal("10.00")
SENDER_PURPOSE = "amendment-s2x2-sender"
ATTEMPT_LEDGER_NAME = "attempt-ledger.jsonl"
SENDER_STATUS_NAME = "sender-status.json"
CEILING_NOTICE_NAME = "ceiling-notice.json"
CEILING_NOTICE_TEXT = (
    "CNY ¥80.00 hard ceiling reached across both thinking passes. "
    "Further sends are stopped. Tell the operator."
)


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
    """Off-peak all-miss input of the wire body, plus max_tokens output."""
    if body.get(MAX_TOKENS_FIELD) != MAX_TOKENS:
        raise AmendmentFlightRefused("worst case requires the explicit max_tokens wire body")
    return spend_cny(OFFPEAK, local_input_tokens(body), 0, MAX_TOKENS)


def accept_run_ceiling(value: Decimal) -> Decimal:
    """A positive Decimal at or under the ¥80.00 hard cap. Floats are refused."""
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


def _atomic_json(path: Path, payload: dict) -> None:
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
    path = _live_path(out)
    if path.is_file():
        path.unlink()


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
        "note": REMAINING_RUN_NOTE,
    }


def _write_hold(out: Path, state: CapState) -> None:
    _atomic_json(_hold_path(out), _hold_payload(state))


def _write_stop(out: Path, state: CapState, ceiling: Decimal, reason: str, extra: dict | None = None) -> None:
    _discard_live(out)
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
    }
    if extra:
        record.update(extra)
    _atomic_json(_stop_path(out), record)


def _load_ledger(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    calls = []
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            if index == len(lines) - 1:
                break
            raise AmendmentFlightRefused("calls ledger is corrupt")
        bill = item.get("bill") if isinstance(item, dict) else None
        if not isinstance(bill, dict) or "spend_cny" not in bill:
            raise AmendmentFlightRefused("calls ledger is corrupt")
        _decimal_field(bill["spend_cny"], "ledger spend")
        calls.append(item)
    return calls


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
    """Reload settled spend and unknown holds. An in-flight call becomes a hold."""
    out = Path(out)
    calls = _load_ledger(_ledger_path(out))
    settled = Decimal("0")
    settled_slots: set[str] = set()
    for row in calls:
        settled += Decimal(row["bill"]["spend_cny"])
        slot_id = row.get("slot_id")
        if not isinstance(slot_id, str) or slot_id == "":
            raise AmendmentFlightRefused("calls ledger is missing slot_id")
        if slot_id in settled_slots:
            raise AmendmentFlightRefused("calls ledger repeats a slot")
        settled_slots.add(slot_id)
    events: list[dict] = []
    pending = None
    stored_unknown = Decimal("0")
    sticky = None
    path = _hold_path(out)
    if path.is_file():
        try:
            hold = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise AmendmentFlightRefused("cap hold is corrupt") from exc
        if not isinstance(hold, dict):
            raise AmendmentFlightRefused("cap hold is corrupt")
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
    state = CapState(settled, calls, events, None, loaded_events)
    state.sticky = sticky
    if path.is_file():
        _write_hold(out, state)
    return state


def _append_ledger(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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


def _cap_extra(state: CapState, remaining: Decimal, slots: list[dict], incomplete: set[str]) -> dict:
    return {
        "remaining_worst_case_cny": _money(remaining),
        "held_plus_remaining_cny": _money(state.exposure_base + remaining),
        "slots_remaining": len(incomplete),
        "slots_planned": len(slots),
        "loaded_timeout_events": state.loaded_events,
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
        "note": (
            "Scripted completion of a non-official sample whose ceiling covered "
            "settled spend, unknown timeout holds, and the remaining-run worst case. "
            "This is not a provider call and not a paid flight."
        ),
    }
    _write_hold(out, state)
    stop_file = _stop_path(out)
    if stop_file.is_file():
        stop_file.unlink()
    _atomic_json(_live_path(out), record)
    return record


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
    ``client``. A partial run does not write ``live.json``.
    """
    if counter is not None and counter.name != "o200k_base":
        raise AmendmentFlightRefused("local bound requires o200k_base")
    ceiling = accept_run_ceiling(ceiling)
    if not plans:
        raise AmendmentFlightRefused("no plans")
    _assert_passes_distinct(plans)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    _pin_tokenizer_cache()
    slots = wire_slots(plans)
    if len({slot["slot_id"] for slot in slots}) != len(slots):
        raise AmendmentFlightRefused("wire slots are not unique")
    costs: dict[str, Decimal] = {}
    for slot in slots:
        digest = slot["request_sha256"]
        if digest not in costs:
            costs[digest] = worst_case_cny(slot["body"])
    state = load_cap_state(out)
    plan_ids = {slot["slot_id"] for slot in slots}
    for row in state.calls:
        if row["slot_id"] not in plan_ids:
            raise AmendmentFlightRefused("calls ledger does not match these plans")
    incomplete = {slot["slot_id"] for slot in slots} - {row["slot_id"] for row in state.calls}
    remaining = _remaining(slots, incomplete, costs)

    def stop(reason: str, extra: dict | None = None) -> None:
        payload = _cap_extra(state, _remaining(slots, incomplete, costs), slots, incomplete)
        if extra:
            payload.update(extra)
        _write_stop(out, state, ceiling, reason, payload)

    if state.sticky:
        stop(state.sticky)
        raise AmendmentFlightRefused(state.sticky)
    if state.exposure_base + remaining > ceiling:
        stop(CAP_STOP)
        raise AmendmentFlightRefused(CAP_STOP)
    if not incomplete:
        if is_official_sample(plans):
            stop(OFFICIAL_DISPATCH_STOP)
            raise AmendmentFlightRefused(OFFICIAL_DISPATCH_STOP)
        if state.settled + state.unknown > ceiling:
            stop("settled spend plus unknown holds would pass the supplied ceiling")
            raise AmendmentFlightRefused("settled spend plus unknown holds would pass the supplied ceiling")
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
        cost = costs[slot["request_sha256"]]
        remaining = _remaining(slots, incomplete, costs)
        if state.exposure_base + remaining > ceiling or state.exposure_base + cost > ceiling:
            stop(CAP_STOP, {"next_call_worst_case_cny": _money(cost)})
            raise AmendmentFlightRefused(CAP_STOP)
        state.pending = _pending_record(slot, cost, moment)
        _write_hold(out, state)
        try:
            payload = client.complete(deepcopy(body))
        except AmendmentFlightRefused:
            _hold_pending(state, "call refused")
            stop(UNKNOWN_STOP)
            raise AmendmentFlightRefused(UNKNOWN_STOP) from None
        except Exception as exc:
            timeout = _is_timeout(exc)
            reason = "timeout" if timeout else "call failed before a settled bill"
            _hold_pending(state, reason)
            stop_reason = TIMEOUT_STOP if timeout else UNKNOWN_STOP
            stop(stop_reason, {"timed_out_request_sha256": slot["request_sha256"]})
            raise AmendmentFlightRefused(stop_reason) from None
        bill, actual = _response_bill(payload)
        if not _acceptable(slot, payload, bill):
            _hold_pending(state, "response was not a settled off-peak completion", actual)
            stop(UNKNOWN_STOP)
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
            "request_sha256": slot["request_sha256"],
            "schedule": OFFPEAK,
            "max_tokens": MAX_TOKENS,
            "clock": moment.isoformat(),
            "bill": bill,
            "provider_called": False,
            "provider_network": False,
            "scripted": True,
        }
        state.calls.append(observation)
        _append_ledger(_ledger_path(out), observation)
        _write_hold(out, state)
        incomplete.discard(slot["slot_id"])
        if state.settled > ceiling or state.settled + state.unknown > ceiling:
            stop("settled spend passed the supplied ceiling")
            raise AmendmentFlightRefused("settled spend passed the supplied ceiling")
    if incomplete:
        stop("run ended with incomplete slots")
        raise AmendmentFlightRefused("run ended with incomplete slots")
    if state.settled + state.unknown > ceiling:
        stop("settled spend plus unknown holds would pass the supplied ceiling")
        raise AmendmentFlightRefused("settled spend plus unknown holds would pass the supplied ceiling")
    return _write_live(out, state, ceiling)


def _gate(summary: dict, moment, funded: bool) -> dict:
    plan_totals = summary["token_totals_plan"]["all_840"]
    wire_totals = summary["token_totals_wire"]["all_840"]
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
        "hard_cap_funds_remaining_run": funded,
        "start_refused": not funded,
        "remaining_run_note": REMAINING_RUN_NOTE,
        "remaining_run_worst_case_cny": _money(summary["remaining_run_worst_case_cny"]),
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
    """Write the offline gate for the ¥80 cap. Does not call a provider."""
    out = Path(out)
    for name in ("calls-ledger.jsonl", "cap-hold.json", "live.json", "stop.json"):
        if (out / name).exists():
            raise AmendmentFlightRefused("preflight directory already has a run record; refusing to relabel it")
    flight = build_flight(bfcl_root, repo)
    summary = summarize_flight(flight["plans"], local_counter())
    moment = clock()
    funded = summary["remaining_run_worst_case_cny"] <= HARD_CAP_CNY
    gate = _gate(summary, moment, funded)
    gate["control_cases"] = flight["control_cases"]
    gate["control_x2_equals_u"] = flight["control_x2_equals_u"]
    gate["control_sx2_equals_s2"] = flight["control_sx2_equals_s2"]
    gate["sample_cases"] = len(flight["order"])
    _atomic_json(out / "gate.json", gate)
    if not funded:
        state = CapState(Decimal("0"), [], [], None, 0)
        _write_stop(
            out,
            state,
            HARD_CAP_CNY,
            CAP_STOP,
            {
                "remaining_worst_case_cny": _money(summary["remaining_run_worst_case_cny"]),
                "held_plus_remaining_cny": _money(summary["remaining_run_worst_case_cny"]),
                "slots_remaining": summary["send_slots"],
                "slots_planned": summary["send_slots"],
                "unique_wire_hashes": summary["unique_wire_union"],
            },
        )
    return gate


def _is_official_provider_client(client) -> bool:
    """True only for the official 840 provider client. A test double stays false."""
    return type(client).__module__ == "tool_compression.official_840_provider"


def _official_provider_client():
    """Official provider client for the authorized live command.

    Called only when that command is selected.
    """
    import tool_compression.official_840 as official_runner

    return official_runner.build_live_client()


# Request-by-request sender.
# Spend is recorded after a request completes. Nothing here reserves the next
# request or stops early because a remaining-run worst case would not fit.


def _attempt_ledger_path(out: Path) -> Path:
    return Path(out) / ATTEMPT_LEDGER_NAME


def _sender_status_path(out: Path) -> Path:
    return Path(out) / SENDER_STATUS_NAME


def _ceiling_notice_path(out: Path) -> Path:
    return Path(out) / CEILING_NOTICE_NAME


def _latest_by_attempt(rows: list[dict]) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for row in rows:
        latest[row["attempt_id"]] = row
    return latest


def _attempt_total(rows: list[dict]) -> Decimal:
    return sum((Decimal(row["spend_cny"]) for row in _latest_by_attempt(rows).values()), Decimal("0"))


def _validate_attempt_row(item) -> dict:
    if not isinstance(item, dict):
        raise AmendmentFlightRefused("attempt ledger is corrupt")
    attempt_id = item.get("attempt_id")
    slot_id = item.get("slot_id")
    kind = item.get("kind")
    charge = item.get("charge")
    usable = item.get("usable")
    if not isinstance(attempt_id, str) or attempt_id == "":
        raise AmendmentFlightRefused("attempt ledger is corrupt")
    if not isinstance(slot_id, str) or slot_id == "":
        raise AmendmentFlightRefused("attempt ledger is corrupt")
    if kind not in ("attempt", "settlement"):
        raise AmendmentFlightRefused("attempt ledger is corrupt")
    if charge not in ("confirmed", "unresolved"):
        raise AmendmentFlightRefused("attempt ledger is corrupt")
    if kind == "settlement" and charge != "confirmed":
        raise AmendmentFlightRefused("attempt ledger is corrupt")
    if not isinstance(usable, bool):
        raise AmendmentFlightRefused("attempt ledger is corrupt")
    if kind == "attempt":
        index = item.get("attempt_index")
        if isinstance(index, bool) or not isinstance(index, int) or index < 1:
            raise AmendmentFlightRefused("attempt ledger is corrupt")
    _decimal_field(item.get("spend_cny"), "attempt spend")
    return item


def load_attempts(out: Path) -> list[dict]:
    """Read the attempt ledger. A corrupt line refuses the resume.

    The total is not reset to zero. Invalid JSON is not skipped.
    """
    path = _attempt_ledger_path(out)
    if not path.is_file():
        return []
    rows = []
    seen: set[str] = set()
    latest: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AmendmentFlightRefused("attempt ledger is corrupt") from exc
        row = _validate_attempt_row(item)
        if row["kind"] == "attempt":
            if row["attempt_id"] in seen:
                raise AmendmentFlightRefused("attempt ledger repeats an attempt")
            seen.add(row["attempt_id"])
        elif row["attempt_id"] not in seen:
            raise AmendmentFlightRefused("attempt ledger is corrupt")
        prior = latest.get(row["attempt_id"])
        if prior is not None and prior["charge"] == "confirmed":
            same = row["charge"] == "confirmed" and Decimal(row["spend_cny"]) == Decimal(prior["spend_cny"])
            if not same:
                raise AmendmentFlightRefused("attempt ledger is corrupt")
        latest[row["attempt_id"]] = row
        rows.append(row)
    return rows


def _load_sender_status(out: Path) -> dict | None:
    path = _sender_status_path(out)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AmendmentFlightRefused("sender status is corrupt") from exc
    if not isinstance(payload, dict):
        raise AmendmentFlightRefused("sender status is corrupt")
    return payload


def _recorded_frozen(out: Path) -> bool | None:
    payload = _load_sender_status(out)
    if payload is None:
        return None
    if not isinstance(payload.get("frozen_official"), bool):
        raise AmendmentFlightRefused("sender status is corrupt")
    return payload["frozen_official"]


def _recorded_authorized(out: Path) -> bool | None:
    """Authorization recorded for this output directory.

    A status written before this flag existed counts as not authorized.
    A status whose dispatch fields disagree is corrupt and is not treated as zero.
    """
    payload = _load_sender_status(out)
    if payload is None:
        return None
    allowed = payload.get("provider_call_authorized")
    if not isinstance(allowed, bool):
        raise AmendmentFlightRefused("sender status is corrupt")
    if "authorized_official_live" not in payload:
        if allowed is False:
            return False
        raise AmendmentFlightRefused("sender status is corrupt")
    authorized = payload.get("authorized_official_live")
    if not isinstance(authorized, bool) or authorized is not allowed:
        raise AmendmentFlightRefused("sender status is corrupt")
    expected = "authorized" if authorized else "refused"
    if payload.get("live_dispatch") != expected:
        raise AmendmentFlightRefused("sender status is corrupt")
    return authorized


def _require_explicit_authorization(value) -> bool:
    if value is True or value is False:
        return value
    raise AmendmentFlightRefused("official live authorization must be explicit")


def _attempt_evidence(body: dict, schedule: str) -> Decimal:
    """All-miss local bound of an attempt that has already been sent.

    The bound is stored only after the attempt fails to return a charge.
    It is not consulted before the send, and it is not a peak-window reserve
    of a later request.
    """
    if schedule not in ("off-peak", "peak"):
        raise AmendmentFlightRefused(f"unknown schedule {schedule}")
    if body.get(MAX_TOKENS_FIELD) != MAX_TOKENS:
        raise AmendmentFlightRefused("unresolved evidence requires the wire body")
    return spend_cny(schedule, local_input_tokens(body), 0, MAX_TOKENS)


def _confirmed_charge(payload, schedule: str) -> tuple[dict | None, Decimal | None]:
    usage = payload.get("usage") if isinstance(payload, dict) else None
    try:
        bill = usage_bill(schedule, usage)
    except UsxFlightRefused:
        return None, None
    amount = Decimal(bill["spend_cny"])
    if not amount.is_finite() or amount < 0:
        return None, None
    return bill, amount


def _sender_status(
    plans: list[dict],
    rows: list[dict],
    frozen_official: bool,
    *,
    authorize_official_live: bool = False,
) -> dict:
    authorize_official_live = _require_explicit_authorization(authorize_official_live)
    slots = wire_slots(plans)
    latest = _latest_by_attempt(rows)
    confirmed_rows = [row for row in latest.values() if row["charge"] == "confirmed"]
    unresolved_rows = [row for row in latest.values() if row["charge"] != "confirmed"]
    confirmed = sum((Decimal(row["spend_cny"]) for row in confirmed_rows), Decimal("0"))
    unresolved = sum((Decimal(row["spend_cny"]) for row in unresolved_rows), Decimal("0"))
    total = confirmed + unresolved
    usable = {
        row["slot_id"]
        for row in confirmed_rows
        if row["usable"] is True
    }
    planned = [slot["slot_id"] for slot in slots]
    slots_usable = sum(1 for slot_id in planned if slot_id in usable)
    official_shape = is_official_sample(plans)
    evaluation_done = len(planned) > 0 and slots_usable == len(planned) and not unresolved_rows
    full = bool(frozen_official and official_shape and evaluation_done)
    ceiling = total >= HARD_CAP_CNY
    notice = None
    if ceiling:
        notice = CEILING_NOTICE_TEXT if full else f"{CEILING_NOTICE_TEXT} This run is not the full 840."
    provider_called = any(row.get("provider_called") is True for row in latest.values())
    provider_network = any(row.get("provider_network") is True for row in latest.values())
    return {
        "purpose": SENDER_PURPOSE,
        "catalogue_tip": CATALOGUE_TIP,
        "frozen_official": frozen_official,
        "official_840_plan": bool(frozen_official and official_shape),
        "hard_ceiling_cny": _money(HARD_CAP_CNY),
        "comfortable_expectation_cny": _money(COMFORTABLE_EXPECTATION_CNY),
        "comfortable_expectation_is_a_stop_line": False,
        "peak_rate_next_request_reserve": False,
        "precharge_funding_gate": False,
        "remaining_run_bound_used_as_stop": False,
        "spend_cny": _money(total),
        "confirmed_spend_cny": _money(confirmed),
        "unresolved_spend_cny": _money(unresolved),
        "attempts": sum(1 for row in rows if row["kind"] == "attempt"),
        "unresolved_attempts": len(unresolved_rows),
        "slots_planned": len(planned),
        "slots_usable": slots_usable,
        "cases_in_plan": len({plan["case_id"] for plan in plans}),
        "evaluation_slots_complete": slots_usable == len(planned) and len(planned) > 0,
        "full_840_labeled": full,
        "labeled_case_count": sum(CATEGORY_COUNTS.values()) if full else None,
        "hard_ceiling_reached": ceiling,
        "further_sends_stopped": ceiling,
        "operator_notice": notice,
        "official_settlement": False,
        "official_v1_1": OFFICIAL_V11,
        "human_review": HUMAN_REVIEW,
        "flight_ready": False,
        "paid_flight_ready": False,
        "authorized_official_live": authorize_official_live,
        "provider_call_authorized": authorize_official_live,
        "provider_called": provider_called,
        "provider_network": provider_network,
        "api_key_in_record": False,
        "live_dispatch": "authorized" if authorize_official_live else "refused",
        "max_tokens": MAX_TOKENS,
        "thinking_passes": list(PASSES),
        "model": MODEL,
    }


def _publish_sender(
    out: Path,
    plans: list[dict],
    rows: list[dict],
    frozen_official: bool,
    *,
    authorize_official_live: bool = False,
) -> dict:
    status = _sender_status(
        plans,
        rows,
        frozen_official,
        authorize_official_live=authorize_official_live,
    )
    _atomic_json(_sender_status_path(out), status)
    notice_path = _ceiling_notice_path(out)
    if status["hard_ceiling_reached"]:
        _atomic_json(
            notice_path,
            {
                "purpose": SENDER_PURPOSE,
                "catalogue_tip": CATALOGUE_TIP,
                "operator_notice": status["operator_notice"],
                "hard_ceiling_cny": status["hard_ceiling_cny"],
                "spend_cny": status["spend_cny"],
                "confirmed_spend_cny": status["confirmed_spend_cny"],
                "unresolved_spend_cny": status["unresolved_spend_cny"],
                "full_840_labeled": status["full_840_labeled"],
                "labeled_case_count": status["labeled_case_count"],
                "further_sends_stopped": True,
                "official_settlement": False,
                "official_v1_1": OFFICIAL_V11,
                "human_review": HUMAN_REVIEW,
                "authorized_official_live": status["authorized_official_live"],
                "provider_called": status["provider_called"],
                "provider_network": status["provider_network"],
                "provider_call_authorized": status["provider_call_authorized"],
                "live_dispatch": status["live_dispatch"],
            },
        )
    elif notice_path.is_file():
        notice_path.unlink()
    return status


def _require_sender_client(client, *, authorize_official_live: bool = False) -> None:
    authorize_official_live = _require_explicit_authorization(authorize_official_live)
    if client is None or not callable(getattr(client, "complete", None)):
        raise AmendmentFlightRefused(LIVE_STOP)
    if authorize_official_live is not True:
        _refuse_live_client(client)


def _check_wire_body(slot: dict) -> dict:
    body = slot["body"]
    if body.get(MAX_TOKENS_FIELD) != MAX_TOKENS or body.get("model") != MODEL:
        raise AmendmentFlightRefused("refusing to send a body without the explicit output-token limit")
    if body.get("temperature") != BFCL_DEFAULT_TEMPERATURE or body.get("store") is not False:
        raise AmendmentFlightRefused("refusing a wire body that drops temperature 0.001 or store false")
    if body.get("thinking") != thinking_body(slot["thinking"]):
        raise AmendmentFlightRefused("thinking field does not match the pass")
    plan_fields = {key: value for key, value in body.items() if key != MAX_TOKENS_FIELD}
    _assert_wire_is_plan_plus_limit(plan_fields, body)
    return body


def _attempt_row(
    slot: dict,
    index: int,
    charge: str,
    spend: Decimal,
    usable: bool,
    schedule: str,
    moment,
    reason: str,
    *,
    provider: bool = False,
) -> dict:
    if provider is not True and provider is not False:
        raise AmendmentFlightRefused("provider marker must be explicit")
    return {
        "kind": "attempt",
        "attempt_id": f"{slot['slot_id']}#{index}",
        "attempt_index": index,
        "slot_id": slot["slot_id"],
        "case_id": slot["case_id"],
        "thinking": slot["thinking"],
        "request_sha256": slot["request_sha256"],
        "charge": charge,
        "spend_cny": _money(spend),
        "usable": usable,
        "schedule": schedule,
        "clock": moment.isoformat(),
        "reason": reason,
        "provider_called": provider,
        "provider_network": provider,
    }


def note_confirmed_charge(
    plans: list[dict],
    out: Path,
    attempt_id: str,
    spend: Decimal,
    *,
    frozen_official: bool = False,
) -> dict:
    """Replace one unresolved attempt's evidence with a confirmed charge.

    The ledger keeps the earlier row. The running total uses the confirmed
    charge for that attempt. Other attempts are left as they are. This does
    not send a request.
    """
    if isinstance(spend, bool) or not isinstance(spend, Decimal):
        raise AmendmentFlightRefused("confirmed charge must be a Decimal")
    if not spend.is_finite() or spend < 0:
        raise AmendmentFlightRefused("confirmed charge must be a non-negative Decimal")
    if not isinstance(attempt_id, str) or attempt_id == "":
        raise AmendmentFlightRefused("unknown attempt")
    if not plans:
        raise AmendmentFlightRefused("no plans")
    out = Path(out)
    recorded = _recorded_frozen(out)
    if recorded is not None and recorded is not frozen_official:
        raise AmendmentFlightRefused("sender record does not match this plan")
    recorded_auth = _recorded_authorized(out)
    authorize_official_live = False if recorded_auth is None else recorded_auth
    rows = load_attempts(out)
    prior = _latest_by_attempt(rows).get(attempt_id)
    if prior is None:
        raise AmendmentFlightRefused("unknown attempt")
    if prior["charge"] == "confirmed":
        if Decimal(prior["spend_cny"]) != spend:
            raise AmendmentFlightRefused("confirmed charge already recorded")
        return _publish_sender(
            out,
            plans,
            rows,
            frozen_official,
            authorize_official_live=authorize_official_live,
        )
    kept_provider = prior.get("provider_called") is True
    row = {
        "kind": "settlement",
        "attempt_id": attempt_id,
        "attempt_index": prior.get("attempt_index"),
        "slot_id": prior["slot_id"],
        "case_id": prior.get("case_id"),
        "thinking": prior.get("thinking"),
        "request_sha256": prior.get("request_sha256"),
        "charge": "confirmed",
        "spend_cny": _money(spend),
        "usable": prior["usable"],
        "schedule": prior.get("schedule"),
        "clock": prior.get("clock"),
        "reason": "confirmed charge noted",
        "provider_called": kept_provider,
        "provider_network": prior.get("provider_network") is True,
    }
    rows.append(row)
    _append_ledger(_attempt_ledger_path(out), row)
    return _publish_sender(
        out,
        plans,
        rows,
        frozen_official,
        authorize_official_live=authorize_official_live,
    )


def send_evaluation(
    plans: list[dict],
    out: Path,
    client,
    clock,
    *,
    frozen_official: bool = False,
    authorize_official_live: bool = False,
) -> dict:
    """Send plan slots one request at a time and record each charge after it completes.

    The hard ceiling is ¥80.00 of recorded spend across both thinking passes.
    About ¥10 is reported as a comfortable expectation and does not stop the
    run. A partial run is not labeled as the full 840. A provider client is
    refused unless ``authorize_official_live`` is true.
    """
    authorize_official_live = _require_explicit_authorization(authorize_official_live)
    _require_sender_client(client, authorize_official_live=authorize_official_live)
    if not plans:
        raise AmendmentFlightRefused("no plans")
    _assert_passes_distinct(plans)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    recorded = _recorded_frozen(out)
    if recorded is not None and recorded is not frozen_official:
        raise AmendmentFlightRefused("sender record does not match this plan")
    recorded_auth = _recorded_authorized(out)
    if recorded_auth is not None and recorded_auth is not authorize_official_live:
        raise AmendmentFlightRefused("sender record does not match this authorization")
    slots = wire_slots(plans)
    rows = load_attempts(out)
    plan_ids = {slot["slot_id"] for slot in slots}
    for row in rows:
        if row["slot_id"] not in plan_ids:
            raise AmendmentFlightRefused("attempt ledger does not match these plans")
    done = {
        row["slot_id"]
        for row in _latest_by_attempt(rows).values()
        if row["charge"] == "confirmed" and row["usable"] is True
    }
    counts: dict[str, int] = {}
    for row in rows:
        if row["kind"] == "attempt":
            counts[row["slot_id"]] = counts.get(row["slot_id"], 0) + 1
    total = _attempt_total(rows)
    provider_attempt = _is_official_provider_client(client)
    status = None
    try:
        for slot in slots:
            if total >= HARD_CAP_CNY:
                break
            if slot["slot_id"] in done:
                continue
            moment = clock()
            schedule = schedule_at(moment)
            body = _check_wire_body(slot)
            index = counts.get(slot["slot_id"], 0) + 1
            try:
                payload = client.complete(deepcopy(body))
            except AmendmentFlightRefused:
                raise
            except Exception as exc:
                spend = _attempt_evidence(body, schedule)
                reason = "timeout" if _is_timeout(exc) else "unresolved"
                row = _attempt_row(
                    slot, index, "unresolved", spend, False, schedule, moment, reason, provider=provider_attempt
                )
                usable = False
            else:
                bill, spend = _confirmed_charge(payload, schedule)
                if spend is None:
                    spend = _attempt_evidence(body, schedule)
                    row = _attempt_row(
                        slot, index, "unresolved", spend, False, schedule, moment, "unresolved", provider=provider_attempt
                    )
                    usable = False
                else:
                    usable = _acceptable(slot, payload, bill)
                    row = _attempt_row(
                        slot, index, "confirmed", spend, usable, schedule, moment, "confirmed", provider=provider_attempt
                    )
            rows.append(row)
            _append_ledger(_attempt_ledger_path(out), row)
            counts[slot["slot_id"]] = index
            total = _attempt_total(rows)
            if usable:
                done.add(slot["slot_id"])
            status = _publish_sender(
                out, plans, rows, frozen_official, authorize_official_live=authorize_official_live
            )
    finally:
        status = _publish_sender(
            out, plans, rows, frozen_official, authorize_official_live=authorize_official_live
        )
    return status


def send_frozen_plan(
    bfcl_root: Path,
    out: Path,
    client,
    clock,
    repo: Path | None = None,
    *,
    authorize_official_live: bool = False,
) -> dict:
    """Send the frozen 840-case U/S2/X2/SX2 plan from catalogue tip 96795322.

    The caller supplies the client. Unless ``authorize_official_live`` is
    true, a provider client is refused before the plan is built. This
    function does not read a key.
    """
    authorize_official_live = _require_explicit_authorization(authorize_official_live)
    _require_sender_client(client, authorize_official_live=authorize_official_live)
    flight = build_flight(bfcl_root, repo)
    if flight.get("catalogue_tip") != CATALOGUE_TIP:
        raise AmendmentFlightRefused("catalogue tip is not the frozen 96795322 catalogues")
    return send_evaluation(
        flight["plans"],
        out,
        client,
        clock,
        frozen_official=True,
        authorize_official_live=authorize_official_live,
    )


def main(argv: list[str] | None = None) -> int:
    """Offline gate, unless official live dispatch is explicitly authorized.

    ``--live`` alone is refused and does not read a key or open a socket.
    ``--live --authorize-official-live`` builds the frozen plan and sends it.
    """
    parser = argparse.ArgumentParser(prog="tool_compression.amendment_s2x2_flight")
    parser.add_argument("--bfcl-root", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Refused unless --authorize-official-live is also set.",
    )
    parser.add_argument(
        "--authorize-official-live",
        action="store_true",
        help="With --live, build the frozen 840-case plan and send it with the provider client.",
    )
    args = parser.parse_args(argv)
    if args.authorize_official_live and not args.live:
        print("authorized official live dispatch requires --live")
        return 2
    if args.live and not args.authorize_official_live:
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

    if args.live:
        try:
            client = _official_provider_client()
            status = send_frozen_plan(
                args.bfcl_root,
                args.out,
                client,
                clock,
                authorize_official_live=True,
            )
        except UsxFlightRefused as exc:
            print(str(exc))
            return 1
        print(
            json.dumps(
                {
                    "authorized_official_live": status["authorized_official_live"],
                    "provider_call_authorized": status["provider_call_authorized"],
                    "provider_called": status["provider_called"],
                    "provider_network": status["provider_network"],
                    "live_dispatch": status["live_dispatch"],
                    "full_840_labeled": status["full_840_labeled"],
                    "labeled_case_count": status["labeled_case_count"],
                    "spend_cny": status["spend_cny"],
                    "hard_ceiling_reached": status["hard_ceiling_reached"],
                    "further_sends_stopped": status["further_sends_stopped"],
                    "slots_usable": status["slots_usable"],
                    "slots_planned": status["slots_planned"],
                    "official_settlement": status["official_settlement"],
                    "official_v1_1": status["official_v1_1"],
                    "human_review": status["human_review"],
                    "catalogue_tip": status["catalogue_tip"],
                    "operator_notice": status["operator_notice"],
                },
                sort_keys=True,
            )
        )
        if status["full_840_labeled"]:
            return 0
        return 1

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
