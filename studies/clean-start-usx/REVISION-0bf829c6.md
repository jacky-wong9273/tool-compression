# Diagnosis of the 0bf829c6 validation flight and revision of S, X, SX (2026-11-26)

Base: the flown PR #28 tip `0bf829c6c2d24e5efa0483c7447c7ed0df4c53b9`, editors `s-rules-2026-11-25.2` and `x-rules-2026-11-25.3`. The flight's evidence is archived unmodified in `evidence/validation-2026-11-25-0bf829c6/` (archive SHA-256 `93f360f99f5fe6841374ebb737f0180b0fd4212ef524eb348965fb9713faff9d`, 1498 files, `SHA256SUMS`). `official_settlement` stays false. Nothing in this revision sent a provider request, read a key, retried, resumed, or re-ran a flight.

**Both flown draws are now exposed.** The 41-case pilot and the 313-case validation draw have been flown and diagnosed case by case. They are regression and diagnostic data from here on, not unseen validation for these or any later editors. Neither draw was changed.

Editors stay blind to questions, ids, gold answers, model outputs, scores and files. Every rule below is general and grounded in the tool catalogue: it reads one tool's own text and schema, plus which verbatim request-level excerpts earlier tools in the same request carry. No rule names a case id or a tool. The flight evidence was used offline to find where the editors spend and save tokens and whether any paired difference has a mechanism. The draws appear only in diagnostic and regression tests.

## Outcome

- **The flight does not show any editor changing accuracy.** All four arms finished 303 scoring cases: U 250, S 250, X 248, SX 252 correct (82.5%, 82.5%, 81.8%, 83.2%). Nineteen cases differ between arms. Among single-turn arm pairs that sent byte-identical tools, 22 of 880 pairs still differed in outcome (2.5%). The arm differences are within that noise, and no replicate U was run.
- **X's new `live_irrelevance` loss is noise.** X scored 50 of 64 against U's 54. In all four cases X lost and U won, X sent exactly U's bytes, because X cued no tool there. Across all single-turn cases, no X−U discordance involves a tool X changed.
- **No S or SX mechanism clears the noise floor.** The one plausible S mechanism is the float suffix S drops: on `parallel_multiple_166`, S and SX passed 7 where U and X passed 0.07. Among the 70 S-edited parameters that both U and S filled, that is the only value difference. Arms that sent identical text for a parameter also differed once in 70 (`parallel_multiple_75`). The two cases where SX alone failed sent exactly the bytes S sent; S passed both, so they are noise and not an SX interaction.
- **The flight measured modest savings because of where the tokens sit, not because S was timid on prose.** Half of the U tools tokens are names, schema and JSON (51.0% on the validation draw). In single-turn catalogues, the remaining description text is mostly unique real-API prose. The large redundant structures are request-level repeats: the official language hint on every tool, and suite preambles on every multi-turn and memory tool. Before this revision, S never touched the hint and kept every membership sentence.
- **Revised editors (`s-rules-2026-11-26`, `x-rules-2026-11-26`).** S now states each language hint and each suite membership once per request. Later tools drop the byte-identical hint and name their suite as a label (`Gorilla file system: ...`). X now refuses pairs whose action texts act on different objects. Over all 3127 questions, tools-array tokens:

| arm | flown at 0bf829c6 | revised | what changed |
| --- | ---: | ---: | --- |
| S − U | −10.21% | −18.72% | hints dropped on 30,762 and suite labels on 25,133 question-tool occurrences; no flown S edit is lost |
| X − U | +0.68% | +0.57% | 36 of 71 distinct cues refused (618 question-tool occurrences); no cue changed or added |
| SX − U | −9.53% | −18.15% | both, composed exactly |

  On the validation draw, S−U goes from −5.46% to −11.97% and SX−U from −4.90% to −11.57%. These are local o200k_base counts. The revised editors have never been sent, so there is no accuracy claim for them.

## 1. The evidence

| item | value | source |
| --- | --- | --- |
| window | 19:22:21–20:41:33 HKT, off-peak band, thinking off | `original/STARTED.json`, `original/RESULTS.md`, journal |
| sends | 2482 sent, 2481 billed; attempt 2482 has no terminal event and may have been charged | `attempts.jsonl`, `bills.jsonl` |
| spend | $0.346230789 in the bill ledger, plus possibly attempt 2482 | `bills.jsonl`, `FINAL-0bf829c6.json` |
| stop | box environment lost; no provider error, no ceiling stop, no retry, no resume | `FINAL-0bf829c6.json` |
| progress | scoring 1214/1252 slots; prerequisites 20/60; 303 cases on all four arms; memory_vector and memory_rec_sum never reached | journal, `score/` |
| stale files | `run.json` says running and `spend.json` is one bill behind; the journal, the ledger and FINAL are the record | `original/live-0bf829c6/` |
| scoring | pinned official evaluator, `underscore_to_dot=True`, run afterwards on the finished result files | `score/` |
| sent bytes | all 2482 sent tool hashes match `sent_renders_0bf829c6.json`, which the flown commit regenerates byte for byte | `package/validation_2026_11_25_analysis.json` `sent_bytes` |

Every number in sections 1 and 2 is rebuilt from that directory by `python -m tool_compression.clean_start report-validation` (`package/validation_2026_11_25_analysis.json`). The flown-editor digests come from `scripts/clean_start_sent_digest.py` run on a worktree of `0bf829c6`, and a test regenerates both when that commit is in local history.

The local o200k_base count on the validation draw (U 254,243 tools tokens) is 115 below the figure in `RESULTS.md`, in every arm. The deltas are identical, so the offset is a tokenizer build difference, not a render difference.

## 2. Paired diagnosis

Severity is what the finding does to a conclusion. Each row separates what the evidence confirms from what it only suggests.

| # | severity | finding | evidence | confirmed / uncertain | action |
| --- | --- | --- | --- | --- | --- |
| 1 | high | Provider noise is as large as every arm difference. | 22 of 880 single-turn pairs with byte-identical tools differ in outcome; 685 of them made identical calls. Trajectory pairs with identical tools: 8, none differ in outcome, too few to set a floor. | confirmed | No accuracy claim. A replicate U is the only way to measure the floor directly. |
| 2 | high (for X) | X's `live_irrelevance` drop is not caused by X. | The four cases where U passed and X failed all sent X bytes identical to U. No single-turn X−U discordance involves a cued tool. | confirmed | X precision was still tightened (finding 7), on catalogue grounds, not to chase this loss. |
| 3 | medium | The SX-only failures are not an SX interaction. | `live_irrelevance_746-257-0` and `live_multiple_965-207-1`: X cued nothing, so SX sent S's bytes and X sent U's. S passed both. | confirmed noise | None. |
| 4 | medium | The float suffix may have changed one argument. | `parallel_multiple_166`: S drops ` This is a float type value.` while the schema keeps `type: number`, `format: float`. U and X sent 0.07; S and SX sent 7. 1 of 70 S-edited parameters differ, the same rate as identical-text controls (`parallel_multiple_75`, X/SX against U/S). | plausible, not separable from noise | Rule kept. The schema still states the type; the risk is listed below. |
| 5 | low | `live_multiple_105-43-3` (S and SX failed) has no mechanism. | S edited two tools; neither arm called either of them. | confirmed no mechanism | None. |
| 6 | low | Trajectory wins for S/SX cannot be attributed. | `multi_turn_long_context_2`, `multi_turn_miss_param_51`, `multi_turn_miss_func_61`, `multi_turn_miss_func_9`, `memory_kv_148-notetaker-18`: the arms take different paths over 15–30 changed tools. On `miss_param_51`, U and X asked the user for permission after a login error, while S and SX logged in and retried. | uncertain | None. |
| 7 | medium (design) | X spends cues on pairs that are not alternatives for one need. | Cues such as `For statistics about messages, use get_message_stats.` on `message_get_login_status`, or `For the time difference, use timezones_get_difference.` on `flights_search`, pair tools whose action texts share a verb but act on different objects. Each rival's own description already says what it does. | confirmed on the catalogue | Object-head rule (section 4). |
| 8 | high (design) | S savings are capped by structure, not by caution. | Section 3. | confirmed on the catalogue | Hint and suite-label rules (section 4). |
| 9 | none | The runner was faithful. | One S trajectory force-quit (`multi_turn_miss_func_9`, 26 steps), as pinned. The stop was the box, not the runner. | confirmed | No runner change, and no resume machinery. |

Tokens reached the provider as rendered. On turn 0 step 0 of the 303 matched cases (identical messages in every arm), the provider billed S −3.78%, X +0.35% and SX −3.49% prompt tokens against U (332,874 tokens). Those are shares of the whole prompt; the tools array is the only part that differs between arms, and locally it was S −5.46%, X +0.56%, SX −4.90% of the tools array over the 313 draw cases.

## 3. Why the savings were modest: where U's tokens sit

`package/token_tables.json` `u_anatomy`, local o200k_base, U arm. Description kinds are summed field by field. "Outside descriptions" is the tools tokens minus those fields: names, parameter names, types, enums, defaults and JSON punctuation. Hints and suite preambles sit inside function descriptions. "Repeated" counts each occurrence after the first tool of the request that carries the same hint or membership. The single-turn, multi-turn and memory rows sum the `by_category` rows of each kind.

| scope | outside descriptions | function descriptions | parameter descriptions | language hints | repeated hints | suite preambles | repeated preambles |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all 3127 questions | 55.3% | 28.5% | 16.2% | 7.1% | 6.5% | 14.5% | 13.6% |
| validation draw (313) | 51.0% | 23.4% | 25.6% | 7.1% | 5.6% | 6.9% | 6.5% |
| pilot draw (41) | 55.8% | 29.5% | 14.7% | 7.2% | 6.6% | 15.5% | 14.5% |
| single-turn categories | 48.5% | 17.0% | 34.4% | 6.4% | 4.7% | 0 | 0 |
| multi-turn categories | 57.7% | 31.1% | 11.2% | 7.1% | 6.8% | 18.9% | 17.8% |
| memory categories | 55.2% | 36.2% | 8.6% | 8.8% | 8.0% | 18.3% | 16.6% |

S must keep everything outside the descriptions, because that is the executable schema. In single-turn catalogues, which are 285 of the 313 validation cases, half of the tokens are outside descriptions. The other half is mostly unique real-API prose: formats, examples, ranges and enum meanings that a model needs to fill arguments. The flown S could remove only schema-guaranteed clauses and subject frames there, about 0.3–2% of tools tokens. The repeated hint alone was 4.7%.

A phrase census of the flown S output found nothing comparable. Over all questions, these are shares of S tools tokens: type frames such as `A string representing` 0.19%, `e.g.` and `such as` clauses 0.20% (they carry formats), leading `Specifies`/`Indicates` 0.06%, `if not specified` clauses 0.05%, optional/required markers 0.01%. Parameter descriptions repeated verbatim across sibling tools are 0.64%. Paraphrasing unique prose further would trade meaning for tokens, which the brief rules out.

## 4. What changed

### S (`s-rules-2026-11-26`)

- **`hint_context` (contract change).** The official language hint (` Note that the provided function is in Python 3 syntax.`, or the Java or JavaScript one) applies to every tool of a request. The first tool that carries it keeps it verbatim. A later tool whose hint is byte-identical drops it, and its ledger fact records the excerpt and `carried_by_tool_index`. A description that would be empty without its hint keeps the hint. Before this revision, S never edited the hint and NOTE.md said so.
- **`suite_label`.** When an earlier tool already states `This tool belongs to the <suite>` verbatim, a later tool of that suite writes `<Suite>: <its own description>`. The suite name is copied verbatim, with its first letter capitalised; only `This tool belongs to (the)` and the closing period become `: `. This is applied together with the existing `suite_context` rule, which already dropped the shared elaboration and the `Tool description:` label.
- **Unchanged.** `suite_context`, `schema_guaranteed` (including the float suffix), `direct_action`, `within_tool_duplicate`, `flag_normalization`, every refusal, and the faithfulness checks. Those checks still forbid dropping a negation, `only`, `whether`, `internal`, a unit, or a literal the schema does not carry, and adding a word stem the source lacks.
- **State.** S still edits one tool at a time in request order. Besides the tool, it sees only which verbatim excerpts (suite elaborations, membership sentences, hints) earlier tools still carry. It never looks ahead, so appending held-out tools never changes a tool already sent. Rows now record `suite_context_state`, `membership_state` and `hint_state`.

### X (`x-rules-2026-11-26`)

- **Shared object.** A pair now also needs the same object: the head noun of each action text's direct object must match, lemmatised. The object starts after the verb and one particle (`for`, `up`, ...). It ends at the first preposition, relative word, adverb or participle after a content word, and the head is its last content word. A light noun followed by `of`, `about` or `regarding` hands the head on: `a list of X`, `the number of X`, `information about X`. A refused pair says `The two action texts act on different objects (<head> versus <head>)`.
- **Effect.** 71 distinct cues before, 35 after; 3,561 cued question-tool occurrences before, 2,943 after. Every remaining cue is unchanged, and no tool gained a cue or changed rival. Tools that now go uncued for this reason are counted as `uncued:different_objects` in the coverage tables.

### SX

SX is still S with each X cue appended verbatim (`S text + " " + cue`), checked fail-closed by `verify_arms`. X still decides on U and never sees S. Every text cue quotes a phrase from its rival's action text; S never edits action text, so every phrase survives in S (`verify_cue_phrases`). One SX-specific consequence: on a later cued tool, U and X put the cue after the hint, and S and SX put it after the action text, because S dropped the hint.

## 5. Before and after

S, a multi-turn request (first tool unchanged; the next tool of the same suite):

| tool | U | S |
| --- | --- | --- |
| `cat` (first) | This tool belongs to the Gorilla file system. It is a simple file system that allows users to perform basic file operations such as navigating directories, creating files and directories, reading and writing to files, etc. Tool description: Display the contents of a file of any extension from currrent directory. Note that the provided function is in Python 3 syntax. | unchanged |
| `cd` (later) | This tool belongs to the Gorilla file system. It is a simple file system that allows users to perform basic file operations such as navigating directories, creating files and directories, reading and writing to files, etc. Tool description: Change the current working directory to the specified folder. Note that the provided function is in Python 3 syntax. | Gorilla file system: Change the current working directory to the specified folder. |

S, a later tool in a single-turn request: `Retrieve the dimensions, such as area and circumference, of a circle if radius is given. Note that the provided function is in Python 3 syntax.` becomes `Retrieve the dimensions, such as area and circumference, of a circle if radius is given.`

X, cues now refused (target action text, rival action text, refused cue):

| target | rival | refused cue |
| --- | --- | --- |
| Get the login status of the current user. | Get statistics about messages for the current user. | For statistics about messages, use get_message_stats. |
| Find flights between two cities. | Find the time difference between two cities. | For the time difference, use timezones_get_difference. |
| Fetch the capital city of a specified country. | Fetch the current population of a specified country. | For the current population, use country_info_population. |
| Create a new directory in the current directory. | Create a new file of any extension in the current directory. | For a new file of any extension, use touch. |
| Calculate the greatest common divisor of two integers. | Calculate the least common multiple of two integers. | For the least common multiple, use lcm. |

X, cues kept (same object, one differing modifier): `Add a key-value pair to the long-term memory.` against `... to the short-term memory.` (`For the short-term memory, use core_memory_add.`); `the return on assets (ROA)` against `the return on equity (ROE)`; `the maximum value` against `the minimum value`; player statistics against team statistics.

`package/EXAMPLES.md` has examples for every category, and `package/revision_vs_0bf829c6.json` lists every removed cue and every new S edit class.

## 6. Tokens and coverage

All 3127 in-scope questions, tools-array tokens against U, flown editors and revised (`package/revision_vs_0bf829c6.json`):

| scope | questions | U | S−U flown | S−U revised | X−U flown | X−U revised | SX−U flown | SX−U revised |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all in scope | 3127 | 5,700,811 | −10.21% | −18.72% | +0.68% | +0.57% | −9.53% | −18.15% |
| multiple | 200 | 68,792 | −2.07% | −8.25% | +0.60% | +0.26% | −1.47% | −7.99% |
| parallel_multiple | 200 | 61,409 | −2.20% | −8.39% | +0.75% | +0.23% | −1.45% | −8.17% |
| live_multiple | 1053 | 855,004 | −0.34% | −4.72% | +0.06% | +0.04% | −0.28% | −4.69% |
| live_parallel | 2 | 542 | 0.00% | −4.43% | 0.00% | 0.00% | 0.00% | −4.43% |
| live_parallel_multiple | 24 | 17,420 | −0.49% | −5.36% | 0.00% | 0.00% | −0.49% | −5.36% |
| live_irrelevance | 372 | 298,077 | −0.49% | −5.26% | +0.09% | +0.06% | −0.40% | −5.20% |
| live_relevance | 11 | 8,290 | −0.31% | −4.37% | 0.00% | 0.00% | −0.31% | −4.37% |
| multi_turn_base | 200 | 940,391 | −13.53% | −22.88% | +0.23% | +0.09% | −13.30% | −22.79% |
| multi_turn_miss_func | 200 | 895,544 | −13.57% | −22.98% | +0.23% | +0.09% | −13.35% | −22.89% |
| multi_turn_miss_param | 200 | 940,391 | −13.53% | −22.88% | +0.23% | +0.09% | −13.30% | −22.79% |
| multi_turn_long_context | 200 | 940,391 | −13.53% | −22.88% | +0.23% | +0.09% | −13.30% | −22.79% |
| memory_kv | 155 | 323,795 | −10.72% | −22.12% | +7.66% | +7.66% | −3.06% | −14.46% |
| memory_vector | 155 | 261,175 | −10.45% | −21.54% | +1.42% | +1.42% | −9.02% | −20.12% |
| memory_rec_sum | 155 | 89,590 | −10.38% | −22.14% | 0.00% | 0.00% | −10.38% | −22.14% |

Both exposed draws and the rest of the population (`package/token_tables.json` `draws`). The flown pilot-draw figures are computed with the 0bf829c6 editors; the validation-draw ones are in `package/validation_2026_11_25_analysis.json`.

| scope | questions | U tools | S−U flown → revised | X−U flown → revised | SX−U flown → revised | descriptions S−U / X−U / SX−U revised |
| --- | ---: | ---: | --- | --- | --- | --- |
| pilot draw | 41 | 87,106 | −10.79% → −19.62% | +0.80% → +0.70% | −9.98% → −18.92% | −44.56% / +1.58% / −42.98% |
| validation draw | 313 | 254,243 | −5.46% → −11.97% | +0.56% → +0.40% | −4.90% → −11.57% | −24.52% / +0.81% / −23.71% |
| outside both draws | 2773 | 5,359,462 | n/a → −19.02% | n/a → +0.58% | n/a → −18.45% | −42.91% / +1.30% / −41.62% |

Coverage, revised editors (`coverage` in each table; per question, so a catalogue counts once per question that uses it):

| scope | S fields edited | S fields kept (already minimal / no faithful shorter / ambiguous) | questions without an S edit | X tools cued | X tools uncued: different action / different object / window too long / name spells it / other | questions without an X cue |
| --- | ---: | --- | ---: | ---: | --- | ---: |
| all 3127 | 37,918 of 95,707 | 54,934 / 2,701 / 154 | 0 | 2,943 of 33,889 | 28,739 / 63 / 1,810 / 202 / 132 | 2534 |
| validation draw | 1,542 of 5,487 | 3,694 / 247 / 4 | 0 | 89 of 1,507 | 1,114 / 19 / 258 / 15 / 12 | 290 |

Every in-scope catalogue has at least two tools, so every question now has at least one S edit, a dropped repeated hint. Before this revision 1,202 questions (172 in the validation draw) had none. X abstains on most tools by design: 28,739 tools have no rival sharing their verb.

## 7. Options considered and not taken

- **Pluralise the hint on its first carrier** (`... the provided functions are ...`). That needs to know later tools exist, which breaks prefix-only state and the held-out stability guarantee.
- **Drop the membership sentence from later tools entirely.** Suite identity would then rest on tool order, and requests mix suites. The label keeps the suite name for about five tokens less than the sentence.
- **Factor parameter descriptions repeated across sibling tools** (0.64%). S would have to read other tools' parameter text, which widens what S sees beyond verbatim request-level excerpts, for a small gain.
- **Phrase-level rewrites** (type frames, `e.g.` clauses, `Specifies`/`Indicates`, optional markers): 0.01–0.2% each and riskier, because several of them carry formats or constraints.
- **X insertion-only windows and multiple windows.** The population has only 10 insertion-only pairs, and most of the cues they would produce are misleading.
- **Drop the float rule.** The one paired difference is as likely to be noise as mechanism (finding 4), and the schema keeps `format: float`. The rule stays, with the risk listed.

## 8. Tests

- Existing suites, unchanged in intent: pinned Gorilla scorer and runner tests, evidence checksums, report regeneration, flown-digest reproduction, editor isolation.
- New: the validation evidence checksums (1498 files), the paired report's regeneration and headline numbers, the four X `live_irrelevance` losses sending U's bytes, and both flown digests regenerated from `0bf829c6`.
- New corpus-wide audits over all 1020 unique in-scope catalogues (`tests/test_clean_start_editor_audit.py`):
  - each hint is kept on its first carrier and dropped only after it;
  - every suite label names a suite an earlier tool states verbatim;
  - no field gains a word stem, loses a negation or qualifier, or loses a literal the schema does not carry;
  - every X cue joins tools with one object head;
  - SX is S plus the cue, byte for byte, and no arm touches the schema;
  - S and render never look ahead;
  - the editors produce the same arms with file access disabled.
- Exposed-draw regression: on every validation-draw catalogue, S keeps every edit it made at 0bf829c6 and X cues a subset of the tools it cued then.
- Synthetic unit tests: hint carriers and states, labels without an elaboration, a description that is only a hint, the object-head refusal (headlights against cruise control, file against folder, GCD against LCM), and sibling cues kept (front against rear lights, ROA against ROE).
- Integrity over all 3127 questions now also checks that every hint and every membership sentence of the U request is still verbatim somewhere in the S request.

## 9. Remaining risks

- **Nothing here is flown.** The revised editors have no accuracy evidence. The flights so far show no editor effect above provider noise, in either direction.
- **The hint contract change is untested on the provider.** A model could read a later tool without the hint as not Python 3. The hint is a request-level statement and stays on the first tool, but whether a model treats it that way is an empirical question.
- **The label is a new text shape.** `Gorilla file system: Change ...` states membership without the `belongs to` sentence; it has not been sent.
- **X loses recall by design.** 36 cue patterns are gone. None was shown to help, and none was shown to hurt.
- **The float suffix** may have flipped one argument (finding 4).
- **Both draws are exposed.** Any future comparison on them is a regression check, not validation. Only the 2773 questions outside both draws have never been flown.
- **`validation/cost.json` is frozen** as the plan the 0bf829c6 flight used. `package/validation_20261126.json` recomputes the same report with the revised editors (first-request floor 1,092,024 tokens instead of 1,130,882; the planning upper barely moves, because trajectory allowances dominate it).
- **Local counts are 115 tokens below `RESULTS.md`** in every arm on the validation draw, a tokenizer build difference that leaves deltas unchanged.
