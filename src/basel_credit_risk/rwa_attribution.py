"""Deterministic prior-to-current RWA bridge with an explicit residual."""

from __future__ import annotations

import pandas as pd

from .config import load_yaml
from .irb_rwa import calculate_irb_rwa


def attribute_rwa(
    prior: pd.DataFrame, current: pd.DataFrame, config: dict | None = None
) -> pd.DataFrame:
    """Replace inputs sequentially; nonlinear interactions follow the stated order."""
    config = config or load_yaml("irb_parameters.yaml")
    previous = prior.set_index("exposure_id")
    latest = current.set_index("exposure_id")
    stable_ids = previous.index.intersection(latest.index)
    prior_total = previous["irb_rwa"].sum()
    current_total = latest["irb_rwa"].sum()
    new = latest.loc[latest.index.difference(previous.index), "irb_rwa"].sum()
    runoff = -previous.loc[previous.index.difference(latest.index), "irb_rwa"].sum()
    rows = [
        ["Prior RWA", prior_total, "total"],
        ["New business", new, "change"],
        ["Run-off / repayment", runoff, "change"],
    ]
    state = previous.loc[stable_ids].copy()
    value = state["irb_rwa"].sum()
    groups = {
        "EAD movement": ["ead_irb"],
        "Rating / PD migration": ["pd_regulatory"],
        "LGD / collateral": ["lgd_regulatory"],
        "Maturity": ["m_effective"],
        "Class / eligibility / default": [
            "irb_function",
            "performing_exposure_class",
            "annual_revenue_eur",
            "default_flag",
        ],
    }
    for driver, columns in groups.items():
        state[columns] = latest.loc[stable_ids, columns]
        next_value = calculate_irb_rwa(state, config)["irb_rwa"].sum()
        rows.append([driver, next_value - value, "change"])
        value = next_value
    explained = prior_total + sum(row[1] for row in rows if row[2] == "change")
    rows.extend(
        [
            ["Rounding residual", current_total - explained, "change"],
            ["Current RWA", current_total, "total"],
        ]
    )
    return pd.DataFrame(rows, columns=["driver", "amount", "kind"])
