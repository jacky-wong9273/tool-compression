# Offline S2 / X2 / SX2 amendment

This packet builds S2, X2, and SX2 beside the official U catalogues for the same 200 `multiple`, 400 `simple_python`, and 240 `irrelevance` cases. It does not replace U, S, X, or SX. It does not score Part A, read a question or gold answer, call a provider, or merge.

U files under `rendered/<case>/U.json` are byte copies of `docs/official-840/catalogues/U/<case>.json`.

## Reproduce

```bash
python -m tool_compression amendment-s2x2 --check
```

The command rebuilds the edits in memory, compares them with these files, and repeats the mocked completion with socket construction denied. It does not accept `--live`. `--freeze` rewrites this directory and is not the check.

Evidence ownership for the 30 cues, and the split of adopted S2 edits into suffix-only float-sentence removals and other adopted edits, are in `comparison/sheet.md`, `checks/evidence-ownership.json`, and `checks/s2-edit-split.json`. The blinded-sample protocol and the source-only packets are `docs/child-revision-evidence-ownership/`.

Local token counts use `o200k_base`. `cl100k_base` is a recount only. Neither number is provider usage, a billed saving, or the closed 1/10 target. The BPE tables are the committed files in `src/tool_compression/tiktoken_cache`. The check does not download them.
