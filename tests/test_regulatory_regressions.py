"""Independent checks for regulatory routing, inputs, summaries and attribution."""

from copy import deepcopy

import numpy as np
import pytest

from basel_credit_risk.config import load_all_config
from basel_credit_risk.data_generation import generate_portfolio
from basel_credit_risk.data_validation import validate_exposures
from basel_credit_risk.pipeline import calculate_exposures, representative_sample, run_pipeline
from basel_credit_risk.rwa_attribution import attribute_rwa


@pytest.fixture(scope="module")
def result():
    return run_pipeline(portfolio_size=2000, write_outputs=False)


def test_all_qualifying_cards_use_retail_irb(result):
    cards = result.exposures.loc[lambda x: x["qrre_eligible"]]
    assert not cards.empty
    assert cards["irb_function"].eq("qrre").all()
    assert cards["asset_correlation_r"].eq(0.04).all()
    assert cards["maturity_adjustment"].eq(1.0).all()


def test_foundation_unsecured_lgd_and_maturity(result):
    foundation = result.exposures.loc[
        lambda x: x["airb_restriction_flag"] & x["collateral_type"].eq("none")
    ]
    banks = foundation["performing_exposure_class"].eq("bank")
    assert banks.any() and (~banks).any()
    assert np.allclose(foundation.loc[banks, "lgd_regulatory"], 0.45)
    assert np.allclose(foundation.loc[~banks, "lgd_regulatory"], 0.40)
    assert foundation["m_effective"].eq(2.5).all()


def test_class_specific_input_floors(result):
    x = result.exposures
    revolvers = x["irb_function"].eq("qrre") & ~x["retail_transactor"]
    assert x.loc[revolvers, "pd_floor_applied"].eq(0.001).all()
    assert x.loc[x["irb_function"].eq("qrre"), "lgd_floor_applied"].eq(0.50).all()
    assert x.loc[x["irb_function"].eq("mortgage"), "lgd_floor_applied"].eq(0.05).all()
    own = ~x["airb_restriction_flag"]
    assert (x.loc[own, "lgd_regulatory"] >= x.loc[own, "lgd_floor_applied"]).all()


def test_own_ead_floor_binds_when_ccf_assumption_is_low():
    cfg = deepcopy(load_all_config())
    cfg["irb_parameters"]["own_ccf_estimates"]["other_commitment"] = 0
    x = calculate_exposures(generate_portfolio(1000).current, cfg)
    affected = ~x["airb_restriction_flag"] & x["commitment_type"].eq("other_commitment")
    assert affected.any()
    assert (x.loc[affected, "ead_irb"] > x.loc[affected, "ead_irb_before_floor"]).all()
    assert np.allclose(
        x.loc[affected, "ead_irb"],
        x.loc[affected, "funded_exposure"] + 0.5 * 0.4 * x.loc[affected, "undrawn_amount"],
    )


def test_lgd_uses_irb_exposure_and_discounted_recovery(result):
    x = result.exposures
    expected = (
        (x["ead_irb"] - x["downturn_discounted_recovery"] + x["downturn_workout_cost"])
        / x["ead_irb"]
    ).clip(0, 1)
    assert np.allclose(x["downturn_lgd"], np.maximum(expected, x["normal_lgd"]))


def test_rated_sme_uses_corporate_rating_table(result):
    x = result.exposures.loc[lambda x: x["basel_exposure_class"].eq("corporate_sme")]
    assert not x.empty
    expected = x["external_rating"].map(
        result.configs["sa_risk_weights"]["rating_risk_weights"]["corporate"]
    )
    assert np.allclose(x["sa_risk_weight"], expected)
    assert x["annual_revenue_eur"].le(50_000_000).all()


def test_sme_above_sales_limit_is_corporate():
    raw = generate_portfolio(100).current.loc[lambda x: x["segment"].eq("sme")].head(1).copy()
    raw["annual_revenue"] = 6_000_000_000
    x = calculate_exposures(raw, load_all_config())
    assert x["performing_exposure_class"].eq("corporate").all()


@pytest.mark.parametrize(
    "column,value",
    [
        ("outstanding_balance", np.nan),
        ("undrawn_amount", np.inf),
        ("product_type", "unknown"),
        ("internal_grade", "unknown"),
        ("contractual_maturity_years", 0),
    ],
)
def test_invalid_input_is_rejected(column, value):
    raw = generate_portfolio(100).current
    raw.loc[0, column] = value
    assert not validate_exposures(raw).empty
    with pytest.raises(ValueError):
        calculate_exposures(raw, load_all_config())


def test_borrower_attributes_are_consistent():
    portfolio = generate_portfolio(1000)
    fields = ["sector", "internal_grade", "external_rating", "annual_revenue", "default_flag"]
    for frame in [portfolio.current, portfolio.prior]:
        assert frame.groupby("borrower_id")[fields].nunique().le(1).all().all()


def test_public_sample_covers_every_segment():
    raw = generate_portfolio(2000).current
    sample = representative_sample(raw, 500)
    assert len(sample) == 500
    assert set(sample["segment"]) == set(raw["segment"])
    assert sample["exposure_id"].is_unique


def test_weighted_summary_matches_independent_calculation(result):
    summary = result.tables["irb_summary"].set_index("basel_exposure_class")
    for name, group in result.exposures.groupby("basel_exposure_class"):
        assert np.isclose(
            summary.loc[name, "weighted_pd"],
            np.average(group["pd_regulatory"], weights=group["ead_irb"]),
        )
        assert np.isclose(
            summary.loc[name, "weighted_lgd"],
            np.average(group["lgd_regulatory"], weights=group["ead_irb"]),
        )


def test_bridge_is_exact_for_an_isolated_ead_change(result):
    prior = result.exposures
    current = prior.copy()
    current["ead_irb"] *= 1.1
    current["irb_rwa"] *= 1.1
    bridge = attribute_rwa(prior, current).set_index("driver")
    assert np.isclose(bridge.loc["EAD movement", "amount"], prior["irb_rwa"].sum() * 0.1)
    assert abs(bridge.loc["Rating / PD migration", "amount"]) < 0.01
    assert abs(bridge.loc["Rounding residual", "amount"]) < 0.01


def test_prior_period_has_real_grade_and_maturity_movements(result):
    bridge = result.tables["rwa_bridge"].set_index("driver")
    assert abs(bridge.loc["Rating / PD migration", "amount"]) > 1
    assert abs(bridge.loc["Maturity", "amount"]) > 1


def test_long_run_pd_is_preserved_under_stress(result):
    assert np.allclose(
        result.scenarios["base"]["pd_long_run"], result.scenarios["severe"]["pd_long_run"]
    )
    assert (
        result.scenarios["severe"]["pd_scenario"] >= result.scenarios["base"]["pd_scenario"]
    ).all()
