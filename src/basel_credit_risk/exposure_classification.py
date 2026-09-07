"""Transparent mapping from source products to Basel-oriented classes."""

from __future__ import annotations

import numpy as np
import pandas as pd


def classify_exposures(df: pd.DataFrame) -> pd.DataFrame:
    """Classify every loan using visible borrower, product and eligibility fields."""
    out = df.copy()
    conditions = [
        out["borrower_type"].eq("sovereign"),
        out["borrower_type"].eq("bank"),
        out["segment"].eq("large_corporate"),
        out["is_sme"] & ~out["managed_as_retail"],
        out["product_type"].eq("mortgage") & out["regulatory_real_estate_eligible"],
        out["product_type"].eq("credit_card") & out["retail_transactor"],
        out["product_type"].eq("credit_card"),
        out["managed_as_retail"],
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
    ]
    out["performing_exposure_class"] = np.select(conditions, classes, default="other")
    out["classification_rule_id"] = np.select(conditions, rules, default="CLASS_OTHER")
    out["basel_exposure_class"] = out["performing_exposure_class"]
    out["classification_exception"] = out["basel_exposure_class"].isna()
    defaulted = out["default_flag"].eq(1)
    out.loc[defaulted, "basel_exposure_class"] = "defaulted"
    out.loc[defaulted, "classification_rule_id"] = "CLASS_DEFAULTED_OVERRIDE"
    return out
