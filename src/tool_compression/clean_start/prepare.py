"""Build the model-facing U tools the official OpenAI-completions path would send.

Language hints and the Java/JavaScript stringification are official prompt
preparation from the pinned ``bfcl_eval.utils``. They are not editor rewrites.
Editor S and editor X run afterwards, on description text only.
"""

from __future__ import annotations

from copy import deepcopy

from tool_compression.clean_start.categories import is_java, is_javascript
from tool_compression.convert import to_openai_completions_tools

PYTHON_HINT = " Note that the provided function is in Python 3 syntax."
JAVA_HINT = " Note that the provided function is in Java 8 SDK syntax."
JAVASCRIPT_HINT = " Note that the provided function is in JavaScript syntax."

# Pinned bfcl_eval.constants.default_prompts strings. Sent as prompt text.
# They are not tool documentation and are not editor inputs.
AGENTIC_SYSTEM_PROMPT = (
    "For your final answer to the user, you must respond in this format: "
    "{'answer': A short and precise answer to the question, 'context': A brief explanation "
    "of how you arrived at this answer or why it is correct}. If you do not know the answer, "
    "respond with {'answer': 'I do not know', 'context': 'I do not know'}. If you think the "
    "question cannot be properly answered, response with "
    "{'answer': 'I cannot answer this question', 'context': A short reason explaining why "
    "this question cannot be answered}.\n"
)
HOLDOUT_USER_PROMPT = "I have updated some more functions you can choose from. What about now?"


def language_hint(category: str) -> str:
    if is_javascript(category):
        return JAVASCRIPT_HINT
    if is_java(category):
        return JAVA_HINT
    return PYTHON_HINT


def apply_official_language_hint(functions: list[dict], category: str) -> list[dict]:
    """Follow ``_func_doc_language_specific_pre_processing`` at the pinned commit."""
    functions = deepcopy(functions)
    if not functions:
        return functions
    hint = language_hint(category)
    for item in functions:
        if not isinstance(item.get("description"), str):
            raise ValueError(f"{item.get('name')} has no description string")
        item["description"] = item["description"] + hint
        properties = item["parameters"]["properties"]
        if is_java(category):
            for value in properties.values():
                if not isinstance(value.get("description"), str):
                    raise ValueError("Java parameter is missing a description")
                if value["type"] == "any":
                    value["description"] += (
                        " This parameter can be of any type of Java object in string representation."
                    )
                else:
                    value["description"] += (
                        f" This is Java {value['type']} type parameter in string representation."
                    )
                if value["type"] in {"ArrayList", "Array"}:
                    value["description"] += (
                        f" The list elements are of type {value['items']['type']}; "
                        "they are not in string representation."
                    )
                    del value["items"]
                value["type"] = "string"
        elif is_javascript(category):
            for value in properties.values():
                if not isinstance(value.get("description"), str):
                    raise ValueError("JavaScript parameter is missing a description")
                if value["type"] == "any":
                    value["description"] += (
                        " This parameter can be of any type of JavaScript object in string representation."
                    )
                else:
                    value["description"] += (
                        f" This is JavaScript {value['type']} type parameter in string representation."
                    )
                if value["type"] == "array":
                    value["description"] += (
                        f" The list elements are of type {value['items']['type']}; "
                        "they are not in string representation."
                    )
                    del value["items"]
                if value["type"] == "dict" and "properties" in value:
                    value["description"] += (
                        " The dictionary entries have the following schema; "
                        "they are not in string representation. "
                        + __import__("json").dumps(value["properties"])
                    )
                    del value["properties"]
                value["type"] = "string"
    return functions


def model_facing_tools(functions: list[dict], category: str) -> list[dict]:
    """OpenAI tool entries the editors and the sender see.

    The clean-start scope counts one choice tool per entry in this list.
    """
    hinted = apply_official_language_hint(functions, category)
    return to_openai_completions_tools(hinted)


def response_description_pointers(functions: list[dict]) -> list[str]:
    """Description strings under ``response`` that the OpenAI tool walker does not edit."""
    found = []
    for index, function in enumerate(functions):
        response = function.get("response")
        if isinstance(response, dict):
            _walk_descriptions(response, f"/{index}/response", found)
    return found


def _walk_descriptions(node: object, prefix: str, found: list[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            path = f"{prefix}/{key}"
            if key == "description" and isinstance(value, str):
                found.append(path)
            else:
                _walk_descriptions(value, path, found)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _walk_descriptions(value, f"{prefix}/{index}", found)
