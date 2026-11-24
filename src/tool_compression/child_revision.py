"""Blinded source packets for a later human review.

The selection method is docs/child-revision-evidence-ownership/PROTOCOL.md.
This module builds the packets. It does not review a field, score an
alternative, or call a provider.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from tool_compression.amendment_bundle import AmendmentFailure, _json_text, _jsonl, _mock_child, _network_denied, build_packet, repo_root
from tool_compression.amendment_s2 import FLOAT_SUFFIX
from tool_compression.amendment_x2 import value_at

PARENT_COMMIT = "9154b8b171ed4022fd062cabc47136ccf5d5d22a"
PR13_BRANCH = "cursor/s2-x2-sx2-amendment-e97e"
PROTOCOL_SEED = "child-revision-evidence-ownership-2026-11-24"
PROTOCOL_SHA256 = "ef669197f1be2893f62eeb5230034c0be15f5e617f343be9b1e7d48871d20d08"
ACCEPTED_SAMPLE_SIZE = 24
NAMED_EXPOSED = ("multiple_11", "multiple_12", "multiple_34", "multiple_35")
GET_ANGLES_FUNCTION = "triangle_properties_get"
GET_ANGLES_POINTER = "/function/parameters/properties/get_angles/description"
GET_ANGLES_FINAL = "Whether to calculate the internal angles"
RENDERED_CATALOGUE_SHA256 = "da8c9b86986af9d4d70b1405aaf825913eb515f6e24c58ed4235984462921d76"
RENDERED_CATALOGUE_FILES = 3360
BANNED_PACKET_KEYS = frozenset({
    "adopted",
    "candidate",
    "change_class",
    "cosmetic",
    "cue",
    "evidence",
    "final",
    "gold",
    "ground_truth",
    "keep_detail",
    "keep_reason",
    "meaningful",
    "no_cue_reason",
    "possible_answer",
    "question",
    "rejected_candidates",
    "rival",
    "rule_effect",
})


class ChildRevisionFailure(RuntimeError):
    """The blinded packet does not match the predeclared protocol."""


def child_dir() -> Path:
    return repo_root() / "docs" / "child-revision-evidence-ownership"


def _rendered_catalogue_sha256() -> str:
    root = repo_root()
    rendered = root / "docs" / "amendment-s2x2" / "rendered"
    digest = sha256()
    count = 0
    for path in sorted(rendered.glob("*/*.json")):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
        count += 1
    if count != RENDERED_CATALOGUE_FILES:
        raise ChildRevisionFailure(f"rendered catalogue file count is {count}")
    return digest.hexdigest()


def _copy(value):
    return json.loads(json.dumps(value, ensure_ascii=False))


def _require_protocol(text: str, formative: list[str]) -> None:
    if sha256(text.encode("utf-8")).hexdigest() != PROTOCOL_SHA256:
        raise ChildRevisionFailure("PROTOCOL.md changed after it was predeclared")
    required = (
        PROTOCOL_SEED,
        "The sample size is 24",
        "o200k_base",
        "Character length is not the score.",
        "There is no coverage quota",
        "no model is a judge or editor",
        "including questions",
        "multiple_12",
        "get_angles",
        "formative",
        "does not add a rule for `multiple_12`",
    )
    missing = [item for item in required if item not in text]
    if missing:
        raise ChildRevisionFailure("protocol is missing predeclared text: " + ", ".join(missing))
    for case_id in list(formative) + list(NAMED_EXPOSED):
        if f"`{case_id}`" not in text:
            raise ChildRevisionFailure(f"protocol does not flag {case_id}")


def _exposed_cases(formative: list[str]) -> list[str]:
    seen = []
    for case_id in list(formative) + list(NAMED_EXPOSED):
        if case_id not in seen:
            seen.append(case_id)
    return seen


def _occurrences(packet: dict) -> tuple[dict, list]:
    found = {}
    order = []
    for case in packet["cases"]:
        tools = case["tools"]["U"]
        for row in case["s2_rows"]:
            key = (row["context_id"], row["pointer"])
            item = {
                "case_id": case["case_id"],
                "tool_index": row["tool_index"],
                "function_name": row["function_name"],
                "pointer": row["pointer"],
                "context_id": row["context_id"],
                "adopted": row["adopted"],
                "nontrivial": row["nontrivial"],
                "original": row["original"],
                "tool": tools[row["tool_index"]],
            }
            if key not in found:
                found[key] = []
                order.append(key)
            found[key].append(item)
            if found[key][0]["adopted"] != item["adopted"] or found[key][0]["nontrivial"] != item["nontrivial"]:
                raise ChildRevisionFailure(f"own-tool context disagrees with itself at {item['case_id']} {item['pointer']}")
    return found, order


def _context_exposed(items: list[dict], exposed: set[str]) -> bool:
    if any(item["case_id"] in exposed for item in items):
        return True
    return any(
        item["function_name"] == GET_ANGLES_FUNCTION and item["pointer"] == GET_ANGLES_POINTER
        for item in items
    )


def _accepted_digest(context_id: str, pointer: str) -> str:
    return sha256(f"{PROTOCOL_SEED}\naccepted\n{context_id}\n{pointer}".encode("utf-8")).hexdigest()


def _banned_keys(node, path: str = "") -> list[str]:
    found = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in BANNED_PACKET_KEYS:
                found.append(path + "/" + key)
            found.extend(_banned_keys(value, path + "/" + str(key)))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(_banned_keys(value, f"{path}/{index}"))
    return found


def _assert_source_only(packet_text: str, cues: list[str], exposed: set[str]) -> None:
    for case_id in exposed:
        for field in ("case_id", "first_case_id"):
            if f'"{field}":"{case_id}"' in packet_text:
                raise ChildRevisionFailure(f"blinded packet includes exposed case {case_id}")
    if GET_ANGLES_POINTER in packet_text or GET_ANGLES_FINAL in packet_text or "Unlike " in packet_text:
        raise ChildRevisionFailure("blinded packet includes a decision, the get_angles wording, or a cue")
    for cue in cues:
        if cue and cue in packet_text:
            raise ChildRevisionFailure("blinded packet includes a cue sentence")


def _select(packet: dict) -> dict:
    formative = list(packet["manifest"]["formative_12"])
    exposed_list = _exposed_cases(formative)
    exposed = set(exposed_list)
    found, order = _occurrences(packet)
    retained = []
    retained_excluded = 0
    accepted_pool = []
    accepted_excluded = 0
    for key in order:
        items = found[key]
        first = items[0]
        exposed_context = _context_exposed(items, exposed)
        if first["adopted"]:
            if exposed_context:
                accepted_excluded += 1
                continue
            accepted_pool.append((_accepted_digest(key[0], key[1]), key))
            continue
        if not first["nontrivial"]:
            continue
        if exposed_context:
            retained_excluded += 1
            continue
        if value_at(first["tool"], first["pointer"]) != first["original"]:
            raise ChildRevisionFailure(f"retained source does not match {first['case_id']} {first['pointer']}")
        retained.append({
            "population": "retained_nontrivial_unique_own_tool_context",
            "context_id": first["context_id"],
            "pointer": first["pointer"],
            "first_case_id": first["case_id"],
            "first_tool_index": first["tool_index"],
            "function_name": first["function_name"],
            "original_tool": _copy(first["tool"]),
        })
    retained.sort(key=lambda row: (row["context_id"], row["pointer"]))
    accepted_pool.sort(key=lambda item: item[0])
    if len(accepted_pool) < ACCEPTED_SAMPLE_SIZE:
        raise ChildRevisionFailure("accepted-edit population is smaller than the predeclared sample")
    accepted = []
    for _digest, key in accepted_pool[:ACCEPTED_SAMPLE_SIZE]:
        first = found[key][0]
        if value_at(first["tool"], first["pointer"]) != first["original"]:
            raise ChildRevisionFailure(f"accepted source does not match {first['case_id']} {first['pointer']}")
        accepted.append({
            "population": "accepted_edit_sample",
            "context_id": first["context_id"],
            "pointer": first["pointer"],
            "first_case_id": first["case_id"],
            "first_tool_index": first["tool_index"],
            "function_name": first["function_name"],
            "original_field": first["original"],
            "original_tool": _copy(first["tool"]),
        })
    uncued = []
    uncued_excluded = 0
    for case in packet["cases"]:
        if case["category"] != "multiple":
            continue
        catalogue = _copy(case["tools"]["U"])
        for row in case["x2_rows"]:
            if row["cue"]:
                continue
            if case["case_id"] in exposed:
                uncued_excluded += 1
                continue
            uncued.append({
                "population": "uncued_original_multi_tool_target",
                "case_id": case["case_id"],
                "tool_index": row["tool_index"],
                "function_name": row["function_name"],
                "original_catalogue": catalogue,
            })
    get_angles = []
    for case in packet["cases"]:
        for index, tool in enumerate(case["tools"]["U"]):
            if tool["function"]["name"] != GET_ANGLES_FUNCTION:
                continue
            if value_at(tool, GET_ANGLES_POINTER) is None:
                continue
            get_angles.append({
                "case_id": case["case_id"],
                "tool_index": index,
                "function_name": GET_ANGLES_FUNCTION,
                "pointer": GET_ANGLES_POINTER,
                "reasons": ["triangle_get_angles_wording"],
            })
    if not get_angles:
        raise ChildRevisionFailure("the triangle get_angles wording was not flagged")
    case_rows = []
    for case_id in exposed_list:
        reasons = []
        if case_id in formative:
            reasons.append("formative_12")
        if case_id in NAMED_EXPOSED:
            reasons.append("named_fixture")
        if any(item["case_id"] == case_id for item in get_angles):
            reasons.append("triangle_get_angles_wording")
        case_rows.append({"case_id": case_id, "reasons": reasons})
    cues = [row["cue"] for case in packet["cases"] for row in case["x2_rows"] if row["cue"]]
    packet_text = _jsonl(retained) + _jsonl(uncued) + _jsonl(accepted)
    for row in retained + uncued + accepted:
        leaked = _banned_keys(row)
        if leaked:
            raise ChildRevisionFailure("packet contains a decision field: " + ", ".join(leaked[:8]))
    _assert_source_only(packet_text, cues, exposed)
    if len(accepted) != ACCEPTED_SAMPLE_SIZE:
        raise ChildRevisionFailure("accepted sample size drifted")
    return {
        "retained": retained,
        "uncued": uncued,
        "accepted": accepted,
        "exposure": {
            "flagged_before_packet_build": True,
            "review_conducted": False,
            "cases": case_rows,
            "get_angles_fields": get_angles,
            "excluded_from_blinded_packets": {
                "retained_nontrivial_contexts": retained_excluded,
                "uncued_multi_tool_targets": uncued_excluded,
                "accepted_edit_contexts": accepted_excluded,
            },
            "blinded_counts": {
                "retained_nontrivial_contexts": len(retained),
                "uncued_multi_tool_targets": len(uncued),
                "accepted_edit_sample": len(accepted),
                "accepted_population_before_the_draw": len(accepted_pool),
            },
        },
    }


def _report(packet: dict, rendered_sha: str, mock: dict) -> str:
    ownership = packet["evidence_ownership"]
    split = packet["s2_edit_split"]["all_840"]
    fix = ownership["value_fixes"][0]
    before = fix["audited_misattribution"]
    after = fix["corrected"]
    other = split["other_adopted_by_change_class"]
    other_text = ", ".join(f"{name} {other[name]}" for name in sorted(other))
    directions = [
        item for item in ownership["cues"] if item["case_id"] == "multiple_11"
    ]
    direction_lines = []
    for item in directions:
        mark = "value corrected" if item["value_fix"] else "cited values already owned by that side"
        direction_lines.append(
            f"- `{item['function_name']}` index {item['tool_index']} versus "
            f"`{item['rival_function_name']}` index {item['rival_tool_index']}: "
            f"target parameters {item['target_parameter_names']}; "
            f"rival parameters {item['rival_parameter_names']}; "
            f"order_support on {item['order_support_side']}. {mark}."
        )
    lines = [
        "# Child revision after PR #13",
        "",
        f"Parent commit `{PARENT_COMMIT}` on `{PR13_BRANCH}`. That branch is the frozen comparator. This packet does not retitle, close, or rewrite it.",
        "",
        "Offline only. Socket construction is denied during the rebuild. No provider is called and no API key is read. This command has no live mode. Official v1.1, T1/T2, #11, and #12 are unmodified. No accuracy result and no billed-input result is claimed.",
        "",
        "## Rendered catalogues",
        "",
        (
            f"Rendered U, S2, X2, and SX2 bytes under `docs/amendment-s2x2/rendered/` are unchanged versus `{PARENT_COMMIT}`. "
            f"{RENDERED_CATALOGUE_FILES} files, SHA-256 `{rendered_sha}`."
        ),
        "",
        "The evidence records, the S2 rule-effect column, and the comparison sheet changed. The cue sentences did not, so the rendered tool text did not.",
        "",
        "## Evidence-ownership fixes",
        "",
        "All 30 cues were checked in both directions: the target citation and the rival citation, against the original tool, index, path, and value.",
        "",
        "One value fix:",
        "",
        (
            f"`{fix['case_id']}` `{fix['target']['function_name']}` at index {fix['target']['tool_index']} "
            f"cited {before['target_parameter_names']}, which belong to {before['target_parameters_belong_to']}. "
            f"The rival `{fix['rival']['function_name']}` at index {fix['rival']['tool_index']} cited "
            f"{before['rival_parameter_names']} and held `order_support`, which belong to {before['order_support_belongs_to']}. "
            f"The target now cites {after['target_parameter_names']} and `order_support` at `{after['order_support_path']}`. "
            f"The rival now cites {after['rival_parameter_names']}. Both directions of that swapped record were corrected."
        ),
        "",
        "The cue sentence did not change:",
        "",
        f"> {fix['cue']}",
        "",
        "`multiple_11` in every direction:",
        "",
        *direction_lines,
        "",
        (
            f"Cue text changes: {len(ownership['cue_text_changes'])}. "
            f"Cues whose cited values were already on the owning tool: {ownership['cues_with_no_value_change']}. "
            "Those 29 rows gained an explicit tool index, path, and value on each citation. The excerpts and schema values stored for them were already the original text of that tool."
        ),
        "",
        "`multiple_12` remains uncued. No grammar rule or regular expression was added. The return-on-equity versus return-on-assets contrast, equity versus assets in the denominator, stays a recorded limitation of the current cue rule.",
        "",
        "Machine-readable detail: `docs/amendment-s2x2/checks/evidence-ownership.json` and `docs/amendment-s2x2/ledgers/x2.jsonl`.",
        "",
        "## Adopted S2 edits",
        "",
        split["label"],
        "",
        "The audited parent set `meaningfully_changed` equal to the adopted count and `cosmetic_only` to zero. "
        "Those labels were produced by the row constructor, not by a separate reading of the text. They are omitted here.",
        "",
        "| rule effect | fields | o200k_base field tokens saved | changed cases |",
        "| --- | ---: | ---: | ---: |",
        f"| suffix_only_float_sentence | {split['suffix_only_fields']} | {split['suffix_only_field_tokens_o200k']} | {split['cases_suffix_only']} |",
        f"| other_adopted | {split['other_adopted_fields']} | {split['other_field_tokens_o200k']} | {split['cases_with_other_adopted']} |",
        f"| adopted | {split['adopted_fields']} | {split['saved_field_tokens_o200k']} | {split['cases_with_an_adopted_field']} |",
        "",
        (
            f"Suffix-only removals are {split['suffix_only_field_tokens_o200k']} of {split['saved_field_tokens_o200k']} "
            f"saved field tokens ({split['suffix_only_share_of_saved_field_tokens']}). "
            f"In {split['cases_suffix_only']} of {split['cases_with_an_adopted_field']} changed cases, every adopted edit is that removal."
        ),
        "",
        f"A suffix-only removal deletes only the converter sentence `{FLOAT_SUFFIX}` from the end of the field. "
        f"The other adopted edits, by the rule that fired: {other_text}. "
        f"`schema_guaranteed` covers {split['suffix_only_by_change_class'].get('schema_guaranteed', 0)} suffix-only fields "
        f"and {other.get('schema_guaranteed', 0)} other adopted fields, so the change class alone is not the split.",
        "",
        "The token count is local `o200k_base`. It is not billed usage, accuracy, or the closed 1/10 target. Character length is not this split.",
        "",
        "Detail: `docs/amendment-s2x2/checks/s2-edit-split.json` and `docs/amendment-s2x2/comparison/sheet.md`.",
        "",
        "## Blinded sample",
        "",
        "The selection method is `docs/child-revision-evidence-ownership/PROTOCOL.md`, written before these packets. This revision stops there. No human review was filled in, and no model was used as a judge or editor.",
        "",
        "Previously exposed fixtures are flagged in `docs/child-revision-evidence-ownership/exposure-index.json` and left out of the packets.",
        "",
        "Source-only packets:",
        "",
        "- `docs/child-revision-evidence-ownership/packets/retained-nontrivial-contexts.jsonl`",
        "- `docs/child-revision-evidence-ownership/packets/uncued-multi-tool-targets.jsonl`",
        "- `docs/child-revision-evidence-ownership/packets/accepted-edit-sample.jsonl`",
        "",
        "If a later review produces more than one faithful alternative for a field, the comparison uses the `o200k_base` token count of the field text. That score is not computed here. Complete serialized requests, including questions, are not counted here.",
        "",
        f"Rebuild check: socket probes denied {mock.get('socket_probes_denied')}, network `{mock.get('network_access')}`.",
        "",
    ]
    return "\n".join(lines)


def _packet_readme() -> str:
    return "\n".join([
        "# Blinded source packets",
        "",
        "These rows follow `../PROTOCOL.md`. They are source material for a later human reviewer.",
        "",
        "No review was conducted. No model judged or edited a field. A row does not contain a KEEP decision, a no-cue decision, a cue, a rewrite, a score, a question, or a gold answer.",
        "",
        "`accepted-edit-sample.jsonl` is the first 24 rows of the predeclared hash order. The draw was not replaced after it was built. There is no coverage quota.",
        "",
        "A later comparison of faithful alternatives uses the `o200k_base` token count of the field text. Character length is not the score. This directory does not contain that score.",
        "",
    ])


def _files_from_packet(packet: dict, mock: dict) -> dict[str, str]:
    rendered_sha = _rendered_catalogue_sha256()
    if rendered_sha != RENDERED_CATALOGUE_SHA256:
        raise ChildRevisionFailure(
            "rendered U/S2/X2/SX2 catalogue bytes changed versus "
            f"{PARENT_COMMIT}: {rendered_sha}"
        )
    protocol = (child_dir() / "PROTOCOL.md").read_text(encoding="utf-8")
    _require_protocol(protocol, list(packet["manifest"]["formative_12"]))
    if not mock.get("enforced") or mock.get("network_access") != "denied":
        raise ChildRevisionFailure("socket construction was not denied")
    selected = _select(packet)
    return {
        "report.md": _report(packet, rendered_sha, mock),
        "exposure-index.json": _json_text(selected["exposure"]),
        "packets/README.md": _packet_readme(),
        "packets/retained-nontrivial-contexts.jsonl": _jsonl(selected["retained"]),
        "packets/uncued-multi-tool-targets.jsonl": _jsonl(selected["uncued"]),
        "packets/accepted-edit-sample.jsonl": _jsonl(selected["accepted"]),
    }


def _generate() -> dict[str, str]:
    with _network_denied():
        mock = _mock_child()
        try:
            packet = build_packet()
        except AmendmentFailure as exc:
            raise ChildRevisionFailure(str(exc)) from exc
        return _files_from_packet(packet, mock)


def _expected_paths() -> set[str]:
    return {
        "PROTOCOL.md",
        "report.md",
        "exposure-index.json",
        "packets/README.md",
        "packets/retained-nontrivial-contexts.jsonl",
        "packets/uncued-multi-tool-targets.jsonl",
        "packets/accepted-edit-sample.jsonl",
    }


def freeze() -> dict:
    files = _generate()
    root = child_dir()
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return {
        "froze": True,
        "files": len(files) + 1,
        "rendered_catalogue_sha256": RENDERED_CATALOGUE_SHA256,
        "rendered_catalogue_bytes_changed_versus_9154b8b": False,
        "accepted_sample_size": ACCEPTED_SAMPLE_SIZE,
        "review_conducted": False,
    }


def check() -> dict:
    files = _generate()
    root = child_dir()
    errors = []
    for relative, text in files.items():
        path = root / relative
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            errors.append(f"drift {relative}")
    if not (root / "PROTOCOL.md").is_file():
        errors.append("missing PROTOCOL.md")
    extra = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative not in _expected_paths():
            extra.append(relative)
    if extra:
        errors.append("unexpected child-revision files: " + ", ".join(sorted(extra)))
    if errors:
        raise ChildRevisionFailure("child revision check failed:\n" + "\n".join(errors[:30]))
    return {
        "passed": True,
        "files": len(files) + 1,
        "rendered_catalogue_sha256": RENDERED_CATALOGUE_SHA256,
        "rendered_catalogue_bytes_changed_versus_9154b8b": False,
        "accepted_sample_size": ACCEPTED_SAMPLE_SIZE,
        "review_conducted": False,
        "network_access": "denied",
        "reproduction": "python -m tool_compression child-revision --check",
    }
