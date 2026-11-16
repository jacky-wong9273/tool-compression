"""What the handler float suffix carries after the pinned conversion.

The sentence is handler-generated. This module records the schema facts around
it. It does not decide that the sentence is harmless or necessary, and it does
not add a suffix-control arm.
"""

from copy import deepcopy

from tool_compression.convert import FLOAT_SUFFIX, to_openai_completions_tools
from tool_compression.cues import cue_reasons
from tool_compression.segment import segment_spans

SENTENCE = FLOAT_SUFFIX.strip()


def sentence_facts() -> dict:
    cues = list(cue_reasons(SENTENCE))
    return {
        "cues": cues,
        "matches_protection_cue": bool(cues),
        "mentions_float": "float" in SENTENCE.casefold(),
        "mentions_number": "number" in SENTENCE.casefold(),
        "contains_digit": any(character.isdigit() for character in SENTENCE),
        "harmless": None,
        "necessary": None,
    }


def span_position(prefix: str) -> dict:
    """Locate the suffix sentence without returning the surrounding description."""
    text = prefix + FLOAT_SUFFIX
    spans = segment_spans(text)
    indexes = [
        index
        for index, (start, stop) in enumerate(spans)
        if text[start:stop] == SENTENCE
    ]
    return {
        "span_count": len(spans),
        "sentence_span_indexes": indexes,
        "sentence_is_first_span": indexes == [0],
        "matches_protection_cue": bool(cue_reasons(SENTENCE)),
    }


def inspect_parameter(prop: dict) -> dict:
    """Convert one synthetic property and return schema flags, not description text."""
    try:
        tools = to_openai_completions_tools(
            [
                {
                    "name": "fn",
                    "description": "Function.",
                    "parameters": {"properties": {"v": deepcopy(prop)}},
                }
            ]
        )
    except (KeyError, TypeError) as exc:
        return {"converted": False, "error": type(exc).__name__, "nodes": []}
    converted = tools[0]["function"]["parameters"]["properties"]["v"]
    nodes: list[dict] = []
    _collect(prop, converted, "v", nodes)
    return {"converted": True, "error": None, "nodes": nodes}


def float_suffix_report() -> dict:
    cases = {
        "float_property": {"type": "float", "description": "Length."},
        "double_property": {"type": "double", "description": "Length."},
        "number_property": {"type": "number", "description": "Length."},
        "integer_property": {"type": "integer", "description": "Length."},
        "float_empty_description": {"type": "float", "description": ""},
        "array_item_float": {
            "type": "array",
            "description": "Rows.",
            "items": {"type": "float", "description": "Item."},
        },
        "array_of_array_float": {
            "type": "array",
            "description": "Rows.",
            "items": {"type": "array", "items": {"type": "float", "description": "Deep."}},
        },
        "array_object_float": {
            "type": "array",
            "description": "Rows.",
            "items": {
                "type": "dict",
                "properties": {"inner": {"type": "float", "description": "Inner."}},
            },
        },
    }
    return {
        "handler": "OpenAICompletionsHandler._query_FC",
        "conversion": "convert_to_tool GORILLA_TO_OPENAPI OPENAI_COMPLETIONS",
        "suffix": FLOAT_SUFFIX,
        "sentence": sentence_facts(),
        "later_span_after_authored_sentence": span_position("Length."),
        "suffix_only_field": span_position(""),
        "cases": {name: inspect_parameter(prop) for name, prop in cases.items()},
        "missing_description": inspect_parameter({"type": "float"}),
        "harmless": None,
        "necessary": None,
        "suffix_control_arm": False,
        "conclusion": "unresolved",
        "implementation_correction": False,
    }


def _collect(before: dict, after: dict, path: str, nodes: list[dict]) -> None:
    if not isinstance(before, dict) or not isinstance(after, dict):
        return
    if "type" in before or "type" in after:
        nodes.append(
            {
                "path": path,
                "original_type": before.get("type"),
                "converted_type": after.get("type"),
                "format": after.get("format"),
                "suffix_appended": _suffix_appended(before, after),
                "type_encodes_float": after.get("type") == "float",
                "format_encodes_float": after.get("format") == "float",
            }
        )
    before_properties = before.get("properties")
    after_properties = after.get("properties")
    if isinstance(before_properties, dict) and isinstance(after_properties, dict):
        for name, schema in before_properties.items():
            if isinstance(schema, dict) and isinstance(after_properties.get(name), dict):
                _collect(schema, after_properties[name], f"{path}/properties/{name}", nodes)
    if isinstance(before.get("items"), dict) and isinstance(after.get("items"), dict):
        _collect(before["items"], after["items"], f"{path}/items", nodes)


def _suffix_appended(before: dict, after: dict) -> bool:
    before_text = before.get("description")
    after_text = after.get("description")
    if not isinstance(before_text, str) or not isinstance(after_text, str):
        return False
    return after_text == before_text + FLOAT_SUFFIX
