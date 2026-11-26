# Revised no-web thinking-OFF pilot — c47b186c

official_settlement: false. Not official settlement or a full BFCL score.

PR #28 tip `c47b186c6004e69840db3537ebe532dc22f638a8`; pinned Gorilla `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`. CI: two tip-matching pytest checks and router success. Checkout clean before launch.
Start 2026-11-25T16:46:03.834466+08:00 HKT Asia/Hong_Kong; last journal event 2026-11-25T17:22:14.793501+08:00 HKT Asia/Hong_Kong. PID 1606685.

Status **incomplete**; complete=False; reason=provider_error:IncompleteRead. Finished scoring **128/164**; prerequisite **12/216**; total 140/380. Provider sends 900 (899 billed responses + 1 uncertain failed response); billed provider requests 899; recorded USD **0.287883432000 / $20**; uncertain attempts [900]. No retry/resume.
Completion bands {'peak': 899}; send bands {'peak': 899}. Cache assumptions {'reported': 899}.

## Official accuracy
Official pinned evaluator, underscore_to_dot=True; partial-eval, one arm/category at a time. Cells correct/scored; absent results are not failures or zeros. Memory prerequisites excluded from accuracy.

| Category | Frozen n | U | S | X | SX | Common complete n | Matched U/S/X/SX correct |
|---|---:|---|---|---|---|---:|---|
| multiple | 3 | 3/3 (100.0%) | 3/3 (100.0%) | 3/3 (100.0%) | 3/3 (100.0%) | 3 | 3/3/3/3 |
| parallel_multiple | 3 | 3/3 (100.0%) | 3/3 (100.0%) | 3/3 (100.0%) | 3/3 (100.0%) | 3 | 3/3/3/3 |
| live_multiple | 3 | 3/3 (100.0%) | 3/3 (100.0%) | 3/3 (100.0%) | 3/3 (100.0%) | 3 | 3/3/3/3 |
| live_parallel | 2 | 2/2 (100.0%) | 2/2 (100.0%) | 2/2 (100.0%) | 2/2 (100.0%) | 2 | 2/2/2/2 |
| live_parallel_multiple | 3 | 2/3 (66.7%) | 2/3 (66.7%) | 2/3 (66.7%) | 2/3 (66.7%) | 3 | 2/2/2/2 |
| live_irrelevance | 3 | 3/3 (100.0%) | 3/3 (100.0%) | 3/3 (100.0%) | 3/3 (100.0%) | 3 | 3/3/3/3 |
| live_relevance | 3 | 3/3 (100.0%) | 3/3 (100.0%) | 3/3 (100.0%) | 3/3 (100.0%) | 3 | 3/3/3/3 |
| multi_turn_base | 3 | 3/3 (100.0%) | 3/3 (100.0%) | 3/3 (100.0%) | 3/3 (100.0%) | 3 | 3/3/3/3 |
| multi_turn_miss_func | 3 | 3/3 (100.0%) | 3/3 (100.0%) | 3/3 (100.0%) | 3/3 (100.0%) | 3 | 3/3/3/3 |
| multi_turn_miss_param | 3 | 1/3 (33.3%) | 1/3 (33.3%) | 1/3 (33.3%) | 0/3 (0.0%) | 3 | 1/1/1/0 |
| multi_turn_long_context | 3 | 1/3 (33.3%) | 0/3 (0.0%) | 2/3 (66.7%) | 0/3 (0.0%) | 3 | 1/0/2/0 |
| memory_kv | 3 | not scored | not scored | not scored | not scored | 0 | — |
| memory_vector | 3 | not scored | not scored | not scored | not scored | 0 | — |
| memory_rec_sum | 3 | not scored | not scored | not scored | not scored | 0 | — |

Matched column compares the same completed case IDs across all four arms. It is the fair denominator when a run is partial. Machine-readable common counts and raw official scores remain alongside this report.

## Tokens and spend
Prompt contains cache hit + miss. Output is separate; reasoning is not added twice. Prerequisite cost is kept separate.

### scoring
| Arm | Requests | Prompt | Cache hit | Cache miss | Output | USD |
|---|---:|---:|---:|---:|---:|---:|
| U | 150 | 660201 | 613248 | 46953 | 14902 | 0.035647788000 |
| S | 155 | 603367 | 550396 | 52971 | 15889 | 0.038260476000 |
| X | 154 | 697092 | 644992 | 52100 | 16224 | 0.038968752000 |
| SX | 144 | 557223 | 508032 | 49191 | 15295 | 0.036159492000 |
| Total | 603 | 2517883 | 2316668 | 201215 | 62310 | 0.149036508000 |
### prerequisite
| Arm | Requests | Prompt | Cache hit | Cache miss | Output | USD |
|---|---:|---:|---:|---:|---:|---:|
| U | 74 | 539737 | 518016 | 21721 | 20901 | 0.034705596000 |
| S | 64 | 426493 | 406656 | 19837 | 19183 | 0.031410636000 |
| X | 83 | 661324 | 637056 | 24268 | 22462 | 0.038057136000 |
| SX | 75 | 507467 | 485376 | 22091 | 20945 | 0.034673556000 |
| Total | 296 | 2135021 | 2047104 | 87917 | 83491 | 0.138846924000 |
### all
| Arm | Requests | Prompt | Cache hit | Cache miss | Output | USD |
|---|---:|---:|---:|---:|---:|---:|
| U | 224 | 1199938 | 1131264 | 68674 | 35803 | 0.070353384000 |
| S | 219 | 1029860 | 957052 | 72808 | 35072 | 0.069671112000 |
| X | 237 | 1358416 | 1282048 | 76368 | 38686 | 0.077025888000 |
| SX | 219 | 1064690 | 993408 | 71282 | 36240 | 0.070833048000 |
| Total | 899 | 4652904 | 4363772 | 289132 | 145801 | 0.287883432000 |

## Local frozen catalogue tokens vs observed provider usage
Local tiktoken o200k_base counts are not provider billed tokens. The initial catalogue is counted once per frozen scoring case, not every trajectory step; held-out additions are excluded. Description fields and complete compact-JSON tools array are distinct measurements.
| Arm | Description fields | Full tools array | Description change vs U | Tools change vs U |
|---|---:|---:|---:|---:|
| U | 38500 | 87106 | 0 (0.00%) | 0 (0.00%) |
| S | 28491 | 77112 | -10009 (-26.00%) | -9994 (-11.47%) |
| X | 39231 | 87837 | 731 (1.90%) | 731 (0.84%) |
| SX | 29222 | 77843 | -9278 (-24.10%) | -9263 (-10.63%) |

Observed provider totals below use only scoring cases finished on all four arms. They include evolving trajectories, responses, and unequal step counts; cache/spend changes are NOT pure compression savings, even with rotated arm order.
| Arm | Requests | Prompt | Output | Cache hit | Cache miss | USD | Prompt change vs U | Output change vs U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| U | 150 | 660201 | 14902 | 613248 | 46953 | 0.035647788000 | 0 | 0 |
| S | 155 | 603367 | 15889 | 550396 | 52971 | 0.038260476000 | -56834 | 987 |
| X | 154 | 697092 | 16224 | 644992 | 52100 | 0.038968752000 | 36891 | 1322 |
| SX | 144 | 557223 | 15295 | 508032 | 49191 | 0.036159492000 | -102978 | 393 |

## Limitations and evidence
- No thinking-on, full study, external web search, SerpAPI, merge, push, or retries. No API key printed, logged, or copied.
- Scope: 14 categories; 41 scoring cases plus 54 matched prerequisite conversations. Memory results are meaningful only when matched prerequisites finished for the same arm; inspect completeness before treating partial memory scores as valid.
- A failed/timed-out attempt can be charged without ledger usage; recorded spend is not guaranteed final provider billing. Do not fill gaps by re-sending.
- New S/X rules are pinned in run identity; editor limitations and semantic risks remain. No claim that lexical compression preserves every behavioral distinction.
- Attempts, bills, per-step sidecars, arm-isolated result files, memory snapshots and official scores are preserved in this run directory.

## Exact invocation
```
/workspace/tool-compression-usx-12-2026-11-23/venv/bin/python -m tool_compression.clean_start run --pilot --live --authorize-live --thinking off --memory-prereqs matched --ceiling-usd 20 --bfcl-root /workspace/tool-compression-flash-2026-11-17/gorilla --out /home/box/cos/clean-start-usx-revised-pilot-2026-11-25/live-c47b186c
```

Artifact root: `/home/box/cos/clean-start-usx-revised-pilot-2026-11-25/live-c47b186c`. Launch and first-request confirmation: `/home/box/cos/clean-start-usx-revised-pilot-2026-11-25/LAUNCH-c47b186c.json`, `/home/box/cos/clean-start-usx-revised-pilot-2026-11-25/STARTED.json`.

## Stop details and final integrity
- End: **2026-11-25 17:22:14 HKT Asia/Hong_Kong**. Provider attempt 900 failed with `IncompleteRead` (not a timeout), after approximately 3.8 seconds, on `memory_kv_prereq_3-customer-3`, SX, turn 0 step 6. Its six earlier billed steps survive in the stopped sidecar. Attempt 900 has no bill row and may still be charged.
- 240 slots did not finish: 36 scoring memory slots and 204 prerequisite slots (one of those started/stopped). No memory scoring question was reached; no memory accuracy claim is possible.
- One of the 12 runner-finished prerequisite slots hit the step limit: `memory_kv_prereq_2-customer-2` arm U has `forced_quit=true`. Thus runner-finished does not imply a fully completed prerequisite conversation. This did not enter any scoring accuracy denominator.
- Official offline evaluation succeeded on all 44 available arm/category combinations, with zero evaluator failures. Matching 32 complete scoring cases per arm: U 27/32 (84.375%), S 26/32 (81.25%), X 28/32 (87.5%), SX 25/32 (78.125%). These are small pilot results, not causal significance claims.
- 141 sidecars: 140 finished, 1 stopped. 48 official result files (including four prerequisite files), 44 scoring files. No thinking-on artifacts. Both checkout tracked trees remain clean.
- $20 is enforced against the package's recorded request-by-request ledger. The unknown charge for attempt 900 prevents claiming an exact final provider invoice total, though recorded spend is only $0.287883432.
- First-request proof: STARTED.json records first billed completion at 16:46:06 HKT Asia/Hong_Kong, arm U, multiple_142, peak. Old pilot artifacts were not changed.
