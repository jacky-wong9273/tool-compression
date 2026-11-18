"""Locked validation-flight record. No network and no API key.

The default execution record stays empty. This module describes the one
authorized flight: DeepSeek ``deepseek-flash``, thinking disabled, the
off-peak CNY card, and a hard ceiling of ¥50. It does not settle official
accuracy or the 10% provider-input target.
"""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from tool_compression.config import (
    BFCL_DEFAULT_TEMPERATURE,
    BFCL_STORE,
    DEFAULT_CONFIG,
    PLACEHOLDER_MODEL,
)

PURPOSE = "validation-and-prep"
MODEL = "deepseek-flash"
MODEL_VERSION = "DeepSeek-V4.1-Flash-1017"
API_BASE_URL = "https://api.deepseek.com"
API_PATH = "/chat/completions"
API_KEY_ENV = "DEEPSEEK_API_KEY"
THINKING_DISABLED = {"type": "disabled"}
CEILING_CNY = Decimal("50")
RATE_HIT = Decimal("0.02")
RATE_MISS = Decimal("1")
RATE_OUTPUT = Decimal("4")
MILLION = Decimal(1000000)
# Published Flash limits: 1M context and 384K (393216) maximum output.
MAX_INPUT_TOKENS = 1000000
MAX_OUTPUT_TOKENS = 393216
SHANGHAI = ZoneInfo("Asia/Shanghai")
PEAK_WINDOWS = (("09:00", "12:00"), ("14:00", "18:00"))
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
DENOMINATORS = {"multiple": 200, "simple_python": 400, "irrelevance": 240}
SECRET_FIELDS = ("api_key", "token", "secret", "authorization", "deepseek_api_key")


def spend_cny(total_input: int, cache_hit: int, output: int) -> Decimal:
    """Off-peak CNY for one billed attempt. Cache hit is not part of a second total."""
    if total_input < 0 or cache_hit < 0 or output < 0:
        raise ValueError("token counts are non-negative")
    if cache_hit > total_input:
        raise ValueError("cache hit exceeds total input")
    miss = total_input - cache_hit
    return (Decimal(cache_hit) * RATE_HIT + Decimal(miss) * RATE_MISS + Decimal(output) * RATE_OUTPUT) / MILLION


def pre_call_reserve_cny() -> Decimal:
    """Worst-case one-call bill at the locked miss and output rates.

    A later call is refused when spend plus this reserve would pass ¥50.
    The reserve is not a rate-card change.
    """
    return spend_cny(MAX_INPUT_TOKENS, 0, MAX_OUTPUT_TOKENS)


def format_cny(amount: Decimal) -> str:
    return format(amount, "f")


def remaining_allows_call(spent: Decimal, ceiling: Decimal, reserve: Decimal) -> bool:
    """True only when a new call cannot be shown to risk passing the ceiling."""
    if reserve <= 0 or ceiling <= 0 or spent < 0:
        return False
    if spent >= ceiling:
        return False
    return spent + reserve <= ceiling


def is_peak(moment: datetime) -> bool:
    """Weekday 09:00–12:00 and 14:00–18:00 in Asia/Shanghai, half-open intervals.

    Weekends are off-peak. A holiday calendar is not applied: a weekday
    holiday inside these windows is still treated as peak, so the run stops.
    """
    if moment.tzinfo is None:
        raise ValueError("peak check requires a timezone-aware clock")
    local = moment.astimezone(SHANGHAI)
    if local.weekday() > 4:
        return False
    seconds = local.hour * 3600 + local.minute * 60 + local.second + local.microsecond / 1000000
    windows = ((9 * 3600, 12 * 3600), (14 * 3600, 18 * 3600))
    return any(start <= seconds < stop for start, stop in windows)


def analysis_configuration() -> dict:
    return {
        "compare": ["U", "L", "E"],
        "l_is_reporting_label_only": True,
        "l_is_compressor": False,
        "reference_comparison": "C-U",
        "c_represented_by": "L where P, I, and C requests coincide",
        "representing_c_by_l_tests_contrast": False,
        "target_provider_input_reduction": "1/10",
        "e_versus_u_reported_separately": True,
        "e_versus_u_can_satisfy_reference_target": False,
        "retune": {
            "r": False,
            "lambda": False,
            "protections": False,
            "neighbour_limits": False,
            "target": False,
        },
        "denominators": dict(DENOMINATORS),
        "settings": DEFAULT_CONFIG.as_dict(),
    }


def failure_policy() -> dict:
    return {
        "auth_or_payment": "stop",
        "auth_statuses": [401, 403],
        "payment_statuses": [402],
        "transient_statuses": [429, 500, 502, 503, 504],
        "transient_errors": ["timeout", "connection"],
        "max_retries": 2,
        "backoff_seconds": [1, 2],
        "spend": "hard_stop_before_call_when_remaining_may_be_insufficient",
        "ceiling_cny": "50",
        "do_not_exhaust_ceiling": True,
    }


def peak_hours_policy() -> dict:
    return {
        "timezone": "Asia/Shanghai",
        "weekdays": list(WEEKDAYS),
        "windows": [list(window) for window in PEAK_WINDOWS],
        "do_not_start_or_continue_into_peak": True,
        "holiday_calendar": "not_applied",
        "note": (
            "Do not start or continue a run inside weekday 09:00-12:00 or "
            "14:00-18:00 Asia/Shanghai. Weekends are off peak. PRC public "
            "holidays are off peak on the public price page; this guard still "
            "stops inside the weekday windows."
        ),
    }


def rate_card() -> dict:
    return {
        "schedule": "off-peak",
        "currency": "CNY",
        "unit": "per_million_tokens",
        "cache_hit_per_million": "0.02",
        "cache_miss_per_million": "1",
        "output_per_million": "4",
        "locked": True,
        "note": (
            "Locked off-peak Flash card for this validation flight, in CNY "
            "per million tokens. Do not replace it with a peak card or "
            "another schedule."
        ),
    }


def validation_flight_record() -> dict:
    """Filled record for the validation flight. It is not frozen until freeze."""
    return {
        "purpose": PURPOSE,
        "official_settlement": False,
        "official_accuracy": False,
        "model": MODEL,
        "model_version": MODEL_VERSION,
        "provider_options": {
            "temperature": BFCL_DEFAULT_TEMPERATURE,
            "store": BFCL_STORE,
            "thinking": dict(THINKING_DISABLED),
        },
        "thinking": {
            "type": "disabled",
            "pinned_before_any_call": True,
        },
        "replicate_count": 1,
        "failure_policy": failure_policy(),
        "analysis_configuration": analysis_configuration(),
        "paid_inference_authorized": True,
        "spending_ceiling": {
            "amount": "50",
            "currency": "CNY",
            "hard": True,
            "do_not_lift": True,
        },
        "rate_card": rate_card(),
        "peak_hours_policy": peak_hours_policy(),
        "api_base_url": API_BASE_URL,
        "api_path": API_PATH,
        "api_key_source": API_KEY_ENV,
        "api_key_in_repository": False,
        "pre_call_reserve_cny": format_cny(pre_call_reserve_cny()),
        "pre_call_reserve_assumption": (
            "1_000_000 input tokens at the cache-miss rate plus 393_216 output "
            "tokens at the output rate, from the published context length and "
            "maximum output. A call is not started when spent plus this reserve "
            "would exceed the ceiling."
        ),
        "bfcl_defaults_included": [
            "temperature=0.001",
            "store=false",
            "tools when the catalogue is non-empty",
            "messages from question turn 0",
        ],
        "bfcl_request_deviations": [
            "thinking is {type: disabled} on every request because DeepSeek enables thinking when the field is omitted",
        ],
        "week1_placeholder_model": PLACEHOLDER_MODEL,
        "identity": "recomputed_from_model_messages_catalogue_and_sent_options",
        "implementation_corrections": [],
        "preparation_outputs_regenerated": False,
        "frozen": False,
    }


def flight_record_gaps(record: dict) -> list[str]:
    """Semantic holes. A non-empty list cannot authorize a provider call."""
    if not isinstance(record, dict):
        return ["execution_record"]
    gaps = []
    if record.get("purpose") != PURPOSE:
        gaps.append("purpose")
    if record.get("official_settlement") is not False:
        gaps.append("official_settlement")
    if record.get("official_accuracy") is not False:
        gaps.append("official_accuracy")
    if record.get("model") != MODEL:
        gaps.append("model")
    if record.get("model_version") != MODEL_VERSION:
        gaps.append("model_version")
    if not _provider_options_locked(record.get("provider_options")):
        gaps.append("provider_options")
    if not _thinking_disabled(record):
        gaps.append("thinking_disabled")
    if record.get("replicate_count") != 1:
        gaps.append("replicate_count")
    if not _failure_policy_locked(record.get("failure_policy")):
        gaps.append("failure_policy")
    if not _analysis_locked(record.get("analysis_configuration")):
        gaps.append("analysis_configuration")
    if not _ceiling_locked(record.get("spending_ceiling")):
        gaps.append("spending_ceiling")
    if not _rate_card_locked(record.get("rate_card")):
        gaps.append("rate_card")
    if not _peak_policy_locked(record.get("peak_hours_policy")):
        gaps.append("peak_hours_policy")
    if record.get("api_base_url") != API_BASE_URL:
        gaps.append("api_base_url")
    if record.get("api_path") != API_PATH:
        gaps.append("api_path")
    if record.get("api_key_source") != API_KEY_ENV:
        gaps.append("api_key_source")
    if record.get("api_key_in_repository") is not False:
        gaps.append("api_key_in_repository")
    if not _reserve_locked(record.get("pre_call_reserve_cny")):
        gaps.append("pre_call_reserve_cny")
    if record.get("frozen") is not True:
        gaps.append("frozen")
    if _secret_material(record):
        gaps.append("secret_material")
    return gaps


def _thinking_disabled(record: dict) -> bool:
    pin = record.get("thinking")
    options = record.get("provider_options")
    option_thinking = options.get("thinking") if isinstance(options, dict) else None
    return (
        isinstance(pin, dict)
        and pin.get("type") == "disabled"
        and pin.get("pinned_before_any_call") is True
        and option_thinking == THINKING_DISABLED
    )


def _provider_options_locked(options) -> bool:
    if not isinstance(options, dict):
        return False
    if options.get("temperature") != BFCL_DEFAULT_TEMPERATURE:
        return False
    if options.get("store") is not False:
        return False
    if options.get("thinking") != THINKING_DISABLED:
        return False
    if "reasoning_effort" in options:
        return False
    return True


def _ceiling_locked(value) -> bool:
    if not isinstance(value, dict):
        return False
    if value.get("currency") != "CNY" or value.get("hard") is not True or value.get("do_not_lift") is not True:
        return False
    try:
        amount = Decimal(str(value.get("amount")))
    except Exception:
        return False
    return amount == CEILING_CNY


def _rate_card_locked(value) -> bool:
    if not isinstance(value, dict) or value.get("locked") is not True:
        return False
    if value.get("schedule") != "off-peak" or value.get("currency") != "CNY":
        return False
    try:
        hit = Decimal(str(value.get("cache_hit_per_million")))
        miss = Decimal(str(value.get("cache_miss_per_million")))
        output = Decimal(str(value.get("output_per_million")))
    except Exception:
        return False
    return hit == RATE_HIT and miss == RATE_MISS and output == RATE_OUTPUT


def _reserve_locked(value) -> bool:
    try:
        return Decimal(str(value)) == pre_call_reserve_cny()
    except Exception:
        return False


def _failure_policy_locked(value) -> bool:
    if not isinstance(value, dict):
        return False
    if value.get("auth_or_payment") != "stop":
        return False
    if set(value.get("auth_statuses") or []) != {401, 403}:
        return False
    if set(value.get("payment_statuses") or []) != {402}:
        return False
    transient = set(value.get("transient_statuses") or [])
    if not {429, 500, 502, 503, 504} <= transient:
        return False
    retries = value.get("max_retries")
    backoff = value.get("backoff_seconds")
    if type(retries) is not int or not 1 <= retries <= 3:
        return False
    if not isinstance(backoff, list) or len(backoff) != retries:
        return False
    if any(type(item) is not int or not 0 < item <= 8 for item in backoff):
        return False
    if value.get("ceiling_cny") != "50" or value.get("do_not_exhaust_ceiling") is not True:
        return False
    spend = value.get("spend")
    return isinstance(spend, str) and "hard_stop" in spend


def _analysis_locked(value) -> bool:
    if not isinstance(value, dict):
        return False
    if value.get("compare") != ["U", "L", "E"]:
        return False
    if value.get("l_is_reporting_label_only") is not True or value.get("l_is_compressor") is not False:
        return False
    if value.get("reference_comparison") != "C-U":
        return False
    if value.get("representing_c_by_l_tests_contrast") is not False:
        return False
    if value.get("target_provider_input_reduction") != "1/10":
        return False
    if value.get("e_versus_u_can_satisfy_reference_target") is not False:
        return False
    if value.get("e_versus_u_reported_separately") is not True:
        return False
    retune = value.get("retune")
    if not isinstance(retune, dict):
        return False
    for key in ("r", "lambda", "protections", "neighbour_limits", "target"):
        if retune.get(key) is not False:
            return False
    if value.get("denominators") != DENOMINATORS:
        return False
    settings = value.get("settings")
    if not isinstance(settings, dict):
        return False
    return (
        settings.get("retention_r") == "3/4"
        and settings.get("lambda") == "1/2"
        and settings.get("jaccard_min") == "1/5"
        and settings.get("max_neighbours") == 2
        and settings.get("tuned") is False
        and settings.get("placeholder_model") == PLACEHOLDER_MODEL
        and settings.get("temperature") == BFCL_DEFAULT_TEMPERATURE
        and settings.get("store") is False
    )


def _peak_policy_locked(value) -> bool:
    if not isinstance(value, dict):
        return False
    return (
        value.get("timezone") == "Asia/Shanghai"
        and value.get("weekdays") == list(WEEKDAYS)
        and value.get("windows") == [list(window) for window in PEAK_WINDOWS]
        and value.get("do_not_start_or_continue_into_peak") is True
    )


def _secret_material(record: dict) -> bool:
    for key in SECRET_FIELDS:
        value = record.get(key)
        if value:
            return True
    return False
