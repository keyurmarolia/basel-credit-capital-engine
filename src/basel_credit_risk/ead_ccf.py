"""Exposure at default and credit-conversion-factor calculations."""

from __future__ import annotations

import pandas as pd


def calculate_ead(df: pd.DataFrame, ccf_config: dict) -> pd.DataFrame:
    """Calculate funded plus converted off-balance-sheet exposure."""
    out = df.copy()
    rules = ccf_config["rules"]
    out["ccf"] = out["commitment_type"].map(lambda x: rules[x]["ccf"])
    out["ccf_rule_id"] = out["commitment_type"].map(lambda x: rules[x]["rule_id"])
    out["ccf_basel_reference"] = out["commitment_type"].map(
        lambda x: rules[x]["basel_reference"]
    )
    out["funded_exposure"] = out["outstanding_balance"] + out["accrued_interest"]
    out["converted_undrawn"] = out["ccf"] * out["undrawn_amount"]
    out["ead_pre_crm"] = out["funded_exposure"] + out["converted_undrawn"]
    return out
