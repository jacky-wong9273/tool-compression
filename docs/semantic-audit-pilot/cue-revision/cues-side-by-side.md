# Old and new cues

The old cue is the sealed first-pilot string. The new cue is the cue-revision string. An empty cue is no cue: X stays U and SX stays S. The new string is appended to the original function description for X and to the frozen S function description for SX, with one space and no other change.

A shorter string is not a successful contrast. The review question for every pair is: could both descriptions be true of the same request, and if so, does this cue still help the reader choose?

## multiple_35 — revised

One rival. The distinction is the quantity, LCM versus GCD. The shared inputs, two integers, stay in the original description and are not repeated.

### t0 `calculate_lcm`

- Old cue: Unlike calculate_gcd, which calculates the greatest common divisor (gcd) between two integers, this calculates the least common multiple (lcm) between two integers.
- New cue: Unlike calculate_gcd, which is the greatest common divisor, this is the least common multiple.
- Rival: `calculate_gcd`
- Axis: which two-integer quantity is calculated
- Why this rival: Only one other tool, and it states the other quantity.
- Same request: both descriptions can fit = false; cue still helps = true; unsupported exclusion = false.
- A request for the least common multiple does not make the greatest-common-divisor description true. The cue names that quantity difference and does not say either tool rejects integers.

### t1 `calculate_gcd`

- Old cue: Unlike calculate_lcm, which calculates the least common multiple (lcm) between two integers, this calculates the greatest common divisor (gcd) between two integers.
- New cue: Unlike calculate_lcm, which is the least common multiple, this is the greatest common divisor.
- Rival: `calculate_lcm`
- Axis: which two-integer quantity is calculated
- Why this rival: Only one other tool.
- Same request: both descriptions can fit = false; cue still helps = true; unsupported exclusion = false.
- A request for the greatest common divisor does not make the least-common-multiple description true.

## multiple_0 — revised

One rival. Area is named by both descriptions, so the cue states the required measurement only: three side lengths versus a radius.

### t0 `triangle_properties_get`

- Old cue: Unlike circle_properties_get, which retrieves the dimensions, such as area and circumference, of a circle if radius is given, this retrieves the dimensions, such as area and perimeter, of a triangle if lengths of three sides are given.
- New cue: Unlike circle_properties_get, which takes a radius, this takes the lengths of three sides.
- Rival: `circle_properties_get`
- Axis: figure and the measurement the description requires
- Why this rival: Only one other tool.
- Same request: both descriptions can fit = true; cue still helps = true; unsupported exclusion = false.
- A request for area, which both descriptions name, can fit either description until the figure or the given measurement is known. The cue names three side lengths versus a radius. It does not say the circle tool cannot return angles.

### t1 `circle_properties_get`

- Old cue: Unlike triangle_properties_get, which retrieves the dimensions, such as area and perimeter, of a triangle if lengths of three sides are given, this retrieves the dimensions, such as area and circumference, of a circle if radius is given.
- New cue: Unlike triangle_properties_get, which takes the lengths of three sides, this takes a radius.
- Rival: `triangle_properties_get`
- Axis: figure and the measurement the description requires
- Why this rival: Only one other tool.
- Same request: both descriptions can fit = true; cue still helps = true; unsupported exclusion = false.
- Both descriptions can fit an area request. The cue still separates a radius from three side lengths.

## multiple_11 — revised

The first-pilot contrast of polynomial with quadratic as equation classes is not reused. A quadratic is a polynomial, so that juxtaposition can imply an exclusion the sources do not support. Quadratic versus cubic remains a real class difference. The cues use the documented argument shape: three named coefficients, four named coefficients, or one highest-degree-first array.

### t0 `math_roots_quadratic`

- Old cue: Unlike math_roots_cubic, which calculates the roots of a cubic equation, this calculates the roots of a quadratic equation.
- New cue: Unlike math_roots_cubic, which takes four separate coefficients of a cubic, this takes three separate coefficients of a quadratic.
- Rival: `math_roots_cubic`
- Axis: how the coefficients of one fixed-degree equation are supplied
- Why this rival: Cubic is the closer resource: separate named coefficients of one fixed degree. The polynomial tool takes an array. Catalogue order is not needed once that resource difference is used. A cubic is not a quadratic, so this pair does not have the polynomial failure mode.
- Same request: both descriptions can fit = false; cue still helps = true; unsupported exclusion = false.
- A quadratic equation and a cubic equation are not the same request. The cue names the length of the coefficient list. It does not say the polynomial tool cannot take a quadratic.

### t1 `math_roots_cubic`

- Old cue: Unlike math_roots_quadratic, which calculates the roots of a quadratic equation, this calculates the roots of a cubic equation.
- New cue: Unlike math_roots_quadratic, which takes three separate coefficients of a quadratic, this takes four separate coefficients of a cubic.
- Rival: `math_roots_quadratic`
- Axis: how the coefficients of one fixed-degree equation are supplied
- Why this rival: Quadratic is the other fixed-degree named-coefficient tool, and it is earlier than the polynomial tool.
- Same request: both descriptions can fit = false; cue still helps = true; unsupported exclusion = false.
- A cubic request does not make the quadratic description true. The cue does not say this tool is the only cubic solver.

### t2 `math_roots_polynomial`

- Old cue: Unlike math_roots_quadratic, which calculates the roots of a quadratic equation, this calculates the roots of a polynomial equation.
- New cue: Unlike math_roots_quadratic, which takes separate a, b, and c arguments, this takes a coefficient array in highest-degree-first order.
- Rival: `math_roots_quadratic`
- Axis: coefficient array versus separate a, b, and c arguments
- Why this rival: Quadratic and cubic both take separate named coefficients, so both differ from the array on this axis. The tie breaks by catalogue order: the quadratic tool is earlier. The cue uses that argument-shape difference and does not treat polynomial and quadratic as mutually exclusive classes.
- Same request: both descriptions can fit = true; cue still helps = true; unsupported exclusion = false.
- A request for the roots of a quadratic can make both the quadratic description and the polynomial description true. The cue still helps: separate a, b, and c versus one coefficient array in highest-degree-first order. It does not say the array tool excludes quadratics.

## multiple_12 — revised

The cues keep one input distinction and do not restate both calculations. For ROE versus ROA the distinction is the base of the return: average shareholder equity versus total average assets. Net income is shared and stays on the parameters.

### t0 `corporate_finance_calculate_YOY_growth_rate`

- Old cue: Unlike financial_ratios_calculate_ROE, which calculates the return on equity (ROE) for a company from net income for the period and average shareholder equity for the period, this calculates the year over year (YOY) growth rate for a company from revenue for an initial year and revenue for a subsequent year.
- New cue: Unlike financial_ratios_calculate_ROE, which uses net income and average shareholder equity, this uses revenue from an initial year and a subsequent year.
- Rival: `financial_ratios_calculate_ROE`
- Axis: revenue growth across two years versus a return on equity
- Why this rival: ROE and ROA are similarly far from a revenue growth rate. ROE is the earlier of those two.
- Same request: both descriptions can fit = true; cue still helps = true; unsupported exclusion = false.
- A request that only asks how a company changed can be read as year-over-year revenue growth or as return on equity. The cue names the inputs that differ. It does not invent a growth formula.

### t1 `financial_ratios_calculate_ROE`

- Old cue: Unlike financial_ratios_calculate_ROA, which calculates the return on assets (ROA) for a company from net income for the period and total average assets for the period, this calculates the return on equity (ROE) for a company from net income for the period and average shareholder equity for the period.
- New cue: Unlike financial_ratios_calculate_ROA, whose denominator is total average assets, this uses average shareholder equity as its denominator.
- Rival: `financial_ratios_calculate_ROA`
- Axis: which figure is the base of the return
- Why this rival: ROA is the same kind of return ratio. The growth-rate tool is a weaker rival.
- Same request: both descriptions can fit = true; cue still helps = true; unsupported exclusion = false.
- A request for a company's return, without saying equity or assets, can fit both descriptions. The cue names the documented base. Denominator paraphrases return on plus that base. The sources do not write an arithmetic operator.

### t2 `financial_ratios_calculate_ROA`

- Old cue: Unlike financial_ratios_calculate_ROE, which calculates the return on equity (ROE) for a company from net income for the period and average shareholder equity for the period, this calculates the return on assets (ROA) for a company from net income for the period and total average assets for the period.
- New cue: Unlike financial_ratios_calculate_ROE, whose denominator is average shareholder equity, this uses total average assets as its denominator.
- Rival: `financial_ratios_calculate_ROE`
- Axis: which figure is the base of the return
- Why this rival: ROE is the more similar return ratio. Catalogue order is not the reason. ROE does not precede the growth-rate tool; that tool is first in the catalogue.
- Same request: both descriptions can fit = true; cue still helps = true; unsupported exclusion = false.
- The same return request can fit both ratio descriptions. The cue names total average assets versus average shareholder equity and does not say only one tool can take net income.

## multiple_7 — revised

One rival. The cue keeps the verb with the tool that states it: this growth tool assesses growth, and the sibling analyzes impact. Location and period stay in the original sentences.

### t0 `wildlife_population_assess_growth`

- Old cue: Unlike ecological_impact_analyze, which analyzes the impact of a species on a particular ecosystem, this assesses the population growth of a specific species in a specified location over a period.
- New cue: Unlike ecological_impact_analyze, which analyzes impact on a particular ecosystem, this assesses population growth.
- Rival: `ecological_impact_analyze`
- Axis: population growth versus impact on an ecosystem
- Why this rival: Only one other tool.
- Same request: both descriptions can fit = true; cue still helps = true; unsupported exclusion = false.
- A request about a species at a place can fit both descriptions. The cue separates population growth from impact on a particular ecosystem. It does not say the growth tool cannot mention an ecosystem.

### t1 `ecological_impact_analyze`

- Old cue: Unlike wildlife_population_assess_growth, which assesses the population growth of a specific species in a specified location over a period, this analyzes the impact of a species on a particular ecosystem.
- New cue: Unlike wildlife_population_assess_growth, which assesses population growth, this analyzes impact on a particular ecosystem.
- Rival: `wildlife_population_assess_growth`
- Axis: population growth versus impact on an ecosystem
- Why this rival: Only one other tool.
- Same request: both descriptions can fit = true; cue still helps = true; unsupported exclusion = false.
- The same species-and-place request can fit both descriptions. The cue keeps analyzes on this tool and assesses on the growth tool.

## multiple_92 — revised

One distinction, the retailer. The shared lookup is already in each description and is not repeated. The three retailer tools are one cue family in this catalogue, not three trials.

### t0 `safeway_vegan_products`

- Old cue: Unlike wholefoods_vegan_products, which gets available vegan products at specified Whole Foods store, this gets available vegan products at specified Safeway store.
- New cue: Unlike wholefoods_vegan_products, which names a Whole Foods store, this names a Safeway store.
- Rival: `wholefoods_vegan_products`
- Axis: retailer
- Why this rival: Whole Foods and Walmart are the same action on the same kind of resource. Whole Foods is the earlier other tool. The three retailer tools are one cue family in this catalogue, not three trials.
- Same request: both descriptions can fit = true; cue still helps = true; unsupported exclusion = false.
- A request for vegan products in a city can fit every retailer description. The cue names Safeway versus Whole Foods and does not invent a location-format difference.

### t1 `wholefoods_vegan_products`

- Old cue: Unlike safeway_vegan_products, which gets available vegan products at specified Safeway store, this gets available vegan products at specified Whole Foods store.
- New cue: Unlike safeway_vegan_products, which names a Safeway store, this names a Whole Foods store.
- Rival: `safeway_vegan_products`
- Axis: retailer
- Why this rival: Safeway is the earlier other tool. The three retailer tools are one cue family in this catalogue, not three trials.
- Same request: both descriptions can fit = true; cue still helps = true; unsupported exclusion = false.
- The same city request can fit both store descriptions. The cue names the retailer.

### t2 `walmart_vegan_products`

- Old cue: Unlike safeway_vegan_products, which gets available vegan products at specified Safeway store, this gets available vegan products at specified Walmart store.
- New cue: Unlike safeway_vegan_products, which names a Safeway store, this names a Walmart store.
- Rival: `safeway_vegan_products`
- Axis: retailer
- Why this rival: Safeway and Whole Foods both qualify. Safeway is earlier. The three retailer tools are one cue family in this catalogue, not three trials.
- Same request: both descriptions can fit = true; cue still helps = true; unsupported exclusion = false.
- The same city request can fit the Walmart description and the Safeway description. One family with the other two tools.

## multiple_153 — no cue / unchanged

No pair plausibly answers a similar need. Tallest mountains within a radius, entropy change for an isothermal reversible process, and the date of a historical event are different tasks. A shared parameter name, location, does not make the actions confusable. No cue is added. X stays U and SX stays S.

### t0 `locate_tallest_mountains`

- Old cue: no cue / unchanged
- New cue: no cue / unchanged
- Reason: No pair plausibly answers a similar need. Tallest mountains within a radius, entropy change for an isothermal reversible process, and the date of a historical event are different tasks. A shared parameter name, location, does not make the actions confusable. No cue is added. X stays U and SX stays S.

### t1 `calculate_entropy_change`

- Old cue: no cue / unchanged
- New cue: no cue / unchanged
- Reason: No pair plausibly answers a similar need. Tallest mountains within a radius, entropy change for an isothermal reversible process, and the date of a historical event are different tasks. A shared parameter name, location, does not make the actions confusable. No cue is added. X stays U and SX stays S.

### t2 `get_event_date`

- Old cue: no cue / unchanged
- New cue: no cue / unchanged
- Reason: No pair plausibly answers a similar need. Tallest mountains within a radius, entropy change for an isothermal reversible process, and the date of a historical event are different tasks. A shared parameter name, location, does not make the actions confusable. No cue is added. X stays U and SX stays S.

## multiple_100 — no cue / unchanged

No pair plausibly answers a similar need. A music scale progression and the highest common factor of two numbers do not compete for the same request. No cue is added.

### t0 `music_generator_generate_scale_progression`

- Old cue: no cue / unchanged
- New cue: no cue / unchanged
- Reason: No pair plausibly answers a similar need. A music scale progression and the highest common factor of two numbers do not compete for the same request. No cue is added.

### t1 `math_hcf`

- Old cue: no cue / unchanged
- New cue: no cue / unchanged
- Reason: No pair plausibly answers a similar need. A music scale progression and the highest common factor of two numbers do not compete for the same request. No cue is added.

## simple_python_175 — no cue / unchanged

The catalogue has one tool, so there is no rival. X stays U and SX stays S.

### t0 `lawyer_get_experience`

- Old cue: no cue / unchanged
- New cue: no cue / unchanged
- Reason: The catalogue has one tool, so there is no rival. X stays U and SX stays S.

## simple_python_34 — no cue / unchanged

The catalogue has one tool, so there is no rival. X stays U and SX stays S.

### t0 `travel_itinerary_generator`

- Old cue: no cue / unchanged
- New cue: no cue / unchanged
- Reason: The catalogue has one tool, so there is no rival. X stays U and SX stays S.

## irrelevance_59 — no cue / unchanged

The catalogue has one tool, so there is no rival. X stays U and SX stays S.

### t0 `linear_equation_solver`

- Old cue: no cue / unchanged
- New cue: no cue / unchanged
- Reason: The catalogue has one tool, so there is no rival. X stays U and SX stays S.

## irrelevance_50 — no cue / unchanged

The catalogue has one tool, so there is no rival. X stays U and SX stays S.

### t0 `convert_celsius_to_fahrenheit`

- Old cue: no cue / unchanged
- New cue: no cue / unchanged
- Reason: The catalogue has one tool, so there is no rival. X stays U and SX stays S.
