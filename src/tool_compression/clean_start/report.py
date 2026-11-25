"""Paired analysis of the archived 2026-11-25 thinking-off pilot. No new calls.

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
import subprocess

from tool_compression.adapter import description_slots
from tool_compression.clean_start.categories import is_trajectory
from tool_compression.clean_start.pilot import study_dir
from tool_compression.clean_start.pin import ARMS, OFFICIAL_SETTLEMENT, STUDY_ID
from tool_compression.config import LOCAL_TOKENIZER
from tool_compression.count import TiktokenCounter, dump_request

PILOT_EVIDENCE = Path("evidence") / "pilot-2026-11-25-thinking-off"
PILOT_TIP = "0c0284d5c3ca76d77b11a4db304d46953844ec66"
SENT_DIGEST = "sent_renders_0c0284d.json"
RESCORED = "rescored-underscore-to-dot"
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
        },
        "measurement_notes": [
            "No request was sent for this report. Every number comes from the archived evidence or local counting.",
            "provider_* fields are provider-billed usage; sent_local_* and revised_local_* are tiktoken o200k_base counts.",
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
