"""Pins for the clean-start study. This is not Evaluation Protocol v1.1."""

from __future__ import annotations

STUDY_ID = "clean-start-usx"
OFFICIAL_SETTLEMENT = False
EXTENDS_OFFICIAL_V1_1 = False

BFCL_REPOSITORY = "https://github.com/ShishirPatil/gorilla"
BFCL_COMMIT = "6ea57973c7a6097fd7c5915698c54c17c5b1b6c8"
BFCL_SUBDIR = "berkeley-function-call-leaderboard"
BFCL_VERSION_PREFIX = "BFCL_v4"

# Request name. The retired alias still routes; it is not the name we send.
REQUEST_MODEL = "deepseek-flash"
SERVED_AS = "DeepSeek-V4.1-Flash-1017"
RETIRED_ROUTE_ALIAS = "deepseek-v4-flash"
API_URL = "https://api.deepseek.com/chat/completions"

ARMS = ("U", "S", "X", "SX")
THINKING_ORDER = ("off", "on")
TEMPERATURE = 0.001
STEP_LIMIT = 20

RATE_CARD_ID = "deepseek-flash-2026-11-25"
RATE_CARD_URL = "https://api-docs.deepseek.com/quick_start/pricing/"
RATE_CARD_RETRIEVED = "2026-11-25"


def study_manifest() -> dict:
    return {
        "study": STUDY_ID,
        "official_settlement": OFFICIAL_SETTLEMENT,
        "extends_official_v1_1": EXTENDS_OFFICIAL_V1_1,
        "official_v1_1": "historical and closed",
        "bfcl_repository": BFCL_REPOSITORY,
        "bfcl_commit": BFCL_COMMIT,
        "bfcl_subdir": BFCL_SUBDIR,
        "request_model": REQUEST_MODEL,
        "served_as": SERVED_AS,
        "retired_route_alias_not_sent": RETIRED_ROUTE_ALIAS,
        "arms": list(ARMS),
        "thinking_order": list(THINKING_ORDER),
        "thinking_default_on_server": True,
        "temperature_sent": TEMPERATURE,
        "temperature_ignored_while_thinking": True,
        "max_tokens_sent": False,
        "rate_card_id": RATE_CARD_ID,
        "rate_card_url": RATE_CARD_URL,
        "rate_card_retrieved": RATE_CARD_RETRIEVED,
        "paid_inference_authorized_by_this_package": False,
        "provider_called_on_import": False,
    }
