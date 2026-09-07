from __future__ import annotations

import numpy as np

from basel_credit_risk.pipeline import run_pipeline


def test_rwa_bridge_reconciles() -> None:
    bridge = run_pipeline(portfolio_size=750, write_outputs=False).tables["rwa_bridge"]
    prior = bridge.loc[bridge["driver"].eq("Prior RWA"), "amount"].iloc[0]
    current = bridge.loc[bridge["driver"].eq("Current RWA"), "amount"].iloc[0]
    changes = bridge.loc[bridge["kind"].eq("change"), "amount"].sum()
    assert np.isclose(prior + changes, current, atol=1.0)


def test_capital_ratio_identity() -> None:
    capital = run_pipeline(portfolio_size=500, write_outputs=False).tables["capital_adequacy"]
    assert np.allclose(capital["ratio"], capital["capital_amount"] / capital["total_rwa"])


def test_scenario_ordering() -> None:
    scenarios = run_pipeline(portfolio_size=1_000, write_outputs=False).tables["scenario_summary"].set_index("scenario")
    assert scenarios.loc["base", "irb_credit_rwa"] < scenarios.loc["adverse", "irb_credit_rwa"]
    assert scenarios.loc["adverse", "irb_credit_rwa"] < scenarios.loc["severe", "irb_credit_rwa"]
