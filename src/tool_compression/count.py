"""Local token counters.

Field caps and prepared-request recounts use these counters. Neither counter
is provider-reported usage, and neither establishes the utility target.
"""

from dataclasses import dataclass
import json
from typing import Callable, Protocol


def dump_request(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


class TokenCounter(Protocol):
    name: str

    def count(self, text: str) -> int: ...


@dataclass
class CallableCounter:
    name: str
    fn: Callable[[str], int]

    def count(self, text: str) -> int:
        return self.fn(text)


class TiktokenCounter:
    def __init__(self, encoding_name: str):
        import tiktoken

        self.name = encoding_name
        self.backend = f"tiktoken-{tiktoken.__version__}"
        self._encoding = tiktoken.get_encoding(encoding_name)

    def count(self, text: str) -> int:
        return len(self._encoding.encode(text))


def study_counters() -> tuple[TiktokenCounter, TiktokenCounter]:
    from tool_compression.config import LOCAL_TOKENIZER, SENSITIVITY_TOKENIZER

    return TiktokenCounter(LOCAL_TOKENIZER), TiktokenCounter(SENSITIVITY_TOKENIZER)
