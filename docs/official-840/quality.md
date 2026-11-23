# Quality

This note records how a later scored run would be read. It does not define a new official metric, and it does not fill any score. The gate's `quality.scores` is null. Each contrast value is null.

Quality, once outputs exist, is official full-call accuracy on the saved lines. The contrasts are differences of that accuracy, computed separately on the thinking-off outputs and the thinking-on outputs. They are not differences of local token length.

| Contrast | Comparison |
| --- | --- |
| S − U | Own-tool semantic edits against fresh U. |
| X − U | The selection cue against fresh U. |
| SX − S | The same cue on the frozen S base. |
| SX − X | The frozen S base under the same cue. |
| SX − U | Both edits against fresh U. |

L, E, T1, and T2 are history. They are not additional arms, and their stored scores are not these contrasts.

A shorter prepared request is not a correct call. Prompt length is not an input to the label. This is not a matched-length comparison. It does not reset the official 10% target, and it is not v1.1 settlement. `official_settlement` stays false until Jacky separately says otherwise.

The label functions are the ones already used by the 12-case systems test: `classify_multiple` and `classify_irrelevance` in `tool_compression.usx_flight`.

## Multiple

The pinned checker separates a wrong function name from a right name with bad arguments. The tally keeps that split:

| Official `error_type` | Label |
| --- | --- |
| valid call | `correct` |
| `simple_function_checker:wrong_func_name` | `wrong_name` |
| `simple_function_checker:missing_required`, `unexpected_param`, `missing_optional`, and `type_error:*`, `value_error:*` | `right_name_wrong_args` |
| `multiple_function_checker:wrong_count` | `wrong_call_shape` |
| `ast_decoder:*` | `parse_failure` |

`wrong_call_shape` and `parse_failure` stay out of the name-versus-arguments split. A decode failure is not a correct call.

## Irrelevance

The desired irrelevance outcome is a decoded response that does not call a tool. A response that calls a tool is wrong.

A parse or decode failure is neither of those. The pinned relevance runner treats a decode exception as success, because it saw no function call. This report does not. The raw official success flag can be stored beside the row, and the label for that row is `parse_failure`. That label is not abstention, and it is not a correct irrelevance outcome.

## Input T

T is the provider `prompt_tokens` field on the call that produced the line. Cache-hit tokens stay inside T. The price is not folded into T. Arms that shared a body inside one cell share that T, because they shared the observation.

## What Stage A reports

The dry-run is evidence that the plan, the identities, and the stop conditions are recorded. It is not evidence about model accuracy. The 12-case systems-test accuracies are a different sample and are not copied here.
