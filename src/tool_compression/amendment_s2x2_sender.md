# Request-by-request sender

`send_frozen_plan` sends the frozen 840-case U/S2/X2/SX2 plan at catalogue tip `96795322`, thinking off then thinking on. Plan bodies stay without `max_tokens`. Wire bodies add `max_tokens` 8192 only.

Spend is recorded after each request completes. A response with usage keeps that confirmed charge. A timeout or any attempt that returns no charge stays in the running total at the all-miss local bound of the attempt already sent, until `note_confirmed_charge` records a confirmed charge for that same attempt. A later try is a new attempt. The two are not collapsed into one.

The hard ceiling is CNY ¥80.00 across both passes. When recorded spend reaches it, further sends stop and `ceiling-notice.json` tells the operator. About CNY ¥10 is a comfortable expectation, not a cap and not a stop. A run that has not finished every slot is not labeled as the full 840.

The sender does not reserve the next request, at the peak card or otherwise, and it does not stop early because a remaining-run worst case would exceed ¥80. `--live` still exits 2 before a plan is built. Official live dispatch stays refused. No provider key is read. Human review was not performed. Official v1.1 stays closed.
