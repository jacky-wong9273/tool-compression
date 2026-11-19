# Recorded official result

This directory holds the 18–19 November 2026 thinking-off replicate and the adapters that recompute it from saved outputs.

In this single thinking-off replicate, the shared local intervention produced small provider-input savings and remained within the prespecified observed primary accuracy-loss margin. The combined utility target was not reached. These results do not establish statistical non-inferiority or general quality preservation.

L−U is −0.5 percentage points; the observed accuracy loss is +0.5 points.

| Path | Role |
| --- | --- |
| `RESULTS.md` | Package C account of the measured result |
| `COMMANDS.md` | Preparation, mapping, evaluate-from-saved-outputs, and settlement commands |
| `settlement/official_settlement.json` | Locked official U/L/E settlement |
| `tables/measurement_chain.json` | Alias, decode, and flight-identity checks |
| `tables/usage_accounting.json` | Billed-basis `T` and the separate cache-associated input-cost figure |
| `tables/official_score_reproduction.json` | Recorded identity of the nine official score files, without digest bytes |
| `tables/change_class_join.json` | Change class joined to official outcomes and the primary `T` split |
| `tables/preprocessing_overhead.json` | CPU-only per-condition timing |
| `artifact_manifest.json` | Hashes for files in this checkout; null hashes for absent flight trees |

`T` is billed-basis provider total input. The cache-associated input-cost figure is a different measurement and is not the study statistic. The scoring alias `DeepSeek-V3.2-Exp-FC` evaluates saved outputs. The package refuses `bfcl generate` under that alias because the registry `model_name` is `deepseek-chat`.
