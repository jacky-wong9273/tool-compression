# S2 / X2 / SX2 editor rules

These rules are the offline editor. They do not score a case, call a model, or reopen the closed v1.1 comparison.

## Input

U is the official converted catalogue, copied byte for byte. The conversion is `to_openai_completions_tools`. A float BFCL value keeps `format: float`, `type: number`, and the suffix ` This is a float type value.` Questions, gold calls, and outcomes are not inputs.

## S2

Visit every function description, parameter description, and nested description. The editor receives that tool's complete original definition and schema, never a sibling tool. A candidate is the shortest locally verified rewrite this procedure can prove:

- drop a float-suffix sentence only when the schema still says `format: float` and `type: number`;
- drop a quoted enum sentence only when the quoted set equals the unchanged schema enum and the sentence does not define a value;
- drop a default sentence only when the parsed literal equals the unchanged schema default;
- drop a within-tool restatement only when the final function description still contains the recovered wording;
- turn an exact `This function ...` frame into its direct action without adding a claim;
- turn `A flag to determine whether to ...` into the whether-clause. `get_angles` stays `Whether to calculate the internal angles`. The schema default stays in place.

A candidate that is not strictly shorter, that changes only spacing or punctuation, or that drops a condition, negation, `whether`, `internal`, a literal, or a unit, is rejected. Otherwise the original stays, with `already_minimal`, `ambiguous_source`, or `no_shorter_faithful_candidate`. The same decision is reused only when the field and the complete tool context match. Every occurrence is logged.

## X2

Qualify each target on the original ordered catalogue. S2 is hidden. A control, one tool, gets no cue. A rival has to serve one common user need, with evidence on both sides from the original function text, parameter text, or immutable schema. An unrelated tool does not veto another pair. The closest rival is the one with the longer shared wording, then the lower original index. At most one cue is appended to the target's function description. The cue names that rival once, states the supported axis, and does not say that only one tool can do the job. An unqualified target stays verbatim.

The verified axes are a shared action with the same required parameter names and types and one short substitution, and named polynomial coefficients versus one ordered coefficient array. Each citation records the tool index, the path, and the value on the tool that owns that text. The target cites its own parameters. The rival cites its own parameters.

## SX2

Start from the exact S2 tools. At the function description X2 selected, append one ASCII space and the identical X2 cue bytes. Every other field stays S2. SX2 is not edited again.

## Controls

For a one-tool catalogue, the X2 tool input equals the U tool input byte for byte, and the SX2 tool input equals the S2 tool input byte for byte. The file wrapper may carry a different condition label. The compared bytes are the tool list and the request envelope `{model, temperature, store, tools}`.
