# Methodology

This pilot edits copies of 12 catalogues. The original BFCL files stay untouched. Questions, gold calls, stored responses, and official correctness are not part of the edit packets and are not quoted here.

Official scoring, and any later run of the full 200 / 400 / 240 categories, would need a separate agreement. Neither one is in this package.

## Pins

- Repository base: `1ab2b5d042b7d8fadbb0c922c51201ae6fc75c21` on `main`, the Evaluation Protocol v1.1 scaffold.
- Gorilla / BFCL commit: `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`. The three question files were fetched at that commit. A later gorilla tip was not used.
- Source SHA-256 values, the ranking rule, and the selected ids are in `selection/manifest.json`. Recomputing the 840-row and 12-row TSV hashes is part of `tests/test_semantic_audit.py`.
- The case ids in those three files, in file order, match `evidence/week1_request_hashes.jsonl` (200, 400, 240). The recorded official settlement states those same denominators. This package does not copy official scores.
- Conversion: `to_openai_completions_tools` in `src/tool_compression/convert.py`. Dot-to-underscore names, the Gorilla type map, and the handler sentence ` This is a float type value.` on a float property that already has a description.
- Description walker: `description_slots` in `src/tool_compression/adapter.py`. Eligible strings are the function description, property descriptions under `parameters.properties` including nested properties, `items.description`, and the same property walk one array level further. A `description` key inside `default`, `example`, `examples`, or `enum` is not a slot. The pilot did not scan the catalogues for every key named `description`.
- On these 24 tools the walker and a full description-key walk agree: every description string is allowlisted. That is a fact about this sample, recorded by the tests.
- Prepared request: `assemble_request` in `prepare.py`. Messages are question turn 0. `model` is `UNSELECTED`, `temperature` is `0.001`, `store` is false, and `tools` is present when the catalogue is non-empty. Question text is used only to count tokens and is not stored.
- Tokenizer: `o200k_base` through tiktoken 0.14.0. Counts are local serializations. They are not provider usage and they are not the historical 10% target.
- Structural check: `catalogue_violations` in `validate.py`. Anything outside an allowlisted description string must be identical, including types and key order.

Benchmark questions, tool order, conversion, rendering, and the official evaluator stay fixed. The only intended difference across U, S, X, and SX is the allowlisted description text.

## Selection

Within each category, sort by the SHA-256 of the UTF-8 string `semantic-audit-pilot-01|category|case_id` with the literal values and no newline, then by case id. Take the first 8 `multiple`, 2 `simple_python`, and 2 `irrelevance`.

The sample is prospective. It is not a held-out split, and it was not chosen by markers, earlier errors, edits, or token savings. The two control categories are behaviour illustrations. They are outside any claim about the 200 primary catalogues.

## Blinding and the two passes

S was built first, one converted tool at a time. Each packet had that tool's name, schema, and description strings. Sibling names and sibling descriptions were not in the packet. Tools were opened in index rounds: every tool 0, sealed, then every tool 1, then every tool 2. Questions were not written into the packets.

The case id contains the category, so the category was not fully hidden. That limit is recorded here rather than papered over.

Before any cue was written, the 23 changed strings were reread as before/after pairs with the decision notes hidden. That reread changed two wordings: the species parameter keeps the verb `calculated`, and the music function description keeps "in a key, with a tempo and duration." The reread was the same editor, in the same sitting, not a delayed second pass and not an independent rating. Times are in `results/time.json`.

S was then left unchanged. X was written from the ordered original catalogues and their schemas. The S replacement strings were not the source of the cues. A cue sentence that happens to share words with S is allowed; using S as the evidence is not.

## Compression rubric

For each inventoried claim the ledger records the case, tool, path, source span, excerpt, role (`pick`, `use`, or `both`), decision, and where the claim can still be found.

- KEEP leaves the wording.
- CONDENSE replaces it with a shorter paraphrase that the source entails, including any new wording.
- OMIT is used only for a named duplicate, or for a purely illustrative detail, whose meaning still survives. Survival has to be a source span or a schema path in the prepared request. A deleted duplicate is not a lost fact.
- UNCERTAIN keeps the original wording. The handler float sentence is in this class: `format: float` repeats it, and `FLOAT_SUFFIX_INSPECTION.md` leaves that repetition unresolved. The Denver, CO examples are in this class because the state-abbreviation form might be a real input format.
- MERGE was not given a separate label. Where two wordings of one fact were collapsed, the dropped wording is an OMIT duplicate with a recovery path.

Every new assertion in an S string is tied back to an excerpt or a schema value. Polarity, conditions, and precision were checked on the changed fields. Sharing a word with a parameter name is not entailment. Prose/schema conflicts are flagged in the ledger and left as they are.

A counterexample, a place where an edit could change a choice or an argument, is recorded in the results. Preservation is not treated as guaranteed. No model was asked to confirm it.

## Contrast rules

X reads the complete ordered original catalogue. For each target it names at most one rival. A rival qualifies when the two tools plausibly answer a similar need and both originals document different values on a selection-relevant axis. The preferred rival is the one with the same stated action on the same resource. Ties break by original catalogue order.

The ledger names the axis, each tool's fact, the path, and the excerpt. Each tool's own distinction stays explicit. One tool's silence does not establish an exclusion, a limit, or a claim that only one tool can do something. No justified rival means no cue. A one-tool catalogue therefore has X equal to U and SX equal to S. Those cases are counted. Low coverage is a finding about these eight `multiple` catalogues. The cases and the rival rule stay as they are.

The cue is one short sentence. It may paraphrase, and it has to preserve the scope, units, conditions, and meaning of both originals. Wording from a design-discussion table is not locked. Once a cue is final, that exact string is the string in both X and X's partner SX.

Attachment: X keeps every character of the U description and, where a cue exists, appends one space and the cue to that tool's function description only. Parameter descriptions are not edited in X.

Repeated tools are grouped by schema signature so a repeated shape is visible as reuse. Confusability is judged in the actual catalogue, not from the signature alone. The three retailer tools share one parameter signature after description strings are removed. Their three cues are one family inside `multiple_92`, not three independent trials. Including the function name, all 24 tools have distinct schema signatures. The signature definitions are in `checks/signatures.json`.

## How SX is rendered

SX is not a freehand combination and the cue is not shortened. For a cued function description:

`SX text = S text + " " + cue`

`X text = U text + " " + cue`

The cue, the separator, and the path are the ones in `edits/x-record.json`. Every other allowlisted string in SX is the S string, and every other allowlisted string in X is the U string. `src/tool_compression/semantic_audit.py` is the renderer. The tests rebuild U, S, X, and SX from the sealed records and compare them with the committed files.

## Local tokens and checks

Field tokens are the `o200k_base` counts of the allowlisted description strings, summed. Prepared-request tokens are the `o200k_base` counts of the full request serialization. They are reported separately. The saving against U is

`1 - sum(condition tokens) / sum(U tokens)`

using those original totals, for each category and for the 12-case total. This is the ratio of totals, not the mean of per-case percentages. A negative value means the condition is longer than U.

The 12-case total is the sum of this pilot. It is not an estimate for 840 catalogues.

`checks/structural.json` records an empty structural diff, empty composition errors, and no sibling name inside an S description. `checks/fact-counts.json` counts preserved claims, lost claims, unsupported additions, uncertain claims retained, and duplicate or illustration omissions.

## Re-check

```bash
python -m tool_compression semantic-audit
pytest -q
```

`semantic-audit` reruns the committed-package checks. It does not call a provider. If the pinned BFCL files are available locally, `tests/test_semantic_audit.py` also recomputes the ranking hash and the prepared-request totals. The question text is not written out.
