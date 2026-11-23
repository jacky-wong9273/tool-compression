"""T1/T2 flight preparation. Planning does not call a provider.

T1 and T2 stay the phrase-level compressor from ``followon.1``. This module
does not retune that compressor and does not implement the official-compressor
robustness settings reserved for a different pull request.

A later operator supplies ``EXPLORATORY_CEILING_CNY`` at run time. There is no
default ceiling. ``--live`` is required before any generation client is built.
Importing this module does not read ``DEEPSEEK_API_KEY`` and does not open a
socket.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
import json
import os

from tool_compression.config import BFCL_DEFAULT_TEMPERATURE, BFCL_STORE
from tool_compression.count import dump_request
from tool_compression.evaluation import DENOMINATORS
from tool_compression.followon_bind import reproduce_historical_official_counts
from tool_compression.followon_config import T1_CONFIG, T2_CONFIG
from tool_compression.load import STUDY_CATEGORIES, VERSION_PREFIX
from tool_compression.official_score import (
    FLIGHT_MODEL,
    FLIGHT_MODEL_VERSION,
    GORILLA_COMMIT,
    SCORING_ALIAS,
    ScoringAliasGenerateRefused,
    build_bfcl_argv,
)
from tool_compression.phrase_compress import compress_conditions
from tool_compression.prepare import convert_record

SOURCE_TIP = "213bba84d008d69edbddf6a20f2555de1c2a374e"
PARENT_TIP = "3a02e64888c5359f48d2b417ac659161cd3eadae"
ARMS = ("T1", "T2")
CATEGORIES = STUDY_CATEGORIES
EXPECTED_CASES = 840
CEILING_ENV = "EXPLORATORY_CEILING_CNY"
ORIGINAL_AUTHORIZATION_CNY = Decimal("50")
REMAINING_AUTHORIZED_CNY = Decimal("48.74670004")
RATE_HIT = Decimal("0.02")
RATE_MISS = Decimal("1")
RATE_OUTPUT = Decimal("4")
MILLION = Decimal(1000000)
MAX_INPUT_TOKENS = 1000000
MAX_OUTPUT_TOKENS = 393216
API_BASE_URL = "https://api.deepseek.com"
API_PATH = "/chat/completions"
API_KEY_ENV = "DEEPSEEK_API_KEY"
THINKING_DISABLED = {"type": "disabled"}
HKT = ZoneInfo("Asia/Hong_Kong")
PEAK_WINDOWS = ((9 * 3600, 12 * 3600), (14 * 3600, 18 * 3600))
READY_LOCAL = datetime(2026, 11, 23, 20, 0, tzinfo=HKT)
GENERATION_REFUSED = (
    "DeepSeek-V3.2-Exp",
    "DeepSeek-V3.2-Exp-FC",
    "DeepSeek-V3.2-Exp-thinking",
    "deepseek-chat",
    "deepseek-reasoner",
)
NOT_GENERATED = ("U", "L", "E")
EXCLUDED_OFFICIAL_COMPRESSOR_FLIGHTS = (
    "r=0.50 lambda=1/2",
    "r=0.75 lambda=1/4",
)
REDRAW_SENTENCE = (
    "A later flight would be a same-request re-draw of official U, "
    "not a new compressed catalogue."
)
EVALUATE_NOTE = (
    "bfcl evaluate reads saved outputs. DeepSeek-V3.2-Exp-FC is the scoring "
    "alias only. Generation under that alias is refused."
)


class FollowOnFlightRefused(RuntimeError):
    """The follow-on flight path will not start."""


class CeilingRequired(FollowOnFlightRefused):
    """No ceiling was supplied. The code does not choose one."""


def spend_cny(total_input: int, cache_hit: int, output: int) -> Decimal:
    """Off-peak CNY for the spend stop. This amount is not billed-basis T."""
    if total_input < 0 or cache_hit < 0 or output < 0:
        raise ValueError("token counts are non-negative")
    if cache_hit > total_input:
        raise ValueError("cache hit exceeds total input")
    miss = total_input - cache_hit
    return (Decimal(cache_hit) * RATE_HIT + Decimal(miss) * RATE_MISS + Decimal(output) * RATE_OUTPUT) / MILLION


def pre_call_reserve_cny() -> Decimal:
    """Worst-case one-call hold at the locked miss and output rates."""
    return spend_cny(MAX_INPUT_TOKENS, 0, MAX_OUTPUT_TOKENS)


def format_cny(amount: Decimal) -> str:
    return format(amount, "f")


def remaining_allows_call(spent: Decimal, ceiling: Decimal, reserve: Decimal) -> bool:
    if reserve <= 0 or ceiling <= 0 or spent < 0:
        return False
    if spent >= ceiling:
        return False
    return spent + reserve <= ceiling


def accept_ceiling(value) -> Decimal:
    """Parse a supplied ceiling. ``None`` and blanks are refusals, not defaults."""
    if isinstance(value, bool) or isinstance(value, float):
        raise CeilingRequired(
            "Pass the ceiling as a decimal string. There is no default ceiling."
        )
    if value is None:
        raise CeilingRequired(
            f"Set {CEILING_ENV} or pass --ceiling-cny. There is no default ceiling."
        )
    text = str(value).strip()
    if text == "":
        raise CeilingRequired(
            f"{CEILING_ENV} is blank. There is no default ceiling."
        )
    try:
        amount = Decimal(text)
    except (InvalidOperation, ValueError):
        raise CeilingRequired("The supplied ceiling is not a decimal CNY amount.") from None
    if not amount.is_finite() or amount <= 0:
        raise CeilingRequired("The supplied ceiling must be a positive CNY amount.")
    if amount > REMAINING_AUTHORIZED_CNY:
        raise CeilingRequired(
            "Supplied ceiling "
            f"{format_cny(amount)} exceeds the remaining authorized "
            f"{format_cny(REMAINING_AUTHORIZED_CNY)} of {format_cny(ORIGINAL_AUTHORIZATION_CNY)}."
        )
    return amount


def resolve_ceiling(explicit, environ: dict | None = None) -> Decimal:
    """Use the flag when present, otherwise the environment variable.

    Neither path substitutes the remaining authorization. A missing variable
    is a refusal.
    """
    if explicit is not None:
        return accept_ceiling(explicit)
    source = os.environ if environ is None else environ
    if CEILING_ENV not in source:
        raise CeilingRequired(
            f"Set {CEILING_ENV} or pass --ceiling-cny. There is no default ceiling."
        )
    return accept_ceiling(source.get(CEILING_ENV))


def is_peak(moment: datetime) -> bool:
    """Weekday 09:00–12:00 and 14:00–18:00 Asia/Hong_Kong, half-open.

    Hong Kong and the locked Asia/Shanghai card share this civil clock
    (UTC+8, no daylight saving). 20:00 on a weekday is after the second window.
    """
    if moment.tzinfo is None:
        raise ValueError("peak check requires a timezone-aware clock")
    local = moment.astimezone(HKT)
    if local.weekday() > 4:
        return False
    seconds = local.hour * 3600 + local.minute * 60 + local.second + local.microsecond / 1000000
    return any(start <= seconds < stop for start, stop in PEAK_WINDOWS)


def billed_basis_t(usage: dict | None) -> dict:
    """Provider ``prompt_tokens``. Cache hits are not subtracted and prices are not applied."""
    if not isinstance(usage, dict):
        return {
            "T": None,
            "basis": "provider_prompt_tokens",
            "cache_hits_subtracted": False,
            "prices_applied": False,
            "present": False,
        }
    total = usage.get("prompt_tokens", usage.get("total_input_tokens"))
    if isinstance(total, bool) or not isinstance(total, int):
        total = None
    return {
        "T": total,
        "basis": "provider_prompt_tokens",
        "cache_hits_subtracted": False,
        "prices_applied": False,
        "present": total is not None,
    }


def flight_body(messages: list, catalogue: list) -> dict:
    """Thinking-off deepseek-flash body. The scoring alias cannot be selected here."""
    request = {
        "messages": json.loads(json.dumps(messages)),
        "model": FLIGHT_MODEL,
        "temperature": BFCL_DEFAULT_TEMPERATURE,
        "store": BFCL_STORE,
        "thinking": dict(THINKING_DISABLED),
    }
    if catalogue:
        request["tools"] = json.loads(json.dumps(catalogue))
    assert_generation_body(request)
    return request


def assert_generation_body(body: dict) -> None:
    model = body.get("model")
    if model in GENERATION_REFUSED or model == SCORING_ALIAS:
        raise ScoringAliasGenerateRefused(
            f"Refusing generation under {model}. The flight model is {FLIGHT_MODEL}. "
            f"{SCORING_ALIAS} is scoring-only."
        )
    if model != FLIGHT_MODEL:
        raise FollowOnFlightRefused("generation model must be deepseek-flash")
    if body.get("thinking") != THINKING_DISABLED:
        raise FollowOnFlightRefused("thinking must be disabled")
    if "reasoning_effort" in body:
        raise FollowOnFlightRefused("reasoning_effort is not part of this flight")
    if body.get("temperature") != BFCL_DEFAULT_TEMPERATURE or body.get("store") is not False:
        raise FollowOnFlightRefused("temperature and store stay at the official BFCL defaults")


def official_evaluate_argv(result_dir: Path, score_dir: Path, bfcl: str = "bfcl") -> list[str]:
    """Official evaluate command for one saved-output directory. Generate is refused."""
    argv = build_bfcl_argv(
        "evaluate",
        model=SCORING_ALIAS,
        test_category="simple_python,multiple,irrelevance",
        result_dir=str(result_dir),
        score_dir=str(score_dir),
        bfcl=bfcl,
    )
    if "generate" in argv:
        raise ScoringAliasGenerateRefused("evaluate argv must not generate")
    return argv


def reconfirm_committed_identity(root: Path) -> dict:
    """Re-read the #5 audit artifacts. Does not rewrite them."""
    root = Path(root)
    summary_path = root / "followon" / "audit_summary.json"
    hashes_path = root / "followon" / "case_hashes.jsonl"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in hashes_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    by_category = {category: [] for category in CATEGORIES}
    mismatches = []
    for row in rows:
        category = row["category"]
        by_category[category].append(row)
        raw = row["raw_equal"]
        hashes = row["hashes"]
        same = (
            raw["T1_T2"] is True
            and raw["T1_U"] is True
            and raw["T2_U"] is True
            and hashes["T1"] == hashes["T2"] == hashes["U"]
            and row["preparation_failure"] is False
            and row["hash_matches_raw"] is True
        )
        if not same:
            mismatches.append(row.get("id"))
    f_new = {}
    for category, expected in DENOMINATORS.items():
        block = summary["categories"][category]
        numerator = block["f_new"]["numerator"]
        denominator = block["f_new"]["denominator"]
        f_new[category] = {
            "numerator": numerator,
            "denominator": denominator,
            "text": f"{numerator}/{denominator}",
            "unknown": block["f_new"]["unknown"],
            "cases": len(by_category[category]),
            "matches_expected_denominator": denominator == expected and len(by_category[category]) == expected,
        }
    identity_holds = (
        not mismatches
        and len(rows) == EXPECTED_CASES
        and all(item["numerator"] == 0 and item["unknown"] == 0 and item["matches_expected_denominator"] for item in f_new.values())
        and summary.get("provider_called") is False
        and summary.get("measured") is False
    )
    return {
        "source": "followon/audit_summary.json and followon/case_hashes.jsonl",
        "source_tip": SOURCE_TIP,
        "parent_tip": PARENT_TIP,
        "cases": len(rows),
        "hash_mismatches": mismatches,
        "f_new": f_new,
        "t1_equals_t2_equals_u": identity_holds,
        "identity_holds": identity_holds,
        "same_request_redraw_of_u": identity_holds,
        "provider_called": False,
        "measured": False,
        "official_scores_rewritten": False,
    }


def prepare_case(record: dict, counter) -> dict:
    """Build U, T1, and T2 flight bodies for one original case. Nothing is dropped."""
    turns = record.get("question") or []
    if not turns or not isinstance(turns[0], list):
        raise FollowOnFlightRefused(f"question turn missing for {record.get('id')}")
    messages = turns[0]
    catalogue = convert_record(record)
    produced = compress_conditions(catalogue, counter, (T1_CONFIG, T2_CONFIG))
    catalogues = {
        "U": catalogue,
        "T1": produced["catalogues"]["T1"],
        "T2": produced["catalogues"]["T2"],
    }
    bodies = {name: flight_body(messages, catalogues[name]) for name in ("U", "T1", "T2")}
    raw = {name: dump_request(body) for name, body in bodies.items()}
    return {"bodies": bodies, "raw": raw, "catalogues": catalogues}


def plan_record(record: dict, counter, category: str) -> list[dict]:
    """Two arm rows for one case. Identity with U does not remove the case."""
    prepared = prepare_case(record, counter)
    raw = prepared["raw"]
    digests = {name: _sha256(payload) for name, payload in raw.items()}
    identical_pair = raw["T1"] == raw["T2"]
    rows = []
    for arm in ARMS:
        rows.append(
            {
                "arm": arm,
                "category": category,
                "case_id": str(record["id"]),
                "replicate": 0,
                "included": True,
                "dropped": False,
                "dropped_because_identical_to_u": False,
                "identical_to_u": raw[arm] == raw["U"],
                "identical_t1_t2": identical_pair,
                "request_sha256": digests[arm],
                "u_request_sha256": digests["U"],
                "members": [arm],
                "shares_official_u_answer": False,
            }
        )
    return rows


def catalogue_plan(study: dict, counter) -> list[dict]:
    """One row per arm per original case. Cases identical to U stay in the plan."""
    require_official_denominators(study)
    rows = []
    for category in CATEGORIES:
        for record in study[category]:
            rows.extend(plan_record(record, counter, category))
    if len(rows) != EXPECTED_CASES * len(ARMS):
        raise FollowOnFlightRefused("flight plan did not cover both arms on all 840 cases")
    if any(row["dropped"] for row in rows):
        raise FollowOnFlightRefused("flight plan dropped a case")
    return rows


def arm_rows(rows: list[dict], arm: str) -> list[dict]:
    if arm not in ARMS:
        raise FollowOnFlightRefused("flight arms are T1 and T2")
    selected = [row for row in rows if row["arm"] == arm]
    if len(selected) != EXPECTED_CASES:
        raise FollowOnFlightRefused(f"{arm} plan does not contain all {EXPECTED_CASES} cases")
    return selected


def sequential_groups(rows: list[dict]) -> list[dict]:
    """Share one physical call only when T1 and T2 match inside the same case.

    Official U answers are not members of these groups. A separate arm flight
    does not use this sharing; it sends that arm's 840 cases on its own.
    """
    by_case: dict[tuple[str, str], dict[str, dict]] = {}
    order: list[tuple[str, str]] = []
    for row in rows:
        key = (row["category"], row["case_id"])
        if key not in by_case:
            order.append(key)
            by_case[key] = {}
        by_case[key][row["arm"]] = row
    groups = []
    for key in order:
        pair = by_case[key]
        if set(pair) != set(ARMS):
            raise FollowOnFlightRefused(f"sequential plan is missing an arm for {key}")
        left = pair["T1"]
        right = pair["T2"]
        if left["identical_t1_t2"] and left["request_sha256"] == right["request_sha256"]:
            groups.append(
                {
                    "category": key[0],
                    "case_id": key[1],
                    "replicate": 0,
                    "members": ["T1", "T2"],
                    "reused_members": ["T2"],
                    "request_sha256": left["request_sha256"],
                    "identical_to_u": left["identical_to_u"] and right["identical_to_u"],
                    "included_cases": 1,
                    "logical_assignments": 2,
                    "shares_official_u_answer": False,
                }
            )
        else:
            for arm in ARMS:
                groups.append(
                    {
                        "category": key[0],
                        "case_id": key[1],
                        "replicate": 0,
                        "members": [arm],
                        "reused_members": [],
                        "request_sha256": pair[arm]["request_sha256"],
                        "identical_to_u": pair[arm]["identical_to_u"],
                        "included_cases": 1,
                        "logical_assignments": 1,
                        "shares_official_u_answer": False,
                    }
                )
    logical = sum(group["logical_assignments"] for group in groups)
    if logical != EXPECTED_CASES * len(ARMS):
        raise FollowOnFlightRefused("sequential grouping dropped a logical assignment")
    return groups


def identity_from_rows(rows: list[dict]) -> dict:
    per_arm = {}
    for arm in ARMS:
        selected = arm_rows(rows, arm)
        equal_u = sum(row["identical_to_u"] for row in selected)
        per_arm[arm] = {
            "cases": len(selected),
            "included": sum(row["included"] for row in selected),
            "dropped": sum(row["dropped"] for row in selected),
            "identical_to_u": equal_u,
            "different_from_u": len(selected) - equal_u,
        }
    pair_equal = sum(row["identical_t1_t2"] for row in rows if row["arm"] == "T1")
    holds = (
        all(item["cases"] == EXPECTED_CASES and item["dropped"] == 0 for item in per_arm.values())
        and all(item["identical_to_u"] == EXPECTED_CASES for item in per_arm.values())
        and pair_equal == EXPECTED_CASES
    )
    return {
        "arms": per_arm,
        "t1_equals_t2_cases": pair_equal,
        "identity_holds": holds,
        "same_request_redraw_of_u": holds,
        "later_flight_interpretation": REDRAW_SENTENCE if holds else (
            "T1 or T2 flight bodies differ from U. The plan still keeps every original case."
        ),
        "shares_official_u_answer": False,
    }


def execution_record(ceiling: Decimal, arms: tuple[str, ...]) -> dict:
    amount = accept_ceiling(format_cny(ceiling))
    return {
        "purpose": "phrase-contrast-followon",
        "arms": list(arms),
        "official_settlement": False,
        "official_accuracy": False,
        "official_target_lowered": False,
        "revises_official_c_versus_u": False,
        "model": FLIGHT_MODEL,
        "model_version": FLIGHT_MODEL_VERSION,
        "thinking": {"type": "disabled", "pinned_before_any_call": True},
        "provider_options": {
            "temperature": BFCL_DEFAULT_TEMPERATURE,
            "store": False,
            "thinking": dict(THINKING_DISABLED),
        },
        "handler_alias": None,
        "scoring_alias": SCORING_ALIAS,
        "scoring_alias_may_generate": False,
        "generation_refused_aliases": list(GENERATION_REFUSED),
        "not_generated": list(NOT_GENERATED),
        "excluded_official_compressor_flights": list(EXCLUDED_OFFICIAL_COMPRESSOR_FLIGHTS),
        "sample": {
            "multiple": DENOMINATORS["multiple"],
            "simple_python": DENOMINATORS["simple_python"],
            "irrelevance": DENOMINATORS["irrelevance"],
            "total": EXPECTED_CASES,
        },
        "evaluation": "official bfcl evaluate from saved outputs",
        "billed_basis": "provider_prompt_tokens",
        "cache_hits_subtracted_from_T": False,
        "prices_applied_to_T": False,
        "rate_card": _rate_card(),
        "spending_ceiling": {
            "amount": format_cny(amount),
            "currency": "CNY",
            "hard": True,
            "do_not_lift": True,
            "supplied_at_runtime": True,
            "hardcoded": False,
            "default": None,
        },
        "remaining_authorized_cny": format_cny(REMAINING_AUTHORIZED_CNY),
        "remaining_authorized_is_not_a_default": True,
        "original_authorization_cny": format_cny(ORIGINAL_AUTHORIZATION_CNY),
        "pre_call_reserve_cny": format_cny(pre_call_reserve_cny()),
        "api_base_url": API_BASE_URL,
        "api_path": API_PATH,
        "api_key_source": API_KEY_ENV,
        "api_key_in_repository": False,
        "t1": T1_CONFIG.as_dict(),
        "t2": T2_CONFIG.as_dict(),
        "compressor_retuned": False,
        "gorilla_commit": GORILLA_COMMIT,
        "ready_at_local": "2026-11-23T20:00:00+08:00",
        "ready_at_is_peak": is_peak(READY_LOCAL),
        "frozen": True,
        "started_by_import": False,
    }


def flight_summary(rows: list[dict], ceiling: Decimal, arms: tuple[str, ...], *, sequential: bool) -> dict:
    identity = identity_from_rows(rows)
    groups = sequential_groups(rows) if sequential and arms == ARMS else None
    per_arm = {}
    for arm in arms:
        selected = arm_rows(rows, arm)
        per_arm[arm] = {
            "cases": len(selected),
            "physical_calls_if_flown_alone": len(selected),
            "dropped": 0,
            "identical_to_u": sum(row["identical_to_u"] for row in selected),
            "provider_T_sum": None,
            "mean_T": None,
            "official_correct": None,
        }
    summary = {
        "purpose": "phrase-contrast-followon",
        "status": "ready_for_later_flight",
        "measured": False,
        "provider_called": False,
        "network_used": False,
        "started": False,
        "live": False,
        "arms": per_arm,
        "identity": identity,
        "same_request_redraw_of_u": identity["same_request_redraw_of_u"],
        "later_flight_interpretation": identity["later_flight_interpretation"],
        "sequential": sequential and arms == ARMS,
        "sequential_physical_calls": None if groups is None else len(groups),
        "sequential_logical_assignments": None if groups is None else sum(group["logical_assignments"] for group in groups),
        "official_u_answers_reused": False,
        "ceiling_cny": format_cny(accept_ceiling(format_cny(ceiling))),
        "ceiling_default": None,
        "ceiling_hardcoded": False,
        "first_call_allowed_by_reserve": remaining_allows_call(Decimal("0"), ceiling, pre_call_reserve_cny()),
        "pre_call_reserve_cny": format_cny(pre_call_reserve_cny()),
        "billed_basis": "provider_prompt_tokens",
        "prices_applied_to_T": False,
        "cache_hits_subtracted_from_T": False,
        "provider_T_invented": False,
        "official_target_lowered": False,
        "revises_official_c_versus_u": False,
        "official_evaluate": {
            "command": "evaluate",
            "generate": False,
            "invoked": False,
            "decoder_alias": SCORING_ALIAS,
            "note": EVALUATE_NOTE,
        },
    }
    return summary


def write_plan(out: Path, rows: list[dict], ceiling: Decimal, arms: tuple[str, ...], *, sequential: bool) -> dict:
    """Write a plan directory. Does not construct a provider client."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    record = execution_record(ceiling, arms)
    summary = flight_summary(rows, ceiling, arms, sequential=sequential)
    selected = [row for row in rows if row["arm"] in arms]
    if sequential and arms == ARMS:
        index = sequential_groups(rows)
    else:
        index = arm_rows(selected, arms[0]) if len(arms) == 1 else selected
    _write_json(out / "execution_record.json", record)
    _write_json(out / "flight_summary.json", summary)
    _write_jsonl(out / "plan_index.jsonl", index)
    result_dir = out / "bfcl_result"
    score_dir = out / "bfcl_score"
    evaluate = official_evaluate_argv(result_dir, score_dir)
    payload = {
        "argv": evaluate,
        "invoked": False,
        "command": "evaluate",
        "generate": False,
        "decoder_alias": SCORING_ALIAS,
        "note": EVALUATE_NOTE,
    }
    _write_json(out / "official_evaluate_command.json", payload)
    _write_json(
        out / "comparison_versus_official_u.json",
        comparison_versus_official_u(Path(__file__).resolve().parents[2], usage_by_arm=None, identity=summary["identity"]),
    )
    _write_text(
        out / "README.txt",
        "Plan only. provider_called is false. Do not treat this directory as a measured result.\n"
        "Pass --live only after EXPLORATORY_CEILING_CNY is supplied. There is no default ceiling.\n"
        "Score saved outputs with bfcl evaluate. Do not run bfcl generate.\n",
    )
    summary["out"] = str(out)
    return summary


def comparison_versus_official_u(root: Path, usage_by_arm: dict | None, identity: dict | None) -> dict:
    """Token comparison against closed official U. Unflown arms keep T null."""
    historical = reproduce_historical_official_counts(root)
    if not historical["ok"]:
        raise FollowOnFlightRefused("official settlement failed its locked checks")
    redraw = bool(identity and identity.get("same_request_redraw_of_u"))
    rows = []
    for category in CATEGORIES:
        block = historical["categories"][category]
        u_sum = block["provider_input_sum"]["U"]
        n = block["n"]
        for arm in ARMS:
            measured = _arm_category_usage(usage_by_arm, arm, category, n)
            complete = measured["complete"]
            saving = None
            if complete and u_sum:
                saving = {
                    "numerator": u_sum - measured["sum"],
                    "denominator": u_sum,
                    "ratio_of_means": (u_sum - measured["sum"]) / u_sum,
                    "mean_official_U": u_sum / n,
                    "mean_arm": measured["sum"] / n,
                    "paired_case_level": False,
                    "comparator": "closed official U cohort sum",
                    "contemporaneous_u_reflight": False,
                }
            rows.append(
                {
                    "category": category,
                    "arm": arm,
                    "status": "measured" if complete else "unflown",
                    "cases": n,
                    "official_U_provider_input_sum": u_sum,
                    "official_U_correct": block["correct"]["U"],
                    "provider_T_sum": measured["sum"] if complete else None,
                    "mean_T": (measured["sum"] / n) if complete else None,
                    "saving_versus_official_U": saving,
                    "official_correct": None,
                    "prices_applied_to_T": False,
                    "cache_hits_subtracted": False,
                    "exploratory_follow_on": True,
                    "revises_official_c_versus_u": False,
                    "official_target_lowered": False,
                    "official_target_applies_to_this_comparison": False,
                    "same_request_redraw_of_u": redraw,
                }
            )
    return {
        "schema": "tool-compression.followon-comparison.v1",
        "exploratory_follow_on": True,
        "revises_official_c_versus_u": False,
        "official_baseline_closed": True,
        "official_target_lowered": False,
        "official_primary_S_LU": {"numerator": 1398, "denominator": 121018, "revised": False},
        "official_primary_accuracy": {"U": 186, "L": 185, "E": 186, "n": 200, "revised": False},
        "same_request_redraw_of_u": redraw,
        "interpretation": REDRAW_SENTENCE if redraw else (
            "Unflown arms do not receive an invented provider T. "
            "A measured row uses saved prompt_tokens only."
        ),
        "billed_basis": "provider_prompt_tokens",
        "prices_applied_to_T": False,
        "cache_hits_subtracted": False,
        "provider_T_invented": False,
        "rows": rows,
        "historical_source": historical["source"],
    }


def reconfirm_study(study: dict, counter) -> dict:
    """Re-execute T1/T2 on a loaded study and compare flight-body identity to U."""
    rows = catalogue_plan(study, counter)
    found = identity_from_rows(rows)
    by_category = {}
    for category, expected in DENOMINATORS.items():
        arm_cases = [row for row in rows if row["arm"] == "T1" and row["category"] == category]
        differ = [row["case_id"] for row in arm_cases if not row["identical_to_u"] or not row["identical_t1_t2"]]
        by_category[category] = {
            "cases": len(arm_cases),
            "expected": expected,
            "f_new_numerator": len(differ),
            "identical_to_u": len(arm_cases) - len(differ),
        }
    return {
        "reexecuted": True,
        "network_used": False,
        "provider_called": False,
        "categories": by_category,
        "identity": found,
        "rows": rows,
    }


def write_flight_readiness(root: Path, bfcl_root: Path | None, destination: Path) -> dict:
    """Record the reconfirmed audit and the 840-case plan. No provider call."""
    root = Path(root)
    committed = reconfirm_committed_identity(root)
    historical = reproduce_historical_official_counts(root)
    reexecuted = None
    plan_rows = None
    if bfcl_root is not None:
        from tool_compression.count import study_counters
        from tool_compression.load import load_study

        study = load_study(bfcl_root)
        counter, _sensitivity = study_counters()
        reexecuted = reconfirm_study(study, counter)
        plan_rows = reexecuted.pop("rows")
    identity_holds = committed["identity_holds"] and (
        reexecuted is None or reexecuted["identity"]["identity_holds"]
    )
    payload = {
        "schema": "tool-compression.followon-flight-readiness.v1",
        "purpose": "phrase-contrast-followon",
        "source_tip": SOURCE_TIP,
        "parent_tip": PARENT_TIP,
        "parent_pull_request": "https://github.com/jacky-wong9273/tool-compression/pull/4",
        "followon_pull_request": "https://github.com/jacky-wong9273/tool-compression/pull/5",
        "this_pull_request_is_t1_t2_preparation": True,
        "not_the_official_compressor_robustness_flights": True,
        "excluded_official_compressor_flights": list(EXCLUDED_OFFICIAL_COMPRESSOR_FLIGHTS),
        "ready_for_later_flight": identity_holds and historical["ok"],
        "ready_at_local": "2026-11-23T20:00:00+08:00",
        "ready_at_timezone": "Asia/Hong_Kong",
        "ready_at_is_peak": is_peak(READY_LOCAL),
        "measured": False,
        "provider_called": False,
        "network_generation": False,
        "official_scores_rewritten": False,
        "official_target_lowered": False,
        "official_baseline_closed": {
            "S_LU": "1398/121018",
            "ratio": "1.155%",
            "accuracy": {"U": "186/200", "L": "185/200", "E": "186/200"},
            "target": "1/10",
            "target_lowered": False,
        },
        "committed_audit": committed,
        "reexecuted_against_pinned_question_files": reexecuted is not None,
        "reexecution": None if reexecuted is None else {
            "provider_called": False,
            "network_used": False,
            "categories": reexecuted["categories"],
            "identity_holds": reexecuted["identity"]["identity_holds"],
            "gorilla_commit": GORILLA_COMMIT,
        },
        "identity_holds": identity_holds,
        "same_request_redraw_of_u": identity_holds,
        "later_flight_interpretation": (
            REDRAW_SENTENCE if identity_holds else "Identity did not hold. Cases were not dropped."
        ),
        "flight_paths": {
            "T1": {"cases": EXPECTED_CASES, "physical_calls_if_flown_alone": EXPECTED_CASES, "dropped": 0},
            "T2": {"cases": EXPECTED_CASES, "physical_calls_if_flown_alone": EXPECTED_CASES, "dropped": 0},
            "sequential_T1_then_T2": {
                "logical_assignments": EXPECTED_CASES * 2,
                "physical_calls_if_requests_match_within_case": EXPECTED_CASES if identity_holds else None,
                "share_rule": "exact flight-body identity within the same case and this replicate only",
                "official_U_answers_reused": False,
            },
        },
        "evaluation_method": {
            "model": FLIGHT_MODEL,
            "model_version": FLIGHT_MODEL_VERSION,
            "thinking": "disabled",
            "temperature": BFCL_DEFAULT_TEMPERATURE,
            "store": False,
            "categories": dict(DENOMINATORS),
            "scorer": "bfcl evaluate on saved outputs",
            "scoring_alias": SCORING_ALIAS,
            "scoring_alias_may_generate": False,
            "billed_basis_T": "provider prompt_tokens",
            "cache_hits_subtracted": False,
            "prices_applied_to_T": False,
            "official_U_comparator": "closed thinking-off Flash U; not re-flown",
        },
        "ceiling": {
            "env": CEILING_ENV,
            "default": None,
            "hardcoded_default": False,
            "remaining_authorized_cny": format_cny(REMAINING_AUTHORIZED_CNY),
            "original_authorization_cny": format_cny(ORIGINAL_AUTHORIZATION_CNY),
            "remaining_is_not_a_default": True,
            "pre_call_reserve_cny": format_cny(pre_call_reserve_cny()),
        },
        "provider_T": None,
        "configs": {"T1": T1_CONFIG.as_dict(), "T2": T2_CONFIG.as_dict()},
        "compressor_retuned": False,
    }
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    _write_json(destination, payload)
    if plan_rows is not None:
        index_path = destination.parent / "flight_plan_index.jsonl"
        _write_jsonl(index_path, plan_rows)
        payload["plan_index"] = str(index_path.relative_to(root) if index_path.is_relative_to(root) else index_path)
        _write_json(destination, payload)
    return payload


def _arm_category_usage(usage_by_arm: dict | None, arm: str, category: str, n: int) -> dict:
    if not usage_by_arm or arm not in usage_by_arm:
        return {"complete": False, "sum": None}
    arm_usage = usage_by_arm[arm]
    if not isinstance(arm_usage, dict):
        return {"complete": False, "sum": None}
    values = (arm_usage.get("categories") or {}).get(category)
    if not isinstance(values, list) or len(values) != n:
        return {"complete": False, "sum": None}
    parsed = []
    for item in values:
        if isinstance(item, bool) or not isinstance(item, int) or item < 0:
            return {"complete": False, "sum": None}
        parsed.append(item)
    return {"complete": True, "sum": sum(parsed)}


def require_official_denominators(study: dict) -> None:
    for category, expected in DENOMINATORS.items():
        records = study.get(category)
        if not isinstance(records, list) or len(records) != expected:
            found = len(records) if isinstance(records, list) else None
            raise FollowOnFlightRefused(
                f"{category} has {found} cases; the official flight uses {expected}"
            )


def _rate_card() -> dict:
    return {
        "schedule": "off-peak",
        "currency": "CNY",
        "unit": "per_million_tokens",
        "cache_hit_per_million": format_cny(RATE_HIT),
        "cache_miss_per_million": format_cny(RATE_MISS),
        "output_per_million": format_cny(RATE_OUTPUT),
        "locked": True,
        "applied_to_T": False,
        "role": "spend stop only",
    }


def _sha256(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def _write_jsonl(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(row, sort_keys=True, ensure_ascii=False) for row in rows]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def result_filename(category: str) -> str:
    return f"{VERSION_PREFIX}_{category}_result.json"
