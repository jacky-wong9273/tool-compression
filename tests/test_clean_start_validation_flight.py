"""The interrupted 0bf829c6 validation flight: archived evidence, digests, and the paired report."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import io
import json
import os
import subprocess
import sys
import tarfile

import pytest

from tool_compression.clean_start.pilot import study_dir
from tool_compression.clean_start.report import (
    VALIDATION_DIGEST,
    VALIDATION_EVIDENCE,
    VALIDATION_POPULATION,
    VALIDATION_TIP,
    write_validation_flight_report,
)

REPO = Path(__file__).resolve().parents[1]
PACKAGE = study_dir() / "package"
EVIDENCE = study_dir() / VALIDATION_EVIDENCE


def test_validation_evidence_is_byte_identical_to_its_checksums():
    lines = (EVIDENCE / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1498
    for line in lines:
        digest, relative = line.split("  ", 1)
        assert sha256((EVIDENCE / "original" / relative).read_bytes()).hexdigest() == digest, relative
    listed = {line.split("  ", 1)[1].removeprefix("./") for line in lines}
    present = {str(path.relative_to(EVIDENCE / "original")) for path in (EVIDENCE / "original").rglob("*") if path.is_file()}
    assert present == listed
    final = json.loads((EVIDENCE / "original/FINAL-0bf829c6.json").read_text(encoding="utf-8"))
    assert final["tip"] == VALIDATION_TIP
    assert final["official_settlement"] is False
    assert final["retry_or_resume"] is False
    assert (final["scoring_finished"], final["prerequisite_finished"]) == (1214, 20)


def test_validation_report_regenerates_from_the_archived_evidence(tmp_path):
    out = tmp_path / "validation.json"
    summary = write_validation_flight_report(EVIDENCE, out)
    assert out.read_bytes() == (PACKAGE / "validation_2026_11_25_analysis.json").read_bytes()
    assert summary == {
        "sent": 2482,
        "sent_matching_flown_digest": 2482,
        "matched_cases": 303,
        "matched_correct": {"U": 250, "S": 250, "X": 248, "SX": 252},
        "discordant_cases": 19,
        "uncertain_attempts": [2482],
    }
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["official_settlement"] is False
    assert "exposed" in report["exposure"]
    assert report["source"]["ledger_usd"] == "0.346230789000"
    assert report["source"]["billed_responses"] == 2481
    assert report["memory_coverage"]["memory_kv"]["matched_all_arms"] == 2
    first = report["tokens"]["first_request"]
    assert first["prompt_tokens"] == {"U": 332874, "S": 320284, "X": 334037, "SX": 321253}
    assert report["runner"]["forced_quit_slots"] == [{"case_id": "multi_turn_miss_func_9", "arm": "S", "steps": 26}]
    by_category = report["accuracy"]["matched_correct_by_category"]
    assert by_category["live_irrelevance"] == {"matched": 64, "U": 54, "S": 54, "X": 50, "SX": 53}


def test_x_losses_on_live_irrelevance_sent_the_u_bytes():
    report = json.loads((PACKAGE / "validation_2026_11_25_analysis.json").read_text(encoding="utf-8"))
    x_only_losses = [
        row for row in report["accuracy"]["discordant_cases"]
        if row["category"] == "live_irrelevance" and row["passed"]["U"] and not row["passed"]["X"]
    ]
    assert len(x_only_losses) == 4
    assert all(row["identical_sent_tools"]["X=U"] for row in x_only_losses)
    assert not any(row["pair"] == "X-U" and row["category"] == "live_irrelevance"
                   for row in report["different_tools_discordance"])


def _commit_available(commit: str) -> bool:
    try:
        subprocess.run(["git", "-C", str(REPO), "cat-file", "-e", f"{commit}^{{commit}}"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    return True


@pytest.mark.skipif(not _commit_available(VALIDATION_TIP), reason="flown tip not in local history (shallow checkout)")
@pytest.mark.parametrize("mode, committed", [("validation", VALIDATION_DIGEST), ("population", VALIDATION_POPULATION)])
def test_flown_validation_digests_reproduce_from_the_flown_commit(tmp_path, mode, committed):
    archive = subprocess.run(
        ["git", "-C", str(REPO), "archive", "--format=tar", VALIDATION_TIP, "src",
         "studies/clean-start-usx/bfcl", "studies/clean-start-usx/scope.json",
         "studies/clean-start-usx/pilot/draw.json", "studies/clean-start-usx/validation/draw.json"],
        check=True, capture_output=True,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(tmp_path, filter="data")
    env = {key: value for key, value in os.environ.items() if not key.endswith("_API_KEY")}
    env["PYTHONPATH"] = str(tmp_path / "src")
    out = subprocess.run(
        [sys.executable, str(REPO / "scripts/clean_start_sent_digest.py"), mode],
        check=True, capture_output=True, env=env, cwd=tmp_path,
    ).stdout
    payload = json.loads(out)
    payload["source_commit"] = VALIDATION_TIP
    assert payload == json.loads((EVIDENCE / committed).read_text(encoding="utf-8"))
