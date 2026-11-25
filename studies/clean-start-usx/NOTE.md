# Clean-start U/S/X/SX

This study is separate from Evaluation Protocol v1.1. v1.1 stays historical and closed. `official_settlement` is false. Nothing in this package calls a provider. A later evaluation is intended off-peak and is not started here.

The request model is `deepseek-flash`, currently served as DeepSeek-V4.1-Flash-1017. The retired name `deepseek-v4-flash` still routes and is not the name this runner sends. V4.1 Flash defaults to thinking on, so the runner sets `thinking.type` to `disabled` and then `enabled`. Arms are U, S, X, and SX. U is the unmodified original BFCL tools after the official language hint and OpenAI-completions conversion. S edits one tool at a time. X appends at most one contrast cue computed on U. SX is S, then that same cue. Questions and gold answers are not editor inputs.

## Study population

The study uses official BFCL scoring questions whose loaded U catalogue has more than one tool for the model to choose from. `scope.json` is the census and the in-scope id list. The runner, pilot, limitations record, and `evaluate-help` category list apply that same rule to the loaded questions. A run refuses to continue when `scope.json` disagrees with that load.

A question is in scope when `len(tools) > 1` on the catalogue the editors see. The loader is `load_questions`, then the official language hint, then the OpenAI tool entries `compile_case` edits (`model_facing_tools`). One tool is one function-document entry in that initial list. Parameters and response-schema fields stay uncounted. For multi-turn, the count is the initial catalogue on the first turn. An `excluded_function` name that is still in that list counts. A held-out `miss_func` document that is absent from it stays uncounted. `multi_turn_miss_func` still has at least 16 tools on every initial catalogue after those holdouts leave.

Official simple sets stay out of the study: `simple_python`, `simple_java`, `simple_javascript`, and `live_simple`. Every question in those four sets has one tool. The census found no multi-tool question there.

A category with zero in-scope questions is dropped. A mixed category stays, restricted to the in-scope questions. Vendored prompts under `bfcl/` stay the original scoring package, including the dropped sets.

Memory prerequisite conversations are not scoring questions. They stay out of the census population, the pilot, the in-scope id lists, and the limitation question counts. The full runner still sends the 37 prerequisites for each memory backend before that backend's questions, because a full memory score needs those conversations. Those catalogues are multi-tool (kv 15, vector 12, rec_sum 5) and remain outside the population. The pilot does not send them.

The unscoped 22-set package, with its 66-case pilot, stays on PR #24, branch `cursor/clean-start-usx-14e3`, tip `c1df4bbf439151abad2ed79b103d401a61443412`, parented on main `1ab2b5d042b7d8fadbb0c922c51201ae6fc75c21`. This change leaves that branch as it is.

### Census

Counts are scoring questions, in `ALL_SCORING_CATEGORIES` order. Tool counts are the loaded U catalogue. Median is the middle value, or the mean of the two middle values when the set has an even count. `parallel_multiple` is the only half median.

| set | questions | 0 tools | 1 tool | 2+ tools | min | max | median | in scope |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| simple_python | 400 | 0 | 400 | 0 | 1 | 1 | 1 | 0 |
| simple_java | 100 | 0 | 100 | 0 | 1 | 1 | 1 | 0 |
| simple_javascript | 50 | 0 | 50 | 0 | 1 | 1 | 1 | 0 |
| multiple | 200 | 0 | 0 | 200 | 2 | 4 | 3 | 200 |
| parallel | 200 | 0 | 200 | 0 | 1 | 1 | 1 | 0 |
| parallel_multiple | 200 | 0 | 0 | 200 | 2 | 4 | 2.5 | 200 |
| irrelevance | 240 | 0 | 240 | 0 | 1 | 1 | 1 | 0 |
| live_simple | 258 | 0 | 258 | 0 | 1 | 1 | 1 | 0 |
| live_multiple | 1053 | 0 | 0 | 1053 | 2 | 37 | 4 | 1053 |
| live_parallel | 16 | 0 | 14 | 2 | 1 | 2 | 1 | 2 |
| live_parallel_multiple | 24 | 0 | 0 | 24 | 2 | 9 | 4 | 24 |
| live_irrelevance | 884 | 4 | 508 | 372 | 0 | 37 | 1 | 372 |
| live_relevance | 16 | 0 | 5 | 11 | 1 | 5 | 3 | 11 |
| multi_turn_base | 200 | 0 | 0 | 200 | 18 | 39 | 28 | 200 |
| multi_turn_miss_func | 200 | 0 | 0 | 200 | 16 | 38 | 27 | 200 |
| multi_turn_miss_param | 200 | 0 | 0 | 200 | 18 | 39 | 28 | 200 |
| multi_turn_long_context | 200 | 0 | 0 | 200 | 18 | 39 | 28 | 200 |
| memory_kv | 155 | 0 | 0 | 155 | 15 | 15 | 15 | 155 |
| memory_vector | 155 | 0 | 0 | 155 | 12 | 12 | 12 | 155 |
| memory_rec_sum | 155 | 0 | 0 | 155 | 5 | 5 | 5 | 155 |
| web_search_base | 100 | 0 | 0 | 100 | 2 | 2 | 2 | 100 |
| web_search_no_snippet | 100 | 0 | 0 | 100 | 2 | 2 | 2 | 100 |

5106 scoring questions. 3327 are in scope. 1779 are out of scope. The two web sets share one two-tool WebSearchAPI catalogue.

### Dropped

| set | questions | why it leaves the study |
| --- | ---: | --- |
| simple_python | 400 | official simple set; every catalogue has one tool |
| simple_java | 100 | official simple set; every catalogue has one tool |
| simple_javascript | 50 | official simple set; every catalogue has one tool |
| live_simple | 258 | official simple set; every catalogue has one tool |
| parallel | 200 | every catalogue has one tool, so the in-scope count is zero |
| irrelevance | 240 | every catalogue has one tool, so the in-scope count is zero |

`parallel` and `irrelevance` are not official simple sets. They drop because no question has two tools. Checked one-tool ids: `parallel_104`, `parallel_134`, `irrelevance_55`, `irrelevance_165`. The earlier observation that one-tool catalogues have no X cue on `simple_python`, `parallel`, and `irrelevance` matches this census.

### Kept whole

These categories stay with every scoring question: `multiple` (200), `parallel_multiple` (200), `live_multiple` (1053), `live_parallel_multiple` (24), `multi_turn_base` (200), `multi_turn_miss_func` (200), `multi_turn_miss_param` (200), `multi_turn_long_context` (200), `memory_kv` (155), `memory_vector` (155), `memory_rec_sum` (155), `web_search_base` (100), `web_search_no_snippet` (100).

### Mixed filters

`live_parallel` has 16 questions: 14 with one tool and 2 with two tools. In scope: `live_parallel_6-3-0` and `live_parallel_7-3-1`, both `get_current_weather` and `get_snow_report`. One-tool examples: `live_parallel_12-8-0`, `live_parallel_8-4-0`. The in-scope population is under 3, so the pilot freezes both ids in sorted order. The seed stays `20261125`.

`live_irrelevance` has 884 questions: 4 with an empty catalogue, 508 with one tool, and 372 with two or more. In scope: those 372. The empty prompts ship `"function": []`. Their ids are `live_irrelevance_120-9-0`, `live_irrelevance_121-9-1`, `live_irrelevance_122-9-2`, and `live_irrelevance_123-9-3`. One-tool examples, including the previous pilot draw: `live_irrelevance_201-32-14`, `live_irrelevance_522-159-0`, `live_irrelevance_817-314-1`. Multi-tool examples: `live_irrelevance_106-5-0` (2 tools), `live_irrelevance_125-11-0` (3 tools).

`live_relevance` has 16 questions: 5 with one tool and 11 with two to five tools. In scope: those 11. One-tool example: `live_relevance_15-15-0`. Multi-tool examples: `live_relevance_7-7-0` (2 tools), `live_relevance_6-6-0` (4 tools).

The resulting study is 16 categories and 3327 questions. `evaluate-help` names those 16 categories. Each category is passed on its own with `--partial-eval`, because a category result file holds the in-scope ids. The same command is repeated for each of the eight model directories, one arm of one thinking pass. `all_scoring` is outside this study's command.

## What is packaged

1. Unmodified scoring prompts, function-doc catalogues, and memory prerequisites under `bfcl/`, pinned to gorilla `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`. `bfcl/manifest.json` is the byte identity. Gold stays in that Gorilla tree. Saved outputs are the official JSONL result lines (`id` and `result`) plus a sidecar of the assistant message, reasoning, tool calls, and usage. Accuracy is recovered with `bfcl evaluate` after the eight directory names `deepseek-flash-thinking-<off|on>-<U|S|X|SX>` are registered as `deepseek-flash` function-calling models. Each name is one arm of one thinking pass. `python -m tool_compression clean-start evaluate-help` prints the commands. This repo does not score. `official_settlement` stays false.

2. Editors S and X, and the composed SX renders. The pilot renders under `pilot/rendered/` are the inspectable edits. `limitations.json` counts, for every in-scope scoring question, how many S, X, and SX catalogues differ from U.

3. A sender for U/S/X/SX with thinking off, then thinking on. It does not reserve or send `max_tokens`. After each completed response it records `prompt_tokens`, cache hit and miss (or the assumption below), output tokens, and reasoning tokens when the provider reports them. Reasoning tokens are recorded and are not added on top of output tokens. Spend uses the rate card below. If the running spend has reached a later-authorized ceiling, later sends stop. A stopped run has `complete: false` and is not a finished evaluation. A response without billed usage, or a provider error, stops the run and does not invent a charge. There is no retry.

4. The same sender limited to the frozen pilot. `python -m tool_compression clean-start run --pilot --out DIR` writes a dry plan and does not contact a provider. `--live` without `--authorize-live` exits before a key read or a socket. The authorized path also requires `--ceiling-usd` greater than zero and, for any trajectory category, `--bfcl-root` pointing at the pinned Gorilla checkout so the official multi-turn executor can run. This package does not start that run.

## Rate card

Retrieved 2026-11-25 from https://api-docs.deepseek.com/quick_start/pricing/. Prices are USD per 1,000,000 tokens for `deepseek-flash`.

| band | cache hit | cache miss | output |
| --- | ---: | ---: | ---: |
| off-peak | 0.003 | 0.15 | 0.6 |
| peak | 0.006 | 0.30 | 1.2 |

Peak is double off-peak. Peak hours are 01:00–04:00 and 06:00–10:00 UTC, Monday–Friday, half-open, which is 09:00–12:00 and 14:00–18:00 HKT. Chinese public holidays are off-peak for the whole Asia/Shanghai date. The 2026 holiday dates are the 放假 ranges in 国办发明电〔2025〕7号. Weekends stay off-peak, including makeup weekend workdays. Years outside 2026 have no holiday rows in this package. If the provider omits the cache split, the whole prompt is billed as cache miss and the bill says `assumed_all_miss`.

Token bills are `bills.jsonl` (one row per completed HTTP step) and `spend.json` (running USD, ceiling, slot counts, and the rate card). Scorable lines are `result/deepseek-flash-thinking-<off|on>-<U|S|X|SX>/<group>/BFCL_v4_<category>_result.json`. U, S, X, and SX do not append into the same file. The raw message for each slot is `model_outputs/deepseek-flash-thinking-<off|on>/<arm>/<case_id>.json`. Memory snapshots for a trajectory are `result/deepseek-flash-thinking-<off|on>-<U|S|X|SX>/<group>/memory_snapshot/<scenario>_final.json`. The executor instance name is `deepseek_flash_thinking_<off|on>_<arm>`. U, S, X, and SX do not share an in-process class instance or a snapshot file.

## Editor limitations by set

Every in-scope question gets the official language hint before the editors run. X qualifies the wording under that hint, then the cue is appended after it. Response-schema descriptions are not description slots, so they stay unmodified wherever a catalogue has them. A zero in the table means the rules ran on the in-scope questions and no candidate qualified. Dropped sets are omitted here; the census above records them. Question counts in this table are the in-scope counts.

`live_parallel` shows zeros because neither in-scope catalogue changed. The two S differences on the unscoped record are one-tool questions and are outside this study.

| set | in-scope questions | S differs from U | X differs from U | what stays unmodified |
| --- | ---: | ---: | ---: | --- |
| multiple | 200 | 86 | 13 | |
| parallel_multiple | 200 | 74 | 12 | |
| live_multiple | 1053 | 228 | 0 | same rules; no rival qualified |
| live_parallel | 2 | 0 | 0 | same rules; no S candidate and no X rival qualified |
| live_parallel_multiple | 24 | 9 | 0 | same rules; no rival qualified |
| live_irrelevance | 372 | 78 | 0 | same rules; no rival qualified |
| live_relevance | 11 | 3 | 0 | same rules; no rival qualified |
| multi_turn_base | 200 | 200 | 25 | `excluded_function` stays in the catalogue because the pinned loader does not strip it; execution needs the official backend |
| multi_turn_miss_func | 200 | 200 | 25 | held-out docs are absent from the initial tools and return on that turn with the official holdout user prompt, which is sender text |
| multi_turn_miss_param | 200 | 200 | 25 | same catalogue limitation as the base set |
| multi_turn_long_context | 200 | 200 | 25 | the long-context flag is an executor input, not a document edit |
| memory_kv | 155 | 0 | 155 | 37 prerequisite conversations are required for a full score and are not in the pilot; the backend instruction prompt is not invented; the agentic format prompt is sender text |
| memory_vector | 155 | 0 | 155 | same memory limitations |
| memory_rec_sum | 155 | 0 | 0 | same memory limitations; no S candidate and no X rival qualified |
| web_search_base | 100 | 0 | 0 | snippet display is `show_snippet` on the executor; the two web sets share tool docs |
| web_search_no_snippet | 100 | 0 | 0 | `show_snippet` is false when the id contains `no_snippet` |

Still outside the vendored tree: `format_sensitivity`, `exec_simple`, `exec_parallel`, `exec_multiple`, `exec_parallel_multiple`, `rest`, `sql`, `chatable`, `multi_turn_composite`, and `unused_datasets`.

## Frozen pilot

Seed `20261125`. For each kept category with at least 3 in-scope questions, `random.Random("clean-start-usx:20261125:<category>").sample(sorted(in_scope_question_ids), 3)`. `live_parallel` has 2 in-scope questions, so the pilot freezes both in sorted order and does not draw a new seed. Memory prerequisites are excluded. Dropped categories are not in the pilot. Categories whose in-scope population is the full scoring set keep the draw from the unscoped package. The same draw can later drive a peak-hours pipeline test. That test was not run.

| category | cases |
| --- | --- |
| multiple | multiple_142, multiple_66, multiple_77 |
| parallel_multiple | parallel_multiple_191, parallel_multiple_150, parallel_multiple_192 |
| live_multiple | live_multiple_943-196-1, live_multiple_988-219-0, live_multiple_447-144-7 |
| live_parallel | live_parallel_6-3-0, live_parallel_7-3-1 |
| live_parallel_multiple | live_parallel_multiple_3-2-1, live_parallel_multiple_8-7-0, live_parallel_multiple_20-17-0 |
| live_irrelevance | live_irrelevance_663-211-3, live_irrelevance_238-43-0, live_irrelevance_553-169-6 |
| live_relevance | live_relevance_11-11-0, live_relevance_10-10-0, live_relevance_14-14-0 |
| multi_turn_base | multi_turn_base_120, multi_turn_base_86, multi_turn_base_198 |
| multi_turn_miss_func | multi_turn_miss_func_189, multi_turn_miss_func_95, multi_turn_miss_func_167 |
| multi_turn_miss_param | multi_turn_miss_param_187, multi_turn_miss_param_78, multi_turn_miss_param_31 |
| multi_turn_long_context | multi_turn_long_context_140, multi_turn_long_context_6, multi_turn_long_context_31 |
| memory_kv | memory_kv_146-notetaker-16, memory_kv_58-finance-3, memory_kv_7-customer-7 |
| memory_vector | memory_vector_107-student-27, memory_vector_90-student-10, memory_vector_123-student-43 |
| memory_rec_sum | memory_rec_sum_32-healthcare-2, memory_rec_sum_121-student-41, memory_rec_sum_62-finance-7 |
| web_search_base | web_search_base_37, web_search_base_46, web_search_base_58 |
| web_search_no_snippet | web_search_no_snippet_83, web_search_no_snippet_92, web_search_no_snippet_58 |

47 cases. Each case is rendered at `pilot/rendered/<category>/<case_id>.json` with arms U, S, X, and SX.
