"""Transparent mapping from source products to Basel-oriented classes."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import load_yaml


def classify_exposures(
    df: pd.DataFrame, config: dict | None = None, ccf_config: dict | None = None
) -> pd.DataFrame:
    """Classify every loan using visible borrower, product and eligibility fields."""
    out = df.copy()
    config = config or load_yaml("classification_parameters.yaml")
    ccf_config = ccf_config or load_yaml("ccf_parameters.yaml")
    out["annual_revenue_eur"] = out["annual_revenue"] / config["inr_per_eur"]
    corporate = out["segment"].isin(["large_corporate", "sme"])
    sme = corporate & out["annual_revenue_eur"].between(
        0.01, config["corporate_sme_sales_limit_eur"]
    )
    retail_product = out["product_type"].isin(["personal_loan", "credit_card", "sme_revolver"])
    retail_candidate = retail_product & (out["is_individual"] | (sme & out["managed_as_retail"]))
    screening_ccf = out["commitment_type"].map(
        {k: v["ccf"] for k, v in ccf_config["rules"].items()}
    )
    if screening_ccf.isna().any():
        raise ValueError("Unknown commitment type in retail eligibility check.")
    gross = (
        out["outstanding_balance"] + out["accrued_interest"] + screening_ccf * out["undrawn_amount"]
    )
    retail_gross = gross.where(retail_candidate, 0.0)
    out["retail_counterparty_exposure"] = retail_gross.groupby(out["connected_group_id"]).transform(
        "sum"
    )
    small = out["retail_counterparty_exposure"].le(
        config["retail_counterparty_limit_eur"] * config["inr_per_eur"]
    )
    retail_pool = retail_gross.where(small & out["default_flag"].eq(0), 0.0).sum()
    out["retail_granularity_pass"] = out["retail_counterparty_exposure"].le(
        retail_pool * config["retail_granularity_limit"]
    )
    out["regulatory_retail_eligible"] = retail_candidate & small & out["retail_granularity_pass"]
    card = out["product_type"].eq("credit_card") & out["regulatory_retail_eligible"]
    out["qrre_eligible"] = (
        out["product_type"].eq("credit_card")
        & out["is_individual"]
        & out["revolving_flag"]
        & out["collateral_type"].eq("none")
        & out["credit_limit"].le(config["qrre_limit_eur"] * config["inr_per_eur"])
        & out["managed_as_retail"]
    )
    conditions = [
        out["borrower_type"].eq("sovereign"),
        out["borrower_type"].eq("bank"),
        corporate & ~sme,
        sme & ~out["regulatory_retail_eligible"],
        out["product_type"].eq("mortgage") & out["regulatory_real_estate_eligible"],
        card & out["retail_transactor"],
        card,
        out["regulatory_retail_eligible"],
        out["is_individual"],
    ]
    classes = [
        "sovereign",
        "bank",
        "corporate",
        "corporate_sme",
        "residential_real_estate",
        "retail_transactor",
        "revolving_retail",
        "regulatory_retail",
        "other_retail",
    ]
    rules = [
        "CLASS_SOVEREIGN_OBLIGOR",
        "CLASS_BANK_OBLIGOR",
        "CLASS_GENERAL_CORPORATE",
        "CLASS_CORPORATE_SME",
        "CLASS_REGULATORY_RESIDENTIAL_REAL_ESTATE",
        "CLASS_RETAIL_TRANSACTOR",
        "CLASS_REVOLVING_RETAIL",
        "CLASS_REGULATORY_RETAIL",
        "CLASS_OTHER_RETAIL",
    ]
    out["performing_exposure_class"] = np.select(conditions, classes, default="other")
    out["classification_rule_id"] = np.select(conditions, rules, default="CLASS_OTHER")
    out["basel_exposure_class"] = out["performing_exposure_class"]
    out["classification_exception"] = out["performing_exposure_class"].eq("other") & out[
        "segment"
    ].ne("other")
    if out["classification_exception"].any():
        raise ValueError("Unmapped borrower or product in exposure classification.")
    defaulted = out["default_flag"].eq(1)
    out.loc[defaulted, "basel_exposure_class"] = "defaulted"
    out.loc[defaulted, "classification_rule_id"] = "CLASS_DEFAULTED_OVERRIDE"
    return out
