from __future__ import annotations

import numpy as np

from basel_credit_risk.pd_transition import build_transition_matrix
from basel_credit_risk.pipeline import run_pipeline


def test_ccf_comes_from_commitment_type() -> None:
    result = run_pipeline(portfolio_size=1_000, write_outputs=False)
    frame = result.exposures
    expected = {
        name: float(rule["ccf"]) for name, rule in result.configs["ccf_parameters"]["rules"].items()
    }
    mapped = frame["commitment_type"].map(expected)
    assert np.allclose(frame["ccf"], mapped)


def test_mortgage_ltv_uses_full_loan_amount() -> None:
    frame = run_pipeline(portfolio_size=1_000, write_outputs=False).exposures
    mortgages = frame[frame["performing_exposure_class"].eq("residential_real_estate")]
    expected_amount = mortgages["outstanding_balance"] + mortgages["undrawn_amount"]
    expected_ltv = expected_amount / mortgages["property_value_prudent"]
    assert np.allclose(mortgages["ltv_loan_amount"], expected_amount)
    assert np.allclose(mortgages["ltv"], expected_ltv)


def test_transition_matrices_sum_to_one() -> None:
    result = run_pipeline(portfolio_size=500, write_outputs=False)
    config = result.configs["pd_transition_assumptions"]
    for profile in config["profiles"].values():
        matrix = build_transition_matrix(profile, config["matrix_method"], config["grade_order"])
        assert np.allclose(matrix.sum(axis=1), 1.0)


def test_long_run_pd_is_assigned_by_profile_and_grade() -> None:
    result = run_pipeline(portfolio_size=1_000, write_outputs=False)
    frame = result.exposures
    profiles = result.configs["pd_transition_assumptions"]["profiles"]
    performing = frame[frame["default_flag"].eq(0)]
    expected = [
        profiles[profile]["default_rates"][grade]
        for profile, grade in zip(
            performing["pd_transition_profile"], performing["internal_grade"], strict=True
        )
    ]
    assert np.allclose(performing["pd_long_run"], expected)


def test_downturn_lgd_is_not_below_normal_lgd() -> None:
    frame = run_pipeline(portfolio_size=1_000, write_outputs=False).exposures
    assert (frame["downturn_lgd"] >= frame["normal_lgd"]).all()


def test_effective_maturity_has_one_year_floor_and_five_year_cap() -> None:
    frame = run_pipeline(portfolio_size=1_000, write_outputs=False).exposures
    assert frame["m_effective"].between(1.0, 5.0).all()
    foundation = frame["irb_parameter_source"].eq("FOUNDATION_SUPERVISORY_PARAMETERS")
    assert frame.loc[foundation, "m_effective"].eq(2.5).all()
    frame = frame.loc[~foundation]
    assert frame.loc[frame["maturity_input"].gt(5), "m_effective"].eq(5).all()
    assert frame.loc[frame["maturity_input"].lt(1), "m_effective"].eq(1).all()


def test_irb_rwa_is_loan_level_k_times_ead_times_12_5() -> None:
    frame = run_pipeline(portfolio_size=1_000, write_outputs=False).exposures
    expected = 12.5 * frame["capital_k"] * frame["ead_irb"]
    assert np.allclose(frame["irb_rwa"], expected)


def test_retail_correlation_and_maturity_rules() -> None:
    frame = run_pipeline(portfolio_size=1_000, write_outputs=False).exposures
    mortgage = frame[frame["irb_function"].eq("mortgage")]
    qrre = frame[frame["irb_function"].eq("qrre")]
    retail = frame[frame["irb_function"].isin(["mortgage", "qrre", "other_retail"])]
    assert np.allclose(mortgage["asset_correlation_r"], 0.15)
    assert np.allclose(qrre["asset_correlation_r"], 0.04)
    assert np.allclose(retail["maturity_adjustment"], 1.0)
