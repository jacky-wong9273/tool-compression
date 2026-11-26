"""The preliminary draw is a proportional sample inside the $12 ceiling.

It does not replace the pilot or the validation draw, and it does not contact a provider.
"""

from __future__ import annotations

import json
import socket
import sys
import urllib.request
from decimal import Decimal
from hashlib import sha256

import pytest

import tool_compression.clean_start.preliminary as preliminary_module
from tool_compression.clean_start.load import load_prereqs
from tool_compression.clean_start.pilot import build_draw, study_dir
from tool_compression.clean_start.preliminary import (
    CEILING_USD,
    FRACTION,
    FRACTION_QUANTUM,
    PACK_LIMIT_USD,
    PROMPT_ALLOWANCE,
    STEP_ALLOWANCE,
    build_preliminary_draw,
    derived_allowances,
    load_committed_cost,
    preliminary_report,
    select_preliminary_cases,
    upper_for_fraction,
)

STUDY = study_dir()
PILOT_DRAW_SHA = "9dc5597486906feb9277d774c4752d974e6345e27218c6bb0a1664fce4c345c5"
VALIDATION_DRAW_SHA = "01ba0e9f20ae49066ef3aafeb85342abfa00726f0a43f317794e7c4d6a40e568"
DRAW_SHA = "a82dea0cfaa00c015620c3dd0a29f65a100671d7c3e5e8abf9b3151be69ad0ca"
FROZEN = (
    ("multiple", 200, 7),
    ("parallel_multiple", 200, 7),
    ("live_multiple", 1053, 39),
    ("live_parallel", 2, 2),
    ("live_parallel_multiple", 24, 2),
    ("live_irrelevance", 372, 14),
    ("live_relevance", 11, 2),
    ("multi_turn_base", 200, 7),
    ("multi_turn_miss_func", 200, 7),
    ("multi_turn_miss_param", 200, 7),
    ("multi_turn_long_context", 200, 7),
    ("memory_kv", 155, 6),
    ("memory_vector", 155, 6),
    ("memory_rec_sum", 155, 6),
)


def _draw():
    return json.loads((STUDY / "preliminary" / "draw.json").read_text(encoding="utf-8"))


def test_draw_matches_the_builder_on_python_312():
    assert sys.version_info[:2] == (3, 12)
    built = build_preliminary_draw()
    committed = _draw()
    assert committed == built
    assert committed["official_settlement"] is False
    assert committed["seed"] == "20261127"
    assert committed["fraction"] == "0.0374"
    assert committed["thinking"] == "off"
    assert committed["replicate_u"] is False
    assert committed["memory_scenario"] == "notetaker"
    assert committed["ceiling_usd"] == "12"
    raw = (STUDY / "preliminary" / "draw.json").read_bytes()
    assert sha256(raw).hexdigest() == DRAW_SHA
    assert sha256((STUDY / "pilot" / "draw.json").read_bytes()).hexdigest() == PILOT_DRAW_SHA
    assert sha256((STUDY / "validation" / "draw.json").read_bytes()).hexdigest() == VALIDATION_DRAW_SHA


def test_sample_is_proportional_and_keeps_every_category():
    draw = _draw()
    assert [
        (row["category"], row["population"], row["frozen"]) for row in draw["draws"]
    ] == list(FROZEN)
    scoring = [row for row in draw["order"] if not row["prereq"]]
    prereqs = [row for row in draw["order"] if row["prereq"]]
    assert len(scoring) == 119
    assert len(prereqs) == 15
    assert len({row["case_id"] for row in draw["order"]}) == 134
    assert [row["run_index"] for row in draw["order"]] == list(range(134))
    assert all(not row["category"].startswith("web_search") for row in draw["order"])
    pilot = {row["case_id"] for row in build_draw()["rows"]}
    assert draw["pilot_overlap_ids"] == ["live_parallel_6-3-0", "live_parallel_7-3-1"]
    assert set(draw["pilot_overlap_ids"]) <= pilot
    assert not (set(row["case_id"] for row in scoring) - set(draw["pilot_overlap_ids"])) & pilot
    memory_at = next(i for i, row in enumerate(draw["order"]) if row["category"].startswith("memory_"))
    assert all(not row["category"].startswith("memory_") for row in draw["order"][:memory_at])


def test_memory_is_notetaker_prerequisites_before_questions():
    draw = _draw()
    by_id = {case["id"]: case for case in select_preliminary_cases()}
    prereqs = [row for row in draw["order"] if row["prereq"]]
    assert {row["category"] for row in prereqs} == {"memory_kv", "memory_vector", "memory_rec_sum"}
    for category in ("memory_kv", "memory_vector", "memory_rec_sum"):
        expected = [item["id"] for item in load_prereqs(category) if item["scenario"] == "notetaker"]
        got = [row["case_id"] for row in prereqs if row["category"] == category]
        assert got == expected
        assert sum(len(by_id[case_id]["question"]) for case_id in got) == 24
        questions = [row for row in draw["order"] if row["category"] == category and not row["prereq"]]
        assert len(questions) == 6
        assert all(by_id[row["case_id"]]["scenario"] == "notetaker" for row in questions)
        prereq_indexes = [row["run_index"] for row in prereqs if row["category"] == category]
        question_indexes = [row["run_index"] for row in questions]
        assert max(prereq_indexes) < min(question_indexes)


def test_allowances_match_the_archived_bills():
    derived = derived_allowances()
    assert derived["prompt"] == PROMPT_ALLOWANCE
    assert derived["steps"] == STEP_ALLOWANCE
    assert derived["spike"] == 43803
    # The base family's higher 90th percentile is 5, so 6 is the floor, not the percentile.
    assert PROMPT_ALLOWANCE == {
        "multi_turn_base": 6361,
        "multi_turn_miss_func": 6975,
        "multi_turn_miss_param": 7961,
        "multi_turn_long_context": 8740,
        "memory": 12269,
    }
    assert STEP_ALLOWANCE["multi_turn_base"] == 6
    assert STEP_ALLOWANCE["multi_turn_miss_func"] == 9
    assert STEP_ALLOWANCE["multi_turn_long_context"] == 7


def test_cost_file_matches_the_report_and_stays_under_the_ceiling():
    cost = load_committed_cost()
    assert cost == preliminary_report()
    assert cost["official_settlement"] is False
    assert cost["thinking"] == "off"
    assert cost["replicate_u"] is False
    assert cost["cases"]["conversations"] == 134
    assert cost["cases"]["scoring"] == 119
    assert cost["cases"]["prerequisites"] == 15
    assert cost["slots"]["total"] == 536
    assert cost["slots"]["prerequisites"] == 60
    upper = Decimal(cost["planning_upper_usd"])
    assert upper == Decimal("11.489930")
    assert upper <= PACK_LIMIT_USD < CEILING_USD
    assert Decimal(cost["structural_cap_usd"]) > CEILING_USD
    assert Decimal(cost["observed_mean_usd"]) == Decimal("2.527326")
    assert cost["allowance_requests"] == 6012
    assert all(row["before_friday_peak"] for row in cost["duration"].values())
    nxt = upper_for_fraction(FRACTION + FRACTION_QUANTUM)
    assert nxt > CEILING_USD
    source = preliminary_module.__file__
    text = open(source, encoding="utf-8").read()
    assert "possible_answer" not in text
    assert "ground_truth" not in text


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
        "run", "--preliminary", "--thinking", "off", "--memory-prereqs", "matched",
        "--ceiling-usd", "12", "--out", str(out),
    ]) == 0
    plan = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert plan["provider_contacted"] is False
    assert plan["thinking_modes_authorized"] == ["off"]
    assert plan["ceiling_usd"] is None
    assert plan["preliminary"] is True
    assert plan["pilot"] is False
    assert plan["slots_total"] == 536
    assert plan["prereq_slots"] == 60
    assert plan["planning_upper_usd"] == "11.489930"
    assert plan["fraction"] == "0.0374"
    assert plan["status"] == "not_sent"
    assert calls == []
    assert not (out / "bills.jsonl").exists()
    assert not (out / "attempts.jsonl").exists()


def test_preliminary_refuses_a_bad_ceiling_before_the_key(tmp_path, monkeypatch, capsys):
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

    low = main([
        "run", "--preliminary", "--live", "--authorize-live", "--thinking", "off",
        "--memory-prereqs", "matched", "--ceiling-usd", "11", "--out", str(tmp_path / "low"),
    ])
    assert low == 2
    assert "planning upper" in capsys.readouterr().err
    high = main([
        "run", "--preliminary", "--live", "--authorize-live", "--thinking", "off",
        "--memory-prereqs", "matched", "--ceiling-usd", "13", "--out", str(tmp_path / "high"),
    ])
    assert high == 2
    assert "80 CNY" in capsys.readouterr().err
    assert not (tmp_path / "low").exists()
    assert not (tmp_path / "high").exists()


@pytest.mark.parametrize("argv", [
    ["run", "--preliminary", "--thinking", "on", "--memory-prereqs", "matched", "--ceiling-usd", "12", "--out"],
    ["run", "--preliminary", "--thinking", "off,on", "--memory-prereqs", "matched", "--ceiling-usd", "12", "--out"],
    ["run", "--preliminary", "--memory-prereqs", "matched", "--ceiling-usd", "12", "--out"],
    ["run", "--preliminary", "--thinking", "off", "--memory-prereqs", "none", "--ceiling-usd", "12", "--out"],
    ["run", "--preliminary", "--thinking", "off", "--memory-prereqs", "matched", "--out"],
    ["run", "--preliminary", "--pilot", "--thinking", "off", "--memory-prereqs", "matched", "--ceiling-usd", "12", "--out"],
    ["run", "--preliminary", "--validation", "--thinking", "off", "--memory-prereqs", "matched", "--ceiling-usd", "12", "--out"],
    ["run", "--memory-prereqs", "matched", "--out"],
])
def test_preliminary_rejects_other_modes(tmp_path, argv):
    from tool_compression.clean_start.__main__ import main

    assert main(argv + [str(tmp_path)]) == 2
    assert not (tmp_path / "run.json").exists()
