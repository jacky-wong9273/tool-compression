"""Eighth official-840 tranche. S and X are separate maps.

These twelve ids are the formative pilot. The judgements below were made
from the fresh converted catalogues. The pilot seals were not copied.
"""

from __future__ import annotations


ADDED_CUED = (
    "multiple_0",
    "multiple_12",
    "multiple_35",
    "multiple_92",
)
ADDED_UNCUE_MULTI = (
    "multiple_7",
    "multiple_11",
    "multiple_100",
    "multiple_153",
)
ADDED_SINGLES = (
    "simple_python_34",
    "simple_python_175",
    "irrelevance_50",
    "irrelevance_59",
)
ADDED_IDS = ADDED_CUED + ADDED_UNCUE_MULTI + ADDED_SINGLES

_EXPECTED = {
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
if set(ADDED_IDS) != _EXPECTED or len(ADDED_IDS) != len(set(ADDED_IDS)):
    raise ValueError("eighth tranche is not exactly the formative twelve")

ADDED_CHANGES = {
    ("multiple_0", 0, "/function/parameters/properties/get_area/description"): {
        "replacement": "A flag to determine whether to calculate the area of triangle.",
        "reason": "The default sentence repeats the schema default true. The replacement keeps that the argument chooses whether the area is calculated.",
        "parts": [
            {
                "excerpt": "A flag to determine whether to calculate the area of triangle",
                "decision": "KEEP",
                "after": "A flag to determine whether to calculate the area of triangle.",
            },
            {
                "excerpt": "Default is true.",
                "duplicate": True,
                "schema_path": "/function/parameters/properties/get_area/default",
                "schema_equals": True,
                "note": "The schema default is the boolean true.",
            },
        ],
    },
    ("multiple_0", 0, "/function/parameters/properties/get_perimeter/description"): {
        "replacement": "A flag to determine whether to calculate the perimeter of triangle.",
        "reason": "The default sentence repeats the schema default true. The replacement keeps that the argument chooses whether the perimeter is calculated.",
        "parts": [
            {
                "excerpt": "A flag to determine whether to calculate the perimeter of triangle",
                "decision": "KEEP",
                "after": "A flag to determine whether to calculate the perimeter of triangle.",
            },
            {
                "excerpt": "Default is true.",
                "duplicate": True,
                "schema_path": "/function/parameters/properties/get_perimeter/default",
                "schema_equals": True,
                "note": "The schema default is the boolean true.",
            },
        ],
    },
    ("multiple_0", 0, "/function/parameters/properties/get_angles/description"): {
        "replacement": "A flag to determine whether to calculate the internal angles of triangle.",
        "reason": "The default sentence repeats the schema default true. The replacement keeps that the argument chooses whether the internal angles are calculated.",
        "parts": [
            {
                "excerpt": "A flag to determine whether to calculate the internal angles of triangle",
                "decision": "KEEP",
                "after": "A flag to determine whether to calculate the internal angles of triangle.",
            },
            {
                "excerpt": "Default is true.",
                "duplicate": True,
                "schema_path": "/function/parameters/properties/get_angles/default",
                "schema_equals": True,
                "note": "The schema default is the boolean true.",
            },
        ],
    },
    ("multiple_0", 1, "/function/parameters/properties/get_area/description"): {
        "replacement": "A flag to determine whether to calculate the area of circle.",
        "reason": "The default sentence repeats the schema default true. The replacement keeps that the argument chooses whether the area is calculated.",
        "parts": [
            {
                "excerpt": "A flag to determine whether to calculate the area of circle",
                "decision": "KEEP",
                "after": "A flag to determine whether to calculate the area of circle.",
            },
            {
                "excerpt": "Default is true.",
                "duplicate": True,
                "schema_path": "/function/parameters/properties/get_area/default",
                "schema_equals": True,
                "note": "The schema default is the boolean true.",
            },
        ],
    },
    ("multiple_0", 1, "/function/parameters/properties/get_circumference/description"): {
        "replacement": "A flag to determine whether to calculate the circumference of circle.",
        "reason": "The default sentence repeats the schema default true. The replacement keeps that the argument chooses whether the circumference is calculated.",
        "parts": [
            {
                "excerpt": "A flag to determine whether to calculate the circumference of circle",
                "decision": "KEEP",
                "after": "A flag to determine whether to calculate the circumference of circle.",
            },
            {
                "excerpt": "Default is true.",
                "duplicate": True,
                "schema_path": "/function/parameters/properties/get_circumference/default",
                "schema_equals": True,
                "note": "The schema default is the boolean true.",
            },
        ],
    },
    ("multiple_100", 0, "/function/parameters/properties/scale_type/description"): {
        "replacement": "The type of scale to generate.",
        "reason": "The default sentence repeats the schema default major. The replacement keeps that the argument chooses the scale type.",
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
}

ADDED_CONFLICTS = {
    ("multiple_11", 2, "/function/parameters/properties/degree/description"): [
        "The prose says the default is 0. The schema has no default. Left as written."
    ],
    ("multiple_35", 0, "/function/parameters/properties/method/description"): [
        "The prose says the default is 'standard'. The schema has no default. Left as written."
    ],
    ("multiple_35", 1, "/function/parameters/properties/algorithm/description"): [
        "The prose says the default is 'euclidean'. The schema has no default. Left as written."
    ],
    ("multiple_92", 0, "/function/parameters/properties/categories/description"): [
        "The prose says the default is an empty array. The schema has no default. Left as written."
    ],
    ("multiple_92", 1, "/function/parameters/properties/categories/description"): [
        "The prose says the default is an empty array. The schema has no default. Left as written."
    ],
    ("multiple_92", 2, "/function/parameters/properties/categories/description"): [
        "The prose says the default is an empty array. The schema has no default. Left as written."
    ],
    ("multiple_153", 1, "/function/parameters/properties/isothermal/description"): [
        "The prose says the default is True. The schema has no default. Left as written."
    ],
    ("multiple_153", 2, "/function/parameters/properties/location/description"): [
        "The prose says the location defaults to global if not specified. The schema has no default. Left as written."
    ],
}

ADDED_CUES = {
    "multiple_0": {
        "case_reason": "Both retrieve dimensions of a shape. One is a triangle from three sides. The other is a circle from a radius.",
        "tools": {
            0: {
                "cue": "Unlike circle_properties_get, which retrieves the area and circumference of a circle, this retrieves the area and perimeter of a triangle.",
                "rival_index": 1,
                "axis": "whether the dimensions are for a triangle or a circle",
                "why_confusable": "Both retrieve dimensions that include an area. A request that only says the area can be read as either.",
                "why_this_rival": "The other tool is the circle. There is no earlier shape tool.",
                "rejected": ["A cue that says the triangle tool excludes a circle."],
                "target_excerpt": "area and perimeter, of a triangle",
                "rival_excerpt": "area and circumference, of a circle",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request that names a triangle or a circle makes only one description true. A request that only says the area can be read as either.",
            },
            1: {
                "cue": "Unlike triangle_properties_get, which retrieves the area and perimeter of a triangle, this retrieves the area and circumference of a circle.",
                "rival_index": 0,
                "axis": "whether the dimensions are for a circle or a triangle",
                "why_confusable": "Both retrieve dimensions that include an area. A request that only says the area can be read as either.",
                "why_this_rival": "The other tool is the triangle. There is no earlier shape tool.",
                "rejected": ["A cue that says the circle tool excludes a triangle."],
                "target_excerpt": "area and circumference, of a circle",
                "rival_excerpt": "area and perimeter, of a triangle",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request that names a circle or a triangle makes only one description true. A request that only says the area can be read as either.",
            },
        },
    },
    "multiple_12": {
        "case_reason": "All three calculate a company figure. The two returns differ by the base. The growth rate is a different figure, so its rival is the earlier return.",
        "tools": {
            0: {
                "cue": "Unlike financial_ratios_calculate_ROE, which calculates the return on equity, this calculates the year over year growth rate.",
                "rival_index": 1,
                "axis": "whether the company figure is year-over-year growth or a return on equity",
                "why_confusable": "Both calculate a company figure. A request that only says the company's rate can be read as either.",
                "why_this_rival": "The two return tools are the same kind of alternative to a growth rate. Catalogue order selects the earlier return.",
                "rejected": ["financial_ratios_calculate_ROA is the later return tool.", "Naming both return tools."],
                "target_excerpt": "year over year (YOY) growth rate",
                "rival_excerpt": "return on equity (ROE)",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request that names year-over-year growth or return on equity makes only one description true. A request that only says the company's rate can be read as either.",
            },
            1: {
                "cue": "Unlike financial_ratios_calculate_ROA, which calculates the return on assets from total average assets, this calculates the return on equity from average shareholder equity.",
                "rival_index": 2,
                "axis": "whether the return uses average shareholder equity or total average assets",
                "why_confusable": "Both calculate a return for a period. A request that only says the company's return can be read as either.",
                "why_this_rival": "The other return uses the other base. The growth-rate tool is not a return.",
                "rejected": ["corporate_finance_calculate_YOY_growth_rate calculates a growth rate, not a return."],
                "target_excerpt": "return on equity (ROE)",
                "rival_excerpt": "return on assets (ROA)",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request that names equity or assets makes only one description true. A request that only says the company's return can be read as either.",
            },
            2: {
                "cue": "Unlike financial_ratios_calculate_ROE, which calculates the return on equity from average shareholder equity, this calculates the return on assets from total average assets.",
                "rival_index": 1,
                "axis": "whether the return uses total average assets or average shareholder equity",
                "why_confusable": "Both calculate a return for a period. A request that only says the company's return can be read as either.",
                "why_this_rival": "The other return uses the other base. The growth-rate tool is not a return.",
                "rejected": ["corporate_finance_calculate_YOY_growth_rate calculates a growth rate, not a return."],
                "target_excerpt": "return on assets (ROA)",
                "rival_excerpt": "return on equity (ROE)",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request that names assets or equity makes only one description true. A request that only says the company's return can be read as either.",
            },
        },
    },
    "multiple_35": {
        "case_reason": "Both calculate a shared value of two integers. One is the least common multiple. The other is the greatest common divisor.",
        "tools": {
            0: {
                "cue": "Unlike calculate_gcd, which calculates the greatest common divisor, this calculates the least common multiple.",
                "rival_index": 1,
                "axis": "whether the shared value is the least common multiple or the greatest common divisor",
                "why_confusable": "Both take two integers and calculate a shared value. A request that only says the common value can be read as either.",
                "why_this_rival": "The other tool is the greatest common divisor. There is no earlier shared-value tool.",
                "rejected": ["A cue that says the least common multiple excludes a divisor."],
                "target_excerpt": "least common multiple (lcm)",
                "rival_excerpt": "greatest common divisor (gcd)",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request that names the least common multiple or the greatest common divisor makes only one description true. A request that only says the common value can be read as either.",
            },
            1: {
                "cue": "Unlike calculate_lcm, which calculates the least common multiple, this calculates the greatest common divisor.",
                "rival_index": 0,
                "axis": "whether the shared value is the greatest common divisor or the least common multiple",
                "why_confusable": "Both take two integers and calculate a shared value. A request that only says the common value can be read as either.",
                "why_this_rival": "The other tool is the least common multiple. There is no earlier shared-value tool.",
                "rejected": ["A cue that says the greatest common divisor excludes a multiple."],
                "target_excerpt": "greatest common divisor (gcd)",
                "rival_excerpt": "least common multiple (lcm)",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request that names the greatest common divisor or the least common multiple makes only one description true. A request that only says the common value can be read as either.",
            },
        },
    },
    "multiple_92": {
        "case_reason": "All three get available vegan products at a named store. The stores are Safeway, Whole Foods, and Walmart.",
        "tools": {
            0: {
                "cue": "Unlike wholefoods_vegan_products, which gets vegan products at a Whole Foods store, this gets vegan products at a Safeway store.",
                "rival_index": 1,
                "axis": "whether the vegan products are at Safeway or Whole Foods",
                "why_confusable": "All three get vegan products at a store. A request that only says the store can be read as any of them.",
                "why_this_rival": "Whole Foods and Walmart are the same kind of alternative to Safeway. Catalogue order selects Whole Foods.",
                "rejected": ["Naming both other stores.", "Using walmart_vegan_products, which is the later store."],
                "target_excerpt": "Safeway store",
                "rival_excerpt": "Whole Foods store",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request that names Safeway or Whole Foods makes only one description true. A request that only says vegan products at a store can be read as either.",
            },
            1: {
                "cue": "Unlike safeway_vegan_products, which gets vegan products at a Safeway store, this gets vegan products at a Whole Foods store.",
                "rival_index": 0,
                "axis": "whether the vegan products are at Whole Foods or Safeway",
                "why_confusable": "All three get vegan products at a store. A request that only says the store can be read as any of them.",
                "why_this_rival": "Safeway is the earlier store. Walmart is the later store of the same kind.",
                "rejected": ["Naming both other stores.", "Using walmart_vegan_products, which is the later store."],
                "target_excerpt": "Whole Foods store",
                "rival_excerpt": "Safeway store",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request that names Whole Foods or Safeway makes only one description true. A request that only says vegan products at a store can be read as either.",
            },
            2: {
                "cue": "Unlike safeway_vegan_products, which gets vegan products at a Safeway store, this gets vegan products at a Walmart store.",
                "rival_index": 0,
                "axis": "whether the vegan products are at Walmart or Safeway",
                "why_confusable": "All three get vegan products at a store. A request that only says the store can be read as any of them.",
                "why_this_rival": "Safeway and Whole Foods are the same kind of alternative to Walmart. Catalogue order selects Safeway.",
                "rejected": ["Naming both other stores.", "Using wholefoods_vegan_products, which is the later store."],
                "target_excerpt": "Walmart store",
                "rival_excerpt": "Safeway store",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request that names Walmart or Safeway makes only one description true. A request that only says vegan products at a store can be read as either.",
            },
        },
    },
}

ADDED_UNCUE = {
    "multiple_7": {
        "case_reason": "Population growth of a species and the impact of a species on an ecosystem do not answer a similar request.",
        "tools": {
            0: "Assesses the population growth of a specific species in a specified location over a period. The other tool does not document a shared action or resource with that request.",
            1: "Analyzes the impact of a species on a particular ecosystem. The other tool does not document a shared action or resource with that request.",
        },
    },
    "multiple_11": {
        "case_reason": "A quadratic equation and a cubic equation are polynomial equations. A cue against the polynomial tool would read as an exclusion that description does not state, so the case has no cue that covers every tool.",
        "tools": {
            0: "Calculate the roots of a quadratic equation. The other tools do not document a shared action or resource with that request.",
            1: "Calculate the roots of a cubic equation. The other tools do not document a shared action or resource with that request.",
            2: "Calculate the roots of a polynomial equation. The other tools do not document a shared action or resource with that request.",
        },
    },
    "multiple_100": {
        "case_reason": "A music scale progression and the highest common factor of two numbers do not answer a similar request.",
        "tools": {
            0: "Generate a music scale progression in a specific key with a given tempo and duration. The other tool does not document a shared action or resource with that request.",
            1: "Calculate the highest common factor of two numbers. The other tool does not document a shared action or resource with that request.",
        },
    },
    "multiple_153": {
        "case_reason": "Tallest mountains, an entropy change, and the date of a historical event do not answer a similar request.",
        "tools": {
            0: "Find the tallest mountains within a specified radius of a location. The other tools do not document a shared action or resource with that request.",
            1: "Calculate the entropy change for an isothermal and reversible process. The other tools do not document a shared action or resource with that request.",
            2: "Retrieve the date of a historical event. The other tools do not document a shared action or resource with that request.",
        },
    },
}
