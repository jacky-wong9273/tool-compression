# Methodology

## Sample and pin

| Item | Value |
| --- | --- |
| Sample | `multiple` 200, `simple_python` 400, `irrelevance` 240 |
| Gorilla / BFCL commit | `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8` |
| `BFCL_v4_multiple.json` | `aef168155ebd74b7ac2401198b201343bc7d16d7a3d7e0d4e6d8ee82c6969b2a` |
| `BFCL_v4_simple_python.json` | `82dd63ba502eb2520c6b5d1d9a5c4b590e03ff261565175561f6228a367d1991` |
| `BFCL_v4_irrelevance.json` | `2b6ed4c2e992cdcf5f1678a701851f944bef7550ee026ed1ddb89efed5be01a6` |

The hashes are SHA-256 of the category file bytes. `possible_answer` hashes may differ and are not pinned. Questions are loaded only when a gate or a later flight rebuilds the request. They are not stored in U, in the edit records, or in the gate.

U is `to_openai_completions_tools` applied to each pinned record. `catalogues/U/<case_id>.json` is that conversion plus a note that the file holds no question, gold call, or stored response. `checks/u-sha256.json` locks those bytes. A gate rebuilds the conversion from the pin and refuses to continue if any tool list differs.

All 400 `simple_python` catalogues and all 240 `irrelevance` catalogues have one tool. All 200 `multiple` catalogues have two, three, or four tools (79, 85, and 36).

## Four arms

| Arm | Catalogue |
| --- | --- |
| U | The unaltered converted catalogue. |
| S | Own-tool semantic edits of U. No cross-tool cue. Sibling tools are hidden while that tool's S text is written. |
| X | Every character of U, plus, where a rival, an axis, and a location are justified, one space and one short selection cue on the target's function description. No parameter edit. |
| SX | The exact S base plus the exact X cue, with the same separator and the same `/function/description` path. |

S and X are specified from U in separate maps (`CHANGES` and `CUES` in `official_840_tranche.py`). SX is rendered only after both exist. The renderer is the cue-revision `render_conditions`: it applies the frozen S replacements, then appends the cue. The cue is not shortened for SX, and SX is not a freehand combination of the two edits.

An X cue names at most one rival. The cue rules are the revised-cue rules in `docs/semantic-audit-pilot/cue-revision/methodology.md`: same stated action on the same resource where one exists, earlier catalogue order on a tie, one tool's silence is not an exclusion, and the review question is whether both descriptions could be true of the same request and whether the cue still helps the reader choose. Coverage is not cue efficiency. Shorter wording is not the success criterion.

When no rival, axis, and location are justified, the cue is empty. X is then U and SX is then S. That includes a one-tool catalogue. Those cases are counted. An empty cue is a judgement about the sealed case. It is not applied in advance to the 139 unsealed one-tool cases.

X may add tokens. The flight records that cost. It does not rewrite a cue to remove it.

L, E, T1, and T2 are history. They are not arms of this four-way. P, I, and C are not arms either.

## How the sealed tranche was read

Eighteen cases were read. They are disjoint from the formative twelve (`multiple_0`, `multiple_7`, `multiple_11`, `multiple_12`, `multiple_35`, `multiple_92`, `multiple_100`, `multiple_153`, `simple_python_34`, `simple_python_175`, `irrelevance_50`, `irrelevance_59`). Fresh U tools for those twelve match the pilot's rendered U tools, because the conversion is the same function. Their S and X texts are not imported, and their official-840 files are not byte copies of the pilot files.

S was written one tool at a time from that tool's converted name, schema, and description strings. Sibling tools were read in a later index round. No S replacement contains `Unlike ` or a sibling name. The editor then reread the changed before/after strings with the decision notes set aside. That reread changed nothing (`revisions_before_seal` is empty). It is self-review. `independent_review` is false. `questions_used` is false.

X was written from the original converted descriptions after the S map existed. S replacement text was not an input to the cue wording. The same review question was applied to every non-empty cue. Conflicts between prose and schema were left as written. [reading.md](reading.md) is the case record. `edits/s-record.json` and `edits/x-record.json` are the machine ledger.

A second tranche added 131 cases after the same reading: 115 one-tool catalogues and 16 two-tool catalogues. A third tranche added 142 more: 130 one-tool catalogues (`simple_python_62` through `simple_python_141`, and `irrelevance_62` through `irrelevance_111`) and 12 two-tool catalogues. A fourth tranche added 142 more: 130 one-tool catalogues (`simple_python_142` through `simple_python_174`, `simple_python_176` through `simple_python_222`, and `irrelevance_112` through `irrelevance_161`) and 12 two-tool catalogues. A fifth tranche added 132 more: 120 one-tool catalogues (`simple_python_223` through `simple_python_302`, and `irrelevance_162` through `irrelevance_201`) and 12 two-tool catalogues. None of those twelve receive a cue, because the two tools do not answer a similar request. `simple_python_175` stays with the formative twelve. [remaining-work.json](remaining-work.json) lists the other 275 cases. A later editor continues from U with the same rules. The verifier does not permanently ban the formative twelve.

## Thinking passes

Thinking on is a generation-time option. It is not a catalogue change.

| Pass | `thinking` field | Order |
| --- | --- | --- |
| off | `{"type": "disabled"}` | First. |
| on | `{"type": "enabled"}` | Second, over the same messages and the same tools. |

The field is sent. Omitting it would leave DeepSeek's default, which is thinking on. Neither body sets `reasoning_effort`.

The thinking-off body for a catalogue is the 12-case systems-test `generation_body`. That systems test still refuses a body whose thinking field is enabled. The 840-case client is a separate module so the systems-test assertion stays closed. Stage A does not import the live client.

A thinking-off response that contains reasoning stops the run. The thinking-on pass does not start. A thinking-on response may contain reasoning.

## One observation per identical payload

A cell is one case id and one thinking pass. Arms inside that cell share a call when the full body matches: model, messages, temperature, store, thinking, and tools. The arm names are recorded on that observation.

A matching body in another case is a different call. A matching catalogue on the other thinking pass is a different call, because the thinking field differs and the request hash differs.

When an audit shows two arms are identical, the plan records the identity. The package does not insert a token, a cue, or a paraphrase to force the bodies apart.

If the 565 sealed cells were sent, the plan has 1268 payloads: 634 on thinking off and 634 on thinking on. The first 18 cells are still the 70 payloads inside that total. The second tranche is still 152 per pass. The third tranche is still 151 per pass. The fourth tranche is still 157 per pass.

| Sealed cases | Why the bodies match inside one pass | Calls per pass |
| --- | --- | --- |
| `multiple_9`, `multiple_21`, `multiple_73` | U, S, X, and SX are four catalogues | 4 each |
| `multiple_2`, `multiple_4`, `multiple_27`, `multiple_33`, `multiple_45`, `multiple_57` | S matches U, and the cue makes X and SX a second body | 2 each |
| `multiple_24`, `multiple_99` | No cue, so X matches U and SX matches S. S itself differs from U | 2 each |
| `multiple_28` and the six one-tool cases | No cue, and S matches U, so all four arms are one body | 1 each |

The second tranche adds 152 calls per pass. `multiple_10` is four catalogues. The other 12 new cues sit on an unchanged S, so each is two calls. `multiple_39`, `multiple_42`, and `multiple_52` are one call. 109 unchanged one-tool catalogues are one call, and the six edited one-tool catalogues are two calls.

The third tranche adds 151 calls per pass. Seven new cues sit on an unchanged S, so each is two calls. `multiple_55`, `multiple_59`, `multiple_74`, `multiple_78`, and `multiple_79` are one call. 128 unchanged one-tool catalogues are one call, and the two edited one-tool catalogues (`irrelevance_62` and `irrelevance_64`) are two calls.

The fourth tranche adds 157 calls per pass. Nine new cues sit on an unchanged S, so each is two calls. `multiple_93` and `multiple_95` are one call. `multiple_97` has an S edit and no cue, so it is two calls. 125 unchanged one-tool catalogues are one call, and the five edited one-tool catalogues are two calls.

The fifth tranche adds 139 calls per pass. None of the twelve new two-tool catalogues is cued. Eleven of them match U on every arm, so each is one call. `multiple_142` has an S edit and no cue, so it is two calls. 114 unchanged one-tool catalogues are one call, and the six edited one-tool catalogues are two calls.

Unsealed cases are listed in the gate as blocked. They have no generation body.

## Generation settings, recorded for a later flight

| Setting | Value |
| --- | --- |
| Generation model | `deepseek-flash` |
| Model version | `DeepSeek-V4.1-Flash-1017` |
| Temperature | `0.001` |
| `store` | false |
| Endpoint | `POST https://api.deepseek.com/chat/completions` |
| Scoring alias | `DeepSeek-V3.2-Exp-FC` |

The scoring alias is the evaluate `--model` and the result-directory name. It selects the pinned function-call handler. It is not sent as the generation model. The body refuses that alias and refuses `deepseek-chat`.

## Off-peak stop

These 840-case flights are off-peak only. The public weekday windows, Asia/Shanghai, are 09:00–12:00 and 14:00–18:00, half-open, at minute resolution. A Saturday or Sunday is off-peak. There is no holiday calendar. A weekday holiday that falls inside a window still stops the flight, because the schedule function treats that minute as peak and this flight treats peak as a stop.

The stop is the same window the locked validation flight and the exploratory flight already use. This package does not import those modules and does not edit them. It does not set `locked_offpeak_validation_card`. `peak_card_used` stays false. There is no `--authorize-peak` argument on `usx-840`.

Before each call the runner reserves the worst case of one call on the off-peak card: one million input tokens at the miss rate plus 384×1024 output tokens, which is ¥2.572864. The reserve is one call, not 840 calls. The peak equivalent, ¥5.145728, is written on the gate as unused. The ceiling is `EXPLORATORY_CEILING_CNY` as supplied to the process. There is no default and no hardcoded ceiling in this module. A ceiling below the reserve stops before a client is built.

Rates, verified on 2026-11-23 from the public Flash card, CNY per million tokens:

| | Cache hit | Cache miss | Output |
| --- | ---: | ---: | ---: |
| Off-peak, the card this flight bills | 0.02 | 1 | 4 |
| Peak, recorded and not billed | 0.04 | 2 | 8 |

T is provider `prompt_tokens`. Cache hits stay inside T. Prices are not applied to T. A missing or inconsistent cache split is billed entirely at the miss rate. That fallback is a billing choice. It does not change T.

## What the verifier locks

`verify_package` needs no BFCL checkout. It checks the frozen-file hashes, the protocol target `1/10`, the category counts and hashes, the stored U hashes, the S and X records against `build_records`, the rendered catalogues, composition, structure, sibling names, the fact ledger, the cue rules, the identity equations, `counts.json`, and `remaining-work.json`.

`checks/frozen-integrity.json` hashes the listed source modules, the 12-case tests, and every file under `docs/semantic-audit-pilot/`. It does not hash `docs/official-840/` or `__main__.py`. The new `usx-840` subcommand is the only edit to `__main__.py`. The `usx-flight` command, including `--authorize-peak`, is unchanged.
