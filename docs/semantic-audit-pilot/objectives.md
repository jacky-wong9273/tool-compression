# Objectives

This is a formative offline pilot of semantic description editing on 12 pinned catalogues. It asks two questions and compares four conditions built from the same unmodified control.

## The two questions

1. Semantic compression (S). What can be said in fewer words without changing the tool choice or the valid arguments? The edit is semantic. A grammar pass is not the intervention.
2. Explicit contrast (X). When two tools are easy to confuse, does naming the difference help enough to justify the extra words? The edit has to compare tools. A careful reread of each description on its own is not that comparison.

## The four conditions

| Condition | What is rendered |
| --- | --- |
| U | The pinned conversion of the original catalogue. |
| S | U, with the sealed compression replacements applied to allowlisted description strings. |
| X | U, with one sealed cue appended where a rival qualifies. |
| SX | The S text, with that same cue appended at the same path. |

U is the control for every comparison. S, X, and SX are the three edited conditions. Historical labels L, E, T1, and T2 are earlier results. They are not arms in this pilot.

## What this pilot is

- A 12-case prospective sample: 8 `multiple`, 2 `simple_python`, 2 `irrelevance`.
- An edit of copied catalogues, with a fact ledger, two sealed edit records, four rendered variants, structural checks, and local token counts.
- A place to see whether compression and explicit contrast can be built under blinding rules, and what they cost in local tokens.

## What this pilot does not do

- It does not score official accuracy, and it does not call a model provider.
- It does not estimate the 200, 400, or 240 category populations. The two-case controls illustrate behaviour on those catalogues.
- It does not retune markers, weights, `r`, or lambda, and it does not implement a general editor or a learned compressor.
- It does not move the historical 10% provider-input target.
- A later full-category evaluation, including official scoring, would have to be agreed separately. It is not part of this package.
