"""Billed-basis total input and the separate cache-associated input-cost figure.

``T`` is provider ``prompt_tokens`` / ``total_input_tokens``, including cached
and uncached components. The price-weighted input figure uses the locked
off-peak relative prices (cache hit 0.02, cache miss 1) under the observed
cache mix. It is a different measurement. It is not the study statistic.

The constants match the validation-flight card: ¥0.02 / ¥1 / ¥4 per million
cache-hit, cache-miss, and output tokens. Nothing here contacts a provider.
"""

from __future__ import annotations

from decimal import Decimal

RATE_HIT = Decimal("0.02")
RATE_MISS = Decimal("1")
RATE_OUTPUT = Decimal("4")
MILLION = Decimal("1000000")

STUDY_STATISTIC = (
    "billed-basis provider total input T (prompt_tokens), including cached "
    "and uncached components"
)

PRICE_WEIGHTED_NOTE = (
    "Run-specific input-cost difference under the observed cache mix, "
    "calculated from valid usage records and the locked off-peak relative "
    "prices. This is a different measurement from billed-basis total input. "
    "It does not establish attainment of the token target. This execution "
    "does not isolate compression-caused deployment savings from cache state, "
    "request order, or prefix reuse. It also does not establish a claim about "
    "total cost."
)


def spend_cny(total_input: int, cache_hit: int, output: int) -> Decimal:
    """Off-peak CNY for one billed attempt. Cache hit is inside ``total_input``."""
    if total_input < 0 or cache_hit < 0 or output < 0:
        raise ValueError("token counts are non-negative")
    if cache_hit > total_input:
        raise ValueError("cache hit cannot exceed total input")
    miss = total_input - cache_hit
    amount = Decimal(cache_hit) * RATE_HIT + Decimal(miss) * RATE_MISS + Decimal(output) * RATE_OUTPUT
    return amount / MILLION


def format_cny(amount: Decimal) -> str:
    return format(amount.quantize(Decimal("0.00000001")), "f")


def price_weighted_input(cache_hit: int, cache_miss: int) -> Decimal:
    """Weighted input units. Not currency, and not billed-basis ``T``."""
    if cache_hit < 0 or cache_miss < 0:
        raise ValueError("token counts are non-negative")
    return Decimal(cache_hit) * RATE_HIT + Decimal(cache_miss) * RATE_MISS


def contrast_from_cache_sums(cache_by_arm: dict) -> dict:
    """Contrast cohort ``T`` with the price-weighted input sum.

    ``cache_by_arm`` maps an arm to ``sum_cache_hit``, ``sum_cache_miss``, and
    ``sum_total_input``. Arms ``U`` and ``L`` are required. ``E`` is included
    when present.
    """
    weighted = {}
    totals = {}
    for arm, row in cache_by_arm.items():
        hit = int(row["sum_cache_hit"])
        miss = int(row["sum_cache_miss"])
        total = int(row["sum_total_input"])
        if hit + miss != total:
            raise ValueError(f"{arm} cache hit + miss != total input")
        weighted[arm] = price_weighted_input(hit, miss)
        totals[arm] = total
    token_numerator = totals["U"] - totals["L"]
    token_ratio = token_numerator / totals["U"]
    weighted_numerator = weighted["U"] - weighted["L"]
    weighted_ratio = weighted_numerator / weighted["U"]
    payload = {
        "study_statistic": STUDY_STATISTIC,
        "price_weighted_input_is_study_statistic": False,
        "price_weighted_input_establishes_token_target": False,
        "isolates_compression_caused_deployment_savings": False,
        "establishes_total_cost": False,
        "note": PRICE_WEIGHTED_NOTE,
        "relative_prices": {"cache_hit": "0.02", "cache_miss": "1"},
        "token_sum_U": totals["U"],
        "token_sum_L": totals["L"],
        "token_numerator": token_numerator,
        "token_ratio": token_ratio,
        "price_weighted_sum_U": format(weighted["U"], "f"),
        "price_weighted_sum_L": format(weighted["L"], "f"),
        "price_weighted_ratio": format(weighted_ratio, "f"),
        "price_weighted_ratio_float": float(weighted_ratio),
    }
    if "E" in totals:
        payload["token_sum_E"] = totals["E"]
        payload["price_weighted_sum_E"] = format(weighted["E"], "f")
        payload["token_order"] = _order(totals)
        payload["price_weighted_order"] = _order({arm: float(weighted[arm]) for arm in totals})
    return payload


def contrast_usage_accounting(payload: dict) -> dict:
    """Recompute the contrast from the recorded usage-accounting table."""
    categories = {}
    recorded = payload["price_weighted_contrast_not_the_study_statistic"]
    for category, arms in payload["cache_by_category_arm_logical"].items():
        contrast = contrast_from_cache_sums(arms)
        locked = recorded[category]
        contrast["recorded_price_weighted_ratio"] = locked["price_weighted_S_LU"]
        contrast["recorded_token_ratio"] = locked["token_S_LU"]
        contrast["matches_recorded_token_ratio"] = contrast["token_ratio"] == locked["token_S_LU"]
        contrast["close_to_recorded_price_weighted_ratio"] = abs(
            contrast["price_weighted_ratio_float"] - locked["price_weighted_S_LU"]
        ) < 1e-12
        categories[category] = contrast
    spend = payload["spend_check"]
    recomputed = spend_cny(
        int(spend["stage_b_sum_input"]),
        int(spend["stage_b_sum_cache_hit"]),
        int(spend["stage_b_sum_output"]),
    )
    return {
        "definition": payload["definition"],
        "categories": categories,
        "stage_b_spend_cny": format_cny(recomputed),
        "stage_b_spend_matches_ledger": format_cny(recomputed) == spend["stage_b_recomputed_cny"],
        "cumulative_spend_cny": spend["cumulative_ledger"],
        "distinct_measurements": list(payload["distinct_measurements"]),
        "price_weighted_input_is_study_statistic": False,
        "note": PRICE_WEIGHTED_NOTE,
    }


def locked_usage_issues(payload: dict) -> list[str]:
    issues = []
    contrast = contrast_usage_accounting(payload)
    if contrast["stage_b_spend_cny"] != "1.24290304":
        issues.append("stage B spend does not recompute to the locked ledger")
    if payload["spend_check"]["cumulative_ledger"] != "1.25107640":
        issues.append("cumulative spend was altered")
    if payload["spend_check"]["stage_a_ledger_cny"] != "0.00817336":
        issues.append("stage A spend was altered")
    if payload["prompt_equals_hit_plus_miss"] != 1513 or payload["prompt_ne_hit_plus_miss"] != 0:
        issues.append("cache identity counts were altered")
    primary = contrast["categories"]["multiple"]
    if primary["token_numerator"] != 1398 or primary["token_sum_U"] != 121018:
        issues.append("primary billed-basis saving was altered")
    if not primary["matches_recorded_token_ratio"]:
        issues.append("primary token ratio does not match the recorded table")
    if not primary["close_to_recorded_price_weighted_ratio"]:
        issues.append("primary price-weighted ratio does not match the recorded table")
    for category, block in contrast["categories"].items():
        if not block["matches_recorded_token_ratio"]:
            issues.append(f"{category} token ratio does not match the recorded table")
        if not block["close_to_recorded_price_weighted_ratio"]:
            issues.append(f"{category} price-weighted ratio does not match the recorded table")
    if primary["recorded_price_weighted_ratio"] != 0.1302478611568131:
        issues.append("recorded primary price-weighted ratio was altered")
    if primary["price_weighted_input_is_study_statistic"] is not False:
        issues.append("price-weighted input was marked as the study statistic")
    if primary["price_weighted_input_establishes_token_target"] is not False:
        issues.append("price-weighted input was marked as meeting the token target")
    if primary["establishes_total_cost"] is not False:
        issues.append("price-weighted input was marked as a total-cost result")
    if primary["token_order"] == primary["price_weighted_order"]:
        issues.append("primary token order and price-weighted order were collapsed")
    for category, block in contrast["categories"].items():
        if block["token_ratio"] >= 0.1:
            issues.append(f"{category} billed-basis saving was altered above 10 percent")
    return issues


def _order(values: dict) -> list[str]:
    return sorted(values, key=lambda arm: values[arm], reverse=True)
