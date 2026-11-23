# Semantic-audit pilot: U, S, X, SX

Offline 12-case pilot of semantic compression (S), explicit contrast (X), and both (SX), against the unmodified converted catalogue (U). Formative only. No provider call. Official scores are unchanged. This is not a full-category evaluation.

Start here, then use the files below as the reporting sources.

| Section | File |
| --- | --- |
| Objectives, the two questions, and the four conditions | [objectives.md](objectives.md) |
| Selection, blinding, rubric, walker, renderer, tokens | [methodology.md](methodology.md) |
| Selection rule, source hashes, and the 12 ids | [selection/README.md](selection/README.md) |
| Machine-readable selection manifest | [selection/manifest.json](selection/manifest.json) |
| Full 840-row ranking, ids only | [selection/ranked-ids.tsv](selection/ranked-ids.tsv) |
| Selected 12-row ranking | [selection/selected-ids.tsv](selection/selected-ids.tsv) |
| Compression record: every original and replacement | [edits/s-record.json](edits/s-record.json) |
| Contrast record: exact cues, rivals, and no-cue reasons | [edits/x-record.json](edits/x-record.json) |
| Fact ledger in reading order | [edits/fact-ledger.md](edits/fact-ledger.md) |
| Rendered U, S, X, SX catalogues | [rendered/](rendered/) |
| Structural and composition checks | [checks/structural.json](checks/structural.json) |
| Local field and prepared-request tokens | [checks/tokens.json](checks/tokens.json) |
| Schema signatures and the retailer repeat | [checks/signatures.json](checks/signatures.json) |
| Fact-count totals | [checks/fact-counts.json](checks/fact-counts.json) |
| Denominators, coverage, tokens, edits, time, risks | [results/piloting-results.md](results/piloting-results.md) |
| Editing clock | [results/time.json](results/time.json) |
| Short report | [summary.md](summary.md) |
| Invented sales pair, outside the denominator | [illustration/sales-pair.md](illustration/sales-pair.md) |

Each selected case has `rendered/<case_id>/U.json`, `S.json`, `X.json`, and `SX.json`. Those files are converted catalogue copies. They contain no question, gold call, or stored response.

## Cue revision

The files above are the frozen first-pilot record. A later pass keeps that record, keeps S, and compares a new set of contrast cues on the same 12 cases. It is not a shorter-wording contest and it does not rescore v1.1. Start at [cue-revision/README.md](cue-revision/README.md). Corrections to first-pilot explanations, including the ROA order sentence, the growth-tool verb, and the reading of the fact counts, are in [cue-revision/errata.md](cue-revision/errata.md). The sealed strings are not rewritten.

Re-check the package with:

```bash
python -m tool_compression semantic-audit
pytest -q
```

The check command prints counts only. It does not call a model.
