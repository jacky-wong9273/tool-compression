# Cue revision

Same 12 catalogues as the [first pilot](../README.md). S is unchanged. This directory is a second X/SX comparison: one named rival and one documented difference, written so a shorter string is not treated as success.

The first-pilot rendered catalogues, token tables, selection manifest, and sealed S/X strings stay where they are. Explanations that were wrong there are corrected in [errata.md](errata.md), not by editing those files.

| Section | File |
| --- | --- |
| What this pass asks, and what it does not run | [objectives.md](objectives.md) |
| Cue rules, rendering, tokenizer, review order | [methodology.md](methodology.md) |
| Corrections to first-pilot explanations | [errata.md](errata.md) |
| Old cue and new cue for every case, including no cue | [cues-side-by-side.md](cues-side-by-side.md) |
| Sealed new cue record | [edits/x-record.json](edits/x-record.json) |
| U and S byte copies, plus new X and SX | [rendered/](rendered/) |
| Same-sitting reread, before the token counts | [reread.md](reread.md) |
| Structural checks and schema signatures | [checks/structural.json](checks/structural.json), [checks/signatures.json](checks/signatures.json) |
| Hashes of the frozen first-pilot files | [checks/frozen-sha256.json](checks/frozen-sha256.json) |
| Local full-request tokens and deltas | [checks/tokens.json](checks/tokens.json) |
| Tables | [results.md](results.md) |
| Clock | [time.json](time.json) |
| Short report | [summary.md](summary.md) |

Re-check both the frozen pilot and this revision with:

```bash
python -m tool_compression semantic-audit
pytest -q
```

The command prints counts only. It does not call a model.
