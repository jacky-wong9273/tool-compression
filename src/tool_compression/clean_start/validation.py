"""Fresh validation draw for the thinking-off flight under the $20 ceiling.

The draw is local. Nothing here contacts a provider or reads a key. Question
text, gold, and the archived flights are not inputs to which ids are chosen:
membership is a seeded sample of in-scope ids outside the frozen pilot draw.
Editors are not called to choose ids. They are called only when the cost
report counts the tool text the flight would send.

The 2026-11-25 pilot draw stays where it is. This module writes nothing into
``pilot/``.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_CEILING
from hashlib import sha256
from pathlib import Path
import json

from tool_compression.clean_start.categories import is_memory, is_multi_turn
from tool_compression.clean_start.load import load_prereqs
from tool_compression.clean_start.pilot import build_draw, study_dir
from tool_compression.clean_start.pin import ARMS, OFFICIAL_SETTLEMENT, STEP_LIMIT, STUDY_ID
from tool_compression.clean_start.rate_card import PEAK_PER_MILLION
from tool_compression.clean_start.scope import in_scope_questions, study_categories
from tool_compression.config import LOCAL_TOKENIZER
from tool_compression.count import TiktokenCounter, dump_request

VALIDATION_SEED = "20261126"
DRAW_ALGORITHM = (
    "Drop ids in the committed pilot draw. For a memory category, keep the "
    "notetaker scenario only. random.Random('clean-start-usx-validation:"
    "{seed}:{category}').sample(sorted(remaining ids), k) when k is smaller "
    "than that list; otherwise keep the sorted list and do not sample. "
    "Python 3.12 random."
)
# k per category. A missing entry means "every remaining id".
SAMPLE_K = {
    "multiple": 64,
    "parallel_multiple": 64,
    "live_multiple": 64,
    "live_irrelevance": 64,
    "multi_turn_base": 4,
    "multi_turn_miss_func": 4,
    "multi_turn_miss_param": 4,
    "multi_turn_long_context": 4,
    "memory_kv": 4,
    "memory_vector": 4,
    "memory_rec_sum": 4,
}
# No id outside the exposed pilot draw remains.
OMITTED = {
    "live_parallel": "every in-scope id is in the exposed pilot draw",
}
MEMORY_SCENARIO = "notetaker"
MEMORY_SCENARIO_REASON = (
    "notetaker has the fewest prerequisite user-turns of the five scenarios "
    "(24, against 35 to 109). Matched prerequisites are per scenario, so the "
    "scenario is the memory bill. Chosen from the catalogue's turn counts, "
    "not from flight scores."
)

# Planning upper for a trajectory request. Each family records the c47b186c
# bill totals (prompt-token sum, request count) and that flight's 95th
# percentile prompt. memory_kv stands in for the unsent memory backends.
# The allowance is the greater of 1.5 times the mean and that percentile, so
# a family whose mean sits below its own tail is not priced at the mean.
# Steps per turn are 6, at or above the observed 90th percentile. Trajectory
# output is 900 tokens, above the 813-token maximum in those bills.
# Single-turn output is 500, above the 287-token single-turn maximum.
# All of it is priced as a peak cache miss. No cache credit.
FLIGHT_PROMPT_TOKENS = {
    "multi_turn_base": (398566, 94, 5714),
    "multi_turn_long_context": (690409, 152, 7331),
    "multi_turn_miss_func": (720463, 160, 6274),
    "multi_turn_miss_param": (620907, 117, 6739),
    "memory_kv": (2135021, 296, 12269),
}
STEPS_PER_TURN = 6
PROMPT_SCALE = Decimal("1.5")
TRAJECTORY_OUTPUT_TOKENS = 900
SINGLE_OUTPUT_TOKENS = 500
FORCE_QUIT_STEPS = STEP_LIMIT + 1  # the runner sends once more, then stops the trajectory
CEILING_USD = Decimal("20")
# Packable when the planning upper is at or under this, so the $20 cap is not the expected stop.
UPPER_LIMIT_USD = Decimal("17")

DRAW_FILE = Path("validation") / "draw.json"
COST_FILE = Path("validation") / "cost.json"


def validation_dir() -> Path:
    return study_dir() / "validation"


def _dumps(payload: dict) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def draw_sha256(draw: dict) -> str:
    return sha256(_dumps(draw).encode("utf-8")).hexdigest()


def pilot_case_ids() -> list[str]:
    """Ids frozen in the pilot draw. Read from the builder, and checked against the file."""
    built = build_draw()
    committed = json.loads((study_dir() / "pilot" / "draw.json").read_text(encoding="utf-8"))
    if committed != built:
        raise RuntimeError("pilot/draw.json does not match the pilot builder")
    return [row["case_id"] for row in built["rows"]]


def _sample(category: str, ids: list[str], k: int | None) -> tuple[list[str], str]:
    ordered = sorted(ids)
    if k is None or k >= len(ordered):
        return ordered, "all_remaining"
    if k <= 0:
        raise RuntimeError(f"{category} sample size must be positive")
    import random

    rng = random.Random(f"clean-start-usx-validation:{VALIDATION_SEED}:{category}")
    return rng.sample(ordered, k), "sample"


def build_validation_draw() -> dict:
    """The fresh draw. Deterministic. Membership uses ids and memory scenarios, not gold or scores."""
    exposed = set(pilot_case_ids())
    omitted = []
    draws = []
    scoring = []
    for category in study_categories():
        if category in OMITTED:
            omitted.append({"category": category, "reason": OMITTED[category]})
            continue
        if category not in SAMPLE_K and category not in {"live_parallel_multiple", "live_relevance"}:
            raise RuntimeError(f"{category} has no validation sample rule")
        pool = []
        for case in in_scope_questions(category):
            if case["id"] in exposed:
                continue
            if is_memory(category) and case.get("scenario") != MEMORY_SCENARIO:
                continue
            pool.append(case["id"])
        chosen, method = _sample(category, pool, SAMPLE_K.get(category))
        if len(chosen) != len(set(chosen)):
            raise RuntimeError(f"{category} draw repeated an id")
        draws.append({
            "category": category,
            "remaining": len(pool),
            "frozen": len(chosen),
            "method": method,
            "scenario": MEMORY_SCENARIO if is_memory(category) else None,
        })
        for position, case_id in enumerate(chosen):
            scoring.append({
                "case_id": case_id,
                "category": category,
                "prereq": False,
                "position": position,
            })
    prerequisites = []
    seen_memory = []
    for row in scoring:
        if is_memory(row["category"]) and row["category"] not in seen_memory:
            seen_memory.append(row["category"])
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
    order = []
    scoring_by_category: dict[str, list[dict]] = {}
    for row in scoring:
        scoring_by_category.setdefault(row["category"], []).append(row)
    for category in study_categories():
        if is_memory(category):
            continue
        order.extend(scoring_by_category.get(category, []))
    prereq_by_category: dict[str, list[dict]] = {}
    for row in prerequisites:
        prereq_by_category.setdefault(row["category"], []).append(row)
    for category in seen_memory:
        order.extend(prereq_by_category[category])
        order.extend(scoring_by_category[category])
    for index, row in enumerate(order):
        row["run_index"] = index
    draw = {
        "study": STUDY_ID,
        "official_settlement": OFFICIAL_SETTLEMENT,
        "kind": "validation",
        "seed": VALIDATION_SEED,
        "algorithm": DRAW_ALGORITHM,
        "sample_k": SAMPLE_K,
        "memory_scenario": MEMORY_SCENARIO,
        "memory_scenario_reason": MEMORY_SCENARIO_REASON,
        "replicate_u": False,
        "thinking": "off",
        "excluded_pilot_ids": len(exposed),
        "excluded_pilot_ids_sha256": sha256(
            json.dumps(sorted(exposed), ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
        "omitted_categories": omitted,
        "draws": draws,
        "order": order,
    }
    _check_draw(draw, exposed)
    return draw


def _check_draw(draw: dict, exposed: set[str]) -> None:
    ids = [row["case_id"] for row in draw["order"]]
    if len(ids) != len(set(ids)):
        raise RuntimeError("validation order repeats an id")
    if set(ids) & exposed:
        raise RuntimeError("validation draw reuses an exposed pilot id")
    if any(row["category"].startswith("web_search") for row in draw["order"]):
        raise RuntimeError("validation draw contains a web-search category")
    if any(row["category"] == "live_parallel" for row in draw["order"]):
        raise RuntimeError("validation draw contains live_parallel")
    memory_questions = [row for row in draw["order"] if row["category"].startswith("memory_") and not row["prereq"]]
    for row in memory_questions:
        case = next(case for case in in_scope_questions(row["category"]) if case["id"] == row["case_id"])
        if case.get("scenario") != MEMORY_SCENARIO:
            raise RuntimeError("validation memory question is not in the reduced scenario")
    # Memory block is last, and each category's prerequisites precede its questions.
    seen_scoring_memory = False
    last_memory = None
    for row in draw["order"]:
        if not row["category"].startswith("memory_"):
            if seen_scoring_memory or last_memory is not None:
                raise RuntimeError("a non-memory case follows the memory block")
            continue
        if row["prereq"]:
            if seen_scoring_memory and row["category"] == last_memory:
                raise RuntimeError("a prerequisite follows its own category's questions")
            seen_scoring_memory = False
        else:
            seen_scoring_memory = True
        last_memory = row["category"]


def load_committed_draw() -> dict:
    path = study_dir() / DRAW_FILE
    return json.loads(path.read_text(encoding="utf-8"))


def select_validation_cases() -> list[dict]:
    """Cases in frozen run order. Raises when the file and the builder disagree."""
    built = build_validation_draw()
    committed = load_committed_draw()
    if committed != built:
        raise RuntimeError("validation/draw.json does not match the validation builder")
    return cases_for_draw(committed)


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
            raise RuntimeError(f"validation id is not in the loaded questions: {row['case_id']}")
        if bool(case.get("prereq")) != bool(row["prereq"]):
            raise RuntimeError(f"validation prereq flag disagrees for {row['case_id']}")
        chosen.append(case)
    return chosen


def _allowance(category: str) -> int:
    family = "memory_kv" if category.startswith("memory_") else category
    tokens, requests, percentile = FLIGHT_PROMPT_TOKENS[family]
    scaled = (Decimal(tokens) / Decimal(requests)) * PROMPT_SCALE
    scaled_tokens = int(scaled.to_integral_value(ROUND_CEILING))
    return max(scaled_tokens, percentile)


def _request_usd(prompt_tokens: int, output_tokens: int) -> Decimal:
    return (
        Decimal(prompt_tokens) * PEAK_PER_MILLION["cache_miss"]
        + Decimal(output_tokens) * PEAK_PER_MILLION["output"]
    ) / Decimal(1_000_000)


def _message_text(case: dict) -> str:
    from tool_compression.clean_start.runner import turn_messages

    parts = []
    for item in turn_messages(case, 0):
        content = item.get("content")
        if isinstance(content, str):
            parts.append(content)
    return "\n".join(parts)


def _usd(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.000001")))


def validation_report(counter=None) -> dict:
    """Floor and planning upper for the frozen draw, in peak USD, all cache-miss.

    The floor counts the turn-0 message text and the tools array once per slot.
    The planning upper prices trajectories at ``STEPS_PER_TURN`` requests per
    user-turn and the flight-scaled prompt allowance, and adds one force-quit
    turn (21 requests instead of 6) per memory category per arm. The structural
    figure prices every trajectory turn at the runner's 21-request cap; it is
    not the number the flight is sized to.
    """
    from tool_compression.clean_start.runner import arm_tools

    draw = build_validation_draw()
    cases = cases_for_draw(draw)
    counter = counter or TiktokenCounter(LOCAL_TOKENIZER)
    floor_tokens = 0
    single_upper = Decimal("0")
    trajectory_upper = Decimal("0")
    structural = Decimal("0")
    by_category: dict[str, dict] = {}
    for case in cases:
        category = case["category"]
        turns = len(case["question"])
        row = by_category.setdefault(category, {
            "scoring": 0, "prerequisites": 0, "turns": 0, "first_request_tokens": 0,
        })
        if case.get("prereq"):
            row["prerequisites"] += 1
        else:
            row["scoring"] += 1
        row["turns"] += turns
        local = []
        for arm in ARMS:
            tokens = counter.count(_message_text(case)) + counter.count(
                dump_request(arm_tools(case["function"], case["category"], arm))
            )
            local.append(tokens)
        floor_tokens += sum(local)
        row["first_request_tokens"] += sum(local)
        if is_multi_turn(category) or is_memory(category):
            allowance = _allowance(category)
            requests = turns * STEPS_PER_TURN
            trajectory_upper += _request_usd(allowance, TRAJECTORY_OUTPUT_TOKENS) * requests * len(ARMS)
            structural += _request_usd(allowance, TRAJECTORY_OUTPUT_TOKENS) * (turns * FORCE_QUIT_STEPS) * len(ARMS)
        else:
            for tokens in local:
                single_upper += _request_usd(tokens, SINGLE_OUTPUT_TOKENS)
                structural += _request_usd(tokens, SINGLE_OUTPUT_TOKENS)
    memory_categories = [category for category in by_category if category.startswith("memory_")]
    contingency = Decimal("0")
    for category in memory_categories:
        extra = FORCE_QUIT_STEPS - STEPS_PER_TURN
        contingency += _request_usd(_allowance(category), TRAJECTORY_OUTPUT_TOKENS) * extra * len(ARMS)
    floor_usd = _request_usd(floor_tokens, 0)
    upper = single_upper + trajectory_upper + contingency
    if upper > UPPER_LIMIT_USD:
        raise RuntimeError(f"validation planning upper {upper} exceeds the {UPPER_LIMIT_USD} pack limit")
    scoring = sum(1 for case in cases if not case.get("prereq"))
    prereq = len(cases) - scoring
    report = {
        "study": STUDY_ID,
        "official_settlement": OFFICIAL_SETTLEMENT,
        "kind": "validation",
        "seed": VALIDATION_SEED,
        "draw_sha256": draw_sha256(draw),
        "thinking": "off",
        "replicate_u": False,
        "arms": list(ARMS),
        "band": "peak",
        "prices_per_million": {
            "cache_miss": str(PEAK_PER_MILLION["cache_miss"]),
            "output": str(PEAK_PER_MILLION["output"]),
        },
        "cache_credit": "none; every prompt token is priced as a miss",
        "cases": {
            "conversations": len(cases),
            "scoring": scoring,
            "prerequisites": prereq,
            "by_category": by_category,
        },
        "slots": {
            "total": len(cases) * len(ARMS),
            "scoring": scoring * len(ARMS),
            "prerequisites": prereq * len(ARMS),
        },
        "order": "single-turn, then multi-turn, then each memory category's prerequisites before its questions",
        "first_request_floor_tokens": floor_tokens,
        "first_request_floor_usd": _usd(floor_usd),
        "first_request_floor": (
            "Local o200k_base tokens of the turn-0 message text plus the tools array, "
            "summed over the four arms, priced as peak cache misses, with no output and "
            "no chat template. The pinned memory instruction and core-memory text are not "
            "included. This is a lower bound on prompt spend if every slot ended after one "
            "request, not a forecast."
        ),
        "planning_upper_usd": _usd(upper),
        "planning_upper_parts_usd": {
            "single_turn": _usd(single_upper),
            "trajectories_at_six_steps_per_turn": _usd(trajectory_upper),
            "memory_force_quit_contingency": _usd(contingency),
        },
        "planning_upper": (
            f"Peak prices, no cache credit. A single-turn slot is its local first-request "
            f"tokens plus {SINGLE_OUTPUT_TOKENS} output tokens. A trajectory turn is "
            f"{STEPS_PER_TURN} requests at the greater of 1.5 times the mean prompt and the "
            f"95th percentile prompt of that family in the c47b186c bills, plus "
            f"{TRAJECTORY_OUTPUT_TOKENS} output tokens. One extra "
            f"force-quit turn ({FORCE_QUIT_STEPS} requests instead of {STEPS_PER_TURN}) is "
            f"added per memory category per arm. Sized to stay at or under ${UPPER_LIMIT_USD} "
            f"so the ${CEILING_USD} cap is not the way the run is expected to end."
        ),
        "structural_cap_usd": _usd(structural),
        "structural_cap": (
            "The same allowances with every trajectory turn taking the runner cap of "
            f"{FORCE_QUIT_STEPS} requests. That is the tail if the model never finishes a "
            "turn. It is not the planning number. The hard ceiling still stops the run."
        ),
        "ceiling_usd": str(CEILING_USD),
        "pack_limit_usd": str(UPPER_LIMIT_USD),
        "prompt_allowance_tokens": {
            category: _allowance(category)
            for category in sorted(by_category)
            if category.startswith("memory_") or category.startswith("multi_turn_")
        },
    }
    return report


def write_validation_files() -> dict:
    """Write the draw and the cost report. Does not touch the pilot draw."""
    root = validation_dir()
    root.mkdir(parents=True, exist_ok=True)
    draw = build_validation_draw()
    (root / "draw.json").write_text(_dumps(draw), encoding="utf-8")
    report = validation_report()
    if report["draw_sha256"] != draw_sha256(draw):
        raise RuntimeError("validation cost report hashed a different draw")
    (root / "cost.json").write_text(_dumps(report), encoding="utf-8")
    return {
        "conversations": report["cases"]["conversations"],
        "slots": report["slots"]["total"],
        "planning_upper_usd": report["planning_upper_usd"],
        "first_request_floor_usd": report["first_request_floor_usd"],
    }


def load_committed_cost() -> dict:
    report = json.loads((study_dir() / COST_FILE).read_text(encoding="utf-8"))
    draw_bytes = (study_dir() / DRAW_FILE).read_bytes()
    if report["draw_sha256"] != sha256(draw_bytes).hexdigest():
        raise RuntimeError("validation/cost.json does not match validation/draw.json")
    if Decimal(report["planning_upper_usd"]) > UPPER_LIMIT_USD:
        raise RuntimeError("committed validation upper exceeds the pack limit")
    return report
