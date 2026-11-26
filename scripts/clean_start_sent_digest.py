"""Digests of what the clean-start editors send, for a flown commit or the current tip.

Standalone on purpose: it imports whichever ``tool_compression`` is first on
``PYTHONPATH``, so the same script digests the editors at a flown commit (from a
``git worktree`` of that commit) or at the current tip. No provider call, no key.

    git worktree add --detach /tmp/usx-c47b186c c47b186c6004e69840db3537ebe532dc22f638a8
    export CLEAN_START_BFCL_ROOT=/path/to/gorilla PYTHONPATH=/tmp/usx-c47b186c/src
    python scripts/clean_start_sent_digest.py conversations > sent_renders_c47b186c.json
    python scripts/clean_start_sent_digest.py population > population_c47b186c.json

``conversations``: per pilot conversation (41 scoring cases and 54 matched memory
prerequisites), arm and catalogue state (initial, then after each held-out
batch), the tools hash in the runner's journal formula, so it can be compared
with ``attempts.jsonl`` byte for byte, plus local token counts.

``validation``: the same, for the 328 conversations of the frozen validation
draw (313 scoring cases and 15 notetaker prerequisites).

``population``: ``revision.population_summary`` from this checkout's source,
run on the imported editors over every in-scope question's initial catalogue.
"""

from __future__ import annotations

from hashlib import sha256
import importlib.util
import inspect
import json
import subprocess
import sys
from pathlib import Path

from tool_compression.adapter import description_slots
from tool_compression.clean_start.__main__ import _select_cases
from tool_compression.clean_start.pin import ARMS
from tool_compression.clean_start.prepare import model_facing_tools
from tool_compression.clean_start.render import render_tools
from tool_compression.clean_start.runner import arm_tools
from tool_compression.clean_start.scope import in_scope_questions, study_categories
from tool_compression.config import LOCAL_TOKENIZER
from tool_compression.count import TiktokenCounter, dump_request
import tool_compression

HERE = Path(__file__).resolve().parents[1]


def journal_sha256(tools: list[dict]) -> str:
    return sha256(json.dumps(tools, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _row(tools: list[dict], counter) -> dict:
    texts = [container[key] for tool in tools for _pointer, container, key in description_slots(tool)]
    return {
        "tools_sha256": journal_sha256(tools),
        "local_tools_tokens": counter.count(dump_request(tools)),
        "local_field_tokens": sum(counter.count(text) for text in texts),
        "tools": len(tools),
    }


def _held_out_argument(batches: list[list[dict]]):
    """Batches for runners that take ``held_out_batches``; one flat list for older runners."""
    if "held_out_batches" in inspect.signature(arm_tools).parameters:
        return batches
    return [doc for batch in batches for doc in batch]


def _source_commit() -> str | None:
    source = Path(tool_compression.__file__).resolve().parents[2]
    commit = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    ).stdout.strip()
    return commit or None


def _edits(case: dict) -> dict:
    """Description slots S changed and tools X cued, on the initial catalogue."""
    initial = {arm: arm_tools(case["function"], case["category"], arm) for arm in ("U", "S", "X")}

    def slots(tools):
        return [(tool["function"]["name"], pointer, container[key])
                for tool in tools for pointer, container, key in description_slots(tool)]

    base = slots(initial["U"])
    return {
        "s_changed_slots": [
            [name, pointer] for (name, pointer, text), (_n, _p, edited) in zip(base, slots(initial["S"])) if text != edited
        ],
        "x_cued_tools": [
            tool["function"]["name"] for tool, cued in zip(initial["U"], initial["X"]) if tool != cued
        ],
    }


def conversations(selected: list[dict] | None = None) -> dict:
    counter = TiktokenCounter(LOCAL_TOKENIZER)
    cases = {}
    for case in _select_cases(True, "matched") if selected is None else selected:
        states = {"initial": {arm: _row(arm_tools(case["function"], case["category"], arm), counter) for arm in ARMS}}
        batches: list[list[dict]] = []
        for turn in sorted(case.get("held_out", {}), key=int):
            batches = batches + [list(case["held_out"][turn])]
            held = _held_out_argument(batches)
            states[f"held_out:{turn}"] = {
                arm: _row(arm_tools(case["function"], case["category"], arm, held), counter) for arm in ARMS
            }
        cases[case["id"]] = {
            "category": case["category"],
            "prereq": bool(case.get("prereq")),
            "states": states,
        }
        if selected is not None:
            cases[case["id"]]["initial_edits"] = _edits(case)
    return {
        "source_commit": _source_commit(),
        "tokenizer": LOCAL_TOKENIZER,
        "hash": "sha256(json.dumps(tools, ensure_ascii=False, sort_keys=True)), as runner attempts.jsonl",
        "conversations": len(cases),
        "cases": cases,
    }


def validation() -> dict:
    from tool_compression.clean_start.validation import select_validation_cases

    return conversations(select_validation_cases())


def population() -> dict:
    spec = importlib.util.spec_from_file_location(
        "clean_start_revision", HERE / "src" / "tool_compression" / "clean_start" / "revision.py"
    )
    revision = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(revision)
    summary = revision.population_summary(
        study_categories(),
        in_scope_questions,
        model_facing_tools,
        render_tools,
        TiktokenCounter(LOCAL_TOKENIZER),
        dump_request,
    )
    return {"source_commit": _source_commit(), "tokenizer": LOCAL_TOKENIZER, **summary}


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "conversations"
    payload = {"conversations": conversations, "validation": validation, "population": population}[mode]()
    json.dump(payload, sys.stdout, indent=1, ensure_ascii=False)
    sys.stdout.write("\n")
