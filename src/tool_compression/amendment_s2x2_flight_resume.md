# Resume safety for the U/S2/X2/SX2 runner

This note sits beside `amendment_s2x2_flight.py`. It does not change the frozen catalogues, and it does not authorize a provider call. Official v1.1 stays closed. Human review was not performed. The paid flight is not ready. This revision is not authorization to start a paid flight.

## Accounting on resume

A resume refuses to continue when the run directory cannot prove its exposure. Refusal leaves the files in place. A completion marker is not deleted on that path, because it can be the last surviving record of spend. A second restart sees the same evidence and refuses again.

- A missing `calls-ledger.jsonl` is safe only when no hold, stop, or live record claims settled spend, a settled call, unresolved exposure, or completion. Otherwise the resume stops. Settled spend is not replaced with zero.
- A missing `cap-hold.json` is not a zero. If a stop or completion record still shows unresolved exposure, or the records disagree about that exposure, the resume stops and does not send.
- A final ledger line that is not valid JSON is torn. It is not dropped, and nothing is appended after it. Repairing a missing newline on a valid final line is an accounting write. It happens only under the run owner lock, immediately before a later append.
- If a hold, stop, or live summary claims more settled spend than the ledger itemizes, or a stop claims more settled calls than the ledger has rows, the resume stops. A lower summary does not reduce the ledger: a stop file can be older than a later settled line.
- If a stop or completion record claims more unresolved exposure than the hold itemizes, the resume stops. The files are kept until the records are reconciled.
- The public recovery read (`load_cap_state`) does not rewrite the ledger, the hold, the stop, or the completion marker, and it does not take the owner lock because it does not write. Every accounting write goes through that same owner lock.
- The first open writes `wire-manifest.json` for the entire wire plan. Each entry's hash is the hash of the serialized body, not a stored label copied forward. A later open must present that same plan. A partial plan, a rebuilt plan, a body whose bytes no longer match the manifest, or a directory that already has accounting and no manifest is refused.
- Funded and unfunded preflight both persist that manifest before they return, so a later send path is pinned to the verified plan. The ordered-slot digest of the official 2,174 wire slots stays `f9311c325819064255b4cd35d39526a5c05c40c669969857148c5c82117353bd`.
- Before a body is handed to a client, the runner hashes the exact serialized request again and requires that hash to equal the manifest entry for the slot. Before it writes `live.json`, every settled row must match one manifest entry by slot and request hash.
- `run.lock` is an exclusive flock held for the whole open. A second process that resumes the same directory is refused. The lock is released when the process exits, including after a crash.

`live.json` is still written only when every slot in that frozen plan is settled, each settlement matches the manifest, and settled spend plus unknown holds is within the ceiling. A refused resume does not write it. A partial over-cap run is not labeled complete.

## The ¥80.00 ceiling

The figure CNY ¥71.751836 is the local model of one full pass over both thinking modes: 2,174 wire sends, each priced off-peak as all-miss `o200k_base` tokens of that wire body plus the full `max_tokens` 8192 output allowance. It is not a provider invoice. That local model is estimated to fit ¥80. It is not a spending cap.

Jacky's ceiling for this runner is CNY ¥80.00 for both passes together. A supplied ceiling above ¥80.00 is refused. ¥80.00 is not per pass, and it is not USD. The ceiling is not authorization to fly.

Provider `prompt_tokens` is the billed input (`T`). Local token counts are not provider T. The largest billed-to-local ratio seen so far is not an upper bound on the next unseen bill, so this runner does not use that ratio to decide whether another send fits.

### No provider-enforced spend limit

The public DeepSeek Flash Chat Completions API, checked on 2026-11-24 without an API key and without a provider call, does not offer a request field that hard-caps the charge for this run. Account balance is not a control this process can set or read. There is no verified provider-enforced spend limit to turn on, and none is invented here.

What is documented, and what this runner reserves before a send:

- Billable input is at most the documented context window of 1,048,576 tokens. That is the `context_window` in the public list-models example for `deepseek-flash`. The pricing page calls the same window 1M. Chat completions limit the total of input tokens and generated tokens by that context length.
- Billable output is at most 384×1024 = 393,216 tokens. That is the pricing page's maximum output and the example's `max_output_tokens`. `max_tokens` 8192 is still sent. The chat-completions text calls `max_tokens` the maximum number of tokens that can be generated, but it does not explicitly say reasoning tokens sit inside that field. The reservation therefore uses the model's documented maximum output, not 8192. This runner does not use the Responses API, whose `max_output_tokens` text does include reasoning tokens.
- The applicable published tariff used as the upper card is the peak card on the Chinese pricing page (cache-miss input ¥2 per million tokens, output ¥8 per million), which matches the card already in this repository. Off-peak is half of peak. The runner still refuses to send when its Shanghai clock says peak. The reservation uses the higher card because a boundary or an unbundled holiday can be billed at peak.

The reservation adds the full context window at the peak miss rate and the full maximum output at the peak output rate. One call cannot spend both caps at once, because they share the window. The sum overstates a single call and is still an upper bound under that published card. DeepSeek says prices may change, so the card is not a contractual freeze. The reservation is not a spending guarantee against a later price change.

An unknown charge, including a timeout, stays reserved at that per-call bound until it is reconciled. The runner does not send when settled spend, plus unknown holds, plus one such reservation for every not-yet-settled slot, would pass the supplied ceiling. For the 2,174 wire sends that sum is above ¥80, so the offline gate does not treat the run as funded and does not send it. The local ¥71.751836 figure remains on the gate as the estimate. It does not fund the run.

A returned bill is recorded as the provider reported it. If that bill is above the documented reserve or the ceiling, it stays in the ledger. No further send is made, and the partial run is not labeled complete. Detecting that bill is not what keeps the next call from being charged; the reservation checked before the send is.
