# Full in-scope flight, thinking off, 12,952 slots

This is the package for the full in-scope clean-start fly. It is not started, and nothing in this package contacts a provider or reads a key. `official_settlement` is false. Jacky has not named a ceiling for it: the $42 / 280 CNY cap belongs to the 20% preliminary only.

Scope: 3,127 in-scope scoring questions in the 14 in-scope categories, plus the 111 memory prerequisites their scenarios load. That is 3,238 conversations on arms U, S, X and SX, thinking off: 12,952 slots. Every prerequisite scenario is one an in-scope question uses, so the full catalogue's prerequisites and the matched prerequisites are the same 111 conversations. Editors were `s-rules-2026-11-26` and `x-rules-2026-11-26` when this package was preflighted at `6d4081e3`. This branch carries `s-rules-2026-11-27` and `x-rules-2026-11-27` (`REVISION-preliminary-69f33cdc.md`): a fly from it sends the revised editors, needs its own box preflight, and cannot resume a run started at `6d4081e3`, because the run identity records the editor rules. `full/cost.json` stays the plan priced at `6d4081e3`; under the revised editors its gates (ceiling floor, observed-mean and higher-step paths) are unchanged and its first-request figures move by less than a cent. SX is exact S, then X. Out of scope: the official simple sets, web-search sets, SerpAPI, and thinking on. Gorilla pin `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`, model `deepseek-flash`, no `max_tokens`.

Committed files: `full/plan.json` (SHA-256 `fe1059fc5fdb15c59d9aa985072a6a9952cf949e59e149cfd4c4d407dd5326ac`, the case ids in run order) and `full/cost.json` (cost, time, peak and ceiling floor; it records the plan digest). Thinking-off slot SHA-256: `8fff8cd902b3c523473cf38591a20d3719b0c028138728f46632867fc655047f`. The live CLI refuses any other plan or slot order.

## Start gates

All of these must hold before the live command. The CLI enforces the first, the fifth and the seventh. The rest are the operator's.

1. Not before **Friday 27 Nov 2026 18:00:00 HKT**. The CLI reads the box clock, so the box clock must be NTP-synced.
2. The packaged tip is pushed, and the box checkout is exactly that tip. `source_sha256` of `src/tool_compression` is in the run identity.
3. This package is CLEARED, pending the box preflight below.
4. The box preflight passes.
5. The fresh start is off-peak. The CLI refuses a fresh `--full` start inside a rate-card peak window (weekdays 09:00-12:00 and 14:00-18:00 HKT). Friday 18:00 is off-peak. A `--resume` is allowed in peak; the ceiling still applies.
6. The 20% preliminary, and every other clean-start live run, is finished or stopped for good. The CLI cannot see another box's run.
7. Jacky has named a ceiling. `--full` without `--ceiling-usd` exits 2. A ceiling under the **$68.54 floor** (456.81 CNY) exits 2. The prepaid balance must cover the ceiling.
8. `official_settlement` stays false.

Do not fly the superseded 119-case / $12 command, tip `90f675da`, tip `00452963`, or any full 12,952-slot command without `--full`. The plain `run --live` path now refuses the full catalogue. Only `--full` has the 20 s / 60 s deadlines, skip-and-record, and `--resume`.

## Commands

Dry plan. No `--live`. Writes `run.json`, reads no key, opens no socket:

```bash
python -m tool_compression.clean_start run --full --thinking off \
  --memory-prereqs matched --ceiling-usd <CEILING_USD> --out /tmp/full-plan
```

The plan reports `provider_contacted: false`, `full: true`, `slots_total: 12952`, `slot_sha256` `8fff8cd9…`, `read_timeout_seconds: [20.0, 60.0]`, `total_deadline_seconds: [20.0, 60.0]`, and `retry_policy.after_last_failure: "skip_and_record"`.

Live run. `--out` is a new empty directory on storage that outlives the box. `DEEPSEEK_API_KEY` is set in that shell only and is never printed. No SerpAPI key is set. `<CEILING_USD>` is the ceiling Jacky names, at least 68.54:

```bash
python -m tool_compression.clean_start run --full --live --authorize-live \
  --thinking off --memory-prereqs matched --ceiling-usd <CEILING_USD> \
  --bfcl-root /path/to/gorilla --out /path/to/new-empty-dir
```

Exit codes: 0 means the run completed (skipped slots included), 1 means it stopped incomplete (resume it), and 2 means it was refused before any request.

Resume check. Reads the directory, prints what a resume would skip, send again and repair, and writes nothing:

```bash
python -m tool_compression.clean_start run --full --resume \
  --thinking off --memory-prereqs matched --ceiling-usd <CEILING_USD> \
  --out /path/to/the-same-dir
```

Resume. Same tip, same `--out`, same ceiling. Repeat after every stop until it exits 0:

```bash
python -m tool_compression.clean_start run --full --live --authorize-live \
  --thinking off --memory-prereqs matched --ceiling-usd <CEILING_USD> \
  --bfcl-root /path/to/gorilla --out /path/to/the-same-dir --resume
```

Score, against the same pin. Contacts no provider:

```bash
python -m tool_compression.clean_start evaluate \
  --out /path/to/the-same-dir --bfcl-root /path/to/gorilla --thinking off
```

## Send policy

`FULL_FLY_POLICY`, named `deadline-20s-retry-60s-skip`, is recorded in `run.json` under `retry_policy`.

- **First try: 20 s.** This is wall clock from the start of the try. It covers DNS, connect, TLS, writing the request, the response headers and the whole body. Keep-alive bytes do not extend it. At the deadline the socket is shut down under the blocked reader, and the try fails with `TotalDeadlineExceeded`. A worker still in DNS or connect is told not to write the request.
- **One retry: 60 s.** Same body, and the ceiling is checked again first. There is no pause after a timeout or a dropped connection, because the 20 s already waited is the pause. A fast HTTP 429 or 5xx waits 2 s first.
- **Then skip and record.** If the retry also fails in transport, the slot is skipped. The run goes on to the next slot. `failures.jsonl` gets one fsynced line with the case id, category, arm, thinking, turn and step, the error and HTTP status, and every try with its `sent_at`, `failed_at`, deadline, elapsed seconds and `may_be_billed: true`. It also records the billed steps before the skip, the policy and the session. No output is invented. The slot writes no result line, and its sidecar says `skipped`.
- **These still stop the run**, for a resume: other 4xx (402 is an empty balance), a 200 without billed usage or a choice, an executor error, and the ceiling.
- **Outage breaker.** Two skipped slots in a row are allowed. A third consecutive skip stops the run instead (`skip_streak:3:<error>`). The third slot is not recorded as skipped, and `--resume` sends it again from its first request.
- **Memory chains.** One chain is one arm on one memory backend and one scenario. Every entry after a scenario's `-0` prerequisite loads `<scenario>_final.json`, which only a prerequisite writes. If a prerequisite is skipped, every later slot of its chain is recorded as `dependency_skipped` without a request. Each backend has five scenarios, so one skipped prerequisite costs that arm 25 to 50 scoring slots: 50 for student, 30 for customer, 25 for the others.

Why. On 69f33cdc, `run.json` advertised `read_timeout_seconds: 120`. Attempt 218 was sent at 18:16:31 HKT and failed with `TimeoutError` at 18:24:24 HKT, 473 s later. DeepSeek keeps a queued non-streaming request open by sending blank lines. Every byte restarted the 120 s socket timer, so the blank lines held it for about six minutes, and then 120 s of silence raised the error. A socket timeout bounds one read, not a request. The new deadline is a wall clock over the whole try, enforced from outside the reading thread. Tests run it against a local server that trickles keep-alive bytes. One test waits out the real 20 s; an opt-in test (`TC_REAL_DEADLINES=1`) waits out 20 s and then 60 s.

Is 20 s long enough? The archived flights have 3,380 completed sends: 899 on c47b186c and 2,481 on 0bf829c6. Their slowest answer took 10.8 s, on a `memory_kv` prerequisite. None took more than 15 s. On 0bf829c6 the median was 1.84 s and the 99th percentile 3.25 s. So 20 s is about twice the slowest answer seen, and a try that reaches it is very likely queued, not working. Before the full fly, read the latency tail of the 20% run's `attempts.jsonl` (`completed.at` minus `sent_at`). If more than a few answers took over 15 s, raise this before flying, because the 20 s deadline would then cut real answers.

The preliminary policy is unchanged: two retries after 10 s and 30 s, a 120 s socket timeout and a 900 s total deadline, then stop. The in-flight 20% run stays on 69f33cdc. It must be resumed from the 69f33cdc checkout, because a resume from this tip is refused on `source_sha256`.

## Resume

A resume refuses, with exit 2 before the key is read and with nothing written, unless `run.json` contacted a provider, is not complete, and matches on every identity field. The identity fields are the `full/plan.json` digest, the slot order, the case ids, the editors, `source_sha256`, the policy name and its deadlines, thinking off, the ceiling and the rate card. A different ceiling is refused, so raising the ceiling mid-run takes a new decision. It cannot be done by resuming.

- A slot is done when it is finished (its sidecar says `finished`, plus one result line) or skipped (it has a `failures.jsonl` record). Done slots form a prefix of the slot order. Skipped slots are never sent again.
- Every skip record must name failed attempts that are in `attempts.jsonl` for that slot. A record for a slot past the stop, a duplicate record, or a result line for a skipped slot is refused.
- If the box was lost after the failure line but before the sidecar, the resume marks the sidecar `skipped`. Its old copy goes under `resume/session-<n>/`.
- Chains broken by a skipped prerequisite stay broken across sessions.
- The stopped slot is sent again from its first request. Memory snapshots are rolled back to the last finished prerequisite's checkpoint, as in the preliminary.
- Spend restarts from the sum of `bills.jsonl` over every session, against the same ceiling.

Result lines, sidecars, `attempts.jsonl`, `bills.jsonl`, `failures.jsonl`, memory flushes, `run.json` and `spend.json` are fsynced as they are written. The directory is fsynced too, whenever a file is created or replaced.

## Scoring, tokens and spend

- **Accuracy.** `evaluate` runs the pinned `bfcl evaluate` with `partial_eval`, which scores only ids that have a result line. `evaluate_summary.json` has a `ledger` block that lists every skipped and dependency-skipped slot by model and category. An all-ids accuracy counts those slots as not correct.
- **Tokens.** Total tokens are prompt plus output over every row of `bills.jsonl`. Reasoning tokens are inside output and are not added again. `spend.json` and `run.json` carry the running totals, and the evaluation ledger carries them per model.
- **Spend.** Every bill row has its own `usd` and the `running_usd` after it. Tries that failed may be billed, but have no usage to record. They are listed under `unbilled_attempts` and are not in the running total. The ceiling floor below prices them in.

## Cost and time

Rates: off-peak $0.15 per 1M cache-miss prompt tokens, $0.003 per 1M cache hits, and $0.60 per 1M output tokens. Peak is double, weekdays 09:00-12:00 and 14:00-18:00 HKT. The CNY rate is 6.6649 per USD. Every path below is all cache-miss.

Each time profile is serial, starting Friday 18:00 HKT. Seconds per send are the pace, plus the hang rate times the 20 s first deadline; the retry after a hang is already counted as a send. A send inside a peak window costs double. A hung first try is priced as billed, at its case's mean cost per send.

| profile | sends | hours | finish HKT | peak premium | USD with peak and hung tries |
| --- | ---: | ---: | --- | ---: | ---: |
| mean, 1.9 s, 1.5% hangs | 70,144 | 42.87 | Sun 29 Nov 12:52 | $0 | $59.57 |
| mean, 2.0 s, 1.5% hangs | 70,144 | 44.81 | Sun 29 Nov 14:49 | $0 | $59.57 |
| mean, memory 3.3 s and the rest 2.0 s, 1.5% hangs | 70,144 | 50.10 | Sun 29 Nov 20:06 | $0 | $59.57 |
| higher-step, memory 3.3 s and the rest 2.0 s, 3% hangs | 81,987 | 67.36 | Mon 30 Nov 13:22 | $2.06 | $60.72 |
| mean, 3.3 s, 3% hangs | 70,144 | 75.99 | Mon 30 Nov 21:59 | $8.08 | $68.54 |
| planning allowance, 1.9 s, no hangs | 139,988 | 73.88 | Mon 30 Nov 19:53 | $31.57 | $286.00 |
| planning allowance, 1.9 s, 1.5% hangs | 139,988 | 85.55 | Tue 1 Dec 07:33 | $26.44 | $284.69 |
| planning allowance, 3.3 s, 3% hangs | 139,988 | 151.65 | Fri 4 Dec 01:39 | $53.40 | $315.47 |

The observed mean is $58.692511 (391.18 CNY) over 70,144.24 sends. The higher-step path is 81,987.11 sends at $56.949778. It costs less, because the flight with more steps per turn is the cheaper one per turn for memory and `miss_param`. The off-peak planning upper is $254.432685 (1,695.77 CNY) over 139,988 allowance requests.

**Ceiling floor: $68.54 (456.81 CNY).** This is the costliest observed-mean or higher-step profile (mean, 3.3 s, 3% hangs), with its Monday peak premium and its hung first tries billed. The CLI refuses a lower ceiling. A ceiling at the floor should finish the mean paths, but not an allowance-sized fat tail. It is not a recommendation; Jacky names the ceiling.

### Review of the 26 Nov ESTIMATES

The catalogue, the rate card, and the 20% package's observed-mean method are the ones used here. None was substituted. Confirmed:

- The send table: 7,448 / 9,856.57 / 11,744 / 16,524.62 / 9,934.36 / 14,636.69 sends, $58.692505 total. The exact sum is $58.692511 over 70,144.240105 sends; the ESTIMATES figure adds rounded rows, and the difference is immaterial. 391.18 CNY is confirmed.
- The higher-step 81,987.11 sends, with `miss_param` 3.705882 (252/68) and memory 3.934579 (421/107) from 0bf829c6.
- About 43 h at 1.9 s and 45 h at 2.0 s with 1.5% hangs. The 43 h path finishes about Sunday 13:00 HKT, all off-peak.
- About 67 h on the higher-step 95% path and about 76 h on the mean path at 3.3 s with 3% hangs. Friday 18:00 plus 75 h is Monday about 21:00, which crosses Monday peak.
- 10 h is 18,947 sends at 1.9 s (27%) and 18,000 at 2.0 s (26%). That would need 3.70 to 3.90 requests in flight on the mean path, ignoring hangs.
- The off-peak planning upper is $254.43 (1,695.75 CNY; 1,695.77 unrounded). $315 is 2,099.44 CNY. Budgets A and B, and their CNY values, are confirmed as arithmetic, and B is about 21% of A. A and B come from earlier files and were not re-derived here.
- About 1,050 extra first attempts at a 1.5% hang rate (1,052). Priced as billed, they are about $0.88. At 3% they are $1.76.

Corrected:

1. **"Memory at 3.3 s and the rest at 2.0 s: about 49 hours" is 50.1 h**, finishing Sunday about 20:06 HKT, still off-peak. 49 h leaves out the hang overhead on memory sends.
2. **"The earlier planning-upper path at 1.9 s was about 75 hours" is 73.9 h** without hangs. With 1.5% hangs it is 85.6 h. This is minor; 75 h stays a fair 95% wall-clock.
3. **"$275.31 (1,834.91 CNY) if the 75-hour path runs into Monday peak" is $286.00 (1,906.19 CNY).** That is the planning upper at 1.9 s from Friday 18:00, with its Monday 09:00-12:00 and 14:00-18:00 sends at double. The comfortable 95% budget with Monday peak should read **about $286 / 1,906 CNY**, not $275 / 1,835.
4. $315 / 2,099 CNY still covers every allowance profile up to 3.3 s with 3% hangs at peak ($307.83). If every hung first try on that slowest path were also billed, the total would be $315.47, just over.
5. The 67 h higher-step path finishes Monday 13:22 HKT, inside Monday's first peak window, so it pays a $2.06 premium. The 50% paths pay none.
6. With 1.5% hangs, ten hours would need 4.3 to 4.5 requests in flight, not 3.7 to 3.9. Each hang adds 20 s.

## The 10-hour constraint

It is not feasible on the serial runner, and this package does not add concurrency. The mean path alone is about 37 h of successful requests at 1.9 s. The 20 s / 60 s policy cuts hang waste, not work. It matters even so: at 1.5% hangs, 69f33cdc's timeouts would waste about 1,052 × 7 min, or roughly 120 h. The 20 s deadline wastes about 5.8 h. The serial fly from Friday 18:00 is expected to finish Sunday afternoon or evening (43-50 h). At 95% it finishes Monday night (67-76 h).

If ten hours is required, this is the shape I would propose. It is not implemented, and it waits for Jacky:

- **Shards.** Run K separate processes over disjoint, contiguous slot ranges cut at case boundaries. Each memory backend goes to a shard whole, or is split by arm, so no chain crosses shards. Each shard gets its own `--out`, ledgers, failure list, breaker and `--resume`, and the identity adds the shard index and range.
- **In flight.** K = 5 is about 8.6 h on the 1.9 s median path with 1.5% hangs, before imbalance. K = 4 is about 10.7 h and does not make it. At 95% paces, even K = 5 is 15 h.
- **Spend and ceiling.** Split the named ceiling into K fixed shares, each checked before every request in its shard, so the total stays under the ceiling without a cross-process lock. The cost is that one shard can stop early while another still has headroom. The alternative is one shared spend ledger under a file lock, which is new code on the critical path.
- **Resume and failures.** These are per shard, as today. Evaluation needs a merge step that joins the K result trees per model and category, and joins the K failure lists. That is new code.
- **Rate-limit risk.** DeepSeek queues rather than refusing, so more in flight is likely to raise the hang rate and the 429s. The breaker stops a shard after a third consecutive skip, which turns an outage into K resumes. Cache-hit behaviour may change too.
- **Peak.** A ten-hour run from Friday 18:00 ends Saturday 04:00, all off-peak.

## Box preflight

On the box that will run it, before the live command:

- The Gorilla checkout is `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`.
- `all-MiniLM-L6-v2` revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` is already built. `sentence_transformers`, `faiss` and `numpy` import. The live shell sets `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`.
- `DEEPSEEK_API_KEY` is set in that shell and is not printed. No SerpAPI key is set.
- The repository checkout is the packaged tip, and `git status` is clean. A resume refuses any other source tree.
- The dry plan reports `slot_sha256` `8fff8cd902b3c523473cf38591a20d3719b0c028138728f46632867fc655047f` and `read_timeout_seconds` `[20.0, 60.0]`.
- `--out` is a new empty directory on storage that outlives the box. Do not reuse a pilot, validation or preliminary directory.
- The 20% preliminary is finished or stopped for good. Its directory and its 69f33cdc checkout are untouched.
- The box clock is NTP-synced. It is Friday 27 Nov 2026 18:00 HKT or later, off-peak.

## Risks

- The 20 s / 60 s policy, the skip path and `--full --resume` are tested against local sockets and mocks, never live.
- A try cut at its deadline may still be billed, because DeepSeek may finish it. It has no usage to record, so it is listed in `unbilled_attempts` and not counted in the running spend. The ceiling floor prices these tries in, but the provider balance is the final check.
- A skipped memory prerequisite costs its arm 25 to 50 scoring slots. Stopping the run instead, and resuming, would keep those slots at the price of a manual resume. The package skips, as specified.
- An outage of three or more consecutive slots stops the run, and it then needs a resume. During an outage two slots are skipped before the third stops the run. Those two stay skipped.
- Official accuracy over all 3,127 questions counts skipped slots as incorrect. Many skips in one arm would bias the arm comparison, so read the `ledger` block before reading any accuracy.
- A ceiling stop is final unless Jacky names a new ceiling. A resume with a different ceiling is refused, so a new ceiling needs a new decision on how to continue.

## What is in the fly

| category | scoring | prerequisites | user turns | slots |
| --- | ---: | ---: | ---: | ---: |
| multiple | 200 | 0 | 200 | 800 |
| parallel_multiple | 200 | 0 | 200 | 800 |
| live_multiple | 1,053 | 0 | 1,053 | 4,212 |
| live_parallel | 2 | 0 | 2 | 8 |
| live_parallel_multiple | 24 | 0 | 24 | 96 |
| live_irrelevance | 372 | 0 | 372 | 1,488 |
| live_relevance | 11 | 0 | 11 | 44 |
| multi_turn_base | 200 | 0 | 734 | 800 |
| multi_turn_miss_func | 200 | 0 | 934 | 800 |
| multi_turn_miss_param | 200 | 0 | 934 | 800 |
| multi_turn_long_context | 200 | 0 | 734 | 800 |
| memory_kv | 155 | 37 | 478 | 768 |
| memory_vector | 155 | 37 | 478 | 768 |
| memory_rec_sum | 155 | 37 | 478 | 768 |
| **total** | **3,127** | **111** | **6,632** | **12,952** |

Each memory backend has the same five scenarios. Student has 10 prerequisites and 50 questions, customer 10 and 30, finance 7 and 25, healthcare 5 and 25, and notetaker 5 and 25. Memory runs last. Each backend's prerequisites are sent, in loader order, before its questions.
