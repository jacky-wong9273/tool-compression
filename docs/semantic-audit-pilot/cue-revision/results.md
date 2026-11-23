# Cue-revision results

Local `o200k_base` counts. The prepared request is the same serialization as the first pilot: question turn 0, placeholder model, temperature 0.001, `store` false, and the copied tools. Saving is `1 - sum(condition) / sum(U)`. A negative saving means the condition is longer than U. A negative delta against the first-pilot cue means the new string is shorter. Neither sign is evidence that a reader chooses the right tool. No provider was called. Official scores are unchanged.

S is the frozen first-pilot compression. U and S token totals match that record on every case. The 6/8 cue coverage is unchanged. Coverage is an opportunity to test contrast, not a benefit.

## Full-request tokens

| Case | U | S | First X | New X | First SX | New SX |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `multiple_35` | 279 | 258 | 345 | 317 | 324 | 296 |
| `multiple_0` | 422 | 357 | 514 | 458 | 449 | 393 |
| `multiple_11` | 374 | 371 | 451 | 455 | 448 | 452 |
| `multiple_12` | 438 | 426 | 628 | 518 | 616 | 506 |
| `multiple_7` | 293 | 266 | 365 | 333 | 338 | 306 |
| `multiple_92` | 357 | 357 | 443 | 419 | 443 | 419 |
| `multiple_153` | 388 | 386 | 388 | 388 | 386 | 386 |
| `multiple_100` | 245 | 238 | 245 | 245 | 238 | 238 |
| `simple_python_175` | 131 | 128 | 131 | 131 | 128 | 128 |
| `simple_python_34` | 188 | 186 | 188 | 188 | 186 | 186 |
| `irrelevance_59` | 112 | 112 | 112 | 112 | 112 | 112 |
| `irrelevance_50` | 136 | 136 | 136 | 136 | 136 | 136 |
| Total | 3,363 | 3,221 | 3,946 | 3,700 | 3,804 | 3,558 |

## Deltas for the new cues

`New X − frozen` and `New SX − frozen` use the column named in the header. `New X − U` is the cue overhead on the unmodified description. `New SX − S` is the same suffix on the frozen compression.

| Case | New X−U | New X−S | New X−first X | New X−first SX | New SX−U | New SX−S | New SX−first X | New SX−first SX |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `multiple_35` | 38 | 59 | −28 | −7 | 17 | 38 | −49 | −28 |
| `multiple_0` | 36 | 101 | −56 | 9 | −29 | 36 | −121 | −56 |
| `multiple_11` | 81 | 84 | 4 | 7 | 78 | 81 | 1 | 4 |
| `multiple_12` | 80 | 92 | −110 | −98 | 68 | 80 | −122 | −110 |
| `multiple_7` | 40 | 67 | −32 | −5 | 13 | 40 | −59 | −32 |
| `multiple_92` | 62 | 62 | −24 | −24 | 62 | 62 | −24 | −24 |
| `multiple_153` | 0 | 2 | 0 | 2 | −2 | 0 | −2 | 0 |
| `multiple_100` | 0 | 7 | 0 | 7 | −7 | 0 | −7 | 0 |
| `simple_python_175` | 0 | 3 | 0 | 3 | −3 | 0 | −3 | 0 |
| `simple_python_34` | 0 | 2 | 0 | 2 | −2 | 0 | −2 | 0 |
| `irrelevance_59` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `irrelevance_50` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Total | 337 | 479 | −246 | −104 | 195 | 337 | −388 | −246 |

On this sample, `New X − U` equals `New SX − S` on every case, and `New X − first X` equals `New SX − first SX`. That is the mechanical suffix: the same cue is appended to U and to S, and here it tokenized independently of the base. It is a check that SX did not shorten the cue. It is not a quality result.

Saving versus U, using the totals above:

| Condition | Tokens | Versus U |
| --- | ---: | --- |
| S, unchanged | 3,221 | `1 - 3221/3363` |
| First X | 3,946 | `1 - 3946/3363` |
| New X | 3,700 | `1 - 3700/3363` |
| First SX | 3,804 | `1 - 3804/3363` |
| New SX | 3,558 | `1 - 3558/3363` |

## Where the length moved

`multiple_11` is the catalogue that got longer: +4 request tokens against the first cue. The old polynomial cue opposed equation classes. The new cue states separate `a`, `b`, and `c` arguments versus a highest-degree-first coefficient array. The repair was not required to be cheaper, and it was not cheaper.

`multiple_12` was the expensive first-pilot cue. S removes 12 request tokens there (438 to 426). The first cues added 190 (438 to 628), which is 190/583 of the first pilot's total cue overhead. The new cues add 80 (438 to 518), which is 80/337 of the new overhead. ROE versus ROA now names the base, average shareholder equity versus total average assets, and does not restate net income. The growth-rate cue names its inputs against ROE and does not restate both calculations. The catalogue is still longer than U by more than S saves.

The other four cued catalogues are shorter than their first cues and still longer than U. The six uncued catalogues have new X equal to U and new SX equal to S, so their deltas against the first pilot are zero. Their negative `New SX − U` figures are the frozen S savings, not a new cue.

Description-field tokens move by the same integers as the request totals on this sample: field U 1,051, S 909, first X 1,637, new X 1,391, first SX 1,495, new SX 1,249. The comparison that matters for a later benchmark is the full request, because that is what a call would send. Field counts are the description strings alone.

## Coverage and families

| Case | Cue | Change from the first pilot |
| --- | --- | --- |
| `multiple_35` | yes | Quantity only: least common multiple versus greatest common divisor. |
| `multiple_0` | yes | Required measurement only: three side lengths versus a radius. |
| `multiple_11` | yes | Argument shape. The polynomial cue no longer treats "polynomial" and "quadratic" as exclusive classes. |
| `multiple_12` | yes | Inputs, and for the two return ratios the base only. |
| `multiple_7` | yes | Population growth versus impact. The growth tool assesses; the sibling analyzes. |
| `multiple_92` | yes | Retailer only. One family, not three trials. |
| `multiple_153` | no cue / unchanged | No similar need. |
| `multiple_100` | no cue / unchanged | No similar need. |
| `simple_python_175` | no cue / unchanged | One tool. |
| `simple_python_34` | no cue / unchanged | One tool. |
| `irrelevance_59` | no cue / unchanged | One tool. |
| `irrelevance_50` | no cue / unchanged | One tool. |

Schema signatures match the frozen signatures. The only repeated parameter signature is still the three retailer tools. Structural diffs outside allowlisted descriptions are empty. The cue attaches only to the function description.

## Reread

The reread is [reread.md](reread.md). Same editor, same sitting, sealed cues first, token table after. It is not independent validation. No cue was changed after that reading. The bankruptcy example in `simple_python_175` stays deleted from S. The editor marked no inventoried claim as lost or unsupported; that mark does not mean all information was preserved.

A later U/S/X/SX benchmark, if it is authorized, would be a different piece of work. This pass does not start it.
