# Validation thinking-off flight, 2026-11-25 (archived evidence)

`original/` is the uploaded `validation-0bf829c6-evidence.zip` unpacked byte for byte (1498 files). Nothing under it is edited, re-scored in place, or regenerated. `SHA256SUMS` lists every file (`sha256sum -c ../SHA256SUMS` from `original/`). The archive itself had SHA-256 `93f360f99f5fe6841374ebb737f0180b0fd4212ef524eb348965fb9713faff9d` and 2233894 bytes.

- Code tip that ran: `0bf829c6c2d24e5efa0483c7447c7ed0df4c53b9` (PR #28, editors `s-rules-2026-11-25.2` and `x-rules-2026-11-25.3`), on the frozen 313-case draw in `../../validation/draw.json`.
- Thinking off only, off-peak band, started 19:22:21 HKT; last journal event 20:41:33 HKT. 2482 sends, 2481 billed responses, ledger USD 0.346230789. Attempt 2482 has no terminal event and may or may not have been charged.
- The run stopped because the box environment was lost, not because of a provider error or the ceiling. Finished 1214/1252 scoring slots and 20/60 notetaker prerequisites. No retry and no resume. `original/live-0bf829c6/run.json` and `spend.json` are stale (`running`, one bill behind); `FINAL-0bf829c6.json`, the journal and the bill ledger are the record.
- Accuracy in `original/live-0bf829c6/score` is the pinned official evaluator with `underscore_to_dot=True`, run afterwards on the finished result files.
- 303 scoring cases finished on all four arms. Memory: only 2 `memory_kv` cases finished on all four arms; `memory_vector` and `memory_rec_sum` were never reached. U and S each have one extra `memory_kv` result, so per-arm totals over unequal denominators are not comparable.
- `official_settlement` is false. This flight is diagnosis and regression evidence. Both flown draws (the 41-case pilot and this 313-case draw) are now exposed: neither is unseen validation for any later editor.
- The score files contain BFCL gold answers because the official scorer writes them. Editors never read this directory.

Derived files next to `original/` (none of them replaces anything in it). Both come from `scripts/clean_start_sent_digest.py`, which imports whichever `tool_compression` is first on `PYTHONPATH`:

```bash
git worktree add --detach /tmp/usx-0bf829c6 0bf829c6c2d24e5efa0483c7447c7ed0df4c53b9
PYTHONPATH=/tmp/usx-0bf829c6/src python scripts/clean_start_sent_digest.py validation > sent_renders_0bf829c6.json
PYTHONPATH=/tmp/usx-0bf829c6/src python scripts/clean_start_sent_digest.py population > population_0bf829c6.json
```

- `sent_renders_0bf829c6.json`: for each of the 328 conversations of the draw (313 scoring cases, 15 notetaker prerequisites), arm and catalogue state (initial, then after each held-out batch), the tools hash in the runner's journal formula plus local o200k_base counts, and which description slots S changed and which tools X cued on the initial catalogue. All 2482 `sent` rows in `attempts.jsonl` match one of these hashes, so the flight sent exactly what the flown commit renders.
- `population_0bf829c6.json`: the flown editors over the initial catalogue of all 3127 in-scope questions. `../../package/revision_vs_0bf829c6.json` compares the current editors with it, and `../../package/revision_vs_c47b186c.json` is the earlier revision (c47b186c to 0bf829c6), now computed from this file.

Paired tables (sent-byte audit, matched accuracy and discordant cases, identical-tools noise, different-tools discordance with the tools the model called, argument values on parameters S edited, billed tokens, first-request token deltas, forced quits, memory coverage) live in `../../package/validation_2026_11_25_analysis.json` and are rebuilt from this directory by `python -m tool_compression.clean_start report-validation`.
