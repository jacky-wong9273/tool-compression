# Week 1 evidence packet

Label-blind audit of prepared native requests. This file does not start Phase 2, does not call a model, and does not treat a local token counter as the provider-input target.

## Decision

**stop**

Arm E is boundary-compatible (`True`), so the decision is not narrow-to-local. Primary active fraction f is 0/200. Primary request differences are P≠U 89, I≠U 89, C≠U 89, C≠I 0, P≠I 0 out of 200 original cases. P, I, and C keep the same spans, so they are one intervention. Primary neighbour degree counts are `{'0': 275, '1': 166, '2': 116}`. Inactive contrast is not an empty-neighbour artifact on that category. Primary records changed only by removing the handler float suffix: 53. Primary records with any other description change: 36. These two record counts partition C≠U. This measured picture does not justify the original paid comparison. The 10% provider total-input target is unverified. The local ratios are not a proof that the target is impossible.

Reasons:

- `utility_aim_not_established_by_local_counter`
- `arm_e_boundary_compatible`
- `provider_target_unverified`
- `primary_contrast_inactive`
- `local_arms_are_one_intervention`
- `paid_original_scope_not_justified`

Utility aim established: `False`.
Paid inference in this packet: `False`.
Phase 2 started: `False`.

Hard stop: do not harden the package and do not start Phases 2–6 until this packet is reviewed.

## Provenance

- Spec `week1.0` at settings `3/4`, neighbours `1/5` / max `2`, lambda `1/2`.
- BFCL `https://github.com/ShishirPatil/gorilla` commit `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`.
- Conversion `convert_to_tool(..., GORILLA_TO_OPENAPI, OPENAI_COMPLETIONS)`. Handler `OpenAICompletionsHandler._query_FC`.
- Conversion parity against the pinned functions: checked `840`, mismatches `0`.
- TSCG `https://github.com/SKZL-AI/tscg` commit `dfcba63d6190285c45a7c412268dbcc757664ab2`, `@tscg/core` `1.4.3`, entry `packages/core/src/index.ts compressDescriptions`, options `None`.
- Budget tokenizer `o200k_base` via `tiktoken-0.14.0`. Sensitivity recount `cl100k_base` via `tiktoken-0.14.0`. Sensitivity does not select spans.
- Revised proposal present: `True`. Agent plan present: `True`. Unrevised tex present: `False`.
- Conflict rule: The plan names Controlled_Tool_Description_Compression_Proposal.tex. The revised proposal is the source of truth.
- Counting note: Local counts are not provider total-input tokens and do not establish the 10% target.
- Data file sha256 (not vendored):
  - `BFCL_v4_irrelevance.json` `2b6ed4c2e992cdcf5f1678a701851f944bef7550ee026ed1ddb89efed5be01a6`
  - `BFCL_v4_multiple.json` `aef168155ebd74b7ac2401198b201343bc7d16d7a3d7e0d4e6d8ee82c6969b2a`
  - `BFCL_v4_simple_python.json` `82dd63ba502eb2520c6b5d1d9a5c4b590e03ff261565175561f6228a367d1991`
- Pinned BFCL source sha256:
  - `bfcl_eval/__main__.py` `c70b49a7541abeaa399d193dd0d94d535f83ce415bfbbf7aa217c2370d14fcb6`
  - `bfcl_eval/constants/category_mapping.py` `ef31291f17c1ac0504b246345bd56e6bac44fec4239741e158f9fcf2c819cb35`
  - `bfcl_eval/constants/type_mappings.py` `1702fb67afbe2c492608e58e2b7d02e46381f50166b47f3c952f76e34c7cd3bd`
  - `bfcl_eval/eval_checker/ast_eval/ast_checker.py` `2aae7a68461a8f76c0be3894c8901b66b56967a1989d3ab066051e3fb97f1538`
  - `bfcl_eval/eval_checker/eval_runner.py` `b1033684908819ccb312d4d0e2c563359d69247412f00206013b2292b0e3ce81`
  - `bfcl_eval/model_handler/api_inference/openai_completion.py` `f0bc8734a3173df79e52fa6d757ac6b2585f7582e2f19ac7cddf5170269dd3f7`
  - `bfcl_eval/model_handler/base_handler.py` `5ac4bdd139a7fe15cb9ee6cd75735ec27f9b25478ff3d82d2ea5208d832969e4`
  - `bfcl_eval/model_handler/utils.py` `f78fd3edce603b333dc9a88ee2c041dc547d51f71aa449ffebc044c4b1e353f3`

## Original counts and prepared requests

| Category | Role | Records | Prepared | Failures | Tools | Tools/record min–max | Unsupported tools | Unlisted descriptions | Max turns |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|
| multiple | primary | 200 | 200 | 0 | 557 | 2–4 | 0 | 0 | 1 |
| simple_python | control | 400 | 400 | 0 | 400 | 1–1 | 0 | 0 | 1 |
| irrelevance | control | 240 | 240 | 0 | 240 | 1–1 | 0 | 0 | 1 |

The prepared request is the OpenAI Chat Completions object: `messages` (question turn 0 only), `model="UNSELECTED"`, `temperature=0.001`, `store=false`, and `tools` when the catalogue is non-empty. Identity for `f` includes that configuration. No request was truncated to fit a context window. The model is unselected, so no context-window check was applied.

## Description opportunity

### multiple

Float-suffix fields removed: `{'C': 146, 'I': 146, 'P': 146}`. Of the changed fields, suffix-only `{'C': 144, 'I': 144, 'P': 144}`; other description changes `{'C': 54, 'I': 54, 'P': 54}`. Records whose only description edits are suffix removal: `{'C': 53, 'I': 53, 'P': 53}`. Records with any other description change: `{'C': 36, 'I': 36, 'P': 36}`.
Span-choice differences (not only request hashes): `{'cases': {'C_vs_I': 0, 'P_vs_I': 0}, 'fields': {'C_vs_I': 0, 'P_vs_I': 0}}`.

| Arm | Fields | Single-span | Single-span with another cue | With optional | Optional kept | Optional all dropped | Changed | Unchanged | Uplift | Frozen | Below nominal | Stopped early |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| P | 2101 | 1625 | 270 | 198 | 2 | 196 | 198 | 1903 | 1917 | 0 | 174 | 198 |
| I | 2101 | 1625 | 270 | 198 | 2 | 196 | 198 | 1903 | 1917 | 0 | 174 | 0 |
| C | 2101 | 1625 | 270 | 198 | 2 | 196 | 198 | 1903 | 1917 | 0 | 174 | 0 |

Token sums are the local budget tokenizer on fields, not provider totals.

| Arm | d | protected-only p | nominal | budget | achieved | span 1 | span 2 | span 3 | span 4+ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| P | 24924 | 23498 | 17903 | 24057 | 23521 | 1625 | 425 | 48 | 3 |
| I | 24924 | 23498 | 17903 | 24057 | 23521 | 1625 | 425 | 48 | 3 |
| C | 24924 | 23498 | 17903 | 24057 | 23521 | 1625 | 425 | 48 | 3 |

`P` protection-reason span counts `{'condition': 105, 'default': 317, 'first_span': 2101, 'literal': 283, 'negation': 32, 'restriction': 83, 'unit': 197}`; changed fields by role `{'function': 9, 'parameter': 189}`.
`I` protection-reason span counts `{'condition': 105, 'default': 317, 'first_span': 2101, 'literal': 283, 'negation': 32, 'restriction': 83, 'unit': 197}`; changed fields by role `{'function': 9, 'parameter': 189}`.
`C` protection-reason span counts `{'condition': 105, 'default': 317, 'first_span': 2101, 'literal': 283, 'negation': 32, 'restriction': 83, 'unit': 197}`; changed fields by role `{'function': 9, 'parameter': 189}`.

### simple_python

Float-suffix fields removed: `{'C': 42, 'I': 42, 'P': 42}`. Of the changed fields, suffix-only `{'C': 42, 'I': 42, 'P': 42}`; other description changes `{'C': 52, 'I': 52, 'P': 52}`. Records whose only description edits are suffix removal: `{'C': 35, 'I': 35, 'P': 35}`. Records with any other description change: `{'C': 45, 'I': 45, 'P': 45}`.
Span-choice differences (not only request hashes): `{'cases': {'C_vs_I': 0, 'P_vs_I': 0}, 'fields': {'C_vs_I': 0, 'P_vs_I': 0}}`.

| Arm | Fields | Single-span | Single-span with another cue | With optional | Optional kept | Optional all dropped | Changed | Unchanged | Uplift | Frozen | Below nominal | Stopped early |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| P | 1570 | 1238 | 250 | 94 | 3 | 91 | 94 | 1476 | 1489 | 0 | 77 | 94 |
| I | 1570 | 1238 | 250 | 94 | 3 | 91 | 94 | 1476 | 1489 | 0 | 77 | 0 |
| C | 1570 | 1238 | 250 | 94 | 3 | 91 | 94 | 1476 | 1489 | 0 | 77 | 0 |

Token sums are the local budget tokenizer on fields, not provider totals.

| Arm | d | protected-only p | nominal | budget | achieved | span 1 | span 2 | span 3 | span 4+ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| P | 18894 | 18178 | 13598 | 18445 | 18190 | 1238 | 294 | 36 | 2 |
| I | 18894 | 18178 | 13598 | 18445 | 18190 | 1238 | 294 | 36 | 2 |
| C | 18894 | 18178 | 13598 | 18445 | 18190 | 1238 | 294 | 36 | 2 |

`P` protection-reason span counts `{'condition': 110, 'default': 270, 'first_span': 1570, 'literal': 278, 'negation': 53, 'restriction': 63, 'unit': 186}`; changed fields by role `{'function': 12, 'parameter': 82}`.
`I` protection-reason span counts `{'condition': 110, 'default': 270, 'first_span': 1570, 'literal': 278, 'negation': 53, 'restriction': 63, 'unit': 186}`; changed fields by role `{'function': 12, 'parameter': 82}`.
`C` protection-reason span counts `{'condition': 110, 'default': 270, 'first_span': 1570, 'literal': 278, 'negation': 53, 'restriction': 63, 'unit': 186}`; changed fields by role `{'function': 12, 'parameter': 82}`.

### irrelevance

Float-suffix fields removed: `{'C': 101, 'I': 101, 'P': 101}`. Of the changed fields, suffix-only `{'C': 101, 'I': 101, 'P': 101}`; other description changes `{'C': 35, 'I': 35, 'P': 35}`. Records whose only description edits are suffix removal: `{'C': 57, 'I': 57, 'P': 57}`. Records with any other description change: `{'C': 28, 'I': 28, 'P': 28}`.
Span-choice differences (not only request hashes): `{'cases': {'C_vs_I': 0, 'P_vs_I': 0}, 'fields': {'C_vs_I': 0, 'P_vs_I': 0}}`.

| Arm | Fields | Single-span | Single-span with another cue | With optional | Optional kept | Optional all dropped | Changed | Unchanged | Uplift | Frozen | Below nominal | Stopped early |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| P | 933 | 682 | 110 | 136 | 0 | 136 | 136 | 797 | 805 | 0 | 125 | 136 |
| I | 933 | 682 | 110 | 136 | 0 | 136 | 136 | 797 | 805 | 0 | 125 | 0 |
| C | 933 | 682 | 110 | 136 | 0 | 136 | 136 | 797 | 805 | 0 | 125 | 0 |

Token sums are the local budget tokenizer on fields, not provider totals.

| Arm | d | protected-only p | nominal | budget | achieved | span 1 | span 2 | span 3 | span 4+ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| P | 11449 | 10494 | 8224 | 10865 | 10494 | 682 | 225 | 25 | 1 |
| I | 11449 | 10494 | 8224 | 10865 | 10494 | 682 | 225 | 25 | 1 |
| C | 11449 | 10494 | 8224 | 10865 | 10494 | 682 | 225 | 25 | 1 |

`P` protection-reason span counts `{'condition': 61, 'default': 117, 'first_span': 933, 'literal': 140, 'negation': 27, 'restriction': 33, 'unit': 88}`; changed fields by role `{'function': 1, 'parameter': 135}`.
`I` protection-reason span counts `{'condition': 61, 'default': 117, 'first_span': 933, 'literal': 140, 'negation': 27, 'restriction': 33, 'unit': 88}`; changed fields by role `{'function': 1, 'parameter': 135}`.
`C` protection-reason span counts `{'condition': 61, 'default': 117, 'first_span': 933, 'literal': 140, 'negation': 27, 'restriction': 33, 'unit': 88}`; changed fields by role `{'function': 1, 'parameter': 135}`.

Protection reasons overlap; a span can carry more than one. Single-span fields and optional spans retained by a cue are not mutually exclusive causes. `r=0.75` is a per-field cap, not an exact retained fraction. Floor uplift and frozen fields are separate from nominal attainment. A single-span uplift is mechanical: the only span is protected, so the protected rendering is the original and sits above the nominal cap. A multi-span uplift means the protected rendering itself is already above that cap, so the effective cap is the protected rendering. Whole-span selection can also finish below the nominal cap when the next span does not fit. Suffix-removed counts include fields that also change other text; suffix-only counts do not.

## Local arms on complete requests

- `multiple`: P≠U `89`, I≠U `89`, C≠U `89`, C≠I `0` of `200` original records. `f` numerator `0`, denominator `200`, value `0.0`.
  Within-case distinct local requests (U/P/I/C): `{'1': 111, '2': 89, '3': 0, '4': 0}`.
  Local `P` vs U on `cl100k_base`: ratio of means `0.019608`, mean of per-case ratios `0.017923`, n `200`.
  Local `P` vs U on `o200k_base`: ratio of means `0.01945`, mean of per-case ratios `0.017756`, n `200`.
  Local `I` vs U on `cl100k_base`: ratio of means `0.019608`, mean of per-case ratios `0.017923`, n `200`.
  Local `I` vs U on `o200k_base`: ratio of means `0.01945`, mean of per-case ratios `0.017756`, n `200`.
  Local `C` vs U on `cl100k_base`: ratio of means `0.019608`, mean of per-case ratios `0.017923`, n `200`.
  Local `C` vs U on `o200k_base`: ratio of means `0.01945`, mean of per-case ratios `0.017756`, n `200`.
  Blank-description orientation on `o200k_base`: ratio of means `0.331531`. Not a saving ceiling and not used by the selector.
- `simple_python`: P≠U `80`, I≠U `80`, C≠U `80`, C≠I `0` of `400` original records. `f` numerator `0`, denominator `400`, value `0.0`.
  Within-case distinct local requests (U/P/I/C): `{'1': 320, '2': 80, '3': 0, '4': 0}`.
  Local `P` vs U on `cl100k_base`: ratio of means `0.010729`, mean of per-case ratios `0.00963`, n `400`.
  Local `P` vs U on `o200k_base`: ratio of means `0.010511`, mean of per-case ratios `0.009428`, n `400`.
  Local `I` vs U on `cl100k_base`: ratio of means `0.010729`, mean of per-case ratios `0.00963`, n `400`.
  Local `I` vs U on `o200k_base`: ratio of means `0.010511`, mean of per-case ratios `0.009428`, n `400`.
  Local `C` vs U on `cl100k_base`: ratio of means `0.010729`, mean of per-case ratios `0.00963`, n `400`.
  Local `C` vs U on `o200k_base`: ratio of means `0.010511`, mean of per-case ratios `0.009428`, n `400`.
  Blank-description orientation on `o200k_base`: ratio of means `0.270692`. Not a saving ceiling and not used by the selector.
- `irrelevance`: P≠U `85`, I≠U `85`, C≠U `85`, C≠I `0` of `240` original records. `f` numerator `0`, denominator `240`, value `0.0`.
  Within-case distinct local requests (U/P/I/C): `{'1': 155, '2': 85, '3': 0, '4': 0}`.
  Local `P` vs U on `cl100k_base`: ratio of means `0.025413`, mean of per-case ratios `0.022774`, n `240`.
  Local `P` vs U on `o200k_base`: ratio of means `0.025`, mean of per-case ratios `0.022347`, n `240`.
  Local `I` vs U on `cl100k_base`: ratio of means `0.025413`, mean of per-case ratios `0.022774`, n `240`.
  Local `I` vs U on `o200k_base`: ratio of means `0.025`, mean of per-case ratios `0.022347`, n `240`.
  Local `C` vs U on `cl100k_base`: ratio of means `0.025413`, mean of per-case ratios `0.022774`, n `240`.
  Local `C` vs U on `o200k_base`: ratio of means `0.025`, mean of per-case ratios `0.022347`, n `240`.
  Blank-description orientation on `o200k_base`: ratio of means `0.287085`. Not a saving ceiling and not used by the selector.

Active fraction `f` uses every original primary case as the denominator. With response sharing and complete scoring, the absolute observed paired C–I correctness difference is at most `f`. That is an interpretation bound, not a power claim. `f=0` means C and I are the same intervention. It does not by itself bound token differences between C and U.

Local cohort ratios use `(sum U - sum arm) / sum U` on prepared records. The mean of per-case ratios is stored beside it and is not the estimand. These ratios are local serializations. They are not provider `usage.prompt_tokens`.

## Neighbours and schema proxies

- `multiple` degree counts `{'0': 275, '1': 166, '2': 116}`, mean degree `0.714542`, undirected pairs at the threshold `199`, candidate counts `{'0': 275, '1': 166, '2': 116, '3_or_more': 0}`, tools above the cap of 2 `0`.
  Closed-class diagnostic (unused by the compressor): degree counts `{'0': 359, '1': 108, '2': 90}`, undirected pairs `144`.
  Schema: property-name pairs `550`, pairs at the Jaccard threshold `126`, repeated corpus signatures `61` covering `149` tools, within-request duplicate function names `0`.
- `simple_python` degree counts `{'0': 400, '1': 0, '2': 0}`, mean degree `0.0`, undirected pairs at the threshold `0`, candidate counts `{'0': 400, '1': 0, '2': 0, '3_or_more': 0}`, tools above the cap of 2 `0`.
  Closed-class diagnostic (unused by the compressor): degree counts `{'0': 400, '1': 0, '2': 0}`, undirected pairs `0`.
  Schema: property-name pairs `0`, pairs at the Jaccard threshold `0`, repeated corpus signatures `3` covering `7` tools, within-request duplicate function names `0`.
- `irrelevance` degree counts `{'0': 240, '1': 0, '2': 0}`, mean degree `0.0`, undirected pairs at the threshold `0`, candidate counts `{'0': 240, '1': 0, '2': 0, '3_or_more': 0}`, tools above the cap of 2 `0`.
  Closed-class diagnostic (unused by the compressor): degree counts `{'0': 240, '1': 0, '2': 0}`, undirected pairs `0`.
  Schema: property-name pairs `0`, pairs at the Jaccard threshold `0`, repeated corpus signatures `2` covering `4` tools, within-request duplicate function names `0`.

The closed-class degree is a diagnostic. The selector does not remove those words. Schema figures are name and type-signature overlap counts, not a claim that prose is unnecessary.

## Arm E

- Check completed: `True`. Boundary compatible: `True`.
- Output repaired: `False`. Local cap applied: `False`.
- TSCG `estimateTokens` used as provider usage: `False`.
- Options passed: `None`. Documented policy: SDM stripFiller on OpenAI function and top-level parameter descriptions.
- Principles observed: `{'SDM': 840}`.
- Runtime failures: `0`. Preprocessing seconds: `0.506`.
- Description change classes (catalogues_with_no_runtime_or_boundary_failure): `{'case_or_punctuation_only': 505, 'substantive': 292, 'unchanged': 3807}` over `4604` fields.
- Violation shapes: `{}`.
- `irrelevance`: records `240`, runtime failures `0`, boundary failures `0`, changed records `116`, distinct from U `116`.
  Local E vs U on `cl100k_base`: ratio of means `0.004346`, mean of per-case ratios `0.004761`. Local estimate only.
  Local E vs U on `o200k_base`: ratio of means `0.005602`, mean of per-case ratios `0.006048`. Local estimate only.
- `multiple`: records `200`, runtime failures `0`, boundary failures `0`, changed records `149`, distinct from U `149`.
  Local E vs U on `cl100k_base`: ratio of means `0.003408`, mean of per-case ratios `0.003232`. Local estimate only.
  Local E vs U on `o200k_base`: ratio of means `0.004713`, mean of per-case ratios `0.004637`. Local estimate only.
- `simple_python`: records `400`, runtime failures `0`, boundary failures `0`, changed records `154`, distinct from U `154`.
  Local E vs U on `cl100k_base`: ratio of means `0.00401`, mean of per-case ratios `0.004254`. Local estimate only.
  Local E vs U on `o200k_base`: ratio of means `0.00473`, mean of per-case ratios `0.005026`. Local estimate only.

LLMLingua2 was not started. A second compressor would be a new method project. It is unused both when TSCG meets the boundary and when the decision is to narrow the original scope.

## Target, workload, and unresolved limits

Some prepared primary C requests differ from U. A local tokenizer cannot show that the 10% provider total-input target is possible or impossible. The target stays unverified.
Decision `stop` does not establish the utility aim.
Primary within-case distinct local requests: `{'1': 111, '2': 89, '3': 0, '4': 0}`. Distinct requests once a boundary-compatible E hash is added: `{'multiple': {'2': 106, '1': 28, '3': 66}, 'simple_python': {'2': 194, '1': 186, '3': 20}, 'irrelevance': {'2': 129, '1': 75, '3': 36}}`. No dollar range is stated: there is no authorized rate card.
Local preprocessing seconds for P/I/C characterization: `2.287`. Arm E bridge seconds: `0.506`. These are observations on this machine, not a benchmark.
Primary local U request-token orientation: `{'cl100k_base': {'max': 669, 'mean': 356.485, 'min': 178, 'n': 200, 'p50': 345, 'p90': 499}, 'o200k_base': {'max': 685, 'mean': 360.675, 'min': 180, 'n': 200, 'p50': 349, 'p90': 504}}`. Baseline context feasibility is unresolved because the model is unselected. Nothing was dropped to force a fit. This orientation is not a context-window result.
Unresolved: provider usage, official accuracy, the selected model and options beyond the pinned handler defaults used here, dependence components, and any rate. Missing usage stays missing. Exploratory caps 0.50 and 0.25 were not run.

## Stop

Week 1 ends with this packet. Settings stay at the provisional values `r=0.75`, Jaccard at least 1/5, at most two neighbours, and `lambda=1/2`. They were not tuned on labels or on `f`. No benchmark questions, answers, or tool prose are in this packet.
