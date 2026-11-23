# Methodology

The 12 case ids, the frozen S catalogues, and the revised X/SX catalogues are the ones already sealed under `docs/semantic-audit-pilot/`. This flight does not edit them. Questions are read at runtime from a Gorilla checkout of commit `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8` and are not copied into the gate.

## Arms

| Arm | Catalogue used for generation |
| --- | --- |
| U | Fresh OpenAI-completions conversion of the pinned BFCL record. The flight refuses to continue if that conversion differs from `rendered/<case>/U.json`. |
| S | Frozen first-pilot `rendered/<case>/S.json`. |
| X | Cue-revision `cue-revision/rendered/<case>/X.json`. The cue text is the sealed revision, used as already written. |
| SX | Cue-revision `cue-revision/rendered/<case>/SX.json`. |

Historical L, E, T1, and T2 responses are not arms.

## Generation

Each planned call is one Chat Completions body:

- `model`: `deepseek-flash`
- model version recorded beside the body: `DeepSeek-V4.1-Flash-1017`
- `thinking`: `{"type": "disabled"}`. The field is sent. DeepSeek's default is thinking on when the field is omitted.
- `temperature`: `0.001`
- `store`: false
- `messages`: the case's first question turn, loaded from the pin
- `tools`: that arm's catalogue

`DeepSeek-V3.2-Exp-FC` is the evaluate `--model` and the result-directory name. It selects the pinned function-call handler for saved outputs. It is not the generation model, and the body refuses that alias. The handler's own upstream name (`deepseek-chat`) is not sent either.

Endpoint, when a later operator runs `--live`: `POST https://api.deepseek.com/chat/completions`. The key is `DEEPSEEK_API_KEY` in the environment. Stage A never reads that variable.

## One observation per identical payload

Sharing is inside one case. Two arms share a call only when the full body matches: messages, model, temperature, store, thinking, and tools. A match in another case is a different call, because the question is different.

The sealed strings produce 32 payloads, not 48:

| Cases | Why the bodies match | Calls |
| --- | --- | --- |
| `multiple_35`, `multiple_0`, `multiple_11`, `multiple_12`, `multiple_7` | U, S, X, and SX are four different catalogues | 4 each |
| `multiple_92` | Frozen S left the catalogue unchanged, so S matches U and SX matches X. The revised cue still makes X different from U. | 2 |
| `multiple_153`, `multiple_100`, `simple_python_175`, `simple_python_34` | No cue, so X matches U and SX matches S. S itself differs from U. | 2 each |
| `irrelevance_59`, `irrelevance_50` | No cue, and frozen S also left the catalogue unchanged, so all four arms are one body. | 1 each |

The two irrelevance rows are one observation because the frozen catalogues already match. The flight still records all four arm names on that observation. It does not drop an arm and it does not copy a historical response.

## Input T and the bill

T is the provider `prompt_tokens` field on that call. Cache-hit tokens stay inside T. The price is not folded into T.

The bill is separate. It uses the public Flash card for the Asia/Shanghai clock at that call. Cache-hit and cache-miss tokens are billed at their own rates when the provider reports both and they add up to `prompt_tokens`. If the cache split is missing or does not add up, the whole input is billed at the miss rate so the ceiling is not understated. That fallback is a billing choice. It does not change T.

## Rate card

Verified live on 2026-11-23 from [模型 & 价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/). Prices are CNY per million tokens for `deepseek-flash`.

| | Cache hit | Cache miss | Output |
| --- | ---: | ---: | ---: |
| Off-peak | 0.02 | 1 | 4 |
| Peak | 0.04 | 2 | 8 |

Peak is Beijing time, Monday–Friday, excluding Chinese public holidays, 09:00–12:00 and 14:00–18:00. The windows are half-open at the end: 12:00 and 18:00 are off-peak. Weekends, and Chinese public holidays for the whole day, are off-peak. Every other time is off-peak.

No holiday calendar is bundled. A weekday that is a public holiday and falls inside those windows is billed as peak, the higher of the two published cards. That is not a third price.

This card is the public Flash schedule. A peak charge on this systems test is a peak charge. It is not the locked off-peak validation card used by the separate validation flight.

Context reserved as the worst case is the page's 1M input and 384K output, taken as 1,000,000 and 384×1024 = 393,216 tokens. Before each call the reserve is the miss rate on 1,000,000 plus the output rate on 393,216, using whichever schedule the clock says at that moment.

- Off-peak reserve: ¥2.572864
- Peak reserve: ¥5.145728

The reserve is recomputed per call. A run that starts off-peak still reserves the peak amount for a call whose clock is inside a peak window. The call is refused when spent plus that reserve would pass the supplied ceiling. The ceiling is not raised to let the call through.

## Ceiling

`EXPLORATORY_CEILING_CNY` is read from the environment at process start. There is no default in the code, the command line, or this document. A float is refused. A non-positive value is refused. The figure used for the committed gate is recorded in that gate and is explained in [operator.md](operator.md). It is not Jacky's ceiling.

## Peak continuation

The official validation flight stops inside the weekday windows. This command does not import that flight and does not change it.

On this command, `--live` without `--authorize-peak` stops before a key is read, including off-peak. `--live --authorize-peak` may start and continue while the Shanghai clock is inside a peak window. Each call still records the schedule it actually used. The flag is the explicit authorization for this 12-case systems test (t2524u/t2525u). It does not authorize any other flight.

## Scoring command

After a live run has written outputs, each arm is scored on its own with the pinned evaluator:

```bash
python -m bfcl_eval evaluate \
  --model DeepSeek-V3.2-Exp-FC \
  --test-category multiple,simple_python,irrelevance \
  --result-dir result/<arm> \
  --score-dir score/<arm> \
  --partial-eval
```

`<arm>` is `U`, `S`, `X`, or `SX`. Saved lines live at `result/<arm>/DeepSeek-V3.2-Exp-FC/BFCL_v4_<category>_result.json`. The directory name is the scoring alias so the function-call handler is selected. Generation still used `deepseek-flash`.

`--partial-eval` is required. On this pin, `evaluate` without it raises when the model-result file is shorter than the category file, and it tells the operator to pass `--partial-eval`. The 12 cases span `multiple`, `simple_python`, and `irrelevance`, so those three categories are the ones named. Accuracy from that command is the accuracy of the rows present in the result files. It is not a leaderboard score for 200, 400, or 240.

Stage A writes the argv and does not run it. There are no saved outputs to score.
