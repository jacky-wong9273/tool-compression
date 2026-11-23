# Sealed tranche

Eighteen cases. Nine description slots differ from U. Nine cases receive a cue. The other nine have an empty cue, so X equals U and SX equals S. The machine ledger is `edits/s-record.json` and `edits/x-record.json`. This note is the reading.

S and X were specified independently. Cue sentences below are the sealed X strings. Each one is appended to the original function description as a single leading space. SX uses that same string on the S base.

The review question for every cue: could both descriptions be true of the same request, and if so, does this cue still help the reader choose? For each cued tool the answer is yes, a vague request can fit both, and the cue names the difference the originals already state. A precise request can make only one description true. `implies_unsupported_exclusion` is false on every cue. No cue names its own tool. No cue says "only this", "cannot", or "can't".

## S edits

A frame such as "This function calculates" is not a separate claim. A named duplicate whose meaning survives on the same tool is omitted. An open-ended illustration is omitted. A prose default that the schema does not state is kept. Prose that says "number", "list", or "dictionary" is not rewritten to the schema type. A prose/schema conflict is left as written.

| Case | Slot | Replacement |
| --- | --- | --- |
| `multiple_9` | each function description | "Calculate the standard deviation across different scores for a specific student." / "Calculate the average grade across different subjects for a specific student." / "Find the subject where the student got the highest score." |
| `multiple_21` | both function descriptions | "Play a sound wave file." / "Generate a sinusoidal sound wave file of a certain frequency for a specific duration and save it to a WAV file." |
| `multiple_24` | `method` | "The method to use when calculating the route." The parenthetical default `fastest` is the schema default and is omitted. The enum stays in the schema. |
| `multiple_73` | both `religion` parameters | "Name of the religion." "Core beliefs and practices" and "origin and founder" remain on the matching function descriptions. |
| `multiple_99` | `function_variable` | "The variable present in the function. Default is 'x'." The open-ended "for instance x or y, etc." is omitted. The default stays because the schema has no default. |

The other thirteen sealed catalogues are unchanged, so S equals U: `multiple_2`, `multiple_4`, `multiple_27`, `multiple_28`, `multiple_33`, `multiple_45`, `multiple_57`, `simple_python_0`, `simple_python_1`, `simple_python_2`, `irrelevance_0`, `irrelevance_1`, `irrelevance_2`.

Fact ledger for the tranche: 152 propositions, 152 preserved, 0 lost, 0 unsupported additions, 0 uncertain retentions, 4 duplicate or illustration omissions, 112 S propositions, 40 cue propositions (20 cued tools, two excerpts each).

## Cues

`multiple_2`. Three fetch tools on one country. The two city tools are the closer pair. Population's rival is the earlier city tool, by the tie-break.

- `country_info_largest_city`: "Unlike country_info_capital, which fetches the capital city, this fetches the largest city."
- `country_info_capital`: "Unlike country_info_largest_city, which fetches the largest city, this fetches the capital city."
- `country_info_population`: "Unlike country_info_largest_city, which fetches the largest city, this fetches the current population."

`multiple_4`. Both tools take an initial speed, an acceleration, and a time. The axis is the returned quantity, not the shared rounding argument.

- `kinematics_calculate_displacement`: "Unlike kinematics_calculate_final_speed, which calculates the final speed, this calculates displacement."
- `kinematics_calculate_final_speed`: "Unlike kinematics_calculate_displacement, which calculates displacement, this calculates the final speed."

`multiple_9`. Standard deviation and average are the same action. The highest-score tool finds a subject, so its rival is the earlier statistic. `calculate_average` was rejected for that third tool because it is later in the catalogue.

- `calculate_standard_deviation`: "Unlike calculate_average, which calculates the average grade, this calculates the standard deviation."
- `calculate_average`: "Unlike calculate_standard_deviation, which calculates the standard deviation, this calculates the average grade."
- `highest_grade`: "Unlike calculate_standard_deviation, which calculates the standard deviation, this finds the subject with the highest score."

`multiple_21`. Play versus generate. The generator's sinusoidal wording is not turned into an exclusion of playback, and the waveform enum is not the axis.

- `play_sound_wave`: "Unlike generate_sound_wave, which generates a sound wave file, this plays a sound wave file."
- `generate_sound_wave`: "Unlike play_sound_wave, which plays a sound wave file, this generates a sound wave file."

`multiple_27`. Travel time versus shortest path. The shared mode list is not the axis.

- `maps_route_times`: "Unlike maps_shortest_path, which finds the shortest path, this estimates the travel time."
- `maps_shortest_path`: "Unlike maps_route_times, which estimates the travel time, this finds the shortest path."

`multiple_33`. Derivative versus definite integral. The cue keeps "definite" because that is the source's qualifier. It does not use a class label such as "calculus".

- `calculate_derivative`: "Unlike calculate_integral, which calculates the definite integral, this calculates the derivative."
- `calculate_integral`: "Unlike calculate_derivative, which calculates the derivative, this calculates the definite integral."

`multiple_45`. Geological era versus historical event. The shared years-ago flag is not the axis. The event source says "an historical event"; the cue says "a historical event" and adds no century or place.

- `geology_get_era`: "Unlike history_get_event_date, which gets the date of a historical event, this gets the estimated date of a geological era."
- `history_get_event_date`: "Unlike geology_get_era, which gets the estimated date of a geological era, this gets the date of a historical event."

`multiple_57`. Compound versus simple. The conflicting "compounded" sentence on the simple-interest time parameter is not the axis.

- `financial_compound_interest`: "Unlike financial_simple_interest, which calculates simple interest, this calculates compound interest."
- `financial_simple_interest`: "Unlike financial_compound_interest, which calculates compound interest, this calculates simple interest."

`multiple_73`. Beliefs and practices versus origin and founder. Neither half of either fact is dropped.

- `religion_get_core_beliefs`: "Unlike religion_get_origin, which retrieves the origin and founder, this retrieves the core beliefs and practices."
- `religion_get_origin`: "Unlike religion_get_core_beliefs, which retrieves the core beliefs and practices, this retrieves the origin and founder."

## Empty cues

`multiple_24`. A route between two points and the details of a chess club do not answer a similar request. The word "location" in the chess-club description is not a route.

`multiple_28`. Quadratic roots, an RGB-to-hex conversion, and reversing a string do not share an action or a resource.

`multiple_99`. A derivative at a value and a personality-trait lookup do not answer a similar request.

`simple_python_0`, `simple_python_1`, `simple_python_2`, `irrelevance_0`, `irrelevance_1`, `irrelevance_2`. Each catalogue has one tool. There is no second description, so no rival, axis, or cue location qualifies. This rule was applied to these six sealed catalogues only.

## Conflicts left as written

- `multiple_9`: each `gradeDict` description says dictionary; the schema type is object.
- `multiple_21`: the generator description says sinusoidal; `wave_type` also lists square and sawtooth, and its default is sine.
- `multiple_57`: the simple-interest time description says the money is to be compounded; the function description says simple interest.
- `simple_python_1`: the `number` description says number; the schema type is integer.
- `simple_python_2`: the function description names the point (x, y); the schema also has an optional z.
- `irrelevance_1`: the `numbers` description says list; the schema type is array.

## What this tranche does not decide

## Second tranche

131 cases were added. The first 18 were not rewritten. The formative twelve were left unsealed. Their pilot S and X were not copied.

115 of the new cases have one tool: `simple_python_3` through `simple_python_33`, `simple_python_35` through `simple_python_61`, `irrelevance_3` through `irrelevance_49`, `irrelevance_51` through `irrelevance_58`, and `irrelevance_60` through `irrelevance_61`. Each description slot was read. An empty cue is the one-tool rule, applied to these catalogues after that reading. X equals U and SX equals S.

Six of those one-tool catalogues change S:

| Case | Slot | Replacement |
| --- | --- | --- |
| `simple_python_4` | function description | "Solve the quadratic equation and return its roots." |
| `simple_python_16` | `function_variable` | "The variable present in the function. Default is 'x'." The open-ended "for instance x or y, etc." is omitted. The default stays because the schema has no default. |
| `simple_python_17` | function description | "Retrieve prime factors of a number." |
| `irrelevance_32` | function description | "Return the type of the cell based on it's characteristics." The source apostrophe stays. |
| `irrelevance_32` | `membrane_type` | "Type of membrane in the cell." The schema default `Phospholipid bi-layer` is omitted from the prose. |
| `irrelevance_55` | function description | "Add a product to the user's cart." |
| `irrelevance_58` | `usage_efficiency` | "The efficiency of energy usage in the home. This is a float type value." The schema default 0.8 is omitted. The float sentence stays. |

The other one-tool catalogues in this tranche are unchanged, so S equals U. Float sentences, input examples, and prose defaults that the schema does not state were kept. Prose that says "number", "list", or "dictionary" was not rewritten to the schema type. Conflicts that were noticed were left as written, including `simple_python_5` (an unspecified root type may return complex roots, while the parameter says the default is real), `simple_python_30` (the function assumes initial velocity 0 while the parameter can be set), `simple_python_54` (the function says a human gene while species can vary), `irrelevance_24` (the function names voltage and resistance while frequency is also a parameter), `irrelevance_38` (an omitted author is described as the most-cited paper, while the schema default is `'None'`), `irrelevance_53` (dictionary versus object), and `irrelevance_55` (a missing cart id creates a new cart, while the schema default is `'0'`).

Sixteen two-tool catalogues were read after tool 0. Thirteen receive a cue. The cue is one space on the original function description. SX uses that same string on the S base.

`multiple_3`. Euclidean distance versus the angle of two points with respect to the x-axis. The shared rounding argument is not the axis.

`multiple_8`. Estimated property value versus finding properties. The budget belongs only to the finder.

`multiple_10`. Deleting or adding columns versus creating a backup. S drops the frame "This function" on both descriptions. The column parameter still says "list" where the schema says array.

`multiple_13`. Current selling price versus a revenue estimate.

`multiple_15`. Solar-farm energy output versus wind-farm energy output.

`multiple_29`. Zero points of one function versus intersection points of two functions.

`multiple_32`. Cone volume versus cone mass.

`multiple_36`. Acceleration versus the speed of an object that starts from rest. The function's "starts from rest" sentence is not repaired against the settable initial speed.

`multiple_38`. Reserving a library book versus searching for one.

`multiple_40`. Ampere's Circuital Law versus the Biot-Savart law. The cue names the law. It does not turn either geometry sentence into an exclusion.

`multiple_47`. Cosine similarity versus a correlation coefficient. Pearson versus Spearman stays an argument of the correlation tool.

`multiple_48`. Nearby stores versus nearby libraries.

`multiple_53`. Linear regression versus Random Forest Regression. The methods are alternatives. The cue does not treat one as a subclass of the other.

Three two-tool catalogues have an empty cue. `multiple_39`: a grocery order and a ride share a cost ceiling, not an action. `multiple_42`: mixture temperature and mass from molar mass do not answer a similar request. `multiple_52`: a unit conversion can already be read as covering a currency conversion, so a cue would be the polynomial failure, an exclusion the sources do not state.

## What is still open

The remaining 691 cases, including the formative twelve, have no sealed S and no sealed X. A one-tool catalogue in that remainder is not automatically uncued. A multi-tool catalogue in that remainder is not automatically cued. Both wait for the same reading.
