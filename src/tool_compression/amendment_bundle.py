"""Offline S2/X2/SX2 bundle. Editing is separate from scoring.

This module does not read a question, a gold answer, an API key, or a provider.
The only network probe is a mocked completion whose sockets are denied.
"""

from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from difflib import unified_diff
from hashlib import sha256
from pathlib import Path
import json
import os
import re
import socket
import subprocess
import sys

from tool_compression.adapter import description_slots
from tool_compression.amendment_s2 import FLOAT_SUFFIX as S2_FLOAT_SUFFIX
from tool_compression.amendment_s2 import KEEP_REASONS, edit_tool
from tool_compression.amendment_x2 import CUE_POINTER, CUE_SEPARATOR, qualify_catalogue
from tool_compression.config import (
    BFCL_DEFAULT_TEMPERATURE,
    BFCL_STORE,
    LOCAL_TOKENIZER,
    METHODS,
    PLACEHOLDER_MODEL,
    SENSITIVITY_TOKENIZER,
)
from tool_compression.convert import FLOAT_SUFFIX as CONVERSION_FLOAT_SUFFIX
from tool_compression.count import TiktokenCounter, dump_request
from tool_compression.semantic_audit import get_text
from tool_compression.validate import catalogue_violations

SAMPLE = "amendment-s2x2"
BASE_COMMIT = "62bab379f0dae60599378162f2322f03be5d56f9"
PR12_BRANCH = "cursor/official-840-usx-package-87f6"
GORILLA_COMMIT = "6ea57973c7a6097fd7c5915698c54c17c5b1b6c8"
ARMS = ("U", "S2", "X2", "SX2")
CATEGORIES = ("multiple", "simple_python", "irrelevance")
EXPECTED_COUNTS = {"multiple": 200, "simple_python": 400, "irrelevance": 240}
FORBIDDEN_KEYS = frozenset({"question", "possible_answer", "ground_truth", "gold"})
BANNED_CUE = ("only this", "cannot", "can't", "exclusively", "unable to", "does not handle")
REPRODUCTION = "python -m tool_compression amendment-s2x2 --check"
TOKENIZER_CACHE = {
    "o200k_base": {
        "url": "https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken",
        "cache_key": "fb374d419588a4632f3f557e76b4b70aebbca790",
        "sha256": "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d",
    },
    "cl100k_base": {
        "url": "https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken",
        "cache_key": "9b5ad71b2ce5302211f9c61530b329a4922fc6a4",
        "sha256": "223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7",
    },
}

GCD_CUE = (
    "Unlike math_lcm, which calculates the least common multiple, "
    "this calculates the greatest common divisor."
)
LCM_CUE = (
    "Unlike math_gcd, which calculates the greatest common divisor, "
    "this calculates the least common multiple."
)
CALC_LCM_CUE = (
    "Unlike calculate_gcd, which calculates the greatest common divisor (gcd), "
    "this calculates the least common multiple (lcm)."
)
CALC_GCD_CUE = (
    "Unlike calculate_lcm, which calculates the least common multiple (lcm), "
    "this calculates the greatest common divisor (gcd)."
)
QUADRATIC_CUE = (
    "Unlike math_roots_polynomial, which takes an ordered coefficient array, "
    "this takes named quadratic coefficients."
)
CUBIC_CUE = (
    "Unlike math_roots_polynomial, which takes an ordered coefficient array, "
    "this takes named cubic coefficients."
)
POLYNOMIAL_CUE = (
    "Unlike math_roots_quadratic, which takes named quadratic coefficients, "
    "this takes an ordered coefficient array."
)
GET_ANGLES = "Whether to calculate the internal angles"
ALGORITHM_FINAL = "The specific algorithm to use in the calculation. Default 'euclidean'"
METHOD_ORIGINAL = (
    "The specific method to use in the calculation. "
    "Supported values: 'standard', 'reduced'. Default 'standard'"
)

COMPARISON_COLUMNS = (
    ("U", "U"),
    ("systems_test_S", "#11 S"),
    ("pr12_S", "#12 S"),
    ("S2", "S2"),
    ("systems_test_X", "#11 X"),
    ("pr12_X", "#12 X"),
    ("X2", "X2"),
    ("systems_test_SX", "#11 SX"),
    ("pr12_SX", "#12 SX"),
    ("SX2", "SX2"),
)


class AmendmentFailure(RuntimeError):
    """A closed stop. The bundle is not repaired and nothing is scored."""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def bundle_dir() -> Path:
    return repo_root() / "docs" / "amendment-s2x2"


def _official_u(case_id: str) -> Path:
    return repo_root() / "docs" / "official-840" / "catalogues" / "U" / f"{case_id}.json"


def _sha256(data: bytes) -> str:
    return sha256(data).hexdigest()


def _category(case_id: str) -> str:
    for name in ("simple_python", "irrelevance", "multiple"):
        if case_id.startswith(name + "_"):
            return name
    raise AmendmentFailure(f"unrecognised case id {case_id}")


def _ratio(numerator: int, denominator: int) -> dict:
    return {"numerator": numerator, "denominator": denominator, "text": f"{numerator}/{denominator}"}


def _json_text(payload) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def _jsonl(rows: list[dict]) -> str:
    return "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows)


def _under_bundle(path: Path) -> Path:
    path = Path(path)
    root = bundle_dir().resolve()
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    if resolved != root and root not in resolved.parents:
        raise AmendmentFailure(f"refusing to write outside the amendment bundle: {resolved}")
    return resolved


def _write(relative: str, text: str) -> None:
    path = _under_bundle(bundle_dir() / relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _pin_tokenizer_cache() -> None:
    """Point tiktoken at the committed BPE tables. This does not read a secret."""
    cache = repo_root() / "src" / "tool_compression" / "tiktoken_cache"
    for name, pin in TOKENIZER_CACHE.items():
        path = cache / pin["cache_key"]
        if not path.is_file() or _sha256(path.read_bytes()) != pin["sha256"]:
            raise AmendmentFailure(f"tokenizer cache mismatch for {name}")
    os.environ["TIKTOKEN_CACHE_DIR"] = str(cache)


@contextmanager
def _network_denied():
    # Load these before replacing socket.socket. ssl.SSLSocket subclasses it
    # at import time. Do not delete the http.client attribute: later tests
    # still use that module.
    import http.client
    import ssl
    del http, ssl
    original_socket = socket.socket
    original_create = socket.create_connection

    def deny(*_args, **_kwargs):
        raise OSError("network denied")

    socket.socket = deny
    socket.create_connection = deny
    try:
        yield
    finally:
        socket.socket = original_socket
        socket.create_connection = original_create


def _closed_records(root: Path) -> None:
    evaluation = (root / "src" / "tool_compression" / "evaluation.py").read_text(encoding="utf-8")
    config = (root / "src" / "tool_compression" / "config.py").read_text(encoding="utf-8")
    if '"target_provider_input_reduction": "1/10"' not in evaluation:
        raise AmendmentFailure("the closed 1/10 target is not on record")
    if '"official_accuracy_in_scope": False' not in evaluation:
        raise AmendmentFailure("official accuracy is not recorded as out of scope")
    if 'METHODS = ("U", "P", "I", "C")' not in config:
        raise AmendmentFailure("the T1/T2 method record changed")
    if f'LOCAL_TOKENIZER = "{LOCAL_TOKENIZER}"' not in config:
        raise AmendmentFailure("the local tokenizer record changed")
    if S2_FLOAT_SUFFIX != CONVERSION_FLOAT_SUFFIX:
        raise AmendmentFailure("S2 float suffix does not match the pinned conversion")
    if METHODS != ("U", "P", "I", "C"):
        raise AmendmentFailure("T1/T2 methods changed")


def _case_ids(root: Path) -> list[str]:
    manifest = json.loads((root / "docs" / "official-840" / "selection" / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("questions_stored") is not False:
        raise AmendmentFailure("official manifest no longer says questions are absent")
    ids = list(manifest["ids_in_file_order"])
    files = {path.stem for path in (root / "docs" / "official-840" / "catalogues" / "U").glob("*.json")}
    counts = Counter(_category(case_id) for case_id in ids)
    if ids != list(dict.fromkeys(ids)) or files != set(ids) or dict(counts) != EXPECTED_COUNTS:
        raise AmendmentFailure("U catalogue set does not match the official 200/400/240 manifest")
    return ids


def _formative_ids(root: Path) -> list[str]:
    manifest = json.loads(
        (root / "docs" / "semantic-audit-pilot" / "selection" / "manifest.json").read_text(encoding="utf-8")
    )
    ids = [row["case_id"] for row in manifest["selected"]]
    if len(ids) != 12 or len(set(ids)) != 12:
        raise AmendmentFailure("the formative selection is not the former 12 cases")
    return ids


def _forbidden(node, path: str = "") -> list[str]:
    found = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in FORBIDDEN_KEYS:
                found.append(path + "/" + str(key))
            found.extend(_forbidden(value, path + "/" + str(key)))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(_forbidden(value, f"{path}/{index}"))
    return found


def _load_u(case_id: str) -> tuple[bytes, dict]:
    path = _official_u(case_id)
    raw = path.read_bytes()
    document = json.loads(raw)
    leaked = _forbidden(document)
    if leaked or document.get("case_id") != case_id or "tools" not in document:
        raise AmendmentFailure(f"U document {case_id} failed provenance: {leaked}")
    if raw.decode("utf-8").encode("utf-8") != raw:
        raise AmendmentFailure(f"U document {case_id} is not stable UTF-8")
    return raw, document


def _historical_tools(case_id: str) -> dict[str, list]:
    root = repo_root()
    paths = {
        "systems_test_S": root / "docs" / "semantic-audit-pilot" / "rendered" / case_id / "S.json",
        "systems_test_X": root / "docs" / "semantic-audit-pilot" / "cue-revision" / "rendered" / case_id / "X.json",
        "systems_test_SX": root / "docs" / "semantic-audit-pilot" / "cue-revision" / "rendered" / case_id / "SX.json",
        "pr12_S": root / "docs" / "official-840" / "rendered" / case_id / "S.json",
        "pr12_X": root / "docs" / "official-840" / "rendered" / case_id / "X.json",
        "pr12_SX": root / "docs" / "official-840" / "rendered" / case_id / "SX.json",
    }
    loaded = {}
    for key, path in paths.items():
        if not path.is_file():
            raise AmendmentFailure(f"missing historical render {path}")
        document = json.loads(path.read_text(encoding="utf-8"))
        leaked = _forbidden(document)
        if leaked or "tools" not in document:
            raise AmendmentFailure(f"historical render {path} failed provenance: {leaked}")
        loaded[key] = document["tools"]
    return loaded


def _non_slot_bytes(tools: list[dict]) -> bytes:
    cloned = json.loads(json.dumps(tools))
    for tool in cloned:
        for _pointer, container, key in description_slots(tool):
            container[key] = ""
    return (json.dumps(cloned, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _envelope(tools: list[dict]) -> str:
    return dump_request({
        "model": PLACEHOLDER_MODEL,
        "temperature": BFCL_DEFAULT_TEMPERATURE,
        "store": BFCL_STORE,
        "tools": tools,
    })


def _arm_document(case_id: str, category: str, condition: str, tools: list[dict]) -> dict:
    return {
        "sample": SAMPLE,
        "case_id": case_id,
        "category": category,
        "condition": condition,
        "gorilla_commit": GORILLA_COMMIT,
        "conversion": "to_openai_completions_tools",
        "base_commit": BASE_COMMIT,
        "note": "Offline S2/X2/SX2 amendment render. No question, gold call, stored response, or provider call.",
        "tools": tools,
    }


def _apply_cues(tools: list[dict], rows: list[dict]) -> list[dict]:
    edited = json.loads(json.dumps(tools))
    for row in rows:
        cue = row["cue"]
        if cue == "":
            continue
        if row["pointer"] != CUE_POINTER or CUE_SEPARATOR != " ":
            raise AmendmentFailure("a cue is not confined to the function description")
        current = edited[row["tool_index"]]["function"]["description"]
        edited[row["tool_index"]]["function"]["description"] = current + " " + cue
    return edited


def _signature(row: dict):
    return (
        row["candidate"],
        row["final"],
        row["adopted"],
        row["keep_reason"],
        row["change_class"],
        json.dumps(row["facts"], ensure_ascii=False, sort_keys=True, separators=(",", ":")),
    )


def _link_reuse(cases: list[dict]) -> None:
    seen = {}
    for case in cases:
        for row in case["s2_rows"]:
            key = (row["context_id"], row["pointer"])
            signature = _signature(row)
            prior = seen.get(key)
            if prior is None:
                row["reused"] = False
                row["candidate_id"] = _sha256(json.dumps({
                    "context_id": row["context_id"],
                    "pointer": row["pointer"],
                    "candidate": row["candidate"],
                    "final": row["final"],
                    "keep_reason": row["keep_reason"],
                    "change_class": row["change_class"],
                }, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))
                row["first_occurrence_id"] = None
                seen[key] = row
                continue
            if _signature(prior) != signature:
                raise AmendmentFailure(
                    f"reused tool context disagreed at {row['occurrence_id']} and {prior['occurrence_id']}"
                )
            row["reused"] = True
            row["candidate_id"] = prior["candidate_id"]
            row["first_occurrence_id"] = prior["occurrence_id"]


def edit_case(tools: list[dict], case_id: str = "", category: str = "") -> dict:
    """Edit one catalogue. S2 receives each tool alone. X2 receives original U."""
    if not isinstance(tools, list) or any(not isinstance(tool, dict) for tool in tools):
        raise AmendmentFailure(f"{case_id or 'case'} is not a tool list")
    snapshot = json.loads(json.dumps(tools))
    s2_tools = []
    s2_rows = []
    for index, tool in enumerate(tools):
        edited, rows = edit_tool(tool)
        s2_tools.append(edited)
        for row in rows:
            item = dict(row)
            item["case_id"] = case_id
            item["category"] = category
            item["tool_index"] = index
            item["occurrence_id"] = f"{case_id}:{index}:{row['pointer']}"
            item["editor_input"] = "target_tool_only"
            s2_rows.append(item)
    if tools != snapshot:
        raise AmendmentFailure(f"S2 mutated the original catalogue for {case_id}")
    original = snapshot
    x2_rows = qualify_catalogue(original)
    for row in x2_rows:
        row["case_id"] = case_id
        row["category"] = category
        row["occurrence_id"] = f"{case_id}:{row['tool_index']}:{row['pointer']}"
        row["catalogue_input"] = "original_U_only"
        row["s2_hidden"] = True
    x2_tools = _apply_cues(original, x2_rows)
    sx2_tools = _apply_cues(s2_tools, x2_rows)
    rendered = {"U": original, "S2": s2_tools, "X2": x2_tools, "SX2": sx2_tools}
    errors = _invariant_errors(case_id, rendered, s2_rows, x2_rows)
    if errors:
        raise AmendmentFailure(f"{case_id} failed closed:\n" + "\n".join(errors))
    return {
        "case_id": case_id,
        "category": category,
        "control": len(original) == 1,
        "tools": rendered,
        "s2_rows": s2_rows,
        "x2_rows": x2_rows,
    }


def _texts(tools: list[dict]) -> dict[tuple[int, str], str]:
    found = {}
    for index, tool in enumerate(tools):
        for pointer, container, key in description_slots(tool):
            found[(index, pointer)] = container[key]
    return found


def _invariant_errors(case_id: str, rendered: dict, s2_rows: list[dict], x2_rows: list[dict]) -> list[str]:
    errors = []
    original = rendered["U"]
    names = [tool["function"]["name"] for tool in original]
    if [tool["function"]["name"] for tool in rendered["S2"]] != names:
        errors.append("S2 tool membership or order changed")
    if [tool["function"]["name"] for tool in rendered["X2"]] != names:
        errors.append("X2 tool membership or order changed")
    if [tool["function"]["name"] for tool in rendered["SX2"]] != names:
        errors.append("SX2 tool membership or order changed")
    skeleton = _non_slot_bytes(original)
    for arm in ("S2", "X2", "SX2"):
        violations = catalogue_violations(original, rendered[arm])
        errors.extend(f"{arm}:{item}" for item in violations)
        if _non_slot_bytes(rendered[arm]) != skeleton:
            errors.append(f"{arm} non-description bytes differ")
        leaked = _forbidden(rendered[arm])
        errors.extend(f"{arm} hidden {item}" for item in leaked)
    by_pointer = {(row["tool_index"], row["pointer"]): row for row in s2_rows}
    s2_text = _texts(rendered["S2"])
    u_text = _texts(original)
    if set(by_pointer) != set(u_text):
        errors.append("S2 did not visit every description slot")
    for key, row in by_pointer.items():
        if row["final"] != s2_text[key] or row["original"] != u_text[key]:
            errors.append(f"S2 ledger does not match the rendered text {key}")
        if row["adopted"] and not (len(row["final"]) < len(row["original"]) and row["final"] != row["original"]):
            errors.append(f"adopted field is not shorter {key}")
        if row["adopted"] and row["keep_reason"] is not None:
            errors.append(f"adopted field also has a KEEP reason {key}")
        if not row["adopted"] and row["keep_reason"] not in KEEP_REASONS:
            errors.append(f"KEEP reason is not field-specific {key}")
        if row["cosmetic"] or (row["adopted"] and _words_only(row["original"]) == _words_only(row["final"])):
            errors.append(f"cosmetic edit was adopted {key}")
        if row["adopted"] and row["final"] == row["original"]:
            errors.append(f"unchanged field was marked adopted {key}")
    for index, tool in enumerate(rendered["S2"]):
        for pointer, container, key in description_slots(tool):
            text = container[key]
            source = u_text[(index, pointer)]
            for other, name in enumerate(names):
                if other == index or not name:
                    continue
                pattern = re.compile(rf"\b{re.escape(name)}\b")
                if pattern.search(text) and not pattern.search(source):
                    errors.append(f"S2 introduces sibling {name} at {index} {pointer}")
    if len(x2_rows) != len(original):
        errors.append("X2 did not qualify every tool")
    x_text = _texts(rendered["X2"])
    sx_text = _texts(rendered["SX2"])
    for row in x2_rows:
        key = (row["tool_index"], row["pointer"])
        cue = row["cue"]
        if row["pointer"] != "/function/description":
            errors.append("X2 cue path is not the function description")
        for other in u_text:
            if other[0] != row["tool_index"] or other[1] == "/function/description":
                continue
            if x_text[other] != u_text[other] or sx_text[other] != s2_text[other]:
                errors.append(f"cue changed a field other than the function description {other}")
        if cue:
            if x_text[key].encode("utf-8") != u_text[key].encode("utf-8") + b" " + cue.encode("utf-8"):
                errors.append(f"X2 is not U plus the cue at {key}")
            if sx_text[key].encode("utf-8") != s2_text[key].encode("utf-8") + b" " + cue.encode("utf-8"):
                errors.append(f"SX2 is not S2 plus the identical cue at {key}")
            problem = _cue_problem(cue, names, names[row["tool_index"]], row["rival"]["function_name"])
            if problem:
                errors.append(problem)
        else:
            if x_text[key] != u_text[key] or sx_text[key] != s2_text[key]:
                errors.append(f"uncued tool changed {key}")
            if not row["no_cue_reason"]:
                errors.append(f"missing no-cue reason {key}")
        if len(original) == 1 and (cue or row["no_cue_reason"] != "Single-tool control. Controls receive no cue."):
            errors.append("a control received a cue")
    if len(original) == 1:
        if rendered["X2"] != original or _envelope(rendered["X2"]) != _envelope(original):
            errors.append("control X2 input is not U byte for byte")
        if rendered["SX2"] != rendered["S2"] or _envelope(rendered["SX2"]) != _envelope(rendered["S2"]):
            errors.append("control SX2 input is not S2 byte for byte")
    return errors


def _words_only(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9]+", text.lower())


def _cue_problem(cue: str, names: list[str], target: str, rival: str) -> str | None:
    lowered = cue.lower()
    for banned in BANNED_CUE:
        if banned in lowered:
            return f"cue uses exclusive wording {banned!r}"
    if cue.count(rival) != 1 or target in cue:
        return "cue does not name exactly one rival"
    others = [name for name in names if name not in {target, rival} and name in cue]
    if others:
        return "cue names a third tool"
    if "only one" in lowered or "only this" in lowered:
        return "cue claims an exclusive capability"
    return None


def _row_by_name(rows: list[dict], name: str) -> dict:
    found = [row for row in rows if row["function_name"] == name and row["pointer"] == "/function/description"]
    if len(found) != 1:
        raise AmendmentFailure(f"expected one function row for {name}")
    return found[0]


def _field(rows: list[dict], name: str, pointer_suffix: str) -> dict:
    found = [row for row in rows if row["function_name"] == name and row["pointer"].endswith(pointer_suffix)]
    if len(found) != 1:
        raise AmendmentFailure(f"expected one field {name} {pointer_suffix}")
    return found[0]


def _fixture_errors(cases: dict[str, dict]) -> list[str]:
    errors = []
    case = cases["multiple_34"]
    gcd = _row_by_name(case["x2_rows"], "math_gcd")
    lcm = _row_by_name(case["x2_rows"], "math_lcm")
    sqrt = _row_by_name(case["x2_rows"], "math_sqrt")
    if gcd["cue"] != GCD_CUE or gcd["rival"]["function_name"] != "math_lcm":
        errors.append("multiple_34 did not cue math_gcd against math_lcm")
    if lcm["cue"] != LCM_CUE or lcm["rival"]["function_name"] != "math_gcd":
        errors.append("multiple_34 did not cue math_lcm against math_gcd")
    if sqrt["cue"] or "An unrelated tool does not veto any other pair." not in sqrt["no_cue_reason"]:
        errors.append("multiple_34 changed or vetoed math_sqrt")
    sqrt_u = next(tool for tool in case["tools"]["U"] if tool["function"]["name"] == "math_sqrt")
    sqrt_x = next(tool for tool in case["tools"]["X2"] if tool["function"]["name"] == "math_sqrt")
    if sqrt_x != sqrt_u:
        errors.append("multiple_34 X2 changed the sqrt tool")
    sqrt_function = _field(case["s2_rows"], "math_sqrt", "/function/description")
    if sqrt_function["final"] != sqrt_function["original"]:
        errors.append("multiple_34 S2 rewrote the sqrt function description")
    pair = cases["multiple_35"]
    calc_lcm = _row_by_name(pair["x2_rows"], "calculate_lcm")
    calc_gcd = _row_by_name(pair["x2_rows"], "calculate_gcd")
    if calc_lcm["cue"] != CALC_LCM_CUE or calc_gcd["cue"] != CALC_GCD_CUE:
        errors.append("multiple_35 did not treat the GCD/LCM pair comparably")
    if calc_lcm["axis"] != "common-value-of-two-numbers" or calc_gcd["axis"] != "common-value-of-two-numbers":
        errors.append("multiple_35 axis is not the shared two-number value")
    method = _field(pair["s2_rows"], "calculate_lcm", "/method/description")
    if method["final"] != METHOD_ORIGINAL or method["keep_reason"] != "no_shorter_faithful_candidate":
        errors.append("multiple_35 method prose was dropped without a schema default")
    algorithm = _field(pair["s2_rows"], "calculate_gcd", "/algorithm/description")
    if algorithm["final"] != ALGORITHM_FINAL or not algorithm["adopted"]:
        errors.append("multiple_35 did not drop the enum sentence and keep the prose default")
    roots = cases["multiple_11"]
    quadratic = _row_by_name(roots["x2_rows"], "math_roots_quadratic")
    cubic = _row_by_name(roots["x2_rows"], "math_roots_cubic")
    polynomial = _row_by_name(roots["x2_rows"], "math_roots_polynomial")
    if quadratic["cue"] != QUADRATIC_CUE or cubic["cue"] != CUBIC_CUE or polynomial["cue"] != POLYNOMIAL_CUE:
        errors.append("multiple_11 did not distinguish named coefficients from the ordered array")
    if quadratic["rival"]["function_name"] != "math_roots_polynomial":
        errors.append("multiple_11 quadratic rival is not the array tool")
    if polynomial["rival"]["function_name"] != "math_roots_quadratic":
        errors.append("multiple_11 did not keep the closest named-coefficient rival")
    for row in (quadratic, cubic, polynomial):
        if _cue_problem(row["cue"], ["math_roots_quadratic", "math_roots_cubic", "math_roots_polynomial"], row["function_name"], row["rival"]["function_name"]):
            errors.append("multiple_11 cue claims an exclusive quadratic capability")
    angles = _field(cases["multiple_0"]["s2_rows"], "triangle_properties_get", "/get_angles/description")
    if angles["final"] != GET_ANGLES or angles["change_class"] != "flag_normalization":
        errors.append("get_angles did not stay a whether-clause with internal kept")
    triangle = next(tool for tool in cases["multiple_0"]["tools"]["S2"] if tool["function"]["name"] == "triangle_properties_get")
    if triangle["function"]["parameters"]["properties"]["get_angles"]["default"] is not True:
        errors.append("get_angles schema default changed")
    for case_id in ("simple_python_0", "irrelevance_0"):
        sample = cases[case_id]
        if not sample["control"]:
            errors.append(f"{case_id} is not a single-tool control")
        if sample["tools"]["X2"] != sample["tools"]["U"] or sample["tools"]["SX2"] != sample["tools"]["S2"]:
            errors.append(f"{case_id} control bytes differ")
    return errors


def _count_tokens(case: dict, budget: TiktokenCounter, sensitivity: TiktokenCounter) -> None:
    rows = []
    totals = {arm: 0 for arm in ARMS}
    sensitivity_totals = {arm: 0 for arm in ARMS}
    for index, tool in enumerate(case["tools"]["U"]):
        for pointer, _container, _key in description_slots(tool):
            item = {"case_id": case["case_id"], "tool_index": index, "pointer": pointer, "o200k_base": {}, "cl100k_base": {}}
            for arm in ARMS:
                text = get_text(case["tools"][arm][index], pointer)
                count = budget.count(text)
                other = sensitivity.count(text)
                item["o200k_base"][arm] = count
                item["cl100k_base"][arm] = other
                totals[arm] += count
                sensitivity_totals[arm] += other
            rows.append(item)
    request = {}
    request_sensitivity = {}
    for arm in ARMS:
        body = _envelope(case["tools"][arm])
        request[arm] = budget.count(body)
        request_sensitivity[arm] = sensitivity.count(body)
    case["field_rows"] = rows
    case["field_tokens"] = totals
    case["field_tokens_cl100k"] = sensitivity_totals
    case["request_tokens"] = request
    case["request_tokens_cl100k"] = request_sensitivity


def _deltas(totals: dict) -> dict:
    return {
        "S2-U": totals["S2"] - totals["U"],
        "X2-U": totals["X2"] - totals["U"],
        "SX2-S2": totals["SX2"] - totals["S2"],
        "SX2-X2": totals["SX2"] - totals["X2"],
        "SX2-U": totals["SX2"] - totals["U"],
    }


def _cue_class(baseline: int, cue: int, net: int) -> str:
    if cue <= 0:
        return "cue_adds_no_tokens"
    if baseline >= 0:
        return "cue_cost_without_s2_savings"
    if net < 0:
        return "cue_consumes_part_of_savings"
    if net == 0:
        return "cue_consumes_all_savings"
    return "cue_exceeds_savings"


def _annotate(case: dict) -> None:
    adopted = [row for row in case["s2_rows"] if row["adopted"]]
    proposed = [row for row in case["s2_rows"] if row["candidate"] != row["original"]]
    cued = [row for row in case["x2_rows"] if row["cue"]]
    case["fields_eligible"] = len(case["s2_rows"])
    case["fields_proposed"] = len(proposed)
    case["fields_adopted"] = len(adopted)
    case["fields_meaningful"] = len(adopted)
    case["fields_cosmetic"] = 0
    case["fields_unchanged"] = len(case["s2_rows"]) - len(adopted)
    tools = {}
    for row in case["s2_rows"]:
        slot = tools.setdefault(row["tool_index"], {"proposed": 0, "adopted": 0})
        if row["candidate"] != row["original"]:
            slot["proposed"] += 1
        if row["adopted"]:
            slot["adopted"] += 1
    case["tools_eligible"] = len(case["tools"]["U"])
    case["tools_proposed"] = sum(1 for slot in tools.values() if slot["proposed"])
    case["tools_adopted"] = sum(1 for slot in tools.values() if slot["adopted"])
    case["tools_meaningful"] = case["tools_adopted"]
    case["tools_cosmetic"] = 0
    case["tools_unchanged"] = case["tools_eligible"] - case["tools_adopted"]
    case["cued_tools"] = len(cued)
    case["noop"] = case["fields_adopted"] == 0 and case["cued_tools"] == 0
    case["field_cue_class"] = _cue_class(
        case["field_tokens"]["S2"] - case["field_tokens"]["U"],
        case["field_tokens"]["SX2"] - case["field_tokens"]["S2"],
        case["field_tokens"]["SX2"] - case["field_tokens"]["U"],
    )
    case["request_cue_class"] = _cue_class(
        case["request_tokens"]["S2"] - case["request_tokens"]["U"],
        case["request_tokens"]["SX2"] - case["request_tokens"]["S2"],
        case["request_tokens"]["SX2"] - case["request_tokens"]["U"],
    )
    cued_fields = []
    lookup = {(row["tool_index"], row["pointer"]): row for row in case["field_rows"]}
    for row in cued:
        tokens = lookup[(row["tool_index"], row["pointer"])]["o200k_base"]
        cued_fields.append({
            "case_id": case["case_id"],
            "tool_index": row["tool_index"],
            "function_name": row["function_name"],
            "class": _cue_class(tokens["S2"] - tokens["U"], tokens["SX2"] - tokens["S2"], tokens["SX2"] - tokens["U"]),
            "deltas": _deltas(tokens),
        })
    case["cued_field_classes"] = cued_fields


def _sum_arm(cases: list[dict], key: str) -> dict:
    totals = {arm: 0 for arm in ARMS}
    for case in cases:
        for arm in ARMS:
            totals[arm] += case[key][arm]
    return totals


def _bucket(cases: list[dict], attribute: str) -> dict:
    counts = Counter(case[attribute] for case in cases)
    names = (
        "cue_adds_no_tokens",
        "cue_consumes_part_of_savings",
        "cue_consumes_all_savings",
        "cue_exceeds_savings",
        "cue_cost_without_s2_savings",
    )
    return {name: _ratio(counts[name], len(cases)) for name in names}


def _scope(cases: list[dict]) -> dict:
    n = len(cases)
    fields = sum(case["fields_eligible"] for case in cases)
    tools = sum(case["tools_eligible"] for case in cases)
    controls = [case for case in cases if case["control"]]
    multi = [case for case in cases if not case["control"]]
    cued_cases = [case for case in cases if case["cued_tools"]]
    verbatim = 0
    cued_case_tools = 0
    for case in cued_cases:
        cued_case_tools += case["tools_eligible"]
        verbatim += case["tools_eligible"] - case["cued_tools"]
    field_tokens = _sum_arm(cases, "field_tokens")
    request_tokens = _sum_arm(cases, "request_tokens")
    field_sensitivity = _sum_arm(cases, "field_tokens_cl100k")
    request_sensitivity = _sum_arm(cases, "request_tokens_cl100k")
    cued_fields = [item for case in cases for item in case["cued_field_classes"]]
    field_classes = Counter(item["class"] for item in cued_fields)
    return {
        "cases": n,
        "fields": {
            "eligible": _ratio(fields, fields),
            "proposed": _ratio(sum(case["fields_proposed"] for case in cases), fields),
            "adopted": _ratio(sum(case["fields_adopted"] for case in cases), fields),
            "meaningfully_changed": _ratio(sum(case["fields_meaningful"] for case in cases), fields),
            "cosmetic_only": _ratio(sum(case["fields_cosmetic"] for case in cases), fields),
            "unchanged": _ratio(sum(case["fields_unchanged"] for case in cases), fields),
        },
        "tools": {
            "eligible": _ratio(tools, tools),
            "proposed": _ratio(sum(case["tools_proposed"] for case in cases), tools),
            "adopted": _ratio(sum(case["tools_adopted"] for case in cases), tools),
            "meaningfully_changed": _ratio(sum(case["tools_meaningful"] for case in cases), tools),
            "cosmetic_only": _ratio(sum(case["tools_cosmetic"] for case in cases), tools),
            "unchanged": _ratio(sum(case["tools_unchanged"] for case in cases), tools),
        },
        "case_status": {
            "eligible": _ratio(n, n),
            "proposed": _ratio(sum(1 for case in cases if case["fields_proposed"]), n),
            "adopted": _ratio(sum(1 for case in cases if case["fields_adopted"]), n),
            "meaningfully_changed": _ratio(sum(1 for case in cases if case["fields_meaningful"]), n),
            "cosmetic_only": _ratio(sum(1 for case in cases if case["fields_cosmetic"] and not case["fields_meaningful"]), n),
            "unchanged": _ratio(sum(1 for case in cases if case["noop"]), n),
        },
        "cues": {
            "cued_tools": _ratio(sum(case["cued_tools"] for case in cases), tools),
            "cued_cases": _ratio(len(cued_cases), n),
            "controls": _ratio(len(controls), n),
            "controls_with_any_cue": _ratio(sum(1 for case in controls if case["cued_tools"]), len(controls)),
            "multi_tool_cases_with_a_cue": _ratio(sum(1 for case in multi if case["cued_tools"]), len(multi)),
            "uncued_tools_in_a_cued_case": _ratio(verbatim, cued_case_tools),
        },
        "field_tokens_o200k_base": {"totals": field_tokens, "signed_deltas": _deltas(field_tokens)},
        "request_tokens_o200k_base_without_messages": {
            "totals": request_tokens,
            "signed_deltas": _deltas(request_tokens),
            "label": "Local serialization of model, temperature, store, and tools. Question messages are not loaded. Not provider usage.",
        },
        "field_tokens_cl100k_base_not_used_for_selection": {
            "totals": field_sensitivity,
            "signed_deltas": _deltas(field_sensitivity),
        },
        "request_tokens_cl100k_base_not_used_for_selection": {
            "totals": request_sensitivity,
            "signed_deltas": _deltas(request_sensitivity),
        },
        "cue_cost_all_description_fields": _bucket(cases, "field_cue_class"),
        "cue_cost_request_without_messages": _bucket(cases, "request_cue_class"),
        "cue_cost_on_the_cued_function_field": {
            name: _ratio(field_classes[name], len(cued_fields))
            for name in (
                "cue_adds_no_tokens",
                "cue_consumes_part_of_savings",
                "cue_consumes_all_savings",
                "cue_exceeds_savings",
                "cue_cost_without_s2_savings",
            )
        },
    }


def _counterexamples(cases: dict[str, dict]) -> dict:
    gcd = _field(cases["multiple_34"]["s2_rows"], "math_gcd", "/function/description")
    method = _field(cases["multiple_35"]["s2_rows"], "calculate_lcm", "/method/description")
    ambiguous = None
    for case in cases.values():
        for row in case["s2_rows"]:
            if row["keep_reason"] == "ambiguous_source":
                ambiguous = row
                break
        if ambiguous:
            break
    if ambiguous is None:
        raise AmendmentFailure("no ambiguous-source counterexample was recorded")
    mixed = None
    for case in cases.values():
        if case["cued_tools"] and any(not row["cue"] for row in case["x2_rows"]):
            quiet = next(row for row in case["x2_rows"] if not row["cue"])
            mixed = {"case_id": case["case_id"], "row": quiet}
            break
    return {
        "s2_already_minimal": gcd,
        "s2_no_shorter_faithful_candidate": method,
        "s2_ambiguous_source": {
            "case_id": ambiguous["case_id"],
            "function_name": ambiguous["function_name"],
            "pointer": ambiguous["pointer"],
            "original": ambiguous["original"],
            "final": ambiguous["final"],
            "keep_reason": ambiguous["keep_reason"],
            "keep_detail": ambiguous["keep_detail"],
        },
        "x2_cued_pair": _row_by_name(cases["multiple_34"]["x2_rows"], "math_gcd"),
        "x2_uncued_neighbor": _row_by_name(cases["multiple_34"]["x2_rows"], "math_sqrt"),
        "x2_control": cases["simple_python_0"]["x2_rows"][0],
        "x2_uncued_while_neighbor_cued": mixed,
    }


def _formative_sheet(cases: dict[str, dict], formative: list[str]) -> list[dict]:
    rows = []
    for case_id in formative:
        case = cases[case_id]
        historical = _historical_tools(case_id)
        columns = {"U": case["tools"]["U"], **historical, "S2": case["tools"]["S2"], "X2": case["tools"]["X2"], "SX2": case["tools"]["SX2"]}
        maps = {name: _texts(tools) for name, tools in columns.items()}
        for name, mapping in maps.items():
            if set(mapping) != set(maps["U"]):
                raise AmendmentFailure(f"{case_id} {name} description slots differ from U")
        keys = list(maps["U"])
        fields = []
        for key in keys:
            values = {name: maps[name].get(key) for name in maps}
            if len(set(values.values())) == 1:
                continue
            index, pointer = key
            fields.append({
                "tool_index": index,
                "function_name": case["tools"]["U"][index]["function"]["name"],
                "pointer": pointer,
                "texts": values,
            })
        rows.append({
            "case_id": case_id,
            "category": case["category"],
            "exposed": True,
            "amendment_noop": case["noop"],
            "arms_equal_to_u": [name for name, tools in columns.items() if tools == columns["U"]],
            "fields_that_differ": fields,
        })
    return rows


def _ledger_s2(row: dict) -> dict:
    return {
        "occurrence_id": row["occurrence_id"],
        "case_id": row["case_id"],
        "category": row["category"],
        "tool_index": row["tool_index"],
        "function_name": row["function_name"],
        "pointer": row["pointer"],
        "context_id": row["context_id"],
        "candidate_id": row["candidate_id"],
        "reused": row["reused"],
        "first_occurrence_id": row["first_occurrence_id"],
        "editor_input": row["editor_input"],
        "original": row["original"],
        "candidate": row["candidate"],
        "final": row["final"],
        "adopted": row["adopted"],
        "keep_reason": row["keep_reason"],
        "keep_detail": row["keep_detail"],
        "change_class": row["change_class"],
        "meaningful": row["meaningful"],
        "cosmetic": row["cosmetic"],
        "facts": row["facts"],
    }


def _ledger_x2(row: dict) -> dict:
    return {
        "occurrence_id": row["occurrence_id"],
        "case_id": row["case_id"],
        "category": row["category"],
        "tool_index": row["tool_index"],
        "function_name": row["function_name"],
        "pointer": row["pointer"],
        "catalogue_input": row["catalogue_input"],
        "s2_hidden": row["s2_hidden"],
        "control": row["control"],
        "rival": row["rival"],
        "axis": row["axis"],
        "evidence": row["evidence"],
        "rejected_rivals": row["rejected_rivals"],
        "cue": row["cue"],
        "no_cue_reason": row["no_cue_reason"],
    }


def _source_diff(root: Path) -> str:
    parts = [f"# Offline amendment source diff against {BASE_COMMIT}\n"]
    base_main = root / "src" / "tool_compression" / "revision_pins" / "__main__.py.at-62bab379"
    current_main = root / "src" / "tool_compression" / "__main__.py"
    if not base_main.is_file():
        raise AmendmentFailure("the pinned base __main__.py is missing")
    parts.append(_unified(
        base_main.read_text(encoding="utf-8"),
        current_main.read_text(encoding="utf-8"),
        "a/src/tool_compression/__main__.py",
        "b/src/tool_compression/__main__.py",
    ))
    for relative in (
        "src/tool_compression/amendment_s2.py",
        "src/tool_compression/amendment_x2.py",
        "src/tool_compression/amendment_bundle.py",
        "tests/test_amendment_s2x2.py",
        "src/tool_compression/tiktoken_cache/README.md",
        "src/tool_compression/revision_pins/__main__.py.at-62bab379",
    ):
        text = (root / relative).read_text(encoding="utf-8")
        parts.append(_unified("", text, "/dev/null", f"b/{relative}"))
    return "\n".join(part.rstrip("\n") for part in parts) + "\n"


def _unified(old: str, new: str, fromfile: str, tofile: str) -> str:
    diff = "".join(unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True), fromfile=fromfile, tofile=tofile))
    if diff and not diff.endswith("\n"):
        diff += "\n"
    return diff


def _file_sha(path: Path) -> str:
    return _sha256(path.read_bytes())


def _revision(root: Path, budget: TiktokenCounter, sensitivity: TiktokenCounter) -> dict:
    def pin(relative: str) -> str:
        return _file_sha(root / relative)
    return {
        "sample": SAMPLE,
        "base_commit": BASE_COMMIT,
        "pr12_branch_for_the_pull_request_base": PR12_BRANCH,
        "gorilla_commit": GORILLA_COMMIT,
        "conversion": "to_openai_completions_tools",
        "conversion_float_suffix": CONVERSION_FLOAT_SUFFIX,
        "questions_used": False,
        "gold_used": False,
        "outcomes_used": False,
        "part_a_scores_used": False,
        "provider_called": False,
        "live": False,
        "tokenizer": {
            "selection": budget.name,
            "selection_backend": budget.backend,
            "sensitivity_not_used_for_selection": sensitivity.name,
            "sensitivity_backend": sensitivity.backend,
            "pinned_package": "tiktoken==0.14.0",
        },
        "source_sha256": {
            "src/tool_compression/convert.py": pin("src/tool_compression/convert.py"),
            "src/tool_compression/config.py": pin("src/tool_compression/config.py"),
            "src/tool_compression/evaluation.py": pin("src/tool_compression/evaluation.py"),
            "src/tool_compression/amendment_s2.py": pin("src/tool_compression/amendment_s2.py"),
            "src/tool_compression/amendment_x2.py": pin("src/tool_compression/amendment_x2.py"),
            "src/tool_compression/amendment_bundle.py": pin("src/tool_compression/amendment_bundle.py"),
            "src/tool_compression/__main__.py": pin("src/tool_compression/__main__.py"),
            "src/tool_compression/revision_pins/__main__.py.at-62bab379": pin("src/tool_compression/revision_pins/__main__.py.at-62bab379"),
            "tests/test_amendment_s2x2.py": pin("tests/test_amendment_s2x2.py"),
            "src/tool_compression/tiktoken_cache/README.md": pin("src/tool_compression/tiktoken_cache/README.md"),
            "src/tool_compression/tiktoken_cache/fb374d419588a4632f3f557e76b4b70aebbca790": TOKENIZER_CACHE["o200k_base"]["sha256"],
            "src/tool_compression/tiktoken_cache/9b5ad71b2ce5302211f9c61530b329a4922fc6a4": TOKENIZER_CACHE["cl100k_base"]["sha256"],
        },
    }


def _config_document(budget: TiktokenCounter, sensitivity: TiktokenCounter) -> dict:
    return {
        "local_budget_tokenizer": budget.name,
        "sensitivity_tokenizer_not_used_for_selection": sensitivity.name,
        "tokenizer_backend": budget.backend,
        "placeholder_model": PLACEHOLDER_MODEL,
        "temperature": BFCL_DEFAULT_TEMPERATURE,
        "store": BFCL_STORE,
        "request_envelope": "model, temperature, store, tools",
        "messages": "omitted; questions are not in this packet",
        "t1_t2_methods_on_record_unchanged": list(METHODS),
        "closed_target_provider_input_reduction": "1/10",
        "closed_target_reopened": False,
        "official_v1_1_retuned": False,
        "edits_selected_by_token_count": False,
        "edits_selected_by_accuracy": False,
        "billed_projection_included": False,
        "hard_cap_proposed": False,
    }


def _rules() -> str:
    return """# S2 / X2 / SX2 editor rules

These rules are the offline editor. They do not score a case, call a model, or reopen the closed v1.1 comparison.

## Input

U is the official converted catalogue, copied byte for byte. The conversion is `to_openai_completions_tools`. A float BFCL value keeps `format: float`, `type: number`, and the suffix ` This is a float type value.` Questions, gold calls, and outcomes are not inputs.

## S2

Visit every function description, parameter description, and nested description. The editor receives that tool's complete original definition and schema, never a sibling tool. A candidate is the shortest locally verified rewrite this procedure can prove:

- drop a float-suffix sentence only when the schema still says `format: float` and `type: number`;
- drop a quoted enum sentence only when the quoted set equals the unchanged schema enum and the sentence does not define a value;
- drop a default sentence only when the parsed literal equals the unchanged schema default;
- drop a within-tool restatement only when the final function description still contains the recovered wording;
- turn an exact `This function ...` frame into its direct action without adding a claim;
- turn `A flag to determine whether to ...` into the whether-clause. `get_angles` stays `Whether to calculate the internal angles`. The schema default stays in place.

A candidate that is not strictly shorter, that changes only spacing or punctuation, or that drops a condition, negation, `whether`, `internal`, a literal, or a unit, is rejected. Otherwise the original stays, with `already_minimal`, `ambiguous_source`, or `no_shorter_faithful_candidate`. The same decision is reused only when the field and the complete tool context match. Every occurrence is logged.

## X2

Qualify each target on the original ordered catalogue. S2 is hidden. A control, one tool, gets no cue. A rival has to serve one common user need, with evidence on both sides from the original function text, parameter text, or immutable schema. An unrelated tool does not veto another pair. The closest rival is the one with the longer shared wording, then the lower original index. At most one cue is appended to the target's function description. The cue names that rival once, states the supported axis, and does not say that only one tool can do the job. An unqualified target stays verbatim.

The verified axes are a shared action with the same required parameter names and types and one short substitution, and named polynomial coefficients versus one ordered coefficient array.

## SX2

Start from the exact S2 tools. At the function description X2 selected, append one ASCII space and the identical X2 cue bytes. Every other field stays S2. SX2 is not edited again.

## Controls

For a one-tool catalogue, the X2 tool input equals the U tool input byte for byte, and the SX2 tool input equals the S2 tool input byte for byte. The file wrapper may carry a different condition label. The compared bytes are the tool list and the request envelope `{model, temperature, store, tools}`.
"""


def _readme() -> str:
    return f"""# Offline S2 / X2 / SX2 amendment

This packet builds S2, X2, and SX2 beside the official U catalogues for the same 200 `multiple`, 400 `simple_python`, and 240 `irrelevance` cases. It does not replace U, S, X, or SX. It does not score Part A, read a question or gold answer, call a provider, or merge.

U files under `rendered/<case>/U.json` are byte copies of `docs/official-840/catalogues/U/<case>.json`.

## Reproduce

```bash
{REPRODUCTION}
```

The command rebuilds the edits in memory, compares them with these files, and repeats the mocked completion with socket construction denied. It does not accept `--live`. `--freeze` rewrites this directory and is not the check.

Local token counts use `o200k_base`. `cl100k_base` is a recount only. Neither number is provider usage, a billed saving, or the closed 1/10 target. The BPE tables are the committed files in `src/tool_compression/tiktoken_cache`. The check does not download them.
"""


def _mock_child() -> dict:
    code = r"""
import json, socket, sys
blocked = {"socket": 0, "create_connection": 0}
def deny_socket(*_args, **_kwargs):
    blocked["socket"] += 1
    raise OSError("network denied")
def deny_create(*_args, **_kwargs):
    blocked["create_connection"] += 1
    raise OSError("network denied")
socket.socket = deny_socket
socket.create_connection = deny_create
denied = False
try:
    socket.socket()
except OSError as exc:
    denied = str(exc) == "network denied"
result = {"provider": "mock", "status": "completed_without_network", "request_sent": False, "output": None}
loaded = [name for name in ("tool_compression.official_840_provider", "tool_compression.usx_provider", "urllib.request") if name in sys.modules]
ok = denied and blocked["socket"] == 1 and blocked["create_connection"] == 0 and not loaded and result["request_sent"] is False
payload = {
    "enforced": ok,
    "socket_probes_denied": blocked["socket"],
    "create_connection_calls": blocked["create_connection"],
    "mock_provider": result,
    "api_keys_read": False,
    "provider_modules_loaded": loaded,
    "network_access": "denied",
}
json.dump(payload, sys.stdout, sort_keys=True)
if not ok:
    sys.exit(2)
"""
    completed = subprocess.run(
        [sys.executable, "-c", code],
        check=False,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(repo_root() / "src"), "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if completed.returncode != 0:
        raise AmendmentFailure("mock network denial was not enforced: " + completed.stderr.strip())
    payload = json.loads(completed.stdout)
    if not payload["enforced"]:
        raise AmendmentFailure("mock network denial reported a miss")
    return payload


def _fence(text: str) -> str:
    fence = "~~~~"
    while fence in text:
        fence += "~"
    return f"{fence}\n{text}\n{fence}"


def _markdown_ratio(block: dict) -> str:
    lines = ["| measure | count |", "| --- | --- |"]
    for key, value in block.items():
        lines.append(f"| {key} | {value['text']} |")
    return "\n".join(lines)


def _markdown_deltas(title: str, block: dict) -> str:
    lines = [f"### {title}", "", "| arm | tokens |", "| --- | ---: |"]
    for arm in ARMS:
        lines.append(f"| {arm} | {block['totals'][arm]} |")
    lines.extend(["", "| signed delta | tokens |", "| --- | ---: |"])
    for name, value in block["signed_deltas"].items():
        lines.append(f"| {name} | {value} |")
    if "label" in block:
        lines.extend(["", block["label"]])
    return "\n".join(lines)


def _comparison_markdown(packet: dict) -> str:
    lines = [
        "# S2 / X2 / SX2 comparison",
        "",
        "Local counts only. A negative signed delta means the first arm has fewer local tokens than the second. These figures are not billed savings, accuracy, or the closed 1/10 target. No hard cap is proposed.",
        "",
        "The request count serializes `{model: UNSELECTED, temperature: 0.001, store: false, tools}` and omits messages because this packet does not load questions. `cl100k_base` is not used to choose an edit.",
        "",
        "Gold-linked rival check: not run. It would be a scoring diagnostic after this freeze, and gold is not an editing input.",
        "",
        "## Fixtures",
        "",
        "```json",
        json.dumps(packet["fixture_report"], indent=2, ensure_ascii=False),
        "```",
        "",
        "## Exposed formative cases",
        "",
        "These 12 cases were opened by the earlier pilot. They are identified whether or not this amendment changes them.",
        "",
    ]
    for row in packet["formative"]:
        lines.append(
            f"- `{row['case_id']}` ({row['category']}): amendment no-op `{row['amendment_noop']}`; "
            f"arms equal to U: {', '.join(row['arms_equal_to_u']) or 'none'}"
        )
    lines.extend(["", "## No-op cases", "", "A no-op case has no adopted S2 field and no X2 cue. The full id list is below, not only the changed cases.", ""])
    for category in CATEGORIES:
        ids = [case["case_id"] for case in packet["cases"] if case["category"] == category and case["noop"]]
        lines.append(f"### {category} ({len(ids)})")
        lines.append("")
        lines.append(", ".join(f"`{case_id}`" for case_id in ids) if ids else "None.")
        lines.append("")
    lines.extend(["## Counts", ""])
    for name, scope in packet["scopes"].items():
        lines.extend([f"## {name}", ""])
        lines.append("Fields")
        lines.append("")
        lines.append(_markdown_ratio(scope["fields"]))
        lines.extend(["", "Tools", ""])
        lines.append(_markdown_ratio(scope["tools"]))
        lines.extend(["", "Cases", ""])
        lines.append(_markdown_ratio(scope["case_status"]))
        lines.extend(["", "Cues", ""])
        lines.append(_markdown_ratio(scope["cues"]))
        lines.extend(["", _markdown_deltas("Field tokens, o200k_base", scope["field_tokens_o200k_base"]), ""])
        lines.extend([_markdown_deltas("Whole request tokens without messages, o200k_base", scope["request_tokens_o200k_base_without_messages"]), ""])
        lines.extend([_markdown_deltas("Field tokens, cl100k_base, not used for selection", scope["field_tokens_cl100k_base_not_used_for_selection"]), ""])
        lines.extend([_markdown_deltas("Whole request tokens without messages, cl100k_base, not used for selection", scope["request_tokens_cl100k_base_not_used_for_selection"]), ""])
        lines.extend(["Cue cost across all description fields in the case. Denominator is every case in this scope.", ""])
        lines.append(_markdown_ratio(scope["cue_cost_all_description_fields"]))
        lines.extend(["", "Cue cost on the request envelope. Denominator is every case in this scope.", ""])
        lines.append(_markdown_ratio(scope["cue_cost_request_without_messages"]))
        lines.extend(["", "Cue cost on the one cued function field. Denominator is cued fields in this scope.", ""])
        lines.append(_markdown_ratio(scope["cue_cost_on_the_cued_function_field"]))
        lines.append("")
    lines.extend([
        "## Where the cue spends the saving",
        "",
        "Cases whose cue exceeds the S2 field-token saving:",
        "",
        ", ".join(f"`{case['case_id']}`" for case in packet["cases"] if case["field_cue_class"] == "cue_exceeds_savings") or "None.",
        "",
        "Cases whose cue exceeds the S2 request-token saving:",
        "",
        ", ".join(f"`{case['case_id']}`" for case in packet["cases"] if case["request_cue_class"] == "cue_exceeds_savings") or "None.",
        "",
        "Cued function fields whose own cue exceeds that field's S2 saving:",
        "",
    ])
    spent = [
        f"`{item['case_id']}` {item['function_name']} ({item['class']}, SX2-U {item['deltas']['SX2-U']})"
        for case in packet["cases"]
        for item in case["cued_field_classes"]
        if item["class"] in {"cue_exceeds_savings", "cue_cost_without_s2_savings"}
    ]
    lines.append("; ".join(spent) if spent else "None.")
    lines.extend(["", "## Formative side by side", "", "Paths: `#11 S` is `docs/semantic-audit-pilot/rendered/<id>/S.json`. `#11 X` and `#11 SX` are `docs/semantic-audit-pilot/cue-revision/rendered/<id>/`. `#12` is `docs/official-840/rendered/<id>/`. S2, X2, and SX2 are this packet.", ""])
    for row in packet["formative"]:
        lines.append(f"### {row['case_id']}")
        lines.append("")
        lines.append(f"Exposed. Amendment no-op: `{row['amendment_noop']}`.")
        lines.append("")
        if not row["fields_that_differ"]:
            lines.append("No description differs across U, the systems-test edits, the #12 edits, and this amendment.")
            lines.append("")
            continue
        for field in row["fields_that_differ"]:
            lines.append(f"#### {field['function_name']} `{field['pointer']}`")
            lines.append("")
            for key, label in COMPARISON_COLUMNS:
                lines.append(f"{label}")
                lines.append("")
                lines.append(_fence(field["texts"][key] if field["texts"][key] is not None else ""))
                lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _counterexample_markdown(packet: dict) -> str:
    rows = packet["counterexamples"]
    quiet = rows["x2_uncued_neighbor"]
    control = rows["x2_control"]
    mixed = rows["x2_uncued_while_neighbor_cued"]
    ambiguous = rows["s2_ambiguous_source"]
    return "\n".join([
        "# Unchanged counterexamples",
        "",
        "These rows are also in the occurrence ledgers. They show a KEEP, a refused cue, and a control.",
        "",
        "## S2 already minimal",
        "",
        f"`{rows['s2_already_minimal']['occurrence_id']}` kept `{rows['s2_already_minimal']['final']}` because `{rows['s2_already_minimal']['keep_reason']}`.",
        "",
        "## S2 no shorter faithful candidate",
        "",
        f"`{rows['s2_no_shorter_faithful_candidate']['occurrence_id']}` kept the method prose because `{rows['s2_no_shorter_faithful_candidate']['keep_detail']}`.",
        "",
        "## S2 ambiguous source",
        "",
        f"`{ambiguous['case_id']}` `{ambiguous['function_name']}` `{ambiguous['pointer']}` kept `{ambiguous['original']}` because {ambiguous['keep_detail']}",
        "",
        "## X2 cued pair",
        "",
        f"`{rows['x2_cued_pair']['occurrence_id']}` cue: {rows['x2_cued_pair']['cue']}",
        "",
        "## X2 uncued neighbor",
        "",
        f"`{quiet['occurrence_id']}` has no cue. {quiet['no_cue_reason']}",
        "",
        "## X2 single-tool control",
        "",
        f"`{control['occurrence_id']}` cue is empty. {control['no_cue_reason']}",
        "",
        "## X2 target left verbatim while a neighbor is cued",
        "",
        f"`{mixed['case_id']}` `{mixed['row']['function_name']}` has no cue. {mixed['row']['no_cue_reason']}",
        "",
    ])


def _files(packet: dict) -> dict[str, str]:
    files = {
        "README.md": _readme(),
        "RULES.md": _rules(),
        "revision.json": _json_text(packet["revision"]),
        "source.diff": packet["source_diff"],
        "config.json": _json_text(packet["config"]),
        "tokenizer.json": _json_text(packet["revision"]["tokenizer"]),
        "manifest.json": _json_text(packet["manifest"]),
        "ledgers/s2.jsonl": _jsonl(packet["s2_ledger"]),
        "ledgers/x2.jsonl": _jsonl(packet["x2_ledger"]),
        "ledgers/counterexamples.md": _counterexample_markdown(packet),
        "comparison/sheet.md": packet["comparison_markdown"],
        "comparison/sheet.json": _json_text(packet["sheet"]),
        "checks/fixtures.json": _json_text(packet["fixture_report"]),
        "checks/invariants.json": _json_text(packet["invariants"]),
        "checks/mock-network-denial.json": _json_text(packet["mock"]),
        "checks/field-tokens.jsonl": _jsonl(packet["field_token_rows"]),
        "checks/request-tokens.jsonl": _jsonl(packet["request_token_rows"]),
    }
    for case in packet["cases"]:
        case_id = case["case_id"]
        files[f"rendered/{case_id}/U.json"] = case["u_text"]
        for arm in ("S2", "X2", "SX2"):
            files[f"rendered/{case_id}/{arm}.json"] = _json_text(
                _arm_document(case_id, case["category"], arm, case["tools"][arm])
            )
    return files


def _assemble() -> dict:
    root = repo_root()
    _closed_records(root)
    ids = _case_ids(root)
    formative = _formative_ids(root)
    missing = [case_id for case_id in formative if case_id not in ids]
    if missing:
        raise AmendmentFailure("formative id missing from U: " + ", ".join(missing))
    _pin_tokenizer_cache()
    budget = TiktokenCounter(LOCAL_TOKENIZER)
    sensitivity = TiktokenCounter(SENSITIVITY_TOKENIZER)
    if budget.name != "o200k_base" or sensitivity.name != "cl100k_base":
        raise AmendmentFailure("tokenizer pin drifted")
    cases = []
    for case_id in ids:
        raw, document = _load_u(case_id)
        category = _category(case_id)
        if category == "multiple" and len(document["tools"]) < 2:
            raise AmendmentFailure(f"{case_id} is multiple with fewer than two tools")
        if category != "multiple" and len(document["tools"]) != 1:
            raise AmendmentFailure(f"{case_id} is a control category with more than one tool")
        case = edit_case(document["tools"], case_id, category)
        case["u_bytes"] = raw
        case["u_text"] = raw.decode("utf-8")
        case["exposed"] = case_id in formative
        _count_tokens(case, budget, sensitivity)
        _annotate(case)
        cases.append(case)
    _link_reuse(cases)
    by_id = {case["case_id"]: case for case in cases}
    fixture_errors = _fixture_errors(by_id)
    if fixture_errors:
        raise AmendmentFailure("fixtures failed closed:\n" + "\n".join(fixture_errors))
    controls = [case for case in cases if case["control"]]
    if len(controls) != 640 or any(case["cued_tools"] for case in controls):
        raise AmendmentFailure("single-tool controls did not stay at 640 with zero cues")
    if any(case["fields_cosmetic"] for case in cases):
        raise AmendmentFailure("a cosmetic edit was adopted")
    mock = _mock_child()
    mock["editor_ran_with_socket_construction_denied"] = True
    scopes = {
        "all_840": _scope(cases),
        "multiple": _scope([case for case in cases if case["category"] == "multiple"]),
        "simple_python": _scope([case for case in cases if case["category"] == "simple_python"]),
        "irrelevance": _scope([case for case in cases if case["category"] == "irrelevance"]),
        "formative_12": _scope([case for case in cases if case["exposed"]]),
        "excluding_formative_12": _scope([case for case in cases if not case["exposed"]]),
    }
    formative_rows = _formative_sheet(by_id, formative)
    counterexamples = _counterexamples(by_id)
    packet = {
        "cases": cases,
        "revision": _revision(root, budget, sensitivity),
        "source_diff": _source_diff(root),
        "config": _config_document(budget, sensitivity),
        "mock": mock,
        "scopes": scopes,
        "formative": formative_rows,
        "counterexamples": counterexamples,
        "fixture_report": {
            "passed": True,
            "multiple_34": {"math_gcd": GCD_CUE, "math_lcm": LCM_CUE, "math_sqrt_cue": ""},
            "multiple_35": {"calculate_lcm": CALC_LCM_CUE, "calculate_gcd": CALC_GCD_CUE},
            "multiple_11": {
                "math_roots_quadratic": QUADRATIC_CUE,
                "math_roots_cubic": CUBIC_CUE,
                "math_roots_polynomial": POLYNOMIAL_CUE,
            },
            "get_angles": GET_ANGLES,
            "controls_checked": 640,
            "control_examples": ["simple_python_0", "irrelevance_0"],
            "control_comparison": "tool list and request envelope bytes; wrapper condition labels may differ",
            "gold_linked_rival_check": {"ran": False, "reason": "Scoring-only diagnostic. Gold is not loaded."},
        },
        "invariants": {
            "passed": True,
            "cases": 840,
            "controls": 640,
            "structural_comparison": "value comparison of every non-description node, plus equal serialized bytes after description slots are blanked",
            "failures": [],
        },
        "manifest": {
            "sample": SAMPLE,
            "base_commit": BASE_COMMIT,
            "cases": 840,
            "counts": EXPECTED_COUNTS,
            "arms": list(ARMS),
            "ids_in_file_order": ids,
            "formative_12": formative,
            "questions_stored": False,
            "gold_stored": False,
            "u_source": "docs/official-840/catalogues/U",
            "reproduction": REPRODUCTION,
        },
    }
    packet["s2_ledger"] = [_ledger_s2(row) for case in cases for row in case["s2_rows"]]
    packet["x2_ledger"] = [_ledger_x2(row) for case in cases for row in case["x2_rows"]]
    packet["field_token_rows"] = [row for case in cases for row in case["field_rows"]]
    packet["request_token_rows"] = [
        {
            "case_id": case["case_id"],
            "category": case["category"],
            "o200k_base": case["request_tokens"],
            "cl100k_base": case["request_tokens_cl100k"],
            "field_cue_class": case["field_cue_class"],
            "request_cue_class": case["request_cue_class"],
        }
        for case in cases
    ]
    packet["sheet"] = {
        "label": "Local token counts. Not billed usage, accuracy, or a proposed cap.",
        "gold_linked_rival_check": packet["fixture_report"]["gold_linked_rival_check"],
        "scopes": scopes,
        "formative": formative_rows,
        "noop_ids": [case["case_id"] for case in cases if case["noop"]],
        "exposed_ids": formative,
        "cued_case_ids": [case["case_id"] for case in cases if case["cued_tools"]],
        "cue_exceeds_field_savings": [case["case_id"] for case in cases if case["field_cue_class"] == "cue_exceeds_savings"],
        "cue_exceeds_request_savings": [case["case_id"] for case in cases if case["request_cue_class"] == "cue_exceeds_savings"],
    }
    packet["comparison_markdown"] = _comparison_markdown(packet)
    return packet


def build_packet() -> dict:
    """Rebuild the offline packet. Socket construction is denied for the whole build."""
    with _network_denied():
        return _assemble()


def _hash_map(files: dict[str, str]) -> dict:
    return {relative: _sha256(text.encode("utf-8")) for relative, text in sorted(files.items())}


def freeze() -> dict:
    packet = build_packet()
    files = _files(packet)
    for relative, text in files.items():
        _write(relative, text)
    digest = _hash_map(files)
    _write("checks/hashes.json", _json_text(digest))
    return {"froze": True, "cases": 840, "files": len(files) + 1, "bundle": str(bundle_dir())}


def check() -> dict:
    packet = build_packet()
    files = _files(packet)
    root = bundle_dir()
    errors = []
    for relative, text in files.items():
        path = root / relative
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            errors.append(f"drift {relative}")
    digest = _hash_map(files)
    hash_path = root / "checks" / "hashes.json"
    if not hash_path.is_file() or json.loads(hash_path.read_text(encoding="utf-8")) != digest:
        errors.append("drift checks/hashes.json")
    extra = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative != "checks/hashes.json" and relative not in files:
            extra.append(relative)
    if extra:
        errors.append("unexpected bundle files: " + ", ".join(sorted(extra)[:20]))
    if errors:
        raise AmendmentFailure("offline check failed:\n" + "\n".join(errors[:30]))
    return {"passed": True, "cases": 840, "files": len(files) + 1, "reproduction": REPRODUCTION}
