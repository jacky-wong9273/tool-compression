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

The same gate records `2026-11-23T19:00:00+08:00` as an off-peak example. `live_permitted` is true there because all 840 cases are sealed and that clock is off-peak. This dry-run did not start `--live`. A paid start still needs the ceiling Jacky supplies, and a peak minute still stops the run before a key is read.

A dry-run with a larger environment value also writes spend `"0"`. The larger value is still not permission to start `--live`.

## Later live run

CoS starts this only after three conditions hold together:

1. Jacky supplies `EXPLORATORY_CEILING_CNY` for this flight. The ceiling already in use is the remaining exploratory amount. This package does not name a new one and does not lift one.
2. `remaining-work.json` is empty and `verify_package` reports 840 sealed cases. That condition now holds. `--live` was not started from this package. There is no partial-live switch. A peak minute, or a ceiling below the off-peak reserve, still returns before a key is read.
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

## Resume onto an existing out directory

The same `--live` command is the resume. It still requires the sealed 840 package, still refuses a peak minute, and still checks the off-peak reserve against the supplied ceiling. It does not take `--authorize-peak`. Point `--out` at the directory that already holds the result files. Do not delete those files and do not start a second out directory for the same flight.

```bash
export EXPLORATORY_CEILING_CNY='<the same ceiling Jacky supplied for this flight>'
export DEEPSEEK_API_KEY='<key in the environment, not in the repo>'
python -m tool_compression usx-840 --live \
  --bfcl-root /path/to/gorilla/berkeley-function-call-leaderboard \
  --out <the existing out directory>
```

A group is skipped only when every arm in that group already has a JSONL row for that thinking pass, category, and case id. A skipped group is not called again and is not appended again. A group that has only some of its arms is called. The arms that already have a row are not appended a second time.

The run that stopped at 19:37 HKT on 23 November 2026 left thinking-off rows for `multiple_0` through `multiple_121`, all four arms, and no `calls-ledger.jsonl`. Resume that directory off-peak with the same ceiling. The first call is then the first thinking-off group that is not fully present, which is the first unique payload of `multiple_122`. Because those 122 cases have rows and no ledger, spend starts at `0`. `resume.json` records that the cache split for those rows is not invented. Do not lower the ceiling or the reserve to make the next call fit. A later run that does have `calls-ledger.jsonl` adds that settled spend, including the cache split, before the reserve check.

`calls-ledger.jsonl` is appended and flushed after each settled call, so a later stop keeps the bills. `stop.json` records the settled spend, the settled call count, and the stop reason. Neither file stores the API key. Official settlement stays false.

## Mid-run provider failures

A provider failure during a call writes `stop.json` and leaves the ledger at the last settled call. The unfinished call is not appended. Resume is the same command and the same `--out`. Completed groups stay skipped.

`urlopen(..., timeout=120)` is an inactivity timeout on one socket. Name resolution sits outside it, and `socket.create_connection` applies that timeout once per DNS address. Unreachable addresses stack: a direct check showed one stalled socket honoring a one-second timeout, and two blackholed addresses taking about two timeouts. The 20:08 HKT stop (last settled call 20:00:22, process exit 20:08:38) and the 20:41 HKT stop (last settled call `simple_python_314` at 20:16:23, process exit 20:41:13) were clean `provider timed out` refusals whose waits were many minutes. That is the shape of several unreachable addresses, each using a full 120-second inactivity timeout. A single socket read that ignores its timeout would land in the same place.

The live client bounds the whole call with a 120-second wall clock. Each address gets at most 10 seconds to connect, and only the time still left on that clock. At the deadline the client shuts down the socket it is blocked on, so a stalled connect, TLS handshake, or response read ends. The flight raises `provider timed out`. That call is omitted from the ledger. The provider may already have accepted it, and resume sends the same group again.

`http.client.RemoteDisconnected` is what `getresponse` raises when the peer closes before a status line. It is a `ConnectionResetError`. That read is not wrapped in `URLError`, which is why the 20:49 HKT resume (tip `69dfc959`) exited 1 with no `stop.json`. The ledger stayed at 584 off-peak calls and spend 0.34947080 CNY. The same drop now raises `provider connection failed` and writes `stop.json`. Other connection drops, including `ConnectionError` and `http.client.HTTPException` such as `IncompleteRead`, stop the same way. A timeout still uses `provider timed out`. The refusal text does not include the API key.

With those 584 ledger rows and thinking-off lines for every `multiple` case, every `simple_python` case, and `irrelevance_0` through `irrelevance_77`, the next call is thinking-off `irrelevance_78`. Thinking-on has not started. The first 122 thinking-off `multiple` cases still have result rows and no ledger line. Resume spend is the ledger total. `resume.json` from the first resume still says the cache split for those unledgered rows was not invented. Pass the same ceiling. A peak minute, or a reserve that does not fit under that ceiling, still stops before the next call.
