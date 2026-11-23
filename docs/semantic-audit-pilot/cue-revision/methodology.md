# Methodology of the cue revision

The sample, the pin, the walker, the renderer, and the tokenizer are the first pilot's. They are stated in [../methodology.md](../methodology.md). This note says only what the revision changes.

## Frozen inputs

- First-pilot tip used as the sealed record: `61329baeba8e40fb3ed6c62fbbc8cae71ded1ac3`.
- Gorilla / BFCL commit, unchanged: `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`.
- The 12 case ids, the selection hashes, and the converted U catalogues are the first pilot's. Questions were not reopened.
- S is the sealed `edits/s-record.json`. Cue wording was written from the original converted descriptions and schemas. S replacement text was not the source. A paraphrase may match S by accident. That match is not the source.

`checks/frozen-sha256.json` is the hash list of the first-pilot files this pass must not rewrite. The pilot index, `docs/semantic-audit-pilot/README.md`, is the exception: it gains a pointer here.

## What a new cue may say

- One named rival.
- One difference that both originals document, on an axis that can change which tool is selected.
- Prefer the same stated action on the same resource. If two rivals tie, the earlier tool in the original catalogue wins.
- Do not repeat a fact both tools state unless the reader needs it to understand the difference.
- One tool's silence is not an exclusion, a limit, or "only this tool can …".
- No parameter edit. The cue is appended to `/function/description` only, as one space plus the cue.
- If no rival qualifies, the cue is empty. New X is U and new SX is S. That includes `multiple_153`, `multiple_100`, and the four one-tool catalogues. A misleading distinction is not repaired by swapping in a different case.

The review question, applied before the cue was sealed: could both descriptions be true of the same request, and if so, does this cue still help the reader choose?

The worked failure is the first-pilot polynomial cue. It set "polynomial equation" against "quadratic equation". A quadratic is a polynomial, so both descriptions can be true of one request, and the contrast can be read as an exclusion. The schemas distinguish the call instead: the quadratic tool takes separate `a`, `b`, and `c`; the polynomial tool takes a coefficient array starting from the highest-degree term.

ROE versus ROA keeps the base of the return, average shareholder equity versus total average assets, and does not restate both calculations. The three retailer tools stay one family.

## How X and SX are built

`render_conditions` in `tool_compression.semantic_audit` applies the frozen S replacements, then appends the new cue. SX is that S string plus the cue. It is not a second rewrite, and the cue is not shortened again for SX. The same cue string is used in X and SX.

U and S files in `cue-revision/rendered/<case_id>/` are byte copies of the frozen first-pilot files. X and SX are new renders.

## Checks

- Structural diff outside allowlisted description strings is empty.
- Schema signatures match the frozen signatures. Only the function description may change, and only by the suffix.
- Every new non-empty cue names exactly one sibling, the recorded rival.
- Spans in `edits/x-record.json` quote the original description they cite.
- Local lengths use `o200k_base` through tiktoken, the same prepared-request serialization as the first pilot (`assemble_request`, then `json.dumps` with `ensure_ascii=False` and `(',', ':')` separators). Field tokens and full-request tokens are separate.
- Saving is `1 - sum(condition) / sum(U)` on the original totals. Negative means longer than U. A negative delta against the first-pilot cue means the new cue is shorter. Neither sign is a finding that contrast worked.

## Review

The cue record was sealed, the catalogues were rendered, and the editor then reread the originals and the new cues without the token deltas. [reread.md](reread.md) is that reading. It is the same sitting. It is self-review, not independent validation. Token tables were written after it.

Official scoring, and any full 200 / 400 / 240 U/S/X/SX run, would be a separate agreement. They are not part of this revision.
