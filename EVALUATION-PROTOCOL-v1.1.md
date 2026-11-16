# Evaluation Protocol v1.1: Native Tool-Description Compression

**Uncompressed input, shared local output, and the external comparator**

- Date: 16 November 2026, Asia/Hong_Kong.
- Basis: Astra’s review of the same date, checked against the Week 1 evidence packet on [tool-compression #1](https://github.com/jacky-wong9273/tool-compression/pull/1) tip [`56982af4`](https://github.com/jacky-wong9273/tool-compression/blob/56982af4d307be7c65d26cc43c40389a4af31fe3/evidence/WEEK1_EVIDENCE_PACKET.md).
- This is the next version of the continuing implementation and evaluation plan. It is not a new go/narrow/stop gate, and it is not permission to resume a halted project.

This version incorporates the Week 1 characterization into the continuing implementation and evaluation plan. At the audited configuration, P, I, and C produce identical transformed requests. Their implementation traces remain separate, while equivalent requests share model responses. The empirical evaluation therefore compares uncompressed input, the shared local output, and the external comparator.

## 1. Evaluation update

The original categories, algorithms, comparator, and denominators remain. Identical-request sharing was already part of the revised proposal. This version consolidates execution and clarifies interpretation; it is not a substantial narrowing of research scope.

**L** denotes the common local output produced by P (protected-prefix), I (independent extraction), and C (I plus neighbour-relative lexical distinctiveness) on the audited inputs at the pinned configuration. It is a reporting label, rather than a new compressor or a selected winning method. That equivalence concerns transformed requests at this setting, not general algorithmic equivalence or an accuracy evaluation already completed.

The Week 1 measurements and historical recommendation remain unchanged. This evaluation plan adopts a different forward interpretation: inactive contrast is a reported finding, while the remaining compression comparisons continue.

The empirical evaluation compares:

- U (uncompressed input);
- L (the shared local output of P, I, and C at the audited setting);
- E (the pinned external comparator, TSCG `compressDescriptions`, at its own operating point).

## 2. What is preserved

- The Week 1 evidence packet remains the historical record, including inactive contrast (`f = 0/200` on the primary category), P≠I = 0, C≠I = 0, the suffix-only versus other-change split, local token ratios, and E’s boundary-compatible integration. Do not rewrite those findings.
- Pins stay as in that packet: BFCL / gorilla `6ea57973`, TSCG `dfcba63` / `@tscg/core` 1.4.3, conversion and handler path as recorded. Settings stay at the values actually tested: `r = 0.75`, Jaccard at least 1/5, at most two neighbours, and `λ = 1/2`.
- Full original categories and denominators stay: primary `multiple` (200) and controls `simple_python` (400) and `irrelevance` (240). Do not replace the primary denominator with the 36 cases that had description changes other than the handler float suffix.
- P, I, and C may keep separate implementation labels and traces. Wherever their complete requests coincide, they share outcomes and are reported as L.

## 3. Observed equivalence and selection constraints

On the primary set, 1,625 of 2,101 description fields contain a single span. The protected-only rendering retains about 94.3% of the original description-field tokens (budget tokenizer: protected-only `p = 23,498` of `d = 24,924`). Of 198 fields with optional content, 196 retain none of that optional content.

The observed equivalence of P, I, and C at this setting is established. The span and protection statistics provide a plausible explanation: the observed span structure, protection floors, and field budgets leave little opportunity for differences in ranking to change the selected text. This does **not** establish that lexical distinctiveness is generally ineffective, or that description compression has no useful potential.

Do not increase the contrast weight, retune `r` or `λ`, relax protections, or lower the cap merely to manufacture differences. No additional suffix-control arm is needed for this modest study.

## 4. Remaining questions

A comparison remains, but its expected practical payoff is modest. On the primary set, E changes 149 of 200 requests, with a local request-token saving of about 0.47% (`o200k_base` ratio of means `0.004713`). The shared local output saves about 1.95% (`0.01945`). These are local estimates, not provider usage. E’s successful integration shows that the external comparison is feasible; it does not show that it delivers useful savings.

The study should still answer, honestly and at this setting:

- Do these actual removals affect official accuracy?
- How do local estimates relate to provider-reported input usage?
- What preprocessing-time, request-latency, provider-usage, and billing tradeoffs accompany the observed compression under the stated execution conditions?
- How are transformations and observed outcome differences distributed across suffix-only, other-change, and unchanged local cases, and how do these patterns relate to protection and span structure?

The last two are descriptive analyses. They do not isolate the causal contribution of each text component. CPU time, latency, input tokens, cached input, output tokens, and retry charges can be reported separately. Any combined economic conclusion needs explicit assumptions.

The handler float suffix (`This is a float type value.`) needs inspection of what information it carries after conversion. Handler-generated text is neither automatically harmless nor automatically necessary.

A valid comparison is not necessarily a highly informative one. Small interventions may produce few accuracy disagreements and leave substantial uncertainty. Report that limitation rather than overclaiming.

## 5. Target

The original reference comparison remains C versus U at \( r = 0.75 \). Where the local requests coincide, C is represented by L. E versus U is reported separately at E’s pinned operating point. E is not an alternative way to pass the original C–U target.

Keep the original practical utility target as stated: at least 10% reduction in mean actual provider total input tokens and at most 2 percentage points of observed official accuracy loss, C versus U, full primary category. Define the token saving as the ratio of cohort means

$$
S_{LU}=\frac{\bar{T}_U-\bar{T}_L}{\bar{T}_U},
$$

where \( T \) is actual provider-reported total input usage over the same full primary cohort.

- This is a ratio of cohort means, not an average of per-case percentage reductions.
- Incomplete usage coverage leaves full-cohort target attainment unresolved.
- The two-percentage-point accuracy margin is an observed descriptive target, not statistical evidence of non-inferiority.

The local evidence gives little reason to expect these configurations to reach the token target, but it is not a provider-level impossibility proof. The target stays unverified until provider usage is measured. Retain the target and report whether it was reached. Do not lower it in order to declare success. The research question is the measured tradeoff, not whether a preferred threshold can be rescued.

## 6. Execution

Retain the full original categories and report U, L, and E. Exact matching requests across all conditions—including U and E—share one response within the same case and replicate. Reused outcomes remain linked to their originating request group and are not counted as independent observations. Request identity includes the model, messages, catalogue, and provider options. Recheck identity after the real model configuration is selected.

Accuracy comparisons use the unchanged official evaluator and paired case-level outcomes, with repeated observations and cross-case dependence addressed in the recorded uncertainty analysis. Technical failures and missing usage remain explicit.

Under the packet’s hashes, with the model still unselected, the provisional unique request-group counts per replicate are 438 on the primary category and 1,513 across all three categories. Actual API attempts can differ because of retries and failures. These figures remain subject to the final model and request configuration.

The selected model, options, replicate count, failure policy, and analysis configuration belong in the execution record before inference begins. Inspecting generated answers already exposes outcomes; waiting until formal scoring is too late for that distinction.

## 7. Package scope

Concentrate the reusable work on:

- a description-only adapter and structural validation;
- interchangeable compression implementations;
- exact-request grouping;
- provider-usage accounting and reproducible evaluation.

Do not spend further effort polishing three selectors whose outputs currently coincide into an elaborate framework. The likely contribution is a modest, setting-specific study and a reusable evaluation package, not a demonstrated compression improvement. The value comes from connecting the selection bottleneck already measured in Week 1 to actual accuracy, provider accounting, external-comparator behaviour, and implementation overhead.

## 8. Document correction

The revised proposal’s Prepared-Input Characterization treats zero contrast activity as something to investigate through its causes and its relationship to the observed tradeoffs, and says that characterization accompanies implementation and official evaluation. Model Execution and Official Outcomes already specifies that identical requests share one response, including when all arms coincide.

The older agent-plan handoff still tells the agent to return a go/narrow/stop packet and stop before further work. That gate was followed for Week 1 and should stay visible as history. Going forward, amend the handoff so it no longer reads as a blanket end to implementation, evaluation, and reporting when contrast is inactive. Align it with the revised proposal and with this protocol. Do not alter the historical Week 1 packet.

## 9. Reference configuration and corrections

The audited algorithm and parameter settings remain the reference configuration. Corrections needed to implement that specification accurately are versioned, with affected preparation outputs regenerated and differences documented. This preserves reproducibility without freezing a genuine implementation defect. It does not invite a new parameter search.

Do not start LLMLingua2 or any second compressor project.
