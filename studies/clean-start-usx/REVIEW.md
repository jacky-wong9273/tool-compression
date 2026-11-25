# Independent review and revision of S, X, SX and the runner (2026-11-25)

Base: `0c0284d5c3ca76d77b11a4db304d46953844ec66` (PR #27, stacked on #25 and #24). `official_settlement` stays false. Nothing in this review sent a provider request, read a key, retried, resumed, or re-ran the pilot. The archived pilot outcomes were read as regression and diagnosis evidence only; no editor rule reads a question, a gold answer, or a score, and none special-cases a case id.

## Outcome in one paragraph

The pilot on 25 Nov measured almost nothing about the editors. At the pilot tip, X sent byte-identical tools to U in all 22 cases that reached the provider, so SX was identical to S, and S changed only 3 of 20 single-turn requests (25 local tokens in total). The billed differences between arms are send-order cache effects, and the archived accuracy is depressed by a scoring registration defect (`underscore_to_dot=False`) that hits every arm equally: rescoring the same result files with the pinned DeepSeek FC flags gives U 20/22, S 21/22, X 21/22, SX 20/21 instead of 14/22, 14/22, 14/22, 13/21. The runner would also have crashed on the first memory trajectory and diverged from the pinned BFCL loop on memory, held-out documents and step limits. This PR fixes the runner and scoring, rewrites S and X on a structural parse of each description, and freezes an offline package. The revised editors cut 24.2% of editable description tokens (10.7% of the tools array) across the 3327 in-scope questions under local counting; X adds cues to 762 questions at 1.6% field-token cost. None of this is a measured provider saving or an accuracy result. The largest S saving (suite preamble removal on multi-turn, memory and web catalogues) has no empirical test yet.

## 1. Critique, ranked by severity

Severity is about what the defect does to a conclusion the study could draw: Critical means a result would be wrong or the run would fail; High means a comparison would be confounded or evidence lost; Medium means a fidelity gap or avoidable cost; Low means cosmetic or documentation.

### Method

| # | severity | finding | evidence | status |
| --- | --- | --- | --- | --- |
| M1 | Critical | The pilot never exercised X. At `0c0284d`, X produced no cue on any of the 20 single-turn cases sent and on neither trajectory sent; SX was therefore S. Where the old X did fire (memory catalogues, not sent), it spliced suite boilerplate into an ungrammatical cue: `Unlike core_memory_add, which this tool belongs to the memory suite which provides APIs ... Tool description Add a key value pair ...`. | `package/pilot_2026_11_25_analysis.json` `single_turn.paired.X-U.cases_with_identical_sent_tools = 20/20`; trajectory `sent_identical_tools.X=U = true`; `git show 0c0284d:studies/clean-start-usx/pilot/rendered/memory_kv/memory_kv_7-customer-7.json`. | Fixed. X now compares one structurally parsed action sentence per tool and writes one positive sentence naming the rival (section 3). |
| M2 | High | The old S was close to a no-op on single-turn catalogues: it changed 3 of 20 sent requests, removing 25 local tokens (the provider billed 26 fewer prompt tokens on the same 3 cases). It also never touched the suite preambles that dominate multi-turn, memory and web catalogues. | `single_turn.paired.S-U`: 17/20 identical; `local_tokens_pilot_47.as_sent_editors_at_pilot_tip`: U 39748 vs S 39027 field tokens. | Revised. On the same 47 pilot cases the revised S gives 29535 field tokens (−25.7%). |
| M3 | High | The pilot sent memory questions without their prerequisite conversations, so memory would have been empty and any memory score uninterpretable. Official BFCL sets `depends_on` to every prerequisite of the question's scenario. | Pinned `process_memory_test_case`; pilot plan had no prereq slots. | Fixed as an explicit choice: `--memory-prereqs matched` (or `none`) is required for a live pilot. `matched` adds 54 prerequisite conversations (466 turns) per arm and thinking mode, about ten times the pilot's memory requests. |
| M4 | High | The biggest revised S saving is unvalidated. `suite_context` drops the suite elaboration (for example `, which provides APIs to interact with a key-value based memory system`) and keeps the membership sentence. That is 160 ledger rows, and it drives the −34% field change on multi-turn and −23% to −30% on memory. The elaboration describes the suite, not the tool, but it can still carry facts a model uses (for example "key-value"). | `package/s_ledger.jsonl` `change_class = suite_context`; `token_tables.json` by category. | Open risk. Flagged in blockers; needs the authorised pilot before any claim. |
| M5 | Medium | X cost is concentrated in `memory_kv`: 14 cues per catalogue, +160 tokens per question (+15.6% field). SX there nets −7.8% against S's −23.4%. Whether a cue earns its tokens is an empirical question the pilot did not answer. | `token_tables.json` `by_category.memory_kv`. | Kept; reported as cue cost, not hidden. |
| M6 | Medium | Name-redundant cues: a cue like `For the cruise control, use setCruiseControl.` repeats words the rival's name already spells and the model already sees. | Census over the in-scope corpus during review. | Fixed: a text cue is dropped (and the next rival tried) when every content word of the rival's differing window is in its name. Opaque names keep the cue (test fixture `tool_a`/`tool_b`). |

### Implementation (runner and scoring)

| # | severity | finding | evidence | status |
| --- | --- | --- | --- | --- |
| I1 | Critical | Scoring registered the eight model directories with `underscore_to_dot=False`. The pinned `DeepSeek-V3.2-Exp-FC` entry is `is_fc_model=True, underscore_to_dot=True`; FC sends replace `.` with `_` in tool names, and the AST checker maps dotted gold names only when the flag is set. Every dotted gold name scored `wrong_func_name`. The defect hits every arm equally, so arm deltas did not move, but absolute accuracy was understated by six cases per arm. | Rescoring the unmodified result files: U 14/22 → 20/22. Scoring with the old flag reproduces all 38 archived score files byte for byte; with the fixed flag it reproduces `rescored-underscore-to-dot/score` byte for byte. | Fixed in `evaluate.py` (in-process registration that checks the pinned entry) and in `evaluate-help`. |
| I2 | Critical | The memory backend was given `model_result_dir` as `str`. The pinned memory API does `model_result_dir / ...`, which raises `TypeError`, so the first memory trajectory would have failed. The pilot stopped before reaching one. | Pinned `MemoryAPI` setup; regression test with the pinned checkout. | Fixed: passed as `Path`. |
| I3 | High | Memory trajectories diverged from the pinned FC loop: no `add_memory_instruction_system_prompt`, no `execute_multi_turn_func_call([])` before the first query, and no `_flush_memory_to_local_file()` after a prerequisite. | Pinned `base_handler` FC loop. | Fixed: `OfficialBfclExecutor.initialize`, `memory_prompt`, `flush_prereq`. |
| I4 | High | Turn control differed from the pinned loop. The pinned loop decodes with `convert_to_function_call`, ends the turn on an exception or an empty decode, and force-quits after `count > 20` (at most 21 queries per turn), and a forced quit ends every remaining turn. | Pinned FC loop. | Fixed: `scoring.decode_execute` and `is_empty_execute_response` are exact ports; `forced_quit` recorded on the result line. |
| I5 | Medium | Held-out `miss_func` documents were sent with the language hint. The pinned loop adds them without it. | Pinned `load_dataset_entry`: `populate_test_cases_with_predefined_functions` moves held-out docs into `missed_function` before `add_language_specific_hint_to_function_doc` runs. | Fixed: `arm_tools(..., held_out=...)` converts held-out docs without the hint; pilot renders now include `held_out_turn_arms`. |
| I6 | Medium | A missing web-search or memory backend module would have failed mid-run after money was spent. A missing `SERPAPI_API_KEY` is worse: every search returns an error string, so web-search trajectories would be billed and scored on meaningless tool output. | Backend imports in the pinned executor and `WebSearchAPI`. | Fixed: `preflight` checks the BFCL root, backend modules, and that the keys are set and non-empty (never printed or stored) before any request. |
| I7 | Medium | The runner always planned thinking off then on; the pilot needed an external driver to send only off. | `original/run_thinking_off_pilot.py`. | Fixed: `--thinking off|on|off,on` is required with `--live`; any slot outside the authorised modes stops the run before a send. |
| I8 | Low | `compile_case` swallowed editor exceptions, so a broken editor could silently ship U bytes as S or X. | Old `pilot.compile_case`. | Fixed: editor errors propagate; the integrity checks fail closed. |

### Measurement

| # | severity | finding | evidence | status |
| --- | --- | --- | --- | --- |
| Me1 | High | Arms were sent in a fixed U, S, X, SX order inside each case, so later arms inherit the provider prefix cache. Cache-hit share by send position was 7%, 71%, 82%, 82%. The archived per-arm USD (U 0.01462, S 0.00999, X 0.00804, SX 0.00752) is an order effect: X and SX sent the same tools as U and S. | `single_turn.cache_by_send_position`. | Fixed for future runs: arm order rotates with case position (`ARMS[i % 4:] + ARMS[:i % 4]`), so each arm leads equally often. Rejected: per-arm `user_id` KV-cache isolation (see section 3). |
| Me2 | High | Paired single-turn deltas are mostly structural zeros. 17 of 20 S requests and 20 of 20 X requests were byte-identical to U, so any output or accuracy difference among them is sampling, not the editor. | `single_turn.paired`. | Reported with identical and differing cases separated. |
| Me3 | Medium | Trajectory arms took different paths. On `multi_turn_base_86` the billed steps were U 10, S 11, X 11 and SX 9 (stopped), with identical X and U tools. Totals mix description effects with model behaviour. | `trajectory[].arms[].steps_per_turn`. | Reported per arm, never as a saving. |
| Me4 | Medium | The sample is tiny (2–3 cases per category, 20–22 scored per arm) and SX has a different denominator (21). A one-case difference is not evidence. Rescored paired discordance S vs U: 20 both correct, 1 S only, 1 both wrong; the single U miss (`live_parallel_multiple_3-2-1`) occurred with tools identical to X and S. | `accuracy.rescored_paired_discordance`. | Reported as such. |
| Me5 | Low | BFCL aggregate CSVs mix categories with missing and full sets; they are not study totals. | `score/data_overall.csv`. | The report reads per-category score files only. |

### Operations

| # | severity | finding | evidence | status |
| --- | --- | --- | --- | --- |
| O1 | High | The 120 s `urllib` timeout applies per socket operation, not per request. The last bill completed at 11:40:19 HKT and the run stopped on `TimeoutError` at 11:44:57, up to 278 s later. | `original/artifacts/bills.jsonl`, `driver_summary.json`. | Fixed: per-read 120 s plus a 900 s total deadline enforced by closing the connection from a worker thread. |
| O2 | High | There was no record of a request before it was sent, so the timed-out request (which may be billed) has no row anywhere. | Bills only on completion. | Fixed: `attempts.jsonl` gets a `sent` line (hashes, byte size, time) before the send and `completed`, `failed` (`may_be_billed`), `unusable_response` or `stopped` after; lines are fsynced. `run.json` lists `uncertain_attempts`. No retry. |
| O3 | High | The stopped SX slot of `multi_turn_base_86` had nine billed steps and left no sidecar, so those outputs are lost. | Evidence README. | Fixed: the sidecar is rewritten after every step, with `turn_end`, executed calls and tool outputs. |
| O4 | Medium | Re-running into an output directory could resume or double-send. | Old runner. | Fixed: a directory with `attempts.jsonl`, `bills.jsonl`, or a `run.json` that contacted a provider is refused before case selection, plan write or key read. |
| O5 | Low | Thinking on uses the provider's default effort (high); reasoning content is passed back on tool turns because the provider requires it with tools. Both are deviations from a stock BFCL handler and are documented, not changed. | Provider docs; `NOTE.md`. | Documented. |

## 2. Literature, read for this review

Each source was fetched on 2026-11-25. What a paper measured is kept separate from what it claims, and nothing is reported as if it had been measured on BFCL here.

**Xu et al., "Concise and Precise Context Compression for Tool-Using Language Models", arXiv:2407.02043v1 (2 Jul 2024), Appendix A.1–A.2, Tables 6–8.** The headline (up to 16×) is soft-token compression with a fine-tuned LLaMA-7B; it needs training and does not apply to a black-box API. A.2 is the relevant baseline: GPT-4 Turbo rewrote only `description` fields, with regeneration until other fields were unchanged. It reached about 1.39× (API-Bank) and 1.42× (APIBench) compression (Table 8), and accuracy fell from 71.47 to 67.87 (API-Bank) and from 88.24 to 87.79 (APIBench) when tested on summarised docs (Table 7). A.1 (Table 6) shows that deleting non-key text entirely hurts accuracy badly (API-Bank 71.47 → 53.21). Takeaways: description-only hard summarisation buys roughly 30% on description text, not 16×, and description text is not free to drop.

**EasyTool, arXiv:2401.06201v3 (27 Mar 2024), §4.1–4.2, Table 3, Limitations, Appendix D (Table 7).** §4.1 has an LLM rewrite each tool's documentation into a purpose statement; §4.2 adds generated usage scenarios with parameters, which adds text. Table 3 reports per-document token counts (ToolBench 2530 → 748, −70.43%; RestBench 3881 → 103, −97.35%). Those are per document on verbose sources with example code, not per request, and BFCL descriptions are already short. The Limitations section says the method treats one document at a time and "neglect[s] the dependencies among tools", which is the gap X is meant to cover. Appendix D shows LLMLingua corrupting parameter and function tokens in tool documents.

**TSCG, arXiv:2605.04107v1 (4 May 2026); code `SKZL-AI/tscg` at `dfcba63d6190285c45a7c412268dbcc757664ab2` (`@tscg/core` 1.4.3, README "Description-Only Mode (v1.4.0)").** The paper's gains come from compiling JSON schemas into a text format (its own decomposition attributes most of the effect to the format change), which leaves the native boundary. The native `compressDescriptions` only applies SDM filler stripping (`packages/core/src/_engine.ts`, `FILLER_PATTERNS`), and the README's "~25-40% description savings" is a library estimate, not a provider measurement. Several patterns are unsafe on BFCL: `\bNote that\s*` rewrites the official language hint, `\bIndicates (?:the|whether)\s*` and `\bThe (?:value|name|...) (?:of |for )?(?:the |a )?` can leave fragments, and `\bto perform\b` deletes inside phrases.

**LLMLingua and LLMLingua-2, `microsoft/LLMLingua` README at `2c6af3f84b9a8f85d6b0903ec13dbed26b7dccf8` (2026-11-24).** Both need a local language model (GPT-2 small up to LLaMA-7B, or an XLM-RoBERTa/BERT token classifier for LLMLingua-2) and are token-level and not structure-aware; `force_tokens` protects listed strings only. EasyTool Appendix D documents the failure mode on tool documents.

**Sparck Jones (1972), "A statistical interpretation of term specificity and its application in retrieval", J. Documentation 28(1), sections "Statistical specificity" and "Weighting by specificity".** A term used across many documents discriminates poorly, though the abstract also notes that frequent terms "are required for good overall performance". This motivates keeping catalogue-wide boilerplate out of contrast evidence; it does not license deleting frequent text from descriptions.

**Carbonell and Goldstein (1998), "The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing Summaries", SIGIR, §2.** MMR combines query relevance with novelty against already-selected items. X has no query, because questions are not editor inputs, so MMR is only an analogy for "say what differs from the nearest rival"; it is not evidence that catalogue distinctiveness predicts tool choice.

**DeepSeek API docs, "Models & Pricing" and "Rate Limit & Isolation" (retrieved 2026-11-25).** These give the rate card in `NOTE.md`, the peak-hour definition, and the `user_id` parameter, documented as isolating KV cache per user.

### What changed because of the literature, and what did not

Adopted:
- Keep S description-only and deterministic, and keep any deletion tied to evidence in the tool's own schema or wording (Xu A.1 and A.2: descriptions carry information, and hard summarisation gives modest ratios even with a strong LLM).
- Report per-field and per-request tokens separately, and never present per-document reductions as request savings (EasyTool Table 3).
- Base X's contrast on the action sentence after setting aside the official hint, suite preambles and `This function` frames, so catalogue-frequent boilerplate never becomes evidence (Sparck Jones).
- Make X cover inter-tool dependencies by naming one rival per target, which per-document methods leave out (EasyTool Limitations).

Rejected:
- TSCG SDM filler stripping. It rewrites the language hint and has fragmenting patterns, and the rest of TSCG leaves the native boundary.
- LLMLingua and LLMLingua-2. They need a local model or GPU, are not structure-aware, and EasyTool Appendix D shows them damaging tool documents. They would add a new compressor, not revise S.
- LLM summarisation as S (Xu A.2, EasyTool §4.1). It would add a paid or local generation service, which this review was told not to add. A faithful broad semantic rewrite cannot be done offline with rules. S therefore stays a rule editor, and its coverage is what the rules can prove, not a whitelist dressed up as summarisation.
- EasyTool §4.2 usage scenarios. They add tokens, and generated examples would be invented content.
- MMR scoring. There is no query to score relevance against.

## 3. Editor revisions

**S (`s-rules-2026-11-25`).** S sees one complete original tool and nothing else. Each description is split into spans; every span is kept unless one of these rules proves a shorter version faithful:
- `schema_guaranteed`: drop a clause the unchanged schema already states (the pinned float suffix with `format: float`, an enum list equal to `enum`, a prose default equal to `default`).
- `suite_context`: when the text labels itself `Tool description:`, keep `This tool belongs to <suite>.` and the tool's own description, and drop the suite elaboration and the label.
- `direct_action`: drop a leading `This function` subject frame.
- `within_tool_duplicate`: drop a clause the function description already states.
- `flag_normalization`: rewrite a boolean `A flag to determine whether to ...` or `Indicates if X should be included in the result.` as a `Whether to ...` clause when its prose default equals the schema default. A trailing `of <noun>` is dropped only when that noun is in the function description, so the clause can lose context such as `of triangle` that the function description restates.

The language hint, names, negations, numbers, units, quoted literals and every non-description field are protected. Each changed field has a ledger row with every span, its decision and the reason (`package/s_ledger.jsonl`, 771 rows). Fields left alone are counted by reason in `s_keep_reasons.json`: 8135 already minimal, 464 with no shorter faithful candidate, and 20 ambiguous.

**X (`x-rules-2026-11-25.2`).** X sees the original U catalogue, never S. For each target, a rival qualifies when the two action sentences share their verb and differ in one short window (at most four words a side, at least one content word each, no negation), and the shared wording is at least as long as that window and contains a content word beyond the verb. Alternatively, the rival qualifies on interface when the required parameters differ in numeric shape. The cue is one sentence, `For <rival's own differing phrase>, use <rival>.`. It never says the target cannot do something, and banned words (`only`, `cannot`, `exclusively`, `unable`) are tested. One unrelated tool never blocks a pair, and a tool can stay uncued while its neighbours get cues. A one-tool catalogue gets no cue (X == U and SX == S on controls). Cues whose content words the rival's name already spells are dropped. `package/x_ledger.jsonl` records, for each catalogue, every cue with evidence from both sides, and the reason for each uncued tool (most often a different verb).

**SX.** SX is the exact S bytes plus the exact X cue bytes at `/function/description`, separated by one space. `integrity.json` checks, on all 3327 questions: membership and order unchanged, every non-description field identical, uncued X == U, uncued SX == S, cued X == U + cue, and cued SX == S + cue. All six checks pass on every question.

Rejected for X: per-arm `user_id` KV-cache isolation, because it adds a request field outside the BFCL request and its effect on generation is unverified. Rotating arm order addresses the same confound with no new field.

## 4. Offline package (`studies/clean-start-usx/package/`)

`python -m tool_compression.clean_start package` rebuilds every file byte for byte (tested). `manifest.json` records the Gorilla pin, rules versions, tokenizer, Python version, commands and SHA-256 of every file.

| file | content |
| --- | --- |
| `token_tables.json` | field and tools tokens per arm and deltas S−U, X−U, SX−S, SX−X, SX−U, overall, excluding the pilot draw, and per category; changed questions; cued tools; cue tokens |
| `integrity.json` | the six SX and immutability checks over 3327 questions and 1021 distinct catalogues |
| `s_ledger.jsonl`, `s_keep_reasons.json` | S provenance |
| `x_ledger.jsonl` | X cues and evidence on both sides, and the reason for each uncued tool |
| `examples.json`, `EXAMPLES.md` | edited and unchanged examples per in-scope set, with cases the rules cannot change marked |
| `pilot_2026_11_25_analysis.json` | paired tables from the archived pilot (section 5) |

Local counts use tiktoken `o200k_base`. "Field" means the editable description strings; "tools" means the compact JSON of the whole tools array. Neither is provider-billed usage. The initial catalogue of each question is counted once; held-out `miss_func` turns are not included.

| set | questions | S changed | X changed | U field | S−U field | X−U field | SX−S field | SX−X field | SX−U field | cue tokens | S−U tools | SX−U tools |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| multiple | 200 | 86 | 19 | 31608 | −1447 (−4.6%) | +405 (+1.3%) | +405 (+1.3%) | −1447 (−4.5%) | −1042 (−3.3%) | 405 | −2.1% | −1.5% |
| parallel_multiple | 200 | 74 | 21 | 28032 | −1359 (−4.8%) | +451 (+1.6%) | +451 (+1.7%) | −1359 (−4.8%) | −908 (−3.2%) | 451 | −2.2% | −1.5% |
| live_multiple | 1053 | 369 | 21 | 442912 | −3173 (−0.7%) | +539 (+0.1%) | +539 (+0.1%) | −3173 (−0.7%) | −2634 (−0.6%) | 539 | −0.4% | −0.3% |
| live_parallel | 2 | 0 | 0 | 294 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0% | 0.0% |
| live_parallel_multiple | 24 | 12 | 0 | 9395 | −87 (−0.9%) | 0 | 0 | −87 (−0.9%) | −87 (−0.9%) | 0 | −0.5% | −0.5% |
| live_irrelevance | 372 | 128 | 11 | 157597 | −1552 (−1.0%) | +273 (+0.2%) | +273 (+0.2%) | −1552 (−1.0%) | −1279 (−0.8%) | 273 | −0.5% | −0.4% |
| live_relevance | 11 | 5 | 0 | 4226 | −29 (−0.7%) | 0 | 0 | −29 (−0.7%) | −29 (−0.7%) | 0 | −0.3% | −0.3% |
| multi_turn_base | 200 | 200 | 95 | 397294 | −134656 (−33.9%) | +2700 (+0.7%) | +2700 (+1.0%) | −134656 (−33.7%) | −131956 (−33.2%) | 2700 | −14.3% | −14.0% |
| multi_turn_miss_func | 200 | 200 | 95 | 379202 | −128936 (−34.0%) | +2550 (+0.7%) | +2550 (+1.0%) | −128936 (−33.8%) | −126386 (−33.3%) | 2550 | −14.4% | −14.1% |
| multi_turn_miss_param | 200 | 200 | 95 | 397294 | −134656 (−33.9%) | +2700 (+0.7%) | +2700 (+1.0%) | −134656 (−33.7%) | −131956 (−33.2%) | 2700 | −14.3% | −14.0% |
| multi_turn_long_context | 200 | 200 | 95 | 397294 | −134656 (−33.9%) | +2700 (+0.7%) | +2700 (+1.0%) | −134656 (−33.7%) | −131956 (−33.2%) | 2700 | −14.3% | −14.0% |
| memory_kv | 155 | 155 | 155 | 159185 | −37200 (−23.4%) | +24800 (+15.6%) | +24800 (+20.3%) | −37200 (−20.2%) | −12400 (−7.8%) | 24800 | −11.5% | −3.8% |
| memory_vector | 155 | 155 | 155 | 100285 | −29760 (−29.7%) | +3720 (+3.7%) | +3720 (+5.3%) | −29760 (−28.6%) | −26040 (−26.0%) | 3720 | −11.4% | −10.0% |
| memory_rec_sum | 155 | 155 | 0 | 42625 | −11625 (−27.3%) | 0 | 0 | −11625 (−27.3%) | −11625 (−27.3%) | 0 | −13.0% | −13.0% |
| web_search_base | 100 | 100 | 0 | 20800 | −3400 (−16.3%) | 0 | 0 | −3400 (−16.3%) | −3400 (−16.3%) | 0 | −5.8% | −5.8% |
| web_search_no_snippet | 100 | 100 | 0 | 20800 | −3400 (−16.3%) | 0 | 0 | −3400 (−16.3%) | −3400 (−16.3%) | 0 | −5.8% | −5.8% |
| **all in scope** | 3327 | 2139 | 762 | 2588843 | −625936 (−24.2%) | +40838 (+1.6%) | +40838 (+2.1%) | −625936 (−23.8%) | −585098 (−22.6%) | 40838 | −10.7% | −10.0% |
| excluding pilot draw | 3280 | 2109 | 751 | 2549095 | −615723 (−24.2%) | +40107 (+1.6%) | +40107 (+2.1%) | −615723 (−23.8%) | −575616 (−22.6%) | 40107 | −10.7% | −10.0% |

X−U equals the cue cost exactly, as composition requires. The figures excluding the 47 exposed pilot cases match the overall figures to within 0.03 percentage points.

Where the rules cannot act, the table shows it. X has no cue on `live_parallel`, `live_parallel_multiple`, `live_relevance`, `memory_rec_sum` or either web set, because no pair of action sentences qualifies. S changes nothing on `live_parallel`, and live sets change by about 1% or less, because their descriptions are mostly already minimal.

## 5. Pilot, re-read from saved data (`package/pilot_2026_11_25_analysis.json`)

`python -m tool_compression.clean_start report-pilot` rebuilds this file from `evidence/pilot-2026-11-25-thinking-off/` without any request. Provider fields are billed usage; `sent_local_*` and `revised_local_*` are local counts of the tools sent at the pilot tip and of the revised editors on the same cases.

- **Scope.** The run was thinking off, in the peak band. It produced 151 bills ($0.040170708), finished 87 of 188 slots, and stopped inside `multi_turn_base_86` SX. 20 single-turn cases were sent with all four arms, plus two trajectories: `multi_turn_base_120` (all four arms) and `multi_turn_base_86` (U, S and X finished, SX stopped). Memory and web cases were not sent.
- **Field vs request vs billed.** S−U on the three single-turn cases whose tools differed: provider prompt −26 tokens, local tools −25, local field −25. On the 17 identical cases the provider delta is exactly 0. X−U is 0 on all 20. For the same 20 cases, the revised editors would give S−U −27 local tokens and X−U +22.
- **Output effects.** The summed output-token deltas over the 20 cases are S−U +24, X−U +4 and SX−S −52, all with identical or near-identical tools, so they are sampling variation.
- **Caching.** Cache-hit share by send position was 0.07, 0.71, 0.82 and 0.82. The USD deltas (S−U −$0.00412, X−U −$0.00481) come from send order, not editors.
- **Trajectories.** Billed steps per turn on `multi_turn_base_120` were U [3,2,3], S [3,2,3], X [3,2,2], SX [3,2,2]. On `multi_turn_base_86` they were U [5,3,2], S [5,3,3], X [5,3,3], and SX stopped after 9 steps. Provider prompt totals differ by path length, not by description.
- **Accuracy.** Archived scores (`underscore_to_dot=False`) were U 14/22, S 14/22, X 14/22, SX 13/21. Rescored with the pinned flags: U 20/22, S 21/22, X 21/22, SX 20/21. The only remaining failures are `live_parallel_multiple_8-7-0` (all arms) and `live_parallel_multiple_3-2-1` (U only, with tools identical to X).
- **Local tokens on the 47 pilot cases.** As sent at the pilot tip: U 39748, S 39027, X 43960, SX 43239 field tokens. With the revised editors: U 39748, S 29535, X 40479, SX 30266.

None of this is a measured saving or an accuracy finding about the revised editors, which have never been sent.

## 6. Reproduction

Offline, no network needed:

```bash
pip install -e ".[test]"
pytest -q                                              # full suite; gated tests skip
python -m tool_compression.clean_start manifest        # BFCL package byte identity
python -m tool_compression.clean_start freeze          # pilot renders and limitations
python -m tool_compression.clean_start package         # this package, byte for byte
python -m tool_compression.clean_start report-pilot    # pilot analysis from archived evidence
python -m tool_compression.clean_start run --pilot --out /tmp/plan   # dry plan, no key, no socket
(cd studies/clean-start-usx/evidence/pilot-2026-11-25-thinking-off/original && sha256sum -c ../SHA256SUMS)
```

Official scoring and the pinned-executor tests need the Gorilla checkout at `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8` and its Python dependencies. In a virtual environment, `pip install -e <gorilla>/berkeley-function-call-leaderboard` installs them. This review's VM had no `ensurepip`, so the same pinned packages were installed with `pip install --target /tmp/bfcl-deps` and put on `PYTHONPATH`.

```bash
git clone https://github.com/ShishirPatil/gorilla /tmp/gorilla && git -C /tmp/gorilla checkout 6ea57973c7a6097fd7c5915698c54c17c5b1b6c8
CLEAN_START_BFCL_ROOT=/tmp/gorilla pytest -q tests/test_clean_start_runner.py tests/test_clean_start_package.py
cp -r studies/clean-start-usx/evidence/pilot-2026-11-25-thinking-off/original/artifacts/result /tmp/rescore/result
python -m tool_compression.clean_start evaluate --out /tmp/rescore --bfcl-root /tmp/gorilla --thinking off
```

A later live run needs explicit authorisation and is not started here. Its form is:

```bash
python -m tool_compression.clean_start run --pilot --live --authorize-live \
  --thinking off --memory-prereqs matched --ceiling-usd <USD> \
  --bfcl-root /tmp/gorilla --out <new empty dir>
python -m tool_compression.clean_start evaluate --out <same dir> --bfcl-root /tmp/gorilla --thinking off
```

## 7. Tests added or changed

`tests/test_clean_start_runner.py` uses mocked transports throughout; `urlopen` and sockets are not reachable. It checks:
- Thinking-mode parsing, refusal of unauthorised modes before any send, and no slot expansion.
- An attempt journalled before each send, with `failed` and `may_be_billed` on timeout and no retry.
- The total deadline enforced on a trickling connection.
- Per-step sidecar persistence when a trajectory stops mid-turn.
- Refusal of output-directory reuse before the key read.
- Preflight of backend modules and key presence.
- Memory prompt, initialisation and flush order; the pinned decode and empty-turn rules; force quit after 21 queries.
- Held-out documents sent without the hint.
- Arm rotation.
- A gated end-to-end trajectory through the pinned executor and memory backend.

`tests/test_clean_start_package.py` checks:
- The archived evidence still matches its 170 checksums.
- The package regenerates byte for byte and its manifest hashes hold.
- Integrity passes on 3327 questions.
- X−U equals the cue cost.
- Every S ledger fact maps back to its source span and kept spans survive.
- The language hint is untouched.
- Every X cue names one rival with evidence on both sides and no banned word.
- The name-redundancy rule, on fixtures.
- Editor modules contain no question, gold or score access.
- The pilot report regenerates and its summary holds.
- The sent-render digest matches `git show 0c0284d` (when the commit is present).
- Official rescoring reproduces the committed scores (gated).

Existing tests in `tests/test_clean_start_usx.py` keep checking arm isolation of result files, snapshots and instances, schema, membership and order immutability, and that the dry pilot stays offline.

## 8. Blockers and limitations

- **No empirical result for the revised editors.** Nothing here says S, X or SX preserves accuracy or saves billed tokens. The authorised pilot is the next step, and its n is too small for anything beyond a pipeline check and gross-regression screen.
- **Suite-context deletion is the main semantic risk** (M4). If the pilot shows multi-turn or memory regressions, this rule is the first suspect and can be dropped on its own; it is a separate `change_class` in the ledger.
- **Memory prerequisites cost.** `--memory-prereqs matched` makes the pilot's memory portion about ten times larger. `none` keeps it small but leaves memory scores uninterpretable. That choice belongs to whoever authorises the run.
- **External services.** `memory_vector` downloads SentenceTransformer weights on first use. Web search calls SerpAPI, which is billed separately and is not in the DeepSeek ceiling.
- **Thinking on** uses the provider's default effort, and reasoning content is passed back on tool turns. Both differ from a stock BFCL handler.
- **Provider tokenizer.** Local `o200k_base` counts track the provider on the three changed pilot cases (−25 vs −26), which is far too few to calibrate. The provider's rendering of float-suffixed and enum-bearing schemas is unverified.
- **Cache.** Rotation balances send position across arms; it does not remove cache sharing. Per-arm `user_id` isolation was not adopted (section 3).
- **Uncertain charge.** The timed-out 25 Nov request may have been billed without a bill row; its cost is not in $0.040170708.
- **No official settlement.** `official_settlement` is false everywhere, and this package is not READY for a claim.
