"""Calculation-safety validation and exception reporting."""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = {
    "exposure_id",
    "borrower_id",
    "product_type",
    "pd_1y",
    "lgd",
    "maturity_years",
    "outstanding_balance",
    "credit_limit",
    "undrawn_amount",
    "collateral_value",
    "default_flag",
    "dpd",
    "commitment_type",
    "borrower_type",
    "contractual_maturity_years",
    "property_value_at_origination",
    "property_value_current",
    "annual_revenue",
}


def validate_exposures(df: pd.DataFrame) -> pd.DataFrame:
    """Return one row per failed validation rule; empty means the data passed."""
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    exceptions: list[dict[str, object]] = []

    def add(mask: pd.Series, rule: str, message: str) -> None:
        for exposure_id in df.loc[mask, "exposure_id"].astype(str):
            exceptions.append({"exposure_id": exposure_id, "rule": rule, "message": message})

    add(df["exposure_id"].duplicated(keep=False), "UNIQUE_EXPOSURE", "Exposure identifier is duplicated.")
    add(df["borrower_id"].isna(), "BORROWER_LINK", "Borrower identifier is missing.")
    add(~df["pd_1y"].between(0, 1), "PD_RANGE", "PD must be between zero and one.")
    add(~df["lgd"].between(0, 1), "LGD_RANGE", "LGD must be between zero and one.")
    add(df["maturity_years"] <= 0, "MATURITY", "Maturity must be positive.")
    add((df[["outstanding_balance", "credit_limit", "undrawn_amount", "collateral_value"]] < 0).any(axis=1), "NON_NEGATIVE", "Balances and collateral must be non-negative.")
    add(df["outstanding_balance"] - df["credit_limit"] > 1.0, "LIMIT_BALANCE", "Outstanding balance exceeds the stated limit.")
    add(
        (df["commitment_type"] == "no_commitment") & (df["undrawn_amount"] > 1.0),
        "COMMITMENT_UNDRAWN",
        "A facility with undrawn exposure must have a commitment type.",
    )
    add(
        df["product_type"].eq("mortgage") & df["property_value_current"].le(0),
        "MORTGAGE_PROPERTY_VALUE",
        "A mortgage requires a positive property value.",
    )
    add((df["default_flag"] == 1) & (df["dpd"] <= 90), "DEFAULT_DPD", "Synthetic default requires DPD above 90.")
    return pd.DataFrame(exceptions, columns=["exposure_id", "rule", "message"])


def validation_summary(df: pd.DataFrame, exceptions: pd.DataFrame) -> pd.DataFrame:
    """Produce a compact control table for reporting."""
    return pd.DataFrame(
        {
            "control": ["Exposure count", "Unique exposure IDs", "Exception count", "Gross balance", "Undrawn amount"],
            "value": [len(df), df["exposure_id"].nunique(), len(exceptions), df["outstanding_balance"].sum(), df["undrawn_amount"].sum()],
            "status": ["PASS", "PASS" if df["exposure_id"].is_unique else "FAIL", "PASS" if exceptions.empty else "FAIL", "PASS", "PASS"],
        }
    )
