"""Assemble the native request the OpenAI completions handler would send.

The model id stays ``UNSELECTED``. Messages are copied and are not shown to
the compressor. Token totals here are local serializations of that object.
"""

from copy import deepcopy
import hashlib

from tool_compression.config import BFCL_DEFAULT_TEMPERATURE, BFCL_STORE, PLACEHOLDER_MODEL
from tool_compression.count import dump_request
from tool_compression.convert import to_openai_completions_tools


def convert_record(record: dict) -> list[dict]:
    return to_openai_completions_tools(record["function"])


def assemble_request(messages: list, catalogue: list, model: str = PLACEHOLDER_MODEL) -> dict:
    request = {
        "messages": deepcopy(messages),
        "model": model,
        "temperature": BFCL_DEFAULT_TEMPERATURE,
        "store": BFCL_STORE,
    }
    if catalogue:
        request["tools"] = deepcopy(catalogue)
    return request


def request_hash(request: dict) -> str:
    return hashlib.sha256(dump_request(request).encode("utf-8")).hexdigest()


def cohort_ratio(baseline: list[int], variant: list[int]) -> dict:
    """(mean baseline - mean variant) / mean baseline, the proposal's S form.

    This is not the mean of per-case ratios. Missing values are not accepted.
    """
    if len(baseline) != len(variant) or not baseline:
        raise ValueError("cohort ratio needs paired non-empty counts")
    base = sum(baseline)
    other = sum(variant)
    per_case = [0.0 if left == 0 else (left - right) / left for left, right in zip(baseline, variant)]
    return {
        "n": len(baseline),
        "sum_baseline": base,
        "sum_variant": other,
        "ratio_of_means": None if base == 0 else (base - other) / base,
        "mean_of_per_case_ratios": sum(per_case) / len(per_case),
    }
