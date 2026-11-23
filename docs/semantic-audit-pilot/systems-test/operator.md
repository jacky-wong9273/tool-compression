# Operator

Two commands share one ceiling variable. Stage A was run for this package. The live command was not.

## Dry-run

From the repository root, with a Gorilla checkout that contains the pinned `BFCL_v4_*.json` files:

```bash
EXPLORATORY_CEILING_CNY='0.01' \
  python -m tool_compression usx-flight --no-api \
  --bfcl-root /path/to/gorilla/berkeley-function-call-leaderboard \
  --out docs/semantic-audit-pilot/systems-test/dry-run
```

Omit `--no-api` and the command still stays on Stage A. `--live` is what leaves Stage A.

What the process does:

1. Read `EXPLORATORY_CEILING_CNY`. Refuse if it is missing, blank, or not a positive decimal. There is no default to fall back on.
2. Rebuild U from the pin and refuse if it differs from the frozen rendered U. Load frozen S and the revised X/SX files.
3. Hash each arm's generation body and collapse identical bodies inside the case.
4. Read the Asia/Shanghai clock, pick the public Flash card for that minute, and compute the worst-case reserve.
5. Write `gate.json` with `provider_called: false`, `api_key_read: false`, and `spend_cny: "0"`.

The process does not read `DEEPSEEK_API_KEY`, even when the variable is present. It does not import the live client and it does not run `bfcl_eval`.

The committed gate was produced with `EXPLORATORY_CEILING_CNY=0.01` while the clock was inside the Monday 14:00–18:00 Asia/Shanghai window, so the reserve is the peak reserve, ¥5.145728. That proof value cannot cover the reserve. `reserve_fits_supplied_ceiling` is false, `stopped_for_peak` is false, and `spend_cny` is `"0"`. The 0.01 figure is there so the file shows which value the process received. It is not Jacky's ceiling, it is not a hardcoded budget, and it does not authorize a later process to spend.

A dry-run with a larger environment value also writes spend `"0"`. The larger value still is not permission to start `--live` unless Jacky has supplied it for that purpose.

## Later live run

CoS starts this only after Jacky supplies `EXPLORATORY_CEILING_CNY`. This package does not contain that amount.

```bash
export EXPLORATORY_CEILING_CNY='<the amount Jacky supplied>'
export DEEPSEEK_API_KEY='<key in the environment, not in the repo>'
python -m tool_compression usx-flight --live --authorize-peak \
  --bfcl-root /path/to/gorilla/berkeley-function-call-leaderboard \
  --out artifacts/usx-12-live
```

`--authorize-peak` is required. Without it the command stops before it reads the key. With it, the run may start and continue during a peak window and bills the peak card for any call whose clock is in that window. Calls outside the window use the off-peak card. Each call records the schedule it used. Peak spend is not relabeled as the locked off-peak validation card.

Before every call the process reserves the worst case on the card in force at that minute. If spent plus the reserve would pass the supplied ceiling, it writes `stop.json` and does not make the call. It does not lift the ceiling.

The key is read only after the first call has passed that reserve check. A ceiling below one worst-case reserve therefore never reads the key.

Saved lines, one JSON object per line:

`artifacts/usx-12-live/result/<arm>/DeepSeek-V3.2-Exp-FC/BFCL_v4_<category>_result.json`

Arms that shared a body receive the same result line. T on the line is `prompt_tokens`.

Then score each arm. Do not point `--result-dir` at the alias directory; the evaluator looks for a model subdirectory inside the directory you pass.

```bash
python -m bfcl_eval evaluate \
  --model DeepSeek-V3.2-Exp-FC \
  --test-category multiple,simple_python,irrelevance \
  --result-dir artifacts/usx-12-live/result/U \
  --score-dir artifacts/usx-12-live/score/U \
  --partial-eval
```

Repeat with `S`, `X`, and `SX`. Keep `--partial-eval`. Without it, this pin rejects a result file that is shorter than the category. After scoring, fill the five contrasts from those accuracies and apply the irrelevance rule in [quality.md](quality.md). Leave the official v1.1 numbers where they are.

`--live` and `--no-api` together are refused.
