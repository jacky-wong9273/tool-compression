"""One-shot bridge to TSCG compressDescriptions.

The bridge transports catalogues and checks the description boundary. It does
not rewrite TSCG output, does not apply the local cap, and does not read
TSCG's own token estimates as provider usage.
"""

from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import time

from tool_compression.adapter import description_slots
from tool_compression.count import dump_request
from tool_compression.prepare import assemble_request, cohort_ratio, convert_record, request_hash
from tool_compression.validate import catalogue_violations

_KNOWN_PATH_PARTS = frozenset(
    {
        "",
        "function",
        "parameters",
        "properties",
        "items",
        "description",
        "type",
        "keys",
        "len",
        "format",
        "default",
        "enum",
        "example",
        "examples",
        "required",
        "response",
    }
)


def run_arm_e(study, tscg_root: Path, script_path: Path, budget_counter, sensitivity_counter) -> dict:
    catalogs = []
    meta = []
    for category, records in study.items():
        for record in records:
            messages = record["question"][0]
            catalogue = convert_record(record)
            catalogs.append(catalogue)
            meta.append((category, record["id"], messages, catalogue))
    started = time.perf_counter()
    invoked = _invoke(Path(tscg_root), Path(script_path), catalogs)
    elapsed = round(time.perf_counter() - started, 3)
    report = {
        "entrypoint": "compressDescriptions",
        "options": None,
        "documented_policy": "SDM stripFiller on OpenAI function and top-level parameter descriptions",
        "local_cap_applied": False,
        "output_repaired": False,
        "tscg_estimate_tokens_used_as_provider_usage": False,
        "preprocessing_seconds": elapsed,
        "check_completed": invoked["ok"],
        "boundary_compatible": False,
        "runtime_failures": 0,
        "catalogues": len(meta),
    }
    if not invoked["ok"]:
        report["failure"] = invoked["failure"]
        return report
    results = invoked["catalogs"]
    if len(results) != len(meta):
        report["check_completed"] = False
        report["failure"] = {"kind": "result_count", "expected": len(meta), "got": len(results)}
        return report
    classes = {"unchanged": 0, "case_or_punctuation_only": 0, "substantive": 0}
    fields = 0
    violation_shapes: dict[str, int] = {}
    principle_sets: dict[str, int] = {}
    rows = []
    per_category: dict[str, dict] = {}
    for item, (category, case_id, messages, original) in zip(results, meta):
        bucket = per_category.setdefault(
            category,
            {"records": 0, "runtime_failures": 0, "boundary_failures": 0, "changed_records": 0},
        )
        bucket["records"] += 1
        if not item.get("ok"):
            report["runtime_failures"] += 1
            bucket["runtime_failures"] += 1
            rows.append(
                {
                    "category": category,
                    "id": case_id,
                    "ok": False,
                    "error_name": str(item.get("error_name") or "Error")[:40],
                }
            )
            continue
        principles = item.get("principles") or []
        principle_sets["+".join(str(part) for part in principles) or "(none)"] = (
            principle_sets.get("+".join(str(part) for part in principles) or "(none)", 0) + 1
        )
        produced = item.get("tools")
        # JSON has one number type. Integral floats such as 1.0 round-trip as ints.
        # This is bridge canonicalization, not a repair of description text.
        left = _json_numbers(original)
        right = _json_numbers(produced) if isinstance(produced, list) else produced
        violations = catalogue_violations(left, right) if isinstance(right, list) else ["/type"]
        if violations:
            bucket["boundary_failures"] += 1
            for path in violations:
                shape = _shape(path)
                violation_shapes[shape] = violation_shapes.get(shape, 0) + 1
            rows.append(
                {
                    "category": category,
                    "id": case_id,
                    "ok": False,
                    "boundary_violations": len(violations),
                }
            )
            continue
        edit_counts = edit_classes(original, produced)
        for kind, count in edit_counts.items():
            classes[kind] += count
            fields += count
        changed = edit_counts["case_or_punctuation_only"] or edit_counts["substantive"]
        if changed:
            bucket["changed_records"] += 1
        request = assemble_request(messages, produced)
        digest = request_hash(request)
        u_digest = request_hash(assemble_request(messages, original))
        rows.append(
            {
                "category": category,
                "id": case_id,
                "ok": True,
                "hash": digest,
                "E_vs_U": digest != u_digest,
            }
        )
        bucket.setdefault("u", []).append(u_digest)
        text = dump_request(request)
        u_text = dump_request(assemble_request(messages, original))
        bucket.setdefault("budget_e", []).append(budget_counter.count(text))
        bucket.setdefault("budget_u", []).append(budget_counter.count(u_text))
        bucket.setdefault("sensitivity_e", []).append(sensitivity_counter.count(text))
        bucket.setdefault("sensitivity_u", []).append(sensitivity_counter.count(u_text))
    compatible = report["runtime_failures"] == 0 and not violation_shapes and report["check_completed"]
    report["boundary_compatible"] = compatible
    report["principles"] = principle_sets
    report["description_change_classes"] = classes
    report["description_change_classes_scope"] = "catalogues_with_no_runtime_or_boundary_failure"
    report["description_fields_compared"] = fields
    report["violation_shapes"] = violation_shapes
    report["categories"] = {
        name: _category_public(bucket, budget_counter.name, sensitivity_counter.name)
        for name, bucket in per_category.items()
    }
    report["rows"] = rows
    return attach_distinct(report)


def _category_public(bucket, budget_name, sensitivity_name) -> dict:
    public = {
        "records": bucket["records"],
        "runtime_failures": bucket["runtime_failures"],
        "boundary_failures": bucket["boundary_failures"],
        "changed_records": bucket["changed_records"],
    }
    if bucket["runtime_failures"] or bucket["boundary_failures"]:
        public["local_cohort_ratio_vs_U"] = None
        return public
    public["local_cohort_ratio_vs_U"] = {
        budget_name: cohort_ratio(bucket["budget_u"], bucket["budget_e"]),
        sensitivity_name: cohort_ratio(bucket["sensitivity_u"], bucket["sensitivity_e"]),
    }
    return public


def attach_distinct(report: dict) -> dict:
    """Count E-versus-U from row flags. Rows stay out of the public JSON."""
    counts: dict[str, int] = {}
    for row in report.get("rows", []):
        if row.get("ok"):
            counts[row["category"]] = counts.get(row["category"], 0) + int(bool(row.get("E_vs_U")))
    for name, bucket in report.get("categories", {}).items():
        if bucket["runtime_failures"] or bucket["boundary_failures"]:
            continue
        bucket["records_distinct_from_U"] = counts.get(name, 0)
    return report


def _invoke(tscg_root: Path, script_path: Path, catalogs: list) -> dict:
    with tempfile.TemporaryDirectory(prefix="tscg-e-") as directory:
        in_path = Path(directory) / "in.json"
        out_path = Path(directory) / "out.json"
        in_path.write_text(json.dumps({"catalogs": catalogs}), encoding="utf-8")
        try:
            completed = subprocess.run(
                ["npx", "--yes", "tsx", str(script_path), str(tscg_root), str(in_path), str(out_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=directory,
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "failure": {"kind": "timeout"}}
        except OSError:
            return {"ok": False, "failure": {"kind": "oserror"}}
        if completed.returncode != 0 or not out_path.is_file():
            print(_redact(completed.stderr, tscg_root, directory), file=sys.stderr)
            return {"ok": False, "failure": {"kind": "process", "returncode": completed.returncode}}
        try:
            payload = json.loads(out_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"ok": False, "failure": {"kind": "json"}}
    catalogs_out = payload.get("catalogs")
    if not isinstance(catalogs_out, list):
        return {"ok": False, "failure": {"kind": "payload"}}
    return {"ok": True, "catalogs": catalogs_out}


def _redact(text: str, tscg_root: Path, directory: str) -> str:
    cleaned = (text or "").replace(str(tscg_root), "[tscg]").replace(directory, "[tmp]")
    cleaned = cleaned.replace(os.getcwd(), "[cwd]")
    line = cleaned.strip().splitlines()[-1] if cleaned.strip() else ""
    return line[:160]


def _json_numbers(value):
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, dict):
        return {key: _json_numbers(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_numbers(item) for item in value]
    return value


def edit_classes(original: list, produced: list) -> dict:
    classes = {"unchanged": 0, "case_or_punctuation_only": 0, "substantive": 0}
    for left_tool, right_tool in zip(original, produced):
        for pointer, container, key in description_slots(left_tool):
            classes[_change_class(container[key], _lookup(right_tool, pointer))] += 1
    return classes


def _change_class(before, after) -> str:
    if not isinstance(before, str) or not isinstance(after, str):
        return "substantive"
    if before == after:
        return "unchanged"
    if _folded(before) == _folded(after):
        return "case_or_punctuation_only"
    return "substantive"


def _folded(text: str) -> str:
    kept = []
    for char in text.casefold():
        kept.append(char if char.isalnum() or char.isspace() else " ")
    return " ".join("".join(kept).split())


def _lookup(tool, pointer: str):
    node = tool
    for part in pointer.strip("/").split("/"):
        if isinstance(node, list):
            if not part.isdigit() or int(part) >= len(node):
                return None
            node = node[int(part)]
        elif isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return node


def _shape(path: str) -> str:
    parts = []
    for part in path.split("/"):
        if part.isdigit() or part in _KNOWN_PATH_PARTS:
            parts.append(part)
        else:
            parts.append("{name}")
    return "/".join(parts)


def public_report(report: dict) -> dict:
    hidden = {"rows"}
    return {key: value for key, value in report.items() if key not in hidden}
