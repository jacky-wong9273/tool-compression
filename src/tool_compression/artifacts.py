"""Artifact manifest for the 18–19 November flight and the recorded tables.

Historical machine paths are labels for where a file was written. They are
not portable defaults. A missing file keeps ``sha256`` null.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

SCHEMA = "tool-compression.artifact-manifest.v1"

IN_REPOSITORY = (
    {
        "id": "official_settlement",
        "role": "locked official U/L/E settlement",
        "path": "official/settlement/official_settlement.json",
    },
    {
        "id": "measurement_chain",
        "role": "recorded measurement-chain checks, including the handler alias",
        "path": "official/tables/measurement_chain.json",
    },
    {
        "id": "usage_accounting",
        "role": "recorded billed-basis and cache-associated input-cost tables",
        "path": "official/tables/usage_accounting.json",
    },
    {
        "id": "official_score_reproduction",
        "role": "recorded SHA-256 identity of the nine official score files",
        "path": "official/tables/official_score_reproduction.json",
    },
    {
        "id": "change_class_join",
        "role": "recorded join of change class, official outcomes, and primary T",
        "path": "official/tables/change_class_join.json",
    },
    {
        "id": "preprocessing_overhead",
        "role": "CPU-only per-condition preprocessing timing",
        "path": "official/tables/preprocessing_overhead.json",
    },
    {
        "id": "week1_characterization",
        "role": "historical Week 1 selected-input characterization",
        "path": "evidence/week1_characterization.json",
    },
    {
        "id": "week1_request_hashes",
        "role": "historical Week 1 request hashes",
        "path": "evidence/week1_request_hashes.jsonl",
    },
    {
        "id": "week1_arm_e",
        "role": "historical Week 1 Arm E packet",
        "path": "evidence/week1_arm_e.json",
    },
    {
        "id": "week1_evidence_packet",
        "role": "historical Week 1 evidence packet",
        "path": "evidence/WEEK1_EVIDENCE_PACKET.md",
    },
)

ABSENT = (
    {
        "id": "stage_b_requests",
        "role": "18 November flight request bodies",
        "expected_rows": 1513,
        "historical_path": "/workspace/tool-compression-flash-2026-11-18/artifacts/validation-flight/stage_b/requests.jsonl",
    },
    {
        "id": "stage_b_responses",
        "role": "18 November provider responses",
        "expected_rows": 1513,
        "historical_path": "/workspace/tool-compression-flash-2026-11-18/artifacts/validation-flight/stage_b/responses.jsonl",
    },
    {
        "id": "stage_b_parsed",
        "role": "18 November parsed model calls",
        "expected_rows": 1513,
        "historical_path": "/workspace/tool-compression-flash-2026-11-18/artifacts/validation-flight/stage_b/parsed.jsonl",
    },
    {
        "id": "stage_b_usage_ledger",
        "role": "18 November provider usage ledger",
        "historical_path": "/workspace/tool-compression-flash-2026-11-18/artifacts/validation-flight/stage_b/usage_ledger.json",
    },
    {
        "id": "stage_b_logical_ledger",
        "role": "18 November logical response ledger",
        "historical_path": "/workspace/tool-compression-flash-2026-11-18/artifacts/validation-flight/stage_b/logical_ledger.json",
    },
    {
        "id": "execution_record",
        "role": "frozen 18 November execution record",
        "historical_path": "/workspace/tool-compression-flash-2026-11-18/artifacts/validation-flight/execution_record.json",
    },
    {
        "id": "official_score_files",
        "role": "nine official BFCL score JSON files",
        "historical_path": "/home/box/cos/tool-compression-official-ule-2026-11-19/bfcl_project/score_{u,l,e}/DeepSeek-V3.2-Exp-FC/non_live/",
    },
    {
        "id": "official_result_files",
        "role": "mapped BFCL result JSONL trees",
        "historical_path": "/home/box/cos/tool-compression-official-ule-2026-11-19/bfcl_project/result_{u,l,e}/DeepSeek-V3.2-Exp-FC/",
    },
    {
        "id": "case_level_outcomes",
        "role": "840-row official outcome and provider-input table",
        "historical_path": "/home/box/cos/tool-compression-official-ule-2026-11-19/settlement/case_level_official_outcomes.jsonl",
    },
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(repo_root: Path) -> dict:
    root = Path(repo_root)
    artifacts = []
    for item in IN_REPOSITORY:
        path = root / item["path"]
        artifacts.append(
            {
                "id": item["id"],
                "role": item["role"],
                "in_repository": True,
                "path": item["path"],
                "sha256": sha256_file(path) if path.is_file() else None,
                "present": path.is_file(),
                "historical_path": None,
                "historical_path_portable": False,
            }
        )
    for item in ABSENT:
        artifacts.append(
            {
                "id": item["id"],
                "role": item["role"],
                "in_repository": False,
                "path": None,
                "sha256": None,
                "present": False,
                "expected_rows": item.get("expected_rows"),
                "historical_path": item["historical_path"],
                "historical_path_portable": False,
                "reason_absent": (
                    "The full 18 November flight trees and the official score "
                    "files are not in this repository. Digest left null."
                ),
            }
        )
    return {
        "schema": SCHEMA,
        "flight_collected": "2026-11-18",
        "officially_scored": "2026-11-19",
        "timezone": "Asia/Hong_Kong",
        "notes": (
            "Historical paths record where the 18–19 November files were written. "
            "They are not portable defaults. sha256 is null when the bytes are "
            "not in this checkout."
        ),
        "artifacts": artifacts,
    }


def verify_manifest(manifest: dict, repo_root: Path) -> list[str]:
    issues = []
    root = Path(repo_root)
    if manifest.get("schema") != SCHEMA:
        issues.append("schema")
    seen = set()
    for item in manifest["artifacts"]:
        if item["id"] in seen:
            issues.append(f"duplicate artifact {item['id']}")
        seen.add(item["id"])
        if item["historical_path_portable"] is not False:
            issues.append(f"{item['id']} marks a historical path as portable")
        if item["in_repository"]:
            path = root / item["path"]
            if not path.is_file():
                issues.append(f"{item['id']} is missing at {item['path']}")
                continue
            digest = sha256_file(path)
            if item.get("sha256") != digest:
                issues.append(f"{item['id']} sha256 does not match {item['path']}")
        else:
            if item.get("sha256") is not None:
                issues.append(f"{item['id']} has a digest but the bytes are not in the repository")
            if item.get("present") is not False:
                issues.append(f"{item['id']} is marked present")
            if not item.get("historical_path"):
                issues.append(f"{item['id']} is missing its historical path label")
    expected = {item["id"] for item in IN_REPOSITORY} | {item["id"] for item in ABSENT}
    if seen != expected:
        issues.append("manifest artifact ids do not match the package list")
    return issues


def write_manifest(path: Path, repo_root: Path) -> dict:
    payload = build_manifest(repo_root)
    Path(path).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload
