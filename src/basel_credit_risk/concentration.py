"""Portfolio concentration metrics for analyst monitoring."""

from __future__ import annotations

import pandas as pd


def concentration_by(df: pd.DataFrame, dimension: str) -> pd.DataFrame:
    """Aggregate EAD/RWA and calculate shares and HHI components."""
    result = (
        df.groupby(dimension, dropna=False)
        .agg(ead=("ead_pre_crm", "sum"), sa_rwa=("sa_rwa", "sum"), irb_rwa=("irb_rwa", "sum"), exposure_count=("exposure_id", "count"), weighted_pd_numerator=("pd_regulatory", lambda x: 0.0))
        .reset_index()
    )
    pd_weight = df.assign(pd_ead=df["pd_regulatory"] * df["ead_pre_crm"]).groupby(dimension, dropna=False)["pd_ead"].sum()
    lgd_weight = df.assign(lgd_ead=df["lgd_regulatory"] * df["ead_pre_crm"]).groupby(dimension, dropna=False)["lgd_ead"].sum()
    result["ead_share"] = result["ead"] / result["ead"].sum()
    result["irb_rwa_share"] = result["irb_rwa"] / result["irb_rwa"].sum()
    result["hhi_component"] = result["ead_share"] ** 2
    result["weighted_pd"] = result[dimension].map(pd_weight) / result["ead"]
    result["weighted_lgd"] = result[dimension].map(lgd_weight) / result["ead"]
    return result.sort_values("ead", ascending=False).reset_index(drop=True)


def borrower_concentration(df: pd.DataFrame) -> pd.DataFrame:
    """Return borrower-level exposure and cumulative concentration shares."""
    out = (
        df.groupby(["borrower_id", "connected_group_id"], as_index=False)
        .agg(ead=("ead_pre_crm", "sum"), irb_rwa=("irb_rwa", "sum"), facility_count=("exposure_id", "count"))
        .sort_values("ead", ascending=False)
        .reset_index(drop=True)
    )
    out["ead_share"] = out["ead"] / out["ead"].sum()
    out["cumulative_ead_share"] = out["ead_share"].cumsum()
    return out


def concentration_summary(df: pd.DataFrame) -> pd.DataFrame:
    borrower = borrower_concentration(df)
    sector = concentration_by(df, "sector")
    return pd.DataFrame(
        {
            "metric": ["Borrower HHI", "Sector HHI", "Top 10 borrower share", "Top 20 borrower share", "Top 5 sector share"],
            "value": [
                (borrower["ead_share"] ** 2).sum(),
                sector["hhi_component"].sum(),
                borrower.head(10)["ead_share"].sum(),
                borrower.head(20)["ead_share"].sum(),
                sector.head(5)["ead_share"].sum(),
            ],
        }
    )

