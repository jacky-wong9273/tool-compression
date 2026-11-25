"""The fresh validation draw stays disjoint from the exposed pilot and inside the cap."""

from __future__ import annotations

import json
import socket
import sys
import urllib.request
from decimal import Decimal
from hashlib import sha256

import pytest

import tool_compression.clean_start.validation as validation_module
from tool_compression.clean_start.evaluate import result_categories
from tool_compression.clean_start.load import load_prereqs
from tool_compression.clean_start.pilot import build_draw, study_dir
from tool_compression.clean_start.validation import (
    CEILING_USD,
    MEMORY_SCENARIO,
    UPPER_LIMIT_USD,
    build_validation_draw,
    load_committed_cost,
    select_validation_cases,
)

STUDY = study_dir()
WEB_IDS = (
    "web_search_base_37",
    "web_search_base_46",
    "web_search_base_58",
    "web_search_no_snippet_83",
    "web_search_no_snippet_92",
    "web_search_no_snippet_58",
)


def _draw():
    return json.loads((STUDY / "validation" / "draw.json").read_text(encoding="utf-8"))


def test_draw_matches_the_builder_on_python_312():
    assert sys.version_info[:2] == (3, 12)
    built = build_validation_draw()
    committed = _draw()
    assert committed == built
    assert committed["official_settlement"] is False
    assert committed["seed"] == "20261126"
    assert committed["thinking"] == "off"
    assert committed["replicate_u"] is False
    assert committed["memory_scenario"] == MEMORY_SCENARIO
    raw = (STUDY / "validation" / "draw.json").read_bytes()
    assert sha256(raw).hexdigest() == "01ba0e9f20ae49066ef3aafeb85342abfa00726f0a43f317794e7c4d6a40e568"


def test_draw_excludes_the_exposed_pilot_and_the_web_ids():
    draw = _draw()
    ids = [row["case_id"] for row in draw["order"]]
    assert len(ids) == len(set(ids)) == 328
    pilot = {row["case_id"] for row in build_draw()["rows"]}
    assert len(pilot) == 41
    assert not (set(ids) & pilot)
    assert not (set(ids) & set(WEB_IDS))
    assert all(not row["category"].startswith("web_search") for row in draw["order"])
    assert all(row["category"] != "live_parallel" for row in draw["order"])
    assert draw["omitted_categories"] == [
        {"category": "live_parallel", "reason": "every in-scope id is in the exposed pilot draw"},
    ]


def test_memory_is_notetaker_prerequisites_before_questions():
    draw = _draw()
    scoring = [row for row in draw["order"] if not row["prereq"]]
    prereqs = [row for row in draw["order"] if row["prereq"]]
    assert len(scoring) == 313
    assert len(prereqs) == 15
    assert {row["category"] for row in prereqs} == {"memory_kv", "memory_vector", "memory_rec_sum"}
    by_id = {case["id"]: case for case in select_validation_cases()}
    for category in ("memory_kv", "memory_vector", "memory_rec_sum"):
        expected = [item["id"] for item in load_prereqs(category) if item["scenario"] == "notetaker"]
        got = [row["case_id"] for row in prereqs if row["category"] == category]
        assert got == expected
        questions = [row for row in scoring if row["category"] == category]
        assert len(questions) == 4
        assert all(by_id[row["case_id"]]["scenario"] == "notetaker" for row in questions)
    memory_at = next(i for i, row in enumerate(draw["order"]) if row["category"].startswith("memory_"))
    assert all(not row["category"].startswith("memory_") for row in draw["order"][:memory_at])
    for category in ("memory_kv", "memory_vector", "memory_rec_sum"):
        indexes = [row["run_index"] for row in draw["order"] if row["category"] == category]
        prereq_indexes = [row["run_index"] for row in draw["order"] if row["category"] == category and row["prereq"]]
        question_indexes = [row["run_index"] for row in draw["order"] if row["category"] == category and not row["prereq"]]
        assert max(prereq_indexes) < min(question_indexes)
        assert indexes == list(range(min(indexes), max(indexes) + 1))


def test_cost_file_matches_the_draw_and_stays_under_the_ceiling():
    cost = load_committed_cost()
    assert cost["official_settlement"] is False
    assert cost["replicate_u"] is False
    assert cost["thinking"] == "off"
    assert cost["cases"]["conversations"] == 328
    assert cost["cases"]["scoring"] == 313
    assert cost["cases"]["prerequisites"] == 15
    assert cost["slots"]["total"] == 1312
    assert cost["slots"]["prerequisites"] == 60
    assert cost["first_request_floor_usd"] == "0.339265"
    assert cost["first_request_floor_tokens"] == 1130882
    upper = Decimal(cost["planning_upper_usd"])
    assert upper == Decimal("16.205873")
    assert upper <= UPPER_LIMIT_USD < CEILING_USD
    assert Decimal(cost["structural_cap_usd"]) > CEILING_USD
    assert Decimal(cost["planning_upper_parts_usd"]["single_turn"]) < Decimal("1")
    source = validation_module.__file__
    text = open(source, encoding="utf-8").read()
    assert "possible_answer" not in text
    assert "evidence/" not in text


def test_dry_plan_reports_the_flight_without_a_provider(tmp_path, monkeypatch):
    calls = []

    def refuse(*_args, **_kwargs):
        calls.append("network")
        raise AssertionError("network")

    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    monkeypatch.setattr(
        "tool_compression.clean_start.__main__.authorized_transport",
        lambda: calls.append("transport") or (_ for _ in ()).throw(AssertionError("transport")),
    )
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    from tool_compression.clean_start.__main__ import main

    out = tmp_path / "plan"
    assert main([
        "run", "--validation", "--thinking", "off", "--memory-prereqs", "matched",
        "--ceiling-usd", "20", "--out", str(out),
    ]) == 0
    plan = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert plan["provider_contacted"] is False
    assert plan["thinking_modes_authorized"] == ["off"]
    assert plan["ceiling_usd"] == "20"
    assert plan["slots_total"] == 1312
    assert plan["prereq_slots"] == 60
    assert plan["validation"] is True
    assert plan["replicate_u"] is False
    assert plan["planning_upper_usd"] == "16.205873"
    assert plan["status"] == "not_sent"
    assert calls == []
    assert not (out / "bills.jsonl").exists()
    assert not (out / "attempts.jsonl").exists()


def test_validation_refuses_a_ceiling_under_the_upper_before_the_key(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        "tool_compression.clean_start.__main__.authorized_transport",
        lambda: (_ for _ in ()).throw(AssertionError("transport")),
    )
    monkeypatch.setattr(
        "tool_compression.clean_start.runner.read_provider_key",
        lambda: (_ for _ in ()).throw(AssertionError("key")),
    )
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    from tool_compression.clean_start.__main__ import main

    code = main([
        "run", "--validation", "--live", "--authorize-live", "--thinking", "off",
        "--memory-prereqs", "matched", "--ceiling-usd", "1", "--out", str(tmp_path),
    ])
    assert code == 2
    assert "planning upper" in capsys.readouterr().err
    assert not (tmp_path / "run.json").exists()


@pytest.mark.parametrize("argv", [
    ["run", "--validation", "--thinking", "on", "--memory-prereqs", "matched", "--ceiling-usd", "20", "--out"],
    ["run", "--validation", "--thinking", "off,on", "--memory-prereqs", "matched", "--ceiling-usd", "20", "--out"],
    ["run", "--validation", "--memory-prereqs", "matched", "--ceiling-usd", "20", "--out"],
    ["run", "--validation", "--thinking", "off", "--memory-prereqs", "none", "--ceiling-usd", "20", "--out"],
    ["run", "--validation", "--thinking", "off", "--memory-prereqs", "matched", "--out"],
    ["run", "--validation", "--pilot", "--thinking", "off", "--memory-prereqs", "matched", "--ceiling-usd", "20", "--out"],
])
def test_validation_rejects_other_modes(tmp_path, argv):
    from tool_compression.clean_start.__main__ import main

    assert main(argv + [str(tmp_path)]) == 2
    assert not (tmp_path / "run.json").exists()


def test_prerequisite_result_files_are_not_scored(tmp_path):
    model = "deepseek-flash-thinking-off-U"
    root = tmp_path / model / "agentic" / "memory" / "kv"
    root.mkdir(parents=True)
    (root / "BFCL_v4_memory_kv_prereq_result.json").write_text("[]", encoding="utf-8")
    (root / "BFCL_v4_memory_kv_result.json").write_text("[]", encoding="utf-8")
    assert result_categories(tmp_path, model) == ["memory_kv"]
