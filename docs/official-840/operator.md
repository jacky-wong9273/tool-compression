# Operator

Stage A was run for this package. The live command was not. This dig does not authorize a paid flight. Official settlement stays false.

## Dry-run

From the repository root, with a Gorilla checkout that contains the pinned `BFCL_v4_*.json` files:

```bash
EXPLORATORY_CEILING_CNY='0.01' \
  python -m tool_compression usx-840 --no-api \
  --bfcl-root /path/to/gorilla/berkeley-function-call-leaderboard \
  --out /tmp/official-840-gate
```

Omit `--no-api` and the command still stays on Stage A. `--live` is what leaves Stage A. `--live` and `--no-api` together are refused. `--authorize-peak` is not a flag of `usx-840`; argparse rejects it.

What the process does:

1. Read `EXPLORATORY_CEILING_CNY`. Refuse if it is missing, blank, or not a positive decimal. There is no default.
2. Check the committed package, including the frozen 12-case bytes and the closed 10% target.
3. Rebuild U from the pin and refuse if it differs from `catalogues/U/`.
4. Plan thinking off for every sealed case, then thinking on over the same catalogues. Unsealed cases are listed as blocked and have no generation body.
5. Hash each arm's body and collapse identical bodies inside that cell only.
6. Read the Asia/Shanghai clock. A peak minute sets `stopped_for_peak` and `live_would_start: false`.
7. Write `gate.json` with `provider_called: false`, `api_key_read: false`, `spend_cny: "0"`, and `official_settlement: false`.

The process does not read `DEEPSEEK_API_KEY`, even when the variable is present. It does not import `official_840_provider`. It does not run `bfcl_eval`.

The committed gate is `dry-run/gate.json`. It was produced with `EXPLORATORY_CEILING_CNY=0.01` at `2026-11-23T17:25:00+08:00`, a Monday inside the 14:00–18:00 window. The schedule is peak, `stopped_for_peak` is true, spend is `"0"`, and the off-peak reserve of ¥2.572864 does not fit under 0.01. The 0.01 figure shows which value the process received. It is not Jacky's ceiling, and it does not authorize a later process to spend.

The same gate records `2026-11-23T19:00:00+08:00` as an off-peak example. `live_permitted` is false there because 407 cases are still unsealed. A paid start at that clock is not feasible on this package.

A dry-run with a larger environment value also writes spend `"0"`. The larger value is still not permission to start `--live`.

## Later live run

CoS starts this only after three conditions hold together:

1. Jacky supplies `EXPLORATORY_CEILING_CNY` for this flight. The ceiling already in use is the remaining exploratory amount. This package does not name a new one and does not lift one.
2. `remaining-work.json` is empty and `verify_package` reports 840 sealed cases. Until then `--live` returns before it reads a key or opens a socket. There is no partial-live switch.
3. The Asia/Shanghai clock is off-peak. A peak minute writes `stop.json` with `stop_reason: peak_hours` and `peak_card_used: false`, including a peak minute that arrives after earlier calls have already settled. The flight does not continue on the peak card.

```bash
export EXPLORATORY_CEILING_CNY='<the amount Jacky supplied>'
export DEEPSEEK_API_KEY='<key in the environment, not in the repo>'
python -m tool_compression usx-840 --live \
  --bfcl-root /path/to/gorilla/berkeley-function-call-leaderboard \
  --out artifacts/official-840-live
```

There is no `--authorize-peak` in that command. Adding it makes argparse exit before the run.

The key is read only after the first call has passed the off-peak reserve check. A ceiling below ¥2.572864 therefore never reads the key. The runner does not raise the ceiling to make the reserve fit.

Generation, when that later run happens: `deepseek-flash` / `DeepSeek-V4.1-Flash-1017`, thinking `{"type":"disabled"}` for the whole sealed set, then `{"type":"enabled"}` over the same catalogues, temperature `0.001`, `store` false. A thinking-off response that includes reasoning stops the run and does not start thinking on.

Saved lines, one JSON object per line, under the scoring alias:

`artifacts/official-840-live/result/thinking-off/<arm>/DeepSeek-V3.2-Exp-FC/BFCL_v4_<category>_result.json`

and the same path with `thinking-on`. Arms that shared a body inside one cell receive the same result line. T on the line is `prompt_tokens`. The two passes do not share a line.

Then score each arm of each pass. Do not point `--result-dir` at the alias directory. The evaluator looks for a model subdirectory inside the directory you pass. Do not pass `--partial-eval`. The official flight is the full 200, 400, and 240.

```bash
python -m bfcl_eval evaluate \
  --model DeepSeek-V3.2-Exp-FC \
  --test-category multiple,simple_python,irrelevance \
  --result-dir artifacts/official-840-live/result/thinking-off/U \
  --score-dir artifacts/official-840-live/score/thinking-off/U
```

Repeat for `S`, `X`, and `SX`, and for `thinking-on`. `DeepSeek-V3.2-Exp-FC` is the handler alias. It is not the generation model.

After scoring, fill the five contrasts from those accuracies, separately per thinking pass, and apply the irrelevance rule in [quality.md](quality.md). Leave the official v1.1 numbers where they are. Leave `official_settlement` false until Jacky separately says otherwise.
