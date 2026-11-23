"""Second official-840 tranche. S and X are separate maps.

Single-tool ids were read from that tool's converted name, schema, and
description strings. The formative pilot ids are not in this tranche.
Cue text is taken from the original function descriptions, not from S.
"""

from __future__ import annotations


def _span(prefix: str, start: int, end: int) -> tuple[str, ...]:
    return tuple(f"{prefix}_{index}" for index in range(start, end))


ADDED_SINGLES = (
    _span("simple_python", 3, 34)
    + _span("simple_python", 35, 62)
    + _span("irrelevance", 3, 50)
    + _span("irrelevance", 51, 59)
    + _span("irrelevance", 60, 62)
)
ADDED_CUED = (
    "multiple_3",
    "multiple_8",
    "multiple_10",
    "multiple_13",
    "multiple_15",
    "multiple_29",
    "multiple_32",
    "multiple_36",
    "multiple_38",
    "multiple_40",
    "multiple_47",
    "multiple_48",
    "multiple_53",
)
ADDED_UNCUE_MULTI = ("multiple_39", "multiple_42", "multiple_52")
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
    raise ValueError("second tranche overlaps the formative pilot or repeats an id")

ADDED_CHANGES = {
    ("multiple_10", 0, "/function/description"): {
        "replacement": "Delete or add columns in a database.",
        "reason": "The frame 'This function allows' is not a separate claim. The replacement keeps deletion and addition of columns.",
    },
    ("multiple_10", 1, "/function/description"): {
        "replacement": "Create a backup of the database before modification.",
        "reason": "The frame 'This function' is not a separate claim. The replacement keeps creating a backup before modification.",
    },
    ("simple_python_4", 0, "/function/description"): {
        "replacement": "Solve the quadratic equation and return its roots.",
        "reason": "The frame 'Function' is not a separate claim. The replacement keeps solving the quadratic equation and returning its roots.",
    },
    ("simple_python_16", 0, "/function/parameters/properties/function_variable/description"): {
        "replacement": "The variable present in the function. Default is 'x'.",
        "reason": "The examples x and y are open-ended illustration. The replacement keeps the variable and the default x, which the schema does not state.",
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
    ("simple_python_17", 0, "/function/description"): {
        "replacement": "Retrieve prime factors of a number.",
        "reason": "The frame 'Function to' is not a separate claim. The replacement keeps retrieving prime factors of a number.",
    },
    ("irrelevance_32", 0, "/function/description"): {
        "replacement": "Return the type of the cell based on it's characteristics.",
        "reason": "The frame 'This function will' is not a separate claim. The replacement keeps returning the cell type, including the source apostrophe.",
    },
    ("irrelevance_32", 0, "/function/parameters/properties/membrane_type/description"): {
        "replacement": "Type of membrane in the cell.",
        "reason": "The trailing clause repeats the schema default. The replacement keeps that the argument is the membrane type.",
        "parts": [
            {
                "excerpt": "Type of membrane in the cell",
                "decision": "KEEP",
                "after": "Type of membrane in the cell.",
            },
            {
                "excerpt": ", default value is 'Phospholipid bi-layer'",
                "duplicate": True,
                "schema_path": "/function/parameters/properties/membrane_type/default",
                "schema_equals": "Phospholipid bi-layer",
                "note": "The schema default is that string.",
            },
        ],
    },
    ("irrelevance_55", 0, "/function/description"): {
        "replacement": "Add a product to the user's cart.",
        "reason": "The frame 'This function allows users to' is not a separate claim. The replacement keeps adding a product to the user's cart.",
    },
    ("irrelevance_58", 0, "/function/parameters/properties/usage_efficiency/description"): {
        "replacement": "The efficiency of energy usage in the home. This is a float type value.",
        "reason": "The default 0.8 repeats the schema default. The float sentence stays.",
        "parts": [
            {
                "excerpt": "The efficiency of energy usage in the home",
                "decision": "KEEP",
                "after": "The efficiency of energy usage in the home.",
            },
            {
                "excerpt": ", default is 0.8",
                "duplicate": True,
                "schema_path": "/function/parameters/properties/usage_efficiency/default",
                "schema_equals": 0.8,
                "note": "The schema default is 0.8.",
            },
            {
                "excerpt": "This is a float type value.",
                "decision": "KEEP",
                "after": "This is a float type value.",
                "note": "The handler float sentence stays.",
            },
        ],
    },
}

ADDED_CONFLICTS = {
    ("simple_python_5", 0, "/function/description"): [
        "The function says an unspecified root_type may return complex roots. The root_type description says the default is 'real'. Left unrepaired."
    ],
    ("simple_python_17", 0, "/function/parameters/properties/number/description"): [
        "Prose says number. Schema type is integer. Left as written."
    ],
    ("simple_python_30", 0, "/function/description"): [
        "The function says the calculation assumes initial velocity is 0. The initial_velocity parameter can be set. Left unrepaired."
    ],
    ("simple_python_54", 0, "/function/description"): [
        "The function says a human gene. The species parameter can name another species. Left unrepaired."
    ],
    ("irrelevance_24", 0, "/function/description"): [
        "The function names voltage and resistance. A frequency parameter is also present. Left unrepaired."
    ],
    ("irrelevance_38", 0, "/function/parameters/properties/author/description"): [
        "The author description says an omitted author fetches the most-cited paper. The schema default is the string 'None'. Left unrepaired."
    ],
    ("irrelevance_45", 0, "/function/parameters/properties/vertices/description"): [
        "Prose says list. Schema type is array. Left as written."
    ],
    ("irrelevance_53", 0, "/function/parameters/properties/connect_credentials/description"): [
        "Prose says dictionary. Schema type is object. Left as written."
    ],
    ("irrelevance_55", 0, "/function/parameters/properties/cart_id/description"): [
        "The description says a missing id creates a new cart. The schema default is the string '0'. Left unrepaired."
    ],
    ("multiple_10", 0, "/function/parameters/properties/columns/description"): [
        "Prose says list. Schema type is array. Left as written."
    ],
    ("multiple_36", 1, "/function/description"): [
        "The function says the object starts from rest. initial_speed can be set, and its schema default is 0. Left unrepaired."
    ],
    ("multiple_39", 0, "/function/parameters/properties/items/description"): [
        "Prose says list. Schema type is array. Left as written."
    ],
}

ADDED_CUES = {
    "multiple_3": {
        "case_reason": "Both tools take two points. One returns the Euclidean distance. The other returns the angle with respect to the x-axis.",
        "tools": {
            0: {
                "cue": "Unlike angleToXAxis_calculate, which calculates the angle between two points with respect to the x-axis, this calculates the Euclidean distance.",
                "rival_index": 1,
                "axis": "whether the result for the two points is the Euclidean distance or the angle with respect to the x-axis",
                "why_confusable": "Both calculate a relation between the same two points.",
                "why_this_rival": "Only one other tool, and it states the other relation.",
                "rejected": ["The shared rounding argument is not the selection axis."],
                "target_excerpt": "Euclidean distance",
                "rival_excerpt": "angle between two points with respect to x-axis",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request that only names two points can be read as either result. A request that names the distance does not make the angle description true.",
            },
            1: {
                "cue": "Unlike EuclideanDistance_calculate, which calculates the Euclidean distance, this calculates the angle between two points with respect to the x-axis.",
                "rival_index": 0,
                "axis": "whether the result for the two points is the angle with respect to the x-axis or the Euclidean distance",
                "why_confusable": "Both calculate a relation between the same two points.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["Do not treat the shared point parameters as the reason to choose a tool."],
                "target_excerpt": "angle between two points with respect to x-axis",
                "rival_excerpt": "Euclidean distance",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "The cue names the angle, including the x-axis, which is the source's own qualifier.",
            },
        },
    },
    "multiple_8": {
        "case_reason": "Both tools take a location, a property type, and a bedroom count. One estimates a value. The other finds properties.",
        "tools": {
            0: {
                "cue": "Unlike realestate_find_properties, which finds properties, this gets the estimated value of a property.",
                "rival_index": 1,
                "axis": "whether the result is an estimated property value or a set of properties",
                "why_confusable": "Both answer a property request with the same location, type, and bedroom inputs.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["The budget parameter belongs only to the finder. It is not a second cue."],
                "target_excerpt": "estimated value",
                "rival_excerpt": "Find properties",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request that only names a city and a property type can be read as a valuation or a search. The cue names which result.",
            },
            1: {
                "cue": "Unlike property_valuation_get, which gets the estimated value of a property, this finds properties.",
                "rival_index": 0,
                "axis": "whether the result is a set of properties or an estimated property value",
                "why_confusable": "Both answer a property request with the same location, type, and bedroom inputs.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["The shared example city is not the selection axis."],
                "target_excerpt": "Find properties",
                "rival_excerpt": "estimated value",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request for listings does not make the valuation description true. A request that only describes the property can be read as either.",
            },
        },
    },
    "multiple_10": {
        "case_reason": "Both tools name a database. One deletes or adds columns. The other creates a backup.",
        "tools": {
            0: {
                "cue": "Unlike database_create_backup, which creates a backup of the database, this deletes or adds columns.",
                "rival_index": 1,
                "axis": "whether the database operation deletes or adds columns or creates a backup",
                "why_confusable": "Both act on a named database. A request that only says to handle the database can be read as either.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["The backup timestamp is an argument of the backup, not a contrast with column edits."],
                "target_excerpt": "deletion or addition of columns",
                "rival_excerpt": "creates a backup of the database",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request to change columns does not make the backup description true. A request that only names the database can be read as either, and the cue names the operation.",
            },
            1: {
                "cue": "Unlike database_modify_columns, which deletes or adds columns, this creates a backup of the database.",
                "rival_index": 0,
                "axis": "whether the database operation creates a backup or deletes or adds columns",
                "why_confusable": "Both act on a named database.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["Do not say the backup tool is unable to change columns. The source does not say that."],
                "target_excerpt": "creates a backup of the database",
                "rival_excerpt": "deletion or addition of columns",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "The cue keeps 'before modification' out of the contrast. The one difference is backup versus a column change.",
            },
        },
    },
    "multiple_13": {
        "case_reason": "Both tools take a company and a product. One fetches the current selling price. The other estimates revenue.",
        "tools": {
            0: {
                "cue": "Unlike corporate_finance_revenue_forecast, which estimates the revenue, this fetches the current selling price.",
                "rival_index": 1,
                "axis": "whether the result is the current selling price or a revenue estimate",
                "why_confusable": "Both answer a money question about a company's product.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["The sales-increase percentage is an argument of the revenue estimate, not a claim that the price tool lacks a company."],
                "target_excerpt": "current selling price",
                "rival_excerpt": "revenue",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request for the product's price does not make the revenue description true. A request that only names the product and the company can be read as either.",
            },
            1: {
                "cue": "Unlike corporate_finance_product_price, which fetches the current selling price, this estimates the revenue.",
                "rival_index": 0,
                "axis": "whether the result is a revenue estimate or the current selling price",
                "why_confusable": "Both answer a money question about a company's product.",
                "why_this_rival": "Only one other tool. The function description is the selection text.",
                "rejected": ["Do not use the price as an input inside the revenue sentence as a second cue."],
                "target_excerpt": "revenue",
                "rival_excerpt": "current selling price",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "Revenue and selling price are both documented results. The cue names which one.",
            },
        },
    },
    "multiple_15": {
        "case_reason": "Both tools estimate energy output for a location and a month. One is a solar farm. The other is a wind farm.",
        "tools": {
            0: {
                "cue": "Unlike windFarm_potential, which estimates the energy output of a wind farm, this estimates the energy output of a solar farm.",
                "rival_index": 1,
                "axis": "whether the energy output is for a solar farm or a wind farm",
                "why_confusable": "Both estimate monthly energy output at a location.",
                "why_this_rival": "Only one other tool, and the action is the same.",
                "rejected": ["Panel area versus turbine count follows the farm type. It is not a second cue."],
                "target_excerpt": "energy output of a solar farm",
                "rival_excerpt": "energy output of a wind farm",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request that only asks for a site's monthly energy can be read as either farm. A request that names solar does not make the wind description true.",
            },
            1: {
                "cue": "Unlike solarFarm_potential, which estimates the energy output of a solar farm, this estimates the energy output of a wind farm.",
                "rival_index": 0,
                "axis": "whether the energy output is for a wind farm or a solar farm",
                "why_confusable": "Both estimate monthly energy output at a location.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["The shared month default is not the selection axis."],
                "target_excerpt": "energy output of a wind farm",
                "rival_excerpt": "energy output of a solar farm",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "The cue names the farm. It does not say either tool rejects a month.",
            },
        },
    },
    "multiple_29": {
        "case_reason": "Both tools locate points of functions given as strings. One finds zero points of one function. The other finds intersections of two functions.",
        "tools": {
            0: {
                "cue": "Unlike functions_intersect, which locates the intersection points of two functions, this finds the zero points of a function.",
                "rival_index": 1,
                "axis": "whether the points are zeros of one function or intersections of two functions",
                "why_confusable": "Both locate points of functions written as strings in x.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["The example string 3x+2 is an input format, not the selection axis."],
                "target_excerpt": "zero points",
                "rival_excerpt": "intersection points",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request that only says to find the points of a function can be read as zeros or as an intersection. The cue names which points.",
            },
            1: {
                "cue": "Unlike functions_zero, which finds the zero points of a function, this locates the intersection points of two functions.",
                "rival_index": 0,
                "axis": "whether the points are intersections of two functions or zeros of one function",
                "why_confusable": "Both locate points of functions written as strings in x.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["Do not treat the second function argument as an exclusion the zero tool stated."],
                "target_excerpt": "intersection points",
                "rival_excerpt": "zero points",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request for where two functions meet does not make the zero-point description true. A vague request about function points can be read as either.",
            },
        },
    },
    "multiple_32": {
        "case_reason": "Both tools take a cone's radius and height. One calculates volume. The other calculates mass.",
        "tools": {
            0: {
                "cue": "Unlike physics_calculate_cone_mass, which calculates the mass of a cone, this calculates the volume of a cone.",
                "rival_index": 1,
                "axis": "whether the cone result is volume or mass",
                "why_confusable": "Both calculate a quantity of a cone from its radius and height.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["Density belongs to the mass tool. It is not a claim that the volume tool rejects a height."],
                "target_excerpt": "volume of a cone",
                "rival_excerpt": "mass of a cone",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request that only gives a cone's radius and height can be read as volume or mass. The cue names the quantity.",
            },
            1: {
                "cue": "Unlike geometry_calculate_cone_volume, which calculates the volume of a cone, this calculates the mass of a cone.",
                "rival_index": 0,
                "axis": "whether the cone result is mass or volume",
                "why_confusable": "Both calculate a quantity of a cone from its radius and height.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["The rounding argument is not the selection axis."],
                "target_excerpt": "mass of a cone",
                "rival_excerpt": "volume of a cone",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "Mass and volume are different quantities. The cue does not say either tool rejects a radius.",
            },
        },
    },
    "multiple_36": {
        "case_reason": "Both tools are kinematics of one object. One calculates acceleration. The other calculates speed for an object that starts from rest.",
        "tools": {
            0: {
                "cue": "Unlike kinematics_calculate_speed_from_rest, which calculates the speed of an object that starts from rest, this calculates the acceleration.",
                "rival_index": 1,
                "axis": "whether the result is acceleration or the speed of an object that starts from rest",
                "why_confusable": "Both answer a motion question about an object over a distance or a time.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["The optional distance on the acceleration tool is not the selection axis."],
                "target_excerpt": "acceleration",
                "rival_excerpt": "speed of an object that starts from rest",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request that only describes an object's motion can be read as either result. The cue names acceleration against speed from rest.",
            },
            1: {
                "cue": "Unlike kinematics_calculate_acceleration, which calculates the acceleration, this calculates the speed of an object that starts from rest.",
                "rival_index": 0,
                "axis": "whether the result is the speed of an object that starts from rest or the acceleration",
                "why_confusable": "Both answer a motion question about an object over a distance or a time.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["Do not turn 'starts from rest' into a claim that the acceleration tool rejects a moving start."],
                "target_excerpt": "speed of an object that starts from rest",
                "rival_excerpt": "acceleration",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "The cue keeps the source's 'starts from rest' qualifier. It does not repair the separate initial-speed parameter.",
            },
        },
    },
    "multiple_38": {
        "case_reason": "Both tools are about a library book. One reserves a book. The other searches for a book.",
        "tools": {
            0: {
                "cue": "Unlike library_search_book, which searches for a book, this reserves a book.",
                "rival_index": 1,
                "axis": "whether a library book is reserved or searched for",
                "why_confusable": "Both concern a book in a library. A request that only says the book can be read as either.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["Availability and genre are arguments of the search, not the contrast with a reservation."],
                "target_excerpt": "Reserves a book",
                "rival_excerpt": "Searches for a book",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "Reserve and search can both be read as true of a request that only names a book. The cue names the action.",
            },
            1: {
                "cue": "Unlike library_reserve_book, which reserves a book, this searches for a book.",
                "rival_index": 0,
                "axis": "whether a library book is searched for or reserved",
                "why_confusable": "Both concern a book in a library.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["The city argument is not a claim that reservation has no branch."],
                "target_excerpt": "Searches for a book",
                "rival_excerpt": "Reserves a book",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request to hold a copy does not make the search description true. A vague library request can be read as either.",
            },
        },
    },
    "multiple_40": {
        "case_reason": "Both tools calculate magnetic field strength. One uses Ampere's Circuital Law. The other uses the Biot-Savart law.",
        "tools": {
            0: {
                "cue": "Unlike electromagnetism_biot_savart_law, which calculates magnetic field strength using the Biot-Savart law, this calculates magnetic field strength using Ampere's Circuital Law.",
                "rival_index": 1,
                "axis": "whether magnetic field strength is calculated with Ampere's Circuital Law or the Biot-Savart law",
                "why_confusable": "Both calculate magnetic field strength from a current and a distance.",
                "why_this_rival": "Only one other tool, and the stated action is the same.",
                "rejected": ["Do not turn the Ampere symmetry sentence into an exclusion of the Biot-Savart tool."],
                "target_excerpt": "Ampere's Circuital Law",
                "rival_excerpt": "Biot-Savart law",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request that only asks for the magnetic field of a current can be read as either law. The cue names the law.",
            },
            1: {
                "cue": "Unlike electromagnetism_ampere_law, which calculates magnetic field strength using Ampere's Circuital Law, this calculates magnetic field strength using the Biot-Savart law.",
                "rival_index": 0,
                "axis": "whether magnetic field strength is calculated with the Biot-Savart law or Ampere's Circuital Law",
                "why_confusable": "Both calculate magnetic field strength from a current and a distance.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["The permeability default is shared machinery, not the selection axis."],
                "target_excerpt": "Biot-Savart law",
                "rival_excerpt": "Ampere's Circuital Law",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "The two laws are alternate calculations, not a class and a subclass. The cue names the law the source names.",
            },
        },
    },
    "multiple_47": {
        "case_reason": "Both tools score the association of two numeric sequences. One calculates cosine similarity. The other calculates a correlation coefficient.",
        "tools": {
            0: {
                "cue": "Unlike correlation_calculate, which calculates the correlation coefficient, this calculates the cosine similarity.",
                "rival_index": 1,
                "axis": "whether the association is cosine similarity or a correlation coefficient",
                "why_confusable": "Both calculate a numeric association between two sequences.",
                "why_this_rival": "Only one other tool, and the action is the same kind of summary.",
                "rejected": ["Pearson versus Spearman is an argument of the correlation tool, not the contrast with cosine similarity."],
                "target_excerpt": "cosine similarity",
                "rival_excerpt": "correlation coefficient",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request to compare two numeric lists can be read as either statistic. Cosine similarity is not a correlation coefficient.",
            },
            1: {
                "cue": "Unlike cosine_similarity_calculate, which calculates the cosine similarity, this calculates the correlation coefficient.",
                "rival_index": 0,
                "axis": "whether the association is a correlation coefficient or cosine similarity",
                "why_confusable": "Both calculate a numeric association between two sequences.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["The shared rounding idea is not the selection axis."],
                "target_excerpt": "correlation coefficient",
                "rival_excerpt": "cosine similarity",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "The cue names the statistic. It does not say either tool rejects a vector.",
            },
        },
    },
    "multiple_48": {
        "case_reason": "Both tools locate a nearby place from a city and preferences. One locates stores. The other locates libraries.",
        "tools": {
            0: {
                "cue": "Unlike library_find_nearby, which locates nearby libraries, this locates nearby stores.",
                "rival_index": 1,
                "axis": "whether the nearby places are stores or libraries",
                "why_confusable": "Both locate nearby places from a city and a preference list.",
                "why_this_rival": "Only one other tool, and the action is the same.",
                "rejected": ["The shared preference examples are not the selection axis."],
                "target_excerpt": "nearby stores",
                "rival_excerpt": "nearby libraries",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request to find a nearby place with those preferences can be read as either. The cue names stores against libraries.",
            },
            1: {
                "cue": "Unlike store_find_nearby, which locates nearby stores, this locates nearby libraries.",
                "rival_index": 0,
                "axis": "whether the nearby places are libraries or stores",
                "why_confusable": "Both locate nearby places from a city and a preference list.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["Do not treat the repeated preference sentence as a second difference."],
                "target_excerpt": "nearby libraries",
                "rival_excerpt": "nearby stores",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request for a library does not make the store description true. A request that only says somewhere nearby can be read as either.",
            },
        },
    },
    "multiple_53": {
        "case_reason": "Both tools predict from independent variables. One applies linear regression. The other applies Random Forest Regression.",
        "tools": {
            0: {
                "cue": "Unlike random_forest_regression, which applies Random Forest Regression, this applies linear regression.",
                "rival_index": 1,
                "axis": "whether the prediction uses linear regression or Random Forest Regression",
                "why_confusable": "Both make a prediction from the same kind of independent and dependent variables.",
                "why_this_rival": "Only one other tool, and the action is a regression prediction.",
                "rejected": ["The tree count belongs to Random Forest Regression. It is not a claim that linear regression lacks a forecast period."],
                "target_excerpt": "linear regression",
                "rival_excerpt": "Random Forest Regression",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "A request that only says to predict from the variables can be read as either method. Linear regression is not Random Forest Regression.",
            },
            1: {
                "cue": "Unlike linear_regression, which applies linear regression, this applies Random Forest Regression.",
                "rival_index": 0,
                "axis": "whether the prediction uses Random Forest Regression or linear regression",
                "why_confusable": "Both make a prediction from the same kind of independent and dependent variables.",
                "why_this_rival": "Only one other tool.",
                "rejected": ["Do not treat one regression method as a subclass the other description already covers."],
                "target_excerpt": "Random Forest Regression",
                "rival_excerpt": "linear regression",
                "both_can_fit": True,
                "cue_still_helps": True,
                "note": "The cue uses the source's own name for the forest method. A request that names one method makes only that description true.",
            },
        },
    },
}

ADDED_UNCUE = {
    "multiple_39": {
        "case_reason": "Ordering groceries and finding a ride share an optional cost ceiling, not an action or a resource.",
        "tools": {
            0: "Orders grocery items from a store. The other tool finds a ride. A delivery price limit is not a ride.",
            1: "Finds a ride from a source to a destination. The other tool orders groceries. A ride cost limit is not a grocery order.",
        },
    },
    "multiple_42": {
        "case_reason": "The final temperature of a gas mixture and the mass of a gas from its molar mass do not answer a similar request.",
        "tools": {
            0: "Calculates the final temperature when two samples of the same gas are mixed. The other tool calculates mass from quantity and molar mass. No shared action is documented.",
            1: "Calculates the mass of a gas from its quantity and molar mass. The other tool calculates a mixture temperature. No selection cue is written.",
        },
    },
    "multiple_52": {
        "case_reason": "A general unit conversion can be read as covering a currency conversion, so a cue would repeat the polynomial failure: both descriptions can be true of one currency request, and the contrast would read as an exclusion the sources do not state.",
        "tools": {
            0: "Converts a value from one unit to another. Currency is a unit of value, so naming the currency tool as a rival would claim an exclusion the unit description does not state.",
            1: "Converts a value from one currency to another. The other description already says it converts a unit. No cue is written.",
        },
    },
}
