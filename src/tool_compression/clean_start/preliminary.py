"""Preliminary 20% draw for the thinking-off flight under a $42 ceiling.

The draw is local. Nothing here contacts a provider or reads a key. Question
text, gold, and scores are not inputs to which ids are chosen. Archived bills
are read only when the cost report checks the prompt and step allowances.
Editors are called only to count the tool text a single-turn slot would send.

The 2026-11-25 pilot draw and the validation draw stay where they are. This
module writes nothing into ``pilot/`` or ``validation/``. The superseded
119-case preliminary (seed 20261127, fraction 0.0374, $12 ceiling) is replaced
by repointing this path. There is no second flag.

The live ceiling is $42, inside the 280 CNY prepaid balance. The planning
upper is an allowance. It is not required to fit under $42, and the draw is
not shrunk to fit the old $11.50 pack limit. A fat-tail run priced at the
allowance can stop at $42 before the 20% sample completes. The check that
replaced the old refusal is the observed-mean path with every send after
Friday 09:00 HKT billed at peak, at each pace profile, at or under $42.
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
from tool_compression.clean_start.rate_card import OFF_PEAK_PER_MILLION, is_peak
from tool_compression.clean_start.scope import in_scope_questions, study_categories
from tool_compression.config import LOCAL_TOKENIZER
from tool_compression.count import TiktokenCounter, dump_request

# 20261125 is the pilot seed, 20261126 is the validation seed, and 20261127 is
# the superseded 119-case preliminary. This draw does not reuse them.
SEED = "20261128"
SEED_REASON = (
    "20261125 is the pilot seed, 20261126 is the committed validation seed, "
    "and 20261127 is the superseded 119-case preliminary, so this draw uses 20261128."
)
FRACTION = Decimal("0.2")
DRAW_ALGORITHM = (
    "n = min(population, max(floor, half_up(f * population))) with half-up "
    "rounding. f is 0.2. live_parallel takes every in-scope id. "
    "live_relevance, live_parallel_multiple, and each memory backend have "
    "floor 2; every other category has floor 1. At f = 0.2 those floors do "
    "not bind. live_parallel is the special case that keeps both in-scope ids, "
    "because half_up(0.2 * 2) is 0. Memory candidates are every in-scope "
    "question, across all five scenarios. The pool drops ids in the exposed "
    "pilot draw when at least n ids remain. random.Random("
    "'clean-start-usx-preliminary:20261128:<category>').sample(sorted(pool), n) "
    "when n is smaller than that pool; otherwise the sorted pool is kept and "
    "sample is not called. Python 3.12 random. Matched prerequisites are every "
    "prerequisite conversation of each memory scenario present in that "
    "backend's draw."
)
# Binds only when it is above the rounded fraction. live_parallel is the whole population.
MINIMUM = {
    "live_relevance": 2,
    "live_parallel_multiple": 2,
    "memory_kv": 2,
    "memory_vector": 2,
    "memory_rec_sum": 2,
}
MEMORY_POOL = "all_in_scope"
MEMORY_POOL_REASON = (
    "Memory candidates are every in-scope question on the backend, all five "
    "scenarios, not the notetaker scenario alone. Matched prerequisites are "
    "every prerequisite conversation of each scenario the draw includes, on "
    "that backend. The scenario mix is whatever the seed draws. It is not "
    "chosen to fit under the ceiling."
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

# 280 CNY prepaid on the rates named for 26 Nov 2026. 42 * 6.6649 = 279.9258 CNY.
# The authorized ceiling is exactly $42. $42.01 is not this package, and neither
# is the superseded $12 / 80 CNY cap or the earlier $27 / 180 CNY recommendation.
BUDGET_CNY = Decimal("280")
CEILING_USD = Decimal("42")
CNY_PER_USD = Decimal("6.6649")
USD_PER_CNY = Decimal("0.150079")
MILLION = Decimal(1_000_000)
MISS = OFF_PEAK_PER_MILLION["cache_miss"]
OUTPUT_PRICE = OFF_PEAK_PER_MILLION["output"]

HKT = ZoneInfo("Asia/Hong_Kong")
START_HKT = datetime(2026, 11, 26, 18, 0, tzinfo=HKT)
FRIDAY_PEAK_HKT = datetime(2026, 11, 27, 9, 0, tzinfo=HKT)

PACE_PROFILES = {
    "observed_at_1.9s": {"memory": Decimal("1.9"), "other": Decimal("1.9")},
    "observed_at_2.0s": {"memory": Decimal("2.0"), "other": Decimal("2.0")},
    "observed_at_3.3s": {"memory": Decimal("3.3"), "other": Decimal("3.3")},
    "observed_memory_at_3.3s_rest_at_2.0s": {"memory": Decimal("3.3"), "other": Decimal("2.0")},
}

DRAW_FILE = Path("preliminary") / "draw.json"
COST_FILE = Path("preliminary") / "cost.json"
# The file bytes of the committed draw.json and the thinking-off slot order.
# A live run, fresh or resumed, refuses anything else.
COMMITTED_DRAW_SHA256 = "2904904116ca21ad8830f4bb2dfaaf9cfd1773124315a8a26fe934f3490a785a"
COMMITTED_SLOT_SHA256 = "a794ab88779d6ef75a0d8928d32359512b19a9aad435587e9c53b8d502421f7f"
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
        if is_memory(category) and len(pool_cases) < k:
            raise RuntimeError(f"{category} in-scope pool is smaller than {k}")
        chosen, method, pool_rule, sample_pool = _choose(
            category, [case["id"] for case in pool_cases], k, exposed,
        )
        if len(chosen) != len(set(chosen)):
            raise RuntimeError(f"{category} draw repeated an id")
        scenarios = None
        if is_memory(category):
            by_id = {case["id"]: case for case in pool_cases}
            scenarios = sorted({by_id[case_id]["scenario"] for case_id in chosen})
        draws.append({
            "category": category,
            "population": population,
            "scenario_pool": len(pool_cases) if is_memory(category) else None,
            "sample_pool": sample_pool,
            "frozen": len(chosen),
            "method": method,
            "pool_rule": pool_rule,
            "scenarios": scenarios,
        })
        for position, case_id in enumerate(chosen):
            scoring.append({
                "case_id": case_id,
                "category": category,
                "prereq": False,
                "position": position,
            })
    seen_memory = []
    scenarios_by_category = {
        row["category"]: set(row["scenarios"])
        for row in draws
        if row["scenarios"]
    }
    for row in scoring:
        if is_memory(row["category"]) and row["category"] not in seen_memory:
            seen_memory.append(row["category"])
    prerequisites = []
    for category in seen_memory:
        wanted = scenarios_by_category[category]
        for item in load_prereqs(category):
            scenario = item.get("scenario")
            if scenario not in wanted:
                continue
            prerequisites.append({
                "case_id": item["id"],
                "category": category,
                "prereq": True,
                "scenario": scenario,
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
        "algorithm": DRAW_ALGORITHM,
        "memory_pool": MEMORY_POOL,
        "memory_pool_reason": MEMORY_POOL_REASON,
        "replicate_u": False,
        "thinking": "off",
        "budget_cny": str(BUDGET_CNY),
        "ceiling_usd": str(CEILING_USD),
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
    drawn_scenarios: dict[str, set[str]] = {}
    for row in draw["draws"]:
        if is_memory(row["category"]):
            if row["scenario_pool"] != row["population"]:
                raise RuntimeError(f"{row['category']} memory pool is not the full in-scope population")
            if not row["scenarios"]:
                raise RuntimeError(f"{row['category']} draw has no memory scenario")
            drawn_scenarios[row["category"]] = set(row["scenarios"])
        elif row["scenarios"] is not None or row["scenario_pool"] is not None:
            raise RuntimeError(f"{row['category']} recorded a memory pool")
    memory_questions = [row for row in draw["order"] if is_memory(row["category"]) and not row["prereq"]]
    seen_question_scenarios: dict[str, set[str]] = {}
    for row in memory_questions:
        case = next(case for case in questions[row["category"]] if case["id"] == row["case_id"])
        scenario = case.get("scenario")
        if scenario not in drawn_scenarios[row["category"]]:
            raise RuntimeError("preliminary memory question scenario was not recorded")
        if row["case_id"] in exposed:
            raise RuntimeError("preliminary memory question reuses an exposed pilot id")
        seen_question_scenarios.setdefault(row["category"], set()).add(scenario)
    if seen_question_scenarios != drawn_scenarios:
        raise RuntimeError("preliminary memory scenarios do not match the drawn questions")
    for category, scenarios in drawn_scenarios.items():
        expected = [
            item["id"] for item in load_prereqs(category) if item.get("scenario") in scenarios
        ]
        got = [
            row["case_id"] for row in draw["order"]
            if row["category"] == category and row["prereq"]
        ]
        if got != expected:
            raise RuntimeError(f"{category} prerequisites are not the drawn scenarios")
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
            if row.get("scenario") not in drawn_scenarios[row["category"]]:
                raise RuntimeError("preliminary prerequisite scenario was not drawn")
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
    rates = {}
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
        steps_per_arm_turn = Decimal(chosen_bucket["requests"]) / Decimal(len(chosen_bucket["turns"]))
        rates[family] = {"sends": steps_per_arm_turn, "usd": chosen_cost}
        family_sends = arm_turns * steps_per_arm_turn
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
        "rates": rates,
        "usd": usd,
        "sends": sends,
        "memory_sends": memory_sends,
        "other_sends": other_sends,
    }


def _peak_windows(days: int = 8) -> list[tuple[Decimal, Decimal]]:
    """Rate-card peak windows as seconds after START_HKT. HKT has no DST."""
    windows = []
    first = START_HKT.date()
    for offset in range(days):
        day = first + timedelta(days=offset)
        for begin, end in ((9, 12), (14, 18)):
            low = datetime(day.year, day.month, day.day, begin, tzinfo=HKT)
            high = datetime(day.year, day.month, day.day, end, tzinfo=HKT)
            if not is_peak(low) or high <= START_HKT:
                continue
            windows.append((
                Decimal(int((max(low, START_HKT) - START_HKT).total_seconds())),
                Decimal(int((high - START_HKT).total_seconds())),
            ))
    return windows


def observed_with_peak(cases: list[dict], observed: dict) -> dict:
    """The observed-mean path in run order, with sends inside a peak window at double price.

    Each case's sends are spread evenly over its own stretch of the clock at
    the profile's pace. A send that falls inside a rate-card peak window costs
    twice its off-peak price. Memory runs last, so the peak share is memory.
    """
    windows = _peak_windows()
    profiles = {}
    for name, pace in PACE_PROFILES.items():
        elapsed = Decimal(0)
        premium = Decimal(0)
        peak_sends = Decimal(0)
        for case in cases:
            family = _family(case["category"])
            rate = observed["rates"][family]
            arm_turns = Decimal(len(case["question"])) * Decimal(len(ARMS))
            sends = arm_turns * rate["sends"]
            usd = arm_turns * rate["usd"]
            seconds = sends * pace["memory" if family == "memory" else "other"]
            low, high = elapsed, elapsed + seconds
            overlap = sum(
                (max(Decimal(0), min(high, end) - max(low, begin)) for begin, end in windows),
                Decimal(0),
            )
            if seconds > 0 and overlap > 0:
                premium += usd * overlap / seconds
                peak_sends += sends * overlap / seconds
            elapsed = high
        done = START_HKT + timedelta(
            microseconds=int((elapsed * Decimal(1_000_000)).to_integral_value(ROUND_HALF_UP))
        )
        profiles[name] = {
            "finish_hkt": done.isoformat(),
            "peak_sends": _usd(peak_sends),
            "peak_premium_usd": _usd(premium),
            "usd": _usd(observed["usd"] + premium),
            "_usd": observed["usd"] + premium,
        }
    worst = max(profiles, key=lambda key: profiles[key]["_usd"])
    highest = profiles[worst]["_usd"]
    for row in profiles.values():
        row.pop("_usd")
    return {"profiles": profiles, "worst": worst, "usd": highest}


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
    # The allowance is the fat tail. It is above the live ceiling on this draw.
    # Refusing that fact was the old $11.50 pack limit. Do not shrink the draw
    # until the upper fits under $42.
    if priced["upper"] <= CEILING_USD:
        raise RuntimeError(
            "preliminary planning upper fits under the ceiling; "
            "do not shrink this 20% draw to fit $42"
        )
    observed = observed_mean(cases)
    peaked = observed_with_peak(cases, observed)
    if peaked["usd"] > CEILING_USD:
        raise RuntimeError(
            f"observed-mean path with the Friday peak (${_usd(peaked['usd'])} at "
            f"{peaked['worst']}) exceeds the ${CEILING_USD} ceiling"
        )
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
        "allowance_at_1.9s": _finish(Decimal(priced["allowance_requests"]), Decimal("1.9")),
        "allowance_at_2.0s": _finish(Decimal(priced["allowance_requests"]), Decimal("2.0")),
        "allowance_at_3.3s": _finish(Decimal(priced["allowance_requests"]), Decimal("3.3")),
    }
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
        "ceiling_rule": (
            "The live ceiling is exactly $42. 42 times 6.6649 is 279.9258 CNY, "
            "inside the 280 CNY prepaid balance. $42.01 is not this package. "
            "The superseded ceilings were $12 inside 80 CNY and $27 inside 180 CNY."
        ),
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
        "memory_pool": MEMORY_POOL,
        "memory_scenarios": {
            row["category"]: row["scenarios"]
            for row in draw["draws"]
            if row["scenarios"]
        },
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
            f"{FORCE_QUIT_STEPS} steps instead of {STEP_ALLOWANCE['memory']}. This allowance "
            f"is not sized to fit under the ${CEILING_USD} ceiling, and the draw is not "
            f"shrunk to fit the old $11.50 pack limit. ${CEILING_USD} can cover the mean "
            f"path and a peak-rate leftover after 09:00 HKT more comfortably than $27. "
            f"A fat-tail run priced at this allowance can still stop before the 20% "
            f"sample completes. Memory is last."
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
        "observed_mean_with_friday_peak_usd": _usd(peaked["usd"]),
        "observed_mean_with_friday_peak_cny": _cny(peaked["usd"]),
        "observed_mean_with_friday_peak_worst_pace": peaked["worst"],
        "observed_mean_with_friday_peak": peaked["profiles"],
        "ceiling_check": (
            "The check that replaced the old pack limit: at every pace profile, the "
            "observed-mean path in run order, with each send inside a rate-card peak "
            "window (09:00-12:00 and 14:00-18:00 HKT on a weekday) billed at double "
            "the off-peak price, must be at or under the $42 ceiling. The builder, "
            "the committed-cost loader, and the live CLI all refuse otherwise. The "
            "allowance upper is not compared with the ceiling."
        ),
        "start_hkt": START_HKT.isoformat(),
        "friday_peak_hkt": FRIDAY_PEAK_HKT.isoformat(),
        "duration": {**finishes, **allowance_finish},
        "prior_spend_not_deducted": (
            "Tonight's authorized cap is $42, inside the 280 CNY prepaid balance. "
            "Earlier incomplete clean-start flights are not subtracted from it. "
            "The superseded preliminary ceiling was $12 inside 80 CNY."
        ),
        "peak_continuation": (
            "Jacky authorized this live run to continue past Friday 09:00 HKT into "
            "peak if it is still going. The leftover is likely memory, which runs "
            "last. Peak rates are double the off-peak prices used in this report. "
            "The $42 ceiling still applies and is checked before every request."
        ),
        "full_run_follow_up": (
            "The full in-scope thinking-off fly is 3,127 scoring questions plus 111 memory "
            "prerequisites, 12,952 slots. It is not this draw. It needs a larger budget. "
            "Retry and --resume are wired for --preliminary only."
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
    if Decimal(report["ceiling_usd"]) != CEILING_USD:
        raise RuntimeError("committed preliminary ceiling is not $42")
    if Decimal(report["planning_upper_usd"]) <= CEILING_USD:
        raise RuntimeError(
            "committed preliminary upper fits under the ceiling; this 20% draw is not shrunk to fit"
        )
    if report["draw_sha256"] != COMMITTED_DRAW_SHA256:
        raise RuntimeError("preliminary/draw.json is not the committed 20% draw")
    peaked = report.get("observed_mean_with_friday_peak_usd")
    if peaked is None or Decimal(peaked) > CEILING_USD:
        raise RuntimeError("committed observed-mean path with the Friday peak is not at or under $42")
    return report
