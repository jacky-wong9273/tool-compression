# T1 and T2 flight path

This file prepares a later evaluation flight. It is not a measured result. No provider was called while it was written. Provider `T` for T1 and T2 is null until a later operator stores saved usage.

The compressor is the frozen phrase-level transform in `FOLLOWON-SPECIFICATION.md`. T1 ranks optional pieces with the tool's own vocabulary. T2 adds `1/2 × q` on those same pieces. Nothing in this path retunes the grammar, the weight, the cap, or the protections. It does not implement the official-compressor robustness flights (`r=0.50`, `λ=1/2` and `r=0.75`, `λ=1/4`).

## Reconfirmed audit

On tip `213bba84d008d69edbddf6a20f2555de1c2a374e`, parent `3a02e64888c5359f48d2b417ac659161cd3eadae` (open pull request #4). The committed audit and a re-execution on gorilla `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8` agree:

| Category | Cases | f_new | T1 request equals T2 | T1 and T2 equal U |
| --- | ---: | --- | ---: | ---: |
| multiple | 200 | 0/200 | 200 | 200 |
| simple_python | 400 | 0/400 | 400 | 400 |
| irrelevance | 240 | 0/240 | 240 | 240 |

Flight bodies add `deepseek-flash`, temperature `0.001`, `store` false, and thinking `{"type":"disabled"}` to every arm, including the uncompressed catalogue used only as an identity check. That substitution does not create a T1 or T2 catalogue different from U.

**A later flight would be a same-request re-draw of official U, not a new compressed catalogue.**

The plans still contain all 840 cases for T1 and all 840 cases for T2. Cases are not dropped because they match U. Official U answers are not reused. Official L and E are not sent.

## Closed official baseline

Unchanged, and not a reset test: `S_LU = 1398/121018 ≈ 1.155%`. Primary accuracy U 186/200, L 185/200, E 186/200. The 10% target stays 1/10. Billed-basis `T` is provider `prompt_tokens`. Cache hits are not subtracted. Prices are not applied to `T`. The off-peak card is only the spend stop.

## Ceiling

`EXPLORATORY_CEILING_CNY` is required at run time. The code does not default it. The remaining authorization is ¥48.74670004 of ¥50. A supplied ceiling above that remaining amount is refused. The pre-call reserve stays ¥2.572864 (1,000,000 input tokens at the cache-miss rate plus 393,216 output tokens at the output rate). A ceiling that cannot hold the reserve stops before the first call.

20:00 Asia/Hong_Kong on Monday 23 November 2026 is after the weekday peak windows 09:00–12:00 and 14:00–18:00. The same civil clock is the locked Asia/Shanghai window. A start inside those windows is refused. Do not start this flight before 20:00 HKT today.

## Commands

Install once from this repository:

```bash
pip install -e ".[test]"
```

`PATH_TO_GORILLA` is a checkout of gorilla `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`. These plan commands do not pass `--live` and do not read `DEEPSEEK_API_KEY`.

Separate plans, 840 cases each:

```bash
export EXPLORATORY_CEILING_CNY=48.74670004
python -m tool_compression followon-flight \
  --arm T1 \
  --ceiling-cny "$EXPLORATORY_CEILING_CNY" \
  --bfcl-root PATH_TO_GORILLA \
  --out artifacts/followon-flight/T1
python -m tool_compression followon-flight \
  --arm T2 \
  --ceiling-cny "$EXPLORATORY_CEILING_CNY" \
  --bfcl-root PATH_TO_GORILLA \
  --out artifacts/followon-flight/T2
```

One sequential replicate. Where the T1 and T2 bodies match inside a case, one physical call of this replicate is shared by both arms. That share does not attach an official U answer. Logical assignments stay 1,680.

```bash
python -m tool_compression followon-flight \
  --arm both \
  --sequential \
  --ceiling-cny "$EXPLORATORY_CEILING_CNY" \
  --bfcl-root PATH_TO_GORILLA \
  --out artifacts/followon-flight/sequential
```

Live generation, only after the ceiling is supplied and only at or after 20:00 HKT. Repeat with `--arm T2` and a separate `--out`, or pass `--arm both --sequential` for one replicate. The key is `DEEPSEEK_API_KEY` in the environment. Generation under `DeepSeek-V3.2-Exp-FC` is refused.

```bash
python -m tool_compression followon-flight \
  --arm T1 \
  --ceiling-cny "$EXPLORATORY_CEILING_CNY" \
  --bfcl-root PATH_TO_GORILLA \
  --out artifacts/followon-flight/T1 \
  --live
```

Score saved outputs. This runs `bfcl evaluate` and does not generate. The handler alias is the pinned decoder directory only. Run it once per arm directory.

```bash
python -m tool_compression followon-score \
  --arm T1 \
  --bfcl PATH_TO_BFCL_EXECUTABLE \
  --project-root artifacts/followon-flight/T1
```

`scripts/run_followon_evaluate.sh` is the same evaluate command. An argument equal to `generate` exits before `bfcl` starts. The child process receives the dummy key `UNUSED_OFFICIAL_EVAL_NO_PROVIDER_CALL`.

Write the token comparison against closed official U. Without a usage file the arm cells stay null. Do not copy official U's `prompt_tokens` into T1 or T2.

```bash
python -m tool_compression followon-compare \
  --out artifacts/followon-flight/T1/comparison_versus_official_u.json
```

After a finished live run, pass the saved usage. The file's `arms` object maps each arm to per-category lists of provider `prompt_tokens`, length 200, 400, and 240. Incomplete lists stay unresolved. The report is an exploratory follow-on. It does not revise official C versus U.

```bash
python -m tool_compression followon-compare \
  --usage artifacts/followon-flight/T1/prompt_tokens.json \
  --out artifacts/followon-flight/T1/comparison_versus_official_u.json
```

Re-run the offline reconfirmation, still with no provider call:

```bash
python -m tool_compression followon-reconfirm \
  --bfcl-root PATH_TO_GORILLA \
  --out followon/flight_readiness.json
```

## How to read a later result

Local `o200k_base` sums in the #5 audit are not provider `T`. If the flight bodies still match U, a new `prompt_tokens` total is another draw of the same request, not evidence that phrase compression shortened the catalogue. Compare that draw with closed official U only under the exploratory label. Do not replace `official/settlement/official_settlement.json`. Do not lower the 10% target. Cursor approval is not merge authority.
