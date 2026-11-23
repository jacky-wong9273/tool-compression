"""Official 840-case U/S/X/SX preparation flight.

Stage A plans the sample and does not read an API key or call a provider.
A later live run is off-peak only. This module has no peak-continuation
switch. It does not rewrite the 12-case systems test, the validation flight,
or the closed 10% target.

Thinking on is a second pass over the same frozen catalogues. It is not a
catalogue edit. Official settlement stays false.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import json

from tool_compression.config import BFCL_DEFAULT_TEMPERATURE, BFCL_STORE
from tool_compression.convert import to_openai_completions_tools
from tool_compression.evaluation import DENOMINATORS, PINS, evaluation_manifest
from tool_compression.load import STUDY_CATEGORIES, VERSION_PREFIX, load_study, resolve_data_dir
from tool_compression.semantic_audit import (
    CUE_POINTER,
    CUE_SEPARATOR,
    HIDDEN_KEYS,
    composition_errors,
    fact_counts,
    file_sha256,
    get_text,
    ledger_errors,
    load_json,
    render_conditions,
    schema_signature,
    sibling_name_errors,
    structural_errors,
    write_json,
)
from tool_compression.usx_flight import (
    API_BASE_URL,
    API_PATH,
    CEILING_ENV,
    EVALUATE_ALIAS,
    MODEL,
    MODEL_VERSION,
    REFUSED_GENERATION_MODELS,
    SHANGHAI,
    UsxFlightRefused,
    _fc_result,
    _thinking_stayed_off,
    _tokens,
    billed_basis_t,
    generation_body as systems_test_generation_body,
    pre_call_reserve_cny,
    rate_card,
    read_ceiling_from_env,
    remaining_allows_call,
    request_sha256,
    schedule_at,
    usage_bill,
)

PURPOSE = "official-840-usx"
SAMPLE = "official-840"
GORILLA_COMMIT = "6ea57973c7a6097fd7c5915698c54c17c5b1b6c8"
CATEGORY_SHA256 = {
    "multiple": "aef168155ebd74b7ac2401198b201343bc7d16d7a3d7e0d4e6d8ee82c6969b2a",
    "simple_python": "82dd63ba502eb2520c6b5d1d9a5c4b590e03ff261565175561f6228a367d1991",
    "irrelevance": "2b6ed4c2e992cdcf5f1678a701851f944bef7550ee026ed1ddb89efed5be01a6",
}
CATEGORY_COUNTS = {"multiple": 200, "simple_python": 400, "irrelevance": 240}
ARMS = ("U", "S", "X", "SX")
CONTRASTS = ("S-U", "X-U", "SX-S", "SX-X", "SX-U")
NOT_ARMS = ("L", "E", "T1", "T2", "P", "I", "C")
PASSES = ("off", "on")
THINKING_BODY = {
    "off": {"type": "disabled"},
    "on": {"type": "enabled"},
}
BANNED_CUE_PHRASES = ("only this", "cannot", "can't")
RESULT_VERSION_PREFIX = VERSION_PREFIX
DRY_RUN_CLOCK = datetime(2026, 11, 23, 17, 25, tzinfo=SHANGHAI)
AIMED_CLOCK = datetime(2026, 11, 23, 19, 0, tzinfo=SHANGHAI)
FROZEN_EXACT = (
    "src/tool_compression/adapter.py",
    "src/tool_compression/convert.py",
    "src/tool_compression/evaluation.py",
    "src/tool_compression/load.py",
    "src/tool_compression/semantic_audit.py",
    "src/tool_compression/usx_flight.py",
    "src/tool_compression/usx_provider.py",
    "src/tool_compression/validate.py",
    "tests/test_cue_revision.py",
    "tests/test_semantic_audit.py",
    "tests/test_usx_flight.py",
)
U_NOTE = "Fresh conversion of the pinned BFCL record. No question, gold call, or stored response."
BLOCKED_REASON = "S and X are not sealed. This case is not part of a flyable four-way cell."


def package_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "docs" / "official-840"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def peak_blocks(moment: datetime) -> bool:
    """True when the public weekday window is in force. A peak minute stops this flight."""
    return schedule_at(moment) == "peak"


def thinking_body(pass_name: str) -> dict:
    if pass_name not in THINKING_BODY:
        raise UsxFlightRefused(f"unknown thinking pass {pass_name}")
    return dict(THINKING_BODY[pass_name])


def generation_body(messages: list, tools: list, pass_name: str) -> dict:
    """One generation body. The catalogue is independent of the thinking pass."""
    if MODEL in REFUSED_GENERATION_MODELS or MODEL != "deepseek-flash":
        raise UsxFlightRefused("generation model is not deepseek-flash")
    body = {
        "model": MODEL,
        "messages": deepcopy(messages),
        "temperature": BFCL_DEFAULT_TEMPERATURE,
        "store": BFCL_STORE,
        "thinking": thinking_body(pass_name),
    }
    if tools:
        body["tools"] = deepcopy(tools)
    assert_official_body(body)
    return body


def assert_official_body(body: dict) -> None:
    if body.get("model") != MODEL or body.get("model") in REFUSED_GENERATION_MODELS:
        raise UsxFlightRefused("refusing a generation body that is not deepseek-flash")
    if body.get("thinking") not in THINKING_BODY.values():
        raise UsxFlightRefused("refusing a generation body whose thinking field is not an explicit off or on pass")
    if "reasoning_effort" in body:
        raise UsxFlightRefused("refusing a generation body that sets reasoning_effort")
    if body.get("temperature") != BFCL_DEFAULT_TEMPERATURE or body.get("store") is not False:
        raise UsxFlightRefused("refusing a generation body that drops temperature 0.001 or store false")


def offpeak_rate_card() -> dict:
    card = dict(rate_card("off-peak"))
    card["peak_card_used"] = False
    card["rewrites_locked_validation_card"] = False
    card["applies_to"] = "official 840 off-peak calls only"
    return card


def offpeak_reserve() -> Decimal:
    return pre_call_reserve_cny("off-peak")


def catalogue_identities(rendered: dict[str, list]) -> dict:
    return {
        "S_equals_U": rendered["S"] == rendered["U"],
        "X_equals_U": rendered["X"] == rendered["U"],
        "SX_equals_S": rendered["SX"] == rendered["S"],
        "SX_equals_X": rendered["SX"] == rendered["X"],
        "SX_equals_U": rendered["SX"] == rendered["U"],
    }


def group_payloads(bodies_by_arm: dict[str, dict]) -> list[dict]:
    """Share one payload inside one cell. Arms stay in U, S, X, SX order."""
    groups: list[dict] = []
    index: dict[str, int] = {}
    for arm in ARMS:
        body = bodies_by_arm[arm]
        digest = request_sha256(body)
        slot = index.get(digest)
        if slot is None:
            index[digest] = len(groups)
            groups.append({"request_sha256": digest, "arms": [arm], "body": body})
        else:
            groups[slot]["arms"].append(arm)
    return groups


def _groups_match_identities(flags: dict, groups: list[dict]) -> bool:
    located = {}
    for group in groups:
        for arm in group["arms"]:
            located[arm] = group["request_sha256"]
    pairs = {
        "S_equals_U": ("S", "U"),
        "X_equals_U": ("X", "U"),
        "SX_equals_S": ("SX", "S"),
        "SX_equals_X": ("SX", "X"),
        "SX_equals_U": ("SX", "U"),
    }
    return all((located[left] == located[right]) is flags[key] for key, (left, right) in pairs.items())


def _public_groups(groups: list[dict]) -> list[dict]:
    return [
        {
            "request_sha256": group["request_sha256"],
            "arms": list(group["arms"]),
            "shared": len(group["arms"]) > 1,
        }
        for group in groups
    ]


def make_plan(case_id: str, category: str, messages: list, rendered: dict[str, list], pass_name: str) -> dict:
    bodies = {arm: generation_body(messages, rendered[arm], pass_name) for arm in ARMS}
    groups = group_payloads(bodies)
    flags = catalogue_identities(rendered)
    if not _groups_match_identities(flags, groups):
        raise UsxFlightRefused(f"payload groups do not match catalogue identity for {case_id} {pass_name}")
    off_reference = systems_test_generation_body(messages, rendered["U"])
    if pass_name == "off" and bodies["U"] != off_reference:
        raise UsxFlightRefused("thinking-off body drifted from the systems-test generation body")
    if pass_name == "on" and bodies["U"] == off_reference:
        raise UsxFlightRefused("thinking-on body collapsed into the thinking-off body")
    for arm in ARMS:
        if "tools" in bodies[arm] and bodies[arm]["tools"] != rendered[arm]:
            raise UsxFlightRefused(f"generation copied a different catalogue for {case_id} {arm}")
    return {
        "case_id": case_id,
        "category": category,
        "thinking": pass_name,
        "cell": f"{case_id}:{pass_name}",
        "catalogue_identities": flags,
        "groups": _public_groups(groups),
        "_bodies": {group["request_sha256"]: group["body"] for group in groups},
    }


def _assert_pass_order(plans: list[dict]) -> None:
    seen_on = False
    seen_off = False
    for plan in plans:
        thinking = plan.get("thinking")
        if thinking == "on":
            if not seen_off:
                raise UsxFlightRefused("thinking-on pass cannot start before the thinking-off pass")
            seen_on = True
        elif thinking == "off":
            if seen_on:
                raise UsxFlightRefused("thinking-off pass must finish before thinking-on")
            seen_off = True
        else:
            raise UsxFlightRefused("unknown thinking pass")
    if not seen_off:
        raise UsxFlightRefused("thinking-off pass is missing")


def catalogue_leak_errors(node, parent_key: str = "") -> list[str]:
    """Refuse stored questions and labels. A parameter name under properties may collide."""
    errors = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in HIDDEN_KEYS and parent_key != "properties":
                errors.append(parent_key + "/" + str(key))
            errors.extend(catalogue_leak_errors(value, str(key)))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            errors.extend(catalogue_leak_errors(value, f"{parent_key}/{index}"))
    return errors


def u_document(case_id: str, category: str, tools: list) -> dict:
    return {
        "sample": SAMPLE,
        "case_id": case_id,
        "category": category,
        "condition": "U",
        "gorilla_commit": GORILLA_COMMIT,
        "conversion": "to_openai_completions_tools",
        "note": U_NOTE,
        "tools": tools,
    }


def condition_document(case_id: str, category: str, condition: str, tools: list) -> dict:
    document = u_document(case_id, category, tools)
    document["condition"] = condition
    if condition != "U":
        document["note"] = "Rendered from the sealed S and X records. No question, gold call, or stored response."
    return document


def manifest_path() -> Path:
    return package_dir() / "selection" / "manifest.json"


def u_path(case_id: str) -> Path:
    return package_dir() / "catalogues" / "U" / f"{case_id}.json"


def rendered_path(case_id: str, condition: str) -> Path:
    return package_dir() / "rendered" / case_id / f"{condition}.json"


def frozen_relative_paths() -> list[str]:
    root = repo_root()
    found = set(FROZEN_EXACT)
    pilot = root / "docs" / "semantic-audit-pilot"
    for path in pilot.rglob("*"):
        if path.is_file():
            found.add(path.relative_to(root).as_posix())
    return sorted(found)


def compute_frozen_hashes() -> dict:
    root = repo_root()
    files = {}
    for relative in frozen_relative_paths():
        path = root / relative
        if not path.is_file():
            raise UsxFlightRefused(f"frozen file missing {relative}")
        files[relative] = file_sha256(path)
    return {
        "algorithm": "sha256",
        "note": "Bytes this package must not rewrite. The hash list does not include docs/official-840.",
        "files": files,
    }


def _load_stored_u() -> tuple[dict, dict[str, list], dict[str, str]]:
    manifest = load_json(manifest_path())
    catalogues = {}
    categories = {}
    for case_id in manifest["ids_in_file_order"]:
        payload = load_json(u_path(case_id))
        if payload.get("case_id") != case_id or payload.get("sample") != SAMPLE:
            raise ValueError(f"U document identity {case_id}")
        catalogues[case_id] = payload["tools"]
        categories[case_id] = payload["category"]
    return manifest, catalogues, categories


def _render_sealed(catalogues: dict[str, list], s_record: dict, x_record: dict) -> dict[str, dict[str, list]]:
    rendered = {}
    fields = {case["case_id"]: case["fields"] for case in s_record["cases"]}
    cues = {case["case_id"]: case["tools"] for case in x_record["cases"]}
    for case_id in fields:
        rendered[case_id] = render_conditions(catalogues[case_id], fields[case_id], cues[case_id])
    return rendered


def cue_rule_errors(x_record: dict, catalogues: dict[str, list], rendered: dict[str, dict[str, list]]) -> list[str]:
    errors = []
    if x_record.get("separator") != CUE_SEPARATOR or x_record.get("pointer") != CUE_POINTER:
        errors.append("cue separator or pointer")
    if x_record.get("s_used_as_cue_source") is not False or x_record.get("parameter_edits") is not False:
        errors.append("cue header")
    if x_record.get("success_is_not_shorter_wording") is not True:
        errors.append("shorter-wording flag")
    for case in x_record["cases"]:
        case_id = case["case_id"]
        tools = catalogues[case_id]
        names = [tool["function"]["name"] for tool in tools]
        if [item["tool_index"] for item in case["tools"]] != list(range(len(tools))):
            errors.append(f"X tool order {case_id}")
        applied = False
        for item in case["tools"]:
            cue = item.get("cue") or ""
            own = item["function_name"]
            if own != names[item["tool_index"]]:
                errors.append(f"X name {case_id} {own}")
            if item.get("pointer") != CUE_POINTER:
                errors.append(f"cue pointer {case_id} {own}")
            if cue != cue.strip() or "\n" in cue:
                errors.append(f"cue whitespace {case_id} {own}")
            if len(tools) == 1 and cue:
                errors.append(f"single-tool cue {case_id}")
            if not cue:
                if not item.get("no_cue_reason"):
                    errors.append(f"missing no-cue reason {case_id} {own}")
                continue
            applied = True
            lowered = cue.lower()
            for banned in BANNED_CUE_PHRASES:
                if banned in lowered:
                    errors.append(f"exclusion wording {case_id} {own}")
            if own in cue or cue.count(item["rival"]["function_name"]) != 1:
                errors.append(f"cue rival count {case_id} {own}")
            others = [name for name in names if name != own and name in cue]
            if others != [item["rival"]["function_name"]]:
                errors.append(f"cue names {case_id} {own} {others}")
            if item["rival"]["tool_index"] == item["tool_index"]:
                errors.append(f"cue rivals itself {case_id}")
            same = item.get("same_request") or {}
            if same.get("cue_still_helps") is not True or same.get("implies_unsupported_exclusion") is not False:
                errors.append(f"review question {case_id} {own}")
            if "both_descriptions_can_fit" not in same or not same.get("note"):
                errors.append(f"review note {case_id} {own}")
            for side in ("target", "rival"):
                fact = item[side]
                source = tools[fact["tool_index"]]
                if fact["excerpt"] not in get_text(source, fact["pointer"]):
                    errors.append(f"cue excerpt missing {case_id} {side}")
            for proposition in item.get("propositions", []):
                source = tools[proposition["source_tool_index"]]
                source_text = get_text(source, proposition["source_pointer"])
                start, end = proposition["span"]
                if source_text[start:end] != proposition["excerpt"]:
                    errors.append(f"cue span {proposition['id']}")
                if proposition.get("unsupported") or proposition.get("lost"):
                    errors.append(f"cue proposition not traced {proposition['id']}")
        for index, tool in enumerate(tools):
            for condition in ARMS:
                if schema_signature(rendered[case_id][condition][index]) != schema_signature(tool):
                    errors.append(f"schema signature {case_id} {index} {condition}")
        if applied != bool(case["cue_applied"]):
            errors.append(f"cue_applied {case_id}")
    return errors


def _identity_rows(rendered: dict[str, dict[str, list]], x_record: dict) -> dict:
    flags = {case_id: catalogue_identities(catalogues) for case_id, catalogues in rendered.items()}
    cue_ids = [case["case_id"] for case in x_record["cases"] if case["cue_applied"]]
    rows = {name: [] for name in (
        "s_equals_u",
        "s_differs_from_u",
        "x_equals_u",
        "sx_equals_s",
        "sx_equals_x",
        "sx_equals_u",
        "four_distinct",
    )}
    for case_id, flag in flags.items():
        if flag["S_equals_U"]:
            rows["s_equals_u"].append(case_id)
        else:
            rows["s_differs_from_u"].append(case_id)
        if flag["X_equals_U"]:
            rows["x_equals_u"].append(case_id)
        if flag["SX_equals_S"]:
            rows["sx_equals_s"].append(case_id)
        if flag["SX_equals_X"]:
            rows["sx_equals_x"].append(case_id)
        if flag["SX_equals_U"]:
            rows["sx_equals_u"].append(case_id)
        if not flag["S_equals_U"] and not flag["X_equals_U"] and not flag["SX_equals_S"] and not flag["SX_equals_X"]:
            rows["four_distinct"].append(case_id)
    rows["cued_ids"] = cue_ids
    rows["uncued_ids"] = [case["case_id"] for case in x_record["cases"] if not case["cue_applied"]]
    return rows


def verify_package() -> dict:
    """Check the committed 840 package. No provider and no question text."""
    root = package_dir()
    errors: list[str] = []
    frozen_path = root / "checks" / "frozen-integrity.json"
    frozen = load_json(frozen_path)
    current = compute_frozen_hashes()["files"]
    if frozen.get("files") != current:
        drifted = [key for key in sorted(set(frozen.get("files", {})) | set(current)) if frozen.get("files", {}).get(key) != current.get(key)]
        errors.append("frozen file changed " + ", ".join(drifted[:8]))
    protocol = evaluation_manifest()
    if protocol["target_provider_input_reduction"] != "1/10" or protocol["official_accuracy_in_scope"] is not False:
        errors.append("official target or accuracy scope")
    if PINS["bfcl_commit"] != GORILLA_COMMIT or dict(DENOMINATORS) != CATEGORY_COUNTS:
        errors.append("pinned denominators")
    manifest, catalogues, categories = _load_stored_u()
    if manifest.get("gorilla_commit") != GORILLA_COMMIT:
        errors.append("manifest pin")
    if manifest.get("category_sha256") != CATEGORY_SHA256:
        errors.append("category hash record")
    if manifest.get("counts") != CATEGORY_COUNTS:
        errors.append("manifest counts")
    ids = manifest["ids_in_file_order"]
    if len(ids) != sum(CATEGORY_COUNTS.values()) or len(set(ids)) != len(ids):
        errors.append("id cardinality")
    counted = {category: 0 for category in CATEGORY_COUNTS}
    for case_id in ids:
        counted[categories[case_id]] += 1
        payload = load_json(u_path(case_id))
        errors.extend(f"hidden key {case_id} {item}" for item in catalogue_leak_errors(payload))
    if counted != CATEGORY_COUNTS:
        errors.append(f"category counts {counted}")
    stored_hashes = load_json(root / "checks" / "u-sha256.json")["files"]
    for case_id in ids:
        relative = f"catalogues/U/{case_id}.json"
        if file_sha256(u_path(case_id)) != stored_hashes.get(relative):
            errors.append(f"U hash {case_id}")
    from tool_compression.official_840_tranche import SEALED_IDS, build_records

    s_record, x_record = build_records(catalogues, categories)
    if s_record != load_json(root / "edits" / "s-record.json"):
        errors.append("S record drift")
    if x_record != load_json(root / "edits" / "x-record.json"):
        errors.append("X record drift")
    if [case["case_id"] for case in s_record["cases"]] != list(SEALED_IDS):
        errors.append("sealed order")
    if [case["case_id"] for case in x_record["cases"]] != list(SEALED_IDS):
        errors.append("X order")
    positions = [ids.index(case_id) for case_id in SEALED_IDS]
    if positions != sorted(positions):
        errors.append("sealed ids left file order")
    rendered = _render_sealed(catalogues, s_record, x_record)
    for case_id, catalogues_by_arm in rendered.items():
        fields = next(case["fields"] for case in s_record["cases"] if case["case_id"] == case_id)
        cue_tools = next(case["tools"] for case in x_record["cases"] if case["case_id"] == case_id)
        errors.extend(f"{case_id}: {item}" for item in composition_errors(catalogues_by_arm, fields, cue_tools))
        errors.extend(f"{case_id}: {item}" for item in structural_errors(catalogues_by_arm))
        errors.extend(f"{case_id}: {item}" for item in sibling_name_errors(catalogues_by_arm))
        for condition, tools in catalogues_by_arm.items():
            document = load_json(rendered_path(case_id, condition))
            if document["tools"] != tools or document["condition"] != condition:
                errors.append(f"rendered drift {case_id} {condition}")
            errors.extend(f"hidden key {case_id} {condition} {item}" for item in catalogue_leak_errors(document))
        if (root / "catalogues" / "U" / f"{case_id}.json").read_bytes() != rendered_path(case_id, "U").read_bytes():
            errors.append(f"rendered U bytes {case_id}")
    errors.extend(ledger_errors(s_record, catalogues))
    errors.extend(cue_rule_errors(x_record, catalogues, rendered))
    identity = _identity_rows(rendered, x_record)
    if identity["x_equals_u"] != identity["uncued_ids"]:
        errors.append("X equals U did not match the uncued ids")
    if identity["sx_equals_s"] != identity["uncued_ids"]:
        errors.append("SX equals S did not match the uncued ids")
    if identity["sx_equals_x"] != identity["s_equals_u"]:
        errors.append("SX equals X did not match S equals U")
    single_tool = [case_id for case_id in ids if len(catalogues[case_id]) == 1]
    remaining_ids = [case_id for case_id in ids if case_id not in set(SEALED_IDS)]
    counts = _counts_document(ids, categories, catalogues, identity, x_record, s_record, single_tool, remaining_ids)
    if load_json(root / "checks" / "counts.json") != counts:
        errors.append("counts drift")
    remaining = _remaining_document(remaining_ids, categories, single_tool, identity)
    if load_json(root / "remaining-work.json") != remaining:
        errors.append("remaining-work drift")
    if errors:
        preview = "\n".join(errors[:30])
        raise ValueError(f"{len(errors)} official-840 checks failed\n{preview}")
    return {
        "cases": len(ids),
        "sealed": len(SEALED_IDS),
        "remaining": len(remaining_ids),
        "provider_called": False,
        "official_settlement": False,
        "counts": counts,
    }


def _counts_document(ids, categories, catalogues, identity, x_record, s_record, single_tool, remaining_ids) -> dict:
    by_category = {category: {"sample": 0, "sealed": 0, "remaining": 0, "single_tool": 0} for category in CATEGORY_COUNTS}
    sealed = set(identity["cued_ids"]) | set(identity["uncued_ids"])
    for case_id in ids:
        bucket = by_category[categories[case_id]]
        bucket["sample"] += 1
        if len(catalogues[case_id]) == 1:
            bucket["single_tool"] += 1
        if case_id in sealed:
            bucket["sealed"] += 1
        else:
            bucket["remaining"] += 1
    return {
        "sample": SAMPLE,
        "sample_cases": len(ids),
        "counts": dict(CATEGORY_COUNTS),
        "single_tool_cases": len(single_tool),
        "multi_tool_cases": len(ids) - len(single_tool),
        "sealed_cases": len(sealed),
        "remaining_cases": len(remaining_ids),
        "by_category": by_category,
        "cued_cases": len(identity["cued_ids"]),
        "uncued_cases": len(identity["uncued_ids"]),
        "uncued_single_tool": len(x_record["coverage"]["uncued_single_tool_ids"]),
        "uncued_multi_tool": len(x_record["coverage"]["uncued_multi_tool_ids"]),
        "cued_ids": identity["cued_ids"],
        "uncued_ids": identity["uncued_ids"],
        "s_equals_u": len(identity["s_equals_u"]),
        "s_differs_from_u": len(identity["s_differs_from_u"]),
        "x_equals_u": len(identity["x_equals_u"]),
        "sx_equals_s": len(identity["sx_equals_s"]),
        "sx_equals_x": len(identity["sx_equals_x"]),
        "sx_equals_u": len(identity["sx_equals_u"]),
        "four_distinct": len(identity["four_distinct"]),
        "s_equals_u_ids": identity["s_equals_u"],
        "s_differs_from_u_ids": identity["s_differs_from_u"],
        "x_equals_u_ids": identity["x_equals_u"],
        "sx_equals_s_ids": identity["sx_equals_s"],
        "sx_equals_x_ids": identity["sx_equals_x"],
        "sx_equals_u_ids": identity["sx_equals_u"],
        "four_distinct_ids": identity["four_distinct"],
        "fact_counts": fact_counts(s_record, x_record),
        "coverage_is_not_efficiency": True,
        "shorter_wording_is_not_success": True,
        "official_settlement": False,
        "flight_ready": False,
        "note": "Identity counts are the sealed tranche. Unsealed cases are not given an S or an X judgement here.",
    }


def _remaining_document(remaining_ids, categories, single_tool, identity) -> dict:
    by_category = {category: [] for category in CATEGORY_COUNTS}
    for case_id in remaining_ids:
        by_category[categories[case_id]].append(case_id)
    return {
        "sample": SAMPLE,
        "remaining_cases": len(remaining_ids),
        "by_category_counts": {category: len(rows) for category, rows in by_category.items()},
        "single_tool_remaining": len([case_id for case_id in remaining_ids if case_id in set(single_tool)]),
        "multi_tool_remaining": len([case_id for case_id in remaining_ids if case_id not in set(single_tool)]),
        "reason": BLOCKED_REASON,
        "not_a_score": True,
        "official_settlement": False,
        "formative_12_case_pilot_is_not_this_sample": True,
        "sealed_ids_not_in_this_list": identity["cued_ids"] + [
            case_id for case_id in identity["uncued_ids"] if case_id not in identity["cued_ids"]
        ],
        "ids": remaining_ids,
    }


def _check_category_files(bfcl_root: Path) -> None:
    data_dir = resolve_data_dir(bfcl_root)
    for category, digest in CATEGORY_SHA256.items():
        path = data_dir / f"{VERSION_PREFIX}_{category}.json"
        if file_sha256(path) != digest:
            raise UsxFlightRefused(f"category file hash mismatch {path.name}")


def load_fresh(bfcl_root: Path) -> tuple[list[str], dict[str, dict]]:
    _check_category_files(bfcl_root)
    study = load_study(bfcl_root)
    order = []
    fresh = {}
    for category in STUDY_CATEGORIES:
        records = study[category]
        if len(records) != CATEGORY_COUNTS[category]:
            raise UsxFlightRefused(f"{category} count is {len(records)}")
        for record in records:
            tools = to_openai_completions_tools(record["function"])
            fresh[record["id"]] = {
                "category": category,
                "tools": tools,
                "messages": record["question"][0],
            }
            order.append(record["id"])
    if len(order) != sum(CATEGORY_COUNTS.values()):
        raise UsxFlightRefused("fresh conversion did not yield 840 cases")
    return order, fresh


def build_flight(bfcl_root: Path) -> dict:
    """Plan every official case. Unsealed cases are blocked and have no generation body."""
    verified = verify_package()
    order, fresh = load_fresh(bfcl_root)
    manifest, catalogues, _categories = _load_stored_u()
    if order != manifest["ids_in_file_order"]:
        raise UsxFlightRefused("stored U order does not match the pinned category files")
    for case_id in order:
        if catalogues[case_id] != fresh[case_id]["tools"]:
            raise UsxFlightRefused(f"fresh U does not match the stored conversion {case_id}")
    from tool_compression.official_840_tranche import SEALED_IDS, build_records

    s_record, x_record = build_records(catalogues, {case_id: fresh[case_id]["category"] for case_id in order})
    rendered = _render_sealed(catalogues, s_record, x_record)
    sealed = [case_id for case_id in order if case_id in set(SEALED_IDS)]
    blocked = [
        {"case_id": case_id, "category": fresh[case_id]["category"], "sealed": False, "reason": BLOCKED_REASON}
        for case_id in order
        if case_id not in set(SEALED_IDS)
    ]
    plans = []
    for pass_name in PASSES:
        for case_id in sealed:
            plan = make_plan(
                case_id,
                fresh[case_id]["category"],
                fresh[case_id]["messages"],
                rendered[case_id],
                pass_name,
            )
            plans.append(plan)
    by_cell = {}
    for plan in plans:
        by_cell.setdefault(plan["case_id"], {})[plan["thinking"]] = plan
    for case_id, passes in by_cell.items():
        if list(passes) != ["off", "on"]:
            raise UsxFlightRefused(f"missing thinking pass {case_id}")
        for arm in ARMS:
            off_groups = {arm_name: group["request_sha256"] for group in passes["off"]["groups"] for arm_name in group["arms"]}
            on_groups = {arm_name: group["request_sha256"] for group in passes["on"]["groups"] for arm_name in group["arms"]}
            if off_groups[arm] == on_groups[arm]:
                raise UsxFlightRefused(f"thinking passes collapsed {case_id} {arm}")
            off_body = passes["off"]["_bodies"][off_groups[arm]]
            on_body = passes["on"]["_bodies"][on_groups[arm]]
            if off_body.get("tools") != on_body.get("tools") or off_body.get("messages") != on_body.get("messages"):
                raise UsxFlightRefused(f"thinking pass changed the catalogue or the question {case_id}")
    _assert_pass_order(plans)
    return {
        "plans": plans,
        "blocked": blocked,
        "sample_cases": len(order),
        "sealed_cases": len(sealed),
        "verified": verified,
    }


def _cell_public(plan: dict) -> dict:
    return {
        "case_id": plan["case_id"],
        "category": plan["category"],
        "thinking": plan["thinking"],
        "cell": plan["cell"],
        "sealed": True,
        "catalogue_identities": plan["catalogue_identities"],
        "groups": plan["groups"],
    }


def quality_block() -> dict:
    return {
        "official_settlement": False,
        "official_scores_closed": True,
        "target_10_percent_unchanged": True,
        "resets_official_10_percent_target": False,
        "matched_length_comparison": False,
        "shorter_request_counts_as_correct": False,
        "quality": "official full-call accuracy on the saved outputs, once a later flight is separately authorized",
        "multiple_split": ["wrong_name", "right_name_wrong_args"],
        "irrelevance_parse_failure_is_abstention": False,
        "label_functions": [
            "tool_compression.usx_flight.classify_multiple",
            "tool_compression.usx_flight.classify_irrelevance",
        ],
        "contrasts": list(CONTRASTS),
        "contrast_values": {name: None for name in CONTRASTS},
        "scores": None,
        "arms": list(ARMS),
        "not_arms": list(NOT_ARMS),
        "input_t": "provider prompt_tokens",
        "prices_applied_to_T": False,
        "cache_hits_subtracted_from_T": False,
        "per_thinking_pass": True,
        "thinking_on_is_catalogue_change": False,
    }


def _later_permission(moment: datetime, sealed_complete: bool) -> dict:
    blocked_by_peak = peak_blocks(moment)
    return {
        "clock": moment.isoformat(),
        "schedule": schedule_at(moment),
        "blocked_by_peak": blocked_by_peak,
        "sealed_complete": sealed_complete,
        "live_permitted": bool(sealed_complete) and not blocked_by_peak,
    }


def run_no_api_gate(bfcl_root: Path, out: Path, ceiling: Decimal, clock) -> dict:
    """Stage A. Writes the gate. Does not read a key, open a socket, or score."""
    flight = build_flight(bfcl_root)
    moment = clock()
    schedule = schedule_at(moment)
    reserve = offpeak_reserve()
    plans = flight["plans"]
    unique = sum(len(plan["groups"]) for plan in plans)
    sealed_complete = flight["sealed_cases"] == flight["sample_cases"] and not flight["blocked"]
    gate = {
        "purpose": PURPOSE,
        "stage": "A",
        "sample": SAMPLE,
        "official_settlement": False,
        "official_scores_closed": True,
        "target_10_percent_unchanged": True,
        "no_api": True,
        "live": False,
        "provider_called": False,
        "api_key_read": False,
        "spend_cny": "0",
        "ceiling_env": CEILING_ENV,
        "ceiling_cny": format(ceiling, "f"),
        "ceiling_hardcoded": False,
        "ceiling_lifted": False,
        "ceiling_authorizes_spend_by_itself": False,
        "ceiling_note": "The value is whatever this process was given in the environment. It is not a default, and it does not authorize a later process to spend.",
        "model": MODEL,
        "model_version": MODEL_VERSION,
        "temperature": BFCL_DEFAULT_TEMPERATURE,
        "store": BFCL_STORE,
        "thinking_passes": list(PASSES),
        "thinking_off": THINKING_BODY["off"],
        "thinking_on": THINKING_BODY["on"],
        "thinking_on_is_catalogue_change": False,
        "scoring_alias": EVALUATE_ALIAS,
        "scoring_alias_is_generation_model": False,
        "arms": list(ARMS),
        "not_arms": list(NOT_ARMS),
        "gorilla_commit": GORILLA_COMMIT,
        "category_sha256": dict(CATEGORY_SHA256),
        "u_source": "fresh conversion of the pinned BFCL records, checked equal to the stored U catalogues",
        "u_backfill": False,
        "sample_cases": flight["sample_cases"],
        "sealed_cases": flight["sealed_cases"],
        "blocked_cases": len(flight["blocked"]),
        "flight_ready": sealed_complete,
        "live_requires_all_840_sealed": True,
        "partial_live_refused": True,
        "unique_payloads_if_the_sealed_cells_were_sent": unique,
        "shared_within_cell_only": True,
        "cell": "one case id and one thinking pass",
        "cross_cell_payloads_are_not_shared": True,
        "passes": {
            pass_name: [_cell_public(plan) for plan in plans if plan["thinking"] == pass_name]
            for pass_name in PASSES
        },
        "blocked": flight["blocked"],
        "off_peak_only": True,
        "do_not_start_or_continue_into_peak": True,
        "peak_card_used": False,
        "peak_continuation_switch": False,
        "clock": moment.isoformat(),
        "schedule_at_gate": schedule,
        "stopped_for_peak": schedule == "peak",
        "live_would_start": False,
        "later_at_gate_clock": _later_permission(moment, sealed_complete),
        "aimed_offpeak_example": _later_permission(AIMED_CLOCK, sealed_complete),
        "rate_card": offpeak_rate_card(),
        "pre_call_reserve_cny": format(reserve, "f"),
        "peak_reserve_not_used_cny": format(pre_call_reserve_cny("peak"), "f"),
        "reserve_fits_supplied_ceiling": remaining_allows_call(Decimal("0"), ceiling, reserve),
        "reserve_is_one_call_not_the_whole_sample": True,
        "evaluate": {
            "argv_by_pass_and_arm": {
                pass_name: {
                    arm: evaluate_argv(pass_name, arm, Path("result") / f"thinking-{pass_name}" / arm, Path("score") / f"thinking-{pass_name}" / arm)
                    for arm in ARMS
                }
                for pass_name in PASSES
            },
            "partial_eval": False,
            "categories": list(STUDY_CATEGORIES),
            "why_not_partial": "The official flight is the full 200, 400, and 240. A short result file is not this sample. Live is refused until every case is sealed.",
            "ran": False,
        },
        "billed_basis_T": billed_basis_t(0) | {"T": None, "note": "T is recorded per live call from prompt_tokens. The gate has no call."},
        "quality": quality_block(),
        "package_verified": True,
        "verified_sealed_cases": flight["verified"]["sealed"],
    }
    if gate["provider_called"] or gate["api_key_read"] or Decimal(gate["spend_cny"]) != 0 or gate["official_settlement"]:
        raise UsxFlightRefused("no-api gate recorded a call, a spend, or a settlement")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "gate.json").write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")
    return gate


def evaluate_argv(pass_name: str, arm: str, result_dir: Path, score_dir: Path) -> list[str]:
    if pass_name not in PASSES or arm not in ARMS:
        raise UsxFlightRefused("evaluate target is not one official pass and arm")
    argv = [
        "python",
        "-m",
        "bfcl_eval",
        "evaluate",
        "--model",
        EVALUATE_ALIAS,
        "--test-category",
        ",".join(STUDY_CATEGORIES),
        "--result-dir",
        str(result_dir),
        "--score-dir",
        str(score_dir),
    ]
    text = " ".join(argv)
    if "--partial-eval" in argv or "generate" in argv or "openfunctions_evaluation" in text:
        raise UsxFlightRefused("official 840 evaluate argv must not be partial and must not generate")
    if MODEL in argv or EVALUATE_ALIAS not in argv:
        raise UsxFlightRefused("evaluate argv must use the scoring alias")
    return argv


def run_live(bfcl_root: Path, out: Path, ceiling: Decimal, clock, client) -> dict:
    """Paid path for a later operator. Refuses until all 840 cases are sealed.

    There is no peak-continuation argument. A peak clock stops the run before
    a key is read.
    """
    verified = verify_package()
    if verified["sealed"] != verified["cases"] or verified["remaining"] != 0:
        raise UsxFlightRefused("official 840 set is not fully sealed")
    flight = build_flight(bfcl_root)
    if flight["blocked"] or flight["sealed_cases"] != flight["sample_cases"]:
        raise UsxFlightRefused("official 840 set is not fully sealed")
    return execute_plans(
        flight["plans"],
        out,
        ceiling,
        clock,
        client,
        sealed=True,
        official_package=True,
    )


def execute_plans(plans: list[dict], out: Path, ceiling: Decimal, clock, client, *, sealed: bool, official_package: bool = False) -> dict:
    """Send planned bodies. Tests pass a scripted client. Official entry requires the full sample."""
    if sealed is not True:
        raise UsxFlightRefused("official 840 set is not fully sealed")
    _assert_pass_order(plans)
    if official_package:
        case_ids = [plan["case_id"] for plan in plans if plan["thinking"] == "off"]
        if len(case_ids) != sum(CATEGORY_COUNTS.values()) or len(set(case_ids)) != len(case_ids):
            raise UsxFlightRefused("official 840 set is not fully sealed")
        if [plan["case_id"] for plan in plans if plan["thinking"] == "on"] != case_ids:
            raise UsxFlightRefused("thinking-on pass is not the same catalogues")
    spent = Decimal("0")
    calls = []
    out = Path(out)
    result_root = out / "result"
    for plan in plans:
        for group in plan["groups"]:
            moment = clock()
            if peak_blocks(moment):
                _write_stop(out, spent, "peak", "peak_hours", ceiling, calls)
                raise UsxFlightRefused("peak_hours")
            reserve = offpeak_reserve()
            if not remaining_allows_call(spent, ceiling, reserve):
                _write_stop(out, spent, "off-peak", "pre-call reserve would pass the supplied ceiling", ceiling, calls)
                raise UsxFlightRefused("pre-call reserve would pass the supplied ceiling")
            if client is None:
                client = build_live_client()
            body = plan["_bodies"][group["request_sha256"]]
            assert_official_body(body)
            if body["thinking"] != thinking_body(plan["thinking"]):
                raise UsxFlightRefused("thinking field does not match the pass")
            payload = client.complete(body)
            bill = usage_bill("off-peak", payload.get("usage") if isinstance(payload, dict) else None)
            if bill["schedule"] != "off-peak":
                raise UsxFlightRefused("peak card used")
            spent += Decimal(bill["spend_cny"])
            observation = {
                "case_id": plan["case_id"],
                "cell": plan["cell"],
                "thinking": plan["thinking"],
                "arms": list(group["arms"]),
                "shared": len(group["arms"]) > 1,
                "request_sha256": group["request_sha256"],
                "catalogue_identities": plan["catalogue_identities"],
                "schedule": "off-peak",
                "rate_card": offpeak_rate_card(),
                "clock": moment.isoformat(),
                "bill": bill,
                "provider_called": True,
            }
            calls.append(observation)
            if spent > ceiling:
                _write_stop(out, spent, "off-peak", "settled spend passed the supplied ceiling", ceiling, calls)
                raise UsxFlightRefused("settled spend passed the supplied ceiling")
            if not isinstance(payload, dict) or not payload.get("choices"):
                _write_stop(out, spent, "off-peak", "provider response had no choice", ceiling, calls)
                raise UsxFlightRefused("provider response had no choice")
            if plan["thinking"] == "off" and not _thinking_stayed_off(payload):
                _write_stop(out, spent, "off-peak", "provider response included thinking on the thinking-off pass", ceiling, calls)
                raise UsxFlightRefused("provider response included thinking on the thinking-off pass")
            for arm in group["arms"]:
                _append_result(result_root, plan["thinking"], arm, plan["category"], plan["case_id"], payload, bill)
    record = {
        "purpose": PURPOSE,
        "official_settlement": False,
        "live": True,
        "provider_called": True,
        "peak_card_used": False,
        "spend_cny": format(spent, "f"),
        "ceiling_cny": format(ceiling, "f"),
        "ceiling_lifted": False,
        "calls": calls,
        "quality": quality_block(),
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "live.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def _write_stop(out: Path, spent: Decimal, schedule: str, reason: str, ceiling: Decimal, calls: list) -> None:
    out.mkdir(parents=True, exist_ok=True)
    record = {
        "purpose": PURPOSE,
        "official_settlement": False,
        "provider_called": bool(calls),
        "api_key_in_record": False,
        "spend_cny": format(spent, "f"),
        "stop_reason": reason,
        "schedule_at_stop": schedule,
        "peak_card_used": False,
        "pre_call_reserve_cny": format(offpeak_reserve(), "f"),
        "ceiling_cny": format(ceiling, "f"),
        "ceiling_lifted": False,
        "calls_already_settled": len(calls),
    }
    (out / "stop.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def _append_result(result_root: Path, pass_name: str, arm: str, category: str, case_id: str, payload: dict, bill: dict) -> None:
    directory = result_root / f"thinking-{pass_name}" / arm / EVALUATE_ALIAS
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{RESULT_VERSION_PREFIX}_{category}_result.json"
    row = {
        "id": case_id,
        "result": _fc_result(payload),
        "input_token_count": bill["T"],
        "output_token_count": bill["output_tokens"],
        "thinking_pass": pass_name,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    _tokens(bill["T"], "prompt_tokens")


def build_live_client():
    """Read the key and return a client. Stage A never calls this."""
    from tool_compression.official_840_provider import LiveClient, require_api_key

    return LiveClient(require_api_key())


def materialize_package(bfcl_root: Path) -> dict:
    """Write fresh U, the sealed tranche, and the check files. Does not call a provider."""
    order, fresh = load_fresh(bfcl_root)
    root = package_dir()
    categories = {case_id: fresh[case_id]["category"] for case_id in order}
    for case_id in order:
        write_json(u_path(case_id), u_document(case_id, categories[case_id], fresh[case_id]["tools"]))
    manifest = {
        "sample": SAMPLE,
        "gorilla_commit": GORILLA_COMMIT,
        "gorilla_repository": "https://github.com/ShishirPatil/gorilla",
        "conversion": "to_openai_completions_tools",
        "possible_answer_hashes_may_differ": True,
        "questions_stored": False,
        "counts": dict(CATEGORY_COUNTS),
        "category_sha256": dict(CATEGORY_SHA256),
        "category_files": {category: f"{VERSION_PREFIX}_{category}.json" for category in CATEGORY_COUNTS},
        "ids_in_file_order": order,
    }
    write_json(manifest_path(), manifest)
    from tool_compression.official_840_tranche import SEALED_IDS, build_records

    catalogues = {case_id: fresh[case_id]["tools"] for case_id in order}
    s_record, x_record = build_records(catalogues, categories)
    write_json(root / "edits" / "s-record.json", s_record)
    write_json(root / "edits" / "x-record.json", x_record)
    rendered = _render_sealed(catalogues, s_record, x_record)
    for case_id in SEALED_IDS:
        for condition in ARMS:
            write_json(
                rendered_path(case_id, condition),
                condition_document(case_id, categories[case_id], condition, rendered[case_id][condition]),
            )
    hashes = {
        "algorithm": "sha256",
        "files": {f"catalogues/U/{case_id}.json": file_sha256(u_path(case_id)) for case_id in order},
    }
    write_json(root / "checks" / "u-sha256.json", hashes)
    write_json(root / "checks" / "frozen-integrity.json", compute_frozen_hashes())
    identity = _identity_rows(rendered, x_record)
    single_tool = [case_id for case_id in order if len(catalogues[case_id]) == 1]
    remaining_ids = [case_id for case_id in order if case_id not in set(SEALED_IDS)]
    write_json(
        root / "checks" / "counts.json",
        _counts_document(order, categories, catalogues, identity, x_record, s_record, single_tool, remaining_ids),
    )
    write_json(
        root / "remaining-work.json",
        _remaining_document(remaining_ids, categories, single_tool, identity),
    )
    return verify_package()
