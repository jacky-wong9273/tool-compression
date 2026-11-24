# Blinded-sample protocol

This protocol is the selection method for a later human review. It was written before the packets were built. It does not review a field, choose a rewrite, or decide KEEP or no-cue.

The parent of this child revision is `9154b8b171ed4022fd062cabc47136ccf5d5d22a` on `cursor/s2-x2-sx2-amendment-e97e` (PR #13). That branch stays as it is. This protocol does not add a grammar rule or a regular expression, and it does not add a rule for `multiple_12`.

## What is exposed

These fixtures were already opened. They are flagged in `exposure-index.json` and left out of the blinded packets.

Named fixtures:

- `multiple_11`
- `multiple_12`
- `multiple_34`
- `multiple_35`
- the triangle `get_angles` wording: function `triangle_properties_get`, pointer `/function/parameters/properties/get_angles/description`

Formative 12, the `selected` ids in `docs/semantic-audit-pilot/selection/manifest.json`:

- `multiple_35`
- `multiple_0`
- `multiple_11`
- `multiple_12`
- `multiple_7`
- `multiple_92`
- `multiple_153`
- `multiple_100`
- `simple_python_175`
- `simple_python_34`
- `irrelevance_59`
- `irrelevance_50`

A case is exposed when it is one of those formative ids or one of the named fixtures. `multiple_34` is a named fixture and is not in the formative 12. The other named cases are already in the formative 12. A unique own-tool context is exposed when any occurrence sits in an exposed case, or when the function is `triangle_properties_get` and the pointer is the `get_angles` description above.

`multiple_12` stays uncued. Return on equity and return on assets use different denominators, equity versus assets. That missed contrast is a recorded limitation of the current cue rule. This protocol does not try to hit it.

## Populations

Official case order is `docs/official-840/selection/manifest.json` `ids_in_file_order`. The source text is the official U tool. S2, X2, and SX2 text are not source for these packets.

An own-tool context is the pair `(context_id, pointer)`. `context_id` is the SHA-256 of one complete original tool. The first occurrence is the earliest case in official order, then the lower tool index.

### Retained nontrivial unique own-tool contexts

Include every unique context that the S2 row kept (`adopted` is false) and marked nontrivial (a shorter candidate was rejected, or the source was ambiguous). Rows kept as already minimal are not in this population. One row per context. The representative is the first occurrence. Skip the context when it is exposed.

The packet contains the context id, the pointer, the first case id, the first tool index, the function name, and the original tool object.

### Uncued original multi-tool targets

Include every tool in a `multiple` catalogue whose X2 cue is empty. Skip the tool when its case is exposed. Order is official case order, then tool index.

The packet contains the case id, the tool index, the function name, and the original ordered catalogue. The catalogue is U. A neighbor that received a cue elsewhere is present only as its original U text.

### Sample of accepted edits

The population is every unique own-tool context with an adopted S2 edit, excluding exposed contexts. Sort that population by the SHA-256 hex digest of the UTF-8 string

`child-revision-evidence-ownership-2026-11-24\naccepted\n{context_id}\n{pointer}`

ascending. The sample size is 24, fixed before the draw. Take the first 24. There is no coverage quota, and the draw is not replaced after seeing which fields it contains.

The packet contains the context id, the pointer, the first case id, the first tool index, the function name, the original field text, and the original tool object.

## What the packets withhold

The packets contain source material only. They withhold this revision's and PR #13's decisions: cue sentences, rival choices, no-cue reasons, KEEP reasons, candidate rewrites, adopted replacements, and rule-effect labels. They withhold questions, gold answers, and outcomes. They do not contain a proposed rewrite or a filled KEEP or no-cue decision. This document does not conduct that review, and no model is a judge or editor.

Existing justified no-change decisions stay in the amendment ledger. This protocol does not overturn them.

## Later scoring, not this revision

If a later human review produces two or more faithful alternatives for one field, the comparison uses the `o200k_base` token count of the field text. Character length is not the score. This revision does not compute that score and does not treat the review as already done.

Counting complete serialized requests, including questions, is out of scope for this revision and is not done here.

## Packets

- `packets/retained-nontrivial-contexts.jsonl`
- `packets/uncued-multi-tool-targets.jsonl`
- `packets/accepted-edit-sample.jsonl`

`exposure-index.json` lists the flagged fixtures. It does not contain tool bodies, cue text, or gold.
