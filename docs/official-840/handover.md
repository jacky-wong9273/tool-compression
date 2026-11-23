# Handover

Preparation only. No provider was called. `--live` was not run. No pull request was merged. Official settlement is false. The closed 10% target is unchanged.

## Git

| | |
| --- | --- |
| Branch | `cursor/official-840-usx-package-87f6` |
| Base | `main` at `1ab2b5d042b7d8fadbb0c922c51201ae6fc75c21` |
| Started from | PR #11 tip `7797047f1280d21e0b1e842d8c2a784cb9dfc7b5` (`cursor/semantic-audit-usx-pilot-5ea4`) |
| First package commit | `2374520557fef85c16af19b2b541c7da09f50f76` |
| Parent of the second tranche | `58ff9a3b2b531d3e5780409f9d35ea61a2244f70` |
| Parent of the third tranche | `561017d2332083b96bebedf2e9b6e39563cebd5a` |
| Parent of this tranche | `93e8adf16426099fda4013f302473a82c6235a07` |
| Pull-request tip | the commit that adds this fourth tranche. The pull request description quotes that tip SHA. |

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
  rendered/<case_id>/{U,S,X,SX}.json   433 cases, 1732 files
  checks/u-sha256.json
  checks/frozen-integrity.json
  checks/counts.json
  dry-run/gate.json
src/tool_compression/official_840.py
src/tool_compression/official_840_provider.py
src/tool_compression/official_840_tranche.py
src/tool_compression/official_840_tranche_b.py   second tranche; the first 18 literals stay in official_840_tranche.py
src/tool_compression/official_840_tranche_c.py   third tranche
src/tool_compression/official_840_tranche_d.py   fourth tranche
src/tool_compression/__main__.py       usx-840 subcommand added; usx-flight unchanged
tests/test_official_840.py
```

## Counts

Sample 840. Sealed 433. Remaining 407. One-tool catalogues in the sample: 640. Multi-tool: 200.

By category, sealed / remaining: `multiple` 52 / 148, `simple_python` 221 / 179, `irrelevance` 160 / 80.

This run added 142 cases. The first 291 were left as sealed. The formative twelve stay unsealed.

Sealed cue coverage, which is not cue efficiency:

| | Count |
| --- | ---: |
| Cued | 38 |
| Uncued | 395 |
| Uncued, one tool | 381 |
| Uncued, multi-tool | 14 |

The fourteen uncued multi-tool cases are `multiple_24`, `multiple_28`, `multiple_39`, `multiple_42`, `multiple_52`, `multiple_55`, `multiple_59`, `multiple_74`, `multiple_78`, `multiple_79`, `multiple_93`, `multiple_95`, `multiple_97`, and `multiple_99`. `multiple_52` and `multiple_95` are uncued because a unit conversion can already be read as covering a currency conversion. `multiple_78` is uncued for the same class-inclusion reason: a museum can already be a tourist spot.

## Identities inside the sealed set

| Identity | Count | What follows |
| --- | ---: | --- |
| S = U | 413 | Those catalogues were left verbatim. |
| S differs from U | 20 | The earlier fourteen, plus frame deletions on `simple_python_157`, `simple_python_215`, and `simple_python_217`, and schema-default omissions on `simple_python_163`, `simple_python_182`, and `multiple_97`. |
| X = U | 395 | The uncued ids. An empty cue leaves X equal to U. |
| SX = S | 395 | The same uncued ids. SX is S plus an empty cue. |
| SX = X | 413 | The same ids as S = U. |
| SX = U | 379 | No S edit and no cue. |
| Four distinct catalogues | 4 | `multiple_9`, `multiple_10`, `multiple_21`, `multiple_73`. |

If the 433 sealed cells were sent, thinking off and thinking on would be 495 payloads each, 990 in total. Identical arms inside one cell share one observation. Identical bodies in another cell, or on the other thinking pass, stay separate calls. The plan does not alter a catalogue to force a difference. `multiple_52`, `multiple_78`, and `multiple_95` stay identical to U on X because the cue was not justified.

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
| Sealed / blocked | 433 / 407 |
| Aimed 19:00 HKT example | off-peak, `live_permitted` false because the set is not sealed |
| Off-peak reserve, one call | ¥2.572864 |
| Peak reserve | ¥5.145728, recorded and not used |
| Ceiling in the gate | `0.01`, a proof value; the reserve does not fit |
| Unique payloads if the sealed cells were sent | 990 |

`pytest -q` passed, including a regeneration of this gate from the pinned BFCL files at `6ea57973`. The regenerated gate matches the committed file. Tests also cover identity sharing inside one cell, a separate call for a matching body in another cell, thinking on as a second pass over the same catalogues, the peak stop with no continuation switch, and the frozen-file hashes.

## Remaining editorial work

407 cases. The ids and the per-category counts are in [remaining-work.md](remaining-work.md). No S or X judgement was invented for them. The formative twelve stay in that list. `flight_ready` is false, and `--live` still refuses.
