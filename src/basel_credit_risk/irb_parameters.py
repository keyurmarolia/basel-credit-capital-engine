"""Loan-level IRB PD, downturn LGD, EAD and maturity preparation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .pd_transition import assign_long_run_pd


def _mapped_parameter(frame: pd.DataFrame, assumptions: dict, name: str) -> pd.Series:
    return frame["product_type"].map(
        lambda product: float(assumptions.get(product, assumptions["other"])[name])
    )


def _calculate_lgd(frame: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Build normal and downturn LGD from recoveries, costs and recovery time."""
    out = frame.copy()
    assumptions = config["recovery_assumptions"]
    discount_rate = float(config["recovery_discount_rate"])

    for condition in ["normal", "downturn"]:
        collateral_rate = _mapped_parameter(out, assumptions, f"{condition}_collateral_recovery")
        unsecured_rate = _mapped_parameter(out, assumptions, f"{condition}_unsecured_recovery")
        cost_rate = _mapped_parameter(out, assumptions, f"{condition}_cost_rate")
        recovery_years = _mapped_parameter(out, assumptions, f"{condition}_recovery_years")

        recoverable_collateral = np.minimum(
            out["ead_irb"], out["collateral_value"] * collateral_rate
        )
        unsecured_exposure = np.maximum(out["ead_irb"] - recoverable_collateral, 0.0)
        gross_recovery = recoverable_collateral + unsecured_exposure * unsecured_rate
        discounted_recovery = gross_recovery / (1 + discount_rate) ** recovery_years
        workout_cost = out["ead_irb"] * cost_rate
        economic_loss = out["ead_irb"] - discounted_recovery + workout_cost
        lgd = np.clip(economic_loss / out["ead_irb"].replace(0, np.nan), 0.0, 1.0).fillna(0.0)

        out[f"{condition}_collateral_recovery_rate"] = collateral_rate
        out[f"{condition}_unsecured_recovery_rate"] = unsecured_rate
        out[f"{condition}_workout_cost_rate"] = cost_rate
        out[f"{condition}_recovery_years"] = recovery_years
        out[f"{condition}_discounted_recovery"] = discounted_recovery
        out[f"{condition}_workout_cost"] = workout_cost
        out[f"{condition}_lgd"] = lgd

    out["downturn_lgd"] = np.maximum(out["downturn_lgd"], out["normal_lgd"])
    out["lgd_method"] = "DISCOUNTED_RECOVERY_COST_DOWNTURN_BUILD"
    return out


def _assign_parameter_source(frame: pd.DataFrame, config: dict) -> pd.DataFrame:
    out = frame.copy()
    revenue_limit = float(config["large_corporate_airb_revenue_limit_eur"])
    large_corporate_restricted = out["performing_exposure_class"].eq("corporate") & out[
        "annual_revenue_eur"
    ].gt(revenue_limit)
    bank_restricted = out["performing_exposure_class"].eq("bank")
    retail = out["performing_exposure_class"].isin(
        [
            "residential_real_estate",
            "retail_transactor",
            "revolving_retail",
            "regulatory_retail",
            "other_retail",
        ]
    )
    out["irb_parameter_source"] = np.select(
        [bank_restricted, large_corporate_restricted, retail],
        [
            "FOUNDATION_SUPERVISORY_PARAMETERS",
            "FOUNDATION_SUPERVISORY_PARAMETERS",
            "RETAIL_IRB_OWN_ESTIMATES",
        ],
        default="OWN_ESTIMATE_PARAMETERS",
    )
    out["airb_restriction_flag"] = bank_restricted | large_corporate_restricted
    return out


def prepare_irb_parameters(
    df: pd.DataFrame,
    config: dict,
    transition_config: dict,
) -> pd.DataFrame:
    """Prepare visible PD, LGD, EAD and M inputs for every loan."""
    out = assign_long_run_pd(df, transition_config)
    out["pd_scenario"] = out["pd_long_run"]
    if "pd_stress_multiplier" in out:
        performing = out["default_flag"].eq(0)
        out.loc[performing, "pd_scenario"] = np.minimum(
            out.loc[performing, "pd_long_run"] * out.loc[performing, "pd_stress_multiplier"],
            1.0,
        )
    out = _assign_parameter_source(out, config)
    out["irb_function"] = out["performing_exposure_class"].map(config["exposure_classes"])
    # SA granularity and IRB revolving-pool eligibility are separate tests.
    out.loc[out["is_individual"], "irb_function"] = "other_retail"
    out.loc[out["qrre_eligible"], "irb_function"] = "qrre"
    out.loc[out["performing_exposure_class"].eq("residential_real_estate"), "irb_function"] = (
        "mortgage"
    )
    if out["irb_function"].isna().any():
        raise ValueError("Missing IRB function mapping.")

    sovereign = out["performing_exposure_class"].eq("sovereign")
    qrre_revolver = out["irb_function"].eq("qrre") & ~out["retail_transactor"]
    pd_floor = np.where(
        sovereign,
        0.0,
        np.where(qrre_revolver, config["qrre_revolver_pd_floor"], config["pd_floor"]),
    )
    out["pd_input"] = out["pd_scenario"]
    out["pd_floor_applied"] = pd_floor
    out["pd_regulatory"] = np.where(
        out["default_flag"].eq(1),
        1.0,
        np.maximum(out["pd_scenario"], pd_floor),
    )

    own_ccf = out["commitment_type"].map(config["own_ccf_estimates"]).astype(float)
    foundation_source = out["irb_parameter_source"].eq("FOUNDATION_SUPERVISORY_PARAMETERS")
    own_eligible = out["revolving_flag"] & out["ccf"].lt(1.0) & ~foundation_source
    out["irb_ccf"] = np.where(own_eligible, own_ccf, out["ccf"])
    out["irb_ccf_source"] = np.where(
        ~own_eligible,
        "SUPERVISORY_CCF",
        "SYNTHETIC_OWN_CCF_ESTIMATE",
    )
    out["ead_irb_before_floor"] = out["funded_exposure"] + out["irb_ccf"] * out["undrawn_amount"]
    out["ead_irb_floor"] = out["funded_exposure"] + np.where(
        sovereign, 0.0, config["own_ead_floor_fraction"] * out["ccf"] * out["undrawn_amount"]
    )
    out["ead_irb"] = np.maximum(out["ead_irb_before_floor"], out["ead_irb_floor"])
    out = _calculate_lgd(out, config)
    if "lgd_stress_addon" in out:
        out["downturn_lgd"] = np.clip(out["downturn_lgd"] + out["lgd_stress_addon"], 0.0, 1.0)

    haircuts = out["collateral_type"].map(config["irb_collateral_haircuts"]).fillna(1.0)
    secured_share = (out["collateral_value"] * (1 - haircuts) / out["ead_irb"]).clip(0, 1)
    floors = config["lgd_floors"]
    unsecured_floor = np.where(
        out["irb_function"].eq("other_retail"),
        floors["other_retail_unsecured"],
        floors["corporate_unsecured"],
    )
    secured_floor = out["collateral_type"].map(floors).fillna(0.0)
    out["lgd_floor_applied"] = unsecured_floor * (1 - secured_share) + secured_floor * secured_share
    out.loc[out["irb_function"].eq("mortgage"), "lgd_floor_applied"] = floors["mortgage"]
    out.loc[out["irb_function"].eq("qrre"), "lgd_floor_applied"] = floors["qrre"]
    out.loc[sovereign, "lgd_floor_applied"] = 0.0
    supervisory = config["foundation_lgd"]
    unsecured_lgd = np.where(
        out["performing_exposure_class"].eq("bank"),
        supervisory["bank_unsecured"],
        supervisory["corporate_unsecured"],
    )
    secured_lgd = out["collateral_type"].map(supervisory).fillna(0.0)
    out["foundation_lgd"] = unsecured_lgd * (1 - secured_share) + secured_lgd * secured_share
    out["lgd_input"] = np.where(foundation_source, out["foundation_lgd"], out["downturn_lgd"])
    out["lgd_regulatory"] = np.where(
        foundation_source,
        out["foundation_lgd"],
        np.maximum(out["lgd_input"], out["lgd_floor_applied"]),
    )
    out.loc[foundation_source, "lgd_floor_applied"] = 0.0
    out["lgd_source"] = np.where(
        foundation_source, "SUPERVISORY_FOUNDATION_LGD", "SYNTHETIC_RECOVERY_LGD_WITH_FLOOR"
    )

    out["maturity_input"] = out["contractual_maturity_years"]
    out["m_effective"] = out["maturity_input"].clip(
        float(config["maturity_min"]), float(config["maturity_max"])
    )
    out.loc[foundation_source, "m_effective"] = config["foundation_maturity"]
    out["maturity_source"] = np.where(
        foundation_source, "FOUNDATION_2_5_YEARS", "CONTRACTUAL_CONSERVATIVE_PROXY"
    )
    out["maturity_floor_applied"] = ~foundation_source & out["maturity_input"].lt(
        float(config["maturity_min"])
    )
    out["maturity_cap_applied"] = ~foundation_source & out["maturity_input"].gt(
        float(config["maturity_max"])
    )
    return out
