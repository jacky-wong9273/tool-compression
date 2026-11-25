"""Paired analyses of the archived 2026-11-25 thinking-off pilots. No new calls.

``write_pilot_report`` reads the first flight (editors at ``PILOT_TIP``) and
``write_revised_pilot_report`` the second (editors at ``REVISED_TIP``).
Inputs are the unmodified evidence (bills, sidecars, archived official scores),
the official rescoring of the same result files with the pinned DeepSeek FC
name mapping, and a digest of the tool arrays the pilot sent (the frozen renders
at its tip). Three token measures are kept apart: local description-field
tokens, local tools-array tokens, and provider-billed prompt tokens, which also
carry the chat template, the messages, and prefix-cache state.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from pathlib import Path
import json
import re
import subprocess

from tool_compression.adapter import description_slots
from tool_compression.clean_start.categories import is_trajectory
from tool_compression.clean_start.editor_s import S_RULES_VERSION
from tool_compression.clean_start.editor_x import X_RULES_VERSION
from tool_compression.clean_start.pilot import study_dir
from tool_compression.clean_start.pin import ARMS, OFFICIAL_SETTLEMENT, STUDY_ID
from tool_compression.config import LOCAL_TOKENIZER
from tool_compression.count import TiktokenCounter, dump_request

PILOT_EVIDENCE = Path("evidence") / "pilot-2026-11-25-thinking-off"
PILOT_TIP = "0c0284d5c3ca76d77b11a4db304d46953844ec66"
SENT_DIGEST = "sent_renders_0c0284d.json"
RESCORED = "rescored-underscore-to-dot"
REVISED_EVIDENCE = Path("evidence") / "pilot-2026-11-25-revised-c47b186c"
REVISED_TIP = "c47b186c6004e69840db3537ebe532dc22f638a8"
REVISED_DIGEST = "sent_renders_c47b186c.json"
REVISED_POPULATION = "population_c47b186c.json"
REVISED_RUN = Path("original") / "live-c47b186c"
PAIRS = (("S", "U"), ("X", "U"), ("SX", "S"), ("SX", "X"), ("SX", "U"))


def render_digest(documents: dict[str, dict], counter) -> dict:
    """Per case and arm: tools hash, local field tokens, local tools tokens, edited slots."""
    digest = {}
    for case_id, document in sorted(documents.items()):
        arms = document["arms"]
        base = arms["U"]
        rows = {}
        for arm in ARMS:
            tools = arms[arm]
            texts = [container[key] for tool in tools for _p, container, key in description_slots(tool)]
            base_texts = [container[key] for tool in base for _p, container, key in description_slots(tool)]
            rows[arm] = {
                "tools_sha256": __import__("hashlib").sha256(dump_request(tools).encode("utf-8")).hexdigest(),
                "field_tokens": sum(counter.count(text) for text in texts),
                "tools_tokens": counter.count(dump_request(tools)),
                "slots_differing_from_u": sum(1 for left, right in zip(texts, base_texts) if left != right),
            }
        digest[case_id] = {"category": document["category"], "arms": rows}
    return digest


def sent_digest_from_git(commit: str = PILOT_TIP) -> dict:
    """Rebuild the sent-render digest from the frozen renders at the pilot tip."""
    root = study_dir()
    repo = root.parents[1]
    draw = json.loads(_git_show(repo, commit, "studies/clean-start-usx/pilot/draw.json"))
    documents = {}
    for row in draw["rows"]:
        path = f"studies/clean-start-usx/pilot/rendered/{row['category']}/{row['case_id']}.json"
        documents[row["case_id"]] = json.loads(_git_show(repo, commit, path))
    counter = TiktokenCounter(LOCAL_TOKENIZER)
    return {
        "source_commit": commit,
        "tokenizer": LOCAL_TOKENIZER,
        "cases": render_digest(documents, counter),
    }


def current_digest() -> dict:
    root = study_dir() / "pilot" / "rendered"
    documents = {path.stem: json.loads(path.read_text(encoding="utf-8")) for path in root.rglob("*.json")}
    return render_digest(documents, TiktokenCounter(LOCAL_TOKENIZER))


def _archived_cases_removed_from_the_draw(sent: dict, on_disk: dict) -> dict:
    """Revised-editor counts for archived pilot cases the current draw no longer freezes.

    The 25 Nov evidence still names the web-search cases. They are rendered here
    and not written back into ``pilot/rendered``.
    """
    from tool_compression.clean_start.load import load_questions
    from tool_compression.clean_start.pilot import render_document

    missing: dict[str, list[str]] = defaultdict(list)
    for case_id, digest in sent.items():
        if case_id not in on_disk:
            missing[digest["category"]].append(case_id)
    documents = {}
    for category, ids in missing.items():
        wanted = set(ids)
        for case in load_questions(category):
            if case["id"] in wanted:
                documents[case["id"]] = render_document(case)
        absent = wanted - set(documents)
        if absent:
            raise RuntimeError(f"archived pilot cases are not in the vendored prompts: {sorted(absent)}")
    if not documents:
        return {}
    return render_digest(documents, TiktokenCounter(LOCAL_TOKENIZER))


def _git_show(repo: Path, commit: str, path: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "show", f"{commit}:{path}"],
        check=True, capture_output=True, text=True,
    ).stdout


def _scores(score_root: Path) -> dict:
    """category -> arm -> {"correct": n, "total": n, "failed_ids": [...]}"""
    table: dict = defaultdict(dict)
    for path in sorted(score_root.glob("deepseek-flash-thinking-off-*/**/*_score.json")):
        arm = path.relative_to(score_root).parts[0].rsplit("-", 1)[1]
        category = path.name[len("BFCL_v4_"):-len("_score.json")]
        lines = path.read_text(encoding="utf-8").splitlines()
        header = json.loads(lines[0])
        failed = sorted(json.loads(line)["id"] for line in lines[1:] if line.strip())
        table[category][arm] = {
            "correct": header["correct_count"],
            "total": header["total_count"],
            "failed_ids": failed,
        }
    return dict(table)


def _scored_ids(result_root: Path) -> dict:
    ids: dict = defaultdict(dict)
    for path in sorted(result_root.glob("deepseek-flash-thinking-off-*/**/*_result.json")):
        arm = path.relative_to(result_root).parts[0].rsplit("-", 1)[1]
        category = path.name[len("BFCL_v4_"):-len("_result.json")]
        ids[category][arm] = sorted(json.loads(line)["id"] for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return dict(ids)


def _discordance(scores: dict, scored: dict) -> dict:
    """Per arm pair, over cases both arms finished: both right, left only, right only, both wrong."""
    out = {}
    for left, right in PAIRS:
        counts = {"both_correct": 0, "left_only": 0, "right_only": 0, "both_wrong": 0, "cases": 0}
        for category, arms in scored.items():
            if left not in arms or right not in arms:
                continue
            common = set(arms[left]) & set(arms[right])
            failed_left = set(scores.get(category, {}).get(left, {}).get("failed_ids", []))
            failed_right = set(scores.get(category, {}).get(right, {}).get("failed_ids", []))
            for case_id in common:
                ok_left, ok_right = case_id not in failed_left, case_id not in failed_right
                counts["cases"] += 1
                key = "both_correct" if ok_left and ok_right else "left_only" if ok_left else "right_only" if ok_right else "both_wrong"
                counts[key] += 1
        out[f"{left}-{right}"] = counts
    return out


def _bills(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_pilot_report(evidence: Path, out: Path) -> dict:
    evidence = Path(evidence)
    original = evidence / "original" / "artifacts"
    bills = _bills(original / "bills.jsonl")
    sent = json.loads((evidence / SENT_DIGEST).read_text(encoding="utf-8"))["cases"]
    now = current_digest()
    now.update(_archived_cases_removed_from_the_draw(sent, now))
    by_slot: dict = defaultdict(list)
    order: dict = defaultdict(list)
    for row in bills:
        by_slot[(row["case_id"], row["arm"])].append(row)
        if row["arm"] not in order[row["case_id"]]:
            order[row["case_id"]].append(row["arm"])
    sidecars = {}
    for path in (original / "model_outputs").rglob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        sidecars[(data["case_id"], data["arm"])] = data

    single_cases = []
    trajectory_cases = []
    for case_id, digest in sent.items():
        category = digest["category"]
        arms = {}
        for arm in ARMS:
            rows = by_slot.get((case_id, arm), [])
            sidecar = sidecars.get((case_id, arm))
            arms[arm] = {
                "requests_billed": len(rows),
                "finished": bool(sidecar and sidecar.get("scorable")),
                "provider_prompt_tokens": sum(row["prompt_tokens"] for row in rows),
                "provider_cache_hit_tokens": sum(row["prompt_cache_hit_tokens"] for row in rows),
                "provider_cache_miss_tokens": sum(row["prompt_cache_miss_tokens"] for row in rows),
                "provider_output_tokens": sum(row["output_tokens"] for row in rows),
                "usd": str(sum((Decimal(row["usd"]) for row in rows), Decimal("0"))),
                "sent_tools_sha256": digest["arms"][arm]["tools_sha256"],
                "sent_local_field_tokens": digest["arms"][arm]["field_tokens"],
                "sent_local_tools_tokens": digest["arms"][arm]["tools_tokens"],
                "sent_slots_differing_from_u": digest["arms"][arm]["slots_differing_from_u"],
                "revised_local_field_tokens": now[case_id]["arms"][arm]["field_tokens"],
                "revised_local_tools_tokens": now[case_id]["arms"][arm]["tools_tokens"],
                "revised_slots_differing_from_u": now[case_id]["arms"][arm]["slots_differing_from_u"],
            }
            if sidecar and is_trajectory(category):
                arms[arm]["steps_per_turn"] = _steps_per_turn(sidecar)
        record = {
            "case_id": case_id,
            "category": category,
            "send_order": order.get(case_id, []),
            "sent_identical_tools": {
                f"{left}={right}": digest["arms"][left]["tools_sha256"] == digest["arms"][right]["tools_sha256"]
                for left, right in PAIRS
            },
            "arms": arms,
        }
        if not order.get(case_id):
            record["not_sent"] = True
        (trajectory_cases if is_trajectory(category) else single_cases).append(record)

    sent_single = [case for case in single_cases if not case.get("not_sent")]
    paired = {}
    for left, right in PAIRS:
        rows = [
            case for case in sent_single
            if case["arms"][left]["finished"] and case["arms"][right]["finished"]
        ]
        identical = [case for case in rows if case["sent_identical_tools"][f"{left}={right}"]]
        differing = [case for case in rows if not case["sent_identical_tools"][f"{left}={right}"]]
        paired[f"{left}-{right}"] = {
            "cases": len(rows),
            "cases_with_identical_sent_tools": len(identical),
            "provider_prompt_delta_all": _delta(rows, left, right, "provider_prompt_tokens"),
            "provider_prompt_delta_where_tools_differ": _delta(differing, left, right, "provider_prompt_tokens"),
            "provider_prompt_delta_where_tools_identical": _delta(identical, left, right, "provider_prompt_tokens"),
            "local_tools_delta_where_tools_differ": _delta(differing, left, right, "sent_local_tools_tokens"),
            "local_field_delta_where_tools_differ": _delta(differing, left, right, "sent_local_field_tokens"),
            "provider_output_delta_all": _delta(rows, left, right, "provider_output_tokens"),
            "provider_cache_miss_delta_all": _delta(rows, left, right, "provider_cache_miss_tokens"),
            "usd_delta_all": str(sum(
                (Decimal(case["arms"][left]["usd"]) - Decimal(case["arms"][right]["usd"]) for case in rows),
                Decimal("0"),
            )),
            "revised_local_tools_delta_same_cases": _delta(rows, left, right, "revised_local_tools_tokens"),
            "revised_local_field_delta_same_cases": _delta(rows, left, right, "revised_local_field_tokens"),
        }
    position = defaultdict(lambda: {"requests": 0, "prompt": 0, "hit": 0, "miss": 0})
    for case in sent_single:
        for index, arm in enumerate(case["send_order"]):
            stats = position[index + 1]
            stats["requests"] += case["arms"][arm]["requests_billed"]
            stats["prompt"] += case["arms"][arm]["provider_prompt_tokens"]
            stats["hit"] += case["arms"][arm]["provider_cache_hit_tokens"]
            stats["miss"] += case["arms"][arm]["provider_cache_miss_tokens"]
    for stats in position.values():
        stats["hit_share"] = round(stats["hit"] / stats["prompt"], 4) if stats["prompt"] else None

    archived = _scores(original / "score")
    rescored_root = evidence / RESCORED / "score"
    rescored = _scores(rescored_root) if rescored_root.is_dir() else {}
    scored_ids = _scored_ids(original / "result")
    revised_totals = {
        arm: {
            "field_tokens": sum(now[case_id]["arms"][arm]["field_tokens"] for case_id in now),
            "tools_tokens": sum(now[case_id]["arms"][arm]["tools_tokens"] for case_id in now),
        }
        for arm in ARMS
    }
    sent_totals = {
        arm: {
            "field_tokens": sum(sent[case_id]["arms"][arm]["field_tokens"] for case_id in sent),
            "tools_tokens": sum(sent[case_id]["arms"][arm]["tools_tokens"] for case_id in sent),
        }
        for arm in ARMS
    }
    report = {
        "study": STUDY_ID,
        "official_settlement": OFFICIAL_SETTLEMENT,
        "source": {
            "evidence": str(PILOT_EVIDENCE),
            "pilot_tip": PILOT_TIP,
            "bills": len(bills),
            "thinking": "off",
            "band": sorted({row["band"] for row in bills}),
            "revised_editor_rules": {"S": S_RULES_VERSION, "X": X_RULES_VERSION},
        },
        "measurement_notes": [
            "No request was sent for this report. Every number comes from the archived evidence or local counting.",
            "provider_* fields are provider-billed usage; sent_local_* and revised_local_* are tiktoken o200k_base counts.",
            "revised_* fields count what the editors at source.revised_editor_rules would send for the same cases.",
            "Arms were sent in fixed U, S, X, SX order inside each case, so later arms inherit the provider prefix cache. "
            "USD and cache-miss deltas are confounded by send position and are not editor effects.",
            "Trajectory slots differ in step counts between arms; their token totals mix description effects with "
            "different model behaviour and are reported per arm, not as a saving.",
            "Accuracy n is tiny (2-3 cases per category, 20-22 scored per arm); differences of one case are not evidence.",
            "archived_official_scores used underscore_to_dot=False, unlike the pinned DeepSeek FC entry; "
            "rescored_official_scores rescore the same result files with underscore_to_dot=True.",
        ],
        "single_turn": {"cases": single_cases, "paired": paired, "cache_by_send_position": dict(sorted(position.items()))},
        "trajectory": trajectory_cases,
        "accuracy": {
            "archived_official_scores": archived,
            "rescored_official_scores": rescored,
            "rescored_paired_discordance": _discordance(rescored, scored_ids) if rescored else None,
        },
        "local_tokens_pilot_47": {
            "as_sent_editors_at_pilot_tip": sent_totals,
            "revised_editors": revised_totals,
        },
        "billed_totals_by_arm": {
            arm: {
                "requests": sum(1 for row in bills if row["arm"] == arm),
                "prompt": sum(row["prompt_tokens"] for row in bills if row["arm"] == arm),
                "cache_hit": sum(row["prompt_cache_hit_tokens"] for row in bills if row["arm"] == arm),
                "cache_miss": sum(row["prompt_cache_miss_tokens"] for row in bills if row["arm"] == arm),
                "output": sum(row["output_tokens"] for row in bills if row["arm"] == arm),
                "usd": str(sum((Decimal(row["usd"]) for row in bills if row["arm"] == arm), Decimal("0"))),
            }
            for arm in ARMS
        },
    }
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "single_turn_cases_sent": len(sent_single),
        "trajectory_cases": len(trajectory_cases),
        "paired_identical_S_U": paired["S-U"]["cases_with_identical_sent_tools"],
        "paired_identical_X_U": paired["X-U"]["cases_with_identical_sent_tools"],
    }


def _delta(rows: list[dict], left: str, right: str, field: str) -> dict:
    values = [case["arms"][left][field] - case["arms"][right][field] for case in rows]
    return {"n": len(values), "sum": sum(values), "min": min(values) if values else None, "max": max(values) if values else None}


def _steps_per_turn(sidecar: dict) -> list[int]:
    counts: dict[int, int] = defaultdict(int)
    for step in sidecar.get("steps", []):
        counts[int(step.get("turn", 0))] += 1
    return [counts[turn] for turn in sorted(counts)]


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _behaviour(sidecar: dict) -> list:
    """What the scorer can see: executed calls per step for trajectories, the decoded result otherwise."""
    steps = sidecar.get("steps", [])
    if any("executed" in step for step in steps):
        return [[step.get("turn"), step.get("executed") or []] for step in steps]
    return [sidecar.get("result")]


def _usd_parts(rows: list[dict]) -> dict:
    from tool_compression.clean_start.rate_card import OFF_PEAK_PER_MILLION, PEAK_PER_MILLION

    parts = {"cache_hit": Decimal("0"), "cache_miss": Decimal("0"), "output": Decimal("0")}
    for row in rows:
        prices = PEAK_PER_MILLION if row["band"] == "peak" else OFF_PEAK_PER_MILLION
        parts["cache_hit"] += Decimal(row["prompt_cache_hit_tokens"]) * prices["cache_hit"] / 1_000_000
        parts["cache_miss"] += Decimal(row["prompt_cache_miss_tokens"]) * prices["cache_miss"] / 1_000_000
        parts["output"] += Decimal(row["output_tokens"]) * prices["output"] / 1_000_000
    return {key: str(value.quantize(Decimal("0.000000000001"))) for key, value in parts.items()}


def write_revised_pilot_report(evidence: Path, out: Path) -> dict:
    """Paired analysis of the 25 Nov thinking-off flight of the editors at ``REVISED_TIP``.

    Reads only the archived evidence, the committed digest of the tools the
    flown commit sends, and the current editors (for revised local token counts).
    """
    from tool_compression.clean_start.__main__ import _select_cases
    from tool_compression.clean_start.runner import arm_tools

    evidence = Path(evidence)
    run_dir = evidence / REVISED_RUN
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    attempts = _jsonl(run_dir / "attempts.jsonl")
    bills = _bills(run_dir / "bills.jsonl")
    digest = json.loads((evidence / REVISED_DIGEST).read_text(encoding="utf-8"))
    if digest["source_commit"] != REVISED_TIP:
        raise ValueError(f"{REVISED_DIGEST} was not computed at {REVISED_TIP}")
    flown_rules = json.loads((evidence / REVISED_POPULATION).read_text(encoding="utf-8"))["rules"]
    sidecars = {}
    for path in sorted((run_dir / "model_outputs").rglob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        sidecars[(data["case_id"], data["arm"])] = data
    scores = _scores(run_dir / "score")
    scored = _scored_ids(run_dir / "result")

    sent = [row for row in attempts if row["event"] == "sent"]
    state_of = {}
    for case_id, record in digest["cases"].items():
        for state, arms in record["states"].items():
            for arm, row in arms.items():
                state_of[(case_id, arm, row["tools_sha256"])] = state
    matched_states = defaultdict(int)
    unmatched = []
    for row in sent:
        state = state_of.get((row["case_id"], row["arm"], row["tools_sha256"]))
        if state is None:
            unmatched.append(row["attempt"])
        else:
            matched_states[state.split(":")[0]] += 1

    failed = {}
    for category, arms in scores.items():
        for arm, table in arms.items():
            for case_id in table["failed_ids"]:
                failed[(case_id, arm)] = True
    matched_cases = sorted(
        case_id
        for category, arms in scored.items()
        if not category.endswith("_prereq")
        for case_id in set.intersection(*(set(arms.get(arm, [])) for arm in ARMS))
    )
    category_of = {case_id: record["category"] for case_id, record in digest["cases"].items()}
    outcome = {(case_id, arm): not failed.get((case_id, arm), False) for case_id in matched_cases for arm in ARMS}

    def identical_tools(case_id: str, left: str, right: str) -> bool:
        states = digest["cases"][case_id]["states"].values()
        return all(arms[left]["tools_sha256"] == arms[right]["tools_sha256"] for arms in states)

    discordant = []
    for case_id in matched_cases:
        passed = {arm: outcome[(case_id, arm)] for arm in ARMS}
        if len(set(passed.values())) > 1:
            discordant.append({
                "case_id": case_id,
                "category": category_of[case_id],
                "passed": passed,
                "identical_sent_tools": {
                    f"{left}={right}": identical_tools(case_id, left, right) for left, right in PAIRS
                },
            })

    noise = {"trajectory": defaultdict(int), "single_turn": defaultdict(int)}
    for case_id in matched_cases:
        kind = "trajectory" if is_trajectory(category_of[case_id]) else "single_turn"
        for left, right in (("U", "X"), ("S", "SX"), ("U", "S"), ("X", "SX")):
            if not identical_tools(case_id, left, right):
                continue
            stats = noise[kind]
            stats["pairs_with_identical_sent_tools"] += 1
            same = _behaviour(sidecars[(case_id, left)]) == _behaviour(sidecars[(case_id, right)])
            stats["identical_model_behaviour"] += int(same)
            stats["outcome_differs"] += int(outcome[(case_id, left)] != outcome[(case_id, right)])

    matched_bills = [row for row in bills if row["case_id"] in set(matched_cases)]
    billed = {}
    for arm in ARMS:
        rows = [row for row in matched_bills if row["arm"] == arm]
        billed[arm] = {
            "requests": len(rows),
            "prompt": sum(row["prompt_tokens"] for row in rows),
            "cache_hit": sum(row["prompt_cache_hit_tokens"] for row in rows),
            "cache_miss": sum(row["prompt_cache_miss_tokens"] for row in rows),
            "output": sum(row["output_tokens"] for row in rows),
            "usd": str(sum((Decimal(row["usd"]) for row in rows), Decimal("0"))),
            "usd_parts": _usd_parts(rows),
            "correct": sum(int(outcome[(case_id, arm)]) for case_id in matched_cases),
        }
    first = {}
    order: dict = defaultdict(list)
    for row in sorted(matched_bills, key=lambda item: item["attempt"]):
        if row["turn"] == 0 and row["step"] == 0:
            first[(row["case_id"], row["arm"])] = row
            order[row["case_id"]].append(row["arm"])
    first_request = {"cases": len(matched_cases), "prompt_tokens": {}, "delta_vs_U": {}}
    for arm in ARMS:
        first_request["prompt_tokens"][arm] = sum(first[(case_id, arm)]["prompt_tokens"] for case_id in matched_cases)
    for arm in ("S", "X", "SX"):
        delta = first_request["prompt_tokens"][arm] - first_request["prompt_tokens"]["U"]
        first_request["delta_vs_U"][arm] = {
            "tokens": delta,
            "percent": round(100 * delta / first_request["prompt_tokens"]["U"], 3),
        }
    position = defaultdict(lambda: {"requests": 0, "prompt": 0, "cache_miss": 0})
    for case_id, arms in order.items():
        for index, arm in enumerate(arms):
            stats = position[index + 1]
            stats["requests"] += 1
            stats["prompt"] += first[(case_id, arm)]["prompt_tokens"]
            stats["cache_miss"] += first[(case_id, arm)]["prompt_cache_miss_tokens"]

    revised = {"scoring": defaultdict(int), "prereq": defaultdict(int)}
    flown = {"scoring": defaultdict(int), "prereq": defaultdict(int)}
    counter = TiktokenCounter(LOCAL_TOKENIZER)
    for case in _select_cases(True, "matched"):
        kind = "prereq" if case.get("prereq") else "scoring"
        for arm in ARMS:
            revised[kind][arm] += counter.count(dump_request(arm_tools(case["function"], case["category"], arm)))
            flown[kind][arm] += digest["cases"][case["id"]]["states"]["initial"][arm]["local_tools_tokens"]

    forced = [
        {"case_id": key[0], "arm": key[1], "steps": len(data.get("steps", []))}
        for key, data in sorted(sidecars.items())
        if data.get("forced_quit")
    ]
    partial = []
    for slot in run.get("partial_slots", []):
        group = run_dir / "result" / f"deepseek-flash-thinking-off-{slot['arm']}"
        rows = [row for path in group.rglob("*_result.json") for row in _jsonl(path)]
        partial.append({
            **slot,
            "sidecar_status": sidecars.get((slot["case_id"], slot["arm"]), {}).get("status"),
            "result_row_written": any(row["id"] == slot["case_id"] for row in rows),
        })
    snapshots = {}
    for arm in ARMS:
        root = run_dir / "result" / f"deepseek-flash-thinking-off-{arm}" / "agentic" / "memory"
        for final in sorted(root.rglob("memory_snapshot/*_final.json")):
            checkpoints = sorted(
                (final.parent / "prereq_checkpoints").glob("*.json"),
                key=lambda path: int(re.search(r"prereq_(\d+)", path.name).group(1)),
            )
            last = checkpoints[-1] if checkpoints else None
            snapshots[f"{arm}/{final.relative_to(root)}"] = {
                "checkpoints": [path.name for path in checkpoints],
                "final_equals_last_checkpoint": bool(last and json.loads(last.read_text(encoding="utf-8"))
                                                     == json.loads(final.read_text(encoding="utf-8"))),
            }

    report = {
        "study": STUDY_ID,
        "official_settlement": OFFICIAL_SETTLEMENT,
        "source": {
            "evidence": str(REVISED_EVIDENCE),
            "flown_tip": digest["source_commit"],
            "flown_rules": flown_rules,
            "current_editor_rules": {"S": S_RULES_VERSION, "X": X_RULES_VERSION},
            "status": run.get("status"),
            "reason": run.get("reason"),
            "provider_sends": len(sent),
            "billed_responses": len(bills),
            "uncertain_attempts": run.get("uncertain_attempts"),
            "running_usd": run.get("running_usd"),
            "thinking": "off",
            "band": sorted({row["band"] for row in bills}),
        },
        "measurement_notes": [
            "No request was sent for this report. Every number comes from the archived evidence or local counting.",
            "Arms were rotated per case, and arms with byte-identical tools (U and X, S and SX on most cases) share "
            "provider prefix cache, so cache-miss and USD differences between arms are confounded by send order.",
            "first_request compares turn 0 step 0 of each matched case. The runner builds identical messages for "
            "every arm, so the prompt-token difference there is the tools array as the provider tokenizes it.",
            "Accuracy covers 32 cases all four arms finished. A one-case difference is not evidence; "
            "identical_tools_noise shows how often arms sending byte-identical tools still behave differently.",
            "Accuracy is from the archived official scorer output (underscore_to_dot=True).",
            "identical_model_behaviour compares executed calls per step for trajectories (the multi-turn checker "
            "scores calls and state, not text) and the decoded result for single-turn cases.",
            "local_tools_tokens_initial_catalogue counts the tools array before any held-out turn: flown_editors "
            "from the digest of the flown commit, current_editors from source.current_editor_rules.",
        ],
        "sent_bytes": {
            "sent_attempts": len(sent),
            "matched_flown_digest": len(sent) - len(unmatched),
            "unmatched_attempts": unmatched,
            "matched_by_state": dict(sorted(matched_states.items())),
        },
        "accuracy": {
            "official_scores": scores,
            "matched_cases": len(matched_cases),
            "matched_correct": {arm: billed[arm]["correct"] for arm in ARMS},
            "paired_discordance": _discordance(scores, {
                category: {arm: [case for case in ids if case in set(matched_cases)] for arm, ids in arms.items()}
                for category, arms in scored.items()
            }),
            "discordant_cases": discordant,
        },
        "identical_tools_noise": {kind: dict(sorted(stats.items())) for kind, stats in noise.items()},
        "tokens": {
            "matched_billed_by_arm": billed,
            "first_request": first_request,
            "first_request_cache_by_send_position": dict(sorted(position.items())),
            "local_tools_tokens_initial_catalogue": {
                "flown_editors": {kind: dict(values) for kind, values in flown.items()},
                "current_editors": {kind: dict(values) for kind, values in revised.items()},
            },
        },
        "runner": {
            "forced_quit_slots": forced,
            "partial_slots": partial,
            "memory_snapshots": snapshots,
        },
    }
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "sent": len(sent),
        "sent_matching_flown_digest": len(sent) - len(unmatched),
        "matched_cases": len(matched_cases),
        "matched_correct": report["accuracy"]["matched_correct"],
        "discordant_cases": len(discordant),
    }
