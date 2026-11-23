# Fact ledger

Each proposition is one inventoried claim. Spans are character offsets into the original allowlisted description. A duplicate or an illustrative omission is not a lost fact. Cue propositions are traced to the original catalogues, not to the S replacements.

## multiple_35

### t0 `calculate_lcm` `/function/description` (no-op)

- Original: Calculate the least common multiple (lcm) between two integers.
- Replacement: Calculate the least common multiple (lcm) between two integers.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `multiple_35/t0/function/descriptiona` KEEP both statement: [0:63] Calculate the least common multiple (lcm) between two integers.
  Left verbatim.

### t0 `calculate_lcm` `/function/parameters/properties/num1/description` (no-op)

- Original: First number to calculate lcm for.
- Replacement: First number to calculate lcm for.
- Reason: Prose says number. Schema type is integer. Left as written. The field is otherwise unchanged.
- Conflict, left unrepaired: Prose says number. Schema type is integer. Left as written.
- `multiple_35/t0/function/parameters/properties/num1/descriptiona` KEEP use statement: [0:34] First number to calculate lcm for.
  Left verbatim.

### t0 `calculate_lcm` `/function/parameters/properties/num2/description` (no-op)

- Original: Second number to calculate lcm for.
- Replacement: Second number to calculate lcm for.
- Reason: Prose says number. Schema type is integer. Left as written. The field is otherwise unchanged.
- Conflict, left unrepaired: Prose says number. Schema type is integer. Left as written.
- `multiple_35/t0/function/parameters/properties/num2/descriptiona` KEEP use statement: [0:35] Second number to calculate lcm for.
  Left verbatim.

### t0 `calculate_lcm` `/function/parameters/properties/method/description` (CONDENSE)

- Original: The specific method to use in the calculation. Supported values: 'standard', 'reduced'. Default 'standard'
- Replacement: Calculation method. Supported values: 'standard', 'reduced'. Default 'standard'.
- Reason: The purpose clause shortens. The supported literals and the default stay in prose because the schema has neither an enum nor a default.
- `multiple_35/t0/function/parameters/properties/method/descriptiona` CONDENSE use purpose: [0:46] The specific method to use in the calculation.
  Paraphrase of the method used in the calculation.
- `multiple_35/t0/function/parameters/properties/method/descriptionb` KEEP use literal: [47:86] Supported values: 'standard', 'reduced'
  Rejected alternative: dropping these literals. They are not in the schema.
- `multiple_35/t0/function/parameters/properties/method/descriptionc` KEEP use default: [88:106] Default 'standard'
  No schema default.

### t1 `calculate_gcd` `/function/description` (no-op)

- Original: Calculate the greatest common divisor (gcd) between two integers.
- Replacement: Calculate the greatest common divisor (gcd) between two integers.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `multiple_35/t1/function/descriptiona` KEEP both statement: [0:65] Calculate the greatest common divisor (gcd) between two integers.
  Left verbatim.

### t1 `calculate_gcd` `/function/parameters/properties/num1/description` (no-op)

- Original: First number to calculate gcd for.
- Replacement: First number to calculate gcd for.
- Reason: Prose says number. Schema type is integer. Left as written. The field is otherwise unchanged.
- Conflict, left unrepaired: Prose says number. Schema type is integer. Left as written.
- `multiple_35/t1/function/parameters/properties/num1/descriptiona` KEEP use statement: [0:34] First number to calculate gcd for.
  Left verbatim.

### t1 `calculate_gcd` `/function/parameters/properties/num2/description` (no-op)

- Original: Second number to calculate gcd for.
- Replacement: Second number to calculate gcd for.
- Reason: Prose says number. Schema type is integer. Left as written. The field is otherwise unchanged.
- Conflict, left unrepaired: Prose says number. Schema type is integer. Left as written.
- `multiple_35/t1/function/parameters/properties/num2/descriptiona` KEEP use statement: [0:35] Second number to calculate gcd for.
  Left verbatim.

### t1 `calculate_gcd` `/function/parameters/properties/algorithm/description` (CONDENSE)

- Original: The specific algorithm to use in the calculation. Supported values: 'euclidean', 'binary'. Default 'euclidean'
- Replacement: Calculation algorithm. Default 'euclidean'.
- Reason: The supported values duplicate the schema enum. The default euclidean is not a schema default, so it stays in prose.
- `multiple_35/t1/function/parameters/properties/algorithm/descriptiona` CONDENSE use purpose: [0:49] The specific algorithm to use in the calculation.
- `multiple_35/t1/function/parameters/properties/algorithm/descriptionb` OMIT use duplicate-enum: [50:89] Supported values: 'euclidean', 'binary'
- `multiple_35/t1/function/parameters/properties/algorithm/descriptionc` KEEP use default: [91:110] Default 'euclidean'
  Rejected alternative: dropping the default because the enum exists. The enum does not state a default.

## multiple_0

### t0 `triangle_properties_get` `/function/description` (CONDENSE)

- Original: Retrieve the dimensions, such as area and perimeter, of a triangle if lengths of three sides are given.
- Replacement: Retrieve a triangle's dimensions, such as area and perimeter, given three side lengths.
- Reason: Same retrieval, the same examples, the triangle, and the three-side condition.
- `multiple_0/t0/function/descriptiona` CONDENSE both action: [0:23] Retrieve the dimensions
- `multiple_0/t0/function/descriptionb` KEEP both returns: [25:51] such as area and perimeter
  Examples stay examples. Angles are not added from the parameter list.
- `multiple_0/t0/function/descriptionc` CONDENSE both scope: [53:66] of a triangle
- `multiple_0/t0/function/descriptiond` CONDENSE both condition: [67:102] if lengths of three sides are given

### t0 `triangle_properties_get` `/function/parameters/properties/side1/description` (CONDENSE)

- Original: The length of first side of the triangle.
- Replacement: Length of the first side.
- Reason: Length and ordinal stay. The triangle scope remains in the function description.
- `multiple_0/t0/function/parameters/properties/side1/descriptiona` CONDENSE use scope: [0:24] The length of first side
- `multiple_0/t0/function/parameters/properties/side1/descriptionb` OMIT use duplicate-scope: [25:40] of the triangle
  Not a lost fact. The function description still names the triangle.

### t0 `triangle_properties_get` `/function/parameters/properties/side2/description` (CONDENSE)

- Original: The length of second side of the triangle.
- Replacement: Length of the second side.
- Reason: Length and ordinal stay. The triangle scope remains in the function description.
- `multiple_0/t0/function/parameters/properties/side2/descriptiona` CONDENSE use scope: [0:25] The length of second side
- `multiple_0/t0/function/parameters/properties/side2/descriptionb` OMIT use duplicate-scope: [26:41] of the triangle

### t0 `triangle_properties_get` `/function/parameters/properties/side3/description` (CONDENSE)

- Original: The length of third side of the triangle.
- Replacement: Length of the third side.
- Reason: Length and ordinal stay. The triangle scope remains in the function description.
- `multiple_0/t0/function/parameters/properties/side3/descriptiona` CONDENSE use scope: [0:24] The length of third side
- `multiple_0/t0/function/parameters/properties/side3/descriptionb` OMIT use duplicate-scope: [25:40] of the triangle

### t0 `triangle_properties_get` `/function/parameters/properties/get_area/description` (CONDENSE)

- Original: A flag to determine whether to calculate the area of triangle. Default is true.
- Replacement: Whether to calculate the area.
- Reason: The area choice stays. The default and the boolean flag are schema facts. The triangle scope remains on the function.
- `multiple_0/t0/function/parameters/properties/get_area/descriptiona` CONDENSE use purpose: [20:49] whether to calculate the area
- `multiple_0/t0/function/parameters/properties/get_area/descriptionb` OMIT use duplicate-scope: [50:61] of triangle
- `multiple_0/t0/function/parameters/properties/get_area/descriptionc` OMIT use duplicate-type: [0:6] A flag
- `multiple_0/t0/function/parameters/properties/get_area/descriptiond` OMIT use duplicate-default: [63:79] Default is true.
  A prose-only reader would miss this default. Under the rubric it remains at the schema path.

### t0 `triangle_properties_get` `/function/parameters/properties/get_perimeter/description` (CONDENSE)

- Original: A flag to determine whether to calculate the perimeter of triangle. Default is true.
- Replacement: Whether to calculate the perimeter.
- Reason: The perimeter choice stays. The default is the schema default.
- `multiple_0/t0/function/parameters/properties/get_perimeter/descriptiona` CONDENSE use purpose: [20:54] whether to calculate the perimeter
- `multiple_0/t0/function/parameters/properties/get_perimeter/descriptionb` OMIT use duplicate-scope: [55:66] of triangle
- `multiple_0/t0/function/parameters/properties/get_perimeter/descriptionc` OMIT use duplicate-default: [68:84] Default is true.

### t0 `triangle_properties_get` `/function/parameters/properties/get_angles/description` (CONDENSE)

- Original: A flag to determine whether to calculate the internal angles of triangle. Default is true.
- Replacement: Whether to calculate the internal angles.
- Reason: Internal angles stay. That phrase is more specific than the parameter name. The default is the schema default.
- `multiple_0/t0/function/parameters/properties/get_angles/descriptiona` CONDENSE use purpose: [20:60] whether to calculate the internal angles
  Rejected alternative: shortening further to angles.
- `multiple_0/t0/function/parameters/properties/get_angles/descriptionb` OMIT use duplicate-scope: [61:72] of triangle
- `multiple_0/t0/function/parameters/properties/get_angles/descriptionc` OMIT use duplicate-default: [74:90] Default is true.

### t1 `circle_properties_get` `/function/description` (CONDENSE)

- Original: Retrieve the dimensions, such as area and circumference, of a circle if radius is given.
- Replacement: Retrieve a circle's dimensions, such as area and circumference, given its radius.
- Reason: Same retrieval, the same examples, the circle, and the radius condition. Edited from this description alone.
- `multiple_0/t1/function/descriptiona` CONDENSE both action: [0:23] Retrieve the dimensions
- `multiple_0/t1/function/descriptionb` KEEP both returns: [25:55] such as area and circumference
- `multiple_0/t1/function/descriptionc` CONDENSE both scope: [57:68] of a circle
- `multiple_0/t1/function/descriptiond` CONDENSE both condition: [69:87] if radius is given

### t1 `circle_properties_get` `/function/parameters/properties/radius/description` (no-op)

- Original: The length of radius of the circle. This is a float type value.
- Replacement: The length of radius of the circle. This is a float type value.
- Reason: The authored clause is already the role or the unit. The handler float sentence stays verbatim because copying format:float and dropping the sentence is unresolved.
- `multiple_0/t1/function/parameters/properties/radius/descriptiona` KEEP use statement: [0:35] The length of radius of the circle.
  Authored clause kept.
- `multiple_0/t1/function/parameters/properties/radius/descriptionb` UNCERTAIN use float-sentence: [35:63]  This is a float type value.
  Schema format is float. The suffix inspection leaves that duplication unresolved, so the sentence stays character for character. Dropping it was rejected.

### t1 `circle_properties_get` `/function/parameters/properties/get_area/description` (CONDENSE)

- Original: A flag to determine whether to calculate the area of circle. Default is true.
- Replacement: Whether to calculate the area.
- Reason: The area choice stays. The default is the schema default. The circle scope remains on the function.
- `multiple_0/t1/function/parameters/properties/get_area/descriptiona` CONDENSE use purpose: [20:49] whether to calculate the area
- `multiple_0/t1/function/parameters/properties/get_area/descriptionb` OMIT use duplicate-scope: [50:59] of circle
- `multiple_0/t1/function/parameters/properties/get_area/descriptionc` OMIT use duplicate-default: [61:77] Default is true.

### t1 `circle_properties_get` `/function/parameters/properties/get_circumference/description` (CONDENSE)

- Original: A flag to determine whether to calculate the circumference of circle. Default is true.
- Replacement: Whether to calculate the circumference.
- Reason: Circumference stays. The default is the schema default.
- `multiple_0/t1/function/parameters/properties/get_circumference/descriptiona` CONDENSE use purpose: [20:58] whether to calculate the circumference
- `multiple_0/t1/function/parameters/properties/get_circumference/descriptionb` OMIT use duplicate-scope: [59:68] of circle
- `multiple_0/t1/function/parameters/properties/get_circumference/descriptionc` OMIT use duplicate-default: [70:86] Default is true.

## multiple_11

### t0 `math_roots_quadratic` `/function/description` (no-op)

- Original: Calculate the roots of a quadratic equation.
- Replacement: Calculate the roots of a quadratic equation.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `multiple_11/t0/function/descriptiona` KEEP both statement: [0:44] Calculate the roots of a quadratic equation.
  Left verbatim.

### t0 `math_roots_quadratic` `/function/parameters/properties/a/description` (no-op)

- Original: Coefficient of the second-degree term.
- Replacement: Coefficient of the second-degree term.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `multiple_11/t0/function/parameters/properties/a/descriptiona` KEEP use statement: [0:38] Coefficient of the second-degree term.
  Left verbatim.

### t0 `math_roots_quadratic` `/function/parameters/properties/b/description` (no-op)

- Original: Coefficient of the first-degree term.
- Replacement: Coefficient of the first-degree term.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `multiple_11/t0/function/parameters/properties/b/descriptiona` KEEP use statement: [0:37] Coefficient of the first-degree term.
  Left verbatim.

### t0 `math_roots_quadratic` `/function/parameters/properties/c/description` (no-op)

- Original: Constant term.
- Replacement: Constant term.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `multiple_11/t0/function/parameters/properties/c/descriptiona` KEEP use statement: [0:14] Constant term.
  Left verbatim.

### t1 `math_roots_cubic` `/function/description` (no-op)

- Original: Calculate the roots of a cubic equation.
- Replacement: Calculate the roots of a cubic equation.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `multiple_11/t1/function/descriptiona` KEEP both statement: [0:40] Calculate the roots of a cubic equation.
  Left verbatim.

### t1 `math_roots_cubic` `/function/parameters/properties/a/description` (no-op)

- Original: Coefficient of the third-degree term. This is a float type value.
- Replacement: Coefficient of the third-degree term. This is a float type value.
- Reason: The authored clause is already the role or the unit. The handler float sentence stays verbatim because copying format:float and dropping the sentence is unresolved.
- `multiple_11/t1/function/parameters/properties/a/descriptiona` KEEP use statement: [0:37] Coefficient of the third-degree term.
  Authored clause kept.
- `multiple_11/t1/function/parameters/properties/a/descriptionb` UNCERTAIN use float-sentence: [37:65]  This is a float type value.
  Schema format is float. The suffix inspection leaves that duplication unresolved, so the sentence stays character for character. Dropping it was rejected.

### t1 `math_roots_cubic` `/function/parameters/properties/b/description` (no-op)

- Original: Coefficient of the second-degree term. This is a float type value.
- Replacement: Coefficient of the second-degree term. This is a float type value.
- Reason: The authored clause is already the role or the unit. The handler float sentence stays verbatim because copying format:float and dropping the sentence is unresolved.
- `multiple_11/t1/function/parameters/properties/b/descriptiona` KEEP use statement: [0:38] Coefficient of the second-degree term.
  Authored clause kept.
- `multiple_11/t1/function/parameters/properties/b/descriptionb` UNCERTAIN use float-sentence: [38:66]  This is a float type value.
  Schema format is float. The suffix inspection leaves that duplication unresolved, so the sentence stays character for character. Dropping it was rejected.

### t1 `math_roots_cubic` `/function/parameters/properties/c/description` (no-op)

- Original: Coefficient of the first-degree term. This is a float type value.
- Replacement: Coefficient of the first-degree term. This is a float type value.
- Reason: The authored clause is already the role or the unit. The handler float sentence stays verbatim because copying format:float and dropping the sentence is unresolved.
- `multiple_11/t1/function/parameters/properties/c/descriptiona` KEEP use statement: [0:37] Coefficient of the first-degree term.
  Authored clause kept.
- `multiple_11/t1/function/parameters/properties/c/descriptionb` UNCERTAIN use float-sentence: [37:65]  This is a float type value.
  Schema format is float. The suffix inspection leaves that duplication unresolved, so the sentence stays character for character. Dropping it was rejected.

### t1 `math_roots_cubic` `/function/parameters/properties/d/description` (no-op)

- Original: Constant term. This is a float type value.
- Replacement: Constant term. This is a float type value.
- Reason: The authored clause is already the role or the unit. The handler float sentence stays verbatim because copying format:float and dropping the sentence is unresolved.
- `multiple_11/t1/function/parameters/properties/d/descriptiona` KEEP use statement: [0:14] Constant term.
  Authored clause kept.
- `multiple_11/t1/function/parameters/properties/d/descriptionb` UNCERTAIN use float-sentence: [14:42]  This is a float type value.
  Schema format is float. The suffix inspection leaves that duplication unresolved, so the sentence stays character for character. Dropping it was rejected.

### t2 `math_roots_polynomial` `/function/description` (no-op)

- Original: Calculate the roots of a polynomial equation.
- Replacement: Calculate the roots of a polynomial equation.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `multiple_11/t2/function/descriptiona` KEEP both statement: [0:45] Calculate the roots of a polynomial equation.
  Left verbatim.

### t2 `math_roots_polynomial` `/function/parameters/properties/coefficients/description` (CONDENSE)

- Original: Array of coefficients of the polynomial equation starting from highest degree term.
- Replacement: Coefficients, starting from the highest-degree term.
- Reason: The highest-degree-first order stays. Array duplicates the schema type. The polynomial equation is the function description.
- `multiple_11/t2/function/parameters/properties/coefficients/descriptiona` KEEP use scope: [9:21] coefficients
- `multiple_11/t2/function/parameters/properties/coefficients/descriptionb` OMIT use duplicate-type: [0:8] Array of
- `multiple_11/t2/function/parameters/properties/coefficients/descriptionc` OMIT use duplicate-scope: [22:48] of the polynomial equation
- `multiple_11/t2/function/parameters/properties/coefficients/descriptiond` CONDENSE use order: [49:82] starting from highest degree term

### t2 `math_roots_polynomial` `/function/parameters/properties/degree/description` (no-op)

- Original: Degree of the polynomial equation. Default 0
- Replacement: Degree of the polynomial equation. Default 0
- Reason: The prose default is not a schema default, so it stays. The rest of the field is already short.
- `multiple_11/t2/function/parameters/properties/degree/descriptiona` KEEP use purpose: [0:34] Degree of the polynomial equation.
- `multiple_11/t2/function/parameters/properties/degree/descriptionb` KEEP use default: [35:44] Default 0
  No schema default.

## multiple_12

### t0 `corporate_finance_calculate_YOY_growth_rate` `/function/description` (no-op)

- Original: Calculate the year over year (YOY) growth rate for a company.
- Replacement: Calculate the year over year (YOY) growth rate for a company.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `multiple_12/t0/function/descriptiona` KEEP both statement: [0:61] Calculate the year over year (YOY) growth rate for a company.
  Left verbatim.

### t0 `corporate_finance_calculate_YOY_growth_rate` `/function/parameters/properties/company_name/description` (CONDENSE)

- Original: The name of the company for which to calculate the YOY growth rate.
- Replacement: Company name.
- Reason: The name fact stays. The YOY purpose repeats the function description, which is unchanged.
- `multiple_12/t0/function/parameters/properties/company_name/descriptiona` CONDENSE use scope: [0:23] The name of the company
- `multiple_12/t0/function/parameters/properties/company_name/descriptionb` OMIT use duplicate-purpose: [24:66] for which to calculate the YOY growth rate

### t0 `corporate_finance_calculate_YOY_growth_rate` `/function/parameters/properties/year1/description` (no-op)

- Original: The initial year.
- Replacement: The initial year.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `multiple_12/t0/function/parameters/properties/year1/descriptiona` KEEP use statement: [0:17] The initial year.
  Left verbatim.

### t0 `corporate_finance_calculate_YOY_growth_rate` `/function/parameters/properties/year1_revenue/description` (no-op)

- Original: The revenue for the initial year.
- Replacement: The revenue for the initial year.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `multiple_12/t0/function/parameters/properties/year1_revenue/descriptiona` KEEP use statement: [0:33] The revenue for the initial year.
  Left verbatim.

### t0 `corporate_finance_calculate_YOY_growth_rate` `/function/parameters/properties/year2/description` (no-op)

- Original: The subsequent year.
- Replacement: The subsequent year.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `multiple_12/t0/function/parameters/properties/year2/descriptiona` KEEP use statement: [0:20] The subsequent year.
  Left verbatim.

### t0 `corporate_finance_calculate_YOY_growth_rate` `/function/parameters/properties/year2_revenue/description` (no-op)

- Original: The revenue for the subsequent year.
- Replacement: The revenue for the subsequent year.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `multiple_12/t0/function/parameters/properties/year2_revenue/descriptiona` KEEP use statement: [0:36] The revenue for the subsequent year.
  Left verbatim.

### t1 `financial_ratios_calculate_ROE` `/function/description` (no-op)

- Original: Calculate the return on equity (ROE) for a company.
- Replacement: Calculate the return on equity (ROE) for a company.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `multiple_12/t1/function/descriptiona` KEEP both statement: [0:51] Calculate the return on equity (ROE) for a company.
  Left verbatim.

### t1 `financial_ratios_calculate_ROE` `/function/parameters/properties/net_income/description` (no-op)

- Original: Net income for the period. This is a float type value.
- Replacement: Net income for the period. This is a float type value.
- Reason: The authored clause is already the role or the unit. The handler float sentence stays verbatim because copying format:float and dropping the sentence is unresolved.
- `multiple_12/t1/function/parameters/properties/net_income/descriptiona` KEEP use statement: [0:26] Net income for the period.
  Authored clause kept.
- `multiple_12/t1/function/parameters/properties/net_income/descriptionb` UNCERTAIN use float-sentence: [26:54]  This is a float type value.
  Schema format is float. The suffix inspection leaves that duplication unresolved, so the sentence stays character for character. Dropping it was rejected.

### t1 `financial_ratios_calculate_ROE` `/function/parameters/properties/shareholder_equity/description` (no-op)

- Original: Average shareholder equity for the period. This is a float type value.
- Replacement: Average shareholder equity for the period. This is a float type value.
- Reason: The authored clause is already the role or the unit. The handler float sentence stays verbatim because copying format:float and dropping the sentence is unresolved.
- `multiple_12/t1/function/parameters/properties/shareholder_equity/descriptiona` KEEP use statement: [0:42] Average shareholder equity for the period.
  Authored clause kept.
- `multiple_12/t1/function/parameters/properties/shareholder_equity/descriptionb` UNCERTAIN use float-sentence: [42:70]  This is a float type value.
  Schema format is float. The suffix inspection leaves that duplication unresolved, so the sentence stays character for character. Dropping it was rejected.

### t2 `financial_ratios_calculate_ROA` `/function/description` (no-op)

- Original: Calculate the return on assets (ROA) for a company.
- Replacement: Calculate the return on assets (ROA) for a company.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `multiple_12/t2/function/descriptiona` KEEP both statement: [0:51] Calculate the return on assets (ROA) for a company.
  Left verbatim.

### t2 `financial_ratios_calculate_ROA` `/function/parameters/properties/net_income/description` (no-op)

- Original: Net income for the period. This is a float type value.
- Replacement: Net income for the period. This is a float type value.
- Reason: The authored clause is already the role or the unit. The handler float sentence stays verbatim because copying format:float and dropping the sentence is unresolved.
- `multiple_12/t2/function/parameters/properties/net_income/descriptiona` KEEP use statement: [0:26] Net income for the period.
  Authored clause kept.
- `multiple_12/t2/function/parameters/properties/net_income/descriptionb` UNCERTAIN use float-sentence: [26:54]  This is a float type value.
  Schema format is float. The suffix inspection leaves that duplication unresolved, so the sentence stays character for character. Dropping it was rejected.

### t2 `financial_ratios_calculate_ROA` `/function/parameters/properties/total_assets/description` (no-op)

- Original: Total average assets for the period. This is a float type value.
- Replacement: Total average assets for the period. This is a float type value.
- Reason: The authored clause is already the role or the unit. The handler float sentence stays verbatim because copying format:float and dropping the sentence is unresolved.
- `multiple_12/t2/function/parameters/properties/total_assets/descriptiona` KEEP use statement: [0:36] Total average assets for the period.
  Authored clause kept.
- `multiple_12/t2/function/parameters/properties/total_assets/descriptionb` UNCERTAIN use float-sentence: [36:64]  This is a float type value.
  Schema format is float. The suffix inspection leaves that duplication unresolved, so the sentence stays character for character. Dropping it was rejected.

## multiple_7

### t0 `wildlife_population_assess_growth` `/function/description` (CONDENSE)

- Original: Assesses the population growth of a specific species in a specified location over a period.
- Replacement: Assesses a species' population growth at a location over a period.
- Reason: Species, population growth, location, and period stay. specific and specified do not add a restriction.
- `multiple_7/t0/function/descriptiona` CONDENSE both action: [0:30] Assesses the population growth
- `multiple_7/t0/function/descriptionb` CONDENSE both scope: [31:52] of a specific species
- `multiple_7/t0/function/descriptionc` CONDENSE both scope: [53:76] in a specified location
- `multiple_7/t0/function/descriptiond` KEEP both scope: [77:90] over a period

### t0 `wildlife_population_assess_growth` `/function/parameters/properties/species/description` (CONDENSE)

- Original: The species for which the growth is to be calculated.
- Replacement: Species whose growth is calculated.
- Reason: The calculated-growth role stays. The verb calculated is the parameter's own verb and was not replaced with the function's verb analyzes.
- `multiple_7/t0/function/parameters/properties/species/descriptiona` CONDENSE use purpose: [0:53] The species for which the growth is to be calculated.
  Masked review rejected swapping calculated for assessed.

### t0 `wildlife_population_assess_growth` `/function/parameters/properties/location/description` (no-op)

- Original: The area where the species is present.
- Replacement: The area where the species is present.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `multiple_7/t0/function/parameters/properties/location/descriptiona` KEEP use statement: [0:38] The area where the species is present.
  Left verbatim.

### t0 `wildlife_population_assess_growth` `/function/parameters/properties/duration/description` (CONDENSE)

- Original: The time period for which the population growth should be calculated in years.
- Replacement: Time period in years.
- Reason: Years is not in the schema, so the unit stays. The growth purpose remains on the function description.
- `multiple_7/t0/function/parameters/properties/duration/descriptiona` CONDENSE use scope: [0:15] The time period
- `multiple_7/t0/function/parameters/properties/duration/descriptionb` KEEP use unit: [69:77] in years
- `multiple_7/t0/function/parameters/properties/duration/descriptionc` OMIT use duplicate-purpose: [26:68] the population growth should be calculated

### t1 `ecological_impact_analyze` `/function/description` (no-op)

- Original: Analyzes the impact of a species on a particular ecosystem.
- Replacement: Analyzes the impact of a species on a particular ecosystem.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `multiple_7/t1/function/descriptiona` KEEP both statement: [0:59] Analyzes the impact of a species on a particular ecosystem.
  Left verbatim.

### t1 `ecological_impact_analyze` `/function/parameters/properties/species/description` (no-op)

- Original: The species whose impact is to be calculated.
- Replacement: The species whose impact is to be calculated.
- Reason: This parameter says the impact is calculated. The function description says analyzes. Left as written. The field is otherwise unchanged.
- Conflict, left unrepaired: This parameter says the impact is calculated. The function description says analyzes. Left as written.
- `multiple_7/t1/function/parameters/properties/species/descriptiona` KEEP use statement: [0:45] The species whose impact is to be calculated.
  Left verbatim.

### t1 `ecological_impact_analyze` `/function/parameters/properties/ecosystem/description` (no-op)

- Original: The ecosystem being affected.
- Replacement: The ecosystem being affected.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `multiple_7/t1/function/parameters/properties/ecosystem/descriptiona` KEEP use statement: [0:29] The ecosystem being affected.
  Left verbatim.

### t1 `ecological_impact_analyze` `/function/parameters/properties/location/description` (no-op)

- Original: The area where the impact is analyzed.
- Replacement: The area where the impact is analyzed.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `multiple_7/t1/function/parameters/properties/location/descriptiona` KEEP use statement: [0:38] The area where the impact is analyzed.
  Left verbatim.

### t1 `ecological_impact_analyze` `/function/parameters/properties/timeframe/description` (CONDENSE)

- Original: The time period for which the impact analysis should be carried out in years.
- Replacement: Time period in years.
- Reason: Years is not in the schema. The impact purpose remains on the function description. The schema default 5 is not in the prose and was not added.
- Conflict, left unrepaired: Schema default is 5. The prose does not state that default, and it was not added.
- `multiple_7/t1/function/parameters/properties/timeframe/descriptiona` CONDENSE use scope: [0:15] The time period
- `multiple_7/t1/function/parameters/properties/timeframe/descriptionb` KEEP use unit: [68:76] in years
- `multiple_7/t1/function/parameters/properties/timeframe/descriptionc` OMIT use duplicate-purpose: [26:67] the impact analysis should be carried out

## multiple_92

### t0 `safeway_vegan_products` `/function/description` (no-op)

- Original: Get available vegan products at specified Safeway store
- Replacement: Get available vegan products at specified Safeway store
- Reason: The retailer name is a qualifier that still means something when the tool is read alone. The sentence is already short.
- `multiple_92/t0/function/descriptiona` KEEP both statement: [0:55] Get available vegan products at specified Safeway store
  Left verbatim.

### t0 `safeway_vegan_products` `/function/parameters/properties/location/description` (no-op)

- Original: City and state where the Safeway store is located, e.g. Denver, CO
- Replacement: City and state where the Safeway store is located, e.g. Denver, CO
- Reason: City and state stay. The Denver, CO example stays because the abbreviation form is uncertain.
- `multiple_92/t0/function/parameters/properties/location/descriptiona` KEEP use format: [0:49] City and state where the Safeway store is located
  City and state format.
- `multiple_92/t0/function/parameters/properties/location/descriptionb` UNCERTAIN use example: [51:66] e.g. Denver, CO
  The example may only illustrate, or it may show a state-abbreviation form. It stays.

### t0 `safeway_vegan_products` `/function/parameters/properties/categories/description` (no-op)

- Original: Product categories to search within. Default empty array
- Replacement: Product categories to search within. Default empty array
- Reason: The function description says vegan products. The category enum also lists gluten-free. Left as written. The field is otherwise unchanged.
- Conflict, left unrepaired: The function description says vegan products. The category enum also lists gluten-free. Left as written.
- `multiple_92/t0/function/parameters/properties/categories/descriptiona` KEEP use purpose: [0:36] Product categories to search within.
- `multiple_92/t0/function/parameters/properties/categories/descriptionb` KEEP use default: [37:56] Default empty array
  The schema has no default. The enum values are not copied into the prose.

### t1 `wholefoods_vegan_products` `/function/description` (no-op)

- Original: Get available vegan products at specified Whole Foods store
- Replacement: Get available vegan products at specified Whole Foods store
- Reason: The retailer name is a qualifier that still means something when the tool is read alone. The sentence is already short.
- `multiple_92/t1/function/descriptiona` KEEP both statement: [0:59] Get available vegan products at specified Whole Foods store
  Left verbatim.

### t1 `wholefoods_vegan_products` `/function/parameters/properties/location/description` (no-op)

- Original: City and state where the Whole Foods store is located, e.g. Denver, CO
- Replacement: City and state where the Whole Foods store is located, e.g. Denver, CO
- Reason: City and state stay. The Denver, CO example stays because the abbreviation form is uncertain.
- `multiple_92/t1/function/parameters/properties/location/descriptiona` KEEP use format: [0:53] City and state where the Whole Foods store is located
  City and state format.
- `multiple_92/t1/function/parameters/properties/location/descriptionb` UNCERTAIN use example: [55:70] e.g. Denver, CO
  The example may only illustrate, or it may show a state-abbreviation form. It stays.

### t1 `wholefoods_vegan_products` `/function/parameters/properties/categories/description` (no-op)

- Original: Product categories to search within. Default empty array
- Replacement: Product categories to search within. Default empty array
- Reason: The function description says vegan products. The category enum also lists gluten-free. Left as written. The field is otherwise unchanged.
- Conflict, left unrepaired: The function description says vegan products. The category enum also lists gluten-free. Left as written.
- `multiple_92/t1/function/parameters/properties/categories/descriptiona` KEEP use purpose: [0:36] Product categories to search within.
- `multiple_92/t1/function/parameters/properties/categories/descriptionb` KEEP use default: [37:56] Default empty array
  The schema has no default. The enum values are not copied into the prose.

### t2 `walmart_vegan_products` `/function/description` (no-op)

- Original: Get available vegan products at specified Walmart store
- Replacement: Get available vegan products at specified Walmart store
- Reason: The retailer name is a qualifier that still means something when the tool is read alone. The sentence is already short.
- `multiple_92/t2/function/descriptiona` KEEP both statement: [0:55] Get available vegan products at specified Walmart store
  Left verbatim.

### t2 `walmart_vegan_products` `/function/parameters/properties/location/description` (no-op)

- Original: City and state where the Walmart store is located, e.g. Denver, CO
- Replacement: City and state where the Walmart store is located, e.g. Denver, CO
- Reason: City and state stay. The Denver, CO example stays because the abbreviation form is uncertain.
- `multiple_92/t2/function/parameters/properties/location/descriptiona` KEEP use format: [0:49] City and state where the Walmart store is located
  City and state format.
- `multiple_92/t2/function/parameters/properties/location/descriptionb` UNCERTAIN use example: [51:66] e.g. Denver, CO
  The example may only illustrate, or it may show a state-abbreviation form. It stays.

### t2 `walmart_vegan_products` `/function/parameters/properties/categories/description` (no-op)

- Original: Product categories to search within. Default empty array
- Replacement: Product categories to search within. Default empty array
- Reason: The function description says vegan products. The category enum also lists gluten-free. Left as written. The field is otherwise unchanged.
- Conflict, left unrepaired: The function description says vegan products. The category enum also lists gluten-free. Left as written.
- `multiple_92/t2/function/parameters/properties/categories/descriptiona` KEEP use purpose: [0:36] Product categories to search within.
- `multiple_92/t2/function/parameters/properties/categories/descriptionb` KEEP use default: [37:56] Default empty array
  The schema has no default. The enum values are not copied into the prose.

## multiple_153

### t0 `locate_tallest_mountains` `/function/description` (no-op)

- Original: Find the tallest mountains within a specified radius of a location.
- Replacement: Find the tallest mountains within a specified radius of a location.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `multiple_153/t0/function/descriptiona` KEEP both statement: [0:67] Find the tallest mountains within a specified radius of a location.
  Left verbatim.

### t0 `locate_tallest_mountains` `/function/parameters/properties/location/description` (no-op)

- Original: The city from which to calculate distance.
- Replacement: The city from which to calculate distance.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `multiple_153/t0/function/parameters/properties/location/descriptiona` KEEP use statement: [0:42] The city from which to calculate distance.
  Left verbatim.

### t0 `locate_tallest_mountains` `/function/parameters/properties/radius/description` (no-op)

- Original: The radius within which to find mountains, measured in kilometers. This is a float type value.
- Replacement: The radius within which to find mountains, measured in kilometers. This is a float type value.
- Reason: The authored clause is already the role or the unit. The handler float sentence stays verbatim because copying format:float and dropping the sentence is unresolved.
- `multiple_153/t0/function/parameters/properties/radius/descriptiona` KEEP use statement: [0:66] The radius within which to find mountains, measured in kilometers.
  Authored clause kept.
- `multiple_153/t0/function/parameters/properties/radius/descriptionb` UNCERTAIN use float-sentence: [66:94]  This is a float type value.
  Schema format is float. The suffix inspection leaves that duplication unresolved, so the sentence stays character for character. Dropping it was rejected.

### t0 `locate_tallest_mountains` `/function/parameters/properties/amount/description` (CONDENSE)

- Original: The number of mountains to find, listed from tallest to smallest.
- Replacement: Number of mountains to find, from tallest to smallest.
- Reason: The count and the tallest-to-smallest order stay. The order is not in the schema. Only the word listed was dropped.
- `multiple_153/t0/function/parameters/properties/amount/descriptiona` CONDENSE use scope: [0:31] The number of mountains to find
- `multiple_153/t0/function/parameters/properties/amount/descriptionb` KEEP use order: [40:64] from tallest to smallest

### t1 `calculate_entropy_change` `/function/description` (no-op)

- Original: Calculate the entropy change for an isothermal and reversible process.
- Replacement: Calculate the entropy change for an isothermal and reversible process.
- Reason: The function description presents an isothermal and reversible process. The isothermal parameter asks whether the process is isothermal. Reversible has no parameter. Left as written. The field is otherwise unchanged.
- Conflict, left unrepaired: The function description presents an isothermal and reversible process. The isothermal parameter asks whether the process is isothermal. Reversible has no parameter. Left as written.
- `multiple_153/t1/function/descriptiona` KEEP both statement: [0:70] Calculate the entropy change for an isothermal and reversible process.
  Left verbatim.

### t1 `calculate_entropy_change` `/function/parameters/properties/initial_temp/description` (no-op)

- Original: The initial temperature in Kelvin. This is a float type value.
- Replacement: The initial temperature in Kelvin. This is a float type value.
- Reason: The authored clause is already the role or the unit. The handler float sentence stays verbatim because copying format:float and dropping the sentence is unresolved.
- `multiple_153/t1/function/parameters/properties/initial_temp/descriptiona` KEEP use statement: [0:34] The initial temperature in Kelvin.
  Authored clause kept.
- `multiple_153/t1/function/parameters/properties/initial_temp/descriptionb` UNCERTAIN use float-sentence: [34:62]  This is a float type value.
  Schema format is float. The suffix inspection leaves that duplication unresolved, so the sentence stays character for character. Dropping it was rejected.

### t1 `calculate_entropy_change` `/function/parameters/properties/final_temp/description` (no-op)

- Original: The final temperature in Kelvin. This is a float type value.
- Replacement: The final temperature in Kelvin. This is a float type value.
- Reason: The authored clause is already the role or the unit. The handler float sentence stays verbatim because copying format:float and dropping the sentence is unresolved.
- `multiple_153/t1/function/parameters/properties/final_temp/descriptiona` KEEP use statement: [0:32] The final temperature in Kelvin.
  Authored clause kept.
- `multiple_153/t1/function/parameters/properties/final_temp/descriptionb` UNCERTAIN use float-sentence: [32:60]  This is a float type value.
  Schema format is float. The suffix inspection leaves that duplication unresolved, so the sentence stays character for character. Dropping it was rejected.

### t1 `calculate_entropy_change` `/function/parameters/properties/heat_capacity/description` (no-op)

- Original: The heat capacity in J/K. This is a float type value.
- Replacement: The heat capacity in J/K. This is a float type value.
- Reason: The authored clause is already the role or the unit. The handler float sentence stays verbatim because copying format:float and dropping the sentence is unresolved.
- `multiple_153/t1/function/parameters/properties/heat_capacity/descriptiona` KEEP use statement: [0:25] The heat capacity in J/K.
  Authored clause kept.
- `multiple_153/t1/function/parameters/properties/heat_capacity/descriptionb` UNCERTAIN use float-sentence: [25:53]  This is a float type value.
  Schema format is float. The suffix inspection leaves that duplication unresolved, so the sentence stays character for character. Dropping it was rejected.

### t1 `calculate_entropy_change` `/function/parameters/properties/isothermal/description` (no-op)

- Original: Whether the process is isothermal. Default is True.
- Replacement: Whether the process is isothermal. Default is True.
- Reason: The prose default is not a schema default, so it stays. The rest of the field is already short.
- `multiple_153/t1/function/parameters/properties/isothermal/descriptiona` KEEP use purpose: [0:34] Whether the process is isothermal.
- `multiple_153/t1/function/parameters/properties/isothermal/descriptionb` KEEP use default: [35:51] Default is True.
  No schema default. The literal True stays.

### t2 `get_event_date` `/function/description` (no-op)

- Original: Retrieve the date of a historical event.
- Replacement: Retrieve the date of a historical event.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `multiple_153/t2/function/descriptiona` KEEP both statement: [0:40] Retrieve the date of a historical event.
  Left verbatim.

### t2 `get_event_date` `/function/parameters/properties/event/description` (no-op)

- Original: The name of the historical event.
- Replacement: The name of the historical event.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `multiple_153/t2/function/parameters/properties/event/descriptiona` KEEP use statement: [0:33] The name of the historical event.
  Left verbatim.

### t2 `get_event_date` `/function/parameters/properties/location/description` (no-op)

- Original: Location where the event took place. Defaults to global if not specified
- Replacement: Location where the event took place. Defaults to global if not specified
- Reason: The prose default is not a schema default, so it stays. The rest of the field is already short.
- `multiple_153/t2/function/parameters/properties/location/descriptiona` KEEP use purpose: [0:36] Location where the event took place.
- `multiple_153/t2/function/parameters/properties/location/descriptionb` KEEP use default: [37:72] Defaults to global if not specified
  The literal global and its condition are not in the schema.

## multiple_100

### t0 `music_generator_generate_scale_progression` `/function/description` (CONDENSE)

- Original: Generate a music scale progression in a specific key with a given tempo and duration.
- Replacement: Generate a music scale progression in a key, with a tempo and duration.
- Reason: The action and the three inputs stay, including in a key rather than a looser for a key. specific and given are not restrictions.
- `multiple_100/t0/function/descriptiona` KEEP both action: [0:34] Generate a music scale progression
- `multiple_100/t0/function/descriptionb` CONDENSE both scope: [35:52] in a specific key
- `multiple_100/t0/function/descriptionc` CONDENSE both scope: [53:84] with a given tempo and duration

### t0 `music_generator_generate_scale_progression` `/function/parameters/properties/key/description` (no-op)

- Original: The key in which to generate the scale progression.
- Replacement: The key in which to generate the scale progression.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `multiple_100/t0/function/parameters/properties/key/descriptiona` KEEP use statement: [0:51] The key in which to generate the scale progression.
  Left verbatim.

### t0 `music_generator_generate_scale_progression` `/function/parameters/properties/tempo/description` (no-op)

- Original: The tempo of the scale progression in BPM.
- Replacement: The tempo of the scale progression in BPM.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `multiple_100/t0/function/parameters/properties/tempo/descriptiona` KEEP use statement: [0:42] The tempo of the scale progression in BPM.
  Left verbatim.

### t0 `music_generator_generate_scale_progression` `/function/parameters/properties/duration/description` (no-op)

- Original: The duration of each note in beats.
- Replacement: The duration of each note in beats.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `multiple_100/t0/function/parameters/properties/duration/descriptiona` KEEP use statement: [0:35] The duration of each note in beats.
  Left verbatim.

### t0 `music_generator_generate_scale_progression` `/function/parameters/properties/scale_type/description` (CONDENSE)

- Original: The type of scale to generate. Defaults to 'major'.
- Replacement: The type of scale to generate.
- Reason: The scale-type purpose stays. Defaults to major duplicates the schema default.
- `multiple_100/t0/function/parameters/properties/scale_type/descriptiona` KEEP use purpose: [0:30] The type of scale to generate.
- `multiple_100/t0/function/parameters/properties/scale_type/descriptionb` OMIT use duplicate-default: [31:50] Defaults to 'major'

### t1 `math_hcf` `/function/description` (no-op)

- Original: Calculate the highest common factor of two numbers.
- Replacement: Calculate the highest common factor of two numbers.
- Reason: Prose says numbers. Schema types are integer. Left as written. The field is otherwise unchanged.
- Conflict, left unrepaired: Prose says numbers. Schema types are integer. Left as written.
- `multiple_100/t1/function/descriptiona` KEEP both statement: [0:51] Calculate the highest common factor of two numbers.
  Left verbatim.

### t1 `math_hcf` `/function/parameters/properties/number1/description` (no-op)

- Original: First number.
- Replacement: First number.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `multiple_100/t1/function/parameters/properties/number1/descriptiona` KEEP use statement: [0:13] First number.
  Left verbatim.

### t1 `math_hcf` `/function/parameters/properties/number2/description` (no-op)

- Original: Second number.
- Replacement: Second number.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `multiple_100/t1/function/parameters/properties/number2/descriptiona` KEEP use statement: [0:14] Second number.
  Left verbatim.

## simple_python_175

### t0 `lawyer_get_experience` `/function/description` (no-op)

- Original: Retrieve months of experience of a Lawyer on handling certain type of law cases.
- Replacement: Retrieve months of experience of a Lawyer on handling certain type of law cases.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `simple_python_175/t0/function/descriptiona` KEEP both statement: [0:80] Retrieve months of experience of a Lawyer on handling certain type of law cases.
  Left verbatim.

### t0 `lawyer_get_experience` `/function/parameters/properties/name/description` (no-op)

- Original: The full name of the Lawyer.
- Replacement: The full name of the Lawyer.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `simple_python_175/t0/function/parameters/properties/name/descriptiona` KEEP use statement: [0:28] The full name of the Lawyer.
  Left verbatim.

### t0 `lawyer_get_experience` `/function/parameters/properties/law_type/description` (OMIT)

- Original: The type of law case. eg. Bankruptcy
- Replacement: The type of law case.
- Reason: eg. Bankruptcy is marked as an illustration. The type of law case remains. The schema has no enum.
- `simple_python_175/t0/function/parameters/properties/law_type/descriptiona` KEEP use purpose: [0:21] The type of law case.
- `simple_python_175/t0/function/parameters/properties/law_type/descriptionb` OMIT use illustrative-example: [22:36] eg. Bankruptcy
  The example is not a closed list of accepted values.

## simple_python_34

### t0 `travel_itinerary_generator` `/function/description` (CONDENSE)

- Original: Generate a travel itinerary based on specific destination, duration and daily budget, with preferred exploration type.
- Replacement: Generate a travel itinerary from destination, duration, daily budget, and preferred exploration type.
- Reason: The action and all four inputs stay, including preferred. specific is not a restriction.
- `simple_python_34/t0/function/descriptiona` KEEP both action: [0:27] Generate a travel itinerary
- `simple_python_34/t0/function/descriptionb` KEEP both scope: [46:57] destination
- `simple_python_34/t0/function/descriptionc` KEEP both scope: [59:67] duration
- `simple_python_34/t0/function/descriptiond` KEEP both scope: [72:84] daily budget
- `simple_python_34/t0/function/descriptione` KEEP both scope: [91:117] preferred exploration type

### t0 `travel_itinerary_generator` `/function/parameters/properties/destination/description` (no-op)

- Original: Destination city of the trip.
- Replacement: Destination city of the trip.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `simple_python_34/t0/function/parameters/properties/destination/descriptiona` KEEP use statement: [0:29] Destination city of the trip.
  Left verbatim.

### t0 `travel_itinerary_generator` `/function/parameters/properties/days/description` (no-op)

- Original: Number of days for the trip.
- Replacement: Number of days for the trip.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `simple_python_34/t0/function/parameters/properties/days/descriptiona` KEEP use statement: [0:28] Number of days for the trip.
  Left verbatim.

### t0 `travel_itinerary_generator` `/function/parameters/properties/daily_budget/description` (no-op)

- Original: The maximum daily budget for the trip.
- Replacement: The maximum daily budget for the trip.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `simple_python_34/t0/function/parameters/properties/daily_budget/descriptiona` KEEP use statement: [0:38] The maximum daily budget for the trip.
  Left verbatim.

### t0 `travel_itinerary_generator` `/function/parameters/properties/exploration_type/description` (no-op)

- Original: The preferred exploration type.
- Replacement: The preferred exploration type.
- Reason: Schema default is urban and the enum lists four types. The prose states neither, and neither was added. The field is otherwise unchanged.
- Conflict, left unrepaired: Schema default is urban and the enum lists four types. The prose states neither, and neither was added.
- `simple_python_34/t0/function/parameters/properties/exploration_type/descriptiona` KEEP use statement: [0:31] The preferred exploration type.
  Left verbatim.

## irrelevance_59

### t0 `linear_equation_solver` `/function/description` (no-op)

- Original: Solve a linear equation.
- Replacement: Solve a linear equation.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `irrelevance_59/t0/function/descriptiona` KEEP both statement: [0:24] Solve a linear equation.
  Left verbatim.

### t0 `linear_equation_solver` `/function/parameters/properties/equation/description` (no-op)

- Original: The linear equation to solve.
- Replacement: The linear equation to solve.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `irrelevance_59/t0/function/parameters/properties/equation/descriptiona` KEEP use statement: [0:29] The linear equation to solve.
  Left verbatim.

### t0 `linear_equation_solver` `/function/parameters/properties/variable/description` (no-op)

- Original: The variable to solve for.
- Replacement: The variable to solve for.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `irrelevance_59/t0/function/parameters/properties/variable/descriptiona` KEEP use statement: [0:26] The variable to solve for.
  Left verbatim.

## irrelevance_50

### t0 `convert_celsius_to_fahrenheit` `/function/description` (no-op)

- Original: Convert a temperature from Celsius to Fahrenheit.
- Replacement: Convert a temperature from Celsius to Fahrenheit.
- Reason: Already one short claim. Cutting it further would be a grammar trim or would drop a unit, order, or qualifier.
- `irrelevance_50/t0/function/descriptiona` KEEP both statement: [0:49] Convert a temperature from Celsius to Fahrenheit.
  Left verbatim.

### t0 `convert_celsius_to_fahrenheit` `/function/parameters/properties/celsius/description` (no-op)

- Original: The temperature in Celsius to be converted. This is a float type value.
- Replacement: The temperature in Celsius to be converted. This is a float type value.
- Reason: The authored clause is already the role or the unit. The handler float sentence stays verbatim because copying format:float and dropping the sentence is unresolved.
- `irrelevance_50/t0/function/parameters/properties/celsius/descriptiona` KEEP use statement: [0:43] The temperature in Celsius to be converted.
  Authored clause kept.
- `irrelevance_50/t0/function/parameters/properties/celsius/descriptionb` UNCERTAIN use float-sentence: [43:71]  This is a float type value.
  Schema format is float. The suffix inspection leaves that duplication unresolved, so the sentence stays character for character. Dropping it was rejected.

### t0 `convert_celsius_to_fahrenheit` `/function/parameters/properties/precision/description` (no-op)

- Original: The decimal precision for the conversion result.
- Replacement: The decimal precision for the conversion result.
- Reason: Schema default is 2. The prose does not state that default, and the default was not copied into the prose. The field is otherwise unchanged.
- Conflict, left unrepaired: Schema default is 2. The prose does not state that default, and the default was not copied into the prose.
- `irrelevance_50/t0/function/parameters/properties/precision/descriptiona` KEEP use statement: [0:48] The decimal precision for the conversion result.
  Left verbatim.

## Contrast cues

### multiple_35

At least one pair has a documented selection difference, so each qualifying target gets one cue.

- t0 `calculate_lcm` cue: Unlike calculate_gcd, which calculates the greatest common divisor (gcd) between two integers, this calculates the least common multiple (lcm) between two integers.
  Rival `calculate_gcd` on axis: quantity calculated from two integers
  Why this pair: Both calculate a named two-integer quantity. A request for one of those quantities can be pointed at the other if the quantity is not contrasted.
  - `multiple_35/t0/cue-target` cue-target: least common multiple (lcm)
  - `multiple_35/t0/cue-rival` cue-rival: greatest common divisor (gcd)
- t1 `calculate_gcd` cue: Unlike calculate_lcm, which calculates the least common multiple (lcm) between two integers, this calculates the greatest common divisor (gcd) between two integers.
  Rival `calculate_lcm` on axis: quantity calculated from two integers
  Why this pair: Both calculate a named two-integer quantity. A request for one of those quantities can be pointed at the other if the quantity is not contrasted.
  - `multiple_35/t1/cue-target` cue-target: greatest common divisor (gcd)
  - `multiple_35/t1/cue-rival` cue-rival: least common multiple (lcm)

### multiple_0

At least one pair has a documented selection difference, so each qualifying target gets one cue.

- t0 `triangle_properties_get` cue: Unlike circle_properties_get, which retrieves the dimensions, such as area and circumference, of a circle if radius is given, this retrieves the dimensions, such as area and perimeter, of a triangle if lengths of three sides are given.
  Rival `circle_properties_get` on axis: figure and the measurement the description requires
  Why this pair: Both retrieve dimensions of a figure from measurements given in the description. Area is named by both, so the figure and the required measurement decide the tool.
  - `multiple_0/t0/cue-target` cue-target: lengths of three sides
  - `multiple_0/t0/cue-rival` cue-rival: if radius is given
  - `multiple_0/t0/cue-examples` cue-target-examples: such as area and perimeter
- t1 `circle_properties_get` cue: Unlike triangle_properties_get, which retrieves the dimensions, such as area and perimeter, of a triangle if lengths of three sides are given, this retrieves the dimensions, such as area and circumference, of a circle if radius is given.
  Rival `triangle_properties_get` on axis: figure and the measurement the description requires
  Why this pair: Both retrieve dimensions of a figure from measurements given in the description. Area is named by both, so the figure and the required measurement decide the tool.
  - `multiple_0/t1/cue-target` cue-target: if radius is given
  - `multiple_0/t1/cue-rival` cue-rival: lengths of three sides

### multiple_11

At least one pair has a documented selection difference, so each qualifying target gets one cue.

- t0 `math_roots_quadratic` cue: Unlike math_roots_cubic, which calculates the roots of a cubic equation, this calculates the roots of a quadratic equation.
  Rival `math_roots_cubic` on axis: equation class whose roots are calculated
  Why this pair: Each tool calculates roots of an equation. The descriptions name different equation classes.
  - `multiple_11/t0/cue-target` cue-target: quadratic equation
  - `multiple_11/t0/cue-rival` cue-rival: cubic equation
- t1 `math_roots_cubic` cue: Unlike math_roots_quadratic, which calculates the roots of a quadratic equation, this calculates the roots of a cubic equation.
  Rival `math_roots_quadratic` on axis: equation class whose roots are calculated
  Why this pair: Each tool calculates roots of an equation. The descriptions name different equation classes.
  - `multiple_11/t1/cue-target` cue-target: cubic equation
  - `multiple_11/t1/cue-rival` cue-rival: quadratic equation
- t2 `math_roots_polynomial` cue: Unlike math_roots_quadratic, which calculates the roots of a quadratic equation, this calculates the roots of a polynomial equation.
  Rival `math_roots_quadratic` on axis: equation class whose roots are calculated
  Why this pair: Each tool calculates roots of an equation. The descriptions name different equation classes.
  - `multiple_11/t2/cue-target` cue-target: polynomial equation
  - `multiple_11/t2/cue-rival` cue-rival: quadratic equation

### multiple_12

At least one pair has a documented selection difference, so each qualifying target gets one cue.

- t0 `corporate_finance_calculate_YOY_growth_rate` cue: Unlike financial_ratios_calculate_ROE, which calculates the return on equity (ROE) for a company from net income for the period and average shareholder equity for the period, this calculates the year over year (YOY) growth rate for a company from revenue for an initial year and revenue for a subsequent year.
  Rival `financial_ratios_calculate_ROE` on axis: which company-finance quantity is calculated, and from which documented inputs
  Why this pair: Each tool calculates a named company-finance quantity. The quantity, and the inputs that define it, are different.
  - `multiple_12/t0/cue-target` cue-target: year over year (YOY) growth rate
  - `multiple_12/t0/cue-rival` cue-rival: return on equity (ROE)
  - `multiple_12/t0/cue-year1` cue-target-input: The revenue for the initial year.
  - `multiple_12/t0/cue-year2` cue-target-input: The revenue for the subsequent year.
  - `multiple_12/t0/cue-ni` cue-rival-input: Net income for the period.
  - `multiple_12/t0/cue-eq` cue-rival-input: Average shareholder equity for the period.
- t1 `financial_ratios_calculate_ROE` cue: Unlike financial_ratios_calculate_ROA, which calculates the return on assets (ROA) for a company from net income for the period and total average assets for the period, this calculates the return on equity (ROE) for a company from net income for the period and average shareholder equity for the period.
  Rival `financial_ratios_calculate_ROA` on axis: which return ratio, and which balance-sheet total
  Why this pair: Each tool calculates a named company-finance quantity. The quantity, and the inputs that define it, are different.
  - `multiple_12/t1/cue-target` cue-target: return on equity (ROE)
  - `multiple_12/t1/cue-rival` cue-rival: return on assets (ROA)
  - `multiple_12/t1/cue-eq` cue-target-input: Average shareholder equity for the period.
  - `multiple_12/t1/cue-assets` cue-rival-input: Total average assets for the period.
- t2 `financial_ratios_calculate_ROA` cue: Unlike financial_ratios_calculate_ROE, which calculates the return on equity (ROE) for a company from net income for the period and average shareholder equity for the period, this calculates the return on assets (ROA) for a company from net income for the period and total average assets for the period.
  Rival `financial_ratios_calculate_ROE` on axis: which return ratio, and which balance-sheet total
  Why this pair: Each tool calculates a named company-finance quantity. The quantity, and the inputs that define it, are different.
  - `multiple_12/t2/cue-target` cue-target: return on assets (ROA)
  - `multiple_12/t2/cue-rival` cue-rival: return on equity (ROE)
  - `multiple_12/t2/cue-assets` cue-target-input: Total average assets for the period.
  - `multiple_12/t2/cue-eq` cue-rival-input: Average shareholder equity for the period.

### multiple_7

At least one pair has a documented selection difference, so each qualifying target gets one cue.

- t0 `wildlife_population_assess_growth` cue: Unlike ecological_impact_analyze, which analyzes the impact of a species on a particular ecosystem, this assesses the population growth of a specific species in a specified location over a period.
  Rival `ecological_impact_analyze` on axis: which quantity is assessed for the species
  Why this pair: Both assess a species at a place. One states population growth. The other states impact on an ecosystem.
  - `multiple_7/t0/cue-target` cue-target: population growth of a specific species in a specified location over a period
  - `multiple_7/t0/cue-rival` cue-rival: impact of a species on a particular ecosystem
- t1 `ecological_impact_analyze` cue: Unlike wildlife_population_assess_growth, which assesses the population growth of a specific species in a specified location over a period, this analyzes the impact of a species on a particular ecosystem.
  Rival `wildlife_population_assess_growth` on axis: which quantity is assessed for the species
  Why this pair: Both assess a species at a place. One states population growth. The other states impact on an ecosystem.
  - `multiple_7/t1/cue-target` cue-target: impact of a species on a particular ecosystem
  - `multiple_7/t1/cue-rival` cue-rival: population growth of a specific species in a specified location over a period

### multiple_92

At least one pair has a documented selection difference, so each qualifying target gets one cue.

- t0 `safeway_vegan_products` cue: Unlike wholefoods_vegan_products, which gets available vegan products at specified Whole Foods store, this gets available vegan products at specified Safeway store.
  Rival `wholefoods_vegan_products` on axis: retailer
  Why this pair: Each tool gets available vegan products at a named retailer's store. The schemas match once the retailer words are removed. The retailer is the difference.
  - `multiple_92/t0/cue-target` cue-target: specified Safeway store
  - `multiple_92/t0/cue-rival` cue-rival: specified Whole Foods store
- t1 `wholefoods_vegan_products` cue: Unlike safeway_vegan_products, which gets available vegan products at specified Safeway store, this gets available vegan products at specified Whole Foods store.
  Rival `safeway_vegan_products` on axis: retailer
  Why this pair: Each tool gets available vegan products at a named retailer's store. The schemas match once the retailer words are removed. The retailer is the difference.
  - `multiple_92/t1/cue-target` cue-target: specified Whole Foods store
  - `multiple_92/t1/cue-rival` cue-rival: specified Safeway store
- t2 `walmart_vegan_products` cue: Unlike safeway_vegan_products, which gets available vegan products at specified Safeway store, this gets available vegan products at specified Walmart store.
  Rival `safeway_vegan_products` on axis: retailer
  Why this pair: Each tool gets available vegan products at a named retailer's store. The schemas match once the retailer words are removed. The retailer is the difference.
  - `multiple_92/t2/cue-target` cue-target: specified Walmart store
  - `multiple_92/t2/cue-rival` cue-rival: specified Safeway store

### multiple_153

No pair plausibly answers a similar need. Tallest mountains within a radius, entropy change for an isothermal reversible process, and the date of a historical event are different tasks. A shared parameter name, location, does not make the actions confusable. No cue is added. X stays U and SX stays S.

- t0 `locate_tallest_mountains`: no cue. No pair plausibly answers a similar need. Tallest mountains within a radius, entropy change for an isothermal reversible process, and the date of a historical event are different tasks. A shared parameter name, location, does not make the actions confusable. No cue is added. X stays U and SX stays S.
- t1 `calculate_entropy_change`: no cue. No pair plausibly answers a similar need. Tallest mountains within a radius, entropy change for an isothermal reversible process, and the date of a historical event are different tasks. A shared parameter name, location, does not make the actions confusable. No cue is added. X stays U and SX stays S.
- t2 `get_event_date`: no cue. No pair plausibly answers a similar need. Tallest mountains within a radius, entropy change for an isothermal reversible process, and the date of a historical event are different tasks. A shared parameter name, location, does not make the actions confusable. No cue is added. X stays U and SX stays S.

### multiple_100

No pair plausibly answers a similar need. A music scale progression and the highest common factor of two numbers do not compete for the same request. No cue is added.

- t0 `music_generator_generate_scale_progression`: no cue. No pair plausibly answers a similar need. A music scale progression and the highest common factor of two numbers do not compete for the same request. No cue is added.
- t1 `math_hcf`: no cue. No pair plausibly answers a similar need. A music scale progression and the highest common factor of two numbers do not compete for the same request. No cue is added.

### simple_python_175

The catalogue has one tool, so there is no rival. X stays U and SX stays S.

- t0 `lawyer_get_experience`: no cue. The catalogue has one tool, so there is no rival. X stays U and SX stays S.

### simple_python_34

The catalogue has one tool, so there is no rival. X stays U and SX stays S.

- t0 `travel_itinerary_generator`: no cue. The catalogue has one tool, so there is no rival. X stays U and SX stays S.

### irrelevance_59

The catalogue has one tool, so there is no rival. X stays U and SX stays S.

- t0 `linear_equation_solver`: no cue. The catalogue has one tool, so there is no rival. X stays U and SX stays S.

### irrelevance_50

The catalogue has one tool, so there is no rival. X stays U and SX stays S.

- t0 `convert_celsius_to_fahrenheit`: no cue. The catalogue has one tool, so there is no rival. X stays U and SX stays S.
