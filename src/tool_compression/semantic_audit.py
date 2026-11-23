"""Mechanical checks for the offline 12-case U/S/X/SX pilot.

The editor's sealed records are data. This module only renders them, checks
the allowlisted description boundary, and counts local tokens. It does not
call a model, score a case, or retune a compressor.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json

from tool_compression.adapter import description_slots
from tool_compression.count import TiktokenCounter, dump_request
from tool_compression.prepare import assemble_request
from tool_compression.validate import catalogue_violations

SEED = "semantic-audit-pilot-01"
CONDITIONS = ("U", "S", "X", "SX")
CUE_SEPARATOR = " "
CUE_POINTER = "/function/description"
TAKE = {"multiple": 8, "simple_python": 2, "irrelevance": 2}
SOURCE_SHA256 = {
    "multiple": "aef168155ebd74b7ac2401198b201343bc7d16d7a3d7e0d4e6d8ee82c6969b2a",
    "simple_python": "82dd63ba502eb2520c6b5d1d9a5c4b590e03ff261565175561f6228a367d1991",
    "irrelevance": "2b6ed4c2e992cdcf5f1678a701851f944bef7550ee026ed1ddb89efed5be01a6",
}
RANKED_TSV_SHA256 = "e56fb0e69e45868dc9d9f1f35492b06a1329e286ddbbd417c6c18d1d354f1bc3"
SELECTED_TSV_SHA256 = "b613f6d31b3e6ffea5520393bf6d9fa16082c84400274094d040b2a82e3b0360"
GORILLA_COMMIT = "6ea57973c7a6097fd7c5915698c54c17c5b1b6c8"
HIDDEN_KEYS = frozenset(
    {
        "question",
        "possible_answer",
        "ground_truth",
        "answer",
        "answers",
        "label",
        "labels",
    }
)


def package_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "docs" / "semantic-audit-pilot"


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: Path, payload) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def selection_digest(category: str, case_id: str, seed: str = SEED) -> str:
    """SHA-256 of the UTF-8 string ``seed|category|case_id``, with no newline."""
    return sha256(f"{seed}|{category}|{case_id}".encode("utf-8")).hexdigest()


def rank_ids(pairs: list[tuple[str, str]], seed: str = SEED) -> list[dict]:
    """Sort each category by the selection digest, then by case id.

    ``pairs`` is ``(category, case_id)`` only. The digest does not read a
    question, a gold call, or a description.
    """
    grouped: dict[str, list[tuple[str, str]]] = {}
    for category, case_id in pairs:
        grouped.setdefault(category, []).append(
            (selection_digest(category, case_id, seed), case_id)
        )
    ranked = []
    for category in ("multiple", "simple_python", "irrelevance"):
        ordered = sorted(grouped.get(category, []), key=lambda item: (item[0], item[1]))
        for rank, (digest, case_id) in enumerate(ordered, start=1):
            ranked.append(
                {
                    "category": category,
                    "case_id": case_id,
                    "sha256": digest,
                    "rank": rank,
                    "selected": rank <= TAKE[category],
                }
            )
    return ranked


def ranked_tsv(rows: list[dict]) -> str:
    return "".join(
        f"{row['category']}\t{row['case_id']}\t{row['sha256']}\t{row['rank']}\n" for row in rows
    )


def file_sha256(path: Path) -> str:
    return sha256(Path(path).read_bytes()).hexdigest()


def _parts(pointer: str) -> list[str]:
    parts = pointer.strip("/").split("/")
    if not parts or parts[-1] != "description":
        raise ValueError(f"description pointer required, got {pointer}")
    return parts


def get_text(tool: dict, pointer: str) -> str:
    node = tool
    for part in _parts(pointer)[:-1]:
        if not isinstance(node, dict) or part not in node:
            raise KeyError(pointer)
        node = node[part]
    if not isinstance(node, dict) or not isinstance(node.get("description"), str):
        raise KeyError(pointer)
    return node["description"]


def set_text(tool: dict, pointer: str, text: str) -> None:
    node = tool
    for part in _parts(pointer)[:-1]:
        node = node[part]
    node["description"] = text


def _index_fields(record: dict) -> dict[str, list[dict]]:
    return {case["case_id"]: case["fields"] for case in record["cases"]}


def _index_cues(record: dict) -> dict[str, list[dict]]:
    return {case["case_id"]: case["tools"] for case in record["cases"]}


def render_conditions(tools: list[dict], fields: list[dict], cue_tools: list[dict]) -> dict[str, list[dict]]:
    """Build U, S, X, and SX from one unmodified catalogue and two sealed records.

    S replaces allowlisted strings. X appends a sealed cue to the original
    function description. SX appends that same cue to the S string. A missing
    cue leaves X equal to U and SX equal to S.
    """
    untouched = deepcopy(tools)
    compressed = deepcopy(tools)
    for field in fields:
        tool = compressed[field["tool_index"]]
        current = get_text(tool, field["pointer"])
        if current != field["original"]:
            raise ValueError(
                f"S original does not match U at {field['tool_index']} {field['pointer']}"
            )
        set_text(tool, field["pointer"], field["replacement"])
    contrasted = deepcopy(untouched)
    both = deepcopy(compressed)
    for item in cue_tools:
        cue = item.get("cue")
        if not cue:
            continue
        pointer = item.get("pointer", CUE_POINTER)
        if pointer != CUE_POINTER:
            raise ValueError("X cues attach only to the function description")
        suffix = CUE_SEPARATOR + cue
        for catalogue in (contrasted, both):
            tool = catalogue[item["tool_index"]]
            set_text(tool, pointer, get_text(tool, pointer) + suffix)
    return {"U": untouched, "S": compressed, "X": contrasted, "SX": both}


def slot_map(tools: list[dict]) -> dict[tuple[int, str], str]:
    found = {}
    for index, tool in enumerate(tools):
        for pointer, _container, _key in description_slots(tool):
            found[(index, pointer)] = get_text(tool, pointer)
    return found


def composition_errors(rendered: dict[str, list[dict]], fields: list[dict], cue_tools: list[dict]) -> list[str]:
    """Return mechanical mismatches. An empty list means S, X, and SX agree."""
    errors = []
    base_u = slot_map(rendered["U"])
    base_s = slot_map(rendered["S"])
    base_x = slot_map(rendered["X"])
    base_sx = slot_map(rendered["SX"])
    if set(base_u) != set(base_s) or set(base_u) != set(base_x) or set(base_u) != set(base_sx):
        errors.append("description slots differ across conditions")
    field_index = {(field["tool_index"], field["pointer"]): field for field in fields}
    if set(field_index) != set(base_u):
        errors.append("S record does not cover every eligible description")
    cues = {}
    for item in cue_tools:
        cues[(item["tool_index"], item.get("pointer", CUE_POINTER))] = item.get("cue") or ""
    for key, original in base_u.items():
        field = field_index.get(key)
        if field is None:
            errors.append(f"missing S field {key}")
            continue
        if base_s[key] != field["replacement"] or field["original"] != original:
            errors.append(f"S replacement mismatch {key}")
        cue = cues.get(key, "")
        if key[1] != CUE_POINTER:
            cue = ""
            if cues.get(key):
                errors.append(f"cue attached outside the function description {key}")
        expected_x = original if not cue else original + CUE_SEPARATOR + cue
        expected_sx = base_s[key] if not cue else base_s[key] + CUE_SEPARATOR + cue
        if base_x[key] != expected_x:
            errors.append(f"X is not U plus the sealed cue {key}")
        if base_sx[key] != expected_sx:
            errors.append(f"SX is not S plus the sealed cue {key}")
    return errors


def structural_errors(rendered: dict[str, list[dict]]) -> list[str]:
    errors = []
    for condition in ("S", "X", "SX"):
        violations = catalogue_violations(rendered["U"], rendered[condition])
        for violation in violations:
            errors.append(f"{condition}:{violation}")
    return errors


def sibling_name_errors(rendered: dict[str, list[dict]]) -> list[str]:
    """S must not name another tool in the same catalogue."""
    names = [tool["function"]["name"] for tool in rendered["U"]]
    errors = []
    for index, tool in enumerate(rendered["S"]):
        for pointer, _container, _key in description_slots(tool):
            text = get_text(tool, pointer)
            for other, name in enumerate(names):
                if other != index and name in text:
                    errors.append(f"S names sibling {name} at tool {index} {pointer}")
    return errors


def schema_signature(tool: dict) -> str:
    """Identity of one converted tool with description strings removed."""
    function = tool["function"]
    payload = {"name": function.get("name"), "parameters": _strip_descriptions(function.get("parameters"))}
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(raw.encode("utf-8")).hexdigest()


def parameter_signature(tool: dict) -> str:
    """Parameter schema only, so repeated shapes group even when names differ."""
    payload = _strip_descriptions(tool["function"].get("parameters"))
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(raw.encode("utf-8")).hexdigest()


def _strip_descriptions(node):
    if isinstance(node, dict):
        return {
            key: _strip_descriptions(value)
            for key, value in node.items()
            if key != "description"
        }
    if isinstance(node, list):
        return [_strip_descriptions(value) for value in node]
    return node


def resolve_path(tool: dict, pointer: str):
    node = tool
    for part in pointer.strip("/").split("/"):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(pointer)
        node = node[part]
    return node


def local_counter() -> TiktokenCounter:
    return TiktokenCounter("o200k_base")


def field_token_rows(case_id: str, rendered: dict[str, list[dict]], counter: TiktokenCounter) -> list[dict]:
    rows = []
    slots = list(slot_map(rendered["U"]))
    for tool_index, pointer in slots:
        row = {"case_id": case_id, "tool_index": tool_index, "pointer": pointer}
        for condition in CONDITIONS:
            row[condition] = counter.count(get_text(rendered[condition][tool_index], pointer))
        rows.append(row)
    return rows


def sum_tokens(rows: list[dict], condition: str) -> int:
    return sum(row[condition] for row in rows)


def saving(baseline: int, variant: int) -> float | None:
    """``1 - sum(variant) / sum(U)``. This is a local ratio of totals."""
    if baseline == 0:
        return None
    return 1 - (variant / baseline)


def saving_block(totals: dict[str, int]) -> dict:
    return {
        "totals": {condition: totals[condition] for condition in CONDITIONS},
        "saving_vs_U": {condition: saving(totals["U"], totals[condition]) for condition in ("S", "X", "SX")},
    }


def aggregate_tokens(rows_by_case: dict[str, dict[str, int]], categories: dict[str, str]) -> dict:
    by_case = {case_id: saving_block(totals) for case_id, totals in rows_by_case.items()}
    by_category = {category: {condition: 0 for condition in CONDITIONS} for category in TAKE}
    overall = {condition: 0 for condition in CONDITIONS}
    for case_id, totals in rows_by_case.items():
        for condition in CONDITIONS:
            overall[condition] += totals[condition]
            by_category[categories[case_id]][condition] += totals[condition]
    return {
        "by_case": by_case,
        "by_category": {category: saving_block(totals) for category, totals in by_category.items()},
        "overall": saving_block(overall),
    }


def hidden_key_errors(node, path: str = "") -> list[str]:
    errors = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in HIDDEN_KEYS:
                errors.append(path + "/" + str(key))
            errors.extend(hidden_key_errors(value, path + "/" + str(key)))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            errors.extend(hidden_key_errors(value, f"{path}/{index}"))
    return errors


def iter_propositions(s_record: dict, x_record: dict):
    for case in s_record["cases"]:
        for field in case["fields"]:
            for proposition in field["propositions"]:
                yield case["case_id"], field, proposition
    for case in x_record["cases"]:
        for tool in case["tools"]:
            for proposition in tool.get("propositions", []):
                yield case["case_id"], tool, proposition


def fact_counts(s_record: dict, x_record: dict) -> dict:
    """Count inventoried propositions.

    A duplicate or an illustrative omission is not a lost fact. An uncertain
    proposition that stays in the text is retained and still preserved.
    """
    counts = {
        "propositions": 0,
        "preserved": 0,
        "lost": 0,
        "unsupported_additions": 0,
        "uncertain_retained": 0,
        "duplicate_or_illustration_omissions": 0,
        "s_propositions": 0,
        "x_propositions": 0,
    }
    for case in s_record["cases"]:
        for field in case["fields"]:
            for proposition in field["propositions"]:
                _accumulate(counts, proposition, "s_propositions")
    for case in x_record["cases"]:
        for tool in case["tools"]:
            for proposition in tool.get("propositions", []):
                _accumulate(counts, proposition, "x_propositions")
    return counts


def _accumulate(counts: dict, proposition: dict, family: str) -> None:
    counts["propositions"] += 1
    counts[family] += 1
    if proposition.get("unsupported"):
        counts["unsupported_additions"] += 1
    if proposition.get("uncertain") and proposition.get("decision") in {"KEEP", "UNCERTAIN"}:
        counts["uncertain_retained"] += 1
    if proposition.get("duplicate") or proposition.get("illustrative"):
        counts["duplicate_or_illustration_omissions"] += 1
    if proposition.get("lost"):
        counts["lost"] += 1
    elif not proposition.get("unsupported"):
        counts["preserved"] += 1


def ledger_errors(s_record: dict, catalogues: dict[str, list[dict]]) -> list[str]:
    errors = []
    for case in s_record["cases"]:
        tools = catalogues[case["case_id"]]
        for field in case["fields"]:
            original = get_text(tools[field["tool_index"]], field["pointer"])
            if original != field["original"]:
                errors.append(f"ledger original mismatch {case['case_id']} {field['pointer']}")
                continue
            replacement = field["replacement"]
            changed = original != replacement
            if changed == field.get("noop"):
                errors.append(f"noop flag mismatch {case['case_id']} {field['pointer']}")
            if field.get("noop") and not field.get("reason"):
                errors.append(f"no-op without a reason {case['case_id']} {field['pointer']}")
            if "Unlike " in replacement:
                errors.append(f"S contains a cross-tool cue {case['case_id']} {field['pointer']}")
            replacements = {
                (item["tool_index"], item["pointer"]): item["replacement"] for item in case["fields"]
            }
            for proposition in field["propositions"]:
                excerpt = proposition["excerpt"]
                start, end = proposition["span"]
                if original[start:end] != excerpt:
                    errors.append(f"span mismatch {proposition['id']}")
                if proposition.get("after") and proposition["after"] not in replacement and not proposition.get("lost"):
                    errors.append(f"after text missing {proposition['id']}")
                if proposition.get("illustrative") and excerpt in replacement:
                    errors.append(f"illustrative excerpt still present {proposition['id']}")
                if proposition.get("schema_path"):
                    try:
                        value = resolve_path(tools[field["tool_index"]], proposition["schema_path"])
                    except KeyError:
                        errors.append(f"schema path missing {proposition['id']}")
                        continue
                    if "schema_equals" in proposition and value != proposition["schema_equals"]:
                        errors.append(f"schema value mismatch {proposition['id']}")
                recovery_pointer = proposition.get("recovery_pointer")
                recovery_excerpt = proposition.get("recovery_excerpt")
                if recovery_pointer and recovery_excerpt:
                    host_u = get_text(tools[field["tool_index"]], recovery_pointer)
                    host_s = replacements[(field["tool_index"], recovery_pointer)]
                    if recovery_excerpt not in host_u or recovery_excerpt not in host_s:
                        errors.append(f"recovery excerpt missing {proposition['id']}")
    return errors


def load_package():
    root = package_dir()
    manifest = load_json(root / "selection" / "manifest.json")
    s_record = load_json(root / "edits" / "s-record.json")
    x_record = load_json(root / "edits" / "x-record.json")
    catalogues = {}
    for case in manifest["selected"]:
        payload = load_json(root / "rendered" / case["case_id"] / "U.json")
        catalogues[case["case_id"]] = payload["tools"]
    return manifest, s_record, x_record, catalogues


def verify_package() -> dict:
    """Check the committed 12-case package. Raises ValueError on the first failure class."""
    root = package_dir()
    manifest, s_record, x_record, catalogues = load_package()
    errors = []
    ranked_path = root / "selection" / "ranked-ids.tsv"
    selected_path = root / "selection" / "selected-ids.tsv"
    if file_sha256(ranked_path) != RANKED_TSV_SHA256:
        errors.append("ranked id TSV hash")
    if file_sha256(selected_path) != SELECTED_TSV_SHA256:
        errors.append("selected id TSV hash")
    selected_ids = [row["case_id"] for row in manifest["selected"]]
    if selected_ids != [case["case_id"] for case in s_record["cases"]]:
        errors.append("S record case order")
    if selected_ids != [case["case_id"] for case in x_record["cases"]]:
        errors.append("X record case order")
    fields = _index_fields(s_record)
    cues = _index_cues(x_record)
    rendered = {}
    field_rows = []
    counter = local_counter()
    signature_rows = []
    for case in manifest["selected"]:
        case_id = case["case_id"]
        tools = catalogues[case_id]
        conditions = render_conditions(tools, fields[case_id], cues[case_id])
        rendered[case_id] = conditions
        errors.extend(f"{case_id}: {item}" for item in composition_errors(conditions, fields[case_id], cues[case_id]))
        errors.extend(f"{case_id}: {item}" for item in structural_errors(conditions))
        errors.extend(f"{case_id}: {item}" for item in sibling_name_errors(conditions))
        for condition, catalogue in conditions.items():
            payload = load_json(root / "rendered" / case_id / f"{condition}.json")
            if payload["tools"] != catalogue:
                errors.append(f"committed {condition} drifted {case_id}")
            errors.extend(
                f"hidden key {case_id} {condition} {item}" for item in hidden_key_errors(payload)
            )
        field_rows.extend(field_token_rows(case_id, conditions, counter))
        for index, tool in enumerate(tools):
            signature_rows.append(
                {
                    "case_id": case_id,
                    "category": case["category"],
                    "tool_index": index,
                    "name": tool["function"]["name"],
                    "schema_signature": schema_signature(tool),
                    "parameter_signature": parameter_signature(tool),
                }
            )
    errors.extend(ledger_errors(s_record, catalogues))
    errors.extend(cue_errors(x_record, catalogues))
    saved_signatures = load_json(root / "checks" / "signatures.json")
    if saved_signatures.get("tools") != signature_rows:
        errors.append("signature drift")
    if errors:
        preview = "\n".join(errors[:30])
        raise ValueError(f"{len(errors)} semantic-audit checks failed\n{preview}")
    tokens = load_json(root / "checks" / "tokens.json")
    _check_saved_field_tokens(tokens, field_rows, manifest)
    counts = fact_counts(s_record, x_record)
    saved_counts = load_json(root / "checks" / "fact-counts.json")
    if {key: saved_counts[key] for key in counts} != counts:
        raise ValueError("fact counts drifted")
    return {
        "cases": len(manifest["selected"]),
        "fields": len(field_rows),
        "fact_counts": counts,
        "field_savings": tokens["field"]["overall"]["saving_vs_U"],
        "request_savings": tokens["request"]["overall"]["saving_vs_U"],
        "cue_cases": sum(1 for case in x_record["cases"] if case["cue_applied"]),
        "provider_called": False,
    }


def _check_saved_field_tokens(tokens: dict, rows: list[dict], manifest: dict) -> None:
    by_case = {}
    categories = {row["case_id"]: row["category"] for row in manifest["selected"]}
    for row in rows:
        bucket = by_case.setdefault(row["case_id"], {condition: 0 for condition in CONDITIONS})
        for condition in CONDITIONS:
            bucket[condition] += row[condition]
    for case_id, totals in by_case.items():
        saved = tokens["field"]["by_case"][case_id]["totals"]
        if saved != totals:
            raise ValueError(f"field token drift {case_id}")
    overall = {condition: 0 for condition in CONDITIONS}
    by_category = {category: {condition: 0 for condition in CONDITIONS} for category in TAKE}
    for case_id, totals in by_case.items():
        for condition in CONDITIONS:
            overall[condition] += totals[condition]
            by_category[categories[case_id]][condition] += totals[condition]
    if tokens["field"]["overall"]["totals"] != overall:
        raise ValueError("overall field token drift")
    for category, totals in by_category.items():
        if tokens["field"]["by_category"][category]["totals"] != totals:
            raise ValueError(f"category field token drift {category}")
    for block_name in ("field", "request"):
        block = tokens[block_name]["overall"]
        for condition in ("S", "X", "SX"):
            expected = saving(block["totals"]["U"], block["totals"][condition])
            if abs(block["saving_vs_U"][condition] - expected) > 1e-12:
                raise ValueError(f"{block_name} saving formula {condition}")


def cue_errors(x_record: dict, catalogues: dict[str, list[dict]]) -> list[str]:
    errors = []
    if x_record.get("separator") != CUE_SEPARATOR:
        errors.append("cue separator")
    if x_record.get("pointer") != CUE_POINTER:
        errors.append("cue pointer")
    multiple_applied = 0
    for case in x_record["cases"]:
        tools = catalogues[case["case_id"]]
        applied = False
        for item in case["tools"]:
            cue = item.get("cue") or ""
            if cue:
                applied = True
                if item["rival"]["function_name"] not in cue:
                    errors.append(f"cue omits rival name {case['case_id']} {item['tool_index']}")
                for side in ("target", "rival"):
                    fact = item[side]
                    text = get_text(tools[fact["tool_index"]], fact["pointer"])
                    if fact["excerpt"] not in text:
                        errors.append(f"cue excerpt missing {case['case_id']} {side} {item['tool_index']}")
                for proposition in item.get("propositions", []):
                    source = tools[proposition["source_tool_index"]]
                    source_text = get_text(source, proposition["source_pointer"])
                    start, end = proposition["span"]
                    if source_text[start:end] != proposition["excerpt"]:
                        errors.append(f"cue span mismatch {proposition['id']}")
                    if proposition.get("unsupported") or proposition.get("lost"):
                        errors.append(f"cue proposition not traced {proposition['id']}")
            if not cue and not item.get("no_cue_reason"):
                errors.append(f"missing no-cue reason {case['case_id']} {item['tool_index']}")
        if applied != bool(case["cue_applied"]):
            errors.append(f"cue_applied flag {case['case_id']}")
        if case["case_id"].startswith("multiple_") and applied:
            multiple_applied += 1
    if x_record["coverage"]["multiple_cases_with_a_cue"] != multiple_applied:
        errors.append("multiple cue coverage count")
    if x_record["coverage"]["multiple_denominator"] != 8:
        errors.append("multiple cue denominator")
    return errors


def fact_ledger_markdown(s_record: dict, x_record: dict) -> str:
    """Readable copy of the sealed proposition ledger. Quotes are description fields only."""
    lines = [
        "# Fact ledger",
        "",
        "Each proposition is one inventoried claim. Spans are character offsets into the original allowlisted description. A duplicate or an illustrative omission is not a lost fact. Cue propositions are traced to the original catalogues, not to the S replacements.",
        "",
    ]
    for case in s_record["cases"]:
        lines.append(f"## {case['case_id']}")
        lines.append("")
        for field in case["fields"]:
            status = "no-op" if field["noop"] else field["decision"]
            lines.append(f"### t{field['tool_index']} `{field['function_name']}` `{field['pointer']}` ({status})")
            lines.append("")
            lines.append(f"- Original: {field['original']}")
            lines.append(f"- Replacement: {field['replacement']}")
            if field.get("reason"):
                lines.append(f"- Reason: {field['reason']}")
            for conflict in field.get("conflicts", []):
                lines.append(f"- Conflict, left unrepaired: {conflict}")
            for proposition in field["propositions"]:
                lines.append(
                    f"- `{proposition['id']}` {proposition['decision']} {proposition['role']} {proposition['kind']}: "
                    f"[{proposition['span'][0]}:{proposition['span'][1]}] {proposition['excerpt']}"
                )
                if proposition.get("note"):
                    lines.append(f"  {proposition['note']}")
            lines.append("")
    lines.append("## Contrast cues")
    lines.append("")
    for case in x_record["cases"]:
        lines.append(f"### {case['case_id']}")
        lines.append("")
        lines.append(case["case_reason"])
        lines.append("")
        for tool in case["tools"]:
            if tool.get("cue"):
                lines.append(f"- t{tool['tool_index']} `{tool['function_name']}` cue: {tool['cue']}")
                lines.append(f"  Rival `{tool['rival']['function_name']}` on axis: {tool['rival']['axis']}")
                lines.append(f"  Why this pair: {tool['rival']['why_confusable']}")
            else:
                lines.append(f"- t{tool['tool_index']} `{tool['function_name']}`: no cue. {tool['no_cue_reason']}")
            for proposition in tool.get("propositions", []):
                lines.append(
                    f"  - `{proposition['id']}` {proposition['kind']}: {proposition['excerpt']}"
                )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def request_token_totals(bfcl_root: Path, rendered: dict[str, dict[str, list[dict]]]) -> dict[str, dict[str, int]]:
    """Count prepared requests. Messages are read and not returned."""
    from tool_compression.load import load_category

    counter = local_counter()
    needed = set(rendered)
    totals: dict[str, dict[str, int]] = {}
    seen: set[str] = set()
    for category in TAKE:
        _path, records = load_category(Path(bfcl_root), category)
        for record in records:
            case_id = record["id"]
            if case_id not in needed:
                continue
            messages = record["question"][0]
            totals[case_id] = {}
            for condition, tools in rendered[case_id].items():
                request = assemble_request(messages, tools)
                totals[case_id][condition] = counter.count(dump_request(request))
            seen.add(case_id)
            del messages
    if seen != needed:
        raise ValueError("selected cases missing from the pinned BFCL files")
    return totals
