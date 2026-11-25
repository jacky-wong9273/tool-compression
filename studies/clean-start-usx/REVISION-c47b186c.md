# Diagnosis of the c47b186c flight and revision of S, X, SX (2026-11-25)

Base: the flown PR #28 tip `c47b186c6004e69840db3537ebe532dc22f638a8`. The flight's evidence is archived unmodified in `evidence/pilot-2026-11-25-revised-c47b186c/` (archive SHA-256 `b1445e426c7dd97daa811c222955aeb74e749df11db84bd087cfd41e9cbda2b9`, 397 files, `SHA256SUMS`). `official_settlement` stays false. Nothing in this revision sent a provider request, read a key, retried, resumed, or re-ran the pilot.

Editors stay blind to questions, gold answers, model outputs and scores. Every rule change below was found by reading the 3127-question catalogue population and the flown renders, not by tuning to pilot outcomes. No rule names a case id or a pilot tool. The exposed pilot cases appear in diagnostic and regression tests only. They are not fresh or unseen validation.

## Outcome

- **The flight cannot tell whether any editor helps or hurts accuracy.** All four arms finished 32 cases: U 27, S 26, X 28, SX 25 correct. Only 3 cases differ between arms, all multi-turn. Arms that sent byte-identical tools made the same calls in only 4 of 16 trajectory pairs, and one of those pairs flipped outcome (`multi_turn_miss_param_78`, S passes and SX fails with identical tools). The observed arm differences are the size of this noise.
- **The token saving reached the provider; the dollar saving did not, for reasons outside the editors.** On the first request of each matched case (identical messages in every arm), the provider billed S −11.81%, X +0.26% and SX −11.55% prompt tokens against U. Local o200k_base tools-array counts on the same 32 requests agree to within 10 tokens. USD is dominated by output and by cache misses on conversation text, and the tools sit in a cached prefix priced at 1/50 of a miss.
- **The runner sent exactly what c47b186c renders and followed the pinned loop.** All 900 sent tool arrays match the flown renders byte for byte, and the forced quit, memory flush and partial stop all behave as in pinned BFCL. The IncompleteRead was a transport failure; no runner change was needed.
- **The catalogue audit found six editor defects, now fixed.** S deleted suite facts from whole requests, deleted enum sentences that glossed their values, and dropped a closing period. X gave a cue that contradicted its target's own text and truncated three cue phrases. X and SX also changed tools that had already been sent once held-out tools arrived (8 of 200 `miss_func` questions; no flown case). Two fail-closed checks were added for this and for SX coherence.
- **Revised editors (`s-rules-2026-11-25.2`, `x-rules-2026-11-25.3`)**, over 3127 questions, tools-array tokens:

| arm | flown editors | revised | change |
| --- | ---: | ---: | --- |
| S − U | −10.84% | −10.21% | 1805 suite elaborations, 14 enum glosses and 7 flag periods are kept |
| X − U | +0.72% | +0.68% | 1 cue removed (198 questions), 3 cues reworded |
| SX − U | −10.13% | −9.53% | both changes above |

  These are local counts. The revised editors have never been sent, so there is no accuracy claim for them.

## 1. The evidence

| item | value | source |
| --- | --- | --- |
| window | 16:46:03–17:22:14 HKT, peak band, thinking off | `original/STARTED.json`, `RESULTS.md` |
| sends | 900 sent, 899 billed, attempt 900 uncertain (`provider_error:IncompleteRead`) | `live-c47b186c/run.json`, `attempts.jsonl` |
| spend | $0.287883432 recorded, plus possibly attempt 900 | `spend.json` |
| progress | scoring 128/164 (32 case ids in all four arms), prerequisites 12/216, memory never scored | `run.json`, `score/` |
| scoring | pinned official evaluator, `underscore_to_dot=True` | `score/`, `evaluate_summary.json` |
| sent bytes | 900/900 sent tool hashes match `sent_renders_c47b186c.json` (785 initial, 115 after a held-out batch) | `package/pilot_2026_11_25_revised_analysis.json` `sent_bytes` |

Every number in sections 2 and 5 is rebuilt from that directory by `python -m tool_compression.clean_start report-pilot --revised` (`package/pilot_2026_11_25_revised_analysis.json`), or by `scripts/clean_start_sent_digest.py` for the flown-editor digests.

## 2. Diagnosis, ranked by severity

Severity is what the finding does to a conclusion. Each row separates what the evidence confirms from what it only suggests.

| # | severity | finding | evidence | confirmed / uncertain | action |
| --- | --- | --- | --- | --- | --- |
| D1 | Critical | The flight is too small and too noisy to compare arms. Paired discordance on 32 cases: S−U 1, X−U 1, SX−S 1, SX−X 3, SX−U 2. When two arms sent byte-identical tools, trajectories made identical calls in only 4 of 16 pairs and changed outcome once. Single-turn outputs were identical in 62 of 72 such pairs, with no outcome change. | `accuracy.paired_discordance`, `identical_tools_noise`, `discordant_cases[].identical_sent_tools` | Confirmed: differences of one or three cases are inside run-to-run variation. Uncertain: the true effect of any arm. | No rule is changed because of an accuracy number. Validation design in section 7. |
| D2 | High | The failures are not the kind X targets. Every failure is a multi-turn state or execution mismatch, plus one wrong-count (`live_parallel_multiple_8-7-0`, all arms). None of the traced trajectories confuses a cued target with its rival. On `long_context_6`, S wrote the report with `\n` separators where U and X used spaces, and SX skipped the `pwd`, `ls` and `cd` calls the other arms made. On `long_context_31`, X ran `cat` before `grep` and passed where U failed at turn 0. | official `score/` error types; `model_outputs/*/{U,S,X,SX}/multi_turn_long_context_{6,31}.json` | Confirmed: X's one extra pass is not evidence that the cue worked. Uncertain: whether losing the file-system suite text (D4) moved S and SX on `long_context_6`. It is one case and S still navigated. | None from this row alone. |
| D3 | High | The USD and cache columns measure send order and path length, not tool text. S billed 8.6% fewer prompt tokens than U on matched cases but cost 7.3% more ($0.03826 vs $0.03565): 155 vs 150 requests, +987 output tokens, +6018 cache-miss tokens. U's USD splits into output 50%, cache miss 40%, cache hit 10%. First-request cache misses by send position: 28803, 29225, 13134, 11882 tokens, because arms with identical tools (U/X, S/SX) share the provider prefix cache. If every S first-request saving had been a miss, it would be worth $0.0025 over 32 cases; as hits it is $0.00005. | `tokens.matched_billed_by_arm` (with `usd_parts`), `first_request`, `first_request_cache_by_send_position` | Confirmed mechanism: tool shortening saves prompt tokens, and realised USD under prefix caching is set by output and conversation misses. | Endpoints redefined for the next run (section 7). No editor change. |
| D4 | High | Flown S deleted each suite elaboration from every tool, so the facts it carried left the request entirely. Examples: "a simple file system that allows users to perform basic file operations such as navigating directories, creating files and directories, reading and writing to files", "a key-value based memory system", and "posting tweets, retweeting, commenting, and following users". Unlike every other S rule, this deletion was not backed by the schema or by a copy elsewhere in the request. The earlier review flagged it as the main semantic risk (REVIEW.md M4). | `population_c47b186c.json` `s_edit_occurrences_by_class.suite_context = 26938`; flown renders | Confirmed against S's own faithfulness contract. Not shown to cost accuracy. | Fixed: the first tool in a request that carries a given elaboration keeps it (C1). |
| D5 | Medium | Flown S deleted enum sentences that gloss their values, for example "Possible values are 'Music' for concerts and 'Theater' for plays." The enum keeps the values but not what they mean. | `revision_vs_c47b186c.json` `s_distinct_edits.no_longer_made` (schema_guaranteed: 3 fields, 14 occurrences) | Confirmed by text. | Fixed: an enum sentence is dropped only when nothing but the header, the quoted values, `and`/`or` and punctuation remains. |
| D6 | Medium | Flown X cued `rm` ("Remove a file or directory.") with "For a directory at current directory, use rmdir.", steering a use that `rm` documents to its rival. Affects 39 catalogues and 198 multi-turn questions. | `revision_vs_c47b186c.json` `cues.removed` | Confirmed by text. | Fixed: a pair is refused when the target's differing words end in `or`/`and` joined to the shared wording. The reverse cue on `rmdir` ("For a file, use rm.") stays. |
| D7 | Medium | Flown X and SX qualified cues on the whole catalogue, held-out tools included, so a tool already sent could gain a cue on a later turn. In `multi_turn_miss_func_6`, `mkdir` gains "For a new file of any extension, use touch." when `touch` arrives at turn 1. U never changes a sent tool. A mid-conversation change shows the model a different description of a tool it is already using and breaks the cached prefix. | 8 of 200 `miss_func` questions at c47b186c. The 3 flown `miss_func` cases were not affected. | Confirmed in the population, absent from the flight. | Fixed: cues are qualified on the catalogue already presented (C2). A fail-closed check refuses any render that changes a sent tool. |
| D8 | Low | Three flown cue phrases lost their head noun: "For equity (ROE), use …", "For assets (ROA), use …", "For major historical events, use …". | `cues.reworded` | Confirmed by text. | Fixed: after `of`/`on` with no determiner, the phrase keeps the preceding head noun and determiner ("the return on equity (ROE)", "a list of major historical events"). |
| D9 | Low | Flown S flag normalisation dropped the closing period ("Whether to calculate the area"). | 7 occurrences | Confirmed. | Fixed. |
| D10 | Low | SX coherence was not checked. A cue quotes the rival's phrase from U; if S removed that phrase from the rival, SX would quote text the request no longer contains. No instance at c47b186c or now. | `integrity.json` `text_cue_phrase_in_rival_u_and_s` | Guard only. | Fail-closed check added. |

### Runner against pinned BFCL (no defect found)

- **Forced quit.** `memory_kv_prereq_2-customer-2` U took 21 steps in turn 8. The runner force-quit, skipped the remaining turns and flushed memory. This matches pinned `base_handler.py` (`count > 20` sets `force_quit` and breaks out of every turn, lines 324–367; the memory flush runs after the turn loop, lines 371–376). The arm's final snapshot equals its last completed prerequisite checkpoint.
- **Partial stop.** `memory_kv_prereq_3-customer-3` SX stopped after 6 billed steps on attempt 900. Its sidecar says `stopped`, no result line was written, and the SX final snapshot equals the `prereq_2` checkpoint, so partial state was not saved as completed. The run did not retry or resume, and `uncertain_attempts` is `[900]`.
- **Memory scoring was blocked by prerequisites, not by an editor.** The 36 unfinished scoring slots are the 9 memory cases × 4 arms, which wait for all matched prerequisites.
- **Held-out turns.** Held-out documents are sent without the language hint, as pinned `utils.py` prepares them, and appended after the initial tools.

## 3. Contract changes and why

The arm meanings stay the same. S is a shortening that keeps the request's information, X is U plus at most one cue per tool naming one rival in the request, and SX is S plus X's exact cue bytes. Two inputs change.

- **C1. S sees which verbatim suite elaborations are already in the request.** Before, S saw one tool and nothing else, so it could only delete a shared elaboration everywhere or nowhere. Now `edit_catalogue` edits tools in request order. Each tool gets only the set of exact elaboration strings that earlier tools still carry. S never reads a sibling's name, description or schema. The first carrier keeps the elaboration, and later tools drop it as a duplicate within the request. Which tool keeps it depends on catalogue order, which is deterministic and is BFCL's own order. Each ledger fact records `carried_by_tool_index`, each row records `suite_context_state`, and `integrity.json` checks `dropped_suite_elaboration_still_in_s_request` on all 3127 questions. This follows Xu et al. A.1 (deleting non-key text hurt API-Bank accuracy, 71.47 → 53.21) and Sparck Jones (frequent terms "are required for good overall performance"). Repetition can be removed; the information cannot.
- **C2. X decides cues on the catalogue the model has already been shown.** `render_tools(tools, presented)` takes the catalogue lengths already sent. A tool keeps the decision it had when it was first sent, and only appended tools are new: `touch` arriving at turn 1 is cued "For a new directory, use mkdir.", and `mkdir` keeps its sent bytes. U already behaves this way. Every arm now does, and `render_tools` fails closed otherwise (`held_out_tools_keep_sent_bytes`).
- **SX composition is unchanged**: exact S bytes, one space, exact X cue bytes at `/function/description`. The new check `text_cue_phrase_in_rival_u_and_s` makes its coherence auditable.

## 4. Before and after

| rule | where | flown (c47b186c) | revised |
| --- | --- | --- | --- |
| S suite context | first Gorilla file system tool (`cat`) in each request | `This tool belongs to the Gorilla file system. Display the contents of a file …` | unchanged from U: `This tool belongs to the Gorilla file system. It is a simple file system that allows users to perform basic file operations such as navigating directories, creating files and directories, reading and writing to files, etc. Tool description: Display the contents …` |
| S suite context | later file-system tools (`cd`) | `This tool belongs to the Gorilla file system. Change the current working directory …` | same (the elaboration is carried by `cat`) |
| S enum gloss | `Events_3_FindEvents.event_type` | `The type of cultural event to find.` | `The type of cultural event to find. Possible values are 'Music' for concerts and 'Theater' for plays.` (U) |
| S flag | `triangle_properties_get.get_area` | `Whether to calculate the area` | `Whether to calculate the area.` |
| X scope | `rm` ("Remove a file or directory.") | `… For a directory at current directory, use rmdir.` | no cue on `rm`; `rmdir` keeps `For a file, use rm.` |
| X phrase | `financial_ratios_calculate_ROA` | `For equity (ROE), use financial_ratios_calculate_ROE.` | `For the return on equity (ROE), use financial_ratios_calculate_ROE.` |
| X staging | `multi_turn_miss_func_6`, turn 1 | `mkdir` re-sent with `For a new file of any extension, use touch.` | `mkdir` bytes unchanged; held-out `touch` gets `For a new directory, use mkdir.` |

More examples: `package/revision_vs_c47b186c.json` (each S edit no longer made, each cue removed or reworded, with question and catalogue counts) and `package/EXAMPLES.md`.

## 5. Token and coverage trade-offs

Local o200k_base counts of the whole tools array. Over the 32 matched first requests, local deltas agree with provider-billed deltas within 10 tokens (S −8473 local vs −8483 billed, X +179 vs +187, SX −8294 vs −8296). That is the calibration behind using local counts here.

| scope | arm | flown | revised |
| --- | --- | ---: | ---: |
| 3127 questions, tools array | S−U / X−U / SX−U | −10.84% / +0.72% / −10.13% | −10.21% / +0.68% / −9.53% |
| 41 pilot cases, tools array | S−U / X−U / SX−U | −11.47% / +0.84% / −10.63% | −10.79% / +0.80% / −9.98% |
| 41 pilot cases, description fields | S−U / X−U / SX−U | −26.00% / +1.90% / −24.10% | −24.44% / +1.81% / −22.63% |
| questions changed | S / X / SX | 1939 / 762 / 1999 | 1925 / 762 / 1985 |
| S occurrences | suite_context / schema_guaranteed | 26938 / 7047 | 25133 / 7033 |
| X cues | distinct / cued-question occurrences | 72 / 3759 | 71 / 3561 |

By category, S−U tools moves from about −14.3% to −13.5% on the multi-turn sets, and from −11.4%–−13.0% to −10.4%–−10.7% on the memory sets. Multi-turn X−U drops from +2700 to +2150 cue tokens per set of 200 (`miss_func` +2550 to +2022), because the `rm` cue is gone. Single-turn sets barely move. `package/token_tables.json` has every cell, and `REVIEW.md` section 4 has the table.

## 6. Unresolved risks

- **No empirical result for the revised editors.** Nothing here says S, X or SX keeps accuracy or saves money.
- **Weak X pairings remain.** X pairs tools on lexical evidence (same verb, one short differing window, shared content words). Some pairs that pass do not serve one user need: `message_get_login_status` → "For statistics about messages, use get_message_stats." (160 questions), and `flights_search` → "For the time difference, use timezones_get_difference." (2 questions). A tighter rule needs a principled test of "one user need" that is not fitted to these names. It is left open rather than special-cased.
- **Cue placement.** X appends the cue after the official language hint on initial tools, and directly after the description on held-out tools, which BFCL sends without the hint. Placement effects are untested.
- **Facts the catalogue does not hold.** Pinned backends have limits that the descriptions do not state. For example, `memory_kv.py` caps core memory at 7 entries of at most 300 characters, and `core_memory_add` says neither. Editors cannot add facts, so neither S nor X can help where the failure is a missing fact.
- **Which tool keeps a suite elaboration depends on order.** The first carrier is deterministic, but whether the elaboration helps more on one tool than another is unmeasured.
- **Exposed cases.** The 41 pilot cases (and the 6 earlier web ids) have been seen by two flights. Tests built on them are regression tests, not validation.
- **Memory remains unmeasured.** No memory scoring slot has ever run, and attempt 900 may carry an unrecorded charge.

## 7. Next validation design (proposal; nothing here authorises a run)

1. **Fresh draw.** Use a new seed. Draw stratified by category from the 3086 in-scope questions outside both pilot draws, and record the excluded ids in the plan. Memory prerequisites are shared per scenario and cannot be excluded; memory questions are drawn from scenarios whose prerequisites run in full.
2. **Token endpoint first.** Primary token endpoint: provider prompt tokens of the first request per case and arm, where messages are identical across arms. It is close to deterministic, so one send per case-arm suffices, and local counts already track it within 10 tokens on 32 cases. Report tools tokens, prompt tokens and realised USD separately. Also report USD with all prompt tokens priced at the miss rate and at the hit rate, so cache sharing cannot pose as an editor effect. Keep arm rotation and analyse send position as a covariate.
3. **Accuracy endpoint with a measured noise floor.** Compare arms pairwise with McNemar on discordant pairs against a pre-registered non-inferiority margin. Add a replicate U pass (same bytes, sent again) so the identical-tools discordance rate is measured in the same run instead of inferred. With 10% discordance, detecting a 5-point paired difference (α 0.05, power 0.8) needs about 310 paired cases per comparison: n = (1.96·√0.10 + 0.84·√(0.10 − 0.05²))² / 0.05². The flight had 32. Trajectory noise (1 flip in 16 identical-tools pairs here) raises discordance, so multi-turn needs more.
4. **Mechanism checks without the model.** Integrity, ledgers and the before/after audit already run offline on all 3127 questions. Any further rule must pass them, and its population-wide effect must be reported as in section 5.

## 8. Reproduction

```bash
pip install -e ".[test]"
pytest -q
python -m tool_compression.clean_start freeze                     # pilot renders; draw.json and scope.json stay byte-identical
python -m tool_compression.clean_start package                    # package, incl. revision_vs_c47b186c.json and the revised analysis
python -m tool_compression.clean_start report-pilot --revised     # package/pilot_2026_11_25_revised_analysis.json from the archived flight
(cd studies/clean-start-usx/evidence/pilot-2026-11-25-revised-c47b186c/original && sha256sum -c ../SHA256SUMS)
git worktree add --detach /tmp/usx-c47b186c c47b186c6004e69840db3537ebe532dc22f638a8
PYTHONPATH=/tmp/usx-c47b186c/src python scripts/clean_start_sent_digest.py conversations   # = sent_renders_c47b186c.json
PYTHONPATH=/tmp/usx-c47b186c/src python scripts/clean_start_sent_digest.py population      # = population_c47b186c.json
CLEAN_START_BFCL_ROOT=/tmp/gorilla PYTHONPATH=/tmp/bfcl-deps pytest -q                     # pinned Gorilla 6ea57973 loop and scoring tests
```

## 9. Tests

`tests/test_clean_start_revision.py`:

- The archived flight matches its 397 checksums, and its revised analysis regenerates byte for byte with the forced-quit, partial-stop and snapshot facts above.
- Synthetic suites check that S keeps an elaboration on its first carrier only, never drops one no earlier tool carries, and is append-only.
- S keeps enum sentences that gloss values and drops bare lists.
- X refuses coordinator-scope pairs (with a non-coordinator control) and completes the head noun after `of`/`on`.
- The cue-phrase check fails closed when S removes the rival's phrase.
- Held-out tools never change tools already sent, in `render_tools` and in `runner.arm_tools`.
- Editor modules do no file I/O and import nothing from report, revision, package, runner or pilot.
- When the flown commit is in local history, both flown-editor digests regenerate from it byte for byte. These tests skip on a shallow checkout.

`tests/test_clean_start_package.py` now also regenerates `pilot_2026_11_25_revised_analysis.json` and `revision_vs_c47b186c.json`, and checks the three new integrity rows on all 3127 questions. The existing pinned Gorilla loop and scoring tests run unchanged.
