"""The full in-scope thinking-off fly: its case list, cost, time, and start gates.

3,127 in-scope scoring questions in 14 categories, and the 111 memory
prerequisites their scenarios load, on U, S, X and SX with thinking off:
12,952 slots. Nothing here contacts a provider or reads a key.

Cost uses the preliminary's observed-mean method on the full catalogue's user
turns: for each family, the archived flight with the higher all-miss cost per
arm-turn, its prompt, output and steps together. The higher-step path takes,
for each family, the flight with more steps per arm-turn instead. The planning
upper is the preliminary's allowance on the full catalogue. It tokenises every
first request locally, which takes about two minutes, so ``write_full_files``
stores it and the CLI reads the stored value.

Time is serial, one request at a time. A hang costs the 20 s first deadline on
top of the retry that then succeeds, so a profile's seconds per send are its
pace plus hang rate times 20 s. Each case's sends are spread evenly over its
stretch of the clock from Friday 27 Nov 2026 18:00 HKT. A send inside a
rate-card peak window costs double. Memory runs last.

The ceiling is Jacky's. The CLI refuses one under ``ceiling_floor_usd``: the
costliest observed-mean or higher-step profile with its peak premium and its
hung first tries priced as billed. A ceiling at the floor is expected to finish
those paths. It does not cover the allowance tail.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from hashlib import sha256
from pathlib import Path
import json

from tool_compression.clean_start.categories import is_memory, is_multi_turn
from tool_compression.clean_start.pilot import study_dir
from tool_compression.clean_start.pin import ARMS, OFFICIAL_SETTLEMENT, STUDY_ID
from tool_compression.clean_start.preliminary import (
    CNY_PER_USD,
    FLIGHTS,
    FORCE_QUIT_STEPS,
    HKT,
    LONG_CONTEXT_SPIKE_TOKENS,
    MISS,
    OUTPUT_PRICE,
    OUTPUT_TOKENS,
    PROMPT_ALLOWANCE,
    STEP_ALLOWANCE,
    _allowance_family,
    _arm_tokens,
    _family,
    _flight_totals,
    _per_turn_usd,
    _request_usd,
    observed_mean,
    price_cases,
)
from tool_compression.clean_start.rate_card import is_peak, rate_card
from tool_compression.clean_start.runner import FULL_FLY_POLICY, build_slots, plan_summary
from tool_compression.clean_start.scope import select_full_run_cases, study_categories

NOT_BEFORE_HKT = datetime(2026, 11, 27, 18, 0, tzinfo=HKT)
SCORING = 3127
PREREQUISITES = 111
CATEGORIES = 14
SLOTS = 12952
THINKING = ("off",)
COMMITTED_SLOT_SHA256 = "8fff8cd902b3c523473cf38591a20d3719b0c028138728f46632867fc655047f"
PLAN_FILE = Path("full") / "plan.json"
COST_FILE = Path("full") / "cost.json"
HANG_SECONDS = Decimal(str(FULL_FLY_POLICY.attempt_deadlines[0]))
TEN_HOURS = Decimal(36000)
TEN_HOUR_PACES = (Decimal("1.9"), Decimal("2.0"))
SUPERSEDED = (
    "the 119-case / $12 preliminary command",
    "tip 90f675da",
    "tip 00452963",
    "any full 12,952-slot command without --full (no 20 s / 60 s deadlines, no skip-and-record, no resume)",
)

# (name, path, memory seconds, other seconds, hang rate)
PROFILES = {
    "median": (
        ("mean_1.9s_hang_1.5pct", "observed", "1.9", "1.9", "0.015"),
        ("mean_2.0s_hang_1.5pct", "observed", "2.0", "2.0", "0.015"),
        ("mean_memory_3.3s_rest_2.0s_hang_1.5pct", "observed", "3.3", "2.0", "0.015"),
    ),
    "comfortable": (
        ("higher_step_memory_3.3s_rest_2.0s_hang_3pct", "higher_step", "3.3", "2.0", "0.03"),
        ("mean_3.3s_hang_3pct", "observed", "3.3", "3.3", "0.03"),
        ("allowance_1.9s_no_hang", "allowance", "1.9", "1.9", "0"),
        ("allowance_1.9s_hang_1.5pct", "allowance", "1.9", "1.9", "0.015"),
        ("allowance_3.3s_hang_3pct", "allowance", "3.3", "3.3", "0.03"),
    ),
}


def full_dir() -> Path:
    return study_dir() / "full"


def _dumps(payload: dict) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def _usd(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.000001")))


def _cny(usd: Decimal) -> str:
    return str((usd * CNY_PER_USD).quantize(Decimal("0.01")))


def _hours(seconds: Decimal) -> str:
    return str((seconds / Decimal(3600)).quantize(Decimal("0.01")))


def _at(start: datetime, seconds: Decimal) -> datetime:
    return start + timedelta(microseconds=int((seconds * Decimal(1_000_000)).to_integral_value(ROUND_HALF_UP)))


def select_full_cases() -> list[dict]:
    """Every in-scope scoring question, each memory category's prerequisites first.

    Every prerequisite scenario is one an in-scope question uses, so the full
    catalogue's prerequisites and the matched prerequisites are the same list.
    """
    cases = select_full_run_cases()
    scoring = [case for case in cases if not case.get("prereq")]
    prereqs = [case for case in cases if case.get("prereq")]
    if len(scoring) != SCORING or len(prereqs) != PREREQUISITES:
        raise RuntimeError(f"full catalogue is {len(scoring)} scoring and {len(prereqs)} prerequisites")
    if len({case["category"] for case in scoring}) != CATEGORIES or len(study_categories()) != CATEGORIES:
        raise RuntimeError("full catalogue is not 14 categories")
    for category in sorted({case["category"] for case in prereqs}):
        used = {case["scenario"] for case in scoring if case["category"] == category}
        loaded = {case["scenario"] for case in prereqs if case["category"] == category}
        if used != loaded:
            raise RuntimeError(f"{category} prerequisites are not matched to its questions")
    return cases


def full_slots(cases: list[dict]) -> list[dict]:
    slots = build_slots(cases, THINKING)
    if len(slots) != SLOTS:
        raise RuntimeError(f"full fly is {len(slots)} slots, not {SLOTS}")
    return slots


def build_plan() -> dict:
    cases = select_full_cases()
    slots = full_slots(cases)
    summary = plan_summary(slots, THINKING)
    categories = []
    for category in study_categories():
        rows = [case for case in cases if case["category"] == category]
        entry = {
            "category": category,
            "scoring": sum(1 for case in rows if not case.get("prereq")),
            "prerequisites": sum(1 for case in rows if case.get("prereq")),
            "user_turns": sum(len(case["question"]) for case in rows),
            "case_ids": [case["id"] for case in rows],
        }
        if is_memory(category):
            scenarios = {}
            for case in rows:
                row = scenarios.setdefault(case["scenario"], {"prerequisites": 0, "scoring": 0})
                row["prerequisites" if case.get("prereq") else "scoring"] += 1
            entry["scenarios"] = scenarios
        categories.append(entry)
    return {
        "study": STUDY_ID,
        "official_settlement": OFFICIAL_SETTLEMENT,
        "kind": "full",
        "thinking": "off",
        "arms": list(ARMS),
        "replicate_u": False,
        "scoring": SCORING,
        "prerequisites": PREREQUISITES,
        "conversations": len(cases),
        "slots": len(slots),
        "slot_sha256": summary["slot_sha256"],
        "memory_prereqs": "matched",
        "order": (
            "study category order; within a memory category its prerequisites, then its questions; "
            "within a case the four arms in the runner's rotation"
        ),
        "memory_chains": (
            "One chain is one arm on one memory backend and one scenario. Every non-first entry "
            "loads <scenario>_final.json, which only a prerequisite writes. A prerequisite skipped "
            "after its retry breaks its chain: every later slot of that chain is recorded as "
            "dependency_skipped without a request."
        ),
        "out_of_scope": [
            "the official simple sets",
            "web-search sets",
            "SerpAPI",
            "thinking on",
        ],
        "categories": categories,
    }


def plan_sha256(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def higher_step(cases: list[dict]) -> dict:
    """For each family, the archived flight with more steps per arm-turn, its cost per arm-turn with it."""
    totals = _flight_totals()
    draw_turns: dict[str, int] = {}
    for case in cases:
        family = _family(case["category"])
        draw_turns[family] = draw_turns.get(family, 0) + len(case["question"])
    rates = {}
    families = {}
    usd = sends = memory_sends = other_sends = Decimal(0)
    for family, turns in sorted(draw_turns.items()):
        chosen = None
        for name, _relative in FLIGHTS:
            bucket = totals[name][family]
            steps = Decimal(bucket["requests"]) / Decimal(len(bucket["turns"]))
            cost = _per_turn_usd(bucket)
            if chosen is None or steps > chosen[1] or (steps == chosen[1] and cost > chosen[2]):
                chosen = (name, steps, cost, bucket)
        name, steps, cost, bucket = chosen
        arm_turns = Decimal(turns) * Decimal(len(ARMS))
        rates[family] = {"sends": steps, "usd": cost}
        family_sends = arm_turns * steps
        usd += arm_turns * cost
        sends += family_sends
        if family == "memory":
            memory_sends += family_sends
        else:
            other_sends += family_sends
        families[family] = {
            "flight": name,
            "requests": bucket["requests"],
            "turns": len(bucket["turns"]),
            "mean_steps": str(steps.quantize(Decimal("0.000001"))),
            "sends": _usd(family_sends),
            "usd": _usd(arm_turns * cost),
        }
    return {
        "rule": (
            "For each family, the archived flight with the higher mean steps per arm-turn, "
            "with that flight's own prompt and output. Four arms on the full catalogue's user turns."
        ),
        "families": families,
        "rates": rates,
        "usd": usd,
        "sends": sends,
        "memory_sends": memory_sends,
        "other_sends": other_sends,
    }


def allowance_by_case(cases: list[dict], single_usd: dict | None = None) -> list[tuple[Decimal, Decimal]]:
    """(requests, usd) per case at the planning allowance. They sum to ``price_cases``.

    The memory force-quit contingency sits on each backend's first scoring
    question. ``single_usd`` is a stored price per single-turn case; without
    it the single-turn first requests are tokenised.
    """
    rows = []
    contingent: set[str] = set()
    for case in cases:
        category = case["category"]
        turns = len(case["question"])
        if is_multi_turn(category) or is_memory(category):
            family = _allowance_family(category)
            requests = Decimal(turns * STEP_ALLOWANCE[family] * len(ARMS))
            usd = _request_usd(PROMPT_ALLOWANCE[family], OUTPUT_TOKENS, int(requests))
            if category == "multi_turn_long_context" and not case.get("prereq"):
                usd += _request_usd(LONG_CONTEXT_SPIKE_TOKENS - PROMPT_ALLOWANCE[family], 0, len(ARMS))
            if is_memory(category) and not case.get("prereq") and category not in contingent:
                contingent.add(category)
                extra = (FORCE_QUIT_STEPS - STEP_ALLOWANCE["memory"]) * len(ARMS)
                requests += Decimal(extra)
                usd += _request_usd(PROMPT_ALLOWANCE["memory"], OUTPUT_TOKENS, extra)
        else:
            requests = Decimal(len(ARMS))
            if single_usd is not None:
                usd = Decimal(single_usd[case["id"]])
            else:
                usd = _request_usd(sum(_arm_tokens(case)), 0) + _request_usd(0, OUTPUT_TOKENS, len(ARMS))
        rows.append((requests, usd))
    return rows


def peak_windows(start: datetime = NOT_BEFORE_HKT, days: int = 10) -> list[tuple[Decimal, Decimal]]:
    """Rate-card peak windows as seconds after ``start``. HKT has no DST."""
    windows = []
    for offset in range(days):
        day = start.date() + timedelta(days=offset)
        for begin, end in ((9, 12), (14, 18)):
            low = datetime(day.year, day.month, day.day, begin, tzinfo=HKT)
            high = datetime(day.year, day.month, day.day, end, tzinfo=HKT)
            if not is_peak(low) or high <= start:
                continue
            windows.append((
                Decimal(int((max(low, start) - start).total_seconds())),
                Decimal(int((high - start).total_seconds())),
            ))
    return windows


def run_profile(
    cases: list[dict],
    per_case: list[tuple[Decimal, Decimal]],
    memory_pace: Decimal,
    other_pace: Decimal,
    hang_rate: Decimal,
    start: datetime = NOT_BEFORE_HKT,
) -> dict:
    """One serial pace in run order from ``start``, with the peak premium and the hung first tries."""
    windows = peak_windows(start)
    elapsed = premium = peak_sends = usd = sends = hung = hung_usd = Decimal(0)
    for case, (case_sends, case_usd) in zip(cases, per_case, strict=True):
        pace = memory_pace if is_memory(case["category"]) else other_pace
        seconds = case_sends * (pace + hang_rate * HANG_SECONDS)
        low, high = elapsed, elapsed + seconds
        overlap = sum((max(Decimal(0), min(high, end) - max(low, begin)) for begin, end in windows), Decimal(0))
        if seconds > 0 and overlap > 0:
            premium += case_usd * overlap / seconds
            peak_sends += case_sends * overlap / seconds
        usd += case_usd
        sends += case_sends
        hung += case_sends * hang_rate
        hung_usd += case_usd * hang_rate
        elapsed = high
    finish = _at(start, elapsed)
    return {
        "sends": _usd(sends),
        "hours": _hours(elapsed),
        "finish_hkt": finish.isoformat(),
        "crosses_peak": premium > 0,
        "peak_sends": _usd(peak_sends),
        "usd_off_peak": _usd(usd),
        "peak_premium_usd": _usd(premium),
        "usd_with_peak": _usd(usd + premium),
        "hung_first_tries": _usd(hung),
        "hung_first_tries_usd_if_billed": _usd(hung_usd),
        "usd_with_peak_and_hung_tries": _usd(usd + premium + hung_usd),
        "cny_with_peak_and_hung_tries": _cny(usd + premium + hung_usd),
        "concurrency_for_ten_hours": str((elapsed / TEN_HOURS).quantize(Decimal("0.01"))),
        "_total": usd + premium + hung_usd,
        "_seconds": elapsed,
    }


def _family_rows(cases: list[dict], path: dict) -> list[tuple[Decimal, Decimal]]:
    rows = []
    for case in cases:
        rate = path["rates"][_family(case["category"])]
        arm_turns = Decimal(len(case["question"])) * Decimal(len(ARMS))
        rows.append((arm_turns * rate["sends"], arm_turns * rate["usd"]))
    return rows


def compute_planning(cases: list[dict]) -> dict:
    """The slow part: local tokens of every first request. About two minutes."""
    priced = price_cases(cases)
    rows = allowance_by_case(cases)
    upper = sum((usd for _requests, usd in rows), Decimal(0))
    requests = sum((requests for requests, _usd in rows), Decimal(0))
    if _usd(upper) != _usd(priced["upper"]) or requests != Decimal(priced["allowance_requests"]):
        raise RuntimeError("per-case allowance does not add up to the planning upper")
    return {
        "planning_upper_usd": _usd(priced["upper"]),
        "planning_upper_parts_usd": {
            "single_turn": _usd(priced["single"]),
            "trajectories": _usd(priced["trajectory"]),
            "long_context_spike": _usd(priced["spike"]),
            "memory_force_quit_contingency": _usd(priced["contingency"]),
        },
        "allowance_requests": priced["allowance_requests"],
        "structural_cap_usd": _usd(priced["structural"]),
        "first_request_floor_tokens": priced["floor_tokens"],
        "first_request_floor_usd": _usd(priced["floor_usd"]),
        "single_turn_allowance_usd": {
            case["id"]: str(usd) for case, (_requests, usd) in zip(cases, rows) if not (
                is_multi_turn(case["category"]) or is_memory(case["category"])
            )
        },
    }


def full_report(planning: dict) -> dict:
    cases = select_full_cases()
    slots = full_slots(cases)
    observed = observed_mean(cases)
    stepped = higher_step(cases)
    paths = {
        "observed": _family_rows(cases, observed),
        "higher_step": _family_rows(cases, stepped),
        "allowance": allowance_by_case(cases, planning["single_turn_allowance_usd"]),
    }
    allowance_total = sum((usd for _requests, usd in paths["allowance"]), Decimal(0))
    if _usd(allowance_total) != planning["planning_upper_usd"]:
        raise RuntimeError("stored single-turn allowance does not add up to the planning upper")
    profiles: dict[str, dict] = {}
    for band, rows in PROFILES.items():
        for name, path, memory_pace, other_pace, hang in rows:
            profile = run_profile(cases, paths[path], Decimal(memory_pace), Decimal(other_pace), Decimal(hang))
            profile.update({"band": band, "path": path, "memory_seconds": memory_pace,
                            "other_seconds": other_pace, "hang_rate": hang})
            profiles[name] = profile
    floor_name = max(
        (name for name, row in profiles.items() if row["path"] != "allowance"),
        key=lambda name: profiles[name]["_total"],
    )
    floor = profiles[floor_name]["_total"].quantize(Decimal("0.01"), rounding=ROUND_CEILING)
    monday = profiles["allowance_1.9s_no_hang"]
    slowest = profiles["allowance_3.3s_hang_3pct"]
    ten_hours = {}
    for pace in TEN_HOUR_PACES:
        capacity = TEN_HOURS / pace
        ten_hours[f"sends_in_ten_hours_at_{pace}s"] = str(capacity.quantize(Decimal("1")))
        ten_hours[f"share_of_mean_path_at_{pace}s"] = str((capacity / observed["sends"]).quantize(Decimal("0.001")))
        ten_hours[f"concurrency_mean_path_at_{pace}s_no_hangs"] = str(
            (observed["sends"] * pace / TEN_HOURS).quantize(Decimal("0.01"))
        )
    for name in ("mean_1.9s_hang_1.5pct", "mean_2.0s_hang_1.5pct", "mean_3.3s_hang_3pct"):
        ten_hours[f"concurrency_{name}"] = profiles[name]["concurrency_for_ten_hours"]
    ten_hours["single_request_floor_hours_at_2.0s"] = _hours(Decimal(SLOTS) * Decimal("2.0"))
    for row in profiles.values():
        row.pop("_total")
        row.pop("_seconds")
    scoring = sum(1 for case in cases if not case.get("prereq"))
    return {
        "study": STUDY_ID,
        "official_settlement": OFFICIAL_SETTLEMENT,
        "kind": "full",
        "thinking": "off",
        "arms": list(ARMS),
        "scoring": scoring,
        "prerequisites": len(cases) - scoring,
        "slots": len(slots),
        "slot_sha256": plan_summary(slots, THINKING)["slot_sha256"],
        "rate_card": rate_card()["id"],
        "prices_per_million_off_peak": {"cache_miss": str(MISS), "output": str(OUTPUT_PRICE), "cache_hit": "0.003"},
        "peak": "double, weekdays 09:00-12:00 and 14:00-18:00 HKT",
        "cny_per_usd": str(CNY_PER_USD),
        "not_before_hkt": NOT_BEFORE_HKT.isoformat(),
        "send_policy": FULL_FLY_POLICY.describe(),
        "observed_mean": observed["rule"],
        "observed_mean_usd": _usd(observed["usd"]),
        "observed_mean_cny": _cny(observed["usd"]),
        "observed_mean_sends": _usd(observed["sends"]),
        "observed_mean_memory_sends": _usd(observed["memory_sends"]),
        "observed_by_family": observed["families"],
        "higher_step": stepped["rule"],
        "higher_step_usd": _usd(stepped["usd"]),
        "higher_step_sends": _usd(stepped["sends"]),
        "higher_step_memory_sends": _usd(stepped["memory_sends"]),
        "higher_step_by_family": stepped["families"],
        **{key: value for key, value in planning.items() if key != "single_turn_allowance_usd"},
        "planning_upper_cny": _cny(Decimal(planning["planning_upper_usd"])),
        "time_rule": (
            "Serial. Seconds per send are the profile pace plus hang rate times the 20 s first "
            "deadline; the retry that follows a hang is already a send. No backoff after a "
            "deadline (FULL_FLY_POLICY), 2 s after an HTTP status. A send inside a peak window "
            "costs double. Hung first tries are priced at their case's mean cost per send, as "
            "if billed."
        ),
        "profiles": profiles,
        "ceiling_floor_usd": str(floor),
        "ceiling_floor_cny": _cny(floor),
        "ceiling_floor_profile": floor_name,
        "ceiling_floor": (
            "The CLI refuses --full with a ceiling under this. It is the costliest observed-mean "
            "or higher-step profile with its peak premium and its hung first tries priced as "
            "billed, rounded up to the cent. It is not a recommendation; Jacky names the ceiling."
        ),
        "allowance_with_monday_peak_usd": monday["usd_with_peak"],
        "allowance_with_monday_peak_cny": _cny(Decimal(monday["usd_with_peak"])),
        "allowance_with_monday_peak": (
            "The planning upper at 1.9 s, no hangs, from Friday 18:00 HKT: it finishes Monday "
            "evening and its Monday 09:00-12:00 and 14:00-18:00 sends cost double."
        ),
        "allowance_slowest_usd_with_peak_and_hung_tries": slowest["usd_with_peak_and_hung_tries"],
        "allowance_slowest_cny_with_peak_and_hung_tries": _cny(Decimal(slowest["usd_with_peak_and_hung_tries"])),
        "ten_hours": ten_hours,
        "ten_hours_verdict": (
            "Not feasible on the serial runner. The mean path alone is about 37 hours of "
            "successful requests at 1.9 s; ten hours would need about four requests in flight "
            "all the time. The 20 s / 60 s policy cuts hang waste, not work."
        ),
        "superseded_not_to_fly": list(SUPERSEDED),
    }


def write_full_files(planning: dict | None = None) -> dict:
    """Write full/plan.json and full/cost.json. ``planning`` reuses a stored upper."""
    root = full_dir()
    root.mkdir(parents=True, exist_ok=True)
    plan_text = _dumps(build_plan())
    (root / "plan.json").write_text(plan_text, encoding="utf-8")
    if planning is None:
        planning = compute_planning(select_full_cases())
    report = full_report(planning)
    report["plan_sha256"] = plan_sha256(plan_text)
    report["single_turn_allowance_usd"] = planning["single_turn_allowance_usd"]
    (root / "cost.json").write_text(_dumps(report), encoding="utf-8")
    return {
        "slots": report["slots"],
        "observed_mean_usd": report["observed_mean_usd"],
        "planning_upper_usd": report["planning_upper_usd"],
        "ceiling_floor_usd": report["ceiling_floor_usd"],
    }


def stored_planning(cost: dict) -> dict:
    keys = (
        "planning_upper_usd", "planning_upper_parts_usd", "allowance_requests", "structural_cap_usd",
        "first_request_floor_tokens", "first_request_floor_usd", "single_turn_allowance_usd",
    )
    return {key: cost[key] for key in keys}


def load_committed_plan() -> tuple[dict, str]:
    text = (study_dir() / PLAN_FILE).read_text(encoding="utf-8")
    plan = json.loads(text)
    if plan != build_plan():
        raise RuntimeError("full/plan.json does not match the full-fly builder")
    if plan["slot_sha256"] != COMMITTED_SLOT_SHA256:
        raise RuntimeError("full/plan.json slot order is not the committed one")
    return plan, plan_sha256(text)


def load_committed_cost() -> dict:
    cost = json.loads((study_dir() / COST_FILE).read_text(encoding="utf-8"))
    _plan, digest = load_committed_plan()
    if cost.get("plan_sha256") != digest:
        raise RuntimeError("full/cost.json does not match full/plan.json")
    if cost.get("official_settlement") is not False:
        raise RuntimeError("full official_settlement must stay false")
    if cost.get("slot_sha256") != COMMITTED_SLOT_SHA256:
        raise RuntimeError("full/cost.json slot order is not the committed one")
    if cost.get("send_policy") != FULL_FLY_POLICY.describe():
        raise RuntimeError("full/cost.json was priced for another send policy")
    if Decimal(cost["ceiling_floor_usd"]) <= Decimal(cost["observed_mean_usd"]):
        raise RuntimeError("full ceiling floor is under the observed mean")
    return cost


def start_gate(now: datetime, *, resume: bool) -> list[str]:
    """Clock gates the CLI can see. The box preflight and Jacky's go are the rest."""
    problems = []
    if now.tzinfo is None:
        raise ValueError("start gate needs a timezone-aware clock")
    if now < NOT_BEFORE_HKT:
        problems.append(f"not before {NOT_BEFORE_HKT.isoformat()}; it is {now.astimezone(HKT).isoformat()}")
    if not resume and is_peak(now):
        problems.append("a fresh full fly starts off-peak only; this is a rate-card peak window")
    return problems
