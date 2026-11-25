"""Official ``bfcl evaluate`` on result files a run already wrote.

Each arm and thinking mode is its own model directory. The directories are
registered in-process as DeepSeek FC models, so the pinned checkout is never
edited. One category and one model at a time, with ``partial_eval`` so an
incomplete run is scored only on the ids it finished. No provider is contacted:
the handler constructor reads a key variable, so a placeholder is set for the
duration of the call and the previous environment is restored afterwards.
"""

from __future__ import annotations

from pathlib import Path
import json
import os
import sys

from tool_compression.clean_start.pin import ARMS, OFFICIAL_SETTLEMENT, REQUEST_MODEL
from tool_compression.clean_start.runner import resolve_bfcl_package
from tool_compression.clean_start.scoring import result_model_name

PLACEHOLDER = "UNUSED_OFFICIAL_EVAL_NO_PROVIDER_CALL"


def model_names(thinking_modes: tuple[str, ...]) -> list[str]:
    return [result_model_name(thinking, arm) for thinking in thinking_modes for arm in ARMS]


def result_categories(result_dir: Path, model: str) -> list[str]:
    root = Path(result_dir) / model
    if not root.is_dir():
        return []
    found = []
    for path in sorted(root.rglob("BFCL_v4_*_result.json")):
        category = path.name[len("BFCL_v4_"):-len("_result.json")]
        if "prereq" not in category:
            found.append(category)
    return found


def register_models(names: list[str]) -> None:
    """Same flags as the pinned ``DeepSeek-V3.2-Exp-FC`` entry.

    ``underscore_to_dot`` must be True: FC tool names have every ``.`` replaced
    by ``_`` before sending, and the AST checker only maps gold names the same
    way when this flag is set. With False, every dotted gold name scores as
    ``wrong_func_name``.
    """
    from bfcl_eval.constants.model_config import MODEL_CONFIG_MAPPING, ModelConfig
    from bfcl_eval.model_handler.api_inference.deepseek import DeepSeekAPIHandler

    reference = MODEL_CONFIG_MAPPING["DeepSeek-V3.2-Exp-FC"]
    if not (reference.is_fc_model and reference.underscore_to_dot):
        raise RuntimeError("pinned DeepSeek FC entry no longer maps dotted names")
    for name in names:
        MODEL_CONFIG_MAPPING[name] = ModelConfig(
            model_name=REQUEST_MODEL,
            display_name=name,
            url="https://api-docs.deepseek.com/",
            org="DeepSeek",
            license="MIT",
            model_handler=DeepSeekAPIHandler,
            input_price=None,
            output_price=None,
            is_fc_model=True,
            underscore_to_dot=True,
        )


def run_official_evaluation(out_dir: Path, bfcl_root: Path, thinking_modes: tuple[str, ...]) -> dict:
    out_dir = Path(out_dir).resolve()
    result_dir = out_dir / "result"
    score_dir = out_dir / "score"
    project = out_dir / "bfcl_project"
    package = resolve_bfcl_package(Path(bfcl_root))
    names = model_names(thinking_modes)
    saved = {key: os.environ.get(key) for key in ("BFCL_PROJECT_ROOT", "DEEPSEEK_API_KEY", "OPENAI_API_KEY", "SERPAPI_API_KEY")}
    project.mkdir(parents=True, exist_ok=True)
    score_dir.mkdir(parents=True, exist_ok=True)
    runs = []
    try:
        os.environ["BFCL_PROJECT_ROOT"] = str(project)
        os.environ["DEEPSEEK_API_KEY"] = PLACEHOLDER
        os.environ["OPENAI_API_KEY"] = PLACEHOLDER
        os.environ.pop("SERPAPI_API_KEY", None)
        if str(package) not in sys.path:
            sys.path.insert(0, str(package))
        register_models(names)
        from bfcl_eval.__main__ import evaluation_main

        for model in names:
            categories = result_categories(result_dir, model)
            if not categories:
                runs.append({"model": model, "category": None, "ok": False, "reason": "no_result_files"})
                continue
            for category in categories:
                try:
                    evaluation_main([model], [category], str(result_dir), str(score_dir), True)
                    runs.append({"model": model, "category": category, "ok": True})
                except Exception as exc:
                    runs.append({
                        "model": model,
                        "category": category,
                        "ok": False,
                        "reason": f"{exc.__class__.__name__}: {exc}",
                    })
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    scored = [run for run in runs if run["category"] is not None]
    summary = {
        "official_settlement": OFFICIAL_SETTLEMENT,
        "thinking_modes": list(thinking_modes),
        "models": names,
        "result_dir": str(result_dir),
        "score_dir": str(score_dir),
        "registration": "in-process MODEL_CONFIG_MAPPING only; the pinned checkout is not edited",
        "partial_eval": True,
        "runs": runs,
        "ok": bool(scored) and all(run["ok"] for run in scored),
        "failed": sum(1 for run in runs if not run["ok"]),
    }
    (out_dir / "evaluate_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return summary
