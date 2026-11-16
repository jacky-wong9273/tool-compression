"""Allowlisted description paths for converted OpenAI Chat Completions tools.

The profile is this walker, not a general JSON-schema search. Description
strings under default, example, examples, or enum objects are not slots.
"""

from collections.abc import Iterator


def is_supported_tool(tool: object) -> bool:
    if not isinstance(tool, dict) or tool.get("type") != "function":
        return False
    function = tool.get("function")
    if not isinstance(function, dict) or not isinstance(function.get("name"), str):
        return False
    return isinstance(function.get("parameters"), dict)


def description_slots(tool: dict) -> list[tuple[str, dict, str]]:
    """Return (pointer, container, key) for editable description strings."""
    if not is_supported_tool(tool):
        return []
    function = tool["function"]
    slots: list[tuple[str, dict, str]] = []
    if isinstance(function.get("description"), str):
        slots.append(("/function/description", function, "description"))
    properties = function["parameters"].get("properties")
    if isinstance(properties, dict):
        _walk_properties(properties, "/function/parameters/properties", slots)
    return slots


def iter_description_texts(tool: dict) -> Iterator[tuple[str, str]]:
    for pointer, container, key in description_slots(tool):
        yield pointer, container[key]


def property_names(tool: dict) -> list[str]:
    names: list[str] = []
    if not is_supported_tool(tool):
        return names
    properties = tool["function"]["parameters"].get("properties")
    if isinstance(properties, dict):
        _collect_names(properties, names)
    return names


def all_description_pointers(node: object, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            path = f"{prefix}/{key}"
            if key == "description" and isinstance(value, str):
                found.append(path)
            else:
                found.extend(all_description_pointers(value, path))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(all_description_pointers(value, f"{prefix}/{index}"))
    return found


def unlisted_description_pointers(tool: dict) -> list[str]:
    allowed = {pointer for pointer, _, _ in description_slots(tool)}
    return [pointer for pointer in all_description_pointers(tool) if pointer not in allowed]


def _walk_properties(properties: dict, prefix: str, slots: list[tuple[str, dict, str]]) -> None:
    for name, schema in properties.items():
        if not isinstance(schema, dict):
            continue
        base = f"{prefix}/{name}"
        if isinstance(schema.get("description"), str):
            slots.append((f"{base}/description", schema, "description"))
        nested = schema.get("properties")
        if isinstance(nested, dict):
            _walk_properties(nested, f"{base}/properties", slots)
        items = schema.get("items")
        if isinstance(items, dict):
            _walk_items(items, f"{base}/items", slots, depth=0)


def _walk_items(items: dict, prefix: str, slots: list[tuple[str, dict, str]], depth: int) -> None:
    if isinstance(items.get("description"), str):
        slots.append((f"{prefix}/description", items, "description"))
    nested = items.get("properties")
    if isinstance(nested, dict):
        _walk_properties(nested, f"{prefix}/properties", slots)
    # One extra array level matches the converted BFCL shapes we pin.
    if depth < 1 and isinstance(items.get("items"), dict):
        _walk_items(items["items"], f"{prefix}/items", slots, depth + 1)


def _collect_names(properties: dict, names: list[str]) -> None:
    for name, schema in properties.items():
        names.append(str(name))
        if not isinstance(schema, dict):
            continue
        nested = schema.get("properties")
        if isinstance(nested, dict):
            _collect_names(nested, names)
        items = schema.get("items")
        if isinstance(items, dict) and isinstance(items.get("properties"), dict):
            _collect_names(items["properties"], names)
