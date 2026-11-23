# Remaining work

549 cases have no sealed S and no sealed X. The ids are in [remaining-work.json](remaining-work.json). That list is a work manifest. It is not a score, and it is not a cue judgement.

| Category | Sample | Sealed | Remaining | One-tool catalogues in the sample |
| --- | ---: | ---: | ---: | ---: |
| `multiple` | 200 | 40 | 160 | 0 |
| `simple_python` | 400 | 141 | 259 | 400 |
| `irrelevance` | 240 | 110 | 130 | 240 |
| Total | 840 | 291 | 549 | 640 |

Of the remainder, 389 catalogues have one tool and 160 have more than one. A one-tool catalogue cannot take a cue, but that rule is applied when the case is sealed. The 389 are not pre-judged here. The 160 multi-tool cases are not pre-cued either.

The formative twelve remain in the list: `multiple_0`, `multiple_7`, `multiple_11`, `multiple_12`, `multiple_35`, `multiple_92`, `multiple_100`, `multiple_153`, `simple_python_34`, `simple_python_175`, `irrelevance_50`, `irrelevance_59`. Their pilot S and X texts stay in `docs/semantic-audit-pilot/`. They are not the official-840 seal.

`flight_ready` is false while this list is non-empty. `--live` refuses the package. A later editor seals further cases with the same S and X rules, rebuilds the records, and leaves official settlement false.
