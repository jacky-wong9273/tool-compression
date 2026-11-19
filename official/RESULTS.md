# How input structure, conservative retention, and provider accounting limit description-only compression

Organizing question: how do input structure, conservative retention, and provider accounting limit the practical benefit of native description-only compression in this benchmark setting?

This account is the recorded 18–19 November 2026 thinking-off replicate. Binding protocol: Evaluation Protocol v1.1. Pins: BFCL / gorilla `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`; TSCG `dfcba63d6190285c45a7c412268dbcc757664ab2` / `@tscg/core` 1.4.3; thinking `{"type":"disabled"}`; `r = 0.75`, Jaccard at least 1/5, at most two neighbours, `λ = 1/2`. Settings were not retuned. L is a reporting label for the shared P/I/C request. The reference comparison is C versus U, reported as L versus U. E versus U is a separate report and cannot satisfy the C–U target.

Four labels are used below.

- **Measured.** A figure computed from the locked official settlement, the usage table, or the Week 1 characterization.
- **Trace-supported.** An explanation that follows from implementation counts in those records, such as selection differences, protection reasons, and early-stop flags.
- **Plausible interpretation.** A reading of one stochastic response. It is not a causal claim.
- **Not established by this configuration.** A claim this single audited setting does not support.

In this single thinking-off replicate, the shared local intervention produced small provider-input savings and remained within the prespecified observed primary accuracy-loss margin. The combined utility target was not reached. These results do not establish statistical non-inferiority or general quality preservation.

L−U is −0.5 percentage points; the observed accuracy loss is +0.5 points.

The study statistic `T` is billed-basis provider total input (`prompt_tokens`), including cached and uncached components. The target is a 10% ratio of means on that statistic, together with the prespecified observed accuracy-loss margin. Both clauses are required. `mean_of_per_case_ratios` is recorded and is a different summary from the ratio of means.

## 1. Selected-input characterization

**Measured.** Local counts use `o200k_base` and come from `evidence/week1_characterization.json`. Provider totals come from `official/settlement/official_settlement.json`. Description-field tokens, local serialized-request tokens, and provider `T` are three counters. Their denominators differ.

| Category | Description-field tokens removed | Local request tokens removed | Provider `T` removed |
| --- | ---: | ---: | ---: |
| multiple (primary) | 1,403 of 24,924 (achieved 23,521) | 1,403 of 72,135 (70,732 left; ratio of means 0.01945) | 1,398 of 121,018 |
| simple_python | 704 of 18,894 (achieved 18,190) | 700 of 66,596 (65,896 left; ratio of means 0.010511) | 702 of 149,432 |
| irrelevance | 955 of 11,449 (achieved 10,494) | 964 of 38,560 (37,596 left; ratio of means 0.025) | 959 of 88,495 |

On the primary category the three removals are numerically close in this run: 1,403 local description tokens, 1,403 local request tokens, and 1,398 provider input tokens. The control rows are numerically close as well and are not identical (704 / 700 / 702 and 955 / 964 / 959). That closeness is a property of this run. It is not a general one-for-one accounting relationship between local tokens and provider tokens.

Primary description retention is 23,521 / 24,924, about 94.37% of the description-field count. The local request ratio of means is 1.945%. The provider ratio of means is 1.155%. Most of the serialized request is outside the description fields, so a large share of description text retained still leaves a small share of the request, and the provider denominator is larger again.

**Measured local-text diagnostic.** Replacing every allowlisted primary description with an empty string changes the local request from 72,135 tokens to 48,220. The removed text is 23,915 of 72,135 tokens, a ratio of means of 0.331531 (33.15%). The Week 1 characterization records this as a local orientation of description share. BPE counts are not monotonic. The figure is a local-text diagnostic only.

**Trace-supported structure, primary category.** There are 2,101 description fields and 557 tools. 1,625 fields are a single span (about 77.3%). 278 multi-span fields are entirely protected. 198 fields contain an optional span (200 optional spans). Of those fields, 196 drop every optional span and 2 retain an optional span. Protection reasons on the C trace: first span 2,101, default 317, literal 283, unit 197, condition 105, restriction 83, negation 32. Neighbour degrees are 275 / 166 / 116, mean degree 0.714542. C versus U request differences are 89 of 200. The active fraction `f` is 0/200.

The controls have no neighbours under the tested threshold: degree 0 on all 400 `simple_python` tools and all 240 `irrelevance` tools. Single-span fields are 1,238 of 1,570 and 682 of 933. Optional spans are almost all dropped (91 of 94 fields, and 136 of 136). C versus U request differences are 80 of 400 and 85 of 240.

**Trace-supported.** P records `stopped_early` on 198 primary fields, 94 `simple_python` fields, and 136 `irrelevance` fields. I and C record `stopped_early` 0 on each category. Field-level and case-level selection differences for C versus I and for P versus I are 0 on all three categories. The early-stop path and the scored path reach the same selected text in this trace. The trace records that coincidence. It leaves open whether another feasible selection exists under the same rules.

Arm E, at its own pinned operating point, changes 149 primary records, 154 `simple_python` records, and 116 `irrelevance` records. Its primary local request ratio of means against U is 0.004713 (72,135 to 71,795). That local figure is smaller than the local C versus U ratio. It is still a local count, and section 2 gives the provider comparison.

## 2. Official U / L / E comparison

**Measured.** Official scoring used saved outputs. The handler alias was `DeepSeek-V3.2-Exp-FC` because `deepseek-flash` is not in the pinned official registry. The alias is an evaluation handler. It is not a V3.2-Exp leaderboard claim. The flight requested and returned `deepseek-flash` on all 1,513 physical calls (`DeepSeek-V4.1-Flash-1017`). Thinking was `{"type":"disabled"}` on all 1,513 request bodies. The registry entry’s `model_name` is `deepseek-chat`. This package refuses `bfcl generate` under the alias. Registry flags used for scoring are `is_fc_model` true and `underscore_to_dot` true.

**Measured checks, cited from `official/tables/measurement_chain.json` and the Week 1 conversion record.** Week 1 conversion parity checked 840 records with 0 mismatches (`convert_to_tool`, `OPENAI_COMPLETIONS`). Dotted tool names in the flight requests: 0. Dotted names in parsed calls: 0. `decode_ast` for `is_fc_model` JSON-loads already-parsed `model_responses`. The official evaluate logs used the dummy key `UNUSED_OFFICIAL_EVAL_NO_PROVIDER_CALL`. The score JSON `model_name` field is the alias.

`data_overall.csv` Overall Acc in that scoring run is 6.95% (U), 6.99% (L), and 6.99% (E). Official rollups treat unevaluated categories as 0. Those rollups are not study metrics. The study accuracies are the three category rows below.

### Primary category (`multiple`, 200)

| Arm | Correct | Provider `T` sum | Mean `T` |
| --- | ---: | ---: | ---: |
| U | 186 (0.93) | 121,018 | 605.09 |
| L | 185 (0.925) | 119,620 | 598.10 |
| E | 186 (0.93) | 120,707 | 603.535 |

L versus U: delta numerator −1, so L−U is −0.5 percentage points and the observed accuracy loss is +0.5 points. The one L gain is `multiple_132`. The L losses are `multiple_45` and `multiple_186`. The descriptive accuracy clause stays inside the prespecified observed margin of 1/50. `S_LU` is 1,398 / 121,018 = 0.011552000528846949 (1.155%). Mean saving is 6.99 tokens per request. `mean_of_per_case_ratios` is 0.010713914615263895 and is not the target statistic. The token clause misses 10%. The combined target is not reached. `target_lowered` is false. Statistical non-inferiority is `not_tested`.

E versus U: accuracy delta 0. The E gain is `multiple_132` and the E loss is `multiple_25`. Equal primary counts are not the same cases. `S_EU` is 311 / 121,018 = 0.002569865639822175 (0.257%). That comparison is reported separately and cannot satisfy the C–U target.

Primary request groups: 600 logical arm assignments, 438 independent observations, 162 reused members. A reused member shares the official outcome and the provider usage of its request group.

### Controls

| Category | U | L | E | `S_LU` | `S_EU` |
| --- | ---: | ---: | ---: | ---: | ---: |
| simple_python (400) | 379 | 373 | 377 | 702 / 149,432 = 0.004697788960865142 | 278 / 149,432 = 0.0018603779645591306 |
| irrelevance (240) | 184 | 187 | 186 | 959 / 88,495 = 0.010836770439007853 | 196 / 88,495 = 0.002214814396293576 |

Every billed-basis `S_LU` in this replicate is under 10%. `simple_python` L losses are `simple_python_36`, `93`, `137`, `152`, `225`, and `285`. E losses on that category are `249` and `360`. `irrelevance` L gains are `14`, `16`, `108`, and `191`; the L loss is `106`. E gains are `32`, `73`, `99`, `157`, and `191`; E losses are `60`, `160`, and `222`.

## 3. Billed-basis `T` and the cache-associated input-cost figure

**Measured.** On all 1,513 physical calls, `prompt_tokens = prompt_cache_hit_tokens + prompt_cache_miss_tokens`. Logical primary sums:

| Arm | Cache hit | Cache miss | Total input `T` | Cases with a cache hit |
| --- | ---: | ---: | ---: | ---: |
| U | 3,451 | 117,567 | 121,018 | 23 |
| L | 17,659 | 101,961 | 119,620 | 81 |
| E | 20,091 | 100,616 | 120,707 | 102 |

The price-weighted input sum uses the locked off-peak relative prices, cache hit at 0.02 and cache miss at 1, under the observed cache mix. It is not divided into currency here. The recorded primary price-weighted `S_LU` is 0.1302478611568131. The same construction is 0.05353300534602582 on `simple_python` and 0.10184429285486692 on `irrelevance`.

**Measured ordering.** On primary billed-basis `T` the order is U, then E, then L (121,018; 120,707; 119,620). On the price-weighted input sum the order is U, then L, then E. The two measurements rank L and E differently in this run. That ranking difference is a measured illustration that the measurements differ.

The price-weighted figure is a run-specific input-cost difference under the observed cache mix, calculated from valid usage records and prices. It is a different measurement from billed-basis total input, and it is not the study statistic. Cache-associated input-cost differences are reported separately from input-token reductions. They do not establish attainment of the token target. This execution does not isolate compression-caused deployment savings from cache state, request order, or prefix reuse. They also do not establish a claim about total cost.

**Measured monetary ledger, separate again.** Stage B recomputes to ¥1.24290304 from 669,623 input tokens (83,702 hit, 585,921 miss), 163,827 output tokens, and 1,513 physical calls, using ¥0.02 / ¥1 / ¥4 per million hit, miss, and output tokens. Stage A is ¥0.00817336. The cumulative ledger is ¥1.25107640. That ledger includes output tokens. It is neither `T` nor the price-weighted input ratio.

## 4. Mixed accuracy, by change class

**Measured class sizes** come from the Week 1 characterization. **Measured class-conditional official counts** and the primary provider-token split come from the 19 November diagnosis and are stored in `official/tables/change_class_join.json`. They add to the official totals. Per-case flight rows are not in this checkout, so the class token split is the recorded aggregate and is not recomputed from JSONL here.

| Category | Class | n | Correct U | Correct L |
| --- | --- | ---: | ---: | ---: |
| multiple | unchanged | 111 | 101 | 101 |
| multiple | suffix-only | 53 | 51 | 52 |
| multiple | other-change | 36 | 34 | 32 |
| simple_python | unchanged | 320 | 304 | 304 |
| simple_python | suffix-only | 35 | 32 | 30 |
| simple_python | other-change | 45 | 43 | 39 |
| irrelevance | unchanged | 155 | 118 | 118 |
| irrelevance | suffix-only | 57 | 45 | 48 |
| irrelevance | other-change | 28 | 21 | 21 |

Unchanged rows are tied on the official L versus U outcome. Primary provider input removed on changed cases is 850 on the 53 suffix-only cases and 548 on the 36 other-change cases. Unchanged cases contribute 0. The sum is 1,398. Means on the changed classes are about 16.04 and 15.22 tokens, and 1,398 / 89 is about 15.71 tokens on a changed primary case.

**Measured irrelevance decode split.** Official successes are text answers with no call: U 184, L 187, E 186. Official failures are decoded calls: 56, 53, and 54. Parse or decode failures counted as correct: 0 on every arm. The accuracy movement is a call-versus-no-call movement.

**Plausible interpretation, one stochastic response each.** These alignments are specific enough to report. They are not causes established by this replicate.

- `multiple_45` (other-change, L loss). L dropped “e.g Ice age” from `era_name` and called a history tool. U and E called the geology tool with `era_name` “Ice age”.
- `multiple_186` (other-change, L loss). L dropped the recipe-type examples and filled `recipe_type` with “brownies”. U and E used “dessert”.
- `multiple_132` (suffix-only, L gain and E gain). L removed the handler sentence “This is a float type value.” U passed `rate_of_return` 8. L and E passed 0.08.
- `simple_python_36`, `93`, `225`, and `285` (other-change, L losses). L dropped a format or example cue, and the official error is a string mismatch on that slot.
- `simple_python_137` and `152` (suffix-only, L losses). U used the fractional rate and L used the percent-as-integer. The direction is the opposite of `multiple_132`.
- `irrelevance_14`, `16`, and `108` (suffix-only, L gains) and `irrelevance_191` (other-change, L and E gain) are text answers where U decoded a call, except that the diagnosis records the particular user questions and calls.
- `irrelevance_106` (other-change, L loss). L dropped the soil examples and called `soil_analysis_analyze_soil_type` with `soil_type` “loam”, an example that had been in the dropped text. U and E answered in text.

E does not reproduce L’s six `simple_python` losses. `multiple_25` is an unchanged U=L success and an E loss: the diagnosis records E at 640 input tokens and U at 635, with a punctuational description difference and a wrong function count. The diagnosis does not assign suffix-only versus other-change to `irrelevance_60` and `irrelevance_99`. Those two cases stay unclassified here.

## 5. The observed C–I coincidence

**Measured.** At the audited setting, C and I produced identical complete requests on all three categories. With shared responses, their observed paired accuracy difference is therefore zero. This setting provides no behavioural comparison between different contrast-aware and independent selections. That is a zero realized intervention difference, with limited implications beyond this setting.

**Trace-supported.** Span structure, protection, and field budgets strongly constrain selection. Under the tested scoring rules, the resulting selections coincide: selection differences are 0 at field and case level, including P versus I, while P’s `stopped_early` counts differ from I and C. On the controls the neighbour graph has degree 0, so the contrast term has no neighbour to score. On the primary category the graph does have neighbours, mean degree 0.714542, and the selections still coincide. Neighbour absence on the controls is therefore only part of the trace. The traces do not establish that the protection floor is the only selection the rules allow.

## 6. C versus I preprocessing overhead

**Measured, and not separable.** The Week 1 characterization records 2.287 seconds for the combined P/I/C preparation of the study catalogues. That single clock does not separate C from I. Arm E’s preparation clock in `evidence/week1_arm_e.json` is 0.506 seconds. Request latency is not a field of the flight ledger used here.

**Measured, CPU only, this checkout.** `official/tables/preprocessing_overhead.json` times `compress` for P, I, and C separately on synthetic catalogues, with one warmup and five timed passes in rotated order, using `o200k_base`. No model is called. The corpus is 48 catalogues. It is not the BFCL catalogue. On that corpus the multi-tool medians (three tools) are about 0.0582 s (P), 0.0586 s (I), and 0.0796 s (C). The median C minus I gap is about 0.0210 s, and C/I is about 1.36. The single-tool medians are about 0.0196 s, 0.0196 s, and 0.0199 s, with a C minus I gap of about 0.00025 s. All 48 catalogues in each block have identical P, I, and C selections. The JSON holds the unrounded medians from this Python 3.12.3 run. Another machine, or another run, will report different wall-clock numbers. The identity of the selections on this synthetic corpus follows from a long protected first span that exceeds `r = 0.75`. That identity is an exercise result. It does not reopen the BFCL coincidence, which is already measured in section 5.

## 7. Uncertainty

**Measured design facts.** One replicate. Thinking disabled. Model `deepseek-flash`. Primary groups are 438 independent observations and 162 reused members inside 600 logical arm assignments. Reused members are not extra independent observations. Cross-case dependence is not modelled. The protocol’s section 6 therefore has no confidence interval to report: one replicate does not identify a sampling distribution.

Statistical non-inferiority was not tested. General quality preservation is not a result of this replicate. Same-setting replicates are outside this package. Additional replicates at this setting would still leave the broader safety claim unestablished, because the dependence across cases and the single audited configuration would remain.

## 8. What this configuration cannot establish

This single configuration does not establish:

- statistical non-inferiority
- general quality preservation
- a full BFCL leaderboard result
- a behavioural comparison of different contrast-aware and independent selections
- isolation of compression-caused deployment savings from cache state, request order, or prefix reuse
- a total-cost claim
- attainment of the 10% billed-basis token target

The practical limit in this benchmark setting is visible in the three measured layers together. Description fields are mostly one protected span, so the audited policy retains about 94% of primary description tokens. The provider denominator is the whole billed request, so the same edit is a 1.155% reduction in `T`. The cache-associated input-cost figure moves much more under the observed cache mix, and it answers a different question from `T`.
