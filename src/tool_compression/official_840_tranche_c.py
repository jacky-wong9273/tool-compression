"""Third official-840 tranche. S and X are separate maps.

The formative pilot ids are not in this tranche. Cue text is taken from
the original function descriptions, not from S.
"""

from __future__ import annotations


def _span(prefix: str, start: int, end: int) -> tuple[str, ...]:
    return tuple(f"{prefix}_{index}" for index in range(start, end))


ADDED_SINGLES = _span("simple_python", 62, 142) + _span("irrelevance", 62, 112)
ADDED_CUED = (
    "multiple_54",
    "multiple_58",
    "multiple_61",
    "multiple_62",
    "multiple_69",
    "multiple_72",
    "multiple_76",
)
ADDED_UNCUE_MULTI = (
    "multiple_55",
    "multiple_59",
    "multiple_74",
    "multiple_78",
    "multiple_79",
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
    raise ValueError("third tranche overlaps the formative pilot or repeats an id")

ADDED_CHANGES = {
    ("irrelevance_62", 0, "/function/description"): {
        "replacement": "Create a recommendation model using a given user data and an algorithm type.",
        "reason": "The frame 'This function is used to' is not a separate claim. The replacement keeps creating a recommendation model from user data and an algorithm type.",
    },
    ("irrelevance_64", 0, "/function/parameters/properties/coin_type/description"): {
        "replacement": "The type of the coin. Possible values are 'fair', 'double_heads', 'double_tails'.",
        "reason": "The default sentence repeats the schema default fair. The possible values stay because they name the accepted inputs.",
        "parts": [
            {
                "excerpt": "The type of the coin",
                "decision": "KEEP",
                "after": "The type of the coin.",
            },
            {
                "excerpt": "Default is 'fair'.",
                "duplicate": True,
                "schema_path": "/function/parameters/properties/coin_type/default",
                "schema_equals": "fair",
                "note": "The schema default is the string fair.",
            },
            {
                "excerpt": "Possible values are 'fair', 'double_heads', 'double_tails'.",
                "decision": "KEEP",
                "after": "Possible values are 'fair', 'double_heads', 'double_tails'.",
                "note": "The accepted values stay in the prose.",
            },
        ],
    },
}

ADDED_CONFLICTS = {
    ("simple_python_64", 0, "/function/description"): [
        "The function says the homozygous dominant genotype. The genotype parameter also lists Aa and aa. Left unrepaired."
    ],
    ("simple_python_82", 0, "/function/description"): [
        "Prose says list. The numbers parameter schema type is array. Left as written."
    ],
    ("simple_python_87", 0, "/function/description"): [
        "Prose says list. The list parameter schema type is array. Left as written."
    ],
    ("simple_python_103", 0, "/function/parameters/properties/limits/description"): [
        "Prose says list. Schema type is array. Left as written."
    ],
    ("simple_python_113", 0, "/function/description"): [
        "The function says a six-sided die. die_sides can name another number of sides. Left unrepaired."
    ],
    ("simple_python_130", 0, "/function/parameters/properties/cash_flows/description"): [
        "Prose says list. Schema type is array. Left as written."
    ],
    ("irrelevance_69", 0, "/function/parameters/properties/scaler/description"): [
        "Prose says a scaler object. Schema type is number, and the schema default is the string '1.2'. Left unrepaired."
    ],
    ("irrelevance_75", 0, "/function/parameters/properties/period/description"): [
        "Schema type is integer and the schema default is the string '5 years'. The prose says a number of time periods. Left unrepaired."
    ],
    ("irrelevance_87", 0, "/function/parameters/properties/documents/description"): [
        "Prose says list. Schema type is array. Left as written."
    ],
    ("irrelevance_90", 0, "/function/description"): [
        "The function says a noise complaint. complaint_type also names other complaint types. Left unrepaired."
    ],
}

ADDED_CUES = {
    "multiple_54": {
        "case_reason": "Both tools retrieve a company's market history. One returns dividend data. The other returns stock market data.",
        "tools": {
            0: {
                "cue": "Unlike stock_market_data, which retrieves stock market data, this gets historical dividend data.",
                "rival_index": 1,
                "axis": "whether the company history is dividend data or stock market data",
                "why_confusable": "Both retrieve a company's recorded market history over a time span.",
                "why_this_rival": "Only one other tool, and the action is the same kind of retrieval.",
                "rejected": ["Years versus days follows the dataset. It is not a second cue."],
                "target_excerpt": "historical dividend data",
                "rival_excerpt": "stock market data",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request for a company's market history can be read as either dataset. A request that names dividends does not make the stock-market description true.",
            },
            1: {
                "cue": "Unlike corporate_finance_dividend_data, which gets historical dividend data, this retrieves stock market data.",
                "rival_index": 0,
                "axis": "whether the company history is stock market data or dividend data",
                "why_confusable": "Both retrieve a company's recorded market history over a time span.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["The dividend frequency is an argument of the dividend tool, not the contrast with stock market data."],
                "target_excerpt": "stock market data",
                "rival_excerpt": "historical dividend data",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "The cue names the dataset. It does not say either tool rejects a company name.",
            },
        },
    },
    "multiple_58": {
        "case_reason": "Both tools search by location and expertise. One searches for a doctor. The other searches for a lawyer.",
        "tools": {
            0: {
                "cue": "Unlike lawyer_search, which searches for a lawyer, this searches for a doctor.",
                "rival_index": 1,
                "axis": "whether the search is for a doctor or a lawyer",
                "why_confusable": "Both search for a professional by location and area of expertise.",
                "why_this_rival": "Only one other tool, and the action is the same.",
                "rejected": ["The example specialties are not the selection axis."],
                "target_excerpt": "Search for a doctor",
                "rival_excerpt": "Search for a lawyer",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request that only says to find a professional in a city can be read as either. The cue names the profession.",
            },
            1: {
                "cue": "Unlike doctor_search, which searches for a doctor, this searches for a lawyer.",
                "rival_index": 0,
                "axis": "whether the search is for a lawyer or a doctor",
                "why_confusable": "Both search for a professional by location and area of expertise.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["Do not treat the shared city example as the difference."],
                "target_excerpt": "Search for a lawyer",
                "rival_excerpt": "Search for a doctor",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request for a lawyer does not make the doctor description true. A vague professional search can be read as either.",
            },
        },
    },
    "multiple_61": {
        "case_reason": "Both tools search by location and specialization. One searches for a home renovation expert. The other searches for a landscape architect.",
        "tools": {
            0: {
                "cue": "Unlike landscape_architect_find_specialty, which searches for a landscape architect, this searches for a home renovation expert.",
                "rival_index": 1,
                "axis": "whether the professional is a home renovation expert or a landscape architect",
                "why_confusable": "Both search for a local specialist by location and area of work.",
                "why_this_rival": "Only one other tool, and the action is the same.",
                "rejected": ["Years of experience is a shared optional argument, not the selection axis."],
                "target_excerpt": "home renovation expert",
                "rival_excerpt": "landscape architect",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request for a local specialist can be read as either profession. The cue names which one.",
            },
            1: {
                "cue": "Unlike home_renovation_expert_find_specialty, which searches for a home renovation expert, this searches for a landscape architect.",
                "rival_index": 0,
                "axis": "whether the professional is a landscape architect or a home renovation expert",
                "why_confusable": "Both search for a local specialist by location and area of work.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["The listed design areas belong to the architect tool. They are not a second cue."],
                "target_excerpt": "landscape architect",
                "rival_excerpt": "home renovation expert",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "The cue names the profession. It does not say either tool rejects a city.",
            },
        },
    },
    "multiple_62": {
        "case_reason": "Both tools locate a nearby place from a city. One locates nature parks. The other locates restaurants.",
        "tools": {
            0: {
                "cue": "Unlike restaurant_find_nearby, which locates nearby restaurants, this locates nearby nature parks.",
                "rival_index": 1,
                "axis": "whether the nearby places are nature parks or restaurants",
                "why_confusable": "Both locate nearby places from a city and a preference list.",
                "why_this_rival": "Only one other tool, and the action is the same.",
                "rejected": ["Camping and scenic views are examples on the park tool, not the contrast with restaurants."],
                "target_excerpt": "nearby nature parks",
                "rival_excerpt": "nearby restaurants",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request to find somewhere nearby can be read as either. The cue names parks against restaurants.",
            },
            1: {
                "cue": "Unlike nature_park_find_nearby, which locates nearby nature parks, this locates nearby restaurants.",
                "rival_index": 0,
                "axis": "whether the nearby places are restaurants or nature parks",
                "why_confusable": "Both locate nearby places from a city and a preference list.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["The amenity list is an argument of the restaurant tool, not a claim that parks have no criteria."],
                "target_excerpt": "nearby restaurants",
                "rival_excerpt": "nearby nature parks",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request for a restaurant does not make the park description true. A request that only names the city can be read as either.",
            },
        },
    },
    "multiple_69": {
        "case_reason": "Both tools analyse personality. One uses the Myers-Briggs Type Indicator. The other uses the five-factor model.",
        "tools": {
            0: {
                "cue": "Unlike five_factor_model_analyse, which analyses personality based on the five-factor model, this analyses personality based on the Myers-Briggs Type Indicator.",
                "rival_index": 1,
                "axis": "whether the personality analysis uses the Myers-Briggs Type Indicator or the five-factor model",
                "why_confusable": "Both analyse personality. A request that only says to analyse personality can be read as either instrument.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["The four MBTI preference axes are arguments of that instrument, not a claim that the five-factor model lacks traits."],
                "target_excerpt": "Myers-Briggs Type Indicator",
                "rival_excerpt": "five-factor model",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "The two instruments are alternatives, not a class and a subclass. The cue names the instrument.",
            },
            1: {
                "cue": "Unlike MBTI_analyse, which analyses personality based on the Myers-Briggs Type Indicator, this analyses personality based on the five-factor model.",
                "rival_index": 0,
                "axis": "whether the personality analysis uses the five-factor model or the Myers-Briggs Type Indicator",
                "why_confusable": "Both analyse personality.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["Do not treat the Big Five trait list as an exclusion of the Myers-Briggs tool."],
                "target_excerpt": "five-factor model",
                "rival_excerpt": "Myers-Briggs Type Indicator",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request that names one instrument makes only that description true. A request that only says personality can be read as either.",
            },
        },
    },
    "multiple_72": {
        "case_reason": "Both tools retrieve a historical figure for a U.S. state and a year. One retrieves population. The other retrieves GDP.",
        "tools": {
            0: {
                "cue": "Unlike us_economy_gdp_by_state_year, which retrieves historical GDP data, this retrieves historical population data.",
                "rival_index": 1,
                "axis": "whether the state-year figure is population or GDP",
                "why_confusable": "Both retrieve a historical figure for the same state and year.",
                "why_this_rival": "Only one other tool, and the action is the same kind of retrieval.",
                "rejected": ["Real versus nominal is an argument of the GDP tool, not the contrast with population."],
                "target_excerpt": "historical population data",
                "rival_excerpt": "historical GDP data",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request for a state's historical figure in a year can be read as either. The cue names population against GDP.",
            },
            1: {
                "cue": "Unlike us_history_population_by_state_year, which retrieves historical population data, this retrieves historical GDP data.",
                "rival_index": 0,
                "axis": "whether the state-year figure is GDP or population",
                "why_confusable": "Both retrieve a historical figure for the same state and year.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["Do not use the inflation adjustment as the reason to choose a tool."],
                "target_excerpt": "historical GDP data",
                "rival_excerpt": "historical population data",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "Population and GDP are different figures. The cue does not say either tool rejects a year.",
            },
        },
    },
    "multiple_76": {
        "case_reason": "Both tools order a custom art object. One orders a painting. The other orders a sculpture.",
        "tools": {
            0: {
                "cue": "Unlike sculpture_create_custom, which orders a custom sculpture, this orders a custom painting.",
                "rival_index": 1,
                "axis": "whether the custom object is a painting or a sculpture",
                "why_confusable": "Both order a custom art object of a chosen subject and size.",
                "why_this_rival": "Only one other tool, and the action is the same.",
                "rejected": ["Color versus material follows the object. It is not a second cue."],
                "target_excerpt": "custom painting",
                "rival_excerpt": "custom sculpture",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request to commission a custom piece can be read as either object. The cue names a painting against a sculpture.",
            },
            1: {
                "cue": "Unlike painting_create_custom, which orders a custom painting, this orders a custom sculpture.",
                "rival_index": 0,
                "axis": "whether the custom object is a sculpture or a painting",
                "why_confusable": "Both order a custom art object of a chosen subject and size.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["The shared default size is not the selection axis."],
                "target_excerpt": "custom sculpture",
                "rival_excerpt": "custom painting",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "The cue names the object. It does not say either tool rejects a subject.",
            },
        },
    },
}

ADDED_UNCUE = {
    "multiple_55": {
        "case_reason": "A stock-price forecast and a weather forecast do not answer a similar request. Sharing a day count is not a selection axis.",
        "tools": {
            0: "Predicts a company's future stock price. The other tool retrieves a weather forecast. A stock price is not weather.",
            1: "Retrieves a weather forecast for a city. The other tool predicts a stock price. No shared action or resource is documented.",
        },
    },
    "multiple_59": {
        "case_reason": "Renting a car and locating a lawyer do not answer a similar request.",
        "tools": {
            0: "Rents a car. The other tool locates lawyers. A fuel type is not a legal specialization.",
            1: "Locates lawyers by specialization. The other tool rents a car. No selection cue is written.",
        },
    },
    "multiple_74": {
        "case_reason": "An artwork's auction price and a library book search do not answer a similar request, even though both take a title, a creator, and a platform.",
        "tools": {
            0: "Fetches the auction price of an artwork. The other tool searches for a library book. A price is not a book search.",
            1: "Searches for a book in a library. The other tool fetches an artwork price. No shared action or resource is documented.",
        },
    },
    "multiple_78": {
        "case_reason": "A museum can already be a tourist spot, so both descriptions can be true of one museum request. A cue would read as an exclusion the tourist-spot description does not state.",
        "tools": {
            0: "Retrieves information about a tourist spot. A museum can be that spot, so naming the museum tool as a rival would claim an exclusion the source does not state.",
            1: "Retrieves information about a museum. The tourist-spot description can already be true of the same museum. No cue is written.",
        },
    },
    "multiple_79": {
        "case_reason": "Restaurant information for an area and exhibition information for a museum do not answer a similar request.",
        "tools": {
            0: "Gets restaurant information for an area. The other tool gets exhibition information for a museum. A cuisine is not an exhibition.",
            1: "Gets exhibition information for a museum. The other tool gets restaurant information. No shared action or resource is documented.",
        },
    },
}
