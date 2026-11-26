"""The preliminary draw is a 20% sample under a $42 ceiling.

The allowance upper is above that ceiling. The draw is not shrunk to fit.
It does not replace the pilot or the validation draw, and it does not contact a provider.
"""

from __future__ import annotations

import json
import socket
import sys
import urllib.request
from collections import Counter
from decimal import Decimal
from hashlib import sha256

import pytest

import tool_compression.clean_start.preliminary as preliminary_module
from tool_compression.clean_start.categories import MEMORY_SCENARIOS
from tool_compression.clean_start.load import load_prereqs
from tool_compression.clean_start.pilot import build_draw, study_dir
from tool_compression.clean_start.preliminary import (
    CEILING_USD,
    COMMITTED_DRAW_SHA256,
    COMMITTED_SLOT_SHA256,
    FRACTION,
    PACE_PROFILES,
    START_HKT,
    build_preliminary_draw,
    derived_allowances,
    load_committed_cost,
    preliminary_report,
    select_preliminary_cases,
)

STUDY = study_dir()
PILOT_DRAW_SHA = "9dc5597486906feb9277d774c4752d974e6345e27218c6bb0a1664fce4c345c5"
VALIDATION_DRAW_SHA = "01ba0e9f20ae49066ef3aafeb85342abfa00726f0a43f317794e7c4d6a40e568"
DRAW_SHA = "2904904116ca21ad8830f4bb2dfaaf9cfd1773124315a8a26fe934f3490a785a"
SLOT_SHA = "a794ab88779d6ef75a0d8928d32359512b19a9aad435587e9c53b8d502421f7f"
FROZEN = (
    ("multiple", 200, 40),
    ("parallel_multiple", 200, 40),
    ("live_multiple", 1053, 211),
    ("live_parallel", 2, 2),
    ("live_parallel_multiple", 24, 5),
    ("live_irrelevance", 372, 74),
    ("live_relevance", 11, 2),
    ("multi_turn_base", 200, 40),
    ("multi_turn_miss_func", 200, 40),
    ("multi_turn_miss_param", 200, 40),
    ("multi_turn_long_context", 200, 40),
    ("memory_kv", 155, 31),
    ("memory_vector", 155, 31),
    ("memory_rec_sum", 155, 31),
)
SCENARIO_COUNTS = {
    "memory_kv": {"notetaker": 5, "finance": 5, "healthcare": 6, "student": 7, "customer": 8},
    "memory_vector": {"notetaker": 5, "finance": 6, "healthcare": 5, "student": 11, "customer": 4},
    "memory_rec_sum": {"notetaker": 7, "finance": 6, "healthcare": 5, "student": 9, "customer": 4},
}


def _draw():
    return json.loads((STUDY / "preliminary" / "draw.json").read_text(encoding="utf-8"))


def test_draw_matches_the_builder_on_python_312():
    assert sys.version_info[:2] == (3, 12)
    built = build_preliminary_draw()
    committed = _draw()
    assert committed == built
    assert committed["official_settlement"] is False
    assert committed["seed"] == "20261128"
    assert committed["fraction"] == "0.2"
    assert FRACTION == Decimal("0.2")
    assert committed["thinking"] == "off"
    assert committed["replicate_u"] is False
    assert committed["memory_pool"] == "all_in_scope"
    assert committed["ceiling_usd"] == "42"
    assert committed["budget_cny"] == "280"
    assert "pack_limit_usd" not in committed
    assert "memory_scenario" not in committed
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
    assert len(scoring) == 627
    assert len(prereqs) == 111
    assert len({row["case_id"] for row in draw["order"]}) == 738
    assert [row["run_index"] for row in draw["order"]] == list(range(738))
    assert all(not row["category"].startswith("web_search") for row in draw["order"])
    pilot = {row["case_id"] for row in build_draw()["rows"]}
    assert draw["pilot_overlap_ids"] == ["live_parallel_6-3-0", "live_parallel_7-3-1"]
    assert set(draw["pilot_overlap_ids"]) <= pilot
    assert not (set(row["case_id"] for row in scoring) - set(draw["pilot_overlap_ids"])) & pilot
    assert len(draw["validation_overlap_ids"]) == 72
    memory_at = next(i for i, row in enumerate(draw["order"]) if row["category"].startswith("memory_"))
    assert all(not row["category"].startswith("memory_") for row in draw["order"][:memory_at])
    for row in draw["draws"]:
        if row["category"].startswith("memory_"):
            assert row["scenario_pool"] == 155
            assert row["sample_pool"] == 152
            assert row["pool_rule"] == "excluding_exposed_pilot"
            assert row["scenarios"] == sorted(MEMORY_SCENARIOS)


def test_memory_draws_every_scenario_and_sends_the_full_prerequisites():
    draw = _draw()
    by_id = {case["id"]: case for case in select_preliminary_cases()}
    prereqs = [row for row in draw["order"] if row["prereq"]]
    assert {row["category"] for row in prereqs} == {"memory_kv", "memory_vector", "memory_rec_sum"}
    for category, expected_counts in SCENARIO_COUNTS.items():
        expected = [item["id"] for item in load_prereqs(category)]
        got = [row["case_id"] for row in prereqs if row["category"] == category]
        assert got == expected
        assert sum(len(by_id[case_id]["question"]) for case_id in got) == 323
        questions = [row for row in draw["order"] if row["category"] == category and not row["prereq"]]
        assert len(questions) == 31
        counts = Counter(by_id[row["case_id"]]["scenario"] for row in questions)
        assert dict(counts) == expected_counts
        assert set(counts) == set(MEMORY_SCENARIOS)
        prereq_indexes = [row["run_index"] for row in prereqs if row["category"] == category]
        question_indexes = [row["run_index"] for row in questions]
        assert max(prereq_indexes) < min(question_indexes)
    assert sum(len(by_id[row["case_id"]]["question"]) for row in prereqs) == 969


def test_allowances_match_the_archived_bills():
    derived = derived_allowances()
    assert derived["prompt"] == {
        "multi_turn_base": 6361,
        "multi_turn_miss_func": 6975,
        "multi_turn_miss_param": 7961,
        "multi_turn_long_context": 8740,
        "memory": 12269,
    }
    assert derived["steps"]["multi_turn_base"] == 6
    assert derived["steps"]["multi_turn_miss_func"] == 9
    assert derived["steps"]["multi_turn_miss_param"] == 7
    assert derived["steps"]["multi_turn_long_context"] == 7
    assert derived["steps"]["memory"] == 6
    assert derived["spike"] == 43803


def test_cost_file_matches_the_report_and_leaves_the_upper_above_the_ceiling():
    cost = load_committed_cost()
    assert cost == preliminary_report()
    assert cost["official_settlement"] is False
    assert cost["thinking"] == "off"
    assert cost["replicate_u"] is False
    assert cost["seed"] == "20261128"
    assert cost["fraction"] == "0.2"
    assert cost["budget_cny"] == "280"
    assert cost["ceiling_usd"] == "42"
    assert Decimal(cost["ceiling_cny"]["at_6.6649_cny_per_usd"]) == Decimal("279.925800")
    assert cost["cases"]["conversations"] == 738
    assert cost["cases"]["scoring"] == 627
    assert cost["cases"]["prerequisites"] == 111
    assert cost["slots"]["total"] == 2952
    assert cost["slots"]["scoring"] == 2508
    assert cost["slots"]["prerequisites"] == 444
    assert cost["start_hkt"] == "2026-11-26T18:00:00+08:00"
    upper = Decimal(cost["planning_upper_usd"])
    assert upper == Decimal("95.376500")
    assert upper > CEILING_USD
    assert "pack_limit_usd" not in cost
    assert Decimal(cost["structural_cap_usd"]) == Decimal("307.266045")
    assert Decimal(cost["observed_mean_usd"]) == Decimal("21.572285")
    assert Decimal(cost["observed_mean_sends"]) == Decimal("21892.190671")
    assert cost["allowance_requests"] == 46708
    assert cost["first_request_floor_tokens"] == 4907006
    assert Decimal(cost["first_request_floor_usd"]) == Decimal("0.736051")
    assert cost["planning_upper_parts_usd"] == {
        "single_turn": "0.965265",
        "trajectories": "93.141259",
        "long_context_spike": "0.841512",
        "memory_force_quit_contingency": "0.428463",
    }
    assert "double" in cost["peak_continuation"]
    assert "$42" in cost["peak_continuation"]
    duration = cost["duration"]
    assert duration["observed_at_1.9s"]["before_friday_peak"] is True
    assert duration["observed_at_1.9s"]["finish_hkt"].startswith("2026-11-27T05:33:15")
    assert duration["observed_at_2.0s"]["before_friday_peak"] is True
    assert duration["observed_at_2.0s"]["finish_hkt"].startswith("2026-11-27T06:09:44")
    assert duration["observed_at_3.3s"]["before_friday_peak"] is False
    assert duration["observed_memory_at_3.3s_rest_at_2.0s"]["before_friday_peak"] is False
    assert duration["observed_memory_at_3.3s_rest_at_2.0s"]["finish_hkt"].startswith("2026-11-27T10:04:36")
    assert duration["allowance_at_1.9s"]["before_friday_peak"] is False
    assert duration["allowance_at_2.0s"]["before_friday_peak"] is False
    assert duration["allowance_at_3.3s"]["before_friday_peak"] is False
    assert Decimal(cost["observed_mean_with_friday_peak_usd"]) == Decimal("25.759637")
    assert Decimal(cost["observed_mean_with_friday_peak_usd"]) <= CEILING_USD
    assert cost["observed_mean_with_friday_peak_worst_pace"] == "observed_at_3.3s"
    peaked = cost["observed_mean_with_friday_peak"]
    assert set(peaked) == set(PACE_PROFILES)
    for pace in ("observed_at_1.9s", "observed_at_2.0s"):
        assert peaked[pace]["peak_premium_usd"] == "0.000000"
        assert peaked[pace]["usd"] == cost["observed_mean_usd"]
    assert peaked["observed_at_3.3s"]["peak_premium_usd"] == "4.187352"
    assert peaked["observed_at_3.3s"]["peak_sends"] == "3346.736126"
    assert peaked["observed_memory_at_3.3s_rest_at_2.0s"]["usd"] == "23.041855"
    for pace, row in peaked.items():
        assert row["finish_hkt"] == duration[pace]["finish_hkt"]
    assert "peak window" in cost["ceiling_check"] and "$42" in cost["ceiling_check"]
    assert cost["draw_sha256"] == COMMITTED_DRAW_SHA256 == DRAW_SHA
    assert COMMITTED_SLOT_SHA256 == SLOT_SHA
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
        "--ceiling-usd", "42", "--out", str(out),
    ]) == 0
    plan = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert plan["provider_contacted"] is False
    assert plan["thinking_modes_authorized"] == ["off"]
    assert plan["ceiling_usd"] is None
    assert plan["preliminary"] is True
    assert plan["pilot"] is False
    assert plan["slots_total"] == 2952
    assert plan["prereq_slots"] == 444
    assert plan["planning_upper_usd"] == "95.376500"
    assert plan["fraction"] == "0.2"
    assert plan["slot_sha256"] == SLOT_SHA
    assert plan["status"] == "not_sent"
    assert calls == []
    assert not (out / "bills.jsonl").exists()
    assert not (out / "attempts.jsonl").exists()


def test_preliminary_refuses_a_bad_ceiling_before_the_key(tmp_path, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(
        "tool_compression.clean_start.__main__.authorized_transport",
        lambda: calls.append("transport") or (_ for _ in ()).throw(AssertionError("transport")),
    )
    monkeypatch.setattr(
        "tool_compression.clean_start.runner.read_provider_key",
        lambda: (_ for _ in ()).throw(AssertionError("key")),
    )
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    from tool_compression.clean_start.__main__ import main

    low = main([
        "run", "--preliminary", "--live", "--authorize-live", "--thinking", "off",
        "--memory-prereqs", "matched", "--ceiling-usd", "27", "--out", str(tmp_path / "low"),
    ])
    assert low == 2
    assert "authorized" in capsys.readouterr().err
    high = main([
        "run", "--preliminary", "--live", "--authorize-live", "--thinking", "off",
        "--memory-prereqs", "matched", "--ceiling-usd", "42.01", "--out", str(tmp_path / "high"),
    ])
    assert high == 2
    assert "280 CNY" in capsys.readouterr().err
    authorized = main([
        "run", "--preliminary", "--live", "--authorize-live", "--thinking", "off",
        "--memory-prereqs", "matched", "--ceiling-usd", "42", "--out", str(tmp_path / "authorized"),
    ])
    assert authorized == 2
    err = capsys.readouterr().err
    assert "planning upper" not in err
    assert "280 CNY" not in err
    assert "refusing before any request" in err
    assert calls == []
    assert not (tmp_path / "low").exists()
    assert not (tmp_path / "high").exists()
    assert not (tmp_path / "authorized").exists()


@pytest.mark.parametrize("argv", [
    ["run", "--preliminary", "--thinking", "on", "--memory-prereqs", "matched", "--ceiling-usd", "42", "--out"],
    ["run", "--preliminary", "--thinking", "off,on", "--memory-prereqs", "matched", "--ceiling-usd", "42", "--out"],
    ["run", "--preliminary", "--memory-prereqs", "matched", "--ceiling-usd", "42", "--out"],
    ["run", "--preliminary", "--thinking", "off", "--memory-prereqs", "none", "--ceiling-usd", "42", "--out"],
    ["run", "--preliminary", "--thinking", "off", "--memory-prereqs", "matched", "--out"],
    ["run", "--preliminary", "--pilot", "--thinking", "off", "--memory-prereqs", "matched", "--ceiling-usd", "42", "--out"],
    ["run", "--preliminary", "--validation", "--thinking", "off", "--memory-prereqs", "matched", "--ceiling-usd", "42", "--out"],
    ["run", "--memory-prereqs", "matched", "--out"],
])
def test_preliminary_rejects_other_modes(tmp_path, argv):
    from tool_compression.clean_start.__main__ import main

    assert main(argv + [str(tmp_path)]) == 2
    assert not (tmp_path / "run.json").exists()


def test_peak_windows_follow_the_rate_card():
    from datetime import timedelta

    from tool_compression.clean_start.preliminary import _peak_windows
    from tool_compression.clean_start.rate_card import is_peak

    windows = _peak_windows()
    assert windows[:2] == [(Decimal(15 * 3600), Decimal(18 * 3600)), (Decimal(20 * 3600), Decimal(24 * 3600))]
    for begin, end in windows:
        assert is_peak(START_HKT + timedelta(seconds=int(begin)))
        assert is_peak(START_HKT + timedelta(seconds=int(end) - 1))
        assert not is_peak(START_HKT + timedelta(seconds=int(end)))
    assert is_peak(START_HKT - timedelta(seconds=1))
    assert not is_peak(START_HKT)


def test_committed_cost_and_cli_refuse_a_peak_path_over_the_ceiling(tmp_path, monkeypatch, capsys):
    root = tmp_path / "study"
    (root / "preliminary").mkdir(parents=True)
    (root / "preliminary" / "draw.json").write_bytes((STUDY / "preliminary" / "draw.json").read_bytes())
    cost = json.loads((STUDY / "preliminary" / "cost.json").read_text(encoding="utf-8"))
    cost["observed_mean_with_friday_peak_usd"] = "42.000001"
    (root / "preliminary" / "cost.json").write_text(json.dumps(cost), encoding="utf-8")
    monkeypatch.setattr(preliminary_module, "study_dir", lambda: root)
    with pytest.raises(RuntimeError, match="Friday peak"):
        load_committed_cost()
    monkeypatch.undo()

    real = load_committed_cost()
    monkeypatch.setattr(preliminary_module, "load_committed_cost", lambda: {**real, "observed_mean_with_friday_peak_usd": "42.5"})
    monkeypatch.setattr(
        "tool_compression.clean_start.__main__.authorized_transport",
        lambda: (_ for _ in ()).throw(AssertionError("transport")),
    )
    from tool_compression.clean_start.__main__ import main

    code = main([
        "run", "--preliminary", "--live", "--authorize-live", "--thinking", "off",
        "--memory-prereqs", "matched", "--ceiling-usd", "42", "--out", str(tmp_path / "out"),
    ])
    assert code == 2
    assert "Friday peak $42.5 exceeds ceiling $42" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_the_builder_refuses_when_the_peak_path_would_not_fit(monkeypatch):
    monkeypatch.setattr(preliminary_module, "CEILING_USD", Decimal("25"))
    with pytest.raises(RuntimeError, match="Friday peak"):
        preliminary_report()


def _prior_preliminary_run(out):
    from datetime import datetime, timezone

    from tool_compression.clean_start.__main__ import run_identity
    from tool_compression.clean_start.runner import ProviderHTTPError, build_slots, execute

    noon = datetime(2026, 11, 26, 10, 30, tzinfo=timezone.utc)
    text = {"choices": [{"message": {"role": "assistant", "content": "done"}}],
            "usage": {"prompt_tokens": 100, "prompt_cache_miss_tokens": 100, "prompt_cache_hit_tokens": 0, "completion_tokens": 5}}
    script = [text, text, text, ProviderHTTPError(500, "busy")]
    sent = []

    def transport(body):
        sent.append(body)
        item = script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    cases = select_preliminary_cases()
    cost = load_committed_cost()
    identity = run_identity(cases, pilot=False, memory_prereqs="matched", preliminary=True, cost=cost)
    result = execute(
        cases, build_slots(cases, ("off",)), out, transport, ceiling_usd=CEILING_USD,
        thinking_modes=("off",), clock=lambda: noon, identity=identity,
    )
    assert result["slots_sent"] == 3 and len(sent) == 4
    return result


def test_preliminary_resume_check_reports_without_writing_and_live_resume_refuses_before_the_key(
    tmp_path, monkeypatch, capsys,
):
    calls = []
    monkeypatch.setattr(
        "tool_compression.clean_start.__main__.authorized_transport",
        lambda: calls.append("transport") or (_ for _ in ()).throw(AssertionError("transport")),
    )
    monkeypatch.setattr(
        "tool_compression.clean_start.runner.read_provider_key",
        lambda: (_ for _ in ()).throw(AssertionError("key")),
    )
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    from tool_compression.clean_start.__main__ import main

    out = tmp_path / "flight"
    prior = _prior_preliminary_run(out)
    snapshot = {path: path.read_bytes() for path in out.rglob("*") if path.is_file()}
    base = ["run", "--preliminary", "--thinking", "off", "--memory-prereqs", "matched", "--ceiling-usd", "42"]

    capsys.readouterr()
    assert main(base + ["--resume", "--out", str(out)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["resume_check"] is True and report["provider_contacted"] is False
    assert report["finished_slots"] == 3 and report["slots_total"] == 2952
    assert report["next_slot"]["index"] == 3
    assert report["session"] == 2
    assert report["prior_spend_usd"] == prior["running_usd"]
    assert [row["attempt"] for row in report["unbilled_attempts"]] == [4]
    assert {path: path.read_bytes() for path in out.rglob("*") if path.is_file()} == snapshot

    assert main(base[:1] + ["--preliminary", "--live", "--authorize-live"] + base[2:] + ["--resume", "--out", str(out)]) == 2
    assert "refusing before any request" in capsys.readouterr().err
    assert main(base[:1] + ["--preliminary", "--live", "--authorize-live"] + base[2:] + ["--out", str(out)]) == 2
    assert "--resume to continue that run" in capsys.readouterr().err
    assert main(["run", "--resume", "--out", str(out)]) == 2
    assert "--preliminary or --full only" in capsys.readouterr().err
    assert {path: path.read_bytes() for path in out.rglob("*") if path.is_file()} == snapshot
    assert calls == []

    run = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert run["identity"]["draw_sha256"] == DRAW_SHA
    assert run["slot_sha256"] == SLOT_SHA
    run["identity"]["draw_sha256"] = "0" * 64
    (out / "run.json").write_text(json.dumps(run), encoding="utf-8")
    assert main(base + ["--resume", "--out", str(out)]) == 2
    assert "refusing to resume: resume_draw_mismatch" in capsys.readouterr().err
    assert main(base + ["--resume", "--out", str(tmp_path / "nothing")]) == 2
    assert "resume_without_prior_run" in capsys.readouterr().err
