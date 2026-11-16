"""Pinned OpenAI Chat Completions conversion for BFCL function catalogues.

This follows ``convert_to_tool`` for ``ModelStyle.OPENAI_COMPLETIONS`` at the
gorilla commit recorded in the evidence packet: dot-to-underscore names, the
Gorilla type map, and the float-description suffix. It does not call an API.
"""

from copy import deepcopy
import re

GORILLA_TO_OPENAPI = {
    "integer": "integer",
    "number": "number",
    "float": "number",
    "string": "string",
    "boolean": "boolean",
    "bool": "boolean",
    "array": "array",
    "list": "array",
    "dict": "object",
    "object": "object",
    "tuple": "array",
    "any": "string",
    "byte": "integer",
    "short": "integer",
    "long": "integer",
    "double": "number",
    "char": "string",
    "ArrayList": "array",
    "Array": "array",
    "HashMap": "object",
    "Hashtable": "object",
    "Queue": "array",
    "Stack": "array",
    "Any": "string",
    "String": "string",
    "Bigint": "integer",
}

FLOAT_SUFFIX = " This is a float type value."


def to_openai_completions_tools(functions: list[dict]) -> list[dict]:
    functions = deepcopy(functions)
    tools = []
    for item in functions:
        if "." in item["name"]:
            item["name"] = re.sub(r"\.", "_", item["name"])
        item["parameters"]["type"] = "object"
        item["parameters"]["properties"] = _cast_properties(item["parameters"]["properties"])
        tools.append({"type": "function", "function": item})
    return tools


def _cast_properties(properties: dict) -> dict:
    for value in properties.values():
        if "type" not in value:
            value["type"] = "string"
        else:
            var_type = value["type"]
            if var_type == "float":
                value["format"] = "float"
                value["description"] += FLOAT_SUFFIX
            if var_type in GORILLA_TO_OPENAPI:
                value["type"] = GORILLA_TO_OPENAPI[var_type]
            else:
                value["type"] = "string"
        if value["type"] in ("array", "object"):
            if "properties" in value:
                value["properties"] = _cast_properties(value["properties"])
            elif "items" in value:
                value["items"]["type"] = GORILLA_TO_OPENAPI[value["items"]["type"]]
                items = value["items"]
                if items["type"] == "array" and "items" in items:
                    items["items"]["type"] = GORILLA_TO_OPENAPI[items["items"]["type"]]
                elif items["type"] == "object" and "properties" in items:
                    items["properties"] = _cast_properties(items["properties"])
    return properties
