"""Continue a stopped full fly from a new source_sha256, in a new directory.

No test reads a provider key or opens a socket. The prior directory is
fingerprinted and must stay byte-for-byte unchanged.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import json
import os
import shutil

import pytest

from tool_compression.clean_start.categories import result_group
from tool_compression.clean_start.rate_card import spend_usd
from tool_compression.clean_start.resume import inspect_resume, source_sha256, stage_continue_from
from tool_compression.clean_start.runner import (
    FULL_FLY_POLICY,
    ProviderHTTPError,
    RunStopped,
    build_slots,
    execute,
)

NOON = datetime(2026, 11, 28, 4, 0, tzinfo=timezone.utc)
# Stand-in hashes for a stopped run and a different tree. The CLI test checks
# the real source_sha256() of this checkout.
OLD_SOURCE = "ef5b9ad9f1ead3fd011c94f398fe9b49950a374210a51d71e94d20ebc89005c0"
NEW_SOURCE = "e19490caab93fac8d8cc07e6756d12b6fe586f4aa7b95096481c6b4617378c71"
CEILING = Decimal("1")


def _clock():
    return NOON


def _identity(source: str, **overrides) -> dict:
    identity = {
        "study": "clean-start-usx",
        "draw_sha256": "full-a",
        "editor_rules": {"S": "s-rules-2026-11-27", "X": "x-rules-2026-11-27"},
        "retry_policy": FULL_FLY_POLICY.name,
        "attempt_deadlines_seconds": [20.0, 60.0],
        "memory_prereqs": "matched",
        "source_sha256": source,
    }
    identity.update(overrides)
    return identity


def _function() -> dict:
    return {
        "name": "echo",
        "description": "Echo a value.",
        "parameters": {
            "type": "dict",
            "properties": {"value": {"type": "string", "description": "A value."}},
            "required": ["value"],
        },
    }


def _usage() -> dict:
    return {
        "prompt_tokens": 1000,
        "prompt_cache_hit_tokens": 200,
        "prompt_cache_miss_tokens": 800,
        "completion_tokens": 50,
    }


def _text(text: str = "done") -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": text}}], "usage": _usage()}


def _tool(value: str = "a") -> dict:
    return {
        "choices": [{"message": {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"id": "call_1", "type": "function", "function": {
                "name": "echo", "arguments": json.dumps({"value": value}),
            }}],
        }}],
        "usage": _usage(),
    }


def _one() -> Decimal:
    return spend_usd(cache_hit=200, cache_miss=800, output=50, at=NOON)[0]


def _single(case_id: str) -> dict:
    return {
        "id": case_id,
        "category": "multiple",
        "question": [[{"role": "user", "content": "q"}]],
        "function": [_function()],
        "prereq": False,
    }


def _memory(case_id: str, prereq: bool) -> dict:
    return {
        "id": case_id,
        "category": "memory_kv",
        "question": [[{"role": "user", "content": f"remember for {case_id}"}]],
        "function": [_function()],
        "involved_classes": ["MemoryAPI_kv"],
        "initial_config": {},
        "prereq": prereq,
        "scenario": "customer",
    }


def _u_slots(cases):
    return [slot for slot in build_slots(cases, ("off",)) if slot["arm"] == "U"]


def _lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _fingerprint(root: Path) -> list[tuple]:
    rows = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            rows.append((rel, "symlink", os.readlink(path)))
        elif path.is_file():
            stat = path.stat()
            rows.append((rel, "file", stat.st_mtime_ns, stat.st_size, sha256(path.read_bytes()).hexdigest()))
        elif path.is_dir():
            rows.append((rel, "dir", path.stat().st_mtime_ns))
    return rows


class _BoxLost(BaseException):
    """The process dies here. Nothing in the runner catches it."""


class _Deadlined:
    enforces_deadline = True

    def __init__(self, responses):
        self.responses = list(responses)
        self.bodies = []
        self.deadlines = []

    def __call__(self, body, deadline=None):
        self.bodies.append(body)
        self.deadlines.append(deadline)
        if not self.responses:
            raise AssertionError("script exhausted")
        item = self.responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class _DiskMemory:
    def __init__(self, die_after_flush: str | None = None):
        self.loaded = []
        self.die_after_flush = die_after_flush

    def _folder(self, case, config):
        root = config["initial_config"]["MemoryAPI_kv"]["model_result_dir"]
        return Path(root) / result_group(case["category"]) / "memory_snapshot"

    def initialize(self, case, config):
        folder = self._folder(case, config)
        final = folder / f"{case['scenario']}_final.json"
        if (case.get("prereq") and case["id"].endswith("-0")) or not final.exists():
            notes = []
        else:
            notes = json.loads(final.read_text(encoding="utf-8"))["notes"]
        self.loaded.append((case["id"], list(notes)))
        return {"MemoryAPI_kv": {"notes": notes, "folder": folder, "final": final}}

    def memory_prompt(self, question, case, instances):
        self.current = instances["MemoryAPI_kv"]
        return question

    def execute_calls(self, strings, case, config):
        for item in strings:
            self.current["notes"].append(item.split("'")[1])
        return ["stored" for _ in strings]

    def flush_prereq(self, case, instances):
        instance = instances["MemoryAPI_kv"]
        data = json.dumps({"notes": instance["notes"]}, indent=4)
        checkpoint = instance["folder"] / "prereq_checkpoints" / f"{case['id']}.json"
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        checkpoint.write_text(data)
        instance["final"].write_text(data)
        if case["id"] == self.die_after_flush:
            raise _BoxLost(case["id"])


def _fly(cases, out: Path, transport, *, ceiling=CEILING, executor=None, identity=None):
    slots = _u_slots(cases)
    try:
        execute(
            cases, slots, out, transport, ceiling_usd=ceiling, thinking_modes=("off",),
            clock=_clock, executor=executor, identity=identity or _identity(OLD_SOURCE),
            policy=FULL_FLY_POLICY,
        )
    except _BoxLost:
        pass
    return slots


def _continue(cases, slots, prior: Path, new: Path, transport, *, ceiling=CEILING, executor=None, identity=None):
    identity = identity or _identity(NEW_SOURCE)
    record = stage_continue_from(
        prior, new, cases, slots, identity=identity, ceiling_usd=ceiling, thinking_modes=("off",),
    )
    result = execute(
        cases, slots, new, transport, ceiling_usd=ceiling, thinking_modes=("off",),
        clock=_clock, executor=executor, identity=identity, policy=FULL_FLY_POLICY,
        resume=True, accept_new_source=True, continue_from=record,
    )
    return record, result


def test_a_silent_resume_refuses_when_only_source_sha256_differs(tmp_path):
    cases = [_single("multiple_0"), _single("multiple_1")]
    prior = tmp_path / "prior"
    slots = _fly(cases, prior, _Deadlined([_text(), _BoxLost("sent")]))
    before = _fingerprint(prior)
    with pytest.raises(RunStopped) as stopped:
        execute(
            cases, slots, prior, _Deadlined([_text()]), ceiling_usd=CEILING, thinking_modes=("off",),
            clock=_clock, identity=_identity(NEW_SOURCE), policy=FULL_FLY_POLICY, resume=True,
        )
    assert stopped.value.reason == "resume_identity_mismatch:source_sha256"
    assert _fingerprint(prior) == before
    assert not (prior / "resume").exists()
    with pytest.raises(RunStopped) as inspected:
        inspect_resume(
            prior, cases, slots, identity=_identity(NEW_SOURCE), ceiling_usd=CEILING, thinking_modes=("off",),
        )
    assert inspected.value.reason == "resume_identity_mismatch:source_sha256"
    assert _fingerprint(prior) == before


def test_continue_from_retries_a_sent_slot_from_try_1_and_counts_the_bills(tmp_path):
    # The stopped journal ends on a sent line, as attempt 4133 did. The ceiling
    # is one and a half bills. Carried spend allows the retried slot and then
    # stops. A fresh ceiling of the same amount would send the slot after it too.
    cases = [_single("multiple_0"), _single("live_multiple_623-160-3"), _single("multiple_2")]
    prior = tmp_path / "prior"
    ceiling = _one() * Decimal("1.5")
    first = _Deadlined([_text("kept"), _BoxLost("attempt sent, no outcome")])
    slots = _fly(cases, prior, first, ceiling=ceiling)
    attempts = _lines(prior / "attempts.jsonl")
    assert attempts[-1]["event"] == "sent"
    assert attempts[-1]["case_id"] == "live_multiple_623-160-3" and attempts[-1]["arm"] == "U"
    assert attempts[-1]["try"] == 1
    assert not any(row["attempt"] == attempts[-1]["attempt"] and row["event"] != "sent" for row in attempts)
    names = ("attempts.jsonl", "bills.jsonl", "run.json", "spend.json")
    ledgers = {name: (prior / name).read_bytes() for name in names}
    before = _fingerprint(prior)
    second = _Deadlined([_text("retried"), _text("would be a fresh ceiling")])
    record, result = _continue(cases, slots, prior, tmp_path / "continued", second, ceiling=ceiling)
    assert _fingerprint(prior) == before
    for name, payload in ledgers.items():
        assert (prior / name).read_bytes() == payload

    assert record["kind"] == "continue-from"
    assert record["prior_source_sha256"] == OLD_SOURCE
    assert record["source_sha256"] == NEW_SOURCE
    assert record["prior_out"] == str(prior.resolve())
    assert second.bodies == [first.bodies[1]]
    assert second.deadlines == [20.0]
    sent = [row for row in _lines(tmp_path / "continued" / "attempts.jsonl") if row["event"] == "sent"]
    resumed = [row for row in sent if row.get("session") == 2]
    assert resumed[0]["try"] == 1 and resumed[0]["deadline_seconds"] == 20.0
    assert resumed[0]["case_id"] == "live_multiple_623-160-3" and resumed[0]["arm"] == "U"
    assert "retry_of" not in resumed[0]
    assert (tmp_path / "continued" / "attempts.jsonl").read_bytes().startswith(ledgers["attempts.jsonl"])
    assert (tmp_path / "continued" / "bills.jsonl").read_bytes().startswith(ledgers["bills.jsonl"])
    bills = _lines(tmp_path / "continued" / "bills.jsonl")
    assert len(bills) == 2
    assert Decimal(result["running_usd"]) == sum(Decimal(row["usd"]) for row in bills) == _one() * 2
    assert result["reason"] == "ceiling"
    assert result["unbilled_attempts"][0]["event"] == "no_outcome_recorded"
    assert result["unbilled_attempts"][0]["case_id"] == "live_multiple_623-160-3"
    run = json.loads((tmp_path / "continued" / "run.json").read_text())
    assert run["identity"]["source_sha256"] == NEW_SOURCE
    assert run["continue_from"] == record
    assert run["official_settlement"] is False
    assert run["retry_policy"]["name"] == "deadline-20s-retry-60s-skip"
    assert run["retry_policy"]["attempt_deadlines_seconds"] == [20.0, 60.0]
    assert run["thinking_modes_authorized"] == ["off"]
    assert run["sessions"][1]["continue_from"] == record
    prior_run = json.loads((tmp_path / "continued" / "resume" / "session-2" / "prior_run.json").read_text())
    assert prior_run["identity"]["source_sha256"] == OLD_SOURCE
    assert "continue_from" not in prior_run


def test_continue_from_refuses_editor_plan_slot_and_ceiling_mismatches(tmp_path):
    cases = [_single("multiple_0"), _single("multiple_1"), _single("multiple_2")]
    prior = tmp_path / "prior"
    slots = _fly(cases, prior, _Deadlined([_text(), ProviderHTTPError(402, "balance")]))
    original = _fingerprint(prior)

    def refused(name: str, reason: str, *, identity=None, ceiling=CEILING, used_slots=None, modes=("off",), edit=None):
        scratch = tmp_path / name
        shutil.copytree(prior, scratch)
        if edit:
            edit(scratch)
        before = _fingerprint(scratch)
        with pytest.raises(RunStopped) as stopped:
            stage_continue_from(
                scratch, tmp_path / f"out-{name}", cases, used_slots or slots,
                identity=identity or _identity(NEW_SOURCE), ceiling_usd=ceiling, thinking_modes=modes,
            )
        assert stopped.value.reason == reason
        assert _fingerprint(scratch) == before
        assert not (tmp_path / f"out-{name}").exists()

    refused("editor", "resume_identity_mismatch:editor_rules", identity=_identity(
        NEW_SOURCE, editor_rules={"S": "s-rules-other", "X": "x-rules-2026-11-27"},
    ))
    refused("plan", "resume_draw_mismatch", identity=_identity(NEW_SOURCE, draw_sha256="full-b"))
    refused("slots", "resume_slot_mismatch", used_slots=list(reversed(slots)))
    refused("ceiling", "resume_ceiling_mismatch", ceiling=CEILING * 2)
    refused("policy", "resume_identity_mismatch:retry_policy", identity=_identity(NEW_SOURCE, retry_policy="other"))
    refused(
        "deadlines", "resume_identity_mismatch:attempt_deadlines_seconds",
        identity=_identity(NEW_SOURCE, attempt_deadlines_seconds=[10.0, 60.0]),
    )
    refused("prereqs", "resume_identity_mismatch:memory_prereqs", identity=_identity(NEW_SOURCE, memory_prereqs="none"))
    refused("thinking", "resume_thinking_mismatch", modes=("off", "on"))
    refused("model", "resume_study_mismatch", edit=lambda path: _rewrite(path, model="other-model"))
    refused("settlement", "resume_official_settlement_mismatch", edit=lambda path: _rewrite(path, official_settlement=True))
    refused("arms", "resume_arms_mismatch", edit=lambda path: _rewrite(path, arms=["U"]))
    refused("rate", "resume_rate_card_mismatch", edit=lambda path: _rewrite_rate(path))
    assert _fingerprint(prior) == original


def _rewrite(path: Path, **fields) -> None:
    run = json.loads((path / "run.json").read_text())
    run.update(fields)
    (path / "run.json").write_text(json.dumps(run))


def _rewrite_rate(path: Path) -> None:
    run = json.loads((path / "run.json").read_text())
    run["rate_card"] = {**run["rate_card"], "id": "other-card"}
    (path / "run.json").write_text(json.dumps(run))


def test_continue_from_rolls_memory_back_on_the_copy_only(tmp_path):
    cases = [
        _memory("memory_kv_prereq_0-customer-0", True),
        _memory("memory_kv_prereq_1-customer-1", True),
        _memory("memory_kv_7-customer-7", False),
    ]
    prior = tmp_path / "prior"
    slots = _fly(
        cases, prior,
        _Deadlined([_tool("a"), _text(), _tool("b"), _text()]),
        executor=_DiskMemory(die_after_flush="memory_kv_prereq_1-customer-1"),
    )
    final = prior / "result/deepseek-flash-thinking-off-U/agentic/memory/kv/memory_snapshot/customer_final.json"
    assert json.loads(final.read_text())["notes"] == ["a", "b"]
    before = _fingerprint(prior)
    memory = _DiskMemory()
    _record, result = _continue(
        cases, slots, prior, tmp_path / "continued",
        _Deadlined([_tool("c"), _text(), _text("answer")]),
        executor=memory,
    )
    assert result["complete"] is True
    assert memory.loaded[0] == ("memory_kv_prereq_1-customer-1", ["a"])
    assert _fingerprint(prior) == before
    assert json.loads(final.read_text())["notes"] == ["a", "b"]


def test_restage_does_not_recopy_and_another_source_is_refused(tmp_path):
    cases = [_single("multiple_0"), _single("multiple_1")]
    prior = tmp_path / "prior"
    slots = _fly(cases, prior, _Deadlined([_text(), _BoxLost("sent")]))
    new = tmp_path / "continued"
    record = stage_continue_from(
        prior, new, cases, slots, identity=_identity(NEW_SOURCE), ceiling_usd=CEILING, thinking_modes=("off",),
    )
    (new / "extra.txt").write_text("kept")
    before = _fingerprint(prior)
    again = stage_continue_from(
        prior, new, cases, slots, identity=_identity(NEW_SOURCE), ceiling_usd=CEILING, thinking_modes=("off",),
    )
    assert again == record
    assert (new / "extra.txt").read_text() == "kept"
    assert _fingerprint(prior) == before
    with pytest.raises(RunStopped) as other:
        stage_continue_from(
            prior, new, cases, slots, identity=_identity("f" * 64), ceiling_usd=CEILING, thinking_modes=("off",),
        )
    assert other.value.reason == "continue_from_staged_for_another_source"
    assert (new / "extra.txt").read_text() == "kept"
    assert _fingerprint(prior) == before
    nested = prior / "nested"
    with pytest.raises(RunStopped) as overlap:
        stage_continue_from(
            prior, nested, cases, slots, identity=_identity(NEW_SOURCE), ceiling_usd=CEILING, thinking_modes=("off",),
        )
    assert overlap.value.reason == "continue_from_out_overlaps_prior"
    assert _fingerprint(prior) == before
    assert not nested.exists()


def test_a_later_resume_of_the_new_directory_keeps_the_cutover(tmp_path):
    cases = [_single("multiple_0"), _single("multiple_1"), _single("multiple_2")]
    prior = tmp_path / "prior"
    ceiling = _one() * Decimal("1.5")
    slots = _fly(cases, prior, _Deadlined([_text(), _BoxLost("sent")]), ceiling=ceiling)
    new = tmp_path / "continued"
    _record, first = _continue(cases, slots, prior, new, _Deadlined([_text(), _text()]), ceiling=ceiling)
    assert first["reason"] == "ceiling"
    before = _fingerprint(prior)
    again = _Deadlined([_text()])
    result = execute(
        cases, slots, new, again, ceiling_usd=ceiling, thinking_modes=("off",),
        clock=_clock, identity=_identity(NEW_SOURCE), policy=FULL_FLY_POLICY, resume=True,
    )
    assert again.bodies == []
    assert result["reason"] == "ceiling"
    assert result["continue_from"]["kind"] == "continue-from"
    assert result["continue_from"]["prior_source_sha256"] == OLD_SOURCE
    assert result["identity"]["source_sha256"] == NEW_SOURCE
    assert "continue_from" not in result["identity"]
    assert result["sessions"][1]["continue_from"]["source_sha256"] == NEW_SOURCE
    assert _fingerprint(prior) == before


def test_cli_continue_from_accepts_only_a_new_source_and_writes_nothing(tmp_path, monkeypatch, capsys):
    from tool_compression.clean_start import full
    from tool_compression.clean_start.__main__ import main, run_identity
    from tool_compression.clean_start.runner import _status, plan_summary

    cases = full.select_full_cases()
    slots = build_slots(cases, ("off",))
    cost = full.load_committed_cost()
    identity = run_identity(cases, pilot=False, memory_prereqs="matched", full=True, cost=cost)
    assert identity["source_sha256"] == source_sha256()
    identity = {**identity, "source_sha256": OLD_SOURCE}
    prior = tmp_path / "live-ae57892d"
    summary = plan_summary(slots, ("off",))
    _status(
        prior,
        status="incomplete",
        complete=False,
        reason="stopped",
        provider_contacted=True,
        identity=identity,
        ceiling_usd="68.54",
        running_usd="0",
        slots_sent=0,
        session=1,
        sessions=[{"session": 1, "started_at": "2026-11-27T12:00:00+00:00", "resumed": False}],
        **summary,
    )
    # One sent line with no outcome, for the first slot. The check must not rewrite it.
    sent = {
        "attempt": 1, "event": "sent", "case_id": slots[0]["case_id"], "arm": slots[0]["arm"],
        "thinking": "off", "turn": 0, "step": 0, "sent_at": NOON.isoformat(), "try": 1,
        "deadline_seconds": 20.0, "session": 1,
    }
    (prior / "attempts.jsonl").write_text(json.dumps(sent) + "\n")
    before = _fingerprint(prior)
    monkeypatch.setattr(
        "tool_compression.clean_start.__main__.authorized_transport",
        lambda: (_ for _ in ()).throw(AssertionError("key read")),
    )
    base = [
        "run", "--full", "--thinking", "off", "--memory-prereqs", "matched", "--ceiling-usd", "68.54",
    ]
    new = tmp_path / "new-empty-dir"
    assert main(base + ["--resume", "--out", str(prior)]) == 2
    assert "resume_identity_mismatch:source_sha256" in capsys.readouterr().err
    assert _fingerprint(prior) == before
    assert not new.exists()

    assert main(base + ["--continue-from", str(prior), "--out", str(new)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["continue_from_check"] is True and report["provider_contacted"] is False
    assert report["continue_from"]["kind"] == "continue-from"
    assert report["continue_from"]["prior_out"] == str(prior.resolve())
    assert report["continue_from"]["prior_source_sha256"] == OLD_SOURCE
    assert report["continue_from"]["source_sha256"] == source_sha256()
    assert report["next_slot"]["case_id"] == slots[0]["case_id"]
    assert report["next_slot"]["arm"] == slots[0]["arm"]
    assert report["unbilled_attempts"] == [{
        "attempt": 1, "event": "no_outcome_recorded", "session": 1,
        "case_id": slots[0]["case_id"], "arm": slots[0]["arm"],
    }]
    assert _fingerprint(prior) == before
    assert not new.exists()

    def swapped(name: str, **fields) -> Path:
        dest = tmp_path / name
        shutil.copytree(prior, dest)
        run = json.loads((dest / "run.json").read_text())
        run.update(fields)
        (dest / "run.json").write_text(json.dumps(run))
        return dest

    editor = swapped("editor", identity={**identity, "editor_rules": {"S": "other", "X": "x-rules-2026-11-27"}})
    assert main(base + ["--continue-from", str(editor), "--out", str(tmp_path / "editor-out")]) == 2
    assert "resume_identity_mismatch:editor_rules" in capsys.readouterr().err
    plan = swapped("plan", identity={**identity, "draw_sha256": "0" * 64})
    assert main(base + ["--continue-from", str(plan), "--out", str(tmp_path / "plan-out")]) == 2
    assert "resume_draw_mismatch" in capsys.readouterr().err
    slot = swapped("slot", slot_sha256="0" * 64)
    assert main(base + ["--continue-from", str(slot), "--out", str(tmp_path / "slot-out")]) == 2
    assert "resume_slot_mismatch" in capsys.readouterr().err
    assert main(base + ["--continue-from", str(prior), "--ceiling-usd", "70", "--out", str(tmp_path / "ceiling-out")]) == 2
    assert "resume_ceiling_mismatch" in capsys.readouterr().err
    assert main(base + ["--continue-from", str(prior), "--resume", "--out", str(new)]) == 2
    assert "--continue-from copies a stopped run" in capsys.readouterr().err
    assert main(["run", "--continue-from", str(prior), "--out", str(new), "--ceiling-usd", "1"]) == 2
    assert "--continue-from applies to --full only" in capsys.readouterr().err
    assert _fingerprint(prior) == before
    assert not new.exists()
    for name in ("editor", "plan", "slot"):
        assert _fingerprint(tmp_path / name)  # the copies exist; the outs must not
        assert not (tmp_path / f"{name}-out").exists()
    assert not (tmp_path / "ceiling-out").exists()


def test_cli_live_continue_stages_the_copy_and_does_not_call_the_provider(tmp_path, monkeypatch):
    import tool_compression.clean_start.__main__ as cli

    cases_holder = {}

    def build_prior():
        from tool_compression.clean_start import full
        from tool_compression.clean_start.runner import _status, plan_summary

        cases = full.select_full_cases()
        slots = build_slots(cases, ("off",))
        cost = full.load_committed_cost()
        identity = cli.run_identity(cases, pilot=False, memory_prereqs="matched", full=True, cost=cost)
        identity = {**identity, "source_sha256": OLD_SOURCE}
        prior = tmp_path / "live-ae57892d"
        _status(
            prior,
            status="incomplete",
            complete=False,
            reason="stopped",
            provider_contacted=True,
            identity=identity,
            ceiling_usd="68.54",
            running_usd="0",
            slots_sent=0,
            session=1,
            sessions=[{"session": 1, "started_at": "2026-11-27T12:00:00+00:00", "resumed": False}],
            **plan_summary(slots, ("off",)),
        )
        cases_holder["prior"] = prior
        cases_holder["source"] = source_sha256()
        return prior

    prior = build_prior()
    before = _fingerprint(prior)
    seen = {}

    def fake_execute(*args, **kwargs):
        seen["out"] = args[2]
        seen["kwargs"] = kwargs
        return {
            "complete": False, "status": "incomplete", "reason": "stopped", "running_usd": "0",
            "session": 2, "slots_sent": 0, "slots_total": 12952, "tokens": {},
            "uncertain_attempts": [], "unbilled_attempts": [],
        }

    class _Executor:
        def __init__(self, *_args, **_kwargs):
            pass

    monkeypatch.setattr(cli, "_now", lambda: datetime(2026, 11, 28, 12, 0, tzinfo=timezone.utc))
    monkeypatch.setattr(cli, "preflight", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(cli, "resolve_bfcl_package", lambda root: Path(root))
    monkeypatch.setattr(cli, "OfficialBfclExecutor", _Executor)
    monkeypatch.setattr(cli, "authorized_transport", lambda: object())
    monkeypatch.setattr(cli, "execute", fake_execute)
    new = tmp_path / "new-empty-dir"
    code = cli.main([
        "run", "--full", "--live", "--authorize-live", "--thinking", "off", "--memory-prereqs", "matched",
        "--ceiling-usd", "68.54", "--continue-from", str(prior), "--bfcl-root", str(tmp_path / "gorilla"),
        "--out", str(new),
    ])
    assert code == 1
    assert seen["kwargs"]["resume"] is True
    assert seen["kwargs"]["accept_new_source"] is True
    assert seen["kwargs"]["continue_from"]["kind"] == "continue-from"
    assert seen["kwargs"]["continue_from"]["prior_source_sha256"] == OLD_SOURCE
    assert seen["kwargs"]["continue_from"]["source_sha256"] == cases_holder["source"]
    assert seen["kwargs"]["policy"].name == "deadline-20s-retry-60s-skip"
    assert Path(seen["out"]) == new
    assert (new / "continue-from.json").is_file()
    assert _fingerprint(prior) == before
    assert not (prior / "continue-from.json").exists()
