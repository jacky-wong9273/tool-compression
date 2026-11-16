"""Synthetic Week 1 checks. No benchmark prose and no model calls."""

from pathlib import Path
import json

import pytest

from tool_compression.adapter import description_slots
from tool_compression.compress import compress
from tool_compression.config import DEFAULT_CONFIG, Config
from tool_compression.convert import to_openai_completions_tools
from tool_compression.decision import recommend
from tool_compression.lexical import select_neighbours
from tool_compression.load import load_category
from tool_compression.prepare import cohort_ratio
from tool_compression.publish import dump_public
from tool_compression.segment import render, segment_spans
from tool_compression.validate import catalogue_violations

ROOT = Path(__file__).resolve().parents[1]
COMPRESSOR_FILES = (
    "compress.py",
    "select.py",
    "lexical.py",
    "segment.py",
    "cues.py",
    "adapter.py",
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


def test_segmentation_keeps_abbreviations_and_decimals():
    assert len(segment_spans("See e.g. this item.")) == 1
    assert len(segment_spans("Use 3.14 exactly.")) == 1
    assert len(segment_spans("Hello. World.")) == 2
    text = "A.  B."
    spans = segment_spans(text)
    assert render(text, spans, set(range(len(spans)))) == text


def test_contrast_changes_the_optional_span_and_identities_hold():
    catalogue = [
        tool("ta", "AAAA. bbbb cccc. dddd eeee."),
        tool("tb", "bbbb cccc."),
    ]
    independent = compress(catalogue, "I", DEFAULT_CONFIG, Words())
    contrast = compress(catalogue, "C", DEFAULT_CONFIG, Words())
    protected = compress(catalogue, "P", DEFAULT_CONFIG, Words())
    assert description(independent) == "AAAA. bbbb cccc."
    assert description(protected) == "AAAA. bbbb cccc."
    assert description(contrast) == "AAAA. dddd eeee."
    alone = [tool("ta", "AAAA. bbbb cccc. dddd eeee.")]
    assert description(compress(alone, "C", DEFAULT_CONFIG, Words())) == description(
        compress(alone, "I", DEFAULT_CONFIG, Words())
    )
    zero = Config(lambda_numerator=0)
    assert description(compress(catalogue, "C", zero, Words())) == description(independent)


def test_protected_prefix_stops_and_independent_skips():
    catalogue = [tool("ta", "AAAA. bbbb cccc dddd. eeee.")]
    protected = description(compress(catalogue, "P", DEFAULT_CONFIG, Words()))
    independent = description(compress(catalogue, "I", DEFAULT_CONFIG, Words()))
    assert protected == "AAAA."
    assert independent == "AAAA. eeee."
    assert description(compress(catalogue, "C", DEFAULT_CONFIG, Words())) == independent


def test_single_span_empty_and_whitespace_stay_put():
    catalogue = [tool("ta", "Alpha beta gamma.", param="   ")]
    for method in ("U", "P", "I", "C"):
        result = compress(catalogue, method, DEFAULT_CONFIG, Words())
        assert description(result) == "Alpha beta gamma."
        assert result["catalogue"][0]["function"]["parameters"]["properties"]["x"]["description"] == "   "
    blank = [tool("ta", "")]
    assert description(compress(blank, "C", DEFAULT_CONFIG, Words())) == ""


def test_cap_freeze_uplift_and_no_mutation():
    class Expand:
        name = "expand"

        def count(self, text: str) -> int:
            if text == "Alpha.":
                return 9
            return len(text.split())

    frozen = compress([tool("ta", "Alpha. beta.")], "I", DEFAULT_CONFIG, Expand())
    field = frozen["traces"][0]["fields"][0]
    assert field["frozen"] is True
    assert description(frozen) == "Alpha. beta."
    lifted = compress([tool("ta", "One two three four. x.")], "P", DEFAULT_CONFIG, Words())
    lifted_field = lifted["traces"][0]["fields"][0]
    assert lifted_field["uplift"] is True
    assert lifted_field["achieved"] <= lifted_field["budget"]
    original = [tool("ta", "AAAA. bbbb cccc. dddd eeee.")]
    snapshot = json.loads(json.dumps(original))
    compress(original, "C", DEFAULT_CONFIG, Words())
    assert original == snapshot


def test_default_object_is_not_a_description_slot():
    catalogue = [tool("ta", "AAAA. bbbb cccc. dddd eeee.")]
    catalogue[0]["function"]["parameters"]["properties"]["x"]["default"] = {"description": "KEEP_ME"}
    result = compress(catalogue, "C", DEFAULT_CONFIG, Words())
    kept = result["catalogue"][0]["function"]["parameters"]["properties"]["x"]["default"]["description"]
    assert kept == "KEEP_ME"
    assert result["unlisted_descriptions"] >= 1
    broken = json.loads(json.dumps(result["catalogue"]))
    broken[0]["function"]["parameters"]["properties"]["x"]["default"]["description"] = "EDITED"
    assert catalogue_violations(result["catalogue"], broken)


def test_items_description_is_allowlisted_and_unsupported_passes_through():
    catalogue = [
        {
            "type": "function",
            "function": {
                "name": "n",
                "description": "D.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "rows": {"type": "array", "items": {"type": "string", "description": "one row"}}
                    },
                },
            },
        }
    ]
    pointers = [pointer for pointer, _, _ in description_slots(catalogue[0])]
    assert "/function/parameters/properties/rows/items/description" in pointers
    unsupported = [{"type": "custom"}]
    result = compress(unsupported, "C", DEFAULT_CONFIG, Words())
    assert result["catalogue"] == unsupported
    assert result["unsupported_tools"] == 1


def test_conversion_renames_dots_and_suffixes_floats():
    tools = to_openai_completions_tools(
        [
            {
                "name": "a.b",
                "description": "Measure.",
                "parameters": {"properties": {"v": {"type": "float", "description": "length"}}},
            }
        ]
    )
    function = tools[0]["function"]
    assert function["name"] == "a_b"
    prop = function["parameters"]["properties"]["v"]
    assert prop["type"] == "number"
    assert prop["format"] == "float"
    assert prop["description"] == "length This is a float type value."


def test_neighbour_tie_keeps_the_earlier_catalogue_index():
    chosen = select_neighbours([{"a", "b"}, {"a"}, {"b"}], max_neighbours=1)
    assert chosen[0][0] == (1,)


def test_cohort_ratio_is_not_the_mean_of_ratios():
    ratio = cohort_ratio([100, 10], [90, 0])
    assert ratio["mean_of_per_case_ratios"] == pytest.approx(0.55)
    assert ratio["ratio_of_means"] == pytest.approx(20 / 110)


def test_loader_refuses_labels(tmp_path):
    data = tmp_path / "bfcl_eval" / "data"
    data.mkdir(parents=True)
    (data / "BFCL_v4_multiple.json").write_text(
        json.dumps([{"id": "a", "question": [[]], "function": [], "possible_answer": 1}]) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError):
        load_category(tmp_path, "multiple")
    hidden = tmp_path / "possible_answer" / "BFCL_v4_multiple.json"
    hidden.parent.mkdir()
    hidden.write_text("[]\n", encoding="utf-8")
    with pytest.raises(RuntimeError):
        load_category(hidden.parent, "multiple")


def test_collapsed_local_arms_stop_even_when_e_is_compatible():
    categories = {}
    for name in ("multiple", "simple_python", "irrelevance"):
        categories[name] = {
            "tools_per_record": {"max": 1 if name != "multiple" else 4},
            "request_differences": {"C_vs_I": 0, "P_vs_I": 0, "C_vs_U": 3},
            "active_fraction_c_vs_i": {"numerator": 0, "denominator": 10, "value": 0.0},
        }
    result = recommend(
        {"structural_violations": 0, "categories": categories},
        {"check_completed": True, "boundary_compatible": True},
    )
    assert result["decision"] == "stop"
    assert result["decision"] != "go"
    assert result["utility_aim_established"] is False
    assert "primary_contrast_inactive" in result["reasons"]
    assert "local_arms_are_one_intervention" in result["reasons"]
    assert "paid_original_scope_not_justified" in result["reasons"]


def test_shared_request_groups_count_distinct_hashes():
    from tool_compression.packet import shared_request_groups

    local = [
        {"category": "multiple", "id": "a", "hashes": {"U": "u", "P": "c", "I": "c", "C": "c"}},
        {"category": "multiple", "id": "b", "hashes": {"U": "u", "P": "u", "I": "u", "C": "u"}},
    ]
    arm = [
        {"category": "multiple", "id": "a", "ok": True, "hash": "e"},
        {"category": "multiple", "id": "b", "ok": True, "hash": "u"},
    ]
    assert shared_request_groups(local, arm) == {"multiple": {"3": 1, "1": 1}}


def test_hard_rules_never_call_an_incompatible_comparator_a_go():
    characterization = {
        "structural_violations": 0,
        "categories": {
            "simple_python": {"tools_per_record": {"max": 1}, "request_differences": {"C_vs_I": 0}},
            "irrelevance": {"tools_per_record": {"max": 1}, "request_differences": {"C_vs_I": 0}},
            "multiple": {
                "request_differences": {"C_vs_U": 4},
                "active_fraction_c_vs_i": {"value": 0.02},
            },
        },
    }
    incompatible = recommend(
        characterization, {"check_completed": True, "boundary_compatible": False}
    )
    incomplete = recommend(characterization, {"check_completed": False, "boundary_compatible": False})
    assert incompatible["decision"] == "narrow-to-local"
    assert incomplete["decision"] == "narrow-to-local"
    assert incompatible["utility_aim_established"] is False
    identical = json.loads(json.dumps(characterization))
    identical["categories"]["multiple"]["request_differences"]["C_vs_U"] = 0
    stopped = recommend(identical, {"check_completed": True, "boundary_compatible": True})
    assert stopped["decision"] == "stop"
    blocked = json.loads(json.dumps(characterization))
    blocked["structural_violations"] = 1
    assert recommend(blocked, {"check_completed": True, "boundary_compatible": True})["decision"] == "stop"


def test_compressor_modules_do_not_read_labels_or_questions():
    package = ROOT / "src" / "tool_compression"
    for name in COMPRESSOR_FILES:
        text = (package / name).read_text(encoding="utf-8")
        assert "possible_answer" not in text
        assert "ground_truth" not in text
        assert "question" not in text


def test_specification_records_the_cue_names():
    text = (ROOT / "SPECIFICATION.md").read_text(encoding="utf-8")
    for name in ("first_span", "negation", "condition", "unit", "default", "restriction", "literal"):
        assert name in text
    assert "week1.0" in text


def test_public_json_rejects_long_strings(tmp_path):
    with pytest.raises(RuntimeError):
        dump_public(tmp_path / "bad.json", {"text": "x" * 401})


def test_arm_e_edit_classes_walk_each_tool():
    from tool_compression.external import edit_classes

    catalogue = [tool("ta", "Hello there."), tool("tb", "Keep.")]
    edited = json.loads(json.dumps(catalogue))
    edited[0]["function"]["description"] = "Hello."
    edited[1]["function"]["description"] = "keep."
    classes = edit_classes(catalogue, edited)
    assert classes == {"unchanged": 2, "case_or_punctuation_only": 1, "substantive": 1}


def test_committed_evidence_stops_and_keeps_the_measured_partition():
    evidence = ROOT / "evidence"
    characterization = json.loads((evidence / "week1_characterization.json").read_text(encoding="utf-8"))
    arm_e = json.loads((evidence / "week1_arm_e.json").read_text(encoding="utf-8"))
    decision = recommend(characterization, arm_e)
    primary = characterization["categories"]["multiple"]
    assert decision["decision"] == "stop"
    assert decision["utility_aim_established"] is False
    assert "narrow-to-local" not in decision["decision"]
    assert arm_e["boundary_compatible"] is True
    assert primary["active_fraction_c_vs_i"]["numerator"] == 0
    assert primary["active_fraction_c_vs_i"]["denominator"] == 200
    assert primary["request_differences"]["C_vs_U"] == 89
    assert primary["request_differences"]["C_vs_I"] == 0
    suffix_only = primary["records_changed_only_by_float_suffix"]["C"]
    other = primary["records_with_other_description_changes"]["C"]
    assert suffix_only + other == 89
    assert primary["selection_differences"]["fields"]["C_vs_I"] == 0
    packet = (evidence / "WEEK1_EVIDENCE_PACKET.md").read_text(encoding="utf-8")
    assert "**stop**" in packet
    assert "bbbb cccc" not in packet
    assert "SENTINEL" not in packet


def test_sentinel_question_does_not_enter_the_summary():
    from tool_compression.characterize import characterize_study

    record = {
        "id": "s",
        "question": [[{"role": "user", "content": "SENTINEL_QUESTION_DO_NOT_LEAK"}]],
        "function": [
            {
                "name": "pkg.fn",
                "description": "AAAA. bbbb cccc. dddd eeee.",
                "parameters": {
                    "properties": {"x": {"type": "string", "description": "xxxx"}},
                },
            }
        ],
    }
    payload, _rows = characterize_study({"multiple": [record]}, Words(), Words(), DEFAULT_CONFIG)
    blob = json.dumps(payload)
    assert "SENTINEL_QUESTION_DO_NOT_LEAK" not in blob
    assert "bbbb cccc" not in blob
    assert payload["utility_aim_established"] is False
