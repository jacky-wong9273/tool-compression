"""Frozen exploratory settings on the official P/I/C compressor.

H50 is r=0.50 and H25 is r=0.25, both at lambda 1/2. Setting A is the same
r=0.50, lambda 1/2 compressor, planned as a full 840-case flight. Setting B
is r=0.75 at lambda 1/4. Jaccard stays at least 1/5, and the neighbour cap
stays at two. The official r=0.75, lambda 1/2 configuration is not an
exploratory setting and is not retuned. This module does not call a provider.
"""

from decimal import Decimal
import sys

from tool_compression.config import (
    DEFAULT_CONFIG,
    JACCARD_DENOMINATOR,
    JACCARD_NUMERATOR,
    LAMBDA_DENOMINATOR,
    LAMBDA_NUMERATOR,
    LOCAL_TOKENIZER,
    MAX_NEIGHBOURS,
    Config,
)
from tool_compression.usage import usage_from_mapping

BASE_COMMIT = "8619d2fd58dee5babc511970a8d88fb975037149"
H50_LABEL = "H50"
H25_LABEL = "H25"
A_LABEL = "A"
B_LABEL = "B"
EXPLORATORY_LABELS = (H50_LABEL, H25_LABEL)
FULL_CATALOGUE_LABELS = (A_LABEL, B_LABEL)
H50_SPEC_VERSION = "exploratory.h50.2026-11-20"
H25_SPEC_VERSION = "exploratory.h25.2026-11-20"
A_SPEC_VERSION = "exploratory.a.r50.lambda12.2026-11-23"
B_SPEC_VERSION = "exploratory.b.r75.lambda14.2026-11-23"
FULL_CATALOGUE_BASE_COMMIT = "33f29512170f065faad08415f0e48dcbadac09d1"
FULL_CATALOGUE_PURPOSE = "exploratory-full-catalogue"
GENERATION_MODEL = "deepseek-flash"
GENERATION_MODEL_VERSION = "DeepSeek-V4.1-Flash-1017"
# Pinned BFCL decoder for evaluate-from-saved-outputs. Generation under this
# alias is refused: it selects deepseek-chat, not deepseek-flash.
EVALUATE_DECODER_ALIAS = "DeepSeek-V3.2-Exp-FC"
REFUSED_GENERATION_ALIASES = frozenset(
    {
        "DeepSeek-V3.2-Exp-FC",
        "DeepSeek-V3.2-Exp",
        "DeepSeek-V3.2-Exp-thinking",
        "deepseek-chat",
        "deepseek-reasoner",
    }
)
NOT_REFLOWN = ("U", "E", "L")
ARM_NAMES = ("P", "I", "C")
CLOSED_OFFICIAL_RESULT = {
    "label": "L",
    "retention_r": "3/4",
    "lambda": "1/2",
    "thinking": "disabled",
    "model": GENERATION_MODEL,
    "model_version": GENERATION_MODEL_VERSION,
    "primary_accuracy": {"U": "186/200", "L": "185/200", "E": "186/200"},
    "S_LU": "1398/121018",
    "S_LU_approximation": "1.155%",
    "primary_U_provider_prompt_tokens": 121018,
    "target_provider_input_reduction": "1/10",
    "target_lowered": False,
    "retuned_by_this_package": False,
}


class ExploratoryFlightRefused(RuntimeError):
    """The exploratory flight must not start."""


def _setting_spec(label: str) -> tuple[str, tuple[int, int], tuple[int, int]]:
    """Spec version, retention, and lambda for one frozen exploratory label."""
    table = {
        H50_LABEL: (H50_SPEC_VERSION, (1, 2), (LAMBDA_NUMERATOR, LAMBDA_DENOMINATOR)),
        H25_LABEL: (H25_SPEC_VERSION, (1, 4), (LAMBDA_NUMERATOR, LAMBDA_DENOMINATOR)),
        A_LABEL: (A_SPEC_VERSION, (1, 2), (LAMBDA_NUMERATOR, LAMBDA_DENOMINATOR)),
        B_LABEL: (B_SPEC_VERSION, (3, 4), (1, 4)),
    }
    try:
        return table[label]
    except KeyError:
        raise ValueError(f"unknown exploratory setting {label}") from None


def frozen_config(label: str) -> Config:
    """The versioned config for one frozen exploratory label."""
    spec, retention, lam = _setting_spec(label)
    config = Config(
        spec_version=spec,
        retention_numerator=retention[0],
        retention_denominator=retention[1],
        lambda_numerator=lam[0],
        lambda_denominator=lam[1],
    )
    assert_frozen(label, config)
    return config


def assert_frozen(label: str, config: Config) -> None:
    """Refuse a retune of the frozen lambda, neighbours, Jaccard, or tokenizer.

    H50, H25, and A keep lambda at 1/2. Official r=0.75 with lambda 1/2 is
    not an exploratory setting. B is the one frozen lambda 1/4 setting, and
    only at the official retention cap. No other lambda is accepted.
    """
    spec, retention, lam = _setting_spec(label)
    if config.spec_version != spec:
        raise ValueError("exploratory spec_version is not the frozen value")
    if label != B_LABEL and (config.retention_numerator, config.retention_denominator) == (3, 4):
        raise ValueError("official r=0.75 is not an exploratory setting")
    if (
        label == B_LABEL
        and (config.retention_numerator, config.retention_denominator) == (3, 4)
        and (config.lambda_numerator, config.lambda_denominator) == (LAMBDA_NUMERATOR, LAMBDA_DENOMINATOR)
    ):
        raise ValueError("official r=0.75 with lambda 1/2 is not setting B")
    if (config.retention_numerator, config.retention_denominator) != retention:
        raise ValueError("exploratory retention is not the frozen cap")
    if (config.lambda_numerator, config.lambda_denominator) != lam:
        if label == B_LABEL:
            raise ValueError("setting B keeps lambda at 1/4")
        raise ValueError("lambda stays 1/2")
    if (config.jaccard_numerator, config.jaccard_denominator) != (JACCARD_NUMERATOR, JACCARD_DENOMINATOR):
        raise ValueError("Jaccard stays at least 1/5")
    if config.max_neighbours != MAX_NEIGHBOURS:
        raise ValueError("the neighbour cap stays at two")
    if config.tokenizer_name != LOCAL_TOKENIZER:
        raise ValueError("the local tokenizer stays o200k_base")
    if DEFAULT_CONFIG.retention_numerator != 3 or DEFAULT_CONFIG.retention_denominator != 4:
        raise ValueError("the official r=0.75 config was changed")
    if (DEFAULT_CONFIG.lambda_numerator, DEFAULT_CONFIG.lambda_denominator) != (
        LAMBDA_NUMERATOR,
        LAMBDA_DENOMINATOR,
    ):
        raise ValueError("the official lambda 1/2 config was changed")


def classify_case(hashes: dict, official_hashes: dict | None) -> dict:
    """Identity of one prepared case against U and official L at r=0.75."""
    for name in ("U", *ARM_NAMES):
        if name not in hashes:
            raise ValueError("case hashes are incomplete")
    coincide = hashes["P"] == hashes["I"] == hashes["C"]
    official_l = None
    official_u = None
    official_coincide = None
    if official_hashes and all(name in official_hashes for name in ("U", *ARM_NAMES)):
        official_u = official_hashes["U"]
        official_coincide = official_hashes["P"] == official_hashes["I"] == official_hashes["C"]
        if official_coincide:
            official_l = official_hashes["P"]
    identical_to_u = all(hashes[name] == hashes["U"] for name in ARM_NAMES)
    identical_to_official_l = official_l is not None and all(hashes[name] == official_l for name in ARM_NAMES)
    new_arms = []
    for name in ARM_NAMES:
        if hashes[name] == hashes["U"]:
            continue
        if official_l is None or hashes[name] == official_l:
            continue
        new_arms.append(name)
    return {
        "p_i_c_coincide": coincide,
        "identical_to_u": identical_to_u,
        "identical_to_official_l": identical_to_official_l,
        "official_l_hash": official_l,
        "official_u_hash": official_u,
        "u_matches_official_u": official_u is not None and hashes["U"] == official_u,
        "official_p_i_c_coincide": official_coincide,
        "new_arms": new_arms,
        "new_request": bool(new_arms),
    }


def flight_groups(label: str, hashes: dict, official_l_hash: str | None) -> list[tuple[str, ...]]:
    """Members to send. U, E, and official L are never members."""
    if label not in EXPLORATORY_LABELS:
        raise ValueError(label)
    classified = classify_case(
        hashes,
        None
        if official_l_hash is None
        else {"U": hashes["U"], "P": official_l_hash, "I": official_l_hash, "C": official_l_hash},
    )
    # classify_case treats a supplied official hash as L only when P=I=C on that
    # official trio. The caller passes the already-resolved official L hash.
    if official_l_hash is None or not classified["new_request"]:
        groups: list[tuple[str, ...]] = []
    elif classified["p_i_c_coincide"]:
        groups = [(label,)]
    else:
        order = []
        buckets: dict[str, list[str]] = {}
        for name in classified["new_arms"]:
            digest = hashes[name]
            if digest not in buckets:
                buckets[digest] = []
                order.append(digest)
            buckets[digest].append(name)
        groups = [tuple(buckets[digest]) for digest in order]
    for members in groups:
        assert_flight_members(members)
    return groups


def full_catalogue_groups(label: str, hashes: dict) -> list[tuple[str, ...]]:
    """Every prepared case is sent, including a request identical to official L.

    U, E, and the official L label are never members. When P, I, and C
    coincide, the one request is sent under the setting label.
    """
    if label not in FULL_CATALOGUE_LABELS:
        raise ValueError(label)
    for name in ("U", *ARM_NAMES):
        if name not in hashes:
            raise ValueError("case hashes are incomplete")
    if hashes["P"] == hashes["I"] == hashes["C"]:
        groups = [(label,)]
    else:
        order = []
        buckets: dict[str, list[str]] = {}
        for name in ARM_NAMES:
            digest = hashes[name]
            if digest not in buckets:
                buckets[digest] = []
                order.append(digest)
            buckets[digest].append(name)
        groups = [tuple(buckets[digest]) for digest in order]
    for members in groups:
        assert_flight_members(members)
    return groups


def full_catalogue_plan_decision(
    cases: list[dict],
    *,
    coverage_complete: bool,
    hash_reproduction_matched: bool,
) -> dict:
    """The full catalogue is planned even when every request matches official L."""
    prepared = [case for case in cases if not case.get("preparation_failure")]
    identical_to_u = bool(prepared) and all(case["identical_to_u"] for case in prepared)
    identical_to_official_l = bool(prepared) and all(case["identical_to_official_l"] for case in prepared)
    new_cases = sum(1 for case in prepared if case.get("new_request"))
    identical_l_cases = sum(1 for case in prepared if case.get("identical_to_official_l"))
    if not hash_reproduction_matched:
        reason = "official_r075_hash_reproduction_failed"
        plan_ready = False
    elif not coverage_complete:
        reason = "incomplete_coverage"
        plan_ready = False
    elif not prepared:
        reason = "no_prepared_cases"
        plan_ready = False
    elif identical_to_official_l:
        reason = "complete_requests_identical_to_official_L"
        plan_ready = True
    else:
        reason = "full_catalogue_includes_every_prepared_case"
        plan_ready = True
    return {
        "plan_ready": plan_ready,
        "reason": reason,
        "drops_identical_to_official_l": False,
        "identical_to_u": identical_to_u,
        "identical_to_official_l": identical_to_official_l,
        "cases_with_new_request": new_cases,
        "cases_identical_to_official_l": identical_l_cases,
        "prepared_cases": len(prepared),
        "cases_planned": len(prepared) if plan_ready else 0,
    }


def assert_flight_members(members: tuple[str, ...] | list[str]) -> None:
    if not members:
        raise ExploratoryFlightRefused("empty flight group")
    allowed = set(EXPLORATORY_LABELS) | set(FULL_CATALOGUE_LABELS) | set(ARM_NAMES)
    for name in members:
        if name in NOT_REFLOWN:
            raise ExploratoryFlightRefused("U, E, and official L are not re-flown")
        if name in REFUSED_GENERATION_ALIASES:
            raise ExploratoryFlightRefused("refusing generation under the handler alias " + name)
        if name not in allowed:
            raise ExploratoryFlightRefused("unknown flight member " + str(name))


def setting_flyability(
    cases: list[dict],
    *,
    coverage_complete: bool,
    hash_reproduction_matched: bool,
) -> dict:
    """A setting is flyable only when some complete request differs from U and from official L."""
    prepared = [case for case in cases if not case.get("preparation_failure")]
    identical_to_u = bool(prepared) and all(case["identical_to_u"] for case in prepared)
    identical_to_official_l = bool(prepared) and all(case["identical_to_official_l"] for case in prepared)
    new_cases = sum(1 for case in prepared if case.get("new_request"))
    if not hash_reproduction_matched:
        reason = "official_r075_hash_reproduction_failed"
        flyable = False
    elif not coverage_complete:
        reason = "incomplete_coverage"
        flyable = False
    elif identical_to_official_l and identical_to_u:
        reason = "complete_requests_identical_to_official_L_and_U"
        flyable = False
    elif identical_to_official_l:
        reason = "complete_requests_identical_to_official_L"
        flyable = False
    elif identical_to_u:
        reason = "complete_requests_identical_to_U"
        flyable = False
    elif new_cases == 0:
        reason = "no_request_different_from_U_and_official_L"
        flyable = False
    else:
        reason = "complete_requests_differ_from_U_and_official_L"
        flyable = True
    return {
        "flyable": flyable,
        "reason": reason,
        "identical_to_u": identical_to_u,
        "identical_to_official_l": identical_to_official_l,
        "cases_with_new_request": new_cases,
        "prepared_cases": len(prepared),
    }


def accept_ceiling(value) -> Decimal:
    """The operator supplies the ceiling. There is no default and no raise."""
    if value is None or isinstance(value, bool):
        raise ExploratoryFlightRefused("a financial ceiling is required at run time")
    if isinstance(value, float):
        raise ExploratoryFlightRefused("ceiling must be an exact decimal, not a binary float")
    text = value if isinstance(value, str) else str(value)
    if isinstance(value, Decimal):
        amount = value
    else:
        stripped = text.strip()
        if stripped == "" or stripped.lower() in {"none", "null"}:
            raise ExploratoryFlightRefused("a financial ceiling is required at run time")
        try:
            amount = Decimal(stripped)
        except Exception as exc:
            raise ExploratoryFlightRefused("ceiling is not a decimal amount") from exc
    if not amount.is_finite() or amount <= 0:
        raise ExploratoryFlightRefused("ceiling must be a positive amount")
    return amount


def assert_ceiling_not_raised(supplied: Decimal, recorded: Decimal) -> None:
    if recorded != supplied or recorded > supplied:
        raise ExploratoryFlightRefused("refusing a ceiling that was raised or replaced")


def refuse_generation_alias(name: str) -> None:
    if name in REFUSED_GENERATION_ALIASES:
        raise ExploratoryFlightRefused("refusing generation under the handler alias " + name)


def assert_generation_body(body: dict) -> None:
    model = body.get("model")
    refuse_generation_alias(str(model))
    if model != GENERATION_MODEL:
        raise ExploratoryFlightRefused("generation model must be deepseek-flash")
    if body.get("thinking") != {"type": "disabled"}:
        raise ExploratoryFlightRefused("thinking must be disabled")
    if "reasoning_effort" in body:
        raise ExploratoryFlightRefused("refusing reasoning_effort")


def billed_basis_t(payload: dict) -> dict:
    """Provider total input. Cache hits are not subtracted and prices are not applied."""
    usage = usage_from_mapping(payload)
    return {
        "T": usage.total_input_tokens,
        "basis": "provider_prompt_tokens",
        "price_weighted": False,
        "cache_subtracted": False,
    }


def official_evaluate_argv(result_dir, score_dir) -> list[str]:
    """Pinned ``bfcl evaluate`` on saved outputs. This is not ``bfcl generate``."""
    argv = [
        sys.executable,
        "-m",
        "bfcl_eval",
        "evaluate",
        "--model",
        EVALUATE_DECODER_ALIAS,
        "--test-category",
        "multiple,simple_python,irrelevance",
        "--result-dir",
        str(result_dir),
        "--score-dir",
        str(score_dir),
    ]
    assert_evaluate_command(argv)
    return argv


def assert_evaluate_command(argv: list[str]) -> None:
    if "generate" in argv or "openfunctions_evaluation" in argv:
        raise ExploratoryFlightRefused("refusing generation; scoring reads saved outputs")
    if "evaluate" not in argv:
        raise ExploratoryFlightRefused("scoring command is bfcl evaluate")
