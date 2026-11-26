# Revised no-web thinking-off pilot, 2026-11-25 (archived evidence)

`original/` is the uploaded `revised-pilot-c47b186c-evidence.zip` unpacked byte for byte (397 files). Nothing under it is edited, re-scored in place, or regenerated. `SHA256SUMS` lists every file (`sha256sum -c ../SHA256SUMS` from `original/`). The archive itself had SHA-256 `b1445e426c7dd97daa811c222955aeb74e749df11db84bd087cfd41e9cbda2b9`.

- Code tip that ran: `c47b186c6004e69840db3537ebe532dc22f638a8` (PR #28 after the web-search categories were removed; editors `s-rules-2026-11-25` and `x-rules-2026-11-25.2`).
- Thinking off only, peak band, 16:46:03 to 17:22:14 HKT. 900 sends, 899 billed responses, recorded USD 0.287883432. Attempt 900 (`memory_kv_prereq_3-customer-3`, arm SX, after six billed steps) ended in `provider_error:IncompleteRead`; it may or may not have been charged. No retry and no resume.
- Finished 128/164 scoring slots (32 case IDs in all four arms) and 12/216 memory prerequisites. Memory categories were never scored.
- Accuracy in `original/live-c47b186c/score` is the pinned official evaluator with `underscore_to_dot=True`.
- `official_settlement` is false. This pilot is regression and diagnosis evidence. Its outcomes are not editor inputs and were not used to choose or tune any rule.
- The score files contain BFCL gold answers because the official scorer writes them. Editors never read this directory.

Derived files next to `original/` (none of them replaces anything in it). Both come from `scripts/clean_start_sent_digest.py`, which imports whichever `tool_compression` is first on `PYTHONPATH`:

```bash
git worktree add --detach /tmp/usx-c47b186c c47b186c6004e69840db3537ebe532dc22f638a8
PYTHONPATH=/tmp/usx-c47b186c/src python scripts/clean_start_sent_digest.py conversations > sent_renders_c47b186c.json
PYTHONPATH=/tmp/usx-c47b186c/src python scripts/clean_start_sent_digest.py population > population_c47b186c.json
```

- `sent_renders_c47b186c.json`: for each of the 95 pilot conversations (41 scoring cases, 54 matched prerequisites), arm and catalogue state (initial, then after each held-out batch), the tools hash in the runner's journal formula plus local o200k_base counts. All 900 `sent` rows in `attempts.jsonl` match one of these hashes (785 initial, 115 after a held-out batch), so the flight sent exactly what the flown commit renders.
- `population_c47b186c.json`: the flown editors over the initial catalogue of all 3127 in-scope questions (tools-array tokens per arm, S edits by class, every distinct X cue). `../../package/revision_vs_c47b186c.json` compares the current editors with it.

Paired tables (sent-byte audit, matched accuracy and discordant cases, identical-tools noise, billed tokens with USD parts, first-request token deltas, send-position cache, forced quit, partial stop, memory snapshots) live in `../../package/pilot_2026_11_25_revised_analysis.json` and are rebuilt from this directory by `python -m tool_compression.clean_start report-pilot --revised`.
