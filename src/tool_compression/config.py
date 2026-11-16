"""Provisional Week 1 controls. These values are not tuned."""

from dataclasses import dataclass

SPEC_VERSION = "week1.0"

# Nominal retained cap r = 3/4. This is an upper cap, not an exact fraction.
RETENTION_NUMERATOR = 3
RETENTION_DENOMINATOR = 4

# Natural neighbours: Jaccard >= 1/5, at most two, catalogue-order ties.
JACCARD_NUMERATOR = 1
JACCARD_DENOMINATOR = 5
MAX_NEIGHBOURS = 2

# Contrast weight on neighbour rarity. At 1/2 this is the locked lambda.
LAMBDA_NUMERATOR = 1
LAMBDA_DENOMINATOR = 2

# Local budget tokenizer. Not a provider usage measurement.
LOCAL_TOKENIZER = "o200k_base"
# Recount only. Not used to choose spans.
SENSITIVITY_TOKENIZER = "cl100k_base"

# BFCL generate default at the pinned handler, included in request identity.
# The model id is intentionally unselected.
PLACEHOLDER_MODEL = "UNSELECTED"
BFCL_DEFAULT_TEMPERATURE = 0.001
BFCL_STORE = False

METHODS = ("U", "P", "I", "C")


@dataclass(frozen=True)
class Config:
    spec_version: str = SPEC_VERSION
    retention_numerator: int = RETENTION_NUMERATOR
    retention_denominator: int = RETENTION_DENOMINATOR
    jaccard_numerator: int = JACCARD_NUMERATOR
    jaccard_denominator: int = JACCARD_DENOMINATOR
    max_neighbours: int = MAX_NEIGHBOURS
    lambda_numerator: int = LAMBDA_NUMERATOR
    lambda_denominator: int = LAMBDA_DENOMINATOR
    tokenizer_name: str = LOCAL_TOKENIZER

    def as_dict(self) -> dict:
        return {
            "spec_version": self.spec_version,
            "retention_r": f"{self.retention_numerator}/{self.retention_denominator}",
            "jaccard_min": f"{self.jaccard_numerator}/{self.jaccard_denominator}",
            "max_neighbours": self.max_neighbours,
            "lambda": f"{self.lambda_numerator}/{self.lambda_denominator}",
            "neighbour_tie": "higher Jaccard, then earlier catalogue index",
            "local_budget_tokenizer": self.tokenizer_name,
            "sensitivity_tokenizer_not_used_for_selection": SENSITIVITY_TOKENIZER,
            "placeholder_model": PLACEHOLDER_MODEL,
            "temperature": BFCL_DEFAULT_TEMPERATURE,
            "store": BFCL_STORE,
            "tuned": False,
        }


DEFAULT_CONFIG = Config()
