"""Week 1 go / narrow-to-local / stop rules.

``recommend`` returns the historical Week 1 decision. An inactive primary
contrast still stops. Evaluation Protocol v1.1 is a later authorization for
unpaid implementation. It does not change the decision this module returns,
and it does not authorize official accuracy or provider-usage measurement.

The utility aim is never marked established here. A local counter cannot meet
the provider-token target. Structural failure stops. An incomplete or
boundary-incompatible E check narrows to the local arms and is not called a go.
Identical primary C and U requests stop: under any request-determined accounting
those requests have the same provider input total, so the reference saving is zero.
"""


def recommend(characterization: dict, arm_e: dict) -> dict:
    reasons = ["utility_aim_not_established_by_local_counter"]
    if characterization.get("structural_violations"):
        return _pack("stop", reasons + ["structural_violations"])
    for name in ("simple_python", "irrelevance"):
        summary = characterization["categories"][name]
        maximum = summary.get("tools_per_record", {}).get("max")
        contrast = summary.get("request_differences", {}).get("C_vs_I", 0)
        if maximum == 1 and contrast:
            return _pack("stop", reasons + [f"control_identity_failed:{name}"])
    if not arm_e.get("check_completed"):
        return _pack("narrow-to-local", reasons + ["arm_e_check_incomplete"])
    if not arm_e.get("boundary_compatible"):
        return _pack("narrow-to-local", reasons + ["arm_e_outside_description_boundary"])
    primary = characterization["categories"]["multiple"]
    if primary.get("request_differences", {}).get("C_vs_U", 0) == 0:
        return _pack(
            "stop",
            reasons
            + [
                "primary_c_requests_identical_to_u",
                "request_identity_implies_zero_provider_input_difference",
            ],
        )
    return assess_continuing_scope(characterization, arm_e, reasons)


def assess_continuing_scope(characterization: dict, arm_e: dict, reasons: list[str]) -> dict:
    """E matches the boundary and at least one primary C request differs from U.

    This is not a go. Compatibility of E does not by itself justify the original
    paid comparison. A collapsed local contrast (no C/I or P/I request difference)
    means the neighbour term and the separate local arms are not distinct
    interventions. The provider target stays unverified either way. Settings
    are not retuned from these counts.
    """
    extra = ["arm_e_boundary_compatible", "provider_target_unverified"]
    primary = characterization["categories"]["multiple"]
    if primary["active_fraction_c_vs_i"]["numerator"] == 0:
        extra.append("primary_contrast_inactive")
    else:
        extra.append("primary_contrast_active")
    collapsed = True
    for name in ("multiple", "simple_python", "irrelevance"):
        diffs = characterization["categories"][name]["request_differences"]
        if diffs.get("C_vs_I", 0) or diffs.get("P_vs_I", 0):
            collapsed = False
    if collapsed:
        extra.append("local_arms_are_one_intervention")
    extra.append("paid_original_scope_not_justified")
    return _pack("stop", reasons + extra)


def _pack(decision: str, reasons: list[str]) -> dict:
    if decision not in {"go", "narrow-to-local", "stop"}:
        raise ValueError(decision)
    return {
        "decision": decision,
        "reasons": reasons,
        "utility_aim_established": False,
        "phase_2_started": False,
        "paid_inference": False,
    }
