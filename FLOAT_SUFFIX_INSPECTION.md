# Handler float-suffix inspection

- Date: 16 November 2026.
- Pins: BFCL / gorilla `6ea57973`, conversion `convert_to_tool(..., GORILLA_TO_OPENAPI, OPENAI_COMPLETIONS)`, handler `OpenAICompletionsHandler._query_FC`.
- This note inspects the sentence ` This is a float type value.` It does not add a suffix-control arm, and it does not rewrite `evidence/WEEK1_EVIDENCE_PACKET.md`.

The sentence is produced by the pinned `_cast_to_openai_type` when the type map is `GORILLA_TO_OPENAPI` and a property's type is `float`. In that branch the handler sets `format` to `float`, appends the sentence to the existing description, and then maps the type. `float` becomes `number`. The OpenAI completions path keeps `format`. The completions query forwards the converted tools. It does not add the sentence again.

## What the sentence says

The sentence says that the value is a float type. It contains no digit. It matches none of the `week1.0` protection cues (`negation`, `condition`, `unit`, `default`, `restriction`, `literal`). It does not state a range, a precision, a unit, or a default.

## What the converted schema already carries

On a property, the handler records the float fact in two places:

- `format` is `float`.
- The description gains the sentence.

`type` becomes `number`. That same converted type is used for Gorilla `double` and for Gorilla `number`. `type` alone does not say float. `double` receives neither `format` nor the sentence. `integer` stays `integer` and receives no sentence.

For a reader of `format`, the sentence repeats the format flag. For a reader of the description who treats `type: number` as an undifferentiated number, the sentence is the remaining float marker. Which of those readers the eventual model is, is unmeasured. The sentence is therefore neither automatically harmless nor automatically necessary. This inspection's conclusion is **unresolved**.

## Where the handler writes neither fact

A bare array item whose type is `float` is remapped to `number`. The item does not gain `format: float`, and its description does not gain the sentence. A `float` item nested one array deeper is treated the same way. A `float` property inside an array item that is an object does go through `_cast_to_openai_type`, so that property gains both `format` and the sentence.

A `float` property with no description raises `KeyError` on the append. The handler does not invent a description in order to attach the sentence. The local converter follows that path. Week 1 recorded conversion parity of 0 mismatches on 840 records. This inspection does not re-run that check.

## How the reference selector treats the sentence

The sentence is protected when it is the first span, because the first span is always protected. An empty author description plus the sentence is that case: the sentence is the only span. An authored sentence followed by the suffix leaves the suffix as a later span. That later span matches no cue, so it is optional. A synthetic Words-counter check drops that later span under the reference cap and keeps the sentence when it is the only span. That check uses the existing selector. It is not a new arm.

The historical packet already counts the audited removals on the full categories. On `multiple`, 53 records change only by removal of this sentence and 36 records have some other description change. Those two counts partition the 89 C≠U records. The primary denominator remains 200.

## Corrections

The local converter was compared with the pinned conversion source. The float branch, the type map, the array-item remap, and the nested-property walk match. No `week1.0` selector, cap, cue, neighbour rule, or lambda value was changed. No preparation output was regenerated.

Reproduce the structural flags with:

```bash
python -m tool_compression inspect-suffix
```
