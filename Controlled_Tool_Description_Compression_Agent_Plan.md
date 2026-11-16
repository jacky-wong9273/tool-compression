# A Controlled Study of Tool-Description Compression for Native Function Calling

**Coding-agent implementation plan**  
**Author:** Jacky Wong · **UID:** 3035687479  
**Email:** obwong.jacky@connect.hku.hk  
**Programme:** HKU MSc Computer Science, The University of Hong Kong  
**Companion:** `Controlled_Tool_Description_Compression_Proposal.tex`  
**Evaluation protocol:** `EVALUATION-PROTOCOL-v1.1.md`  
**Operational note:** `OPERATIONAL-NOTE-v1.1.md`

**Status on 16 November 2026:** The Week 1 historical handoff was followed. The stop packet on pull request #1 remains the historical record. Evaluation Protocol v1.1 continues unpaid implementation, evaluation scaffolding, and reporting when contrast is inactive. The current handoff below governs that work. Paid inference is not authorized. The preface immediately below is the plan as first written.

This is a self-contained plan for proposed work, not an implemented package or a completed audit. No full selected-category audit, selected-mode TSCG implementation audit, provider experiment, or accuracy result is claimed. Preserve existing deliverables. This plan does not authorize paid inference or public release; both require the explicit decisions below.

## 1. Project Goal

### Initial instruction to the coding agent

#### Week 1 historical handoff

This instruction was followed. It produced the stop packet recorded on pull request #1. It remains here as history. It is not a current instruction to end implementation, evaluation, and reporting when contrast is inactive.

> Start with the Week 1 audit/prototype, not the finished package. Pin original BFCL `multiple`, `simple_python`, and `irrelevance` inputs and their official conversion/evaluation code. Keep labels outside method development. Build the smallest deterministic P/I/C prototype that produces the intended description-only outputs after the shared conversion; prepare and count actual complete requests for every selected original input. In parallel with that work, inspect and try the selected TSCG `compressDescriptions` mode within the bounded effort below. It is the planned core external comparator, not a late optional extra. Measure short-original versus protection limitations, achieved savings, unchanged/pass-through rates, natural neighbours, and actual C/I request differences. Check structural invariants and the baseline's feasibility. Return a go/narrow/stop evidence packet, including the active fraction, practical-target assessment, comparator decision, unresolved counting limitations, and estimated workload. Then STOP for review before package hardening or any paid inference. Do not force activity, tune on labels, modify benchmark membership, repair the external algorithm, or invent results. Later work requires the recorded scope decision; paid execution additionally requires a frozen protocol, separate authorization, and a spending ceiling.

#### Current handoff (Evaluation Protocol v1.1)

The revised proposal studies zero contrast activity through its causes and its relationship to the observed tradeoffs. That characterization accompanies implementation and official evaluation. Identical complete requests share one response, including when all arms coincide. `EVALUATION-PROTOCOL-v1.1.md` is the scientific protocol. `OPERATIONAL-NOTE-v1.1.md` covers launch and authorization.

Build the modest unpaid package on the Week 1 prototype. Keep the description-only adapter and structural validation. Keep separate implementation traces for P, I, and C. Where those complete requests coincide, report the shared request as L, the reporting label defined by the protocol. Leave the three selectors as they are.

The reference comparison remains C versus U at `r=0.75`. Where the local requests coincide, C is represented by L. Report E versus U separately at E's pinned operating point. An E–U result cannot pass the C–U target. Keep the full denominators: `multiple` 200, `simple_python` 400, and `irrelevance` 240. The 36 other-change cases stay a descriptive split inside that primary denominator.

Scaffold exact-request grouping and provider-usage accounting now. Exact matching requests across U, L, and E share one response within the same case and replicate. Reused outcomes stay linked to that request group. The 10% provider-input target and the 2 percentage-point observed accuracy margin stay as stated. A local token estimate leaves the provider target unresolved. Keep `r`, lambda, the protection cues, and the neighbour limits at the audited values. Paid inference, model selection for execution, replicate count, a spending ceiling, and any rate card require a separate later authorization.

Inspect the information the handler float suffix carries after conversion. Handler-generated text is neither automatically harmless nor automatically necessary. Add no suffix-control arm. Start no second compressor.

### Research questions and estimands

The primary contribution is a **controlled empirical study plus a reusable description-only package**. It is not new theory or a new compression family. Novelty is optional.

1. **Compression opportunity:** How much compression is actually achieved on original native requests, and how much is limited by short originals versus the chosen protection policy?
2. **Practical tradeoffs:** What accuracy–token–overhead tradeoffs do simple and established description-only methods achieve under the same native request and evaluation protocol?
3. **Incremental feature effect:** What changes when a neighbour-relative lexical distinctiveness term is added to an independent selector under shared local rules?

Use U = uncompressed, P = protected-prefix, I = independent extraction, C = I plus neighbour-relative lexical distinctiveness, and E = one pinned existing native description-only comparator. The core is **one native model, one primary local setting, U/P/I/C plus one compatible E operating point**.

- **Primary practical comparison:** C–U at provisional `r=0.75`, on the entire original pinned BFCL `multiple` category.
- **Prespecified secondary feature ablation:** C–I at the same setting. It isolates a feature addition, not equal achieved cost or a token-independent semantic effect.
- **Required tradeoff context:** P, I–U, and E against U/local methods. E is core to the original comparative scope, but is not forced into local caps or protection rules.
- **Controls:** complete original `simple_python` and `irrelevance` categories. Their tasks, candidate lists/order, labels, and official evaluation remain unchanged.
- Extra ratios, balanced repetitions, or another model are secondary, budget-dependent work, decided before scoring. Do not automatically repeat E at every local ratio or choose the best observed setting as primary.

### Targets, completion, and authority

The practical utility **target**, not a promise or completion condition, is **at least 10% reduction in mean actual provider total input tokens and at most 2 percentage points of observed official accuracy loss**, C versus U on the full primary category. At the primary setting, assess actual prepared-request savings before fees. A local proxy is not provider measurement unless matching counting has been established. Meeting the observed margin is not proven non-inferiority.

A completed study needs tested software, the full input audit, completed evaluation within an explicitly approved scope, reproducible analysis, and an honest report. A negative result can complete those objectives. Contrast advantage and novelty are optional. An audit-only stop is a feasibility deliverable, **not completion of the planned model evaluation**, and does not establish course acceptance. If E fails, an approved local-only study must be named as narrower; it is not completion of the original external-comparison scope.

| Fixed scientific commitments | Decide input-only, document, then freeze | Requires explicit scope/budget decision |
|---|---|---|
| Original categories and full denominators; unchanged official evaluator; description-only boundary; shared local rules; I own-tool information; C only adds one term; response sharing within case/replicate | Minimal supported schema profile, segmentation/cues, lexical normalization, ranking details, tokenizer/counting adapter, model/options, external configuration, dependence/uncertainty procedure | Category reduction; target change; dropping/replacing E; negative-study rationale; extra settings/models/repetitions; paid execution and ceiling |

Input-only decisions are not licence to search for settings merely to force C/I differences. Give reasons, preserve audit revisions, and freeze before scoring. No official development split is established: use handcrafted fixtures and label-blind inputs, not public answer snippets or evaluator success signals. Outcome-informed tuning makes affected analysis exploratory.

## 2. Potential Solutions

### Shared boundary and scope

Apply the same pinned official/provider conversion to every arm **before** compression. Retain raw-source and converted-reference hashes. The compressor receives the converted catalogue and configuration, not questions, labels, history, or feedback; the runner adds unchanged messages separately.

Allow edits only to genuine function and parameter-schema description strings reached by an explicit adapter profile. Preserve candidate count/order, names, parameter/schema data, defaults, constraints, unknown metadata, and every non-description request value. An object inside an example/default is not an editable schema merely because it contains a `description` key. Never mutate inputs. Use type- and order-sensitive comparison outside allowlisted strings on every prepared output.

Unsupported inputs have explicit unchanged pass-throughs and remain in denominators. Invalid ingestion or structural violations block execution; do not disguise implementation defects as benign fallback or silently fix source records. A frozen single-sentence field must not freeze the entire catalogue. Structural preservation is necessary but is not semantic fidelity.

Keep local methods query-agnostic, deterministic, extractive, and CPU-based. Exclude training, retrieval, tool deletion/insertion, synthetic distractors, pooled catalogues, new serialization, query-aware expansion, benchmark changes, adaptive cross-tool allocation, and history/result/memory compression. No GPU or agent framework is required for the local package.

### Minimal local specification to produce in Week 1

Write a short versioned specification alongside the prototype; do not recreate an exhaustive parser/configuration contract. It must make the following choices reproducible:

- Conservative whole sentence/newline units, source offsets, and rendering in original order. Local P/I/C retain exact source spans with documented joining whitespace, not paraphrases. Return original text when unchanged/all units retained.
- Shared protection of the first unit and recognizable constraint-bearing units: for example negation, conditions, units, defaults, and important literals. Choose precise cues and segmentation from input-only inspection; document uncertain-language/segmentation handling. Protecting prose heuristically does not prove it is safe to remove the rest.
- Common field caps, complete-rendering token checks, deterministic ties, and explicit pass-through/freeze reasons.
- I's own-tool position/frequency features and C's sole neighbour-rarity addition. Neighbours and features come from original catalogues, not questions or previously compressed text.

A feasible initial selector is below. These details are **provisional engineering choices** to verify label-blind, not additional immutable scientific claims:

```text
I: average a source-position preference with normalized own-tool unigram frequency.
Neighbours: Jaccard overlap of original description and function/property-name unigrams.
q_i(u): average, over unit unigram/bigram features, of the fraction of neighbours
        in whose original descriptions that feature is absent; zero if none.
C: s_C(u) = s_I(u) + lambda * q_i(u).
```

P starts with all protected units, adds optional units in source order, and stops at the first that does not fit. I/C start with the same protected units, rank optional units by score per token with stable source-order ties, and skip oversized units while continuing. Accept only whole units after re-tokenizing the complete proposed field rendering. Output remains in source order. Do not transfer unused caps between fields or tools. Zero contrast weight, or no neighbours for a tool, must reproduce I's local selections under identical rules; diagnostic timing/method labels need not be identical.

### Compact provisional settings and accounting

| Setting | Starting choice / status |
|---|---|
| Primary retained cap | `r=0.75` |
| Exploratory retained caps | `0.50`, `0.25`; not automatic core runs |
| Natural neighbours | Jaccard `>=0.2`, at most `2`, stable catalogue-order ties |
| Contrast weight | `lambda=0.5` |
| Inference | One model; one logical completion per case/condition initially |
| External comparator | TSCG `compressDescriptions`, one pinned compatible configuration |
| Utility target | Mean actual provider total-input reduction `>=10%`; observed C–U loss `<=2 pp` |
| Unresolved before execution | Exact data/code versions, model/options, tokenizer/counting method, external version/settings, uncertainty method, rates, approval and ceiling |

For an original description with count `d_j` and protected-only rendering count `p_j`, use nominal cap `floor(r*d_j)` and shared effective cap `b_j=max(floor(r*d_j),p_j)` when `p_j<=d_j`. Otherwise freeze that field at its original form and count. Preserve empty/whitespace-only fields explicitly. Every supported successful output must meet its effective cap; report nominal attainment, uplift, frozen fields, and achieved counts separately.

`r` is an upper retained cap subject to protection-floor uplift, **not an exact retained fraction**. Whole-span selection can retain less; protection can require more. Do not use `0.25 * description share` as a hard maximum saving at `r=0.75`. Re-tokenize complete candidate renderings; summed span costs are not sufficient. Field-token sums are not additive provider totals. The protected-only request is a policy diagnostic, not a proven global minimum. Count actual prepared full requests, labelling local estimates and their limitations. Never claim provider saving or impossibility from an unmatched local counter. U must fit the chosen context with output reserve; do not silently truncate anything to make it fit.

### External baseline integration boundary

Prioritize TSCG's native `compressDescriptions`, not its text-format compiler. In Week 1, time-box the initial selected-mode check to **one working day**. Read that entry point and invoked edit logic; inspect actual output format/edits, immutable compatibility, dependencies, own policy, runtime, and preprocessing costs. No whole-repository audit is required. Pin the release/commit and configuration and run it locally on fixtures and selected inputs when feasible. Documentation of native mode is not proof its implementation meets this boundary, and text-format headline results are not native-mode evidence.

Keep E's original algorithm/protection policy. A Python-to-other-runtime wrapper may transport inputs/outputs but must not rewrite E to mimic local caps or repair incompatible output. Never remove violations and report the result as the unchanged external method. Audit achieved tokens and accuracy at E's operating point without claiming equal-cap/equal-cost matching. Record initialization and recurring costs; no training or paid compressor calls are authorized.

If TSCG is unavailable/incompatible, LLMLingua2 is a **predeclared fallback possibility only if practical** within the same bounded effort/resource constraints. Record the substitution and configuration decision before scoring; do not start a second open-ended method project. If no compatible E is practical, report evidence and request explicit narrowing to local ablation/feasibility. A rejected/unsupported mode is not a measured competitive result.

### Suggested package shape, not a prescribed module tree

A pure function such as `compress(catalogue, method, ratio, config)` should return a new catalogue plus edit traces, token/cap diagnostics, and supported/unchanged/pass-through status. The exact API names are open. Keep four responsibilities separable: pure local compression; native/counting adapters and external wrapper; preparation/authorized execution; official scoring and analysis. A small Python package with ordinary tests and lockable dependencies is sufficient.

Preserve input hashes, selected offsets, protection/freeze reasons, achieved counts, and versioned configuration. Timing is separate from deterministic-content checks. Add caching only after correctness; its key must include the complete ordered original catalogue, neighbours implicitly included, and algorithm/adapter/tokenizer/configuration versions. It is a compilation cache, not conversational memory. Do not spend Week 1 building a polished CLI, full dataclass hierarchy, or cache service.

## 3. Experimental Plan

### Phase 1 — Week 1: audit prototype and return a decision

**Inputs:** original pinned BFCL `multiple`, `simple_python`, `irrelevance`; official converter/evaluator code; provisional native model/counting configuration; selected external mode. Labels are available only to the later evaluator, not to the compressor or tuning process.

**Work:** map actual inputs, preserve every original ID, and diagnose parse/duplicate problems. Implement enough of the chosen local specification to generate actual P/I/C outputs, not score-only estimates. Prepare complete native U/P/I/C requests for all selected inputs; include E once runnable. Audit the primary setting first; optional local ratio preparation is cheap but any scored sweep still requires scope/budget approval. Check invariants and supported-output caps now without requiring final package engineering.

**Evidence packet:**

- Provenance and full original counts; candidate sizes; genuine description lengths; actual prepared full-request counts per arm, with counting method/coverage.
- Actual compression, unchanged, pass-through, and unsupported rates. Optional-unit counts; first-unit/constraint protection reasons; protected-only costs, floor uplift, and frozen fields.
- Short/single-unit originals versus otherwise optional material retained by protection, including overlap. Do not force these into mutually exclusive causal explanations.
- Natural-neighbour prevalence and input-only name/parameter/schema overlap proxies. Score/ranking changes are supplementary; actual C/I text and complete-request differences are essential.
- External selected-mode compatibility, configuration, actual edits, dependency/resource/preprocessing costs, or documented failure within the effort limit.
- Baseline context feasibility, actual within-case request groups, proposed workload/cost range, target assessment, and unresolved evidence. Do not invent counts before preparing requests.

Define the **active fraction** at the primary setting:

```text
f = number of original multiple cases with distinct COMPLETE C and I requests
    / number of ALL original multiple cases
```

Requests include the same model/provider configuration. With response sharing for identical requests and complete scoring, `abs(observed paired C–I correctness difference) <= f`, since identical pairs contribute zero. This is a simple interpretation bound, not a theorem claim, power calculation, or activity threshold. `f=0` means no contrast efficacy test under that configuration. `f>0` alone does not establish adequate informative scale. Report counts, fraction, dependence, and the expected interpretive limitation; do not invent a minimum f or search settings just to exceed one.

Assess the 10% actual provider-total-input target at `r=0.75` before fees. If counting is only a local estimate, state that the provider target remains unverified, not proved possible/impossible. If evidence leaves the target unsupported, document one of these routes:

1. **Go:** justify a useful full comparison, informative scope, comparator readiness, and realistic cost/accounting assumptions.
2. **Narrow/revise:** explicitly approve and freeze a label-blind scope or target revision, or a bounded negative accuracy study answering a remaining question. Low headroom does not automatically forbid a negative study; zero f cannot test contrast efficacy but can coexist with useful other comparisons.
3. **Stop/review:** explain blockers or inadequate scientific value under current time/resources.

Do not spend merely to test token saving already established as unattainable with matched accounting; do not silently lower the target. **Stop and return this packet for review before hardening.** Any approved revision needs reasons, a new configuration/version, and refreshed affected audit outputs. No paid run is authorized by passing this gate.

That stop was the Week 1 gate, and it was followed. The packet on pull request #1 records it and stays unchanged. Under Evaluation Protocol v1.1, inactive contrast is a reported finding. Unpaid implementation, evaluation scaffolding, and reporting continue under the current handoff. Paid inference remains unauthorized.

### Phase 2 — Week 2: harden only the approved minimal library

**Inputs:** reviewed Phase 1 decision, prototype outputs, short versioned specification, approved E decision.

Evaluation Protocol v1.1 is the scope decision for the unpaid package: the description-only adapter and structural validation, interchangeable local implementations with separate P/I/C traces, exact-request grouping, provider-usage accounting hooks, and reproducible evaluation scaffolding. The protocol leaves `r`, lambda, protections, neighbour limits, and the 10% target at their audited values. It authorizes no paid inference and no second compressor.

**Work:** make the pure transformation reusable and deterministic; finish adapter guards, tracing, token checks, and the minimal external wrapper. Use handcrafted fixtures, not benchmark-answer examples. Preserve prototype outputs under hardening; substantive algorithm changes require a label-blind re-audit and versioned decision.

**Exit evidence:** installable source with pinned dependencies, targeted passing tests, no input mutation/non-description changes/cap violations across supported prepared outputs, and explicit pass-through coverage. Unknown schemas are not a reason to build an unrestricted parser. The compact test checklist below is sufficient to organize coverage without prescribing dozens of bespoke tests.

### Phase 3 — Week 3: evaluator integration and protocol freeze

**Inputs:** hardened package, complete prepared corpus, approved scope, pinned official adapter/evaluator, provisional analysis and cost plan.

**Work:** verify native response parsing and official scoring with fixtures, including irrelevance and missing outputs. Freeze one model/version/options, tokenizer/counting convention, comparator settings, local configuration, ordering, retry policy, and all planned comparisons. Inspect input-derived dependence, then choose and freeze a reasonable paired uncertainty method before scores. Finalize any optional diagnostic sample at this point.

Group identical **complete native requests within the same case and replicate only**; identity includes model/endpoint, messages, ordered tools, and all generation/provider options. Exclude bookkeeping-only method labels. Submit one request per group and attach its single designated response to all logical members. Never reuse across cases or replicates. Contrast-disabled identity is a software check, not another paid arm. Retain every logical condition in analysis while billing each physical attempt once.

Counterbalance condition/group order across cases with a recorded deterministic rule. Freeze concurrency and cache regime; record provider fingerprints and material drift. Use bounded transport retries only (provisionally at most two after the initial attempt), never retries for wrong answers, refusals, or malformed model calls. Retain every attempt and unknown timeout charges. An external preprocessing call, fixture API smoke call, or extra repetition can also cost money: stubs are the default until separately authorized.

**Exit evidence:** immutable run manifest, actual distinct-request workload, fixture-tested scorer/failure behavior, prespecified analysis, verified current rates/output reserve/retry allowance, and an explicit approval ceiling. No presumed matrix size or paid authorization. If the full approved workload is unaffordable, stop for an explicit pre-scoring scope decision rather than selecting convenient cases.

### Phase 4 — Week 4: execute only the authorized scope

**Inputs:** frozen manifest plus explicit paid-inference authorization and spending ceiling.

**Work:** execute original cases in the frozen order, recording complete prepared request hashes, shared logical memberships, response/usage, timestamps, attempts, status, and model fingerprint. Keep labels and scores out of method adjustment. Stop on structural defects, ceiling exhaustion, material backend drift, or systemic failures. Preserve the run boundary rather than pooling incompatible runs silently.

**Exit evidence:** immutable response/attempt ledger and coverage table, or an honest interruption report. A terminal group failure propagates to every equivalent slot. Never fabricate a no-call response for transport missing. Resume according to the frozen policy, not after selecting which answers were poor.

### Phase 5 — Week 5: official scoring and bounded interpretation

**Inputs:** saved responses, original labels, unchanged official scorer, frozen analysis specification.

**Work and required results:**

- Use official AST correctness/category aggregation for `multiple` and `simple_python`. For `irrelevance`, keep the official score and separately show valid no-call responses versus parse/decode failures; the inspected official path may treat malformed calls as abstention. No new judge or replacement correctness metric.
- Show the full original denominator and prepared/supported/unchanged/pass-through/attempted/received/scorer-accepted/missing counts for every arm. Unsupported pass-throughs stay in the full result. Structural errors are blockers, not successful fallbacks.
- If required scorer inputs are missing, report the official result as incomplete. A separate full-cohort operational score assigning terminal technical missing zero is not an official-score repair. Show paired-complete sensitivity and unresolved missingness; do not claim full evaluation from a favourable subset.
- Report achieved description counts, local complete-request estimates, provider total input/cached/output tokens, preprocessing time, latency, retries, and costs separately. Distinguish cold initialization, recurring/cache-hit preprocessing, and API caching. Use measured usage and verified rates; mark unknown charges. Logical deployment usage and physical experiment billing are different ledgers.
- Compute C–U and C–I paired correctness differences and gain/loss counts on the complete original primary category. The 10% provider-input target uses `(mean(total_input_U) - mean(total_input_C)) / mean(total_input_U)` on the same complete cohort with complete U/C usage coverage, **not the mean of per-case relative reductions**. Missing provider usage is never zero-filled or treated as complete: report coverage and any paired-available estimate or local proxy separately; neither establishes full-cohort target attainment.
- Present the fixed-corpus descriptive result first, alongside prespecified uncertainty. Shared exact original tool signatures/duplicate inputs are dependence proxies, not proof of independent families. A paired component bootstrap is a feasible choice if the audited structure supports it; freeze its details before scoring. Explain sparse-component or zero-discordance limitations. Do not automatically assume IID cases, infer equivalence from nonsignificance, or infer non-inferiority from a degenerate interval or the observed 2 pp margin.
- Compare achieved accuracy, token use, and overhead for all arms. Equal local caps do not ensure equal achieved tokens. Output-defined cost strata, if used, are descriptive and cannot establish a token-independent causal effect. Do not pad, trim, or omit cases to manufacture matching. E's own operating point provides context, not an artificial equal-cap ablation.

**Optional input-only review:** a small sample of input/compressed pairs may be reviewed with outcome and method identity blinded where feasible. Freeze sample size/selection/questions before scores and allow an uncertain category. Use name/parameter/schema overlap and natural-neighbour proxies as diagnostics only; do not infer prose necessity from them. Disclose nonrepresentative sampling, and never change primary membership or denominators. This is not a new annotation programme or judge metric.

**Exit evidence:** reproducible official scores, coverage, paired effects/uncertainty, achieved-token/overhead tables, and clearly separated target attainment, inconclusive inference, and optional contrast findings.

### Phase 6 — Week 6: reproduce, package, and report

**Inputs:** versioned source/configurations, gate decisions, frozen manifests, saved outputs, and analysis.

**Work:** replay preparation and scoring/analysis from retained artifacts without new model calls; verify hashes, denominators, and tables. Document API usage, supported profile, pass-through limitations, comparator configuration, installation, and separate preparation/inference/scoring steps. Retain notices and dependency licences encountered; do not assume redistribution rights for every downloaded artifact. Keep credentials out of source/manifests and use authorized retention for responses.

**Exit evidence:** package and tests, minimal specification, original provenance, complete audit, approved scope/deviations, prepared request hashes/traces, response/attempt ledger, official outputs, analysis, and reproducibility guide. The final report distinguishes completed approved evaluation from an audit-only stop, the practical target from project completion, and novelty/contrast advantage from required work. Publication remains subject to scientific review and explicit release approval. Weeks 7–8 are contingency, not automatic expansion.

### Compact testing and reproducibility checklist

These are **planned future tests**, not tests executed by creating this document.

- **Boundary:** allowlisted genuine schema descriptions only; embedded examples/defaults and other values unchanged; type/order preservation; no input mutation; unsupported pass-through versus blocking errors distinguished.
- **Extraction/caps:** exact offsets and source order; first/constraint protection shared; empty/uncertain fields safe; single-sentence field isolation; complete-rendering token checks including non-additive tokenizer behavior; uplift/freeze recorded.
- **Ablation/determinism:** I salience unaffected by rivals; zero-weight/no-neighbour identities; deterministic ties/output; if caching is used, whole-catalogue/config/tokenizer changes invalidate it.
- **External method:** actual native output respects the same invariant; wrapper does not repair/change E policy; dependencies/settings and preprocessing costs recorded.
- **Runner/evaluator:** exact request sharing within case/replicate only; no quality retries; missing status propagation; valid abstention versus parse failure; no double-counted billing or fake official completeness.
- **Analysis/gates:** toy paired arithmetic, denominators and active-fraction bound with complete scoring; missing/zero-discordance cases; provider-versus-proxy accounting; frozen configuration and spending gate block unapproved execution.

Keep one manifest recording source/data/code hashes, original IDs, conversion/scorer versions, algorithm/configuration, tokenizer/counting limits, external version, model/options, request groups/order, analysis choices, scope approvals, rates, and ceiling. Keep per-case preparation and per-physical-attempt ledgers linked by hashes. Do not impose exact dataclasses or nonexistent CLI commands; provide real commands only when the implementation exists. No package tests, inference, compilation, or empirical gains may be claimed without saved evidence.

### Public references for implementation and positioning

Pin actual commits/assets; these discovery URLs are not immutable experiment identifiers.

- BFCL repository: https://github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard
- Category mapping: https://github.com/ShishirPatil/gorilla/blob/main/berkeley-function-call-leaderboard/bfcl_eval/constants/category_mapping.py
- Native adapter: https://github.com/ShishirPatil/gorilla/blob/main/berkeley-function-call-leaderboard/bfcl_eval/model_handler/api_inference/openai_completion.py
- AST checker: https://github.com/ShishirPatil/gorilla/blob/main/berkeley-function-call-leaderboard/bfcl_eval/eval_checker/ast_eval/ast_checker.py
- Evaluation runner: https://github.com/ShishirPatil/gorilla/blob/main/berkeley-function-call-leaderboard/bfcl_eval/eval_checker/eval_runner.py
- TSCG native mode and code: https://github.com/SKZL-AI/tscg ; paper: https://arxiv.org/abs/2605.04107 . Native-mode compatibility is unverified; headline text-format results do not establish it.
- Xu et al., description-only setting, Appendix A.2: https://arxiv.org/html/2407.02043
- LLMLingua/LLMLingua2: https://github.com/microsoft/LLMLingua
- EasyTool, Sections 4.1–4.2 and Limitations: https://arxiv.org/html/2401.06201v3 . Its dependency limitation is not evidence of an implemented rival-aware compressor.
- K. Spärck Jones (1972), “A statistical interpretation of term specificity and its application in retrieval,” *Journal of Documentation* 28(1), 11–21, “Weighting by specificity,” DOI 10.1108/eb026526: https://www.cl.cam.ac.uk/archive/ksj21/ksjdigipapers/jdoc72.pdf
- J. Carbonell and J. Goldstein (1998), “The use of MMR, diversity-based reranking for reordering documents and producing summaries,” SIGIR, Section 2, DOI 10.1145/290941.291025: https://www.cs.cmu.edu/~./jgc/publication/MMR_DiversityBased_Reranking_SIGIR_1998.pdf . MMR uses query relevance and already-selected diversity; the proposed q is fixed neighbour rarity.
