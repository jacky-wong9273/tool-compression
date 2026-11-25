# Thinking-off peak pilot, 2026-11-25 (archived evidence)

`original/` is the uploaded `pilot-evidence_cefb.zip` unpacked byte for byte. Nothing under it is edited, re-scored in place, or regenerated. `SHA256SUMS` lists every file (`sha256sum -c SHA256SUMS` from `original/`). The archive itself had SHA-256 `327a235b6b9005a2f2c24300cf346ef8596296d55daa0d82a14d436fae25e034`.

- Code tip that ran: `0c0284d5c3ca76d77b11a4db304d46953844ec66` (S/X/SX editors and runner before this review).
- Thinking off only, peak band, 151 billed requests, 87/188 slots finished, stopped on `provider_error:TimeoutError` inside `multi_turn_base_86` arm SX after nine billed steps. The stopped slot left no result line and no sidecar.
- `official_settlement` is false. This pilot is regression and diagnosis evidence. Its outcomes are not editor inputs and were not used to tune the revised editors.
- The score files contain BFCL gold answers because the official scorer writes them. Editors never read this directory.

Derived tables (paired tokens, cache, outputs) live in `../../package/pilot_2026_11_25_analysis.json` and are rebuilt from this directory alone by `python -m tool_compression.clean_start report-pilot`.
