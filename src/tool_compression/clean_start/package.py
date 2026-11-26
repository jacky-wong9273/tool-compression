"""Offline review package for the U/S/X/SX editors over the whole locked scope.

Everything here is local: the vendored BFCL questions' tool catalogues, the
editors, and a local tokenizer. No provider is contacted and nothing is billed.
Token counts are local o200k_base counts, not provider usage. Questions and
gold answers are read only to find each question's tool catalogue and id; the
editors receive the catalogue alone.
"""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
from pathlib import Path
import json
import platform

from tool_compression.adapter import description_slots
from tool_compression.clean_start.descriptions import split_protected, suite_context, suite_preamble
from tool_compression.clean_start.editor_s import S_RULES_VERSION, context_id, edit_catalogue
from tool_compression.clean_start.editor_x import X_RULES_VERSION, qualify_catalogue
from tool_compression.clean_start.load import prompt_manifest
from tool_compression.clean_start.pilot import study_dir
from tool_compression.clean_start.pin import ARMS, OFFICIAL_SETTLEMENT, STUDY_ID, study_manifest
from tool_compression.clean_start.prepare import model_facing_tools
from tool_compression.clean_start.render import render_tools
from tool_compression.clean_start.revision import population_summary, revision_diff
from tool_compression.clean_start.runner import arm_tools
from tool_compression.clean_start.scope import in_scope_questions, study_categories
from tool_compression.config import LOCAL_TOKENIZER
from tool_compression.count import TiktokenCounter, dump_request

PAIRS = (("S", "U"), ("X", "U"), ("SX", "S"), ("SX", "X"), ("SX", "U"))
BEFORE_SUMMARY = "population_c47b186c.json"


def _hash(value) -> str:
    return sha256(dump_request(value).encode("utf-8")).hexdigest()


def _field_tokens(tools: list[dict], counter) -> int:
    total = 0
    for tool in tools:
        for _pointer, container, key in description_slots(tool):
            total += counter.count(container[key])
    return total


def _pilot_ids() -> set[str]:
    draw = json.loads((study_dir() / "pilot" / "draw.json").read_text(encoding="utf-8"))
    return {row["case_id"] for row in draw["rows"]}


def _validation_ids() -> set[str]:
    draw = json.loads((study_dir() / "validation" / "draw.json").read_text(encoding="utf-8"))
    return {row["case_id"] for row in draw["order"] if not row["prereq"]}


_X_REASONS = (
    ("Single-tool control", "single_tool_control"),
    ("No other tool", "no_other_tool"),
    ("Different actions", "different_actions"),
    ("One action text does not open with a verb", "no_leading_verb"),
    ("One side has no action text", "no_action_text"),
    ("The action texts are identical", "identical_action_text"),
    ("The differing wording is not one window", "window_too_long"),
    ("The differing window has no content word", "window_without_content"),
    ("The differing window carries a negation", "window_negation"),
    ("The shared wording is shorter", "shared_wording_too_short"),
    ("The shared wording has no content word", "shared_wording_without_content"),
    ("The target's differing words end in a coordinator", "target_claims_rival_object"),
    ("The two action texts act on different objects", "different_objects"),
    ("The rival's differing phrase", "phrase_not_a_noun_phrase"),
    ("The rival's name already spells", "rival_name_spells_difference"),
    ("The cue", "cue_form"),
)


def _x_reason(text: str) -> str:
    closest = text.removeprefix("No rival qualifies. Closest refusal: ")
    for prefix, key in _X_REASONS:
        if closest.startswith(prefix):
            return key
    return "other"


def _coverage(tools: list[dict], rendered: dict) -> dict:
    """What each editor did with every field and tool of one catalogue: edits, abstentions, cues."""
    _edited, rows = edit_catalogue(json.loads(json.dumps(tools)))
    s_fields = Counter()
    for row in (row for tool_rows in rows for row in tool_rows):
        s_fields["fields"] += 1
        if row["adopted"]:
            s_fields["edited"] += 1
            for rule in row["change_class"].split("+"):
                s_fields[f"edited:{rule}"] += 1
        else:
            s_fields[f"kept:{row['keep_reason']}"] += 1
    x_tools = Counter()
    for row in rendered["x_decisions"]:
        x_tools["tools"] += 1
        if row["cue"]:
            x_tools["cued"] += 1
            x_tools[f"cued:{(row['axis'] or '').split(':')[0]}"] += 1
        else:
            x_tools[f"uncued:{_x_reason(row['no_cue_reason'] or '')}"] += 1
    return {"s_fields": s_fields, "x_tools": x_tools}


def _empty_totals() -> dict:
    return {
        "questions": 0,
        "field_tokens": {arm: 0 for arm in ARMS},
        "tools_tokens": {arm: 0 for arm in ARMS},
        "changed_questions": {arm: 0 for arm in ARMS if arm != "U"},
        "cued_tools": 0,
        "cue_tokens": 0,
        "coverage": {"s_fields": Counter(), "x_tools": Counter()},
        "u_anatomy": Counter(),
    }


def _add(totals: dict, record: dict) -> None:
    totals["questions"] += 1
    for arm in ARMS:
        totals["field_tokens"][arm] += record["field_tokens"][arm]
        totals["tools_tokens"][arm] += record["tools_tokens"][arm]
    for arm in totals["changed_questions"]:
        totals["changed_questions"][arm] += int(record["changed"][arm])
    totals["cued_tools"] += record["cued_tools"]
    totals["cue_tokens"] += record["cue_tokens"]
    for editor, counts in record["coverage"].items():
        totals["coverage"][editor].update(counts)
    totals["u_anatomy"].update(record["anatomy"])


def _with_deltas(totals: dict) -> dict:
    deltas = {}
    for left, right in PAIRS:
        field = totals["field_tokens"][left] - totals["field_tokens"][right]
        tools = totals["tools_tokens"][left] - totals["tools_tokens"][right]
        base_field = totals["field_tokens"][right]
        base_tools = totals["tools_tokens"][right]
        deltas[f"{left}-{right}"] = {
            "field_tokens": field,
            "field_percent": round(100 * field / base_field, 3) if base_field else None,
            "tools_tokens": tools,
            "tools_percent": round(100 * tools / base_tools, 3) if base_tools else None,
        }
    coverage = {editor: dict(sorted(counts.items())) for editor, counts in totals["coverage"].items()}
    coverage["questions_without_s_edit"] = totals["questions"] - totals["changed_questions"]["S"]
    coverage["questions_without_x_cue"] = totals["questions"] - totals["changed_questions"]["X"]
    coverage["questions_unchanged_in_sx"] = totals["questions"] - totals["changed_questions"]["SX"]
    base = totals["tools_tokens"]["U"]
    anatomy = {"outside_descriptions": base - totals["field_tokens"]["U"], **totals["u_anatomy"]}
    u_anatomy = {
        name: {"tokens": anatomy.get(name, 0), "percent_of_u_tools": round(100 * anatomy.get(name, 0) / base, 3) if base else None}
        for name in _ANATOMY
    }
    return {**totals, "coverage": coverage, "u_anatomy": u_anatomy, "deltas": deltas}


_ANATOMY = (
    "outside_descriptions", "function_descriptions", "parameter_descriptions", "language_hints",
    "repeated_language_hints", "suite_preambles", "repeated_suite_preambles",
)


def _catalogue_record(tools: list[dict], counter, cache: dict) -> dict:
    key = _hash(tools)
    if key in cache:
        return cache[key]
    rendered = render_tools(tools)
    arms = rendered["arms"]
    cues = [row["cue"] for row in rendered["x_decisions"]]
    cue_tokens = 0
    for tool, cue in zip(arms["U"], cues):
        if cue:
            text = tool["function"]["description"]
            cue_tokens += counter.count(text + " " + cue) - counter.count(text)
    record = {
        "catalogue_sha256": key,
        "tools": len(tools),
        "field_tokens": {arm: _field_tokens(arms[arm], counter) for arm in ARMS},
        "tools_tokens": {arm: counter.count(dump_request(arms[arm])) for arm in ARMS},
        "changed": {arm: arms[arm] != arms["U"] for arm in ARMS},
        "cued_tools": sum(1 for cue in cues if cue),
        "cue_tokens": cue_tokens,
        "arm_sha256": {arm: _hash(arms[arm]) for arm in ARMS},
        "rendered": rendered,
        "integrity": _integrity(arms, rendered["x_decisions"]),
        "coverage": _coverage(tools, rendered),
        "anatomy": _anatomy(arms["U"], counter),
    }
    cache[key] = record
    return record


def _anatomy(tools: list[dict], counter) -> Counter:
    """Where the U tools tokens sit: description kinds, and request-level text repeated after its first tool."""
    parts = Counter()
    seen_hints: set[str] = set()
    seen_members: set[str] = set()
    for tool in tools:
        for pointer, container, key in description_slots(tool):
            kind = "function_descriptions" if pointer == "/function/description" else "parameter_descriptions"
            parts[kind] += counter.count(container[key])
        head, hint = split_protected(tool["function"]["description"])
        if hint:
            parts["language_hints"] += counter.count(hint)
            if hint in seen_hints:
                parts["repeated_language_hints"] += counter.count(hint)
            seen_hints.add(hint)
        suite = suite_preamble(head)
        if suite:
            preamble = counter.count(head[: suite["core_start"]])
            membership = head[suite["membership"][0]:suite["membership"][1]]
            parts["suite_preambles"] += preamble
            if membership in seen_members:
                parts["repeated_suite_preambles"] += preamble
            seen_members.add(membership)
    return parts


def _integrity(arms: dict, decisions: list[dict]) -> dict:
    cues = [row["cue"] for row in decisions]
    names = [tool["function"]["name"] for tool in arms["U"]]
    checks = {
        "membership_and_order": all([tool["function"]["name"] for tool in arms[arm]] == names for arm in ARMS),
        "parameters_identical_outside_descriptions": True,
        "uncued_x_equals_u": True,
        "uncued_sx_equals_s": True,
        "cued_x_is_u_plus_cue": True,
        "cued_sx_is_s_plus_cue": True,
        "text_cue_phrase_in_rival_u_and_s": True,
        "dropped_suite_elaboration_still_in_s_request": _suite_context_kept(arms),
        "every_language_hint_still_in_s_request": _excerpts_kept(arms, _hint_of),
        "every_membership_sentence_still_in_s_request": _excerpts_kept(arms, _membership_of),
    }
    for row in decisions:
        if row["cue"] and row["rival_phrase"]:
            rival = row["rival_index"]
            checks["text_cue_phrase_in_rival_u_and_s"] &= all(
                row["rival_phrase"] in arms[arm][rival]["function"]["description"] for arm in ("U", "S")
            )
    for index, cue in enumerate(cues):
        u_text = arms["U"][index]["function"]["description"]
        s_text = arms["S"][index]["function"]["description"]
        x_text = arms["X"][index]["function"]["description"]
        sx_text = arms["SX"][index]["function"]["description"]
        if cue:
            checks["cued_x_is_u_plus_cue"] &= x_text == u_text + " " + cue
            checks["cued_sx_is_s_plus_cue"] &= sx_text == s_text + " " + cue
        else:
            checks["uncued_x_equals_u"] &= arms["X"][index] == arms["U"][index]
            checks["uncued_sx_equals_s"] &= arms["SX"][index] == arms["S"][index]
        for arm in ARMS:
            checks["parameters_identical_outside_descriptions"] &= (
                _blank(arms[arm][index]) == _blank(arms["U"][index])
            )
    return checks


def _suite_context_kept(arms: dict) -> bool:
    """Every suite elaboration in the U request is still somewhere in the S request."""
    s_texts = [tool["function"]["description"] for tool in arms["S"]]
    for tool in arms["U"]:
        context = suite_context(tool["function"]["description"])
        if context is not None and not any(context in text for text in s_texts):
            return False
    return True


def _excerpts_kept(arms: dict, excerpt_of) -> bool:
    """Every request-level excerpt of the U request is still verbatim in some S description."""
    s_texts = [tool["function"]["description"] for tool in arms["S"]]
    for tool in arms["U"]:
        excerpt = excerpt_of(tool["function"]["description"])
        if excerpt and not any(excerpt in text for text in s_texts):
            return False
    return True


def _hint_of(description: str) -> str:
    return split_protected(description)[1]


def _membership_of(description: str) -> str | None:
    head, _hint = split_protected(description)
    suite = suite_preamble(head)
    return head[suite["membership"][0]:suite["membership"][1]] if suite else None


def _held_out_keeps_sent_bytes(case: dict) -> bool:
    """Tools sent before each held-out batch keep their bytes in every arm afterwards."""
    if not case.get("held_out"):
        return True
    batches: list[list[dict]] = []
    before = {arm: arm_tools(case["function"], case["category"], arm) for arm in ARMS}
    for turn in sorted(case["held_out"], key=int):
        batches = batches + [list(case["held_out"][turn])]
        after = {arm: arm_tools(case["function"], case["category"], arm, batches) for arm in ARMS}
        for arm in ARMS:
            if dump_request(after[arm][: len(before[arm])]) != dump_request(before[arm]):
                return False
        before = after
    return True


def _blank(tool: dict) -> str:
    copied = json.loads(json.dumps(tool))
    for _pointer, container, key in description_slots(copied):
        container[key] = ""
    return dump_request(copied)


def build_package(out_dir: Path) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    counter = TiktokenCounter(LOCAL_TOKENIZER)
    pilot = _pilot_ids()
    validation = _validation_ids()
    cache: dict[str, dict] = {}
    by_category: dict[str, dict] = {}
    overall = _empty_totals()
    outside_pilot = _empty_totals()
    draws = {"pilot_draw": _empty_totals(), "validation_draw": _empty_totals(), "outside_both_draws": _empty_totals()}
    integrity = Counter()
    integrity_failures = []
    s_ledger: dict[str, dict] = {}
    s_keep = Counter()
    x_ledger: dict[str, dict] = {}
    examples: dict[str, dict] = {}
    for category in study_categories():
        totals = _empty_totals()
        questions = in_scope_questions(category)
        for case in questions:
            tools = model_facing_tools(case["function"], case["category"])
            seen = _hash(tools) in cache
            record = _catalogue_record(tools, counter, cache)
            _add(totals, record)
            _add(overall, record)
            if case["id"] not in pilot:
                _add(outside_pilot, record)
            if case["id"] in pilot:
                _add(draws["pilot_draw"], record)
            if case["id"] in validation:
                _add(draws["validation_draw"], record)
            if case["id"] not in pilot | validation:
                _add(draws["outside_both_draws"], record)
            checks = {**record["integrity"], "held_out_tools_keep_sent_bytes": _held_out_keeps_sent_bytes(case)}
            for name, ok in checks.items():
                integrity[name] += int(ok)
                if not ok:
                    integrity_failures.append({"case_id": case["id"], "check": name})
            if not seen:
                _ledger_s(tools, s_ledger, s_keep)
            _ledger_x(record, x_ledger)
            _examples(category, case, record, examples)
        by_category[category] = _with_deltas(totals)
    integrity_summary = {
        "questions_checked": overall["questions"],
        "unique_catalogues": len(cache),
        "passed_per_check": dict(integrity),
        "failures": integrity_failures,
        "render_verify_arms_fail_closed": True,
    }
    tables = {
        "study": STUDY_ID,
        "official_settlement": OFFICIAL_SETTLEMENT,
        "measurement": (
            "Local counts with tiktoken o200k_base. field_tokens sums every editable description "
            "string (function and parameter descriptions; response-schema descriptions are not "
            "editable and not counted). tools_tokens counts the compact JSON of the whole tools "
            "array, the part of a request the arms change. Neither is provider-billed usage; the "
            "provider tokenizer and chat template differ. The initial catalogue of each in-scope "
            "question is counted once per question; held-out miss_func turns are not included. "
            "coverage counts, per question, every editable field S saw (edited, then once under each "
            "rule that edited it, or kept by reason) and every tool X saw (cued by axis kind, or "
            "uncued by the closest refusal). u_anatomy splits the U tools tokens: description kinds are "
            "summed field by field; outside_descriptions is tools tokens minus those fields (names, "
            "schema, JSON punctuation; approximate, since tokens do not add across field seams); hints "
            "and suite preambles are inside function descriptions, and their repeated_ parts are the "
            "occurrences after the first tool of the request that carries the same hint or membership."
        ),
        "exposure": (
            "pilot_draw (41 cases) and validation_draw (313 cases) have both been flown and diagnosed; "
            "they are exposed regression data, not unseen validation."
        ),
        "rules": {"S": S_RULES_VERSION, "X": X_RULES_VERSION},
        "all_in_scope": _with_deltas(overall),
        "excluding_pilot_draw": _with_deltas(outside_pilot),
        "draws": {name: _with_deltas(totals) for name, totals in draws.items()},
        "by_category": by_category,
    }
    _write(out_dir / "token_tables.json", tables)
    _write(out_dir / "integrity.json", integrity_summary)
    s_rows = [s_ledger[key] for key in sorted(s_ledger) if s_ledger[key] is not None]
    _write_jsonl(out_dir / "s_ledger.jsonl", s_rows)
    _write_jsonl(out_dir / "x_ledger.jsonl", [x_ledger[key] for key in sorted(x_ledger)])
    _write(out_dir / "s_keep_reasons.json", {"rules": S_RULES_VERSION, "fields_kept_by_reason": dict(sorted(s_keep.items()))})
    _write(out_dir / "examples.json", examples)
    (out_dir / "EXAMPLES.md").write_text(_examples_markdown(examples), encoding="utf-8")
    from tool_compression.clean_start.report import (
        PILOT_EVIDENCE,
        REVISED_EVIDENCE,
        VALIDATION_EVIDENCE,
        VALIDATION_POPULATION,
        write_pilot_report,
        write_revised_pilot_report,
        write_validation_flight_report,
    )

    write_pilot_report(study_dir() / PILOT_EVIDENCE, out_dir / "pilot_2026_11_25_analysis.json")
    write_revised_pilot_report(study_dir() / REVISED_EVIDENCE, out_dir / "pilot_2026_11_25_revised_analysis.json")
    write_validation_flight_report(study_dir() / VALIDATION_EVIDENCE, out_dir / "validation_2026_11_25_analysis.json")
    measurement = "Local o200k_base counts of the whole tools array of each in-scope question's initial catalogue."
    before = json.loads((study_dir() / REVISED_EVIDENCE / BEFORE_SUMMARY).read_text(encoding="utf-8"))
    flown = json.loads((study_dir() / VALIDATION_EVIDENCE / VALIDATION_POPULATION).read_text(encoding="utf-8"))
    after = population_summary(
        study_categories(), in_scope_questions, model_facing_tools, render_tools, counter, dump_request
    )
    _write(out_dir / "revision_vs_c47b186c.json", {
        "study": STUDY_ID,
        "official_settlement": OFFICIAL_SETTLEMENT,
        "before_source": f"{REVISED_EVIDENCE}/{BEFORE_SUMMARY} (editors at {before['source_commit']})",
        "measurement": measurement,
        **revision_diff(before, flown),
    })
    _write(out_dir / "revision_vs_0bf829c6.json", {
        "study": STUDY_ID,
        "official_settlement": OFFICIAL_SETTLEMENT,
        "before_source": f"{VALIDATION_EVIDENCE}/{VALIDATION_POPULATION} (editors at {flown['source_commit']})",
        "after_source": "current editors",
        "measurement": measurement,
        **revision_diff(flown, after),
    })
    from tool_compression.clean_start.validation import validation_report

    _write(out_dir / "validation_20261126.json", {
        **validation_report(counter),
        "editors": {"S": S_RULES_VERSION, "X": X_RULES_VERSION},
        "frozen_plan": (
            "validation/cost.json is the plan the 0bf829c6 flight was sized and checked against, with the "
            "editors of that commit. This file is the same report recomputed with the editors above."
        ),
    })
    vendored = prompt_manifest()
    manifest = {
        "study": STUDY_ID,
        "official_settlement": OFFICIAL_SETTLEMENT,
        "study_manifest": study_manifest(),
        "bfcl_commit": vendored.get("bfcl_commit"),
        "vendored_manifest_sha256": sha256(
            (study_dir() / "bfcl" / "manifest.json").read_bytes()
        ).hexdigest() if (study_dir() / "bfcl" / "manifest.json").is_file() else None,
        "rules": {"S": S_RULES_VERSION, "X": X_RULES_VERSION},
        "tokenizer": {"encoding": LOCAL_TOKENIZER, "backend": counter.backend},
        "python": platform.python_version(),
        "commands": {
            "freeze": "python -m tool_compression.clean_start freeze",
            "package": "python -m tool_compression.clean_start package",
            "pilot_report": "python -m tool_compression.clean_start report-pilot",
            "revised_pilot_report": "python -m tool_compression.clean_start report-pilot --revised",
            "validation_flight_report": "python -m tool_compression.clean_start report-validation",
            "before_summary": (
                "PYTHONPATH=<worktree of c47b186c>/src python scripts/clean_start_sent_digest.py population"
            ),
            "flown_sent_digest": (
                "PYTHONPATH=<worktree of c47b186c>/src python scripts/clean_start_sent_digest.py conversations"
            ),
            "validation_flown_summary": (
                "PYTHONPATH=<worktree of 0bf829c6>/src python scripts/clean_start_sent_digest.py population"
            ),
            "validation_flown_sent_digest": (
                "PYTHONPATH=<worktree of 0bf829c6>/src python scripts/clean_start_sent_digest.py validation"
            ),
            "score_existing_results": (
                "python -m tool_compression.clean_start evaluate --out <run dir> "
                "--bfcl-root <pinned gorilla checkout> --thinking off"
            ),
            "validation_dry_plan": (
                "python -m tool_compression.clean_start run --validation --thinking off "
                "--memory-prereqs matched --ceiling-usd 20 --out <new empty dir>"
            ),
            "preliminary_dry_plan": (
                "python -m tool_compression.clean_start run --preliminary --thinking off "
                "--memory-prereqs matched --ceiling-usd 42 --out <new empty dir>"
            ),
            "preliminary_resume_check": (
                "python -m tool_compression.clean_start run --preliminary --resume --thinking off "
                "--memory-prereqs matched --ceiling-usd 42 --out <the stopped run dir>"
            ),
            "preliminary_resume": (
                "python -m tool_compression.clean_start run --preliminary --live --authorize-live "
                "--thinking off --memory-prereqs matched --ceiling-usd 42 "
                "--bfcl-root <pinned gorilla checkout> --out <the stopped run dir> --resume"
            ),
        },
        "files": {},
    }
    for path in sorted(out_dir.iterdir()):
        if path.name == "manifest.json" or not path.is_file():
            continue
        manifest["files"][path.name] = sha256(path.read_bytes()).hexdigest()
    _write(out_dir / "manifest.json", manifest)
    return {
        "questions": overall["questions"],
        "unique_catalogues": len(cache),
        "integrity_failures": len(integrity_failures),
        "s_ledger_rows": len(s_rows),
        "x_ledger_catalogues": len(x_ledger),
    }


_S_STATES = ("suite_context_state", "membership_state", "hint_state")


def _ledger_s(tools: list[dict], ledger: dict, keep: Counter) -> None:
    """One row per distinct tool, carried-excerpt state, and field.

    S sees one tool plus which verbatim suite elaborations, membership sentences
    and language hints earlier tools carry, so a tool is edited identically
    wherever it has the same state, and each (tool, state) is recorded once,
    from the first catalogue that holds it (``tool_index`` is its index there).
    """
    _edited, all_rows = edit_catalogue(json.loads(json.dumps(tools)))
    for index, (tool, rows) in enumerate(zip(tools, all_rows)):
        states = {name: rows[0][name] if rows else None for name in _S_STATES}
        state = "|".join(str(states[name]) for name in _S_STATES)
        tool_key = f"tool:{context_id(tool)}:{state}"
        if tool_key in ledger:
            continue
        ledger[tool_key] = None
        for row in rows:
            key = f"{row['context_id']}{row['pointer']}:{state}"
            if not row["adopted"]:
                if row["keep_reason"]:
                    keep[row["keep_reason"]] += 1
                continue
            ledger[key] = {
                "rules_version": row["rules_version"],
                "context_id": row["context_id"],
                "function": row["function_name"],
                "tool_index": index,
                "pointer": row["pointer"],
                **states,
                "before": row["original"],
                "after": row["final"],
                "change_class": row["change_class"],
                "facts": row["facts"],
            }


def _ledger_x(record: dict, ledger: dict) -> None:
    key = record["catalogue_sha256"]
    if key in ledger:
        return
    decisions = record["rendered"]["x_decisions"]
    if not any(row["cue"] for row in decisions):
        return
    tools = record["rendered"]["arms"]["U"]
    full = qualify_catalogue(json.loads(json.dumps(tools)))
    ledger[key] = {
        "catalogue_sha256": key,
        "rules_version": X_RULES_VERSION,
        "tools": [tool["function"]["name"] for tool in tools],
        "cues": [
            {
                "target": row["function_name"],
                "rival": row["rival"]["function_name"],
                "axis": row["axis"],
                "cue": row["cue"],
                "evidence": row["evidence"],
            }
            for row in full
            if row["cue"]
        ],
        "uncued": [
            {"target": row["function_name"], "reason": row["no_cue_reason"]}
            for row in full
            if not row["cue"]
        ],
    }


def _examples(category: str, case: dict, record: dict, examples: dict) -> None:
    slot = examples.setdefault(category, {"S_edit": None, "X_cue": None, "unchanged": None})
    rendered = record["rendered"]
    if slot["S_edit"] is None:
        for change in rendered["changes"]:
            if change["arm"] == "S":
                slot["S_edit"] = {"case_id": case["id"], **{k: change[k] for k in ("function", "pointer", "before", "after", "change_class")}}
                break
    if slot["X_cue"] is None and record["cued_tools"]:
        full = qualify_catalogue(json.loads(json.dumps(rendered["arms"]["U"])))
        row = next(item for item in full if item["cue"])
        slot["X_cue"] = {
            "case_id": case["id"],
            "target": row["function_name"],
            "rival": row["rival"]["function_name"],
            "cue": row["cue"],
            "target_action": row["evidence"]["target"]["action_text"],
            "rival_action": row["evidence"]["rival"]["action_text"],
            "axis": row["axis"],
        }
    if slot["unchanged"] is None and not record["changed"]["SX"]:
        reasons = [row["no_cue_reason"] for row in rendered["x_decisions"]]
        slot["unchanged"] = {
            "case_id": case["id"],
            "tools": [tool["function"]["name"] for tool in rendered["arms"]["U"]],
            "x_no_cue_reasons": reasons[:3],
        }


def _examples_markdown(examples: dict) -> str:
    lines = [
        "# U/S/X/SX examples across the locked scope",
        "",
        "Generated by `python -m tool_compression.clean_start package`. The first in-scope question",
        "(loader order) of each category that shows each kind of outcome. \"Not possible in this",
        "category\" means no in-scope question of that category has that outcome under the frozen rules.",
        "official_settlement: false.",
        "",
    ]
    for category, slot in examples.items():
        lines.append(f"## {category}")
        lines.append("")
        edit = slot["S_edit"]
        if edit:
            lines += [
                f"S edit, `{edit['case_id']}`, `{edit['function']}` `{edit['pointer']}` ({edit['change_class']}):",
                "",
                f"- before: {edit['before']!r}",
                f"- after: {edit['after']!r}",
                "",
            ]
        else:
            lines += ["S edit: not possible in this category.", ""]
        cue = slot["X_cue"]
        if cue:
            lines += [
                f"X cue, `{cue['case_id']}`, on `{cue['target']}` naming `{cue['rival']}` ({cue['axis']}):",
                "",
                f"- target action text: {cue['target_action']!r}",
                f"- rival action text: {cue['rival_action']!r}",
                f"- appended cue: {cue['cue']!r}",
                "",
            ]
        else:
            lines += ["X cue: not possible in this category (no rival qualifies anywhere).", ""]
        same = slot["unchanged"]
        if same:
            lines += [
                f"Unchanged by S, X, and SX: `{same['case_id']}` with tools {', '.join(f'`{name}`' for name in same['tools'][:6])}.",
                f"First X refusals: {same['x_no_cue_reasons']}",
                "",
            ]
        else:
            lines += ["Unchanged question: none; every in-scope question of this category has at least one edit.", ""]
    return "\n".join(lines) + "\n"


def _write(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
