"""Study population: multi-tool U catalogues, minus billable web search.

A scoring question is in scope when the model-facing U catalogue has more
than one tool. That list is the OpenAI tool entries ``compile_case`` hands
to the editors after ``load_questions`` and the official language hint.
Official simple sets stay out of the study even if a question were
multi-tool. ``web_search_base`` and ``web_search_no_snippet`` stay out
because every search calls billable SerpAPI, which is outside the DeepSeek
ceiling. Their prompts stay in the vendored BFCL package. Memory backends
stay in the study; their Python libraries and the MiniLM weight file are
local, not a billable service. Memory prerequisites are not scoring questions.

``scope.json`` is the checked census. The runner applies this rule to the
loaded questions; it does not keep a second id list in code.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import json
import statistics

from tool_compression.clean_start.categories import (
    ALL_SCORING_CATEGORIES,
    category_from_id,
)
from tool_compression.clean_start.load import load_prereqs, load_questions
from tool_compression.clean_start.pin import OFFICIAL_SETTLEMENT, STUDY_ID
from tool_compression.clean_start.prepare import model_facing_tools

OFFICIAL_SIMPLE_CATEGORIES = (
    "simple_python",
    "simple_java",
    "simple_javascript",
    "live_simple",
)

# Both web sets are multi-tool. They leave the study because the pinned
# executor calls SerpAPI, a billable service outside the DeepSeek ceiling.
# This is not a redraw of any other category's questions.
EXCLUDED_EXTERNAL_SERVICE_CATEGORIES = (
    "web_search_base",
    "web_search_no_snippet",
)
EXTERNAL_SERVICE_EXCLUSION_REASON = (
    "excluded: web search calls billable SerpAPI outside the DeepSeek ceiling; "
    "the vendored prompts stay in the BFCL package"
)

# Examples measured while scoping. The census builder refuses a different count.
CHECKED_EXAMPLES = (
    ("parallel_104", 1),
    ("parallel_134", 1),
    ("irrelevance_55", 1),
    ("irrelevance_165", 1),
    ("live_parallel_12-8-0", 1),
    ("live_parallel_8-4-0", 1),
    ("live_parallel_6-3-0", 2),
    ("live_parallel_7-3-1", 2),
    ("live_irrelevance_201-32-14", 1),
    ("live_irrelevance_522-159-0", 1),
    ("live_irrelevance_817-314-1", 1),
    ("live_irrelevance_106-5-0", 2),
    ("live_irrelevance_125-11-0", 3),
    ("live_irrelevance_120-9-0", 0),
    ("live_irrelevance_121-9-1", 0),
    ("live_irrelevance_122-9-2", 0),
    ("live_irrelevance_123-9-3", 0),
    ("live_relevance_15-15-0", 1),
    ("live_relevance_7-7-0", 2),
    ("live_relevance_6-6-0", 4),
)

FILTER_EXAMPLES = {
    "live_parallel": {
        "one_tool": ("live_parallel_12-8-0", "live_parallel_8-4-0"),
        "multi_tool": ("live_parallel_6-3-0", "live_parallel_7-3-1"),
    },
    "live_irrelevance": {
        "one_tool": (
            "live_irrelevance_201-32-14",
            "live_irrelevance_522-159-0",
            "live_irrelevance_817-314-1",
        ),
        "multi_tool": ("live_irrelevance_106-5-0", "live_irrelevance_125-11-0"),
    },
    "live_relevance": {
        "one_tool": ("live_relevance_15-15-0",),
        "multi_tool": ("live_relevance_7-7-0", "live_relevance_6-6-0"),
    },
}

UNSCOPE_PACKAGE = {
    "pull_request": 24,
    "url": "https://github.com/jacky-wong9273/tool-compression/pull/24",
    "branch": "cursor/clean-start-usx-14e3",
    "tip": "c1df4bbf439151abad2ed79b103d401a61443412",
    "base": "1ab2b5d042b7d8fadbb0c922c51201ae6fc75c21",
    "scoring_categories": 22,
    "pilot_cases": 66,
}


def scope_path() -> Path:
    return Path(__file__).resolve().parents[3] / "studies" / "clean-start-usx" / "scope.json"


def u_tool_count(case: dict) -> int:
    """Tools in the U catalogue the editors see.

    One count per function-document entry, which is one OpenAI tool entry
    after the official language hint. Parameters and response-schema fields
    are not tools. The caller passes the initial catalogue: held-out
    ``miss_func`` docs are already absent, and ``excluded_function`` names
    that the loader left in that list are still present.
    """
    functions = list(case.get("function") or [])
    tools = model_facing_tools(functions, case["category"])
    if len(tools) != len(functions):
        raise RuntimeError(
            f"{case.get('id')} has {len(functions)} function documents "
            f"and {len(tools)} OpenAI tool entries"
        )
    return len(tools)


def question_in_scope(case: dict) -> bool:
    """Scoring question with a multi-tool U catalogue, outside the exclusions."""
    if case.get("prereq"):
        return False
    category = case.get("category")
    if category not in ALL_SCORING_CATEGORIES:
        return False
    if category in OFFICIAL_SIMPLE_CATEGORIES or category in EXCLUDED_EXTERNAL_SERVICE_CATEGORIES:
        return False
    return u_tool_count(case) > 1


@lru_cache(maxsize=1)
def _loaded_questions() -> dict[str, tuple[dict, ...]]:
    return {
        category: tuple(load_questions(category))
        for category in ALL_SCORING_CATEGORIES
    }


@lru_cache(maxsize=1)
def _tool_counts() -> dict[str, dict[str, int]]:
    counted = {}
    for category, cases in _loaded_questions().items():
        counted[category] = {case["id"]: u_tool_count(case) for case in cases}
    return counted


def study_categories() -> tuple[str, ...]:
    """Scoring categories that have at least one in-scope question."""
    counts = _tool_counts()
    kept = []
    for category in ALL_SCORING_CATEGORIES:
        if category in OFFICIAL_SIMPLE_CATEGORIES or category in EXCLUDED_EXTERNAL_SERVICE_CATEGORIES:
            continue
        if any(count > 1 for count in counts[category].values()):
            kept.append(category)
    return tuple(kept)


def in_scope_questions(category: str) -> list[dict]:
    if category not in ALL_SCORING_CATEGORIES:
        raise ValueError(f"{category} is not a scoring category")
    if category in OFFICIAL_SIMPLE_CATEGORIES or category in EXCLUDED_EXTERNAL_SERVICE_CATEGORIES:
        return []
    counts = _tool_counts()[category]
    return [
        case
        for case in _loaded_questions()[category]
        if counts[case["id"]] > 1
    ]


def require_recorded_scope() -> dict:
    """Refuse a census file that disagrees with the loaded questions."""
    recorded = load_scope()
    live = build_scope_document()
    if recorded != live:
        raise RuntimeError("scope.json does not match the loaded multi-tool census")
    return recorded


def select_full_run_cases() -> list[dict]:
    """In-scope scoring questions, with memory prerequisites sent first.

    Prerequisites are not study questions. A full memory score still needs
    those conversations before the in-scope memory questions. The pilot does
    not include them.
    """
    require_recorded_scope()
    cases: list[dict] = []
    for category in study_categories():
        cases.extend(load_prereqs(category))
        cases.extend(in_scope_questions(category))
    return cases


def _median(values: list[int]) -> int | float:
    value = statistics.median(values)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _ids_with_count(counts: dict[str, int], predicate) -> list[str]:
    return [case_id for case_id, count in counts.items() if predicate(count)]


def _examples(category: str, counts: dict[str, int], kind: str) -> list[str]:
    preferred = FILTER_EXAMPLES.get(category, {}).get(kind, ())
    if kind == "one_tool":
        allowed = {case_id for case_id, count in counts.items() if count == 1}
    elif kind == "multi_tool":
        allowed = {case_id for case_id, count in counts.items() if count > 1}
    else:
        allowed = {case_id for case_id, count in counts.items() if count == 0}
    chosen = [case_id for case_id in preferred if case_id in allowed]
    if len(chosen) != len(preferred):
        missing = [case_id for case_id in preferred if case_id not in allowed]
        raise RuntimeError(f"{category} {kind} examples are not in that bucket: {missing}")
    return chosen


def _census_row(category: str) -> dict:
    counts = _tool_counts()[category]
    values = list(counts.values())
    histogram_map: dict[int, int] = {}
    for count in values:
        histogram_map[count] = histogram_map.get(count, 0) + 1
    zero_ids = _ids_with_count(counts, lambda count: count == 0)
    one_ids = _ids_with_count(counts, lambda count: count == 1)
    multi_ids = _ids_with_count(counts, lambda count: count > 1)
    if category in OFFICIAL_SIMPLE_CATEGORIES:
        disposition = "dropped"
        if multi_ids:
            reason = "official simple set; multi-tool questions remain excluded"
        elif len(one_ids) == len(values) and not zero_ids:
            reason = "official simple set; census confirms every question has one tool"
        else:
            reason = "official simple set; excluded regardless of tool count"
        in_scope_ids: list[str] = []
    elif category in EXCLUDED_EXTERNAL_SERVICE_CATEGORIES:
        disposition = "dropped"
        reason = EXTERNAL_SERVICE_EXCLUSION_REASON
        in_scope_ids = []
    elif not multi_ids:
        disposition = "dropped"
        reason = "no question has more than one tool in the loaded U catalogue"
        in_scope_ids = []
    elif len(multi_ids) == len(values):
        disposition = "kept"
        reason = "every question has more than one tool in the loaded U catalogue"
        in_scope_ids = multi_ids
    else:
        disposition = "filtered"
        reason = "mixed; in scope only when the loaded U catalogue has more than one tool"
        in_scope_ids = multi_ids
    return {
        "category": category,
        "questions": len(values),
        "zero_tool": len(zero_ids),
        "one_tool": len(one_ids),
        "multi_tool": len(multi_ids),
        "in_scope": len(in_scope_ids),
        "min_tools": min(values),
        "max_tools": max(values),
        "median_tools": _median(values),
        "tool_count_histogram": [
            {"tools": count, "questions": histogram_map[count]}
            for count in sorted(histogram_map)
        ],
        "disposition": disposition,
        "reason": reason,
        "in_scope_ids": in_scope_ids,
        "zero_tool_ids": zero_ids,
    }


def _checked_examples() -> list[dict]:
    rows = []
    for case_id, expected in CHECKED_EXAMPLES:
        category = category_from_id(case_id)
        measured = _tool_counts()[category][case_id]
        if measured != expected:
            raise RuntimeError(f"{case_id} has {measured} tools, expected {expected}")
        case = next(item for item in _loaded_questions()[category] if item["id"] == case_id)
        rows.append({
            "id": case_id,
            "category": category,
            "tools": measured,
            "in_scope": question_in_scope(case),
        })
    return rows


def _memory_prerequisites() -> dict:
    backends = {}
    for category in ("memory_kv", "memory_vector", "memory_rec_sum"):
        prereqs = load_prereqs(category)
        counts = [u_tool_count(case) for case in prereqs]
        backends[category] = {
            "conversations": len(prereqs),
            "min_tools": min(counts),
            "max_tools": max(counts),
            "in_study_population": False,
        }
    return {
        "in_study_population": False,
        "reason": (
            "Memory prerequisites are not scoring questions. "
            "They are excluded from the census population, the pilot, and the in-scope id lists. "
            "The full runner still sends them before the in-scope memory questions, "
            "because a full memory score needs those conversations."
        ),
        "backends": backends,
    }


def build_scope_document() -> dict:
    """Census every scoring question and list the in-scope ids."""
    census = [_census_row(category) for category in ALL_SCORING_CATEGORIES]
    keep = [row["category"] for row in census if row["disposition"] != "dropped"]
    drop = [row["category"] for row in census if row["disposition"] == "dropped"]
    mixed = []
    in_scope_ids = {}
    official_simple_multi_tool_ids = [
        case_id
        for category in OFFICIAL_SIMPLE_CATEGORIES
        for case_id, count in _tool_counts()[category].items()
        if count > 1
    ]
    for row in census:
        if row["disposition"] == "dropped":
            continue
        in_scope_ids[row["category"]] = list(row["in_scope_ids"])
        if row["disposition"] != "filtered":
            continue
        counts = _tool_counts()[row["category"]]
        mixed.append({
            "category": row["category"],
            "questions": row["questions"],
            "in_scope": row["in_scope"],
            "out_of_scope": row["questions"] - row["in_scope"],
            "zero_tool": row["zero_tool"],
            "one_tool": row["one_tool"],
            "multi_tool": row["multi_tool"],
            "zero_tool_examples": list(row["zero_tool_ids"]),
            "one_tool_examples": _examples(row["category"], counts, "one_tool"),
            "multi_tool_examples": _examples(row["category"], counts, "multi_tool"),
            "out_of_scope_ids": [
                case_id for case_id, count in counts.items() if count <= 1
            ],
        })
    surprises = []
    empty = next(row for row in census if row["category"] == "live_irrelevance")
    if empty["zero_tool"]:
        surprises.append({
            "kind": "empty_loaded_catalogue",
            "category": "live_irrelevance",
            "count": empty["zero_tool"],
            "ids": list(empty["zero_tool_ids"]),
            "note": (
                "The official prompt function list is empty. "
                "These questions are not one-tool catalogues and are not in scope."
            ),
        })
    short = [row for row in census if 0 < row["in_scope"] < 3]
    for row in short:
        surprises.append({
            "kind": "fewer_than_three_in_scope",
            "category": row["category"],
            "in_scope": row["in_scope"],
            "ids": list(row["in_scope_ids"]),
            "note": (
                "The pilot freezes every in-scope id in sorted order. "
                "It does not call sample and it does not use a new seed."
            ),
        })
    public_census = []
    for row in census:
        public = dict(row)
        public.pop("in_scope_ids")
        public.pop("zero_tool_ids")
        public_census.append(public)
    in_scope_questions_count = sum(len(ids) for ids in in_scope_ids.values())
    scoring_questions = sum(row["questions"] for row in census)
    return {
        "study": STUDY_ID,
        "official_settlement": OFFICIAL_SETTLEMENT,
        "rule": {
            "in_scope": (
                "A scoring question is in scope iff len(tools) > 1 on the loaded U "
                "catalogue, the category is not an official simple set, and the "
                "category is not web_search_base or web_search_no_snippet."
            ),
            "excluded_external_service": list(EXCLUDED_EXTERNAL_SERVICE_CATEGORIES),
            "excluded_external_service_reason": EXTERNAL_SERVICE_EXCLUSION_REASON,
            "tool": (
                "One function-document entry in the initial model-facing U catalogue, "
                "which is one OpenAI tool entry after official load and the language hint. "
                "Parameters, response-schema fields, and holdout documents absent from "
                "that initial list are not counted. excluded_function entries that remain "
                "in the initial list are counted."
            ),
            "loader": "load_questions, then model_facing_tools. compile_case edits that same list.",
            "official_simple_sets": list(OFFICIAL_SIMPLE_CATEGORIES),
            "memory_prerequisites": "excluded; they are not scoring questions",
        },
        "unscope_package": dict(UNSCOPE_PACKAGE),
        "scoring_questions": scoring_questions,
        "in_scope_questions": in_scope_questions_count,
        "out_of_scope_questions": scoring_questions - in_scope_questions_count,
        "keep": keep,
        "drop": drop,
        "mixed": mixed,
        "surprises": surprises,
        "official_simple_multi_tool_ids": official_simple_multi_tool_ids,
        "checked_examples": _checked_examples(),
        "memory_prerequisites": _memory_prerequisites(),
        "census": public_census,
        "in_scope_ids": in_scope_ids,
    }


def load_scope() -> dict:
    payload = json.loads(scope_path().read_text(encoding="utf-8"))
    if payload.get("study") != STUDY_ID:
        raise RuntimeError("scope.json is not the clean-start study census")
    if payload.get("official_settlement") is not False:
        raise RuntimeError("scope.json must keep official_settlement false")
    return payload


def write_scope(path: Path | None = None) -> dict:
    document = build_scope_document()
    destination = path or scope_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return document
