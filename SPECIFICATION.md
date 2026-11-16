# Week 1 specification `week1.0`

This note records the engineering choices in the Week 1 prototype. It is not a replacement for `Controlled_Tool_Description_Compression_Proposal_Revised.tex`. The coding-agent plan names `Controlled_Tool_Description_Compression_Proposal.tex`. Where they differ, the revised proposal wins.

The plan's initial selector is used where the revised proposal leaves the score formula open. Settings were not tuned on labels, on official scores, or on the active fraction `f`.

## Boundary

Conversion follows the pinned BFCL OpenAI Chat Completions path before any arm edits a description: dot-to-underscore function names, `GORILLA_TO_OPENAPI`, and the float suffix ` This is a float type value.`

Allowlisted strings are:

- `/function/description`
- parameter `description` values under `parameters.properties`, including nested `properties`
- `items.description`, and the same property walk one further array level

A `description` key inside `default`, `example`, `examples`, or `enum` is not a slot. Unsupported tool shapes pass through and stay in the denominator. Type- and order-sensitive comparison outside the allowlisted strings blocks a local output that leaves the boundary. Inputs are copied; the caller's catalogue is not mutated.

## Segmentation and rendering

Spans are conservative sentence or newline units. `.`, `!`, and `?` end a span only at whitespace or end of text, and not when the mark continues an ellipsis, follows a digit, or belongs to `e.g.`, `i.e.`, `etc.`, `vs.`, `dr.`, `mr.`, `mrs.`, `ms.`, `fig.`, `eq.`, `vol.`, `al.`, or `st.`. Anything ambiguous stays one span.

Keeping every span returns the original string. A gap of one or more dropped spans becomes one ASCII space. Adjacent kept spans keep the original characters between them. A kept first span keeps the original prefix. A kept last span keeps the original suffix. Empty and whitespace-only fields are returned unchanged.

## Protection

The first span is always protected (`first_span`). Later spans are protected when they match a cue: `negation`, `condition`, `unit`, `default`, `restriction`, or `literal`. Literals are digits or quoted strings, the plan's "important literals" elaboration of constraint-bearing units. Cues overlap and are counted that way. A protected single-span field stays unchanged. The cues are a fallible lexical heuristic.

## Budgets and selectors

`d_j` and `p_j` are local token counts of the original field and of its protected-only rendering. The budget tokenizer is `o200k_base` because the model id is unselected. `cl100k_base` recounts prepared requests and does not select spans. Neither count is provider usage.

Nominal cap is `floor(3/4 * d_j)`. When `p_j <= d_j`, the effective cap is `max(nominal, p_j)`. When `p_j > d_j`, the field keeps its original text. Each candidate rendering is re-tokenized. Caps do not move across fields.

`P` adds optional spans in source order and stops at the first that does not fit. `I` and `C` rank optional spans by score per span token, break ties toward the earlier source index, skip a span that does not fit, and continue. Output is in source order.

`I` averages a source-position preference with normalized own-tool unigram frequency. Position for span `i` of `n` is `1` when `n=1`, otherwise `(n-1-i)/(n-1)`. Frequency is the mean, over the span's distinct unigrams, of that unigram's count divided by the maximum unigram count in the tool's original allowlisted descriptions.

Unigrams are lowercase pieces split on camel case and non-alphanumeric boundaries. No stopword list is used by the selector.

Neighbours use Jaccard overlap of original description unigrams plus function-name and property-name unigrams. The threshold is `1/5`, at most two neighbours. Equal Jaccard keeps the earlier catalogue index. The tool itself is excluded.

`q_i(u)` is the average, over the span's unigram and within-span bigram features, of the fraction of neighbours whose original descriptions lack that feature. It is zero with no neighbours or no features. Names are in the Jaccard set and not in the `q` corpus. Bigrams do not cross fields.

`s_C(u) = s_I(u) + (1/2) q_i(u)`. Lambda zero, or no neighbours, reproduces `I`.

## Requests and arm E

The prepared request uses question turn 0 as `messages`, `model="UNSELECTED"`, `temperature=0.001`, `store=false`, and `tools` when non-empty. `U` is the converted catalogue. The compressor does not receive questions or labels.

Arm E calls TSCG `compressDescriptions` with no options at the pinned commit. Its own policy is kept. The bridge does not apply `r` and does not repair output. TSCG's `estimateTokens` figures are not provider counts. JSON has one number type, so integral floats are canonicalized before the boundary comparison; description text is not rewritten by that step.

## What this specification does not do

No second ratio, no second model, no paid call, no official score, and no cache. The utility target remains a target. Week 1 stops at the evidence packet.

## Evaluation protocol v1.1

`week1.0` remains the reference configuration. Evaluation Protocol v1.1 is a later authorization for unpaid implementation. It does not retune `r` or lambda, and it does not rewrite the Week 1 stop. L is a reporting label only. Representing C by L where requests coincide does not test the contrast term; primary `f` is 0. Official accuracy and provider-usage measurement stay out of scope until a separate authorization and a spending ceiling. The handler float-suffix inspection is `FLOAT_SUFFIX_INSPECTION.md`. No preparation output was regenerated, because the audited conversion and selectors were left unchanged.
