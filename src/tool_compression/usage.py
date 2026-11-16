"""Provider-usage accounting hooks. Nothing here contacts a provider.

Missing totals stay missing. The cohort saving is a ratio of means. The 10%
target is fixed. Logical response usage and physical attempt billing are
separate ledgers. A local token estimate cannot set the target.
"""

from dataclasses import dataclass
from fractions import Fraction


TARGET_PROVIDER_INPUT_REDUCTION = Fraction(1, 10)
OBSERVED_ACCURACY_LOSS_LIMIT = Fraction(1, 50)


@dataclass(frozen=True)
class ProviderUsage:
    total_input_tokens: int | None = None
    cached_input_tokens: int | None = None
    output_tokens: int | None = None


@dataclass(frozen=True)
class Attempt:
    status: str
    usage: ProviderUsage


def usage_from_mapping(payload: dict | None) -> ProviderUsage:
    """Read a handler parse dict or a provider usage dict. Absent fields stay absent.

    The pinned ``_parse_query_response_FC`` records ``input_token`` from
    ``prompt_tokens`` and ``output_token`` from ``completion_tokens``. It does
    not read cached tokens. A cached figure is stored only when the payload
    carries one. Total input is the provider total, not total minus cached.
    """
    if payload is None:
        return ProviderUsage()
    if "usage" in payload and isinstance(payload["usage"], dict):
        return usage_from_mapping(payload["usage"])
    if "input_token" in payload or "output_token" in payload:
        total = payload.get("input_token")
        output = payload.get("output_token")
        cached = payload.get("cached_input_tokens")
    else:
        total = payload.get("prompt_tokens", payload.get("total_input_tokens"))
        output = payload.get("completion_tokens", payload.get("output_tokens"))
        details = payload.get("prompt_tokens_details")
        cached = payload.get("cached_input_tokens")
        if cached is None and isinstance(details, dict):
            cached = details.get("cached_tokens")
    return ProviderUsage(
        total_input_tokens=_as_token(total),
        cached_input_tokens=_as_token(cached),
        output_tokens=_as_token(output),
    )


class UsageLedger:
    """One row per physical attempt. Logical members point at that row."""

    def __init__(self) -> None:
        self.attempts: list[dict] = []

    def record_attempt(
        self,
        *,
        response_group_id: str,
        case_id: str,
        replicate: int,
        members: tuple[str, ...] | list[str],
        status: str,
        usage: ProviderUsage,
    ) -> None:
        if status not in {"received", "failed", "unknown"}:
            raise ValueError(status)
        self.attempts.append(
            {
                "response_group_id": response_group_id,
                "case_id": case_id,
                "replicate": replicate,
                "members": tuple(members),
                "status": status,
                "usage": usage,
            }
        )

    def physical_attempt_count(self) -> int:
        return len(self.attempts)

    def logical_response_input(self, case_id: str, replicate: int, member: str) -> int | None:
        received = [
            row
            for row in self._rows(case_id, replicate, member)
            if row["status"] == "received"
        ]
        if len(received) != 1:
            return None
        return received[0]["usage"].total_input_tokens

    def physical_billed_input(self, case_id: str, replicate: int, member: str) -> dict:
        rows = self._rows(case_id, replicate, member)
        if not rows or any(row["usage"].total_input_tokens is None for row in rows):
            return {"tokens": None, "coverage": "incomplete", "attempts": len(rows)}
        return {
            "tokens": sum(row["usage"].total_input_tokens for row in rows),
            "coverage": "complete",
            "attempts": len(rows),
        }

    def _rows(self, case_id: str, replicate: int, member: str) -> list[dict]:
        return [
            row
            for row in self.attempts
            if row["case_id"] == case_id and row["replicate"] == replicate and member in row["members"]
        ]


def cohort_provider_saving(baseline: list, variant: list, *, denominator: int) -> dict:
    """(mean baseline - mean variant) / mean baseline on provider total input.

    The target stays 1/10. Missing values are not replaced with zero. An
    incomplete series leaves attainment unresolved.
    """
    target = _target_text()
    if denominator <= 0 or len(baseline) != denominator or len(variant) != denominator:
        return _unresolved("incomplete_cohort", denominator, len(baseline))
    parsed_baseline = [_as_token(value) for value in baseline]
    parsed_variant = [_as_token(value) for value in variant]
    paired = list(zip(parsed_baseline, parsed_variant))
    if any(left is None or right is None for left, right in paired):
        covered = sum(left is not None and right is not None for left, right in paired)
        payload = _unresolved("missing_usage", denominator, len(baseline))
        payload["coverage"] = covered
        return payload
    base = sum(parsed_baseline)
    other = sum(parsed_variant)
    if base == 0:
        return _unresolved("zero_baseline", denominator, len(baseline))
    per_case = [(left - right) / left if left else 0.0 for left, right in paired]
    reached = Fraction(base - other, base) >= TARGET_PROVIDER_INPUT_REDUCTION
    return {
        "attainment": "resolved",
        "reason": "complete_provider_usage",
        "target": target,
        "target_reached": reached,
        "target_lowered": False,
        "ratio_numerator": base - other,
        "ratio_denominator": base,
        "ratio_of_means": (base - other) / base,
        "mean_of_per_case_ratios": sum(per_case) / len(per_case),
        "n": denominator,
        "denominator": denominator,
        "statistical_non_inferiority": "not_tested",
    }


def paired_accuracy_change(correct_baseline: list, correct_variant: list, *, denominator: int) -> dict:
    """Observed paired accuracy change. The 2 percentage-point margin is descriptive."""
    limit = "1/50"
    if denominator <= 0 or len(correct_baseline) != denominator or len(correct_variant) != denominator:
        return {
            "attainment": "unresolved",
            "reason": "incomplete_cohort",
            "within_observed_limit": None,
            "non_inferiority_tested": False,
            "limit": limit,
            "denominator": denominator,
        }
    parsed_baseline = [_as_bool(value) for value in correct_baseline]
    parsed_variant = [_as_bool(value) for value in correct_variant]
    if any(value is None for value in parsed_baseline + parsed_variant):
        return {
            "attainment": "unresolved",
            "reason": "missing_outcome",
            "within_observed_limit": None,
            "non_inferiority_tested": False,
            "limit": limit,
            "denominator": denominator,
        }
    gains = sum(
        1
        for baseline, variant in zip(parsed_baseline, parsed_variant)
        if variant and not baseline
    )
    losses = sum(
        1
        for baseline, variant in zip(parsed_baseline, parsed_variant)
        if baseline and not variant
    )
    delta = sum(parsed_variant) - sum(parsed_baseline)
    return {
        "attainment": "resolved",
        "reason": "supplied_outcomes",
        "gains": gains,
        "losses": losses,
        "delta_numerator": delta,
        "delta_denominator": denominator,
        "within_observed_limit": Fraction(delta, denominator) >= -OBSERVED_ACCURACY_LOSS_LIMIT,
        "limit": limit,
        "non_inferiority_tested": False,
        "denominator": denominator,
    }


def combine_targets(token: dict, accuracy: dict) -> dict:
    """The reference target needs both clauses. Either gap leaves it unresolved."""
    if token.get("attainment") != "resolved" or accuracy.get("attainment") != "resolved":
        return {
            "attainment": "unresolved",
            "target_reached": None,
            "target_lowered": False,
            "reference_comparison": "C-U",
            "statistical_non_inferiority": "not_tested",
        }
    return {
        "attainment": "resolved",
        "target_reached": bool(token.get("target_reached")) and bool(accuracy.get("within_observed_limit")),
        "target_lowered": False,
        "reference_comparison": "C-U",
        "statistical_non_inferiority": "not_tested",
    }


def local_estimate_status(ratio_of_means: float) -> dict:
    """A local ratio is recorded and cannot close the provider target."""
    _ = ratio_of_means
    return {
        "provider_target_reached": None,
        "target": _target_text(),
        "reason": "local_estimate",
        "target_lowered": False,
    }


def _as_token(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("token counts are integers")
    if value < 0:
        raise ValueError("token counts are non-negative")
    return value


def _as_bool(value):
    if value is None:
        return None
    if type(value) is not bool:
        raise TypeError("outcomes are booleans")
    return value


def _target_text() -> str:
    return "1/10"


def _unresolved(reason: str, denominator: int, observed: int) -> dict:
    return {
        "attainment": "unresolved",
        "reason": reason,
        "target": _target_text(),
        "target_reached": None,
        "target_lowered": False,
        "denominator": denominator,
        "n": observed,
    }
