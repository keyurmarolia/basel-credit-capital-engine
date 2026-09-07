"""Basel-style IRB unexpected-loss capital functions."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm


def _correlation(
    pd_values: np.ndarray,
    family: np.ndarray,
    exposure_class: np.ndarray,
    annual_revenue_eur: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    corporate = 0.12 * (1 - np.exp(-50 * pd_values)) / (1 - np.exp(-50)) + 0.24 * (1 - (1 - np.exp(-50 * pd_values)) / (1 - np.exp(-50)))
    other_retail = 0.03 * (1 - np.exp(-35 * pd_values)) / (1 - np.exp(-35)) + 0.16 * (1 - (1 - np.exp(-35 * pd_values)) / (1 - np.exp(-35)))
    sales_million_eur = np.clip(annual_revenue_eur / 1_000_000, 5.0, 50.0)
    sme_adjustment = 0.04 * (1 - (sales_million_eur - 5) / 45)
    sme_adjustment = np.where(exposure_class == "corporate_sme", sme_adjustment, 0.0)
    corporate_after_sme = corporate - sme_adjustment
    correlation = np.select(
        [family == "mortgage", family == "qrre", family == "other_retail"],
        [0.15, 0.04, other_retail],
        default=corporate_after_sme,
    )
    return correlation, sme_adjustment


def calculate_irb_rwa(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Calculate K, expected loss and RWA while retaining intermediate variables."""
    out = df.copy()
    pdv = np.clip(out["pd_regulatory"].to_numpy(float), 1e-8, 1 - 1e-8)
    lgd = out["lgd_regulatory"].to_numpy(float)
    family = out["irb_function"].to_numpy(str)
    exposure_class = out["performing_exposure_class"].to_numpy(str)
    annual_revenue_eur = out["annual_revenue_eur"].to_numpy(float)
    maturity = out["m_effective"].to_numpy(float)
    defaulted = out["default_flag"].to_numpy(int) == 1
    corr, sme_adjustment = _correlation(
        pdv, family, exposure_class, annual_revenue_eur
    )
    b = (0.11852 - 0.05478 * np.log(pdv)) ** 2
    maturity_adj = np.where(family == "corporate", (1 + (maturity - 2.5) * b) / (1 - 1.5 * b), 1.0)
    conditional_pd = norm.cdf((norm.ppf(pdv) / np.sqrt(1 - corr)) + np.sqrt(corr / (1 - corr)) * norm.ppf(float(config["confidence_level"])))
    capital_k = np.maximum((lgd * conditional_pd - pdv * lgd) * maturity_adj, 0.0)
    capital_k = np.where(defaulted, 0.0, capital_k)
    out["asset_correlation_r"] = corr
    out["sme_correlation_adjustment"] = sme_adjustment
    out["correlation_rule"] = np.select(
        [family == "mortgage", family == "qrre", family == "other_retail", exposure_class == "corporate_sme"],
        [
            "IRB_R_15_PERCENT_MORTGAGE",
            "IRB_R_4_PERCENT_QRRE",
            "IRB_R_PD_FUNCTION_OTHER_RETAIL",
            "IRB_R_CORPORATE_PD_WITH_SME_SIZE_ADJUSTMENT",
        ],
        default="IRB_R_CORPORATE_PD_FUNCTION",
    )
    out["maturity_adjustment"] = maturity_adj
    out["conditional_stressed_pd"] = conditional_pd
    out["conditional_pd_999"] = conditional_pd
    out["expected_loss_rate"] = out["pd_regulatory"] * out["lgd_regulatory"]
    out["expected_loss_amount"] = out["expected_loss_rate"] * out["ead_irb"]
    out["capital_k"] = capital_k
    out["irb_rwa"] = float(config["scaling_factor"]) * out["capital_k"] * out["ead_irb"]
    out["irb_rwa_density"] = np.where(out["ead_irb"] > 0, out["irb_rwa"] / out["ead_irb"], 0.0)
    return out
