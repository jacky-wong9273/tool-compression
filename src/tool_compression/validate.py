"""Type- and order-sensitive comparison outside allowlisted description strings."""

from tool_compression.adapter import description_slots


def catalogue_violations(before: list, after: list) -> list[str]:
    if type(before) is not type(after):
        return ["/type"]
    if len(before) != len(after):
        return ["/len"]
    violations: list[str] = []
    for index, (left, right) in enumerate(zip(before, after)):
        allowed = {f"/{index}{pointer}" for pointer, _, _ in description_slots(left)}
        violations.extend(_compare(left, right, f"/{index}", allowed))
    return violations


def _compare(left, right, path: str, allowed: set[str]) -> list[str]:
    if type(left) is not type(right):
        return [path or "/"]
    if isinstance(left, dict):
        if list(left) != list(right):
            return [path + "/keys"]
        found: list[str] = []
        for key in left:
            child = f"{path}/{key}"
            if key == "description" and isinstance(left[key], str) and child in allowed:
                continue
            found.extend(_compare(left[key], right[key], child, allowed))
        return found
    if isinstance(left, list):
        if len(left) != len(right):
            return [path + "/len"]
        found = []
        for index, (item, other) in enumerate(zip(left, right)):
            found.extend(_compare(item, other, f"{path}/{index}", allowed))
        return found
    if left != right:
        return [path]
    return []
