# Unchanged counterexamples

These rows are also in the occurrence ledgers. They show a KEEP, a refused cue, and a control.

## S2 already minimal

`multiple_34:0:/function/description` kept `Calculates the greatest common divisor of two numbers.` because `already_minimal`.

## S2 no shorter faithful candidate

`multiple_35:0:/function/parameters/properties/method/description` kept the method prose because `/function/parameters/properties/method/description states "Default 'standard'", and the schema has no default to point at, so the prose default stays.`.

## S2 ambiguous source

`multiple_9` `calculate_standard_deviation` `/function/parameters/properties/gradeDict/description` kept `A dictionary where keys represent subjects and values represent scores` because Prose says dictionary and the schema type is object. The word is left as written.

## X2 cued pair

`multiple_34:0:/function/description` cue: Unlike math_lcm, which calculates the least common multiple, this calculates the greatest common divisor.

## X2 uncued neighbor

`multiple_34:1:/function/description` has no cue. No rival serves a common user need with evidence on both sides. Required parameter names or types differ ((('num', 'number'),) versus (('num1', 'integer'), ('num2', 'integer'))). An unrelated tool does not veto any other pair.

## X2 single-tool control

`simple_python_0:0:/function/description` cue is empty. Single-tool control. Controls receive no cue.

## X2 target left verbatim while a neighbor is cued

`multiple_2` `country_info_population` has no cue. No rival serves a common user need with evidence on both sides. The function texts do not share one short supported axis. An unrelated tool does not veto any other pair.
