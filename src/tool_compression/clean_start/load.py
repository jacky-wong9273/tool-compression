"""Load unmodified BFCL prompt files. Gold answers are refused.

Questions, ``path``, and ``initial_config`` stay on the case for the sender and
the official executor. Editors receive only tool documentation.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import json

from tool_compression.clean_start.categories import (
    ALL_SCORING_CATEGORIES,
    FUNC_DOC_FILES,
    MEMORY_SCENARIOS,
    PROMPT_FILES,
    is_agentic,
    is_memory,
    is_multi_turn,
    is_web_search,
)
from tool_compression.clean_start.pin import BFCL_COMMIT, BFCL_VERSION_PREFIX

LABEL_KEYS = frozenset({
    "possible_answer",
    "ground_truth",
    "answer",
    "answers",
    "label",
    "labels",
})
REFUSED_PARTS = frozenset({"possible_answer", "unused_datasets", "format_sensitivity"})


def bfcl_root() -> Path:
    root = Path(__file__).resolve().parents[3] / "studies" / "clean-start-usx" / "bfcl"
    if not (root / "manifest.json").is_file():
        raise FileNotFoundError(f"vendored BFCL prompts are missing under {root}")
    return root


def read_jsonl(path: Path) -> list[dict]:
    if REFUSED_PARTS.intersection(path.parts):
        raise RuntimeError(f"refusing benchmark path {path}")
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        found = LABEL_KEYS.intersection(record)
        if found:
            raise RuntimeError(f"refusing label fields {sorted(found)} in {path.name}")
        records.append(record)
    return records


@lru_cache(maxsize=1)
def function_catalogues() -> dict[str, tuple[dict, ...]]:
    root = bfcl_root() / "func_docs"
    catalogues = {}
    for class_name, filename in FUNC_DOC_FILES.items():
        catalogues[class_name] = tuple(read_jsonl(root / filename))
    return catalogues


def _attach_functions(record: dict) -> tuple[list[dict], dict[str, list[dict]]]:
    """Return the initial tool docs and docs held out until a later turn."""
    if not (is_multi_turn(record["id"]) or is_agentic(record["id"])):
        return list(record.get("function") or []), {}
    catalogues = function_catalogues()
    functions: list[dict] = []
    for class_name in record["involved_classes"]:
        functions.extend(json.loads(json.dumps(list(catalogues[class_name]))))
    held: dict[str, list[dict]] = {}
    missed = record.get("missed_function") or {}
    for turn, names in missed.items():
        held[str(turn)] = []
        for name in list(names):
            for index, doc in enumerate(functions):
                if doc.get("name") == name:
                    held[str(turn)].append(functions.pop(index))
                    break
    return functions, held


def _case(record: dict, category: str, *, prereq: bool) -> dict:
    functions, held = _attach_functions({**record, "id": record["id"]})
    # ``path`` is the multi-turn ground-truth function list shipped inside the
    # prompt file. It is not copied onto the case the editor can see.
    return {
        "id": record["id"],
        "category": category,
        "prereq": prereq,
        "question": record["question"],
        "function": functions,
        "held_out": held,
        "involved_classes": list(record.get("involved_classes") or []),
        "initial_config": record.get("initial_config") or {},
        "scenario": record.get("scenario"),
        "excluded_function": list(record.get("excluded_function") or []),
    }


def load_questions(category: str) -> list[dict]:
    """Scoring questions for one category, with official ids and tool docs.

    Memory prerequisite conversations are not included. They are loaded by
    ``load_prereqs`` because a later full memory run has to send them first.
    """
    if category not in ALL_SCORING_CATEGORIES:
        raise ValueError(f"{category} is not a scoring category")
    root = bfcl_root() / "prompts"
    if is_memory(category):
        records = read_jsonl(root / PROMPT_FILES["memory"])
        cases = []
        for record in records:
            rewritten = json.loads(json.dumps(record))
            rewritten["id"] = rewritten["id"].replace("memory", category)
            rewritten["involved_classes"] = [f"MemoryAPI_{category[len('memory_'):]}"]
            cases.append(_case(rewritten, category, prereq=False))
        return cases
    if is_web_search(category):
        records = read_jsonl(root / PROMPT_FILES["web_search"])
        cases = []
        for record in records:
            rewritten = json.loads(json.dumps(record))
            rewritten["id"] = rewritten["id"].replace("web_search", category)
            cases.append(_case(rewritten, category, prereq=False))
        return cases
    filename = PROMPT_FILES[category]
    return [_case(record, category, prereq=False) for record in read_jsonl(root / filename)]


def load_prereqs(category: str) -> list[dict]:
    if not is_memory(category):
        return []
    cases = []
    root = bfcl_root() / "memory_prereq"
    backend = category[len("memory_"):]
    for scenario in MEMORY_SCENARIOS:
        for record in read_jsonl(root / f"memory_{scenario}.json"):
            rewritten = json.loads(json.dumps(record))
            rewritten["id"] = rewritten["id"].replace("memory", category)
            rewritten["involved_classes"] = [f"MemoryAPI_{backend}"]
            cases.append(_case(rewritten, category, prereq=True))
    return cases


def iter_scoring_cases(*, include_prereqs: bool) -> list[dict]:
    cases: list[dict] = []
    for category in ALL_SCORING_CATEGORIES:
        if include_prereqs:
            cases.extend(load_prereqs(category))
        cases.extend(load_questions(category))
    return cases


def prompt_manifest() -> dict:
    payload = json.loads((bfcl_root() / "manifest.json").read_text(encoding="utf-8"))
    if payload.get("bfcl_commit") != BFCL_COMMIT:
        raise RuntimeError("vendored manifest commit does not match the study pin")
    if payload.get("files") and not str(payload["files"][0]["path"]).startswith("BFCL"):
        prefix = payload["files"][0]["path"]
        if not prefix.endswith(".json"):
            raise RuntimeError(f"unexpected manifest entry {prefix}")
    return payload


def file_sha256(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity_rows() -> list[dict]:
    root = bfcl_root()
    rows = []
    for path in sorted(root.rglob("*.json")):
        if path.name == "manifest.json":
            continue
        data = path.read_bytes()
        lines = [line for line in data.decode("utf-8").splitlines() if line.strip()]
        rows.append({
            "path": str(path.relative_to(root)),
            "sha256": __import__("hashlib").sha256(data).hexdigest(),
            "bytes": len(data),
            "lines": len(lines),
        })
    return rows


def raw_prompt_filename(category: str) -> str:
    if is_memory(category):
        return PROMPT_FILES["memory"]
    if is_web_search(category):
        return PROMPT_FILES["web_search"]
    return PROMPT_FILES[category]


def version_prefix() -> str:
    return BFCL_VERSION_PREFIX
