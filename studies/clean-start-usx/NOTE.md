# Clean-start U/S/X/SX

This study is separate from Evaluation Protocol v1.1. v1.1 stays historical and closed. `official_settlement` is false. Nothing in this package calls a provider. A later evaluation is intended off-peak and is not started here.

The request model is `deepseek-flash`, currently served as DeepSeek-V4.1-Flash-1017. The retired name `deepseek-v4-flash` still routes and is not the name this runner sends. V4.1 Flash defaults to thinking on, so the runner sets `thinking.type` to `disabled` and then `enabled`. Arms are U, S, X, and SX. U is the unmodified original BFCL tools after the official language hint and OpenAI-completions conversion. S edits one tool at a time. X appends at most one contrast cue computed on U. SX is S, then that same cue. Questions and gold answers are not editor inputs.

## What is packaged

1. Unmodified scoring prompts, function-doc catalogues, and memory prerequisites under `bfcl/`, pinned to gorilla `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`. `bfcl/manifest.json` is the byte identity. Gold stays in that Gorilla tree. Saved outputs are the official JSONL result lines (`id` and `result`) plus a sidecar of the assistant message, reasoning, tool calls, and usage. Accuracy is recovered with `bfcl evaluate` after both directory names `deepseek-flash-thinking-off` and `deepseek-flash-thinking-on` are registered as `deepseek-flash` function-calling models. `python -m tool_compression clean-start evaluate-help` prints the command. This repo does not score.

2. Editors S and X, and the composed SX renders. The pilot renders under `pilot/rendered/` are the inspectable edits. `limitations.json` counts, for every scoring question, how many S, X, and SX catalogues differ from U.

3. A sender for U/S/X/SX with thinking off, then thinking on. It does not reserve or send `max_tokens`. After each completed response it records `prompt_tokens`, cache hit and miss (or the assumption below), output tokens, and reasoning tokens when the provider reports them. Reasoning tokens are recorded and are not added on top of output tokens. Spend uses the rate card below. If the running spend has reached a later-authorized ceiling, later sends stop. A stopped run has `complete: false` and is not a finished evaluation. A response without billed usage, or a provider error, stops the run and does not invent a charge. There is no retry.

4. The same sender limited to the frozen pilot. `python -m tool_compression clean-start run --pilot --out DIR` writes a dry plan and does not contact a provider. `--live` without `--authorize-live` exits before a key read or a socket. The authorized path also requires `--ceiling-usd` greater than zero and, for any trajectory category, `--bfcl-root` pointing at the pinned Gorilla checkout so the official multi-turn executor can run. This package does not start that run.

## Rate card

Retrieved 2026-11-25 from https://api-docs.deepseek.com/quick_start/pricing/. Prices are USD per 1,000,000 tokens for `deepseek-flash`.

| band | cache hit | cache miss | output |
| --- | ---: | ---: | ---: |
| off-peak | 0.003 | 0.15 | 0.6 |
| peak | 0.006 | 0.30 | 1.2 |

Peak is double off-peak. Peak hours are 01:00–04:00 and 06:00–10:00 UTC, Monday–Friday, half-open, which is 09:00–12:00 and 14:00–18:00 HKT. Chinese public holidays are off-peak for the whole Asia/Shanghai date. The 2026 holiday dates are the 放假 ranges in 国办发明电〔2025〕7号. Weekends stay off-peak, including makeup weekend workdays. Years outside 2026 have no holiday rows in this package. If the provider omits the cache split, the whole prompt is billed as cache miss and the bill says `assumed_all_miss`.

Token bills are `bills.jsonl` (one row per completed HTTP step) and `spend.json` (running USD, ceiling, slot counts, and the rate card). Scorable lines are `result/deepseek-flash-thinking-<off|on>/<group>/BFCL_v4_<category>_result.json`. The raw message for each slot is `model_outputs/deepseek-flash-thinking-<off|on>/<arm>/<case_id>.json`.

## Editor limitations by set

Every set gets the official language hint before the editors run. X qualifies the wording under that hint, then the cue is appended after it. Response-schema descriptions are not description slots, so they stay unmodified wherever a catalogue has them. A zero in the table means the rules ran and no candidate qualified. It is not a skipped set.

| set | questions | S differs from U | X differs from U | what stays unmodified |
| --- | ---: | ---: | ---: | --- |
| simple_python | 400 | 69 | 0 | one-tool catalogues have no X cue |
| simple_java | 100 | 0 | 0 | Java parameters are stringified, with a Java type sentence, before the edit |
| simple_javascript | 50 | 7 | 0 | JavaScript parameters are stringified the same way |
| multiple | 200 | 86 | 13 | |
| parallel | 200 | 42 | 0 | one-tool catalogues have no X cue |
| parallel_multiple | 200 | 74 | 12 | |
| irrelevance | 240 | 75 | 0 | one-tool catalogues have no X cue |
| live_simple | 258 | 36 | 0 | same rules; no rival qualified |
| live_multiple | 1053 | 228 | 0 | same rules; no rival qualified |
| live_parallel | 16 | 2 | 0 | same rules; no rival qualified |
| live_parallel_multiple | 24 | 9 | 0 | same rules; no rival qualified |
| live_irrelevance | 884 | 263 | 0 | same rules; no rival qualified |
| live_relevance | 16 | 4 | 0 | same rules; no rival qualified |
| multi_turn_base | 200 | 200 | 25 | `excluded_function` stays in the catalogue because the pinned loader does not strip it; execution needs the official backend |
| multi_turn_miss_func | 200 | 200 | 25 | held-out docs are absent from the initial tools and return on that turn with the official holdout user prompt, which is sender text |
| multi_turn_miss_param | 200 | 200 | 25 | same catalogue limitation as the base set |
| multi_turn_long_context | 200 | 200 | 25 | the long-context flag is an executor input, not a document edit |
| memory_kv | 155 | 0 | 155 | 37 prerequisite conversations are required for a full score and are not in the pilot; the backend instruction prompt is not invented; the agentic format prompt is sender text |
| memory_vector | 155 | 0 | 155 | same memory limitations |
| memory_rec_sum | 155 | 0 | 0 | same memory limitations; no S candidate and no X rival qualified |
| web_search_base | 100 | 0 | 0 | snippet display is `show_snippet` on the executor; the two web sets share tool docs |
| web_search_no_snippet | 100 | 0 | 0 | `show_snippet` is false when the id contains `no_snippet` |

Out of scope, and not vendored: `format_sensitivity`, `exec_simple`, `exec_parallel`, `exec_multiple`, `exec_parallel_multiple`, `rest`, `sql`, `chatable`, `multi_turn_composite`, and `unused_datasets`.

## Frozen pilot

Seed `20261125`. For each scoring category, `random.Random("clean-start-usx:20261125:<category>").sample(sorted(question_ids), 3)`. Population is scoring questions only. Memory prerequisites are excluded. The same draw can later drive a peak-hours pipeline test. That test was not run.

| category | cases |
| --- | --- |
| simple_python | simple_python_212, simple_python_125, simple_python_311 |
| simple_java | simple_java_46, simple_java_86, simple_java_2 |
| simple_javascript | simple_javascript_0, simple_javascript_33, simple_javascript_16 |
| multiple | multiple_142, multiple_66, multiple_77 |
| parallel | parallel_134, parallel_115, parallel_72 |
| parallel_multiple | parallel_multiple_191, parallel_multiple_150, parallel_multiple_192 |
| irrelevance | irrelevance_55, irrelevance_165, irrelevance_238 |
| live_simple | live_simple_166-99-0, live_simple_26-6-0, live_simple_29-7-2 |
| live_multiple | live_multiple_943-196-1, live_multiple_988-219-0, live_multiple_447-144-7 |
| live_parallel | live_parallel_6-3-0, live_parallel_8-4-0, live_parallel_12-8-0 |
| live_parallel_multiple | live_parallel_multiple_3-2-1, live_parallel_multiple_8-7-0, live_parallel_multiple_20-17-0 |
| live_irrelevance | live_irrelevance_817-314-1, live_irrelevance_522-159-0, live_irrelevance_201-32-14 |
| live_relevance | live_relevance_15-15-0, live_relevance_6-6-0, live_relevance_7-7-0 |
| multi_turn_base | multi_turn_base_120, multi_turn_base_86, multi_turn_base_198 |
| multi_turn_miss_func | multi_turn_miss_func_189, multi_turn_miss_func_95, multi_turn_miss_func_167 |
| multi_turn_miss_param | multi_turn_miss_param_187, multi_turn_miss_param_78, multi_turn_miss_param_31 |
| multi_turn_long_context | multi_turn_long_context_140, multi_turn_long_context_6, multi_turn_long_context_31 |
| memory_kv | memory_kv_146-notetaker-16, memory_kv_58-finance-3, memory_kv_7-customer-7 |
| memory_vector | memory_vector_107-student-27, memory_vector_90-student-10, memory_vector_123-student-43 |
| memory_rec_sum | memory_rec_sum_32-healthcare-2, memory_rec_sum_121-student-41, memory_rec_sum_62-finance-7 |
| web_search_base | web_search_base_37, web_search_base_46, web_search_base_58 |
| web_search_no_snippet | web_search_no_snippet_83, web_search_no_snippet_92, web_search_no_snippet_58 |

Each case is rendered at `pilot/rendered/<category>/<case_id>.json` with arms U, S, X, and SX.
