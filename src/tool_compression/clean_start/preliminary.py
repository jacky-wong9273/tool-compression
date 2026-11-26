"""Preliminary draw for the thinking-off flight inside the 80 CNY ceiling.

The draw is local. Nothing here contacts a provider or reads a key. Question
text, gold, and scores are not inputs to which ids are chosen. Archived bills
are read only when the cost report checks the prompt and step allowances.
Editors are called only to count the tool text a single-turn slot would send.

The 2026-11-25 pilot draw and the validation draw stay where they are. This
module writes nothing into ``pilot/`` or ``validation/``.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_EVEN, ROUND_HALF_UP
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import random

from tool_compression.clean_start.categories import is_memory, is_multi_turn
from tool_compression.clean_start.load import load_prereqs
from tool_compression.clean_start.pilot import build_draw, study_dir
from tool_compression.clean_start.pin import ARMS, OFFICIAL_SETTLEMENT, STEP_LIMIT, STUDY_ID
from tool_compression.clean_start.rate_card import OFF_PEAK_PER_MILLION
from tool_compression.clean_start.scope import in_scope_questions, study_categories
from tool_compression.config import LOCAL_TOKENIZER
from tool_compression.count import TiktokenCounter, dump_request

# 20261126 is the committed validation seed, so this draw does not reuse it.
SEED = "20261127"
SEED_REASON = "20261126 is the committed validation seed, so the preliminary draw uses 20261127."
FRACTION = Decimal("0.0374")
FRACTION_QUANTUM = Decimal("0.0001")
DRAW_ALGORITHM = (
    "n = min(population, max(floor, half_up(f * population))) with half-up "
    "rounding. f is 0.0374, the largest multiple of 0.0001 whose off-peak "
    "planning upper is at or under $11.50. live_parallel takes every in-scope "
    "id. live_relevance, live_parallel_multiple, and each memory backend have "
    "floor 2; every other category has floor 1. Memory candidates are the "
    "notetaker scenario only. The pool drops ids in the exposed pilot draw "
    "when at least n ids remain. random.Random('clean-start-usx-preliminary:"
    "20261127:<category>').sample(sorted(pool), n) when n is smaller than that "
    "pool; otherwise the sorted pool is kept and sample is not called. "
    "Python 3.12 random. Matched prerequisites are every prerequisite "
    "conversation of each drawn memory scenario."
)
# Binds only when it is above the rounded fraction. live_parallel is the whole population.
MINIMUM = {
    "live_relevance": 2,
    "live_parallel_multiple": 2,
    "memory_kv": 2,
    "memory_vector": 2,
    "memory_rec_sum": 2,
}
MEMORY_SCENARIO = "notetaker"
MEMORY_SCENARIO_REASON = (
    "notetaker has the fewest prerequisite user-turns of the five scenarios "
    "(24, against 35, 47, 108, and 109). Matched prerequisites are every "
    "conversation of a drawn scenario, on each backend, so a second scenario "
    "does not fit under the ceiling. Chosen from the catalogue's turn counts, "
    "not from flight scores."
)

# Planning allowances. The greater of ceil(1.5 times the mean prompt) and the
# 95th percentile, then the greater of the two archived flights. The percentile
# index is round-half-even of p*(n-1). Steps are at least 6, or the higher
# flight's 90th percentile. Output is 900 tokens. One long-context request per
# case per arm is raised to the largest prompt in those bills. One memory turn
# per included backend per arm is priced at 21 steps instead of the step
# allowance. preliminary_report checks these integers against the bills.
PROMPT_ALLOWANCE = {
    "multi_turn_base": 6361,
    "multi_turn_miss_func": 6975,
    "multi_turn_miss_param": 7961,
    "multi_turn_long_context": 8740,
    "memory": 12269,
}
STEP_ALLOWANCE = {
    "multi_turn_base": 6,
    "multi_turn_miss_func": 9,
    "multi_turn_miss_param": 7,
    "multi_turn_long_context": 7,
    "memory": 6,
}
LONG_CONTEXT_SPIKE_TOKENS = 43803
OUTPUT_TOKENS = 900
MINIMUM_STEPS = 6
FORCE_QUIT_STEPS = STEP_LIMIT + 1

# 80 CNY on the rates named for 26 Nov 2026. The live ceiling is twelve dollars.
BUDGET_CNY = Decimal("80")
CEILING_USD = Decimal("12")
PACK_LIMIT_USD = Decimal("11.50")
CNY_PER_USD = Decimal("6.6649")
USD_PER_CNY = Decimal("0.150079")
MILLION = Decimal(1_000_000)
MISS = OFF_PEAK_PER_MILLION["cache_miss"]
OUTPUT_PRICE = OFF_PEAK_PER_MILLION["output"]

HKT = ZoneInfo("Asia/Hong_Kong")
START_HKT = datetime(2026, 11, 26, 18, 30, tzinfo=HKT)
FRIDAY_PEAK_HKT = datetime(2026, 11, 27, 9, 0, tzinfo=HKT)

DRAW_FILE = Path("preliminary") / "draw.json"
COST_FILE = Path("preliminary") / "cost.json"
C47_BILLS = Path("evidence/pilot-2026-11-25-revised-c47b186c/original/live-c47b186c/bills.jsonl")
VALIDATION_BILLS = Path("evidence/validation-2026-11-25-0bf829c6/original/live-0bf829c6/bills.jsonl")
FLIGHTS = (("c47b186c", C47_BILLS), ("0bf829c6", VALIDATION_BILLS))

_TOKEN_CACHE: dict[str, list[int]] = {}


def preliminary_dir() -> Path:
    return study_dir() / "preliminary"


def _dumps(payload: dict) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def draw_sha256(draw: dict) -> str:
    return sha256(_dumps(draw).encode("utf-8")).hexdigest()


def _usd(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.000001")))


def _cny(usd: Decimal) -> dict:
    return {
        "at_6.6649_cny_per_usd": _usd(usd * CNY_PER_USD),
        "at_0.150079_usd_per_cny": _usd(usd / USD_PER_CNY),
    }


def _half_up(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _percentile(values: list[int], p: Decimal) -> int:
    ordered = sorted(values)
    if not ordered:
        raise RuntimeError("percentile of an empty bill sample")
    index = int((p * Decimal(len(ordered) - 1)).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))
    return ordered[index]


def _family(category: str) -> str:
    if category.startswith("memory_"):
        return "memory"
    if category.startswith("multi_turn_"):
        return category
    return "single"


def _bill_rows(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("output_tokens") is None or row.get("prompt_tokens") is None:
            raise RuntimeError(f"bill row missing tokens in {path}")
        rows.append(row)
    if not rows:
        raise RuntimeError(f"no bills in {path}")
    return rows


def derived_allowances() -> dict:
    """Prompt, step, and spike allowances from the two archived flights."""
    per_flight: dict[str, dict] = {}
    spike = 0
    for name, relative in FLIGHTS:
        grouped: dict[str, list[dict]] = {}
        for row in _bill_rows(study_dir() / relative):
            grouped.setdefault(_family(row["category"]), []).append(row)
            if row["category"] == "multi_turn_long_context":
                spike = max(spike, int(row["prompt_tokens"]))
        summary = {}
        for family, rows in grouped.items():
            turns: dict[tuple, int] = {}
            prompt = 0
            for row in rows:
                prompt += int(row["prompt_tokens"])
                key = (row["case_id"], row["arm"], row["turn"])
                turns[key] = turns.get(key, 0) + 1
            mean = Decimal(prompt) / Decimal(len(rows))
            scaled = int((mean * Decimal("1.5")).to_integral_value(ROUND_CEILING))
            summary[family] = {
                "prompt": max(scaled, _percentile([int(row["prompt_tokens"]) for row in rows], Decimal("0.95"))),
                "steps": _percentile(list(turns.values()), Decimal("0.90")),
            }
        per_flight[name] = summary
    prompt = {}
    steps = {}
    for family in PROMPT_ALLOWANCE:
        prompt[family] = max(per_flight[name][family]["prompt"] for name, _relative in FLIGHTS)
        highest = max(per_flight[name][family]["steps"] for name, _relative in FLIGHTS)
        steps[family] = max(MINIMUM_STEPS, highest)
    return {"prompt": prompt, "steps": steps, "spike": spike, "flights": per_flight}


def _check_allowances(derived: dict) -> None:
    if derived["prompt"] != PROMPT_ALLOWANCE:
        raise RuntimeError("prompt allowances do not match the archived bills")
    if derived["steps"] != STEP_ALLOWANCE:
        raise RuntimeError("step allowances do not match the archived bills")
    if derived["spike"] != LONG_CONTEXT_SPIKE_TOKENS:
        raise RuntimeError("long-context spike does not match the archived bills")
    if LONG_CONTEXT_SPIKE_TOKENS <= PROMPT_ALLOWANCE["multi_turn_long_context"]:
        raise RuntimeError("long-context spike is not above the prompt allowance")


def pilot_case_ids() -> set[str]:
    built = build_draw()
    committed = json.loads((study_dir() / "pilot" / "draw.json").read_text(encoding="utf-8"))
    if committed != built:
        raise RuntimeError("pilot/draw.json does not match the pilot builder")
    return {row["case_id"] for row in built["rows"]}


def validation_case_ids() -> set[str]:
    path = study_dir() / "validation" / "draw.json"
    draw = json.loads(path.read_text(encoding="utf-8"))
    return {row["case_id"] for row in draw["order"]}


def sample_size(category: str, population: int, fraction: Decimal = FRACTION) -> int:
    if population <= 0:
        raise RuntimeError(f"{category} has no in-scope questions")
    if category == "live_parallel":
        return population
    rounded = _half_up(fraction * Decimal(population))
    return min(population, max(MINIMUM.get(category, 1), rounded))


def _choose(category: str, ids: list[str], k: int, pilot_ids: set[str]) -> tuple[list[str], str, str, int]:
    ordered = sorted(ids)
    free = [case_id for case_id in ordered if case_id not in pilot_ids]
    if len(free) >= k:
        pool, pool_rule = free, "excluding_exposed_pilot"
    else:
        pool, pool_rule = ordered, "including_exposed_pilot"
    if k > len(pool):
        raise RuntimeError(f"{category} needs {k} ids and the pool has {len(pool)}")
    if k == len(pool):
        return list(pool), "all_in_pool", pool_rule, len(pool)
    rng = random.Random(f"clean-start-usx-preliminary:{SEED}:{category}")
    return rng.sample(pool, k), "sample", pool_rule, len(pool)


def _questions() -> dict[str, list[dict]]:
    return {category: list(in_scope_questions(category)) for category in study_categories()}


def assemble_draw(fraction: Decimal = FRACTION) -> dict:
    """Ids for one fraction. Deterministic. Does not read gold, scores, or bills."""
    if fraction <= 0:
        raise RuntimeError("preliminary fraction must be positive")
    exposed = pilot_case_ids()
    questions = _questions()
    draws = []
    scoring = []
    for category in study_categories():
        cases = questions[category]
        population = len(cases)
        k = sample_size(category, population, fraction)
        pool_cases = cases
        scenario = None
        if is_memory(category):
            scenario = MEMORY_SCENARIO
            pool_cases = [case for case in cases if case.get("scenario") == MEMORY_SCENARIO]
            if len(pool_cases) < k:
                raise RuntimeError(f"{category} notetaker pool is smaller than {k}")
        chosen, method, pool_rule, sample_pool = _choose(
            category, [case["id"] for case in pool_cases], k, exposed,
        )
        if len(chosen) != len(set(chosen)):
            raise RuntimeError(f"{category} draw repeated an id")
        draws.append({
            "category": category,
            "population": population,
            "scenario_pool": len(pool_cases) if scenario else None,
            "sample_pool": sample_pool,
            "frozen": len(chosen),
            "method": method,
            "pool_rule": pool_rule,
            "scenario": scenario,
        })
        for position, case_id in enumerate(chosen):
            scoring.append({
                "case_id": case_id,
                "category": category,
                "prereq": False,
                "position": position,
            })
    seen_memory = []
    for row in scoring:
        if is_memory(row["category"]) and row["category"] not in seen_memory:
            seen_memory.append(row["category"])
    prerequisites = []
    for category in seen_memory:
        for item in load_prereqs(category):
            if item.get("scenario") != MEMORY_SCENARIO:
                continue
            prerequisites.append({
                "case_id": item["id"],
                "category": category,
                "prereq": True,
                "scenario": MEMORY_SCENARIO,
            })
    scoring_by_category: dict[str, list[dict]] = {}
    for row in scoring:
        scoring_by_category.setdefault(row["category"], []).append(row)
    prereq_by_category: dict[str, list[dict]] = {}
    for row in prerequisites:
        prereq_by_category.setdefault(row["category"], []).append(row)
    order = []
    for category in study_categories():
        if is_memory(category):
            continue
        order.extend(scoring_by_category.get(category, []))
    for category in seen_memory:
        order.extend(prereq_by_category[category])
        order.extend(scoring_by_category[category])
    for index, row in enumerate(order):
        row["run_index"] = index
    scoring_ids = [row["case_id"] for row in scoring]
    return {
        "study": STUDY_ID,
        "official_settlement": OFFICIAL_SETTLEMENT,
        "kind": "preliminary",
        "seed": SEED,
        "seed_reason": SEED_REASON,
        "fraction": str(FRACTION) if fraction == FRACTION else str(fraction),
        "fraction_quantum": str(FRACTION_QUANTUM),
        "algorithm": DRAW_ALGORITHM,
        "memory_scenario": MEMORY_SCENARIO,
        "memory_scenario_reason": MEMORY_SCENARIO_REASON,
        "replicate_u": False,
        "thinking": "off",
        "budget_cny": str(BUDGET_CNY),
        "ceiling_usd": str(CEILING_USD),
        "pack_limit_usd": str(PACK_LIMIT_USD),
        "pilot_overlap_ids": sorted(set(scoring_ids) & exposed),
        "validation_overlap_ids": sorted(set(scoring_ids) & validation_case_ids()),
        "draws": draws,
        "order": order,
    }


def _check_committed(draw: dict) -> None:
    if draw["official_settlement"] is not False:
        raise RuntimeError("preliminary official_settlement must stay false")
    if draw["seed"] != SEED or draw["thinking"] != "off" or draw["replicate_u"] is not False:
        raise RuntimeError("preliminary draw left its thinking-off pin")
    if Decimal(draw["fraction"]) != FRACTION:
        raise RuntimeError("preliminary draw fraction is not the frozen fraction")
    ids = [row["case_id"] for row in draw["order"]]
    if len(ids) != len(set(ids)):
        raise RuntimeError("preliminary order repeats an id")
    if any(row["category"].startswith("web_search") for row in draw["order"]):
        raise RuntimeError("preliminary draw contains a web-search category")
    categories = [row["category"] for row in draw["draws"]]
    if categories != list(study_categories()):
        raise RuntimeError("preliminary draw dropped or reordered a category")
    exposed = set(pilot_case_ids())
    questions = _questions()
    for row in draw["draws"]:
        expected = sample_size(row["category"], len(questions[row["category"]]))
        if row["frozen"] != expected or row["population"] != len(questions[row["category"]]):
            raise RuntimeError(f"{row['category']} sample size does not match the fraction")
    memory_questions = [row for row in draw["order"] if is_memory(row["category"]) and not row["prereq"]]
    for row in memory_questions:
        case = next(case for case in questions[row["category"]] if case["id"] == row["case_id"])
        if case.get("scenario") != MEMORY_SCENARIO:
            raise RuntimeError("preliminary memory question is not notetaker")
        if row["case_id"] in exposed:
            raise RuntimeError("preliminary memory question reuses an exposed pilot id")
    live_parallel = {case["id"] for case in questions["live_parallel"]}
    if set(draw["pilot_overlap_ids"]) != live_parallel:
        raise RuntimeError("preliminary pilot overlap is not exactly the live_parallel population")
    seen_scoring_memory = False
    last_memory = None
    for row in draw["order"]:
        if not is_memory(row["category"]):
            if seen_scoring_memory or last_memory is not None:
                raise RuntimeError("a non-memory case follows the memory block")
            continue
        if row["prereq"]:
            if seen_scoring_memory and row["category"] == last_memory:
                raise RuntimeError("a prerequisite follows its own category's questions")
            if row.get("scenario") != MEMORY_SCENARIO:
                raise RuntimeError("preliminary prerequisite is not notetaker")
            seen_scoring_memory = False
        else:
            seen_scoring_memory = True
        last_memory = row["category"]
    indexes = [row["run_index"] for row in draw["order"]]
    if indexes != list(range(len(indexes))):
        raise RuntimeError("preliminary run_index is not the order")


def build_preliminary_draw() -> dict:
    draw = assemble_draw(FRACTION)
    _check_committed(draw)
    return draw


def load_committed_draw() -> dict:
    return json.loads((study_dir() / DRAW_FILE).read_text(encoding="utf-8"))


def cases_for_draw(draw: dict) -> list[dict]:
    scoring = {
        (category, case["id"]): case
        for category in study_categories()
        for case in in_scope_questions(category)
    }
    prereqs = {
        (category, case["id"]): case
        for category in study_categories()
        if is_memory(category)
        for case in load_prereqs(category)
    }
    chosen = []
    for row in draw["order"]:
        key = (row["category"], row["case_id"])
        case = prereqs.get(key) if row["prereq"] else scoring.get(key)
        if case is None:
            raise RuntimeError(f"preliminary id is not in the loaded questions: {row['case_id']}")
        if bool(case.get("prereq")) != bool(row["prereq"]):
            raise RuntimeError(f"preliminary prereq flag disagrees for {row['case_id']}")
        chosen.append(case)
    return chosen


def select_preliminary_cases() -> list[dict]:
    """Cases in frozen run order. Raises when the file and the builder disagree."""
    built = build_preliminary_draw()
    committed = load_committed_draw()
    if committed != built:
        raise RuntimeError("preliminary/draw.json does not match the preliminary builder")
    return cases_for_draw(committed)


def _request_usd(prompt_tokens: int, output_tokens: int, requests: int = 1) -> Decimal:
    return (
        Decimal(prompt_tokens) * MISS + Decimal(output_tokens) * OUTPUT_PRICE
    ) / MILLION * Decimal(requests)


def _message_text(case: dict) -> str:
    from tool_compression.clean_start.runner import turn_messages

    parts = []
    for item in turn_messages(case, 0):
        content = item.get("content")
        if isinstance(content, str):
            parts.append(content)
    return "\n".join(parts)


def _arm_tokens(case: dict) -> list[int]:
    cached = _TOKEN_CACHE.get(case["id"])
    if cached is not None:
        return cached
    from tool_compression.clean_start.runner import arm_tools

    counter = _arm_tokens.counter
    tokens = []
    for arm in ARMS:
        tokens.append(
            counter.count(_message_text(case))
            + counter.count(dump_request(arm_tools(case["function"], case["category"], arm)))
        )
    _TOKEN_CACHE[case["id"]] = tokens
    return tokens


_arm_tokens.counter = TiktokenCounter(LOCAL_TOKENIZER)


def _allowance_family(category: str) -> str:
    if is_memory(category):
        return "memory"
    if category not in PROMPT_ALLOWANCE:
        raise RuntimeError(f"{category} has no trajectory allowance")
    return category


def price_cases(cases: list[dict]) -> dict:
    """Off-peak planning upper for one case list. All prompt tokens are cache misses."""
    _check_allowances(derived_allowances())
    single = Decimal(0)
    trajectory = Decimal(0)
    spike = Decimal(0)
    structural = Decimal(0)
    floor_tokens = 0
    allowance_requests = 0
    by_category: dict[str, dict] = {}
    long_cases = 0
    memory_backends = []
    for case in cases:
        category = case["category"]
        turns = len(case["question"])
        row = by_category.setdefault(category, {
            "scoring": 0, "prerequisites": 0, "scoring_turns": 0, "prereq_turns": 0,
        })
        if case.get("prereq"):
            row["prerequisites"] += 1
            row["prereq_turns"] += turns
        else:
            row["scoring"] += 1
            row["scoring_turns"] += turns
        tokens = _arm_tokens(case)
        floor_tokens += sum(tokens)
        if is_multi_turn(category) or is_memory(category):
            family = _allowance_family(category)
            prompt = PROMPT_ALLOWANCE[family]
            steps = STEP_ALLOWANCE[family]
            requests = turns * steps * len(ARMS)
            trajectory += _request_usd(prompt, OUTPUT_TOKENS, requests)
            structural += _request_usd(prompt, OUTPUT_TOKENS, turns * FORCE_QUIT_STEPS * len(ARMS))
            allowance_requests += requests
            if category == "multi_turn_long_context" and not case.get("prereq"):
                long_cases += 1
            if is_memory(category) and category not in memory_backends and not case.get("prereq"):
                memory_backends.append(category)
        else:
            single += _request_usd(sum(tokens), 0) + _request_usd(0, OUTPUT_TOKENS, len(ARMS))
            structural += _request_usd(sum(tokens), 0) + _request_usd(0, OUTPUT_TOKENS, len(ARMS))
            allowance_requests += len(ARMS)
    spike = _request_usd(
        LONG_CONTEXT_SPIKE_TOKENS - PROMPT_ALLOWANCE["multi_turn_long_context"],
        0,
        long_cases * len(ARMS),
    )
    structural += spike
    contingency = Decimal(0)
    for _category in memory_backends:
        extra = FORCE_QUIT_STEPS - STEP_ALLOWANCE["memory"]
        contingency += _request_usd(PROMPT_ALLOWANCE["memory"], OUTPUT_TOKENS, extra * len(ARMS))
        allowance_requests += extra * len(ARMS)
    upper = single + trajectory + spike + contingency
    return {
        "upper": upper,
        "single": single,
        "trajectory": trajectory,
        "spike": spike,
        "contingency": contingency,
        "structural": structural,
        "floor_tokens": floor_tokens,
        "floor_usd": _request_usd(floor_tokens, 0),
        "allowance_requests": allowance_requests,
        "by_category": by_category,
        "long_cases": long_cases,
        "memory_backends": memory_backends,
    }


def upper_for_fraction(fraction: Decimal) -> Decimal:
    """Planning upper of the draw that fraction would freeze. Used to show the next step does not fit."""
    return price_cases(cases_for_draw(assemble_draw(fraction)))["upper"]


def _flight_totals() -> dict[str, dict[str, dict]]:
    totals: dict[str, dict[str, dict]] = {}
    for name, relative in FLIGHTS:
        families: dict[str, dict] = {}
        for row in _bill_rows(study_dir() / relative):
            bucket = families.setdefault(_family(row["category"]), {
                "prompt": 0, "output": 0, "requests": 0, "turns": set(),
            })
            bucket["prompt"] += int(row["prompt_tokens"])
            bucket["output"] += int(row["output_tokens"])
            bucket["requests"] += 1
            bucket["turns"].add((row["case_id"], row["arm"], row["turn"]))
        totals[name] = families
    return totals


def _per_turn_usd(bucket: dict) -> Decimal:
    turns = len(bucket["turns"])
    if turns == 0:
        raise RuntimeError("flight family has no turns")
    return (Decimal(bucket["prompt"]) * MISS + Decimal(bucket["output"]) * OUTPUT_PRICE) / Decimal(turns) / MILLION


def observed_mean(cases: list[dict]) -> dict:
    """Higher archived flight's own mean prompt, output, and steps, on this draw's turns."""
    totals = _flight_totals()
    draw_turns: dict[str, int] = {}
    for case in cases:
        family = _family(case["category"])
        draw_turns[family] = draw_turns.get(family, 0) + len(case["question"])
    families = {}
    usd = Decimal(0)
    sends = Decimal(0)
    memory_sends = Decimal(0)
    other_sends = Decimal(0)
    for family, turns in sorted(draw_turns.items()):
        chosen_name = None
        chosen_bucket = None
        chosen_cost = None
        flights = {}
        for name, _relative in FLIGHTS:
            bucket = totals[name][family]
            cost = _per_turn_usd(bucket)
            flights[name] = {
                "requests": bucket["requests"],
                "turns": len(bucket["turns"]),
                "usd_per_arm_turn": _usd(cost),
            }
            if chosen_cost is None or cost > chosen_cost:
                chosen_name = name
                chosen_bucket = bucket
                chosen_cost = cost
        arm_turns = Decimal(turns) * Decimal(len(ARMS))
        family_sends = arm_turns * Decimal(chosen_bucket["requests"]) / Decimal(len(chosen_bucket["turns"]))
        family_usd = arm_turns * chosen_cost
        usd += family_usd
        sends += family_sends
        if family == "memory":
            memory_sends += family_sends
        else:
            other_sends += family_sends
        families[family] = {
            "flight": chosen_name,
            "draw_user_turns": turns,
            "mean_steps": str(
                (Decimal(chosen_bucket["requests"]) / Decimal(len(chosen_bucket["turns"]))).quantize(Decimal("0.01"))
            ),
            "sends": _usd(family_sends),
            "usd": _usd(family_usd),
            "flights": flights,
        }
    return {
        "rule": (
            "For each family, use the archived flight with the higher mean off-peak "
            "all-miss cost per arm-turn, taking that flight's prompt, output, and "
            "steps together. Apply it to this draw's user turns and four arms. "
            "The long-context spike and the 21-step memory turn are allowance tails, "
            "not part of this mean."
        ),
        "families": families,
        "usd": usd,
        "sends": sends,
        "memory_sends": memory_sends,
        "other_sends": other_sends,
    }


def _finish(sends: Decimal, seconds_per_request: Decimal) -> dict:
    micros = (sends * seconds_per_request * Decimal(1_000_000)).to_integral_value(ROUND_HALF_UP)
    done = START_HKT + timedelta(microseconds=int(micros))
    hours = sends * seconds_per_request / Decimal(3600)
    return {
        "pace_seconds": str(seconds_per_request),
        "hours": str(hours.quantize(Decimal("0.01"))),
        "finish_hkt": done.isoformat(),
        "before_friday_peak": done < FRIDAY_PEAK_HKT,
    }


def preliminary_report() -> dict:
    """Floor, planning upper, and observed mean for the frozen draw, off-peak, all cache-miss."""
    draw = build_preliminary_draw()
    cases = cases_for_draw(draw)
    priced = price_cases(cases)
    if priced["upper"] > PACK_LIMIT_USD:
        raise RuntimeError(
            f"preliminary planning upper {priced['upper']} exceeds the {PACK_LIMIT_USD} pack limit"
        )
    observed = observed_mean(cases)
    mixed_seconds = observed["other_sends"] * Decimal("2.0") + observed["memory_sends"] * Decimal("3.3")
    mixed_done = START_HKT + timedelta(
        microseconds=int((mixed_seconds * Decimal(1_000_000)).to_integral_value(ROUND_HALF_UP))
    )
    finishes = {
        "observed_at_1.9s": _finish(observed["sends"], Decimal("1.9")),
        "observed_at_2.0s": _finish(observed["sends"], Decimal("2.0")),
        "observed_at_3.3s": _finish(observed["sends"], Decimal("3.3")),
        "observed_memory_at_3.3s_rest_at_2.0s": {
            "pace_seconds": "memory 3.3, other 2.0",
            "hours": str((mixed_seconds / Decimal(3600)).quantize(Decimal("0.01"))),
            "finish_hkt": mixed_done.isoformat(),
            "before_friday_peak": mixed_done < FRIDAY_PEAK_HKT,
        },
    }
    allowance_finish = {
        "allowance_at_2.0s": _finish(Decimal(priced["allowance_requests"]), Decimal("2.0")),
        "allowance_at_3.3s": _finish(Decimal(priced["allowance_requests"]), Decimal("3.3")),
    }
    for label, row in {**finishes, **allowance_finish}.items():
        if not row["before_friday_peak"]:
            raise RuntimeError(f"{label} reaches Friday peak")
    scoring = sum(1 for case in cases if not case.get("prereq"))
    prereq = len(cases) - scoring
    return {
        "study": STUDY_ID,
        "official_settlement": OFFICIAL_SETTLEMENT,
        "kind": "preliminary",
        "seed": SEED,
        "seed_reason": SEED_REASON,
        "fraction": str(FRACTION),
        "draw_sha256": draw_sha256(draw),
        "thinking": "off",
        "replicate_u": False,
        "arms": list(ARMS),
        "band": "off_peak",
        "prices_per_million": {"cache_miss": str(MISS), "output": str(OUTPUT_PRICE)},
        "cache_credit": "none; every prompt token is priced as a miss",
        "budget_cny": str(BUDGET_CNY),
        "rates_named_2026_11_26": {
            "cny_per_usd": str(CNY_PER_USD),
            "usd_per_cny": str(USD_PER_CNY),
            "source": "named by Jacky for 26 Nov 2026; not fetched by this package",
        },
        "ceiling_usd": str(CEILING_USD),
        "ceiling_cny": _cny(CEILING_USD),
        "pack_limit_usd": str(PACK_LIMIT_USD),
        "cases": {
            "conversations": len(cases),
            "scoring": scoring,
            "prerequisites": prereq,
            "by_category": priced["by_category"],
        },
        "slots": {
            "total": len(cases) * len(ARMS),
            "scoring": scoring * len(ARMS),
            "prerequisites": prereq * len(ARMS),
        },
        "order": "single-turn, then multi-turn, then each memory category's prerequisites before its questions",
        "memory_scenario": MEMORY_SCENARIO,
        "pilot_overlap_ids": draw["pilot_overlap_ids"],
        "validation_overlap_ids": draw["validation_overlap_ids"],
        "first_request_floor_tokens": priced["floor_tokens"],
        "first_request_floor_usd": _usd(priced["floor_usd"]),
        "first_request_floor": (
            "Local o200k_base tokens of the turn-0 message text plus the tools array, "
            "summed over the four arms, priced as off-peak cache misses, with no output and "
            "no chat template. The pinned memory instruction and core-memory text are not "
            "included. This is a lower bound on prompt spend if every slot ended after one "
            "request, not a forecast."
        ),
        "planning_upper_usd": _usd(priced["upper"]),
        "planning_upper_cny": _cny(priced["upper"]),
        "planning_upper_parts_usd": {
            "single_turn": _usd(priced["single"]),
            "trajectories": _usd(priced["trajectory"]),
            "long_context_spike": _usd(priced["spike"]),
            "memory_force_quit_contingency": _usd(priced["contingency"]),
        },
        "planning_upper": (
            f"Off-peak prices, no cache credit. A single-turn slot is its local first-request "
            f"tokens plus {OUTPUT_TOKENS} output tokens. A trajectory turn is the family's step "
            f"allowance (at least {MINIMUM_STEPS}, or the higher archived 90th percentile) at "
            f"the greater of 1.5 times the mean prompt and the 95th percentile prompt across "
            f"c47b186c and 0bf829c6, plus {OUTPUT_TOKENS} output tokens. One long-context "
            f"request per drawn case per arm is raised to {LONG_CONTEXT_SPIKE_TOKENS} prompt "
            f"tokens. One memory turn per included backend per arm is priced at "
            f"{FORCE_QUIT_STEPS} steps instead of {STEP_ALLOWANCE['memory']}. Sized to stay at "
            f"or under ${PACK_LIMIT_USD} so the ${CEILING_USD} cap is not the way the run is "
            f"expected to end."
        ),
        "allowance_requests": priced["allowance_requests"],
        "structural_cap_usd": _usd(priced["structural"]),
        "structural_cap": (
            "The same prompt allowances with every trajectory turn taking the runner cap of "
            f"{FORCE_QUIT_STEPS} requests, plus the long-context spike. That is the tail if "
            "the model never finishes a turn. It is not the planning number. The hard ceiling "
            "still stops the run."
        ),
        "prompt_allowance_tokens": PROMPT_ALLOWANCE,
        "step_allowance": STEP_ALLOWANCE,
        "long_context_spike_tokens": LONG_CONTEXT_SPIKE_TOKENS,
        "observed_mean_usd": _usd(observed["usd"]),
        "observed_mean_cny": _cny(observed["usd"]),
        "observed_mean_sends": _usd(observed["sends"]),
        "observed_mean": observed["rule"],
        "observed_by_family": observed["families"],
        "start_hkt": START_HKT.isoformat(),
        "friday_peak_hkt": FRIDAY_PEAK_HKT.isoformat(),
        "duration": {**finishes, **allowance_finish},
        "prior_spend_not_deducted": (
            "Tonight's authorized cap is $12. Earlier incomplete clean-start flights are not "
            "subtracted from it."
        ),
        "full_run_follow_up": (
            "The full in-scope thinking-off fly is 3,127 scoring questions plus 111 memory "
            "prerequisites, 12,952 slots. It is not this draw. It needs a larger budget, and "
            "the runner still has no retry and no resume."
        ),
    }


def write_preliminary_files() -> dict:
    """Write the draw and the cost report. Does not touch the pilot or validation draws."""
    root = preliminary_dir()
    root.mkdir(parents=True, exist_ok=True)
    draw = build_preliminary_draw()
    text = _dumps(draw)
    (root / "draw.json").write_text(text, encoding="utf-8")
    report = preliminary_report()
    if report["draw_sha256"] != sha256(text.encode("utf-8")).hexdigest():
        raise RuntimeError("preliminary cost report hashed a different draw")
    (root / "cost.json").write_text(_dumps(report), encoding="utf-8")
    return {
        "conversations": report["cases"]["conversations"],
        "scoring": report["cases"]["scoring"],
        "prerequisites": report["cases"]["prerequisites"],
        "slots": report["slots"]["total"],
        "planning_upper_usd": report["planning_upper_usd"],
        "observed_mean_usd": report["observed_mean_usd"],
        "observed_mean_sends": report["observed_mean_sends"],
        "allowance_requests": report["allowance_requests"],
    }


def load_committed_cost() -> dict:
    report = json.loads((study_dir() / COST_FILE).read_text(encoding="utf-8"))
    draw_bytes = (study_dir() / DRAW_FILE).read_bytes()
    if report["draw_sha256"] != sha256(draw_bytes).hexdigest():
        raise RuntimeError("preliminary/cost.json does not match preliminary/draw.json")
    if report["official_settlement"] is not False:
        raise RuntimeError("preliminary official_settlement must stay false")
    if Decimal(report["planning_upper_usd"]) > PACK_LIMIT_USD:
        raise RuntimeError("committed preliminary upper exceeds the pack limit")
    if Decimal(report["ceiling_usd"]) != CEILING_USD:
        raise RuntimeError("committed preliminary ceiling is not $12")
    return report
