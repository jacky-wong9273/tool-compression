#!/usr/bin/env python3
"""Official bfcl evaluate for the thinking-off pilot, one category and arm at a time.

Registers the four thinking-off model directories in-process (no edits to the
pinned Gorilla checkout). Does not evaluate thinking-on. Does not pass
all_scoring. official_settlement stays false.

This script scores already-written result files. It does not contact DeepSeek
for inference. A dummy provider key is used only because the handler
constructor reads an environment variable.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path("/home/box/cos/clean-start-usx-pilot-2026-11-25")
RESULT_DIR = ROOT / "artifacts" / "result"
SCORE_DIR = ROOT / "artifacts" / "score"
BFCL_PROJECT = ROOT / "bfcl_project"
BFCL_PACKAGE = Path(
    "/workspace/tool-compression-flash-2026-11-17/gorilla/berkeley-function-call-leaderboard"
)
ARMS = ("U", "S", "X", "SX")
MODELS = [f"deepseek-flash-thinking-off-{arm}" for arm in ARMS]


def existing_categories(model: str) -> list[str]:
    root = RESULT_DIR / model
    if not root.is_dir():
        return []
    found = []
    for path in sorted(root.rglob("BFCL_v4_*_result.json")):
        name = path.name
        # BFCL_v4_<category>_result.json
        category = name[len("BFCL_v4_") : -len("_result.json")]
        found.append(category)
    return found


def register_models() -> None:
    from bfcl_eval.constants.model_config import MODEL_CONFIG_MAPPING, ModelConfig
    from bfcl_eval.model_handler.api_inference.deepseek import DeepSeekAPIHandler

    for name in MODELS:
        MODEL_CONFIG_MAPPING[name] = ModelConfig(
            model_name="deepseek-flash",
            display_name=name,
            url="https://api-docs.deepseek.com/",
            org="DeepSeek",
            license="MIT",
            model_handler=DeepSeekAPIHandler,
            input_price=None,
            output_price=None,
            is_fc_model=True,
            underscore_to_dot=False,
        )


def main() -> int:
    # Keep locks and default result/score dirs out of the pinned Gorilla tree.
    BFCL_PROJECT.mkdir(parents=True, exist_ok=True)
    os.environ["BFCL_PROJECT_ROOT"] = str(BFCL_PROJECT)
    # Constructor-only dummy. Evaluate must not use the live inference key.
    os.environ["DEEPSEEK_API_KEY"] = "UNUSED_OFFICIAL_EVAL_NO_PROVIDER_CALL"
    os.environ["OPENAI_API_KEY"] = "UNUSED_OFFICIAL_EVAL_NO_PROVIDER_CALL"
    os.environ.pop("SERPAPI_API_KEY", None)

    sys.path.insert(0, str(BFCL_PACKAGE))
    register_models()

    from bfcl_eval.__main__ import evaluation_main

    SCORE_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for model in MODELS:
        categories = existing_categories(model)
        if not categories:
            results.append({
                "model": model,
                "category": None,
                "ok": False,
                "reason": "missing_result_dir_or_files",
                "official_settlement": False,
            })
            continue
        for category in categories:
            print(f"===== evaluate model={model} category={category} =====", flush=True)
            try:
                evaluation_main(
                    [model],
                    [category],
                    str(RESULT_DIR.resolve()),
                    str(SCORE_DIR.resolve()),
                    True,  # partial_eval
                )
                results.append({
                    "model": model,
                    "category": category,
                    "ok": True,
                    "official_settlement": False,
                })
            except Exception as exc:
                results.append({
                    "model": model,
                    "category": category,
                    "ok": False,
                    "reason": f"{exc.__class__.__name__}: {exc}",
                    "official_settlement": False,
                })
                print(f"FAILED {model} {category}: {exc.__class__.__name__}: {exc}", flush=True)
    payload = {
        "official_settlement": False,
        "thinking": "off",
        "models": MODELS,
        "result_dir": str(RESULT_DIR.resolve()),
        "score_dir": str(SCORE_DIR.resolve()),
        "bfcl_project_root": str(BFCL_PROJECT),
        "pinned_gorilla_unmodified": True,
        "registration": "in-process MODEL_CONFIG_MAPPING only; no checkout edits",
        "runs": results,
    }
    (ROOT / "evaluate_summary.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    failed = [row for row in results if not row["ok"]]
    print(json.dumps({
        "official_settlement": False,
        "ok": len(failed) == 0,
        "runs": len(results),
        "failed": len(failed),
    }, sort_keys=True), flush=True)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
