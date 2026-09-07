"""Calculation-safety validation and exception reporting."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import load_yaml

REQUIRED_COLUMNS = {
    "exposure_id",
    "borrower_id",
    "product_type",
    "pd_1y",
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
    "connected_group_id",
    "segment",
    "is_individual",
    "is_sme",
    "managed_as_retail",
    "retail_transactor",
    "internal_grade",
    "external_rating",
    "accrued_interest",
    "revolving_flag",
    "collateral_type",
    "property_cashflow_dependent",
    "regulatory_real_estate_eligible",
    "guarantee_value",
    "guarantor_type",
    "guarantor_rating",
    "sector",
    "geography",
    "group_total_assets",
    "reporting_date",
    "origination_date",
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

    add(
        df[list(REQUIRED_COLUMNS)].isna().any(axis=1),
        "MISSING_VALUE",
        "A required field is missing.",
    )
    numeric = [
        "pd_1y",
        "contractual_maturity_years",
        "outstanding_balance",
        "credit_limit",
        "undrawn_amount",
        "collateral_value",
        "property_value_at_origination",
        "property_value_current",
        "annual_revenue",
        "group_total_assets",
        "accrued_interest",
        "guarantee_value",
        "dpd",
    ]
    converted = df[numeric].apply(pd.to_numeric, errors="coerce")
    add(
        ~np.isfinite(converted).all(axis=1),
        "FINITE_NUMERIC",
        "Amounts and rates must be finite numbers.",
    )
    if not all(pd.api.types.is_numeric_dtype(df[column]) for column in numeric):
        add(
            pd.Series(True, index=df.index),
            "NUMERIC_TYPE",
            "Numeric fields must use numeric column types.",
        )
        return pd.DataFrame(exceptions, columns=["exposure_id", "rule", "message"])
    products = {
        "mortgage",
        "corporate_revolver",
        "sme_revolver",
        "personal_loan",
        "credit_card",
        "bank_loan",
        "sovereign_bond",
        "other",
    }
    add(~df["product_type"].isin(products), "PRODUCT", "Unknown product type.")
    add(
        ~df["segment"].isin(
            {
                "mortgage",
                "large_corporate",
                "sme",
                "personal_loan",
                "credit_card",
                "bank",
                "sovereign",
                "other",
            }
        ),
        "SEGMENT",
        "Unknown source segment.",
    )
    add(
        ~df["borrower_type"].isin(
            {"individual", "large_corporate", "sme", "bank", "sovereign", "other"}
        ),
        "BORROWER_TYPE",
        "Unknown borrower type.",
    )
    add(
        ~df["commitment_type"].isin(load_yaml("ccf_parameters.yaml")["rules"]),
        "COMMITMENT_TYPE",
        "Unknown commitment type.",
    )
    add(
        ~df["collateral_type"].isin(
            {"none", "cash", "residential_property", "commercial_property"}
        ),
        "COLLATERAL_TYPE",
        "Collateral type outside the selected portfolio scope.",
    )
    grades = {"AAA", "AA", "A", "BBB", "BB", "B", "CCC"}
    add(~df["internal_grade"].isin(grades), "INTERNAL_GRADE", "Unknown internal grade.")
    add(
        ~df["external_rating"].isin(grades | {"UNRATED"}),
        "EXTERNAL_RATING",
        "Unknown external rating.",
    )
    add(
        df["borrower_type"].eq("bank") & df["external_rating"].eq("UNRATED"),
        "BANK_RATING",
        "Unrated-bank SCRA treatment is outside this selected scope.",
    )
    flags = [
        "default_flag",
        "is_individual",
        "is_sme",
        "managed_as_retail",
        "retail_transactor",
        "revolving_flag",
        "property_cashflow_dependent",
        "regulatory_real_estate_eligible",
    ]
    for column in flags:
        add(
            ~df[column].isin([True, False, 0, 1]),
            "BOOLEAN_FLAG",
            f"{column} must be true or false.",
        )
    add(
        ~np.isclose(
            df["outstanding_balance"] + df["undrawn_amount"], df["credit_limit"], rtol=0, atol=1
        ),
        "LIMIT_RECONCILIATION",
        "Drawn plus undrawn must equal the limit.",
    )
    borrower_fields = [
        "sector",
        "geography",
        "internal_grade",
        "external_rating",
        "annual_revenue",
        "group_total_assets",
        "default_flag",
    ]
    inconsistent = df.groupby("borrower_id")[borrower_fields].nunique().gt(1).any(axis=1)
    add(
        df["borrower_id"].map(inconsistent).fillna(False),
        "BORROWER_CONSISTENCY",
        "Borrower attributes differ across facilities.",
    )
    report_date = pd.to_datetime(df["reporting_date"], errors="coerce")
    origin_date = pd.to_datetime(df["origination_date"], errors="coerce")
    add(
        report_date.isna() | origin_date.isna() | origin_date.gt(report_date),
        "DATES",
        "Origination must precede a valid reporting date.",
    )

    add(
        df["exposure_id"].duplicated(keep=False),
        "UNIQUE_EXPOSURE",
        "Exposure identifier is duplicated.",
    )
    add(df["borrower_id"].isna(), "BORROWER_LINK", "Borrower identifier is missing.")
    add(~df["pd_1y"].between(0, 1), "PD_RANGE", "PD must be between zero and one.")
    add(df["contractual_maturity_years"] <= 0, "MATURITY", "Maturity must be positive.")
    add(
        (df[["outstanding_balance", "credit_limit", "undrawn_amount", "collateral_value"]] < 0).any(
            axis=1
        ),
        "NON_NEGATIVE",
        "Balances and collateral must be non-negative.",
    )
    add(
        df["outstanding_balance"] - df["credit_limit"] > 1.0,
        "LIMIT_BALANCE",
        "Outstanding balance exceeds the stated limit.",
    )
    add(
        df["outstanding_balance"].le(0),
        "POSITIVE_BALANCE",
        "The selected portfolio contains positive funded balances.",
    )
    add(
        converted.drop(columns=["pd_1y"]).lt(0).any(axis=1),
        "NON_NEGATIVE_INPUT",
        "Amounts and durations cannot be negative.",
    )
    add(
        df["guarantee_value"].gt(0)
        & (~df["guarantor_type"].eq("eligible_bank") | ~df["guarantor_rating"].eq("AA")),
        "GUARANTOR_SCOPE",
        "This selected scope recognises only eligible AA bank guarantees.",
    )
    add(
        (df["commitment_type"] == "no_commitment") & (df["undrawn_amount"] > 1.0),
        "COMMITMENT_UNDRAWN",
        "A facility with undrawn exposure must have a commitment type.",
    )
    add(
        df["product_type"].eq("mortgage")
        & (df["property_value_current"].le(0) | df["property_value_at_origination"].le(0)),
        "MORTGAGE_PROPERTY_VALUE",
        "A mortgage requires a positive property value.",
    )
    add(
        (df["default_flag"] == 1) & (df["dpd"] <= 90),
        "DEFAULT_DPD",
        "Synthetic default requires DPD above 90.",
    )
    add(
        (df["default_flag"] == 0) & (df["dpd"] > 90),
        "DEFAULT_DPD",
        "DPD above 90 requires default treatment in this scope.",
    )
    return pd.DataFrame(exceptions, columns=["exposure_id", "rule", "message"])


def validation_summary(df: pd.DataFrame, exceptions: pd.DataFrame) -> pd.DataFrame:
    """Produce a compact control table for reporting."""
    return pd.DataFrame(
        {
            "control": [
                "Exposure count",
                "Unique exposure IDs",
                "Exception count",
                "Gross balance",
                "Undrawn amount",
            ],
            "value": [
                len(df),
                df["exposure_id"].nunique(),
                len(exceptions),
                df["outstanding_balance"].sum(),
                df["undrawn_amount"].sum(),
            ],
            "status": [
                "PASS",
                "PASS" if df["exposure_id"].is_unique else "FAIL",
                "PASS" if exceptions.empty else "FAIL",
                "PASS",
                "PASS",
            ],
        }
    )
