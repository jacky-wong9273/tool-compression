"""Resume a stopped run in its own output directory.

A slot is finished when its sidecar says ``finished`` and its result file holds
exactly one line with its id. A slot is skipped when ``failures.jsonl`` holds
its record; it has no result line and is not sent again. The runner stops at
its first slot that is neither, so finished and skipped slots are a prefix of
the slot order. Anything else is refused. The first other slot is sent again
from its first request: its stopped sidecar, and a result line it may have
written before the box was lost, are moved under ``resume/session-<n>/``.
``attempts.jsonl``, ``bills.jsonl`` and ``failures.jsonl`` are never rewritten.
A skipped slot whose sidecar was not yet marked when the box was lost is
marked. Recorded spend is the sum of the bill ledger, and that sum counts
against the same ceiling.

Memory state. In pinned BFCL every entry of a scenario other than the ``-0``
prerequisite loads ``<scenario>_final.json``, and only a prerequisite flush
writes it, right after ``prereq_checkpoints/<id>.json``. So
``<scenario>_final.json`` must equal the checkpoint of the chain's last
finished prerequisite, or be absent when none finished. A flush that landed
for the unfinished prerequisite is rolled back to that checkpoint. Any other
mismatch is refused. Multi-turn class instances live in process memory, so a
new process starts the re-sent slot from its initial config.

``inspect_resume`` reads only. ``apply_resume`` does the moves.
"""

from __future__ import annotations

from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import json
import os
import shutil

from tool_compression.clean_start.categories import is_memory, result_group
from tool_compression.clean_start.pin import OFFICIAL_SETTLEMENT, REQUEST_MODEL, STUDY_ID
from tool_compression.clean_start.rate_card import rate_card
from tool_compression.clean_start.scoring import registry_dir, result_model_name, result_relative

RESUME_DIR = "resume"
RESUME_LOG = "resume.jsonl"
FAILURES = "failures.jsonl"
SKIP_KINDS = ("skipped", "dependency_skipped")


def source_sha256() -> str:
    """Every ``.py`` file under ``src/tool_compression``. A resume runs the code that started the run."""
    root = Path(__file__).resolve().parents[1]
    digest = sha256()
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        digest.update(path.relative_to(root).as_posix().encode("utf-8") + b"\0")
        digest.update(path.read_bytes() + b"\0")
    return digest.hexdigest()


def _stop(reason: str):
    from tool_compression.clean_start.runner import RunStopped

    return RunStopped(reason)


def _rows(path: Path, label: str) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            raise _stop(f"resume_unreadable_line:{label}:{number}") from None
        if not isinstance(row, dict):
            raise _stop(f"resume_unreadable_line:{label}:{number}")
        rows.append(row)
    return rows


def _sidecar_path(out_dir: Path, slot: dict) -> Path:
    return out_dir / "model_outputs" / registry_dir(slot["thinking"]) / slot["arm"] / f"{slot['case_id']}.json"


def _snapshot_folder(out_dir: Path, thinking: str, arm: str, category: str) -> Path:
    return out_dir / "result" / result_model_name(thinking, arm) / result_group(category) / "memory_snapshot"


def _relative(out_dir: Path, path: Path) -> str:
    return path.relative_to(out_dir).as_posix()


def _prior_run(out_dir: Path) -> dict:
    path = out_dir / "run.json"
    if not path.is_file():
        raise _stop("resume_without_prior_run")
    try:
        prior = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise _stop("resume_prior_run_unreadable") from None
    if not prior.get("provider_contacted"):
        raise _stop("resume_without_provider_evidence")
    return prior


def _check_identity(prior: dict, *, identity: dict, slots: list[dict], modes: tuple[str, ...], ceiling_usd: Decimal) -> None:
    from tool_compression.clean_start.runner import plan_summary

    if prior.get("study") != STUDY_ID or prior.get("model") != REQUEST_MODEL:
        raise _stop("resume_study_mismatch")
    if prior.get("official_settlement") is not OFFICIAL_SETTLEMENT:
        raise _stop("resume_official_settlement_mismatch")
    if prior.get("complete"):
        raise _stop("resume_already_complete")
    before = prior.get("identity") or {}
    if before.get("draw_sha256") != identity.get("draw_sha256"):
        raise _stop("resume_draw_mismatch")
    for key in sorted(set(before) | set(identity)):
        if before.get(key) != identity.get(key):
            raise _stop(f"resume_identity_mismatch:{key}")
    if prior.get("slot_sha256") != plan_summary(slots, modes)["slot_sha256"] or prior.get("slots_total") != len(slots):
        raise _stop("resume_slot_mismatch")
    if prior.get("thinking_modes_authorized") != list(modes):
        raise _stop("resume_thinking_mismatch")
    if prior.get("ceiling_usd") is None or Decimal(str(prior["ceiling_usd"])) != ceiling_usd:
        raise _stop("resume_ceiling_mismatch")
    if (prior.get("rate_card") or {}).get("id") != rate_card()["id"]:
        raise _stop("resume_rate_card_mismatch")


def _ledgers(out_dir: Path) -> dict:
    attempts = _rows(out_dir / "attempts.jsonl", "attempts.jsonl")
    bills = _rows(out_dir / "bills.jsonl", "bills.jsonl")
    sent: dict[int, dict] = {}
    events: dict[int, list[str]] = {}
    order: list[int] = []
    for row in attempts:
        number = row.get("attempt")
        if not isinstance(number, int) or isinstance(number, bool):
            raise _stop("resume_attempt_journal_unreadable")
        if row.get("event") == "sent":
            if number in sent:
                raise _stop(f"resume_attempt_sent_twice:{number}")
            sent[number] = row
            order.append(number)
        elif number not in sent:
            raise _stop(f"resume_attempt_event_before_send:{number}")
        else:
            events.setdefault(number, []).append(str(row.get("event")))
    if order != list(range(1, len(order) + 1)):
        raise _stop("resume_attempt_journal_gap")
    from tool_compression.clean_start.runner import add_tokens, empty_tokens

    running = Decimal(0)
    tokens = empty_tokens()
    billed: set[int] = set()
    for row in bills:
        number = row.get("attempt")
        if number not in sent or number in billed:
            raise _stop(f"resume_bill_without_its_attempt:{number}")
        attempt = sent[number]
        if (row.get("case_id"), row.get("arm"), row.get("thinking")) != (
            attempt.get("case_id"), attempt.get("arm"), attempt.get("thinking")
        ):
            raise _stop(f"resume_bill_attempt_mismatch:{number}")
        running += Decimal(str(row["usd"]))
        if Decimal(str(row["running_usd"])) != running:
            raise _stop(f"resume_bill_ledger_inconsistent:{number}")
        add_tokens(tokens, row)
        billed.add(number)
    unbilled = []
    for number in order:
        if number in billed:
            continue
        seen = events.get(number) or []
        unbilled.append({
            "attempt": number,
            "event": seen[-1] if seen else "no_outcome_recorded",
            "session": sent[number].get("session", 1),
            "case_id": sent[number].get("case_id"),
            "arm": sent[number].get("arm"),
        })
    return {
        "sent": sent,
        "events": events,
        "bills": bills,
        "running": running,
        "tokens": tokens,
        "unbilled": unbilled,
        "max_attempt": len(order),
        "retries": sum(1 for row in sent.values() if row.get("retry_of") is not None),
        "sessions": max([int(row.get("session", 1)) for row in sent.values()] or [0]),
    }


def _failures(out_dir: Path, ledgers: dict, index_of: dict) -> dict[int, dict]:
    """Skipped slots by slot index. Every skip names failed attempts that are in the journal."""
    skipped: dict[int, dict] = {}
    for number, row in enumerate(_rows(out_dir / FAILURES, FAILURES), 1):
        key = (row.get("thinking"), row.get("arm"), row.get("case_id"))
        index = index_of.get(key)
        if row.get("kind") not in SKIP_KINDS or index is None:
            raise _stop(f"resume_failure_record_for_no_slot:{number}")
        if index in skipped:
            raise _stop(f"resume_failure_recorded_twice:{row.get('case_id')}:{row.get('arm')}")
        if row["kind"] == "skipped":
            listed = row.get("attempts") or []
            if not listed:
                raise _stop(f"resume_failure_without_its_attempt:{row.get('case_id')}:{row.get('arm')}")
            for item in listed:
                attempt = item.get("attempt")
                sent = ledgers["sent"].get(attempt)
                if sent is None or "failed" not in (ledgers["events"].get(attempt) or []):
                    raise _stop(f"resume_failure_without_its_attempt:{attempt}")
                if (sent.get("thinking"), sent.get("arm"), sent.get("case_id")) != key:
                    raise _stop(f"resume_failure_attempt_mismatch:{attempt}")
        skipped[index] = row
    return skipped


def _result_lines(out_dir: Path) -> dict[str, list[tuple[int, dict]]]:
    found: dict[str, list[tuple[int, dict]]] = {}
    root = out_dir / "result"
    if not root.exists():
        return found
    for path in sorted(root.rglob("*_result.json")):
        if "memory_snapshot" in path.parts:
            continue
        label = _relative(out_dir, path)
        rows = []
        for number, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError:
                raise _stop(f"resume_unreadable_line:{label}:{number}") from None
            if not isinstance(row, dict) or "id" not in row:
                raise _stop(f"resume_unreadable_line:{label}:{number}")
            rows.append((number, row))
        found[label] = rows
    return found


def inspect_resume(
    out_dir: Path,
    cases: list[dict],
    slots: list[dict],
    *,
    identity: dict,
    ceiling_usd: Decimal,
    thinking_modes: tuple[str, ...],
) -> dict:
    """What a resume of ``out_dir`` would skip, send again, and repair. Writes nothing."""
    out_dir = Path(out_dir)
    modes = tuple(thinking_modes)
    prior = _prior_run(out_dir)
    _check_identity(prior, identity=identity, slots=slots, modes=modes, ceiling_usd=ceiling_usd)
    ledgers = _ledgers(out_dir)
    by_id = {case["id"]: case for case in cases}
    index_of = {(slot["thinking"], slot["arm"], slot["case_id"]): index for index, slot in enumerate(slots)}
    expected_lines = {
        (result_relative(slot["case_id"], slot["thinking"], slot["arm"]).as_posix(), slot["case_id"]): index
        for index, slot in enumerate(slots)
    }
    lines: dict[int, list[tuple[str, int]]] = {}
    for label, rows in _result_lines(out_dir).items():
        for number, row in rows:
            index = expected_lines.get((label, row["id"]))
            if index is None:
                raise _stop(f"resume_result_line_for_no_slot:{label}:{number}")
            lines.setdefault(index, []).append((label, number))
    skipped = _failures(out_dir, ledgers, index_of)

    first = None
    sidecar_of_first = None
    unmarked: list[int] = []
    for index, slot in enumerate(slots):
        path = _sidecar_path(out_dir, slot)
        found = lines.get(index, [])
        if len(found) > 1:
            raise _stop(f"resume_duplicate_result_line:{slot['case_id']}:{slot['arm']}")
        sidecar = None
        if path.exists():
            try:
                sidecar = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                sidecar = {"status": "unreadable"}
        if first is None:
            if index in skipped:
                if found:
                    raise _stop(f"resume_result_line_for_skipped_slot:{slot['case_id']}:{slot['arm']}")
                if sidecar is None or sidecar.get("status") != "skipped":
                    unmarked.append(index)
                continue
            finished = (
                sidecar is not None
                and sidecar.get("status") == "finished"
                and sidecar.get("scorable") is True
                and len(found) == 1
            )
            if finished:
                continue
            first = index
            sidecar_of_first = sidecar
        elif index in skipped:
            raise _stop(f"resume_failure_beyond_the_stop:{slot['case_id']}:{slot['arm']}")
        elif sidecar is not None or found:
            raise _stop(f"resume_finished_slots_not_a_prefix:{slot['case_id']}:{slot['arm']}")

    limit = len(slots) if first is None else first
    broken = _broken_chains(slots, by_id, skipped, limit)
    abandoned = Decimal(0)
    for row in ledgers["bills"]:
        index = index_of.get((row.get("thinking"), row.get("arm"), row.get("case_id")))
        if index is None or index > limit:
            raise _stop(f"resume_bill_beyond_the_stop:{row.get('attempt')}")
        if index == first:
            abandoned += Decimal(str(row["usd"]))
    for number, row in ledgers["sent"].items():
        index = index_of.get((row.get("thinking"), row.get("arm"), row.get("case_id")))
        if index is None or index > limit:
            raise _stop(f"resume_attempt_beyond_the_stop:{number}")

    actions: list[dict] = []
    for index in unmarked:
        slot = slots[index]
        actions.append({
            "kind": "mark_skipped",
            "path": _relative(out_dir, _sidecar_path(out_dir, slot)),
            "case_id": slot["case_id"],
            "arm": slot["arm"],
            "record": skipped[index],
        })
    if first is not None:
        slot = slots[first]
        if first in lines:
            label, number = lines[first][0]
            actions.append({"kind": "drop_result_line", "path": label, "line": number, "case_id": slot["case_id"]})
        if sidecar_of_first is not None:
            actions.append({
                "kind": "quarantine",
                "path": _relative(out_dir, _sidecar_path(out_dir, slot)),
                "why": f"sidecar of the slot sent again, status {sidecar_of_first.get('status')}",
            })
    actions.extend(_memory_actions(out_dir, cases, slots, by_id, first, set(skipped)))

    sessions_seen = [ledgers["sessions"], int(prior.get("session") or 1)]
    for row in _rows(out_dir / RESUME_LOG, RESUME_LOG):
        sessions_seen.append(int(row.get("session") or 0))
    resume_root = out_dir / RESUME_DIR
    if resume_root.exists():
        for child in resume_root.iterdir():
            if child.name.startswith("session-") and child.name[len("session-"):].isdigit():
                sessions_seen.append(int(child.name[len("session-"):]))
    next_slot = None
    if first is not None:
        slot = slots[first]
        next_slot = {
            "index": first,
            "case_id": slot["case_id"],
            "arm": slot["arm"],
            "thinking": slot["thinking"],
            "prereq": slot["prereq"],
        }
    return {
        "session": max(sessions_seen) + 1,
        "prior_status": {key: prior.get(key) for key in ("status", "reason", "running_usd", "slots_sent")},
        "prior_sessions": list(prior.get("sessions") or []),
        "prior_spend_usd": ledgers["running"],
        "prior_billed": len(ledgers["bills"]),
        "prior_tokens": ledgers["tokens"],
        "max_attempt": ledgers["max_attempt"],
        "prior_retries": ledgers["retries"],
        "unbilled_attempts": ledgers["unbilled"],
        "finished_slots": limit,
        "prior_skipped": len(skipped),
        "skipped_slots": [
            {"index": index, "case_id": slots[index]["case_id"], "arm": slots[index]["arm"], "kind": row["kind"]}
            for index, row in sorted(skipped.items())
        ],
        "broken_chains": broken,
        "slots_total": len(slots),
        "next_slot": next_slot,
        "abandoned_partial_usd": abandoned,
        "actions": actions,
    }


def _broken_chains(slots, by_id, skipped: dict[int, dict], limit: int) -> list[dict]:
    """Memory chains whose prerequisite was skipped. Every later slot of one is skipped too."""
    from tool_compression.clean_start.runner import memory_chain

    broken: dict[tuple, str] = {}
    for index, slot in enumerate(slots[:limit]):
        chain = memory_chain(slot, by_id[slot["case_id"]])
        if chain is None:
            continue
        kind = skipped[index]["kind"] if index in skipped else None
        if chain in broken:
            if kind != "dependency_skipped":
                raise _stop(f"resume_slot_after_its_chain_broke:{slot['case_id']}:{slot['arm']}")
            continue
        if kind == "dependency_skipped":
            raise _stop(f"resume_dependency_skip_without_a_skipped_prerequisite:{slot['case_id']}:{slot['arm']}")
        if kind == "skipped" and slot["prereq"]:
            broken[chain] = slot["case_id"]
    return [
        {"thinking": key[0], "arm": key[1], "category": key[2], "scenario": key[3], "prereq": prereq}
        for key, prereq in broken.items()
    ]


def _memory_actions(out_dir: Path, cases, slots, by_id, first, skipped: set[int] = frozenset()) -> list[dict]:
    chains: dict[tuple, list[int]] = {}
    for index, slot in enumerate(slots):
        case = by_id[slot["case_id"]]
        if not is_memory(case["category"]):
            continue
        key = (slot["thinking"], slot["arm"], case["category"], case.get("scenario"))
        chain = chains.setdefault(key, [])
        if case.get("prereq"):
            chain.append(index)
    actions = []
    for (thinking, arm, category, scenario), prereqs in chains.items():
        folder = _snapshot_folder(out_dir, thinking, arm, category)
        final = folder / f"{scenario}_final.json"

        def checkpoint(index: int) -> Path:
            return folder / "prereq_checkpoints" / f"{slots[index]['case_id']}.json"

        # A skipped prerequisite never flushed: it stopped before its last turn.
        done = [index for index in prereqs if (first is None or index < first) and index not in skipped]
        pending = [index for index in prereqs if first is not None and index >= first]
        for index in pending[1:]:
            if checkpoint(index).exists():
                raise _stop(f"resume_memory_checkpoint_ahead_of_the_stop:{_relative(out_dir, checkpoint(index))}")
        upcoming = checkpoint(pending[0]) if pending else None
        expected = None
        source = None
        if done:
            source = checkpoint(done[-1])
            if not source.is_file():
                raise _stop(f"resume_memory_checkpoint_missing:{_relative(out_dir, source)}")
            expected = source.read_bytes()
        actual = final.read_bytes() if final.is_file() else None
        if actual != expected:
            if upcoming is None or not upcoming.exists():
                raise _stop(f"resume_memory_snapshot_unexpected:{_relative(out_dir, final)}")
            actions.append({
                "kind": "restore_snapshot",
                "path": _relative(out_dir, final),
                "from": None if source is None else _relative(out_dir, source),
                "quarantine": [_relative(out_dir, upcoming)] + ([_relative(out_dir, final)] if actual is not None else []),
            })
        elif upcoming is not None and upcoming.exists():
            actions.append({
                "kind": "quarantine",
                "path": _relative(out_dir, upcoming),
                "why": "checkpoint of the prerequisite sent again",
            })
    return actions


def describe(plan: dict) -> dict:
    """JSON form of a resume plan."""
    return {
        "session": plan["session"],
        "prior_status": plan["prior_status"],
        "prior_spend_usd": str(plan["prior_spend_usd"]),
        "prior_billed": plan["prior_billed"],
        "max_attempt": plan["max_attempt"],
        "prior_retries": plan["prior_retries"],
        "unbilled_attempts": plan["unbilled_attempts"],
        "finished_slots": plan["finished_slots"],
        "skipped_slots": len(plan.get("skipped_slots") or []),
        "broken_chains": plan.get("broken_chains") or [],
        "slots_total": plan["slots_total"],
        "next_slot": plan["next_slot"],
        "abandoned_partial_usd": str(plan["abandoned_partial_usd"]),
        "actions": plan["actions"],
    }


def _fsync_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)
    from tool_compression.clean_start.runner import fsync_dir

    fsync_dir(path.parent)


def _move(out_dir: Path, session_dir: Path, relative: str) -> None:
    source = out_dir / relative
    if not source.exists():
        return
    target = session_dir / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    os.replace(source, target)


def _keep_copy(out_dir: Path, session_dir: Path, relative: str) -> None:
    source = out_dir / relative
    if not source.exists():
        return
    target = session_dir / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def apply_resume(out_dir: Path, plan: dict, at: str) -> dict:
    """Move the re-sent slot's leftovers aside and log the session. Ledgers are untouched.

    Every step leaves a state that a fresh ``inspect_resume`` reads as either
    the same plan or a shorter one, so a box lost here is resumed again.
    """
    out_dir = Path(out_dir)
    session_dir = out_dir / RESUME_DIR / f"session-{plan['session']}"
    if session_dir.exists():
        raise _stop(f"resume_session_dir_exists:{plan['session']}")
    session_dir.mkdir(parents=True)
    for name in ("run.json", "spend.json"):
        if (out_dir / name).exists():
            shutil.copy2(out_dir / name, session_dir / f"prior_{name}")
    for action in plan["actions"]:
        if action["kind"] == "drop_result_line":
            path = out_dir / action["path"]
            original = path.read_text(encoding="utf-8").split("\n")
            kept = [line for number, line in enumerate(original, 1) if number != action["line"] and line.strip()]
            dropped = original[action["line"] - 1]
            _keep_copy(out_dir, session_dir, action["path"])
            with (session_dir / "dropped_result_lines.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"path": action["path"], "line": action["line"], "text": dropped}) + "\n")
            if kept:
                _fsync_write(path, ("\n".join(kept) + "\n").encode("utf-8"))
            else:
                path.unlink()
        elif action["kind"] == "quarantine":
            _move(out_dir, session_dir, action["path"])
        elif action["kind"] == "mark_skipped":
            path = out_dir / action["path"]
            sidecar = {}
            if path.is_file():
                _keep_copy(out_dir, session_dir, action["path"])
                try:
                    sidecar = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    sidecar = {}
            if not isinstance(sidecar, dict):
                sidecar = {}
            record = action["record"]
            sidecar.setdefault("case_id", record["case_id"])
            sidecar.setdefault("category", record.get("category"))
            sidecar.setdefault("arm", record["arm"])
            sidecar.setdefault("thinking", record["thinking"])
            sidecar.setdefault("steps", [])
            sidecar.pop("stage", None)
            sidecar.update({"status": "skipped", "scorable": False, "skip": record, "marked_on_resume": True})
            _fsync_write(path, (json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
        elif action["kind"] == "restore_snapshot":
            final = out_dir / action["path"]
            restored = (out_dir / action["from"]).read_bytes() if action["from"] else None
            _keep_copy(out_dir, session_dir, action["path"])
            if restored is not None:
                _fsync_write(final, restored)
            elif final.exists():
                final.unlink()
            for relative in action["quarantine"]:
                if relative != action["path"]:
                    _move(out_dir, session_dir, relative)
        else:
            raise _stop(f"resume_unknown_action:{action['kind']}")
    record = {"at": at, **describe(plan)}
    log = out_dir / RESUME_LOG
    with log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    _fsync_write(session_dir / "plan.json", (json.dumps(record, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    return record
