"""Load original non-live BFCL question files. Answer files are refused."""

from pathlib import Path
import json

PRIMARY_CATEGORY = "multiple"
CONTROL_CATEGORIES = ("simple_python", "irrelevance")
STUDY_CATEGORIES = (PRIMARY_CATEGORY, *CONTROL_CATEGORIES)
CATEGORY_ROLE = {
    "multiple": "primary",
    "simple_python": "control",
    "irrelevance": "control",
}
VERSION_PREFIX = "BFCL_v4"
LABEL_KEYS = frozenset({"possible_answer", "ground_truth", "answer", "answers", "label", "labels"})
REFUSED_PARTS = frozenset({"possible_answer", "unused_datasets"})


def resolve_data_dir(root: Path) -> Path:
    root = Path(root)
    candidates = [
        root,
        root / "bfcl_eval" / "data",
        root / "berkeley-function-call-leaderboard" / "bfcl_eval" / "data",
    ]
    for candidate in candidates:
        if (candidate / f"{VERSION_PREFIX}_multiple.json").is_file():
            _refuse(candidate)
            return candidate
    raise FileNotFoundError(
        f"No {VERSION_PREFIX}_multiple.json under {root}. "
        "Use a Gorilla checkout. Do not vendor the benchmark into this repository."
    )


def load_category(bfcl_root: Path, category: str) -> tuple[Path, list[dict]]:
    if category not in STUDY_CATEGORIES:
        raise ValueError(f"Week 1 reads only {', '.join(STUDY_CATEGORIES)}")
    path = resolve_data_dir(bfcl_root) / f"{VERSION_PREFIX}_{category}.json"
    _refuse(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    records = _read(path)
    seen: set[str] = set()
    for record in records:
        found = LABEL_KEYS.intersection(record)
        if found:
            raise RuntimeError(f"refusing label fields {sorted(found)} in {path.name}")
        if not {"id", "question", "function"} <= set(record):
            raise RuntimeError(f"unexpected record shape in {path.name}")
        if record["id"] in seen:
            raise RuntimeError(f"duplicate id in {path.name}")
        seen.add(record["id"])
    return path, records


def load_study(bfcl_root: Path) -> dict[str, list[dict]]:
    return {category: load_category(bfcl_root, category)[1] for category in STUDY_CATEGORIES}


def _refuse(path: Path) -> None:
    if REFUSED_PARTS.intersection(Path(path).parts):
        raise RuntimeError(f"refusing benchmark path {path}")


def _read(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    if text.lstrip().startswith("["):
        data = json.loads(text)
        if not isinstance(data, list):
            raise RuntimeError(f"expected a list in {path.name}")
        return data
    return [json.loads(line) for line in text.splitlines() if line.strip()]
