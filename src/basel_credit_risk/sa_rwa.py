"""Selected-scope Basel Standardised Approach RWA engine."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _mortgage_weight(ltv: float, bands: list[dict]) -> float:
    for band in bands:
        if ltv <= float(band["max_ltv"]):
            return float(band["risk_weight"])
    return float(bands[-1]["risk_weight"])


def calculate_sa_rwa(df: pd.DataFrame, sa_config: dict, crm_config: dict) -> pd.DataFrame:
    """Assign SA risk weights and calculate exposure-level RWA."""
    out = df.copy()
    rating_tables = sa_config["rating_risk_weights"]
    fixed = sa_config["fixed_risk_weights"]
    standard_mortgage_bands = sa_config["mortgage_ltv_bands_not_income_dependent"]
    income_dependent_bands = sa_config["mortgage_ltv_bands_income_dependent"]
    out["ltv_loan_amount"] = out["outstanding_balance"] + out["undrawn_amount"]
    out["property_value_prudent"] = np.minimum(
        out["property_value_at_origination"], out["property_value_current"]
    )
    out["ltv"] = out["ltv_loan_amount"] / out["property_value_prudent"].replace(0, np.nan)

    def risk_weight(row: pd.Series) -> tuple[float, str]:
        cls = row["basel_exposure_class"]
        rating = (
            row["external_rating"]
            if row["external_rating"] in {"AAA", "AA", "A", "BBB", "BB", "B", "CCC"}
            else "UNRATED"
        )
        if cls == "defaulted":
            return float(fixed["defaulted"]), "SA_DEFAULTED"
        if cls == "corporate_sme":
            rw = (
                fixed["corporate_sme"]
                if rating == "UNRATED"
                else rating_tables["corporate"][rating]
            )
            return float(rw), f"SA_CORPORATE_SME_{rating}"
        if cls in rating_tables:
            return float(
                rating_tables[cls].get(rating, rating_tables[cls]["UNRATED"])
            ), f"SA_{cls.upper()}_{rating}"
        if cls == "residential_real_estate":
            bands = (
                income_dependent_bands
                if bool(row["property_cashflow_dependent"])
                else standard_mortgage_bands
            )
            rw = _mortgage_weight(float(row["ltv"]), bands)
            dependency = (
                "INCOME_DEPENDENT" if row["property_cashflow_dependent"] else "OWNER_REPAYMENT"
            )
            return rw, f"SA_MORTGAGE_{dependency}_LTV_{rw:.2f}"
        return float(fixed.get(cls, fixed["other"])), f"SA_FIXED_{str(cls).upper()}"

    assigned = out.apply(risk_weight, axis=1, result_type="expand")
    out[["sa_risk_weight", "sa_rule_id"]] = assigned
    out["sa_rwa_before_guarantee"] = out["sa_ead_post_crm"] * out["sa_risk_weight"]
    guarantee_rw = float(crm_config["guarantee"]["guarantor_risk_weight"])
    # Protection need not be recognised where it would increase the charge.
    out["guarantor_risk_weight_used"] = np.minimum(out["sa_risk_weight"], guarantee_rw)
    out["sa_rwa"] = (
        out["unguaranteed_portion"] * out["sa_risk_weight"]
        + out["guaranteed_portion"] * out["guarantor_risk_weight_used"]
    )
    out["sa_rwa_density"] = np.where(
        out["sa_ead_post_crm"] > 0, out["sa_rwa"] / out["sa_ead_post_crm"], 0.0
    )
    return out
