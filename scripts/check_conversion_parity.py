"""Compare the local OpenAI-completions conversion with the pinned BFCL functions.

Prints mismatch counts and value kinds. Does not print description text.
"""

from pathlib import Path
import ast
import copy
import json
import re
import sys

from tool_compression.convert import GORILLA_TO_OPENAPI, to_openai_completions_tools
from tool_compression.load import STUDY_CATEGORIES, load_category


class ModelStyle:
    OPENAI_COMPLETIONS = "OPENAI_COMPLETIONS"
    OPENAI_RESPONSES = "OPENAI_RESPONSES"
    MISTRAL = "MISTRAL"
    GOOGLE = "GOOGLE"
    OSSMODEL = "OSSMODEL"
    ANTHROPIC = "ANTHROPIC"
    COHERE = "COHERE"
    AMAZON = "AMAZON"
    NOVITA_AI = "NOVITA_AI"
    WRITER = "WRITER"
    FIREWORK_AI = "FIREWORK_AI"


def load_official(utils_path: Path):
    source = utils_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    chunks = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in {"_cast_to_openai_type", "convert_to_tool"}:
            chunks.append(ast.get_source_segment(source, node))
    namespace = {
        "copy": copy,
        "json": json,
        "re": re,
        "GORILLA_TO_OPENAPI": GORILLA_TO_OPENAPI,
        "ModelStyle": ModelStyle,
    }
    exec("\n\n".join(chunks), namespace)
    return namespace["convert_to_tool"]


def first_difference(left, right, path=""):
    if type(left) is not type(right):
        return f"{path} type {type(left).__name__}/{type(right).__name__}"
    if isinstance(left, dict):
        if list(left) != list(right):
            return f"{path} key_order"
        for key in left:
            found = first_difference(left[key], right[key], f"{path}/{key if key in {'type', 'description', 'properties', 'items', 'parameters', 'function', 'format', 'required', 'name'} else '{name}'}")
            if found:
                return found
        return None
    if isinstance(left, list):
        if len(left) != len(right):
            return f"{path} len"
        for index, (item, other) in enumerate(zip(left, right)):
            found = first_difference(item, other, f"{path}/{index}")
            if found:
                return found
        return None
    if left != right:
        kind = "string" if isinstance(left, str) else type(left).__name__
        return f"{path} value {kind}"
    return None


def summarize(bfcl_root: Path, utils_path: Path) -> dict:
    """Return mismatch counts only. Does not print record text."""
    official = load_official(utils_path)
    mismatches = 0
    checked = 0
    for category in STUDY_CATEGORIES:
        _path, records = load_category(bfcl_root, category)
        for record in records:
            checked += 1
            try:
                left = official(record["function"], GORILLA_TO_OPENAPI, ModelStyle.OPENAI_COMPLETIONS)
                right = to_openai_completions_tools(record["function"])
            except Exception:
                mismatches += 1
                continue
            if first_difference(left, right):
                mismatches += 1
    return {
        "checked_records": checked,
        "mismatches": mismatches,
        "official_functions": "_cast_to_openai_type and convert_to_tool",
        "style": "OPENAI_COMPLETIONS",
    }


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: check_conversion_parity.py BFCL_ROOT UTILS_PY")
        return 2
    root = Path(sys.argv[1])
    official = load_official(Path(sys.argv[2]))
    mismatches = 0
    checked = 0
    for category in STUDY_CATEGORIES:
        _path, records = load_category(root, category)
        for record in records:
            checked += 1
            try:
                left = official(record["function"], GORILLA_TO_OPENAPI, ModelStyle.OPENAI_COMPLETIONS)
                right = to_openai_completions_tools(record["function"])
            except Exception as exc:
                mismatches += 1
                print(f"{category} {record['id']} exception {type(exc).__name__}")
                continue
            diff = first_difference(left, right)
            if diff:
                mismatches += 1
                print(f"{category} {record['id']} {diff}")
    print(f"checked={checked} mismatches={mismatches}")
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
