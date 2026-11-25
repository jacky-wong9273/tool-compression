# Clean-start U/S/X/SX thinking-off peak pilot — results

official_settlement: false. This is not official settlement.

## Run identity

- Tip: `0c0284d5c3ca76d77b11a4db304d46953844ec66` (PR #27, stacked on #25 tip `0fc24dfc`)
- Checkout: `/home/box/cos/clean-start-usx-pilot-2026-11-25/repo` (detached HEAD, unmodified)
- Thinking: off only. The stock CLI would also send thinking-on after thinking-off; a driver outside the checkout filtered to `thinking == "off"` (188 slots asserted; no thinking-on slot was passed to `execute`)
- Cases / slots planned: 47 cases × 4 arms = 188 thinking-off slots (seed 20261125)
- Ceiling: $20 USD
- official_settlement: false in run.json, spend.json, driver_summary.json, and this briefing
- Model: `deepseek-flash` (request body `thinking.type: disabled`). No max_tokens. No reserve stack. 120s HTTP timeout.
- Executor package: pinned Gorilla at `/workspace/tool-compression-flash-2026-11-17/gorilla` commit `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8` (tracked tree left unmodified; evaluate registered the four thinking-off directories in-process only)
- Out dir: `/home/box/cos/clean-start-usx-pilot-2026-11-25/artifacts`
- Start: 2026-11-25 11:35:15 HKT Asia/Hong_Kong
- End: 2026-11-25 11:44:57 HKT Asia/Hong_Kong
- First billed request completed: 2026-11-25 11:35:18 HKT Asia/Hong_Kong
- Last billed request completed: 2026-11-25 11:40:19 HKT Asia/Hong_Kong

## Completeness

- complete: false
- status: incomplete
- reason: `provider_error:TimeoutError`
- slots sent (finished): 87 / 188
- running USD (ledger): $0.040170708000
- ceiling: $20
- partial_presented_as_complete: false
- thinking-on sent: false (no thinking-on result directories, sidecars, or bill rows)
- Peak window: the run started and stopped inside the Monday–Friday 09:00–12:00 HKT Asia/Hong_Kong peak. All 151 ledger rows are band `peak`. No off-peak requests.

The run finished every single-turn pilot slot (80) and then seven of the twelve `multi_turn_base` slots. It stopped mid-slot on `multi_turn_base_86` arm SX, thinking off:

- Nine steps of that slot were billed, through turn 2 step 0 at 11:40:19 HKT Asia/Hong_Kong ($0.001870776000 to that point, included in the running ledger).
- No official result line and no sidecar were written for this slot (`append_result` only happens when the slot finishes).
- The next provider request hit the 120s HTTP timeout. That in-flight request may have been billed by the provider with no `bills.jsonl` row. It was not retried, to avoid double-sending a slot that already had billed steps and a possible unbilled mid-request charge.

Not sent after the stop (100 slots): `multi_turn_base_198` on all four arms, and every arm of `multi_turn_miss_func`, `multi_turn_miss_param`, `multi_turn_long_context`, `memory_kv`, `memory_vector`, `memory_rec_sum`, `web_search_base`, and `web_search_no_snippet`.

## Official accuracy (thinking off, partial-eval)

Accuracy is from official `bfcl evaluate --partial-eval` on the pinned Gorilla tree, one category and one model directory at a time. The four directories `deepseek-flash-thinking-off-U`, `-S`, `-X`, and `-SX` were registered in-process as `model_name="deepseek-flash"`, `is_fc_model=True`, `DeepSeekAPIHandler`. Thinking-on directories were not registered and do not exist. `all_scoring` was not passed. Score files: `/home/box/cos/clean-start-usx-pilot-2026-11-25/artifacts/score/`.

`n` is the number of in-scope pilot rows for that category (`live_parallel` n=2; all others n=3). The official scorer reports `correct / n_scored` on the IDs present in the result file. For an incomplete category those two numbers differ.

| Category | n in scope | U | S | X | SX |
|---|---:|---|---|---|---|
| multiple | 3 | 1/3 (33.3%) | 1/3 (33.3%) | 1/3 (33.3%) | 1/3 (33.3%) |
| parallel_multiple | 3 | 0/3 (0.0%) | 0/3 (0.0%) | 0/3 (0.0%) | 0/3 (0.0%) |
| live_multiple | 3 | 2/3 (66.7%) | 2/3 (66.7%) | 2/3 (66.7%) | 2/3 (66.7%) |
| live_parallel | 2 | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) |
| live_parallel_multiple | 3 | 1/3 (33.3%) | 1/3 (33.3%) | 1/3 (33.3%) | 1/3 (33.3%) |
| live_irrelevance | 3 | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) |
| live_relevance | 3 | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) |
| multi_turn_base | 3 | 2/2 (100%) | 2/2 (100%) | 2/2 (100%) | 1/1 (100%) |
| multi_turn_miss_func | 3 | not sent | not sent | not sent | not sent |
| multi_turn_miss_param | 3 | not sent | not sent | not sent | not sent |
| multi_turn_long_context | 3 | not sent | not sent | not sent | not sent |
| memory_kv | 3 | not sent | not sent | not sent | not sent |
| memory_vector | 3 | not sent | not sent | not sent | not sent |
| memory_rec_sum | 3 | not sent | not sent | not sent | not sent |
| web_search_base | 3 | not sent | not sent | not sent | not sent |
| web_search_no_snippet | 3 | not sent | not sent | not sent | not sent |
| **scored overall** (sum of official `correct_count` / `total_count` on finished ids only) | **47 planned** | **14/22** | **14/22** | **14/22** | **13/21** |

`multi_turn_base` notes: U/S/X scored the two finished ids (`multi_turn_base_120`, `multi_turn_base_86`); `multi_turn_base_198` was never sent. SX scored only `multi_turn_base_120`; `multi_turn_base_86` SX is the timed-out incomplete slot and is absent from the result file.

The overall numerators are the sum of the official per-category `correct_count` values (12 from the seven finished single-turn categories, plus 2 for U/S/X `multi_turn_base` and 1 for SX). Do not use the BFCL leaderboard `data_overall.csv` / group CSV percentages: those mix in unsent categories and full-set denominators, and are not this study's totals.

On every fully finished category the four arms have the same official accuracy in this partial draw.

## Tokens and USD by arm

All 151 billed requests used the peak rate card (cache hit $0.006, cache miss $0.30, output $1.2 per 1,000,000 tokens). Cache fields were provider-reported on every row (`assumed_all_miss`: none). `usage_inconsistent`: 0. No reasoning-token double count: reasoning is billed inside output.

SX token and USD totals are lower because `multi_turn_base_86` SX stopped after 9 billed steps and later slots were not sent.

| Arm | Prompt | Cache hit | Cache miss | Output | USD | Requests | Finished slots |
|---|---:|---:|---:|---:|---:|---:|---:|
| U | 99,669 | 69,120 | 30,549 | 4,203 | 0.014623020000 | 38 | 22 |
| S | 104,703 | 90,368 | 14,335 | 4,287 | 0.009987108000 | 39 | 22 |
| X | 102,559 | 94,848 | 7,711 | 4,296 | 0.008037588000 | 38 | 22 |
| SX | 89,544 | 82,432 | 7,112 | 4,079 | 0.007522992000 | 36 | 21 + 1 incomplete |
| **Total** | **396,475** | **336,768** | **59,707** | **16,865** | **0.040170708000** | **151** | **87 finished; 88 slots with at least one bill** |

### Spend by category (practical breakdown)

| Category | Requests | Slots with a bill | Prompt | Cache hit | Cache miss | Output | USD |
|---|---:|---:|---:|---:|---:|---:|---:|
| multiple | 12 | 12 | 6,870 | 3,328 | 3,542 | 1,008 | 0.002292168000 |
| parallel_multiple | 12 | 12 | 10,824 | 6,144 | 4,680 | 3,060 | 0.005112864000 |
| live_multiple | 12 | 12 | 10,824 | 4,864 | 5,960 | 800 | 0.002777184000 |
| live_parallel | 8 | 8 | 4,300 | 2,432 | 1,868 | 664 | 0.001371792000 |
| live_parallel_multiple | 12 | 12 | 21,546 | 13,312 | 8,234 | 1,834 | 0.004750872000 |
| live_irrelevance | 12 | 12 | 19,268 | 12,800 | 6,468 | 943 | 0.003148800000 |
| live_relevance | 12 | 12 | 13,860 | 10,112 | 3,748 | 987 | 0.002369472000 |
| multi_turn_base | 71 | 8 | 308,983 | 283,776 | 25,207 | 7,569 | 0.018347556000 |
| **Total** | **151** | **88** | **396,475** | **336,768** | **59,707** | **16,865** | **0.040170708000** |

The first arm of a case pays more cache-miss USD; later arms show higher cache-hit counts.

## Notes

- Memory rows were not reached. Even if they had been, they would not be a full official memory score because prerequisites are excluded from this pilot.
- Missing slots: 101 of 188 (1 started and unfinished, 100 never started), as listed under Completeness.
- Executor errors: none recorded. The stop was a provider HTTP timeout.
- Unbilled mid-request kill: possible, on the request after `multi_turn_base_86` SX turn 2 step 0. Not retried.
- Cache: no `assumed_all_miss` rows.
- Ungrammatical X cues were not fixed on this tip.
- This is not official settlement. official_settlement remains false.
- Web-search slots were not reached; `SERPAPI_API_KEY` was not set on the box, which would have mattered only if those slots had run.
- Forced-quit sidecars: none among the 87 finished slots.
- The API key was confirmed set and was not printed, logged, or written to any file in this directory.

## Artifact paths

- Briefing: `/home/box/cos/clean-start-usx-pilot-2026-11-25/RESULTS.md`
- Driver: `/home/box/cos/clean-start-usx-pilot-2026-11-25/run_thinking_off_pilot.py`
- run.json: `/home/box/cos/clean-start-usx-pilot-2026-11-25/artifacts/run.json`
- spend.json: `/home/box/cos/clean-start-usx-pilot-2026-11-25/artifacts/spend.json`
- bills.jsonl: `/home/box/cos/clean-start-usx-pilot-2026-11-25/artifacts/bills.jsonl`
- Official result files: `/home/box/cos/clean-start-usx-pilot-2026-11-25/artifacts/result/deepseek-flash-thinking-off-<U|S|X|SX>/...`
- Sidecars: `/home/box/cos/clean-start-usx-pilot-2026-11-25/artifacts/model_outputs/deepseek-flash-thinking-off/<arm>/...`
- Official scores: `/home/box/cos/clean-start-usx-pilot-2026-11-25/artifacts/score/`
- Logs: `/home/box/cos/clean-start-usx-pilot-2026-11-25/logs/`
