# Validation flight, thinking off

Packaging only. This tree does not contact a provider, read a key, or start the run. The parent box flies it after checking the tip, the tests, and the dry plan.

The draw is `validation/draw.json`. Its SHA-256 (the file bytes) is `01ba0e9f20ae49066ef3aafeb85342abfa00726f0a43f317794e7c4d6a40e568`. The same digest is `draw_sha256` in `validation/cost.json`. Seed `20261126`, Python 3.12 `random.Random`. `official_settlement` is false. Editors are unchanged: `s-rules-2026-11-25.2` and `x-rules-2026-11-25.3`. SX is the exact S catalogue plus the exact X cue. The draw was chosen from ids and memory scenarios. It does not read gold, saved answers, or the archived bills. The 41-case pilot and the six earlier web ids stay diagnostic and are not in this draw.

Gorilla pin: `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`. Model `deepseek-flash`, thinking disabled, no `max_tokens`, no retry. Arms U, S, X, SX. The evaluator registers `is_fc_model=True` and `underscore_to_dot=True`, and it skips result files whose names contain `prereq`.

## Commands

Dry plan. No `--live`. Writes `run.json` and does not open a socket:

```bash
python -m tool_compression.clean_start run --validation --thinking off \
  --memory-prereqs matched --ceiling-usd 20 --out /tmp/validation-plan
```

The plan reports `provider_contacted: false`, `thinking_modes_authorized: ["off"]`, `ceiling_usd: "20"`, and `slots_total: 1312`.

Live run. `--out` must be a new empty directory. Set `DEEPSEEK_API_KEY` on the box. Do not set a SerpAPI key; this draw has no web-search slot. Cache `all-MiniLM-L6-v2` before the run, because memory vector loads it locally.

```bash
python -m tool_compression.clean_start run --validation --live --authorize-live \
  --thinking off --memory-prereqs matched --ceiling-usd 20 \
  --bfcl-root /path/to/gorilla --out /path/to/new-empty-dir
```

Score, after the run, against the same pin. This contacts no provider:

```bash
python -m tool_compression.clean_start evaluate \
  --out /path/to/new-empty-dir --bfcl-root /path/to/gorilla --thinking off
```

A ceiling under the committed planning upper is refused before a key read. An output directory that already holds attempts, bills, or a run that contacted a provider is refused. There is no resume.

## What is in the draw

328 conversations, 1312 slots, thinking off, four arms. 313 scoring cases and 15 prerequisite conversations (60 slots). No second U pass. `live_parallel` is omitted: both of its in-scope ids are in the exposed pilot. No web-search category.

| category | scoring | prerequisites | user turns |
| --- | ---: | ---: | ---: |
| multiple | 64 | 0 | 64 |
| parallel_multiple | 64 | 0 | 64 |
| live_multiple | 64 | 0 | 64 |
| live_parallel_multiple | 21 | 0 | 21 |
| live_irrelevance | 64 | 0 | 64 |
| live_relevance | 8 | 0 | 8 |
| multi_turn_base | 4 | 0 | 14 |
| multi_turn_miss_func | 4 | 0 | 20 |
| multi_turn_miss_param | 4 | 0 | 17 |
| multi_turn_long_context | 4 | 0 | 12 |
| memory_kv | 4 | 5 | 28 |
| memory_vector | 4 | 5 | 28 |
| memory_rec_sum | 4 | 5 | 28 |

Single-turn is 285 cases. `live_parallel_multiple` and `live_relevance` keep every remaining id. The other single-turn categories draw 64. Multi-turn is 16 cases, 63 user turns. Memory is the notetaker scenario only, four questions on each backend. The five notetaker prerequisites are sent on kv, vector, and rec_sum, in loader order, before that backend's questions. Memory is last. Single-turn is first, then multi-turn.

The token endpoint is the first request of each scoring slot: `prompt_tokens` on the turn-0 step-0 row in `bills.jsonl`. There is no replicate U pass, so this flight does not separately measure within-case noise. Sixteen multi-turn cases and twelve memory questions are enough to score those categories, not enough to detect a small accuracy difference.

## Why this is the size that fits

The hard ceiling is $20. The planning upper is **$16.205873**. The pack limit in the builder is $17, so a draw whose upper crosses $17 is not written. Prices are weekday peak, every prompt token a cache miss, no cache credit: $0.30 per million input and $1.20 per million output. The 25 Nov partial spent $0.28788 because it stopped early and most of its prompt tokens were cache hits. That figure is not a forecast.

The upper has three parts:

| part | USD |
| --- | ---: |
| single-turn, local first-request tokens plus 500 output | 0.896683 |
| trajectories at 6 requests per user turn | 14.452265 |
| one force-quit turn per memory category per arm | 0.856926 |
| total | 16.205873 |

Six requests a turn is at or above the 90th percentile of every family in the c47b186c bills. `multi_turn_long_context` had a 95th percentile of 7, so a few of those turns can cost one request more than the allowance. The prompt allowance is the greater of 1.5 times that family's mean prompt and its 95th percentile. For memory that is 12,269 tokens, the flown 95th percentile; the unsent vector and rec_sum backends use the same figure. Trajectory output is 900 tokens, above the 813-token maximum in those bills. The force-quit contingency replaces 6 requests with 21 on one turn of each memory category on each arm (twelve turns). The c47b186c flight had one force-quit in 116 memory turns and none in multi-turn.

The same draw priced at the flown mean step count and the flown mean all-miss request cost is about $3.79. The upper is the bad case of that flight applied to every request, not the expected bill. The ceiling sits $3.79 above the upper.

The local first-request floor is 1,130,882 o200k_base tokens, **$0.339265**. That counts turn-0 message text plus the tools array, four arms, peak miss, no output, and no chat template. It does not include the pinned memory instruction or core memory, which the executor adds at send time, so it is a floor on prompt spend if every slot ended after one request.

The structural figure, every trajectory turn taking the runner's 21-request cap at the same allowances, is **$51.479609**. That exceeds $20. It is the tail if the model never finishes a turn. It is not the number the flight is sized to. The ceiling still stops the run, and because memory is last a stop there leaves single-turn and multi-turn complete.

## What was reduced

`REVISION-c47b186c.md` section 7 asks for a fresh draw, first-request prompt tokens, a second U pass, and memory with matched prerequisites. The full version does not fit.

All five memory scenarios are 323 prerequisite user-turns on a backend, 969 turns across kv, vector, and rec_sum. At the flown mean of 2.55 steps and the flown mean all-miss memory request, those prerequisites alone are about $24.73, before a scoring question or a multi-turn case. At the planning rate (6 steps, the 12,269-token allowance, 900 output tokens) they are about $110. Reducing the number of memory questions does not shrink that bill: matched prerequisites are per scenario. Customer, student, healthcare, or finance, added beside notetaker at the planning rate, each pushes the prerequisites past the ceiling before multi-turn is counted. Notetaker is the shortest prerequisite list, 24 user-turns, chosen from those turn counts and not from flight scores. It is sent on all three backends.

A fifth arm at the same planning rate adds a quarter of $16.205873, about $4.05, and the total is about $20.26. That does not fit under $20. The second U pass is omitted. Memory is reduced to notetaker rather than dropped, because that slice fits with the multi-turn cases still in the run.

## Checks

`validation/draw.json` matches `build_validation_draw()` on Python 3.12. The order has no duplicate ids, no pilot id, no web-search id, and no `live_parallel` id. Every memory question is notetaker. The fifteen prerequisite rows are the loader's notetaker rows, and each backend's prerequisites precede its questions. `validation/cost.json` hashes the draw file. The runner refuses a validation ceiling below the committed upper before it reads a key. `package/validation_20261126.json` is the same report. The pilot draw, `scope.json`, and both evidence directories are unchanged.
