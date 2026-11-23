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
| Parent of the fourth tranche | `93e8adf16426099fda4013f302473a82c6235a07` |
| Parent of the fifth tranche | `e0fa9e9505eec53c0ce1580dedb3f2fa33f015b1` |
| Parent of the sixth tranche | `237ba7972e5e29950dbc6e2ac58d4e75d7bb3a82` |
| Parent of this tranche | `3833000cf7a90e0165710a4b0aa3893fd5df116b` |
| Pull-request tip | the commit that adds this seventh tranche. The pull request description quotes that tip SHA. |

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
  rendered/<case_id>/{U,S,X,SX}.json   828 cases, 3312 files
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
src/tool_compression/official_840_tranche_e.py   fifth tranche
src/tool_compression/official_840_tranche_f.py   sixth tranche
src/tool_compression/official_840_tranche_g.py   seventh tranche
src/tool_compression/__main__.py       usx-840 subcommand added; usx-flight unchanged
tests/test_official_840.py
```

## Counts

Sample 840. Sealed 828. Remaining 12. One-tool catalogues in the sample: 640. Multi-tool: 200.

By category, sealed / remaining: `multiple` 192 / 8, `simple_python` 398 / 2, `irrelevance` 238 / 2.

This run added 114 cases. The first 714 were left as sealed. The formative twelve stay unsealed. The remainder is exactly those twelve.

Sealed cue coverage, which is not cue efficiency:

| | Count |
| --- | ---: |
| Cued | 54 |
| Uncued | 774 |
| Uncued, one tool | 636 |
| Uncued, multi-tool | 138 |

The sixteen new cues are `multiple_1`, `multiple_5`, `multiple_17`, `multiple_18`, `multiple_19`, `multiple_22`, `multiple_23`, `multiple_26`, `multiple_30`, `multiple_51`, `multiple_64`, `multiple_70`, `multiple_83`, `multiple_87`, `multiple_89`, and `multiple_94`. Ninety-eight new multi-tool catalogues are uncued. `multiple_31`, `multiple_44`, `multiple_49`, `multiple_60`, `multiple_68`, `multiple_71`, and `multiple_77` stay uncued because a cue would read as an exclusion the sources do not state. `multiple_52`, `multiple_78`, and `multiple_95` stay uncued for the same class-inclusion reason.

## Identities inside the sealed set

| Identity | Count | What follows |
| --- | ---: | --- |
| S = U | 787 | Those catalogues were left verbatim. |
| S differs from U | 41 | The earlier thirty-five, plus frame deletions on `multiple_127` and `multiple_165`, and schema-default omissions on `multiple_20`, `multiple_30`, `multiple_165`, `multiple_177`, and `multiple_187`. |
| X = U | 774 | The uncued ids. An empty cue leaves X equal to U. |
| SX = S | 774 | The same uncued ids. SX is S plus an empty cue. |
| SX = X | 787 | The same ids as S = U. |
| SX = U | 738 | No S edit and no cue. |
| Four distinct catalogues | 5 | `multiple_9`, `multiple_10`, `multiple_21`, `multiple_30`, `multiple_73`. |

If the 828 sealed cells were sent, thinking off and thinking on would be 928 payloads each, 1856 in total. Identical arms inside one cell share one observation. Identical bodies in another cell, or on the other thinking pass, stay separate calls. The plan does not alter a catalogue to force a difference. `multiple_30` is the new four-distinct cell: its S edit and its cue were judged separately.

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
| Sealed / blocked | 828 / 12 |
| Aimed 19:00 HKT example | off-peak, `live_permitted` false because the set is not sealed |
| Off-peak reserve, one call | ¥2.572864 |
| Peak reserve | ¥5.145728, recorded and not used |
| Ceiling in the gate | `0.01`, a proof value; the reserve does not fit |
| Unique payloads if the sealed cells were sent | 1856 |

`pytest -q` passed, including a regeneration of this gate from the pinned BFCL files at `6ea57973`. The regenerated gate matches the committed file. Tests also cover identity sharing inside one cell, a separate call for a matching body in another cell, thinking on as a second pass over the same catalogues, the peak stop with no continuation switch, and the frozen-file hashes.

## Remaining editorial work

12 cases. They are the formative twelve, and their ids are in [remaining-work.md](remaining-work.md). No S or X judgement was invented for them. `flight_ready` is false, and `--live` still refuses.
