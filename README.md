# tool-compression

Week 1 prototype for a controlled study of description-only tool compression on native function-calling requests.

The source of truth is `Controlled_Tool_Description_Compression_Proposal_Revised.tex`. `Controlled_Tool_Description_Compression_Agent_Plan.md` is the coding-agent plan. That plan names an unrevised `.tex`; the revised proposal wins. `SPECIFICATION.md` records the `week1.0` engineering choices. It is not another proposal.

The local arms are U, P, I, and C at the provisional cap `r=0.75`, with Jaccard neighbours of at least 0.2, at most two neighbours, and `lambda=0.5`. Those settings are untuned. Arm E is TSCG `compressDescriptions` at its own pinned policy. The primary category is the original BFCL `multiple` category. `simple_python` and `irrelevance` are controls.

This repository does not vendor BFCL or TSCG. Check out the commits named in `evidence/WEEK1_EVIDENCE_PACKET.md`, then run:

```bash
pip install -e ".[test]"
pytest -q
python -m tool_compression characterize --bfcl-root PATH_TO_GORILLA --out evidence/week1_characterization.json
python -m tool_compression arm-e --bfcl-root PATH_TO_GORILLA --tscg-root PATH_TO_TSCG --out evidence/week1_arm_e.json
python -m tool_compression packet --characterization evidence/week1_characterization.json --arm-e evidence/week1_arm_e.json --out evidence/WEEK1_EVIDENCE_PACKET.md
```

`characterize` and `arm-e` read the local checkouts and write counts, hashes, and the packet. They do not call a model. A local token count is not the 10% provider-input target.

This branch stops at the Week 1 packet. It does not harden the package, start Phases 2–6, or merge itself.
