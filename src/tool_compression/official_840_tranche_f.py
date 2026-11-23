"""Sixth official-840 tranche. S and X are separate maps.

The formative pilot ids are not in this tranche. These fourteen two-tool
catalogues have no justified cue. Cue text from earlier tranches is not
copied here.
"""

from __future__ import annotations


def _span(prefix: str, start: int, end: int) -> tuple[str, ...]:
    return tuple(f"{prefix}_{index}" for index in range(start, end))


ADDED_SINGLES = _span("simple_python", 303, 400) + _span("irrelevance", 202, 240)
ADDED_CUED = ()
ADDED_UNCUE_MULTI = (
    "multiple_144",
    "multiple_146",
    "multiple_148",
    "multiple_152",
    "multiple_157",
    "multiple_162",
    "multiple_163",
    "multiple_169",
    "multiple_171",
    "multiple_174",
    "multiple_185",
    "multiple_186",
    "multiple_189",
    "multiple_199",
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
    raise ValueError("sixth tranche overlaps the formative pilot or repeats an id")

ADDED_CHANGES = {
    ("simple_python_326", 0, "/function/parameters/properties/include_player_stats/description"): {
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
    ("simple_python_331", 0, "/function/parameters/properties/number_of_players/description"): {
        "replacement": "Number of players you want to retrieve.",
        "reason": "The default clause repeats the schema default 10. The replacement keeps that the argument is how many players to retrieve.",
        "parts": [
            {
                "excerpt": "Number of players you want to retrieve",
                "decision": "KEEP",
                "after": "Number of players you want to retrieve.",
            },
            {
                "excerpt": "default value is 10",
                "duplicate": True,
                "schema_path": "/function/parameters/properties/number_of_players/default",
                "schema_equals": 10,
                "note": "The schema default is the integer 10.",
            },
        ],
    },
    ("simple_python_357", 0, "/function/parameters/properties/diet_preference/description"): {
        "replacement": "Preferred dietary consideration like vegan, vegetarian, gluten-free etc.",
        "reason": "The default sentence repeats the schema default none. The replacement keeps the dietary examples.",
        "parts": [
            {
                "excerpt": "Preferred dietary consideration like vegan, vegetarian, gluten-free etc",
                "decision": "KEEP",
                "after": "Preferred dietary consideration like vegan, vegetarian, gluten-free etc.",
            },
            {
                "excerpt": "Default is none.",
                "duplicate": True,
                "schema_path": "/function/parameters/properties/diet_preference/default",
                "schema_equals": "none",
                "note": "The schema default is the string none.",
            },
        ],
    },
    ("simple_python_384", 0, "/function/parameters/properties/room_type/description"): {
        "replacement": "The type of the room. Options are 'Standard', 'Deluxe', 'Suite'.",
        "reason": "The default clause repeats the schema default Standard. The replacement keeps the room type and the listed options.",
        "parts": [
            {
                "excerpt": "The type of the room",
                "decision": "KEEP",
                "after": "The type of the room.",
            },
            {
                "excerpt": "default is 'Standard'.",
                "duplicate": True,
                "schema_path": "/function/parameters/properties/room_type/default",
                "schema_equals": "Standard",
                "note": "The schema default is the string Standard.",
            },
            {
                "excerpt": "Options are 'Standard', 'Deluxe', 'Suite'.",
                "decision": "KEEP",
                "after": "Options are 'Standard', 'Deluxe', 'Suite'.",
            },
        ],
    },
    ("simple_python_385", 0, "/function/parameters/properties/no_of_rooms/description"): {
        "replacement": "Number of rooms to book.",
        "reason": "The default sentence repeats the schema default 1. The replacement keeps that the argument is how many rooms to book.",
        "parts": [
            {
                "excerpt": "Number of rooms to book",
                "decision": "KEEP",
                "after": "Number of rooms to book.",
            },
            {
                "excerpt": "Default is 1.",
                "duplicate": True,
                "schema_path": "/function/parameters/properties/no_of_rooms/default",
                "schema_equals": 1,
                "note": "The schema default is the integer 1.",
            },
        ],
    },
    ("irrelevance_202", 0, "/function/parameters/properties/game_rounds/description"): {
        "replacement": "The total game rounds.",
        "reason": "The default sentence repeats the schema default 3. The replacement keeps that the argument is the number of game rounds.",
        "parts": [
            {
                "excerpt": "The total game rounds",
                "decision": "KEEP",
                "after": "The total game rounds.",
            },
            {
                "excerpt": "Defaults to 3 if not provided.",
                "duplicate": True,
                "schema_path": "/function/parameters/properties/game_rounds/default",
                "schema_equals": "3",
                "note": "The schema default is the string 3.",
            },
        ],
    },
    ("irrelevance_204", 0, "/function/parameters/properties/solve_method/description"): {
        "replacement": "Method to be used to solve the puzzle.",
        "reason": "The default sentence repeats the schema default brute_force. The replacement keeps that the argument is the method used to solve the puzzle.",
        "parts": [
            {
                "excerpt": "Method to be used to solve the puzzle",
                "decision": "KEEP",
                "after": "Method to be used to solve the puzzle.",
            },
            {
                "excerpt": "Default is brute_force.",
                "duplicate": True,
                "schema_path": "/function/parameters/properties/solve_method/default",
                "schema_equals": "brute_force",
                "note": "The schema default is the string brute_force.",
            },
        ],
    },
    ("multiple_185", 0, "/function/parameters/properties/number_of_players/description"): {
        "replacement": "Number of players you want to retrieve.",
        "reason": "The default clause repeats the schema default 10. The replacement keeps that the argument is how many players to retrieve. The sentence is this tool's own description.",
        "parts": [
            {
                "excerpt": "Number of players you want to retrieve",
                "decision": "KEEP",
                "after": "Number of players you want to retrieve.",
            },
            {
                "excerpt": "default value is 10",
                "duplicate": True,
                "schema_path": "/function/parameters/properties/number_of_players/default",
                "schema_equals": 10,
                "note": "The schema default is the integer 10.",
            },
        ],
    },
}

ADDED_CONFLICTS = {
    ("simple_python_307", 0, "/function/parameters/properties/teams/description"): [
        "Prose says list. Schema type is array. Left as written."
    ],
    ("simple_python_316", 0, "/function/parameters/properties/gender/description"): [
        "The prose says the possible values are male or female. The schema default is the string 'all', and the prose does not restate that default. Left unrepaired."
    ],
    ("simple_python_337", 0, "/function/parameters/properties/players/description"): [
        "Prose says list. Schema type is array. Left as written."
    ],
    ("simple_python_340", 0, "/function/parameters/properties/hand1/description"): [
        "Prose says list. Schema type is array. Left as written."
    ],
    ("simple_python_340", 0, "/function/parameters/properties/hand2/description"): [
        "Prose says list. Schema type is array. Left as written."
    ],
    ("simple_python_359", 0, "/function/parameters/properties/ingredients/description"): [
        "Prose says list. Schema type is array. Left as written."
    ],
    ("simple_python_370", 0, "/function/parameters/properties/items/description"): [
        "Prose says list. Schema type is array. Left as written."
    ],
    ("simple_python_371", 0, "/function/parameters/properties/items/description"): [
        "Prose says list. Schema type is array. Left as written."
    ],
    ("simple_python_375", 0, "/function/parameters/properties/items/description"): [
        "Prose says list. Schema type is array. Left as written."
    ],
    ("simple_python_379", 0, "/function/parameters/properties/timezone/description"): [
        "The default sentence ends without a value, and the schema has no default. Left as written."
    ],
    ("irrelevance_202", 0, "/function/parameters/properties/game_rounds/description"): [
        "Schema type is integer and the schema default is the string '3'. Left unrepaired."
    ],
    ("irrelevance_206", 0, "/function/parameters/properties/inventory/description"): [
        "Prose says list. Schema type is array. Left as written."
    ],
    ("irrelevance_217", 0, "/function/parameters/properties/ingredients/description"): [
        "Prose says list. Schema type is array. Left as written."
    ],
    ("irrelevance_217", 0, "/function/parameters/properties/instructions/description"): [
        "Prose says list. Schema type is array. Left as written."
    ],
    ("irrelevance_218", 0, "/function/parameters/properties/ingredients/description"): [
        "Prose says list. Schema type is array. Left as written."
    ],
    ("irrelevance_220", 0, "/function/parameters/properties/pre_heating/description"): [
        "Schema type is boolean and the schema default is the string 'false'. The prose does not restate that default. Left unrepaired."
    ],
    ("irrelevance_224", 0, "/function/parameters/properties/is_24_hours/description"): [
        "Schema type is boolean and the schema default is the string 'True'. The prose does not restate that default. Left unrepaired."
    ],
    ("irrelevance_225", 0, "/function/parameters/properties/time/description"): [
        "The schema default is the string '13:30:00'. The prose example is '15:30:00'. Left unrepaired."
    ],
    ("irrelevance_239", 0, "/function/description"): [
        "The function says it gets the time difference between two locations. The unit parameter measures distance. Left unrepaired."
    ],
    ("irrelevance_239", 0, "/function/parameters/properties/location_2/description"): [
        "The description repeats the first city's wording. Left as written."
    ],
    ("multiple_171", 1, "/function/parameters/properties/teams/description"): [
        "Prose says list. Schema type is array. Left as written."
    ],
}

ADDED_CUES = {}

ADDED_UNCUE = {
    "multiple_144": {
        "case_reason": "A sports-team ranking and an air-quality index do not answer a similar request.",
        "tools": {
            0: "Fetches the ranking of a sports team in a league. The other tool retrieves an air-quality index. A ranking is not an air-quality reading.",
            1: "Retrieves the air-quality index for a city. The other tool fetches a sports ranking. No shared action or resource is documented.",
        },
    },
    "multiple_146": {
        "case_reason": "A restaurant search and a precipitation record do not answer a similar request. Sharing a location is not a selection axis.",
        "tools": {
            0: "Locates nearby restaurants by cuisine. The other tool retrieves precipitation data. A restaurant is not a rainfall record.",
            1: "Retrieves precipitation data for a location and a period. The other tool locates restaurants. No shared action or resource is documented.",
        },
    },
    "multiple_148": {
        "case_reason": "The current time in a city and information about a stock do not answer a similar request.",
        "tools": {
            0: "Retrieves the current time in a city. The other tool retrieves stock information. A clock time is not a stock.",
            1: "Retrieves stock information for a company. The other tool retrieves the current time. No shared action or resource is documented.",
        },
    },
    "multiple_152": {
        "case_reason": "Key historical events and the market value of a sculpture do not answer a similar request.",
        "tools": {
            0: "Retrieves key historical events for a country and a period. The other tool retrieves a sculpture's market value. An event is not a sculpture price.",
            1: "Retrieves the market value of a sculpture. The other tool retrieves historical events. No shared action or resource is documented.",
        },
    },
    "multiple_157": {
        "case_reason": "A team's current ranking and the earliest historical reference of a person do not answer a similar request.",
        "tools": {
            0: "Retrieves a team's current ranking in a league. The other tool retrieves the earliest reference of a person. A ranking is not a historical reference.",
            1: "Retrieves the earliest historical reference of a person. The other tool retrieves a team ranking. No shared action or resource is documented.",
        },
    },
    "multiple_162": {
        "case_reason": "A player's statistics and an analysis of a building do not answer a similar request.",
        "tools": {
            0: "Retrieves a player's statistics for a year. The other tool analyses a building. A player statistic is not a structural analysis.",
            1: "Analyses a building from an id and floor numbers. The other tool retrieves player statistics. No shared action or resource is documented.",
        },
    },
    "multiple_163": {
        "case_reason": "Popular artworks at one museum and a search for lawsuits do not answer a similar request.",
        "tools": {
            0: "Fetches popular artworks at the Metropolitan Museum of Art. The other tool searches for lawsuits. An artwork is not a lawsuit.",
            1: "Searches for lawsuits related to a company. The other tool fetches museum artworks. No shared action or resource is documented.",
        },
    },
    "multiple_169": {
        "case_reason": "Walmart item information and a musical scale do not answer a similar request.",
        "tools": {
            0: "Retrieves Walmart item information, including stock. The other tool returns a musical scale. A product is not a scale.",
            1: "Returns the musical scale of a key. The other tool retrieves Walmart items. No shared action or resource is documented.",
        },
    },
    "multiple_171": {
        "case_reason": "The probability of a poker full house and the winner of a basketball game do not answer a similar request.",
        "tools": {
            0: "Calculates the probability of a full house in poker. The other tool returns the winner of a basketball game. A poker probability is not a basketball result.",
            1: "Returns the winner of a basketball game. The other tool calculates a poker probability. No shared action or resource is documented.",
        },
    },
    "multiple_174": {
        "case_reason": "A sports-team ranking and a compound-interest calculation do not answer a similar request.",
        "tools": {
            0: "Fetches the ranking of a sports team in a league. The other tool calculates compound interest. A ranking is not an interest amount.",
            1: "Calculates compound interest. The other tool fetches a sports ranking. No shared action or resource is documented.",
        },
    },
    "multiple_185": {
        "case_reason": "Top chess players and the closest sushi restaurant do not answer a similar request. Sharing a location is not a selection axis.",
        "tools": {
            0: "Finds top chess players in a city by rating. The other tool locates a sushi restaurant. A chess player is not a restaurant.",
            1: "Locates the closest sushi restaurant. The other tool finds chess players. No shared action or resource is documented.",
        },
    },
    "multiple_186": {
        "case_reason": "A recipe search and the details of a scientific discovery do not answer a similar request.",
        "tools": {
            0: "Finds a recipe from dietary restrictions, type, and time. The other tool retrieves a scientific discovery. A recipe is not a discovery.",
            1: "Retrieves the details of a scientific discovery. The other tool finds a recipe. No shared action or resource is documented.",
        },
    },
    "multiple_189": {
        "case_reason": "Greenhouse-gas savings and a time-zone conversion do not answer a similar request.",
        "tools": {
            0: "Calculates greenhouse-gas savings from a renewable source. The other tool converts a time between zones. An emission saving is not a clock time.",
            1: "Converts a time from one time zone to another. The other tool calculates emission savings. No shared action or resource is documented.",
        },
    },
    "multiple_199": {
        "case_reason": "A forest-growth forecast and a database-record fetch do not answer a similar request.",
        "tools": {
            0: "Predicts forest growth over a number of years. The other tool fetches database records. A forest is not a table row.",
            1: "Fetches records from a database table. The other tool forecasts forest growth. No shared action or resource is documented.",
        },
    },
}
