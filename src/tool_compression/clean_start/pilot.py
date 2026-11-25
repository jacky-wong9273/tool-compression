"""Frozen three-case draw and the inspectable U/S/X/SX renders.

The draw is local. Nothing here contacts a provider.
"""

from __future__ import annotations

from pathlib import Path
import json
import random

from tool_compression.clean_start.categories import (
    ALL_SCORING_CATEGORIES,
    is_java,
    is_javascript,
    is_memory,
    is_multi_turn,
    is_trajectory,
    is_web_search,
)
from tool_compression.clean_start.load import load_prereqs, load_questions
from tool_compression.clean_start.pin import ARMS, OFFICIAL_SETTLEMENT, STUDY_ID
from tool_compression.clean_start.prepare import model_facing_tools, response_description_pointers
from tool_compression.clean_start.render import render_tools

PILOT_SEED = 20261125
PILOT_K = 3
DRAW_ALGORITHM = (
    "random.Random('clean-start-usx:{seed}:{category}').sample(sorted(question_ids), 3)"
)


def study_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "studies" / "clean-start-usx"


def catalogue_limitations(category: str, functions: list[dict]) -> list[str]:
    notes = [
        "language_hint_is_official_preparation",
        "x_qualifies_under_the_language_hint",
    ]
    if is_java(category) or is_javascript(category):
        notes.append("java_js_parameters_stringified_before_edit")
    if response_description_pointers(functions):
        notes.append("response_descriptions_left_unmodified")
    if is_multi_turn(category):
        notes.append("excluded_function_left_in_catalogue")
        notes.append("trajectory_requires_official_backend")
    if category == "multi_turn_miss_func":
        notes.append("miss_func_holdout_absent_from_initial_tools")
    if category == "multi_turn_long_context":
        notes.append("long_context_payload_left_unmodified")
    if is_memory(category):
        notes.extend([
            "memory_prereq_required_for_a_full_score",
            "memory_instruction_prompt_not_invented",
            "agentic_format_prompt_left_unmodified",
            "trajectory_requires_official_backend",
        ])
    if is_web_search(category):
        notes.extend([
            "snippet_flag_is_execution_setting",
            "agentic_format_prompt_left_unmodified",
            "trajectory_requires_official_backend",
        ])
    if is_trajectory(category) and "trajectory_requires_official_backend" not in notes:
        notes.append("trajectory_requires_official_backend")
    return notes


def compile_case(case: dict) -> dict:
    limitations = catalogue_limitations(case["category"], case["function"])
    held = [
        doc.get("name")
        for docs in case.get("held_out", {}).values()
        for doc in docs
    ]
    base = {
        "case_id": case["id"],
        "category": case["category"],
        "prereq": bool(case.get("prereq")),
        "limitations": limitations,
        "held_out_functions": held,
        "excluded_function_present": list(case.get("excluded_function") or []),
    }
    try:
        tools = model_facing_tools(case["function"], case["category"])
    except (KeyError, TypeError, ValueError) as exc:
        return {
            **base,
            "editable": False,
            "sendable": False,
            "unmodified_reason": f"conversion_failed: {exc.__class__.__name__}: {exc}",
            "arms": None,
            "changes": [],
        }
    try:
        rendered = render_tools(tools)
    except (KeyError, TypeError, ValueError, RuntimeError) as exc:
        identical = {arm: tools for arm in ARMS}
        return {
            **base,
            "editable": False,
            "sendable": True,
            "unmodified_reason": f"editor_failed: {exc.__class__.__name__}: {exc}",
            "arms": identical,
            "changes": [],
        }
    return {
        **base,
        "editable": True,
        "sendable": True,
        "unmodified_reason": None,
        "arms": rendered["arms"],
        "changes": rendered["changes"],
    }


def draw_category(category: str, case_ids: list[str], *, seed: int = PILOT_SEED) -> list[str]:
    population = sorted(case_ids)
    if len(population) < PILOT_K:
        raise RuntimeError(f"{category} has {len(population)} questions")
    rng = random.Random(f"clean-start-usx:{seed}:{category}")
    return rng.sample(population, PILOT_K)


def build_draw(seed: int = PILOT_SEED) -> dict:
    rows = []
    for category in ALL_SCORING_CATEGORIES:
        questions = load_questions(category)
        chosen = draw_category(category, [case["id"] for case in questions], seed=seed)
        for position, case_id in enumerate(chosen):
            rows.append({
                "category": category,
                "case_id": case_id,
                "position": position,
            })
    return {
        "study": STUDY_ID,
        "official_settlement": OFFICIAL_SETTLEMENT,
        "seed": seed,
        "k": PILOT_K,
        "algorithm": DRAW_ALGORITHM,
        "population": "scoring questions only; memory prerequisites are excluded",
        "categories": list(ALL_SCORING_CATEGORIES),
        "rows": rows,
    }


def render_document(case: dict) -> dict:
    compiled = compile_case(case)
    document = {
        "study": STUDY_ID,
        "official_settlement": OFFICIAL_SETTLEMENT,
        "case_id": compiled["case_id"],
        "category": compiled["category"],
        "editable": compiled["editable"],
        "sendable": compiled["sendable"],
        "unmodified_reason": compiled["unmodified_reason"],
        "limitations": compiled["limitations"],
        "held_out_functions": compiled["held_out_functions"],
        "excluded_function_present": compiled["excluded_function_present"],
        "changes": compiled["changes"],
        "arms": compiled["arms"],
    }
    if set(document["arms"] or {}) - set(ARMS):
        raise RuntimeError("rendered arms must be U, S, X, and SX")
    return document


def coverage() -> dict:
    """Edit every scoring question and record what stayed unmodified."""
    categories = {}
    unsendable = 0
    for category in ALL_SCORING_CATEGORIES:
        questions = load_questions(category)
        changed_s = 0
        cued_x = 0
        changed_sx = 0
        failed = 0
        reasons = []
        notes = []
        for case in questions:
            compiled = compile_case(case)
            notes = compiled["limitations"]
            if not compiled["sendable"]:
                failed += 1
                unsendable += 1
                reasons.append(compiled["unmodified_reason"])
                continue
            arms = compiled["arms"]
            if arms["S"] != arms["U"]:
                changed_s += 1
            if arms["X"] != arms["U"]:
                cued_x += 1
            if arms["SX"] != arms["U"]:
                changed_sx += 1
            if compiled["unmodified_reason"]:
                reasons.append(compiled["unmodified_reason"])
        categories[category] = {
            "questions": len(questions),
            "prereqs": len(load_prereqs(category)) if is_memory(category) else 0,
            "sendable": len(questions) - failed,
            "unsendable": failed,
            "s_cases_different_from_u": changed_s,
            "x_cases_different_from_u": cued_x,
            "sx_cases_different_from_u": changed_sx,
            "limitations": notes,
            "unmodified_reasons": reasons[:8],
        }
    return {
        "study": STUDY_ID,
        "official_settlement": OFFICIAL_SETTLEMENT,
        "unsendable": unsendable,
        "categories": categories,
    }


def _dump(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def freeze() -> dict:
    """Write the committed pilot draw, renders, and limitation record."""
    root = study_dir()
    draw = build_draw()
    _dump(root / "pilot" / "draw.json", draw)
    by_category: dict[str, dict[str, dict]] = {}
    for category in ALL_SCORING_CATEGORIES:
        for case in load_questions(category):
            by_category.setdefault(category, {})[case["id"]] = case
    for row in draw["rows"]:
        document = render_document(by_category[row["category"]][row["case_id"]])
        _dump(root / "pilot" / "rendered" / row["category"] / f"{row['case_id']}.json", document)
    record = coverage()
    _dump(root / "limitations.json", record)
    return {"draw": len(draw["rows"]), "unsendable": record["unsendable"]}
