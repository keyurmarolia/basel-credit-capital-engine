"""Deterministic prior-to-current RWA bridge with an explicit residual."""

from __future__ import annotations

import numpy as np
import pandas as pd


def attribute_rwa(prior: pd.DataFrame, current: pd.DataFrame, metric: str = "irb_rwa") -> pd.DataFrame:
    """Explain RWA movement with transparent sequential proxy drivers."""
    cols = ["exposure_id", metric, "ead_pre_crm", "pd_regulatory", "lgd_regulatory", "m_effective"]
    merged = prior[cols].merge(current[cols], on="exposure_id", how="outer", suffixes=("_prior", "_current"), indicator=True)
    prior_total = merged[f"{metric}_prior"].fillna(0).sum()
    current_total = merged[f"{metric}_current"].fillna(0).sum()
    new_business = merged.loc[merged["_merge"].eq("right_only"), f"{metric}_current"].sum()
    runoff = -merged.loc[merged["_merge"].eq("left_only"), f"{metric}_prior"].sum()
    stable = merged["_merge"].eq("both")
    p_rwa = merged.loc[stable, f"{metric}_prior"]
    c_rwa = merged.loc[stable, f"{metric}_current"]
    p_ead = merged.loc[stable, "ead_pre_crm_prior"].replace(0, np.nan)
    c_ead = merged.loc[stable, "ead_pre_crm_current"]
    ead_effect = ((c_ead - p_ead) * (p_rwa / p_ead)).fillna(0).sum()
    stable_change_after_ead = (c_rwa - p_rwa).sum() - ead_effect
    pd_change = (merged.loc[stable, "pd_regulatory_current"] - merged.loc[stable, "pd_regulatory_prior"]).abs().sum()
    lgd_change = (merged.loc[stable, "lgd_regulatory_current"] - merged.loc[stable, "lgd_regulatory_prior"]).abs().sum()
    m_change = (merged.loc[stable, "m_effective_current"] - merged.loc[stable, "m_effective_prior"]).abs().sum()
    scale = pd_change + lgd_change + m_change
    if scale == 0:
        pd_effect = lgd_effect = maturity_effect = 0.0
    else:
        pd_effect = stable_change_after_ead * pd_change / scale
        lgd_effect = stable_change_after_ead * lgd_change / scale
        maturity_effect = stable_change_after_ead * m_change / scale
    residual = current_total - (prior_total + new_business + runoff + ead_effect + pd_effect + lgd_effect + maturity_effect)
    return pd.DataFrame(
        {
            "driver": ["Prior RWA", "New business", "Run-off / repayment", "EAD movement", "Rating / PD migration", "LGD / collateral", "Maturity", "Residual", "Current RWA"],
            "amount": [prior_total, new_business, runoff, ead_effect, pd_effect, lgd_effect, maturity_effect, residual, current_total],
            "kind": ["total", "change", "change", "change", "change", "change", "change", "change", "total"],
        }
    )

