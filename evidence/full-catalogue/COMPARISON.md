# Exploratory full-catalogue comparison

This comparison is exploratory only. Official C versus U stays the closed result. Official S_LU stays 1398/121018 (about 1.155%). The 10% token target stays 1/10. No provider call was made.

Sample size is 840 cases: multiple 200, simple_python 400, irrelevance 240. The evaluation method is official `bfcl evaluate` on saved outputs. The handler alias `DeepSeek-V3.2-Exp-FC` is scoring-only. A later generation stays `deepseek-flash` with thinking disabled.

## Three measurements

1. Baseline, already collected and not re-flown. r=0.75, λ=1/2, thinking off, DeepSeek-V4.1-Flash-1017. Primary accuracy U 186/200 (93.00%), L 185/200 (92.50%), E 186/200 (93.00%). S_LU = 1398/121018.
2. Setting A. r=0.50, λ=1/2, all 840 cases. Spec `exploratory.a.r50.lambda12.2026-11-23`.
3. Setting B. r=0.75, λ=1/4, all 840 cases. Spec `exploratory.b.r75.lambda14.2026-11-23`. Jaccard stays at least 1/5, the neighbour cap stays at two, and the tokenizer stays `o200k_base`.

H25 (r=0.25, λ=1/2) stays on the #7 audit. These measurements are the closed baseline, setting A, and setting B.

## Request identity

### Setting A

P, I, and C coincide on 840 of 840 cases. Cases identical to U: 586. Cases identical to official L: 837. Cases different from official L: 3.

Requests that differ from both U and official L: `multiple/multiple_40`, `simple_python/simple_python_99`, `simple_python/simple_python_316`. The full-catalogue plan still lists every case, including the requests identical to official L.

| Category | Cases | Identical to U | Identical to official L | Contrast f | C−I cases | C−I fields |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| multiple | 200 | 111 | 199 | 0/200 | 0 | 0 |
| simple_python | 400 | 320 | 398 | 0/400 | 0 | 0 |
| irrelevance | 240 | 155 | 240 | 0/240 | 0 | 0 |

### Setting B

P, I, and C coincide on 840 of 840 cases. Cases identical to U: 586. Cases identical to official L: 840. Cases different from official L: 0.

Every request is identical to official L. λ stays 1/4, and protections, Jaccard, the neighbour cap, and the tokenizer stay as frozen. The full-catalogue plan still lists every case and does not start a paid call.

| Category | Cases | Identical to U | Identical to official L | Contrast f | C−I cases | C−I fields |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| multiple | 200 | 111 | 200 | 0/200 | 0 | 0 |
| simple_python | 400 | 320 | 400 | 0/400 | 0 | 0 |
| irrelevance | 240 | 155 | 240 | 0/240 | 0 | 0 |

Setting A matches the #7 H50 request hashes on 840 of 840 cases. The flight prepared here is the full 840-case plan. It is separate from the #7 plan, which sends only the cases that differ from official L.

## Token savings

This table is exploratory only. It leaves official S_LU where the closed result put it.

### Official billed basis

Cohort: primary `multiple`, 200 cases. Basis: provider `prompt_tokens`. Cache hits stay in T. Prices stay off T.

- U = 121018
- S_LU = 1398/121018 ≈ 1.155%
- Derived primary L = 119620, from 121018 minus the closed numerator 1398. That subtraction restates the closed ratio. It is not a new measurement.
- Provider T for all 840 cases is absent from the closed figures used here.
- Provider T for setting A is not measured.
- Provider T for setting B is not measured.
- The later 3-case H50 provider figures stay out of this table.

### Local `o200k_base` sums

Local o200k_base sums count the prepared request serialization. Official S_LU uses provider prompt_tokens on the primary cohort. Those denominators differ. Local savings do not revise S_LU.

| Category | U | Official L | A | B |
| --- | ---: | ---: | ---: | ---: |
| multiple | 72135 | 70732 | 70709 | 70732 |
| simple_python | 66596 | 65896 | 65884 | 65896 |
| irrelevance | 38560 | 37596 | 37596 | 37596 |
| all 840 | 177291 | 174224 | 174189 | 174224 |

Local ratio of sums versus U, `(sum U − sum arm) / sum U`:

- official_L, all 840: 3067/177291 ≈ 1.730%
- A, all 840: 3102/177291 ≈ 1.750%
- B, all 840: 3067/177291 ≈ 1.730%
- official_L, primary: 1403/72135 ≈ 1.945%
- A, primary: 1426/72135 ≈ 1.977%
- B, primary: 1403/72135 ≈ 1.945%

Local tokens versus official L, all 840: A removes 35; B removes 0.

## Later live run and scoring

The plan commands require `--ceiling-cny`. The code supplies no ceiling and does not read one from the environment. An operator may pass the remaining authorized amount, ¥48.74670004 of ¥50, as that flag. This package does not pass it.

The locked pre-call reserve stays ¥2.572864. Under the remaining authorized amount that reserve allows 18 calls before the run stops. The plan still lists 840 cases. A stopped run has incomplete coverage, and its partial `prompt_tokens` sum is not a cohort T. This package leaves the reserve unchanged.

Plan only, no provider call. Repeat with `--setting B` and a separate `--out` directory.

```bash
python -m tool_compression full-catalogue-flight \
  --setting A \
  --ceiling-cny "$EXPLORATORY_CEILING_CNY" \
  --audit evidence/full-catalogue/audit.json \
  --bfcl-root PATH_TO_GORILLA \
  --out artifacts/full-catalogue/A
```

A later operator adds `--live` only after exporting `DEEPSEEK_API_KEY` and supplying the ceiling. Thinking stays disabled. Generation under `DeepSeek-V3.2-Exp-FC` is refused.

Score a finished live run from saved outputs. This command does not generate:

```bash
python -m tool_compression full-catalogue-flight \
  --setting A \
  --bfcl-root PATH_TO_GORILLA \
  --out artifacts/full-catalogue/A \
  --score
```

That runs `python -m bfcl_eval evaluate` with `--model DeepSeek-V3.2-Exp-FC` and `--test-category multiple,simple_python,irrelevance`. The alias is the decoder directory for saved outputs.

Add billed-basis T to this same comparison from `flight_summary.json` field `billed_basis_T_prompt_tokens`, and from each saved result row's `input_token_count`. Sum provider `prompt_tokens` on received calls. Keep cache hits in the sum. Leave prices off the sum. Put the figure on the arm that was flown, and name the cohort (primary 200, or all 840, only when coverage is complete). Leave official S_LU unchanged. Leave an unflown arm blank. Leave a partial run out of the cohort ratio.

Re-run the offline audit with:

```bash
python -m tool_compression full-catalogue-audit \
  --bfcl-root PATH_TO_GORILLA \
  --out evidence/full-catalogue
```

