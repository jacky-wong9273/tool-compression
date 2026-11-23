# Handover

Preparation only. No provider was called. `--live` was not run. No pull request was merged. Official settlement is false. The closed 10% target is unchanged.

## Git

| | |
| --- | --- |
| Branch | `cursor/official-840-usx-package-87f6` |
| Base | `main` at `1ab2b5d042b7d8fadbb0c922c51201ae6fc75c21` |
| Started from | PR #11 tip `7797047f1280d21e0b1e842d8c2a784cb9dfc7b5` (`cursor/semantic-audit-usx-pilot-5ea4`) |
| Package commit | recorded in the following commit on this branch |
| Pull-request tip | the commit that records the package commit; the pull request description quotes that tip SHA |

PR #11 was not updated. The first-pilot files from `61329baeba8e40fb3ed6c62fbbc8cae71ded1ac3` are covered by `checks/frozen-integrity.json` and were not rewritten.

## File tree

```
docs/official-840/
  README.md
  objectives.md
  methodology.md
  reading.md
  quality.md
  operator.md
  remaining-work.md
  remaining-work.json
  handover.md
  selection/manifest.json
  catalogues/U/<case_id>.json          840 files
  edits/s-record.json
  edits/x-record.json
  rendered/<case_id>/{U,S,X,SX}.json   18 cases, 72 files
  checks/u-sha256.json
  checks/frozen-integrity.json
  checks/counts.json
  dry-run/gate.json
src/tool_compression/official_840.py
src/tool_compression/official_840_provider.py
src/tool_compression/official_840_tranche.py
src/tool_compression/__main__.py       usx-840 subcommand added; usx-flight unchanged
tests/test_official_840.py
```

## Counts

Sample 840. Sealed 18. Remaining 822. One-tool catalogues in the sample: 640. Multi-tool: 200.

Sealed cue coverage, which is not cue efficiency:

| | Count | Ids |
| --- | ---: | --- |
| Cued | 9 | `multiple_2`, `multiple_4`, `multiple_9`, `multiple_21`, `multiple_27`, `multiple_33`, `multiple_45`, `multiple_57`, `multiple_73` |
| Uncued | 9 | `multiple_24`, `multiple_28`, `multiple_99`, `simple_python_0`, `simple_python_1`, `simple_python_2`, `irrelevance_0`, `irrelevance_1`, `irrelevance_2` |
| Uncued, one tool | 6 | the three `simple_python` and three `irrelevance` ids above |
| Uncued, multi-tool | 3 | `multiple_24`, `multiple_28`, `multiple_99` |

## Identities inside the sealed tranche

| Identity | Count | What follows |
| --- | ---: | --- |
| S = U | 13 | Those catalogues were left verbatim. |
| S differs from U | 5 | `multiple_9`, `multiple_21`, `multiple_24`, `multiple_73`, `multiple_99`. Nine description slots changed. |
| X = U | 9 | The uncued ids. An empty cue leaves X equal to U. |
| SX = S | 9 | The same uncued ids. SX is S plus an empty cue. |
| SX = X | 13 | The same ids as S = U. The cue, empty or not, sits on an unchanged base. |
| SX = U | 7 | `multiple_28` plus the six one-tool cases. No S edit and no cue. |
| Four distinct catalogues | 3 | `multiple_9`, `multiple_21`, `multiple_73`. |

If those 18 cells were sent, thinking off and thinking on would be 35 payloads each, 70 in total. Identical arms inside one cell share one observation. Identical bodies in another cell, or on the other thinking pass, stay separate calls. The plan does not alter a catalogue to force a difference.

## Dry-run

`docs/official-840/dry-run/gate.json` is Stage A.

| Field | Value |
| --- | --- |
| Provider called | false |
| API key read | false |
| Spend | `0` |
| Official settlement | false |
| Clock | `2026-11-23T17:25:00+08:00` |
| Schedule | peak |
| Stopped for peak | true |
| Live would start | false |
| Flight ready | false |
| Sealed / blocked | 18 / 822 |
| Aimed 19:00 HKT example | off-peak, `live_permitted` false because the set is not sealed |
| Off-peak reserve, one call | ¥2.572864 |
| Peak reserve | ¥5.145728, recorded and not used |
| Ceiling in the gate | `0.01`, a proof value; the reserve does not fit |
| Unique payloads if the sealed cells were sent | 70 |

`pytest -q` passed, including a regeneration of this gate from the pinned BFCL files at `6ea57973`. The regenerated gate matches the committed file. Tests also cover identity sharing inside one cell, a separate call for a matching body in another cell, thinking on as a second pass over the same catalogues, the peak stop with no continuation switch, and the frozen-file hashes.

## Remaining editorial work

822 cases. The ids and the per-category counts are in [remaining-work.md](remaining-work.md). No S or X judgement was invented for them. The formative twelve stay in that list.
