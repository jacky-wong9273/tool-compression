# Piloting results

Local `o200k_base` counts for the sealed 12 catalogues. The saving is `1 - sum(condition) / sum(U)`. A negative saving means the condition is longer than U. These are not provider totals and not official scores. The 12-case line is the sum of this pilot, not a population estimate. L, E, T1, and T2 do not appear, because they are not arms here.

The two control categories are behaviour illustrations. Their rows are not rates for the 400 or 240 source catalogues.

## Denominators

| Slice | Cases | Tools | Allowlisted fields | Fields changed | Fields left as U |
| --- | ---: | ---: | ---: | ---: | ---: |
| `multiple` | 8 | 20 | 81 | 21 | 60 |
| `simple_python` | 2 | 2 | 8 | 2 | 6 |
| `irrelevance` | 2 | 2 | 6 | 0 | 6 |
| Pilot total | 12 | 24 | 95 | 23 | 72 |

Unique schema signatures, name included and description strings removed: 24, beside the 8 / 2 / 2 case totals. Unique parameter signatures, function name ignored: 22. The only repeated parameter signature is the three retailer tools in `multiple_92` (`safeway_vegan_products`, `wholefoods_vegan_products`, `walmart_vegan_products`). Those three cues are one family in one catalogue.

Every description string on these 24 tools is on the walker allowlist. No nested property description and no `items.description` occurred in the sample. The walker still covers those scopes; this sample did not exercise them.

## Cue coverage

6 of 8 `multiple` catalogues receive at least one cue, on 15 of 20 tools in those catalogues.

| Case | Tools | Cue | Why |
| --- | ---: | --- | --- |
| `multiple_35` | 2 | yes | LCM versus GCD, both calculated from two integers. |
| `multiple_0` | 2 | yes | Triangle given three side lengths versus circle given a radius. |
| `multiple_11` | 3 | yes | Roots of a quadratic, a cubic, or a polynomial. |
| `multiple_12` | 3 | yes | YOY growth from revenue versus ROE versus ROA. |
| `multiple_7` | 2 | yes | Population growth versus impact on an ecosystem. |
| `multiple_92` | 3 | yes | The same vegan-product lookup at three retailers. |
| `multiple_153` | 3 | no | Mountains, entropy, and a historical date do not answer a similar need. A shared parameter name, `location`, does not make the actions confusable. |
| `multiple_100` | 2 | no | A music scale progression and a highest common factor do not answer a similar need. |

`simple_python_175`, `simple_python_34`, `irrelevance_59`, and `irrelevance_50` each have one tool, so X stays U and SX stays S. `multiple_92` has no S change at all: every field was already the retailer qualifier, the city-state format, or a prose default the schema does not carry. Its X/SX difference is the cue alone.

The 6/8 count is a finding about these eight catalogues. It is not a rate for the other 192 `multiple` catalogues, and it is not a reason to add a cue where no rival qualifies.

## Local tokens

Field tokens are the description strings only. Request tokens are the full prepared request, including the question turn, the schema, and the wrapper. Question text is not stored.

### Description fields

| Slice | U | S | X | SX | S saving | X saving | SX saving |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `multiple` | 927 | 790 | 1,513 | 1,376 | 137/927 | −586/927 | −449/927 |
| `simple_python` | 76 | 71 | 76 | 71 | 5/76 | 0/76 | 5/76 |
| `irrelevance` | 48 | 48 | 48 | 48 | 0/48 | 0/48 | 0/48 |
| Pilot total | 1,051 | 909 | 1,637 | 1,495 | 142/1,051 | −586/1,051 | −444/1,051 |

142/1,051 is 13.51%. 5/76 is 6.58%. The request-level picture is smaller, because the question and the schema dominate.

### Prepared requests

| Slice | U | S | X | SX | S saving | X saving | SX saving |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `multiple` | 2,796 | 2,659 | 3,379 | 3,242 | 137/2,796 | −583/2,796 | −446/2,796 |
| `simple_python` | 319 | 314 | 319 | 314 | 5/319 | 0/319 | 5/319 |
| `irrelevance` | 248 | 248 | 248 | 248 | 0/248 | 0/248 | 0/248 |
| Pilot total | 3,363 | 3,221 | 3,946 | 3,804 | 142/3,363 | −583/3,363 | −441/3,363 |

142/3,363 is 4.22%. 137/2,796 is 4.90%. 5/319 is 1.57%.

S removes the same 142 tokens from the field sum and from the request sum. X and SX do not: the field sum grows by 586 and 444, while the request sum grows by 583 and 441. The three-token gap is the prepared-request serialization, not a second edit. Reporting the two layers separately is what makes that visible.

Per case, description-field tokens, then prepared-request tokens:

| Case | Fields U/S/X/SX | Requests U/S/X/SX |
| --- | --- | --- |
| `multiple_35` | 103 / 81 / 169 / 147 | 279 / 258 / 345 / 324 |
| `multiple_0` | 162 / 97 / 254 / 189 | 422 / 357 / 514 / 449 |
| `multiple_11` | 115 / 112 / 192 / 189 | 374 / 371 / 451 / 448 |
| `multiple_12` | 132 / 120 / 322 / 310 | 438 / 426 / 628 / 616 |
| `multiple_7` | 99 / 72 / 171 / 144 | 293 / 266 / 365 / 338 |
| `multiple_92` | 103 / 103 / 192 / 192 | 357 / 357 / 443 / 443 |
| `multiple_153` | 143 / 141 / 143 / 141 | 388 / 386 / 388 / 386 |
| `multiple_100` | 70 / 64 / 70 / 64 | 245 / 238 / 245 / 238 |
| `simple_python_175` | 31 / 28 / 31 / 28 | 131 / 128 / 131 / 128 |
| `simple_python_34` | 45 / 43 / 45 / 43 | 188 / 186 / 188 / 186 |
| `irrelevance_59` | 17 / 17 / 17 / 17 | 112 / 112 / 112 / 112 |
| `irrelevance_50` | 31 / 31 / 31 / 31 | 136 / 136 / 136 / 136 |

`multiple_12` shows the token cost of naming the finance inputs inside the cue: field tokens go from 132 to 322. `multiple_0` shows the largest S cut, 162 to 97, mostly from flag sentences whose defaults already sit on the schema.

## Fact counts

The counting unit is an inventoried claim in `edits/fact-ledger.md` and the two JSON records, not a token and not a field.

| Count | Value |
| --- | ---: |
| Propositions | 201 |
| Preserved, from the edited text or a cited schema path | 201 |
| Lost | 0 |
| Unsupported additions | 0 |
| Uncertain claims retained | 17 |
| Duplicate or illustration omissions, not counted as losses | 22 |
| S propositions | 162 |
| X cue propositions | 39 |

The 17 uncertain retentions are 14 handler float sentences and 3 `e.g. Denver, CO` examples. The 22 omissions are schema-duplicated defaults, types, and enum lists, scope phrases that remain on the function description, and the illustrative `eg. Bankruptcy` example.

## A useful edit and a rejected one

Useful S edit, `multiple_0` / `triangle_properties_get` / `get_angles`:

- Before: "A flag to determine whether to calculate the internal angles of triangle. Default is true."
- After: "Whether to calculate the internal angles."
- `internal` stays, because the parameter name does not say it. "Default is true." is the schema default `true`. "of triangle" remains in the function description.

Rejected S edit: deleting ` This is a float type value.` wherever `format` is `float`. The suffix note treats that repetition as unresolved, so the sentence stays character for character. Replacing "number" with "integer" where the prose and the schema disagree was also rejected; those conflicts stay flagged and unrepaired. Dropping `'standard'` and `'reduced'` from `calculate_lcm` was rejected because that schema has no enum.

Useful X edit, `multiple_92` / `safeway_vegan_products`, appended after one space:

"Unlike wholefoods_vegan_products, which gets available vegan products at specified Whole Foods store, this gets available vegan products at specified Safeway store."

The same sentence is on X and on SX. Whole Foods is the earlier of the two equally close rivals.

Rejected X edit: "the circle tool cannot return angles." `circle_properties_get` never says that. Silence is not an exclusion. A cue that contrasted the ecology tools by a default of 5 years was rejected for the same reason: the growth tool's prose does not state a default, and the impact tool's prose does not state its schema default of 5. No cue was written for `multiple_153` or `multiple_100`.

## Time

One editor. Descriptions were first opened at about 2026-11-23T03:31:00Z. Round-0 decisions were saved at 2026-11-23T03:33:34Z, before any sibling tool was opened. Both records were sealed at 2026-11-23T03:52:09Z. Wall-clock from open to seal is 21 minutes: about 17 on S, including the masked before/after reread, and about 4 on the cue check against the ordered catalogues. The reread was the same editor in the same sitting. It is not a delayed second pass and not an independent validation. Details are in `time.json`.

## Residual risks

No model saw U, S, X, or SX. A zero lost-fact count means each inventoried claim still has a cited string or schema path. It does not mean a model will use that path.

The plausible counterexamples are:

- Flag defaults on the triangle and circle tools now live on the schema (`default: true`) and no longer in the prose. A reader that ignores schema defaults loses "true."
- `calculate_gcd`'s allowed algorithms live on the enum. The prose keeps only the default, `euclidean`, which the schema does not state.
- "Company name." no longer says the YOY calculation. The function sentence still does.
- "Time period in years." no longer says population growth or impact. The function sentences still do. The unit years stays, because the schema does not state it.
- `law_type` no longer contains the only concrete illustration, Bankruptcy. The schema has no enum, so a model that was using the example as a hint loses that hint. The words "eg." are why it was treated as an illustration.
- After S, both geometry tools say "Whether to calculate the area." The function descriptions still differ: triangle, three side lengths, perimeter, versus circle, radius, circumference. X and SX add the cross-tool sentence on top of that. If those function sentences had been collapsed into the same words, the shared parameter line would be a real choice risk. They were not.
- Cue text can repeat a clause S shortened. That is the mechanical SX rule, and it is why SX is longer than S even when the cue restates something S treated as a duplicate.
- Several prose/schema tensions were left in place: "number" versus integer, vegan-product functions whose category enum includes `gluten-free`, "calculated" versus "analyzes," and an entropy function that states an isothermal reversible process while `isothermal` is also a boolean parameter. The pilot does not repair them.
- X spends tokens by design. Whether the extra sentence changes a tool choice is unmeasured.

## What would be a different study

A scored run, a provider-token measurement, a 200 / 400 / 240 pass, or a change to the historical 10% target would be a different study. This package stops at the sealed 12-case records and the local checks.
