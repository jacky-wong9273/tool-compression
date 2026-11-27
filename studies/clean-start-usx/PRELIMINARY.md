# Preliminary flight, thinking off, 20% sample, 280 CNY

This is a preliminary sample, not a completed full-set study. `official_settlement` is false. The budget named for 26 Nov 2026 is 280 CNY prepaid. At the rates named with it (CGB USD/CNY middle 6.6649, mid-market CNYUSD 0.150079), forty-two dollars is 279.925800 CNY and 279.852611 CNY. The live ceiling is exactly `--ceiling-usd 42`. $42.01 is not this package. The superseded package was 119 scoring cases, fraction 0.0374, seed `20261127`, an 18:30 start, and a $12 ceiling inside 80 CNY. An earlier $27 ceiling inside 180 CNY is also superseded. This package does not contact a provider, read a key, or start the run.

The draw is `preliminary/draw.json`. Its SHA-256 (the file bytes) is `2904904116ca21ad8830f4bb2dfaaf9cfd1773124315a8a26fe934f3490a785a`. The same digest is `draw_sha256` in `preliminary/cost.json`. Seed `20261128`, because `20261125` is the pilot seed, `20261126` is the committed validation seed, and `20261127` is the superseded 119-case preliminary. Python 3.12 `random.Random`. Editors stay `s-rules-2026-11-26` and `x-rules-2026-11-26`. SX is the exact S catalogue plus the exact X cue. The interrupted 69f33cdc flight of this draw is diagnosed in `REVISION-preliminary-69f33cdc.md`. Code carrying the revised editors (`s-rules-2026-11-27`, `x-rules-2026-11-27`) refuses to resume that run, because the run identity records the editor rules. `preliminary/cost.json` stays the plan that flight used; `package/preliminary_20261128.json` recomputes it with the revised editors. The draw was chosen from ids and population counts. It does not read gold, saved answers, or scores. Archived bills are used only for the allowance and the observed-mean estimate.

Gorilla pin: `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`. Model `deepseek-flash`, thinking disabled, no `max_tokens`. A send that fails in transport is sent again at most twice. A stopped run is continued with `--resume` in the same directory (see [Resume](#resume)). Arms U, S, X, SX. No web-search category and no SerpAPI call. The evaluator registers `is_fc_model=True` and `underscore_to_dot=True`, and it skips result files whose names contain `prereq`.

## Commands

Every preliminary command passes `--thinking off`. Omitting `--thinking` exits 2 and does not fall through to the full-run default of thinking off and on. A dry plan still drops both live flags. The plan file records `ceiling_usd` as null; the live path still requires the ceiling and checks it before every request. The ceiling must be exactly $42. A higher ceiling is over the 280 CNY balance. A lower ceiling, including $12 and $27, is not this package.

Dry plan. No `--live`. Writes `run.json` and does not open a socket:

```bash
python -m tool_compression.clean_start run --preliminary --thinking off \
  --memory-prereqs matched --ceiling-usd 42 --out /tmp/preliminary-plan
```

The plan reports `provider_contacted: false`, `thinking_modes_authorized: ["off"]`, `preliminary: true`, `pilot: false`, `ceiling_usd: null`, `slots_total: 2952`, `prereq_slots: 444`, `fraction: "0.2"`, and `planning_upper_usd: "95.376500"`. The plan's `slot_sha256` is `a794ab88779d6ef75a0d8928d32359512b19a9aad435587e9c53b8d502421f7f`.

Live run, for 18:00 HKT on Thursday 26 Nov 2026. `--out` must be a new empty directory on storage that outlives the box. Set `DEEPSEEK_API_KEY` on the box only. Do not set a SerpAPI key.

```bash
python -m tool_compression.clean_start run --preliminary --live --authorize-live \
  --thinking off --memory-prereqs matched --ceiling-usd 42 \
  --bfcl-root /path/to/gorilla --out /path/to/new-empty-dir
```

Score, after the run, against the same pin. This contacts no provider:

```bash
python -m tool_compression.clean_start evaluate \
  --out /path/to/new-empty-dir --bfcl-root /path/to/gorilla --thinking off
```

The planning upper is above $42. The live command is accepted anyway. The ceiling is checked before every request and stops the run when spend reaches it. It is not a pack limit the draw has to fit under. The live command refuses a ceiling below the observed-mean path with its Friday-peak slice. It also refuses a draw or slot order other than the committed ones: draw SHA-256 `2904904…` and thinking-off slot SHA-256 `a794ab…`. A fresh run refuses an output directory that already holds attempts, bills, or a run that contacted a provider. Continuing that run takes `--resume`.

Exit codes: 0 means the run completed, 1 means it stopped incomplete (resume it), and 2 means it was refused before any request.

## Resume

If the run stops before it completes, continue it in the same directory with the same tip. That covers a provider error left after retries, a lost box, or an interrupt. A ceiling stop is final. A resume refuses any ceiling other than $42, and at $42 it would stop again before its first request. Check first. This reads the directory, prints what a resume would skip, send again, and repair, and writes nothing. It reads no key and opens no socket:

```bash
python -m tool_compression.clean_start run --preliminary --resume \
  --thinking off --memory-prereqs matched --ceiling-usd 42 \
  --out /path/to/the-same-dir
```

Then resume:

```bash
python -m tool_compression.clean_start run --preliminary --live --authorize-live \
  --thinking off --memory-prereqs matched --ceiling-usd 42 \
  --bfcl-root /path/to/gorilla --out /path/to/the-same-dir --resume
```

Repeat the same command after every stop until it exits 0. Then score the same directory with the `evaluate` command above.

A resume refuses, with exit 2 before the key is read and with nothing written, unless the directory's `run.json` contacted a provider, is not complete, and matches this run exactly. The fields compared are:

- `draw_sha256` `2904904116ca21ad8830f4bb2dfaaf9cfd1773124315a8a26fe934f3490a785a`;
- `slot_sha256` `a794ab88779d6ef75a0d8928d32359512b19a9aad435587e9c53b8d502421f7f`;
- the case ids;
- editors `s-rules-2026-11-26` and `x-rules-2026-11-26`;
- `source_sha256` of every `.py` file under `src/tool_compression`;
- thinking off;
- the $42 ceiling;
- the rate card.

It also refuses if any of these hold:

- the attempt journal has a gap;
- the bill ledger's running total does not add up;
- the finished slots are not a prefix of the slot order;
- a result line is duplicated, or belongs to no slot;
- a memory snapshot matches no checkpoint it could have come from.

What a resume does:

- **Skips finished slots.** A slot is finished when its sidecar says `finished` and its result file holds exactly one line with its id.
- **Sends the stopped slot again from its first request.** It does not continue a slot mid-conversation. Multi-turn class instances start again from the initial config in the new process. The slot's stopped sidecar, and any result line it wrote just before the box was lost, are moved under `resume/session-<n>/`, not deleted.
- **Keeps memory state right.** In pinned BFCL, every memory entry other than a scenario's `-0` prerequisite loads `<scenario>_final.json`. Only a prerequisite flush writes that file, right after `prereq_checkpoints/<id>.json`. So the final file must equal the checkpoint of that arm's last finished prerequisite. Sometimes the box is lost after a prerequisite flushed but before its result line was written. The final file is then restored from the previous checkpoint, and the stale checkpoint is moved aside. Then the re-sent prerequisite starts from the right memory.
- **Counts recorded spend against the same $42.** The running total starts at the sum of `bills.jsonl` over every session, and is checked before every request. Bills of the abandoned part of the re-sent slot stay counted, because they were billed. Attempt numbers continue, and every attempt and bill row carries `session`.
- **Lists what may be billed but is not recorded.** Every attempt with no bill is listed in `run.json` under `unbilled_attempts`, and is not in the running total. That is a failed try, an unusable response, or a send with no outcome before a box loss. The provider dashboard is the record for those.
- **Logs the session.** One line in `resume.jsonl`, plus a copy of the previous `run.json` and `spend.json` under `resume/session-<n>/`.

Accuracy and tokens stay recoverable after any number of resumes:

- **Accuracy.** The result files hold exactly one line per finished id, so `evaluate` is unchanged.
- **All billed tokens.** These are the rows of `bills.jsonl` across sessions.
- **Tokens of the attempt that produced a slot's result.** These are in that slot's sidecar steps. Equivalently, they are that slot's bills (same `thinking`, `case_id`, `arm`) whose `session` equals the sidecar's `session`.

Do not start a fresh `--out` after a partial run. Spend would restart at $0, and $42 would no longer bound the total. `--out` must survive the box, or be copied back intact before resuming. Result lines, sidecars, ledgers, and memory flushes are fsynced as they are written. A resume's own repairs copy a file aside before replacing it atomically. A box lost during the repair leaves either the old state or the repaired one, and the next resume plans the same repair again.

## Retry

The preliminary live path sends a failed request again at most twice, after 10 s and then 30 s, for transport failures only:

- timeouts, including the 900 s total deadline;
- dropped connections, `IncompleteRead`, and TLS or DNS errors;
- HTTP 429 and 5xx.

The body is the same, the ceiling is checked again before each try, and each try is its own journalled attempt. A failed try is marked `may_be_billed` and listed under `unbilled_attempts`. Nothing else in the slot has changed by then: the failure comes before any tool runs or any history is appended. These are not retried:

- other 4xx, including 402 for an exhausted balance;
- a 200 whose body has no billed usage or no choice.

If the second retry also fails, the run stops incomplete, and you continue it with `--resume`.

## What is in the draw

738 conversations, 2,952 slots, thinking off, four arms. 627 scoring cases and 111 prerequisite conversations (444 slots). No second U pass. No web-search category. All 14 in-scope categories are present. Memory is last. Each memory backend's prerequisites are sent, in loader order, before that backend's questions.

| category | population | scoring | prerequisites | user turns |
| --- | ---: | ---: | ---: | ---: |
| multiple | 200 | 40 | 0 | 40 |
| parallel_multiple | 200 | 40 | 0 | 40 |
| live_multiple | 1053 | 211 | 0 | 211 |
| live_parallel | 2 | 2 | 0 | 2 |
| live_parallel_multiple | 24 | 5 | 0 | 5 |
| live_irrelevance | 372 | 74 | 0 | 74 |
| live_relevance | 11 | 2 | 0 | 2 |
| multi_turn_base | 200 | 40 | 0 | 153 |
| multi_turn_miss_func | 200 | 40 | 0 | 185 |
| multi_turn_miss_param | 200 | 40 | 0 | 193 |
| multi_turn_long_context | 200 | 40 | 0 | 136 |
| memory_kv | 155 | 31 | 37 | 354 |
| memory_vector | 155 | 31 | 37 | 354 |
| memory_rec_sum | 155 | 31 | 37 | 354 |

The fraction is 0.2. For each category, n is the minimum of the population and the maximum of the floor and half-up of 0.2 times the population. `live_parallel` keeps both in-scope ids, because half-up of 0.4 is 0 and the special case takes the whole population. `live_relevance`, `live_parallel_multiple`, and each memory backend have a floor of 2. Every other category has a floor of 1. At this fraction those floors do not bind: `live_relevance` is half-up of 2.2, which is 2, and `live_parallel_multiple` is half-up of 4.8, which is 5.

The pool drops ids in the exposed 41-case pilot when at least n ids remain. That rule binds in every category except `live_parallel`, whose only two in-scope ids are the pilot overlap: `live_parallel_6-3-0` and `live_parallel_7-3-1`. Seventy-two scoring ids are also in the validation draw. That overlap is expected at this fraction. It is not a fresh hold-out.

Memory questions are drawn from all 155 in-scope questions on each backend, not from the notetaker scenario alone. On seed `20261128` all five scenarios appear on all three backends:

| backend | notetaker | finance | healthcare | student | customer |
| --- | ---: | ---: | ---: | ---: | ---: |
| memory_kv | 5 | 5 | 6 | 7 | 8 |
| memory_vector | 5 | 6 | 5 | 11 | 4 |
| memory_rec_sum | 7 | 6 | 5 | 9 | 4 |

Matched prerequisites are every prerequisite conversation of each drawn scenario. That is the full catalogue: 37 conversations on each backend, 111 conversations, 969 user turns. Per backend the prerequisite mix is notetaker 5 (24 turns), finance 7 (35), healthcare 5 (47), student 10 (108), and customer 10 (109).

Scoring user turns are 1,134. With the 969 prerequisite turns, the draw has 2,103 user turns.

## Why the ceiling does not size the draw

The hard ceiling is $42. The planning upper is **$95.376500** (635.674832 CNY at 6.6649 on the unrounded product, 635.508629 CNY at 0.150079). Multiplying the rounded $95.376500 by 6.6649 gives 635.674835 CNY. The upper is above the ceiling. The draw is not shrunk to fit the old $11.50 pack limit or to fit $42. The builder used to refuse a draw whose upper exceeded $11.50. That refusal is gone. The report now refuses an upper that fits under $42, so this sample cannot be silently cut down until the allowance fits.

Four refusals went with it. The builder and `load_committed_cost()` no longer refuse an upper above $11.50. The builder no longer refuses a finish at or after Friday 09:00 HKT. The CLI no longer caps the ceiling at $12 or $27, and no longer refuses a ceiling below the planning upper. In their place is one explicit check, in the builder, in `load_committed_cost()`, and in the live CLI. It prices the observed-mean path in run order, with every send that falls inside a weekday peak window billed at double, at each pace profile. The peak windows are 09:00–12:00 and 14:00–18:00 HKT. The worst profile must be at or under the ceiling:

| pace | sends in peak | peak premium | observed-mean with peak | finish HKT |
| --- | ---: | ---: | ---: | --- |
| 1.9 s | 0 | $0.000000 | $21.572285 | 05:33:15 Fri |
| 2.0 s | 0 | $0.000000 | $21.572285 | 06:09:44 Fri |
| 3.3 s | 3,346.736126 | $4.187352 | **$25.759637** | 14:04:04 Fri |
| memory 3.3 s, the rest 2.0 s | 1,174.552340 | $1.469570 | $23.041855 | 10:04:36 Fri |

$25.759637 is at or under $42, so the check passes. The figure is `observed_mean_with_friday_peak_usd` in `preliminary/cost.json`.

Headroom. $42 × 6.6649 is 279.9258 CNY. That leaves 0.0742 CNY, or $0.0111, under 280 CNY. The ceiling is checked before each request with no reserve, so the last request can carry the ledger past $42 by that request's cost. Memory runs last. A memory request at peak, priced at the 12,269-token allowance plus 900 output tokens, is about $0.0048, under the headroom. Attempts listed under `unbilled_attempts` can add unrecorded charges on top of that. If the prepaid balance runs out first, the provider answers 402. That is not retried, and the run stops incomplete. The cap stays $42.

Prices in the allowance are off-peak, every prompt token a cache miss, no cache credit: $0.15 per million input and $0.60 per million output.

| part | USD |
| --- | ---: |
| single-turn, local first-request tokens plus 900 output | 0.965265 |
| trajectories at the step allowance | 93.141259 |
| one long-context request per case per arm raised to 43,803 prompt tokens | 0.841512 |
| one 21-step memory turn per backend per arm | 0.428463 |
| total | 95.376500 |

The four displayed parts sum to $95.376499. The total is the unrounded sum, quantized once. The first-request floor, local tokens only and no output, is 4,907,006 tokens, $0.736051. The structural tail, every trajectory turn at 21 requests plus the long-context spike, is $307.266045. It is not the planning number. The ceiling still stops the run. The allowance is 46,708 requests.

The prompt allowance is the greater of 1.5 times a family's mean prompt and its 95th percentile, then the greater of c47b186c and 0bf829c6. The percentile index is round-half-even of p times (n−1). That is 6,361 tokens for `multi_turn_base`, 6,975 for `multi_turn_miss_func`, 7,961 for `multi_turn_miss_param`, 8,740 for `multi_turn_long_context`, and 12,269 for memory. Steps are at least 6, or the higher flight's 90th percentile: 6, 9, 7, 7, and 6 in that same order. Output is 900 tokens. The 43,803-token spike is the largest long-context prompt in the 0bf829c6 bills. The force-quit contingency is 15 extra requests (21 instead of 6) on one turn of each memory backend on each arm.

The same draw at the higher flight's own mean prompt, mean output, and mean steps is **$21.572285** (143.777123 CNY at 6.6649 on the unrounded product, 143.739532 CNY at 0.150079), 21,892.190671 sends. Multiplying the rounded $21.572285 by 6.6649 gives 143.777122 CNY. Memory uses the c47b186c mean of 2.55 steps. The upper is the fat tail applied to every request, not the expected bill.

| family | flight | user turns | mean steps | sends | USD |
| --- | --- | ---: | ---: | ---: | ---: |
| single-turn | c47b186c | 374 | 1.00 | 1,496.000000 | 0.349823 |
| multi_turn_base | c47b186c | 153 | 3.36 | 2,054.571429 | 1.441948 |
| multi_turn_miss_func | 0bf829c6 | 185 | 4.42 | 3,273.076923 | 2.416932 |
| multi_turn_miss_param | c47b186c | 193 | 2.66 | 2,052.818182 | 1.788223 |
| multi_turn_long_context | 0bf829c6 | 136 | 4.00 | 2,176.000000 | 2.012968 |
| memory | c47b186c | 1,062 | 2.55 | 10,839.724138 | 13.562390 |
| total | | 2,103 | | 21,892.190671 | 21.572285 |

The recorded-mean estimate from the 20% briefing, scaling arm-specific means by n / N, is a different figure from this observed-mean. Estimate A, off-peak and all cache-miss, is **$17.546872** (116.948147 CNY) for the 12 scoring sets that have a recorded average plus recorded and imputed prerequisites. A labeled placeholder that copies the kv notetaker scoring mean onto `memory_vector` and `memory_rec_sum` adds $0.188612, for **$17.735484** (118.205227 CNY). Estimate B, the same tokens at the observed cache mix, is **$3.515060** (23.427523 CNY), or **$3.585651** (23.898005 CNY) with that placeholder. `memory_vector` and `memory_rec_sum` scoring have no recorded average, and most of the prerequisite portion of A is imputation. Those two estimates are not recomputed by `preliminary.py`. The figure this package computes from the archived flights and this draw's turns is the observed-mean $21.572285.

$42 can cover that mean path. A at about $17.55 and the package observed-mean at about $21.57 both sit well under $42, with more room than they had under $27. A peak-rate leftover after 09:00 HKT is more comfortable under $42 than under $27, because peak prices are double and the extra dollars are the margin. $42 cannot cover the $95.376500 allowance. A fat-tail run priced at the allowance can stop before the 20% sample completes. Memory is last, so a cap stop there can still leave the single-turn and multi-turn slices finished.

Earlier incomplete flights are not subtracted from the $42. Archived ledgers: $0.040170708 (thinking-off pilot), $0.287883432 (c47b186c), $0.346230789 (0bf829c6). The thinking-off pilot on tip `747e72fb` was recorded at $0.325173531; that ledger is not in this checkout.

## Duration from 18:00 HKT

Jacky authorized this live run to continue past Friday 09:00 HKT into peak if it is still going. The leftover is likely memory, because memory is last. Peak rates are double the off-peak prices in this sheet. The $42 ceiling still applies.

Expected sends are 21,892.190671. Friday peak starts 09:00 HKT, 15 hours after 18:00.

| path | sends | pace | hours | finish HKT | before Friday 09:00 |
| --- | ---: | --- | ---: | --- | --- |
| mean | 21,892.190671 | 1.9 s | 11.55 | 05:33:15 Fri 27 Nov 2026 | yes |
| mean | 21,892.190671 | 2.0 s | 12.16 | 06:09:44 Fri 27 Nov 2026 | yes |
| mean | 21,892.190671 | 3.3 s | 20.07 | 14:04:04 Fri 27 Nov 2026 | no |
| mean, memory 3.3 s and the rest 2.0 s | 21,892.190671 | mixed | 16.08 | 10:04:36 Fri 27 Nov 2026 | no |
| allowance | 46,708 | 1.9 s | 24.65 | 18:39:05 Fri 27 Nov 2026 | no |
| allowance | 46,708 | 2.0 s | 25.95 | 19:56:56 Fri 27 Nov 2026 | no |
| allowance | 46,708 | 3.3 s | 42.82 | 12:48:56 Sat 28 Nov 2026 | no |

At 1.9 or 2.0 seconds per request the mean path finishes inside the off-peak window. At 3.3 seconds on memory and 2.0 seconds on the rest, it runs about an hour into Friday morning peak. The allowance path does not finish off-peak at any of these paces. The prices in the allowance and the observed-mean are off-peak. A slice that actually falls after 09:00 is billed at the peak rate.

Earlier clean-start flights stopped at 152 sends (a 120 s read timeout), 900 (an `IncompleteRead`), and 2,482 (a lost box). This mean path is about 21,892 sends. With no retry and no resume, one flight would very likely have stopped early. Now a transport failure is sent again up to twice. A stop that still happens, including a lost box, is continued with `--resume`, from the stopped slot and against the same $42.

## Box preflight

Before the live command, on the box that will run it:

- The Gorilla checkout is `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`.
- `all-MiniLM-L6-v2` revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` is already built in that environment. The runner's preflight checks that `sentence_transformers`, `faiss`, and `numpy` import. It does not open the weight file. The pinned backend constructs the model when the first `memory_vector` slot runs.
- The live shell sets `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`.
- `DEEPSEEK_API_KEY` is set in that shell and is not printed. No SerpAPI key is set.
- `--out` is a new empty directory on storage that outlives the box. Do not reuse a pilot, validation, or earlier preliminary directory.
- The checkout is the packaged tip. A resume refuses any other source tree.
- The dry plan reports `slot_sha256` `a794ab88779d6ef75a0d8928d32359512b19a9aad435587e9c53b8d502421f7f`.

## Follow-up

The full in-scope thinking-off fly is still unsent: 3,127 scoring questions plus 111 memory prerequisites, 3,238 conversations, 12,952 slots. It is packaged in [FULL-FLY.md](FULL-FLY.md) behind `run --full`, with a 20 s wall-clock first deadline, one 60 s retry, skip-and-record, and `--resume`. It needs a ceiling Jacky has not named yet. This preliminary draw does not settle it. `official_settlement` stays false.

The preliminary's own policy is unchanged on later tips: two retries after 10 s and 30 s, a 120 s socket timeout, and a 900 s total deadline. A run started on 69f33cdc resumes only from a 69f33cdc checkout. A later tip refuses it on `source_sha256`.
