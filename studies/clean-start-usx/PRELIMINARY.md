# Preliminary flight, thinking off, 80 CNY

This is a preliminary sample, not a completed full-set study. `official_settlement` is false. The budget named for 26 Nov 2026 is 80 CNY. At the rates named with it (CGB USD/CNY middle 6.6649, mid-market CNYUSD 0.150079), twelve dollars is 79.978800 CNY and 79.957889 CNY. The live ceiling is `--ceiling-usd 12`. This package does not contact a provider, read a key, or start the run.

The draw is `preliminary/draw.json`. Its SHA-256 (the file bytes) is `a82dea0cfaa00c015620c3dd0a29f65a100671d7c3e5e8abf9b3151be69ad0ca`. The same digest is `draw_sha256` in `preliminary/cost.json`. Seed `20261127`, because `20261126` is the committed validation seed. Python 3.12 `random.Random`. Editors are `s-rules-2026-11-26` and `x-rules-2026-11-26`. SX is the exact S catalogue plus the exact X cue. The draw was chosen from ids, population counts, and memory-scenario turn counts. It does not read gold, saved answers, or scores. Archived bills are used only for the allowance and the observed-mean estimate.

Gorilla pin: `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`. Model `deepseek-flash`, thinking disabled, no `max_tokens`, no retry, no resume. Arms U, S, X, SX. No web-search category and no SerpAPI call. The evaluator registers `is_fc_model=True` and `underscore_to_dot=True`, and it skips result files whose names contain `prereq`.

## Commands

Every preliminary command passes `--thinking off`. Omitting `--thinking` exits 2 and does not fall through to the full-run default of thinking off and on. A dry plan still drops both live flags. The plan file records `ceiling_usd` as null; the live path still requires the ceiling and checks it before every request.

Dry plan. No `--live`. Writes `run.json` and does not open a socket:

```bash
python -m tool_compression.clean_start run --preliminary --thinking off \
  --memory-prereqs matched --ceiling-usd 12 --out /tmp/preliminary-plan
```

The plan reports `provider_contacted: false`, `thinking_modes_authorized: ["off"]`, `preliminary: true`, `pilot: false`, `ceiling_usd: null`, `slots_total: 536`, and `prereq_slots: 60`.

Live run, for 18:30 HKT on Thursday 26 Nov 2026. `--out` must be a new empty directory. Set `DEEPSEEK_API_KEY` on the box only. Do not set a SerpAPI key.

```bash
python -m tool_compression.clean_start run --preliminary --live --authorize-live \
  --thinking off --memory-prereqs matched --ceiling-usd 12 \
  --bfcl-root /path/to/gorilla --out /path/to/new-empty-dir
```

Score, after the run, against the same pin. This contacts no provider:

```bash
python -m tool_compression.clean_start evaluate \
  --out /path/to/new-empty-dir --bfcl-root /path/to/gorilla --thinking off
```

A ceiling above $12, or below the committed planning upper, is refused before a key read. An output directory that already holds attempts, bills, or a run that contacted a provider is refused. There is no resume.

## What is in the draw

134 conversations, 536 slots, thinking off, four arms. 119 scoring cases and 15 prerequisite conversations (60 slots). No second U pass. No web-search category. All 14 in-scope categories are present. Memory is last. Each memory backend's five notetaker prerequisites are sent, in loader order, before that backend's questions.

| category | population | scoring | prerequisites | user turns |
| --- | ---: | ---: | ---: | ---: |
| multiple | 200 | 7 | 0 | 7 |
| parallel_multiple | 200 | 7 | 0 | 7 |
| live_multiple | 1053 | 39 | 0 | 39 |
| live_parallel | 2 | 2 | 0 | 2 |
| live_parallel_multiple | 24 | 2 | 0 | 2 |
| live_irrelevance | 372 | 14 | 0 | 14 |
| live_relevance | 11 | 2 | 0 | 2 |
| multi_turn_base | 200 | 7 | 0 | 24 |
| multi_turn_miss_func | 200 | 7 | 0 | 39 |
| multi_turn_miss_param | 200 | 7 | 0 | 30 |
| multi_turn_long_context | 200 | 7 | 0 | 20 |
| memory_kv | 155 | 6 | 5 | 30 |
| memory_vector | 155 | 6 | 5 | 30 |
| memory_rec_sum | 155 | 6 | 5 | 30 |

The fraction is 0.0374, the largest multiple of 0.0001 whose off-peak planning upper is at or under $11.50. For each category, n is the population times that fraction, rounded half up, then raised to a floor and capped at the population. `live_parallel` keeps both in-scope ids. `live_relevance`, `live_parallel_multiple`, and each memory backend have a floor of 2. Every other category has a floor of 1. The floor binds for `live_parallel`, `live_parallel_multiple` (the fraction alone would take 1), and `live_relevance` (the fraction alone would take 0). Memory's proportional n is 6, so its floor does not bind.

The pool drops ids in the exposed 41-case pilot when at least n ids remain. The only pilot overlap is `live_parallel_6-3-0` and `live_parallel_7-3-1`, because those are the whole in-scope population. Eleven scoring ids are also in the validation draw. For `live_relevance` and `live_parallel_multiple`, every id outside the pilot is already in that draw, so excluding the pilot puts both sampled ids there. The other overlaps are `multiple_50`, `multiple_53`, `parallel_multiple_122`, `parallel_multiple_187`, `live_irrelevance_236-41-0`, `multi_turn_miss_param_6`, and `memory_rec_sum_153-notetaker-23`.

Memory questions are notetaker only. Notetaker has 24 prerequisite user turns; finance, healthcare, student, and customer have 35, 47, 108, and 109. Matched prerequisites are every conversation of a drawn scenario, on each backend. The next-smallest scenario does not fit under $12 beside a proportional sample of the other categories. The scenario was chosen from those turn counts, not from flight scores. The sample does not send the other 32 prerequisite conversations per backend.

The next multiple, 0.0375, prices at $12.50, because each multi-turn category gains a case. It does not fit.

## Why this is the size that fits

The hard ceiling is $12. The planning upper is **$11.489930** (76.579237 CNY at 6.6649, 76.559215 CNY at 0.150079). The pack limit in the builder is $11.50, so at least $0.50 of the cap remains. Prices are off-peak, every prompt token a cache miss, no cache credit: $0.15 per million input and $0.60 per million output.

| part | USD |
| --- | ---: |
| single-turn, local first-request tokens plus 900 output | 0.191675 |
| trajectories at the step allowance | 10.722527 |
| one long-context request per case per arm raised to 43,803 prompt tokens | 0.147265 |
| one 21-step memory turn per backend per arm | 0.428463 |
| total | 11.489930 |

The prompt allowance is the greater of 1.5 times a family's mean prompt and its 95th percentile, then the greater of c47b186c and 0bf829c6. The percentile index is round-half-even of p times (n−1). That is 6,361 tokens for `multi_turn_base`, 6,975 for `multi_turn_miss_func`, 7,961 for `multi_turn_miss_param`, 8,740 for `multi_turn_long_context`, and 12,269 for memory. Steps are at least 6, or the higher flight's 90th percentile: 6, 9, 7, 7, and 6 in that same order. Output is 900 tokens. The 43,803-token spike is the largest long-context prompt in the 0bf829c6 bills. The force-quit contingency is 15 extra requests (21 instead of 6) on one turn of each memory backend on each arm. The structural tail, every trajectory turn at 21 requests, is $34.022885. It is not the planning number. The ceiling still stops the run.

The same draw at the higher flight's own mean prompt, mean output, and mean steps is **$2.527326** (16.844378 CNY at 6.6649, 16.839974 CNY at 0.150079), about 2,862 sends. Memory uses the c47b186c mean of 2.55 steps, which is the higher-cost flight; the 0bf829c6 memory mean is 3.93 steps and would add about 500 sends, still the same evening at these paces. The upper is the fat tail applied to every request, not the expected bill.

Earlier incomplete flights are not subtracted from the $12. Archived ledgers: $0.040170708 (thinking-off pilot), $0.287883432 (c47b186c), $0.346230789 (0bf829c6). The thinking-off pilot on tip `747e72fb` was recorded at $0.325173531; that ledger is not in this checkout.

## Duration from 18:30 HKT

Expected sends are about 2,862. At 1.9 seconds per request that is 1.51 hours, finishing 20:01 HKT. At 2.0 seconds, 1.59 hours, finishing 20:05 HKT. At 3.3 seconds on every request, 2.62 hours, finishing 21:07 HKT. With memory at 3.3 seconds and the rest at 2.0, 1.92 hours, finishing 20:25 HKT. The allowance's 6,012 requests finish at 21:50 HKT at 2.0 seconds per request, and at 00:01 HKT Friday at 3.3 seconds. Friday peak starts 09:00 HKT. None of these reach it.

A provider error still stops the run, and there is still no retry and no resume. Earlier clean-start flights stopped at 152, 900, and 2,482 sends. This draw is a few thousand sends, which is the size that was asked for, and a transport error can still end it early.

## Box preflight

Before the live command, on the box that will run it:

- The Gorilla checkout is `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`.
- `all-MiniLM-L6-v2` revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` is already built in that environment. The runner's preflight checks that `sentence_transformers`, `faiss`, and `numpy` import. It does not open the weight file. The pinned backend constructs the model when the first `memory_vector` slot runs.
- The live shell sets `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`.
- `DEEPSEEK_API_KEY` is set in that shell and is not printed. No SerpAPI key is set.
- `--out` is a new empty directory. Do not reuse a pilot, validation, or earlier preliminary directory.

## Follow-up

The full in-scope thinking-off fly is still unsent: 3,127 scoring questions plus 111 memory prerequisites, 3,238 conversations, 12,952 slots. It is a follow-up for when a larger budget exists. The runner would also need a retry or a resume before that fly is a credible single shot. This preliminary draw does not settle it. `official_settlement` stays false.
