# Quality

Quality, once outputs exist, is official full-call accuracy on the saved lines. The contrasts are differences of that accuracy. They are not differences of local token length.

| Contrast | Comparison |
| --- | --- |
| S − U | Frozen semantic compression against fresh U. |
| X − U | Revised cue against fresh U. |
| SX − S | Revised cue on top of frozen S. |
| SX − X | Frozen S on top of the revised cue. |
| SX − U | Both edits against fresh U. |

The five values in the gate are null. Filling them in from a guess, from local token deltas, or from an older official U file would be a different study. This one waits for the saved outputs.

A shorter prepared request is not a correct call. Prompt length is not an input to the label.

This is not a matched-length comparison. It does not reset the official 10% target, and it is not v1.1 settlement.

## Multiple

The pinned checker separates a wrong function name from a right name with bad arguments. The systems-test tally keeps that split:

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

A parse or decode failure is neither of those. The pinned relevance runner treats a decode exception as success, because it saw no function call. This report does not. The raw official success flag can be stored beside the row, and the systems-test label for that row is `parse_failure`: not abstention, and not a correct irrelevance outcome.

## What Stage A reports

The gate's `quality.scores` is null and each contrast is null. The dry-run is evidence that the plan is recorded, not evidence about model accuracy.
