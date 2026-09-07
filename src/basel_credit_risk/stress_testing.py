"""Deterministic credit stress transmission."""

from __future__ import annotations

import numpy as np
import pandas as pd


def apply_stress(df: pd.DataFrame, scenario_name: str, stress_config: dict) -> pd.DataFrame:
    """Apply scenario shocks to a raw portfolio copy.

    Base is deliberately an identity transformation and is tested as such.
    """
    scenario = stress_config["scenarios"][scenario_name]
    out = df.copy()
    cyclical = out["sector"].isin(stress_config["cyclical_sectors"])
    retail = out["product_type"].isin(stress_config["retail_products"])
    multiplier = np.full(len(out), float(scenario["pd_multiplier"]))
    multiplier = np.where(cyclical, float(scenario["cyclical_sector_pd_multiplier"]), multiplier)
    multiplier = np.where(retail, float(scenario["retail_pd_multiplier"]), multiplier)
    out["pd_1y"] = np.clip(out["pd_1y"] * multiplier, 0.00001, 1.0)
    out["pd_stress_multiplier"] = multiplier
    out["lgd_stress_addon"] = float(scenario["lgd_addon"])
    out["collateral_value"] *= 1 - float(scenario["collateral_shock"])
    out["property_value_current"] *= 1 - float(scenario["collateral_shock"])
    addon = float(scenario["undrawn_utilisation_addon"])
    additional_draw = np.minimum(out["undrawn_amount"], out["credit_limit"] * addon)
    out["outstanding_balance"] += additional_draw
    out["undrawn_amount"] -= additional_draw
    out["scenario"] = scenario_name
    return out


def stress_contribution(
    base: pd.DataFrame, stressed: pd.DataFrame, dimension: str, metric: str = "irb_rwa"
) -> pd.DataFrame:
    """Attribute scenario RWA increase to a reporting dimension."""
    base_values = base.groupby(dimension)[metric].sum()
    stressed_values = stressed.groupby(dimension)[metric].sum()
    out = (
        pd.concat([base_values.rename("base_rwa"), stressed_values.rename("stressed_rwa")], axis=1)
        .fillna(0)
        .reset_index()
    )
    out["rwa_increase"] = out["stressed_rwa"] - out["base_rwa"]
    total = out["rwa_increase"].sum()
    out["contribution_share"] = out["rwa_increase"] / total if total else 0.0
    return out.sort_values("rwa_increase", ascending=False).reset_index(drop=True)
