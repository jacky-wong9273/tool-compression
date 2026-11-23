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

## Third tranche

142 cases were added. The first 149 were not rewritten. The formative twelve were left unsealed. Their pilot S and X were not copied.

130 of the new cases have one tool: `simple_python_62` through `simple_python_141`, and `irrelevance_62` through `irrelevance_111`. Each description slot was read. An empty cue is the one-tool rule, applied after that reading. X equals U and SX equals S.

Two of those one-tool catalogues change S:

| Case | Slot | Replacement |
| --- | --- | --- |
| `irrelevance_62` | function description | "Create a recommendation model using a given user data and an algorithm type." The frame "This function is used to" is omitted. The source wording "a given user data" stays. |
| `irrelevance_64` | `coin_type` | "The type of the coin. Possible values are 'fair', 'double_heads', 'double_tails'." The schema default `fair` is omitted. The possible values stay. |

The other one-tool catalogues in this tranche are unchanged, so S equals U. Prose defaults that the schema does not state were kept, including a prose default of 0.5 where the schema has no default. Schema defaults that the prose does not restate were not copied into S. Prose that says "list" was not rewritten to array. Conflicts that were noticed were left as written, including `simple_python_64` (the function says the homozygous dominant genotype while the parameter also lists Aa and aa), `simple_python_113` (the function says a six-sided die while `die_sides` can name another count), `irrelevance_69` (prose says a scaler object while the schema type is number and the schema default is the string `'1.2'`), `irrelevance_75` (the schema default is the string `'5 years'` on an integer period), and `irrelevance_90` (the function says a noise complaint while `complaint_type` also names other types).

Twelve two-tool catalogues were read from each tool's own description. Seven receive a cue. The cue is one space on the original function description. SX uses that same string on the S base. None of these twelve change S.

`multiple_54`. Historical dividend data versus stock market data for a company.

`multiple_58`. A search for a doctor versus a search for a lawyer.

`multiple_61`. A home renovation expert versus a landscape architect.

`multiple_62`. Nearby nature parks versus nearby restaurants.

`multiple_69`. The Myers-Briggs Type Indicator versus the five-factor model. The instruments are alternatives. The cue does not treat one as a subclass of the other.

`multiple_72`. Historical population versus historical GDP for a U.S. state and a year. Real versus nominal stays an argument of the GDP tool.

`multiple_76`. A custom painting versus a custom sculpture.

Five two-tool catalogues have an empty cue. `multiple_55`: a stock-price forecast and a weather forecast do not answer a similar request. `multiple_59`: renting a car and locating a lawyer do not. `multiple_74`: an artwork's auction price and a library book search do not, even though both take a title, a creator, and a platform. `multiple_78`: a museum can already be a tourist spot, so both descriptions can be true of one museum request, and a cue would be an exclusion the tourist-spot description does not state. `multiple_79`: restaurant information and museum exhibition information do not answer a similar request.

## Fourth tranche

142 cases were added. The first 291 were not rewritten. The formative twelve were left unsealed. Their pilot S and X were not copied. `simple_python_175` is one of those twelve and was skipped.

130 of the new cases have one tool: `simple_python_142` through `simple_python_174`, `simple_python_176` through `simple_python_222`, and `irrelevance_112` through `irrelevance_161`. Each description slot was read. An empty cue is the one-tool rule, applied after that reading. X equals U and SX equals S.

Five of those one-tool catalogues change S:

| Case | Slot | Replacement |
| --- | --- | --- |
| `simple_python_157` | function description | "Check if an individual has any prior felony convictions based on their full name and birth date." The frame "This function" is omitted. |
| `simple_python_163` | `include_owner` | "Include owner's name in the property record." The schema default false is omitted. |
| `simple_python_182` | `year` | "The year in which the lawsuit case was initiated." The schema default 2023 is omitted. |
| `simple_python_215` | function description | "Retrieve a brief about a specified movie." The frame "This function" is omitted. |
| `simple_python_217` | function description | "Take in fMRI data to output analyzed data." The frame "This function" is omitted. |

The other one-tool catalogues in this tranche are unchanged, so S equals U. Prose defaults that the schema does not state were kept. Schema defaults that the prose does not restate were not copied into S. Prose that says "list" was not rewritten to array. Conflicts that were noticed were left as written, including `simple_python_169` and `simple_python_215` (a boolean field whose schema default is the string `'false'`), `irrelevance_113` (a number field whose schema default is the string `'0.3'`), `irrelevance_122` and `irrelevance_129` (boolean fields whose schema defaults are the strings `'False'` and `'True'`), and `irrelevance_136` (the function says the president while the state parameter says a governor lookup).

Twelve two-tool catalogues were read from each tool's own description. Nine receive a cue. The cue is one space on the original function description. SX uses that same string on the S base.

`multiple_80`. Nearby music shops versus nearby gyms.

`multiple_81`. A concert ticket versus a festival ticket.

`multiple_82`. A piece of music versus an audio signal. The two are alternatives. The cue does not treat one as a subclass of the other.

`multiple_84`. Top goal scorers versus top assist makers.

`multiple_85`. Basketball scores versus soccer scores.

`multiple_86`. A BoardGameGeek recommendation versus an Amazon Game Store recommendation.

`multiple_88`. Active players versus sales figures for a video game and a year.

`multiple_90`. Events suitable for groups versus restaurants suitable for groups.

`multiple_91`. Restaurants versus cooking recipes.

Three two-tool catalogues have an empty cue. `multiple_93`: renting a car and booking a hotel room do not answer a similar request. `multiple_95`: a unit conversion can already be read as covering a currency conversion, so a cue would be an exclusion the unit description does not state. `multiple_97`: the area of a circle and a sine-wave plot do not answer a similar request. S on `multiple_97` drops "(defaults to meters)" because the schema default is meters. That edit comes from the circle tool's own description.

## Fifth tranche

132 cases were added. The first 433 were not rewritten. The formative twelve were left unsealed. Their pilot S and X were not copied.

120 of the new cases have one tool: `simple_python_223` through `simple_python_302`, and `irrelevance_162` through `irrelevance_201`. Each description slot was read. An empty cue is the one-tool rule, applied after that reading. X equals U and SX equals S.

Six of those one-tool catalogues change S:

| Case | Slot | Replacement |
| --- | --- | --- |
| `simple_python_252` | `sort_by` | "Order of sorting the events." The schema default chronological is omitted. |
| `simple_python_252` | `count` | "Number of events to return." The schema default 5 is omitted. |
| `simple_python_257` | function description | "Identify the RGB values of a named color." The frame "This function" is omitted. |
| `simple_python_277` | `information` | "The type of information needed from the museum. This is optional." The schema default `all` is omitted. The schema type is array and the default is the string `'all'`; that mismatch stays. |
| `simple_python_296` | `scale_type` | "The type of scale to generate." The schema default major is omitted. |
| `irrelevance_163` | function description | "Tune instruments based on the instrument type and the desired key or note." The frame "This function helps" is omitted. |
| `irrelevance_164` | `top` | "Number of top players to return." The schema default 5 is omitted. |

The other one-tool catalogues in this tranche are unchanged, so S equals U. Prose defaults that the schema does not state were kept. Schema defaults that the prose does not restate were not copied into S. Prose that says "list" was not rewritten to array. Conflicts that were noticed were left as written, including `irrelevance_167` (boolean fields whose schema default is the string `'false'`), `irrelevance_176` (an integer field whose schema default is the string `'optional'`), `irrelevance_179` (a venue field whose schema default is the string `'basketball'`), `irrelevance_189` (an integer year whose schema default is the string `'The current year'`), and `irrelevance_195` (the function says chess while the game parameter names the board game).

Twelve two-tool catalogues were read from each tool's own description. None receives a cue. The pairs do not answer a similar request: a greatest common divisor and landmark law cases, paint mixing and density, heat capacity and discounted cash flow, game collectables and a genetic mutation, forest growth and a discovery credit, body mass index and a celebrity's net worth, lawsuits and compound interest, a mutual-fund balance and a circle's area, court-case details and a triangle's area, a crime rate and a poker winner, lawsuits and hotel availability, and a humidity forecast and a team's score. Sharing a location, as in `multiple_140`, is not a selection axis.

`multiple_142` drops "Default is false." on `include_player_stats` because the schema default is false. That edit comes from the sports tool's own description. X stays equal to U because there is no cue.

## Sixth tranche

149 cases were added. The first 565 were not rewritten. The formative twelve were left unsealed. Their pilot S and X were not copied.

135 of the new cases have one tool: `simple_python_303` through `simple_python_399`, and `irrelevance_202` through `irrelevance_239`. Each description slot was read. An empty cue is the one-tool rule, applied after that reading. X equals U and SX equals S.

Seven of those one-tool catalogues change S:

| Case | Slot | Replacement |
| --- | --- | --- |
| `simple_python_326` | `include_player_stats` | "Indicates if individual player statistics should be included in the result." The schema default false is omitted. |
| `simple_python_331` | `number_of_players` | "Number of players you want to retrieve." The schema default 10 is omitted. |
| `simple_python_357` | `diet_preference` | "Preferred dietary consideration like vegan, vegetarian, gluten-free etc." The schema default none is omitted. |
| `simple_python_384` | `room_type` | "The type of the room. Options are 'Standard', 'Deluxe', 'Suite'." The schema default Standard is omitted. The option list stays. |
| `simple_python_385` | `no_of_rooms` | "Number of rooms to book." The schema default 1 is omitted. |
| `irrelevance_202` | `game_rounds` | "The total game rounds." The schema default 3 is omitted. The schema type is integer and the default is the string `'3'`; that mismatch stays. |
| `irrelevance_204` | `solve_method` | "Method to be used to solve the puzzle." The schema default brute_force is omitted. |

The other one-tool catalogues in this tranche are unchanged, so S equals U. A word that names an option, such as "normal" on `simple_python_341` or "12" on `irrelevance_228`, was kept when the sentence does not state that value as the default. Prose defaults that the schema does not state were kept, including the unfinished default sentence on `simple_python_379`. Schema defaults that the prose does not restate were not copied into S. Prose that says "list" was not rewritten to array. Conflicts that were noticed were left as written, including `irrelevance_220` (a boolean field whose schema default is the string `'false'`), `irrelevance_224` (a boolean field whose schema default is the string `'True'`), `irrelevance_225` (the schema default is `'13:30:00'` and the example is `'15:30:00'`), and `irrelevance_239` (the function says a time difference while the unit measures distance, and the second location repeats the first city's wording).

Fourteen two-tool catalogues were read from each tool's own description. None receives a cue. The pairs do not answer a similar request: a sports ranking and air quality, restaurants and precipitation, the current time and a stock, historical events and a sculpture's value, a team ranking and a person's earliest reference, player statistics and a building analysis, museum artworks and lawsuits, Walmart items and a musical scale, a poker full-house probability and a basketball winner, a sports ranking and compound interest, chess players and a sushi restaurant, a recipe and a scientific discovery, emission savings and a time-zone conversion, and a forest forecast and database records. Sharing a location, as in `multiple_146` and `multiple_185`, is not a selection axis.

`multiple_185` drops "default value is 10" on `number_of_players` because the schema default is 10. That edit comes from the chess tool's own description. X stays equal to U because there is no cue.

## Seventh tranche

114 multi-tool cases were added. The first 714 were not rewritten. The formative twelve were left unsealed. Their pilot S and X were not copied.

Sixteen catalogues receive a cue because every tool shares an action and the sources document the difference: areas in `multiple_1` and `multiple_30`, weather in `multiple_5` and `multiple_64`, currency conversion in `multiple_17`, European history in `multiple_18` and `multiple_70`, religious events in `multiple_19`, NBA point records in `multiple_22`, basketball statistics in `multiple_23`, game facts in `multiple_26` and `multiple_87`, chance devices in `multiple_51`, football goal figures in `multiple_83`, food searches in `multiple_89`, and travel prices in `multiple_94`. Each cue names one rival. Where two rivals were the same kind of alternative, catalogue order selected the earlier tool.

`multiple_30` also drops "default is false" on `isDiameter` because the schema default is false. That edit comes from the circle tool's own description. The cue is a separate judgement about the shape. SX is the S text plus the cue, so U, S, X, and SX are four catalogues.

98 catalogues have an empty cue. A square can already be read as a rectangle in `multiple_31`. A unit conversion can already be read as covering a currency conversion in `multiple_44`. A future value can already be read as covering compound or simple interest in `multiple_49`. An event search can already be read as covering movie showtimes in `multiple_60`. A search in a given library can already cover Google Books or the Open Library in `multiple_68`. Statistical or demographic data can already be read as covering population in `multiple_71`. A tourist attraction can already be a park in `multiple_77`. `multiple_34` and `multiple_37` each contain a closer pair, but another tool in the same catalogue does not share that action, and a cue has to cover every tool. The remaining empty cues are catalogues whose tools do not answer a similar request.

Six catalogues change S. `multiple_127` and `multiple_165` drop the frame "This function". `multiple_20`, `multiple_165`, `multiple_177`, and `multiple_187` omit a schema default. `multiple_43` states a glucose-specific default of 2800 kJ/mol while the schema default is the integer 2800. That mismatch stays.

## What is still open

The remaining 12 cases are the formative twelve. They have no sealed S and no sealed X. Their pilot seals were not copied. They wait for an independent reading from U.
