"""DeepSeek flash rate card retrieved on 2026-11-25.

Prices are USD per 1,000,000 tokens. Peak is double off-peak. Peak hours are
01:00–04:00 and 06:00–10:00 UTC, Monday through Friday. Chinese public holidays
are off-peak for the whole Asia/Shanghai calendar day. The holiday dates are
the 放假 ranges in 国办发明电〔2025〕7号 (State Council, 4 November 2025):
https://www.gov.cn/zhengce/zhengceku/202511/content_7047091.htm

Makeup weekend workdays named in that notice are not added to the peak week.
The rate card keys peak to Monday–Friday, and weekends stay off-peak.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from tool_compression.clean_start.pin import RATE_CARD_ID, RATE_CARD_RETRIEVED, RATE_CARD_URL

OFF_PEAK_PER_MILLION = {
    "cache_hit": Decimal("0.003"),
    "cache_miss": Decimal("0.15"),
    "output": Decimal("0.6"),
}
PEAK_PER_MILLION = {key: value * 2 for key, value in OFF_PEAK_PER_MILLION.items()}
QUANTUM = Decimal("0.000000000001")
SHANGHAI = ZoneInfo("Asia/Shanghai")

# Inclusive 放假 dates from the 2026 notice. Not makeup workdays.
_HOLIDAY_RANGES = (
    (date(2026, 1, 1), date(2026, 1, 3)),
    (date(2026, 2, 15), date(2026, 2, 23)),
    (date(2026, 4, 4), date(2026, 4, 6)),
    (date(2026, 5, 1), date(2026, 5, 5)),
    (date(2026, 6, 19), date(2026, 6, 21)),
    (date(2026, 9, 25), date(2026, 9, 27)),
    (date(2026, 10, 1), date(2026, 10, 7)),
)


def chinese_public_holidays_2026() -> frozenset[date]:
    found: set[date] = set()
    for start, stop in _HOLIDAY_RANGES:
        day = start
        while day <= stop:
            found.add(day)
            day = date.fromordinal(day.toordinal() + 1)
    return frozenset(found)


HOLIDAYS_2026 = chinese_public_holidays_2026()


def rate_card() -> dict:
    return {
        "id": RATE_CARD_ID,
        "retrieved": RATE_CARD_RETRIEVED,
        "url": RATE_CARD_URL,
        "currency": "USD",
        "unit": "per 1_000_000 tokens",
        "model": "deepseek-flash",
        "served_as": "DeepSeek-V4.1-Flash-1017",
        "off_peak": {key: str(value) for key, value in OFF_PEAK_PER_MILLION.items()},
        "peak": {key: str(value) for key, value in PEAK_PER_MILLION.items()},
        "peak_is_double_off_peak": True,
        "peak_utc": ["01:00-04:00", "06:00-10:00"],
        "peak_hkt": ["09:00-12:00", "14:00-18:00"],
        "peak_interval": "half-open [start, end)",
        "peak_days": "Monday-Friday",
        "holiday_calendar": "国务院办公厅 国办发明电〔2025〕7号",
        "holiday_dates": [day.isoformat() for day in sorted(HOLIDAYS_2026)],
        "holiday_timezone": "Asia/Shanghai",
        "reasoning_tokens_billed_inside_output": True,
        "output_not_added_twice": True,
    }


def is_peak(moment: datetime) -> bool:
    """Peak when the UTC clock is inside a peak window on a non-holiday weekday.

    A Chinese public holiday is the Asia/Shanghai calendar date. That whole
    local day is off-peak, including the UTC hours that would otherwise be peak.
    """
    if moment.tzinfo is None:
        raise ValueError("rate-card timestamps must be timezone-aware")
    if moment.astimezone(SHANGHAI).date() in HOLIDAYS_2026:
        return False
    utc = moment.astimezone(timezone.utc)
    if utc.weekday() >= 5:
        return False
    minute = utc.hour * 60 + utc.minute
    return (60 <= minute < 4 * 60) or (6 * 60 <= minute < 10 * 60)


def quantize_usd(amount: Decimal) -> Decimal:
    return amount.quantize(QUANTUM, rounding=ROUND_HALF_UP)


def spend_usd(*, cache_hit: int, cache_miss: int, output: int, at: datetime) -> tuple[Decimal, str]:
    prices = PEAK_PER_MILLION if is_peak(at) else OFF_PEAK_PER_MILLION
    band = "peak" if prices is PEAK_PER_MILLION else "off_peak"
    raw = (
        Decimal(cache_hit) * prices["cache_hit"]
        + Decimal(cache_miss) * prices["cache_miss"]
        + Decimal(output) * prices["output"]
    ) / Decimal(1_000_000)
    return quantize_usd(raw), band
