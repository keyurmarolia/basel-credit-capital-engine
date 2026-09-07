from __future__ import annotations

import numpy as np

from basel_credit_risk.output_floor import calculate_output_floor
from basel_credit_risk.pipeline import run_pipeline


def test_ead_identity() -> None:
    result = run_pipeline(portfolio_size=500, write_outputs=False)
    df = result.exposures
    assert np.allclose(df["ead_pre_crm"], df["funded_exposure"] + df["ccf"] * df["undrawn_amount"])


def test_sa_rwa_aggregates() -> None:
    result = run_pipeline(portfolio_size=500, write_outputs=False)
    assert np.isclose(result.exposures["sa_rwa"].sum(), result.tables["sa_summary"]["sa_rwa"].sum())


def test_irb_outputs_are_bounded() -> None:
    df = run_pipeline(portfolio_size=500, write_outputs=False).exposures
    assert df["asset_correlation_r"].between(0, 1).all()
    assert (df["capital_k"] >= 0).all()
    assert (df["irb_rwa"] >= 0).all()


def test_output_floor_is_aggregate() -> None:
    floor = calculate_output_floor(100.0, 50.0, 20.0, 30.0, 0.725)
    standardised = floor.loc[floor["metric"].eq("Standardised aggregate RWA base"), "value"].iloc[0]
    floor_amount = floor.loc[floor["metric"].eq("Output-floor amount"), "value"].iloc[0]
    assert standardised == 150.0
    assert floor_amount == 108.75


def test_base_stress_is_identity() -> None:
    result = run_pipeline(portfolio_size=500, write_outputs=False)
    base = result.scenarios["base"]
    current = result.exposures
    assert np.allclose(base["ead_pre_crm"], current["ead_pre_crm"])
    assert np.allclose(base["irb_rwa"], current["irb_rwa"])
