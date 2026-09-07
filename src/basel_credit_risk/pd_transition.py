"""Transparent synthetic rating migrations and long-run grade PD assignment."""

from __future__ import annotations

import numpy as np
import pandas as pd


def build_transition_matrix(
    profile: dict, matrix_method: dict, grade_order: list[str]
) -> pd.DataFrame:
    """Create a simple one-year matrix whose default column is the long-run PD anchor."""
    performing_grades = grade_order[:-1]
    stay_probability = float(matrix_method["stay_probability"])
    upgrade_probability = float(matrix_method["upgrade_probability"])
    rows: list[dict[str, float | str]] = []

    for position, grade in enumerate(performing_grades):
        default_probability = float(profile["default_rates"][grade])
        available_probability = 1.0 - default_probability
        stay = min(stay_probability, available_probability)
        upgrade = min(upgrade_probability, max(available_probability - stay, 0.0))
        downgrade = max(available_probability - stay - upgrade, 0.0)

        row = {destination: 0.0 for destination in grade_order}
        row["From grade"] = grade
        row[grade] += stay
        if position == 0:
            row[grade] += upgrade
        else:
            row[performing_grades[position - 1]] += upgrade
        if position == len(performing_grades) - 1:
            row[grade] += downgrade
        else:
            row[performing_grades[position + 1]] += downgrade
        row["D"] = default_probability
        rows.append(row)

    default_row = {destination: 0.0 for destination in grade_order}
    default_row["From grade"] = "D"
    default_row["D"] = 1.0
    rows.append(default_row)
    return pd.DataFrame(rows).set_index("From grade")[grade_order]


def pd_profile_for_exposure(frame: pd.DataFrame) -> pd.Series:
    """Map each loan to the transition profile appropriate to its IRB family."""
    conditions = [
        frame["performing_exposure_class"].eq("sovereign"),
        frame["performing_exposure_class"].eq("bank"),
        frame["performing_exposure_class"].isin(["corporate", "corporate_sme", "other"]),
        frame["performing_exposure_class"].eq("residential_real_estate"),
        frame["qrre_eligible"],
    ]
    profiles = [
        "sovereign",
        "bank",
        "corporate",
        "residential_mortgage",
        "qualifying_revolving_retail",
    ]
    return pd.Series(
        np.select(conditions, profiles, default="other_retail"),
        index=frame.index,
        dtype="object",
    )


def assign_long_run_pd(frame: pd.DataFrame, transition_config: dict) -> pd.DataFrame:
    """Assign the D-column probability for the loan's grade and risk profile."""
    out = frame.copy()
    out["pd_transition_profile"] = pd_profile_for_exposure(out)
    default_rates = {
        profile: values["default_rates"]
        for profile, values in transition_config["profiles"].items()
    }
    out["pd_long_run"] = [
        float(default_rates[profile][grade])
        for profile, grade in zip(out["pd_transition_profile"], out["internal_grade"], strict=True)
    ]
    out.loc[out["default_flag"].eq(1), "pd_long_run"] = 1.0
    out["pd_source"] = "SYNTHETIC_LONG_RUN_TRANSITION_DEFAULT_COLUMN"
    return out
