# tool-compression

Unpaid Evaluation Protocol v1.1 scaffold for description-only compression of native function-calling requests, built on the Week 1 prototype.

The revised proposal, `Controlled_Tool_Description_Compression_Proposal_Revised.tex`, is the source of truth for the study design. `EVALUATION-PROTOCOL-v1.1.md` is the scientific protocol. `OPERATIONAL-NOTE-v1.1.md` covers launch and authorization. `Controlled_Tool_Description_Compression_Agent_Plan.md` keeps the Week 1 handoff as history and states the current handoff. That plan names an unrevised `.tex`; the revised proposal wins. `SPECIFICATION.md` records the `week1.0` reference configuration.

`evidence/WEEK1_EVIDENCE_PACKET.md` is the historical Week 1 record, including the stop recommendation. This package does not rewrite it. Paid inference is not included and is not authorized.

The reference configuration stays at `r=0.75`, Jaccard neighbours of at least 1/5, at most two neighbours, and `lambda=1/2`. P, I, and C keep separate implementation traces. Where their complete requests coincide, the reporting label is L. E is TSCG `compressDescriptions` at its own pinned operating point. The reference comparison is C versus U, with C represented by L where those requests coincide. E versus U is a separate report and cannot pass the C–U target. The denominators stay `multiple` 200, `simple_python` 400, and `irrelevance` 240.

The 10% mean provider-input target is unresolved until provider usage is measured. Local token counts do not establish it, and the target is unchanged.

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
