"""Scoring categories copied from the pinned BFCL ``category_mapping.py``.

``format_sensitivity`` is non-scoring. The commented-out exec, REST, SQL,
chatable, and composite multi-turn names are out of scope, as is the
``unused_datasets`` directory.
"""

from __future__ import annotations

NON_LIVE_CATEGORY = (
    "simple_python",
    "simple_java",
    "simple_javascript",
    "multiple",
    "parallel",
    "parallel_multiple",
    "irrelevance",
)
LIVE_CATEGORY = (
    "live_simple",
    "live_multiple",
    "live_parallel",
    "live_parallel_multiple",
    "live_irrelevance",
    "live_relevance",
)
MULTI_TURN_CATEGORY = (
    "multi_turn_base",
    "multi_turn_miss_func",
    "multi_turn_miss_param",
    "multi_turn_long_context",
)
MEMORY_BACKENDS = ("kv", "vector", "rec_sum")
MEMORY_CATEGORY = tuple(f"memory_{backend}" for backend in MEMORY_BACKENDS)
MEMORY_SCENARIOS = ("student", "customer", "finance", "healthcare", "notetaker")
WEB_SEARCH_CATEGORY = ("web_search_base", "web_search_no_snippet")

# Official BFCL scoring categories. The clean-start study population is the
# multi-tool subset in ``tool_compression.clean_start.scope``, not this tuple.
ALL_SCORING_CATEGORIES = (
    NON_LIVE_CATEGORY + LIVE_CATEGORY + MULTI_TURN_CATEGORY + MEMORY_CATEGORY + WEB_SEARCH_CATEGORY
)

OUT_OF_SCOPE = (
    "format_sensitivity",
    "exec_simple",
    "exec_parallel",
    "exec_multiple",
    "exec_parallel_multiple",
    "rest",
    "sql",
    "chatable",
    "multi_turn_composite",
)

FUNC_DOC_FILES = {
    "GorillaFileSystem": "gorilla_file_system.json",
    "MathAPI": "math_api.json",
    "MessageAPI": "message_api.json",
    "TwitterAPI": "posting_api.json",
    "TicketAPI": "ticket_api.json",
    "TradingBot": "trading_bot.json",
    "TravelAPI": "travel_booking.json",
    "VehicleControlAPI": "vehicle_control.json",
    "WebSearchAPI": "web_search.json",
    "MemoryAPI_kv": "memory_kv.json",
    "MemoryAPI_vector": "memory_vector.json",
    "MemoryAPI_rec_sum": "memory_rec_sum.json",
}

PROMPT_FILES = {
    "simple_python": "BFCL_v4_simple_python.json",
    "simple_java": "BFCL_v4_simple_java.json",
    "simple_javascript": "BFCL_v4_simple_javascript.json",
    "multiple": "BFCL_v4_multiple.json",
    "parallel": "BFCL_v4_parallel.json",
    "parallel_multiple": "BFCL_v4_parallel_multiple.json",
    "irrelevance": "BFCL_v4_irrelevance.json",
    "live_simple": "BFCL_v4_live_simple.json",
    "live_multiple": "BFCL_v4_live_multiple.json",
    "live_parallel": "BFCL_v4_live_parallel.json",
    "live_parallel_multiple": "BFCL_v4_live_parallel_multiple.json",
    "live_irrelevance": "BFCL_v4_live_irrelevance.json",
    "live_relevance": "BFCL_v4_live_relevance.json",
    "multi_turn_base": "BFCL_v4_multi_turn_base.json",
    "multi_turn_miss_func": "BFCL_v4_multi_turn_miss_func.json",
    "multi_turn_miss_param": "BFCL_v4_multi_turn_miss_param.json",
    "multi_turn_long_context": "BFCL_v4_multi_turn_long_context.json",
    "memory": "BFCL_v4_memory.json",
    "web_search": "BFCL_v4_web_search.json",
}


def is_java(category: str) -> bool:
    return "java" in category and "javascript" not in category


def is_javascript(category: str) -> bool:
    return "javascript" in category


def is_multi_turn(category: str) -> bool:
    return category.startswith("multi_turn")


def is_memory(category: str) -> bool:
    return category.startswith("memory_")


def is_web_search(category: str) -> bool:
    return category.startswith("web_search")


def is_agentic(category: str) -> bool:
    return is_memory(category) or is_web_search(category)


def is_trajectory(category: str) -> bool:
    return is_multi_turn(category) or is_agentic(category)


def category_from_id(case_id: str) -> str:
    """Match BFCL ``extract_test_category_from_id`` for scoring ids."""
    return case_id.rsplit("_", 1)[0]


def result_group(category: str) -> str:
    """Match BFCL result directories, including memory backends."""
    base = category.replace("_prereq", "")
    if base.startswith("memory_"):
        return f"agentic/memory/{base[len('memory_'):]}"
    if base.startswith("web_search"):
        return "agentic"
    if base.startswith("multi_turn"):
        return "multi_turn"
    if base.startswith("live"):
        return "live"
    return "non_live"
