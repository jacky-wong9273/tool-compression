# tool-compression

Unpaid Evaluation Protocol v1.1 scaffold for description-only compression of native function-calling requests, built on the Week 1 prototype.

The revised proposal, `Controlled_Tool_Description_Compression_Proposal_Revised.tex`, is the source of truth for the study design. `EVALUATION-PROTOCOL-v1.1.md` is the scientific protocol. `OPERATIONAL-NOTE-v1.1.md` covers launch and authorization. `Controlled_Tool_Description_Compression_Agent_Plan.md` keeps the Week 1 handoff as history and states the current handoff. That plan names an unrevised `.tex`; the revised proposal wins. `SPECIFICATION.md` records the `week1.0` reference configuration.

`evidence/WEEK1_EVIDENCE_PACKET.md` is the historical Week 1 record, including the stop recommendation. This package does not rewrite it. Paid inference is not included and is not authorized.

The reference configuration stays at `r=0.75`, Jaccard neighbours of at least 1/5, at most two neighbours, and `lambda=1/2`. P, I, and C keep separate implementation traces. L is a reporting label only. Where their complete requests coincide, those requests are reported as L. E is TSCG `compressDescriptions` at its own pinned operating point. The reference comparison is C versus U at `r=0.75`, with C represented by L where those requests coincide. That representation is not evidence that the contrast term was tested: primary `f` is still 0. E versus U is a separate report and cannot pass the C–U target. The denominators stay `multiple` 200, `simple_python` 400, and `irrelevance` 240.

Official accuracy and provider-usage measurement stay out of scope until a separate authorization and a spending ceiling. The 10% mean provider-input target is unchanged and unresolved. Local token counts do not establish it.

This repository does not vendor BFCL or TSCG. Check out the commits named in `evidence/WEEK1_EVIDENCE_PACKET.md`, then run:

```bash
pip install -e ".[test]"
pytest -q
python -m tool_compression characterize --bfcl-root PATH_TO_GORILLA --out evidence/week1_characterization.json
python -m tool_compression arm-e --bfcl-root PATH_TO_GORILLA --tscg-root PATH_TO_TSCG --out evidence/week1_arm_e.json
python -m tool_compression packet --characterization evidence/week1_characterization.json --arm-e evidence/week1_arm_e.json --out evidence/WEEK1_EVIDENCE_PACKET.md
```

`characterize` and `arm-e` read the local checkouts and write counts, hashes, and the packet. They do not call a model. A local token count is not the 10% provider-input target.

The evaluation scaffold reads the committed Week 1 hashes and does not need those checkouts:

```bash
python -m tool_compression manifest
python -m tool_compression inspect-suffix
python -m tool_compression groups
```

`manifest` prints the reference pins, denominators, and the unset execution record. `inspect-suffix` reports what the handler float sentence carries after conversion. `groups` counts provisional exact-request groups for U, L, and E. None of these commands calls a model. `FLOAT_SUFFIX_INSPECTION.md` records the suffix inspection. No preparation output was regenerated: the `week1.0` implementation was checked against the pinned OpenAI completions conversion and left unchanged.

## Validation flight

Paid inference is not the default. The unset execution record still refuses a provider call. A separate validation-and-prep flight can be frozen and run by an operator who has `DEEPSEEK_API_KEY` in the environment. That flight is not an official accuracy settlement and does not decide the 10% provider-input target. It does not authorize thinking-on, a ceiling above ¥50, or a second compressor. Week 1 request hashes used model `UNSELECTED`; the flight recomputes identity after substituting `deepseek-flash` and the options actually sent. Those provisional hashes are only a way to choose the stage A sample.

The locked flight is DeepSeek `deepseek-flash` (DeepSeek-V4.1-Flash-1017) at `https://api.deepseek.com/chat/completions`. Thinking is pinned off with `thinking: {"type": "disabled"}` in the frozen record and in every request body, because DeepSeek enables thinking when the field is omitted. BFCL defaults stay on the body: temperature `0.001`, `store: false`, and tools when the catalogue is non-empty. The off-peak card is ¥0.02 cache hit, ¥1 cache miss, and ¥4 output per million tokens. The hard ceiling is ¥50. A call is not started when spend plus a documented worst-case reserve would pass that ceiling. Weekday 09:00–12:00 and 14:00–18:00 Asia/Shanghai are peak; the runner stops instead of entering those windows. The key is read only from `DEEPSEEK_API_KEY`. There is no key flag and the value is not written into the record or the artifacts.

Check out the same pins as Week 1 before a live or `--no-api` study run. BFCL / gorilla `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`. TSCG `dfcba63d6190285c45a7c412268dbcc757664ab2`, with Node available for the existing `npx tsx` bridge. Do not put the API key in the shell history of a committed file; export it in the operator environment.

```bash
pip install -e ".[test]"
python -m tool_compression freeze-record \
  --out artifacts/validation-flight/execution_record.json
python -m tool_compression validate-flight \
  --record artifacts/validation-flight/execution_record.json \
  --bfcl-root PATH_TO_GORILLA \
  --tscg-root PATH_TO_TSCG \
  --out artifacts/validation-flight
```

`validate-flight` runs stage A, then starts stage B only when that sample validates. On the committed Week 1 hashes the sample is `multiple_8`, `simple_python_38`, `irrelevance_6` (distinct U, L, and E groups) and `multiple_3` (U and L coincide, E differs). Those hashes only choose the cases. Request identity is recomputed after the model and the sent options are substituted. Stage B is one thinking-off all-category replicate under the same ceiling, still tagged validation-and-prep. If the sample fails, the command stops and does not call the provider for the replicate. `--stage a` stops after the sample even when it validates. Add `--no-api` to exercise the harness without a key and without the network. A dry run is not a live validation, and it cannot be continued as a live stage B. `flight_summary.json` records the cumulative CNY across both stages. Each stage ledger's `stage_cny` is that stage only.

Artifacts:

- `artifacts/validation-flight/execution_record.json`
- `artifacts/validation-flight/identity_recheck.json`
- `artifacts/validation-flight/flight_summary.json`
- `artifacts/validation-flight/stage_a/summary.json`
- `artifacts/validation-flight/stage_a/requests.jsonl`
- `artifacts/validation-flight/stage_a/responses.jsonl`
- `artifacts/validation-flight/stage_a/parsed.jsonl`
- `artifacts/validation-flight/stage_a/usage_ledger.json`
- `artifacts/validation-flight/stage_a/logical_ledger.json`
- `artifacts/validation-flight/stage_a/spend_ledger.json`
- `artifacts/validation-flight/stage_b/` with the same layout, only after stage A validates
- `artifacts/validation-flight/official_evaluator/README.txt` for later official-evaluator output

`store: false` is included because it is a BFCL default. The published chat-completions schema does not list that field. This package does not drop it without a live rejection to record.
