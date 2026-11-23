# Exploratory r=0.50 and r=0.25

The later full-catalogue comparison of setting A (r=0.50, λ=1/2, all 840 cases) and setting B (r=0.75, λ=1/4, all 840 cases) is `evidence/full-catalogue/COMPARISON.md`. The official figures below stay closed.

Offline audit of the official P/I/C compressor at the two named ratios. No provider call was made. The closed r=0.75 result is unchanged: L, λ=1/2, thinking off, DeepSeek-V4.1-Flash-1017, S_LU = 1398/121018 ≈ 1.155%, primary accuracy U 186/200, L 185/200, E 186/200. The 10% token target stays 1/10. This package does not claim that target.

Branch base: `8619d2fd58dee5babc511970a8d88fb975037149` (open PR #3). Configs: `exploratory.h50.2026-11-20` (r=1/2) and `exploratory.h25.2026-11-20` (r=1/4). λ=1/2, Jaccard ≥ 1/5, at most two neighbours, tokenizer `o200k_base`. Protections, first-span structure, pins, and thinking-off are the official ones.

## Flyable

**H50 is flyable. H25 is flyable.**

Coverage is 840/840 in both settings (multiple 200, simple_python 400, irrelevance 240). Failures: none. Structural violations: 0. P, I, and C coincide on every case, so each setting uses one shared label. `ready_for_evaluation` is true. `provider_called` is false. `network_used` is false. Official r=0.75 hashes were reproduced (840/840, mismatch count 0) and the BFCL data pin matched.

The complete H50 requests and the complete H25 requests are the same 840 hashes. The 0.25 cap does not change any request beyond r=0.50 on this catalogue. Flyability is identity versus U and versus official L. Both settings meet that rule. A later H25 flight repeats the same three catalogues as H50.

Three cases differ from both U and official L, at both settings:

- `multiple/multiple_40`
- `simple_python/simple_python_99`
- `simple_python/simple_python_316`

The other 837 cases match official L. Irrelevance matches official L on all 240 cases. A later flight sends only the three cases above, one call each. It does not send U, E, or official L.

## Request identity

| Category | Cases | Identical to U | Different from U | Identical to official L | Different from official L | New versus both |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| multiple | 200 | 111 | 89 | 199 | 1 | 1 |
| simple_python | 400 | 320 | 80 | 398 | 2 | 2 |
| irrelevance | 240 | 155 | 85 | 240 | 0 | 0 |

The same table applies to H50 and to H25. Per-arm counts match the case counts because P, I, and C share one hash.

Unique request groups of U plus the shared compressed request: 1,094 (multiple 289, simple_python 480, irrelevance 325). That count excludes E. The official U/L/E group count remains 1,513.

## Local token sums (`o200k_base`)

These sums use the official local tokenizer. They are not provider billed-basis T. The historical primary U denominator on that basis is 121,018.

| Category | U | Official L (r=0.75) | H50 and H25 | Local tokens versus official L |
| --- | ---: | ---: | ---: | ---: |
| multiple | 72,135 | 70,732 | 70,709 | −23 |
| simple_python | 66,596 | 65,896 | 65,884 | −12 |
| irrelevance | 38,560 | 37,596 | 37,596 | 0 |
| all 840 | 177,291 | 174,224 | 174,189 | −35 |

P, I, and C sums are equal inside each setting. Local ratio of means versus U is 1,426/72,135 on multiple, 712/66,596 on simple_python, and 964/38,560 on irrelevance.

## Uplift, contrast, and field status

Contrast activity f is 0/240, 0/200, and 0/400. C−I request differences are 0 cases and 0 fields in every category. Optional spans retained: 0. Frozen fields: 0. Empty or whitespace fields: 0.

The protection floor already exceeds the nominal cap on these description fields:

| Category | Fields | H50 uplift | H25 uplift | H50 below nominal | H25 below nominal |
| --- | ---: | ---: | ---: | ---: | ---: |
| multiple | 2,101 | 2,014 | 2,101 | 30 | 0 |
| simple_python | 1,570 | 1,540 | 1,570 | 21 | 0 |
| irrelevance | 933 | 873 | 933 | 16 | 0 |

P records `stopped_early` on the fields it changes (multiple 198, simple_python 94, irrelevance 136). I and C record `stopped_early` 0. The selected requests still coincide. Cue counts, identical at both caps: multiple condition 105, default 317, first_span 2,101, literal 283, negation 32, restriction 83, unit 197; simple_python condition 110, default 270, first_span 1,570, literal 278, negation 53, restriction 63, unit 186; irrelevance condition 61, default 117, first_span 933, literal 140, negation 27, restriction 33, unit 88.

Full rows: `evidence/exploratory/audit.json`, `evidence/exploratory/h50_request_hashes.jsonl`, `evidence/exploratory/h25_request_hashes.jsonl`.

## Later operator flight

This path does not start on import, on the audit command, or without `--live`. The commands below were checked only as a plan (`started=false`, `provider_called=false`, three groups). Do not start them from this handover.

Set `EXPLORATORY_CEILING_CNY` to the authorized ceiling before either command. The code has no default ceiling and refuses a recorded ceiling that differs from the supplied one. The existing pre-call reserve is ¥2.572864 (1,000,000 input tokens at the miss rate plus 393,216 output tokens at the output rate). A supplied ceiling that cannot hold that reserve stops before the first call. The reserve is the locked #3 reserve. It is not a new price and it is not raised here.

Locked off-peak card, used only as the spend stop: ¥0.02 cache hit, ¥1 cache miss, ¥4 output, per million tokens. Billed-basis T is provider `prompt_tokens` (total input). Cache tokens are not subtracted and are not a price-weighted substitute for T.

Generation model: `deepseek-flash`, version DeepSeek-V4.1-Flash-1017, thinking `disabled`. The key is `DEEPSEEK_API_KEY` in the environment. Generation under the handler alias `DeepSeek-V3.2-Exp-FC` is refused. Scoring uses `python -m bfcl_eval evaluate` on saved outputs, with that alias only as the pinned BFCL decoder directory. The evaluate command does not generate.

Replace `PATH_TO_GORILLA` with a checkout of gorilla `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`. Run from this repository after `pip install -e ".[test]"`.

Plan only, no provider call:

```bash
python -m tool_compression exploratory-flight \
  --setting H50 \
  --ceiling-cny "$EXPLORATORY_CEILING_CNY" \
  --audit evidence/exploratory/audit.json \
  --bfcl-root PATH_TO_GORILLA \
  --out artifacts/exploratory-flight/H50
```

Live flight, after a ceiling is authorized. Repeat with `--setting H25` and a separate `--out` directory. H25 sends the same three catalogues.

```bash
python -m tool_compression exploratory-flight \
  --setting H50 \
  --ceiling-cny "$EXPLORATORY_CEILING_CNY" \
  --audit evidence/exploratory/audit.json \
  --bfcl-root PATH_TO_GORILLA \
  --out artifacts/exploratory-flight/H50 \
  --live
```

Score the saved outputs of a finished live run. This command does not generate:

```bash
python -m tool_compression exploratory-flight \
  --setting H50 \
  --bfcl-root PATH_TO_GORILLA \
  --out artifacts/exploratory-flight/H50 \
  --score
```

Re-run the offline audit with:

```bash
python -m tool_compression exploratory-audit \
  --bfcl-root PATH_TO_GORILLA \
  --out evidence/exploratory
```

## Reading a later result

Local sums above are not provider T. Accuracy against the historical U 186/200 draw is a different stochastic draw. Historical L is the closed baseline. E is out of scope and is not re-flown. A later hit or miss at r=0.50 or r=0.25 does not revise the official C versus U result, and it does not lower the 10% target. Cursor Approval is not merge authority.
