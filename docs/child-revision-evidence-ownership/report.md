# Child revision after PR #13

Parent commit `9154b8b171ed4022fd062cabc47136ccf5d5d22a` on `cursor/s2-x2-sx2-amendment-e97e`. That branch is the frozen comparator. This packet does not retitle, close, or rewrite it.

Offline only. Socket construction is denied during the rebuild. No provider is called and no API key is read. This command has no live mode. Official v1.1, T1/T2, #11, and #12 are unmodified. No accuracy result and no billed-input result is claimed.

## Rendered catalogues

Rendered U, S2, X2, and SX2 bytes under `docs/amendment-s2x2/rendered/` are unchanged versus `9154b8b171ed4022fd062cabc47136ccf5d5d22a`. 3360 files, SHA-256 `da8c9b86986af9d4d70b1405aaf825913eb515f6e24c58ed4235984462921d76`.

The evidence records, the S2 rule-effect column, and the comparison sheet changed. The cue sentences did not, so the rendered tool text did not.

## Evidence-ownership fixes

All 30 cues were checked in both directions: the target citation and the rival citation, against the original tool, index, path, and value.

One value fix:

`multiple_11` `math_roots_polynomial` at index 2 cited ['a', 'b', 'c'], which belong to math_roots_quadratic. The rival `math_roots_quadratic` at index 0 cited ['coefficients'] and held `order_support`, which belong to math_roots_polynomial. The target now cites ['coefficients'] and `order_support` at `/function/parameters/properties/coefficients/description`. The rival now cites ['a', 'b', 'c']. Both directions of that swapped record were corrected.

The cue sentence did not change:

> Unlike math_roots_quadratic, which takes named quadratic coefficients, this takes an ordered coefficient array.

`multiple_11` in every direction:

- `math_roots_quadratic` index 0 versus `math_roots_polynomial` index 2: target parameters ['a', 'b', 'c']; rival parameters ['coefficients']; order_support on rival. cited values already owned by that side.
- `math_roots_cubic` index 1 versus `math_roots_polynomial` index 2: target parameters ['a', 'b', 'c', 'd']; rival parameters ['coefficients']; order_support on rival. cited values already owned by that side.
- `math_roots_polynomial` index 2 versus `math_roots_quadratic` index 0: target parameters ['coefficients']; rival parameters ['a', 'b', 'c']; order_support on target. value corrected.

Cue text changes: 0. Cues whose cited values were already on the owning tool: 29. Those 29 rows gained an explicit tool index, path, and value on each citation. The excerpts and schema values stored for them were already the original text of that tool.

`multiple_12` remains uncued. No grammar rule or regular expression was added. The return-on-equity versus return-on-assets contrast, equity versus assets in the denominator, stays a recorded limitation of the current cue rule.

Machine-readable detail: `docs/amendment-s2x2/checks/evidence-ownership.json` and `docs/amendment-s2x2/ledgers/x2.jsonl`.

## Adopted S2 edits

Rule effect of each adopted S2 field. suffix_only_float_sentence removes only the converter sentence ' This is a float type value.' other_adopted is every remaining adopted edit. These counts are what the editor removed. They are not a meaningful-versus-cosmetic judgment.

The audited parent set `meaningfully_changed` equal to the adopted count and `cosmetic_only` to zero. Those labels were produced by the row constructor, not by a separate reading of the text. They are omitted here.

| rule effect | fields | o200k_base field tokens saved | changed cases |
| --- | ---: | ---: | ---: |
| suffix_only_float_sentence | 373 | 2611 | 187 |
| other_adopted | 56 | 329 | 43 |
| adopted | 429 | 2940 | 230 |

Suffix-only removals are 2611 of 2940 saved field tokens (88.81%). In 187 of 230 changed cases, every adopted edit is that removal.

A suffix-only removal deletes only the converter sentence ` This is a float type value.` from the end of the field. The other adopted edits, by the rule that fired: direct_action 17, flag_normalization 7, schema_guaranteed 14, within_tool_duplicate 18. `schema_guaranteed` covers 373 suffix-only fields and 14 other adopted fields, so the change class alone is not the split.

The token count is local `o200k_base`. It is not billed usage, accuracy, or the closed 1/10 target. Character length is not this split.

Detail: `docs/amendment-s2x2/checks/s2-edit-split.json` and `docs/amendment-s2x2/comparison/sheet.md`.

## Blinded sample

The selection method is `docs/child-revision-evidence-ownership/PROTOCOL.md`, written before these packets. This revision stops there. No human review was filled in, and no model was used as a judge or editor.

Previously exposed fixtures are flagged in `docs/child-revision-evidence-ownership/exposure-index.json` and left out of the packets.

Source-only packets:

- `docs/child-revision-evidence-ownership/packets/retained-nontrivial-contexts.jsonl`
- `docs/child-revision-evidence-ownership/packets/uncued-multi-tool-targets.jsonl`
- `docs/child-revision-evidence-ownership/packets/accepted-edit-sample.jsonl`

If a later review produces more than one faithful alternative for a field, the comparison uses the `o200k_base` token count of the field text. That score is not computed here. Complete serialized requests, including questions, are not counted here.

Rebuild check: socket probes denied 1, network `denied`.
