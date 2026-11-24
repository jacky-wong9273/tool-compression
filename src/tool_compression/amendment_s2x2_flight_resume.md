# Resume safety for the U/S2/X2/SX2 runner

This note sits beside `amendment_s2x2_flight.py`. It does not change the frozen catalogues, and it does not authorize a provider call. Official v1.1 stays closed. Human review was not performed. The paid flight is not ready.

## Accounting on resume

A resume refuses to continue when the run directory cannot prove its settled spend.

- A missing `calls-ledger.jsonl` is safe only when no hold, stop, or live record claims settled spend, a settled call, or completion. Otherwise the resume stops. Settled spend is not replaced with zero.
- A final ledger line that is not valid JSON is torn. It is not dropped, and nothing is appended after it.
- A final line that is valid JSON and is missing only its terminating newline is repaired before any later append, so the next record cannot glue onto it.
- If a hold, stop, or live summary claims more settled spend than the ledger itemizes, or a stop claims more settled calls than the ledger has rows, the resume stops. A lower summary does not reduce the ledger: a stop file can be older than a later settled line.
- The first open writes `wire-manifest.json` for the entire wire plan (every slot, in order, with its request hash). A later open must present that same plan. A partial plan, a rebuilt plan, or a directory that already has accounting and no manifest is refused.
- `run.lock` is an exclusive flock held for the whole open. A second process that resumes the same directory is refused. The lock is released when the process exits, including after a crash.

`live.json` is still written only when every slot in that frozen plan is settled and settled spend plus unknown holds is within the ceiling. A refused resume does not write it.

## The ¥80.00 ceiling when billed input exceeds the local estimate

The figure CNY ¥71.751836 is the local model of one full pass over both thinking modes: 2,174 wire sends, each priced off-peak as all-miss `o200k_base` tokens of that wire body plus the full `max_tokens` 8192 output allowance. It is not a provider invoice, and it is not the cap. Jacky's ceiling for this runner is CNY ¥80.00 for both passes together. A supplied ceiling above ¥80.00 is refused. ¥80.00 is not per pass, and it is not USD.

Provider `prompt_tokens` is the billed input (`T`). Local token counts are not provider T. When a returned call reports `T` above the local count for that wire body, the runner does all of the following:

1. It records the provider bill from that usage. It does not substitute the local estimate, and it does not drop the charge back to zero.
2. It keeps the ratio `T / local` as exact integers (the greatest such ratio seen on the run). A later resume reads it from the ledger, or from the hold when the hot call was not settled.
3. Before another send, and before it will label the run complete, it prices every not-yet-settled slot as off-peak all-miss on `ceil(local_tokens * ratio)` input tokens plus the full 8192 output allowance.
4. If settled spend, plus unknown-timeout holds, plus that inflated remaining bound, would pass the supplied ceiling, it writes `stop.json` with `complete: false` and does not write `live.json`. The same ceiling check stops a resume.
5. A single returned bill can already be above the ceiling, because the provider total is known only after the response. That spend stays in the ledger. No further send is made, and the partial run is not labeled complete.

A higher billed input that still leaves settled spend, holds, and the inflated remaining bound inside the ceiling can finish. Completion then sums provider bills. The local ¥71.751836 model is not used as a substitute invoice, and it cannot lift the ¥80.00 hard stop.
