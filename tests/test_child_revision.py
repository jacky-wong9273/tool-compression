"""Blinded source packets. No review and no provider call."""

import json
from hashlib import sha256
from pathlib import Path

import pytest

from tool_compression.__main__ import main
from tool_compression.amendment_x2 import value_at
from tool_compression.child_revision import (
    ACCEPTED_SAMPLE_SIZE,
    BANNED_PACKET_KEYS,
    GET_ANGLES_FINAL,
    PROTOCOL_SHA256,
    check,
)

ROOT = Path(__file__).resolve().parents[1]
CHILD = ROOT / "docs" / "child-revision-evidence-ownership"


def test_protocol_is_the_predeclared_text():
    text = (CHILD / "PROTOCOL.md").read_text(encoding="utf-8")
    assert sha256(text.encode("utf-8")).hexdigest() == PROTOCOL_SHA256
    assert "The sample size is 24" in text
    assert "o200k_base" in text
    assert "Character length is not the score." in text
    assert "no model is a judge or editor" in text


def test_live_flag_is_rejected():
    with pytest.raises(SystemExit) as caught:
        main(["child-revision", "--check", "--live"])
    assert caught.value.code != 0


def test_child_sources_do_not_call_a_provider():
    text = (ROOT / "src" / "tool_compression" / "child_revision.py").read_text(encoding="utf-8")
    for banned in (
        "DEEPSEEK_API_KEY",
        "OPENAI_API_KEY",
        "urlopen",
        "import tool_compression.official_840_provider",
        "import tool_compression.usx_provider",
        "--live",
    ):
        assert banned not in text


def _keys(node) -> set[str]:
    found = set()
    if isinstance(node, dict):
        found.update(node)
        for value in node.values():
            found.update(_keys(value))
    elif isinstance(node, list):
        for value in node:
            found.update(_keys(value))
    return found


def test_frozen_child_revision_matches():
    status = check()
    assert status["passed"] is True
    assert status["rendered_catalogue_bytes_changed_versus_9154b8b"] is False
    assert status["review_conducted"] is False
    assert status["accepted_sample_size"] == ACCEPTED_SAMPLE_SIZE
    assert status["network_access"] == "denied"
    sample = (CHILD / "packets" / "accepted-edit-sample.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(sample) == ACCEPTED_SAMPLE_SIZE
    for relative in (
        "packets/accepted-edit-sample.jsonl",
        "packets/retained-nontrivial-contexts.jsonl",
        "packets/uncued-multi-tool-targets.jsonl",
    ):
        raw = (CHILD / relative).read_text(encoding="utf-8")
        assert "Unlike " not in raw
        assert GET_ANGLES_FINAL not in raw
        for line in raw.splitlines():
            assert BANNED_PACKET_KEYS.isdisjoint(_keys(json.loads(line)))
    exposure = json.loads((CHILD / "exposure-index.json").read_text(encoding="utf-8"))
    assert exposure["review_conducted"] is False
    assert BANNED_PACKET_KEYS.isdisjoint(_keys(exposure))
    flagged = {row["case_id"] for row in exposure["cases"]}
    for case_id in ("multiple_11", "multiple_12", "multiple_34", "multiple_35", "multiple_0"):
        assert case_id in flagged
    for line in sample:
        row = json.loads(line)
        assert value_at(row["original_tool"], row["pointer"]) == row["original_field"]
