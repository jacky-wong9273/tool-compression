"""Fifth official-840 tranche. S and X are separate maps.

The formative pilot ids are not in this tranche. These twelve two-tool
catalogues have no justified cue. Cue text, where it exists in earlier
tranches, is not copied here.
"""

from __future__ import annotations


def _span(prefix: str, start: int, end: int) -> tuple[str, ...]:
    return tuple(f"{prefix}_{index}" for index in range(start, end))


ADDED_SINGLES = _span("simple_python", 223, 303) + _span("irrelevance", 162, 202)
ADDED_CUED = ()
ADDED_UNCUE_MULTI = (
    "multiple_101",
    "multiple_107",
    "multiple_108",
    "multiple_110",
    "multiple_112",
    "multiple_116",
    "multiple_129",
    "multiple_133",
    "multiple_135",
    "multiple_136",
    "multiple_140",
    "multiple_142",
)
ADDED_IDS = ADDED_CUED + ADDED_UNCUE_MULTI + ADDED_SINGLES

_FORMATIVE = {
    "multiple_0",
    "multiple_7",
    "multiple_11",
    "multiple_12",
    "multiple_35",
    "multiple_92",
    "multiple_100",
    "multiple_153",
    "simple_python_34",
    "simple_python_175",
    "irrelevance_50",
    "irrelevance_59",
}
if set(ADDED_IDS) & _FORMATIVE or len(ADDED_IDS) != len(set(ADDED_IDS)):
    raise ValueError("fifth tranche overlaps the formative pilot or repeats an id")

ADDED_CHANGES = {
    ("simple_python_252", 0, "/function/parameters/properties/sort_by/description"): {
        "replacement": "Order of sorting the events.",
        "reason": "The default sentence repeats the schema default chronological. The replacement keeps that the argument orders the events.",
        "parts": [
            {
                "excerpt": "Order of sorting the events",
                "decision": "KEEP",
                "after": "Order of sorting the events.",
            },
            {
                "excerpt": "Default is chronological.",
                "duplicate": True,
                "schema_path": "/function/parameters/properties/sort_by/default",
                "schema_equals": "chronological",
                "note": "The schema default is the string chronological.",
            },
        ],
    },
    ("simple_python_252", 0, "/function/parameters/properties/count/description"): {
        "replacement": "Number of events to return.",
        "reason": "The default sentence repeats the schema default 5. The replacement keeps that the argument is how many events to return.",
        "parts": [
            {
                "excerpt": "Number of events to return",
                "decision": "KEEP",
                "after": "Number of events to return.",
            },
            {
                "excerpt": "Default is 5.",
                "duplicate": True,
                "schema_path": "/function/parameters/properties/count/default",
                "schema_equals": 5,
                "note": "The schema default is the integer 5.",
            },
        ],
    },
    ("simple_python_257", 0, "/function/description"): {
        "replacement": "Identify the RGB values of a named color.",
        "reason": "The frame 'This function' is not a separate claim. The replacement keeps identifying the RGB values of a named color.",
    },
    ("simple_python_277", 0, "/function/parameters/properties/information/description"): {
        "replacement": "The type of information needed from the museum. This is optional.",
        "reason": "The default clause repeats the schema default all. The replacement keeps that the argument is the type of museum information and that it is optional.",
        "parts": [
            {
                "excerpt": "The type of information needed from the museum",
                "decision": "KEEP",
                "after": "The type of information needed from the museum.",
            },
            {
                "excerpt": "This is optional",
                "decision": "KEEP",
                "after": "This is optional.",
            },
            {
                "excerpt": "and defaults to 'all' if not specified.",
                "duplicate": True,
                "schema_path": "/function/parameters/properties/information/default",
                "schema_equals": "all",
                "note": "The schema default is the string all.",
            },
        ],
    },
    ("simple_python_296", 0, "/function/parameters/properties/scale_type/description"): {
        "replacement": "The type of scale to generate.",
        "reason": "The default sentence repeats the schema default major. The replacement keeps that the argument is the type of scale.",
        "parts": [
            {
                "excerpt": "The type of scale to generate",
                "decision": "KEEP",
                "after": "The type of scale to generate.",
            },
            {
                "excerpt": "Defaults to 'major'.",
                "duplicate": True,
                "schema_path": "/function/parameters/properties/scale_type/default",
                "schema_equals": "major",
                "note": "The schema default is the string major.",
            },
        ],
    },
    ("irrelevance_163", 0, "/function/description"): {
        "replacement": "Tune instruments based on the instrument type and the desired key or note.",
        "reason": "The frame 'This function helps' is not a separate claim. The replacement keeps tuning an instrument from its type and the desired key or note.",
    },
    ("irrelevance_164", 0, "/function/parameters/properties/top/description"): {
        "replacement": "Number of top players to return.",
        "reason": "The default sentence repeats the schema default 5. The replacement keeps that the argument is how many top players to return.",
        "parts": [
            {
                "excerpt": "Number of top players to return",
                "decision": "KEEP",
                "after": "Number of top players to return.",
            },
            {
                "excerpt": "Default is 5.",
                "duplicate": True,
                "schema_path": "/function/parameters/properties/top/default",
                "schema_equals": 5,
                "note": "The schema default is the integer 5.",
            },
        ],
    },
    ("multiple_142", 1, "/function/parameters/properties/include_player_stats/description"): {
        "replacement": "Indicates if individual player statistics should be included in the result.",
        "reason": "The default sentence repeats the schema default false. The replacement keeps that the argument includes individual player statistics.",
        "parts": [
            {
                "excerpt": "Indicates if individual player statistics should be included in the result",
                "decision": "KEEP",
                "after": "Indicates if individual player statistics should be included in the result.",
            },
            {
                "excerpt": "Default is false.",
                "duplicate": True,
                "schema_path": "/function/parameters/properties/include_player_stats/default",
                "schema_equals": False,
                "note": "The schema default is boolean false.",
            },
        ],
    },
}

ADDED_CONFLICTS = {
    ("simple_python_227", 0, "/function/parameters/properties/traits/description"): [
        "Prose says list. Schema type is array. Left as written."
    ],
    ("simple_python_229", 0, "/function/parameters/properties/characteristics/description"): [
        "Prose says list. Schema type is array. Left as written."
    ],
    ("simple_python_277", 0, "/function/parameters/properties/information/description"): [
        "Schema type is array and the schema default is the string 'all'. Left unrepaired."
    ],
    ("irrelevance_167", 0, "/function/parameters/properties/include_artist_info/description"): [
        "Schema type is boolean and the schema default is the string 'false'. The prose does not restate that default. Left unrepaired."
    ],
    ("irrelevance_176", 0, "/function/parameters/properties/year_composed/description"): [
        "Schema type is integer and the schema default is the string 'optional'. The prose does not restate that default. Left unrepaired."
    ],
    ("irrelevance_179", 0, "/function/parameters/properties/venue/description"): [
        "The schema default is the string 'basketball' on a venue field. The prose says the venue of the match. Left unrepaired."
    ],
    ("irrelevance_189", 0, "/function/parameters/properties/year/description"): [
        "Schema type is integer and the schema default is the string 'The current year'. The prose does not restate that default. Left unrepaired."
    ],
    ("irrelevance_195", 0, "/function/description"): [
        "The function says the game is chess. The game parameter names the board game. Left unrepaired."
    ],
    ("irrelevance_196", 0, "/function/parameters/properties/player_actions/description"): [
        "Prose says list. Schema type is array. Left as written."
    ],
    ("multiple_136", 0, "/function/parameters/properties/players/description"): [
        "Prose says list. Schema type is array. Left as written."
    ],
}

ADDED_CUES = {}

ADDED_UNCUE = {
    "multiple_101": {
        "case_reason": "The greatest common divisor of two integers and a list of landmark law cases do not answer a similar request.",
        "tools": {
            0: "Calculates the greatest common divisor of two integers. The other tool retrieves landmark law cases. A divisor is not a legal case.",
            1: "Retrieves landmark cases in a field of law. The other tool calculates a greatest common divisor. No shared action or resource is documented.",
        },
    },
    "multiple_107": {
        "case_reason": "Mixing paint colors and calculating density do not answer a similar request.",
        "tools": {
            0: "Combines two primary paint colors. The other tool calculates density from mass and volume. A color is not a density.",
            1: "Calculates density from mass and volume. The other tool mixes paint. No shared action or resource is documented.",
        },
    },
    "multiple_108": {
        "case_reason": "The heat capacity of air and the discounted cash flow of a bond do not answer a similar request.",
        "tools": {
            0: "Calculates the heat capacity of air. The other tool calculates a bond's discounted cash flow. A gas temperature is not a coupon.",
            1: "Calculates the discounted cash flow of a bond. The other tool calculates heat capacity. No shared action or resource is documented.",
        },
    },
    "multiple_110": {
        "case_reason": "Collectable items in a game and the type of a genetic mutation do not answer a similar request.",
        "tools": {
            0: "Retrieves collectable items in a game season. The other tool finds a mutation type from an SNP id. A game item is not a mutation.",
            1: "Finds the type of a genetic mutation. The other tool retrieves game collectables. No shared action or resource is documented.",
        },
    },
    "multiple_112": {
        "case_reason": "A forest-growth forecast and the scientist credited for a discovery do not answer a similar request.",
        "tools": {
            0: "Predicts forest growth over a number of years. The other tool retrieves the scientist credited for a discovery. A forest is not a discovery credit.",
            1: "Retrieves the scientist credited for a discovery. The other tool forecasts forest growth. No shared action or resource is documented.",
        },
    },
    "multiple_116": {
        "case_reason": "A person's body mass index and a sports celebrity's net worth do not answer a similar request.",
        "tools": {
            0: "Calculates body mass index from weight and height. The other tool gets a celebrity's net worth. A weight is not a net worth.",
            1: "Gets a sports celebrity's net worth. The other tool calculates body mass index. No shared action or resource is documented.",
        },
    },
    "multiple_129": {
        "case_reason": "A search for lawsuits and a compound-interest calculation do not answer a similar request.",
        "tools": {
            0: "Searches for lawsuits against a company. The other tool calculates compound interest. A case type is not an interest rate.",
            1: "Calculates compound interest. The other tool searches for lawsuits. No shared action or resource is documented.",
        },
    },
    "multiple_133": {
        "case_reason": "A mutual-fund balance and the area of a circle do not answer a similar request.",
        "tools": {
            0: "Calculates a mutual-fund balance from an investment, a yield, and a period. The other tool calculates a circle's area. A yield is not a radius.",
            1: "Calculates the area of a circle from a radius. The other tool calculates a mutual-fund balance. No shared action or resource is documented.",
        },
    },
    "multiple_135": {
        "case_reason": "Court-case details and the area of a triangle do not answer a similar request.",
        "tools": {
            0: "Retrieves case details from a docket and a court. The other tool calculates a triangle's area. A docket is not a base.",
            1: "Calculates the area of a triangle from a base and a height. The other tool retrieves case details. No shared action or resource is documented.",
        },
    },
    "multiple_136": {
        "case_reason": "A city's crime rate and the winner of a poker game do not answer a similar request.",
        "tools": {
            0: "Retrieves the crime rate of a city. The other tool identifies a poker winner. A crime type is not a hand of cards.",
            1: "Identifies the winner of a poker game. The other tool retrieves a crime rate. No shared action or resource is documented.",
        },
    },
    "multiple_140": {
        "case_reason": "A search for lawsuits and a hotel-availability check do not answer a similar request. Sharing a location is not a selection axis.",
        "tools": {
            0: "Searches for lawsuits against a company. The other tool checks hotel availability. A lawsuit is not a room.",
            1: "Checks hotel availability for a city and a stay. The other tool searches for lawsuits. No shared action or resource is documented.",
        },
    },
    "multiple_142": {
        "case_reason": "A humidity forecast and a sports team's latest score do not answer a similar request.",
        "tools": {
            0: "Retrieves a humidity forecast for a city. The other tool retrieves a team's latest game score. Humidity is not a score.",
            1: "Retrieves a sports team's latest game score. The other tool forecasts humidity. No shared action or resource is documented.",
        },
    },
}
