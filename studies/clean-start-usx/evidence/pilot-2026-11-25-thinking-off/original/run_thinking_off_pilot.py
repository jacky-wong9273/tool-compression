#!/usr/bin/env python3
"""Authorized thinking-off-only clean-start U/S/X/SX pilot driver.

Lives outside the repo checkout. Does not send thinking-on. Does not print
or write DEEPSEEK_API_KEY. official_settlement stays false.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

HKT = ZoneInfo("Asia/Hong_Kong")
ROOT = Path("/home/box/cos/clean-start-usx-pilot-2026-11-25")
REPO_SRC = ROOT / "repo" / "src"
OUT = ROOT / "artifacts"
BFCL_ROOT = Path("/workspace/tool-compression-flash-2026-11-17/gorilla")
CEILING = Decimal("20")
EXPECTED_CASES = 47
EXPECTED_SLOTS = 188

# Load the reviewed tip, not any other checkout on PYTHONPATH.
sys.path.insert(0, str(REPO_SRC))


def _key_is_set() -> bool:
    value = os.environ.get("DEEPSEEK_API_KEY")
    return bool(value and str(value).strip())


def main() -> int:
    started = datetime.now(HKT)
    if not _key_is_set():
        print("refusing: DEEPSEEK_API_KEY is not set", file=sys.stderr)
        return 2

    from tool_compression.clean_start.__main__ import _select_cases
    from tool_compression.clean_start.pin import (
        OFFICIAL_SETTLEMENT,
        REQUEST_MODEL,
        STUDY_ID,
    )
    from tool_compression.clean_start.runner import (
        OfficialBfclExecutor,
        authorized_transport,
        build_slots,
        execute,
        resolve_bfcl_package,
    )

    if OFFICIAL_SETTLEMENT is not False:
        print("refusing: official_settlement must stay false", file=sys.stderr)
        return 2
    if REQUEST_MODEL != "deepseek-flash":
        print("refusing: unexpected request model", file=sys.stderr)
        return 2

    cases = _select_cases(True)
    if len(cases) != EXPECTED_CASES:
        raise RuntimeError(f"expected {EXPECTED_CASES} pilot cases, got {len(cases)}")

    all_slots = build_slots(cases)
    slots = [slot for slot in all_slots if slot["thinking"] == "off"]
    if len(slots) != EXPECTED_SLOTS:
        raise RuntimeError(f"expected {EXPECTED_SLOTS} thinking-off slots, got {len(slots)}")
    if any(slot["thinking"] != "off" for slot in slots):
        raise RuntimeError("thinking-on leaked into the filtered slot list")
    if any(slot["thinking"] == "on" for slot in all_slots if slot in slots):
        raise RuntimeError("thinking-on present in the run list")
    thinking_on_count = sum(1 for slot in all_slots if slot["thinking"] == "on")
    if thinking_on_count != EXPECTED_SLOTS:
        # The unfiltered builder still plans thinking-on; we just must not send it.
        raise RuntimeError(f"unexpected thinking-on plan size {thinking_on_count}")

    OUT.mkdir(parents=True, exist_ok=True)
    preflight = {
        "study": STUDY_ID,
        "official_settlement": False,
        "tip": "0c0284d5c3ca76d77b11a4db304d46953844ec66",
        "pr": 27,
        "thinking": "off",
        "thinking_on_sent": False,
        "cases": len(cases),
        "slots": len(slots),
        "ceiling_usd": str(CEILING),
        "request_model": REQUEST_MODEL,
        "bfcl_root": str(BFCL_ROOT),
        "out_dir": str(OUT),
        "started_at_hkt": started.isoformat(),
        "api_key_set": True,
        "peak_acknowledged": True,
    }
    (ROOT / "preflight.json").write_text(
        json.dumps(preflight, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "phase": "preflight_ok",
        "official_settlement": False,
        "cases": len(cases),
        "slots": len(slots),
        "thinking_on_planned_but_not_sent": thinking_on_count,
        "ceiling_usd": str(CEILING),
        "started_at_hkt": started.isoformat(),
        "api_key_set": True,
    }, sort_keys=True), flush=True)

    package = resolve_bfcl_package(BFCL_ROOT)
    executor = OfficialBfclExecutor(package, "deepseek_flash")
    transport = authorized_transport()
    result = execute(
        cases,
        slots,
        OUT,
        transport,
        ceiling_usd=CEILING,
        executor=executor,
    )
    ended = datetime.now(HKT)
    summary = {
        "complete": result["complete"],
        "status": result["status"],
        "reason": result.get("reason"),
        "running_usd": result.get("running_usd"),
        "ceiling_usd": result.get("ceiling_usd", str(CEILING)),
        "slots_sent": result.get("slots_sent"),
        "slots_total": result.get("slots_total"),
        "official_settlement": False,
        "thinking_on_sent": False,
        "started_at_hkt": started.isoformat(),
        "ended_at_hkt": ended.isoformat(),
        "api_key_set": True,
    }
    (ROOT / "driver_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, sort_keys=True), flush=True)
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
