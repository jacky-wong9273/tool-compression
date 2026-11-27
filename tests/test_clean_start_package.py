"""Offline review package, pilot report, evidence immutability, editor isolation."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import os
import subprocess

import pytest

from tool_compression.clean_start.editor_x import qualify_catalogue
from tool_compression.clean_start.package import build_package
from tool_compression.clean_start.pilot import study_dir
from tool_compression.clean_start.prepare import JAVA_HINT, JAVASCRIPT_HINT, PYTHON_HINT
from tool_compression.clean_start.report import (
    PILOT_EVIDENCE,
    PILOT_TIP,
    SENT_DIGEST,
    sent_digest_from_git,
    write_pilot_report,
)

REPO = Path(__file__).resolve().parents[1]
PACKAGE = study_dir() / "package"
EVIDENCE = study_dir() / PILOT_EVIDENCE


def _tool(name: str, description: str, required=None, properties=None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties or {"value": {"type": "string", "description": "A value."}},
                "required": required if required is not None else ["value"],
            },
        },
    }


def test_archived_pilot_evidence_is_byte_identical_to_its_checksums():
    lines = (EVIDENCE / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 170
    for line in lines:
        digest, relative = line.split("  ", 1)
        path = EVIDENCE / "original" / relative
        assert sha256(path.read_bytes()).hexdigest() == digest, relative
    listed = {line.split("  ", 1)[1].lstrip("./") for line in lines}
    present = {str(path.relative_to(EVIDENCE / "original")) for path in (EVIDENCE / "original").rglob("*") if path.is_file()}
    assert present == listed


def test_package_regenerates_byte_identical(tmp_path):
    summary = build_package(tmp_path)
    assert summary["questions"] == 3127
    assert summary["integrity_failures"] == 0
    for name in (
        "token_tables.json", "integrity.json", "s_ledger.jsonl", "x_ledger.jsonl",
        "s_keep_reasons.json", "examples.json", "EXAMPLES.md", "pilot_2026_11_25_analysis.json",
        "pilot_2026_11_25_revised_analysis.json", "revision_vs_c47b186c.json",
        "validation_20261126.json", "validation_2026_11_25_analysis.json", "revision_vs_0bf829c6.json",
        "preliminary_20261128.json",
    ):
        assert (tmp_path / name).read_bytes() == (PACKAGE / name).read_bytes(), name
    committed = json.loads((PACKAGE / "manifest.json").read_text(encoding="utf-8"))
    for name, digest in committed["files"].items():
        assert sha256((PACKAGE / name).read_bytes()).hexdigest() == digest, name
    integrity = json.loads((PACKAGE / "integrity.json").read_text(encoding="utf-8"))
    assert integrity["failures"] == []
    assert set(integrity["passed_per_check"].values()) == {3127}
    tables = json.loads((PACKAGE / "token_tables.json").read_text(encoding="utf-8"))
    assert tables["official_settlement"] is False
    overall = tables["all_in_scope"]
    assert overall["deltas"]["X-U"]["field_tokens"] == overall["cue_tokens"] > 0
    assert tables["by_category"]["live_parallel"]["deltas"]["S-U"]["field_tokens"] < 0
    assert tables["by_category"]["live_parallel"]["deltas"]["X-U"]["field_tokens"] == 0
    for row in tables["by_category"].values():
        assert row["deltas"]["X-U"]["tools_tokens"] >= 0
        assert row["deltas"]["S-U"]["tools_tokens"] < 0
    draws = tables["draws"]
    assert {name: row["questions"] for name, row in draws.items()} == {
        "pilot_draw": 41, "validation_draw": 313, "outside_both_draws": 2773,
    }
    assert "exposed" in tables["exposure"]
    for row in [overall, *draws.values()]:
        coverage = row["coverage"]
        assert coverage["s_fields"]["fields"] == coverage["s_fields"]["edited"] + sum(
            count for key, count in coverage["s_fields"].items() if key.startswith("kept:")
        )
        assert coverage["x_tools"]["tools"] == coverage["x_tools"]["cued"] + sum(
            count for key, count in coverage["x_tools"].items() if key.startswith("uncued:")
        )
        assert coverage["questions_without_x_cue"] <= row["questions"]
        anatomy = row["u_anatomy"]
        assert sum(anatomy[name]["tokens"] for name in (
            "outside_descriptions", "function_descriptions", "parameter_descriptions",
        )) == row["tools_tokens"]["U"]
        assert anatomy["repeated_language_hints"]["tokens"] <= anatomy["language_hints"]["tokens"]
        assert anatomy["repeated_suite_preambles"]["tokens"] <= anatomy["suite_preambles"]["tokens"]
        assert anatomy["language_hints"]["tokens"] <= anatomy["function_descriptions"]["tokens"]


def test_s_ledger_rows_keep_their_facts_and_never_touch_names():
    rows = [json.loads(line) for line in (PACKAGE / "s_ledger.jsonl").read_text(encoding="utf-8").splitlines()]
    assert rows
    dropped_hints = 0
    for row in rows:
        assert row["before"] != row["after"]
        assert row["pointer"].endswith("/description")
        for fact in row["facts"]:
            start, end = fact["span"]
            assert row["before"][start:end] == fact["excerpt"]
            if fact.get("decision") == "KEEP":
                assert fact["after"] in row["after"]
        for hint in (PYTHON_HINT, JAVA_HINT, JAVASCRIPT_HINT):
            if hint in row["before"] and hint not in row["after"]:
                dropped_hints += 1
                carried = [fact for fact in row["facts"] if fact["decision"] == "HINT_CONTEXT"]
                assert [fact["excerpt"] for fact in carried] == [hint]
                assert carried[0]["carried_excerpt"] == hint
                assert 0 <= carried[0]["carried_by_tool_index"] < row["tool_index"]
            elif hint in row["before"]:
                assert row["after"].endswith(hint)
    assert dropped_hints > 0


def test_x_ledger_cues_name_one_rival_with_evidence_on_both_sides():
    rows = [json.loads(line) for line in (PACKAGE / "x_ledger.jsonl").read_text(encoding="utf-8").splitlines()]
    assert rows
    for row in rows:
        names = set(row["tools"])
        for cue in row["cues"]:
            assert cue["rival"] in names and cue["target"] in names and cue["rival"] != cue["target"]
            assert cue["cue"].startswith("For ") and cue["cue"].endswith(f", use {cue['rival']}.")
            assert cue["evidence"]["target"]["action_text"] and cue["evidence"]["rival"]["action_text"]
            for banned in ("only", "cannot", "can't", "exclusively", "unable"):
                assert banned not in cue["cue"].lower().split()


def test_x_drops_cues_the_rival_name_already_spells():
    named = [
        _tool("setFrontLights", "Sets the front lights of the vehicle."),
        _tool("setRearLights", "Sets the rear lights of the vehicle."),
    ]
    assert [row["cue"] for row in qualify_catalogue(named)] == ["", ""]
    assert "already spells" in qualify_catalogue(named)[0]["no_cue_reason"]
    opaque = [
        _tool("tool_a", "Sets the front lights of the vehicle."),
        _tool("tool_b", "Sets the rear lights of the vehicle."),
    ]
    assert [row["cue"] for row in qualify_catalogue(opaque)] == [
        "For the rear lights, use tool_b.",
        "For the front lights, use tool_a.",
    ]


def test_x_refuses_pairs_whose_actions_take_different_objects():
    different = [
        _tool("tool_a", "Sets the headlights of the vehicle."),
        _tool("tool_b", "Sets the cruise control of the vehicle."),
    ]
    rows = qualify_catalogue(different)
    assert [row["cue"] for row in rows] == ["", ""]
    assert "different objects (headlight versus control)" in rows[0]["no_cue_reason"]


def test_editor_modules_have_no_question_or_gold_inputs():
    for name in ("editor_s.py", "editor_x.py", "descriptions.py", "render.py"):
        text = (REPO / "src/tool_compression/clean_start" / name).read_text(encoding="utf-8")
        for forbidden in ("possible_answer", "ground_truth", "load_questions", "in_scope_questions", "bills.jsonl", "score/"):
            assert forbidden not in text, (name, forbidden)
        assert "import tool_compression.clean_start.load" not in text
        assert "from tool_compression.clean_start.load" not in text


def test_pilot_report_regenerates_from_the_archived_evidence(tmp_path):
    out = tmp_path / "analysis.json"
    summary = write_pilot_report(EVIDENCE, out)
    assert out.read_bytes() == (PACKAGE / "pilot_2026_11_25_analysis.json").read_bytes()
    assert summary == {
        "single_turn_cases_sent": 20,
        "trajectory_cases": 27,
        "paired_identical_S_U": 17,
        "paired_identical_X_U": 20,
    }
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["official_settlement"] is False
    assert report["source"]["bills"] == 151
    archived = report["accuracy"]["archived_official_scores"]
    rescored = report["accuracy"]["rescored_official_scores"]
    assert sum(archived[c]["U"]["correct"] for c in archived) == 14
    assert sum(rescored[c]["U"]["correct"] for c in rescored) == 20
    paired = report["single_turn"]["paired"]
    assert paired["X-U"]["provider_prompt_delta_all"]["sum"] == 0
    assert paired["S-U"]["provider_prompt_delta_where_tools_identical"]["sum"] == 0


def _commit_available(commit: str) -> bool:
    try:
        subprocess.run(["git", "-C", str(REPO), "cat-file", "-e", f"{commit}^{{commit}}"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    return True


@pytest.mark.skipif(not _commit_available(PILOT_TIP), reason="pilot tip not in local history (shallow checkout)")
def test_sent_render_digest_matches_the_pilot_tip():
    committed = json.loads((EVIDENCE / SENT_DIGEST).read_text(encoding="utf-8"))
    assert sent_digest_from_git(PILOT_TIP) == committed


@pytest.mark.skipif(not os.environ.get("CLEAN_START_BFCL_ROOT"), reason="CLEAN_START_BFCL_ROOT not set")
def test_official_rescoring_reproduces_the_committed_scores(tmp_path):
    import shutil

    from tool_compression.clean_start.evaluate import run_official_evaluation

    shutil.copytree(EVIDENCE / "original/artifacts/result", tmp_path / "result")
    summary = run_official_evaluation(tmp_path, Path(os.environ["CLEAN_START_BFCL_ROOT"]), ("off",))
    assert summary["ok"] is True
    committed = EVIDENCE / "rescored-underscore-to-dot/score"
    for path in committed.rglob("*"):
        if path.is_file():
            assert (tmp_path / "score" / path.relative_to(committed)).read_bytes() == path.read_bytes()
