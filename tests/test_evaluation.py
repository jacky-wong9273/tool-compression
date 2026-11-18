"""Evaluation Protocol v1.1 scaffold. No model calls and no benchmark prose."""

from pathlib import Path
import json

import pytest

from tool_compression import __version__
from tool_compression.compress import compress
from tool_compression.config import DEFAULT_CONFIG
from tool_compression.convert import FLOAT_SUFFIX
from tool_compression.evaluation import (
    DENOMINATORS,
    PaidInferenceRefused,
    assert_inference_allowed,
    evaluation_manifest,
    execution_record_gaps,
    execution_record_template,
    freeze_execution_record,
    prepare_case,
    prepare_reference_case,
    primary_accuracy_change,
    primary_provider_saving,
    reference_target_from_external,
    study_target_status,
    summarize_hash_rows,
)
from tool_compression.flight_spec import validation_flight_record
from tool_compression.grouping import group_exact_requests
from tool_compression.implementations import ExternalSnapshot, LocalMethod, reference_implementations
from tool_compression.prepare import assemble_request, identity_components, request_hash
from tool_compression.suffix import float_suffix_report
from tool_compression.usage import (
    UsageLedger,
    cohort_provider_saving,
    combine_targets,
    local_estimate_status,
    paired_accuracy_change,
    usage_from_mapping,
)
from tool_compression.__main__ import main

ROOT = Path(__file__).resolve().parents[1]
NEW_MODULES = (
    "implementations.py",
    "grouping.py",
    "usage.py",
    "evaluation.py",
    "suffix.py",
)


class Words:
    name = "words"

    def count(self, text: str) -> int:
        return len(text.split())


def tool(name, description, param="xxxx"):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {"x": {"type": "string", "description": param}},
                "required": ["x"],
            },
        },
    }


def description(result, index=0):
    return result["catalogue"][index]["function"]["description"]


def messages():
    return [{"role": "user", "content": "task"}]


def float_node(case, path_end):
    matches = [node for node in case["nodes"] if node["path"].endswith(path_end)]
    assert len(matches) == 1
    return matches[0]


def test_package_version_and_reference_manifest_keep_the_audited_settings():
    assert __version__ == "0.2.0"
    manifest = evaluation_manifest()
    settings = manifest["settings"]
    assert settings["spec_version"] == "week1.0"
    assert settings["retention_r"] == "3/4"
    assert settings["jaccard_min"] == "1/5"
    assert settings["max_neighbours"] == 2
    assert settings["lambda"] == "1/2"
    assert settings["tuned"] is False
    assert manifest["denominators"] == DENOMINATORS
    assert manifest["other_change_cases_not_a_denominator"] == 36
    assert manifest["target_provider_input_reduction"] == "1/10"
    assert manifest["paid_inference_authorized"] is False
    assert manifest["paid_inference_implemented"] is True
    assert manifest["execution_record"]["model"] is None
    assert manifest["execution_record"]["paid_inference_authorized"] is False
    assert manifest["execution_record"]["frozen"] is False
    assert manifest["implementation_corrections"] == []
    assert manifest["preparation_outputs_regenerated"] is False
    assert manifest["second_compressor"] is False
    assert manifest["e_versus_u_can_satisfy_reference_target"] is False
    assert manifest["l_is_reporting_label_only"] is True
    assert manifest["representing_c_by_l_tests_contrast"] is False
    assert manifest["week1_primary_active_fraction_f"] == "0/200"
    assert manifest["contrast_term_tested"] is False
    assert manifest["official_accuracy_in_scope"] is False
    assert manifest["provider_usage_measurement_in_scope"] is False
    assert set(reference_implementations()) == {"U", "P", "I", "C"}


def test_manifest_pins_match_the_week1_packet():
    manifest = evaluation_manifest()
    characterization = json.loads((ROOT / "evidence" / "week1_characterization.json").read_text(encoding="utf-8"))
    arm = json.loads((ROOT / "evidence" / "week1_arm_e.json").read_text(encoding="utf-8"))
    assert manifest["pins"]["bfcl_commit"] == characterization["provenance"]["bfcl_commit"]
    assert manifest["pins"]["tscg_commit"] == arm["tscg"]["commit"]
    assert manifest["pins"]["tscg_version"] == arm["tscg"]["version"]
    assert manifest["pins"]["tscg_package"] == arm["tscg"]["package"]


def test_l_is_not_an_implementation_and_a_second_compressor_is_rejected():
    with pytest.raises(ValueError):
        LocalMethod("L")
    with pytest.raises(ValueError):
        LocalMethod("LLMLingua2")
    with pytest.raises(ValueError):
        prepare_case([tool("ta", "Alpha.")], messages(), {"L": LocalMethod("U")}, DEFAULT_CONFIG, Words())


def test_interchangeable_implementations_keep_traces_and_validate_the_boundary():
    class Edit:
        def __init__(self, name):
            self.name = name
            self.calls = 0

        def apply(self, catalogue, config, counter):
            _ = (config, counter)
            self.calls += 1
            blob = json.dumps(catalogue)
            assert "SENTINEL_MESSAGE" not in blob
            produced = json.loads(blob)
            if self.name != "U":
                produced[0]["function"]["description"] = "Kept."
            return {"catalogue": produced, "traces": [{"method": self.name}], "method": self.name}

    class Rename:
        name = "P"

        def apply(self, catalogue, config, counter):
            _ = (config, counter)
            produced = json.loads(json.dumps(catalogue))
            produced[0]["function"]["name"] = "changed"
            return {"catalogue": produced, "traces": [], "method": "P"}

    edits = {name: Edit(name) for name in ("U", "P", "I", "C")}
    caller = [tool("ta", "Alpha beta.")]
    snapshot = json.loads(json.dumps(caller))
    prepared = prepare_case(
        caller,
        [{"role": "user", "content": "SENTINEL_MESSAGE"}],
        edits,
        DEFAULT_CONFIG,
        Words(),
    )
    assert caller == snapshot
    assert all(edit.calls == 1 for edit in edits.values())
    assert prepared["reporting_label"] == "L"
    assert prepared["label_is_compressor"] is False
    assert prepared["label_is_selected_winner"] is False
    assert set(prepared["traces"]) == {"P", "I", "C"}
    assert "L" not in prepared["traces"]
    assert [group["members"] for group in prepared["groups"]] == [["U"], ["L"]]
    with pytest.raises(RuntimeError):
        prepare_case(caller, messages(), {"U": edits["U"], "P": Rename()}, DEFAULT_CONFIG, Words())


def test_reference_selector_labels_l_only_when_requests_coincide():
    coinciding = prepare_reference_case(
        [tool("ta", "Alpha beta gamma.")],
        messages(),
        Words(),
        case_id="one",
    )
    assert coinciding["reporting_label"] == "L"
    assert coinciding["groups"][0]["members"] == ["U", "L"]
    assert coinciding["groups"][0]["group_is_one_independent_response"] is True
    assert set(coinciding["traces"]) == {"P", "I", "C"}
    diverging = prepare_reference_case(
        [
            tool("ta", "AAAA. bbbb cccc. dddd eeee."),
            tool("tb", "bbbb cccc."),
        ],
        messages(),
        Words(),
        case_id="two",
    )
    assert diverging["reporting_label"] is None
    assert all("L" not in group["members"] for group in diverging["groups"])
    flat = [member for group in diverging["groups"] for member in group["members"]]
    assert flat == ["U", "P", "I", "C"]
    shared = [group for group in diverging["groups"] if group["members"] == ["P", "I"]]
    assert len(shared) == 1
    assert shared[0]["extra_members_are_reused"] is True


def test_exact_matches_share_one_response_inside_case_and_replicate_only():
    conditions = {"U": "h", "L": "h", "E": "e"}
    first = group_exact_requests("multiple", "case", 0, conditions)
    second = group_exact_requests("multiple", "case", 1, conditions)
    other = group_exact_requests("multiple", "other", 0, conditions)
    assert [group.members for group in first] == [("U", "L"), ("E",)]
    assert first[0].shared_response_id != second[0].shared_response_id
    assert first[0].shared_response_id != other[0].shared_response_id
    external = prepare_case(
        [tool("ta", "Alpha.")],
        messages(),
        {**reference_implementations(), "E": ExternalSnapshot([tool("ta", "Alpha.")])},
        DEFAULT_CONFIG,
        Words(),
    )
    assert external["groups"][0]["members"] == ["U", "L", "E"]
    assert external["groups"][0]["logical_members"] == 3
    assert external["groups"][0]["extra_members_are_reused"] is True


def test_request_identity_includes_model_messages_catalogue_and_options():
    catalogue = [tool("ta", "Alpha.")]
    request = assemble_request(messages(), catalogue)
    parts = identity_components(request)
    assert parts["provisional"] is True
    assert parts["model"] == "UNSELECTED"
    assert parts["messages"] == messages()
    assert parts["catalogue"] == catalogue
    assert parts["provider_options"] == {"temperature": 0.001, "store": False}
    changed = dict(request)
    changed["temperature"] = 0.0
    assert request_hash(request) != request_hash(changed)
    renamed = dict(request)
    renamed["model"] = "selected-later"
    assert request_hash(request) != request_hash(renamed)


def test_packet_hashes_reproduce_the_provisional_group_counts():
    local = [
        json.loads(line)
        for line in (ROOT / "evidence" / "week1_request_hashes.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    arm_rows = [
        json.loads(line)
        for line in (ROOT / "evidence" / "week1_arm_e_hashes.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    summary = summarize_hash_rows(local, arm_rows)
    published = json.loads((ROOT / "evidence" / "week1_arm_e.json").read_text(encoding="utf-8"))
    assert summary["size_histogram"] == published["shared_request_groups"]
    counts = summary["provisional_unique_request_groups_per_replicate"]
    assert counts["multiple"] == 438
    assert counts["all_categories"] == 1513
    assert summary["cases_with_reporting_label_L"] == {
        "multiple": 200,
        "simple_python": 400,
        "irrelevance": 240,
    }
    assert summary["cases_without_reporting_label_L"] == {
        "multiple": 0,
        "simple_python": 0,
        "irrelevance": 0,
    }
    assert summary["c_represented_by"] == "L"
    assert summary["l_is_reporting_label_only"] is True
    assert summary["representing_c_by_l_tests_contrast"] is False
    assert summary["primary_active_fraction_f"] == {"numerator": 0, "denominator": 200}
    assert summary["contrast_term_tested"] is False
    assert summary["official_accuracy_in_scope"] is False
    assert summary["provider_usage_measurement_in_scope"] is False
    assert summary["reporting_label_covers"] == ["P", "I", "C"]
    assert summary["label_is_compressor"] is False
    assert summary["logical_condition_assignments"] == (200 + 400 + 240) * 3
    assert (
        summary["reused_logical_assignments"]
        == summary["logical_condition_assignments"] - counts["all_categories"]
    )
    assert summary["denominators"]["multiple"] == 200
    assert summary["physical_attempts"] == 0
    assert summary["provider_usage_measured"] is False
    assert summary["target_reached"] is None
    assert summary["target_status"] == "unresolved_provider_usage_not_measured"
    assert summary["replicate_count_selected"] is None
    assert summary["paid_inference"] is False
    assert summary["preparation_outputs_regenerated"] is False


def test_primary_denominator_stays_200_and_missing_usage_is_not_zero():
    with pytest.raises(ValueError):
        primary_provider_saving([100] * 36, [90] * 36)
    with pytest.raises(ValueError):
        primary_accuracy_change([True] * 36, [True] * 36)
    missing = primary_provider_saving([100] * 199 + [None], [90] * 200)
    assert missing["attainment"] == "unresolved"
    assert missing["target_reached"] is None
    assert missing["reason"] == "missing_usage"
    reached = primary_provider_saving([100] * 200, [90] * 200)
    assert reached["target_reached"] is True
    assert reached["ratio_numerator"] == 2000
    assert reached["ratio_denominator"] == 20000
    short = primary_provider_saving([100] * 200, [95] * 200)
    assert short["target_reached"] is False
    utility = combine_targets(reached, {"attainment": "unresolved"})
    assert utility["target_reached"] is None
    assert utility["reference_comparison"] == "C-U"
    met = {"attainment": "resolved", "within_observed_limit": True}
    missed = {"attainment": "resolved", "within_observed_limit": False}
    assert combine_targets(reached, met)["target_reached"] is True
    assert combine_targets(short, met)["target_reached"] is False
    assert combine_targets(reached, missed)["target_reached"] is False


def test_cohort_saving_is_the_ratio_of_means_and_local_estimates_stay_open():
    saving = cohort_provider_saving([100, 10], [90, 0], denominator=2)
    assert saving["ratio_numerator"] == 20
    assert saving["ratio_denominator"] == 110
    assert saving["mean_of_per_case_ratios"] == pytest.approx(0.55)
    assert saving["target"] == "1/10"
    assert saving["target_lowered"] is False
    exact = cohort_provider_saving([100], [90], denominator=1)
    under = cohort_provider_saving([100], [91], denominator=1)
    assert exact["target_reached"] is True
    assert under["target_reached"] is False
    assert local_estimate_status(0.5)["provider_target_reached"] is None
    with pytest.raises(TypeError):
        cohort_provider_saving([True], [False], denominator=1)
    external = reference_target_from_external(0.5)
    assert external["can_satisfy_c_u_target"] is False


def test_accuracy_margin_is_descriptive_and_outcomes_can_be_missing():
    baseline = [True, True, False, False]
    variant = [True, False, True, False]
    change = paired_accuracy_change(baseline, variant, denominator=4)
    assert change["gains"] == 1
    assert change["losses"] == 1
    assert change["delta_numerator"] == 0
    assert change["non_inferiority_tested"] is False
    at_limit = primary_accuracy_change([True] * 200, [True] * 196 + [False] * 4)
    past_limit = primary_accuracy_change([True] * 200, [True] * 195 + [False] * 5)
    assert at_limit["within_observed_limit"] is True
    assert at_limit["losses"] == 4
    assert past_limit["within_observed_limit"] is False
    unresolved = paired_accuracy_change([True, None], [True, False], denominator=2)
    assert unresolved["attainment"] == "unresolved"
    assert unresolved["within_observed_limit"] is None


def test_usage_ledger_separates_shared_responses_from_physical_attempts():
    usage = usage_from_mapping(
        {
            "prompt_tokens": 100,
            "completion_tokens": 5,
            "prompt_tokens_details": {"cached_tokens": 40},
        }
    )
    assert usage.total_input_tokens == 100
    assert usage.cached_input_tokens == 40
    assert usage.output_tokens == 5
    handler = usage_from_mapping({"input_token": 10, "output_token": 2})
    assert handler.cached_input_tokens is None
    assert usage_from_mapping(None).total_input_tokens is None
    assert usage_from_mapping({}).total_input_tokens is None
    assert usage_from_mapping({"prompt_tokens": 0}).total_input_tokens == 0
    ledger = UsageLedger()
    ledger.record_attempt(
        response_group_id="g",
        case_id="case",
        replicate=0,
        members=("U", "L"),
        status="received",
        usage=usage,
    )
    ledger.record_attempt(
        response_group_id="g",
        case_id="case",
        replicate=0,
        members=("U", "L"),
        status="failed",
        usage=usage_from_mapping(None),
    )
    assert ledger.physical_attempt_count() == 2
    assert ledger.logical_response_input("case", 0, "U") == 100
    assert ledger.logical_response_input("case", 0, "L") == 100
    billed = ledger.physical_billed_input("case", 0, "U")
    assert billed["coverage"] == "incomplete"
    assert billed["tokens"] is None
    assert billed["attempts"] == 2


def test_inference_is_refused_when_the_execution_record_is_empty_or_filled():
    template = execution_record_template()
    assert template["paid_inference_authorized"] is False
    assert template["frozen"] is False
    assert "model" in execution_record_gaps(template)
    assert study_target_status(template)["target_reached"] is None
    with pytest.raises(PaidInferenceRefused):
        assert_inference_allowed(template)
    filled = {
        "model": "selected-later",
        "provider_options": {"temperature": 0.001},
        "replicate_count": 1,
        "failure_policy": "unset-in-this-package",
        "analysis_configuration": "logical_response_input",
        "paid_inference_authorized": True,
        "spending_ceiling": "separate-authorization",
        "frozen": True,
    }
    gaps = execution_record_gaps(filled)
    assert gaps
    assert "thinking_disabled" in gaps
    assert "spending_ceiling" in gaps
    with pytest.raises(PaidInferenceRefused):
        assert_inference_allowed(filled)
    frozen = freeze_execution_record(validation_flight_record())
    assert execution_record_gaps(frozen) == []
    assert_inference_allowed(frozen)
    assert study_target_status(frozen)["attainment"] == "unresolved"
    assert study_target_status(frozen)["target_reached"] is None


def test_float_suffix_information_after_conversion():
    report = float_suffix_report()
    blob = json.dumps(report)
    assert "Length." not in blob
    assert "Item." not in blob
    assert report["harmless"] is None
    assert report["necessary"] is None
    assert report["suffix_control_arm"] is False
    assert report["conclusion"] == "unresolved"
    assert report["implementation_correction"] is False
    sentence = report["sentence"]
    assert sentence["cues"] == []
    assert sentence["mentions_float"] is True
    assert sentence["mentions_number"] is False
    assert sentence["contains_digit"] is False
    assert sentence["harmless"] is None
    assert sentence["necessary"] is None
    later = report["later_span_after_authored_sentence"]
    assert later["span_count"] == 2
    assert later["sentence_span_indexes"] == [1]
    assert later["sentence_is_first_span"] is False
    assert report["suffix_only_field"]["sentence_is_first_span"] is True
    floated = float_node(report["cases"]["float_property"], "v")
    assert floated["converted_type"] == "number"
    assert floated["format"] == "float"
    assert floated["suffix_appended"] is True
    assert floated["type_encodes_float"] is False
    assert floated["format_encodes_float"] is True
    doubled = float_node(report["cases"]["double_property"], "v")
    assert doubled["converted_type"] == "number"
    assert doubled["format"] is None
    assert doubled["suffix_appended"] is False
    integer = float_node(report["cases"]["integer_property"], "v")
    assert integer["converted_type"] == "integer"
    assert integer["suffix_appended"] is False
    item = float_node(report["cases"]["array_item_float"], "items")
    assert item["original_type"] == "float"
    assert item["converted_type"] == "number"
    assert item["format"] is None
    assert item["suffix_appended"] is False
    nested_item = float_node(report["cases"]["array_of_array_float"], "items/items")
    assert nested_item["suffix_appended"] is False
    assert nested_item["format"] is None
    inner = float_node(report["cases"]["array_object_float"], "inner")
    assert inner["format_encodes_float"] is True
    assert inner["suffix_appended"] is True
    assert report["missing_description"]["converted"] is False
    assert report["missing_description"]["error"] == "KeyError"
    kept = compress([tool("ta", FLOAT_SUFFIX)], "C", DEFAULT_CONFIG, Words())
    assert description(kept) == FLOAT_SUFFIX
    dropped = compress([tool("ta", "Length." + FLOAT_SUFFIX)], "C", DEFAULT_CONFIG, Words())
    assert FLOAT_SUFFIX not in description(dropped)


def test_commands_and_protocol_files_stay_offline():
    assert main(["manifest"]) == 0
    assert main(["inspect-suffix"]) == 0
    assert main(["groups"]) == 0
    package = ROOT / "src" / "tool_compression"
    for name in NEW_MODULES:
        text = (package / name).read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if not (stripped.startswith("import ") or stripped.startswith("from ")):
                continue
            module = stripped.split()[1].split(".")[0].rstrip(",")
            assert module not in {"openai", "httpx", "urllib", "requests", "socket"}
    protocol = (ROOT / "EVALUATION-PROTOCOL-v1.1.md").read_text(encoding="utf-8")
    note = (ROOT / "OPERATIONAL-NOTE-v1.1.md").read_text(encoding="utf-8")
    plan = (ROOT / "Controlled_Tool_Description_Compression_Agent_Plan.md").read_text(encoding="utf-8")
    inspection = (ROOT / "FLOAT_SUFFIX_INSPECTION.md").read_text(encoding="utf-8")
    packet = (ROOT / "evidence" / "WEEK1_EVIDENCE_PACKET.md").read_text(encoding="utf-8")
    assert protocol.startswith("# Evaluation Protocol v1.1")
    assert "S_{LU}" in protocol
    assert "not granted by this note" in note
    assert "bc-8c54379f" in note
    assert "Week 1 historical handoff" in plan
    assert "Current handoff (Evaluation Protocol v1.1)" in plan
    assert "Then STOP for review before package hardening" in plan
    assert "later authorization for continuing unpaid implementation" in plan
    assert "L is a reporting label only" in plan
    assert "not evidence that the contrast term was tested" in plan
    assert "`f` is still 0" in plan
    assert "separate authorization and a spending ceiling" in plan
    assert "It is not a current instruction" not in plan
    assert "format" in inspection
    assert "200" in inspection
    assert "**stop**" in packet
    assert "f is 0/200" in packet or "0/200" in packet


def test_groups_command_writes_a_short_summary(tmp_path, capsys):
    destination = tmp_path / "groups.json"
    assert main(["groups", "--out", str(destination)]) == 0
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["provisional_unique_request_groups_per_replicate"]["multiple"] == 438
    assert payload["provisional_unique_request_groups_per_replicate"]["all_categories"] == 1513
    assert payload["target_reached"] is None
    printed = capsys.readouterr().out
    assert "wrote" in printed
