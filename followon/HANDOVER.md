# Follow-on handover

This package is ready for a separately authorized evaluation. It is not a measured result. No provider was called, and no price was invented.

## What is already closed

Evaluation Protocol v1.1 and the submitted proposal govern the thinking-off Flash reference run only. That run, its hashes, snapshots, and the 10% C-versus-U target stay as recorded. The target was not met: primary L removed 1398 of 121018 provider input tokens, and official accuracy was U 186/200, L 185/200, E 186/200. Those thresholds are historical reference, not a reset test for T1 or T2.

Pull request #4, at `3a02e64888c5359f48d2b417ac659161cd3eadae`, supplied the saved-output scoring package. This branch starts from that commit and does not merge it. `DeepSeek-V3.2-Exp-FC` remains a scoring alias. Generation under that alias is refused because its registry model name is `deepseek-chat`.

## What these two conditions are

T1 and T2 are one phrase-level extractive compressor. T1 ranks optional aliases and illustrations with the tool's own identifier overlap. T2 adds `1/2 × q`, the pinned prior neighbour score from `lexical.contrast_q`, on those same pieces. The cap `max(floor(0.75 × d), p)` and the weight `1/2` are new-trial settings. They do not retune `week1.0`.

The frozen rules are `FOLLOWON-SPECIFICATION.md`. Fixture catalogues are not benchmark rows.

## Offline audit

Ready for evaluation: true. Measured: false. Implementation defects: 0.

Primary eligible fields observed 2101 against the Week 1 inventory 2101 (reconciled: true).

| Row | Name | Fields | Cases |
| --- | --- | --- | --- |
| 1 | opportunity | 0 / 2101 | 0 / 200 |
| 2 | neighbour | 0 / 2101 | 0 / 200 |
| 3 | ranking | 0 / 2101 | 0 / 200 |
| 4 | delivered | 0 / 2101 | 0 / 200 |

| Category | n | f_new | Request groups | T1 fields changed vs U | T2 fields changed vs U | Fields T2≠T1 |
| --- | --- | --- | --- | --- | --- | --- |
| multiple | 200 | 0/200 | 200 | 0 | 0 | 0 |
| simple_python | 400 | 0/400 | 400 | 0 | 0 | 0 |
| irrelevance | 240 | 0/240 | 240 | 0 | 0 | 0 |

| Category | Stop reason | Cases |
| --- | --- | --- |
| multiple | indivisible_single_clause | 30 |
| multiple | no_two_optional_fragments | 170 |
| simple_python | indivisible_single_clause | 142 |
| simple_python | no_two_optional_fragments | 258 |
| irrelevance | indivisible_single_clause | 86 |
| irrelevance | no_two_optional_fragments | 154 |

Optional fragments marked by the frozen grammar: multiple 0, simple_python 0, irrelevance 0. With no optional fragment, no field has two pieces that can compete, so every funnel row is zero. T1, T2, and U requests were compared as raw JSON. The identical counts above mean there is no request difference on which to score a model. The grammar and scores were not adjusted to raise these counts.

Single-tool controls are `simple_python` and `irrelevance`. A T2 versus T1 request difference there is an implementation defect.

## Scoring path

Historical official counts were recomputed from `official/settlement/official_settlement.json` with network access unused. Reproduction ok: true. The raw 18 November flight trees are not in this repository; their manifest digests stay null. The committed settlement is the saved-output reproduction. Archived answers are not attached to T1 or T2. A join fails on duplicate, missing, or hash-mismatched rows.

Provider input `T`, official accuracy, name hits, and abstention counts for T1 and T2 are unmeasured. The reporting shell leaves those cells null.

## Later T1 and T2 flight

The phrase compressor is unchanged. `followon/FLIGHT.md` is the operator path for a later thinking-off `deepseek-flash` flight of all 840 cases, scored with official `bfcl evaluate` on saved outputs. `DeepSeek-V3.2-Exp-FC` stays scoring-only.

The reconfirmed audit is `followon/flight_readiness.json`. Where that file records T1, T2, and U flight bodies as identical, a later flight is a same-request re-draw of official U, not a new compressed catalogue. The plan still contains every multiple, simple_python, and irrelevance case for T1 and for T2.

The command requires `EXPLORATORY_CEILING_CNY` or `--ceiling-cny`. There is no default. The remaining authorization is ¥48.74670004 of ¥50, and that figure is a cap, not a filled-in ceiling. `--live` is required before a client is built. This package does not call the provider.

A comparison against official U is exploratory. It does not revise the closed C-versus-U result, and it does not invent provider `T` for an arm that has not been flown. Official L and E are not re-flown. The official-compressor robustness settings are not part of this package.
