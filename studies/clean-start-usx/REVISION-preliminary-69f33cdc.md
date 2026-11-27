# Why the 69f33cdc 20% slice shows smaller savings than the 747e72fb 32-case flight, and revision of S and X (2026-11-27)

Base: PR #28 tip `6d4081e3a05f0cb4229f329854a8602791407f71`. The 32-case flight (`747e72fb`), the interrupted 20% run (`69f33cdc`) and `6d4081e3` all carry editors `s-rules-2026-11-26` and `x-rules-2026-11-26`. This branch carries `s-rules-2026-11-27` and `x-rules-2026-11-27`. `official_settlement` stays false. Nothing here sent a provider request, read a key, resumed the stopped run, or touched its ledger or the full-fly workdir. The 20% run's evaluation outputs are on CoS's machine and were not read: the accuracy and billed-token figures below are the ones Jacky supplied (t2641u), and every other number is a local o200k_base count of the tools array.

## Outcome

- **The cause is mostly case mix, not an editor change.** Between `747e72fb`, `69f33cdc` and `6d4081e3`, the sources of `editor_s.py`, `editor_x.py`, `descriptions.py`, `render.py`, `prepare.py`, `adapter.py`, `convert.py` and `count.py` are byte-identical. The tools that `arm_tools` builds hash identically at `747e72fb` and `6d4081e3` for all four arms of the 322 slice cases and the 32 flight cases.
- **The slice has no multi-turn case.** On single-turn catalogues, S saves the repeated language hint and a few schema-guaranteed clauses: −5.09% of tools tokens, −34.7 tokens per case. The provider billed S −34.6 prompt tokens per case against U, so every local token saved reached the bill. Chat template, messages and output dilute it to −3.00% of total tokens.
- **The 32-case flight was dominated by multi-turn.** Its 12 multi-turn cases resend the whole catalogue on every step. In those catalogues, every tool repeats the suite preamble and the hint, and S cuts 20–26% of the tools tokens. U averaged 20,834 prompt tokens per case there, against 1,055 on the slice, which produced −21.0% overall.
- **Category by category, the two sets compress the same.** For example, live_multiple is −4.59% on the slice and −6.38% on the flight's 3 cases; multiple is −8.17% and −7.55%.
- **Accuracy shows no editor effect on the slice.** Against U's 251, S is +2, X +1 and SX +1. Pairwise discordance is 5 to 10 cases of 322. X changes the request on only 7 of the 322 cases, and SX differs from S on the same 7.
- **The SX multi-turn drop is not attributable to X or to the composition.** On the flight, SX scored 0/3 on miss_param and 0/3 on long_context. In 3 of those 6 cases, SX sent exactly S's bytes because X cued nothing. On the 16 multi-turn cases of the 0bf829c6 validation flight (earlier editors), SX scored 10, against U 6, S 8 and X 7. Regardless, the revised X cues no tool in any in-scope multi-turn catalogue, so SX now sends S's bytes on every multi-turn request.
- **The editors were leaving a little on the table, and that is now taken.**
  - S refused schema-proven default clauses that contain `None` or `if not specified`.
  - S did not match empty-string, empty-list or empty-object defaults.
  - S kept whitespace at the end of a field.
  - X cued pairs whose rival name already spells the difference (`max_value`/`min_value`, `wholefoods_...`, `openlibrary_...`).
  - X cued `For a file, use rm.` on `rmdir`, a conjunct cut from rm's `Remove a file or directory`.
- **The gains are small, as the data says they should be.** Over all 3,127 questions, S−U goes from −18.72% to −18.91% and SX−U from −18.15% to −18.40%. On the slice, S−U goes from −5.09% to −5.10%. Single-turn S is close to its faithful ceiling. Larger single-turn savings would need paraphrasing unique prose or editing the schema, and both are ruled out.

## 1. The two sets

| | 32-case flight, `747e72fb` | 20% slice, `69f33cdc` |
| --- | --- | --- |
| cases | 32: the pilot draw minus its 9 memory cases | 322: the four-arm intersection |
| mix | 12 multi-turn (3 per category), 20 single-turn | 0 multi-turn; live_multiple 211, multiple 40, parallel_multiple 40, live_irrelevance 24, live_parallel_multiple 5, live_parallel 2 |
| U prompt tokens | 666,698 (20,834 per case) | 339,733 (1,055 per case) |
| U tools tokens, first request, local | 74,050 (2,314 per case) | 219,518 (682 per case) |
| total tokens vs U (S / X / SX) | −21.0% / +0.5% / −20.9% | −3.00% / −0.03% / −2.92% |
| accuracy U / S / X / SX | 26 / 26 / 27 / 24 | 251 / 253 / 252 / 252 |

## 2. Diagnosis

| # | finding | evidence | status |
| --- | --- | --- | --- |
| 1 | The editors did not change. | Empty `git diff` for the editor, description, render, prepare, adapter, convert and count sources across the three commits. `arm_tools` output hashes are identical at `747e72fb` and `6d4081e3` for 354 cases × 4 arms. The runner's changes (send policy, retry, resume, ledgers) do not touch the tools it sends. | confirmed |
| 2 | The slice is a different mix. | Local tools tokens S−U per category, slice vs flight: multiple −8.17% vs −7.55%; parallel_multiple −8.86% vs −5.91%; live_multiple −4.59% vs −6.38%; live_irrelevance −5.10% vs −4.79%; multi_turn_* not on the slice vs −20.2% to −25.8%. | confirmed |
| 3 | The local saving reached the bill. | S−U is −11,169 local tools tokens (−34.7 per case) and −11,152 billed prompt tokens (−34.6 per case). | confirmed |
| 4 | Dilution explains −3% instead of −5%. | Tools are about 65% of the slice's prompt (219,518 of 339,733). The rest is the chat template and the messages. Output is 9% of total tokens and does not change with the arm. | confirmed |
| 5 | Accuracy differences are within noise. | Discordant pairs (first arm correct only / second arm correct only): U–S 3/5, U–X 2/3, U–SX 4/5, S–X 3/2, S–SX 4/3, X–SX 5/5. The validation flight's identical-tools noise floor was 2.5% (22 of 880 pairs). Here U–S is 8 of 322 (2.5%). | confirmed noise-compatible |
| 6 | The SX multi-turn drop cannot be pinned on X or the composition. | Three of the six SX losses sent S's exact bytes. The other three (`miss_param_31`, `long_context_6`, `long_context_31`) carried a cue that X also sent, and X scored best overall (27). Validation flight multi-turn: SX 10/16 ≥ S 8, X 7, U 6. | uncertain; now moot, because X cues no multi-turn tool |
| 7 | S was over-conservative on default clauses. | `Defaults to None.`, and `Defaults to 'localhost' if not specified.` against a schema default `localhost`, tripped the negation guard. `an empty string` / `an empty list` / `an empty dictionary` never matched `""`, `[]` or `{}`. | confirmed on the catalogue; small |
| 8 | S kept whitespace at the end of fields. | `The name of the second file in current directory. ` and 75 other distinct ledger fields, 10,113 field occurrences across the population. | confirmed; about 1 token each |
| 9 | X spent cues that the rival name already states. | `For the minimum value, use min_value.`, `For Whole Foods store, use wholefoods_vegan_products.`, `For the Open Library, use openlibrary_books_search.`, `For BoardGameGeek store, use BoardGameGeek_recommend.` | confirmed on the catalogue |
| 10 | One X cue misstated its rival. | On `rmdir` (`Remove a directory ...`), `For a file, use rm.` quotes rm's `Remove a file or directory`, whose own text also claims directories. | confirmed on the catalogue |
| 11 | Single-turn S is near its faithful ceiling. | On the slice, descriptions are 51.6% of U tools tokens. S removes 9.9% of the description tokens, mostly the repeated hint. What remains is unique API prose: formats, examples, ranges and enum glosses. The phrase census in `REVISION-0bf829c6.md` §3 still holds. | confirmed |

## 3. What changed

Every rule reads only one tool's text and schema, plus the verbatim request-level excerpts that earlier tools carry (S) or the presented catalogue (X). No rule names a category, a case or a tool.

### S (`s-rules-2026-11-27`)

- **Default clauses.** A clause that states exactly the schema default is still removed only under `schema_guaranteed`. When checking negations, the value and the unset condition (`if not specified/provided/given`) of such a removed clause no longer count. Every other word of the original is still checked, so `Do not add a port.` survives next to a dropped `Defaults to 'localhost' if not specified.`.
- **Empty defaults.** `an empty string`, `an empty list` / `array`, and `an empty dictionary` / `dict` / `object` now match a schema default of `""`, `[]` or `{}`. A mismatch, for example `an empty list` against `""`, is kept.
- **`trailing_space`.** Whitespace that ends the field's own text is dropped, before the protected hint or at the end. Internal spacing is untouched, and a field that would become empty is untouched. The ledger records a `WHITESPACE` fact. A field whose only change is this is counted as edited but cosmetic.
- **Unchanged.** Hint and suite rules, `suite_context`, `direct_action`, `within_tool_duplicate`, `flag_normalization`, every other refusal, request-order state and append stability.

### X (`x-rules-2026-11-27`)

- **The name spells the difference.** A text cue is dropped, and the next rival tried, when the rival's name already states its differing window. The window counts as stated in three cases:
  - every content word is one of the name's parts;
  - a part of at least three letters is each word's leading abbreviation (`min` for `minimum`);
  - words of the cue phrase that include the whole window, written together, are a run of whole parts (`Whole Foods` in `wholefoods_vegan_products`, `the Open Library` in `openlibrary_books_search`, `BoardGameGeek` in `BoardGameGeek_recommend`).

  A run never ends inside a part, so `log` is not spelled by `login_entries`. Two-letter parts never abbreviate, so `go` does not spell `golden`.
- **The rival's coordinator.** A pair is refused when the rival's differing words end in `or`/`and` joined to the shared wording. The existing target-side refusal is mirrored here: the rival's text then also claims the target's object, and its phrase would be one conjunct.
- **Effect.** Distinct cue pairs fall from 35 to 27. Cued question-tool occurrences fall from 2,943 to 2,537. No remaining cue changed and no tool gained a cue. The only cues on multi-turn catalogues were rmdir→rm and max↔min, so no in-scope multi-turn catalogue, initial or after any held-out batch, carries a cue. Cues remain on memory_kv, memory_vector and a few single-turn catalogues.

### SX

Unchanged: `S text + " " + cue`, verified fail-closed by `verify_arms` and `verify_cue_phrases`. On multi-turn, SX is now byte-identical to S, and X to U.

## 4. Before and after

| field | before | after |
| --- | --- | --- |
| `host` | `The host. Defaults to 'localhost' if not specified. Do not add a port.` | `The host. Do not add a port.` |
| `file_name` (`echo`) | `The name of the file at current directory to write the content to. Defaults to None. ` | `The name of the file at current directory to write the content to.` |
| `enable` (time tracking) | `Flag to enable or disable the selected time tracking provider. Defaults to true if not specified.` | `Flag to enable or disable the selected time tracking provider.` |
| `amount` (`place_order`) | `Number of shares to trade. ` | `Number of shares to trade.` |

The `host` row is the unit-test example. The others are population fields from `package/s_ledger.jsonl`.

X cues removed: `max_value` ↔ `min_value` (both directions), `rmdir` → `rm`, `google_books_search` and `library_search_books` → `openlibrary_books_search`, `safeway_vegan_products` and `walmart_vegan_products` → `wholefoods_vegan_products`, and `AmazonGameStore_recommend` → `BoardGameGeek_recommend`.

## 5. Tokens

Tools-array tokens against U, local o200k_base, before → after:

| set | U | S−U | X−U | SX−U |
| --- | ---: | --- | --- | --- |
| all 3,127 in scope | 5,700,811 | −18.72% → −18.91% | +0.57% → +0.51% | −18.15% → −18.40% |
| multi_turn_base / miss_param / long_context | 940,391 each | −22.88% → −23.09% | +0.09% → 0.00% | −22.79% → −23.09% |
| multi_turn_miss_func | 895,544 | −22.98% → −23.19% | +0.09% → 0.00% | −22.89% → −23.19% |
| memory_kv | 323,795 | −22.12% → −22.59% | +7.66% → +7.66% | −14.46% → −14.94% |
| live_multiple | 855,004 | −4.72% → −4.74% | +0.04% → +0.04% | −4.69% → −4.70% |
| 20% slice (322) | 219,518 | −5.09% → −5.10% | +0.08% → +0.08% | −5.01% → −5.02% |
| 32-case flight set | 74,050 | −19.22% → −19.38% | +0.08% → 0.00% | −19.14% → −19.38% |
| validation draw (313) | 254,243 | −11.97% → −12.08% | +0.40% → +0.35% | −11.57% → −11.73% |

On the slice, the revision changes S on 5 of 322 cases and X on none. On the 32-case flight set, it changes S on 10 cases and removes the X cue from 3. `package/token_tables.json` and `package/revision_vs_0bf829c6.json` have every category.

The frozen plans stay as flown or preflighted:
- `preliminary/cost.json` is the 69f33cdc plan. `package/preliminary_20261128.json` recomputes it with the revised editors: the first-request floor falls from 4,907,006 to 4,899,890 tokens and the planning upper from $95.376500 to $95.376489.
- `full/cost.json` is the plan preflighted at `6d4081e3`. Recomputed with the revised editors, the ceiling floor ($68.54), the observed-mean path ($58.692511) and the higher-step path are unchanged. The planning upper moves from $254.432685 to $254.432611, and the first-request floor from 22,002,459 to 21,972,222 tokens. Those figures, the tools-render digest, and `source_sha256` are in `package/full_20261127.json`. The CLI still reads `full/cost.json`.

## 6. Options not taken

- **Response-schema descriptions.** They are a large share of multi-turn tokens but are not description slots. Editing them changes the contract, so that is Jacky's call.
- **Collapsing internal double spaces.** Rare, and spacing inside a field can be formatting.
- **Optional and required markers, leading articles, and telegraphic rewrites.** Each is 0.01–0.2% of tokens, and they paraphrase or drop meaning.
- **Factoring parameter text repeated across sibling tools.** That would widen what S sees beyond verbatim request-level excerpts.
- **Targeting multi-turn or SX directly.** No rule reads a category. The multi-turn cue removal follows from the two general X rules.

## 7. Tests

- Unit tests in `tests/test_clean_start_revision.py`:
  - name spelling by part, abbreviation, compound, camel case and phrase run; opaque names, two-letter parts and a word inside a longer part (`log` in `login`) are still cued;
  - default clauses with `None` and `if not specified`, with a negation outside the clause kept;
  - empty defaults and their mismatches;
  - trailing whitespace on the first and later hint carriers, internal spaces kept, flags and facts;
  - the rival-side coordinator refusal.
- Corpus audits in `tests/test_clean_start_editor_audit.py`:
  - the kept-words audit excuses a word only when an independent parse finds every occurrence inside a dropped sentence that states the schema default;
  - a new audit renders every in-scope multi-turn question's initial catalogue and every held-out stage, and checks that no tool is cued, X equals U and SX equals S.
- `preliminary_20261128.json` regenerates byte for byte. The frozen 20% plan may differ from it only in first-request-token fields.
- The opt-in `TC_FULL_PLANNING=1` test allows drift only in those fields and keeps every gate exact.

## 8. Risks

- **Nothing here is flown.** The revised editors have no accuracy evidence. They are ready for a box preflight only, not for a live start.
- **Default clauses leave the prose.** The schema still carries `default`. This is the same contract as every earlier `schema_guaranteed` drop, now applied to `None` and to empty literals.
- **X no longer cues anything on multi-turn.** X equals U and SX equals S there by construction. Multi-turn X−U and SX−S pairs become identical-tools noise controls, not tests of X.
- **The 20% slice is now exposed.** It was read to diagnose these editors. Like the pilot and validation draws, it is a regression set for them, not unseen validation.
- **Resume.** Code on this branch refuses to resume a run started at `69f33cdc` or `6d4081e3`, because the run identity records the editor rules and source digests. That is intended: one run never mixes editors.
