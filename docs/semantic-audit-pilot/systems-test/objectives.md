# Objectives

Fly the 12-case U/S/X/SX pilot as a scored systems test, then stop before any paid call. The point of this package is to show that the path can be dry-run, that the ceiling and the peak rule are enforced, and that a later operator has one documented way to start the live run.

Jacky authorized the systems test at peak (t2524u/t2525u, 2026-11-23, about 14:17 Asia/Hong_Kong). Official scores stay closed. The paid call waits until Jacky supplies `EXPLORATORY_CEILING_CNY`. This directory does not supply that amount.

## What a later scored run would answer

On these 12 catalogues, with one fresh generation pass:

- S − U: semantic compression against the unmodified catalogue.
- X − U: the revised contrast cue against the unmodified catalogue.
- SX − S: the same cue added to the frozen compression.
- SX − X: compression given the cue.
- SX − U: both edits against the unmodified catalogue.

Those five differences are the reporting plan. They are empty until saved outputs exist. This package does not fill them in.

## What this package is

- A Stage A gate: no API key is read, no socket is opened, spend stays ¥0.
- A generation plan for `deepseek-flash` (`DeepSeek-V4.1-Flash-1017`), thinking disabled, temperature 0.001, `store` false.
- A scoring plan that uses pinned BFCL `evaluate --partial-eval` and the saved-output alias `DeepSeek-V3.2-Exp-FC`.
- An explicit peak authorization that applies only when the operator passes `--authorize-peak` on this command.

## What this package does not do

- It does not settle v1.1, and it does not rewrite the 10% provider-input target.
- It does not backfill historical official U responses. U is converted again from the pinned questions at flight time and must match the frozen rendered U.
- It does not rewrite the sealed first-pilot S strings, the first X/SX strings, or `cue-revision/checks/frozen-sha256.json`.
- It does not start the 840-case editorial package, T1/T2, or a robustness A/B.
- It does not treat a shorter local request as a correct call, and it does not treat this comparison as matched-length.
