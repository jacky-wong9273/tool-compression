"""Interchangeable catalogue implementations for the reference conditions.

U, P, I, and C call the Week 1 compressor. E is a caller-supplied catalogue
from the pinned external comparator. L is a reporting label and is rejected
here. This module does not add a selector framework or a second compressor.
"""

from copy import deepcopy

from tool_compression.compress import compress
from tool_compression.config import METHODS, Config


class LocalMethod:
    def __init__(self, method: str):
        if method == "L":
            raise ValueError("L is a reporting label, not a compression implementation")
        if method not in METHODS:
            raise ValueError(f"unknown implementation {method}")
        self.name = method

    def apply(self, catalogue: list, config: Config, counter) -> dict:
        return compress(catalogue, self.name, config, counter)


class ExternalSnapshot:
    """A catalogue already produced by E. Applying it does not run TSCG or a model."""

    name = "E"

    def __init__(self, catalogue: list):
        self._catalogue = deepcopy(catalogue)

    def apply(self, catalogue: list, config: Config, counter) -> dict:
        _ = (config, counter)
        return {
            "catalogue": deepcopy(self._catalogue),
            "method": "E",
            "traces": [],
            "unchanged": self._catalogue == catalogue,
        }


def reference_implementations() -> dict[str, LocalMethod]:
    return {name: LocalMethod(name) for name in METHODS}
