# Follow-on specification `followon.1`

This note freezes T1 and T2 before the cohort audit. It does not replace `SPECIFICATION.md`, Evaluation Protocol v1.1, or the submitted proposal. Those govern the closed thinking-off Flash run only.

The cap `max(floor(0.75 × d), p)` and the T2 weight `1/2` are new-trial settings. They are the same fractions as `week1.0` `r` and `lambda`, and they do not retune that run, its hashes, its snapshots, or its 10% C-versus-U target. That target is not a reset test for these conditions.

T1 and T2 are one compressor. The only difference is the optional-piece score.

## Boundary

Start from `to_openai_completions_tools`, the same pinned conversion as U: dot-to-underscore names, `GORILLA_TO_OPENAPI`, and the float suffix ` This is a float type value.`

Eligible strings are exactly the slots from `description_slots`: the function description and parameter descriptions reached by that walker, including nested properties and one further array level. Descriptions under `default`, `example`, `examples`, or `enum` are not slots. Unknown shapes, absent or non-string descriptions, and unsupported tools pass through unchanged. Key order, tool order, names, required flags, schemas, defaults, enums, messages, history, and model options are preserved.

Each case is compressed from its own original converted catalogue. Questions, labels, past answers, and other cases do not enter either score.

## Boundaries inside a field

Pieces are character offsets. The frozen markers are:

- Sentence ends `.` `!` `?`, using the Week 1 tests: the mark is followed by whitespace or end of text, is not an ellipsis, is not a decimal point, and is not one of `e.g.`, `i.e.`, `etc.`, `vs.`, `dr.`, `mr.`, `mrs.`, `ms.`, `fig.`, `eq.`, `vol.`, `al.`, `st.`. Closing quotes may sit between the mark and the whitespace.
- ASCII semicolon `;` (U+003B) outside quotations and outside parentheticals.
- Spaced em dash U+2014 with whitespace on both sides, outside quotations and outside parentheticals. The whitespace run before the dash starts the following piece. En dashes and hyphens are not boundaries.
- Balanced parentheses outside quotations. Preceding whitespace is part of the parenthetical piece. When the parenthetical starts at offset 0, the following whitespace is part of it instead.

A semicolon or spaced em dash is not a boundary when the following word is `and`, `or`, `but`, `nor`, or `yet` and the text before the boundary matches the v1 negation cue. Commas are never boundaries. Digits around a period are never a sentence boundary. Unclosed double quotes and unbalanced parentheses keep the whole field.

The field-final sentence mark, when it is a real sentence end, is its own always-kept terminal piece. A detachable clause keeps its separator: the semicolon, the spaced em dash and its spaces, or the parentheses.

## What may be dropped

A piece is optional only when, after stripping its leading separator, it starts with one of these exact markers, compared case-insensitively:

- `also called`
- `also known as`
- `for example`

`e.g.` is not a marker. The piece is not optional, and the field falls back whole, when that piece also contains a comma, a quoted literal, one of `must`, `shall`, `required`, `only`, `valid`, `accepted`, `allowed`, `one of`, `either`, `equal`, `equals`, `means`, or a blocking guard: negation, condition, unit, default, restriction, direction, type, return, or the float cue. Anything else is kept. Unclassified pieces are kept. No lead-in is deleted.

## Anchor

The anchor is a prefix piece, after detachable material has been marked. It is not a stranded verb or a lone adjective.

- A function anchor has a verb from the frozen `ACTION_VERBS` lexicon, or a simple `-s`, `-es`, `-ed`, `-ing`, or `-d` form of one, and at least one later content word that is not itself only a verb. Closed-class words may precede the verb. A content word before any verb means the action is not established.
- A parameter anchor is that action, or a noun phrase: it does not start with a preposition, it does not end on a dangling determiner, preposition, conjunction, or auxiliary, and it has a content word outside the frozen adjective-only list. One such noun is enough. A lone adjective is not.

Attached complements that sit before the next boundary stay inside the anchor piece. If no complete anchor is established, the original field is emitted and the fallback is logged. Fallbacks are not shortened to meet a quota.

## Protection

The anchor, terminal punctuation, and every non-optional piece are mandatory. v1 cue categories still apply: negation, condition, unit, default, restriction, and literal. Follow-on labels, recorded here and not written back into `week1.0`, are direction, quantity, type, return, and `float_type_cue`.

The converted sentence `This is a float type value` is a type cue. Its period may sit in the terminal piece. The cue is not optional because of its handler origin. If a rendering would drop it, the original field is restored and logged.

## Rendering

Kept pieces are concatenated in source order with no added characters. Keeping every piece returns the original string object. A rendering that joins two alphanumeric characters across a deleted gap, adds leading or trailing whitespace the original did not have, or leaves quotes or parentheses unbalanced, is rejected and the original field is emitted.

## Score, cap, and selector

Terms are the Week 1 unigram split: underscores, camel case, and other non-alphanumeric separators, then case-fold. Empty pieces score zero.

The own score is `|terms(piece) ∩ terms(name and property names)| / |terms(piece)|`. The identifier set is the original function name and property names of that tool only. Description text is not an identifier.

`q` is `lexical.contrast_q` on the piece, against neighbours chosen by `lexical.select_neighbours` from the full original uncompressed catalogue of this request. The pinned rule is Jaccard at least 1/5, at most two neighbours, ties toward the earlier catalogue index. Names are in the Jaccard set and not in the `q` description corpus. No neighbours, or no features, yields zero. This package does not replace that definition.

T1 score is the own score. T2 score is the own score plus `1/2 × q`. A configured weight of zero is only a fixture; the frozen T2 weight is `1/2`.

`d` is the original field's `o200k_base` token count. `p` is the count of the protected rendering. If `p > d`, emit the original field, log non-expansion, and continue. Otherwise the cap is `max(floor(0.75 × d), p)`. No emitted edit may exceed `d`. Local tokens are not provider usage.

Start from the protected pieces. Visit optional pieces by descending score, breaking ties by start offset and then piece index. Try each once. Keep it when the re-rendered field fits in the cap and in `d`; otherwise continue. Do not stop at the first miss.

## Fixtures

`Find station records; also called station search; also called railhead search.` is one sentence and is not a benchmark row. The anchor is `Find station records`. The optional ranges are `; also called station search` and `; also called railhead search`. The final period is terminal.

With tied own scores, a budget that admits either alias but not both, and the pinned tokenizer, source order makes T1 keep station search. A neighbour whose description repeats station search gives railhead search a strictly larger `q`, so T2 keeps that alias. Neighbour order is checked with `select_neighbours` and `contrast_q`.

Separate fixtures require T2 to equal T1 when there is no neighbour or the contrast weight is zero; an all-kept rendering to be the original string; `Do not include closed stations, except stations marked open, or stations without a code.` not to be split; and a description whose float type is present only as the converted sentence not to lose that sentence.

## Audit and scoring

The cohort audit is offline. `f_new` is the number of original cases whose complete T1 and T2 requests differ, divided by the category size. Preparation failures are unknown, not equal. Requests are compared as canonical JSON with the same model, options, and tool order; the hash is a lookup and the raw strings are the identity.

The primary funnel has four cumulative rows over all fields and all 200 cases, carrying one field forward: both competing fragments fit with the protected text but the pair does not; that same tool has a neighbour; T2 reverses that pair's order after the tie-break; the kept member changes, the field text changes, and the T2 request differs from T1. Stop reasons cover the cases that do not reach the next row.

`simple_python` and `irrelevance` are single-tool controls. T2 differing from T1 there is an implementation defect.

Saved-output scoring reuses the #4 adapter. `DeepSeek-V3.2-Exp-FC` cannot generate. Historical counts are recomputed from the committed settlement without network access. An archived answer binds only inside the same case and replicate and only to the same request hash. Historical conditions do not bind onto T1 or T2.

No query-aware retrieval, shortlist, tool removal, reordering, dynamic schema, extra model call, synthetic benchmark distractor, third compressor, or sweep of the old C settings is part of this specification.
