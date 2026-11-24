# Request-by-request sender

`send_frozen_plan` sends the frozen 840-case U/S2/X2/SX2 plan at catalogue tip `96795322`, thinking off then thinking on. Plan bodies stay without `max_tokens`. Wire bodies add `max_tokens` 8192 only.

Spend is recorded after each request completes. A response with usage keeps that confirmed charge. A timeout or any attempt that returns no charge stays in the running total at the all-miss local bound of the attempt already sent, until `note_confirmed_charge` records a confirmed charge for that same attempt. A later try is a new attempt. The two are not collapsed into one.

The hard ceiling is CNY ¥80.00 across both passes. When recorded spend reaches it, further sends stop and `ceiling-notice.json` tells the operator. About CNY ¥10 is a comfortable expectation, not a cap and not a stop. A run that has not finished every slot is not labeled as the full 840.

The sender does not reserve the next request, at the peak card or otherwise, and it does not stop early because a remaining-run worst case would exceed ¥80.

`--live` alone still exits 2 before a plan is built. No provider key is read and no socket is opened. `--authorize-official-live` without `--live` also exits 2 and does not build a plan.

The authorized official live path is:

```
python -m tool_compression.amendment_s2x2_flight --live --authorize-official-live --bfcl-root <bfcl-root> --out <out>
```

A later operator invoking that command builds the frozen 840-case plan and sends it with the official provider client. Spend is still recorded after each completed request. The ¥80 ceiling still stops further sends and writes `ceiling-notice.json`. The command exits 0 only when that run is labeled as the full 840. A short run exits 1 and is not labeled as the full 840. About CNY ¥10 stays a comfortable expectation, not a stop. Human review was not performed. Official v1.1 stays closed. Official settlement stays false.
