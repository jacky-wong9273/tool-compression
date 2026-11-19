# Commands for the recorded 18–19 November 2026 result

These commands prepare local counts, map saved flight outputs, evaluate those saved outputs, and recompute the locked settlement. They do not call a model provider. Paths are arguments. Historical machine directories are labels in `official/artifact_manifest.json`, and their `sha256` stays null while the bytes are absent. They are not defaults.

In this single thinking-off replicate, the shared local intervention produced small provider-input savings and remained within the prespecified observed primary accuracy-loss margin. The combined utility target was not reached. These results do not establish statistical non-inferiority or general quality preservation.

L−U is −0.5 percentage points; the observed accuracy loss is +0.5 points.

The study statistic remains billed-basis provider total input. The cache-associated input-cost figure is a different measurement. `python -m tool_compression official-check` recomputes both and keeps that distinction. Do not read `data_overall.csv` Overall Acc (6.95% / 6.99% / 6.99% in the scoring run) as a study metric. Official rollups treat unevaluated categories as 0.

## Check the committed record

Works in this repository with no gorilla checkout and no flight JSONL:

```bash
pip install -e ".[test]"
pytest -q
python -m tool_compression official-check
python -m tool_compression artifact-manifest --check official/artifact_manifest.json
```

`official-check` recomputes the locked settlement arithmetic, the usage contrast, the change-class join, and the artifact manifest. It exits non-zero if a locked figure has moved.

## Map saved stage B outputs

Requires the flight directory that contains `logical_ledger.json`, `usage_ledger.json`, and `parsed.jsonl`. The 18 November flight has 1,513 physical groups. The adapter reads that directory and writes result files. It does not modify the flight directory.

```bash
python -m tool_compression official-map \
  --stage-b PATH_TO_STAGE_B \
  --out PATH_TO_OFFICIAL_TREE \
  --expected-groups 1513
```

The same entry point is `scripts/map_saved_outputs_to_bfcl_results.py` with the same arguments. Result files land at:

`PATH_TO_OFFICIAL_TREE/bfcl_project/result_{u,l,e}/DeepSeek-V3.2-Exp-FC/BFCL_v4_{category}_result.json`

The mapping is `PATH_TO_OFFICIAL_TREE/mapping/arm_case_mapping.jsonl`.

## Evaluate saved results

`scripts/run_official_evaluate.sh` runs `bfcl evaluate` only. Any argument equal to `generate` exits 2 before `bfcl` starts. The scoring alias `DeepSeek-V3.2-Exp-FC` has registry `model_name` `deepseek-chat`, so generate under that alias would call a different model from the flight model `deepseek-flash`.

```bash
bash scripts/run_official_evaluate.sh \
  --bfcl PATH_TO_BFCL_EXECUTABLE \
  --project-root PATH_TO_BFCL_PROJECT
```

The script exports dummy keys `UNUSED_OFFICIAL_EVAL_NO_PROVIDER_CALL` and unsets other provider keys it knows about. `--project-root` must already contain `result_{u,l,e}/DeepSeek-V3.2-Exp-FC/`. If the `bfcl` executable is missing, the script exits and does not call a provider.

The guard alone:

```bash
python -m tool_compression official-guard \
  --action evaluate --model DeepSeek-V3.2-Exp-FC
python -m tool_compression official-guard \
  --action generate --model DeepSeek-V3.2-Exp-FC
```

The generate form exits 2.

## Settle from saved score files

```bash
python -m tool_compression official-settle \
  --score-root PATH_TO_BFCL_PROJECT \
  --mapping PATH_TO_ARM_CASE_MAPPING.jsonl \
  --execution-record PATH_TO_EXECUTION_RECORD.json \
  --out PATH_TO_SETTLEMENT.json
```

`scripts/compute_official_settlement.py` takes the same arguments. The committed file `official/settlement/official_settlement.json` is the locked settlement. A fresh settlement from saved scores is a recomputation. It does not replace the locked file inside this package, and it does not fill missing per-case rows.

## Join and timing

`join-outcomes` summarizes a JSONL of case rows (`category`, `case_id`, `change_class`, `correct_U`, `correct_L`, and optional token fields). Missing token fields stay missing.

```bash
python -m tool_compression join-outcomes --rows PATH_TO_ROWS.jsonl --out PATH_TO_JOIN.json
```

The recorded join is `official/tables/change_class_join.json`. Per-case provider tokens for the flight are not in this checkout.

CPU-only preprocessing timing, with no model call:

```bash
python -m tool_compression time-preprocessing \
  --out official/tables/preprocessing_overhead.json
```

The committed JSON is one Python 3.12.3 run. Re-running the command changes the wall-clock medians. Week 1 combined characterization time remains 2.287 seconds and does not separate C from I.

## Reproduce the Week 1 preparation

These commands need local checkouts. They rewrite local count files. They do not produce official scores. The historical packet `evidence/WEEK1_EVIDENCE_PACKET.md` stays the Week 1 record.

```bash
python -m tool_compression characterize \
  --bfcl-root PATH_TO_GORILLA \
  --out evidence/week1_characterization.json
python -m tool_compression arm-e \
  --bfcl-root PATH_TO_GORILLA \
  --tscg-root PATH_TO_TSCG \
  --out evidence/week1_arm_e.json
python -m tool_compression packet \
  --characterization evidence/week1_characterization.json \
  --arm-e evidence/week1_arm_e.json \
  --out evidence/WEEK1_EVIDENCE_PACKET.md
```

Pins for those checkouts: gorilla `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`, TSCG `dfcba63d6190285c45a7c412268dbcc757664ab2`.

## Refresh the manifest after a hashed file changes

```bash
python -m tool_compression artifact-manifest --out official/artifact_manifest.json
python -m tool_compression artifact-manifest --check official/artifact_manifest.json
```

Absent flight trees, official score files, and the case-level outcome table keep `sha256` null.
