"""Saved-output joins for the follow-on package. No generation and no network.

Historical U/L/E answers stay on the closed flight. A saved answer may be
shared only when the case, replicate, and request hash all match.
"""

from __future__ import annotations

import json
from pathlib import Path

from tool_compression.official_score import locked_settlement_issues

HISTORICAL_CONDITIONS = frozenset({"U", "L", "E", "P", "I", "C"})
FOLLOWON_CONDITIONS = frozenset({"T1", "T2"})
JOIN_KEYS = ("case_id", "replicate", "condition", "request_group")


class ArchivedAnswerRefused(RuntimeError):
    """A saved answer does not belong on this request."""


class FollowOnJoinError(RuntimeError):
    def __init__(self, issues: list[str]):
        self.issues = issues
        super().__init__("; ".join(issues[:8]))


def bind_saved_answer(
    *,
    archived_condition: str,
    archived_case: str,
    archived_replicate: str,
    archived_request_hash: str,
    target_condition: str,
    target_case: str,
    target_replicate: str,
    target_request_hash: str,
) -> dict:
    """Return a bind record or raise. This does not read a response body."""
    if archived_condition in HISTORICAL_CONDITIONS and target_condition in FOLLOWON_CONDITIONS:
        raise ArchivedAnswerRefused(
            "An archived model answer cannot be assigned to a T1 or T2 request."
        )
    if archived_condition in FOLLOWON_CONDITIONS and target_condition in HISTORICAL_CONDITIONS:
        raise ArchivedAnswerRefused(
            "A follow-on answer cannot be assigned to a historical condition."
        )
    if archived_case != target_case or archived_replicate != target_replicate:
        raise ArchivedAnswerRefused(
            "A saved answer cannot move across cases or independent flights."
        )
    if archived_request_hash != target_request_hash:
        raise ArchivedAnswerRefused("A saved answer cannot be assigned to a changed request.")
    return {
        "bound": True,
        "shared_request": archived_condition != target_condition,
        "case_id": target_case,
        "replicate": target_replicate,
        "condition": target_condition,
        "request_hash": target_request_hash,
    }


def join_followon_records(rows: list[dict], expected: list[tuple] | None = None) -> dict:
    """Fail on duplicate, missing, or hash-mismatched join rows."""
    issues: list[str] = []
    seen: dict[tuple, dict] = {}
    for index, row in enumerate(rows):
        missing = [key for key in (*JOIN_KEYS, "request_hash") if key not in row]
        if missing:
            issues.append(f"row {index} missing {', '.join(missing)}")
            continue
        identity = tuple(row[key] for key in JOIN_KEYS)
        if identity in seen:
            issues.append(f"duplicate {identity}")
            continue
        verified = row.get("verified_request_hash")
        if verified is not None and verified != row["request_hash"]:
            issues.append(f"mismatched request hash for {identity}")
            continue
        seen[identity] = row
    if expected is not None:
        missing_keys = [key for key in expected if key not in seen]
        if missing_keys:
            issues.append(f"missing {len(missing_keys)} records")
    if issues:
        raise FollowOnJoinError(issues)
    return {"records": len(seen), "issues": []}


def reproduce_historical_official_counts(root: Path) -> dict:
    """Recompute the locked U/L/E counts from the committed settlement.

    The function reads local files only. It does not open a socket, and it
    does not treat the closed target as a reset test for T1 or T2.
    """
    path = Path(root) / "official" / "settlement" / "official_settlement.json"
    settlement = json.loads(path.read_text(encoding="utf-8"))
    issues = locked_settlement_issues(settlement)
    categories = {}
    for name, block in settlement["categories"].items():
        categories[name] = {
            "n": block["denominator"],
            "correct": {arm: block["accuracy"][arm]["correct"] for arm in ("U", "L", "E")},
            "provider_input_sum": {
                arm: block["provider_total_input"][arm]["sum"] for arm in ("U", "L", "E")
            },
            "saving_numerator_L_vs_U": block["S_LU"]["ratio_numerator"],
            "saving_denominator_L_vs_U": block["S_LU"]["ratio_denominator"],
        }
    reference = settlement["reference_target_L_represents_C"]["combine_targets"]
    return {
        "network_used": False,
        "source": "official/settlement/official_settlement.json",
        "issues": issues,
        "ok": not issues,
        "target_reached": reference["target_reached"],
        "target_lowered": reference["target_lowered"],
        "target_is_reset_test_for_followon": False,
        "scoring_alias": "DeepSeek-V3.2-Exp-FC",
        "scoring_alias_may_generate": False,
        "categories": categories,
    }
