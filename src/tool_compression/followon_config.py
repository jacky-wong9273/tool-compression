"""Follow-on T1/T2 settings.

The cap ``max(floor(0.75 × d), p)`` and the T2 weight ``1/2`` are new-trial
settings for this post-result package. They use the same fractions as the
closed ``week1.0`` run and do not retune that run, its hashes, or its target.
"""

from dataclasses import dataclass

FOLLOWON_SPEC_VERSION = "followon.1"
T1_NAME = "T1"
T2_NAME = "T2"
FOLLOWON_CONDITIONS = (T1_NAME, T2_NAME)

# New-trial cap. Not a retune of week1.0 r.
RETENTION_NUMERATOR = 3
RETENTION_DENOMINATOR = 4

# Pinned prior neighbour rule, verified against lexical.select_neighbours.
JACCARD_NUMERATOR = 1
JACCARD_DENOMINATOR = 5
MAX_NEIGHBOURS = 2

# New-trial T2 weight on the pinned prior q. T1 uses zero.
T2_CONTRAST_NUMERATOR = 1
T2_CONTRAST_DENOMINATOR = 2

LOCAL_TOKENIZER = "o200k_base"


@dataclass(frozen=True)
class FollowOnConfig:
    spec_version: str = FOLLOWON_SPEC_VERSION
    condition: str = T1_NAME
    retention_numerator: int = RETENTION_NUMERATOR
    retention_denominator: int = RETENTION_DENOMINATOR
    jaccard_numerator: int = JACCARD_NUMERATOR
    jaccard_denominator: int = JACCARD_DENOMINATOR
    max_neighbours: int = MAX_NEIGHBOURS
    contrast_numerator: int = 0
    contrast_denominator: int = 1
    tokenizer_name: str = LOCAL_TOKENIZER

    def as_dict(self) -> dict:
        return {
            "spec_version": self.spec_version,
            "condition": self.condition,
            "cap": "max(floor(0.75 × d), p)",
            "retention": f"{self.retention_numerator}/{self.retention_denominator}",
            "contrast_weight": f"{self.contrast_numerator}/{self.contrast_denominator}",
            "jaccard_min": f"{self.jaccard_numerator}/{self.jaccard_denominator}",
            "max_neighbours": self.max_neighbours,
            "neighbour_tie": "higher Jaccard, then earlier catalogue index",
            "neighbour_source": "full original uncompressed catalogue of this request",
            "q": "tool_compression.lexical.contrast_q",
            "own_score": "|terms(piece) ∩ terms(own identifiers)| / |terms(piece)|",
            "local_budget_tokenizer": self.tokenizer_name,
            "new_trial_settings": True,
            "retunes_week1": False,
            "retunes_closed_official_run": False,
            "closed_target_is_reset_test": False,
            "tuned_on_labels_or_funnel": False,
        }


T1_CONFIG = FollowOnConfig(condition=T1_NAME, contrast_numerator=0, contrast_denominator=1)
T2_CONFIG = FollowOnConfig(
    condition=T2_NAME,
    contrast_numerator=T2_CONTRAST_NUMERATOR,
    contrast_denominator=T2_CONTRAST_DENOMINATOR,
)
T2_ZERO_CONFIG = FollowOnConfig(condition=T2_NAME, contrast_numerator=0, contrast_denominator=1)


def same_transform(left: FollowOnConfig, right: FollowOnConfig) -> bool:
    """True when two configs share every control except the contrast weight."""
    keys = (
        "spec_version",
        "retention_numerator",
        "retention_denominator",
        "jaccard_numerator",
        "jaccard_denominator",
        "max_neighbours",
        "tokenizer_name",
    )
    return all(getattr(left, key) == getattr(right, key) for key in keys)
