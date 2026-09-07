"""Selected-scope credit risk mitigation treatments with full traceability."""

from __future__ import annotations

import numpy as np
import pandas as pd


def apply_crm(df: pd.DataFrame, crm_config: dict) -> pd.DataFrame:
    """Recognise eligible collateral and guarantees without hiding the treatment type."""
    out = df.copy()
    rules = crm_config["collateral"]
    out["crm_eligible"] = out["collateral_type"].map(
        lambda x: bool(rules.get(x, rules["none"])["eligible"])
    )
    out["collateral_haircut"] = out["collateral_type"].map(
        lambda x: float(rules.get(x, rules["none"])["haircut"])
    )
    out["crm_treatment"] = out["collateral_type"].map(
        lambda x: rules.get(x, rules["none"])["treatment"]
    )
    out["eligible_collateral_value"] = np.where(
        out["crm_eligible"], out["collateral_value"] * (1 - out["collateral_haircut"]), 0.0
    )
    exposure_reduction = out["crm_treatment"].eq("exposure_reduction")
    out["collateral_exposure_reduction"] = np.where(
        exposure_reduction, np.minimum(out["ead_pre_crm"], out["eligible_collateral_value"]), 0.0
    )
    guarantee_haircut = float(crm_config["guarantee"]["eligible_haircut"])
    out["eligible_guarantee_value"] = np.minimum(
        out["ead_pre_crm"], out["guarantee_value"] * (1 - guarantee_haircut)
    )
    out["sa_ead_post_crm"] = np.maximum(
        out["ead_pre_crm"] - out["collateral_exposure_reduction"], 0.0
    )
    out["guaranteed_portion"] = np.minimum(out["sa_ead_post_crm"], out["eligible_guarantee_value"])
    out["unguaranteed_portion"] = out["sa_ead_post_crm"] - out["guaranteed_portion"]
    out["crm_benefit"] = out["ead_pre_crm"] - out["sa_ead_post_crm"]
    out["crm_coverage_ratio"] = np.where(
        out["ead_pre_crm"] > 0,
        np.minimum(
            (out["eligible_collateral_value"] + out["eligible_guarantee_value"])
            / out["ead_pre_crm"],
            1.0,
        ),
        0.0,
    )
    return out
