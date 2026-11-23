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

The remaining 822 cases, including the formative twelve, have no sealed S and no sealed X. A one-tool catalogue in that remainder is not automatically uncued. A multi-tool catalogue in that remainder is not automatically cued. Both wait for the same reading.
