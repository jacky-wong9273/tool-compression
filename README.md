# tool-compression

Recorded Evaluation Protocol v1.1 result for description-only compression of native function-calling requests, on the Week 1 prototype.

In this single thinking-off replicate, the shared local intervention produced small provider-input savings and remained within the prespecified observed primary accuracy-loss margin. The combined utility target was not reached. These results do not establish statistical non-inferiority or general quality preservation.

L−U is −0.5 percentage points; the observed accuracy loss is +0.5 points.

Primary billed-basis saving is 1,398 of 121,018 provider input tokens (ratio of means 0.011552000528846949). The combined utility target is resolved and was not reached. The account is `official/RESULTS.md`. Commands that reproduce preparation and official scoring from saved outputs are `official/COMMANDS.md`. The locked settlement is `official/settlement/official_settlement.json`.

The study statistic `T` is billed-basis provider total input (`prompt_tokens`), including cached and uncached components. The cache-associated input-cost figure in `official/tables/usage_accounting.json` is a different measurement and is not the study statistic.

Official scoring used the handler alias `DeepSeek-V3.2-Exp-FC` because `deepseek-flash` is not in the pinned official registry. That alias evaluates saved outputs. Its registry `model_name` is `deepseek-chat`, and this package refuses `bfcl generate` under the alias. The flight model was `deepseek-flash` with thinking `{"type":"disabled"}`. Paid inference is not implemented.

The revised proposal, `Controlled_Tool_Description_Compression_Proposal_Revised.tex`, is the source of truth for the study design. `EVALUATION-PROTOCOL-v1.1.md` is the scientific protocol. `OPERATIONAL-NOTE-v1.1.md` covers launch and authorization. `Controlled_Tool_Description_Compression_Agent_Plan.md` keeps the Week 1 handoff and the protocol handoff as history, and states the recorded-result handoff. That plan names an unrevised `.tex`; the revised proposal wins. `SPECIFICATION.md` records the `week1.0` reference configuration.

`evidence/WEEK1_EVIDENCE_PACKET.md` is the historical Week 1 record, including the stop recommendation. This package does not rewrite it.

The reference configuration stays at `r=0.75`, Jaccard neighbours of at least 1/5, at most two neighbours, and `lambda=1/2`. P, I, and C keep separate implementation traces. L is a reporting label only. Where their complete requests coincide, those requests are reported as L. E is TSCG `compressDescriptions` at its own pinned operating point. The reference comparison is C versus U at `r=0.75`, with C represented by L where those requests coincide. That representation is not evidence that the contrast term was tested: primary `f` is still 0. E versus U is a separate report and cannot pass the C–U target. The denominators stay `multiple` 200, `simple_python` 400, and `irrelevance` 240.

Pins: BFCL / gorilla `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`; TSCG `dfcba63d6190285c45a7c412268dbcc757664ab2` / `@tscg/core` 1.4.3.

This repository does not vendor BFCL or TSCG. Check out the commits named in `evidence/WEEK1_EVIDENCE_PACKET.md`, then run:

```bash
pip install -e ".[test]"
pytest -q
python -m tool_compression official-check
python -m tool_compression characterize --bfcl-root PATH_TO_GORILLA --out evidence/week1_characterization.json
python -m tool_compression arm-e --bfcl-root PATH_TO_GORILLA --tscg-root PATH_TO_TSCG --out evidence/week1_arm_e.json
python -m tool_compression packet --characterization evidence/week1_characterization.json --arm-e evidence/week1_arm_e.json --out evidence/WEEK1_EVIDENCE_PACKET.md
```

`characterize` and `arm-e` read the local checkouts and write counts, hashes, and the packet. They do not call a model and they do not produce official scores. A local token count is not the 10% provider-input target.

The evaluation scaffold reads the committed Week 1 hashes and the recorded settlement. It does not need those checkouts:

```bash
python -m tool_compression manifest
python -m tool_compression inspect-suffix
python -m tool_compression groups
python -m tool_compression artifact-manifest --check official/artifact_manifest.json
```

`manifest` prints the reference pins, denominators, and the execution-record slots. `inspect-suffix` reports what the handler float sentence carries after conversion. `groups` counts provisional exact-request groups for U, L, and E. `FLOAT_SUFFIX_INSPECTION.md` records the suffix inspection.

## Post-result T1 and T2

`FOLLOWON-SPECIFICATION.md` freezes one phrase-level extractive compressor in two configurations. T1 uses the tool's own identifier overlap. T2 adds one half of the pinned neighbour score `q` on the same optional pieces. The cap and the weight are new-trial settings. They do not retune the closed run, and the 10% C-versus-U target is not a reset test.

The offline package is `followon/`. It is ready for a separately authorized evaluation and is not a measured result. `followon/HANDOVER.md` separates the submitted baseline, the saved-output package, and these two conditions. `followon/FLIGHT.md` is the later thinking-off Flash path for all 840 T1 cases and all 840 T2 cases. The code requires `EXPLORATORY_CEILING_CNY` and does not default one. `--live` is required before a client is built. Where the reconfirmed audit shows T1, T2, and U requests identical, that later flight is a same-request re-draw of official U, not a new compressed catalogue. No provider call is made by the preparation itself.
