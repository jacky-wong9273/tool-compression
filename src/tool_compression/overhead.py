"""Per-condition preprocessing time for P, I, and C.

Week 1 recorded one combined characterization time. This exercise times the
three local conditions on the same catalogues, with the same counter and
config. It does not call a model. It is not request latency.
"""

from __future__ import annotations

import statistics
import time
from platform import python_version

from tool_compression.compress import compress
from tool_compression.config import DEFAULT_CONFIG, Config


def synthetic_catalogues(*, n: int, tools: int, seed: int = 1) -> list[list[dict]]:
    """Catalogues whose protected first span already exceeds the nominal cap.

    Later spans are optional and carry no protection cue. The contrast term
    still scores them. The builder is deterministic.
    """
    catalogues = []
    for index in range(n):
        catalogue = []
        for tool_index in range(tools):
            shared = _shared_words(seed, index)
            catalogue.append(_tool(seed, index, tool_index, shared))
        catalogues.append(catalogue)
    return catalogues


def measure_preprocessing(
    catalogues: list[list[dict]],
    counter,
    *,
    repeats: int = 5,
    config: Config = DEFAULT_CONFIG,
) -> dict:
    if repeats < 1:
        raise ValueError("repeats")
    if not catalogues:
        raise ValueError("catalogues")
    methods = ("P", "I", "C")
    for method in methods:
        for catalogue in catalogues:
            compress(catalogue, method, config, counter)
    samples = {method: [] for method in methods}
    last = {}
    for repeat in range(repeats):
        order = methods[repeat % 3 :] + methods[: repeat % 3]
        produced = {}
        for method in order:
            started = time.perf_counter()
            produced[method] = [
                compress(catalogue, method, config, counter)["catalogue"] for catalogue in catalogues
            ]
            samples[method].append(time.perf_counter() - started)
        last = produced
    identical_c_i = sum(left == right for left, right in zip(last["C"], last["I"]))
    identical_p_i = sum(left == right for left, right in zip(last["P"], last["I"]))
    medians = {method: statistics.median(samples[method]) for method in methods}
    return {
        "model_called": False,
        "counter": getattr(counter, "name", type(counter).__name__),
        "repeats": repeats,
        "catalogues": len(catalogues),
        "tools_per_catalogue": len(catalogues[0]),
        "warmup_passes": 1,
        "order_rotated": True,
        "seconds": {
            method: {
                "median": medians[method],
                "minimum": min(samples[method]),
                "maximum": max(samples[method]),
            }
            for method in methods
        },
        "median_C_minus_I_seconds": medians["C"] - medians["I"],
        "median_C_over_I": None if medians["I"] == 0 else medians["C"] / medians["I"],
        "catalogues_with_identical_C_and_I": identical_c_i,
        "catalogues_with_identical_P_and_I": identical_p_i,
        "selections_coincide_on_this_corpus": identical_c_i == len(catalogues) and identical_p_i == len(catalogues),
        "python": python_version(),
    }


def exercise_record(counter, *, multi_tools: int = 3, single_tools: int = 1, n: int = 48, repeats: int = 5) -> dict:
    multi = measure_preprocessing(
        synthetic_catalogues(n=n, tools=multi_tools),
        counter,
        repeats=repeats,
    )
    single = measure_preprocessing(
        synthetic_catalogues(n=n, tools=single_tools, seed=2),
        counter,
        repeats=repeats,
    )
    return {
        "kind": "cpu_only_per_condition_timing",
        "week1_combined_pic_preprocessing_seconds": 2.287,
        "week1_combined_time_separates_C_from_I": False,
        "arm_e_preprocessing_seconds": 0.506,
        "request_latency_recorded_on_the_flight": False,
        "model_called": False,
        "corpus": (
            "Synthetic catalogues with a long protected first span and a later "
            "optional span. This is not the BFCL catalogue and does not reopen "
            "the finding that the tested BFCL selections coincide."
        ),
        "multi_tool": multi,
        "single_tool": single,
    }


def _tool(seed: int, index: int, tool_index: int, shared: str) -> dict:
    name = f"parcel_tool_{seed}_{tool_index}"
    first = (
        f"Route a parcel along the shared hub corridor toward the regional depot "
        f"with the standard handling note {shared}."
    )
    later = "Supplemental catalogue note about the parcel route."
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f"{first} {later}",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {
                        "type": "string",
                        "description": f"{first} {later}",
                    }
                },
                "required": ["value"],
            },
        },
    }


def _shared_words(seed: int, index: int) -> str:
    pool = ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot")
    return " ".join(pool[(seed + index + offset) % len(pool)] for offset in range(3))
