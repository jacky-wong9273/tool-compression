"""Sealed editorial decisions for the first official-840 tranche.

S specifications and X specifications are separate dictionaries. Cue text is
not derived from an S replacement. Questions are not inputs.

This is a partial seal. Every other case stays in the remaining-work manifest.
"""

from __future__ import annotations

from pathlib import Path

from tool_compression.adapter import description_slots
from tool_compression.semantic_audit import get_text, load_json

SAMPLE = "official-840"
SEALED_IDS = (
    "multiple_2",
    "multiple_4",
    "multiple_9",
    "multiple_21",
    "multiple_24",
    "multiple_27",
    "multiple_28",
    "multiple_33",
    "multiple_45",
    "multiple_57",
    "multiple_73",
    "multiple_99",
    "simple_python_0",
    "simple_python_1",
    "simple_python_2",
    "irrelevance_0",
    "irrelevance_1",
    "irrelevance_2",
)

# Own-tool S edits. Absent keys stay verbatim. Sibling names are not inputs.
CHANGES = {
    ("multiple_9", 0, "/function/description"): {
        "replacement": "Calculate the standard deviation across different scores for a specific student.",
        "reason": "The frame 'This function calculates' is not a separate claim. The replacement keeps the statistic, the scores, and the student.",
    },
    ("multiple_9", 1, "/function/description"): {
        "replacement": "Calculate the average grade across different subjects for a specific student.",
        "reason": "The frame 'This function calculates' is not a separate claim. The replacement keeps the average, the subjects, and the student.",
    },
    ("multiple_9", 2, "/function/description"): {
        "replacement": "Find the subject where the student got the highest score.",
        "reason": "The frame 'This function finds' is not a separate claim. The replacement keeps the subject, the student, and the highest score.",
    },
    ("multiple_21", 0, "/function/description"): {
        "replacement": "Play a sound wave file.",
        "reason": "The frame 'This function is for' is not a separate claim. The replacement keeps playing a sound wave file.",
    },
    ("multiple_21", 1, "/function/description"): {
        "replacement": "Generate a sinusoidal sound wave file of a certain frequency for a specific duration and save it to a WAV file.",
        "reason": "The frame 'This function is for' is not a separate claim. The replacement keeps generate, sinusoidal, frequency, duration, and WAV. The sinusoidal wording stays even though wave_type lists other waveforms.",
    },
    ("multiple_24", 0, "/function/parameters/properties/method/description"): {
        "replacement": "The method to use when calculating the route.",
        "reason": "The parenthetical repeats the schema default fastest. The replacement keeps that this argument chooses the route method. The enum values stay in the schema and are not copied into the prose.",
        "parts": [
            {
                "excerpt": "The method to use when calculating the route",
                "decision": "KEEP",
                "after": "The method to use when calculating the route.",
            },
            {
                "excerpt": "(default is 'fastest')",
                "duplicate": True,
                "schema_path": "/function/parameters/properties/method/default",
                "schema_equals": "fastest",
                "note": "The schema default is the string fastest. The quotes in the prose are not a second fact.",
            },
        ],
    },
    ("multiple_73", 0, "/function/parameters/properties/religion/description"): {
        "replacement": "Name of the religion.",
        "reason": "The trailing clause repeats the function description. The replacement keeps that the argument is the religion's name. Beliefs and practices remain on the function description.",
        "parts": [
            {
                "excerpt": "Name of the religion",
                "decision": "KEEP",
                "after": "Name of the religion.",
            },
            {
                "excerpt": "for which to retrieve the core beliefs and practices",
                "duplicate": True,
                "recovery_pointer": "/function/description",
                "recovery_excerpt": "core beliefs and practices",
                "note": "The function description still says core beliefs and practices.",
            },
        ],
    },
    ("multiple_73", 1, "/function/parameters/properties/religion/description"): {
        "replacement": "Name of the religion.",
        "reason": "The trailing clause repeats the function description. The replacement keeps that the argument is the religion's name. Origin and founder remain on the function description.",
        "parts": [
            {
                "excerpt": "Name of the religion",
                "decision": "KEEP",
                "after": "Name of the religion.",
            },
            {
                "excerpt": "for which to retrieve the founder and origin",
                "duplicate": True,
                "recovery_pointer": "/function/description",
                "recovery_excerpt": "origin and founder",
                "note": "The function description says origin and founder. The parameter's word order is the duplicate, not a second fact.",
            },
        ],
    },
    ("multiple_99", 0, "/function/parameters/properties/function_variable/description"): {
        "replacement": "The variable present in the function. Default is 'x'.",
        "reason": "The examples x and y are open-ended illustration. The replacement keeps that the argument is the variable in the function, and it keeps the default x, which the schema does not state.",
        "parts": [
            {
                "excerpt": "The variable present in the function",
                "decision": "KEEP",
                "after": "The variable present in the function.",
            },
            {
                "excerpt": ", for instance x or y, etc.",
                "illustrative": True,
                "note": "The examples are not a closed input format. The sentence says etc.",
            },
            {
                "excerpt": "Default is 'x'",
                "decision": "KEEP",
                "after": "Default is 'x'.",
                "note": "The schema has no default. The prose default stays.",
            },
        ],
    },
}

CONFLICTS = {
    ("multiple_9", 0, "/function/parameters/properties/gradeDict/description"): [
        "Prose says dictionary. Schema type is object. Left as written."
    ],
    ("multiple_9", 1, "/function/parameters/properties/gradeDict/description"): [
        "Prose says dictionary. Schema type is object. Left as written."
    ],
    ("multiple_9", 2, "/function/parameters/properties/gradeDict/description"): [
        "Prose says dictionary. Schema type is object. Left as written."
    ],
    ("multiple_21", 1, "/function/description"): [
        "The function description says sinusoidal. wave_type also lists square and sawtooth, and its default is sine. Left unrepaired."
    ],
    ("multiple_57", 1, "/function/parameters/properties/time/description"): [
        "The time description says the money is to be compounded. The function description says simple interest. Left unrepaired."
    ],
    ("simple_python_1", 0, "/function/parameters/properties/number/description"): [
        "Prose says number. Schema type is integer. Left as written."
    ],
    ("simple_python_2", 0, "/function/description"): [
        "The function description names the point (x, y). The schema also has an optional z coordinate. Left unrepaired."
    ],
    ("irrelevance_1", 0, "/function/parameters/properties/numbers/description"): [
        "Prose says list. Schema type is array. Left as written."
    ],
}

CUES = {
    "multiple_2": {
        "case_reason": "Three fetch tools on one country. The two city facts share an action and a resource. Population is a different returned fact, so its rival is the earlier city tool.",
        "tools": {
            0: {
                "cue": "Unlike country_info_capital, which fetches the capital city, this fetches the largest city.",
                "rival_index": 1,
                "axis": "which city fact of the country is fetched",
                "why_confusable": "Both fetch a city of a specified country. A request that only says the country's city can be read as either.",
                "why_this_rival": "Capital is the same action on the same resource, a city of the country. Population returns a count, so it is not the closer rival.",
                "rejected": ["country_info_population returns a count, not a city."],
                "target_excerpt": "largest city",
                "rival_excerpt": "capital city",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request that says capital or largest city makes only one description true. A request that only says the country's city can be read as either, and the cue names which city fact.",
            },
            1: {
                "cue": "Unlike country_info_largest_city, which fetches the largest city, this fetches the capital city.",
                "rival_index": 0,
                "axis": "which city fact of the country is fetched",
                "why_confusable": "Both fetch a city of a specified country.",
                "why_this_rival": "Largest city is the other city fact. Population is a count.",
                "rejected": ["country_info_population is a different returned fact."],
                "target_excerpt": "capital city",
                "rival_excerpt": "largest city",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "The two city descriptions are not included in each other. The cue names the city fact a vague request left open.",
            },
            2: {
                "cue": "Unlike country_info_largest_city, which fetches the largest city, this fetches the current population.",
                "rival_index": 0,
                "axis": "whether the returned country fact is a city or the current population",
                "why_confusable": "All three tools fetch a fact about a specified country. An underspecified country request can be offered to any of them.",
                "why_this_rival": "The two city tools are the same kind of alternative to a population count. Catalogue order selects the earlier city tool.",
                "rejected": ["Naming both city tools in one cue.", "Using country_info_capital, which is the later city tool."],
                "target_excerpt": "current population",
                "rival_excerpt": "largest city",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request for the population does not make the largest-city description true. A request that only names the country can be read as either, and the cue names the returned fact. Current stays in the cue because the source says current population.",
            },
        },
    },
    "multiple_4": {
        "case_reason": "Both tools take an initial speed, an acceleration, and a time. The selection axis is the quantity they return.",
        "tools": {
            0: {
                "cue": "Unlike kinematics_calculate_final_speed, which calculates the final speed, this calculates displacement.",
                "rival_index": 1,
                "axis": "which kinematic quantity is calculated",
                "why_confusable": "Both calculate a straight-line motion quantity from initial speed, acceleration, and time.",
                "why_this_rival": "Only one other tool, and it states the other quantity.",
                "rejected": ["The rounding argument is shared machinery, not the selection axis."],
                "target_excerpt": "displacement",
                "rival_excerpt": "final speed",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request that only says the object accelerated for a time can be read as asking for either quantity. A request that names displacement does not make the final-speed description true.",
            },
            1: {
                "cue": "Unlike kinematics_calculate_displacement, which calculates displacement, this calculates the final speed.",
                "rival_index": 0,
                "axis": "which kinematic quantity is calculated",
                "why_confusable": "Both calculate a straight-line motion quantity from initial speed, acceleration, and time.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["Do not treat float versus integer parameter types as the reason to choose a tool."],
                "target_excerpt": "final speed",
                "rival_excerpt": "displacement",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "The descriptions name different quantities. The cue repeats that difference and does not say either tool rejects a duration.",
            },
        },
    },
    "multiple_9": {
        "case_reason": "All three read one grade dictionary. Standard deviation and average are the same action, a statistic over the scores. The highest-score tool finds a subject instead.",
        "tools": {
            0: {
                "cue": "Unlike calculate_average, which calculates the average grade, this calculates the standard deviation.",
                "rival_index": 1,
                "axis": "which statistic of the scores is calculated",
                "why_confusable": "Both calculate a statistic from the same kind of subject-to-score dictionary for one student.",
                "why_this_rival": "Average is the same action, a summary statistic. Finding the subject with the highest score is a different action.",
                "rejected": ["highest_grade returns a subject, not a statistic."],
                "target_excerpt": "standard deviation",
                "rival_excerpt": "average grade",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request to summarize the scores can be read as either statistic. The descriptions are not included in each other: an average is not a standard deviation.",
            },
            1: {
                "cue": "Unlike calculate_standard_deviation, which calculates the standard deviation, this calculates the average grade.",
                "rival_index": 0,
                "axis": "which statistic of the scores is calculated",
                "why_confusable": "Both calculate a statistic from the same kind of grade dictionary.",
                "why_this_rival": "Standard deviation is the same action. The subject-finding tool is a different action.",
                "rejected": ["highest_grade is a different action."],
                "target_excerpt": "average grade",
                "rival_excerpt": "standard deviation",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request for the student's overall grade can be read as the average. The cue names that statistic against the spread.",
            },
            2: {
                "cue": "Unlike calculate_standard_deviation, which calculates the standard deviation, this finds the subject with the highest score.",
                "rival_index": 0,
                "axis": "whether the result is a statistic or the subject with the highest score",
                "why_confusable": "All three read the same grade dictionary. A request about how the student did can be offered to a statistic or to the top subject.",
                "why_this_rival": "Both statistics are the same kind of alternative to finding a subject. Catalogue order selects the earlier statistic.",
                "rejected": ["Naming both statistics in one cue.", "Using calculate_average, which is the later statistic."],
                "target_excerpt": "highest score",
                "rival_excerpt": "standard deviation",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request for the strongest subject does not make the standard-deviation description true. A vague request about the scores can be read as either, and the cue names a subject rather than a spread.",
            },
        },
    },
    "multiple_21": {
        "case_reason": "Both tools are about a sound wave file. One plays an existing file. The other generates a file.",
        "tools": {
            0: {
                "cue": "Unlike generate_sound_wave, which generates a sound wave file, this plays a sound wave file.",
                "rival_index": 1,
                "axis": "whether an existing sound wave file is played or a new file is generated",
                "why_confusable": "Both concern a sound wave file. A request that only says sound wave can be read as either.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["Do not turn the generator's sinusoidal wording into a claim that playback rejects other waveforms."],
                "target_excerpt": "playing a sound wave file",
                "rival_excerpt": "generating a sinusoidal sound wave file",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "Play and generate can both be read as true of a request that only says sound wave. The cue names the action. It does not say playback is unable to generate.",
            },
            1: {
                "cue": "Unlike play_sound_wave, which plays a sound wave file, this generates a sound wave file.",
                "rival_index": 0,
                "axis": "whether a sound wave file is generated or an existing file is played",
                "why_confusable": "Both concern a sound wave file.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["The waveform enum is an argument of generation, not a contrast with playback."],
                "target_excerpt": "generating a sinusoidal sound wave file",
                "rival_excerpt": "playing a sound wave file",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "The generator description adds frequency, duration, and WAV. Those stay in the original. The cue's one difference is generate versus play.",
            },
        },
    },
    "multiple_27": {
        "case_reason": "Both tools take a trip and a mode of transportation. One estimates travel time. The other finds the shortest path.",
        "tools": {
            0: {
                "cue": "Unlike maps_shortest_path, which finds the shortest path, this estimates the travel time.",
                "rival_index": 1,
                "axis": "whether the result is a travel time or the shortest path",
                "why_confusable": "Both answer a from-here-to-there request with the same listed modes.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["The mode list is shared, so it is not the selection axis."],
                "target_excerpt": "time it will take to travel",
                "rival_excerpt": "shortest path",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request to get from one place to another can be read as asking for a duration or for a path. The cue names which result.",
            },
            1: {
                "cue": "Unlike maps_route_times, which estimates the travel time, this finds the shortest path.",
                "rival_index": 0,
                "axis": "whether the result is the shortest path or a travel time",
                "why_confusable": "Both answer a from-here-to-there request.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["Start and end location wording is an argument difference, not the selection axis."],
                "target_excerpt": "shortest path",
                "rival_excerpt": "time it will take to travel",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "Shortest path and travel time are both documented results. The cue does not say either tool rejects a mode.",
            },
        },
    },
    "multiple_33": {
        "case_reason": "Both tools take a single-variable function. One calculates a derivative. The other calculates a definite integral.",
        "tools": {
            0: {
                "cue": "Unlike calculate_integral, which calculates the definite integral, this calculates the derivative.",
                "rival_index": 1,
                "axis": "whether the operation is a derivative or a definite integral",
                "why_confusable": "Both operate on a single-variable function. A request that only says to do the calculus can be read as either.",
                "why_this_rival": "Only one other tool, and the function descriptions name the two operations.",
                "rejected": ["Do not contrast the class word calculus. A derivative is not a definite integral, and the cue names the operation."],
                "target_excerpt": "derivative",
                "rival_excerpt": "definite integral",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request for the derivative does not make the definite-integral description true. A request that only names the function can be read as either. The cue uses the operation, not a nested class label.",
            },
            1: {
                "cue": "Unlike calculate_derivative, which calculates the derivative, this calculates the definite integral.",
                "rival_index": 0,
                "axis": "whether the operation is a definite integral or a derivative",
                "why_confusable": "Both operate on a single-variable function.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["The bounds versus an x value follow the operation. They are not a second cue."],
                "target_excerpt": "definite integral",
                "rival_excerpt": "derivative",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "Definite integral is the source's own qualifier. The cue keeps it so the contrast is not any integral against any derivative.",
            },
        },
    },
    "multiple_45": {
        "case_reason": "Both tools return a date and share a years-ago flag. One dates a geological era. The other dates a historical event.",
        "tools": {
            0: {
                "cue": "Unlike history_get_event_date, which gets the date of a historical event, this gets the estimated date of a geological era.",
                "rival_index": 1,
                "axis": "whether the dated thing is a geological era or a historical event",
                "why_confusable": "Both get a date. A request that only says when something was can be read as either domain.",
                "why_this_rival": "Only one other tool. The shared years-ago flag is the same fact, so it is not the axis.",
                "rejected": ["The shared boolean is not a difference."],
                "target_excerpt": "geological era",
                "rival_excerpt": "historical event",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "An era name does not make the historical-event description true, and an event name does not make the era description true. An ambiguous when-was-it request can be read as either, and the cue names the domain. Estimated stays because the era description says estimated.",
            },
            1: {
                "cue": "Unlike geology_get_era, which gets the estimated date of a geological era, this gets the date of a historical event.",
                "rival_index": 0,
                "axis": "whether the dated thing is a historical event or a geological era",
                "why_confusable": "Both get a date.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["Do not treat the shared default on the years-ago flag as the reason to choose a tool."],
                "target_excerpt": "historical event",
                "rival_excerpt": "geological era",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "The source says an historical event. The cue's 'a historical event' keeps that noun and does not add a century, a place, or an exclusion.",
            },
        },
    },
    "multiple_57": {
        "case_reason": "Both tools calculate interest from a principal, a rate, and a time. One is compound interest. The other is simple interest.",
        "tools": {
            0: {
                "cue": "Unlike financial_simple_interest, which calculates simple interest, this calculates compound interest.",
                "rival_index": 1,
                "axis": "whether the interest is compound or simple",
                "why_confusable": "Both calculate interest from an initial amount, an annual rate, and a time in years.",
                "why_this_rival": "Only one other tool, and the function descriptions name the two interest types.",
                "rejected": ["The compounding frequency n is an argument of compound interest, not a contrast that simple interest lacks a rate."],
                "target_excerpt": "compound interest",
                "rival_excerpt": "simple interest",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request that only says interest can be read as either type. Compound and simple are alternate types, not a class and a subclass. The cue names the type.",
            },
            1: {
                "cue": "Unlike financial_compound_interest, which calculates compound interest, this calculates simple interest.",
                "rival_index": 0,
                "axis": "whether the interest is simple or compound",
                "why_confusable": "Both calculate interest from an initial amount, an annual rate, and a time in years.",
                "why_this_rival": "Only one other tool. The function description is the selection text.",
                "rejected": [
                    "The simple-interest time sentence says compounded. That conflicts with this function description and is not used as the axis."
                ],
                "target_excerpt": "simple interest",
                "rival_excerpt": "compound interest",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "The cue follows the function description, which says simple interest. It does not repeat the conflicting time sentence and does not say either tool rejects a principal.",
            },
        },
    },
    "multiple_73": {
        "case_reason": "Both tools look up one religion. One returns core beliefs and practices. The other returns origin and founder.",
        "tools": {
            0: {
                "cue": "Unlike religion_get_origin, which retrieves the origin and founder, this retrieves the core beliefs and practices.",
                "rival_index": 1,
                "axis": "whether the religion fact is the core beliefs and practices or the origin and founder",
                "why_confusable": "Both retrieve a fact about a specified religion. A request that only names the religion can be read as either.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["Do not drop practices or founder. Each description states both halves of its fact."],
                "target_excerpt": "core beliefs and practices",
                "rival_excerpt": "origin and founder",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "Beliefs and origin can both be true of a request that only names the religion. The cue keeps practices with beliefs and founder with origin, which is what the sources say.",
            },
            1: {
                "cue": "Unlike religion_get_core_beliefs, which retrieves the core beliefs and practices, this retrieves the origin and founder.",
                "rival_index": 0,
                "axis": "whether the religion fact is the origin and founder or the core beliefs and practices",
                "why_confusable": "Both retrieve a fact about a specified religion.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["The parameter name religion is shared, so it is not the axis."],
                "target_excerpt": "origin and founder",
                "rival_excerpt": "core beliefs and practices",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request for the founder does not make the beliefs description true. The cue still separates the two facts when the request only names the religion.",
            },
        },
    },
}

def _single(case_id: str) -> str:
    return (
        f"{case_id} has one tool. There is no second description, so no rival, axis, or cue location qualifies."
    )


UNCUE = {
    "multiple_24": {
        "case_reason": "A route between two points and the details of a chess club do not answer a similar request. The word location in the chess-club description is not a route.",
        "tools": {
            0: "Calculates a route between two points. The other tool returns details of a named chess club. No shared action or resource is documented.",
            1: "Returns details of a chess club, including location. The other tool calculates a route. A location is not a route, so no selection cue is written.",
        },
    },
    "multiple_28": {
        "case_reason": "Quadratic roots, an RGB-to-hex conversion, and reversing a string do not share an action or a resource.",
        "tools": {
            0: "Solves a quadratic equation. Neither an RGB conversion nor string reversal documents a shared selection axis with that equation.",
            1: "Converts RGB values to a hexadecimal color. Quadratic roots and string reversal are not color conversions.",
            2: "Reverses a string. Quadratic roots and an RGB conversion are not string operations on the same resource.",
        },
    },
    "multiple_99": {
        "case_reason": "A derivative at a value and a personality-trait lookup do not answer a similar request.",
        "tools": {
            0: "Computes a derivative of a function at a value. The other tool retrieves personality traits. No shared action or resource is documented.",
            1: "Retrieves personality traits for a personality type. The other tool computes a derivative. No selection cue is written.",
        },
    },
    "simple_python_0": {"case_reason": _single("simple_python_0"), "tools": None},
    "simple_python_1": {"case_reason": _single("simple_python_1"), "tools": None},
    "simple_python_2": {"case_reason": _single("simple_python_2"), "tools": None},
    "irrelevance_0": {"case_reason": _single("irrelevance_0"), "tools": None},
    "irrelevance_1": {"case_reason": _single("irrelevance_1"), "tools": None},
    "irrelevance_2": {"case_reason": _single("irrelevance_2"), "tools": None},
}


def _keep_reason(text: str) -> str:
    if "This is a float type value." in text and ("E.g." in text or "e.g." in text or "e.g " in text):
        return "The handler float sentence stays, and the input example stays with it. Neither is cut."
    if "This is a float type value." in text:
        return "The handler float sentence stays. The unit or scale beside it stays too."
    if "e.g" in text or "E.g." in text or "for instance" in text:
        return "An example in the description may be an input format. The example and the claim beside it stay."
    lowered = text.lower()
    if "default" in lowered or "optional" in lowered:
        return "The description states an optional argument or a default. That wording stays."
    return "Left verbatim. The string is one claim, and a shorter wording would drop its quantity, unit, condition, or argument role."


def _proposition(case_id: str, tool_index: int, pointer: str, ordinal: int, excerpt: str, start: int, **flags) -> dict:
    proposition = {
        "id": f"{case_id}/t{tool_index}{pointer}#{ordinal}",
        "excerpt": excerpt,
        "span": [start, start + len(excerpt)],
        "role": "both" if pointer == "/function/description" else "use",
        "decision": flags.get("decision", "KEEP"),
        "kind": "statement",
        "recovery": "verbatim",
        "lost": False,
        "unsupported": False,
        "uncertain": False,
        "duplicate": bool(flags.get("duplicate")),
        "illustrative": bool(flags.get("illustrative")),
        "note": flags.get("note", ""),
    }
    if "after" in flags:
        proposition["after"] = flags["after"]
    if flags.get("schema_path"):
        proposition["schema_path"] = flags["schema_path"]
        proposition["schema_equals"] = flags["schema_equals"]
        proposition["recovery"] = "schema"
    if flags.get("recovery_pointer"):
        proposition["recovery_pointer"] = flags["recovery_pointer"]
        proposition["recovery_excerpt"] = flags["recovery_excerpt"]
        proposition["recovery"] = "sibling-slot-same-tool"
    return proposition


def _span_parts(case_id: str, tool_index: int, pointer: str, original: str, parts: list[dict]) -> list[dict]:
    cursor = 0
    propositions = []
    for ordinal, part in enumerate(parts):
        excerpt = part["excerpt"]
        start = original.find(excerpt, cursor)
        if start < 0:
            raise ValueError(f"excerpt not found {case_id} {pointer} {excerpt!r}")
        cursor = start + len(excerpt)
        flags = {key: value for key, value in part.items() if key != "excerpt"}
        propositions.append(_proposition(case_id, tool_index, pointer, ordinal, excerpt, start, **flags))
    return propositions


def _field(case_id: str, tool_index: int, name: str, pointer: str, original: str) -> dict:
    key = (case_id, tool_index, pointer)
    change = CHANGES.get(key)
    conflicts = list(CONFLICTS.get(key, []))
    if change is None:
        return {
            "case_id": case_id,
            "tool_index": tool_index,
            "function_name": name,
            "pointer": pointer,
            "decision": "KEEP",
            "noop": True,
            "reason": _keep_reason(original),
            "original": original,
            "replacement": original,
            "conflicts": conflicts,
            "propositions": [
                _proposition(
                    case_id,
                    tool_index,
                    pointer,
                    0,
                    original,
                    0,
                    decision="KEEP",
                    after=original,
                    note="Left verbatim.",
                )
            ],
        }
    replacement = change["replacement"]
    if replacement == original:
        raise ValueError(f"change does not edit {case_id} {pointer}")
    parts = change.get("parts")
    if parts:
        propositions = _span_parts(case_id, tool_index, pointer, original, parts)
    else:
        propositions = [
            _proposition(
                case_id,
                tool_index,
                pointer,
                0,
                original,
                0,
                decision="CONDENSE",
                after=replacement,
                note=change["reason"],
            )
        ]
    return {
        "case_id": case_id,
        "tool_index": tool_index,
        "function_name": name,
        "pointer": pointer,
        "decision": "CONDENSE",
        "noop": False,
        "reason": change["reason"],
        "original": original,
        "replacement": replacement,
        "conflicts": conflicts + list(change.get("conflicts", [])),
        "propositions": propositions,
    }


def _cue_tool(case_id: str, tools: list[dict], index: int, spec: dict | None, no_cue_reason: str | None) -> dict:
    tool = tools[index]
    name = tool["function"]["name"]
    base = {
        "tool_index": index,
        "function_name": name,
        "pointer": "/function/description",
    }
    if spec is None:
        base["cue"] = ""
        base["no_cue_reason"] = no_cue_reason
        return base
    rival = tools[spec["rival_index"]]
    description = get_text(tool, "/function/description")
    rival_description = get_text(rival, "/function/description")
    target_excerpt = spec["target_excerpt"]
    rival_excerpt = spec["rival_excerpt"]
    target_at = description.find(target_excerpt)
    rival_at = rival_description.find(rival_excerpt)
    if target_at < 0 or rival_at < 0:
        raise ValueError(f"cue excerpt missing {case_id} t{index}")
    base.update(
        {
            "cue": spec["cue"],
            "target": {
                "tool_index": index,
                "pointer": "/function/description",
                "excerpt": target_excerpt,
            },
            "rival": {
                "tool_index": spec["rival_index"],
                "function_name": rival["function"]["name"],
                "pointer": "/function/description",
                "excerpt": rival_excerpt,
                "axis": spec["axis"],
                "why_confusable": spec["why_confusable"],
                "why_this_rival": spec["why_this_rival"],
                "rejected": list(spec["rejected"]),
            },
            "same_request": {
                "both_descriptions_can_fit": spec["both_can_fit"],
                "cue_still_helps": spec["cue_still_helps"],
                "implies_unsupported_exclusion": False,
                "note": spec["note"],
            },
            "propositions": [
                _proposition(
                    case_id,
                    index,
                    "/function/description",
                    0,
                    target_excerpt,
                    target_at,
                    decision="KEEP",
                    note="Target fact cited by the cue.",
                )
                | {"kind": "cue-target", "source_tool_index": index, "source_pointer": "/function/description"},
                _proposition(
                    case_id,
                    spec["rival_index"],
                    "/function/description",
                    1,
                    rival_excerpt,
                    rival_at,
                    decision="KEEP",
                    note="Rival fact cited by the cue, from that tool's original description.",
                )
                | {
                    "kind": "cue-rival",
                    "source_tool_index": spec["rival_index"],
                    "source_pointer": "/function/description",
                },
            ],
        }
    )
    return base


def build_records(catalogues: dict[str, list[dict]], categories: dict[str, str]) -> tuple[dict, dict]:
    """Build the S and X records from stored U catalogues. Cue literals are not read from S."""
    if set(catalogues) < set(SEALED_IDS):
        missing = [case_id for case_id in SEALED_IDS if case_id not in catalogues]
        raise ValueError(f"sealed ids missing from U: {missing}")
    overlap = set(CUES) & set(UNCUE)
    if overlap or set(CUES) | set(UNCUE) != set(SEALED_IDS):
        raise ValueError("cue and no-cue maps must partition the sealed ids")
    s_cases = []
    x_cases = []
    for case_id in SEALED_IDS:
        tools = catalogues[case_id]
        names = [tool["function"]["name"] for tool in tools]
        fields = []
        for index, tool in enumerate(tools):
            for pointer, _container, _key in description_slots(tool):
                original = get_text(tool, pointer)
                fields.append(_field(case_id, index, names[index], pointer, original))
        for field in fields:
            if "Unlike " in field["replacement"]:
                raise ValueError(f"S contains a cross-tool cue {case_id}")
            for other, name in enumerate(names):
                if other != field["tool_index"] and name in field["replacement"]:
                    raise ValueError(f"S names sibling {name} {case_id}")
        s_cases.append({"case_id": case_id, "category": categories[case_id], "fields": fields})
        if case_id in CUES:
            block = CUES[case_id]
            if set(block["tools"]) != set(range(len(tools))):
                raise ValueError(f"cue tools do not cover {case_id}")
            x_tools = [
                _cue_tool(case_id, tools, index, block["tools"][index], None) for index in range(len(tools))
            ]
            cue_applied = True
        else:
            block = UNCUE[case_id]
            if len(tools) == 1:
                reasons = {0: block["case_reason"]}
            else:
                reasons = block["tools"]
                if set(reasons) != set(range(len(tools))):
                    raise ValueError(f"no-cue tools do not cover {case_id}")
            x_tools = [
                _cue_tool(case_id, tools, index, None, reasons[index]) for index in range(len(tools))
            ]
            cue_applied = False
        x_cases.append(
            {
                "case_id": case_id,
                "category": categories[case_id],
                "cue_applied": cue_applied,
                "case_reason": block["case_reason"],
                "tools": x_tools,
            }
        )
    s_record = {
        "sample": SAMPLE,
        "record": "S",
        "editor": "single editor, blinded by tool index",
        "reviewer": "same editor, before/after reread of the changed strings",
        "independent_review": False,
        "questions_used": False,
        "siblings_hidden_while_building_s": True,
        "blinding": "The first 18 cases were read one tool at a time, and sibling tools were opened in a later index round. Later one-tool cases have no sibling. For the added multi-tool cases, each S string was taken from that tool's own description. The S edits among them are frame deletions on multiple_10, multiple_127, and multiple_165, and schema-default omissions on multiple_0, multiple_20, multiple_30, multiple_97, multiple_100, multiple_142, multiple_165, multiple_177, multiple_185, and multiple_187. No S replacement names a sibling or uses a sibling's wording.",
        "self_review": {
            "method": "The changed before/after strings were reread with the decision notes set aside.",
            "revisions_before_seal": [],
            "note": "The reread did not change a replacement.",
        },
        "cases": s_cases,
    }
    cued_ids = [case_id for case_id in SEALED_IDS if case_id in CUES]
    uncued_ids = [case_id for case_id in SEALED_IDS if case_id in UNCUE]
    single_uncued = [case_id for case_id in uncued_ids if len(catalogues[case_id]) == 1]
    multi_uncued = [case_id for case_id in uncued_ids if len(catalogues[case_id]) != 1]
    x_record = {
        "sample": SAMPLE,
        "record": "X",
        "s_record": "docs/official-840/edits/s-record.json",
        "s_used_as_cue_source": False,
        "separator": " ",
        "pointer": "/function/description",
        "parameter_edits": False,
        "source": "Original converted descriptions and schemas. S replacement text was not an input to the cue wording.",
        "editor": "same editor, after S was specified",
        "reviewer": "same editor",
        "independent_review": False,
        "questions_used": False,
        "review_question": "Could both descriptions be true of the same request, and if so, does this cue still help the reader choose?",
        "success_is_not_shorter_wording": True,
        "coverage_is_not_efficiency": True,
        "coverage": {
            "sealed_cases": len(SEALED_IDS),
            "cued_cases": len(cued_ids),
            "uncued_cases": len(uncued_ids),
            "uncued_single_tool": len(single_uncued),
            "uncued_multi_tool": len(multi_uncued),
            "cued_ids": cued_ids,
            "uncued_ids": uncued_ids,
            "uncued_single_tool_ids": single_uncued,
            "uncued_multi_tool_ids": multi_uncued,
            "note": "These denominators are the sealed cases. Coverage is not cue efficiency. Shorter wording is not the success criterion.",
        },
        "cases": x_cases,
    }
    return s_record, x_record


def _merge_second_tranche():
    """Add the second tranche and put every sealed id back into file order."""
    from tool_compression.official_840_tranche_b import (
        ADDED_CHANGES,
        ADDED_CONFLICTS,
        ADDED_CUES,
        ADDED_IDS,
        ADDED_SINGLES,
        ADDED_UNCUE,
    )

    if set(ADDED_IDS) & set(SEALED_IDS):
        raise ValueError("second tranche overlaps the first sealed ids")
    CHANGES.update(ADDED_CHANGES)
    CONFLICTS.update(ADDED_CONFLICTS)
    if set(ADDED_CUES) & set(CUES) or set(ADDED_UNCUE) & set(UNCUE):
        raise ValueError("second tranche repeats a cue or no-cue case")
    CUES.update(ADDED_CUES)
    UNCUE.update(ADDED_UNCUE)
    for case_id in ADDED_SINGLES:
        if case_id in CUES or case_id in UNCUE:
            raise ValueError(f"single-tool case already specified {case_id}")
        UNCUE[case_id] = {"case_reason": _single(case_id), "tools": None}
    manifest = load_json(Path(__file__).resolve().parents[2] / "docs" / "official-840" / "selection" / "manifest.json")
    wanted = set(SEALED_IDS) | set(ADDED_IDS)
    ordered = tuple(case_id for case_id in manifest["ids_in_file_order"] if case_id in wanted)
    if len(ordered) != len(wanted):
        missing = sorted(wanted - set(ordered))
        raise ValueError(f"sealed ids missing from the manifest: {missing}")
    return ordered


SEALED_IDS = _merge_second_tranche()


def _merge_third_tranche():
    """Add the third tranche and put every sealed id back into file order."""
    from tool_compression.official_840_tranche_c import (
        ADDED_CHANGES,
        ADDED_CONFLICTS,
        ADDED_CUES,
        ADDED_IDS,
        ADDED_SINGLES,
        ADDED_UNCUE,
    )

    if set(ADDED_IDS) & set(SEALED_IDS):
        raise ValueError("third tranche overlaps an earlier sealed id")
    CHANGES.update(ADDED_CHANGES)
    CONFLICTS.update(ADDED_CONFLICTS)
    if set(ADDED_CUES) & set(CUES) or set(ADDED_UNCUE) & set(UNCUE):
        raise ValueError("third tranche repeats a cue or no-cue case")
    CUES.update(ADDED_CUES)
    UNCUE.update(ADDED_UNCUE)
    for case_id in ADDED_SINGLES:
        if case_id in CUES or case_id in UNCUE:
            raise ValueError(f"single-tool case already specified {case_id}")
        UNCUE[case_id] = {"case_reason": _single(case_id), "tools": None}
    manifest = load_json(Path(__file__).resolve().parents[2] / "docs" / "official-840" / "selection" / "manifest.json")
    wanted = set(SEALED_IDS) | set(ADDED_IDS)
    ordered = tuple(case_id for case_id in manifest["ids_in_file_order"] if case_id in wanted)
    if len(ordered) != len(wanted):
        missing = sorted(wanted - set(ordered))
        raise ValueError(f"sealed ids missing from the manifest: {missing}")
    return ordered


SEALED_IDS = _merge_third_tranche()


def _merge_fourth_tranche():
    """Add the fourth tranche and put every sealed id back into file order."""
    from tool_compression.official_840_tranche_d import (
        ADDED_CHANGES,
        ADDED_CONFLICTS,
        ADDED_CUES,
        ADDED_IDS,
        ADDED_SINGLES,
        ADDED_UNCUE,
    )

    if set(ADDED_IDS) & set(SEALED_IDS):
        raise ValueError("fourth tranche overlaps an earlier sealed id")
    CHANGES.update(ADDED_CHANGES)
    CONFLICTS.update(ADDED_CONFLICTS)
    if set(ADDED_CUES) & set(CUES) or set(ADDED_UNCUE) & set(UNCUE):
        raise ValueError("fourth tranche repeats a cue or no-cue case")
    CUES.update(ADDED_CUES)
    UNCUE.update(ADDED_UNCUE)
    for case_id in ADDED_SINGLES:
        if case_id in CUES or case_id in UNCUE:
            raise ValueError(f"single-tool case already specified {case_id}")
        UNCUE[case_id] = {"case_reason": _single(case_id), "tools": None}
    manifest = load_json(Path(__file__).resolve().parents[2] / "docs" / "official-840" / "selection" / "manifest.json")
    wanted = set(SEALED_IDS) | set(ADDED_IDS)
    ordered = tuple(case_id for case_id in manifest["ids_in_file_order"] if case_id in wanted)
    if len(ordered) != len(wanted):
        missing = sorted(wanted - set(ordered))
        raise ValueError(f"sealed ids missing from the manifest: {missing}")
    return ordered


SEALED_IDS = _merge_fourth_tranche()


def _merge_fifth_tranche():
    """Add the fifth tranche and put every sealed id back into file order."""
    from tool_compression.official_840_tranche_e import (
        ADDED_CHANGES,
        ADDED_CONFLICTS,
        ADDED_CUES,
        ADDED_IDS,
        ADDED_SINGLES,
        ADDED_UNCUE,
    )

    if set(ADDED_IDS) & set(SEALED_IDS):
        raise ValueError("fifth tranche overlaps an earlier sealed id")
    CHANGES.update(ADDED_CHANGES)
    CONFLICTS.update(ADDED_CONFLICTS)
    if set(ADDED_CUES) & set(CUES) or set(ADDED_UNCUE) & set(UNCUE):
        raise ValueError("fifth tranche repeats a cue or no-cue case")
    CUES.update(ADDED_CUES)
    UNCUE.update(ADDED_UNCUE)
    for case_id in ADDED_SINGLES:
        if case_id in CUES or case_id in UNCUE:
            raise ValueError(f"single-tool case already specified {case_id}")
        UNCUE[case_id] = {"case_reason": _single(case_id), "tools": None}
    manifest = load_json(Path(__file__).resolve().parents[2] / "docs" / "official-840" / "selection" / "manifest.json")
    wanted = set(SEALED_IDS) | set(ADDED_IDS)
    ordered = tuple(case_id for case_id in manifest["ids_in_file_order"] if case_id in wanted)
    if len(ordered) != len(wanted):
        missing = sorted(wanted - set(ordered))
        raise ValueError(f"sealed ids missing from the manifest: {missing}")
    return ordered


SEALED_IDS = _merge_fifth_tranche()


def _merge_sixth_tranche():
    """Add the sixth tranche and put every sealed id back into file order."""
    from tool_compression.official_840_tranche_f import (
        ADDED_CHANGES,
        ADDED_CONFLICTS,
        ADDED_CUES,
        ADDED_IDS,
        ADDED_SINGLES,
        ADDED_UNCUE,
    )

    if set(ADDED_IDS) & set(SEALED_IDS):
        raise ValueError("sixth tranche overlaps an earlier sealed id")
    CHANGES.update(ADDED_CHANGES)
    CONFLICTS.update(ADDED_CONFLICTS)
    if set(ADDED_CUES) & set(CUES) or set(ADDED_UNCUE) & set(UNCUE):
        raise ValueError("sixth tranche repeats a cue or no-cue case")
    CUES.update(ADDED_CUES)
    UNCUE.update(ADDED_UNCUE)
    for case_id in ADDED_SINGLES:
        if case_id in CUES or case_id in UNCUE:
            raise ValueError(f"single-tool case already specified {case_id}")
        UNCUE[case_id] = {"case_reason": _single(case_id), "tools": None}
    manifest = load_json(Path(__file__).resolve().parents[2] / "docs" / "official-840" / "selection" / "manifest.json")
    wanted = set(SEALED_IDS) | set(ADDED_IDS)
    ordered = tuple(case_id for case_id in manifest["ids_in_file_order"] if case_id in wanted)
    if len(ordered) != len(wanted):
        missing = sorted(wanted - set(ordered))
        raise ValueError(f"sealed ids missing from the manifest: {missing}")
    return ordered


SEALED_IDS = _merge_sixth_tranche()


def _merge_seventh_tranche():
    """Add the seventh tranche and put every sealed id back into file order."""
    from tool_compression.official_840_tranche_g import (
        ADDED_CHANGES,
        ADDED_CONFLICTS,
        ADDED_CUES,
        ADDED_IDS,
        ADDED_SINGLES,
        ADDED_UNCUE,
    )

    if set(ADDED_IDS) & set(SEALED_IDS):
        raise ValueError("seventh tranche overlaps an earlier sealed id")
    CHANGES.update(ADDED_CHANGES)
    CONFLICTS.update(ADDED_CONFLICTS)
    if set(ADDED_CUES) & set(CUES) or set(ADDED_UNCUE) & set(UNCUE):
        raise ValueError("seventh tranche repeats a cue or no-cue case")
    CUES.update(ADDED_CUES)
    UNCUE.update(ADDED_UNCUE)
    for case_id in ADDED_SINGLES:
        if case_id in CUES or case_id in UNCUE:
            raise ValueError(f"single-tool case already specified {case_id}")
        UNCUE[case_id] = {"case_reason": _single(case_id), "tools": None}
    manifest = load_json(Path(__file__).resolve().parents[2] / "docs" / "official-840" / "selection" / "manifest.json")
    wanted = set(SEALED_IDS) | set(ADDED_IDS)
    ordered = tuple(case_id for case_id in manifest["ids_in_file_order"] if case_id in wanted)
    if len(ordered) != len(wanted):
        missing = sorted(wanted - set(ordered))
        raise ValueError(f"sealed ids missing from the manifest: {missing}")
    return ordered


SEALED_IDS = _merge_seventh_tranche()


def _merge_eighth_tranche():
    """Add the eighth tranche and put every sealed id back into file order."""
    from tool_compression.official_840_tranche_h import (
        ADDED_CHANGES,
        ADDED_CONFLICTS,
        ADDED_CUES,
        ADDED_IDS,
        ADDED_SINGLES,
        ADDED_UNCUE,
    )

    if set(ADDED_IDS) & set(SEALED_IDS):
        raise ValueError("eighth tranche overlaps an earlier sealed id")
    CHANGES.update(ADDED_CHANGES)
    CONFLICTS.update(ADDED_CONFLICTS)
    if set(ADDED_CUES) & set(CUES) or set(ADDED_UNCUE) & set(UNCUE):
        raise ValueError("eighth tranche repeats a cue or no-cue case")
    CUES.update(ADDED_CUES)
    UNCUE.update(ADDED_UNCUE)
    for case_id in ADDED_SINGLES:
        if case_id in CUES or case_id in UNCUE:
            raise ValueError(f"single-tool case already specified {case_id}")
        UNCUE[case_id] = {"case_reason": _single(case_id), "tools": None}
    manifest = load_json(Path(__file__).resolve().parents[2] / "docs" / "official-840" / "selection" / "manifest.json")
    wanted = set(SEALED_IDS) | set(ADDED_IDS)
    ordered = tuple(case_id for case_id in manifest["ids_in_file_order"] if case_id in wanted)
    if len(ordered) != len(wanted):
        missing = sorted(wanted - set(ordered))
        raise ValueError(f"sealed ids missing from the manifest: {missing}")
    return ordered


SEALED_IDS = _merge_eighth_tranche()
