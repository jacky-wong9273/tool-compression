# Validation thinking-OFF flight — 0bf829c6

official_settlement: false. This is not official settlement and not a full official BFCL score.

PR #28 tip `0bf829c6c2d24e5efa0483c7447c7ed0df4c53b9`. Editors remain the tip's pinned rules (`s-rules-2026-11-25.2`, `x-rules-2026-11-25.3`). Pinned Gorilla `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`. Both GitHub pytest jobs on this SHA succeeded (runs 45603020163 / 45603031501, jobs 139166535944 / 139166575183). Checkout was clean and detached before launch. Prior pilot artifacts were not modified.
Start 2026-11-25T19:22:21.886929+08:00 HKT Asia/Hong_Kong; last journal event 2026-11-25T20:41:33.220374+08:00 HKT Asia/Hong_Kong. PID 1642321.
First billed request: attempt 1, multiple_180 arm U, band off_peak (send band off_peak), completed 2026-11-25T19:22:25.499714+08:00 HKT Asia/Hong_Kong, prompt_tokens 802.

Observed status **INCOMPLETE — original process lost during box environment interruption**. The immutable original run.json still says running; that is stale metadata, not an active process. Finished scoring **1214/1252**; prerequisite runner-finished **20/60**; total slots sent 1234/1312. Provider billed responses 2481; ledger USD **0.346230789000 / $20**; inferred uncertain attempt **2482**. Original run.json/spend.json lag one bill: 2480 responses and $0.346140159000. No retry or resume.
Completion bands {'off_peak': 2481}; send bands {'off_peak': 2481}. Cache field assumptions {'reported': 2481}.

## Official accuracy
Official pinned evaluator, `is_fc_model=True` and `underscore_to_dot=True`; `--partial-eval`; one arm and one scoring category at a time. Prerequisite result files were skipped. Cells are correct/scored on the IDs present in that arm's result file. Absent results are not zeros. Memory accuracy is only meaningful if the matched notetaker prerequisites finished for that arm.

| Category | Frozen n | U | S | X | SX | Common complete n | Matched U/S/X/SX correct |
|---|---:|---|---|---|---|---:|---|
| multiple | 64 | 59/64 (92.2%) | 59/64 (92.2%) | 59/64 (92.2%) | 60/64 (93.8%) | 64 | 59/59/59/60 |
| parallel_multiple | 64 | 58/64 (90.6%) | 56/64 (87.5%) | 57/64 (89.1%) | 56/64 (87.5%) | 64 | 58/56/57/56 |
| live_multiple | 64 | 52/64 (81.2%) | 51/64 (79.7%) | 52/64 (81.2%) | 50/64 (78.1%) | 64 | 52/51/52/50 |
| live_parallel_multiple | 21 | 15/21 (71.4%) | 15/21 (71.4%) | 16/21 (76.2%) | 15/21 (71.4%) | 21 | 15/15/16/15 |
| live_irrelevance | 64 | 54/64 (84.4%) | 54/64 (84.4%) | 50/64 (78.1%) | 53/64 (82.8%) | 64 | 54/54/50/53 |
| live_relevance | 8 | 6/8 (75.0%) | 6/8 (75.0%) | 7/8 (87.5%) | 7/8 (87.5%) | 8 | 6/6/7/7 |
| multi_turn_base | 4 | 3/4 (75.0%) | 3/4 (75.0%) | 3/4 (75.0%) | 3/4 (75.0%) | 4 | 3/3/3/3 |
| multi_turn_miss_func | 4 | 0/4 (0.0%) | 0/4 (0.0%) | 0/4 (0.0%) | 2/4 (50.0%) | 4 | 0/0/0/2 |
| multi_turn_miss_param | 4 | 1/4 (25.0%) | 2/4 (50.0%) | 1/4 (25.0%) | 2/4 (50.0%) | 4 | 1/2/1/2 |
| multi_turn_long_context | 4 | 2/4 (50.0%) | 3/4 (75.0%) | 3/4 (75.0%) | 3/4 (75.0%) | 4 | 2/3/3/3 |
| memory_kv | 4 | 1/3 (33.3%) | 2/3 (66.7%) | 0/2 (0.0%) | 1/2 (50.0%) | 2 | 0/1/0/1 |
| memory_vector | 4 | not scored | not scored | not scored | not scored | 0 | — |
| memory_rec_sum | 4 | not scored | not scored | not scored | not scored | 0 | — |
| **Matched overall** | **313** |  |  |  |  | **303** | **250/250/248/252** |

The matched column uses only case IDs finished on all four arms, so the denominator does not mix partial coverage.

## First-request prompt_tokens (token measure)
The validation token measure is the provider-reported `prompt_tokens` on each slot's first request (turn 0, step 0). Later trajectory steps, cache hits on later arms, and output tokens are not this measure. Scoring cases only.

| Arm | First requests | Prompt | Cache hit | Cache miss | Output (not the measure) |
|---|---:|---:|---:|---:|---:|
| U | 304 | 335414 | 193631 | 141783 | 38561 |
| S | 304 | 322552 | 186474 | 136078 | 38315 |
| X | 304 | 336798 | 201196 | 135602 | 38415 |
| SX | 303 | 321253 | 189928 | 131325 | 38385 |
| Total | 1215 | 1316017 | 771229 | 544788 | 153676 |

Paired first-request prompt_tokens on the 303 scoring cases finished on every arm:
| Arm | Requests | Prompt | vs U | Cache hit | Cache miss |
|---|---:|---:|---:|---:|---:|
| U | 303 | 332874 | +0 (+0.00%) | 191327 | 141547 |
| S | 303 | 320284 | -12590 (-3.78%) | 184426 | 135858 |
| X | 303 | 334037 | +1163 (+0.35%) | 198636 | 135401 |
| SX | 303 | 321253 | -11621 (-3.49%) | 189928 | 131325 |
Rotated arm order and cache hits mean later arms are not a pure compression contrast, even on first requests.

## Local catalogue token deltas (tiktoken o200k_base)
Local tiktoken o200k_base counts of the initial catalogue of each of the 313 validation scoring questions, once per question. field_tokens sums editable function and parameter descriptions. tools_tokens counts compact JSON of the whole tools array. Not provider-billed usage; held-out later turns are excluded.
| Arm | Description fields | Full tools array | Description vs U | Tools vs U |
|---|---:|---:|---:|---:|
| U | 123618 | 254358 | 0 (0.00%) | 0 (0.00%) |
| S | 109880 | 240476 | -13738 (-11.11%) | -13882 (-5.46%) |
| X | 125043 | 255783 | 1425 (1.15%) | 1425 (0.56%) |
| SX | 111305 | 241901 | -12313 (-9.96%) | -12457 (-4.90%) |

## Spend by arm, scoring vs prerequisites
Prompt = cache hit + cache miss. Output is billed separately; reasoning tokens are not added twice. Prerequisite spend is kept separate from scoring spend. Cache and output differences are not pure editor savings.

### scoring
| Arm | Requests | Prompt | Cache hit | Cache miss | Output | USD |
|---|---:|---:|---:|---:|---:|---:|
| U | 515 | 1374667 | 1137631 | 237036 | 55834 | 0.072468693000 |
| S | 522 | 1239934 | 1008874 | 231060 | 55755 | 0.071138622000 |
| X | 533 | 1492713 | 1257580 | 235133 | 57806 | 0.073726290000 |
| SX | 509 | 1198551 | 973928 | 224623 | 54842 | 0.069520434000 |
| Total | 2079 | 5305865 | 4378013 | 927852 | 224237 | 0.286854039000 |
### prerequisite
| Arm | Requests | Prompt | Cache hit | Cache miss | Output | USD |
|---|---:|---:|---:|---:|---:|---:|
| U | 94 | 407509 | 378624 | 28885 | 13907 | 0.013812822000 |
| S | 114 | 508852 | 476672 | 32180 | 16626 | 0.016232616000 |
| X | 96 | 430569 | 400256 | 30313 | 13417 | 0.013797918000 |
| SX | 98 | 444167 | 414848 | 29319 | 16485 | 0.015533394000 |
| Total | 402 | 1791097 | 1670400 | 120697 | 60435 | 0.059376750000 |
### all
| Arm | Requests | Prompt | Cache hit | Cache miss | Output | USD |
|---|---:|---:|---:|---:|---:|---:|
| U | 609 | 1782176 | 1516255 | 265921 | 69741 | 0.086281515000 |
| S | 636 | 1748786 | 1485546 | 263240 | 72381 | 0.087371238000 |
| X | 629 | 1923282 | 1657836 | 265446 | 71223 | 0.087524208000 |
| SX | 607 | 1642718 | 1388776 | 253942 | 71327 | 0.085053828000 |
| Total | 2481 | 7096962 | 6048413 | 1048549 | 284672 | 0.346230789000 |

## Limitations and evidence
- official_settlement remains false. No full-BFCL or official settlement claim.
- No thinking-on, no SerpAPI, no web-search sets, no second U, no live_parallel, no merge, no push, no editor changes, no retry/resume.
- Scope: 328 conversations / 1312 thinking-off slots (1252 scoring + 60 matched notetaker prerequisite slots). Memory is last. A $20 ceiling stop is a valid incomplete end.
- An uncertain failed/incomplete request may be charged without a ledger usage row. Recorded spend is not a guaranteed final invoice.
- First-request prompt_tokens is the token measure requested for this flight; later-step and cache/output totals are reported separately as caveats.
- Attempts, bills, per-step sidecars, arm-isolated result files, and official scores are in the live out directory.
- The API key was confirmed present and was not printed, logged, or copied.

## Exact invocation
```
/workspace/tool-compression-usx-12-2026-11-23/venv/bin/python -m tool_compression.clean_start run --validation --live --authorize-live --thinking off --memory-prereqs matched --ceiling-usd 20 --bfcl-root /workspace/tool-compression-flash-2026-11-17/gorilla --out /home/box/cos/clean-start-usx-validation-2026-11-25/live-0bf829c6
```

Artifact root: `/home/box/cos/clean-start-usx-validation-2026-11-25/live-0bf829c6`. STARTED.json: `/home/box/cos/clean-start-usx-validation-2026-11-25/STARTED.json`.

## Recovered offline evaluation and interruption accounting
- Offline recovery succeeded. **Sanctioned evaluate CLI exit code 0**, 44 arm/category scoring jobs successful, 0 failed. Config: DeepSeekAPIHandler, is_fc_model=True, underscore_to_dot=True; partial-eval; prerequisite files skipped. No evaluator or editor code was changed. No new live requests, inference retries, or flight resumes occurred.
- Dedicated environment: `/home/box/cos/clean-start-usx-validation-2026-11-25/evaluator-env`, Python 3.12.16. Installed public dependencies from the pinned Gorilla metadata; added its required qwen-agent and soundfile import dependencies. Vector inference libraries were unnecessary for these preserved results. Initial import attempts failed until these dependencies were present; final scoring succeeded. Logs: `evaluate-recovered-3.stdout.log`, `evaluate-recovered-3.stderr.log`. No unit suite rerun was needed; official scorer execution is the evaluation evidence.
- box-doctor: 11 checks, 0 failed; 114 GB free at diagnosis. Exact repo/Gorilla SHAs survived. The old /workspace venv was genuinely missing after environment interruption.
- Start **2026-11-25 19:22:21.887 HKT Asia/Hong_Kong**. Last completed response **20:41:33.220 HKT**; last sent request **20:41:33.245 HKT**. Exact process termination time is unknown; absence was confirmed around 20:53 HKT. The observed process loss—not the $20 ceiling—ended the flight.
- Attempt **2482**, memory_kv_136-notetaker-6, X, turn 0 step 1, is sent without a completion/failure journal event. Possible charge unknown. 2482 sends, 2481 billed responses. No replay was made.
- Finished scoring slots: U304/S304/X303/SX303 =1214/1252. Prerequisites:20/60. 78 total slots did not finish. One active scoring slot has a billed response but no finished result. There are 1234 finished sidecars.
- All **20 KV notetaker prerequisite slots finished, none forced quit**. Thus the two common KV scoring cases have matched completed prerequisite coverage across arms. This remains a narrow notetaker-only partial memory comparison, not a full official memory benchmark. U/S have one extra KV scoring result each; use the matched 2-case denominator rather than mixing 3/3/2/2. Neither vector nor recursive-summary prerequisites/scoring ran.
- One finished scoring trajectory forced quit: multi_turn_miss_func_9, S. It remains in official scoring; not silently excluded.
- Matched 303-case overall accuracy: **U250/303 (82.51%), S250/303 (82.51%), X248/303 (81.85%), SX252/303 (83.17%)**. Tiny differences are descriptive, not statistical significance claims.
- All billed responses were off-peak, cache fields reported. Ledger cost: scoring $0.286854039 + prerequisites $0.059376750 =$0.346230789. Possible additional charge for attempt2482 is unknown.
- SHA256 checks confirm attempts.jsonl, bills.jsonl, run.json and spend.json are unchanged by recovery. Old blocked reports preserved as `RESULTS-blocked-evaluator-historical.md` and `FINAL-blocked-evaluator-historical.json`. Prior pilot evidence also untouched. Both tracked repository trees remain clean.
- No original API key was read for recovery: live credential variables were removed from the evaluator subprocess; the sanctioned scorer uses constructor-only dummy credentials and no provider requests.
