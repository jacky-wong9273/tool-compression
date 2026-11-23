# Outcome-blind reread

This is a self-review by the same editor who wrote the cues. It is not an independent validation. The cues and the rendered catalogues were already sealed. This reread used the original converted descriptions, their schemas, and the new cues. It did not use token deltas. Those counts were recorded only after this note.

The reread is the same sitting as the cue draft. There was no later sitting. A delay was not available in this run, and none is claimed.

The question on every cued pair was: could both descriptions be true of the same request, and if so, does the cue still help the reader choose? The reread also asked whether the cue implies an exclusion the sources do not support, and whether shortening dropped a hint that could guide an argument even when that hint was not a requirement.

## multiple_11, the failure mode the revision had to fix

The sealed polynomial description now reads: calculate the roots of a polynomial equation, unlike `math_roots_quadratic`, which takes separate `a`, `b`, and `c` arguments; this tool takes a coefficient array in highest-degree-first order.

A request for the roots of a quadratic can make both descriptions true, because a quadratic is a polynomial. The first-pilot cue answered that pair by opposing "polynomial equation" to "quadratic equation". Neither description was misquoted, and the juxtaposition can still be read as an exclusion the sources do not state. The new cue does not say that. It names the call shape both schemas document: three separate arguments versus one array whose description starts from the highest-degree term. That still helps a reader who has one of those two inputs.

Residual, accepted under the one-rival rule: a cubic is also a polynomial, and the cubic tool's cue names the quadratic tool, not the polynomial tool. Neither new cue states the cubic-versus-array pair. The polynomial cue therefore does not warn a reader who has four named cubic coefficients. That is a missing comparison, not an exclusion invented by the cue.

Quadratic versus cubic is a different pair. A quadratic equation is not a cubic equation, so those two descriptions are not both true of one equation. The new cues keep that class and add the documented list length, three named coefficients versus four. They do not say the polynomial tool cannot take either equation.

What the shortening does not carry: quadratic `a` is the second-degree coefficient, and cubic `a` is the third-degree coefficient. Those sentences remain on the parameter descriptions. The first-pilot cue did not carry them either, so this is not a hint the revision deleted. It is still a way to mis-align arguments if a reader treats `a`, `b`, and `c` as the same roles on both tools. The same-sitting reread cannot show that a later reader will not do that.

The polynomial `degree` parameter, default 0, stays out of the cue. It is not the selection axis, and the default was not used as a contrast.

## multiple_12

ROE and ROA can both fit a request that asks for a company's return and does not name the base. The new cues name that base and stop there: average shareholder equity versus total average assets. They do not restate net income, the company, or the whole calculation.

"Denominator" is a paraphrase of "return on" plus the figure the matching parameter names. Neither description writes an arithmetic operator. The paraphrase does not add a unit or a second base. It also does not say that only one tool may take net income. Net income remains on both parameter descriptions. Dropping it from the cue removes a repeated argument hint that the first-pilot cue had copied into the function description. The hint is still in the request, on the parameter. Whether a reader who leans on the function description will miss it is the same kind of unsettled question as an omitted example. This reread does not treat the omission as a lost selection fact, and it does not treat it as proved harmless.

The growth-rate cue names the inputs that differ from ROE: net income and average shareholder equity, versus revenue from an initial year and a subsequent year. It does not invent a growth formula. The original description still says year-over-year growth. ROE remains the rival because it is the nearer return ratio only in the sense that ROA is the nearer rival of ROE; for the growth tool, ROE and ROA are similarly far, and ROE is the earlier of those two. The ROA cue's own rationale no longer says that ROE precedes the growth-rate tool.

## multiple_35, multiple_0, multiple_7, multiple_92

LCM and GCD are not both true of one quantity request. The cue names the other quantity and drops the repeated "between two integers" and the repeated verb. Both remain in the original sentence, which the cue does not replace. The parenthetical abbreviations remain there too.

Triangle and circle descriptions can both fit an area request. The cue names three side lengths versus a radius. Perimeter, circumference, and area remain in the original sentences. The cue does not say the circle tool cannot return angles, and it does not say only one tool returns area.

A species-at-a-place request can fit both ecology tools. The cue keeps the verbs where the original sentences put them: the growth tool assesses population growth, and the sibling analyzes impact on a particular ecosystem. Location and period remain in the original growth sentence. The cue does not use a default timeframe, and it does not say the growth tool cannot mention an ecosystem.

A vegan-products request that names a city and no retailer can fit all three store tools. Each cue names the retailer and one earlier rival. The shared lookup is left in the original sentence. The cues do not say that only one tool accepts a city and state. The three tools remain one family. The original retailer sentences have no final period, so the appended cue continues the sentence. That join is the required separator. It is not a new claim.

## Cases left uncued

`multiple_153` and `multiple_100` still have no pair that plausibly answers a similar need. A shared parameter name is not a rival. The four one-tool catalogues still have no rival. No cue was added to manufacture coverage. New X stays U and new SX stays S on those six catalogues.

## Argument hint the revision does not reopen

In `simple_python_175`, the sealed S text removes `eg. Bankruptcy` from the law-type description. The schema has no enum and no replacement example. This pass does not edit S, so the example is still absent. An example can guide an argument even when it is not a requirement. The editor marked that omission as illustrative rather than as a lost inventoried claim. That marking is not the same as a finding that all information was preserved. This same-sitting reread cannot settle whether the missing example changes a later argument.

## Result of the reread

No sealed cue was rewritten after this reading. The polynomial cue no longer uses the misleading class exclusion. The ROE and ROA cues name the base and not the whole calculation. The ecology verbs sit on the tools that state them. The uncued catalogues stay uncued. The remaining limits are the cubic-versus-array pair that the one-rival rule does not name, the unstated arithmetic operator behind "denominator", the coefficient roles that stay only on the parameters, and the bankruptcy example, which this pass leaves in its sealed S form.
