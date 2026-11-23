"""Fourth official-840 tranche. S and X are separate maps.

The formative pilot ids are not in this tranche. Cue text is taken from
the original function descriptions, not from S.
"""

from __future__ import annotations


def _span(prefix: str, start: int, end: int) -> tuple[str, ...]:
    return tuple(f"{prefix}_{index}" for index in range(start, end))


ADDED_SINGLES = (
    _span("simple_python", 142, 175)
    + _span("simple_python", 176, 223)
    + _span("irrelevance", 112, 162)
)
ADDED_CUED = (
    "multiple_80",
    "multiple_81",
    "multiple_82",
    "multiple_84",
    "multiple_85",
    "multiple_86",
    "multiple_88",
    "multiple_90",
    "multiple_91",
)
ADDED_UNCUE_MULTI = (
    "multiple_93",
    "multiple_95",
    "multiple_97",
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
    raise ValueError("fourth tranche overlaps the formative pilot or repeats an id")

ADDED_CHANGES = {
    ("simple_python_157", 0, "/function/description"): {
        "replacement": "Check if an individual has any prior felony convictions based on their full name and birth date.",
        "reason": "The frame 'This function' is not a separate claim. The replacement keeps checking prior felony convictions from a full name and a birth date.",
    },
    ("simple_python_163", 0, "/function/parameters/properties/include_owner/description"): {
        "replacement": "Include owner's name in the property record.",
        "reason": "The default sentence repeats the schema default false. The replacement keeps that the argument includes the owner's name.",
        "parts": [
            {
                "excerpt": "Include owner's name in the property record",
                "decision": "KEEP",
                "after": "Include owner's name in the property record.",
            },
            {
                "excerpt": "Default is false.",
                "duplicate": True,
                "schema_path": "/function/parameters/properties/include_owner/default",
                "schema_equals": False,
                "note": "The schema default is boolean false.",
            },
        ],
    },
    ("simple_python_182", 0, "/function/parameters/properties/year/description"): {
        "replacement": "The year in which the lawsuit case was initiated.",
        "reason": "The default sentence repeats the schema default 2023. The replacement keeps that the argument is the year the case was initiated.",
        "parts": [
            {
                "excerpt": "The year in which the lawsuit case was initiated",
                "decision": "KEEP",
                "after": "The year in which the lawsuit case was initiated.",
            },
            {
                "excerpt": "Default is 2023 if not specified.",
                "duplicate": True,
                "schema_path": "/function/parameters/properties/year/default",
                "schema_equals": 2023,
                "note": "The schema default is the integer 2023.",
            },
        ],
    },
    ("simple_python_215", 0, "/function/description"): {
        "replacement": "Retrieve a brief about a specified movie.",
        "reason": "The frame 'This function' is not a separate claim. The replacement keeps retrieving a brief about a specified movie.",
    },
    ("simple_python_217", 0, "/function/description"): {
        "replacement": "Take in fMRI data to output analyzed data.",
        "reason": "The frame 'This function' is not a separate claim. The replacement keeps taking fMRI data and outputting analyzed data.",
    },
    ("multiple_97", 0, "/function/parameters/properties/units/description"): {
        "replacement": "The units in which the radius is measured.",
        "reason": "The parenthetical repeats the schema default meters. The replacement keeps that the argument is the unit of the radius.",
        "parts": [
            {
                "excerpt": "The units in which the radius is measured",
                "decision": "KEEP",
                "after": "The units in which the radius is measured.",
            },
            {
                "excerpt": "(defaults to meters)",
                "duplicate": True,
                "schema_path": "/function/parameters/properties/units/default",
                "schema_equals": "meters",
                "note": "The schema default is the string meters.",
            },
        ],
    },
}

ADDED_CONFLICTS = {
    ("simple_python_147", 0, "/function/parameters/properties/companies/description"): [
        "Prose says list. Schema type is array. Left as written."
    ],
    ("simple_python_149", 0, "/function/parameters/properties/company_names/description"): [
        "Prose says list. Schema type is array. Left as written."
    ],
    ("simple_python_169", 0, "/function/parameters/properties/full_text/description"): [
        "Schema type is boolean and the schema default is the string 'false'. The prose does not restate that default. Left unrepaired."
    ],
    ("simple_python_215", 0, "/function/parameters/properties/extra_info/description"): [
        "Schema type is boolean and the schema default is the string 'false'. The prose does not restate that default. Left unrepaired."
    ],
    ("irrelevance_113", 0, "/function/parameters/properties/rating/description"): [
        "Schema type is number and the schema default is the string '0.3'. The prose does not restate that default. Left unrepaired."
    ],
    ("irrelevance_122", 0, "/function/parameters/properties/filter_frequency/description"): [
        "Schema type is boolean and the schema default is the string 'False'. The prose does not restate that default. Left unrepaired."
    ],
    ("irrelevance_129", 0, "/function/parameters/properties/detailed_output/description"): [
        "Schema type is boolean and the schema default is the string 'True'. The prose does not restate that default. Left unrepaired."
    ],
    ("irrelevance_136", 0, "/function/description"): [
        "The function says the president of the United States. The state parameter says a governor lookup. Left unrepaired."
    ],
    ("irrelevance_149", 0, "/function/parameters/properties/available_colors/items/description"): [
        "Prose says list. The items sit on an array. Left as written."
    ],
    ("irrelevance_158", 0, "/function/parameters/properties/materials/description"): [
        "Prose says list. Schema type is array. Left as written."
    ],
}

ADDED_CUES = {
    "multiple_80": {
        "case_reason": "Both tools locate a nearby place from a city. One locates music shops. The other locates gyms.",
        "tools": {
            0: {
                "cue": "Unlike gym_find_nearby, which locates nearby gyms, this locates nearby music shops.",
                "rival_index": 1,
                "axis": "whether the nearby places are music shops or gyms",
                "why_confusable": "Both locate nearby places from a city and a preference list.",
                "why_this_rival": "Only one other tool, and the action is the same.",
                "rejected": ["Instrument lessons belong to the music-shop tool. They are not the contrast with gyms."],
                "target_excerpt": "nearby music shops",
                "rival_excerpt": "nearby gyms",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request to find somewhere nearby can be read as either. The cue names music shops against gyms.",
            },
            1: {
                "cue": "Unlike music_shop_find_nearby, which locates nearby music shops, this locates nearby gyms.",
                "rival_index": 0,
                "axis": "whether the nearby places are gyms or music shops",
                "why_confusable": "Both locate nearby places from a city and a preference list.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["Fitness classes belong to the gym tool. They are not a second cue."],
                "target_excerpt": "nearby gyms",
                "rival_excerpt": "nearby music shops",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request for a gym does not make the music-shop description true. A request that only names the city can be read as either.",
            },
        },
    },
    "multiple_81": {
        "case_reason": "Both tools book a ticket at a city with add-ons. One books a concert. The other books a festival.",
        "tools": {
            0: {
                "cue": "Unlike festival_book_ticket, which books a ticket for a festival, this books a ticket for a concert.",
                "rival_index": 1,
                "axis": "whether the ticket is for a concert or a festival",
                "why_confusable": "Both book a ticket for an event in a city, with optional add-ons.",
                "why_this_rival": "Only one other tool, and the action is the same.",
                "rejected": ["A backstage pass is an example on the concert tool, not the contrast with a festival."],
                "target_excerpt": "ticket for a concert",
                "rival_excerpt": "ticket for a festival",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request to book a ticket in a city can be read as either event. The cue names a concert against a festival.",
            },
            1: {
                "cue": "Unlike concert_book_ticket, which books a ticket for a concert, this books a ticket for a festival.",
                "rival_index": 0,
                "axis": "whether the ticket is for a festival or a concert",
                "why_confusable": "Both book a ticket for an event in a city, with optional add-ons.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["Camping access is an example on the festival tool, not a second cue."],
                "target_excerpt": "ticket for a festival",
                "rival_excerpt": "ticket for a concert",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "The cue names the event. It does not say either tool rejects a city.",
            },
        },
    },
    "multiple_82": {
        "case_reason": "Both tools generate sound. One generates a piece of music. The other generates an audio signal.",
        "tools": {
            0: {
                "cue": "Unlike audio_generate, which generates an audio signal, this generates a piece of music.",
                "rival_index": 1,
                "axis": "whether the generated sound is a piece of music or an audio signal",
                "why_confusable": "Both generate sound. A request that only says to generate sound can be read as either.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["Key, tempo, and time signature belong to the music tool. They are not a claim that an audio signal has no frequency."],
                "target_excerpt": "a piece of music",
                "rival_excerpt": "an audio signal",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A piece of music and an audio signal are alternatives here. The cue does not treat one as a subclass of the other.",
            },
            1: {
                "cue": "Unlike music_generate, which generates a piece of music, this generates an audio signal.",
                "rival_index": 0,
                "axis": "whether the generated sound is an audio signal or a piece of music",
                "why_confusable": "Both generate sound.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["Frequency, amplitude, and duration follow the signal. They are not a second cue."],
                "target_excerpt": "an audio signal",
                "rival_excerpt": "a piece of music",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request that names a frequency makes the signal description true. A request that only says to generate sound can be read as either.",
            },
        },
    },
    "multiple_84": {
        "case_reason": "Both tools return a top list for a competition and a team. One returns goal scorers. The other returns assist makers.",
        "tools": {
            0: {
                "cue": "Unlike getTopAssists, which returns the top assist makers, this returns the top goal scorers.",
                "rival_index": 1,
                "axis": "whether the top list is goal scorers or assist makers",
                "why_confusable": "Both return a top list for the same competition and team.",
                "why_this_rival": "Only one other tool, and the action is the same kind of retrieval.",
                "rejected": ["The number of names is a shared argument, not the selection axis."],
                "target_excerpt": "top goal scorers",
                "rival_excerpt": "top assist makers",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request for a team's top players can be read as either statistic. The cue names goals against assists.",
            },
            1: {
                "cue": "Unlike getTopGoalScorers, which returns the top goal scorers, this returns the top assist makers.",
                "rival_index": 0,
                "axis": "whether the top list is assist makers or goal scorers",
                "why_confusable": "Both return a top list for the same competition and team.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["Do not use the shared example competition as the difference."],
                "target_excerpt": "top assist makers",
                "rival_excerpt": "top goal scorers",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "Goals and assists are different figures. The cue does not say either tool rejects a team.",
            },
        },
    },
    "multiple_85": {
        "case_reason": "Both tools retrieve scores for a team and a league. One retrieves basketball scores. The other retrieves soccer scores.",
        "tools": {
            0: {
                "cue": "Unlike soccer_scores_get_scores, which retrieves soccer scores, this retrieves basketball scores.",
                "rival_index": 1,
                "axis": "whether the scores are basketball scores or soccer scores",
                "why_confusable": "Both retrieve scores for a team and a league over past rounds.",
                "why_this_rival": "Only one other tool, and the action is the same.",
                "rejected": ["The round count is shared. It is not the selection axis."],
                "target_excerpt": "basketball scores",
                "rival_excerpt": "soccer scores",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request for a team's recent scores can be read as either sport. The cue names basketball against soccer.",
            },
            1: {
                "cue": "Unlike basketball_scores_get_scores, which retrieves basketball scores, this retrieves soccer scores.",
                "rival_index": 0,
                "axis": "whether the scores are soccer scores or basketball scores",
                "why_confusable": "Both retrieve scores for a team and a league over past rounds.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["Do not treat the shared league argument as the difference."],
                "target_excerpt": "soccer scores",
                "rival_excerpt": "basketball scores",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "The cue names the sport. It does not say either tool rejects a league.",
            },
        },
    },
    "multiple_86": {
        "case_reason": "Both tools recommend a game by player count and category. One uses BoardGameGeek. The other uses Amazon Game Store.",
        "tools": {
            0: {
                "cue": "Unlike AmazonGameStore_recommend, which generates a game recommendation from Amazon Game Store, this generates a game recommendation from BoardGameGeek store.",
                "rival_index": 1,
                "axis": "whether the recommendation comes from BoardGameGeek or Amazon Game Store",
                "why_confusable": "Both recommend a game from a player count and a category.",
                "why_this_rival": "Only one other tool, and the action is the same.",
                "rejected": ["Difficulty belongs to the BoardGameGeek tool. Price range belongs to the Amazon tool. Neither is a second cue."],
                "target_excerpt": "BoardGameGeek store",
                "rival_excerpt": "Amazon Game Store",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request for a game recommendation can be read as either store. The cue names the store.",
            },
            1: {
                "cue": "Unlike BoardGameGeek_recommend, which generates a game recommendation from BoardGameGeek store, this generates a game recommendation from Amazon Game Store.",
                "rival_index": 0,
                "axis": "whether the recommendation comes from Amazon Game Store or BoardGameGeek",
                "why_confusable": "Both recommend a game from a player count and a category.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["Do not use the price range as the reason to choose a store."],
                "target_excerpt": "Amazon Game Store",
                "rival_excerpt": "BoardGameGeek store",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "The cue names the store. It does not say either tool rejects a player count.",
            },
        },
    },
    "multiple_88": {
        "case_reason": "Both tools retrieve a figure for a video game and a year. One retrieves the number of active players. The other retrieves sales figures.",
        "tools": {
            0: {
                "cue": "Unlike video_games_get_sales, which retrieves the sales figures, this retrieves the number of active players.",
                "rival_index": 1,
                "axis": "whether the game-year figure is active players or sales",
                "why_confusable": "Both retrieve a figure for the same video game and year.",
                "why_this_rival": "Only one other tool, and the action is the same kind of retrieval.",
                "rejected": ["The platform argument is shared. It is not the selection axis."],
                "target_excerpt": "number of active players",
                "rival_excerpt": "sales figures",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request for a game's figure in a year can be read as either. The cue names players against sales.",
            },
            1: {
                "cue": "Unlike video_games_get_player_count, which retrieves the number of active players, this retrieves the sales figures.",
                "rival_index": 0,
                "axis": "whether the game-year figure is sales or active players",
                "why_confusable": "Both retrieve a figure for the same video game and year.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["Do not use the shared platform examples as the difference."],
                "target_excerpt": "sales figures",
                "rival_excerpt": "number of active players",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "Players and sales are different figures. The cue does not say either tool rejects a year.",
            },
        },
    },
    "multiple_90": {
        "case_reason": "Both tools find a place for a group in a city. One finds events. The other finds restaurants.",
        "tools": {
            0: {
                "cue": "Unlike restaurant_find_group, which finds restaurants suitable for groups, this finds events suitable for groups.",
                "rival_index": 1,
                "axis": "whether the group place is an event or a restaurant",
                "why_confusable": "Both find a place that can take a group in a city.",
                "why_this_rival": "Only one other tool, and the action is the same kind of search.",
                "rejected": ["Cuisine belongs to the restaurant tool. It is not a claim that events have no type."],
                "target_excerpt": "events suitable for groups",
                "rival_excerpt": "restaurants suitable for groups",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request to find something for a group in a city can be read as either. The cue names events against restaurants.",
            },
            1: {
                "cue": "Unlike events_find_event, which finds events suitable for groups, this finds restaurants suitable for groups.",
                "rival_index": 0,
                "axis": "whether the group place is a restaurant or an event",
                "why_confusable": "Both find a place that can take a group in a city.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["The event-type list is an argument of the event tool, not a second cue."],
                "target_excerpt": "restaurants suitable for groups",
                "rival_excerpt": "events suitable for groups",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request for a restaurant does not make the event description true. A request that only names the group and the city can be read as either.",
            },
        },
    },
    "multiple_91": {
        "case_reason": "Both tools locate something from a food criterion. One locates restaurants. The other locates cooking recipes.",
        "tools": {
            0: {
                "cue": "Unlike recipe_find, which locates cooking recipes, this locates restaurants.",
                "rival_index": 1,
                "axis": "whether the result is a restaurant or a cooking recipe",
                "why_confusable": "Both locate something the reader might want when they name a food.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["Price range belongs to the restaurant tool. An ingredient limit belongs to the recipe tool. Neither is a second cue."],
                "target_excerpt": "Locate restaurants",
                "rival_excerpt": "Locate cooking recipes",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request that only names a food can be read as either. The cue names a restaurant against a recipe.",
            },
            1: {
                "cue": "Unlike restaurant_find, which locates restaurants, this locates cooking recipes.",
                "rival_index": 0,
                "axis": "whether the result is a cooking recipe or a restaurant",
                "why_confusable": "Both locate something the reader might want when they name a food.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["Do not treat the shared idea of an ingredient as an exclusion of restaurants."],
                "target_excerpt": "Locate cooking recipes",
                "rival_excerpt": "Locate restaurants",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A recipe and a restaurant are different results. The cue does not say either tool rejects a cuisine name.",
            },
        },
    },
}

ADDED_UNCUE = {
    "multiple_93": {
        "case_reason": "Renting a car and booking a hotel room do not answer a similar request. Sharing a location and a duration count is not a selection axis.",
        "tools": {
            0: "Rents a car for a number of days. The other tool books a hotel room. A car type is not a room type.",
            1: "Books a hotel room for a number of nights. The other tool rents a car. No shared action or resource is documented.",
        },
    },
    "multiple_95": {
        "case_reason": "A unit conversion can already be read as covering a currency conversion, so a cue would be an exclusion the unit description does not state.",
        "tools": {
            0: "Converts an amount from one currency to another. The other tool converts a value from one unit to another, which can already be true of a currency conversion.",
            1: "Converts a value from one unit to another. Naming the currency tool as a rival would claim an exclusion the unit description does not state.",
        },
    },
    "multiple_97": {
        "case_reason": "The area of a circle and a sine-wave plot do not answer a similar request.",
        "tools": {
            0: "Calculates the area of a circle from a radius. The other tool plots a sine wave. A radius is not a frequency.",
            1: "Plots a sine wave over a range. The other tool calculates a circle's area. No shared action or resource is documented.",
        },
    },
}
